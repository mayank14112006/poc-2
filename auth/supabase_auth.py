from supabase import create_client
from config.settings import SUPABASE_URL, SUPABASE_ANON_KEY

_supabase_client = None

def get_supabase_client():
    global _supabase_client
    if _supabase_client is None:
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            raise ValueError("Supabase configuration missing (SUPABASE_URL or SUPABASE_ANON_KEY).")
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    return _supabase_client

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
    Returns: User dict on success, raises ValueError/Exception on failure.
    """
    if not auth_header or not auth_header.startswith("Bearer "):
        raise ValueError("Missing or invalid Authorization header.")
    
    token = auth_header.split(" ")[1]
    if not token:
        raise ValueError("Empty Authorization token.")
        
    supabase = get_supabase_client()
    # Remote token validation with Supabase
    response = supabase.auth.get_user(token)
    if not response or not response.user:
        raise ValueError("Invalid user session.")
    
    # Return user data and raw user object for metadata checks
    return {
        "id": response.user.id,
        "email": response.user.email,
        "raw_user": response.user
    }

def is_admin_user(user_id: str, raw_user=None) -> bool:
    """
    Checks if a user is an admin by querying the admin_users table or inspecting metadata.
    """
    # 1. Check metadata (role = admin)
    if raw_user:
        app_metadata = getattr(raw_user, "app_metadata", {}) or {}
        user_metadata = getattr(raw_user, "user_metadata", {}) or {}
        if app_metadata.get("role") == "admin" or user_metadata.get("role") == "admin":
            return True
            
    # 2. Check database admin_users table
    from config.settings import SUPABASE_SERVICE_ROLE_KEY
    if not SUPABASE_SERVICE_ROLE_KEY:
        return False
        
    try:
        service_role_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        response = service_role_client.table("admin_users") \
            .select("id") \
            .eq("user_id", user_id) \
            .execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"Error checking admin status in admin_users: {e}")
        return False

