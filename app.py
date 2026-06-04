import streamlit as st
import anthropic
from auth.supabase_auth import login, logout, require_auth, get_current_user
from guardrails.pii_detector import check_pii
from guardrails.intent_filter import check_intent
from guardrails.rate_limiter import check_rate_limit
from services.civic_kb import build_system_prompt
from audit.logger import log_event
from config.settings import ANTHROPIC_API_KEY

# Set up page configurations
st.set_page_config(
    page_title="Pragati Nagar Nigam — Citizen Portal",
    page_icon="🏛️",
    layout="centered"
)

# Custom premium styling using CSS injection
st.markdown("""
<style>
    /* Import modern typography */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Center the login box and give it a card effect */
    .stForm {
        background-color: #1E293B !important;
        padding: 2.5rem !important;
        border-radius: 16px !important;
        border: 1px solid #334155 !important;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.3) !important;
    }
    
    /* Accent text styling */
    .highlight-text {
        background: linear-gradient(135deg, #FF9933 0%, #FFCC66 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
    }
    
    /* Button custom hover animation */
    button[kind="secondaryFormSubmit"], button[kind="primary"] {
        background-color: #FF9933 !important;
        color: white !important;
        border: none !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        transition: transform 0.2s ease, background-color 0.2s ease !important;
    }
    
    button[kind="secondaryFormSubmit"]:hover, button[kind="primary"]:hover {
        transform: translateY(-2px);
        background-color: #E6801A !important;
    }
    
    /* Custom chat alerts styling */
    .stAlert {
        border-radius: 12px !important;
        border: 1px solid #EF4444 !important;
    }
</style>
""", unsafe_allow_html=True)

# ── LOGIN GATE ──────────────────────────────────────────────
if not require_auth():
    st.markdown("<h1 style='text-align: center; margin-top: 5vh;'>🏛️ <span class='highlight-text'>Pragati Nagar Nigam</span></h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94A3B8; font-size: 1.1rem; margin-bottom: 4vh;'>Official Citizen Services Portal & AI Assistant</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 4, 1])
    with col2:
        with st.form("login_form"):
            st.markdown("<h3 style='margin-top:0; text-align: center; color: #FF9933;'>Citizen Login</h3>", unsafe_allow_html=True)
            email = st.text_input("Registered Email ID", placeholder="e.g. citizen@example.com")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Verify & Access Portal")
            
            if submitted:
                if not email or not password:
                    st.error("Please enter both email and password.")
                else:
                    with st.spinner("Authenticating secure session..."):
                        success, error = login(email, password)
                        if success:
                            st.success("Access Granted! Loading portal...")
                            st.rerun()
                        else:
                            st.error(f"Login failed: {error}")
    st.stop()  # Stop execution of the page here if not authenticated

# ── AUTHENTICATED CHAT UI ────────────────────────────────────
user = get_current_user()
user_id = user.id

# Build sidebar user profile and navigation
with st.sidebar:
    st.markdown("<h2 style='color:#FF9933; margin-top:0;'>🏛️ PNN Portal</h2>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(f"**Welcome, Citizen**\n`{user.email}`")
    st.markdown("Securely authenticated via Supabase ID:")
    st.code(user_id[:18] + "...", language="text")
    st.markdown("---")
    st.markdown("### Supported Services:")
    st.markdown("- 🏠 Property Tax\n- 💧 Water Bill\n- 🧹 Sanitation / Waste\n- 👶 Birth Certificate\n- 💼 Trade Licence")
    st.markdown("---")
    if st.button("Secure Logout", use_container_width=True):
        logout()
        st.rerun()

# Chat page header
st.markdown("<h1>🏛️ <span class='highlight-text'>Pragati Nagar Nigam</span> AI Assistant</h1>", unsafe_allow_html=True)
st.caption("Ask questions about property tax, water connections, trade licences, sanitation and more. All conversations are audited for safety.")

# Initialize chat session history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous conversation messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# User Chat Input
if prompt := st.chat_input("How can I apply for a water connection or check property tax?"):
    
    # 1. Render and store user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # Initialize client and build system prompt
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    SYSTEM_PROMPT = build_system_prompt()

    # ── GUARDRAIL G3: Rate limit (cheapest check, do first) ──
    rate_result = check_rate_limit(user_id)
    if not rate_result["allowed"]:
        blocked_msg = f"⚠️ Request Blocked: {rate_result['reason']}"
        log_event(user_id, prompt, "BLOCKED_RATE", blocked_reason=rate_result["reason"])
        with st.chat_message("assistant"):
            st.warning(rate_result["reason"])
        st.session_state.messages.append({"role": "assistant", "content": blocked_msg})
        st.stop()

    # ── GUARDRAIL G1: PII detection ──────────────────────────
    pii_result = check_pii(prompt)
    if not pii_result["safe"]:
        blocked_msg = f"⚠️ Request Blocked: {pii_result['reason']}"
        log_event(user_id, prompt, "BLOCKED_PII", blocked_reason=pii_result["reason"])
        with st.chat_message("assistant"):
            st.warning(pii_result["reason"])
        st.session_state.messages.append({"role": "assistant", "content": blocked_msg})
        st.stop()

    # ── GUARDRAIL G2: Intent filter ──────────────────────────
    intent_result = check_intent(prompt)
    if not intent_result["safe"]:
        blocked_reason_msg = intent_result.get("reason", "Violates chatbot safety guidelines.")
        blocked_msg = f"⚠️ Request Blocked: {blocked_reason_msg}"
        log_event(user_id, prompt, "BLOCKED_INTENT", blocked_reason=blocked_reason_msg)
        with st.chat_message("assistant"):
            st.warning(f"This request cannot be processed: {blocked_reason_msg}")
        st.session_state.messages.append({"role": "assistant", "content": blocked_msg})
        st.stop()

    # ── ALL GUARDRAILS PASSED — call Claude ──────────────────
    with st.chat_message("assistant"):
        with st.spinner("Retrieving official municipal guidelines..."):
            try:
                # Use claude-sonnet-4-5 as specified
                response = client.messages.create(
                    model="claude-sonnet-4-5",
                    max_tokens=1000,
                    system=SYSTEM_PROMPT,
                    messages=[
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.messages
                    ]
                )
                answer = response.content[0].text
                st.write(answer)
                
                # Append answer and log allowed transaction
                st.session_state.messages.append({"role": "assistant", "content": answer})
                log_event(user_id, prompt, "ALLOWED", response=answer)
            except Exception as e:
                st.error(f"Failed to communicate with AI Assistant: {e}")
