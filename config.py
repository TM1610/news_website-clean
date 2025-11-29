import os

# Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',           # Change to your MySQL username
    'password': '',           # Change to your MySQL password
    'database': 'news_db'
}

# Flask Configuration
SECRET_KEY = os.urandom(24)  # For session management
DEBUG = True

# Pagination
HEADLINES_PER_PAGE = 12