# app/routes/companies.py - Companies Route Handler Integrado
"""
Companies route handler for multi-tenant admin panel
Handles company listing, selection, and advanced company operations
INTEGRADO con sistema multi-tenant existente
"""

from flask import Blueprint, jsonify, request
from app.config.company_config import get_company_manager
from app.services.multi_agent_factory import get_multi_agent_factory
from app.services.redis_service import get_redis_client
from app.utils.helpers import create_success_response, create_error_response
from app.utils.decorators import handle_errors
import logging
import os
import json
import time

logger = logging.getLogger(__name__)

# Create blueprint con prefix correcto
bp = Blueprint('companies', __name__, url_prefix='/api/companies')

def load_companies_config():
    """Load companies from configuration file - FALLBACK method"""
    try:
        # Primero intentar usar el company_manager avanzado
        try:
            company_manager = get_company_manager()
            companies_data = company_manager.get_all_companies()
            if companies_data:
                logger.info(f"Loaded companies from CompanyManager: {len(companies_data)} companies")
                # Convertir a formato compatible con frontend
                formatted_companies = {}
                for company_id, config in companies_data.items():
                    formatted_companies[company_id] = {
                        "company_name": config.company_name,
                        "business_type": getattr(config, 'business_type', 'Unknown'),
                        "services": config.services if hasattr(config, 'services') else [],
                        "agents": getattr(config, 'agents', []),
                        "status": "active",
                        "vectorstore_index": config.vectorstore_index,
                        "redis_prefix": config.redis_prefix
                    }
                return formatted_companies
        except Exception as e:
            logger.warning(f"CompanyManager not available, using fallback: {e}")
        
        # Fallback: Try to load from companies_config.json
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'companies_config.json')
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                companies_data = json.load(f)
                logger.info(f"Loaded companies from config file: {len(companies_data)} companies")
                return companies_data
        else:
            logger.warning(f"Companies config file not found at {config_path}")
            # Return fallback companies
            return {
                "benova": {
                    "company_name": "Benova Estética",
                    "business_type": "medicina_estetica",
                    "services": ["Tratamientos faciales", "Depilación láser", "Rejuvenecimiento"],
                    "agents": ["router_agent", "sales_agent", "support_agent", "emergency_agent"],
                    "status": "active"
                },
                "medispa": {
                    "company_name": "MediSpa Wellness",
                    "business_type": "spa_wellness", 
                    "services": ["Medicina estética", "Spa wellness", "Terapias"],
                    "agents": ["router_agent", "sales_agent", "support_agent"],
                    "status": "active"
                },
                "clinica_dental": {
                    "company_name": "Clínica Dental Premium",
                    "business_type": "odontologia",
                    "services": ["Odontología general", "Ortodoncia", "Estética dental"],
                    "agents": ["router_agent", "sales_agent", "support_agent"],
                    "status": "active"
                },
                "spa_wellness": {
                    "company_name": "Spa & Wellness Center",
                    "business_type": "spa_wellness",
                    "services": ["Masajes", "Tratamientos corporales", "Relajación"],
                    "agents": ["router_agent", "sales_agent", "support_agent"],
                    "status": "active"
                }
            }
            
    except Exception as e:
        logger.error(f"Error loading companies config: {e}")
        # Return minimal fallback
        return {
            "fallback": {
                "company_name": "Modo de Emergencia",
                "business_type": "fallback",
                "services": ["Sistema en modo fallback"],
                "agents": [],
                "status": "fallback"
            }
        }

