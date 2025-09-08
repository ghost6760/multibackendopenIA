# app/routes/admin.py - Endpoints administrativos integrados

from flask import Blueprint, request, jsonify, current_app
from app.services.multi_agent_factory import get_multi_agent_factory
from app.services.redis_service import get_redis_client
from app.config.company_config import get_company_manager
from app.utils.decorators import handle_errors, require_api_key
from app.utils.helpers import create_success_response, create_error_response
from app.services.prompt_redis_manager import get_prompt_redis_manager
from app.services.openai_service import OpenAIService
from app.services.prompt_manager import PromptManager
from typing import Optional
import logging
import time

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
# ENDPOINTS PARA GESTIÓN DE PROMPTS PERSONALIZADOS - CON REDIS
# ============================================================================

@bp.route('/prompts', methods=['GET'])
@handle_errors
def get_prompts():
    """Obtener prompts actuales de los agentes para una empresa desde Redis"""
    try:
        company_id = _get_company_id_from_request()
        
        if not company_id:
            logger.error("No company_id provided in request")
            return create_error_response("company_id is required", 400)
        
        logger.info(f"Getting prompts for company: {company_id}")
        
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        # 🆕 Usar el manager de Redis
        prompt_manager = get_prompt_redis_manager()
        
        # Obtener factory y agentes
        factory = get_multi_agent_factory()
        orchestrator = factory.get_orchestrator(company_id)
        
        if not orchestrator:
            logger.error(f"Orchestrator not available for {company_id}")
            return create_error_response(f"Orchestrator not available for {company_id}", 503)
        
        prompts_data = {}
        agents_to_check = ['router_agent', 'sales_agent', 'support_agent', 'emergency_agent', 'schedule_agent']
        
        # 🆕 Obtener todos los prompts desde Redis
        all_prompts = prompt_manager.get_all_prompts(company_id)
        
        for agent_name in agents_to_check:
            try:
                agent = getattr(orchestrator, agent_name, None)
                if agent:
                    # Obtener prompt actual (personalizado o default)
                    current_prompt = agent.get_current_prompt_template() if hasattr(agent, 'get_current_prompt_template') else None
                    
                    # Obtener información del prompt desde Redis
                    prompt_info = all_prompts.get(agent_name, {})
                    
                    prompts_data[agent_name] = {
                        "current": current_prompt or prompt_info.get('template') or prompt_info.get('default_template') or "Prompt no configurado",
                        "is_custom": prompt_info.get('is_custom', False),
                        "modified_at": prompt_info.get('modified_at'),
                        "modified_by": prompt_info.get('modified_by')
                    }
                else:
                    # Si el agente no existe, usar info de Redis
                    prompt_info = all_prompts.get(agent_name, {})
                    prompts_data[agent_name] = {
                        "current": prompt_info.get('template') or prompt_info.get('default_template') or f"Default prompt for {agent_name}",
                        "is_custom": prompt_info.get('is_custom', False),
                        "modified_at": prompt_info.get('modified_at'),
                        "modified_by": prompt_info.get('modified_by')
                    }
                    
            except Exception as e:
                logger.warning(f"Error getting prompt for {agent_name}: {e}")
                prompts_data[agent_name] = {
                    "current": f"Error loading prompt for {agent_name}",
                    "is_custom": False,
                    "error": str(e)
                }
        
        return create_success_response({
            "company_id": company_id,
            "agents": prompts_data,  # ✅ Compatible con frontend
            "source": "redis_with_fallback"
        })
        
    except Exception as e:
        logger.error(f"Error getting prompts: {e}", exc_info=True)
        return create_error_response(f"Failed to get prompts: {str(e)}", 500)


