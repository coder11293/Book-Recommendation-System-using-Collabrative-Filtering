# app.py
# ========== MAIN STREAMLIT APPLICATION ==========

import html
import logging
import time

import streamlit as st

from config import APP_TITLE, APP_LAYOUT

# set_page_config MUST be the first Streamlit command
# Do NOT import modules that use @st.cache_resource or @st.cache_data before this!
st.set_page_config(
    page_title=APP_TITLE,
    layout=APP_LAYOUT,
    initial_sidebar_state="expanded"
)

# Configure logging after set_page_config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import modules AFTER set_page_config (they use @st.cache_resource)
from auth import render_login_signup, logout
from database import db
from models import get_all_book_names, get_book_details, get_recommendations, is_model_loaded
from utils import display_user_badge, landing_page, load_css, set_background

# ========== ERROR BOUNDARY ==========
class ErrorBoundary:
    """Context manager for handling errors with retry capability"""
    def __init__(self, operation_name):
        self.operation_name = operation_name
        self.error = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, _):
        if exc_type is not None:
            self.error = str(exc_val)
            logger.error(f"Error in {self.operation_name}: {exc_val}")
            return True  # Suppress the exception
        return False

def with_error_boundary(operation_name, fallback=None):
    """Decorator for functions that need error handling"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {operation_name}: {e}")
                if fallback is not None:
                    return fallback
                return None
        return wrapper
    return decorator

# ========== DIAGNOSTIC CHECK ==========
def check_setup():
    """Check if everything is configured correctly"""
    issues = []
    warnings_list = []

    # Check data storage connection
    if not db.is_connected():
        issues.append("❌ Data storage error. Please run setup_database.py.")

    # Check model files
    if not is_model_loaded():
        issues.append("❌ Model files not loaded. Please run train_model.ipynb first")

    # Check background image (warning only)
    import os
    if not os.path.exists("12.webp"):
        warnings_list.append("⚠️ Background image '12.webp' not found")

    if issues:
        st.error("### ⚠️ Setup Issues Found:")
        for issue in issues:
            st.write(f"- {issue}")
        st.info("💡 Please fix the above issues before using the app.")

        # Retry button
        if st.button("🔄 Retry Connection", key="retry_btn"):
            st.rerun()
        st.stop()

    if warnings_list:
        for warning in warnings_list:
            st.warning(warning)

# ========== INITIALIZE SESSION STATE ==========
def init_session_state():
    """Initialize all session state variables"""
    book_names = get_all_book_names()
    
    defaults = {
        'authenticated': False,
        'username': "",
        'current_book': book_names[0] if len(book_names) > 0 else "",
        'get_recs': False,
        'page': "Home",
        'refresh_liked': False,
        'last_request_time': 0
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# ========== RATE LIMITING ==========
def check_rate_limit():
    """Rate limiting for API calls"""
    current_time = time.time()
    if current_time - st.session_state.get('last_request_time', 0) < 0.5:
        return False
    st.session_state.last_request_time = current_time
    return True

# ========== SIDEBAR ==========
def render_sidebar():
    """Render sidebar with user info and navigation"""
    with st.sidebar:
        st.markdown('<div class="brand-logo">📖 Book Recommendation System</div>', unsafe_allow_html=True)
        st.markdown('<div class="brand-sub">Discover your next great read</div>', unsafe_allow_html=True)
        st.markdown('<hr class="sidebar-hr">', unsafe_allow_html=True)

        if st.session_state.authenticated:
            # Show user badge
            display_user_badge(st.session_state.username)

            # Show liked books count
            liked_books = db.load_liked_books(st.session_state.username)
            liked_count = len(liked_books)
            st.markdown(f'<div style="text-align: center; font-size: 0.75rem; color: #8a8278;">❤️ {liked_count} liked books</div>', unsafe_allow_html=True)

            # Show disliked books count
            disliked_books = db.load_disliked_books(st.session_state.username)
            disliked_count = len(disliked_books)
            st.markdown(f'<div style="text-align: center; font-size: 0.75rem; color: #8a8278;">👎 {disliked_count} disliked</div>', unsafe_allow_html=True)

            st.markdown('<hr class="sidebar-hr">', unsafe_allow_html=True)

            # Navigation buttons
            if st.button("🏠  Home", use_container_width=True, key="nav_home"):
                st.session_state.page = "Home"
                st.session_state.refresh_liked = False
                st.rerun()

            if st.button("❤️  Liked Books", use_container_width=True, key="nav_liked"):
                st.session_state.page = "Liked Books"
                st.session_state.refresh_liked = True
                st.rerun()

            if st.button("👎  Disliked Books", use_container_width=True, key="nav_disliked"):
                st.session_state.page = "Disliked Books"
                st.rerun()

            st.markdown('<hr class="sidebar-hr">', unsafe_allow_html=True)

            if st.button("🚪  Logout", use_container_width=True, key="nav_logout"):
                logout()
        else:
            # Show login/signup forms
            render_login_signup()

# ========== HOME PAGE ==========
def home_page():
    """Render home page with book selector and recommendations"""
    book_names = get_all_book_names()
    
    if not book_names:
        st.error("No books found. Please check your model files.")
        return
    
    st.markdown('<h1 class="page-title">📚 Book Recommendation System</h1>', unsafe_allow_html=True)
    st.markdown('<p class="page-sub">Select a book you enjoy and discover similar titles</p>', unsafe_allow_html=True)
    
    # Book selector - filter out disliked books
    disliked_books = db.load_disliked_books(st.session_state.username)
    available_books = [b for b in book_names if b not in disliked_books]

    current_index = 0
    if st.session_state.current_book in available_books:
        current_index = available_books.index(st.session_state.current_book)

    selected_book = st.selectbox(
        "🔍 Select a book you like",
        available_books,
        index=current_index,
        key="book_selector"
    )
    
    # If current book is disliked, auto-switch to another but DON'T auto-fetch
    if st.session_state.current_book in disliked_books and available_books:
        st.session_state.current_book = available_books[0]
        st.session_state.get_recs = False  # Don't auto-fetch, user clicks manually

    if selected_book != st.session_state.current_book:
        st.session_state.current_book = selected_book
        st.session_state.get_recs = False  # Don't auto-fetch, user clicks manually

    # Get recommendations button
    col_btn, _, _ = st.columns([2, 2, 3])
    with col_btn:
        if st.button("🎯 Get Recommendations", use_container_width=True, key="get_recs_btn"):
            if check_rate_limit():
                with st.spinner("🔍 Finding similar books..."):
                    st.session_state.get_recs = True
            else:
                st.warning("Please wait a moment before trying again.")

    # Show recommendations
    if st.session_state.get_recs:
        with st.spinner("📚 Loading recommendations..."):
            # Get more recommendations than needed to fill after filtering
            all_recs = get_recommendations(st.session_state.current_book, n_recommendations=20)

            # Filter out disliked books
            disliked_books = db.load_disliked_books(st.session_state.username)
            recs = [r for r in all_recs if r not in disliked_books][:10]  # Take top 10

            book = get_book_details(st.session_state.current_book)
        
        if book:
            # Display selected book details
            st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
            col_img, col_info = st.columns([1, 3], gap="large")
            
            with col_img:
                img_url = book.get('image_url', '')
                if img_url:
                    try:
                        st.image(img_url, use_container_width=True)
                    except Exception:
                        st.markdown('<div style="text-align: center; font-size: 3rem;">📖</div>', unsafe_allow_html=True)
            
            with col_info:
                title = html.escape(str(book.get('title', 'Unknown Title')))
                author = html.escape(str(book.get('author', 'Unknown Author')))
                pub = html.escape(str(book.get('publisher', 'N/A')))
                year = html.escape(str(book.get('year', 'N/A')))
                rating = book.get('avg_rating', 'N/A')
                num_rat = book.get('num_of_rating', 'N/A')
                
                st.markdown(f'<div class="book-title">{html.escape(title)}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="book-author">by {html.escape(author)}</div>', unsafe_allow_html=True)
                st.markdown(f"""
                <div class="book-pills">
                    <span class="pill">⭐ {rating} / 10</span>
                    <span class="pill">👥 {num_rat} ratings</span>
                    <span class="pill">📅 {year}</span>
                    <span class="pill">🏢 {pub}</span>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("<div style='margin-top:1.4rem'></div>", unsafe_allow_html=True)
                
                # Check if book is already liked or disliked
                liked_books = db.load_liked_books(st.session_state.username)
                disliked_books = db.load_disliked_books(st.session_state.username)
                is_liked = st.session_state.current_book in liked_books
                is_disliked = st.session_state.current_book in disliked_books

                # Like/Dislike buttons - side by side
                btn_col1, btn_col2 = st.columns([1, 1], gap="small")
                with btn_col1:
                    if is_liked:
                        if st.button("✅ Liked", key="like_btn", disabled=True):
                            pass
                    elif is_disliked:
                        if st.button("❌ Disliked", key="like_btn_disliked", disabled=True):
                            pass
                    else:
                        if st.button("❤️ Like", key="like_btn"):
                            if check_rate_limit():
                                with st.spinner("💾 Saving..."):
                                    success, message = db.save_like(st.session_state.username, st.session_state.current_book)
                                    if success:
                                        st.success(message)
                                        st.rerun()
                                    else:
                                        st.info(message)
                            else:
                                st.warning("Please wait a moment before trying again.")

                with btn_col2:
                    if is_disliked:
                        if st.button("👎 Disliked", key="dislike_btn_disabled", disabled=True):
                            pass
                    elif is_liked:
                        if st.button("👎  Remove Like", key="dislike_btn_liked"):
                            if check_rate_limit():
                                with st.spinner("💾 Removing..."):
                                    success, message = db.remove_like(st.session_state.username, st.session_state.current_book)
                                    if success:
                                        st.info(message)
                                        st.rerun()
                            else:
                                st.warning("Please wait a moment before trying again.")
                    else:
                        if st.button("👎  Not for Me", key="dislike_btn"):
                            if check_rate_limit():
                                with st.spinner("💾 Saving..."):
                                    success, message = db.save_dislike(st.session_state.username, st.session_state.current_book)
                                    if success:
                                        st.success(message)
                                        # Don't refresh - let user manually search
                                    else:
                                        st.info(message)
                            else:
                                st.warning("Please wait a moment before trying again.")
            
            # Display recommendations (already filtered to 10)
            st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="section-heading">📖 Top {len(recs)} Recommendations for You</div>', unsafe_allow_html=True)

            if recs:
                for row_start in range(0, len(recs), 5):
                    cols = st.columns(5, gap="small")
                    for j, col in enumerate(cols):
                        idx = row_start + j
                        if idx >= len(recs):
                            break
                        rec_title = recs[idx]
                        rec_book = get_book_details(rec_title)
                        if rec_book:
                            with col:
                                # Escape output to prevent XSS
                                safe_title = html.escape(rec_title[:38])
                                rec_img = rec_book.get('image_url', '')
                                if rec_img:
                                    try:
                                        st.image(rec_img, use_container_width=True)
                                    except Exception:
                                        st.markdown('<div style="text-align: center; font-size: 2rem;">📚</div>', unsafe_allow_html=True)
                                rec_rat = rec_book.get('avg_rating', 'N/A')
                                st.markdown(f"""
                                <div class="rec-card-text">
                                    <div class="rec-title">{safe_title}…</div>
                                    <div class="rec-rating">⭐ {rec_rat}</div>
                                </div>
                                """, unsafe_allow_html=True)
                                if st.button("Explore →", key=f"rec_{row_start}_{j}", use_container_width=True):
                                    if check_rate_limit():
                                        st.session_state.current_book = rec_title
                                        st.session_state.get_recs = True
                                        st.rerun()
            else:
                st.warning("No recommendations found for this book.")
    else:
        # Empty state
        st.markdown("""
        <div class="empty-state">
            <div class="empty-icon">🔍</div>
            <div class="empty-text">
                Select a book above and click<br>
                <strong>"Get Recommendations"</strong> to discover similar titles.
            </div>
        </div>
        """, unsafe_allow_html=True)

