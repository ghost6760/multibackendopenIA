# app/routes/admin.py - Endpoints administrativos integrados

from flask import Blueprint, request, jsonify, current_app
from app.services.multi_agent_factory import get_multi_agent_factory
from app.services.redis_service import get_redis_client
from app.config.company_config import get_company_manager
from app.utils.decorators import handle_errors, require_api_key
from app.utils.helpers import create_success_response, create_error_response
from typing import Dict, Any, List
import logging
import time
from app.services.prompt_service import get_prompt_service
from app.utils.helpers import create_success_response, create_error_response
from app.utils.validators import validate_company_id, validate_agent_name

import json
import os
from datetime import datetime
from app.services.openai_service import OpenAIService

logger = logging.getLogger(__name__)

bp = Blueprint('admin', __name__, url_prefix='/api/admin')

def _get_company_id_from_request():
    """Obtener company_id de múltiples fuentes con validación"""
    company_id = None
    
    # Prioridad 1: Header
    if request.headers.get('X-Company-ID'):
        company_id = request.headers.get('X-Company-ID')
        logger.debug(f"Company ID from header: {company_id}")
    
    # Prioridad 2: Query parameter
    elif request.args.get('company_id'):
        company_id = request.args.get('company_id')
        logger.debug(f"Company ID from query: {company_id}")
    
    # Prioridad 3: JSON body
    elif request.is_json and request.get_json().get('company_id'):
        company_id = request.get_json().get('company_id')
        logger.debug(f"Company ID from body: {company_id}")
    
    # Validar que no esté vacío
    if company_id and company_id.strip():
        return company_id.strip()
    
    # Si no hay company_id, retornar None (no string vacío)
    return None

# ============================================================================
# NUEVOS ENDPOINTS PARA FRONTEND REACT
# ============================================================================

@bp.route('/config/google-calendar', methods=['POST'])
@handle_errors
def update_google_calendar_config():
    """Actualizar configuración de Google Calendar para una empresa"""
    try:
        data = request.get_json()
        company_id = data.get('company_id') or request.headers.get('X-Company-ID')
        google_calendar_url = data.get('google_calendar_url')
        
        if not company_id:
            return create_error_response("company_id is required", 400)
        
        if not google_calendar_url:
            return create_error_response("google_calendar_url is required", 400)
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        # TODO: Actualizar configuración real en extended_companies_config.json
        # Por ahora, lo simulamos como exitoso
        logger.info(f"Google Calendar URL updated for company {company_id}: {google_calendar_url}")
        
        return create_success_response({
            "message": "Google Calendar configuration updated successfully",
            "company_id": company_id,
            "google_calendar_url": google_calendar_url
        })
        
    except Exception as e:
        logger.error(f"Error updating Google Calendar config: {e}")
        return create_error_response(str(e), 500)

# ============================================================================
# ENDPOINTS AVANZADOS EXISTENTES - MEJORADOS
# ============================================================================

@bp.route('/vectorstore/force-recovery', methods=['POST'])
@handle_errors
@require_api_key
def force_vectorstore_recovery():
    """Force vectorstore recovery - ENHANCED Multi-tenant"""
    try:
        company_id = _get_company_id_from_request()
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        from app.services.vector_auto_recovery import get_auto_recovery_instance
        
        # Get company-specific auto-recovery instance
        auto_recovery = get_auto_recovery_instance(company_id)
        if not auto_recovery:
            return create_error_response(f"Auto-recovery system not available for company: {company_id}", 500)
        
        logger.info(f"[{company_id}] Manual recovery initiated...")
        
        # Limpiar cache específico de empresa
        auto_recovery.health_cache = {"last_check": 0, "status": None}
        
        success = auto_recovery.reconstruct_index_from_stored_data()
        
        if success:
            return create_success_response({
                "company_id": company_id,
                "message": f"Index recovery completed successfully for {company_id}",
                "new_health": auto_recovery.verify_index_health()
            })
        else:
            return create_error_response(f"Index recovery failed for {company_id}", 500)
            
    except Exception as e:
        return create_error_response(str(e), 500)

@bp.route('/vectorstore/protection-status', methods=['GET'])
@handle_errors
def protection_status():
    """Get protection status - Multi-tenant"""
    try:
        company_id = _get_company_id_from_request()
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        from app.services.vector_auto_recovery import get_auto_recovery_instance
        
        auto_recovery = get_auto_recovery_instance(company_id)
        if not auto_recovery:
            return jsonify({
                "company_id": company_id,
                "auto_recovery_initialized": False,
                "vectorstore_healthy": False,
                "protection_active": False,
                "error": "Auto-recovery system not initialized"
            })
        
        status = auto_recovery.get_protection_status()
        
        return jsonify({
            **status,
            "company_id": company_id,
            "auto_recovery_initialized": True,
            "protection_active": True,
            "system_type": "multi-tenant-with-recovery"
        })
        
    except Exception as e:
        return create_error_response(str(e), 500)

@bp.route('/vectorstore/health', methods=['GET'])
@handle_errors
def vectorstore_health_check():
    """Vectorstore health check - Multi-tenant"""
    try:
        company_id = _get_company_id_from_request()
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        from app.services.vector_auto_recovery import get_auto_recovery_instance, get_health_recommendations
        
        auto_recovery = get_auto_recovery_instance(company_id)
        if not auto_recovery:
            return jsonify({
                "status": "error",
                "company_id": company_id,
                "message": f"Auto-recovery system not initialized for {company_id}"
            }), 500
        
        health = auto_recovery.verify_index_health()
        status_code = 200 if health.get("healthy", False) else 503
        
        return jsonify({
            "status": "healthy" if health.get("healthy") else "unhealthy",
            "company_id": company_id,
            "details": health,
            "auto_recovery_available": True,
            "auto_recovery_enabled": auto_recovery.auto_recovery_enabled,
            "recommendations": get_health_recommendations(health),
            "system_type": "multi-tenant-enhanced"
        }), status_code
        
    except Exception as e:
        return jsonify({
            "status": "error", 
            "company_id": company_id,
            "message": str(e)
        }), 500

@bp.route('/system/reset', methods=['POST'])
@handle_errors
@require_api_key
def reset_system():
    """Reset system caches - Multi-tenant Enhanced"""
    try:
        company_id = _get_company_id_from_request()
        reset_all = request.json.get('reset_all', False) if request.is_json else False
        
        redis_client = get_redis_client()
        cleared_count = 0
        
        if reset_all:
            # Reset ALL companies
            logger.info("Resetting ALL companies system caches")
            patterns = ["processed_message:*", "*:bot_status:*", "cache:*", "*:conversation:*"]
            
            for pattern in patterns:
                keys = redis_client.keys(pattern)
                if keys:
                    redis_client.delete(*keys)
                    cleared_count += len(keys)
        else:
            # Reset specific company
            company_manager = get_company_manager()
            if not company_manager.validate_company_id(company_id):
                return create_error_response(f"Invalid company_id: {company_id}", 400)
            
            config = company_manager.get_company_config(company_id)
            prefix = config.redis_prefix
            
            logger.info(f"[{company_id}] Resetting company-specific caches")
            
            # Company-specific patterns
            patterns = [
                f"processed_message:*",  # Global pero filtrable
                f"{prefix}bot_status:*",
                f"cache:*", 
                f"{prefix}conversation:*",
                f"{prefix}document:*"
            ]
            
            for pattern in patterns:
                keys = redis_client.keys(pattern)
                # Filter by company for global patterns
                if pattern.startswith("processed_message:"):
                    keys = [k for k in keys if company_id in (k.decode() if isinstance(k, bytes) else k)]
                
                if keys:
                    redis_client.delete(*keys)
                    cleared_count += len(keys)
        
        # Clear factory caches
        try:
            factory = get_multi_agent_factory()
            if reset_all:
                factory.clear_all_cache()
                logger.info("All factory caches cleared")
            else:
                factory.clear_company_cache(company_id)
                logger.info(f"[{company_id}] Company factory cache cleared")
        except Exception as e:
            logger.warning(f"Could not clear factory cache: {e}")
        
        # Clear auto-recovery cache
        try:
            from app.services.vector_auto_recovery import get_auto_recovery_instance
            
            if reset_all:
                # Clear all auto-recovery instances
                company_manager = get_company_manager()
                for cid in company_manager.get_all_companies().keys():
                    auto_recovery = get_auto_recovery_instance(cid)
                    if auto_recovery:
                        auto_recovery.health_cache = {"last_check": 0, "status": None}
                logger.info("All auto-recovery caches cleared")
            else:
                auto_recovery = get_auto_recovery_instance(company_id)
                if auto_recovery:
                    auto_recovery.health_cache = {"last_check": 0, "status": None}
                    logger.info(f"[{company_id}] Auto-recovery cache cleared")
        except Exception as e:
            logger.warning(f"Could not clear auto-recovery cache: {e}")
        
        scope = "ALL COMPANIES" if reset_all else company_id
        logger.info(f"System reset completed for {scope}, cleared {cleared_count} keys")
        
        return create_success_response({
            "message": f"System reset completed for {scope}",
            "company_id": company_id if not reset_all else "ALL",
            "keys_cleared": cleared_count,
            "timestamp": time.time(),
            "scope": "global" if reset_all else "company-specific"
        })
        
    except Exception as e:
        logger.error(f"System reset failed: {e}")
        return create_error_response("Failed to reset system", 500)

@bp.route('/status', methods=['GET'])
@handle_errors
def get_system_status():
    """Get comprehensive system status - Multi-tenant Enhanced"""
    try:
        company_id = request.args.get('company_id')  # Optional for this endpoint
        show_all = request.args.get('show_all', 'false').lower() == 'true'
        
        redis_client = get_redis_client()
        company_manager = get_company_manager()
        
        if show_all:
            # Status de todas las empresas
            companies_stats = {}
            total_conversations = 0
            total_documents = 0
            
            for cid, config in company_manager.get_all_companies().items():
                try:
                    prefix = config.redis_prefix
                    conv_count = len(redis_client.keys(f"{prefix}conversation:*"))
                    doc_count = len(redis_client.keys(f"{prefix}document:*"))
                    
                    companies_stats[cid] = {
                        "company_name": config.company_name,
                        "conversations": conv_count,
                        "documents": doc_count,
                        "vectorstore_index": config.vectorstore_index,
                        "services": config.services
                    }
                    
                    total_conversations += conv_count
                    total_documents += doc_count
                    
                except Exception as e:
                    companies_stats[cid] = {"error": str(e)}
            
            # Factory stats
            factory = get_multi_agent_factory()
            factory_stats = {
                "active_orchestrators": len(factory.get_all_companies()),
                "cached_vectorstore_services": len(factory._vectorstore_services) if hasattr(factory, '_vectorstore_services') else 0
            }
            
            return create_success_response({
                "timestamp": time.time(),
                "system_type": "multi-tenant-enhanced",
                "total_companies": len(company_manager.get_all_companies()),
                "total_statistics": {
                    "total_conversations": total_conversations,
                    "total_documents": total_documents
                },
                "companies": companies_stats,
                "factory": factory_stats,
                "environment": {
                    "model": current_app.config.get('MODEL_NAME', 'gpt-4o-mini'),
                    "embedding_model": current_app.config.get('EMBEDDING_MODEL', 'text-embedding-3-small')
                }
            })
        
        elif company_id:
            # Status de empresa específica
            if not company_manager.validate_company_id(company_id):
                return create_error_response(f"Invalid company_id: {company_id}", 400)
            
            config = company_manager.get_company_config(company_id)
            prefix = config.redis_prefix
            
            # Estadísticas específicas
            conversation_count = len(redis_client.keys(f"{prefix}conversation:*"))
            document_count = len(redis_client.keys(f"{prefix}document:*"))
            bot_status_keys = redis_client.keys(f"{prefix}bot_status:*")
            
            # Factory status
            factory = get_multi_agent_factory()
            orchestrator = factory.get_orchestrator(company_id)
            
            orchestrator_status = {}
            if orchestrator:
                health = orchestrator.health_check()
                orchestrator_status = {
                    "system_healthy": health.get("system_healthy", False),
                    "agents_available": list(health.get("agents_status", {}).keys()),
                    "vectorstore_connected": orchestrator.vectorstore_service is not None
                }
            
            return create_success_response({
                "timestamp": time.time(),
                "company_id": company_id,
                "company_name": config.company_name,
                "statistics": {
                    "conversations": conversation_count,
                    "documents": document_count,
                    "bot_statuses": len(bot_status_keys)
                },
                "orchestrator": orchestrator_status,
                "configuration": {
                    "services": config.services,
                    "vectorstore_index": config.vectorstore_index,
                    "schedule_service_url": getattr(config, 'schedule_service_url', 'Not configured')
                },
                "system_type": "multi-tenant-enhanced"
            })
        
        else:
            # Status general del sistema
            companies = company_manager.get_all_companies()
            
            return create_success_response({
                "timestamp": time.time(),
                "system_type": "multi-tenant-enhanced",
                "companies_configured": len(companies),
                "available_companies": list(companies.keys()),
                "message": "Use ?company_id=X for specific company status or ?show_all=true for all companies"
            })
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return create_error_response("Failed to get status", 500)

@bp.route('/companies/reload-config', methods=['POST'])
@handle_errors
@require_api_key
def reload_companies_config():
    """Reload companies configuration from file"""
    try:
        # Clear current config
        company_manager = get_company_manager()
        company_manager._configs.clear()
        
        # Reload from file
        company_manager._load_company_configs()
        
        # Clear factory caches to force recreation with new config
        factory = get_multi_agent_factory()
        factory.clear_all_cache()
        
        new_companies = company_manager.get_all_companies()
        
        logger.info(f"Companies configuration reloaded: {list(new_companies.keys())}")
        
        return create_success_response({
            "message": "Companies configuration reloaded successfully",
            "companies_loaded": len(new_companies),
            "companies": list(new_companies.keys()),
            "timestamp": time.time()
        })
        
    except Exception as e:
        logger.error(f"Failed to reload companies config: {e}")
        return create_error_response("Failed to reload companies configuration", 500)

@bp.route('/multimedia/test', methods=['POST'])
@handle_errors
def test_multimedia_integration():
    """Test multimedia integration - Multi-tenant aware"""
    try:
        company_id = _get_company_id_from_request()
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        from app.services.chatwoot_service import ChatwootService
        
        # Test multimedia methods with company context
        chatwoot_service = ChatwootService(company_id=company_id)
        
        # Check if multimedia methods exist
        has_transcribe = hasattr(chatwoot_service, 'transcribe_audio_from_url')
        has_analyze = hasattr(chatwoot_service, 'analyze_image_from_url')
        has_process_attachment = hasattr(chatwoot_service, 'process_attachment')
        
        return create_success_response({
            "company_id": company_id,
            "multimedia_integration": {
                "transcribe_audio_from_url": has_transcribe,
                "analyze_image_from_url": has_analyze,
                "process_attachment": has_process_attachment,
                "fully_integrated": has_transcribe and has_analyze and has_process_attachment
            },
            "openai_service_available": chatwoot_service.openai_service is not None,
            "voice_enabled": current_app.config.get('VOICE_ENABLED', False),
            "image_enabled": current_app.config.get('IMAGE_ENABLED', False),
            "company_specific_config": True
        })
        
    except Exception as e:
        return create_error_response(f"Failed to test multimedia integration: {e}", 500)

# ============================================================================
# ENDPOINTS ADICIONALES PARA FRONTEND REACT
# ============================================================================

@bp.route('/diagnostics', methods=['GET'])
@handle_errors
def run_system_diagnostics():
    """Ejecutar diagnósticos completos del sistema"""
    try:
        company_id = _get_company_id_from_request()
        
        # Validar empresa si se especifica
        company_manager = get_company_manager()
        if company_id != 'benova' and not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        diagnostics = {
            "timestamp": time.time(),
            "company_id": company_id,
            "system_diagnostics": {
                "redis_connection": False,
                "openai_service": False,
                "company_manager": False,
                "multi_agent_factory": False
            }
        }
        
        # Test Redis connection
        try:
            redis_client = get_redis_client()
            redis_client.ping()
            diagnostics["system_diagnostics"]["redis_connection"] = True
        except Exception as e:
            diagnostics["redis_error"] = str(e)
        
        # Test Company Manager
        try:
            companies = company_manager.get_all_companies()
            diagnostics["system_diagnostics"]["company_manager"] = True
            diagnostics["companies_available"] = list(companies.keys())
        except Exception as e:
            diagnostics["company_manager_error"] = str(e)
        
        # Test Multi-Agent Factory
        try:
            factory = get_multi_agent_factory()
            orchestrator = factory.get_orchestrator(company_id)
            diagnostics["system_diagnostics"]["multi_agent_factory"] = True
            diagnostics["orchestrator_available"] = orchestrator is not None
        except Exception as e:
            diagnostics["factory_error"] = str(e)
        
        # Test OpenAI (si está disponible)
        try:
            from app.services.openai_service import OpenAIService
            openai_service = OpenAIService()
            diagnostics["system_diagnostics"]["openai_service"] = True
            diagnostics["openai_model"] = current_app.config.get('MODEL_NAME', 'Unknown')
        except Exception as e:
            diagnostics["openai_error"] = str(e)
        
        # Calcular score general
        total_tests = len(diagnostics["system_diagnostics"])
        passed_tests = sum(diagnostics["system_diagnostics"].values())
        diagnostics["health_score"] = (passed_tests / total_tests) * 100
        
        return create_success_response(diagnostics)
        
    except Exception as e:
        logger.error(f"System diagnostics failed: {e}")
        return create_error_response(f"Failed to run diagnostics: {e}", 500)

