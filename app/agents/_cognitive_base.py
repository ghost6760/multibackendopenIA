"""
Base cognitiva compartida para agentes LangGraph.

Este módulo define la infraestructura común que todos los agentes cognitivos
deben implementar, incluyendo tipos de estado, interfaces de nodos y contratos
de ejecución.

IMPORTANTE: Los agentes cognitivos mantienen los mismos nombres de clase y firmas
públicas que sus versiones anteriores, pero internamente usan LangGraph para
razonamiento, decisión y ejecución de tools.
"""

from typing import TypedDict, Annotated, Sequence, Any, Dict, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from abc import ABC, abstractmethod
import operator
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS Y CONSTANTES
# ============================================================================

class AgentType(str, Enum):
    """Tipos de agentes en el sistema."""
    SCHEDULE = "schedule"
    EMERGENCY = "emergency"
    PLANNING = "planning"
    SALES = "sales"
    SUPPORT = "support"
    ROUTER = "router"
    AVAILABILITY = "availability"


class NodeType(str, Enum):
    """Tipos de nodos en el grafo cognitivo."""
    REASONING = "reasoning"
    TOOL_EXECUTION = "tool_execution"
    VALIDATION = "validation"
    DECISION = "decision"
    RESPONSE_GENERATION = "response_generation"


