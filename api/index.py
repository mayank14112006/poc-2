from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import sys

# Add root folder to python path so we can import from existing packages
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.supabase_auth import login as supabase_login
from guardrails.pii_detector import check_pii
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
    success, error = supabase_login(req.email, req.password)
    if success:
        from auth.supabase_auth import get_current_user
        user = get_current_user()
        return {
            "success": True,
            "user": {
                "id": user.id,
                "email": user.email
            }
        }
    else:
        raise HTTPException(status_code=401, detail=f"Login failed: {error}")

@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    if not req.messages:
        raise HTTPException(status_code=400, detail="Empty messages list")
        
    user_id = req.user_id
    prompt = req.messages[-1].content
    
    # ── GUARDRAIL G3: Rate limit (cheapest check, do first) ──
    rate_result = check_rate_limit(user_id)
    if not rate_result["allowed"]:
        log_event(user_id, prompt, "BLOCKED_RATE", blocked_reason=rate_result["reason"])
        return {
            "decision": "BLOCKED_RATE",
            "reason": rate_result["reason"],
            "response": f"⚠️ Request Blocked: {rate_result['reason']}"
        }
        
    # ── GUARDRAIL G1: PII detection ──────────────────────────
    pii_result = check_pii(prompt)
    if not pii_result["safe"]:
        log_event(user_id, prompt, "BLOCKED_PII", blocked_reason=pii_result["reason"])
        return {
            "decision": "BLOCKED_PII",
            "reason": pii_result["reason"],
            "response": f"⚠️ Request Blocked: {pii_result['reason']}"
        }
        
    # ── GUARDRAIL G2: Intent filter ──────────────────────────
    intent_result = check_intent(prompt)
    if not intent_result["safe"]:
        blocked_reason_msg = intent_result.get("reason", "Violates safety guidelines.")
        log_event(user_id, prompt, "BLOCKED_INTENT", blocked_reason=blocked_reason_msg)
        return {
            "decision": "BLOCKED_INTENT",
            "reason": blocked_reason_msg,
            "response": f"⚠️ Request Blocked: {blocked_reason_msg}"
        }
        
    # ── ALL GUARDRAILS PASSED — call Claude ──────────────────
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        SYSTEM_PROMPT = build_system_prompt()
        
        # Transform messages for Anthropic API
        messages_formatted = []
        for m in req.messages:
            # Strip out warning prefix if previous messages in sequence were blocked
            content = m.content
            if content.startswith("⚠️ Request Blocked:"):
                continue
            messages_formatted.append({"role": m.role, "content": content})
            
        if not messages_formatted:
            messages_formatted.append({"role": "user", "content": prompt})

        # Use claude-sonnet-4-5 for response generation
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=messages_formatted
        )
        answer = response.content[0].text
        
        # Log event as allowed
        log_event(user_id, prompt, "ALLOWED", response=answer)
        
        return {
            "decision": "ALLOWED",
            "response": answer
        }
    except Exception as e:
        print(f"FastAPI Next.js Claude call error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to query AI Assistant: {e}")

@app.get("/api/logs")
def get_logs_endpoint():
    logs = get_recent_logs(50)
    return {"logs": logs}
