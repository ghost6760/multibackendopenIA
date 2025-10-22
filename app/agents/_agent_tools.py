# app/agents/_agent_tools.py

"""
Registry y adaptador de herramientas por agente.
Mapea qué tools están disponibles para cada agente cognitivo y proporciona
interfaces para consultar y validar capacidades.

Este archivo NO reemplaza ToolsLibrary existente, sino que actúa como
capa de abstracción entre agentes cognitivos y el sistema de tools.
"""

from typing import Dict, List, Set, Optional, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# DEFINICIÓN DE HERRAMIENTAS POR AGENTE
# ============================================================================

class ToolCategory(Enum):
    """Categorías de herramientas"""
    KNOWLEDGE = "knowledge"  # Búsqueda en knowledge base
    CALENDAR = "calendar"  # Operaciones de calendario
    SCHEDULING = "scheduling"  # Agendamiento de citas
    COMMUNICATION = "communication"  # Envío de mensajes, emails
    DATA_RETRIEVAL = "data_retrieval"  # Consulta de datos
    VALIDATION = "validation"  # Validaciones
    EMERGENCY = "emergency"  # Herramientas de emergencia


# Mapeo completo: AgentType -> Tools disponibles
AGENT_TOOLS_REGISTRY: Dict[str, List[str]] = {
    "schedule_agent": [
        "knowledge_base_search",
        "get_available_slots",
        "create_appointment",
        "check_availability",
        "get_calendar_events",
        "validate_appointment_data",
        "send_confirmation"
    ],
    
    "emergency_agent": [
        "knowledge_base_search",
        "get_emergency_protocols",
        "escalate_to_human",
        "send_urgent_notification",
        "check_availability",
        "create_priority_appointment"
    ],
    
    "sales_agent": [
        "knowledge_base_search",
        "get_product_info",
        "get_pricing",
        "calculate_estimate",
        "send_quote",
        "schedule_consultation"
    ],
    
    "support_agent": [
        "knowledge_base_search",
        "get_faq",
        "search_documentation",
        "create_ticket",
        "send_followup"
    ],
    
    "planning_agent": [
        "knowledge_base_search",
        "get_treatment_plans",
        "get_recommendations",
        "calculate_duration",
        "get_available_slots"
    ],
    
    "availability_agent": [
        "get_available_slots",
        "check_availability",
        "get_calendar_events",
        "get_business_hours"
    ],
    
    "router_agent": [
        "knowledge_base_search",
        "classify_intent",
        "get_agent_capabilities"
    ]
}


