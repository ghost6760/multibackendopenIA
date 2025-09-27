import logging
import json
import os
import time
from datetime import datetime
from dataclasses import asdict
from typing import Dict, Any, Optional, List
from flask import Blueprint, request, jsonify


from app.utils.helpers import create_success_response, create_error_response
from app.utils.decorators import handle_errors, require_api_key
from app.config.company_config import get_company_manager
from app.services.multi_agent_factory import get_multi_agent_factory
from app.services.company_config_service import (
    get_enterprise_company_service, 
    EnterpriseCompanyConfig
)

# 🆕 IMPORTAR NUEVO SERVICIO DE PROMPTS
from app.services.prompt_service import get_prompt_service

# Importaciones existentes mantenidas
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser

logger = logging.getLogger(__name__)
bp = Blueprint('admin', __name__, url_prefix='/api/admin')

def _get_company_id_from_request():
    """Obtener company_id desde request - COMPATIBLE con GET y POST"""
    try:
        # 1. Intentar desde query parameters (GET requests)
        company_id = request.args.get('company_id')
        if company_id:
            return company_id.strip()
        
        # 2. Intentar desde JSON body (POST requests)
        if request.get_json():
            data = request.get_json()
            company_id = data.get('company_id')
            if company_id:
                return company_id.strip()
        
        # 3. Intentar desde form data
        company_id = request.form.get('company_id')
        if company_id:
            return company_id.strip()
            
        return None
        
    except Exception as e:
        logger.warning(f"Error getting company_id from request: {e}")
        return None

def _safe_reload_orchestrator(company_id: str, operation: str, agent_name: str = None) -> Dict[str, Any]:
    """Recarga SEGURA del orquestador con preservación de company_id"""
    try:
        logger.info(f"🔄 Starting safe reload for {company_id} after {operation}")
        
        # Validar que company_id no se haya corrompido
        original_company_id = company_id.strip()
        if not original_company_id:
            return {
                "attempted": True,
                "successful": False,
                "company_id_preserved": False,
                "error": "Empty company_id detected"
            }
        
        # Limpiar cache del factory
        factory = get_multi_agent_factory()
        factory.clear_company_cache(original_company_id)
        
        # Recrear orquestador
        new_orchestrator = factory.get_orchestrator(original_company_id)
        
        if new_orchestrator:
            # Verificar que el company_id se preservó
            if hasattr(new_orchestrator, 'company_id'):
                preserved = new_orchestrator.company_id == original_company_id
            else:
                # Si no tiene atributo, asumir que se preservó si se creó exitosamente
                preserved = True
            
            return {
                "attempted": True,
                "successful": True,
                "company_id_preserved": preserved,
                "operation": operation,
                "agent_name": agent_name
            }
        else:
            return {
                "attempted": True,
                "successful": False,
                "company_id_preserved": False,
                "error": "Could not create new orchestrator"
            }
            
    except Exception as e:
        logger.error(f"Error in safe reload for {company_id}: {e}")
        return {
            "attempted": True,
            "successful": False,
            "company_id_preserved": False,
            "error": str(e)
        }

# ============================================================================
# ENDPOINTS PARA GESTIÓN DE PROMPTS - VERSIÓN REFACTORIZADA
# MANTIENE 100% COMPATIBILIDAD CON FRONTEND EXISTENTE
# ============================================================================

@bp.route('/prompts', methods=['GET'])
@handle_errors  
def get_prompts():
    """CORREGIDO: Obtener prompts de empresa desde query params"""
    try:
        # CORREGIDO: Usar query parameters para GET
        company_id = request.args.get('company_id')
        if not company_id or not company_id.strip():
            return create_error_response("company_id is required in query parameters", 400)
        
        company_id = company_id.strip()
        logger.info(f"Getting prompts for company: {company_id}")
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        # NUEVA LÓGICA: Usar PromptService
        prompt_service = get_prompt_service()
        agents_data = prompt_service.get_company_prompts(company_id)
        
        # Obtener status de la base de datos
        db_status = prompt_service.get_db_status()
        fallback_info = prompt_service.get_last_fallback_info()
        
        response_data = {
            "company_id": company_id,
            "agents": agents_data,
            "database_status": db_status,
            "fallback_used": fallback_info.get("level", "none"),
            "total_agents": len(agents_data),
            "custom_prompts": len([a for a in agents_data.values() if a.get("is_custom", False)])
        }
        
        return create_success_response(response_data)
        
    except Exception as e:
        logger.error(f"Error getting prompts: {e}", exc_info=True)
        return create_error_response(f"Failed to get prompts: {str(e)}", 500)

