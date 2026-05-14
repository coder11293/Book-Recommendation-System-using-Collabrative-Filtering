# database.py
# ========== CSV FILE-BASED STORAGE ==========

import csv
import logging
import os
import re
from datetime import datetime
from pathlib import Path

import bcrypt
import streamlit as st

# Data directory
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

USERS_FILE = DATA_DIR / "users.csv"
LIKES_FILE = DATA_DIR / "likes.csv"
DISLIKES_FILE = DATA_DIR / "dislikes.csv"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _ensure_csv_file(filepath, headers):
    """Ensure CSV file exists with headers"""
    if not filepath.exists():
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)


def _read_csv(filepath):
    """Read CSV file and return list of rows"""
    if not filepath.exists():
        return []
    with open(filepath, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


def _write_csv(filepath, headers, rows):
    """Write rows to CSV file"""
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


class Database:
    def __init__(self):
        self._initialized = False
        self._initialize()

    def _initialize(self):
        """Initialize CSV files"""
        try:
            _ensure_csv_file(USERS_FILE, ['username', 'password', 'created_at', 'last_login'])
            _ensure_csv_file(LIKES_FILE, ['username', 'book_title', 'liked_at'])
            _ensure_csv_file(DISLIKES_FILE, ['username', 'book_title', 'disliked_at'])
            self._initialized = True
            logger.info("CSV database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize CSV database: {e}")
            self._initialized = False

    def is_connected(self):
        """Check if CSV storage is available"""
        return self._initialized and DATA_DIR.exists()

    def get_engine(self):
        """For compatibility - returns None"""
        return None

    def hash_password(self, password):
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode('utf-8')

    def verify_password(self, password, hashed):
        """Verify password against bcrypt hash"""
        return bcrypt.checkpw(password.encode(), hashed.encode('utf-8'))

    def is_password_strong(self, password):
        """Check password strength"""
        if len(password) < 8:
            return False, "Password must be at least 8 characters"
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        if not re.search(r'\d', password):
            return False, "Password must contain at least one number"
        return True, "Strong password"

    def save_user(self, username, password):
        """Save new user to CSV"""
        if not self.is_connected():
            return False, "Storage error. Please try again later."

        if not username or not password:
            return False, "Username and password are required"

        if len(username) < 3:
            return False, "Username must be at least 3 characters"

        is_strong, msg = self.is_password_strong(password)
        if not is_strong:
            return False, msg

        try:
            users = _read_csv(USERS_FILE)
            # Check if user exists
            for user in users:
                if user['username'] == username:
                    return False, "Username already exists. Please choose another."

            # Add new user
            users.append({
                'username': username,
                'password': self.hash_password(password),
                'created_at': datetime.now().isoformat(),
                'last_login': ''
            })
            _write_csv(USERS_FILE, ['username', 'password', 'created_at', 'last_login'], users)
            return True, "User created successfully"
        except Exception as e:
            logger.error(f"Error saving user: {e}")
            return False, f"Storage error: {str(e)}"

    def authenticate(self, username, password):
        """Authenticate user login"""
        if not self.is_connected():
            logger.error("Storage error during authentication")
            st.error("Storage error")
            return False

        if not username or not password:
            return False

        try:
            users = _read_csv(USERS_FILE)
            for user in users:
                if user['username'] == username:
                    if self.verify_password(password, user['password']):
                        logger.info(f"User '{username}' authenticated successfully")
                        # Update last login
                        try:
                            for u in users:
                                if u['username'] == username:
                                    u['last_login'] = datetime.now().isoformat()
                            _write_csv(USERS_FILE, ['username', 'password', 'created_at', 'last_login'], users)
                        except Exception as e:
                            logger.warning(f"Could not update last_login: {e}")
                        return True
            logger.warning(f"Failed login attempt for user '{username}'")
            return False
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False

    def save_like(self, username, book_title):
        """Save liked book to CSV"""
        if not self.is_connected():
            return False, "Storage error"

        try:
            likes = _read_csv(LIKES_FILE)
            # Check if already liked
            for like in likes:
                if like['username'] == username and like['book_title'] == book_title:
                    return False, "Book already in your liked list"

            # Add like
            likes.append({
                'username': username,
                'book_title': book_title,
                'liked_at': datetime.now().isoformat()
            })
            _write_csv(LIKES_FILE, ['username', 'book_title', 'liked_at'], likes)
            return True, "Book added to your liked list! ❤️"
        except Exception as e:
            return False, f"Error: {str(e)}"

    def remove_like(self, username, book_title):
        """Remove book from liked list"""
        if not self.is_connected():
            return False, "Storage error"

        try:
            likes = _read_csv(LIKES_FILE)
            original_count = len(likes)
            likes = [l for l in likes if not (l['username'] == username and l['book_title'] == book_title)]

            if len(likes) < original_count:
                _write_csv(LIKES_FILE, ['username', 'book_title', 'liked_at'], likes)
                return True, f"Removed '{book_title[:50]}' from liked books"
            else:
                return False, "Book not found in liked list"
        except Exception as e:
            return False, f"Error: {str(e)}"

    def load_liked_books(self, username):
        """Get all liked books for a user"""
        if not self.is_connected():
            return []

        try:
            likes = _read_csv(LIKES_FILE)
            user_likes = [l['book_title'] for l in likes if l['username'] == username]
            return user_likes
        except Exception as e:
            logger.error(f"Error loading liked books: {e}")
            return []

    def save_dislike(self, username, book_title):
        """Save disliked book to CSV"""
        if not self.is_connected():
            return False, "Storage error"

        try:
            dislikes = _read_csv(DISLIKES_FILE)
            # Check if already disliked
            for dislike in dislikes:
                if dislike['username'] == username and dislike['book_title'] == book_title:
                    return False, "Book already in your disliked list"

            # Check if it's in liked (and remove if so)
            likes = _read_csv(LIKES_FILE)
            likes = [l for l in likes if not (l['username'] == username and l['book_title'] == book_title)]
            _write_csv(LIKES_FILE, ['username', 'book_title', 'liked_at'], likes)

            # Add dislike
            dislikes.append({
                'username': username,
                'book_title': book_title,
                'disliked_at': datetime.now().isoformat()
            })
            _write_csv(DISLIKES_FILE, ['username', 'book_title', 'disliked_at'], dislikes)
            return True, "Book added to disliked list! 👎"
        except Exception as e:
            return False, f"Error: {str(e)}"

    def remove_dislike(self, username, book_title):
        """Remove book from disliked list"""
        if not self.is_connected():
            return False, "Storage error"

        try:
            dislikes = _read_csv(DISLIKES_FILE)
            original_count = len(dislikes)
            dislikes = [d for d in dislikes if not (d['username'] == username and d['book_title'] == book_title)]

            if len(dislikes) < original_count:
                _write_csv(DISLIKES_FILE, ['username', 'book_title', 'disliked_at'], dislikes)
                return True, f"Removed '{book_title[:50]}' from disliked books"
            else:
                return False, "Book not in disliked list"
        except Exception as e:
            return False, f"Error: {str(e)}"

    def load_disliked_books(self, username):
        """Get all disliked books for a user"""
        if not self.is_connected():
            return []

        try:
            dislikes = _read_csv(DISLIKES_FILE)
            user_dislikes = [d['book_title'] for d in dislikes if d['username'] == username]
            return user_dislikes
        except Exception as e:
            logger.error(f"Error loading disliked books: {e}")
            return []


# Create global database instance with Streamlit caching
@st.cache_resource
def get_database():
    """Get cached database instance"""
    return Database()


# Use this instead of direct instantiation
db = get_database()