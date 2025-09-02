# app/__init__.py - Corregido para servir archivos estáticos de React correctamente

import os
from flask import Flask, jsonify, send_from_directory, send_file
from flask_cors import CORS
import logging

def create_app(config_name='production'):
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Configure CORS
    CORS(app, origins=['*'])
    
    # Basic configuration
    app.config['ENV'] = config_name
    app.config['DEBUG'] = config_name == 'development'
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = app.logger
    
    # Try to import and configure full app
    try:
        from app.config.company_config import get_company_manager
        from app.routes import health
        
        # Register basic health endpoint
        app.register_blueprint(health.bp, url_prefix='/api/health')
        logger.info("Health endpoint registered")
        
        # Try to register other blueprints
        try:
            from app.routes import webhook, documents, conversations, multimedia
            app.register_blueprint(webhook.bp, url_prefix='/api/webhook')
            app.register_blueprint(documents.bp, url_prefix='/api/documents') 
            app.register_blueprint(conversations.bp, url_prefix='/api/conversations')
            app.register_blueprint(multimedia.bp, url_prefix='/api/multimedia')
            logger.info("All API blueprints registered")
        except ImportError as e:
            logger.warning(f"Some API routes not available: {e}")
            
    except ImportError as e:
        logger.warning(f"Advanced features not available: {e}")
    
    # ============================================================================
    # API ENDPOINTS BÁSICOS
    # ============================================================================
    
    @app.route('/api/companies')
    def get_companies():
        """Get all companies - fallback implementation"""
        try:
            from app.config.company_config import get_company_manager
            company_manager = get_company_manager()
            companies = company_manager.get_all_companies()
            
            return jsonify({
                "status": "success",
                "companies": {
                    company_id: {
                        "company_name": config.company_name,
                        "services": config.services,
                        "phone": getattr(config, 'phone', 'N/A'),
                        "email": getattr(config, 'email', 'N/A')
                    }
                    for company_id, config in companies.items()
                }
            })
        except Exception as e:
            logger.error(f"Error getting companies: {e}")
            # Fallback response
            return jsonify({
                "status": "success",
                "companies": {
                    "demo": {
                        "company_name": "Empresa Demo",
                        "services": "Servicios de demostración",
                        "phone": "N/A",
                        "email": "demo@example.com"
                    }
                }
            })
    
    @app.route('/api/health')
    def health_check():
        """Basic health check"""
        return jsonify({
            "status": "healthy",
            "message": "Multi-Tenant Backend API is running",
            "system_type": "multi-tenant-multi-agent"
        })
    
    # ============================================================================
    # SERVIR FRONTEND REACT - CORREGIDO
    # ============================================================================
    
    # Configurar directorio de archivos estáticos de React
    frontend_build_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src', 'build')
    
    @app.route('/static/<path:filename>')
    def serve_static(filename):
        """Servir archivos estáticos de React (CSS, JS, etc.)"""
        static_path = os.path.join(frontend_build_path, 'static')
        if os.path.exists(os.path.join(static_path, filename)):
            return send_from_directory(static_path, filename)
        else:
            logger.error(f"Static file not found: {filename}")
            logger.error(f"Looking in: {static_path}")
            logger.error(f"Available files: {os.listdir(static_path) if os.path.exists(static_path) else 'Directory not found'}")
            return jsonify({"error": "Static file not found"}), 404
    
    @app.route('/manifest.json')
    def serve_manifest():
        """Servir manifest.json"""
        manifest_path = os.path.join(frontend_build_path, 'manifest.json')
        if os.path.exists(manifest_path):
            return send_file(manifest_path)
        else:
            return jsonify({
                "short_name": "MT Admin",
                "name": "Multi-Tenant Admin",
                "start_url": "./",
                "display": "standalone"
            })
    
    @app.route('/favicon.ico')
    def serve_favicon():
        """Servir favicon"""
        favicon_path = os.path.join(frontend_build_path, 'favicon.ico')
        if os.path.exists(favicon_path):
            return send_file(favicon_path)
        else:
            # Return empty response for missing favicon
            return '', 204
    
    @app.route('/logo192.png')
    def serve_logo():
        """Servir logo"""
        logo_path = os.path.join(frontend_build_path, 'logo192.png')
        if os.path.exists(logo_path):
            return send_file(logo_path)
        else:
            return '', 204
    
    @app.route('/sw.js')
    def serve_sw():
        """Servir service worker"""
        return '', 204  # Empty service worker
    
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        """Servir el frontend React"""
        # Si es una llamada a la API, no servir frontend
        if path.startswith('api/'):
            return jsonify({"error": "API endpoint not found"}), 404
        
        # Si es un archivo específico que no sea HTML, intentar servirlo
        if path and '.' in path and not path.endswith('.html'):
            file_path = os.path.join(frontend_build_path, path)
            if os.path.exists(file_path):
                return send_file(file_path)
        
        # Para todas las demás rutas, servir index.html (SPA routing)
        index_path = os.path.join(frontend_build_path, 'index.html')
        
        if os.path.exists(index_path):
            return send_file(index_path)
        else:
            logger.error(f"Frontend not found at: {frontend_build_path}")
            logger.error(f"Available files: {os.listdir(os.path.dirname(frontend_build_path)) if os.path.exists(os.path.dirname(frontend_build_path)) else 'Parent dir not found'}")
            
            # Fallback: mostrar información del sistema
            return jsonify({
                "status": "healthy",
                "message": "Multi-Tenant Chatbot Backend API is running",
                "system_type": "multi-tenant-multi-agent", 
                "frontend_status": "React frontend not built or not found",
                "expected_path": frontend_build_path,
                "api_documentation": "/api/health"
            })
    
    # ============================================================================
    # ERROR HANDLERS
    # ============================================================================
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors"""
        return jsonify({"error": "Endpoint not found"}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        logger.error(f"Internal server error: {error}")
        return jsonify({"error": "Internal server error"}), 500
    
    # ============================================================================
    # LOGGING DE INICIALIZACIÓN
    # ============================================================================
    
    logger.info("Flask application created successfully")
    logger.info(f"Frontend build path: {frontend_build_path}")
    logger.info(f"Frontend exists: {os.path.exists(frontend_build_path)}")
    
    if os.path.exists(frontend_build_path):
        files = os.listdir(frontend_build_path)
        logger.info(f"Frontend files: {files}")
        
        static_path = os.path.join(frontend_build_path, 'static')
        if os.path.exists(static_path):
            static_files = os.listdir(static_path)
            logger.info(f"Static files: {static_files}")
        else:
            logger.warning("Static directory not found in build")
    
    return app
