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
    Authenticates email and password. Works for both Streamlit and FastAPI.
    Returns: (success_bool, session_object_or_error_string)
    """
    try:
        supabase = get_supabase_client()
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        # Streamlit session integration fallback
        try:
            import streamlit as st
            # Only write if Streamlit session state is initialized and running
            if st.runtime.exists():
                st.session_state["user"] = response.user
                st.session_state["access_token"] = response.session.access_token
        except Exception:
            pass
            
        return True, response
    except Exception as e:
        return False, str(e)

def logout():
    try:
        supabase = get_supabase_client()
        supabase.auth.sign_out()
    except Exception:
        pass
        
    try:
        import streamlit as st
        if st.runtime.exists():
            st.session_state.clear()
    except Exception:
        pass

def get_current_user():
    try:
        import streamlit as st
        if st.runtime.exists():
            return st.session_state.get("user", None)
    except Exception:
        pass
    return None

def require_auth():
    try:
        import streamlit as st
        if st.runtime.exists():
            return st.session_state.get("user", None) is not None
    except Exception:
        pass
    return False
