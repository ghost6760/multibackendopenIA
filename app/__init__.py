# app/__init__.py - Multi-Tenant Flask Application Factory - VERSIÓN REFACTORIZADA

from flask import Flask, request, send_from_directory, send_file, jsonify
from app.config import Config
from app.utils.error_handlers import register_error_handlers
from app.services.redis_service import init_redis
from app.services.vectorstore_service import init_vectorstore
from app.services.openai_service import init_openai
from app.config.company_config import get_company_manager
from app.services.multi_agent_factory import get_multi_agent_factory
from app.services.prompt_service import get_prompt_service

# 🆕 IMPORTAR SERVICIO ENTERPRISE
from app.services.company_config_service import get_enterprise_company_service

# Importar blueprints existentes
from app.routes import webhook, documents, conversations, health, multimedia

# Importar blueprint de diagnóstico (TEMPORAL)
from app.routes.diagnostic import diagnostic_bp

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
        
        # 🆕 INICIALIZAR SERVICIO ENTERPRISE
        try:
            enterprise_service = get_enterprise_company_service()
            logger.info("✅ Enterprise company service initialized")
            
            # Verificar conexión a PostgreSQL
            db_status = enterprise_service.get_db_status()
            if db_status.get('postgresql_available'):
                logger.info("✅ PostgreSQL connection available for Enterprise features")
            else:
                logger.warning("⚠️ PostgreSQL not available, Enterprise service will use JSON fallback")
                
        except Exception as e:
            logger.warning(f"⚠️ Enterprise service initialization failed: {e}")
    
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

    # Registrar blueprint temporal
    app.register_blueprint(diagnostic_bp)  # /api/diagnostic
    
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
            
            # 🆕 AGREGAR INFO ENTERPRISE
            enterprise_info = {}
            try:
                enterprise_service = get_enterprise_company_service()
                db_status = enterprise_service.get_db_status()
                enterprise_info = {
                    "enterprise_enabled": True,
                    "postgresql_available": db_status.get('postgresql_available', False),
                    "connection_status": db_status.get('connection_status', 'unknown'),
                    "fallback_mode": not db_status.get('postgresql_available', False)
                }
            except Exception as e:
                enterprise_info = {
                    "enterprise_enabled": False,
                    "error": str(e)
                }
            
            return jsonify({
                "status": "healthy",
                "message": "Multi-Tenant Chatbot Backend API is running",
                "system_type": "multi-tenant-multi-agent",
                "version": "1.0.0",
                "companies_configured": len(companies),
                "available_companies": list(companies.keys()),
                "frontend_type": "simple_static",
                "enterprise": enterprise_info,  # 🆕 AGREGAR
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
                    "redis-isolation",
                    "enterprise-config"  # 🆕 AGREGAR
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
            
            # 🆕 AGREGAR HEALTH CHECK ENTERPRISE
            try:
                enterprise_service = get_enterprise_company_service()
                db_status = enterprise_service.get_db_status()
                health_data["enterprise"] = {
                    "service_available": True,
                    "postgresql_available": db_status.get('postgresql_available', False),
                    "connection_status": db_status.get('connection_status', 'unknown')
                }
            except Exception as e:
                health_data["enterprise"] = {
                    "service_available": False,
                    "error": str(e)
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
                    
                    # 🆕 AGREGAR INFO ENTERPRISE POR EMPRESA
                    try:
                        enterprise_service = get_enterprise_company_service()
                        enterprise_config = enterprise_service.get_company_config(company_id, use_cache=False)
                        company_health["enterprise_config"] = {
                            "available": enterprise_config is not None,
                            "source": "postgresql" if enterprise_config and hasattr(enterprise_config, 'notes') and 'postgresql' in enterprise_config.notes.lower() else "json_fallback"
                        }
                    except Exception as e:
                        company_health["enterprise_config"] = {
                            "available": False,
                            "error": str(e)
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
    # DEBUG: Estructura de archivos Vue.js
    # ================================================================
    @app.route('/debug/vue-structure')
    def debug_vue_structure():
        """Ver la estructura de archivos del build de Vue.js"""
        result = {
            "static_path": STATIC_DIR,
            "exists": os.path.exists(STATIC_DIR)
        }
        
        if os.path.exists(STATIC_DIR):
            try:
                # Archivos en la raíz
                files = os.listdir(STATIC_DIR)
                result["root_files"] = []
                
                for file in files:
                    file_path = os.path.join(STATIC_DIR, file)
                    if os.path.isfile(file_path):
                        result["root_files"].append({
                            "name": file,
                            "size": os.path.getsize(file_path),
                            "path": file_path
                        })
                
                # Assets directory (donde Vue.js pone JS/CSS)
                assets_path = os.path.join(STATIC_DIR, 'assets')
                if os.path.exists(assets_path):
                    result["assets_dir"] = {
                        "exists": True,
                        "path": assets_path,
                        "files": []
                    }
                    
                    for file in os.listdir(assets_path):
                        file_path = os.path.join(assets_path, file)
                        if os.path.isfile(file_path):
                            result["assets_dir"]["files"].append({
                                "name": file,
                                "size": os.path.getsize(file_path),
                                "type": "js" if file.endswith('.js') else "css" if file.endswith('.css') else "other"
                            })
                else:
                    result["assets_dir"] = {"exists": False}
                
                # Verificar archivos críticos
                critical_files = ['index.html', 'vite.svg', 'favicon.ico']
                result["critical_files"] = {}
                
                for file in critical_files:
                    file_path = os.path.join(STATIC_DIR, file)
                    result["critical_files"][file] = {
                        "exists": os.path.exists(file_path),
                        "path": file_path
                    }
                    
            except Exception as e:
                result["error"] = str(e)
        
        return jsonify(result)
    
    # ================================================================
    # SERVIR FRONTEND VUE.JS - SPA SUPPORT
    # ================================================================
    
    @app.route('/assets/<path:filename>')
    def serve_vue_assets(filename):
        """Servir assets de Vue.js (JS, CSS, imágenes)"""
        assets_dir = os.path.join(STATIC_DIR, 'assets')
        logger.info(f"📦 Vue asset request: {filename}")
        
        try:
            return send_from_directory(assets_dir, filename)
        except Exception as e:
            logger.error(f"❌ Error serving Vue asset {filename}: {e}")
            return jsonify({
                "error": "Vue asset not found",
                "requested": filename,
                "assets_dir": assets_dir
            }), 404
    
    @app.route('/static/<path:filename>')
    def serve_static_files(filename):
        """Servir archivos estáticos adicionales (favicon, etc.)"""
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
    
    # ================================================================
    # VUE.JS SPA ROUTING - CATCH-ALL ROUTE
    # ================================================================
    
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_vue_spa(path):
        """Servir Vue.js SPA con soporte completo para routing"""
        
        # ============================================
        # 1. No interferir con rutas de API
        # ============================================
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
                    "/api/multimedia",
                    "/api/prompts",
                    "/api/enterprise/*",
                    "/api/admin/*"
                ]
            }), 404
        
        # ============================================
        # 2. Servir assets de Vue.js directamente
        # ============================================
        if path.startswith('assets/'):
            asset_filename = path[7:]  # Remover 'assets/' prefix
            return serve_vue_assets(asset_filename)
        
        # ============================================
        # 3. Archivos estáticos especiales
        # ============================================
        special_files = ['favicon.ico', 'robots.txt', 'sitemap.xml']
        if path in special_files:
            try:
                return send_from_directory(STATIC_DIR, path)
            except:
                # Si no existe, servir 404 silencioso
                return jsonify({"error": f"File not found: {path}"}), 404
        
        # ============================================
        # 4. SERVIR VUE.JS SPA - index.html para todas las rutas
        # ============================================
        index_path = os.path.join(STATIC_DIR, 'index.html')
        
        logger.info(f"🌐 Vue.js SPA route request: '{path}'")
        
        if os.path.exists(index_path):
            logger.info("✅ Serving Vue.js SPA index.html")
            
            # Agregar headers para SPA
            response = make_response(send_file(index_path))
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            
            return response
        else:
            logger.error(f"❌ Vue.js index.html not found at {index_path}")
            
            # Debug info para troubleshooting
            debug_info = {
                "error": "Vue.js frontend not found",
                "expected_path": index_path,
                "static_dir": STATIC_DIR,
                "static_dir_exists": os.path.exists(STATIC_DIR)
            }
            
            if os.path.exists(STATIC_DIR):
                debug_info["files_in_static"] = os.listdir(STATIC_DIR)
            
            return jsonify(debug_info), 500
    


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
        
        # 🆕 VERIFICAR SERVICIO ENTERPRISE EN INICIALIZACIÓN
        try:
            enterprise_service = get_enterprise_company_service()
            db_status = enterprise_service.get_db_status()
            
            if db_status.get('postgresql_available'):
                logger.info("🏢 Enterprise PostgreSQL service operational")
                
                # Listar empresas en PostgreSQL
                try:
                    pg_companies = enterprise_service.list_companies()
                    logger.info(f"📊 PostgreSQL companies: {len(pg_companies)} found")
                    for company in pg_companies[:3]:  # Log first 3
                        logger.info(f"   • PG: {company.company_id} - {company.company_name}")
                except Exception as e:
                    logger.debug(f"Could not list PostgreSQL companies: {e}")
            else:
                logger.info("🏢 Enterprise service using JSON fallback mode")
                
        except Exception as e:
            logger.warning(f"⚠️ Enterprise service check failed in initialization: {e}")
        
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
