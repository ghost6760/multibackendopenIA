# app/__init__.py - Versión final que funciona con los archivos confirmados

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
    
    # ============================================================================
    # CONFIGURAR RUTAS DE ARCHIVOS ESTÁTICOS
    # ============================================================================
    
    # Ruta absoluta a los archivos build de React
    frontend_build_path = os.path.join('/app', 'src', 'build')
    static_files_path = os.path.join(frontend_build_path, 'static')
    
    logger.info(f"Frontend build path: {frontend_build_path}")
    logger.info(f"Static files path: {static_files_path}")
    logger.info(f"Build directory exists: {os.path.exists(frontend_build_path)}")
    logger.info(f"Static directory exists: {os.path.exists(static_files_path)}")
    
    # ============================================================================
    # ENDPOINTS PARA ARCHIVOS ESTÁTICOS
    # ============================================================================
    
    @app.route('/static/<path:filename>')
    def serve_static_files(filename):
        """Servir archivos estáticos de React (CSS, JS, etc.)"""
        try:
            logger.info(f"Requesting static file: {filename}")
            
            # Intentar servir desde la carpeta static
            full_path = os.path.join(static_files_path, filename)
            logger.info(f"Looking for file at: {full_path}")
            logger.info(f"File exists: {os.path.exists(full_path)}")
            
            if os.path.exists(full_path):
                logger.info(f"✓ Serving static file: {filename}")
                return send_from_directory(static_files_path, filename)
            else:
                logger.error(f"✗ Static file not found: {filename}")
                return jsonify({"error": "Static file not found", "path": full_path}), 404
                
        except Exception as e:
            logger.error(f"Error serving static file {filename}: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/favicon.ico')
    def serve_favicon():
        """Servir favicon"""
        favicon_path = os.path.join(frontend_build_path, 'Favicon.ico')  # Nota: mayúscula como en los logs
        if os.path.exists(favicon_path):
            return send_file(favicon_path)
        return '', 204
    
    @app.route('/manifest.json')
    def serve_manifest():
        """Servir manifest.json"""
        manifest_path = os.path.join(frontend_build_path, 'manifest.json')
        if os.path.exists(manifest_path):
            return send_file(manifest_path)
        return jsonify({"short_name": "MT Admin", "name": "Multi-Tenant Admin"}), 200
    
    @app.route('/robots.txt')
    def serve_robots():
        """Servir robots.txt"""
        robots_path = os.path.join(frontend_build_path, 'robots.txt')
        if os.path.exists(robots_path):
            return send_file(robots_path)
        return 'User-agent: *\nAllow: /', 200, {'Content-Type': 'text/plain'}
    
    @app.route('/sw.js')
    def serve_service_worker():
        """Servir service worker vacío"""
        return '', 204
    
    # ============================================================================
    # ENDPOINTS DE DEBUG
    # ============================================================================
    
    @app.route('/debug/static')
    def debug_static_files():
        """Debug endpoint para verificar archivos estáticos"""
        debug_info = {
            "frontend_build_path": frontend_build_path,
            "static_files_path": static_files_path,
            "build_exists": os.path.exists(frontend_build_path),
            "static_exists": os.path.exists(static_files_path),
            "current_working_directory": os.getcwd()
        }
        
        if os.path.exists(frontend_build_path):
            debug_info["build_contents"] = os.listdir(frontend_build_path)
        
        if os.path.exists(static_files_path):
            # Listar todos los archivos estáticos recursivamente
            static_files = []
            for root, dirs, files in os.walk(static_files_path):
                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), static_files_path)
                    static_files.append(rel_path)
            debug_info["all_static_files"] = static_files
            debug_info["static_subdirs"] = [d for d in os.listdir(static_files_path) if os.path.isdir(os.path.join(static_files_path, d))]
        
        return jsonify(debug_info)
    
    # ============================================================================
    # API ENDPOINTS BÁSICOS
    # ============================================================================
    
    @app.route('/api/health')
    def health_check():
        """Basic health check"""
        return jsonify({
            "status": "healthy",
            "message": "Multi-Tenant Backend API is running",
            "system_type": "multi-tenant-multi-agent"
        })
    
    @app.route('/api/companies')
    def get_companies():
        """Get all companies - fallback implementation"""
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
    
    # ============================================================================
    # SERVIR FRONTEND REACT (SPA ROUTING)
    # ============================================================================
    
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_react_app(path):
        """Servir la aplicación React (Single Page Application)"""
        
        # Si es una llamada a la API, no servir frontend
        if path.startswith('api/'):
            return jsonify({"error": "API endpoint not found"}), 404
        
        # Si es una ruta de debug, no interferir
        if path.startswith('debug/'):
            return jsonify({"error": "Debug endpoint not found"}), 404
        
        # Si es un archivo estático que no manejamos arriba, verificar si existe
        if path and '.' in path and not path.endswith('.html'):
            file_path = os.path.join(frontend_build_path, path)
            if os.path.exists(file_path):
                return send_file(file_path)
        
        # Para todas las demás rutas, servir index.html (SPA routing)
        index_path = os.path.join(frontend_build_path, 'index.html')
        
        if os.path.exists(index_path):
            logger.info(f"Serving React app index.html for path: {path}")
            return send_file(index_path)
        else:
            logger.error(f"React index.html not found at: {index_path}")
            return jsonify({
                "error": "Frontend not available",
                "message": "React build not found",
                "expected_path": index_path
            }), 404
    
    # ============================================================================
    # ERROR HANDLERS
    # ============================================================================
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors"""
        return jsonify({"error": "Resource not found"}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        logger.error(f"Internal server error: {error}")
        return jsonify({"error": "Internal server error"}), 500
    
    # ============================================================================
    # INICIALIZACIÓN
    # ============================================================================
    
    logger.info("🚀 Flask application created successfully")
    logger.info(f"📁 Frontend build directory: {frontend_build_path}")
    logger.info(f"📄 Static files directory: {static_files_path}")
    
    # Verificar archivos al inicio
    if os.path.exists(frontend_build_path):
        logger.info(f"✅ Build directory found")
        files = os.listdir(frontend_build_path)
        logger.info(f"📋 Build contents: {files}")
        
        if os.path.exists(static_files_path):
            logger.info(f"✅ Static directory found")
            static_subdirs = [d for d in os.listdir(static_files_path) if os.path.isdir(os.path.join(static_files_path, d))]
            logger.info(f"📋 Static subdirectories: {static_subdirs}")
        else:
            logger.warning(f"⚠️ Static directory not found")
    else:
        logger.error(f"❌ Build directory not found")
    
    return app
