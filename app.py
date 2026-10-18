"""app.py - main entry point.  Run with:  streamlit run app/app.py"""

import streamlit as st
import database as db
import pages_ui as pages

st.set_page_config(page_title="Thyroid CDSM", page_icon="\U0001FA7A", layout="wide")

CSS = """
<style>
#MainMenu, footer {visibility: hidden;}
.block-container {padding-top: 1.2rem;}
.stApp {background: #F4F7FA;}

/* top header banner */
.app-header {
    background: linear-gradient(100deg, #0E7C7B 0%, #1565C0 100%);
    padding: 20px 28px; border-radius: 14px; margin-bottom: 20px;
    box-shadow: 0 4px 14px rgba(14,124,123,0.25);
}
.app-header h1 {color: #ffffff; margin: 0; font-size: 26px; font-weight: 700;}
.app-header p  {color: #e0f2f1; margin: 4px 0 0; font-size: 14px;}

/* section sub-titles */
.card-title {font-size: 16px; font-weight: 700; color: #0E7C7B;
    margin: 14px 0 6px; border-left: 4px solid #0E7C7B; padding-left: 8px;}

/* metric cards */
[data-testid="stMetric"] {background: #fff; border: 1px solid #e3e8ee;
    border-radius: 12px; padding: 14px 18px; box-shadow: 0 1px 3px rgba(0,0,0,.05);}

/* diagnosis result cards */
.result-card {background:#fff; border:1px solid #e3e8ee; border-radius:12px;
    padding:16px 20px; box-shadow:0 1px 3px rgba(0,0,0,.05);}
.rc-label {font-size:13px; color:#6b7a8d; text-transform:uppercase; letter-spacing:.5px;}
.rc-value {font-size:24px; font-weight:700; color:#1A2B3C; margin-top:4px;}

/* treatment card */
.treat-card {background:#f0f7f7; border:1px solid #b2dfdb; border-radius:12px;
    padding:16px 20px; line-height:1.8; color:#1A2B3C;}

/* buttons */
.stButton>button, .stForm button[kind="primary"] {border-radius: 8px; font-weight:600;}

/* login box */
.login-wrap {max-width: 420px; margin: 4vh auto 0;}
</style>
"""


def login_screen():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        "<div class='app-header' style='text-align:center'>"
        "<h1>🦋 Thyroid Clinical Decision Support Module</h1>"
        "<p>Machine-learning assisted thyroid diagnosis & treatment</p></div>",
        unsafe_allow_html=True)
    st.markdown("<div class='login-wrap'>", unsafe_allow_html=True)
    with st.form("login"):
        st.markdown("#### Sign in")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login", type="primary", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
    if submit:
        user = db.verify_user(username, password)
        if user:
            st.session_state.user = user
            db.log_action(username, "login", "")
            st.rerun()
        else:
            st.error("Invalid username or password.")


def main():
    db.ensure_schema()   # auto-upgrade db if needed

    if "user" not in st.session_state:
        login_screen()
        return

    user = st.session_state.user
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        f"<div class='app-header'><h1>🦋 Thyroid CDSM</h1>"
        f"<p>Logged in as {user['full_name']} &nbsp;•&nbsp; role: {user['role']}</p></div>",
        unsafe_allow_html=True)

    st.sidebar.markdown(f"### {user['full_name']}")
    st.sidebar.caption(f"Role: {user['role']}")
    options = ["Dashboard", "Diagnose", "Patient Records", "My Account"]
    if user["role"] == "admin":
        options.append("Admin")
    if st.session_state.get("nav") not in options:
        st.session_state.nav = "Dashboard"
    choice = st.sidebar.radio("Navigate", options, key="nav")
    if st.sidebar.button("Logout", use_container_width=True):
        db.log_action(user["username"], "logout", "")
        del st.session_state.user
        st.rerun()

    if choice == "Diagnose":
        pages.page_diagnose(user)
    elif choice == "Patient Records":
        pages.page_records(user)
    elif choice == "Dashboard":
        pages.page_dashboard(user)
    elif choice == "My Account":
        pages.page_account(user)
    elif choice == "Admin":
        pages.page_admin(user)


if __name__ == "__main__":
    main()