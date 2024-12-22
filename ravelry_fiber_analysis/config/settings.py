import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
LOG_DIR = BASE_DIR / "logs"

# Create necessary directories
DATA_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# Ravelry API credentials
RAVELRY_CLIENT_KEY = os.getenv('RAVELRY_CLIENT_KEY', 'default_client_key')
RAVELRY_CLIENT_SECRET = os.getenv('RAVELRY_CLIENT_SECRET', 'default_client_secret')
RAVELRY_OAUTH_TOKEN = os.getenv('RAVELRY_OAUTH_TOKEN', 'default_oauth_token')
RAVELRY_OAUTH_SECRET = os.getenv('RAVELRY_OAUTH_SECRET', 'default_oauth_secret')

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
        'simple': {
            'format': '%(levelname)s - %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'level': 'INFO',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'ravelry.log',
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
            'level': 'DEBUG',
        },
    },
    'loggers': {
        'ravelry_fiber_analysis': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}