# Metadata de cada herramienta
TOOL_METADATA: Dict[str, Dict[str, Any]] = {
    "knowledge_base_search": {
        "category": ToolCategory.KNOWLEDGE,
        "description": "Buscar información en la base de conocimiento vectorial",
        "required_params": ["query", "company_id"],
        "optional_params": ["top_k", "filter"],
        "critical": True,
        "requires_vectorstore": True
    },
    
    "get_available_slots": {
        "category": ToolCategory.SCHEDULING,
        "description": "Obtener slots disponibles en el calendario",
        "required_params": ["start_date", "end_date", "company_id"],
        "optional_params": ["duration", "provider_id"],
        "critical": True,
        "requires_calendar": True
    },
    
    "create_appointment": {
        "category": ToolCategory.SCHEDULING,
        "description": "Crear una nueva cita en el calendario",
        "required_params": ["datetime", "patient_info", "service", "company_id"],
        "optional_params": ["provider_id", "notes"],
        "critical": True,
        "requires_calendar": True,
        "requires_validation": True
    },
    
    "check_availability": {
        "category": ToolCategory.CALENDAR,
        "description": "Verificar disponibilidad en una fecha/hora específica",
        "required_params": ["datetime", "company_id"],
        "optional_params": ["duration", "provider_id"],
        "critical": False,
        "requires_calendar": True
    },
    
    "get_calendar_events": {
        "category": ToolCategory.CALENDAR,
        "description": "Obtener eventos del calendario",
        "required_params": ["start_date", "end_date", "company_id"],
        "optional_params": ["event_type"],
        "critical": False,
        "requires_calendar": True
    },
    
    "validate_appointment_data": {
        "category": ToolCategory.VALIDATION,
        "description": "Validar datos de cita antes de crear",
        "required_params": ["appointment_data"],
        "optional_params": [],
        "critical": True,
        "requires_validation": True
    },
    
    "send_confirmation": {
        "category": ToolCategory.COMMUNICATION,
        "description": "Enviar confirmación por email/SMS",
        "required_params": ["recipient", "message_type", "data"],
        "optional_params": ["channel"],
        "critical": False,
        "requires_communication": True
    },
    
    "get_emergency_protocols": {
        "category": ToolCategory.EMERGENCY,
        "description": "Obtener protocolos de emergencia",
        "required_params": ["emergency_type", "company_id"],
        "optional_params": [],
        "critical": True,
        "requires_vectorstore": True
    },
    
    "escalate_to_human": {
        "category": ToolCategory.EMERGENCY,
        "description": "Escalar a atención humana",
        "required_params": ["reason", "priority", "context"],
        "optional_params": [],
        "critical": True,
        "requires_communication": True
    },
    
    "send_urgent_notification": {
        "category": ToolCategory.EMERGENCY,
        "description": "Enviar notificación urgente",
        "required_params": ["recipient", "message", "priority"],
        "optional_params": [],
        "critical": True,
        "requires_communication": True
    },
    
    "get_product_info": {
        "category": ToolCategory.DATA_RETRIEVAL,
        "description": "Obtener información de productos/servicios",
        "required_params": ["product_id", "company_id"],
        "optional_params": [],
        "critical": False,
        "requires_vectorstore": True
    },
    
    "get_pricing": {
        "category": ToolCategory.DATA_RETRIEVAL,
        "description": "Obtener precios de servicios",
        "required_params": ["service_id", "company_id"],
        "optional_params": [],
        "critical": False,
        "requires_vectorstore": True
    },
    
    "calculate_estimate": {
        "category": ToolCategory.DATA_RETRIEVAL,
        "description": "Calcular estimado de costo",
        "required_params": ["services", "company_id"],
        "optional_params": ["discounts"],
        "critical": False,
        "requires_vectorstore": False
    },
    
    "create_priority_appointment": {
        "category": ToolCategory.EMERGENCY,
        "description": "Crear cita prioritaria (emergencia)",
        "required_params": ["datetime", "patient_info", "emergency_type", "company_id"],
        "optional_params": ["notes"],
        "critical": True,
        "requires_calendar": True
    }
}


# ============================================================================
# CLASE REGISTRY
# ============================================================================

