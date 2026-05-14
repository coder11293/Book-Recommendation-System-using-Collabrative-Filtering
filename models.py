# models.py
# ========== ML MODEL AND RECOMMENDATION FUNCTIONS ==========

import logging
import os

import numpy as np
import pandas as pd
import pickle
import streamlit as st
from config import MODEL_PATH, BOOK_PIVOT_PATH, BOOK_NAMES_PATH, BOOK_DETAILS_PATH, N_NEIGHBORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@st.cache_resource(ttl=3600)  # Cache for 1 hour
def load_model():
    """Load the recommendation model and data with caching"""
    try:
        if not os.path.exists(MODEL_PATH):
            logger.error(f"Model file not found at {MODEL_PATH}")
            return None, None, None, None

        if not os.path.exists(BOOK_PIVOT_PATH):
            logger.error(f"Book pivot file not found at {BOOK_PIVOT_PATH}")
            return None, None, None, None

        model = pickle.load(open(MODEL_PATH, 'rb'))
        book_pivot = pickle.load(open(BOOK_PIVOT_PATH, 'rb'))
        book_names = pickle.load(open(BOOK_NAMES_PATH, 'rb'))
        book_details = pickle.load(open(BOOK_DETAILS_PATH, 'rb'))

        logger.info(f"Model loaded successfully - {len(book_names)} books")
        return model, book_pivot, book_names, book_details
    except FileNotFoundError as e:
        logger.error(f"Model file not found: {e}")
        return None, None, None, None
    except Exception as e:
        logger.error(f"Error loading model files: {str(e)}")
        return None, None, None, None

# Load models with error handling
model, book_pivot, book_names, book_details = load_model()

def is_model_loaded():
    """Check if model is properly loaded"""
    if model is None or book_pivot is None:
        return False
    return True

def get_model_state():
    """Get model and related data safely"""
    if not is_model_loaded():
        return None, None, None, None
    return model, book_pivot, book_names, book_details

def get_recommendations(book_title, n_recommendations=None):
    """Get book recommendations using KNN algorithm

    Args:
        book_title: The book to get recommendations for
        n_recommendations: Number of recommendations to return (default: N_NEIGHBORS-1)
    """
    if not is_model_loaded():
        logger.warning("Model not loaded, cannot get recommendations")
        return []

    if n_recommendations is None:
        n_recommendations = N_NEIGHBORS - 1

    try:
        if book_title not in book_pivot.index:
            logger.warning(f"Book '{book_title}' not found in pivot table")
            return []
        idx = np.where(book_pivot.index == book_title)[0][0]
        # Request more than needed to account for filtering
        distances, suggestions = model.kneighbors(
            book_pivot.iloc[idx, :].values.reshape(1, -1),
            n_neighbors=n_recommendations + 10  # Get extra in case some are filtered
        )
        recommendations = [book_pivot.index[i] for i in suggestions[0][1:]]
        logger.info(f"Generated {len(recommendations)} recommendations for '{book_title}'")
        return recommendations
    except Exception as e:
        logger.error(f"Recommendation error: {e}")
        return []

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_book_details(title):
    """Get detailed information about a book with caching"""
    if book_details is None:
        return None

    try:
        match = book_details[book_details['title'] == title]
        if not match.empty:
            return match.iloc[0].to_dict()
    except Exception as e:
        logger.warning(f"Error getting book details for '{title}': {e}")
    return None

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_all_book_names():
    """Return list of all book names with caching"""
    if book_names is None:
        return []
    return book_names

def get_book_pivot():
    """Return book pivot table"""
    return book_pivot