@bp.route('/prompts/<agent_name>', methods=['PUT'])
@handle_errors  
def update_agent_prompt(agent_name):
    """
    Actualizar prompt de agente con RECARGA CONTROLADA Y SEGURA
    """
    try:
        # Validación de entrada exacta
        data = request.get_json()
        if not data:
            return create_error_response("JSON data is required", 400)
        
        company_id = data.get('company_id')
        template = data.get('prompt_template')
        modified_by = data.get('modified_by', 'admin')
        
        if not company_id or not template:
            return create_error_response("company_id and prompt_template are required", 400)
        
        # CRÍTICO: Preservar company_id original
        original_company_id = company_id.strip()
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(original_company_id):
            return create_error_response(f"Invalid company_id: {original_company_id}", 400)
        
        # Validar agente
        valid_agents = ['router_agent', 'sales_agent', 'support_agent', 'emergency_agent', 'schedule_agent', 'availability_agent']
        if agent_name not in valid_agents:
            return create_error_response(f"Invalid agent_name: {agent_name}", 400)
        
        logger.info(f"Updating prompt for {agent_name} in company {original_company_id}")
        
        # GUARDAR PROMPT (SIN auto-recarga en PromptService)
        prompt_service = get_prompt_service()
        success = prompt_service.save_custom_prompt(
            original_company_id, 
            agent_name, 
            template, 
            modified_by
        )
        
        if not success:
            return create_error_response("Failed to save prompt", 500)
        
        logger.info(f"✅ Prompt saved successfully for {original_company_id}/{agent_name}")
        
        # RECARGA CONTROLADA después de guardar exitosamente
        reload_result = _safe_reload_orchestrator(original_company_id, "update_prompt", agent_name)
        
        # Preparar respuesta
        response_data = {
            "message": f"Prompt updated successfully for {agent_name}",
            "company_id": original_company_id,
            "agent_name": agent_name,
            "version": prompt_service.get_current_version(original_company_id, agent_name),
            "database_status": prompt_service.get_db_status(),
            # Información de recarga
            "orchestrator_reload": {
                "attempted": reload_result["attempted"],
                "successful": reload_result["successful"],
                "company_id_preserved": reload_result["company_id_preserved"],
                "error": reload_result.get("error")
            }
        }
        
        # Log resultado de recarga
        if reload_result["successful"]:
            logger.info(f"✅ Orchestrator reloaded successfully after prompt update")
        else:
            logger.warning(f"⚠️ Orchestrator reload failed: {reload_result.get('error')}")
            # No fallar la respuesta si solo falla la recarga
        
        return create_success_response(response_data)
        
    except Exception as e:
        logger.error(f"Error updating prompt: {e}", exc_info=True)
        return create_error_response(f"Failed to update prompt: {str(e)}", 500)

@bp.route('/prompts/<agent_name>', methods=['DELETE'])
@handle_errors
def reset_agent_prompt(agent_name):
    """
    Restaurar prompt a default con RECARGA CONTROLADA Y SEGURA
    """
    try:
        company_id = _get_company_id_from_request()
        
        if not company_id:
            return create_error_response("company_id is required", 400)
        
        # CRÍTICO: Preservar company_id original
        original_company_id = company_id.strip()
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(original_company_id):
            return create_error_response(f"Invalid company_id: {original_company_id}", 400)
        
        # Validar agente
        valid_agents = ['router_agent', 'sales_agent', 'support_agent', 'emergency_agent', 'schedule_agent', 'availability_agent']
        if agent_name not in valid_agents:
            return create_error_response(f"Invalid agent_name: {agent_name}", 400)
        
        logger.info(f"Resetting prompt for {agent_name} in company {original_company_id}")
        
        # RESTAURAR PROMPT (SIN auto-recarga en PromptService)
        prompt_service = get_prompt_service()
        success = prompt_service.restore_default_prompt(
            original_company_id, 
            agent_name, 
            modified_by="admin_reset"
        )
        
        if not success:
            return create_error_response("Failed to reset prompt", 500)
        
        logger.info(f"✅ Prompt reset successfully for {original_company_id}/{agent_name}")
        
        # RECARGA CONTROLADA después de restaurar exitosamente
        reload_result = _safe_reload_orchestrator(original_company_id, "restore_prompt", agent_name)
        
        # Preparar respuesta
        response_data = {
            "message": f"Prompt reset to default for {agent_name}",
            "company_id": original_company_id,
            "agent_name": agent_name,
            "orchestrator_reload": {
                "attempted": reload_result["attempted"],
                "successful": reload_result["successful"], 
                "company_id_preserved": reload_result["company_id_preserved"],
                "error": reload_result.get("error")
            }
        }
        
        # Log resultado de recarga
        if reload_result["successful"]:
            logger.info(f"✅ Orchestrator reloaded successfully after prompt reset")
        else:
            logger.warning(f"⚠️ Orchestrator reload failed: {reload_result.get('error')}")
        
        return create_success_response(response_data)
        
    except Exception as e:
        logger.error(f"Error resetting prompt: {e}", exc_info=True)
        return create_error_response(f"Failed to reset prompt: {str(e)}", 500)

