# app/workflows/tool_executor.py - NUEVO ARCHIVO

from typing import Dict, Any, Optional
from app.workflows.tools_library import ToolsLibrary
from app.services.vectorstore_service import VectorstoreService
from app.services.calendar_integration_service import CalendarIntegrationService
from app.models.conversation import ConversationManager
import logging

logger = logging.getLogger(__name__)

class ToolExecutor:
    """
    Ejecutor unificado de herramientas.
    Envuelve servicios existentes sin modificarlos.
    """
    
    def __init__(self, company_id: str):
        self.company_id = company_id
        self.tools_library = ToolsLibrary()
        
        # Servicios que se inyectan externamente
        self.vectorstore_service: Optional[VectorstoreService] = None
        self.calendar_service: Optional[CalendarIntegrationService] = None
        self.conversation_manager: Optional[ConversationManager] = None
        
        logger.info(f"ToolExecutor initialized for company: {company_id}")
    
    def set_vectorstore_service(self, service: VectorstoreService):
        """Inyectar servicio de vectorstore"""
        self.vectorstore_service = service
    
    def set_calendar_service(self, service: CalendarIntegrationService):
        """Inyectar servicio de calendario"""
        self.calendar_service = service
    
    def set_conversation_manager(self, manager: ConversationManager):
        """Inyectar gestor de conversaciones"""
        self.conversation_manager = manager
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecutar una herramienta por nombre.
        
        Args:
            tool_name: Nombre de la tool (ej: "google_calendar", "knowledge_base")
            parameters: Parámetros específicos de la tool
            
        Returns:
            Resultado de la ejecución en formato estándar
        """
        try:
            # Verificar que la tool existe
            tool_def = self.tools_library.get_tool(tool_name)
            if not tool_def:
                return {
                    "success": False,
                    "error": f"Tool '{tool_name}' not found"
                }
            
            # Ejecutar según el tipo de tool
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
            
            else:
                return {
                    "success": False,
                    "error": f"Tool '{tool_name}' not implemented yet"
                }
                
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _execute_knowledge_base(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecutar búsqueda en knowledge base (RAG)"""
        if not self.vectorstore_service:
            return {
                "success": False,
                "error": "VectorstoreService not configured"
            }
        
        query = params.get("query", "")
        top_k = params.get("top_k", 3)
        
        try:
            docs = self.vectorstore_service.search_by_company(
                query, 
                self.company_id,
                k=top_k
            )
            
            return {
                "success": True,
                "tool": "knowledge_base",
                "results": [
                    {
                        "content": doc.page_content if hasattr(doc, 'page_content') else str(doc),
                        "metadata": doc.metadata if hasattr(doc, 'metadata') else {}
                    }
                    for doc in docs
                ]
            }
            
        except Exception as e:
            logger.error(f"Error in knowledge_base tool: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _execute_google_calendar(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecutar operación de Google Calendar"""
        if not self.calendar_service:
            return {
                "success": False,
                "error": "CalendarIntegrationService not configured"
            }
        
        action = params.get("action", "check_availability")
        
        try:
            if action == "check_availability":
                date = params.get("date")
                treatment = params.get("treatment", "general")
                
                result = self.calendar_service.check_availability(date, treatment)
                
                return {
                    "success": True,
                    "tool": "google_calendar",
                    "action": "check_availability",
                    "data": result
                }
            
            elif action == "create_booking":
                booking_data = params.get("booking_data", {})
                
                result = self.calendar_service.create_booking(booking_data)
                
                return {
                    "success": result.get("success", False),
                    "tool": "google_calendar",
                    "action": "create_booking",
                    "data": result
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown calendar action: {action}"
                }
                
        except Exception as e:
            logger.error(f"Error in google_calendar tool: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _execute_send_whatsapp(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecutar envío de WhatsApp (via Chatwoot)"""
        # TODO: Implementar cuando tengamos chatwoot_service
        return {
            "success": False,
            "message": "send_whatsapp tool pending implementation"
        }
    
    def _execute_transcribe_audio(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecutar transcripción de audio"""
        # TODO: Implementar cuando tengamos multimedia_service
        return {
            "success": False,
            "message": "transcribe_audio tool pending implementation"
        }
    
    def _execute_analyze_image(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecutar análisis de imagen"""
        # TODO: Implementar cuando tengamos multimedia_service
        return {
            "success": False,
            "message": "analyze_image tool pending implementation"
        }
    
    def get_available_tools(self) -> Dict[str, bool]:
        """Obtener lista de tools disponibles y su estado"""
        return {
            "knowledge_base": self.vectorstore_service is not None,
            "google_calendar": self.calendar_service is not None,
            "send_whatsapp": False,  # TODO
            "transcribe_audio": False,  # TODO
            "analyze_image": False  # TODO
        }
