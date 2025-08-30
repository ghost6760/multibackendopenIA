from flask import Blueprint, request, jsonify, send_file
from app.services.openai_service import OpenAIService
from app.services.multi_agent_factory import get_multi_agent_factory
from app.models.conversation import ConversationManager
from app.config.company_config import get_company_manager
from app.utils.decorators import handle_errors
from app.utils.helpers import create_success_response, create_error_response
import logging
import tempfile
import os

logger = logging.getLogger(__name__)

bp = Blueprint('multimedia', __name__)

def _get_company_id_from_request() -> str:
    """Extraer company_id de headers, form data o usar por defecto"""
    # Método 1: Header específico
    company_id = request.headers.get('X-Company-ID')
    
    # Método 2: Form data (para uploads)
    if not company_id and request.form:
        company_id = request.form.get('company_id')
    
    # Método 3: Query parameter
    if not company_id:
        company_id = request.args.get('company_id')
    
    # Método 4: JSON body
    if not company_id and request.is_json:
        data = request.get_json()
        company_id = data.get('company_id') if data else None
    
    # Por defecto
    if not company_id:
        company_id = 'benova'
    
    return company_id

@bp.route('/process-voice', methods=['POST'])
@handle_errors
def process_voice_message():
    """Process voice messages - Multi-tenant"""
    try:
        company_id = _get_company_id_from_request()
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        if 'audio' not in request.files:
            return create_error_response("No audio file provided", 400)
        
        audio_file = request.files['audio']
        user_id = request.form.get('user_id')
        
        if not user_id:
            return create_error_response("User ID is required", 400)
        
        # Save file temporarily
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                audio_file.save(temp_file.name)
                temp_path = temp_file.name
            
            # Transcribe audio
            openai_service = OpenAIService()
            transcript = openai_service.transcribe_audio(temp_path)
            
            logger.info(f"[{company_id}] Audio transcribed for user {user_id}: {len(transcript)} chars")
            
            # Process with multi-agent system específico de empresa
            manager = ConversationManager(company_id=company_id)
            factory = get_multi_agent_factory()
            orchestrator = factory.get_orchestrator(company_id)
            
            if not orchestrator:
                return create_error_response(f"Multi-agent system not available for company: {company_id}", 503)
            
            response, agent_used = orchestrator.get_response(
                question="",  # Empty question since we use media_context
                user_id=user_id,
                conversation_manager=manager,
                media_type="voice",
                media_context=transcript
            )
            
            # Convert response to audio if requested
            return_audio = request.form.get('return_audio', 'false').lower() == 'true'
            if return_audio:
                try:
                    audio_response_path = openai_service.text_to_speech(response)
                    return send_file(audio_response_path, mimetype="audio/mpeg")
                except Exception as tts_error:
                    logger.warning(f"[{company_id}] TTS failed: {tts_error}")
                    # Continue with text response
            
            return create_success_response({
                "company_id": company_id,
                "transcript": transcript,
                "response": response,
                "agent_used": agent_used,
                "user_id": user_id,
                "media_type": "voice"
            })
            
        finally:
            # Cleanup temp file
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
        
    except Exception as e:
        logger.error(f"[{company_id if 'company_id' in locals() else 'unknown'}] Error processing voice message: {e}")
        return create_error_response("Failed to process voice message", 500)

@bp.route('/process-image', methods=['POST'])
@handle_errors
def process_image_message():
    """Process image messages - Multi-tenant"""
    try:
        company_id = _get_company_id_from_request()
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        if 'image' not in request.files:
            return create_error_response("No image file provided", 400)
        
        image_file = request.files['image']
        user_id = request.form.get('user_id')
        question = request.form.get('question', '').strip()
        
        if not user_id:
            return create_error_response("User ID is required", 400)
        
        # Analyze image
        openai_service = OpenAIService()
        
        # Create company-specific prompt for image analysis
        config = company_manager.get_company_config(company_id)
        company_context = f"enfocándote en elementos relevantes para {config.services} en {config.company_name}" if config else "enfocándote en aspectos relevantes"
        
        # Temporarily save image for analysis (OpenAI service handles the analysis)
        image_description = openai_service.analyze_image(image_file)
        
        logger.info(f"[{company_id}] Image analyzed for user {user_id}: {len(image_description)} chars")
        
        # Process with company-specific multi-agent system
        manager = ConversationManager(company_id=company_id)
        factory = get_multi_agent_factory()
        orchestrator = factory.get_orchestrator(company_id)
        
        if not orchestrator:
            return create_error_response(f"Multi-agent system not available for company: {company_id}", 503)
        
        response, agent_used = orchestrator.get_response(
            question=question,
            user_id=user_id,
            conversation_manager=manager,
            media_type="image",
            media_context=image_description
        )
        
        return create_success_response({
            "company_id": company_id,
            "image_description": image_description,
            "response": response,
            "agent_used": agent_used,
            "user_id": user_id,
            "question": question,
            "media_type": "image"
        })
        
    except Exception as e:
        logger.error(f"[{company_id if 'company_id' in locals() else 'unknown'}] Error processing image message: {e}")
        return create_error_response("Failed to process image message", 500)

