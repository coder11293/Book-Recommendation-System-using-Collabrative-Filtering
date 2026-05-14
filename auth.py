# auth.py
# ========== AUTHENTICATION FUNCTIONS ==========

import re
import time

import streamlit as st
from database import db


def check_password_strength(password):
    """Validate password strength matching database rules"""
    checks = {
        'length': len(password) >= 8,
        'uppercase': bool(re.search(r'[A-Z]', password)),
        'lowercase': bool(re.search(r'[a-z]', password)),
        'number': bool(re.search(r'\d', password))
    }
    checks['valid'] = all(checks.values())
    return checks


def check_rate_limit():
    """Simple rate limiting to prevent spam"""
    if 'last_auth_request' in st.session_state:
        time_diff = time.time() - st.session_state.last_auth_request
        if time_diff < 0.5:  # 500ms between requests
            return False
    st.session_state.last_auth_request = time.time()
    return True

def render_login_signup():
    """Render login and signup forms in sidebar"""
    
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Sign Up"])
    
    with tab1:
        st.markdown("### Login to your account")
        username = st.text_input("Username", key="login_user", placeholder="Enter your username")
        password = st.text_input("Password", type="password", key="login_pass", placeholder="Enter your password")
        
        if st.button("Login", use_container_width=True, key="login_btn"):
            if not check_rate_limit():
                st.warning("⚠️ Please wait before trying again.")
            elif username and password:
                if db.authenticate(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.page = "Home"
                    st.session_state.get_recs = False
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password.")
            else:
                st.warning("⚠️ Please enter both username and password.")
    
    with tab2:
        st.markdown("### Create new account")
        new_user = st.text_input("Username", key="signup_user", placeholder="Choose a username (min 3 chars)")
        new_pass = st.text_input("Password", key="signup_pass", placeholder="Choose a password (min 8 chars)")
        confirm_pass = st.text_input("Confirm Password", type="password", key="confirm_pass", placeholder="Confirm your password")
        
        # Password strength indicators (show only when user starts typing)
        if new_pass:
            checks = check_password_strength(new_pass)

            if checks['length']:
                st.success("✅ Length: 8+ chars")
            else:
                st.error("❌ Length: need 8+ chars")

            if checks['uppercase'] and checks['lowercase']:
                st.success("✅ Upper & Lowercase")
            else:
                st.error("❌ Need upper & lowercase")

            if checks['number']:
                st.success("✅ Contains numbers")
            else:
                st.error("❌ Need at least one number")
        
        if st.button("Create Account", use_container_width=True, key="signup_btn"):
            if not check_rate_limit():
                st.warning("⚠️ Please wait before trying again.")
            elif not new_user or not new_pass:
                st.warning("⚠️ Please fill all fields.")
            elif new_pass != confirm_pass:
                st.error("❌ Passwords do not match.")
            else:
                success, message = db.save_user(new_user, new_pass)
                if success:
                    st.success("✅ Account created successfully! Please log in.")
                else:
                    st.error(f"❌ {message}")

def logout():
    """Handle user logout"""
    st.session_state.authenticated = False
    st.session_state.username = ""
    st.session_state.page = "Home"
    st.session_state.get_recs = False
    st.session_state.refresh_liked = False

    # Clear rate limiting
    if 'last_auth_request' in st.session_state:
        del st.session_state.last_auth_request

    st.rerun()