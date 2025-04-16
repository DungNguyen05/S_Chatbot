"""
Configuration module for integrated Crypto News Crawler and RAG system.
Loads settings from environment variables with fallback to default values.
"""
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from distutils.util import strtobool

# Load environment variables from .env file
load_dotenv()

# Helper functions for parsing environment variables
def _parse_bool(value: Optional[str]) -> bool:
    """Parse string to boolean."""
    if value is None:
        return False
    return strtobool(value.lower()) > 0

def _parse_int(value: Optional[str], default: int) -> int:
    """Parse string to integer with default."""
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default

def _parse_float(value: Optional[str], default: float) -> float:
    """Parse string to float with default."""
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default

# Base directories
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data"))).resolve()

# Ensure directories exist
for directory in [TEMPLATES_DIR, STATIC_DIR, DATA_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Documents storage file
DOCUMENTS_FILE = DATA_DIR / "documents.json"

# Database Configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "news_crawler")
}

# API Keys for external services
API_KEY_COINMARKETCAP = os.getenv("API_KEY_COINMARKETCAP", "")
API_KEY_CRYPTOPANIC = os.getenv("API_KEY_CRYPTOPANIC", "")
API_KEY_DIFFBOT = os.getenv("API_KEY_DIFFBOT", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Crawler Configuration
COIN_NUMBER = _parse_int(os.getenv("COIN_NUMBER"), 1000)  # Number of coins to fetch
ARTICLE_EN = _parse_int(os.getenv("ARTICLE_EN"), 50)      # Number of English articles
ARTICLE_VI = _parse_int(os.getenv("ARTICLE_VI"), 200)     # Number of Vietnamese articles
RESET_DATABASE = _parse_bool(os.getenv("RESET_DATABASE"))  # Reset database
CRAWL_INTERVAL_MINUTES = _parse_int(os.getenv("CRAWL_INTERVAL_MINUTES"), 15)  # Crawl interval

# Crawler Timing Configuration
DELAY = _parse_int(os.getenv("DELAY"), 5)                       # Default delay between requests
RETRY = _parse_int(os.getenv("RETRY"), 3)                       # Default retry count
PAGE_LOAD_TIMEOUT = _parse_int(os.getenv("PAGE_LOAD_TIMEOUT"), 30)  # Default page load timeout

# RAG Configuration
# Default to all-MiniLM-L6-v2 which is fast and good quality
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-3.5-turbo")
MAX_SEARCH_RESULTS = _parse_int(os.getenv("MAX_SEARCH_RESULTS"), 5)
MAX_TOKENS_RESPONSE = _parse_int(os.getenv("MAX_TOKENS_RESPONSE"), 500)
TEMPERATURE = _parse_float(os.getenv("TEMPERATURE"), 0.3)
MAX_CONTEXT_LENGTH = _parse_int(os.getenv("MAX_CONTEXT_LENGTH"), 4000)

# Text chunking settings for document processing
CHUNK_SIZE = _parse_int(os.getenv("CHUNK_SIZE"), 1000)
CHUNK_OVERLAP = _parse_int(os.getenv("CHUNK_OVERLAP"), 200)

# Query transformation settings
USE_QUERY_EXPANSION = _parse_bool(os.getenv("USE_QUERY_EXPANSION", "true"))
USE_RERANKING = _parse_bool(os.getenv("USE_RERANKING", "true"))

# HuggingFace Tokenizers settings
TOKENIZERS_PARALLELISM = _parse_bool(os.getenv("TOKENIZERS_PARALLELISM", "false"))
# Already set at the top: os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Server Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = _parse_int(os.getenv("PORT"), 8000)
RELOAD = _parse_bool(os.getenv("RELOAD"))
DEBUG = _parse_bool(os.getenv("DEBUG"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)