@bp.route('/test-multimedia', methods=['POST'])
@handle_errors
def test_multimedia_processing():
    """Test multimedia processing without conversation context - Multi-tenant"""
    try:
        company_id = _get_company_id_from_request()
        
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        media_type = request.form.get('media_type', 'text')
        
        if media_type == 'voice' and 'audio' in request.files:
            audio_file = request.files['audio']
            
            # Save temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                audio_file.save(temp_file.name)
                temp_path = temp_file.name
            
            try:
                openai_service = OpenAIService()
                transcript = openai_service.transcribe_audio(temp_path)
                
                logger.info(f"[{company_id}] Voice test completed: {len(transcript)} chars")
                
                return create_success_response({
                    "company_id": company_id,
                    "media_type": "voice",
                    "transcript": transcript,
                    "processing_success": True,
                    "file_size": os.path.getsize(temp_path)
                })
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        
        elif media_type == 'image' and 'image' in request.files:
            image_file = request.files['image']
            
            openai_service = OpenAIService()
            description = openai_service.analyze_image(image_file)
            
            logger.info(f"[{company_id}] Image test completed: {len(description)} chars")
            
            return create_success_response({
                "company_id": company_id,
                "media_type": "image",
                "description": description,
                "processing_success": True
            })
        
        else:
            # Stats generales del sistema
            return create_success_response({
                "voice_enabled": current_app.config.get('VOICE_ENABLED', False),
                "image_enabled": current_app.config.get('IMAGE_ENABLED', False),
                "openai_model": current_app.config.get('MODEL_NAME', 'gpt-4o-mini'),
                "system_type": "multi-tenant-multimedia",
                "message": "Use ?show_all=true for per-company stats"
            })
            
    except Exception as e:
        return create_error_response(f"Failed to get multimedia stats: {e}", 500)
            return create_error_response("Invalid media_type or missing file", 400)
            
    except Exception as e:
        logger.error(f"[{company_id if 'company_id' in locals() else 'unknown'}] Error in multimedia test: {e}")
        return create_error_response("Multimedia test failed", 500)

@bp.route('/capabilities/<company_id>', methods=['GET'])
@handle_errors
def get_multimedia_capabilities(company_id):
    """Get multimedia capabilities for a specific company"""
    try:
        # Validar empresa
        company_manager = get_company_manager()
        if not company_manager.validate_company_id(company_id):
            return create_error_response(f"Invalid company_id: {company_id}", 400)
        
        config = company_manager.get_company_config(company_id)
        
        # Check service capabilities
        openai_service = OpenAIService()
        capabilities = {
            "voice_transcription": {
                "available": hasattr(openai_service, 'transcribe_audio'),
                "enabled": current_app.config.get('VOICE_ENABLED', False),
                "formats_supported": ["mp3", "wav", "m4a", "ogg"]
            },
            "image_analysis": {
                "available": hasattr(openai_service, 'analyze_image'),
                "enabled": current_app.config.get('IMAGE_ENABLED', False),
                "formats_supported": ["jpg", "jpeg", "png", "gif", "webp"]
            },
            "text_to_speech": {
                "available": hasattr(openai_service, 'text_to_speech'),
                "enabled": current_app.config.get('VOICE_ENABLED', False),
                "voice": "nova"
            }
        }
        
        # Company-specific settings
        company_info = {
            "company_id": company_id,
            "company_name": config.company_name,
            "services": config.services,
            "specialized_analysis": f"Análisis optimizado para {config.services}"
        }
        
        return create_success_response({
            "company": company_info,
            "capabilities": capabilities,
            "system_ready": all(cap["available"] for cap in capabilities.values())
        })
        
    except Exception as e:
        return create_error_response(f"Failed to get capabilities for {company_id}: {e}", 500)

@bp.route('/stats', methods=['GET'])
@handle_errors
def get_multimedia_stats():
    """Get multimedia processing statistics across companies"""
    try:
        show_all = request.args.get('show_all', 'false').lower() == 'true'
        
        if show_all:
            company_manager = get_company_manager()
            companies = company_manager.get_all_companies()
            
            stats = {}
            for company_id, config in companies.items():
                # En un sistema real, estos stats vendrían de Redis/base de datos
                stats[company_id] = {
                    "company_name": config.company_name,
                    "voice_messages_processed": 0,  # Placeholder
                    "images_analyzed": 0,           # Placeholder
                    "tts_generated": 0,             # Placeholder
                    "last_activity": None          # Placeholder
                }
            
            return create_success_response({
                "total_companies": len(companies),
                "multimedia_stats": stats,
                "system_type": "multi-tenant"
            })
        else:
