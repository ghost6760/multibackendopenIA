from app.services.redis_service import get_redis_client
from app.models.conversation import ConversationManager
from app.services.multi_agent_orchestrator import MultiAgentOrchestrator
from app.services.openai_service import OpenAIService
from app.config.company_config import get_company_config
from flask import current_app
import requests
import logging
import json
import time
import tempfile
import os
import base64
from io import BytesIO
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class ChatwootService:
    """Service for handling Chatwoot interactions - Multi-tenant"""

    def __init__(self, company_id: str = None):
        self.company_id = company_id or "benova"
        self.company_config = get_company_config(self.company_id)
        
        if not self.company_config:
            logger.warning(f"No configuration found for company: {self.company_id}")
            # Usar configuración por defecto de Chatwoot
            self.api_key = current_app.config['CHATWOOT_API_KEY']
            self.base_url = current_app.config['CHATWOOT_BASE_URL']
            self.account_id = current_app.config['ACCOUNT_ID']
        else:
            # Usar configuración específica de empresa si está disponible
            # Por ahora usamos la configuración global pero se puede extender
            self.api_key = current_app.config['CHATWOOT_API_KEY']
            self.base_url = current_app.config['CHATWOOT_BASE_URL']
            self.account_id = current_app.config['ACCOUNT_ID']
        
        self.redis_client = get_redis_client()
        self.bot_active_statuses = ["open"]
        self.bot_inactive_statuses = ["pending", "resolved", "snoozed"]
        
        # Prefijo específico de empresa para Redis
        if self.company_config:
            self.redis_prefix = self.company_config.redis_prefix
        else:
            self.redis_prefix = f"{self.company_id}:"
        
        # Initialize OpenAI service for multimedia processing
        self.openai_service = OpenAIService()
        
        logger.info(f"ChatwootService initialized for company: {self.company_id}")

    def update_bot_status(self, conversation_id: int, conversation_status: str):
        """Update bot status for a specific conversation with company context"""
        is_active = conversation_status in self.bot_active_statuses

        # Key específico con contexto de empresa
        status_key = f"{self.redis_prefix}bot_status:{conversation_id}"
        status_data = {
            'active': str(is_active),
            'status': conversation_status,
            'company_id': self.company_id,
            'updated_at': str(time.time())
        }

        try:
            old_status = self.redis_client.hget(status_key, 'active')
            self.redis_client.hset(status_key, mapping=status_data)
            self.redis_client.expire(status_key, 86400)  # 24 hours TTL

            if old_status != str(is_active):
                status_text = "ACTIVO" if is_active else "INACTIVO"
                logger.info(f"🔄 [{self.company_id}] Conversation {conversation_id}: Bot {status_text} (status: {conversation_status})")

        except Exception as e:
            logger.error(f"[{self.company_id}] Error updating bot status in Redis: {e}")

    def is_message_already_processed(self, message_id: int, conversation_id: int) -> bool:
        """Check if message has already been processed with company context"""
        if not message_id:
            return False

        # Key específico con contexto de empresa
        key = f"{self.redis_prefix}processed_message:{conversation_id}:{message_id}"

        try:
            if self.redis_client.exists(key):
                logger.info(f"🔄 [{self.company_id}] Message {message_id} already processed, skipping")
                return True

            self.redis_client.set(key, "1", ex=3600)  # 1 hour TTL
            logger.info(f"✅ [{self.company_id}] Message {message_id} marked as processed")
            return False

        except Exception as e:
            logger.error(f"[{self.company_id}] Error checking processed message: {e}")
            return False

    # Los métodos de multimedia (transcribe_audio_from_url, analyze_image_from_url, etc.)
    # se mantienen igual que en el código original ya que no necesitan cambios multi-tenant

    def process_incoming_message(self, data: Dict[str, Any],
                                 conversation_manager: ConversationManager,
                                 orchestrator: MultiAgentOrchestrator) -> Dict[str, Any]:
        """Process incoming message with multi-tenant context"""
        try:
            # Validar que el orquestador sea del company correcto
            if orchestrator.company_id != self.company_id:
                raise ValueError(f"Orchestrator company mismatch: {orchestrator.company_id} != {self.company_id}")
            
            # Resto del método igual que el original pero con logging de empresa
            message_type = data.get("message_type")
            if message_type != "incoming":
                logger.info(f"🤖 [{self.company_id}] Ignoring message type: {message_type}")
                return {"status": "non_incoming_message", "ignored": True, "company_id": self.company_id}

            # Extract and validate conversation data
            conversation_data = data.get("conversation", {})
            if not conversation_data:
                raise ValueError("Missing conversation data")

            conversation_id = conversation_data.get("id")
            conversation_status = conversation_data.get("status")

            if not conversation_id:
                raise ValueError("Missing conversation ID")

            # Check if bot should respond
            if not self.should_bot_respond(conversation_id, conversation_status):
                return {
                    "status": "bot_inactive",
                    "message": f"Bot is inactive for status: {conversation_status}",
                    "active_only_for": self.bot_active_statuses,
                    "company_id": self.company_id
                }

            # Extract and validate message content
            content = data.get("content", "").strip()
            message_id = data.get("id")
            attachments = data.get("attachments", [])

            logger.info(f"📎 [{self.company_id}] Attachments received: {len(attachments)}")

            # Check for duplicate processing
            if message_id and self.is_message_already_processed(message_id, conversation_id):
                return {"status": "already_processed", "ignored": True, "company_id": self.company_id}

            # Extract contact information
            contact_id, extraction_method, is_valid = self.extract_contact_id(data)
            if not is_valid or not contact_id:
                raise ValueError("Could not extract valid contact_id from webhook data")

            # Generate user_id with company context
            user_id = conversation_manager._create_user_id(contact_id)

            logger.info(f"🔄 [{self.company_id}] Processing message from conversation {conversation_id}")
            logger.info(f"👤 User: {user_id} (contact: {contact_id}, method: {extraction_method})")
            logger.info(f"💬 Message: {content[:100]}...")

            # Process multimedia attachments (igual que el original)
            media_context = None
            media_type = "text"
            processed_attachment = None

            for attachment in attachments:
                try:
                    processed_attachment = self.process_attachment(attachment)
                    
                    if not processed_attachment:
                        continue
                    
                    attachment_type = processed_attachment.get("type")
                    url = processed_attachment.get("url")
                    
                    if not attachment_type or not url:
                        continue

                    if attachment_type in ["image", "audio"]:
                        media_type = attachment_type
                        
                        logger.info(f"🎯 [{self.company_id}] Processing {media_type}: {url}")

                        if media_type == "audio":
                            try:
                                media_context = self.transcribe_audio_from_url(url)
                                logger.info(f"🎵 [{self.company_id}] Audio transcribed: {media_context[:100]}...")
                            except Exception as audio_error:
                                logger.error(f"❌ [{self.company_id}] Audio transcription failed: {audio_error}")
                                media_context = f"[Audio file - transcription failed: {str(audio_error)}]"

                        elif media_type == "image":
                            try:
                                media_context = self.analyze_image_from_url(url)
                                logger.info(f"🖼️ [{self.company_id}] Image analyzed: {media_context[:100]}...")
                            except Exception as image_error:
                                logger.error(f"❌ [{self.company_id}] Image analysis failed: {image_error}")
                                media_context = f"[Image file - analysis failed: {str(image_error)}]"

                        break

                except Exception as e:
                    logger.error(f"❌ [{self.company_id}] Error processing attachment {attachment}: {e}")
                    continue

            # Validate processable content
            if not content and not media_context:
                return {
                    "status": "success",
                    "message": "Empty message handled",
                    "conversation_id": str(conversation_id),
                    "company_id": self.company_id,
                    "assistant_reply": f"Por favor, envía un mensaje con contenido para poder ayudarte en {self.company_config.company_name if self.company_config else self.company_id}. 😊"
                }

            # Use media context as primary content if no text
            if not content and media_context:
                content = media_context

            # Generate response with company-specific orchestrator
            logger.info(f"🤖 [{self.company_id}] Generating response with media_type: {media_type}")
            assistant_reply, agent_used = orchestrator.get_response(
                question=content,
                user_id=user_id,
                conversation_manager=conversation_manager,
                media_type=media_type,
                media_context=media_context
            )

            if not assistant_reply or not assistant_reply.strip():
                company_name = self.company_config.company_name if self.company_config else self.company_id
                assistant_reply = f"Disculpa, no pude procesar tu mensaje. ¿Podrías intentar de nuevo en {company_name}? 😊"

            logger.info(f"🤖 [{self.company_id}] Assistant response: {assistant_reply[:100]}...")

            # Send response to Chatwoot
            success = self.send_message(conversation_id, assistant_reply)

            if not success:
                raise ValueError("Failed to send response to Chatwoot")

            logger.info(f"✅ [{self.company_id}] Successfully processed message for conversation {conversation_id}")

            return {
                "status": "success",
                "message": "Response sent successfully",
                "company_id": self.company_id,
                "conversation_id": str(conversation_id),
                "user_id": user_id,
                "contact_id": contact_id,
                "contact_extraction_method": extraction_method,
                "conversation_status": conversation_status,
                "message_id": message_id,
                "bot_active": True,
                "agent_used": agent_used,
                "message_length": len(content),
                "response_length": len(assistant_reply),
                "media_processed": media_type if media_context else None,
                "processed_attachment": processed_attachment
            }

        except Exception as e:
            logger.exception(f"💥 [{self.company_id}] Error procesando mensaje (ID: {data.get('id', 'unknown')})")
            raise
