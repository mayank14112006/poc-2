import os
import json
from datetime import datetime, timezone

_supabase_client = None

# Fallback log file in project root
FALLBACK_LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "audit_fallback.log")

def get_supabase():
    global _supabase_client
    if _supabase_client is None:
        from supabase import create_client
        from config.settings import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            raise ValueError("Supabase configuration missing (SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY). Check Infisical settings.")
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    return _supabase_client

def log_event(
    user_id: str,
    request: str,
    decision: str,
    response: str = "",
    blocked_reason: str = ""
):
    """
    Logs an interaction event to the audit_logs table in Supabase.
    If database logging fails, writes to a local fallback file.
    """
    event_data = {
        "user_id": user_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request": request[:2000],  # truncate to prevent excessive length issues
        "decision": decision,
        "response": response[:2000] if response else "",
        "blocked_reason": blocked_reason if blocked_reason else ""
    }
    
    supabase_success = False
    try:
        supabase = get_supabase()
        supabase.table("audit_logs").insert(event_data).execute()
        supabase_success = True
    except Exception as e:
        print(f"CRITICAL: Failed to log event to Supabase: {e}")
        
    if not supabase_success:
        try:
            with open(FALLBACK_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(event_data) + "\n")
            print(f"Audit log fallback: Written to {FALLBACK_LOG_FILE}")
        except Exception as fe:
            print(f"CRITICAL ERROR: Failed to write to fallback log file: {fe}")

def get_recent_logs(limit: int = 50):
    """
    Fetches the most recent audit log entries from the database.
    """
    try:
        supabase = get_supabase()
        response = supabase.table("audit_logs") \
            .select("*") \
            .order("timestamp", desc=True) \
            .limit(limit) \
            .execute()
        return response.data
    except Exception as e:
        print(f"Failed to fetch recent logs: {e}")
        
        # Load from fallback file as query fallback
        fallback_logs = []
        if os.path.exists(FALLBACK_LOG_FILE):
            try:
                with open(FALLBACK_LOG_FILE, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    for line in reversed(lines):
                        if line.strip():
                            fallback_logs.append(json.loads(line.strip()))
                            if len(fallback_logs) >= limit:
                                break
            except Exception as fe:
                print(f"Failed to read fallback logs: {fe}")
        return fallback_logs
