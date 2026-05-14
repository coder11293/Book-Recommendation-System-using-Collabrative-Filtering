# config.py
# ========== CONFIGURATION SETTINGS ==========

import os

# App Configuration
APP_TITLE = "Book Recommendation System"
APP_LAYOUT = "wide"
PAGE_ICON = "📖"
BACKGROUND_IMAGE = "12.webp"
CSS_FILE = "style.css"

# Model Paths
MODEL_PATH = "artifacts/model.pkl"
BOOK_PIVOT_PATH = "artifacts/book_pivot.pkl"
BOOK_NAMES_PATH = "artifacts/book_names.pkl"
BOOK_DETAILS_PATH = "artifacts/book_details.pkl"

# Recommendation Settings
N_NEIGHBORS = 11  # Gets 10 recommendations (excluding input book)
DISPLAY_COLUMNS = 5  # Number of columns in recommendation grid
LIKED_BOOKS_COLUMNS = 4  # Number of columns for liked books display