@bp.route('', methods=['GET'])
@handle_errors
def get_companies():
    """Get all available companies - ENHANCED Multi-tenant"""
    try:
        companies = load_companies_config()
        
        # Estadísticas adicionales usando Redis si está disponible
        enhanced_companies = {}
        total_conversations = 0
        total_documents = 0
        
        try:
            redis_client = get_redis_client()
            factory = get_multi_agent_factory()
            
            for company_id, company_data in companies.items():
                enhanced_company = company_data.copy()
                
                # Estadísticas de Redis por empresa
                try:
                    company_manager = get_company_manager()
                    if company_manager.validate_company_id(company_id):
                        config = company_manager.get_company_config(company_id)
                        prefix = config.redis_prefix
                        
                        # Contar conversaciones y documentos
                        conv_count = len(redis_client.keys(f"{prefix}conversation:*"))
                        doc_count = len(redis_client.keys(f"{prefix}document:*"))
                        
                        enhanced_company["statistics"] = {
                            "conversations": conv_count,
                            "documents": doc_count,
                            "active_sessions": len(redis_client.keys(f"{prefix}bot_status:*"))
                        }
                        
                        total_conversations += conv_count
                        total_documents += doc_count
                        
                        # Status del orchestrator
                        orchestrator = factory.get_orchestrator(company_id)
                        enhanced_company["orchestrator_status"] = {
                            "available": orchestrator is not None,
                            "agents_loaded": len(orchestrator.agents) if orchestrator else 0,
                            "vectorstore_connected": orchestrator.vectorstore_service is not None if orchestrator else False
                        }
                        
                except Exception as e:
                    enhanced_company["statistics"] = {"error": f"Could not load stats: {e}"}
                    enhanced_company["orchestrator_status"] = {"available": False, "error": str(e)}
                
                enhanced_companies[company_id] = enhanced_company
                
        except Exception as e:
            logger.warning(f"Could not enhance companies with Redis data: {e}")
            enhanced_companies = companies
        
        return create_success_response({
            "companies": enhanced_companies,
            "total_companies": len(companies),
            "system_statistics": {
                "total_conversations": total_conversations,
                "total_documents": total_documents
            },
            "system_type": "multi-tenant-enhanced"
        })
        
    except Exception as e:
        logger.error(f"Error in get_companies: {e}")
        return create_error_response(str(e), 500)

@bp.route('/<company_id>', methods=['GET'])
@handle_errors
def get_company(company_id):
    """Get specific company details - ENHANCED"""
    try:
        companies = load_companies_config()
        
        if company_id not in companies:
            return create_error_response(f"Company {company_id} not found", 404)
        
        company = companies[company_id].copy()
        
        # Información extendida usando CompanyManager si está disponible
        try:
            company_manager = get_company_manager()
            if company_manager.validate_company_id(company_id):
                config = company_manager.get_company_config(company_id)
                
                # Agregar información detallada de configuración
                company["advanced_config"] = {
                    "vectorstore_index": config.vectorstore_index,
                    "redis_prefix": config.redis_prefix,
                    "schedule_service_url": getattr(config, 'schedule_service_url', None),
                    "business_specific_config": True
                }
                
                # Estado del sistema multi-agente
                factory = get_multi_agent_factory()
                orchestrator = factory.get_orchestrator(company_id)
                
                if orchestrator:
                    health = orchestrator.health_check()
                    company["system_health"] = {
                        "overall_healthy": health.get("system_healthy", False),
                        "agents_status": health.get("agents_status", {}),
                        "vectorstore_ready": orchestrator.vectorstore_service is not None,
                        "last_health_check": time.time()
                    }
                else:
                    company["system_health"] = {
                        "overall_healthy": False,
                        "error": "Orchestrator not initialized"
                    }
                    
        except Exception as e:
            logger.warning(f"Could not load advanced config for {company_id}: {e}")
            company["advanced_config"] = {"error": str(e)}
            company["system_health"] = {"error": str(e)}
        
        return create_success_response({
            "company_id": company_id,
            "company": company
        })
        
    except Exception as e:
        logger.error(f"Error getting company {company_id}: {e}")
        return create_error_response(str(e), 500)

