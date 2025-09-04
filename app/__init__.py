# app/__init__.py - Multi-Tenant Flask Application Factory - VERSIÓN FINAL

from flask import Flask, request, send_from_directory, send_file, jsonify
from app.config import Config
from app.utils.error_handlers import register_error_handlers
from app.services.redis_service import init_redis
from app.services.vectorstore_service import init_vectorstore
from app.services.openai_service import init_openai
from app.config.company_config import get_company_manager
from app.services.multi_agent_factory import get_multi_agent_factory

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


app = Flask(__name__)

# =============================
# Configuración del directorio React build
# =============================
REACT_BUILD_DIR = os.path.abspath(
    os.getenv("REACT_BUILD_DIR", os.path.join(os.getcwd(), "src/build"))
)

app.logger.info(f"✅ React build directory set to: {REACT_BUILD_DIR}")


def create_app(config_class=Config):
    """Factory pattern para crear la aplicación Flask multi-tenant"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Configurar logging con contexto multi-tenant
    logging.basicConfig(
        level=app.config.get('LOG_LEVEL', 'INFO'),
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("🚀 Initializing Multi-Tenant Chatbot System")
    
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
                "system_type": "multi-tenant-multi-agent"
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
    # DEBUG: Ver estructura de build y servir archivos estáticos
    # ================================================================
    @app.route('/debug/build-structure')
    def debug_build_structure():
        """Ver la estructura completa de archivos build"""
        build_path = '/app/src/build'
        result = {
            "build_path": build_path,
            "exists": os.path.exists(build_path)
        }
        
        if os.path.exists(build_path):
            all_files = []
            for root, dirs, files in os.walk(build_path):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, build_path)
                    all_files.append({
                        "path": rel_path,
                        "size": os.path.getsize(full_path),
                        "full_path": full_path
                    })
            result["all_files"] = all_files
            result["total_files"] = len(all_files)
            
            static_path = os.path.join(build_path, 'static')
            if os.path.exists(static_path):
                result["static_structure"] = {
                    "css_exists": os.path.exists(os.path.join(static_path, 'css')),
                    "js_exists": os.path.exists(os.path.join(static_path, 'js')),
                    "css_files": os.listdir(os.path.join(static_path, 'css')) if os.path.exists(os.path.join(static_path, 'css')) else [],
                    "js_files": os.listdir(os.path.join(static_path, 'js')) if os.path.exists(os.path.join(static_path, 'js')) else []
                }
        
        return jsonify(result)

    @app.route('/static/<path:filename>')
    def serve_static(filename):
        static_dir = os.path.join(REACT_BUILD_DIR, 'static')
    
        # ✅ Evitar path traversal (por seguridad)
        if ".." in filename or filename.startswith("/"):
            app.logger.warning(f"❌ Invalid static file request: {filename}")
            return jsonify({"error": "Invalid file path"}), 400
    
        full_path = os.path.join(static_dir, filename)
    
        # ✅ Verificar si el archivo existe
        if os.path.exists(full_path):
            app.logger.info(f"📄 Serving static file: {filename}")
            return send_from_directory(static_dir, filename)
        else:
            app.logger.error(f"❌ Static file not found: {filename}")
            return jsonify({"error": "Static file not found", "requested": filename}), 40

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_react(path):
        # Evitar que APIs o rutas internas pasen por aquí
        if path.startswith('api/') or path.startswith('debug/'):
            return jsonify({"error": "API endpoint not found"}), 404
    
        index_path = os.path.join(REACT_BUILD_DIR, 'index.html')
    
        # ✅ Si el archivo existe, servirlo
        if os.path.exists(index_path):
            app.logger.info(f"📄 Serving React app from: {index_path}")
            return send_file(index_path)
        else:
            # ✅ Si no existe, devolver un error informativo
            app.logger.error(f"❌ React build not found at {index_path}")
            return jsonify({
                "error": "React build not found",
                "expected_path": index_path
            }), 500

    # ================================================================
    # Inicialización multi-tenant
    # ================================================================
    with app.app_context():
        initialize_multitenant_system(app)
    start_background_initialization(app)
    
    logger.info("🎉 Multi-Tenant Flask application created successfully")
    return app
    
    # ============================================================================
    # INICIALIZACIÓN MULTI-TENANT
    # ============================================================================
    
    # Inicializar sistemas multi-tenant después de crear la app
    with app.app_context():
        initialize_multitenant_system(app)
    
    # Iniciar inicialización en background para mejor performance
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
    max_attempts = 10
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
                
                # Verificar que al menos una empresa funcione
                working_companies = 0
                
                for company_id in companies.keys():
                    try:
                        orchestrator = factory.get_orchestrator(company_id)
                        if orchestrator:
                            # Test básico
                            health = orchestrator.health_check()
                            if health.get("system_healthy", False):
                                working_companies += 1
                    except Exception as e:
                        logger.debug(f"Company {company_id} not ready: {e}")
                        continue
                
                if working_companies > 0:
                    logger.info(f"✅ Multi-tenant system operational with {working_companies}/{len(companies)} companies ready")
                    break
                else:
                    logger.info(f"⏳ Waiting for companies to be ready... attempt {attempt}")
                
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error in delayed multi-tenant initialization attempt {attempt}: {e}")
                time.sleep(2)
        
        if attempt >= max_attempts:
            logger.error("❌ Failed to initialize multi-tenant system after maximum attempts")

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
