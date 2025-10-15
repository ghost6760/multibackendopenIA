# ✅ CREAR: app/routes/tools.py (NUEVO ARCHIVO)

from flask import Blueprint, jsonify, request
from app.workflows.tools_library import ToolsLibrary
from app.config.company_config import get_company_config
from app.utils.decorators import require_company_context, handle_errors

bp = Blueprint('tools', __name__, url_prefix='/api/tools')

@bp.route('/available', methods=['GET'])
@handle_errors
def get_available_tools():
    """
    Lista todas las tools disponibles en el sistema.
    
    NO requiere company_id - es info general.
    """
    tools = ToolsLibrary.get_all_tools()
    
    return jsonify({
        "total": len(tools),
        "tools": {
            name: {
                "name": tool.name,
                "category": tool.category,
                "description": tool.description,
                "provider": tool.provider,
                "enabled_by_default": tool.enabled_by_default
            }
            for name, tool in tools.items()
        }
    }), 200

@bp.route('/company/<company_id>', methods=['GET'])
@require_company_context
@handle_errors
def get_company_tools(company_id: str):
    """
    Tools habilitadas para una empresa específica.
    """
    company_config = get_company_config(company_id)
    
    if not company_config:
        return jsonify({"error": "Company not found"}), 404
    
    enabled_tools = ToolsLibrary.get_enabled_tools_for_company(
        company_config.__dict__
    )
    
    tools_detail = {
        name: ToolsLibrary.get_tool(name).__dict__
        for name in enabled_tools
        if ToolsLibrary.get_tool(name)
    }
    
    return jsonify({
        "company_id": company_id,
        "enabled_tools": enabled_tools,
        "tools": tools_detail
    }), 200

@bp.route('/company/<company_id>', methods=['PUT'])
@require_company_context
@handle_errors
def update_company_tools(company_id: str):
    """
    Actualiza las tools habilitadas para una empresa.
    
    Body:
    {
        "enabled_tools": ["knowledge_base", "google_calendar", ...]
    }
    """
    data = request.json
    enabled_tools = data.get("enabled_tools", [])
    
    # Validar que todas las tools existen
    all_tools = ToolsLibrary.get_all_tools()
    invalid_tools = [t for t in enabled_tools if t not in all_tools]
    
    if invalid_tools:
        return jsonify({
            "error": "Invalid tools",
            "invalid_tools": invalid_tools
        }), 400
    
    # Actualizar config de empresa
    # TODO: Implementar update en CompanyConfigManager
    
    return jsonify({
        "status": "success",
        "company_id": company_id,
        "enabled_tools": enabled_tools
    }), 200


@bp.route('/company/<company_id>/status', methods=['GET'])
@require_company_context
@handle_errors
def get_company_tools_status(company_id: str):
    """
    Obtener estado de configuración de tools para una empresa.
    Incluye qué servicios están disponibles.
    
    GET /api/tools/company/benova/status
    """
    try:
        from app.services.multi_agent_factory import get_orchestrator_for_company
        from app.workflows.tool_executor import ToolExecutor
        
        # Obtener orchestrator de la empresa
        orchestrator = get_orchestrator_for_company(company_id)
        if not orchestrator:
            return jsonify({
                "error": "Orchestrator not found for company"
            }), 404
        
        # Crear tool executor temporal para verificar
        tool_executor = ToolExecutor(company_id)
        
        # Inyectar servicios disponibles
        if orchestrator.vectorstore_service:
            tool_executor.set_vectorstore_service(orchestrator.vectorstore_service)
        
        # TODO: Inyectar otros servicios cuando estén disponibles en orchestrator
        
        # Obtener estado de tools
        tools_status = tool_executor.get_available_tools()
        
        return jsonify({
            "company_id": company_id,
            "tools_status": tools_status,
            "services_injected": {
                "vectorstore": orchestrator.vectorstore_service is not None,
                "calendar": hasattr(orchestrator, 'calendar_service') and orchestrator.calendar_service is not None,
                "chatwoot": hasattr(orchestrator, 'chatwoot_service') and orchestrator.chatwoot_service is not None,
                "multimedia": hasattr(orchestrator, 'multimedia_service') and orchestrator.multimedia_service is not None
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting tools status for {company_id}: {e}")
        return jsonify({
            "error": str(e)
        }), 500