@bp.route('/prompts/<agent_name>', methods=['PUT'])
@handle_errors
def update_prompt(agent_name: str):
    """Actualizar prompt de un agente específico en Redis"""
    try:
        data = request.get_json()
        company_id = data.get('company_id') or _get_company_id_from_request()
        prompt_template = data.get('prompt_template')
        
        if not company_id:
            return create_error_response("company_id is required", 400)
        
        if not prompt_template:
            return create_error_response("prompt_template is required", 400)
        
        logger.info(f"Updating prompt for {agent_name} in company {company_id}")
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        # 🆕 Usar el manager de Redis para guardar
        prompt_manager = get_prompt_redis_manager()
        success = prompt_manager.save_custom_prompt(
            company_id,
            agent_name,
            prompt_template,
            modified_by=request.headers.get('X-User-ID', 'admin')
        )
        
        if not success:
            return create_error_response(f"Failed to update prompt for {agent_name}", 500)
        
        # Actualizar el agente en memoria si está activo
        factory = get_multi_agent_factory()
        orchestrator = factory.get_orchestrator(company_id)
        
        if orchestrator:
            agent = getattr(orchestrator, agent_name, None)
            if agent and hasattr(agent, 'save_custom_prompt'):
                agent.save_custom_prompt(prompt_template)
        
        # 🆕 Obtener información actualizada desde Redis
        modification_info = prompt_manager.get_modification_info(company_id, agent_name)
        
        return create_success_response({
            "message": f"Prompt updated successfully for {agent_name}",
            "company_id": company_id,
            "agent_name": agent_name,
            "is_custom": True,
            "modified_at": modification_info.get('modified_at'),
            "modified_by": modification_info.get('modified_by'),
            "source": "redis"  # 🆕 Indicar que se guardó en Redis
        })
        
    except Exception as e:
        logger.error(f"Error updating prompt: {e}", exc_info=True)
        return create_error_response(f"Failed to update prompt: {str(e)}", 500)


@bp.route('/prompts/<agent_name>', methods=['DELETE'])
@handle_errors
def reset_prompt(agent_name: str):
    """Restaurar prompt por defecto de un agente (eliminar personalización de Redis)"""
    try:
        company_id = request.args.get('company_id') or _get_company_id_from_request()
        
        if not company_id:
            return create_error_response("company_id is required", 400)
        
        logger.info(f"Resetting prompt for {agent_name} in company {company_id}")
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        # 🆕 Usar el manager de Redis para eliminar
        prompt_manager = get_prompt_redis_manager()
        success = prompt_manager.delete_custom_prompt(company_id, agent_name)
        
        if not success:
            return create_error_response(f"Failed to reset prompt for {agent_name}", 500)
        
        # Actualizar el agente en memoria si está activo
        factory = get_multi_agent_factory()
        orchestrator = factory.get_orchestrator(company_id)
        
        if orchestrator:
            agent = getattr(orchestrator, agent_name, None)
            if agent and hasattr(agent, 'remove_custom_prompt'):
                agent.remove_custom_prompt()
        
        return create_success_response({
            "message": f"Prompt reset to default for {agent_name}",
            "company_id": company_id,
            "agent_name": agent_name,
            "is_custom": False,
            "source": "redis"  # 🆕 Indicar que se eliminó de Redis
        })
        
    except Exception as e:
        logger.error(f"Error resetting prompt: {e}", exc_info=True)
        return create_error_response(f"Failed to reset prompt: {str(e)}", 500)