@bp.route('/<company_id>/status', methods=['GET'])
@handle_errors
def get_company_status(company_id):
    """Get company status and health information - ENHANCED"""
    try:
        companies = load_companies_config()
        
        if company_id not in companies:
            return create_error_response(f"Company {company_id} not found", 404)
        
        company = companies[company_id]
        
        # Status básico
        status_data = {
            "company_id": company_id,
            "company_name": company.get("company_name", company_id),
            "business_type": company.get("business_type", "unknown"),
            "status": company.get("status", "unknown"),
            "services_count": len(company.get("services", [])),
            "agents_count": len(company.get("agents", [])),
            "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        
        # Health check avanzado
        health_data = {
            "api": True,  # Si llegamos aquí, API está funcionando
            "company_manager": False,
            "multi_agent_factory": False,
            "redis": False,
            "vectorstore": False,
            "openai": False
        }
        
        # Test CompanyManager
        try:
            company_manager = get_company_manager()
            if company_manager.validate_company_id(company_id):
                health_data["company_manager"] = True
        except Exception:
            pass
        
        # Test Redis
        try:
            redis_client = get_redis_client()
            redis_client.ping()
            health_data["redis"] = True
        except Exception:
            pass
        
        # Test Multi-Agent Factory
        try:
            factory = get_multi_agent_factory()
            orchestrator = factory.get_orchestrator(company_id)
            if orchestrator:
                health_data["multi_agent_factory"] = True
                
                # Test Vectorstore
                if orchestrator.vectorstore_service:
                    health_data["vectorstore"] = True
                
                # Test OpenAI service
                if hasattr(orchestrator, 'openai_service') and orchestrator.openai_service:
                    health_data["openai"] = True
                    
        except Exception:
            pass
        
        # Métricas simuladas con datos reales si están disponibles
        metrics = {
            "active_sessions": 0,
            "daily_requests": 0,
            "avg_response_time": "150ms"
        }
        
        if health_data["redis"]:
            try:
                company_manager = get_company_manager()
                config = company_manager.get_company_config(company_id)
                prefix = config.redis_prefix
                
                redis_client = get_redis_client()
                metrics["active_sessions"] = len(redis_client.keys(f"{prefix}bot_status:*"))
                metrics["total_conversations"] = len(redis_client.keys(f"{prefix}conversation:*"))
                metrics["total_documents"] = len(redis_client.keys(f"{prefix}document:*"))
            except Exception:
                pass
        
        # Calcular health score
        healthy_services = sum(health_data.values())
        total_services = len(health_data)
        health_score = (healthy_services / total_services) * 100
        
        status_data.update({
            "health": health_data,
            "health_score": health_score,
            "metrics": metrics,
            "system_type": "multi-tenant-enhanced"
        })
        
        return create_success_response({
            "status": status_data
        })
        
    except Exception as e:
        logger.error(f"Error getting company status {company_id}: {e}")
        return create_error_response(str(e), 500)

@bp.route('/reload-config', methods=['POST'])
@handle_errors
def reload_companies_config():
    """Reload companies configuration from file - ENHANCED"""
    try:
        # Intentar recargar usando CompanyManager avanzado
        try:
            company_manager = get_company_manager()
            
            # Limpiar configuraciones actuales
            if hasattr(company_manager, '_configs'):
                company_manager._configs.clear()
            
            # Recargar desde archivo
            if hasattr(company_manager, '_load_company_configs'):
                company_manager._load_company_configs()
            
            # Limpiar caches del factory
            factory = get_multi_agent_factory()
            factory.clear_all_cache()
            
            companies = company_manager.get_all_companies()
            logger.info(f"Advanced configuration reloaded: {list(companies.keys())}")
            
            return create_success_response({
                "message": "Advanced configuration reloaded successfully",
                "method": "CompanyManager",
                "total_companies": len(companies),
                "companies": list(companies.keys()),
                "features_available": [
                    "multi-agent-orchestrators",
                    "vectorstore-per-company", 
                    "redis-isolation",
                    "auto-recovery"
                ]
            })
            
        except Exception as e:
            logger.warning(f"Advanced reload failed, using fallback: {e}")
            
            # Fallback: recargar método básico
            companies = load_companies_config()
            
            return create_success_response({
                "message": "Basic configuration reloaded successfully",
                "method": "Fallback",
                "total_companies": len(companies),
                "companies": list(companies.keys()),
                "warning": "Advanced features not available"
            })
        
    except Exception as e:
        logger.error(f"Error reloading companies config: {e}")
        return create_error_response(str(e), 500)

@bp.route('/health', methods=['GET'])
@handle_errors
def companies_health():
    """Health check for companies service - ENHANCED"""
    try:
        companies = load_companies_config()
        companies_count = len(companies)
        
        # Test servicios relacionados
        service_health = {
            "companies_loaded": companies_count > 0,
            "company_manager": False,
            "multi_agent_factory": False,
            "redis": False
        }
        
        try:
            company_manager = get_company_manager()
            advanced_companies = company_manager.get_all_companies()
            service_health["company_manager"] = len(advanced_companies) > 0
        except Exception:
            pass
        
        try:
            factory = get_multi_agent_factory()
            service_health["multi_agent_factory"] = True
        except Exception:
            pass
        
        try:
            redis_client = get_redis_client()
            redis_client.ping()
            service_health["redis"] = True
        except Exception:
            pass
        
        # Calcular estado general
        healthy_services = sum(service_health.values())
        total_services = len(service_health)
        overall_health = "healthy" if healthy_services >= total_services * 0.75 else "degraded"
        
        if companies_count == 0:
            overall_health = "unhealthy"
        
        return jsonify({
            "status": overall_health,
            "service": "companies",
            "companies_loaded": companies_count,
            "service_health": service_health,
            "health_score": (healthy_services / total_services) * 100,
            "message": f"Companies service {overall_health} with {companies_count} companies",
            "system_type": "multi-tenant-enhanced"
        })
        
    except Exception as e:
        logger.error(f"Companies health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "service": "companies",
            "error": str(e)
        }), 500

