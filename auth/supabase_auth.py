from supabase import create_client
from config.settings import SUPABASE_URL, SUPABASE_ANON_KEY
import streamlit as st

def get_supabase_client():
    if "supabase_client" not in st.session_state:
        st.session_state["supabase_client"] = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    return st.session_state["supabase_client"]

def login(email: str, password: str):
    supabase = get_supabase_client()
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        st.session_state["user"] = response.user
        st.session_state["access_token"] = response.session.access_token
        return True, None
    except Exception as e:
        return False, str(e)

def logout():
    try:
        supabase = get_supabase_client()
        supabase.auth.sign_out()
    except Exception:
        pass
    st.session_state.clear()

def get_current_user():
    return st.session_state.get("user", None)

def require_auth():
    """Returns True if logged in, False if not. Call at top of every page."""
    return st.session_state.get("user", None) is not None