class AgentToolsRegistry:
    """
    Registry central de herramientas por agente.
    Proporciona métodos para consultar, validar y obtener metadata de tools.
    """
    
    def __init__(self):
        self._agent_tools = AGENT_TOOLS_REGISTRY
        self._tool_metadata = TOOL_METADATA
        logger.info("AgentToolsRegistry initialized")
    
    def get_tools_for_agent(self, agent_type: str) -> List[str]:
        """
        Obtener lista de tools disponibles para un agente.
        
        Args:
            agent_type: Tipo de agente (ej: "schedule_agent")
        
        Returns:
            Lista de nombres de herramientas
        """
        tools = self._agent_tools.get(agent_type, [])
        logger.debug(f"Tools for {agent_type}: {tools}")
        return tools
    
    def get_tool_metadata(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Obtener metadata de una herramienta.
        
        Args:
            tool_name: Nombre de la herramienta
        
        Returns:
            Dict con metadata o None si no existe
        """
        return self._tool_metadata.get(tool_name)
    
    def is_tool_available_for_agent(self, agent_type: str, tool_name: str) -> bool:
        """
        Verificar si una tool está disponible para un agente.
        
        Args:
            agent_type: Tipo de agente
            tool_name: Nombre de la herramienta
        
        Returns:
            True si está disponible
        """
        tools = self.get_tools_for_agent(agent_type)
        return tool_name in tools
    
    def get_critical_tools(self, agent_type: str) -> List[str]:
        """
        Obtener herramientas críticas de un agente.
        
        Args:
            agent_type: Tipo de agente
        
        Returns:
            Lista de tools críticas
        """
        tools = self.get_tools_for_agent(agent_type)
        critical = []
        
        for tool in tools:
            metadata = self.get_tool_metadata(tool)
            if metadata and metadata.get("critical", False):
                critical.append(tool)
        
        return critical
    
    def get_tools_by_category(
        self,
        agent_type: str,
        category: ToolCategory
    ) -> List[str]:
        """
        Obtener herramientas de una categoría específica.
        
        Args:
            agent_type: Tipo de agente
            category: Categoría de herramientas
        
        Returns:
            Lista de tools de esa categoría
        """
        tools = self.get_tools_for_agent(agent_type)
        filtered = []
        
        for tool in tools:
            metadata = self.get_tool_metadata(tool)
            if metadata and metadata.get("category") == category:
                filtered.append(tool)
        
        return filtered
    
    def validate_tool_params(
        self,
        tool_name: str,
        params: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Validar parámetros de una herramienta.
        
        Args:
            tool_name: Nombre de la herramienta
            params: Parámetros a validar
        
        Returns:
            Tupla (es_válido, mensaje_error)
        """
        metadata = self.get_tool_metadata(tool_name)
        
        if not metadata:
            return False, f"Unknown tool: {tool_name}"
        
        # Verificar parámetros requeridos
        required = metadata.get("required_params", [])
        missing = [p for p in required if p not in params]
        
        if missing:
            return False, f"Missing required params: {missing}"
        
        return True, None
    
    def get_agent_capabilities_manifest(self, agent_type: str) -> Dict[str, Any]:
        """
        Obtener manifest completo de capacidades de un agente.
        
        Args:
            agent_type: Tipo de agente
        
        Returns:
            Dict con manifest completo
        """
        tools = self.get_tools_for_agent(agent_type)
        critical_tools = self.get_critical_tools(agent_type)
        
        # Agrupar por categoría
        by_category = {}
        for category in ToolCategory:
            category_tools = self.get_tools_by_category(agent_type, category)
            if category_tools:
                by_category[category.value] = category_tools
        
        # Requisitos
        requires = set()
        for tool in tools:
            metadata = self.get_tool_metadata(tool)
            if metadata:
                if metadata.get("requires_vectorstore"):
                    requires.add("vectorstore_service")
                if metadata.get("requires_calendar"):
                    requires.add("calendar_service")
                if metadata.get("requires_communication"):
                    requires.add("communication_service")
                if metadata.get("requires_validation"):
                    requires.add("validation_service")
        
        return {
            "agent_type": agent_type,
            "total_tools": len(tools),
            "critical_tools": critical_tools,
            "tools_by_category": by_category,
            "all_tools": tools,
            "required_services": list(requires),
            "metadata": {
                "supports_reasoning": True,
                "supports_tool_use": len(tools) > 0,
                "supports_planning": agent_type in ["planning_agent", "schedule_agent"]
            }
        }
    
    def register_custom_tool(
        self,
        agent_type: str,
        tool_name: str,
        metadata: Dict[str, Any]
    ):
        """
        Registrar herramienta personalizada para un agente.
        
        Args:
            agent_type: Tipo de agente
            tool_name: Nombre de la herramienta
            metadata: Metadata de la herramienta
        """
        if agent_type not in self._agent_tools:
            self._agent_tools[agent_type] = []
        
        if tool_name not in self._agent_tools[agent_type]:
            self._agent_tools[agent_type].append(tool_name)
        
        self._tool_metadata[tool_name] = metadata
        
        logger.info(f"Registered custom tool '{tool_name}' for {agent_type}")


# ============================================================================
# INSTANCIA GLOBAL (SINGLETON)
# ============================================================================

_registry_instance: Optional[AgentToolsRegistry] = None

def get_agent_tools_registry() -> AgentToolsRegistry:
    """
    Obtener instancia singleton del registry.
    
    Returns:
        AgentToolsRegistry
    """
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = AgentToolsRegistry()
    return _registry_instance


# ============================================================================
# FUNCIONES DE UTILIDAD
# ============================================================================

def get_tools_for_agent(agent_type: str) -> List[str]:
    """Shortcut para obtener tools de un agente"""
    registry = get_agent_tools_registry()
    return registry.get_tools_for_agent(agent_type)


def validate_tool_for_agent(agent_type: str, tool_name: str) -> bool:
    """Shortcut para validar tool de un agente"""
    registry = get_agent_tools_registry()
    return registry.is_tool_available_for_agent(agent_type, tool_name)


def get_agent_manifest(agent_type: str) -> Dict[str, Any]:
    """Shortcut para obtener manifest de un agente"""
    registry = get_agent_tools_registry()
    return registry.get_agent_capabilities_manifest(agent_type)


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "ToolCategory",
    "AgentToolsRegistry",
    "get_agent_tools_registry",
    "get_tools_for_agent",
    "validate_tool_for_agent",
    "get_agent_manifest",
    "AGENT_TOOLS_REGISTRY",
    "TOOL_METADATA"
]
