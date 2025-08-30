import os
from typing import Dict, Any

class Config:
    """Base configuration class"""
    
    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = False
    TESTING = False
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    MODEL_NAME = os.getenv('MODEL_NAME', 'gpt-4o-mini')
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small')
    MAX_TOKENS = int(os.getenv('MAX_TOKENS', '1500'))
    TEMPERATURE = float(os.getenv('TEMPERATURE', '0.7'))
    
    # Redis Configuration
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    # Chatwoot Configuration
    CHATWOOT_API_KEY = os.getenv('CHATWOOT_API_KEY')
    CHATWOOT_BASE_URL = os.getenv('CHATWOOT_BASE_URL')
    ACCOUNT_ID = os.getenv('ACCOUNT_ID', '7')
    
    # Application Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    MAX_CONTEXT_MESSAGES = int(os.getenv('MAX_CONTEXT_MESSAGES', '10'))
    SIMILARITY_THRESHOLD = float(os.getenv('SIMILARITY_THRESHOLD', '0.7'))
    MAX_RETRIEVED_DOCS = int(os.getenv('MAX_RETRIEVED_DOCS', '3'))
    
    # Feature Flags
    VOICE_ENABLED = os.getenv('VOICE_ENABLED', 'false').lower() == 'true'
    IMAGE_ENABLED = os.getenv('IMAGE_ENABLED', 'false').lower() == 'true'
    WEBHOOK_DEBUG = os.getenv('WEBHOOK_DEBUG', 'false').lower() == 'true'
    
    # Schedule Service
    SCHEDULE_SERVICE_URL = os.getenv('SCHEDULE_SERVICE_URL', 'http://127.0.0.1:4040')
    
    # Security
    API_KEY = os.getenv('API_KEY')
    
    # Auto-recovery
    VECTORSTORE_AUTO_RECOVERY = os.getenv('VECTORSTORE_AUTO_RECOVERY', 'true').lower() == 'true'
    VECTORSTORE_HEALTH_CHECK_INTERVAL = int(os.getenv('VECTORSTORE_HEALTH_CHECK_INTERVAL', '30'))
    VECTORSTORE_RECOVERY_TIMEOUT = int(os.getenv('VECTORSTORE_RECOVERY_TIMEOUT', '60'))
    
    # Multi-tenant Configuration
    COMPANIES_CONFIG_FILE = os.getenv('COMPANIES_CONFIG_FILE', 'companies_config.json')
    DEFAULT_COMPANY_ID = os.getenv('DEFAULT_COMPANY_ID', 'benova')
    
    # Additional OpenAI models
    TTS_MODEL = os.getenv('TTS_MODEL', 'tts-1')
    TTS_VOICE = os.getenv('TTS_VOICE', 'alloy')
    WHISPER_MODEL = os.getenv('WHISPER_MODEL', 'whisper-1')
    VISION_MODEL = os.getenv('VISION_MODEL', 'gpt-4o-mini')

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    
class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    REDIS_URL = 'redis://localhost:6379/1'  # Different DB for testing

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config() -> Config:
    """Get configuration based on environment"""
    env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])