@bp.route('/export/configuration', methods=['GET'])
@handle_errors
def export_system_configuration():
    """Exportar configuración completa del sistema"""
    try:
        company_id = request.args.get('company_id')
        export_all = request.args.get('export_all', 'false').lower() == 'true'
        
        company_manager = get_company_manager()
        
        if export_all:
            # Exportar todas las empresas
            companies_data = company_manager.get_all_companies()
            export_data = {
                "export_type": "full_system",
                "timestamp": time.time(),
                "companies": {}
            }
            
            for cid, config in companies_data.items():
                export_data["companies"][cid] = {
                    "company_name": config.company_name,
                    "business_type": getattr(config, 'business_type', 'Unknown'),
                    "services": config.services,
                    "agents": getattr(config, 'agents', []),
                    "vectorstore_index": config.vectorstore_index
                }
                
        elif company_id:
            # Exportar empresa específica
            if not company_manager.validate_company_id(company_id):
                return create_error_response(f"Invalid company_id: {company_id}", 400)
            
            config = company_manager.get_company_config(company_id)
            export_data = {
                "export_type": "single_company",
                "timestamp": time.time(),
                "company_id": company_id,
                "configuration": {
                    "company_name": config.company_name,
                    "business_type": getattr(config, 'business_type', 'Unknown'),
                    "services": config.services,
                    "agents": getattr(config, 'agents', []),
                    "vectorstore_index": config.vectorstore_index,
                    "redis_prefix": config.redis_prefix
                }
            }
        else:
            return create_error_response("company_id required or use export_all=true", 400)
        
        return create_success_response(export_data)
        
    except Exception as e:
        logger.error(f"Configuration export failed: {e}")
        return create_error_response(f"Failed to export configuration: {e}", 500)


# ============================================================================
# ENDPOINTS PARA GESTIÓN DE PROMPTS PERSONALIZADOS - VERSIÓN CORREGIDA
# ============================================================================

@bp.route('/prompts', methods=['GET'])
@handle_errors
def get_prompts():
    """Obtener prompts actuales de los agentes para una empresa"""
    try:
        company_id = _get_company_id_from_request()
        
        if not company_id:
            logger.error("No company_id provided in request")
            return create_error_response("company_id is required", 400)
        
        logger.info(f"Getting prompts for company: {company_id}")
        
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        # Obtener factory y agentes
        factory = get_multi_agent_factory()
        orchestrator = factory.get_orchestrator(company_id)
        
        if not orchestrator:
            logger.error(f"Orchestrator not available for {company_id}")
            return create_error_response(f"Orchestrator not available for {company_id}", 503)
        
        prompts_data = {}
        agents_to_check = ['router_agent', 'sales_agent', 'support_agent', 'emergency_agent', 'schedule_agent']
        
        # Cargar prompts por defecto desde custom_prompts.json si existe
        default_prompts = _load_default_prompts(company_id)
        
        for agent_key in agents_to_check:
            # Mapear nombres correctamente
            agent_name = agent_key.replace('_agent', '')  # router_agent -> router
            
            # Intentar obtener el agente desde orchestrator.agents
            agent_instance = None
            if hasattr(orchestrator, 'agents') and agent_name in orchestrator.agents:
                agent_instance = orchestrator.agents[agent_name]
            
            if agent_instance:
                try:
                    # Intentar obtener el prompt actual del agente
                    if hasattr(agent_instance, 'prompt_template') and agent_instance.prompt_template:
                        if hasattr(agent_instance.prompt_template, 'messages'):
                            current_prompt = str(agent_instance.prompt_template.messages[0].prompt.template)
                        else:
                            current_prompt = str(agent_instance.prompt_template)
                    else:
                        # Si no hay prompt en el agente, usar el default
                        current_prompt = default_prompts.get(agent_key, f"Default prompt for {agent_key}")
                    
                    prompts_data[agent_key] = {
                        "current_prompt": current_prompt,
                        "is_custom": _has_custom_prompt(company_id, agent_key),
                        "last_modified": _get_prompt_modification_date(company_id, agent_key)
                    }
                    logger.debug(f"Loaded prompt for {agent_key}")
                    
                except Exception as e:
                    logger.warning(f"Error getting prompt for {agent_key}: {e}")
                    # Usar prompt por defecto si hay error
                    prompts_data[agent_key] = {
                        "current_prompt": default_prompts.get(agent_key, f"Default prompt for {agent_key}"),
                        "is_custom": False,
                        "last_modified": None
                    }
            else:
                # Si el agente no existe, proporcionar prompt por defecto
                prompts_data[agent_key] = {
                    "current_prompt": default_prompts.get(agent_key, f"Default prompt for {agent_key}"),
                    "is_custom": False,
                    "last_modified": None
                }
        
        logger.info(f"Successfully loaded {len(prompts_data)} prompts for {company_id}")
        
        return create_success_response({
            "company_id": company_id,
            "agents": prompts_data
        })
        
    except Exception as e:
        logger.error(f"Error getting prompts: {e}", exc_info=True)
        return create_error_response(f"Failed to get prompts: {str(e)}", 500)

@bp.route('/prompts/<agent_name>', methods=['PUT'])
@handle_errors
def update_agent_prompt(agent_name):
    """Actualizar prompt de un agente específico"""
    try:
        # CORRECCIÓN: Manejar el body correctamente
        raw_data = request.get_data(as_text=True)
        logger.debug(f"Raw data received: {raw_data[:200]}")  # Log para debug
        
        # Intentar parsear JSON
        try:
            if raw_data:
                import json
                data = json.loads(raw_data)
            else:
                data = request.get_json(force=True)
        except json.JSONDecodeError as je:
            logger.error(f"JSON decode error: {je}")
            return create_error_response("Invalid JSON format", 400)
        
        if not isinstance(data, dict):
            return create_error_response("Request body must be a JSON object", 400)
            
        company_id = data.get('company_id') or _get_company_id_from_request()
        prompt_template = data.get('prompt_template')
        modified_by = data.get('modified_by', 'admin')
        
        if not company_id:
            return create_error_response("company_id is required", 400)
            
        if not prompt_template:
            return create_error_response("prompt_template is required", 400)
        
        logger.info(f"Updating prompt for {agent_name} in company {company_id}")
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        # Guardar prompt personalizado
        success = _save_custom_prompt(company_id, agent_name, prompt_template, modified_by)
        
        if not success:
            return create_error_response("Failed to save custom prompt", 500)
        
        # Limpiar cache para forzar recreación
        factory = get_multi_agent_factory()
        factory.clear_company_cache(company_id)
        
        logger.info(f"Prompt updated successfully for {agent_name} in {company_id}")
        
        return create_success_response({
            "message": f"Prompt updated successfully for {agent_name}",
            "company_id": company_id,
            "agent_name": agent_name,
            "updated_at": time.time()
        })
        
    except Exception as e:
        logger.error(f"Error updating prompt: {e}", exc_info=True)
        return create_error_response(f"Failed to update prompt: {str(e)}", 500)

