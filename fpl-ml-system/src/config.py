"""Configuration management for FPL AI Optimizer."""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration class."""
    
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 'yes')
    
    # Database configuration
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///fpl.db')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # FPL API configuration
    FPL_API_BASE_URL = os.environ.get('FPL_API_BASE_URL', 'https://fantasy.premierleague.com/api/')
    FPL_CACHE_TIMEOUT = int(os.environ.get('FPL_CACHE_TIMEOUT', '3600'))
    
    # Cache configuration
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'simple')
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_DEFAULT_TIMEOUT', '300'))
    
    # ML Model configuration
    XGBOOST_MODEL_PATH = os.environ.get('XGBOOST_MODEL_PATH', 'models/xgboost_player_predictions.json')
    MODEL_RETRAIN_INTERVAL = int(os.environ.get('MODEL_RETRAIN_INTERVAL', '604800'))  # 1 week
    
    # Logging configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/app.log')
    
    # Optimization constraints
    TEAM_BUDGET = 100.0  # £100M total budget
    FORMATION_CONSTRAINTS = {
        'GKP': 2,  # Goalkeepers
        'DEF': 5,  # Defenders  
        'MID': 5,  # Midfielders
        'FWD': 3   # Forwards
    }
    MAX_PLAYERS_PER_TEAM = 3
    
    # API rate limiting
    API_RATE_LIMIT = '100/hour'
    API_TIMEOUT = 30  # seconds


class DevelopmentConfig(Config):
    """Development configuration."""
    
    DEBUG = True
    SQLALCHEMY_ECHO = True  # Log SQL queries
    
    # Use in-memory cache for development
    CACHE_TYPE = 'simple'


class TestingConfig(Config):
    """Testing configuration."""
    
    TESTING = True
    DEBUG = True
    
    # Use in-memory database for testing
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False
    
    # Use null cache for testing
    CACHE_TYPE = 'null'
    
    # Shorter timeouts for testing
    FPL_CACHE_TIMEOUT = 1
    API_TIMEOUT = 5


class ProductionConfig(Config):
    """Production configuration."""
    
    DEBUG = False
    
    # Use Redis for production caching if available
    REDIS_URL = os.environ.get('REDIS_URL')
    if REDIS_URL:
        CACHE_TYPE = 'redis'
        CACHE_REDIS_URL = REDIS_URL
    
    # Enhanced security for production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config(config_name: Optional[str] = None) -> Config:
    """Get configuration class based on environment."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    return config.get(config_name, config['default'])