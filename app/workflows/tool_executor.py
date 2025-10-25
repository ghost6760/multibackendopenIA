# app/workflows/tool_executor.py - NUEVO ARCHIVO COMPLETO

from typing import Dict, Any, Optional, List
from app.workflows.tools_library import ToolsLibrary, ToolDefinition
from app.services.vectorstore_service import VectorstoreService
from app.services.calendar_integration_service import CalendarIntegrationService
from app.services.chatwoot_service import ChatwootService
from app.services.multimedia_service import MultimediaService
from app.services.email_service import EmailService
from app.models.conversation import ConversationManager
import logging

logger = logging.getLogger(__name__)

class ToolExecutor:
    """
    Ejecutor unificado de herramientas multi-tenant.
    
    ✅ Envuelve todos los servicios existentes sin modificarlos
    ✅ Proporciona interfaz estándar para ejecutar tools
    ✅ Maneja errores de forma consistente
    ✅ Logging detallado por empresa
    """
    
    def __init__(self, company_id: str):
        self.company_id = company_id
        self.tools_library = ToolsLibrary()

        # Servicios que se inyectan externamente
        self.vectorstore_service: Optional[VectorstoreService] = None
        self.calendar_service: Optional[CalendarIntegrationService] = None
        self.chatwoot_service: Optional[ChatwootService] = None
        self.multimedia_service: Optional[MultimediaService] = None
        self.email_service: Optional[EmailService] = None
        self.conversation_manager: Optional[ConversationManager] = None

        logger.info(f"🔧 [{company_id}] ToolExecutor initialized")
    
    # ========================================================================
    # MÉTODOS DE INYECCIÓN DE SERVICIOS
    # ========================================================================
    
    def set_vectorstore_service(self, service: VectorstoreService):
        """Inyectar servicio de vectorstore (RAG)"""
        self.vectorstore_service = service
        logger.info(f"✅ [{self.company_id}] VectorstoreService injected")
    
    def set_calendar_service(self, service: CalendarIntegrationService):
        """Inyectar servicio de calendario"""
        self.calendar_service = service
        logger.info(f"✅ [{self.company_id}] CalendarIntegrationService injected")
    
    def set_chatwoot_service(self, service: ChatwootService):
        """Inyectar servicio de Chatwoot (WhatsApp)"""
        self.chatwoot_service = service
        logger.info(f"✅ [{self.company_id}] ChatwootService injected")
    
    def set_multimedia_service(self, service: MultimediaService):
        """Inyectar servicio multimedia (audio, imagen, TTS)"""
        self.multimedia_service = service
        logger.info(f"✅ [{self.company_id}] MultimediaService injected")

    def set_email_service(self, service: EmailService):
        """Inyectar servicio de email"""
        self.email_service = service
        logger.info(f"✅ [{self.company_id}] EmailService injected")

    def set_conversation_manager(self, manager: ConversationManager):
        """Inyectar gestor de conversaciones"""
        self.conversation_manager = manager
        logger.info(f"✅ [{self.company_id}] ConversationManager injected")
    
    # ========================================================================
    # MÉTODO PRINCIPAL DE EJECUCIÓN
    # ========================================================================
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecutar una herramienta por nombre.
        
        Args:
            tool_name: Nombre de la tool (ej: "google_calendar", "knowledge_base")
            parameters: Parámetros específicos de la tool
            
        Returns:
            Resultado de la ejecución en formato estándar:
            {
                "success": bool,
                "tool": str,
                "data": Any,
                "error": Optional[str]
            }
        """
        try:
            logger.info(f"🔧 [{self.company_id}] Executing tool: {tool_name}")
            logger.debug(f"   Parameters: {parameters}")
            
            # Verificar que la tool existe en la biblioteca
            tool_def = self.tools_library.get_tool(tool_name)
            if not tool_def:
                return self._error_response(
                    tool_name, 
                    f"Tool '{tool_name}' not found in library"
                )
            
            # Enrutar a la implementación específica
            if tool_name == "knowledge_base":
                return self._execute_knowledge_base(parameters)
            
            elif tool_name == "google_calendar":
                return self._execute_google_calendar(parameters)
            
            elif tool_name == "send_whatsapp":
                return self._execute_send_whatsapp(parameters)
            
            elif tool_name == "transcribe_audio":
                return self._execute_transcribe_audio(parameters)
            
            elif tool_name == "analyze_image":
                return self._execute_analyze_image(parameters)
            
            elif tool_name == "text_to_speech":
                return self._execute_text_to_speech(parameters)
            
            elif tool_name == "web_search":
                return self._execute_web_search(parameters)
            
            elif tool_name == "send_email":
                return self._execute_send_email(parameters)
            
            else:
                return self._error_response(
                    tool_name,
                    f"Tool '{tool_name}' registered but not implemented yet"
                )
                
        except Exception as e:
            logger.exception(f"💥 [{self.company_id}] Error executing tool {tool_name}: {e}")
            return self._error_response(tool_name, str(e))
    
    # ========================================================================
    # IMPLEMENTACIONES DE TOOLS
    # ========================================================================
    
    def _execute_knowledge_base(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        ✅ Tool: knowledge_base
        Buscar en la base de conocimiento (RAG)
        """
        if not self.vectorstore_service:
            return self._error_response(
                "knowledge_base",
                "VectorstoreService not configured"
            )
        
        query = params.get("query", "")
        top_k = params.get("top_k", 3)
        
        if not query:
            return self._error_response("knowledge_base", "Query parameter required")
        
        try:
            logger.info(f"🔍 [{self.company_id}] RAG search: {query[:50]}...")
            
            docs = self.vectorstore_service.search_by_company(
                query, 
                self.company_id,
                k=top_k
            )
            
            results = []
            for doc in docs:
                if hasattr(doc, 'page_content'):
                    results.append({
                        "content": doc.page_content,
                        "metadata": getattr(doc, 'metadata', {})
                    })
                elif isinstance(doc, dict):
                    results.append({
                        "content": doc.get('content', str(doc)),
                        "metadata": doc.get('metadata', {})
                    })
            
            logger.info(f"✅ [{self.company_id}] RAG found {len(results)} documents")
            
            return {
                "success": True,
                "tool": "knowledge_base",
                "data": {
                    "query": query,
                    "results": results,
                    "total_found": len(results)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ [{self.company_id}] RAG error: {e}")
            return self._error_response("knowledge_base", str(e))
    
    def _execute_google_calendar(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        ✅ Tool: google_calendar
        Operaciones de Google Calendar (check_availability, create_booking)
        """
        if not self.calendar_service:
            return self._error_response(
                "google_calendar",
                "CalendarIntegrationService not configured"
            )
        
        action = params.get("action", "check_availability")
        
        try:
            if action == "check_availability":
                date = params.get("date")
                treatment = params.get("treatment", "general")
                
                if not date:
                    return self._error_response("google_calendar", "Date parameter required")
                
                logger.info(f"📅 [{self.company_id}] Checking availability: {date} - {treatment}")
                
                result = self.calendar_service.check_availability(date, treatment)
                
                return {
                    "success": True,
                    "tool": "google_calendar",
                    "action": "check_availability",
                    "data": result
                }
            
            elif action == "create_booking":
                booking_data = params.get("booking_data", {})
                
                if not booking_data:
                    return self._error_response("google_calendar", "booking_data required")
                
                logger.info(f"📅 [{self.company_id}] Creating booking")
                
                result = self.calendar_service.create_booking(booking_data)
                
                return {
                    "success": result.get("success", False),
                    "tool": "google_calendar",
                    "action": "create_booking",
                    "data": result
                }
            
            else:
                return self._error_response(
                    "google_calendar",
                    f"Unknown calendar action: {action}"
                )
                
        except Exception as e:
            logger.error(f"❌ [{self.company_id}] Calendar error: {e}")
            return self._error_response("google_calendar", str(e))
    
    def _execute_send_whatsapp(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        ✅ Tool: send_whatsapp
        Enviar mensaje por WhatsApp vía Chatwoot
        """
        if not self.chatwoot_service:
            return self._error_response(
                "send_whatsapp",
                "ChatwootService not configured"
            )
        
        conversation_id = params.get("conversation_id")
        message = params.get("message", "")
        
        if not conversation_id:
            return self._error_response("send_whatsapp", "conversation_id required")
        
        if not message:
            return self._error_response("send_whatsapp", "message required")
        
        try:
            logger.info(f"📱 [{self.company_id}] Sending WhatsApp to conversation {conversation_id}")
            
            success = self.chatwoot_service.send_message(conversation_id, message)
            
            return {
                "success": success,
                "tool": "send_whatsapp",
                "data": {
                    "conversation_id": conversation_id,
                    "message_sent": success,
                    "message_length": len(message)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ [{self.company_id}] WhatsApp error: {e}")
            return self._error_response("send_whatsapp", str(e))
    
    def _execute_transcribe_audio(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        ✅ Tool: transcribe_audio
        Transcribir audio usando Whisper
        """
        if not self.multimedia_service:
            return self._error_response(
                "transcribe_audio",
                "MultimediaService not configured"
            )
        
        # Soportar tanto file path como URL
        audio_path = params.get("audio_path")
        audio_url = params.get("audio_url")
        
        if not audio_path and not audio_url:
            return self._error_response(
                "transcribe_audio",
                "Either audio_path or audio_url required"
            )
        
        try:
            logger.info(f"🎵 [{self.company_id}] Transcribing audio")
            
            if audio_url:
                transcription = self.multimedia_service.transcribe_audio_from_url(audio_url)
            else:
                transcription = self.multimedia_service.transcribe_audio(audio_path)
            
            return {
                "success": True,
                "tool": "transcribe_audio",
                "data": {
                    "transcription": transcription,
                    "length": len(transcription),
                    "source": "url" if audio_url else "file"
                }
            }
            
        except Exception as e:
            logger.error(f"❌ [{self.company_id}] Audio transcription error: {e}")
            return self._error_response("transcribe_audio", str(e))
    
    def _execute_analyze_image(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        ✅ Tool: analyze_image
        Analizar imagen usando GPT-4 Vision
        """
        if not self.multimedia_service:
            return self._error_response(
                "analyze_image",
                "MultimediaService not configured"
            )
        
        # Soportar tanto file como URL
        image_file = params.get("image_file")
        image_url = params.get("image_url")
        
        if not image_file and not image_url:
            return self._error_response(
                "analyze_image",
                "Either image_file or image_url required"
            )
        
        try:
            logger.info(f"🖼️ [{self.company_id}] Analyzing image")
            
            if image_url:
                analysis = self.multimedia_service.analyze_image_from_url(image_url)
            else:
                analysis = self.multimedia_service.analyze_image(image_file)
            
            return {
                "success": True,
                "tool": "analyze_image",
                "data": {
                    "analysis": analysis,
                    "length": len(analysis),
                    "source": "url" if image_url else "file"
                }
            }
            
        except Exception as e:
            logger.error(f"❌ [{self.company_id}] Image analysis error: {e}")
            return self._error_response("analyze_image", str(e))
    
    def _execute_text_to_speech(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        ✅ Tool: text_to_speech
        Convertir texto a voz usando OpenAI TTS
        """
        if not self.multimedia_service:
            return self._error_response(
                "text_to_speech",
                "MultimediaService not configured"
            )
        
        text = params.get("text", "")
        
        if not text:
            return self._error_response("text_to_speech", "text parameter required")
        
        try:
            logger.info(f"🔊 [{self.company_id}] Converting text to speech")
            
            audio_path = self.multimedia_service.text_to_speech(text)
            
            return {
                "success": True,
                "tool": "text_to_speech",
                "data": {
                    "audio_path": audio_path,
                    "text_length": len(text)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ [{self.company_id}] TTS error: {e}")
            return self._error_response("text_to_speech", str(e))
    
    def _execute_web_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        🟡 Tool: web_search (NOT IMPLEMENTED YET)
        Búsqueda en internet en tiempo real
        """
        return {
            "success": False,
            "tool": "web_search",
            "error": "web_search tool not implemented yet. Coming soon!"
        }
    
    def _execute_send_email(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        ✅ Tool: send_email
        Enviar emails automáticos

        Params:
            to_email: str - Email del destinatario
            subject: str - Asunto
            body_html: str (optional) - Cuerpo en HTML
            body_text: str (optional) - Cuerpo en texto plano
            template_name: str (optional) - Nombre del template
            template_vars: dict (optional) - Variables para el template
            cc: list (optional) - Lista de emails en copia
            bcc: list (optional) - Lista de emails en copia oculta
            reply_to: str (optional) - Email para responder
        """
        if not self.email_service:
            return self._error_response(
                "send_email",
                "EmailService not configured"
            )

        # Validar params requeridos
        to_email = params.get("to_email")
        if not to_email:
            return self._error_response(
                "send_email",
                "to_email parameter is required"
            )

        # Si hay template, usar send_template_email
        template_name = params.get("template_name")
        if template_name:
            template_vars = params.get("template_vars", {})

            logger.info(
                f"📧 [{self.company_id}] Sending template email: {template_name} to {to_email}"
            )

            result = self.email_service.send_template_email(
                to_email=to_email,
                template_name=template_name,
                template_vars=template_vars
            )

            return {
                "success": result["success"],
                "tool": "send_email",
                "data": result if result["success"] else None,
                "error": result.get("error")
            }

        # Envío normal
        subject = params.get("subject")
        body_html = params.get("body_html")
        body_text = params.get("body_text")

        if not subject:
            return self._error_response(
                "send_email",
                "subject parameter is required"
            )

        if not body_html and not body_text:
            return self._error_response(
                "send_email",
                "Either body_html or body_text is required"
            )

        logger.info(
            f"📧 [{self.company_id}] Sending email to {to_email}: {subject}"
        )

        result = self.email_service.send_email(
            to_email=to_email,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            cc=params.get("cc"),
            bcc=params.get("bcc"),
            reply_to=params.get("reply_to")
        )

        return {
            "success": result["success"],
            "tool": "send_email",
            "data": result if result["success"] else None,
            "error": result.get("error")
        }
    
    # ========================================================================
    # MÉTODOS AUXILIARES
    # ========================================================================
    
    def _error_response(self, tool_name: str, error_message: str) -> Dict[str, Any]:
        """Formato estándar de respuesta de error"""
        return {
            "success": False,
            "tool": tool_name,
            "error": error_message,
            "company_id": self.company_id
        }
    
    def get_available_tools(self) -> Dict[str, Dict[str, Any]]:
        """
        Obtener lista de tools disponibles y su estado de configuración.
        
        Returns:
            Dict con el estado de cada tool
        """
        tools_status = {}
        
        for tool_name, tool_def in self.tools_library.get_all_tools().items():
            # Determinar si la tool está disponible
            is_available = False
            missing_service = None
            
            if tool_name == "knowledge_base":
                is_available = self.vectorstore_service is not None
                missing_service = "VectorstoreService" if not is_available else None
            
            elif tool_name == "google_calendar":
                is_available = self.calendar_service is not None
                missing_service = "CalendarIntegrationService" if not is_available else None
            
            elif tool_name == "send_whatsapp":
                is_available = self.chatwoot_service is not None
                missing_service = "ChatwootService" if not is_available else None
            
            elif tool_name in ["transcribe_audio", "analyze_image", "text_to_speech"]:
                is_available = self.multimedia_service is not None
                missing_service = "MultimediaService" if not is_available else None
            
            else:
                is_available = False
                missing_service = "Not implemented"
            
            tools_status[tool_name] = {
                "available": is_available,
                "category": tool_def.category,
                "description": tool_def.description,
                "provider": tool_def.provider,
                "missing_service": missing_service
            }
        
        return tools_status
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Obtener información detallada de una tool específica"""
        tool_def = self.tools_library.get_tool(tool_name)
        if not tool_def:
            return None
        
        tools_status = self.get_available_tools()
        status = tools_status.get(tool_name, {})
        
        return {
            "name": tool_def.name,
            "category": tool_def.category,
            "description": tool_def.description,
            "provider": tool_def.provider,
            "config_required": tool_def.config_required,
            "parameters": tool_def.parameters,
            "output_type": tool_def.output_type,
            "available": status.get("available", False),
            "missing_service": status.get("missing_service")
        }