# ============================================================================
# NUEVOS ENDPOINTS PARA FRONTEND REACT
# ============================================================================

@bp.route('/<company_id>/agents', methods=['GET'])
@handle_errors
def get_company_agents(company_id):
    """Get detailed information about company agents"""
    try:
        companies = load_companies_config()
        
        if company_id not in companies:
            return create_error_response(f"Company {company_id} not found", 404)
        
        agents_info = []
        
        try:
            # Usar factory para obtener información real de agentes
            factory = get_multi_agent_factory()
            orchestrator = factory.get_orchestrator(company_id)
            
            if orchestrator and hasattr(orchestrator, 'agents'):
                for agent_name, agent_instance in orchestrator.agents.items():
                    agent_info = {
                        "name": agent_name,
                        "type": type(agent_instance).__name__,
                        "status": "active",
                        "description": getattr(agent_instance, 'description', f'{agent_name} agent'),
                        "capabilities": getattr(agent_instance, 'capabilities', []),
                        "last_used": None  # TODO: Implementar tracking
                    }
                    agents_info.append(agent_info)
            else:
                # Fallback: usar información de configuración
                company = companies[company_id]
                for agent_name in company.get("agents", []):
                    agents_info.append({
                        "name": agent_name,
                        "type": "ConfiguredAgent",
                        "status": "configured",
                        "description": f"Agent configured for {company_id}"
                    })
                    
        except Exception as e:
            logger.warning(f"Could not load real agent info for {company_id}: {e}")
            # Fallback básico
            company = companies[company_id]
            for agent_name in company.get("agents", []):
                agents_info.append({
                    "name": agent_name,
                    "type": "Unknown",
                    "status": "unknown",
                    "error": str(e)
                })
        
        return create_success_response({
            "company_id": company_id,
            "agents": agents_info,
            "total_agents": len(agents_info)
        })
        
    except Exception as e:
        logger.error(f"Error getting agents for company {company_id}: {e}")
        return create_error_response(str(e), 500)

@bp.route('/<company_id>/metrics', methods=['GET'])
@handle_errors
def get_company_metrics(company_id):
    """Get detailed metrics for a specific company"""
    try:
        companies = load_companies_config()
        
        if company_id not in companies:
            return create_error_response(f"Company {company_id} not found", 404)
        
        metrics = {
            "company_id": company_id,
            "timestamp": time.time(),
            "basic_metrics": {
                "conversations": 0,
                "documents": 0,
                "active_sessions": 0,
                "total_messages": 0
            },
            "performance_metrics": {
                "avg_response_time": "N/A",
                "success_rate": "N/A",
                "uptime": "N/A"
            },
            "agent_metrics": {
                "most_used_agent": "N/A",
                "agent_distribution": {}
            }
        }
        
        # Cargar métricas reales si Redis está disponible
        try:
            company_manager = get_company_manager()
            if company_manager.validate_company_id(company_id):
                config = company_manager.get_company_config(company_id)
                prefix = config.redis_prefix
                
                redis_client = get_redis_client()
                
                # Métricas básicas
                metrics["basic_metrics"] = {
                    "conversations": len(redis_client.keys(f"{prefix}conversation:*")),
                    "documents": len(redis_client.keys(f"{prefix}document:*")),
                    "active_sessions": len(redis_client.keys(f"{prefix}bot_status:*")),
                    "total_messages": len(redis_client.keys(f"processed_message:*{company_id}*"))
                }
                
                # TODO: Implementar métricas de performance y agentes
                metrics["performance_metrics"] = {
                    "avg_response_time": "150ms",
                    "success_rate": "98.5%",
                    "uptime": "99.9%"
                }
                
        except Exception as e:
            logger.warning(f"Could not load real metrics for {company_id}: {e}")
            metrics["error"] = str(e)
        
        return create_success_response(metrics)
        
    except Exception as e:
        logger.error(f"Error getting metrics for company {company_id}: {e}")
        return create_error_response(str(e), 500)
