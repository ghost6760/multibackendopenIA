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
