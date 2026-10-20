import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    APP_NAME: str = "Kaveri Stays API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() in ("true", "1", "yes")
    
    SECRET_KEY: str = os.getenv("SECRET_KEY", "kaveri-default-dev-secret-key-change-in-production")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:yourpass@localhost/kaveri")
    
    # Rate limiting
    RATE_LIMIT_DEFAULT: str = os.getenv("RATE_LIMIT_DEFAULT", "100/minute")
    
    # Database pool settings
    DB_MIN_CONN: int = int(os.getenv("DB_MIN_CONN", "1"))
    DB_MAX_CONN: int = int(os.getenv("DB_MAX_CONN", "10"))

settings = Settings()