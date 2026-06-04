from datetime import datetime, timezone

_supabase_client = None

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
    """
    try:
        supabase = get_supabase()
        supabase.table("audit_logs").insert({
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request": request[:2000],  # truncate to prevent excessive length issues
            "decision": decision,
            "response": response[:2000],
            "blocked_reason": blocked_reason if blocked_reason else ""
        }).execute()
    except Exception as e:
        print(f"Failed to log event to Supabase: {e}")

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
        return []