class ExecutionStatus(str, Enum):
    """Estados de ejecución de un agente."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    DEGRADED = "degraded"  # Éxito parcial con safe-fail


class AgentCapability(Enum):
    """Capacidades que puede tener un agente cognitivo"""
    REASONING = "reasoning"  # Razonamiento multi-paso
    TOOL_USE = "tool_use"  # Uso dinámico de herramientas
    MEMORY = "memory"  # Memoria de corto/largo plazo
    PLANNING = "planning"  # Planificación de acciones
    REFLECTION = "reflection"  # Auto-evaluación
    MULTIMODAL = "multimodal"  # Procesamiento de múltiples modalidades


class DecisionType(Enum):
    """Tipos de decisiones que toma un agente"""
    TOOL_SELECTION = "tool_selection"
    NEXT_ACTION = "next_action"
    RESPONSE_GENERATION = "response_generation"
    ESCALATION = "escalation"
    TERMINATION = "termination"


# ============================================================================
# TIPOS DE ESTADO (LangGraph State)
# ============================================================================

class ToolCall(TypedDict):
    """Representa una llamada a una tool."""
    tool_name: str
    arguments: Dict[str, Any]
    timestamp: str
    node_id: str


class ToolResult(TypedDict):
    """Resultado de ejecución de una tool."""
    tool_name: str
    success: bool
    result: Any
    error: Optional[str]
    latency_ms: float
    timestamp: str


class ReasoningStep(TypedDict):
    """Un paso de razonamiento del agente."""
    step_id: str
    node_type: str  # NodeType
    description: str
    thought: str
    action: Optional[str]
    observation: Optional[str]
    decision: Optional[str]
    confidence: Optional[float]
    timestamp: str


class AgentState(TypedDict):
    """
    Estado base que todos los agentes cognitivos deben mantener.
    
    Este estado se pasa entre nodos del grafo LangGraph y permite:
    - Razonamiento multi-paso
    - Debugging y observabilidad
    - Reentrancia y recuperación de errores
    - Telemetría detallada
    """
    # Inputs originales (obligatorios)
    question: str
    chat_history: List[Dict[str, str]]
    user_id: str
    company_id: Optional[str]
    
    # Estado de ejecución
    agent_type: str  # AgentType
    execution_id: str
    status: str  # ExecutionStatus
    current_node: str
    
    # Razonamiento y decisiones
    reasoning_steps: Annotated[List[ReasoningStep], operator.add]
    tools_called: Annotated[List[ToolCall], operator.add]
    tool_results: Annotated[List[ToolResult], operator.add]
    
    # Contexto y memoria
    context: Dict[str, Any]  # Información adicional recuperada
    intermediate_results: Dict[str, Any]  # Resultados parciales
    
    # Herramientas disponibles
    tools_available: List[str]
    
    # Decisiones tomadas
    decisions: List[Dict[str, Any]]
    confidence_scores: Dict[str, float]
    
    # Contexto específico por tipo de agente
    vectorstore_context: Optional[str]
    calendar_context: Optional[Dict]
    
    # Output final
    response: Optional[str]
    
    # Metadata y telemetría
    metadata: Dict[str, Any]
    errors: Annotated[List[str], operator.add]
    warnings: Annotated[List[str], operator.add]
    
    # Control de flujo
    should_continue: bool
    current_step: int
    retry_count: int
    
    # Timestamps
    started_at: str
    completed_at: Optional[str]


class ToolExecutionRecord(TypedDict):
    """Registro de ejecución de una herramienta (legacy compatible)"""
    tool_name: str
    inputs: Dict[str, Any]
    output: Any
    success: bool
    error: Optional[str]
    latency_ms: float
    timestamp: str


# ============================================================================
# DATACLASSES DE CONFIGURACIÓN
# ============================================================================

@dataclass
class AgentCapabilityDef:
    """Define una capacidad de un agente."""
    name: str
    description: str
    tools_required: List[str]
    priority: int = 0
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentManifest:
    """
    Manifest de capacidades y configuración de un agente.
    
    Define qué puede hacer el agente, qué tools necesita,
    prioridades y metadata operativa.
    """
    agent_type: str  # AgentType
    display_name: str
    description: str
    capabilities: List[AgentCapabilityDef]
    required_tools: List[str]
    optional_tools: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    priority: int = 0
    max_retries: int = 3
    timeout_seconds: int = 30
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CognitiveConfig:
    """Configuración para el motor cognitivo de un agente."""
    enable_reasoning_traces: bool = True
    enable_tool_validation: bool = True
    enable_guardrails: bool = True
    max_reasoning_steps: int = 10
    reasoning_temperature: float = 0.7
    require_confirmation_for_critical_actions: bool = True
    safe_fail_on_tool_error: bool = True
    persist_state: bool = True


# ============================================================================
# INTERFACES BASE
# ============================================================================

class CognitiveAgentBase(ABC):
    """
    Clase base abstracta para agentes cognitivos.
    
    IMPORTANTE: Las subclases DEBEN:
    1. Mantener el mismo nombre de clase que sus versiones anteriores
    2. Implementar invoke(inputs: dict) -> str
    3. Mantener métodos de inyección: set_vectorstore_service(), etc.
    4. Usar LangGraph internamente para el grafo de decisión
    """
    
    def __init__(
        self,
        agent_type: AgentType,
        manifest: AgentManifest,
        config: CognitiveConfig
    ):
        """
        Inicializa el agente cognitivo.
        
        Args:
            agent_type: Tipo de agente
            manifest: Manifest de capacidades
            config: Configuración cognitiva
        """
        self.agent_type = agent_type
        self.manifest = manifest
        self.config = config
        
        # Servicios inyectados (inicialmente None)
        self._tool_executor = None
        self._vectorstore_service = None
        self._prompt_service = None
        self._state_manager = None
        self._condition_evaluator = None
        
        logger.info(
            f"[{agent_type.value}] Cognitive agent initialized with "
            f"{len(manifest.capabilities)} capabilities"
        )
    
    # ========================================================================
    # MÉTODOS PÚBLICOS (MANTENER FIRMAS)
    # ========================================================================
    
    @abstractmethod
    def invoke(self, inputs: dict) -> str:
        """
        Punto de entrada principal del agente.
        
        Args:
            inputs: Diccionario con keys: question, chat_history, user_id, etc.
        
        Returns:
            str: Respuesta generada por el agente
        
        IMPORTANTE: Esta firma NO debe cambiar para mantener compatibilidad.
        """
        raise NotImplementedError("Subclases deben implementar invoke()")
    
    def set_vectorstore_service(self, service):
        """Inyecta el servicio de vectorstore."""
        self._vectorstore_service = service
        logger.debug(f"[{self.agent_type.value}] VectorstoreService injected")
    
    def set_prompt_service(self, service):
        """Inyecta el servicio de prompts."""
        self._prompt_service = service
        logger.debug(f"[{self.agent_type.value}] PromptService injected")
    
    # ========================================================================
    # MÉTODOS DE INYECCIÓN NUEVOS (PERMITIDOS)
    # ========================================================================
    
    def set_tool_executor(self, executor):
        """Inyecta el ejecutor de tools."""
        self._tool_executor = executor
        logger.debug(f"[{self.agent_type.value}] ToolExecutor injected")
    
    def set_state_manager(self, manager):
        """Inyecta el gestor de estado."""
        self._state_manager = manager
        logger.debug(f"[{self.agent_type.value}] StateManager injected")
    
    def set_condition_evaluator(self, evaluator):
        """Inyecta el evaluador de condiciones para guardrails."""
        self._condition_evaluator = evaluator
        logger.debug(f"[{self.agent_type.value}] ConditionEvaluator injected")
    
    # ========================================================================
    # MÉTODOS ABSTRACTOS (IMPLEMENTAR EN SUBCLASES)
    # ========================================================================
    
    @abstractmethod
    def build_graph(self):
        """
        Construir el grafo de LangGraph para este agente.
        
        Returns:
            StateGraph de LangGraph
        """
        pass
    
    # ========================================================================
    # MÉTODOS INTERNOS (HELPERS)
    # ========================================================================
    
    def _create_initial_state(self, inputs: dict) -> AgentState:
        """
        Crea el estado inicial para LangGraph.
        
        Args:
            inputs: Inputs del usuario
        
        Returns:
            AgentState inicial
        """
        execution_id = f"{self.agent_type.value}_{datetime.utcnow().isoformat()}"
        
        return AgentState(
            # Inputs
            question=inputs.get("question", ""),
            chat_history=inputs.get("chat_history", []),
            user_id=inputs.get("user_id", ""),
            company_id=inputs.get("company_id"),
            
            # Ejecución
            agent_type=self.agent_type.value,
            execution_id=execution_id,
            status=ExecutionStatus.PENDING.value,
            current_node="start",
            
            # Razonamiento
            reasoning_steps=[],
            tools_called=[],
            tool_results=[],
            
            # Herramientas
            tools_available=self.manifest.required_tools + self.manifest.optional_tools,
            
            # Decisiones
            decisions=[],
            confidence_scores={},
            
            # Contexto
            context={},
            intermediate_results={},
            vectorstore_context=None,
            calendar_context=None,
            
            # Output
            response=None,
            
            # Metadata
            metadata={
                "agent_type": self.agent_type.value,
                "manifest_version": self.manifest.metadata.get("version", "1.0"),
                "config": {
                    "enable_reasoning_traces": self.config.enable_reasoning_traces,
                    "enable_guardrails": self.config.enable_guardrails
                }
            },
            errors=[],
            warnings=[],
            
            # Control
            should_continue=True,
            current_step=0,
            retry_count=0,
            
            # Timestamps
            started_at=datetime.utcnow().isoformat(),
            completed_at=None
        )
    
    def _add_reasoning_step(
        self,
        state: AgentState,
        node_type: NodeType,
        description: str,
        thought: str = "",
        action: Optional[str] = None,
        observation: Optional[str] = None,
        decision: Optional[str] = None,
        confidence: Optional[float] = None
    ) -> ReasoningStep:
        """
        Añade un paso de razonamiento al estado.
        
        Args:
            state: Estado actual
            node_type: Tipo de nodo
            description: Descripción del razonamiento
            thought: Pensamiento del agente
            action: Acción tomada (opcional)
            observation: Observación obtenida (opcional)
            decision: Decisión tomada (opcional)
            confidence: Nivel de confianza (opcional)
        
        Returns:
            ReasoningStep creado
        """
        step = ReasoningStep(
            step_id=f"step_{len(state['reasoning_steps']) + 1}",
            node_type=node_type.value,
            description=description,
            thought=thought or description,
            action=action,
            observation=observation,
            decision=decision,
            confidence=confidence,
            timestamp=datetime.utcnow().isoformat()
        )
        return step
    
    def _record_reasoning_step(
        self,
        state: AgentState,
        thought: str,
        action: Optional[str] = None,
        observation: Optional[str] = None
    ) -> AgentState:
        """
        Registrar paso de razonamiento (método legacy compatible).
        
        Args:
            state: Estado actual
            thought: Pensamiento del agente
            action: Acción tomada (opcional)
            observation: Observación obtenida (opcional)
        
        Returns:
            Estado actualizado
        """
        step = self._add_reasoning_step(
            state,
            NodeType.REASONING,
            thought,
            thought=thought,
            action=action,
            observation=observation
        )
        
        # Persistir en state manager si está disponible
        if self._state_manager:
            try:
                self._state_manager.record_step(
                    agent_name=self.agent_type.value,
                    user_id=state.get("user_id"),
                    step=step
                )
            except Exception as e:
                logger.error(f"Failed to persist reasoning step: {e}")
        
        return state
    
    def _record_tool_execution(
        self,
        state: AgentState,
        tool_name: str,
        inputs: Dict[str, Any],
        output: Any,
        success: bool,
        latency_ms: float,
        error: Optional[str] = None
    ) -> AgentState:
        """
        Registrar ejecución de herramienta.
        
        Args:
            state: Estado actual
            tool_name: Nombre de la herramienta
            inputs: Inputs usados
            output: Output obtenido
            success: Si fue exitosa
            latency_ms: Latencia en milisegundos
            error: Error si ocurrió
        
        Returns:
            Estado actualizado
        """
        record: ToolExecutionRecord = {
            "tool_name": tool_name,
            "inputs": inputs,
            "output": output,
            "success": success,
            "error": error,
            "latency_ms": latency_ms,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Persistir en state manager
        if self._state_manager:
            try:
                self._state_manager.record_tool_execution(
                    agent_name=self.agent_type.value,
                    user_id=state.get("user_id"),
                    tool_record=record
                )
            except Exception as e:
                logger.error(f"Failed to persist tool execution: {e}")
        
        return state
    
    def _validate_inputs(self, inputs: dict) -> bool:
        """
        Valida que los inputs tengan los campos obligatorios.
        
        Args:
            inputs: Inputs del usuario
        
        Returns:
            bool: True si válidos
        
        Raises:
            ValueError: Si faltan campos obligatorios
        """
        required_fields = ["question", "chat_history", "user_id"]
        missing = [f for f in required_fields if f not in inputs]
        
        if missing:
            raise ValueError(f"Faltan campos obligatorios: {missing}")
        
        return True
    
    def _should_continue(self, state: AgentState) -> bool:
        """
        Determinar si el agente debe continuar procesando.
        
        Args:
            state: Estado actual
        
        Returns:
            True si debe continuar, False si debe terminar
        """
        # Verificar errores
        if state.get("errors") and len(state["errors"]) > 0:
            return False
        
        # Verificar si ya hay respuesta
        if state.get("response"):
            return False
        
        # Verificar límite de pasos
        max_steps = self.config.max_reasoning_steps
        if state.get("current_step", 0) >= max_steps:
            logger.warning(
                f"[{self.agent_type.value}] Max steps reached ({max_steps})"
            )
            return False
        
        # Verificar flag explícito
        return state.get("should_continue", True)
    
    def _build_response_from_state(self, state: AgentState) -> str:
        """
        Construye la respuesta final desde el estado.
        
        Args:
            state: Estado final
        
        Returns:
            str: Respuesta formateada
        """
        if state.get("response"):
            return state["response"]
        
        # Safe-fail: generar respuesta de degradación
        return self._generate_degraded_response(state)
    
    def _format_final_response(self, state: AgentState) -> str:
        """
        Formatear respuesta final del agente (método legacy compatible).
        
        Args:
            state: Estado final
        
        Returns:
            String con respuesta formateada
        """
        return self._build_response_from_state(state)
    
    def _generate_degraded_response(self, state: AgentState) -> str:
        """
        Genera una respuesta de degradación cuando algo falla.
        
        Args:
            state: Estado actual
        
        Returns:
            str: Respuesta de safe-fail
        """
        errors = state.get("errors", [])
        if errors:
            logger.error(f"[{self.agent_type.value}] Errors during execution: {errors}")
        
        return (
            "Lo siento, no pude procesar completamente tu solicitud en este momento. "
            "¿Podrías reformular tu pregunta o intentarlo de nuevo?"
        )
    
    def _get_telemetry(self, state: AgentState) -> Dict[str, Any]:
        """
        Obtener telemetría de la ejecución.
        
        Args:
            state: Estado final
        
        Returns:
            Dict con métricas
        """
        return {
            "agent_name": self.agent_type.value,
            "agent_type": self.__class__.__name__,
            "execution_id": state.get("execution_id"),
            "user_id": state.get("user_id"),
            "company_id": state.get("company_id"),
            "reasoning_steps": len(state.get("reasoning_steps", [])),
            "tools_used": [t["tool_name"] for t in state.get("tool_results", [])],
            "total_latency_ms": sum(
                t.get("latency_ms", 0) for t in state.get("tool_results", [])
            ),
            "errors_count": len(state.get("errors", [])),
            "warnings_count": len(state.get("warnings", [])),
            "success": len(state.get("errors", [])) == 0,
            "timestamp": datetime.utcnow().isoformat()
        }


# ============================================================================
# NODE BUILDERS (Helpers para construir nodos LangGraph)
# ============================================================================

def create_reasoning_node(
    name: str,
    reasoning_fn: Callable[[AgentState], AgentState]
) -> Callable:
    """
    Factory para crear nodos de razonamiento.
    
    Args:
        name: Nombre del nodo
        reasoning_fn: Función que realiza el razonamiento
    
    Returns:
        Función de nodo para LangGraph
    """
    def node(state: AgentState) -> AgentState:
        state["current_node"] = name
        state["current_step"] = state.get("current_step", 0) + 1
        return reasoning_fn(state)
    
    return node


def create_tool_node(
    name: str,
    tool_executor,
    tool_selection_fn: Callable[[AgentState], List[str]]
) -> Callable:
    """
    Factory para crear nodos de ejecución de tools.
    
    Args:
        name: Nombre del nodo
        tool_executor: Ejecutor de tools
        tool_selection_fn: Función que decide qué tools ejecutar
    
    Returns:
        Función de nodo para LangGraph
    """
    def node(state: AgentState) -> AgentState:
        state["current_node"] = name
        state["current_step"] = state.get("current_step", 0) + 1
        tools_to_execute = tool_selection_fn(state)
        
        for tool_name in tools_to_execute:
            # Registrar llamada
            tool_call = ToolCall(
                tool_name=tool_name,
                arguments={},  # Extraer de state según el tool
                timestamp=datetime.utcnow().isoformat(),
                node_id=name
            )
            
            # Aquí se ejecutaría la tool con tool_executor
            # La implementación real se hace en agent_tools_service.py
            pass
        
        return state
    
    return node


# ============================================================================
# UTILIDADES COMPARTIDAS
# ============================================================================

def validate_agent_state(state: AgentState) -> bool:
    """
    Validar que el estado del agente tiene los campos mínimos.
    
    Args:
        state: Estado a validar
    
    Returns:
        True si es válido
    """
    required_fields = ["question", "user_id"]
    
    for field in required_fields:
        if field not in state:
            logger.error(f"Missing required field in AgentState: {field}")
            return False
    
    return True


def merge_states(base_state: AgentState, updates: Dict[str, Any]) -> AgentState:
    """
    Mergear actualizaciones en el estado base.
    
    Args:
        base_state: Estado base
        updates: Actualizaciones a aplicar
    
    Returns:
        Estado mergeado
    """
    merged = base_state.copy()
    
    for key, value in updates.items():
        if isinstance(value, list) and key in merged and isinstance(merged[key], list):
            # Para listas, extender
            merged[key].extend(value)
        elif isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
            # Para dicts, mergear
            merged[key].update(value)
        else:
            # Para otros, reemplazar
            merged[key] = value
    
    return merged


def get_execution_metrics(state: AgentState) -> Dict[str, Any]:
    """
    Extrae métricas de ejecución del estado.
    
    Args:
        state: Estado del agente
    
    Returns:
        Dict con métricas
    """
    started = datetime.fromisoformat(state["started_at"])
    completed = datetime.fromisoformat(state["completed_at"]) if state.get("completed_at") else datetime.utcnow()
    
    return {
        "execution_id": state["execution_id"],
        "agent_type": state["agent_type"],
        "status": state["status"],
        "latency_ms": (completed - started).total_seconds() * 1000,
        "reasoning_steps": len(state["reasoning_steps"]),
        "tools_used": len(state["tools_called"]),
        "tools_succeeded": sum(1 for r in state["tool_results"] if r.get("success")),
        "tools_failed": sum(1 for r in state["tool_results"] if not r.get("success")),
        "errors_count": len(state["errors"]),
        "warnings_count": len(state["warnings"])
    }


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    # Enums
    "AgentType",
    "NodeType",
    "ExecutionStatus",
    "AgentCapability",
    "DecisionType",
    
    # TypedDicts
    "AgentState",
    "ToolCall",
    "ToolResult",
    "ReasoningStep",
    "ToolExecutionRecord",
    
    # Dataclasses
    "AgentCapabilityDef",
    "AgentManifest",
    "CognitiveConfig",
    
    # Classes
    "CognitiveAgentBase",
    
    # Node builders
    "create_reasoning_node",
    "create_tool_node",
    
    # Utils
    "validate_agent_state",
    "merge_states",
    "get_execution_metrics"
]