@bp.route('/prompts/<agent_name>', methods=['DELETE'])
@handle_errors
def reset_agent_prompt(agent_name):
    """Restaurar prompt por defecto de un agente"""
    try:
        company_id = _get_company_id_from_request()
        
        if not company_id:
            logger.error("No company_id provided for reset")
            return create_error_response("company_id is required", 400)
        
        logger.info(f"Resetting prompt for {agent_name} in company {company_id}")
        
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        # Eliminar prompt personalizado
        result = _delete_custom_prompt(company_id, agent_name)
        
        if result:
            # En lugar de reset_orchestrator, usar clear_company_cache
            factory = get_multi_agent_factory()
            factory.clear_company_cache(company_id)
            
            logger.info(f"Successfully reset prompt for {agent_name} in {company_id}")
            
            return create_success_response({
                "message": f"Prompt restored to default for {agent_name}",
                "company_id": company_id,
                "agent_name": agent_name
            })
        else:
            return create_error_response(f"Failed to reset prompt for {agent_name}", 500)
        
    except Exception as e:
        logger.error(f"Error resetting prompt: {e}", exc_info=True)
        return create_error_response(f"Failed to reset prompt: {str(e)}", 500)

@bp.route('/prompts/preview', methods=['POST'])
@handle_errors
def preview_prompt():
    """Vista previa de un prompt con mensaje de prueba"""
    try:
        # CORRECCIÓN: Manejar el body correctamente
        raw_data = request.get_data(as_text=True)
        logger.debug(f"Preview raw data: {raw_data[:200]}")  # Log para debug
        
        # Intentar parsear JSON
        try:
            if raw_data:
                import json
                data = json.loads(raw_data)
            else:
                data = request.get_json(force=True)
        except json.JSONDecodeError as je:
            logger.error(f"JSON decode error in preview: {je}")
            return create_error_response("Invalid JSON format", 400)
        
        if not isinstance(data, dict):
            return create_error_response("Request body must be a JSON object", 400)
        
        # Obtener parámetros con validación
        company_id = data.get('company_id')
        agent_name = data.get('agent_name')
        prompt_template = data.get('prompt_template')
        test_message = data.get('test_message', '¿Cuánto cuesta un tratamiento?')
        
        # Validaciones estrictas
        if not company_id or not company_id.strip():
            logger.error("Missing or empty company_id in preview request")
            return create_error_response("company_id is required and cannot be empty", 400)
            
        if not agent_name or not agent_name.strip():
            logger.error("Missing or empty agent_name in preview request")
            return create_error_response("agent_name is required and cannot be empty", 400)
            
        if not prompt_template or not prompt_template.strip():
            logger.error("Missing or empty prompt_template in preview request")
            return create_error_response("prompt_template is required and cannot be empty", 400)
        
        logger.info(f"Preview request for {agent_name} in {company_id}")
        
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        # Crear instancia temporal del agente con el nuevo prompt
        config = company_manager.get_company_config(company_id)
        openai_service = OpenAIService()
        
        # Simular respuesta (sin guardar cambios)
        try:
            preview_result = _simulate_agent_response(
                agent_name=agent_name,
                company_config=config,
                custom_prompt=prompt_template,
                test_message=test_message,
                openai_service=openai_service
            )
            
            logger.info(f"Preview generated successfully for {agent_name}")
            
        except Exception as sim_error:
            logger.error(f"Error simulating response: {sim_error}", exc_info=True)
            preview_result = f"Error generando preview: {str(sim_error)}"
        
        return create_success_response({
            "company_id": company_id,
            "agent_name": agent_name,
            "test_message": test_message,
            "preview_response": preview_result,
            "prompt_preview": prompt_template[:200] + "..." if len(prompt_template) > 200 else prompt_template
        })
        
    except Exception as e:
        logger.error(f"Error previewing prompt: {e}", exc_info=True)
        return create_error_response(f"Failed to preview prompt: {str(e)}", 500)
        
# ============================================================================
# FUNCIONES AUXILIARES PARA GESTIÓN DE PROMPTS
# ============================================================================

def _has_custom_prompt(company_id: str, agent_name: str) -> bool:
    """Verificar si un agente tiene prompt personalizado"""
    try:
        custom_prompts_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            'custom_prompts.json'
        )
        
        if not os.path.exists(custom_prompts_file):
            return False
        
        with open(custom_prompts_file, 'r', encoding='utf-8') as f:
            custom_prompts = json.load(f)
        
        company_prompts = custom_prompts.get(company_id, {})
        agent_data = company_prompts.get(agent_name, {})
        
        return agent_data.get('is_custom', False)
        
    except Exception as e:
        logger.warning(f"Error checking custom prompt: {e}")
        return False

def _get_prompt_modification_date(company_id: str, agent_name: str) -> Optional[str]:
    """Obtener fecha de modificación del prompt"""
    try:
        custom_prompts_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            'custom_prompts.json'
        )
        
        if not os.path.exists(custom_prompts_file):
            return None
        
        with open(custom_prompts_file, 'r', encoding='utf-8') as f:
            custom_prompts = json.load(f)
        
        company_prompts = custom_prompts.get(company_id, {})
        agent_data = company_prompts.get(agent_name, {})
        
        return agent_data.get('modified_at')
        
    except Exception as e:
        logger.warning(f"Error getting modification date: {e}")
        return None

