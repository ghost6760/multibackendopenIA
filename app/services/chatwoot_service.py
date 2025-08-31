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

    def should_bot_respond(self, conversation_id: int, conversation_status: str) -> bool:
        """Check if bot should respond to message with company context"""
        if conversation_status in self.bot_active_statuses:
            return True
        
        # Update status
        self.update_bot_status(conversation_id, conversation_status)
        return False

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

    def extract_contact_id(self, data: Dict[str, Any]) -> Tuple[str, str, bool]:
        """Extract contact ID from webhook data"""
        try:
            # Método 1: Desde sender
            sender = data.get("sender", {})
            if sender and "id" in sender:
                contact_id = str(sender["id"])
                return contact_id, "sender_id", True
            
            # Método 2: Desde conversation.contact_inbox.contact
            conversation = data.get("conversation", {})
            contact_inbox = conversation.get("contact_inbox", {})
            contact = contact_inbox.get("contact", {})
            if contact and "id" in contact:
                contact_id = str(contact["id"])
                return contact_id, "contact_inbox_contact_id", True
            
            # Método 3: ID directo en conversation
            if "contact_id" in conversation:
                contact_id = str(conversation["contact_id"])
                return contact_id, "conversation_contact_id", True
            
            # Fallback
            logger.warning(f"[{self.company_id}] Could not extract contact_id, using fallback")
            return "unknown_contact", "fallback", False
            
        except Exception as e:
            logger.error(f"[{self.company_id}] Error extracting contact_id: {e}")
            return "unknown_contact", "error", False

    def send_message(self, conversation_id: int, message: str) -> bool:
        """Send message to Chatwoot conversation"""
        try:
            url = f"{self.base_url}/api/v1/accounts/{self.account_id}/conversations/{conversation_id}/messages"
            headers = {
                "api_access_token": self.api_key,
                "Content-Type": "application/json"
            }
            payload = {
                "content": message,
                "message_type": "outgoing"
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✅ [{self.company_id}] Message sent to conversation {conversation_id}")
                return True
            else:
                logger.error(f"❌ [{self.company_id}] Failed to send message: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"[{self.company_id}] Error sending message: {e}")
            return False

    def handle_conversation_updated(self, data: Dict[str, Any]) -> bool:
        """Handle conversation status updates"""
        try:
            conversation_data = data.get("conversation", {})
            conversation_id = conversation_data.get("id")
            conversation_status = conversation_data.get("status")
            
            if conversation_id and conversation_status:
                self.update_bot_status(conversation_id, conversation_status)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"[{self.company_id}] Error handling conversation update: {e}")
            return False

    def debug_webhook_data(self, data: Dict[str, Any]):
        """Debug webhook data for development"""
        try:
            logger.info(f"🔍 [{self.company_id}] WEBHOOK DEBUG:")
            logger.info(f"   Event: {data.get('event', 'N/A')}")
            logger.info(f"   Message Type: {data.get('message_type', 'N/A')}")
            logger.info(f"   Content Length: {len(data.get('content', ''))}")
            logger.info(f"   Attachments: {len(data.get('attachments', []))}")
            
            conversation = data.get("conversation", {})
            logger.info(f"   Conversation ID: {conversation.get('id', 'N/A')}")
            logger.info(f"   Conversation Status: {conversation.get('status', 'N/A')}")
            
        except Exception as e:
            logger.error(f"[{self.company_id}] Error in debug: {e}")

    def process_attachment(self, attachment: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process individual attachment"""
        try:
            data_url = attachment.get("data_url")
            file_type = attachment.get("file_type", "")
            
            if not data_url:
                logger.warning(f"[{self.company_id}] Attachment missing data_url")
                return None
            
            # Determine attachment type
            attachment_type = None
            if file_type.startswith("image/"):
                attachment_type = "image"
            elif file_type.startswith("audio/"):
                attachment_type = "audio"
            else:
                logger.info(f"[{self.company_id}] Unsupported attachment type: {file_type}")
                return None
            
            logger.info(f"[{self.company_id}] Processing {attachment_type} attachment")
            
            return {
                "type": attachment_type,
                "url": data_url,
                "file_type": file_type,
                "size": attachment.get("file_size", 0)
            }
            
        except Exception as e:
            logger.error(f"[{self.company_id}] Error processing attachment: {e}")
            return None

    def transcribe_audio_from_url(self, audio_url: str) -> str:
        """Transcribe audio from URL with improved error handling"""
        try:
            logger.info(f"[{self.company_id}] Downloading audio from: {audio_url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; ChatbotAudioTranscriber/1.0)',
                'Accept': 'audio/*,*/*;q=0.9'
            }
            
            response = requests.get(audio_url, headers=headers, timeout=60, stream=True)
            response.raise_for_status()
            
            # Verify content-type if available
            content_type = response.headers.get('content-type', '').lower()
            logger.info(f"[{self.company_id}] Audio content-type: {content_type}")
            
            # Determine extension based on content-type or URL
            extension = '.ogg'  # Default for Chatwoot
            if 'mp3' in content_type or audio_url.endswith('.mp3'):
                extension = '.mp3'
            elif 'wav' in content_type or audio_url.endswith('.wav'):
                extension = '.wav'
            elif 'm4a' in content_type or audio_url.endswith('.m4a'):
                extension = '.m4a'
            
            # Create temporary file with correct extension
            with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    temp_file.write(chunk)
                temp_path = temp_file.name
            
            logger.info(f"[{self.company_id}] Audio saved to temp file: {temp_path} (size: {os.path.getsize(temp_path)} bytes)")
            
            try:
                result = self.openai_service.transcribe_audio(temp_path)
                logger.info(f"[{self.company_id}] Transcription successful: {len(result)} characters")
                return result
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_path)
                    logger.info(f"[{self.company_id}] Temporary file deleted: {temp_path}")
                except Exception as cleanup_error:
                    logger.warning(f"[{self.company_id}] Could not delete temp file {temp_path}: {cleanup_error}")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[{self.company_id}] Error downloading audio: {e}")
            raise Exception(f"Error downloading audio: {str(e)}")
        except Exception as e:
            logger.error(f"[{self.company_id}] Error in audio transcription from URL: {e}")
            raise

    def analyze_image_from_url(self, image_url: str) -> str:
        """Analyze image from URL using GPT-4 Vision"""
        try:
            logger.info(f"[{self.company_id}] Downloading image from: {image_url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; ChatbotImageAnalyzer/1.0)'
            }
            response = requests.get(image_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Verify it's an image
            content_type = response.headers.get('content-type', '').lower()
            if not any(img_type in content_type for img_type in ['image/', 'jpeg', 'png', 'gif', 'webp']):
                logger.warning(f"[{self.company_id}] Content type might not be image: {content_type}")
            
            # Create file in memory
            image_file = BytesIO(response.content)
            
            # Analyze using OpenAI service
            return self.openai_service.analyze_image(image_file)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[{self.company_id}] Error downloading image: {e}")
            raise Exception(f"Error downloading image: {str(e)}")
        except Exception as e:
            logger.error(f"[{self.company_id}] Error in image analysis from URL: {e}")
            raise

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

            # Process multimedia attachments
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
