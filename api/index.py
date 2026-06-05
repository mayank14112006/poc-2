from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import sys

# Add root folder to python path so we can import from existing packages
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.supabase_auth import login as supabase_login
from guardrails.pii_detector import check_pii, redact_pii, get_anthropic_client
from guardrails.intent_filter import check_intent
from guardrails.rate_limiter import check_rate_limit
from services.civic_kb import build_system_prompt
from audit.logger import log_event, get_recent_logs
from config.settings import ANTHROPIC_API_KEY
import anthropic

app = FastAPI(title="Pragati Nagar Nigam — Next.js API Portal")

# Enable CORS for local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LoginRequest(BaseModel):
    email: str
    password: str

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    user_id: str

@app.post("/api/auth/login")
def login_endpoint(req: LoginRequest):
    success, result = supabase_login(req.email, req.password)
    if success:
        return {
            "success": True,
            "access_token": result.session.access_token,
            "user": {
                "id": result.user.id,
                "email": result.user.email
            }
        }
    else:
        raise HTTPException(status_code=401, detail=f"Login failed: {result}")

@app.post("/api/chat")
def chat_endpoint(req: ChatRequest, request: Request):
    # Verify authentication token (JWT) remotely from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authentication token missing")
        
    try:
        from auth.supabase_auth import verify_token
        user_info = verify_token(auth_header)
        user_id = user_info["id"]
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {e}")

    if not req.messages:
        raise HTTPException(status_code=400, detail="Empty messages list")
        
    prompt = req.messages[-1].content
    redacted_prompt = redact_pii(prompt)
    
    # ── GUARDRAIL G3: Rate limit (cheapest check, do first) ──
    rate_result = check_rate_limit(user_id)
    if not rate_result["allowed"]:
        log_event(user_id, redacted_prompt, "BLOCKED_RATE", blocked_reason=rate_result["reason"])
        return {
            "decision": "BLOCKED_RATE",
            "reason": rate_result["reason"],
            "response": f"⚠️ Request Blocked: {rate_result['reason']}"
        }
        
    # ── GUARDRAIL G1: PII detection ──────────────────────────
    pii_result = check_pii(prompt)
    if not pii_result["safe"]:
        log_event(user_id, redacted_prompt, "BLOCKED_PII", blocked_reason=pii_result["reason"])
        return {
            "decision": "BLOCKED_PII",
            "reason": pii_result["reason"],
            "response": f"⚠️ Request Blocked: {pii_result['reason']}"
        }
        
    # ── GUARDRAIL G2: Intent filter ──────────────────────────
    intent_result = check_intent(prompt)
    if not intent_result["safe"]:
        blocked_reason_msg = intent_result.get("reason", "Violates safety guidelines.")
        log_event(user_id, redacted_prompt, "BLOCKED_INTENT", blocked_reason=blocked_reason_msg)
        return {
            "decision": "BLOCKED_INTENT",
            "reason": blocked_reason_msg,
            "response": f"⚠️ Request Blocked: {blocked_reason_msg}"
        }
        
    # ── ALL GUARDRAILS PASSED — call Claude ──────────────────
    try:
        client = get_anthropic_client()
        SYSTEM_PROMPT = build_system_prompt()
        
        # Transform messages for Anthropic API
        messages_formatted = []
        for m in req.messages[:-1]:
            content = m.content
            if content.startswith("⚠️ Request Blocked:"):
                continue
            # Redact PII from past conversation history to ensure it doesn't leak
            messages_formatted.append({"role": m.role, "content": redact_pii(content)})
            
        messages_formatted.append({"role": "user", "content": redacted_prompt})

        # Use claude-sonnet-4-5 for response generation
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=messages_formatted
        )
        answer = response.content[0].text
        
        # Log event as allowed (with redacted prompt)
        log_event(user_id, redacted_prompt, "ALLOWED", response=answer)
        
        return {
            "decision": "ALLOWED",
            "response": answer
        }
    except Exception as e:
        print(f"FastAPI Next.js Claude call error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to query AI Assistant: {e}")

@app.get("/api/logs")
def get_logs_endpoint(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authentication token missing")
        
    try:
        from auth.supabase_auth import verify_token, is_admin_user
        user_info = verify_token(auth_header)
        user_id = user_info["id"]
        raw_user = user_info["raw_user"]
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {e}")
        
    # Authorize: check if admin in database or metadata
    if not is_admin_user(user_id, raw_user):
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required")
        
    logs = get_recent_logs(50)
    return {"logs": logs}
