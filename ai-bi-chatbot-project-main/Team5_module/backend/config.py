import os
from datetime import timedelta
from dotenv import load_dotenv

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load backend-local environment variables if present.
load_dotenv(os.path.join(BASE_DIR, '.env'))


def _parse_csv_env(var_name, default):
    raw = os.getenv(var_name, default)
    return [item.strip() for item in raw.split(',') if item.strip()]

class Config:
    """Base configuration"""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
    DEBUG = False
    
    # Database/Sessions
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # File Upload
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    ALLOWED_EXTENSIONS = {'csv'}
    
    # Models
    MODELS_PATH = os.path.join(BASE_DIR, '..', 'models')
    COLUMN_MAPPER_CONFIDENCE_THRESHOLD = float(os.getenv('COLUMN_MAPPER_CONFIDENCE_THRESHOLD', '0.55'))
    
    # API Keys
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

    # CORS/auth behavior for browser-based frontend integrations.
    CORS_ALLOWED_ORIGINS = _parse_csv_env(
        'CORS_ALLOWED_ORIGINS',
        'http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001,http://localhost:3002,http://127.0.0.1:3002,http://localhost:5173,http://127.0.0.1:5173'
    )
    CORS_SUPPORTS_CREDENTIALS = os.getenv('CORS_SUPPORTS_CREDENTIALS', 'true').lower() == 'true'
    ALLOW_DEMO_USER_FALLBACK = os.getenv('ALLOW_DEMO_USER_FALLBACK', 'false').lower() == 'true'

    # Artifact cleanup policy (internship-friendly defaults)
    CLEANUP_ENABLED = os.getenv('CLEANUP_ENABLED', 'true').lower() == 'true'
    CLEANUP_MAX_AGE_HOURS = int(os.getenv('CLEANUP_MAX_AGE_HOURS', '48'))
    CLEANUP_INTERVAL_MINUTES = int(os.getenv('CLEANUP_INTERVAL_MINUTES', '60'))
    
    # Paths to imported modules
    ANALYTICS_ENGINE_PATH = os.path.join(BASE_DIR, '..', '..', 'analytics_engine')
    TEAM2_MODULE_PATH = os.path.join(BASE_DIR, '..', '..', 'Team2_module')


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True


# Config dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