@bp.route('/prompts/repair', methods=['POST'])
@handle_errors
def repair_prompts():
    """
    Reparar prompts desde repositorio con RECARGA CONTROLADA Y SEGURA
    """
    try:
        data = request.get_json()
        if not data:
            return create_error_response("JSON data is required", 400)
        
        company_id = data.get('company_id')
        agent_name = data.get('agent_name')  # Opcional: reparar agente específico
        
        if not company_id:
            return create_error_response("company_id is required", 400)
        
        # CRÍTICO: Preservar company_id original
        original_company_id = company_id.strip()
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(original_company_id):
            return create_error_response(f"Invalid company_id: {original_company_id}", 400)
        
        # Validar agente si se especifica
        if agent_name:
            valid_agents = ['router_agent', 'sales_agent', 'support_agent', 'emergency_agent', 'schedule_agent', 'availability_agent']
            if agent_name not in valid_agents:
                return create_error_response(f"Invalid agent_name: {agent_name}", 400)
        
        logger.info(f"Repairing prompts for company {original_company_id}, agent: {agent_name or 'ALL'}")
        
        # EJECUTAR REPARACIÓN (SIN auto-recarga en PromptService)
        prompt_service = get_prompt_service()
        success = prompt_service.repair_from_repository(original_company_id, agent_name, "admin_repair")
        
        if not success:
            return create_error_response("Repair operation failed", 500)
        
        repair_summary = prompt_service.get_repair_summary()
        repaired_count = len([item for item in repair_summary if item['success']])
        
        logger.info(f"✅ Repair completed: {repaired_count} agents repaired for {original_company_id}")
        
        # RECARGA CONTROLADA después de reparar exitosamente (solo si hubo cambios)
        reload_result = {"attempted": False}
        if repaired_count > 0:
            reload_result = _safe_reload_orchestrator(original_company_id, "repair_prompts", agent_name)
        
        # Preparar respuesta
        response_data = {
            "message": f"Prompts reparados exitosamente desde repositorio",
            "company_id": original_company_id,
            "agent_name": agent_name,
            "repaired_items": repair_summary,
            "total_repaired": repaired_count,
            "total_attempted": len(repair_summary),
            "orchestrator_reload": reload_result
        }
        
        # Log resultado de recarga
        if reload_result.get("successful"):
            logger.info(f"✅ Orchestrator reloaded successfully after repair")
        elif reload_result.get("attempted"):
            logger.warning(f"⚠️ Orchestrator reload failed: {reload_result.get('error')}")
        
        return create_success_response(response_data)
        
    except Exception as e:
        logger.error(f"Error in repair operation: {e}", exc_info=True)
        return create_error_response(f"Repair operation failed: {str(e)}", 500)

@bp.route('/prompts/preview', methods=['POST'])
@handle_errors
def preview_prompt():
    """
    Generar vista previa con logging de origen de prompts
    MEJORADO: Identifica si usa PostgreSQL o JSON
    """
    try:
        data = request.get_json()
        
        if not data or 'agent_name' not in data or 'company_id' not in data:
            return create_error_response("Missing agent_name or company_id", 400)
        
        agent_name = data['agent_name']
        company_id = data['company_id']
        custom_prompt = data.get('prompt_template', '')
        test_message = data.get('message', '¿Cuánto cuesta un tratamiento?')
        
        if not custom_prompt.strip():
            return create_error_response("Prompt template cannot be empty", 400)
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        # ✅ NUEVO: Verificar origen de prompts ANTES de la vista previa
        prompt_service = get_prompt_service()
        agents_data = prompt_service.get_company_prompts(company_id)
        agent_data = agents_data.get(agent_name, {})
        
        prompt_source = agent_data.get('source', 'unknown')
        current_prompt_preview = agent_data.get('current_prompt', '')[:100] + "..." if agent_data.get('current_prompt') else 'No prompt found'
        
        logger.info(f"🔍 [PREVIEW] Testing {agent_name} for {company_id}")
        logger.info(f"   → Prompt source: {prompt_source}")
        logger.info(f"   → Current prompt preview: {current_prompt_preview}")
        logger.info(f"   → Custom prompt preview: {custom_prompt[:100]}...")
        
        # ✅ Usar el MISMO FLUJO que testConversation()
        from app.models.conversation import ConversationManager
        
        # 1. Usar factory y orchestrator REAL (igual que el tester)
        factory = get_multi_agent_factory()
        orchestrator = factory.get_orchestrator(company_id)
        
        if not orchestrator:
            return create_error_response(f"Multi-agent system not available for company: {company_id}", 503)
        
        # 2. Crear manager para test temporal
        manager = ConversationManager(company_id=company_id)
        temp_user_id = f"preview_test_{int(time.time())}"
        
        # 3. TRUCO: Temporalmente inyectar prompt personalizado
        agent_key = agent_name.replace('_agent', '')  # router_agent -> router
        
        if agent_key not in orchestrator.agents:
            return create_error_response(f"Agent {agent_name} not found", 404)
        
        real_agent = orchestrator.agents[agent_key]
        original_prompt_template = getattr(real_agent, 'prompt_template', None)
        
        try:
            # 4. Crear template temporal con prompt personalizado
            from langchain.prompts import ChatPromptTemplate
            
            # Detectar si el prompt necesita chat_history
            if '{chat_history}' in custom_prompt:
                temp_template = ChatPromptTemplate.from_messages([
                    ("system", custom_prompt),
                    ("human", "{question}")
                ])
            else:
                temp_template = ChatPromptTemplate.from_messages([
                    ("system", custom_prompt),
                    ("human", "{question}")
                ])
            
            # 5. Inyectar temporalmente el prompt personalizado
            real_agent.prompt_template = temp_template
            
            logger.info(f"🔧 [PREVIEW] Using direct agent invocation for {agent_key}")
            
            # 6. Usar el método REAL del orchestrator (igual que test_conversation)
            preview_response = real_agent.invoke({
                "question": test_message,
                "chat_history": [],
                "user_id": temp_user_id,
                "company_id": company_id
            })
            
            agent_used = agent_name  # Retornar el agente solicitado original
            logger.info(f"✅ [PREVIEW] Direct invocation successful, response length: {len(preview_response)}")
            
        finally:
            # 7. Restaurar prompt original
            if original_prompt_template is not None:
                real_agent.prompt_template = original_prompt_template
                logger.info(f"🔄 [PREVIEW] Restored original prompt for {agent_key}")
        
        # ✅ NUEVO: Respuesta con información detallada
        response_data = {
            "preview": preview_response,  # ✅ ASEGURAR que no se trunque aquí
            "agent_name": agent_name,
            "agent_used": agent_used,
            "company_id": company_id,
            "test_message": test_message,
            "prompt_preview": custom_prompt[:150] + "..." if len(custom_prompt) > 150 else custom_prompt,
            "method": "real_agent_system",
            "timestamp": time.time(),
            # ✅ NUEVO: Información de debugging
            "debug_info": {
                "prompt_source": prompt_source,
                "agent_key": agent_key,
                "response_length": len(preview_response),
                "temp_user_id": temp_user_id
            }
        }
        
        logger.info(f"🎯 [PREVIEW] Returning response with {len(preview_response)} characters")
        
        return create_success_response(response_data)
        
    except Exception as e:
        logger.error(f"Error previewing prompt: {e}", exc_info=True)
        return create_error_response(f"Failed to preview prompt: {str(e)}", 500)

