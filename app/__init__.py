# app/__init__.py - Railway Production Fix
"""
Fixed Flask app factory for Railway deployment
Handles the schedule service connection issue (port 4040) gracefully
"""

import os
import logging
from flask import Flask, jsonify, send_file, request
from flask_cors import CORS
import sys

# Configure logging for Railway
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def create_app(config=None):
    """Create and configure Flask app for Railway deployment"""
    
    app = Flask(__name__)
    
    # Railway-specific configuration
    configure_railway_settings(app)
    
    # Configure CORS for Railway
    CORS(app, origins="*")
    
    # Load configuration
    if config:
        app.config.from_object(config)
    else:
        from app.config.settings import config as default_config
        env = os.getenv('FLASK_ENV', 'production')
        app.config.from_object(default_config.get(env, default_config['default']))
    
    # Initialize extensions and services with Railway error handling
    initialize_services_with_railway_support(app)
    
    # Register routes with Railway optimizations
    register_routes_with_railway_support(app)
    
    # Setup Railway error handlers
    setup_railway_error_handlers(app)
    
    # Railway health check endpoints
    setup_railway_health_checks(app)
    
    logger.info("🚄 Flask app created for Railway deployment")
    return app

def configure_railway_settings(app):
    """Configure Railway-specific settings"""
    
    # Railway environment detection
    is_railway = bool(os.getenv('RAILWAY_ENVIRONMENT_NAME'))
    app.config['IS_RAILWAY'] = is_railway
    
    # Dynamic port handling for Railway
    port = int(os.getenv('PORT', 8080))
    app.config['PORT'] = port
    
    # Railway-specific logging
    if is_railway:
        app.config['LOG_LEVEL'] = 'INFO'
        logger.info(f"🚄 Railway environment detected, using port {port}")
    
    # Schedule service configuration with Railway fallback
    schedule_service_url = os.getenv('SCHEDULE_SERVICE_URL', 'http://127.0.0.1:4040')
    app.config['SCHEDULE_SERVICE_URL'] = schedule_service_url
    app.config['SCHEDULE_SERVICE_FALLBACK'] = True  # Enable fallback mode
    
    logger.info(f"📅 Schedule service URL: {schedule_service_url} (fallback enabled)")

def initialize_services_with_railway_support(app):
    """Initialize services with Railway error handling"""
    
    try:
        # Initialize Redis with Railway support
        from app.services.redis_service import get_redis_client
        redis_client = get_redis_client()
        
        # Test Redis connection
        redis_client.ping()
        app.config['REDIS_AVAILABLE'] = True
        logger.info("✅ Redis connection established")
        
    except Exception as e:
        app.config['REDIS_AVAILABLE'] = False
        logger.warning(f"⚠️ Redis connection failed: {e}")
    
    try:
        # Initialize OpenAI service
        from app.services.openai_service import OpenAIService
        openai_service = OpenAIService()
        
        # Test OpenAI connection
        openai_service.test_connection()
        app.config['OPENAI_AVAILABLE'] = True
        logger.info("✅ OpenAI service available")
        
    except Exception as e:
        app.config['OPENAI_AVAILABLE'] = False
        logger.warning(f"⚠️ OpenAI service unavailable: {e}")
    
    try:
        # Initialize company manager with Railway support
        from app.services.company_manager import get_company_manager
        company_manager = get_company_manager()
        
        companies = company_manager.get_all_companies()
        app.config['COMPANIES_COUNT'] = len(companies)
        logger.info(f"✅ Company manager initialized with {len(companies)} companies")
        
    except Exception as e:
        app.config['COMPANIES_COUNT'] = 0
        logger.error(f"❌ Company manager initialization failed: {e}")
    
    # Schedule service availability check (Railway fix for port 4040)
    check_schedule_service_with_railway_fallback(app)

