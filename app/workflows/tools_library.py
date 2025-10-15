# ✅ CREAR: app/workflows/tools_library.py
# ⚠️ NO MODIFICAR archivos existentes todavía

"""
Este archivo es 100% nuevo, no rompe nada.
Simplemente ENVUELVE servicios existentes.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class ToolDefinition:
    """Definición de una herramienta disponible"""
    name: str
    category: str
    description: str
    provider: str
    config_required: List[str]
    parameters: List[str]
    output_type: str
    enabled_by_default: bool = False

class ToolsLibrary:
    """
    Catálogo de herramientas disponibles.
    
    🔒 IMPORTANTE: Este clase NO ejecuta nada, 
                   solo DESCRIBE qué tools existen.
    """
    
    AVAILABLE_TOOLS = {
        # === SEARCH & DATA ===
        "knowledge_base": ToolDefinition(
            name="knowledge_base",
            category="search",
            description="Busca en la base de conocimiento interna (RAG)",
            provider="internal",
            config_required=["company_id"],
            parameters=["query", "top_k"],
            output_type="List[Document]",
            enabled_by_default=True  # Ya existe en producción
        ),
        
        "web_search": ToolDefinition(
            name="web_search",
            category="search",
            description="Búsqueda en internet en tiempo real",
            provider="external",  # Por ahora no implementado
            config_required=["api_key"],
            parameters=["query", "max_results"],
            output_type="List[SearchResult]",
            enabled_by_default=False  # Deshabilitado por defecto
        ),
        
        # === CALENDAR ===
        "google_calendar": ToolDefinition(
            name="google_calendar",
            category="calendar",
            description="Integración con Google Calendar",
            provider="google",
            config_required=["oauth_token", "calendar_id"],
            parameters=["action", "event_data"],
            output_type="Event",
            enabled_by_default=True  # Ya existe en producción
        ),
        
        # === COMMUNICATION ===
        "send_whatsapp": ToolDefinition(
            name="send_whatsapp",
            category="communication",
            description="Envía mensajes por WhatsApp vía Chatwoot",
            provider="chatwoot",
            config_required=["chatwoot_account_id"],
            parameters=["to", "message"],
            output_type="MessageStatus",
            enabled_by_default=True  # Ya existe en producción
        ),
        
        "send_email": ToolDefinition(
            name="send_email",
            category="communication",
            description="Envía emails automáticos",
            provider="smtp",
            config_required=["smtp_config"],
            parameters=["to", "subject", "body"],
            output_type="EmailStatus",
            enabled_by_default=False  # Por implementar
        ),
        
        # === MULTIMEDIA ===
        "transcribe_audio": ToolDefinition(
            name="transcribe_audio",
            category="multimedia",
            description="Transcribe audio usando Whisper",
            provider="openai",
            config_required=["api_key"],
            parameters=["audio_file"],
            output_type="Transcription",
            enabled_by_default=True  # Ya existe
        ),
        
        "analyze_image": ToolDefinition(
            name="analyze_image",
            category="multimedia",
            description="Analiza imágenes con GPT Vision",
            provider="openai",
            config_required=["api_key"],
            parameters=["image_url", "prompt"],
            output_type="ImageAnalysis",
            enabled_by_default=True  # Ya existe
        ),
    }
    
    @classmethod
    def get_all_tools(cls) -> Dict[str, ToolDefinition]:
        """Retorna todas las tools disponibles"""
        return cls.AVAILABLE_TOOLS
    
    @classmethod
    def get_tool(cls, tool_name: str) -> Optional[ToolDefinition]:
        """Obtiene definición de una tool específica"""
        return cls.AVAILABLE_TOOLS.get(tool_name)
    
    @classmethod
    def get_tools_by_category(cls, category: str) -> Dict[str, ToolDefinition]:
        """Filtra tools por categoría"""
        return {
            name: tool 
            for name, tool in cls.AVAILABLE_TOOLS.items()
            if tool.category == category
        }
    
    @classmethod
    def get_enabled_tools_for_company(cls, company_config: dict) -> List[str]:
        """
        Retorna tools habilitadas para una empresa.
        
        Lee de company_config.get("enabled_tools", [])
        Si no existe, usa las habilitadas por defecto.
        """
        # Si la empresa tiene configuración específica
        if "enabled_tools" in company_config:
            return company_config["enabled_tools"]
        
        # Sino, usar las habilitadas por defecto
        return [
            name 
            for name, tool in cls.AVAILABLE_TOOLS.items()
            if tool.enabled_by_default
        ]
