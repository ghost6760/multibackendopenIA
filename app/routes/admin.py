import logging
import json
import os
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from flask import Blueprint, request, jsonify

from app.utils.helpers import create_success_response, create_error_response
from app.utils.decorators import handle_errors
from app.config.company_config import get_company_manager
from app.services.multi_agent_factory import get_multi_agent_factory

# 🆕 IMPORTAR NUEVO SERVICIO DE PROMPTS
from app.services.prompt_service import get_prompt_service

# Importaciones existentes mantenidas
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser

logger = logging.getLogger(__name__)
bp = Blueprint('admin', __name__, url_prefix='/api/admin')

def _get_company_id_from_request() -> Optional[str]:
    """Obtener company_id desde diferentes fuentes en la request"""
    # 1. Desde JSON body
    if request.is_json:
        data = request.get_json()
        if data and 'company_id' in data:
            return data['company_id']
    
    # 2. Desde query parameters
    company_id = request.args.get('company_id')
    if company_id:
        return company_id
    
    # 3. Desde headers
    company_id = request.headers.get('X-Company-ID')
    if company_id:
        return company_id
    
    # 4. Default para compatibilidad
    return None

# ============================================================================
# ENDPOINTS PARA GESTIÓN DE PROMPTS - VERSIÓN REFACTORIZADA
# MANTIENE 100% COMPATIBILIDAD CON FRONTEND EXISTENTE
# ============================================================================

@bp.route('/prompts', methods=['GET'])
@handle_errors
def get_prompts():
    """
    Obtener prompts actuales - REFACTORIZADO CON POSTGRESQL
    MANTIENE: Endpoint exacto, formato de respuesta idéntico
    MEJORA: PostgreSQL con fallbacks, mejor rendimiento
    """
    try:
        company_id = _get_company_id_from_request()
        
        if not company_id:
            logger.error("No company_id provided in request")
            return create_error_response("company_id is required", 400)
        
        logger.info(f"Getting prompts for company: {company_id}")
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        # 🆕 USAR NUEVO SERVICIO DE PROMPTS CON FALLBACKS
        prompt_service = get_prompt_service()
        agents_data = prompt_service.get_company_prompts(company_id)
        
        # MANTENER formato de respuesta exacto para compatibilidad
        response_data = {
            "company_id": company_id,
            "agents": agents_data,
            # 🆕 INFORMACIÓN ADICIONAL SOBRE FALLBACKS (opcional, no rompe compatibilidad)
            "fallback_used": prompt_service.last_fallback_level,
            "database_status": prompt_service.get_db_status()
        }
        
        logger.info(f"Successfully loaded prompts for {company_id} using fallback: {prompt_service.last_fallback_level}")
        return create_success_response(response_data)
        
    except Exception as e:
        logger.error(f"Error getting prompts: {e}", exc_info=True)
        return create_error_response(f"Failed to get prompts: {str(e)}", 500)

@bp.route('/prompts/<agent_name>', methods=['PUT'])
@handle_errors  
def update_agent_prompt(agent_name):
    """
    Actualizar prompt de agente - REFACTORIZADO CON POSTGRESQL
    MANTIENE: Endpoint exacto, validaciones, formato de respuesta
    MEJORA: PostgreSQL con versionado automático
    """
    try:
        # MANTENER validación de entrada exacta
        data = request.get_json()
        if not data:
            return create_error_response("JSON data is required", 400)
        
        company_id = data.get('company_id')
        template = data.get('prompt_template')
        modified_by = data.get('modified_by', 'admin')
        
        if not company_id or not template:
            return create_error_response("company_id and prompt_template are required", 400)
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        # Validar agente
        valid_agents = ['router_agent', 'sales_agent', 'support_agent', 'emergency_agent', 'schedule_agent', 'availability_agent']
        if agent_name not in valid_agents:
            return create_error_response(f"Invalid agent_name: {agent_name}", 400)
        
        logger.info(f"Updating prompt for {agent_name} in company {company_id}")
        
        # 🆕 NUEVA LÓGICA: PostgreSQL con versionado automático
        prompt_service = get_prompt_service()
        success = prompt_service.save_custom_prompt(
            company_id, 
            agent_name, 
            template, 
            modified_by
        )
        
        if not success:
            return create_error_response("Failed to save prompt", 500)
        
        # MANTENER formato de respuesta exacto
        response_data = {
            "message": f"Prompt updated successfully for {agent_name}",
            "company_id": company_id,
            "agent_name": agent_name,
            # 🆕 INFORMACIÓN ADICIONAL (no rompe compatibilidad)
            "version": prompt_service.get_current_version(company_id, agent_name),
            "database_status": prompt_service.get_db_status()
        }
        
        return create_success_response(response_data)
        
    except Exception as e:
        logger.error(f"Error updating prompt: {e}", exc_info=True)
        return create_error_response(f"Failed to update prompt: {str(e)}", 500)