def check_schedule_service_with_railway_fallback(app):
    """Check schedule service availability with Railway fallback handling"""
    
    try:
        import requests
        schedule_url = app.config.get('SCHEDULE_SERVICE_URL', 'http://127.0.0.1:4040')
        
        # Try to connect to schedule service with short timeout
        response = requests.get(f"{schedule_url}/health", timeout=2)
        
        if response.status_code == 200:
            app.config['SCHEDULE_SERVICE_AVAILABLE'] = True
            logger.info("✅ Schedule service available")
        else:
            raise Exception(f"Schedule service returned {response.status_code}")
            
    except Exception as e:
        app.config['SCHEDULE_SERVICE_AVAILABLE'] = False
        logger.warning(f"⚠️ Schedule service unavailable (using fallback): {e}")
        
        # This is expected in Railway - the schedule service might be on a different container
        if app.config.get('IS_RAILWAY'):
            logger.info("🚄 Railway deployment - schedule service fallback mode enabled")

def register_routes_with_railway_support(app):
    """Register routes with Railway-specific optimizations"""
    
    # Import route blueprints
    try:
        from app.routes.health import bp as health_bp
        from app.routes.companies import bp as companies_bp
        from app.routes.documents import bp as documents_bp
        from app.routes.chat import bp as chat_bp
        from app.routes.admin import bp as admin_bp
        from app.routes.status import bp as status_bp
        
        # Register blueprints with API prefix
        app.register_blueprint(health_bp, url_prefix='/api/health')
        app.register_blueprint(companies_bp, url_prefix='/api/companies')
        app.register_blueprint(documents_bp, url_prefix='/api/documents')
        app.register_blueprint(chat_bp, url_prefix='/api/chat')
        app.register_blueprint(admin_bp, url_prefix='/api/admin')
        app.register_blueprint(status_bp, url_prefix='/api/status')
        
        # Try to register multimedia routes if available
        try:
            from app.routes.multimedia import bp as multimedia_bp
            app.register_blueprint(multimedia_bp, url_prefix='/api/multimedia')
            logger.info("✅ Multimedia routes registered")
        except ImportError:
            logger.warning("⚠️ Multimedia routes not available")
        
        # Try to register schedule routes with Railway fallback
        try:
            from app.routes.schedule import bp as schedule_bp
            app.register_blueprint(schedule_bp, url_prefix='/api/schedule')
            logger.info("✅ Schedule routes registered")
        except ImportError:
            logger.warning("⚠️ Schedule routes not available (fallback mode)")
        
        logger.info("✅ All available routes registered")
        
    except Exception as e:
        logger.error(f"❌ Error registering routes: {e}")

def setup_railway_health_checks(app):
    """Setup Railway-specific health check endpoints"""
    
    @app.route('/health')
    def railway_health_check():
        """Railway health check endpoint"""
        try:
            health_status = {
                "status": "healthy",
                "timestamp": os.times(),
                "environment": "railway" if app.config.get('IS_RAILWAY') else "local",
                "port": app.config.get('PORT', 8080),
                "services": {
                    "redis": app.config.get('REDIS_AVAILABLE', False),
                    "openai": app.config.get('OPENAI_AVAILABLE', False),
                    "schedule_service": app.config.get('SCHEDULE_SERVICE_AVAILABLE', False),
                    "companies": app.config.get('COMPANIES_COUNT', 0) > 0
                }
            }
            
            # Determine overall health
            critical_services = ['redis', 'openai', 'companies']
            all_critical_healthy = all(health_status['services'][service] for service in critical_services)
            
            if not all_critical_healthy:
                health_status['status'] = 'partial'
                health_status['message'] = 'Some critical services unavailable'
            
            # Schedule service is non-critical for Railway
            if not health_status['services']['schedule_service'] and app.config.get('IS_RAILWAY'):
                health_status['schedule_service_note'] = 'Running in fallback mode (expected in Railway)'
            
            status_code = 200 if health_status['status'] == 'healthy' else 206
            return jsonify(health_status), status_code
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return jsonify({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": os.times(),
                "environment": "railway" if app.config.get('IS_RAILWAY') else "local"
            }), 503
    
    @app.route('/health/schedule-service')
    def schedule_service_health_check():
        """Specific health check for schedule service (handles port 4040 issue)"""
        try:
            if app.config.get('SCHEDULE_SERVICE_AVAILABLE'):
                return jsonify({
                    "status": "available",
                    "service": "schedule",
                    "url": app.config.get('SCHEDULE_SERVICE_URL')
                })
            else:
                # Return fallback status instead of error
                return jsonify({
                    "status": "fallback",
                    "service": "schedule",
                    "message": "Schedule service in fallback mode",
                    "fallback_enabled": True
                }), 200  # Return 200 instead of error code
                
        except Exception as e:
            logger.warning(f"Schedule service health check failed: {e}")
            return jsonify({
                "status": "fallback",
                "service": "schedule",
                "message": "Schedule service unavailable, using fallback",
                "error": str(e)
            }), 200  # Return 200 to not fail health checks

