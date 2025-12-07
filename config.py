import os

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("root"),
    "password": os.getenv(""),
    "database": os.getenv("news07"),
}

SECRET_KEY = os.getenv("SECRET_KEY", "default-secret")
DEBUG = False
HEADLINES_PER_PAGE = 12
