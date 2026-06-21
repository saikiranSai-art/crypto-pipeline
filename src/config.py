import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Setup base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SQL_DIR = BASE_DIR / "sql"

# Create directories if they do not exist
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Database Configuration
DB_TYPE = os.getenv("DB_TYPE", "mysql")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "3306" if DB_TYPE == "mysql" else "5432")
DB_NAME = os.getenv("DB_NAME", "crypto_bi_db")
DB_USER = os.getenv("DB_USER", "root" if DB_TYPE == "mysql" else "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Construct SQLAlchemy database URI
if DB_TYPE == "mysql":
    DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# CoinGecko API Configuration
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "")
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(BASE_DIR / "pipeline.log", encoding="utf-8")
    ]
)

logger = logging.getLogger("crypto_bi_pipeline")

def get_db_uri():
    """
    Returns the database connection string.
    """
    if not DB_PASSWORD:
        logger.warning("DB_PASSWORD is not set in environment variables.")
    return DATABASE_URI
