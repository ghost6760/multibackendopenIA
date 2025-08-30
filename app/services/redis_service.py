
import redis
from flask import current_app, g
import logging

logger = logging.getLogger(__name__)

def get_redis_client():
    """Get Redis client from Flask g object or create new one"""
    if 'redis_client' not in g:
        g.redis_client = redis.from_url(
            current_app.config['REDIS_URL'], 
            decode_responses=True
        )
    return g.redis_client

def init_redis(app):
    """Initialize Redis connection"""
    try:
        client = redis.from_url(app.config['REDIS_URL'], decode_responses=True)
        client.ping()
        logger.info("✅ Redis connection successful")
        return client
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        raise

def close_redis(e=None):
    """Close Redis connection"""
    client = g.pop('redis_client', None)
    if client is not None:
        client.close()

def get_company_redis_key(company_id: str, key_type: str, identifier: str = "") -> str:
    """Generate company-specific Redis key"""
    from app.config.company_config import get_company_config
    from app.config.constants import REDIS_KEY_PATTERNS
    
    config = get_company_config(company_id)
    if config:
        prefix = config.redis_prefix
    else:
        prefix = f"{company_id}:"
    
    pattern = REDIS_KEY_PATTERNS.get(key_type, "{company_prefix}{key_type}:")
    base_key = pattern.format(company_prefix=prefix, company_id=company_id, key_type=key_type)
    
    if identifier:
        return f"{base_key}{identifier}"
    return base_key
