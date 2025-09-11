# app/__init__.py - Multi-Tenant Flask Application Factory - VERSIÓN REFACTORIZADA

from flask import Flask, request, send_from_directory, send_file, jsonify
from app.config import Config
from app.utils.error_handlers import register_error_handlers
from app.services.redis_service import init_redis
from app.services.vectorstore_service import init_vectorstore
from .openai_service import OpenAIService, init_openai, get_openai_service
from app.config.company_config import get_company_manager
from app.services.multi_agent_factory import get_multi_agent_factory
from app.services.prompt_service import get_prompt_service

# Importar blueprints existentes
from app.routes import webhook, documents, conversations, health, multimedia

# Importar nuevos blueprints integrados
from app.routes.admin import bp as admin_bp
from app.routes.companies import bp as companies_bp
from app.routes.documents_extended import documents_extended_bp
from app.routes.conversations_extended import conversations_extended_bp

import logging
import sys
import threading
import time
import os

def create_app(config_class=Config):
    """Factory pattern para crear la aplicación Flask multi-tenant"""
    app = Flask(__name__, static_folder=None)  # Desactivar static folder por defecto
    app.config.from_object(config_class)
    
    # =============================
    # Configuración del directorio de archivos estáticos simples
    # =============================
    STATIC_DIR = os.path.join('/app', 'static')
    
    # Configurar logging con contexto multi-tenant
    logging.basicConfig(
        level=app.config.get('LOG_LEVEL', 'INFO'),
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("🚀 Initializing Multi-Tenant Chatbot System")
    
    # Log de configuración de archivos estáticos
    logger.info(f"📁 Static directory: {STATIC_DIR}")
    logger.info(f"📁 Static exists: {os.path.exists(STATIC_DIR)}")
    logger.info(f"📁 index.html exists: {os.path.exists(os.path.join(STATIC_DIR, 'index.html'))}")
    
    # Inicializar servicios básicos
    with app.app_context():
        init_redis(app)
        init_openai(app)
        # init_vectorstore se maneja por empresa ahora
    
    # ENHANCED: Middleware multi-tenant
    @app.before_request
    def ensure_multitenant_health():
        """Middleware que verifica salud multi-tenant"""
        multitenant_endpoints = ['/api/webhook/chatwoot', '/api/documents', '/api/conversations', '/webhook/chatwoot']
        
        if any(endpoint in request.path for endpoint in multitenant_endpoints):
            try:
                # Verificar que el gestor de empresas esté inicializado
                company_manager = get_company_manager()
                
                # Log de actividad multi-tenant
                company_id = _extract_company_from_request()
                if company_id:
                    logger.debug(f"Processing request for company: {company_id}")
                
                # Verificación no-bloqueante del factory
                factory = get_multi_agent_factory()
                
                # Si es un webhook, asegurar que el orquestador esté listo en background
                if '/webhook/chatwoot' in request.path and company_id:
                    def background_orchestrator_prep():
                        try:
                            factory.get_orchestrator(company_id)
                        except Exception as e:
                            logger.debug(f"Background orchestrator prep failed for {company_id}: {e}")
                    
                    threading.Thread(target=background_orchestrator_prep, daemon=True).start()
                            
            except Exception as e:
                logger.error(f"Error in multi-tenant middleware: {e}")
                # NUNCA bloquear requests por errores de middleware
    
    def _extract_company_from_request():
        """Extraer company_id del request actual"""
        try:
            # Método 1: Header específico
            company_id = request.headers.get('X-Company-ID')
            if company_id:
                return company_id
            
            # Método 2: Query parameter  
            company_id = request.args.get('company_id')
            if company_id:
                return company_id
            
            # Método 3: Form data (para uploads multimedia)
            if request.form:
                company_id = request.form.get('company_id')
                if company_id:
                    return company_id
            
            # Método 4: JSON body (solo para POST/PUT)
            if request.method in ['POST', 'PUT'] and request.is_json:
                try:
                    data = request.get_json()
                    if data and 'company_id' in data:
                        return data['company_id']
                    
                    # Para webhooks, extraer de la estructura de datos
                    if data and 'conversation' in data:
                        from app.config.company_config import extract_company_id_from_webhook
                        return extract_company_id_from_webhook(data)
                except Exception:
                    pass
            
            return None
            
        except Exception as e:
            logger.debug(f"Could not extract company_id from request: {e}")
            return None
    
    # Registrar blueprints existentes
    app.register_blueprint(webhook.bp, url_prefix='/api/webhook')
    app.register_blueprint(documents.bp, url_prefix='/api/documents')
    app.register_blueprint(conversations.bp, url_prefix='/api/conversations')
    app.register_blueprint(health.bp, url_prefix='/api/health')
    app.register_blueprint(multimedia.bp, url_prefix='/api/multimedia')
    
    # Registrar nuevos blueprints integrados
    app.register_blueprint(admin_bp)  # Ya tiene prefix /api/admin
    app.register_blueprint(companies_bp)  # Ya tiene prefix /api/companies
    app.register_blueprint(documents_extended_bp)  # Ya tiene prefix /api/documents
    app.register_blueprint(conversations_extended_bp)  # Ya tiene prefix /api/conversations
    
    logger.info("✅ All blueprints registered successfully")
    
    # Registrar manejadores de errores
    register_error_handlers(app)
    
    # ============================================================================  
    # ENDPOINTS PRINCIPALES DEL SISTEMA  
    # ============================================================================  
    @app.route('/api/system/info')
    def system_info():
        """Información completa del sistema multi-tenant"""
        try:
            company_manager = get_company_manager()
            companies = company_manager.get_all_companies()
            
            return jsonify({
                "status": "healthy",
                "message": "Multi-Tenant Chatbot Backend API is running",
                "system_type": "multi-tenant-multi-agent",
                "version": "1.0.0",
                "companies_configured": len(companies),
                "available_companies": list(companies.keys()),
                "frontend_type": "simple_static",
                "static_files": {
                    "exists": os.path.exists(STATIC_DIR),
                    "path": STATIC_DIR,
                    "index_html": os.path.exists(os.path.join(STATIC_DIR, 'index.html')),
                    "script_js": os.path.exists(os.path.join(STATIC_DIR, 'script.js')),
                    "style_css": os.path.exists(os.path.join(STATIC_DIR, 'style.css'))
                },
                "endpoints": {
                    "health": "/api/health",
                    "companies": "/api/companies",
                    "documents": "/api/documents",
                    "conversations": "/api/conversations", 
                    "multimedia": "/api/multimedia",
                    "admin": "/api/admin",
                    "webhooks": "/api/webhook"
                },
                "features": [
                    "multi-tenant",
                    "multi-agent",
                    "chatwoot-integration", 
                    "document-management",
                    "multimedia-processing",
                    "google-calendar-integration",
                    "auto-recovery",
                    "redis-isolation"
                ]
            })
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return jsonify({
                "status": "healthy", 
                "message": "Multi-Tenant Backend API is running",
                "system_type": "multi-tenant-multi-agent",
                "error": "Could not load full system info"
            })
    
    @app.route('/api/health/full')  
    def full_health_check():
        """Health check completo con información de empresa"""
        try:
            company_id = request.args.get('company_id')
            
            # Health check básico
            health_data = {
                "status": "healthy",
                "timestamp": time.time(),
                "system_type": "multi-tenant-multi-agent",
                "static_files_ready": os.path.exists(os.path.join(STATIC_DIR, 'index.html'))
            }
            
            # Health check específico de empresa si se proporciona
            if company_id:
                company_manager = get_company_manager()
                if company_manager.validate_company_id(company_id):
                    factory = get_multi_agent_factory()
                    orchestrator = factory.get_orchestrator(company_id)
                    
                    company_health = {
                        "company_id": company_id,
                        "orchestrator_ready": orchestrator is not None,
                        "vectorstore_ready": orchestrator.vectorstore_service is not None if orchestrator else False,
                        "agents_available": list(orchestrator.agents.keys()) if orchestrator else []
                    }
                    health_data["company_health"] = company_health
                else:
                    health_data["company_health"] = {
                        "company_id": company_id,
                        "valid": False,
                        "error": "Company not found"
                    }
            
            return jsonify({
                "status": "success", 
                "data": health_data
            })
            
        except Exception as e:
            logger.error(f"Error in full health check: {e}")
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500

    # ================================================================
    # DEBUG: Ver estructura de archivos estáticos
    # ================================================================
    @app.route('/debug/static-structure')
    def debug_static_structure():
        """Ver la estructura de archivos estáticos"""
        result = {
            "static_path": STATIC_DIR,
            "exists": os.path.exists(STATIC_DIR)
        }
        
        if os.path.exists(STATIC_DIR):
            try:
                files = os.listdir(STATIC_DIR)
                result["files"] = []
                
                for file in files:
                    file_path = os.path.join(STATIC_DIR, file)
                    result["files"].append({
                        "name": file,
                        "size": os.path.getsize(file_path) if os.path.isfile(file_path) else 0,
                        "is_file": os.path.isfile(file_path),
                        "path": file_path
                    })
                
                result["total_files"] = len(files)
                
                # Archivos esperados
                expected_files = ['index.html', 'script.js', 'style.css']
                result["expected_files"] = {}
                
                for file in expected_files:
                    file_path = os.path.join(STATIC_DIR, file)
                    result["expected_files"][file] = {
                        "exists": os.path.exists(file_path),
                        "path": file_path
                    }
                    
            except Exception as e:
                result["error"] = str(e)
        
        return jsonify(result)
    
    # ================================================================
    # SERVIR ARCHIVOS ESTÁTICOS SIMPLES
    # ================================================================
    
    @app.route('/static/<path:filename>')
    def serve_static_files(filename):
        """Servir archivos estáticos (script.js, style.css, etc.)"""
        logger.info(f"📁 Static file request: {filename}")
        
        try:
            return send_from_directory(STATIC_DIR, filename)
        except Exception as e:
            logger.error(f"❌ Error serving static file {filename}: {e}")
            return jsonify({
                "error": "Static file not found",
                "requested": filename,
                "static_dir": STATIC_DIR
            }), 404
    
    @app.route('/script.js')
    def serve_script():
        """Servir script.js directamente"""
        script_path = os.path.join(STATIC_DIR, 'script.js')
        logger.info(f"📄 Script request: {script_path}")
        
        if os.path.exists(script_path):
            logger.info("✅ Serving script.js")
            return send_file(script_path, mimetype='application/javascript')
        else:
            logger.error("❌ script.js not found")
            return jsonify({"error": "script.js not found"}), 404
    
    @app.route('/style.css')
    def serve_style():
        """Servir style.css directamente"""
        style_path = os.path.join(STATIC_DIR, 'style.css')
        logger.info(f"📄 Style request: {style_path}")
        
        if os.path.exists(style_path):
            logger.info("✅ Serving style.css")
            return send_file(style_path, mimetype='text/css')
        else:
            logger.error("❌ style.css not found")
            return jsonify({"error": "style.css not found"}), 404
    
    # ================================================================
    # SERVIR PÁGINA PRINCIPAL - CATCH-ALL ROUTE
    # ================================================================
    
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        """Servir página principal con fallback correcto"""
        
        # No interferir con rutas de API (más específico y completo)
        api_prefixes = ['api/', 'debug/']
        if any(path.startswith(prefix) for prefix in api_prefixes):
            logger.warning(f"⚠️ API route not found: /{path}")
            return jsonify({
                "error": f"API endpoint not found: /{path}",
                "available_endpoints": [
                    "/api/companies",
                    "/api/company/<id>/status", 
                    "/api/health",
                    "/api/health/company/<id>",
                    "/api/admin/status",
                    "/api/documents",
                    "/api/conversations",
                    "/api/multimedia"
                ]
            }), 404
        
        # Archivos estáticos directos
        static_files = ['script.js', 'style.css', 'favicon.ico']
        if path in static_files:
            if path == 'script.js':
                return serve_script()
            elif path == 'style.css':
                return serve_style()
            # Para otros archivos estáticos
            try:
                return send_from_directory(STATIC_DIR, path)
            except:
                return jsonify({"error": f"Static file not found: {path}"}), 404
        
        # Servir index.html para todas las rutas de frontend válidas
        index_path = os.path.join(STATIC_DIR, 'index.html')
        
        logger.info(f"🌐 Frontend route request: '{path}'")
        
        if os.path.exists(index_path):
            logger.info("✅ Serving frontend index.html")
            return send_file(index_path)
        else:
            logger.error(f"❌ Frontend index.html not found at {index_path}")
            return jsonify({
                "error": "Frontend not found",
                "expected_path": index_path,
                "static_dir": STATIC_DIR,
                "files_in_static": os.listdir(STATIC_DIR) if os.path.exists(STATIC_DIR) else [],
                "suggestion": "Check if index.html exists in static directory"
            }), 500

    # ================================================================
    # Inicialización multi-tenant
    # ================================================================
    with app.app_context():
        initialize_multitenant_system(app)
    start_background_initialization(app)
    
    logger.info("🎉 Multi-Tenant Flask application created successfully")
    return app

def initialize_multitenant_system(app):
    """Inicializar sistema multi-tenant después de crear la app"""
    try:
        logger = app.logger
        
        # Inicializar gestor de empresas
        company_manager = get_company_manager()
        companies = company_manager.get_all_companies()
        
        logger.info(f"📊 Multi-tenant system initialized with {len(companies)} companies:")
        for company_id, config in companies.items():
            logger.info(f"   • {company_id}: {config.company_name} ({len(config.services)} services)")
        
        # Inicializar factory de multi-agente
        factory = get_multi_agent_factory()
        logger.info("🏭 Multi-agent factory initialized")
        
        # Pre-cargar orquestadores para empresas principales (opcional)
        primary_companies = ['benova']  # Empresas que se cargan al inicio
        
        for company_id in primary_companies:
            if company_id in companies:
                try:
                    orchestrator = factory.get_orchestrator(company_id)
                    if orchestrator:
                        logger.info(f"✅ Pre-loaded orchestrator for: {company_id}")
                    else:
                        logger.warning(f"⚠️ Could not pre-load orchestrator for: {company_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Error pre-loading orchestrator for {company_id}: {e}")
        
        # Inicializar sistema de auto-recovery multi-tenant (si está habilitado)
        if app.config.get('VECTORSTORE_AUTO_RECOVERY', True):
            try:
                from app.services.vector_auto_recovery import initialize_auto_recovery_system
                
                if initialize_auto_recovery_system():
                    logger.info("🛡️ Multi-tenant auto-recovery system initialized")
                else:
                    logger.warning("⚠️ Could not initialize auto-recovery system")
                    
            except Exception as e:
                logger.warning(f"⚠️ Auto-recovery system initialization failed: {e}")
        
        logger.info("🎯 Multi-tenant system fully initialized")
            
    except Exception as e:
        app.logger.warning(f"⚠️ Could not fully initialize multi-tenant system: {e}")

def startup_checks(app):
    """Verificaciones completas de inicio multi-tenant"""
    try:
        with app.app_context():
            from app.services.redis_service import get_redis_client
            from app.services.openai_service import OpenAIService
            
            # Validar servicios básicos
            redis_client = get_redis_client()
            redis_client.ping()
            
            openai_service = OpenAIService()
            # Test básico sin llamada real para evitar costos innecesarios
            
            # Validar configuración multi-tenant
            company_manager = get_company_manager()
            companies = company_manager.get_all_companies()
            
            if not companies:
                raise ValueError("No companies configured")
            
            # Validar al menos una empresa
            factory = get_multi_agent_factory()
            test_company = list(companies.keys())[0]
            
            orchestrator = factory.get_orchestrator(test_company)
            if not orchestrator:
                raise ValueError(f"Could not create orchestrator for test company: {test_company}")
            
            app.logger.info(f"✅ All startup checks passed for {len(companies)} companies")
            return True
            
    except Exception as e:
        app.logger.error(f"❌ Startup check failed: {e}")
        raise

def delayed_multitenant_initialization(app):
    """Inicialización inteligente multi-tenant en background"""
    max_attempts = 5
    attempt = 0
    
    with app.app_context():
        logger = app.logger
        
        while attempt < max_attempts:
            try:
                attempt += 1
                
                company_manager = get_company_manager()
                companies = company_manager.get_all_companies()
                
                if not companies:
                    logger.warning(f"No companies found on attempt {attempt}")
                    time.sleep(2)
                    continue
                
                factory = get_multi_agent_factory()
                working_companies = 0
                
                for company_id in companies.keys():
                    try:
                        orchestrator = factory.get_orchestrator(company_id)
                        if orchestrator:
                            working_companies += 1
                            logger.debug(f"✅ Orchestrator created for {company_id}")
                    except Exception as e:
                        logger.debug(f"Company {company_id} not ready: {e}")
                        continue
                
                if working_companies > 0:
                    logger.info(f"✅ Multi-tenant system operational with {working_companies}/{len(companies)} companies ready")
                    break
                else:
                    logger.info(f"⏳ Waiting for companies to be ready... attempt {attempt}")
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in delayed multi-tenant initialization attempt {attempt}: {e}")
                time.sleep(1)
        
        if attempt >= max_attempts:
            logger.warning("⚠️ Multi-tenant initialization completed with limited companies")

def start_background_initialization(app):
    """Iniciar proceso de inicialización multi-tenant en background"""
    try:
        init_thread = threading.Thread(
            target=delayed_multitenant_initialization, 
            args=(app,),
            daemon=True
        )
        init_thread.start()
        app.logger.info("🚀 Background multi-tenant initialization started")
    except Exception as e:
        app.logger.error(f"Error starting background multi-tenant initialization: {e}")

# ============================================================================
# FUNCIONES HELPER
# ============================================================================

def get_company_context_from_request(request):
    """Extraer contexto de empresa del request - FUNCIÓN PÚBLICA"""
    # Método 1: Header específico
    company_id = request.headers.get('X-Company-ID')
    if company_id:
        return company_id
    
    # Método 2: Query parameter
    company_id = request.args.get('company_id') 
    if company_id:
        return company_id
    
    # Método 3: Form data
    if request.form:
        company_id = request.form.get('company_id')
        if company_id:
            return company_id
    
    # Método 4: JSON body
    if request.is_json:
        try:
            data = request.get_json()
            if data and 'company_id' in data:
                return data['company_id']
        except:
            pass
    
    # Default fallback
    return 'benova'