@bp.route('/prompts/<agent_name>', methods=['DELETE'])
@handle_errors
def reset_agent_prompt(agent_name):
    """
    Restaurar prompt a default - REFACTORIZADO CON POSTGRESQL
    MANTIENE: Endpoint exacto, comportamiento idéntico
    MEJORA: PostgreSQL con preservación de historial
    """
    try:
        company_id = _get_company_id_from_request()
        
        if not company_id:
            return create_error_response("company_id is required", 400)
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        # Validar agente
        valid_agents = ['router_agent', 'sales_agent', 'support_agent', 'emergency_agent', 'schedule_agent', 'availability_agent']
        if agent_name not in valid_agents:
            return create_error_response(f"Invalid agent_name: {agent_name}", 400)
        
        logger.info(f"Resetting prompt for {agent_name} in company {company_id}")
        
        # 🆕 NUEVA LÓGICA: PostgreSQL con preservación de historial
        prompt_service = get_prompt_service()
        success = prompt_service.restore_default_prompt(
            company_id, 
            agent_name, 
            modified_by="admin_reset"
        )
        
        if not success:
            return create_error_response("Failed to reset prompt", 500)
        
        # MANTENER formato de respuesta exacto
        response_data = {
            "message": f"Prompt reset to default for {agent_name}",
            "company_id": company_id,
            "agent_name": agent_name
        }
        
        return create_success_response(response_data)
        
    except Exception as e:
        logger.error(f"Error resetting prompt: {e}", exc_info=True)
        return create_error_response(f"Failed to reset prompt: {str(e)}", 500)

# 🆕 NUEVA FUNCIÓN PARA BOTÓN REPARAR DEL FRONTEND
@bp.route('/prompts/repair', methods=['POST'])
@handle_errors
def repair_prompts():
    """
    Nueva función REPARAR - Restaura prompts desde repositorio
    Endpoint nuevo que no rompe compatibilidad existente
    """
    try:
        data = request.get_json()
        if not data:
            return create_error_response("JSON data is required", 400)
        
        company_id = data.get('company_id')
        agent_name = data.get('agent_name')  # Opcional: reparar agente específico
        
        if not company_id:
            return create_error_response("company_id is required", 400)
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        # Validar agente si se especifica
        if agent_name:
            valid_agents = ['router_agent', 'sales_agent', 'support_agent', 'emergency_agent', 'schedule_agent', 'availability_agent']
            if agent_name not in valid_agents:
                return create_error_response(f"Invalid agent_name: {agent_name}", 400)
        
        logger.info(f"Repairing prompts for company {company_id}, agent: {agent_name or 'ALL'}")
        
        # Ejecutar reparación
        prompt_service = get_prompt_service()
        success = prompt_service.repair_from_repository(company_id, agent_name, "admin_repair")
        
        if not success:
            return create_error_response("Repair operation failed", 500)
        
        repair_summary = prompt_service.get_repair_summary()
        
        response_data = {
            "message": "Prompts reparados exitosamente desde repositorio",
            "company_id": company_id,
            "agent_name": agent_name,
            "repaired_items": repair_summary,
            "total_repaired": len([item for item in repair_summary if item['success']]),
            "total_attempted": len(repair_summary)
        }
        
        return create_success_response(response_data)
        
    except Exception as e:
        logger.error(f"Error in repair operation: {e}", exc_info=True)
        return create_error_response(f"Repair operation failed: {str(e)}", 500)

