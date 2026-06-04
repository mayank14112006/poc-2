import streamlit as st
import pandas as pd
from audit.logger import get_recent_logs
from auth.supabase_auth import require_auth

# Page configuration
st.set_page_config(
    page_title="Admin Panel — PNN Audit Logs",
    page_icon="🔍",
    layout="wide"
)

# Authenticate check
if not require_auth():
    st.error("Access Denied. You must be logged in to view this page.")
    st.stop()

st.title("🔍 Security & Audit Log Dashboard")
st.caption("Review the latest 50 citizen interactions, safety decisions, and guardrail logs below.")

# Refresh button
if st.button("Refresh Logs", type="primary"):
    st.rerun()

# Fetch latest logs
with st.spinner("Retrieving log database..."):
    logs = get_recent_logs(50)

if not logs:
    st.info("No system interactions have been logged yet.")
else:
    df = pd.DataFrame(logs)
    
    # Format timestamps
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
        
    # Clean and order columns
    display_cols = ["timestamp", "user_id", "decision", "request", "blocked_reason", "response"]
    existing_cols = [col for col in display_cols if col in df.columns]
    df_display = df[existing_cols].copy()
    
    # Define custom style mapping function
    def highlight_decision(val):
        colors = {
            "BLOCKED_PII": "background-color: #78350F; color: #FEF3C7; font-weight: bold;", # Amber/Yellow dark theme styling
            "BLOCKED_INTENT": "background-color: #7F1D1D; color: #FEE2E2; font-weight: bold;", # Red styling
            "BLOCKED_RATE": "background-color: #7C2D12; color: #FFEDD5; font-weight: bold;", # Orange styling
            "ALLOWED": "background-color: #064E3B; color: #D1FAE5;" # Green styling
        }
        return colors.get(val, "")
        
    # Style styling mapping
    try:
        # style.map is used in pandas 2.0+
        styled_df = df_display.style.map(highlight_decision, subset=["decision"])
    except AttributeError:
        # fallback to applymap for older pandas versions
        styled_df = df_display.style.applymap(highlight_decision, subset=["decision"])
        
    # Render interactive styled table
    st.dataframe(
        styled_df,
        use_container_width=True,
        height=600
    )