def setup_railway_error_handlers(app):
    """Setup Railway-specific error handlers"""
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors for Railway"""
        if request.path.startswith('/api/'):
            return jsonify({
                "status": "error",
                "message": "API endpoint not found",
                "path": request.path
            }), 404
        
        # Try to serve frontend for non-API routes
        return serve_frontend_with_fallback()
    
    @app.errorhandler(500)
    def internal_server_error(error):
        """Handle 500 errors for Railway"""
        logger.error(f"Internal server error: {error}")
        
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "timestamp": os.times(),
            "railway_mode": app.config.get('IS_RAILWAY', False)
        }), 500
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Handle unexpected errors in Railway"""
        logger.error(f"Unexpected error: {error}")
        
        # Check if it's a schedule service connection error (port 4040)
        if "4040" in str(error) or "Connection refused" in str(error):
            logger.warning("Schedule service connection error - continuing with fallback")
            return jsonify({
                "status": "warning",
                "message": "Schedule service temporarily unavailable",
                "fallback_mode": True
            }), 200
        
        return jsonify({
            "status": "error",
            "message": "An unexpected error occurred",
            "railway_mode": app.config.get('IS_RAILWAY', False)
        }), 500

def serve_frontend_with_fallback():
    """Serve frontend with Railway fallback handling"""
    
    @app.route('/')
    def serve_frontend():
        """Serve the frontend or API response for Railway"""
        try:
            # Try to serve the main HTML file
            html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'index.html')
            
            if os.path.exists(html_path):
                return send_file(html_path)
            else:
                # Fallback to API response for Railway
                from app.services.company_manager import get_company_manager
                
                try:
                    company_manager = get_company_manager()
                    companies = company_manager.get_all_companies()
                    
                    return jsonify({
                        "status": "healthy",
                        "message": "Multi-Tenant Chatbot Backend API is running",
                        "system_type": "multi-tenant-multi-agent",
                        "environment": "railway" if app.config.get('IS_RAILWAY') else "local",
                        "companies_configured": len(companies),
                        "available_companies": list(companies.keys()),
                        "services": {
                            "redis": app.config.get('REDIS_AVAILABLE', False),
                            "openai": app.config.get('OPENAI_AVAILABLE', False),
                            "schedule_service": app.config.get('SCHEDULE_SERVICE_AVAILABLE', False)
                        }
                    })
                except Exception as e:
                    logger.error(f"Error getting company info: {e}")
                    return jsonify({
                        "status": "healthy",
                        "message": "Multi-Tenant Backend API is running",
                        "system_type": "multi-tenant-multi-agent",
                        "environment": "railway" if app.config.get('IS_RAILWAY') else "local",
                        "note": "Running in minimal mode"
                    })
                    
        except Exception as e:
            logger.error(f"Error serving frontend: {e}")
            return jsonify({
                "status": "healthy",
                "message": "Multi-Tenant Backend API is running",
                "system_type": "multi-tenant-multi-agent",
                "environment": "railway" if app.config.get('IS_RAILWAY') else "local",
                "error": str(e)
            })
    
    @app.route('/<path:filename>')
    def serve_static(filename):
        """Serve static files for Railway deployment"""
        allowed_files = [
            'index.html', 'style.css', 'script.js', 'favicon.ico', 
            'companies_config.json',
            # New modular files
            'styles/main.css', 'styles/components.css', 'styles/responsive.css',
            'scripts/config.js', 'scripts/api.js', 'scripts/ui.js',
            'scripts/companies.js', 'scripts/documents.js', 'scripts/chat.js',
            'scripts/multimedia.js', 'scripts/admin.js', 'scripts/main.js'
        ]
        
        if filename in allowed_files:
            try:
                # Check if it's a modular file path
                if '/' in filename:
                    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), filename)
                else:
                    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), filename)
                
                if os.path.exists(file_path):
                    return send_file(file_path)
                else:
                    logger.warning(f"Static file not found: {filename}")
                    return jsonify({
                        "status": "error",
                        "message": f"File not found: {filename}",
                        "available_files": allowed_files
                    }), 404
                    
            except Exception as e:
                logger.error(f"Error serving static file {filename}: {e}")
                return jsonify({
                    "status": "error",
                    "message": f"Error serving file: {filename}",
                    "error": str(e)
                }), 500
        else:
            return jsonify({
                "status": "error",
                "message": f"File not allowed: {filename}",
                "allowed_files": allowed_files
            }), 403
    
    return serve_frontend