def _save_custom_prompt(company_id: str, agent_name: str, prompt_template: str, modified_by: str = "admin") -> bool:
    """Guardar prompt personalizado"""
    try:
        custom_prompts_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            'custom_prompts.json'
        )
        
        # Cargar prompts existentes o crear estructura vacía
        if os.path.exists(custom_prompts_file):
            with open(custom_prompts_file, 'r', encoding='utf-8') as f:
                custom_prompts = json.load(f)
        else:
            custom_prompts = {}
        
        # Asegurar que existe la estructura para la empresa
        if company_id not in custom_prompts:
            custom_prompts[company_id] = {}
        
        # Asegurar que existe la estructura para el agente
        if agent_name not in custom_prompts[company_id]:
            custom_prompts[company_id][agent_name] = {
                "template": None,
                "is_custom": False,
                "modified_at": None,
                "modified_by": None,
                "default_template": None
            }
        
        # Actualizar con el nuevo prompt personalizado
        custom_prompts[company_id][agent_name].update({
            "template": prompt_template,
            "is_custom": True,
            "modified_at": datetime.utcnow().isoformat() + "Z",
            "modified_by": modified_by
        })
        
        # Guardar archivo actualizado
        with open(custom_prompts_file, 'w', encoding='utf-8') as f:
            json.dump(custom_prompts, f, indent=2, ensure_ascii=False)
        
        logger.info(f"[{company_id}] Custom prompt saved for {agent_name}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving custom prompt: {e}")
        return False


def _delete_custom_prompt(company_id: str, agent_name: str) -> bool:
    """Eliminar prompt personalizado y restaurar al default"""
    try:
        custom_prompts_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            'custom_prompts.json'
        )
        
        if not os.path.exists(custom_prompts_file):
            return True  # No hay archivo, consideramos exitoso
        
        # Cargar prompts existentes
        with open(custom_prompts_file, 'r', encoding='utf-8') as f:
            custom_prompts = json.load(f)
        
        # Verificar si existe la empresa y el agente
        if company_id in custom_prompts and agent_name in custom_prompts[company_id]:
            # Restaurar a valores por defecto
            custom_prompts[company_id][agent_name].update({
                "template": None,
                "is_custom": False,
                "modified_at": datetime.utcnow().isoformat() + "Z",
                "modified_by": "system_reset"
            })
            
            # Guardar archivo actualizado
            with open(custom_prompts_file, 'w', encoding='utf-8') as f:
                json.dump(custom_prompts, f, indent=2, ensure_ascii=False)
            
            logger.info(f"[{company_id}] Custom prompt deleted for {agent_name}, restored to default")
            return True
        else:
            # No había prompt personalizado, no hay nada que eliminar
            logger.info(f"[{company_id}] No custom prompt found for {agent_name}")
            return True
        
    except Exception as e:
        logger.error(f"Error deleting custom prompt: {e}")
        return False
def _remove_custom_prompt(company_id: str, agent_name: str) -> bool:
    """Remover prompt personalizado (volver a default)"""
    try:
        custom_prompts_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            'custom_prompts.json'
        )
        
        if not os.path.exists(custom_prompts_file):
            return True  # No hay archivo, ya está "limpio"
        
        # Cargar prompts
        with open(custom_prompts_file, 'r', encoding='utf-8') as f:
            custom_prompts = json.load(f)
        
        # Limpiar prompt personalizado
        if (company_id in custom_prompts and 
            agent_name in custom_prompts[company_id]):
            custom_prompts[company_id][agent_name].update({
                "template": None,
                "is_custom": False,
                "modified_at": datetime.utcnow().isoformat() + "Z",
                "modified_by": "system_reset"
            })
        
        # Guardar archivo actualizado
        with open(custom_prompts_file, 'w', encoding='utf-8') as f:
            json.dump(custom_prompts, f, indent=2, ensure_ascii=False)
        
        logger.info(f"[{company_id}] Custom prompt removed for {agent_name}")
        return True
        
    except Exception as e:
        logger.error(f"Error removing custom prompt: {e}")
        return False

def _simulate_agent_response(agent_name: str, company_config, custom_prompt: str, 
                           test_message: str, openai_service) -> str:
    """Simular respuesta de agente con prompt personalizado (sin guardar)"""
    try:
        from langchain.prompts import ChatPromptTemplate
        from langchain.schema.output_parser import StrOutputParser
        
        # Crear template temporal con el prompt personalizado
        if '{chat_history}' in custom_prompt:
            template = ChatPromptTemplate.from_messages([
                ("system", custom_prompt),
                ("human", "{question}")
            ])
        else:
            template = ChatPromptTemplate.from_messages([
                ("system", custom_prompt),
                ("human", "{question}")
            ])
        
        # Crear cadena temporal
        chat_model = openai_service.get_chat_model()
        chain = template | chat_model | StrOutputParser()
        
        # Inputs con contexto de empresa
        inputs = {
            "question": test_message,
            "company_name": company_config.company_name,
            "services": company_config.services,
            "agent_name": getattr(company_config, 'sales_agent_name', 'Asistente'),
            "company_id": company_config.company_id,
            "context": "Esta es una vista previa del prompt personalizado.",
            "chat_history": []
        }
        
        # Ejecutar y retornar respuesta
        response = chain.invoke(inputs)
        return response
        
    except Exception as e:
        logger.error(f"Error simulating agent response: {e}")
        return f"Error en la simulación: {str(e)}"


def _load_default_prompts(company_id: str) -> dict:
    """Cargar prompts por defecto desde custom_prompts.json"""
    try:
        custom_prompts_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            'custom_prompts.json'
        )
        
        if not os.path.exists(custom_prompts_file):
            logger.warning(f"custom_prompts.json not found")
            return {}
        
        with open(custom_prompts_file, 'r', encoding='utf-8') as f:
            custom_prompts = json.load(f)
        
        company_prompts = custom_prompts.get(company_id, {})
        default_prompts = {}
        
        for agent_name, agent_data in company_prompts.items():
            if isinstance(agent_data, dict):
                # Usar el template personalizado si existe, sino el default
                template = agent_data.get('template')
                if not template or template == "null" or template == None:
                    template = agent_data.get('default_template', f"Default prompt for {agent_name}")
                default_prompts[agent_name] = template
        
        return default_prompts
        
    except Exception as e:
        logger.error(f"Error loading default prompts: {e}")
        return {}


