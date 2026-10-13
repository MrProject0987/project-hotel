import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# Load .env file
load_dotenv(BASE_DIR / ".env")

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "grandstay-luxury-secret-default-key")
    DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "grandstay.db"))
    
    # Session security settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours in seconds
    
    # App Settings
    HOTEL_NAME = "GrandStay Hotel & Residences"
    HOTEL_PHONE = "+1 (800) 555-GRAND"
    HOTEL_EMAIL = "concierge@grandstayhotel.com"
    HOTEL_ADDRESS = "742 Evergreen Promenade, Palm Crest Bay, CA 90210"
    
    # Currency
    CURRENCY_SYMBOL = "$"
    TAX_RATE = 0.12  # 12% luxury hotel occupancy tax & service fee
