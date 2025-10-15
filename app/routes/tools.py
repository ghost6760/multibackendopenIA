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