# ============================================================================
# FUNCIONES DE VALIDACIÓN
# ============================================================================

def validate_company_id(company_id: str) -> bool:
    """Validar company_id"""
    if not company_id or not isinstance(company_id, str):
        return False
    
    # Validar que existe en la configuración
    company_manager = get_company_manager()
    return company_manager.validate_company_id(company_id)

def validate_agent_name(agent_name: str) -> bool:
    """Validar agent_name"""
    if not agent_name or not isinstance(agent_name, str):
        return False
    
    # Lista de agentes válidos
    valid_agents = [
        'router_agent', 'sales_agent', 'support_agent', 
        'emergency_agent', 'schedule_agent', 'availability_agent'
    ]
    
    return agent_name in valid_agents


# ============================================================================
# NUEVOS ENDPOINTS PARA GESTIÓN DE PROMPTS CON POSTGRESQL
# ============================================================================

@bp.route('/prompts/<company_id>', methods=['GET'])
@handle_errors
def get_company_prompts(company_id: str):
    """Obtener todos los prompts de una empresa"""
    try:
        # Validar entrada
        if not validate_company_id(company_id):
            return create_error_response("Invalid company ID", 400)
        
        # Obtener prompts del servicio PostgreSQL
        prompt_service = get_prompt_service()
        prompts = prompt_service.get_company_prompts(company_id)
        
        # Formatear respuesta para mantener compatibilidad
        formatted_prompts = []
        for prompt in prompts:
            agent_data = {
                "agent_name": prompt['agent_name'],
                "template": prompt['template'],
                "is_custom": prompt['is_custom'],
                "version": prompt.get('version', 1),
                "modified_at": prompt.get('modified_at'),
                "modified_by": prompt.get('modified_by'),
                "has_custom": prompt['is_custom']
            }
            formatted_prompts.append(agent_data)
        
        return create_success_response({
            "company_id": company_id,
            "prompts": formatted_prompts,
            "total_agents": len(formatted_prompts),
            "custom_count": sum(1 for p in formatted_prompts if p['is_custom'])
        })
        
    except Exception as e:
        logger.error(f"Error getting company prompts: {e}", exc_info=True)
        return create_error_response(f"Failed to get prompts: {str(e)}", 500)

@bp.route('/prompts/<company_id>/<agent_name>', methods=['GET'])
@handle_errors
def get_agent_prompt(company_id: str, agent_name: str):
    """Obtener prompt específico de un agente"""
    try:
        # Validar entrada
        if not validate_company_id(company_id) or not validate_agent_name(agent_name):
            return create_error_response("Invalid company ID or agent name", 400)
        
        # Obtener prompt del servicio PostgreSQL
        prompt_service = get_prompt_service()
        prompt_data = prompt_service.get_prompt(company_id, agent_name)
        
        # Formatear respuesta
        response_data = {
            "company_id": company_id,
            "agent_name": agent_name,
            "template": prompt_data['template'],
            "is_custom": prompt_data['is_custom'],
            "version": prompt_data.get('version', 1),
            "modified_at": prompt_data.get('modified_at'),
            "modified_by": prompt_data.get('modified_by'),
            "has_custom": prompt_data['is_custom']
        }
        
        return create_success_response(response_data)
        
    except Exception as e:
        logger.error(f"Error getting agent prompt: {e}", exc_info=True)
        return create_error_response(f"Failed to get prompt: {str(e)}", 500)

@bp.route('/prompts/<company_id>/<agent_name>', methods=['POST'])
@handle_errors
def save_agent_prompt(company_id: str, agent_name: str):
    """Guardar prompt personalizado para un agente"""
    try:
        # Validar entrada
        if not validate_company_id(company_id) or not validate_agent_name(agent_name):
            return create_error_response("Invalid company ID or agent name", 400)
        
        # Obtener datos del request
        data = request.get_json()
        if not data or 'template' not in data:
            return create_error_response("Missing template in request body", 400)
        
        template = data['template'].strip()
        if not template:
            return create_error_response("Template cannot be empty", 400)
        
        modified_by = data.get('modified_by', 'admin')
        
        # Guardar prompt en PostgreSQL
        prompt_service = get_prompt_service()
        success = prompt_service.save_custom_prompt(
            company_id, agent_name, template, modified_by
        )
        
        if success:
            # Obtener datos actualizados
            updated_prompt = prompt_service.get_prompt(company_id, agent_name)
            
            return create_success_response({
                "message": "Prompt saved successfully",
                "company_id": company_id,
                "agent_name": agent_name,
                "version": updated_prompt.get('version', 1),
                "modified_at": updated_prompt.get('modified_at'),
                "modified_by": modified_by
            })
        else:
            return create_error_response("Failed to save prompt", 500)
        
    except Exception as e:
        logger.error(f"Error saving agent prompt: {e}", exc_info=True)
        return create_error_response(f"Failed to save prompt: {str(e)}", 500)

@bp.route('/prompts/<company_id>/<agent_name>', methods=['DELETE'])
@handle_errors
def delete_agent_prompt(company_id: str, agent_name: str):
    """Eliminar prompt personalizado (restaurar a default)"""
    try:
        # Validar entrada
        if not validate_company_id(company_id) or not validate_agent_name(agent_name):
            return create_error_response("Invalid company ID or agent name", 400)
        
        # Eliminar prompt personalizado de PostgreSQL
        prompt_service = get_prompt_service()
        success = prompt_service.delete_custom_prompt(company_id, agent_name)
        
        if success:
            return create_success_response({
                "message": "Custom prompt deleted, restored to default",
                "company_id": company_id,
                "agent_name": agent_name,
                "restored_at": prompt_service.get_modification_date(company_id, agent_name)
            })
        else:
            return create_error_response("Failed to delete prompt", 500)
        
    except Exception as e:
        logger.error(f"Error deleting agent prompt: {e}", exc_info=True)
        return create_error_response(f"Failed to delete prompt: {str(e)}", 500)

