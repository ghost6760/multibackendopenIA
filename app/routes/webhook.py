from flask import Blueprint, request, jsonify
from app.services.chatwoot_service import ChatwootService
from app.services.multi_agent_orchestrator import get_orchestrator_for_company
from app.models.conversation import ConversationManager
from app.config.company_config import extract_company_id_from_webhook, validate_company_context
from app.utils.validators import validate_webhook_data
from app.utils.decorators import handle_errors
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('webhook', __name__)

class WebhookError(Exception):
    """Custom exception for webhook errors"""
    def __init__(self, message, status_code=400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

@bp.route('/chatwoot', methods=['POST'])
@handle_errors
def chatwoot_webhook():
    """Handle Chatwoot webhook events with multi-tenant support"""
    try:
        data = request.get_json()
        event_type = validate_webhook_data(data)
        
        # PASO 1: Extraer company_id
        company_id = extract_company_id_from_webhook(data)
        if not validate_company_context(company_id):
            logger.error(f"Invalid company context: {company_id}")
            return jsonify({"status": "error", "message": "Invalid company context"}), 400
        
        logger.info(f"🔔 [{company_id}] WEBHOOK RECEIVED - Event: {event_type}")
        
        # PASO 2: Inicializar servicios específicos de empresa
        chatwoot_service = ChatwootService(company_id=company_id)
        conversation_manager = ConversationManager(company_id=company_id)
        
        # Obtener orquestador multi-agente específico
        orchestrator = get_orchestrator_for_company(company_id)
        if not orchestrator:
            logger.error(f"Could not get orchestrator for company: {company_id}")
            return jsonify({"status": "error", "message": "Service unavailable"}), 503
        
        # Handle conversation updates
        if event_type == "conversation_updated":
            success = chatwoot_service.handle_conversation_updated(data)
            status_code = 200 if success else 400
            return jsonify({
                "status": "conversation_updated_processed", 
                "success": success,
                "company_id": company_id
            }), status_code
        
        # Handle only message_created events
        if event_type != "message_created":
            logger.info(f"⏭️ [{company_id}] Ignoring event type: {event_type}")
            return jsonify({
                "status": "ignored_event_type", 
                "event": event_type,
                "company_id": company_id
            }), 200
        
        # Debug completo para multimedia si es necesario
        if data.get('attachments'):
            chatwoot_service.debug_webhook_data(data)
        
        # Process incoming message con contexto de empresa
        result = chatwoot_service.process_incoming_message(data, conversation_manager, orchestrator)
        
        # Enriquecer respuesta con company_id
        if isinstance(result, dict):
            result["company_id"] = company_id
        
        if result.get("ignored"):
            return jsonify(result), 200
        
        return jsonify(result), 200
        
    except WebhookError as we:
        logger.error(f"Webhook error: {we.message} (Status: {we.status_code})")
        return jsonify({
            "status": "error", 
            "message": "Error interno del servidor",
            "company_id": company_id if 'company_id' in locals() else "unknown"
        }), we.status_code
    except Exception as e:
        logger.exception("Error no manejado en webhook multi-tenant")
        return jsonify({
            "status": "error", 
            "message": "Error interno del servidor",
            "company_id": company_id if 'company_id' in locals() else "unknown"
        }), 500

@bp.route('/test', methods=['POST'])
@handle_errors  
def test_webhook():
    """Test webhook endpoint for debugging multi-tenant"""
    try:
        data = request.get_json()
        
        # Extraer company_id para pruebas
        company_id = extract_company_id_from_webhook(data)
        
        chatwoot_service = ChatwootService(company_id=company_id)
        chatwoot_service.debug_webhook_data(data)
        
        return jsonify({
            "status": "success",
            "message": "Webhook test completed",
            "company_id": company_id,
            "received_data": data
        }), 200
        
    except Exception as e:
        logger.error(f"Test webhook error: {e}")
        return jsonify({
            "status": "error", 
            "message": str(e),
            "company_id": company_id if 'company_id' in locals() else "unknown"
        }), 500
