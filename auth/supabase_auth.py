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
