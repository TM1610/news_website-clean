"""Example configuration (safe to commit).
Copy this to `config.py` and fill in real values locally.
"""

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'your_db_password',
    'database': 'news_db'
}

# Flask Configuration
# Replace with a secure random string in production
SECRET_KEY = 'change-me-to-a-secure-random-value'
DEBUG = True

# Pagination
HEADLINES_PER_PAGE = 12