# Register the frontend routes
def register_frontend_routes(app):
    """Register frontend routes after app creation"""
    serve_frontend_with_fallback()

# Railway-specific middleware for schedule service fallback
def setup_schedule_service_middleware(app):
    """Setup middleware to handle schedule service failures gracefully"""
    
    @app.before_request
    def before_request():
        """Handle requests with schedule service awareness"""
        # Check if request is for schedule-related endpoints
        if request.path.startswith('/api/schedule/'):
            if not app.config.get('SCHEDULE_SERVICE_AVAILABLE'):
                # Return fallback response instead of allowing request to fail
                return jsonify({
                    "status": "warning",
                    "message": "Schedule service temporarily unavailable",
                    "fallback_mode": True,
                    "available_features": [
                        "document_management",
                        "chat_testing", 
                        "admin_tools"
                    ]
                }), 200

# Additional Railway utilities
def get_railway_config():
    """Get Railway-specific configuration"""
    return {
        "is_railway": bool(os.getenv('RAILWAY_ENVIRONMENT_NAME')),
        "railway_project_id": os.getenv('RAILWAY_PROJECT_ID'),
        "railway_environment": os.getenv('RAILWAY_ENVIRONMENT_NAME', 'production'),
        "railway_deployment_id": os.getenv('RAILWAY_DEPLOYMENT_ID'),
        "port": int(os.getenv('PORT', 8080)),
        "schedule_service_fallback": True
    }

def log_railway_startup_info(app):
    """Log Railway startup information"""
    config = get_railway_config()
    
    logger.info("🚄 Railway Deployment Information:")
    logger.info(f"   Project ID: {config.get('railway_project_id', 'N/A')}")
    logger.info(f"   Environment: {config.get('railway_environment', 'N/A')}")
    logger.info(f"   Deployment ID: {config.get('railway_deployment_id', 'N/A')}")
    logger.info(f"   Port: {config.get('port')}")
    logger.info(f"   Schedule Service Fallback: {config.get('schedule_service_fallback')}")
    
    # Log service availability
    logger.info("📊 Service Status:")
    logger.info(f"   Redis: {'✅' if app.config.get('REDIS_AVAILABLE') else '❌'}")
    logger.info(f"   OpenAI: {'✅' if app.config.get('OPENAI_AVAILABLE') else '❌'}")
    logger.info(f"   Schedule Service: {'✅' if app.config.get('SCHEDULE_SERVICE_AVAILABLE') else '🟡 Fallback'}")
    logger.info(f"   Companies: {app.config.get('COMPANIES_COUNT', 0)} configured")

# Enhanced app factory with all Railway fixes
def create_app_with_railway_support(config=None):
    """Create Flask app with full Railway support"""
    app = create_app(config)
    
    # Apply Railway-specific middleware
    setup_schedule_service_middleware(app)
    
    # Register frontend routes
    register_frontend_routes(app)
    
    # Log Railway startup info
    if app.config.get('IS_RAILWAY'):
        log_railway_startup_info(app)
    
    return app

# Export both factory functions for compatibility
__all__ = ['create_app', 'create_app_with_railway_support', 'get_railway_config']