# ========== LIKED BOOKS PAGE ==========
def liked_books_page():
    """Render liked books page"""
    st.markdown('<h1 class="page-title">❤️ Your Liked Books</h1>', unsafe_allow_html=True)
    
    # Load liked books - always fresh from database
    liked_books = db.load_liked_books(st.session_state.username)

    # Back to Home button (full width, prominent)
    col_btn, _ = st.columns([1, 4])
    with col_btn:
        if st.button("🏠 Back to Home", use_container_width=True, type="primary"):
            st.session_state.page = "Home"
            st.rerun()

    st.markdown("---")
    
    if liked_books:
        st.markdown(f'<p class="page-sub" style="text-align: center;">You have saved <strong>{len(liked_books)}</strong> book{"s" if len(liked_books) > 1 else ""}</p>', unsafe_allow_html=True)
        
        # Display books in a grid
        for row_start in range(0, len(liked_books), 4):
            cols = st.columns(4, gap="small")
            for j, col in enumerate(cols):
                idx = row_start + j
                if idx >= len(liked_books):
                    break
                title = liked_books[idx]
                book = get_book_details(title)
                if book:
                    with col:
                        img_url = book.get('image_url', '')
                        if img_url:
                            try:
                                st.image(img_url, use_container_width=True)
                            except Exception:
                                st.markdown('<div style="text-align: center; font-size: 2rem;">📖</div>', unsafe_allow_html=True)
                        else:
                            # Placeholder if no image
                            st.markdown(f"""
                            <div style="background-color: #f0f2f6; height: 200px; display: flex; align-items: center; justify-content: center; border-radius: 10px;">
                                <span style="font-size: 48px;">📖</span>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # Escape output to prevent XSS
                        safe_title = html.escape(title[:38])
                        safe_author = html.escape(str(book.get('author', 'Unknown Author'))[:30])
                        book_rating = book.get('avg_rating', 'N/A')

                        st.markdown(f"""
                        <div class="rec-card-text">
                            <div class="rec-title" style="font-weight: bold; margin-top: 10px;">{safe_title}…</div>
                            <div class="rec-author" style="color: #666; font-size: 0.8rem; margin: 5px 0;">by {safe_author}</div>
                            <div class="rec-rating">⭐ {book_rating} / 10</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("View", key=f"view_{row_start}_{j}", use_container_width=True):
                                st.session_state.current_book = title
                                st.session_state.page = "Home"
                                st.session_state.get_recs = True
                                st.rerun()
                        with col2:
                            if st.button("🗑️", key=f"remove_{row_start}_{j}", use_container_width=True):
                                if check_rate_limit():
                                    with st.spinner("🗑️ Removing..."):
                                        success, message = db.remove_like(st.session_state.username, title)
                                        if success:
                                            st.success(message)
                                            time.sleep(0.5)
                                            st.rerun()
                                        else:
                                            st.error(message)
    else:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-icon">📭</div>
            <div class="empty-text">
                <h3>No liked books yet!</h3>
                <p>Go to Home and click the ❤️ button on books you enjoy.</p>
                <p>They will appear here once you save them.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("📚 Browse Books", use_container_width=False, key="browse_btn"):
            st.session_state.page = "Home"
            st.rerun()

# ========== DISLIKED BOOKS PAGE ==========
def disliked_books_page():
    """Render disliked books page"""
    st.markdown('<h1 class="page-title">👎 Your Disliked Books</h1>', unsafe_allow_html=True)

    # Load disliked books - always fresh from database
    disliked_books = db.load_disliked_books(st.session_state.username)

    # Back to Home button (full width, prominent)
    col_btn, _ = st.columns([1, 4])
    with col_btn:
        if st.button("🏠 Back to Home", use_container_width=True, type="primary"):
            st.session_state.page = "Home"
            st.rerun()

    st.markdown("---")

    if disliked_books:
        st.markdown(f'<p class="page-sub" style="text-align: center;">You have <strong>{len(disliked_books)}</strong> book{"s" if len(disliked_books) > 1 else ""} you do not like</p>', unsafe_allow_html=True)

        # Display books in a grid
        for row_start in range(0, len(disliked_books), 4):
            cols = st.columns(4, gap="small")
            for j, col in enumerate(cols):
                idx = row_start + j
                if idx >= len(disliked_books):
                    break
                title = disliked_books[idx]
                book = get_book_details(title)
                if book:
                    with col:
                        img_url = book.get('image_url', '')
                        if img_url:
                            try:
                                st.image(img_url, use_container_width=True)
                            except Exception:
                                st.markdown('<div style="text-align: center; font-size: 2rem;">📖</div>', unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div style="background-color: #f0f2f6; height: 200px; display: flex; align-items: center; justify-content: center; border-radius: 10px;">
                                <span style="font-size: 48px;">📖</span>
                            </div>
                            """, unsafe_allow_html=True)

                        # Escape output to prevent XSS
                        safe_title = html.escape(title[:38])
                        safe_author = html.escape(str(book.get('author', 'Unknown Author'))[:30])
                        book_rating = book.get('avg_rating', 'N/A')

                        st.markdown(f"""
                        <div class="rec-card-text">
                            <div class="rec-title" style="font-weight: bold; margin-top: 10px;">{safe_title}…</div>
                            <div class="rec-author" style="color: #666; font-size: 0.8rem; margin: 5px 0;">by {safe_author}</div>
                            <div class="rec-rating">⭐ {book_rating} / 10</div>
                        </div>
                        """, unsafe_allow_html=True)

                        if st.button("🗑️ Remove", key=f"remove_dislike_{row_start}_{j}", use_container_width=True):
                            if check_rate_limit():
                                with st.spinner("🗑️ Removing..."):
                                    success, message = db.remove_dislike(st.session_state.username, title)
                                    if success:
                                        st.success(message)
                                        time.sleep(0.5)
                                        st.rerun()
                                    else:
                                        st.error(message)
    else:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-icon">😊</div>
            <div class="empty-text">
                <h3>No disliked books!</h3>
                <p>Books you mark as "Not for Me" will appear here.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("📚 Browse Books", use_container_width=False, key="browse_dislike_btn"):
            st.session_state.page = "Home"
            st.rerun()

# ========== MAIN ==========
def main():
    """Main application entry point"""
    # Load CSS and background
    load_css()
    set_background()
    
    # Run diagnostic check
    check_setup()
    
    # Initialize session state
    init_session_state()
    
    # Render sidebar
    render_sidebar()
    
    # Main content routing
    if not st.session_state.authenticated:
        landing_page()
    else:
        if st.session_state.page == "Home":
            home_page()
        elif st.session_state.page == "Liked Books":
            liked_books_page()
        elif st.session_state.page == "Disliked Books":
            disliked_books_page()

if __name__ == "__main__":
    main()