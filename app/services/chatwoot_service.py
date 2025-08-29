from app.services.redis_service import get_redis_client
from app.models.conversation import ConversationManager
from app.services.multiagent_system import MultiAgentSystem
from app.services.openai_service import OpenAIService
from app.config.company_config import get_company_config_manager, get_company_config
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
    """Service for handling Chatwoot interactions with integrated multimedia processing - Multi-Company"""

    def __init__(self, company_id: str = "default"):
        self.api_key = current_app.config['CHATWOOT_API_KEY']
        self.base_url = current_app.config['CHATWOOT_BASE_URL']
        self.account_id = current_app.config['ACCOUNT_ID']
        self.redis_client = get_redis_client()
        self.company_config_manager = get_company_config_manager()
        self.company_config = get_company_config(company_id)
        self.company_id = company_id
        self.bot_active_statuses = ["open"]
        self.bot_inactive_statuses = ["pending", "resolved", "snoozed"]
        
        # Initialize OpenAI service for multimedia processing
        self.openai_service = OpenAIService()

    def send_message(self, conversation_id: int, message_content: str) -> bool:
        """Send message to Chatwoot conversation"""
        url = f"{self.base_url}/api/v1/accounts/{self.account_id}/conversations/{conversation_id}/messages"

        headers = {
            "api_access_token": self.api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "content": message_content,
            "message_type": "outgoing",
            "private": False
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=30,
                verify=True
            )

            logger.info(f"Chatwoot API Response Status for {self.company_config.company_name}: {response.status_code}")

            if response.status_code == 200:
                logger.info(f"✅ Message sent to conversation {conversation_id} for {self.company_config.company_name}")
                return True
            else:
                logger.error(f"❌ Failed to send message for {self.company_config.company_name}: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Error sending message to Chatwoot for {self.company_config.company_name}: {e}")
            return False

    def should_bot_respond(self, conversation_id: int, conversation_status: str) -> bool:
        """Determine if bot should respond based on conversation status - Company specific"""
        self.update_bot_status(conversation_id, conversation_status)
        is_active = conversation_status in self.bot_active_statuses

        if is_active:
            logger.info(f"✅ Bot WILL respond to conversation {conversation_id} for {self.company_config.company_name} (status: {conversation_status})")
        else:
            if conversation_status == "pending":
                logger.info(f"⏸️ Bot will NOT respond to conversation {conversation_id} for {self.company_config.company_name} (status: pending - INACTIVE)")
            else:
                logger.info(f"🚫 Bot will NOT respond to conversation {conversation_id} for {self.company_config.company_name} (status: {conversation_status})")

        return is_active

    def update_bot_status(self, conversation_id: int, conversation_status: str):
        """Update bot status for a specific conversation in Redis with company isolation"""
        is_active = conversation_status in self.bot_active_statuses

        status_key = f"{self.company_config.redis_prefix}bot_status:{conversation_id}"
        status_data = {
            'active': str(is_active),
            'status': conversation_status,
            'company_id': self.company_id,
            'company_name': self.company_config.company_name,
            'updated_at': str(time.time())
        }

        try:
            old_status = self.redis_client.hget(status_key, 'active')
            self.redis_client.hset(status_key, mapping=status_data)
            self.redis_client.expire(status_key, 86400)  # 24 hours TTL

            if old_status != str(is_active):
                status_text = "ACTIVO" if is_active else "INACTIVO"
                logger.info(f"🔄 Conversation {conversation_id} ({self.company_config.company_name}): Bot {status_text} (status: {conversation_status})")

        except Exception as e:
            logger.error(f"Error updating bot status in Redis for {self.company_config.company_name}: {e}")

    def is_message_already_processed(self, message_id: int, conversation_id: int) -> bool:
        """Check if message has already been processed - Company isolated"""
        if not message_id:
            return False

        key = f"{self.company_config.redis_prefix}processed_message:{conversation_id}:{message_id}"

        try:
            if self.redis_client.exists(key):
                logger.info(f"🔄 Message {message_id} already processed for {self.company_config.company_name}, skipping")
                return True

            # Store with company information
            message_data = json.dumps({
                'message_id': message_id,
                'conversation_id': conversation_id,
                'company_id': self.company_id,
                'company_name': self.company_config.company_name,
                'processed_at': time.time()
            })
            
            self.redis_client.setex(key, 3600, message_data)  # 1 hour TTL
            logger.info(f"✅ Message {message_id} marked as processed for {self.company_config.company_name}")
            return False

        except Exception as e:
            logger.error(f"Error checking processed message for {self.company_config.company_name}: {e}")
            return False

    def extract_contact_id(self, data: Dict[str, Any]) -> Tuple[Optional[str], str, bool]:
        """Extract contact_id with unified priority system and validation - Company aware"""
        conversation_data = data.get("conversation", {})

        # Priority order for contact extraction
        extraction_methods = [
            ("conversation.contact_inbox.contact_id",
             lambda: conversation_data.get("contact_inbox", {}).get("contact_id")),
            ("conversation.meta.sender.id",
             lambda: conversation_data.get("meta", {}).get("sender", {}).get("id")),
            ("root.sender.id",
             lambda: data.get("sender", {}).get("id") if data.get("sender", {}).get("type") != "agent" else None)
        ]

        for method_name, extractor in extraction_methods:
            try:
                contact_id = extractor()
                if contact_id and str(contact_id).strip():
                    # Validate contact_id format
                    contact_id = str(contact_id).strip()
                    if contact_id.isdigit() or contact_id.startswith("contact_"):
                        logger.info(f"✅ Contact ID extracted for {self.company_config.company_name}: {contact_id} (method: {method_name})")
                        return contact_id, method_name, True
            except Exception as e:
                logger.warning(f"Error in extraction method {method_name} for {self.company_config.company_name}: {e}")
                continue

        logger.error(f"❌ No valid contact_id found in webhook data for {self.company_config.company_name}")
        return None, "none", False

    def handle_conversation_updated(self, data: Dict[str, Any]) -> bool:
        """Handle conversation_updated events - Company aware"""
        try:
            conversation_id = data.get("id")
            if not conversation_id:
                logger.error(f"❌ Could not extract conversation_id from conversation_updated event for {self.company_config.company_name}")
                return False

            conversation_status = data.get("status")
            if not conversation_status:
                logger.warning(f"⚠️ No status found in conversation_updated for {conversation_id} ({self.company_config.company_name})")
                return False

            logger.info(f"📋 Conversation {conversation_id} ({self.company_config.company_name}) updated to status: {conversation_status}")
            self.update_bot_status(conversation_id, conversation_status)
            return True

        except Exception as e:
            logger.error(f"Error handling conversation_updated for {self.company_config.company_name}: {e}")
            return False

    # INTEGRATED MULTIMEDIA PROCESSING METHODS
    
    def transcribe_audio_from_url(self, audio_url: str) -> str:
        """Transcribe audio from URL with robust error handling"""
        try:
            logger.info(f"🔽 Downloading audio for {self.company_config.company_name} from: {audio_url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; ChatbotAudioTranscriber/1.0)',
                'Accept': 'audio/*,*/*;q=0.9'
            }
            
            response = requests.get(audio_url, headers=headers, timeout=60, stream=True)
            response.raise_for_status()
            
            # Verify content-type if available
            content_type = response.headers.get('content-type', '').lower()
            logger.info(f"📄 Audio content-type for {self.company_config.company_name}: {content_type}")
            
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
            
            logger.info(f"📁 Audio saved to temp file for {self.company_config.company_name}: {temp_path} (size: {os.path.getsize(temp_path)} bytes)")
            
            try:
                result = self.openai_service.transcribe_audio(temp_path)
                logger.info(f"🎵 Transcription successful for {self.company_config.company_name}: {len(result)} characters")
                return result
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_path)
                    logger.info(f"🗑️ Temporary file deleted for {self.company_config.company_name}: {temp_path}")
                except Exception as cleanup_error:
                    logger.warning(f"⚠️ Could not delete temp file {temp_path} for {self.company_config.company_name}: {cleanup_error}")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error downloading audio for {self.company_config.company_name}: {e}")
            raise Exception(f"Error downloading audio: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Error in audio transcription from URL for {self.company_config.company_name}: {e}")
            raise

    def analyze_image_from_url(self, image_url: str) -> str:
        """Analyze image from URL using GPT-4 Vision"""
        try:
            logger.info(f"🔽 Downloading image for {self.company_config.company_name} from: {image_url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; ChatbotImageAnalyzer/1.0)'
            }
            response = requests.get(image_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Verify it's an image
            content_type = response.headers.get('content-type', '').lower()
            if not any(img_type in content_type for img_type in ['image/', 'jpeg', 'png', 'gif', 'webp']):
                logger.warning(f"⚠️ Content type might not be image for {self.company_config.company_name}: {content_type}")
            
            # Create file in memory
            image_file = BytesIO(response.content)
            
            # Analyze using OpenAI service
            return self.openai_service.analyze_image(image_file)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error downloading image for {self.company_config.company_name}: {e}")
            raise Exception(f"Error downloading image: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Error in image analysis from URL for {self.company_config.company_name}: {e}")
            raise

    def process_attachment(self, attachment: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process Chatwoot attachment with complete parity to monolith - Company aware"""
        try:
            logger.info(f"Processing Chatwoot attachment for {self.company_config.company_name}: {attachment}")
    
            # Extract type with multiple methods
            attachment_type = None
    
            # Method 1: file_type (most common in Chatwoot)
            if attachment.get("file_type"):
                attachment_type = attachment["file_type"].lower()
                logger.info(f"Type from 'file_type' for {self.company_config.company_name}: {attachment_type}")
    
            # Method 2: extension
            elif attachment.get("extension"):
                ext = attachment["extension"].lower().lstrip('.')
                if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                    attachment_type = "image"
                elif ext in ['mp3', 'wav', 'ogg', 'm4a', 'aac']:
                    attachment_type = "audio"
                logger.info(f"Type inferred from extension '{ext}' for {self.company_config.company_name}: {attachment_type}")
    
            # Extract URL with correct priority
            url = attachment.get("data_url") or attachment.get("url") or attachment.get("thumb_url")
    
            if not url:
                logger.warning(f"No URL found in attachment for {self.company_config.company_name}")
                return None
    
            # Construct full URL if necessary
            if not url.startswith("http"):
                # Remove initial slash to avoid double slash
                if url.startswith("/"):
                    url = url[1:]
                url = f"{self.base_url}/{url}"
                logger.info(f"Full URL constructed for {self.company_config.company_name}: {url}")
    
            # Validate that URL is accessible
            if not url.startswith("http"):
                logger.warning(f"Invalid URL format for {self.company_config.company_name}: {url}")
                return None
    
            return {
                "type": attachment_type,
                "url": url,
                "file_size": attachment.get("file_size", 0),
                "width": attachment.get("width"),
                "height": attachment.get("height"),
                "company_id": self.company_id,
                "company_name": self.company_config.company_name,
                "original_data": attachment
            }
    
        except Exception as e:
            logger.error(f"Error processing Chatwoot attachment for {self.company_config.company_name}: {e}")
            return None

    def debug_webhook_data(self, data: Dict[str, Any]):
        """Complete debugging function - Company aware"""
        logger.info(f"🔍 === WEBHOOK DEBUG INFO ({self.company_config.company_name}) ===")
        logger.info(f"Event: {data.get('event')}")
        logger.info(f"Message ID: {data.get('id')}")
        logger.info(f"Message Type: {data.get('message_type')}")
        logger.info(f"Content: '{data.get('content')}'")
        logger.info(f"Content Length: {len(data.get('content', ''))}")

        attachments = data.get('attachments', [])
        logger.info(f"Attachments Count: {len(attachments)}")

        for i, att in enumerate(attachments):
            logger.info(f"  Attachment {i}:")
            logger.info(f"    Keys: {list(att.keys())}")
            logger.info(f"    Type: {att.get('type')}")
            logger.info(f"    File Type: {att.get('file_type')}")
            logger.info(f"    URL: {att.get('url')}")
            logger.info(f"    Data URL: {att.get('data_url')}")
            logger.info(f"    Thumb URL: {att.get('thumb_url')}")

        logger.info(f"🔍 === END DEBUG INFO ({self.company_config.company_name}) ===")

    def process_incoming_message(self, data: Dict[str, Any],
                                 conversation_manager: ConversationManager = None,
                                 multiagent: MultiAgentSystem = None) -> Dict[str, Any]:
        """Process incoming message with comprehensive validation and error handling - Multi-Company"""
        try:
            # Extract company_id from webhook data first
            extracted_company_id = self.company_config_manager.extract_company_id_from_webhook(data)
            
            # If we got a specific company, update our configuration
            if extracted_company_id and extracted_company_id != "default":
                if extracted_company_id != self.company_id:
                    # Create new service instance for the correct company
                    return ChatwootService(extracted_company_id).process_incoming_message(data, conversation_manager, multiagent)
            
            logger.info(f"🔄 Processing message for company: {self.company_config.company_name}")
            
            # Validate message type
            message_type = data.get("message_type")
            if message_type != "incoming":
                logger.info(f"🤖 Ignoring message type: {message_type} for {self.company_config.company_name}")
                return {"status": "non_incoming_message", "ignored": True, "company_id": self.company_id}

            # Extract and validate conversation data
            conversation_data = data.get("conversation", {})
            if not conversation_data:
                raise ValueError(f"Missing conversation data for {self.company_config.company_name}")

            conversation_id = conversation_data.get("id")
            conversation_status = conversation_data.get("status")

            if not conversation_id:
                raise ValueError(f"Missing conversation ID for {self.company_config.company_name}")

            # Validate conversation_id format
            if not str(conversation_id).strip() or not str(conversation_id).isdigit():
                raise ValueError(f"Invalid conversation ID format for {self.company_config.company_name}")

            # Check if bot should respond
            if not self.should_bot_respond(conversation_id, conversation_status):
                return {
                    "status": "bot_inactive",
                    "message": f"Bot is inactive for status: {conversation_status}",
                    "active_only_for": self.bot_active_statuses,
                    "company_id": self.company_id,
                    "company_name": self.company_config.company_name
                }

            # Extract and validate message content
            content = data.get("content", "").strip()
            message_id = data.get("id")

            # Extract attachments with debugging
            attachments = data.get("attachments", [])
            logger.info(f"📎 Attachments received for {self.company_config.company_name}: {len(attachments)}")
            for i, att in enumerate(attachments):
                logger.info(f"📎 Attachment {i} for {self.company_config.company_name}: {att}")

            # Check for duplicate processing
            if message_id and self.is_message_already_processed(message_id, conversation_id):
                return {"status": "already_processed", "ignored": True, "company_id": self.company_id}

            # Extract contact information with improved validation
            contact_id, extraction_method, is_valid = self.extract_contact_id(data)
            if not is_valid or not contact_id:
                raise ValueError(f"Could not extract valid contact_id from webhook data for {self.company_config.company_name}")

            # Create consistent user_id with company prefix
            user_id = conversation_manager._create_user_id(contact_id) if conversation_manager else f"{self.company_id}_contact_{contact_id}"

            # Handle multimedia attachments
            processed_attachments = []
            multimedia_responses = []
            has_multimedia = len(attachments) > 0

            for attachment in attachments:
                processed_attachment = self.process_attachment(attachment)
                if processed_attachment:
                    processed_attachments.append(processed_attachment)

                    # Process multimedia based on type
                    if processed_attachment["type"] == "audio":
                        try:
                            transcription = self.transcribe_audio_from_url(processed_attachment["url"])
                            multimedia_responses.append({
                                "type": "audio",
                                "transcription": transcription,
                                "url": processed_attachment["url"]
                            })
                            logger.info(f"🎵 Audio transcribed for {self.company_config.company_name}: {len(transcription)} characters")

                        except Exception as e:
                            logger.error(f"Error transcribing audio for {self.company_config.company_name}: {e}")
                            multimedia_responses.append({
                                "type": "audio",
                                "error": f"Error processing audio: {str(e)}",
                                "url": processed_attachment["url"]
                            })

                    elif processed_attachment["type"] == "image":
                        try:
                            image_analysis = self.analyze_image_from_url(processed_attachment["url"])
                            multimedia_responses.append({
                                "type": "image",
                                "analysis": image_analysis,
                                "url": processed_attachment["url"]
                            })
                            logger.info(f"🖼️ Image analyzed for {self.company_config.company_name}: {len(image_analysis)} characters")

                        except Exception as e:
                            logger.error(f"Error analyzing image for {self.company_config.company_name}: {e}")
                            multimedia_responses.append({
                                "type": "image",
                                "error": f"Error processing image: {str(e)}",
                                "url": processed_attachment["url"]
                            })

            # Determine media context for multiagent processing
            media_type = "text"
            media_context = None

            if multimedia_responses:
                if any(mr["type"] == "audio" for mr in multimedia_responses):
                    media_type = "voice"
                    for mr in multimedia_responses:
                        if mr["type"] == "audio" and "transcription" in mr:
                            media_context = mr["transcription"]
                            break

                elif any(mr["type"] == "image" for mr in multimedia_responses):
                    media_type = "image"
                    for mr in multimedia_responses:
                        if mr["type"] == "image" and "analysis" in mr:
                            media_context = mr["analysis"]
                            break

            # Process message with multiagent system
            if not content and has_multimedia:
                if media_context:
                    content = f"[Multimedia content - {media_type}]"
                else:
                    content = "[Multimedia content - processing error]"

            if not content.strip():
                content = "..."

            # Get AI response
            try:
                ai_response, agent_used = multiagent.get_response(
                    content, 
                    user_id, 
                    conversation_manager,
                    media_type=media_type,
                    media_context=media_context
                )

                # Add multimedia context to response if available
                if multimedia_responses and media_context:
                    if media_type == "voice":
                        ai_response = f"🎵 He escuchado tu mensaje de voz.\n\n{ai_response}"
                    elif media_type == "image":
                        ai_response = f"🖼️ He analizado tu imagen.\n\n{ai_response}"

            except Exception as e:
                logger.error(f"Error getting AI response for {self.company_config.company_name}: {e}")
                ai_response = f"Disculpa, tuve un problema técnico procesando tu mensaje en {self.company_config.company_name}. Por favor intenta de nuevo."
                agent_used = "error"

            # Send response to Chatwoot
            try:
                send_success = self.send_message(conversation_id, ai_response)
            except Exception as e:
                logger.error(f"Error sending message to Chatwoot for {self.company_config.company_name}: {e}")
                send_success = False

            return {
                "status": "success" if send_success else "send_error",
                "company_id": self.company_id,
                "company_name": self.company_config.company_name,
                "message_sent": send_success,
                "conversation_id": conversation_id,
                "user_id": user_id,
                "contact_id": contact_id,
                "extraction_method": extraction_method,
                "ai_response_length": len(ai_response),
                "agent_used": agent_used,
                "has_multimedia": has_multimedia,
                "multimedia_count": len(processed_attachments),
                "media_type": media_type,
                "multimedia_responses": multimedia_responses,
                "response": ai_response
            }

        except Exception as e:
            logger.error(f"❌ Error processing incoming message for {self.company_config.company_name}: {e}")
            logger.exception("Stack trace:")

            # Try to send error message if we have conversation_id
            conversation_data = data.get("conversation", {})
            conversation_id = conversation_data.get("id")

            if conversation_id:
                try:
                    error_message = f"Disculpa, tuve un problema técnico en {self.company_config.company_name}. Por favor intenta de nuevo en unos minutos."
                    self.send_message(conversation_id, error_message)
                except:
                    pass

            return {
                "status": "error",
                "company_id": self.company_id,
                "company_name": self.company_config.company_name,
                "error": str(e),
                "conversation_id": conversation_id if 'conversation_id' in locals() else None
            }

    def get_status_summary(self) -> Dict[str, Any]:
        """Get status summary for this company's Chatwoot service"""
        return {
            "company_id": self.company_id,
            "company_name": self.company_config.company_name,
            "chatwoot_base_url": self.base_url,
            "account_id": self.account_id,
            "bot_active_statuses": self.bot_active_statuses,
            "bot_inactive_statuses": self.bot_inactive_statuses,
            "multimedia_processing": {
                "audio_transcription": True,
                "image_analysis": True,
                "supported_audio_formats": ["ogg", "mp3", "wav", "m4a"],
                "supported_image_formats": ["jpg", "jpeg", "png", "gif", "webp"]
            },
            "redis_prefix": self.company_config.redis_prefix,
            "service_healthy": True
        }


class MultiCompanyChatwootService:
    """Service manager for handling Chatwoot across multiple companies"""
    
    def __init__(self):
        self.company_services = {}
        self.company_config_manager = get_company_config_manager()
    
    def get_service_for_company(self, company_id: str) -> ChatwootService:
        """Get Chatwoot service for specific company"""
        if company_id not in self.company_services:
            self.company_services[company_id] = ChatwootService(company_id)
        
        return self.company_services[company_id]
    
    def process_webhook_message(self, webhook_data: Dict[str, Any], 
                               conversation_manager=None, 
                               multiagent_system=None) -> Dict[str, Any]:
        """Process webhook message with automatic company detection"""
        try:
            # Extract company_id from webhook data
            company_id = self.company_config_manager.extract_company_id_from_webhook(webhook_data)
            
            logger.info(f"Processing webhook for company: {company_id}")
            
            # Get appropriate service for the company
            chatwoot_service = self.get_service_for_company(company_id)
            
            # Get company-specific managers if needed
            if conversation_manager is None:
                from app.models.conversation import ConversationManager
                conversation_manager = ConversationManager(company_id)
            
            if multiagent_system is None:
                from app.services.multiagent_system import MultiAgentSystem
                multiagent_system = MultiAgentSystem(company_id)
            
            # Process the message
            return chatwoot_service.process_incoming_message(
                webhook_data, 
                conversation_manager, 
                multiagent_system
            )
            
        except Exception as e:
            logger.error(f"Error in multi-company webhook processing: {e}")
            return {
                "status": "error",
                "error": str(e),
                "company_id": "unknown"
            }
    
    def get_global_status_summary(self) -> Dict[str, Any]:
        """Get status summary for all company Chatwoot services"""
        global_status = {
            "total_companies": len(self.company_services),
            "companies": {},
            "global_summary": {
                "total_active_services": 0,
                "multimedia_enabled_companies": 0,
                "unique_accounts": set(),
                "unique_base_urls": set()
            }
        }
        
        for company_id, service in self.company_services.items():
            try:
                company_status = service.get_status_summary()
                global_status["companies"][company_id] = company_status
                
                # Update global summary
                global_status["global_summary"]["total_active_services"] += 1
                
                if company_status.get("multimedia_processing", {}).get("audio_transcription", False):
                    global_status["global_summary"]["multimedia_enabled_companies"] += 1
                
                global_status["global_summary"]["unique_accounts"].add(company_status.get("account_id"))
                global_status["global_summary"]["unique_base_urls"].add(company_status.get("chatwoot_base_url"))
                
            except Exception as e:
                logger.error(f"Error getting status for company {company_id}: {e}")
                global_status["companies"][company_id] = {
                    "company_id": company_id,
                    "error": str(e),
                    "service_healthy": False
                }
                continue
        
        # Convert sets to lists for JSON serialization
        global_status["global_summary"]["unique_accounts"] = list(global_status["global_summary"]["unique_accounts"])
        global_status["global_summary"]["unique_base_urls"] = list(global_status["global_summary"]["unique_base_urls"])
        
        return global_status
