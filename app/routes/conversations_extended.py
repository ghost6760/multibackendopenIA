from flask import Blueprint, request, jsonify
from app.config.company_config import get_company_manager
from app.utils.helpers import create_success_response, create_error_response
import logging

logger = logging.getLogger(__name__)

conversations_extended_bp = Blueprint('conversations_extended', __name__, url_prefix='/api/conversations')

@conversations_extended_bp.route('/stats', methods=['GET'])
def get_conversations_stats():
    """Obtener estadísticas de conversaciones para una empresa"""
    try:
        company_id = request.args.get('company_id') or request.headers.get('X-Company-ID')
        
        if not company_id:
            return create_error_response("company_id is required", 400)
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        # Estadísticas simuladas
        stats = {
            "company_id": company_id,
            "total_conversations": 127,
            "active_conversations": 12,
            "total_messages": 1543,
            "avg_messages_per_conversation": 12.1,
            "most_used_agents": {
                "sales_agent": 45,
                "support_agent": 38,
                "router_agent": 44
            },
            "conversations_today": 8,
            "conversations_this_week": 32,
            "last_activity": "2025-01-15T14:22:00Z"
        }
        
        return create_success_response({
            "stats": stats
        })
        
    except Exception as e:
        logger.error(f"Error getting conversation stats for company {company_id}: {e}")
        return create_error_response(str(e), 500)

@conversations_extended_bp.route('/history/<user_id>', methods=['GET'])
def get_conversation_history(user_id):
    """Obtener historial de conversaciones de un usuario"""
    try:
        company_id = request.args.get('company_id') or request.headers.get('X-Company-ID')
        limit = request.args.get('limit', 50, type=int)
        
        if not company_id:
            return create_error_response("company_id is required", 400)
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        # Historial simulado
        history = [
            {
                "id": f"conv_{i}",
                "user_id": user_id,
                "company_id": company_id,
                "messages": [
                    {
                        "role": "user",
                        "content": f"Pregunta {i} del usuario",
                        "timestamp": "2025-01-15T14:00:00Z"
                    },
                    {
                        "role": "assistant",
                        "content": f"Respuesta {i} del asistente para {company_id}",
                        "agent_used": "sales_agent",
                        "timestamp": "2025-01-15T14:00:30Z"
                    }
                ],
                "created_at": "2025-01-15T14:00:00Z",
                "updated_at": "2025-01-15T14:00:30Z"
            }
            for i in range(1, min(limit + 1, 11))
        ]
        
        return create_success_response({
            "conversations": history,
            "user_id": user_id,
            "company_id": company_id,
            "total_conversations": len(history)
        })
        
    except Exception as e:
        logger.error(f"Error getting conversation history for user {user_id}: {e}")
        return create_error_response(str(e), 500)

@conversations_extended_bp.route('/clear/<user_id>', methods=['POST'])
def clear_user_conversations(user_id):
    """Limpiar conversaciones de un usuario"""
    try:
        data = request.get_json() or {}
        company_id = request.headers.get('X-Company-ID') or data.get('company_id')
        
        if not company_id:
            return create_error_response("company_id is required", 400)
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        # Limpiar conversaciones (simulado)
        logger.info(f"Clearing conversations for user {user_id} in company {company_id}")
        
        return create_success_response({
            "message": f"Conversations cleared for user {user_id}",
            "user_id": user_id,
            "company_id": company_id
        })
        
    except Exception as e:
        logger.error(f"Error clearing conversations for user {user_id}: {e}")
        return create_error_response(str(e), 500)

@conversations_extended_bp.route('/<conversation_id>/export', methods=['GET'])
def export_conversation(conversation_id):
    """Exportar una conversación"""
    try:
        company_id = request.args.get('company_id') or request.headers.get('X-Company-ID')
        format_type = request.args.get('format', 'json')
        
        if not company_id:
            return create_error_response("company_id is required", 400)
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        # Datos de conversación simulados
        conversation_data = {
            "id": conversation_id,
            "company_id": company_id,
            "export_format": format_type,
            "messages": [
                {
                    "role": "user",
                    "content": "Hola, necesito información sobre sus servicios",
                    "timestamp": "2025-01-15T14:00:00Z"
                },
                {
                    "role": "assistant",
                    "content": f"¡Hola! Estaré encantado de ayudarte con información sobre nuestros servicios de {company_id}...",
                    "agent_used": "sales_agent",
                    "timestamp": "2025-01-15T14:00:30Z"
                },
                {
                    "role": "user",
                    "content": "¿Cuáles son sus horarios?",
                    "timestamp": "2025-01-15T14:01:00Z"
                },
                {
                    "role": "assistant",
                    "content": "Nuestros horarios de atención son de lunes a viernes de 9:00 AM a 6:00 PM.",
                    "agent_used": "support_agent",
                    "timestamp": "2025-01-15T14:01:30Z"
                }
            ],
            "exported_at": "2025-01-15T15:00:00Z"
        }
        
        return create_success_response({
            "conversation": conversation_data,
            "format": format_type
        })
        
    except Exception as e:
        logger.error(f"Error exporting conversation {conversation_id}: {e}")
        return create_error_response(str(e), 500)
