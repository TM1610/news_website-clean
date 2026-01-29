import os

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT", "5432"),
}

SECRET_KEY = os.getenv("SECRET_KEY", "dev-key")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

HEADLINES_PER_PAGE = 12