@bp.route('/prompts/preview', methods=['POST'])
@handle_errors
def preview_prompt():
    """
    Vista previa de prompt - MANTIENE funcionalidad existente
    MEJORA: Mejor simulación con contexto empresarial
    """
    try:
        data = request.get_json()
        if not data:
            return create_error_response("JSON data is required", 400)
        
        company_id = data.get('company_id')
        agent_name = data.get('agent_name')
        prompt_template = data.get('prompt_template')
        test_message = data.get('test_message', '¿Cuánto cuesta un tratamiento?')
        
        if not all([company_id, agent_name, prompt_template]):
            return create_error_response("company_id, agent_name, and prompt_template are required", 400)
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        logger.info(f"Generating preview for {agent_name} in company {company_id}")
        
        # Simular respuesta del agente
        preview_response = _simulate_agent_response(
            company_id, agent_name, prompt_template, test_message
        )
        
        response_data = {
            "company_id": company_id,
            "agent_name": agent_name,
            "test_message": test_message,
            "preview_response": preview_response
        }
        
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
# FUNCIONES AUXILIARES - MEJORADAS PERO COMPATIBLES
# ============================================================================

def _simulate_agent_response(company_id: str, agent_name: str, prompt_template: str, test_message: str) -> str:
    """
    Simular respuesta del agente con prompt personalizado
    MEJORADO: Mejor contexto empresarial, manejo de errores
    """
    try:
        # Obtener configuración de la empresa
        company_manager = get_company_manager()
        config = company_manager.get_company_config(company_id)
        
        # Crear contexto mejorado
        context_data = {
            "company_name": config.company_name,
            "services": config.services,
            "business_type": getattr(config, 'business_type', 'Servicios médicos'),
            "agent_name": agent_name.replace('_', ' ').title()
        }
        
        # Crear prompt template con contexto
        full_template = f"""
{prompt_template}

CONTEXTO DE LA EMPRESA:
- Empresa: {context_data['company_name']}
- Servicios: {context_data['services']}
- Tipo de negocio: {context_data['business_type']}

Responde al siguiente mensaje como {context_data['agent_name']}:
{{message}}
"""
        
        # Usar el modelo de chat disponible
        try:
            factory = get_multi_agent_factory()
            orchestrator = factory.get_orchestrator(company_id)
            
            if orchestrator and hasattr(orchestrator, 'openai_service'):
                chat_model = orchestrator.openai_service.get_chat_model()
                
                # Crear chain simple para preview
                template = ChatPromptTemplate.from_template(full_template)
                chain = template | chat_model | StrOutputParser()
                
                # Ejecutar simulación
                response = chain.invoke({"message": test_message})
                return response[:500]  # Limitar respuesta para preview
            else:
                return f"Simulación no disponible. El agente {agent_name} respondería basado en el prompt personalizado al mensaje: '{test_message}'"
        
        except Exception as model_error:
            logger.warning(f"Model simulation failed: {model_error}")
            return f"Vista previa simulada: El agente {agent_name} para {config.company_name} respondería al mensaje '{test_message}' usando el prompt personalizado."
        
    except Exception as e:
        logger.error(f"Error simulating agent response: {e}")
        return f"Error en la simulación: {str(e)}"

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
    """Estado del sistema administrativo"""
    try:
        company_manager = get_company_manager()
        companies = company_manager.get_all_companies()
        
        # 🆕 INCLUIR ESTADO DEL SISTEMA DE PROMPTS
        prompt_service = get_prompt_service()
        db_status = prompt_service.get_db_status()
        
        status_data = {
            "system_status": "operational",
            "companies_configured": len(companies),
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
                    "company_id": comp.company_id,
                    "company_name": comp.company_name,
                    "status": "active"
                }
                for comp in companies
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