@bp.route('/api/admin/prompts/<agent_name>/preview', methods=['POST'])
def preview_prompt(agent_name):
    """Preview del prompt procesado con variables"""
    try:
        data = request.get_json()
        company_id = data.get('company_id', request.headers.get('X-Company-ID', 'benova'))
        prompt = data.get('prompt', '')
        
        logger.info(f"Previewing prompt for {agent_name} in company {company_id}")
        
        # Crear instancia del servicio OpenAI
        openai_service = OpenAIService()
        
        # Obtener la configuración de la empresa
        company_config = current_app.config.get('COMPANIES_CONFIG', {}).get(company_id, {})
        
        # Variables de sustitución basadas en el agente
        variables = {
            'company_name': company_config.get('name', 'Empresa'),
            'business_hours': company_config.get('business_hours', 'Lun-Vie 9:00-18:00'),
            'services': ', '.join([s['name'] for s in company_config.get('services', [])[:5]]) if company_config.get('services') else 'servicios varios',
            'contact_email': company_config.get('contact_email', 'info@empresa.com'),
            'contact_phone': company_config.get('contact_phone', '+57 300 000 0000'),
            'question': '[Pregunta del usuario]',
            'context': '[Información contextual del RAG]',
            'chat_history': '[Historial de conversación]',
            'emergency_protocols': '[Protocolos de emergencia]',
            'schedule_context': '[Información de disponibilidad]'
        }
        
        # Procesar el prompt con las variables
        processed_prompt = prompt
        for key, value in variables.items():
            processed_prompt = processed_prompt.replace(f'{{{key}}}', value)
        
        # Simular una respuesta del agente
        test_message = "Hola, ¿me puedes ayudar?"
        
        # Ajustar el mensaje de prueba según el tipo de agente
        if 'router' in agent_name.lower():
            test_message = "Quiero información sobre los servicios disponibles"
        elif 'sales' in agent_name.lower():
            test_message = "¿Cuáles son los precios de sus servicios?"
        elif 'emergency' in agent_name.lower():
            test_message = "Tengo un problema urgente con mi tratamiento"
        elif 'schedule' in agent_name.lower():
            test_message = "Quiero agendar una cita para mañana"
        elif 'support' in agent_name.lower():
            test_message = "¿Cuál es el horario de atención?"
        
        # Reemplazar la variable {question} con el mensaje de prueba
        test_prompt = processed_prompt.replace('[Pregunta del usuario]', test_message)
        
        response = openai_service.create_chat_completion(
            messages=[
                {"role": "system", "content": test_prompt},
                {"role": "user", "content": test_message}
            ],
            temperature=0.7,
            max_tokens=200
        )
        
        return jsonify({
            'success': True,
            'processed_prompt': processed_prompt,
            'test_message': test_message,
            'sample_response': response
        })
        
    except Exception as e:
        logger.error(f"Error previewing prompt: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/prompts/export', methods=['GET'])
@handle_errors
def export_prompts():
    """Exportar todos los prompts de una empresa desde Redis"""
    try:
        company_id = request.args.get('company_id') or _get_company_id_from_request()
        
        if not company_id:
            return create_error_response("company_id is required", 400)
        
        # 🆕 Usar el manager de Redis
        prompt_manager = get_prompt_redis_manager()
        all_prompts = prompt_manager.get_all_prompts(company_id)
        
        export_data = {
            "company_id": company_id,
            "export_timestamp": datetime.utcnow().isoformat() + "Z",
            "prompts": all_prompts,
            "source": "redis"
        }
        
        return create_success_response(export_data)
        
    except Exception as e:
        logger.error(f"Error exporting prompts: {e}", exc_info=True)
        return create_error_response(f"Failed to export prompts: {str(e)}", 500)


@bp.route('/prompts/import', methods=['POST'])
@handle_errors
def import_prompts():
    """Importar prompts a Redis para una empresa"""
    try:
        data = request.get_json()
        company_id = data.get('company_id') or _get_company_id_from_request()
        prompts_data = data.get('prompts', {})
        
        if not company_id:
            return create_error_response("company_id is required", 400)
        
        if not prompts_data:
            return create_error_response("prompts data is required", 400)
        
        # 🆕 Usar el manager de Redis
        prompt_manager = get_prompt_redis_manager()
        
        imported_count = 0
        errors = []
        
        for agent_name, prompt_info in prompts_data.items():
            try:
                if prompt_info.get('is_custom') and prompt_info.get('template'):
                    success = prompt_manager.save_custom_prompt(
                        company_id,
                        agent_name,
                        prompt_info['template'],
                        modified_by=prompt_info.get('modified_by', 'import')
                    )
                    if success:
                        imported_count += 1
                    else:
                        errors.append(f"Failed to import {agent_name}")
            except Exception as e:
                errors.append(f"Error importing {agent_name}: {str(e)}")
        
        response_data = {
            "company_id": company_id,
            "imported_count": imported_count,
            "message": f"Imported {imported_count} custom prompts to Redis"
        }
        
        if errors:
            response_data["errors"] = errors
        
        return create_success_response(response_data)
        
    except Exception as e:
        logger.error(f"Error importing prompts: {e}", exc_info=True)
        return create_error_response(f"Failed to import prompts: {str(e)}", 500)

        
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
