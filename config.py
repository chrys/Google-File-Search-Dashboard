"""
Application configuration management for different environments
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration - shared across all environments"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = False
    TESTING = False
    
    # Application settings
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20MB max file size
    JSON_SORT_KEYS = False
    JSONIFY_PRETTYPRINT_REGULAR = False


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    ENV = 'development'
    
    # Allow all CORS origins in development
    CORS_ORIGINS = "*"


class ProductionConfig(Config):
    """Production configuration - strict security settings"""
    DEBUG = False
    TESTING = False
    ENV = 'production'
    
    # Restrict CORS origins to specific domains
    CORS_ORIGINS = [
        "https://www.fasolaki.com",
        "https://fasolaki.com"
    ]
    
    # Get SECRET_KEY from environment or use default
    # Validation happens at runtime in the app, not at import time
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    @classmethod
    def validate(cls):
        """Validate production configuration at runtime"""
        if not cls.SECRET_KEY or cls.SECRET_KEY == 'dev-secret-key-change-in-production':
            raise ValueError("SECRET_KEY environment variable must be set and changed in production")


class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    ENV = 'testing'
    
    # Allow all CORS origins in testing
    CORS_ORIGINS = "*"


def get_config(env=None):
    """
    Get configuration object based on environment
    
    Args:
        env: Environment name ('development', 'production', 'testing')
             If None, reads from FLASK_ENV environment variable
    
    Returns:
        Configuration class for the specified environment
    """
    if env is None:
        env = os.getenv('FLASK_ENV', 'development')
    
    env = env.lower()
    
    configs = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig
    }
    
    config_class = configs.get(env, DevelopmentConfig)
    
    print(f"[CONFIG] Loading configuration for environment: {env}")
    
    return config_class