# 🆕 NUEVO ENDPOINT PARA MIGRACIÓN
@bp.route('/prompts/migrate', methods=['POST'])
@handle_errors
def migrate_prompts_to_postgresql():
    """
    Migrar prompts existentes de JSON a PostgreSQL
    Endpoint administrativo para transición
    """
    try:
        data = request.get_json() or {}
        force_migration = data.get('force', False)
        
        logger.info("Starting prompt migration from JSON to PostgreSQL")
        
        prompt_service = get_prompt_service()
        
        # Verificar estado de la base de datos
        db_status = prompt_service.get_db_status()
        if not db_status['postgresql_available']:
            return create_error_response("PostgreSQL not available for migration", 503)
        
        # Ejecutar migración
        migration_stats = prompt_service.migrate_from_json()
        
        if migration_stats['success']:
            logger.info(f"Migration completed successfully: {migration_stats}")
            return create_success_response({
                "message": "Migration completed successfully",
                "statistics": migration_stats,
                "database_status": db_status
            })
        else:
            logger.error(f"Migration failed: {migration_stats}")
            return create_error_response("Migration failed", 500, {
                "statistics": migration_stats,
                "database_status": db_status
            })
        
    except Exception as e:
        logger.error(f"Error in migration: {e}", exc_info=True)
        return create_error_response(f"Migration failed: {str(e)}", 500)


# ============================================================================
# FUNCIONES DE COMPATIBILIDAD - MANTENER PARA NO ROMPER CÓDIGO EXISTENTE
# ============================================================================

def _has_custom_prompt(company_id: str, agent_name: str) -> bool:
    """Verificar si un agente tiene prompt personalizado - COMPATIBILIDAD"""
    try:
        prompt_service = get_prompt_service()
        agents_data = prompt_service.get_company_prompts(company_id)
        agent_data = agents_data.get(agent_name, {})
        return agent_data.get('is_custom', False)
    except Exception as e:
        logger.warning(f"Error checking custom prompt: {e}")
        return False

def _get_prompt_modification_date(company_id: str, agent_name: str) -> Optional[str]:
    """Obtener fecha de modificación del prompt - COMPATIBILIDAD"""
    try:
        prompt_service = get_prompt_service()
        agents_data = prompt_service.get_company_prompts(company_id)
        agent_data = agents_data.get(agent_name, {})
        return agent_data.get('last_modified')
    except Exception as e:
        logger.warning(f"Error getting modification date: {e}")
        return None

# ============================================================================
# OTROS ENDPOINTS EXISTENTES - MANTENER SIN CAMBIOS
# ============================================================================

@bp.route('/status', methods=['GET'])
@handle_errors
def get_admin_status():
    """Estado del sistema administrativo - CORREGIDO"""
    try:
        company_manager = get_company_manager()
        companies_dict = company_manager.get_all_companies()  # ✅ Es un diccionario
        
        # 🆕 INCLUIR ESTADO DEL SISTEMA DE PROMPTS
        prompt_service = get_prompt_service()
        db_status = prompt_service.get_db_status()
        
        status_data = {
            "system_status": "operational",
            "companies_configured": len(companies_dict),
            "multi_tenant_mode": True,
            "prompt_system": {
                "postgresql_available": db_status['postgresql_available'],
                "fallback_active": db_status.get('fallback_mode', 'none') != 'none',
                "tables_status": db_status.get('tables_exist', False),
                "total_custom_prompts": db_status.get('total_custom_prompts', 0),
                "total_default_prompts": db_status.get('total_default_prompts', 0)
            },
            "companies": [
                {
                    "company_id": company_id,  # ✅ CORREGIDO: usar la key del diccionario
                    "company_name": config.company_name,  # ✅ CORREGIDO: usar el objeto config
                    "status": "active"
                }
                for company_id, config in companies_dict.items()  # ✅ CORREGIDO: iterar correctamente
            ]
        }
        
        return create_success_response(status_data)
        
    except Exception as e:
        logger.error(f"Error getting admin status: {e}")
        return create_error_response(f"Failed to get admin status: {str(e)}", 500)
        
