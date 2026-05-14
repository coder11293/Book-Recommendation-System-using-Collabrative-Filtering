# utils.py
# ========== UTILITY FUNCTIONS ==========

import base64
import html
import os
from io import BytesIO

import requests
from PIL import Image
import streamlit as st

from config import BACKGROUND_IMAGE, CSS_FILE

def load_css():
    """Load custom CSS styling"""
    if os.path.exists(CSS_FILE):
        with open(CSS_FILE, 'r') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
        .stApp { background-color: #0e1117; }
        </style>
        """, unsafe_allow_html=True)

def set_background():
    """Set background image with dark overlay"""
    if os.path.exists(BACKGROUND_IMAGE):
        try:
            with open(BACKGROUND_IMAGE, "rb") as img_file:
                base64_image = base64.b64encode(img_file.read()).decode()
                st.markdown(f"""
                    <style>
                    .stApp {{
                        background-image: url("data:image/webp;base64,{base64_image}");
                        background-size: cover;
                        background-position: center top;
                        background-attachment: scroll;
                        background-color: rgba(8,7,6,0.85);
                        background-blend-mode: darken;
                    }}
                    </style>
                """, unsafe_allow_html=True)
        except Exception:
            # Fallback to dark background
            st.markdown("""
                <style>
                .stApp { background-color: #0a0908; }
                </style>
            """, unsafe_allow_html=True)

def load_image_with_fallback(image_url, fallback_emoji="📖"):
    """Load image with timeout and fallback"""
    if not image_url:
        return None
    
    try:
        response = requests.get(image_url, timeout=3)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            return img
    except Exception:
        pass
    return None

def get_initials(name):
    """Get user initials for avatar"""
    # Sanitize input to prevent XSS
    safe_name = html.escape(str(name))
    parts = safe_name.split()
    if len(parts) > 1:
        initials = parts[0][0] + parts[-1][0]
    else:
        initials = safe_name[:2]
    return initials.upper()

def display_user_badge(username):
    """Display user badge in sidebar"""
    # Escape username to prevent XSS
    safe_username = html.escape(str(username))
    av = get_initials(safe_username)
    st.markdown(f"""
    <div class="user-badge">
        <div class="user-avatar">{av}</div>
        <div class="user-info">
            <div class="user-name">{safe_username}</div>
            <div class="user-role">Member</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def landing_page():
    """Display landing page for unauthenticated users"""
    st.markdown("""
    <div class="landing-wrapper">
        <div class="landing-icon">📖</div>
        <h1 class="landing-title">Book Recommendation System</h1>
        <p class="landing-subtitle">Discover your next favorite book with AI-powered recommendations</p>
        <div class="landing-cta">← Login or Sign Up from the sidebar to get started</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Add some CSS for landing page
    st.markdown("""
    <style>
    .landing-subtitle {
        color: #8a8278;
        font-size: 1rem;
        margin-bottom: 2rem;
        text-align: center;
    }
    .landing-wrapper {
        min-height: 70vh;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
    }
    .landing-icon {
        font-size: 4rem;
        margin-bottom: 1rem;
    }
    .landing-title {
        font-size: 2.5rem;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)