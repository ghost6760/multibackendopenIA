from flask import Blueprint, jsonify, current_app
from app.services.redis_service import get_redis_client
from app.services.multi_agent_factory import get_multi_agent_factory
from app.services.openai_service import OpenAIService
from app.config.company_config import get_company_manager
from app.utils.decorators import handle_errors
import time
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('health', __name__)

@bp.route('', methods=['GET'])
def health_check():
    """Main health check endpoint - Multi-tenant aware"""
    try:
        # Verificar componentes básicos
        basic_components = check_basic_components()
        
        # Verificar empresas
        company_manager = get_company_manager()
        companies = company_manager.get_all_companies()
        
        # Health check de multi-agente por empresa
        factory = get_multi_agent_factory()
        company_health = factory.health_check_all()
        
        # Estadísticas Redis por empresa
        redis_client = get_redis_client()
        company_stats = {}
        
        for company_id in companies.keys():
            try:
                conversation_pattern = f"{company_id}:conversation:*"
                document_pattern = f"{company_id}:document:*"
                bot_status_pattern = f"bot_status:*"  # Shared across companies
                
                company_stats[company_id] = {
                    "conversations": len(redis_client.keys(conversation_pattern)),
                    "documents": len(redis_client.keys(document_pattern)),
                    "vectorstore_index": companies[company_id].vectorstore_index
                }
            except Exception as e:
                company_stats[company_id] = {"error": str(e)}
        
        # Determinar salud general
        all_companies_healthy = all(
            health.get("system_healthy", False) 
            for health in company_health.values()
        )
        
        basic_healthy = all("error" not in str(status) for status in basic_components.values())
        overall_healthy = basic_healthy and all_companies_healthy
        
        response_data = {
            "timestamp": time.time(),
            "system_type": "multi-tenant-multi-agent",
            "basic_components": basic_components,
            "companies": {
                "total": len(companies),
                "configured": list(companies.keys()),
                "health": company_health,
                "stats": company_stats
            },
            "configuration": {
                "model": current_app.config['MODEL_NAME'],
                "embedding_model": current_app.config['EMBEDDING_MODEL'],
                "max_tokens": current_app.config['MAX_TOKENS'],
                "temperature": current_app.config['TEMPERATURE']
            }
        }
        
        status_code = 200 if overall_healthy else 503
        status = "healthy" if overall_healthy else "unhealthy"
        
        return jsonify({"status": status, **response_data}), status_code
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time(),
            "system_type": "multi-tenant-multi-agent"
        }), 503

@bp.route('/company/<company_id>', methods=['GET'])
@handle_errors
def company_health_check(company_id):
    """Health check específico de una empresa"""
    try:
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return jsonify({
                "status": "error",
                "message": f"Invalid company_id: {company_id}"
            }), 400
        
        # Health check del orquestrador específico
        factory = get_multi_agent_factory()
        orchestrator = factory.get_orchestrator(company_id)
        
        if not orchestrator:
            return jsonify({
                "status": "unhealthy",
                "company_id": company_id,
                "error": "Could not initialize orchestrator"
            }), 503
        
        health = orchestrator.health_check()
        status_code = 200 if health.get("system_healthy", False) else 503
        
        return jsonify(health), status_code
        
    except Exception as e:
        return jsonify({
            "status": "error", 
            "company_id": company_id,
            "message": str(e)
        }), 500

@bp.route('/companies', methods=['GET'])
@handle_errors
def companies_overview():
    """Overview de todas las empresas configuradas"""
    try:
        company_manager = get_company_manager()
        companies = company_manager.get_all_companies()
        
        company_overview = {}
        for company_id, config in companies.items():
            company_overview[company_id] = {
                "company_name": config.company_name,
                "services": config.services,
                "vectorstore_index": config.vectorstore_index,
                "schedule_service_url": config.schedule_service_url,
                "redis_prefix": config.redis_prefix
            }
        
        return jsonify({
            "total_companies": len(companies),
            "companies": company_overview
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

def check_basic_components():
    """Check health of basic system components"""
    components = {}
    
    # Check Redis
    try:
        redis_client = get_redis_client()
        redis_client.ping()
        components["redis"] = "connected"
    except Exception as e:
        components["redis"] = f"error: {str(e)}"
    
    # Check OpenAI
    try:
        openai_service = OpenAIService()
        openai_service.test_connection()
        components["openai"] = "connected"
    except Exception as e:
        components["openai"] = f"error: {str(e)}"
    
    return components
