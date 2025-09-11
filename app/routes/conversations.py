from flask import Blueprint, request, jsonify
from app.models.conversation import ConversationManager
from app.services.multi_agent_factory import get_multi_agent_factory
from app.config.company_config import get_company_manager
from app.utils.decorators import handle_errors
from app.utils.helpers import create_success_response, create_error_response
import logging
import time

logger = logging.getLogger(__name__)

bp = Blueprint('conversations', __name__)

def _get_company_id_from_request() -> str:
    """Extraer company_id de headers o usar por defecto"""
    company_id = request.headers.get('X-Company-ID')
    if not company_id:
        company_id = request.args.get('company_id')
    if not company_id and request.is_json:
        data = request.get_json()
        company_id = data.get('company_id') if data else None
    if not company_id:
        company_id = 'benova'
    return company_id

@bp.route('', methods=['GET'])
@handle_errors
def list_conversations():
    """List all conversations with pagination - Multi-tenant"""
    try:
        company_id = _get_company_id_from_request()
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        page = int(request.args.get('page', 1))
        page_size = min(int(request.args.get('page_size', 50)), 100)
        
        manager = ConversationManager(company_id=company_id)
        conversations = manager.list_conversations(page, page_size)
        
        return create_success_response(conversations)
        
    except Exception as e:
        logger.error(f"Error listing conversations for company {company_id if 'company_id' in locals() else 'unknown'}: {e}")
        return create_error_response("Failed to list conversations", 500)

@bp.route('/<user_id>', methods=['GET'])
@handle_errors
def get_conversation(user_id):
    """Get a specific conversation history - Multi-tenant"""
    try:
        company_id = _get_company_id_from_request()
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        manager = ConversationManager(company_id=company_id)
        history = manager.get_conversation_details(user_id)
        
        if not history:
            return create_error_response(f"Conversation not found for user {user_id} in company {company_id}", 404)
        
        return create_success_response(history)
        
    except Exception as e:
        logger.error(f"Error getting conversation for company {company_id if 'company_id' in locals() else 'unknown'}: {e}")
        return create_error_response("Failed to get conversation", 500)

@bp.route('/<user_id>', methods=['DELETE'])
@handle_errors
def delete_conversation(user_id):
    """Delete a conversation - Multi-tenant"""
    try:
        company_id = _get_company_id_from_request()
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        manager = ConversationManager(company_id=company_id)
        success = manager.clear_conversation(user_id)
        
        if success:
            logger.info(f"✅ [{company_id}] Conversation {user_id} deleted")
            return create_success_response({
                "company_id": company_id,
                "message": f"Conversation {user_id} deleted"
            })
        else:
            return create_error_response("Failed to delete conversation", 500)
        
    except Exception as e:
        logger.error(f"Error deleting conversation for company {company_id if 'company_id' in locals() else 'unknown'}: {e}")
        return create_error_response("Failed to delete conversation", 500)

@bp.route('/<user_id>/test', methods=['POST'])
@handle_errors
def test_conversation(user_id):
    """Test conversation with a specific user - Multi-tenant"""
    try:
        company_id = _get_company_id_from_request()
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        data = request.get_json()
        if not data or 'message' not in data:
            return create_error_response("Message is required", 400)
        
        message = data['message'].strip()
        if not message:
            return create_error_response("Message cannot be empty", 400)

        # 🆕 LOGS DETALLADOS COMO VISTA PREVIA
        logger.info(f"Getting prompts for company: {company_id}")
        
        # Verificar prompts disponibles
        from app.services.prompt_service import get_prompt_service
        prompt_service = get_prompt_service()
        agents_data = prompt_service.get_company_prompts(company_id)
        logger.debug(f"Retrieved prompts for {company_id}: {len(agents_data)} agents")
        
        logger.info(f"🔍 [TESTER] Testing conversation for {company_id}")
        logger.info(f"   → User: {user_id}")
        logger.info(f"   → Message: {message[:100]}...")
        
        # Servicios específicos de empresa
        logger.info(f"ConversationManager initialized for company: {company_id}")
        manager = ConversationManager(company_id=company_id)
        factory = get_multi_agent_factory()
        orchestrator = factory.get_orchestrator(company_id)
        
        if not orchestrator:
            return create_error_response(f"Multi-agent system not available for company: {company_id}", 503)
        
        response, agent_used = orchestrator.get_response(message, user_id, manager)
        
        return create_success_response({
            "company_id": company_id,
            "user_id": user_id,
            "user_message": message,
            "bot_response": response,
            "agent_used": agent_used,
            "timestamp": time.time()
        })
        
    except Exception as e:
        logger.error(f"Error testing conversation for company {company_id if 'company_id' in locals() else 'unknown'}: {e}")
        return create_error_response("Failed to test conversation", 500)