@bp.route('/companies/export', methods=['GET'])
@handle_errors
def export_companies_configuration():
    """Exportar configuración de empresas - MANTENER FUNCIONALIDAD EXISTENTE"""
    try:
        export_all = request.args.get('export_all', 'false').lower() == 'true'
        company_id = request.args.get('company_id')
        
        company_manager = get_company_manager()
        
        if export_all:
            # Exportar todas las empresas
            companies = company_manager.get_all_companies()
            export_data = {
                "export_type": "all_companies",
                "timestamp": time.time(),
                "total_companies": len(companies),
                "companies": {
                    comp.company_id: {
                        "company_name": comp.company_name,
                        "business_type": getattr(comp, 'business_type', 'Unknown'),
                        "services": comp.services,
                        "agents": getattr(comp, 'agents', []),
                        "vectorstore_index": comp.vectorstore_index,
                        "redis_prefix": comp.redis_prefix
                    }
                    for comp in companies
                }
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
# ENDPOINTS ADICIONALES DEL ARCHIVO ORIGINAL - MANTENER SIN CAMBIOS
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

@bp.route('/vectorstore/force-recovery', methods=['POST'])
@handle_errors
def force_vectorstore_recovery():
    """Force vectorstore recovery - ENHANCED Multi-tenant"""
    try:
        from app.utils.decorators import require_api_key
        
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
def reset_system():
    """Reset system caches - Multi-tenant Enhanced"""
    try:
        from app.utils.decorators import require_api_key
        from app.services.redis_service import get_redis_client
        
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

@bp.route('/companies/reload-config', methods=['POST'])
@handle_errors
def reload_companies_config():
    """Reload companies configuration from file"""
    try:
        from app.utils.decorators import require_api_key
        
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
        from flask import current_app
        
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

@bp.route('/diagnostics', methods=['GET'])
@handle_errors
def run_system_diagnostics():
    """Ejecutar diagnósticos completos del sistema"""
    try:
        from flask import current_app
        from app.services.redis_service import get_redis_client
        
        company_id = _get_company_id_from_request()
        
        # Validar empresa si se especifica
        company_manager = get_company_manager()
        if company_id and company_id != 'benova' and not company_manager.validate_company_id(company_id):
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
            orchestrator = factory.get_orchestrator(company_id or 'benova')
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



@bp.route('/companies/create', methods=['POST'])
@handle_errors
@require_api_key
def create_new_company_enterprise():
    """
    ENDPOINT ENTERPRISE - Crear nueva empresa con PostgreSQL como source of truth
    """
    try:
        data = request.get_json()
        
        # Validar campos requeridos
        required_fields = ['company_id', 'company_name', 'services']
        for field in required_fields:
            if not data.get(field):
                return create_error_response(f"Missing required field: {field}", 400)
        
        company_id = data['company_id'].lower().strip()
        
        # Validar formato de company_id
        import re
        if not re.match(r'^[a-z0-9_]+$', company_id):
            return create_error_response(
                "company_id must contain only lowercase letters, numbers, and underscores", 
                400
            )
        
        # Obtener servicio enterprise
        enterprise_service = get_enterprise_company_service()
        
        # Verificar que la empresa no existe
        existing_config = enterprise_service.get_company_config(company_id, use_cache=False)
        if existing_config and existing_config.notes != "Default emergency configuration":
            return create_error_response(f"Company {company_id} already exists", 400)
        
        # 1. CREAR CONFIGURACIÓN ENTERPRISE
        enterprise_config = EnterpriseCompanyConfig(
            company_id=company_id,
            company_name=data['company_name'],
            business_type=data.get('business_type', 'general'),
            services=data['services'],
            
            # Configuración de agentes
            sales_agent_name=data.get('sales_agent_name', f"Asistente de {data['company_name']}"),
            model_name=data.get('model_name', 'gpt-4o-mini'),
            max_tokens=data.get('max_tokens', 1500),
            temperature=data.get('temperature', 0.7),
            max_context_messages=data.get('max_context_messages', 10),
            
            # Servicios externos
            schedule_service_url=data.get('schedule_service_url', 'http://127.0.0.1:4040'),
            schedule_integration_type=data.get('schedule_integration_type', 'basic'),
            chatwoot_account_id=data.get('chatwoot_account_id'),
            
            # Configuración de negocio
            treatment_durations=data.get('treatment_durations'),
            schedule_keywords=data.get('schedule_keywords'),
            emergency_keywords=data.get('emergency_keywords'),
            sales_keywords=data.get('sales_keywords'),
            required_booking_fields=data.get('required_booking_fields'),
            
            # Localización
            timezone=data.get('timezone', 'America/Bogota'),
            language=data.get('language', 'es'),
            currency=data.get('currency', 'COP'),
            
            # Límites y suscripción
            subscription_tier=data.get('subscription_tier', 'basic'),
            max_documents=data.get('max_documents', 1000),
            max_conversations=data.get('max_conversations', 10000),
            
            # Metadatos
            created_by="admin_api",
            modified_by="admin_api",
            notes=f"Created via API on {datetime.now().isoformat()}"
        )
        
        # 2. GUARDAR EN POSTGRESQL (Source of Truth)
        postgresql_success = enterprise_service.create_company(
            enterprise_config, 
            created_by="admin_api"
        )
        
        if not postgresql_success:
            return create_error_response("Failed to save company configuration to PostgreSQL", 500)
        
        # 3. INICIALIZAR VECTOR STORE EN REDIS
        vectorstore_status = "not_initialized"
        try:
            from app.services.vectorstore_service import VectorstoreService
            vectorstore_service = VectorstoreService(company_id=company_id)
            
            health_status = vectorstore_service.check_health()
            if health_status.get('index_exists'):
                vectorstore_status = "initialized"
            else:
                vectorstore_status = "failed"
        except Exception as e:
            logger.warning(f"Could not initialize vectorstore for {company_id}: {e}")
            vectorstore_status = f"failed: {str(e)}"
        
        # 4. VERIFICAR SISTEMA DE PROMPTS (NO CREAR PROMPTS CUSTOM)
        prompt_status = "system_ready"
        try:
            from app.services.prompt_service import get_prompt_service
            prompt_service = get_prompt_service()
            
            # Verificar estado de la base de datos
            db_status = prompt_service.get_db_status()
            if not db_status.get('postgresql_available', False):
                logger.warning(f"PostgreSQL not available for {company_id}, will use fallback prompts")
            
            # Verificar que puede obtener prompts para la empresa (usa fallbacks automáticos)
            test_agents = ['router_agent', 'sales_agent', 'support_agent', 'emergency_agent', 'schedule_agent']
            agents_data = prompt_service.get_company_prompts(company_id)
            
            if agents_data:
                # Contar qué tipos de prompts está usando
                sources = {}
                for agent_name, agent_info in agents_data.items():
                    source = agent_info.get('source', 'unknown')
                    sources[source] = sources.get(source, 0) + 1
                
                prompt_status = f"verified ({len(agents_data)} agents using sources: {sources})"
                logger.info(f"✅ Prompt system ready for {company_id}: {prompt_status}")
            else:
                prompt_status = "fallback_mode (using hardcoded prompts)"
                logger.warning(f"⚠️ Prompt system in fallback mode for {company_id}")
            
        except Exception as e:
            logger.error(f"Error verifying prompt system for {company_id}: {e}")
            prompt_status = f"error: {str(e)} (will use hardcoded fallbacks)"

        # 5. AGREGAR AL COMPANY MANAGER LEGACY PRIMERO (PARA COMPATIBILIDAD)
        company_manager_status = "not_added"
        try:
            company_manager = get_company_manager()
            legacy_config = enterprise_config.to_legacy_config()
            
            # ✅ CRÍTICO: Agregar ANTES de crear orchestrator
            company_manager.add_company_config(legacy_config)
            company_manager_status = "added_to_legacy_manager"
            
            logger.info(f"✅ Company {company_id} added to legacy CompanyManager")
            
        except Exception as e:
            logger.error(f"Failed to add company to legacy manager: {e}")
            company_manager_status = f"failed: {str(e)}"

        # 6. INICIALIZAR ORQUESTADOR MULTI-AGENTE (DESPUÉS DE AGREGAR AL MANAGER)
        orchestrator_status = "not_initialized"
        try:
            if company_manager_status.startswith("added"):
                factory = get_multi_agent_factory()
                orchestrator = factory.get_orchestrator(company_id)
                
                if orchestrator:
                    orchestrator_status = "initialized"
                    logger.info(f"✅ Orchestrator created successfully for {company_id}")
                else:
                    orchestrator_status = "failed - could not create"
                    logger.error(f"❌ Orchestrator creation failed for {company_id}")
            else:
                orchestrator_status = "skipped - company_manager failed"
                logger.warning(f"⚠️ Skipping orchestrator creation due to company_manager failure")
                
        except Exception as e:
            logger.error(f"Error initializing orchestrator for {company_id}: {e}")
            orchestrator_status = f"failed: {str(e)}"

        # 7. ACTUALIZAR JSON CONFIG (PARA COMPATIBILIDAD TOTAL)
        json_fallback_status = "not_updated"
        try:
            config_file = os.getenv('COMPANIES_CONFIG_FILE', 'companies_config.json')
            
            # Leer configuración existente
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    existing_config = json.load(f)
            else:
                existing_config = {}
            
            # Agregar nueva empresa (formato legacy para compatibilidad)
            existing_config[company_id] = {
                "company_name": enterprise_config.company_name,
                "business_type": enterprise_config.business_type,
                "redis_prefix": enterprise_config.redis_prefix,
                "vectorstore_index": enterprise_config.vectorstore_index,
                "schedule_service_url": enterprise_config.schedule_service_url,
                "sales_agent_name": enterprise_config.sales_agent_name,
                "services": enterprise_config.services,
                "model_name": enterprise_config.model_name,
                "max_tokens": enterprise_config.max_tokens,
                "temperature": enterprise_config.temperature,
                "_source": "postgresql",
                "_created_via": "enterprise_api",
                "_version": enterprise_config.version
            }
            
            # Guardar archivo actualizado
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(existing_config, f, indent=2, ensure_ascii=False)
            
            json_fallback_status = "updated"
            logger.info(f"✅ JSON config updated for {company_id}")
            
        except Exception as e:
            logger.warning(f"Could not update JSON fallback for {company_id}: {e}")
            json_fallback_status = f"failed: {str(e)}"

        # ✅ RETURN AL FINAL CON TODAS LAS VARIABLES DEFINIDAS
        logger.info(f"✅ Enterprise company created: {company_id} ({enterprise_config.company_name})")
        
        return create_success_response({
            "message": f"Enterprise company {company_id} created successfully",
            "company_id": company_id,
            "company_name": enterprise_config.company_name,
            "business_type": enterprise_config.business_type,
            "architecture": "enterprise_postgresql",
            "setup_status": {
                "postgresql_config_saved": postgresql_success,
                "vectorstore_initialized": vectorstore_status,
                "prompts_configured": prompt_status,
                "company_manager_added": company_manager_status,
                "orchestrator_initialized": orchestrator_status,
                "json_fallback_updated": json_fallback_status
            },
            "configuration": {
                "redis_prefix": enterprise_config.redis_prefix,
                "vectorstore_index": enterprise_config.vectorstore_index,
                "timezone": enterprise_config.timezone,
                "language": enterprise_config.language,
                "currency": enterprise_config.currency,
                "subscription_tier": enterprise_config.subscription_tier,
                "max_documents": enterprise_config.max_documents,
                "max_conversations": enterprise_config.max_conversations
            },
            "system_ready": orchestrator_status.startswith("initialized"),
            "endpoints_available": [
                f"POST /documents (with X-Company-ID: {company_id})",
                f"POST /conversations/{{user_id}}/test?company_id={company_id}",
                f"POST /webhook/chatwoot (auto-detect company)",
                f"GET /api/admin/companies/{company_id} (configuration)",
                f"PUT /api/admin/companies/{company_id} (update configuration)"
            ],
            "next_steps": [
                f"Test system: curl -X POST /conversations/test123/test?company_id={company_id} -d '{{\"message\": \"Hola\"}}'",
                f"Upload documents: curl -X POST /documents -H 'X-Company-ID: {company_id}' -d '{{\"content\": \"...\"}}'",
                f"Update config: curl -X PUT /api/admin/companies/{company_id} -d '{{\"sales_agent_name\": \"New Name\"}}'",
                "Configure Chatwoot webhook with company_id in conversation metadata"
            ]
        })
        
    except Exception as e:
        logger.error(f"Error creating enterprise company: {e}")
        return create_error_response(f"Failed to create enterprise company: {str(e)}", 500)
        

@bp.route('/companies/<company_id>', methods=['GET'])
@handle_errors
@require_api_key
def get_company_configuration(company_id):
    """
    OBTENER configuración completa de empresa desde PostgreSQL
    
    GET /api/admin/companies/spa_wellness
    """
    try:
        enterprise_service = get_enterprise_company_service()
        config = enterprise_service.get_company_config(company_id, use_cache=False)
        
        if not config:
            return create_error_response(f"Company {company_id} not found", 404)
        
        # Información adicional del estado
        db_status = enterprise_service.get_db_status()
        
        return create_success_response({
            "company_id": config.company_id,
            "configuration": asdict(config),
            "metadata": {
                "source": "postgresql" if db_status.get('postgresql_available') else "json_fallback",
                "version": config.version,
                "last_modified": config.modified_by,
                "is_enterprise": True,
                "db_status": db_status.get('connection_status', 'unknown')
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting company configuration for {company_id}: {e}")
        return create_error_response(f"Failed to get company configuration: {str(e)}", 500)


@bp.route('/companies/<company_id>', methods=['PUT'])
@handle_errors
@require_api_key
def update_company_configuration(company_id):
    """
    ACTUALIZAR configuración de empresa en PostgreSQL con versionado automático
    
    PUT /api/admin/companies/spa_wellness
    {
        "company_name": "Nuevo Nombre",
        "services": "nuevos servicios actualizados",
        "sales_agent_name": "Nuevo Agente",
        "treatment_durations": {
            "masaje_nuevo": 75
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return create_error_response("No data provided", 400)
        
        enterprise_service = get_enterprise_company_service()
        
        # Verificar que existe
        existing_config = enterprise_service.get_company_config(company_id, use_cache=False)
        if not existing_config:
            return create_error_response(f"Company {company_id} not found", 404)
        
        # Filtrar campos que se pueden actualizar
        updatable_fields = [
            'company_name', 'business_type', 'services', 'sales_agent_name',
            'model_name', 'max_tokens', 'temperature', 'max_context_messages',
            'schedule_service_url', 'schedule_integration_type', 'chatwoot_account_id',
            'treatment_durations', 'schedule_keywords', 'emergency_keywords', 
            'sales_keywords', 'required_booking_fields', 'timezone', 'language', 
            'currency', 'subscription_tier', 'max_documents', 'max_conversations', 'notes'
        ]
        
        updates = {key: value for key, value in data.items() if key in updatable_fields}
        
        if not updates:
            return create_error_response("No valid fields to update", 400)
        
        # Actualizar en PostgreSQL
        success = enterprise_service.update_company(
            company_id, 
            updates, 
            modified_by="admin_api"
        )
        
        if not success:
            return create_error_response("Failed to update company configuration", 500)
        
        # Invalidar cache del orquestador si cambió configuración de agentes
        agent_related_fields = ['sales_agent_name', 'model_name', 'max_tokens', 'temperature']
        if any(field in updates for field in agent_related_fields):
            try:
                factory = get_multi_agent_factory()
                factory.clear_company_cache(company_id)
                logger.info(f"Orchestrator cache cleared for {company_id} due to agent config changes")
            except Exception as e:
                logger.warning(f"Could not clear orchestrator cache: {e}")
        
        # Obtener configuración actualizada
        updated_config = enterprise_service.get_company_config(company_id, use_cache=False)
        
        logger.info(f"✅ Company {company_id} configuration updated: {list(updates.keys())}")
        
        # Invalidar cache del endpoint /api/companies para sincronizar CompanySelector
        try:
            company_manager = get_company_manager()
            
            if hasattr(company_manager, '_configs'):
                company_manager._configs.clear()
                logger.info("Cleared company_manager._configs cache that affects /api/companies")
            
            if hasattr(company_manager, '_load_company_configs'):
                company_manager._load_company_configs()
                logger.info("Reloaded company_manager configurations from PostgreSQL")
            
            factory = get_multi_agent_factory()
            factory.clear_all_cache()
            logger.info("Cleared factory cache for complete synchronization")
            
        except Exception as cache_error:
            logger.warning(f"Could not invalidate /api/companies cache: {cache_error}")
        
        return create_success_response({
            "message": f"Company {company_id} updated successfully",
            "company_id": company_id,
            "fields_updated": list(updates.keys()),
            "new_version": updated_config.version if updated_config else "unknown",
            "configuration": asdict(updated_config) if updated_config else None,
            "cache_invalidated": True
        })
        
        
    except Exception as e:
        logger.error(f"Error updating company {company_id}: {e}")
        return create_error_response(f"Failed to update company: {str(e)}", 500)


@bp.route('/companies', methods=['GET'])
@handle_errors
@require_api_key
def list_all_companies():
    """
    LISTAR todas las empresas desde PostgreSQL con filtros
    
    GET /api/admin/companies?active_only=true&business_type=healthcare
    """
    try:
        # Parámetros de filtro
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        business_type = request.args.get('business_type')
        
        enterprise_service = get_enterprise_company_service()
        companies = enterprise_service.list_companies(
            active_only=active_only,
            business_type=business_type
        )
        
        # Obtener estado de DB
        db_status = enterprise_service.get_db_status()
        
        # Formatear respuesta
        companies_data = []
        for config in companies:
            companies_data.append({
                "company_id": config.company_id,
                "company_name": config.company_name,
                "business_type": config.business_type,
                "services": config.services,
                "is_active": config.is_active,
                "subscription_tier": config.subscription_tier,
                "version": config.version,
                "created_by": config.created_by,
                "modified_by": config.modified_by
            })
        
        return create_success_response({
            "total_companies": len(companies_data),
            "filters_applied": {
                "active_only": active_only,
                "business_type": business_type
            },
            "companies": companies_data,
            "source": "postgresql" if db_status.get('postgresql_available') else "json_fallback",
            "db_status": db_status
        })
        
    except Exception as e:
        logger.error(f"Error listing companies: {e}")
        return create_error_response(f"Failed to list companies: {str(e)}", 500)


@bp.route('/companies/migrate-from-json', methods=['POST'])
@handle_errors
@require_api_key
def migrate_companies_from_json():
    """
    MIGRAR configuraciones desde JSON hacia PostgreSQL
    
    POST /api/admin/companies/migrate-from-json
    """
    try:
        enterprise_service = get_enterprise_company_service()
        
        # Verificar estado de PostgreSQL
        db_status = enterprise_service.get_db_status()
        if not db_status.get('postgresql_available'):
            return create_error_response(
                "PostgreSQL not available for migration", 
                503
            )
        
        # Ejecutar migración
        migration_stats = enterprise_service.migrate_from_json()
        
        if migration_stats['success']:
            return create_success_response({
                "message": "Migration completed successfully",
                "statistics": migration_stats,
                "recommendation": "Consider using PostgreSQL as primary configuration source"
            })
        else:
            return create_error_response(
                "Migration completed with errors",
                partial_data={
                    "statistics": migration_stats,
                    "recommendation": "Check logs and retry failed companies"
                }
            )
        
    except Exception as e:
        logger.error(f"Migration error: {e}")
        return create_error_response(f"Migration failed: {str(e)}", 500)
