from flask import Flask, request, send_from_directory, send_file, jsonify
from app.config import Config
from app.utils.error_handlers import register_error_handlers
from app.services.redis_service import init_redis
from app.services.vectorstore_service import init_vectorstore
from app.services.openai_service import init_openai
from app.config.company_config import get_company_manager
from app.services.multi_agent_factory import get_multi_agent_factory
from app.routes import webhook, documents, conversations, health, multimedia, admin
import logging
import sys
import threading
import time
import os

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
        multitenant_endpoints = ['/webhook/chatwoot', '/documents', '/conversations']
        
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
                
                # Si es un webhook, asegurar que el orquestador esté listo
                if '/webhook/chatwoot' in request.path and company_id:
                    def background_orchestrator_prep():
                        try:
                            factory.get_orchestrator(company_id)
                        except:
                            pass
                    
                    threading.Thread(target=background_orchestrator_prep, daemon=True).start()
                            
            except Exception as e:
                logger.error(f"Error in multi-tenant middleware: {e}")
                # NUNCA bloquear requests
    
    def _extract_company_from_request() -> str:
        """Extraer company_id del request actual"""
        try:
            # Método 1: Header
            company_id = request.headers.get('X-Company-ID')
            if company_id:
                return company_id
            
            # Método 2: Query param
            company_id = request.args.get('company_id')
            if company_id:
                return company_id
            
            # Método 3: JSON body (solo para POST/PUT)
            if request.method in ['POST', 'PUT'] and request.is_json:
                data = request.get_json()
                if data and 'company_id' in data:
                    return data['company_id']
                
                # Para webhooks, extraer de la estructura de datos
                if data and 'conversation' in data:
                    from app.config.company_config import extract_company_id_from_webhook
                    return extract_company_id_from_webhook(data)
            
            return None
            
        except Exception as e:
            logger.debug(f"Could not extract company_id from request: {e}")
            return None
    
    # Registrar blueprints
    app.register_blueprint(webhook.bp, url_prefix='/webhook')
    app.register_blueprint(documents.bp, url_prefix='/documents')
    app.register_blueprint(conversations.bp, url_prefix='/conversations')
    app.register_blueprint(health.bp, url_prefix='/health')
    app.register_blueprint(multimedia.bp, url_prefix='/multimedia')
    app.register_blueprint(admin.bp, url_prefix='/admin')
    
    # Rutas adicionales multi-tenant
    @app.route('/companies')
    def list_companies():
        """Listar todas las empresas configuradas"""
        try:
            company_manager = get_company_manager()
            companies = company_manager.get_all_companies()
            
            companies_info = {}
            for company_id, config in companies.items():
                companies_info[company_id] = {
                    "company_name": config.company_name,
                    "services": config.services,
                    "vectorstore_index": config.vectorstore_index,
                    "status": "configured"
                }
            
            return jsonify({
                "status": "success",
                "total_companies": len(companies),
                "companies": companies_info,
                "system_type": "multi-tenant"
            })
            
        except Exception as e:
            logger.error(f"Error listing companies: {e}")
            return jsonify({
                "status": "error",
                "message": "Failed to list companies",
                "system_type": "multi-tenant"
            }), 500
    
    @app.route('/company/<company_id>/status')
    def company_status(company_id):
        """Estado específico de una empresa"""
        try:
            company_manager = get_company_manager()
            
            if not company_manager.validate_company_id(company_id):
                return jsonify({
                    "status": "error",
                    "message": f"Company not found: {company_id}"
                }), 404
            
            config = company_manager.get_company_config(company_id)
            factory = get_multi_agent_factory()
            orchestrator = factory.get_orchestrator(company_id)
            
            status_info = {
                "company_id": company_id,
                "company_name": config.company_name,
                "services": config.services,
                "orchestrator_ready": orchestrator is not None,
                "vectorstore_index": config.vectorstore_index,
                "redis_prefix": config.redis_prefix
            }
            
            if orchestrator:
                health = orchestrator.health_check()
                status_info.update({
                    "system_healthy": health.get("system_healthy", False),
                    "agents_available": health.get("agents_status", {}).keys()
                })
            
            return jsonify({
                "status": "success",
                "data": status_info
            })
            
        except Exception as e:
            logger.error(f"Error getting status for company {company_id}: {e}")
            return jsonify({
                "status": "error",
                "message": f"Failed to get status for company: {company_id}"
            }), 500
    
    @app.route('/')
    def serve_frontend():
        """Servir el frontend o respuesta API multi-tenant"""
        try:
            html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'index.html')
            
            if os.path.exists(html_path):
                return send_file(html_path)
            else:
                # Información del sistema multi-tenant
                company_manager = get_company_manager()
                companies = company_manager.get_all_companies()
                
                return jsonify({
                    "status": "healthy",
                    "message": "Multi-Tenant Chatbot Backend API is running",
                    "system_type": "multi-tenant-multi-agent",
                    "companies_configured": len(companies),
                    "available_companies": list(companies.keys())
                })
        except Exception as e:
            logger.error(f"Error serving frontend: {e}")
            return jsonify({
                "status": "healthy", 
                "message": "Multi-Tenant Backend API is running",
                "system_type": "multi-tenant-multi-agent"
            })
    
    @app.route('/<path:filename>')
    def serve_static(filename):
        """Servir archivos estáticos del frontend"""
        allowed_files = ['style.css', 'script.js', 'index.html', 'favicon.ico', 'companies_config.json']
        
        if filename in allowed_files:
            try:
                file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), filename)
                
                if os.path.exists(file_path):
                    return send_file(file_path)
                else:
                    return jsonify({"status": "error", "message": "File not found"}), 404
            except Exception as e:
                logger.error(f"Error serving static file {filename}: {e}")
                return jsonify({"status": "error", "message": "Error serving file"}), 500
        else:
            return jsonify({"status": "error", "message": "File not allowed"}), 403
    
    # Registrar error handlers
    register_error_handlers(app)
    
    # ENHANCED: Inicializar sistemas multi-tenant después de crear la app
    with app.app_context():
        initialize_multitenant_system(app)
    
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
            logger.info(f"   • {company_id}: {config.company_name} ({config.services})")
        
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
                from app.services.vector_auto_recovery import (
                    initialize_auto_recovery_system
                )
                
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
            openai_service.test_connection()
            
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
