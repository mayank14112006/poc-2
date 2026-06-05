import time
from supabase import create_client
from config.settings import SUPABASE_URL, SUPABASE_ANON_KEY

_supabase_client = None
_service_role_client = None

# In-memory caches with 5-minute TTL (Time-To-Live)
CACHE_TTL = 300
_token_cache = {}
_admin_cache = {}

def get_supabase_client():
    global _supabase_client
    if _supabase_client is None:
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            raise ValueError("Supabase configuration missing (SUPABASE_URL or SUPABASE_ANON_KEY).")
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    return _supabase_client

def get_service_role_client():
    global _service_role_client
    if _service_role_client is None:
        from config.settings import SUPABASE_SERVICE_ROLE_KEY
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            raise ValueError("Supabase URL or Service Role Key missing.")
        _service_role_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    return _service_role_client

def login(email: str, password: str):
    """
    Authenticates email and password.
    Returns: (success_bool, session_object_or_error_string)
    """
    try:
        supabase = get_supabase_client()
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        return True, response
    except Exception as e:
        return False, str(e)

def verify_token(auth_header: str) -> dict:
    """
    Verifies Supabase access token (JWT) using remote validation.
    Results are cached in memory for CACHE_TTL seconds to eliminate round-trip latency.
    Returns: User dict on success, raises ValueError/Exception on failure.
    """
    if not auth_header or not auth_header.startswith("Bearer "):
        raise ValueError("Missing or invalid Authorization header.")
    
    token = auth_header.split(" ")[1]
    if not token:
        raise ValueError("Empty Authorization token.")
        
    # Check in-memory cache
    now = time.time()
    if token in _token_cache:
        cached = _token_cache[token]
        if now < cached["expires_at"]:
            return cached["user_info"]
        else:
            del _token_cache[token]
            
    supabase = get_supabase_client()
    # Remote token validation with Supabase
    response = supabase.auth.get_user(token)
    if not response or not response.user:
        raise ValueError("Invalid user session.")
    
    user_info = {
        "id": response.user.id,
        "email": response.user.email,
        "raw_user": response.user
    }
    
    # Cache the validation result
    _token_cache[token] = {
        "user_info": user_info,
        "expires_at": now + CACHE_TTL
    }
    
    return user_info

def is_admin_user(user_id: str, raw_user=None) -> bool:
    """
    Checks if a user is an admin.
    Caches database queries to prevent slow queries on every admin route check.
    """
    # 1. Check metadata (role = admin) - Instant, no DB calls
    if raw_user:
        app_metadata = getattr(raw_user, "app_metadata", {}) or {}
        user_metadata = getattr(raw_user, "user_metadata", {}) or {}
        if app_metadata.get("role") == "admin" or user_metadata.get("role") == "admin":
            return True
            
    # Check in-memory cache for database result
    now = time.time()
    if user_id in _admin_cache:
        cached = _admin_cache[user_id]
        if now < cached["expires_at"]:
            return cached["is_admin"]
        else:
            del _admin_cache[user_id]
            
    # 2. Check database admin_users table
    from config.settings import SUPABASE_SERVICE_ROLE_KEY
    if not SUPABASE_SERVICE_ROLE_KEY:
        return False
        
    try:
        service_role_client = get_service_role_client()
        response = service_role_client.table("admin_users") \
            .select("id") \
            .eq("user_id", user_id) \
            .execute()
        is_admin = len(response.data) > 0
        
        # Cache the result
        _admin_cache[user_id] = {
            "is_admin": is_admin,
            "expires_at": now + CACHE_TTL
        }
        return is_admin
    except Exception as e:
        print(f"Error checking admin status in admin_users: {e}")
        return False

