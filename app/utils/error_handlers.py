from flask import jsonify
import logging

logger = logging.getLogger(__name__)

def register_error_handlers(app):
    """Register error handlers for the Flask app"""
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "status": "error",
            "message": "Endpoint not found"
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            "status": "error",
            "message": "Method not allowed"
        }), 405
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            "status": "error",
            "message": "Bad request"
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            "status": "error",
            "message": "Unauthorized"
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            "status": "error",
            "message": "Forbidden"
        }), 403
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        logger.error(f"Unhandled exception: {e}")
        return jsonify({
            "status": "error",
            "message": "An unexpected error occurred"
        }), 500

class WebhookError(Exception):
    """Custom exception for webhook errors"""
    def __init__(self, message, status_code=400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class ValidationError(Exception):
    """Custom exception for validation errors"""
    def __init__(self, message, field=None):
        self.message = message
        self.field = field
        super().__init__(self.message)

class ServiceError(Exception):
    """Custom exception for service errors"""
    def __init__(self, service_name, message):
        self.service_name = service_name
        self.message = f"{service_name} error: {message}"
        super().__init__(self.message)

def register_multitenant_error_handlers(app):
    """Register enhanced error handlers with multi-tenant context"""
    
    # Call original error handlers first
    register_error_handlers(app)
    
    @app.errorhandler(400)
    def enhanced_bad_request(error):
        from app.utils.helpers import extract_company_from_request
        
        try:
            company_id = extract_company_from_request()
        except:
            company_id = None
        
        response = {
            "status": "error",
            "message": "Bad request",
            "timestamp": time.time()
        }
        
        if company_id:
            response["company_id"] = company_id
        
        return jsonify(response), 400
    
    @app.errorhandler(500)
    def enhanced_internal_error(error):
        from app.utils.helpers import extract_company_from_request
        
        try:
            company_id = extract_company_from_request()
            app.logger.error(f"[{company_id}] Internal server error: {error}")
        except:
            company_id = None
            app.logger.error(f"Internal server error: {error}")
        
        response = {
            "status": "error",
            "message": "Internal server error",
            "timestamp": time.time()
        }
        
        if company_id:
            response["company_id"] = company_id
        
        return jsonify(response), 500
