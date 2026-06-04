from datetime import datetime, timedelta, timezone

RATE_LIMIT = 10  # max requests per 60 seconds per user
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

def check_rate_limit(user_id: str) -> dict:
    """
    Checks if a user is within the rate limit (max 10 requests per 60 seconds).
    
    Returns:
        {"allowed": True} if under limit
        {"allowed": False, "reason": "..."} if over limit
    """
    since = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
    
    try:
        supabase = get_supabase()
        response = supabase.table("audit_logs") \
            .select("id", count="exact") \
            .eq("user_id", user_id) \
            .gte("timestamp", since) \
            .execute()
        
        count = response.count
        
        if count >= RATE_LIMIT:
            return {
                "allowed": False,
                "reason": f"Rate limit exceeded. You have made {count} requests in the last 60 seconds. Please wait."
            }
    except Exception as e:
        print(f"Rate Limiter error: {e}")
        # Fail-safe / fail-open so the application doesn't crash if database is temporarily unavailable
        return {"allowed": True}
    
    return {"allowed": True}