@bp.route('/prompts/<company_id>/<agent_name>/preview', methods=['POST'])
@handle_errors
def preview_prompt(company_id: str, agent_name: str):
    """Vista previa de prompt con variables de prueba"""
    try:
        # Validar entrada
        if not validate_company_id(company_id) or not validate_agent_name(agent_name):
            return create_error_response("Invalid company ID or agent name", 400)
        
        # Obtener template del request
        data = request.get_json()
        if not data or 'template' not in data:
            return create_error_response("Missing template in request body", 400)
        
        template = data['template']
        test_vars = data.get('variables', {})
        
        # Obtener configuración de la empresa para variables reales
        company_manager = get_company_manager()
        company_config = company_manager.get_company_config(company_id)
        
        # Variables de prueba basadas en la empresa real
        default_vars = {
            'company_name': company_config.company_name if company_config else 'Empresa de Prueba',
            'phone': company_config.phone if company_config else '+1234567890',
            'email': company_config.email if company_config else 'contacto@empresa.com',
            'address': company_config.address if company_config else 'Dirección de Prueba 123',
            'question': '¿Cuáles son sus servicios?',
            'chat_history': 'Usuario: Hola\nAsistente: ¡Hola! ¿En qué puedo ayudarte?',
            'services': company_config.services if company_config else 'servicios de belleza'
        }
        
        # Combinar variables por defecto con las proporcionadas
        preview_vars = {**default_vars, **test_vars}
        
        # Aplicar variables al template
        try:
            preview_text = template.format(**preview_vars)
        except KeyError as e:
            return create_error_response(f"Missing variable in template: {e}", 400)
        except Exception as e:
            return create_error_response(f"Template formatting error: {e}", 400)
        
        return create_success_response({
            "preview": preview_text,
            "variables_used": list(preview_vars.keys()),
            "template_length": len(template),
            "preview_length": len(preview_text),
            "template_preview": template[:200] + "..." if len(template) > 200 else template
        })
        
    except Exception as e:
        logger.error(f"Error previewing prompt: {e}", exc_info=True)
        return create_error_response(f"Failed to preview prompt: {str(e)}", 500)

@bp.route('/prompts/<company_id>/<agent_name>/history', methods=['GET'])
@handle_errors  
def get_prompt_history(company_id: str, agent_name: str):
    """Obtener historial de versiones de un prompt"""
    try:
        # Validar entrada
        if not validate_company_id(company_id) or not validate_agent_name(agent_name):
            return create_error_response("Invalid company ID or agent name", 400)
        
        # Obtener historial de PostgreSQL
        prompt_service = get_prompt_service()
        history = prompt_service.get_prompt_history(company_id, agent_name)
        
        return create_success_response({
            "company_id": company_id,
            "agent_name": agent_name,
            "history": history,
            "total_versions": len(history)
        })
        
    except Exception as e:
        logger.error(f"Error getting prompt history: {e}", exc_info=True)
        return create_error_response(f"Failed to get history: {str(e)}", 500)

@bp.route('/prompts/<company_id>/<agent_name>/restore/<int:version>', methods=['POST'])
@handle_errors
def restore_prompt_version(company_id: str, agent_name: str, version: int):
    """Restaurar una versión específica del prompt"""
    try:
        # Validar entrada
        if not validate_company_id(company_id) or not validate_agent_name(agent_name):
            return create_error_response("Invalid company ID or agent name", 400)
        
        if version < 1:
            return create_error_response("Invalid version number", 400)
        
        # Obtener usuario que solicita la restauración
        data = request.get_json() or {}
        modified_by = data.get('modified_by', 'admin')
        
        # Restaurar versión en PostgreSQL
        prompt_service = get_prompt_service()
        success = prompt_service.restore_prompt_version(
            company_id, agent_name, version, modified_by
        )
        
        if success:
            # Obtener datos actualizados
            updated_prompt = prompt_service.get_prompt(company_id, agent_name)
            
            return create_success_response({
                "message": f"Prompt restored to version {version}",
                "company_id": company_id,
                "agent_name": agent_name,
                "restored_version": version,
                "new_version": updated_prompt.get('version', 1),
                "modified_at": updated_prompt.get('modified_at'),
                "modified_by": modified_by
            })
        else:
            return create_error_response(f"Failed to restore version {version}", 500)
        
    except Exception as e:
        logger.error(f"Error restoring prompt version: {e}", exc_info=True)
        return create_error_response(f"Failed to restore version: {str(e)}", 500)

# ============================================================================
# ENDPOINTS DE ESTADÍSTICAS Y ADMINISTRACIÓN
# ============================================================================

@bp.route('/prompts/stats', methods=['GET'])
@handle_errors
def get_prompt_stats():
    """Obtener estadísticas generales de prompts"""
    try:
        prompt_service = get_prompt_service()
        
        # Obtener estadísticas básicas
        company_manager = get_company_manager()
        all_companies = company_manager.get_all_companies()
        
        total_custom = 0
        company_stats = []
        
        for company_id in all_companies.keys():
            prompts = prompt_service.get_company_prompts(company_id)
            custom_count = sum(1 for p in prompts if p['is_custom'])
            total_custom += custom_count
            
            if custom_count > 0:
                company_stats.append({
                    "company_id": company_id,
                    "custom_prompts": custom_count,
                    "total_prompts": len(prompts)
                })
        
        return create_success_response({
            "total_companies": len(all_companies),
            "total_custom_prompts": total_custom,
            "companies_with_custom": len(company_stats),
            "company_breakdown": company_stats
        })
        
    except Exception as e:
        logger.error(f"Error getting prompt stats: {e}", exc_info=True)
        return create_error_response(f"Failed to get stats: {str(e)}", 500)

@bp.route('/prompts/health', methods=['GET'])
@handle_errors
def prompt_service_health():
    """Verificar estado del servicio de prompts"""
    try:
        prompt_service = get_prompt_service()
        
        # Intentar una consulta simple para verificar conectividad
        test_result = prompt_service.get_prompt("test", "test_agent")
        
        return create_success_response({
            "status": "healthy",
            "service": "prompt_service",
            "database": "postgresql",
            "test_query": "success",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    except Exception as e:
        logger.error(f"Prompt service health check failed: {e}")
        return create_error_response(f"Service unhealthy: {str(e)}", 503)


