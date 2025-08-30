from functools import wraps
from flask import jsonify
import logging

logger = logging.getLogger(__name__)

def handle_errors(f):
    """Decorator for consistent error handling"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            return jsonify({"status": "error", "message": str(e)}), 400
        except Exception as e:
            logger.exception(f"Unhandled error in {f.__name__}")
            return jsonify({"status": "error", "message": "Internal server error"}), 500
    return decorated_function

def require_api_key(f):
    """Decorator to require API key"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request, current_app
        
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != current_app.config.get('API_KEY'):
            return jsonify({"status": "error", "message": "Invalid API key"}), 401
        
        return f(*args, **kwargs)
    return decorated_function

def cache_result(timeout=300):
    """Decorator for caching results in Redis"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from app.services.redis_service import get_redis_client
            import json
            
            # Create cache key
            cache_key = f"cache:{f.__name__}:{str(args)}:{str(kwargs)}"
            redis_client = get_redis_client()
            
            # Check cache
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Get fresh result
            result = f(*args, **kwargs)
            
            # Cache result
            redis_client.setex(cache_key, timeout, json.dumps(result))
            
            return result
        return decorated_function


  def require_company_context(f):
    """Decorator to ensure company context is present and valid"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request
        from app.config.company_config import get_company_manager
        
        # Extract company_id from request
        company_id = (request.headers.get('X-Company-ID') or 
                     request.args.get('company_id') or 
                     (request.get_json().get('company_id') if request.is_json else None))
        
        if not company_id:
            return jsonify({
                "status": "error", 
                "message": "Company ID is required"
            }), 400
        
        # Validate company
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return jsonify({
                "status": "error", 
                "message": f"Invalid company ID: {company_id}"
            }), 400
        
        # Add company_id to kwargs for the handler
        kwargs['company_id'] = company_id
        
        return f(*args, **kwargs)
    
    return decorated_function
    return decorator
