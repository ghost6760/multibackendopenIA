"""
Base cognitiva para agentes LangGraph (Sin compatibilidad legacy).

PRINCIPIOS:
- NO normalizar ni transformar datos
- Pasar state crudo a LangGraph
- Devolver exactamente lo que graph.run() retorne
- Fail-fast (no fallbacks silenciosos)
"""

from typing import TypedDict, Annotated, Any, Dict, List, Optional
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
    node_type: str
    description: str
    thought: str
    action: Optional[str]
    observation: Optional[str]
    decision: Optional[str]
    confidence: Optional[float]
    timestamp: str


class AgentState(TypedDict):
    """
    Estado base para agentes LangGraph.
    
    NO incluye lógica de normalización - solo estructura de datos.
    Los nodos del grafo son responsables de interpretar los datos.
    """
    # Core inputs (pasados directamente desde invocación)
    prompt_payload: Dict[str, Any]  # JSONB desde PromptService
    input_state: Dict[str, Any]     # Datos de entrada sin procesar
    
    # Execution metadata
    agent_type: str
    execution_id: str
    company_id: int
    agent_key: str
    
    # Tracking
    reasoning_steps: Annotated[List[ReasoningStep], operator.add]
    tools_called: Annotated[List[ToolCall], operator.add]
    tool_results: Annotated[List[ToolResult], operator.add]
    
    # Context (información runtime adicional)
    context: Dict[str, Any]
    
    # Control flow
    should_continue: bool
    current_step: int
    
    # Timestamps
    started_at: str
    completed_at: Optional[str]


# ============================================================================
# DATACLASSES DE CONFIGURACIÓN
# ============================================================================

@dataclass
class AgentManifest:
    """
    Manifest de capacidades y configuración de un agente.
    """
    agent_type: str
    display_name: str
    description: str
    required_tools: List[str]
    optional_tools: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    max_retries: int = 3
    timeout_seconds: int = 30
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CognitiveConfig:
    """Configuración para el motor cognitivo de un agente."""
    max_reasoning_steps: int = 10
    enable_tracing: bool = True
    fail_fast: bool = True  # Fail-fast en errores críticos


# ============================================================================
# BASE CLASS (Minimalista)
# ============================================================================

class CognitiveAgentBase(ABC):
    """
    Clase base minimalista para agentes LangGraph.
    
    Responsabilidades:
    1. Construir state inicial desde prompt_payload + input_state
    2. Invocar graph.run(state)
    3. Devolver output crudo del grafo
    
    NO normaliza, NO transforma, NO hace fallbacks automáticos.
    """
    
    def __init__(
        self,
        agent_type: AgentType,
        manifest: AgentManifest,
        config: CognitiveConfig,
        prompt_service,
        graph=None
    ):
        """
        Inicializa el agente cognitivo.
        
        Args:
            agent_type: Tipo de agente
            manifest: Manifest de capacidades
            config: Configuración cognitiva
            prompt_service: Servicio de prompts (requerido)
            graph: Implementación de LangGraph (StateGraph runner)
        """
        self.agent_type = agent_type
        self.manifest = manifest
        self.config = config
        self._prompt_service = prompt_service
        self._graph = graph
        
        if not self._prompt_service:
            raise ValueError("prompt_service is required")
        
        logger.info(
            f"[{agent_type.value}] CognitiveAgent initialized "
            f"(LangGraph mode - no legacy support)"
        )
    
    def set_graph(self, graph):
        """
        Inyectar implementación del grafo LangGraph.
        
        Args:
            graph: Objeto con método .run(state) -> Any
        """
        self._graph = graph
        logger.debug(f"[{self.agent_type.value}] Graph injected")
    
    # ========================================================================
    # CORE METHODS (Minimalista)
    # ========================================================================
    
    def _build_langgraph_state(
        self,
        company_id: int,
        agent_key: str,
        input_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Construir state para LangGraph.
        
        Obtiene prompt_payload desde PromptService y lo combina con input_state.
        NO transforma ni normaliza - pasa datos tal cual.
        
        Args:
            company_id: ID de la empresa
            agent_key: Key del agente
            input_state: Estado de entrada (chat_history, user_id, etc.)
        
        Returns:
            Dict con estructura:
            {
                'prompt_payload': {...},  # JSONB desde DB
                'input_state': {...}      # Datos crudos de entrada
            }
        
        Raises:
            RuntimeError: Si no encuentra prompt_payload (fail-fast)
        """
        # Obtener prompt payload
        payload = self._prompt_service.get_prompt_payload(company_id, agent_key)
        
        if payload is None:
            error_msg = (
                f"No prompt payload found for company_id={company_id}, "
                f"agent_key={agent_key}. Cannot proceed."
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        # Construir execution ID
        import uuid
        execution_id = f"{agent_key}_{uuid.uuid4().hex[:8]}"
        
        # Construir state para LangGraph
        lg_state: AgentState = {
            # Core data (sin transformaciones)
            "prompt_payload": payload,
            "input_state": input_state,
            
            # Metadata
            "agent_type": self.agent_type.value,
            "execution_id": execution_id,
            "company_id": company_id,
            "agent_key": agent_key,
            
            # Tracking
            "reasoning_steps": [],
            "tools_called": [],
            "tool_results": [],
            
            # Context
            "context": {
                "request_timestamp": datetime.utcnow().isoformat(),
                "prompt_version": payload.get('meta', {}).get('version'),
                "prompt_source": payload.get('meta', {}).get('source')
            },
            
            # Control
            "should_continue": True,
            "current_step": 0,
            
            # Timestamps
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None
        }
        
        logger.debug(
            f"[{self.agent_type.value}] Built LangGraph state: "
            f"execution_id={execution_id}, "
            f"prompt_version={lg_state['context'].get('prompt_version')}"
        )
        
        return lg_state
    
    def run_graph(
        self,
        company_id: int,
        agent_key: str,
        input_state: Dict[str, Any]
    ) -> Any:
        """
        Ejecutar grafo LangGraph.
        
        Construye el state, invoca graph.run(state) y devuelve el resultado
        EXACTO sin transformaciones ni envoltorios.
        
        Args:
            company_id: ID de la empresa
            agent_key: Key del agente
            input_state: Estado de entrada crudo
        
        Returns:
            Resultado exacto de graph.run(state)
        
        Raises:
            RuntimeError: Si no hay grafo configurado o si falla ejecución
        """
        if not self._graph:
            raise RuntimeError(
                f"[{self.agent_type.value}] No graph configured. "
                "Call set_graph() before run_graph()."
            )
        
        try:
            # 1. Construir state (puede lanzar RuntimeError si no hay prompt)
            lg_state = self._build_langgraph_state(company_id, agent_key, input_state)
            
            logger.info(
                f"[{self.agent_type.value}] Starting graph execution: "
                f"execution_id={lg_state['execution_id']}"
            )
            
            # 2. Ejecutar grafo (sync o async según implementación)
            result = self._graph.run(lg_state)
            
            logger.info(
                f"[{self.agent_type.value}] Graph execution completed: "
                f"execution_id={lg_state['execution_id']}"
            )
            
            # 3. Devolver resultado EXACTO (sin wrapping)
            return result
            
        except RuntimeError:
            # Re-raise RuntimeError con contexto adicional
            raise
        except Exception as e:
            error_msg = (
                f"[{self.agent_type.value}] Graph execution failed: "
                f"company_id={company_id}, agent_key={agent_key}, error={e}"
            )
            logger.error(error_msg, exc_info=True)
            
            if self.config.fail_fast:
                raise RuntimeError(error_msg) from e
            else:
                # Re-raise original exception
                raise
    
    # ========================================================================
    # ABSTRACT METHODS
    # ========================================================================
    
    @abstractmethod
    def invoke(self, inputs: Dict[str, Any]) -> Any:
        """
        Método público de invocación del agente.
        
        Las subclases implementan este método para mantener compatibilidad
        con la interfaz pública, pero internamente llaman a run_graph().
        
        Args:
            inputs: Dict con inputs de invocación
        
        Returns:
            Resultado de la ejecución del agente
        """
        pass


# ============================================================================
# NODE BUILDERS (Helpers para construir nodos LangGraph)
# ============================================================================

def create_reasoning_node(
    name: str,
    reasoning_fn
) -> callable:
    """
    Factory para crear nodos de razonamiento.
    
    Args:
        name: Nombre del nodo
        reasoning_fn: Función que realiza el razonamiento
    
    Returns:
        Función de nodo para LangGraph
    """
    def node(state: AgentState) -> AgentState:
        state["current_step"] = state.get("current_step", 0) + 1
        
        # Agregar reasoning step
        step: ReasoningStep = {
            "step_id": f"{name}_{state['current_step']}",
            "node_type": NodeType.REASONING.value,
            "description": f"Node: {name}",
            "thought": "",
            "action": None,
            "observation": None,
            "decision": None,
            "confidence": None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        state["reasoning_steps"].append(step)
        
        # Ejecutar lógica del nodo
        return reasoning_fn(state)
    
    return node


def create_tool_node(
    name: str,
    tool_executor,
    tool_selection_fn
) -> callable:
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
        state["current_step"] = state.get("current_step", 0) + 1
        tools_to_execute = tool_selection_fn(state)
        
        for tool_name in tools_to_execute:
            # Registrar llamada
            tool_call: ToolCall = {
                "tool_name": tool_name,
                "arguments": {},
                "timestamp": datetime.utcnow().isoformat(),
                "node_id": name
            }
            
            state["tools_called"].append(tool_call)
            
            # Aquí se ejecutaría la tool con tool_executor
            # La implementación real debe ser provista por el caller
        
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
    required_fields = ["prompt_payload", "input_state", "agent_key", "company_id"]
    
    for field in required_fields:
        if field not in state:
            logger.error(f"Missing required field in AgentState: {field}")
            return False
    
    return True


def get_execution_metrics(state: AgentState) -> Dict[str, Any]:
    """
    Extrae métricas de ejecución del estado.
    
    Args:
        state: Estado del agente
    
    Returns:
        Dict con métricas
    """
    started = datetime.fromisoformat(state["started_at"])
    completed = (
        datetime.fromisoformat(state["completed_at"]) 
        if state.get("completed_at") 
        else datetime.utcnow()
    )
    
    return {
        "execution_id": state["execution_id"],
        "agent_type": state["agent_type"],
        "agent_key": state["agent_key"],
        "company_id": state["company_id"],
        "latency_ms": (completed - started).total_seconds() * 1000,
        "reasoning_steps": len(state.get("reasoning_steps", [])),
        "tools_used": len(state.get("tools_called", [])),
        "tools_succeeded": sum(
            1 for r in state.get("tool_results", []) if r.get("success")
        ),
        "tools_failed": sum(
            1 for r in state.get("tool_results", []) if not r.get("success")
        )
    }


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    # Enums
    "AgentType",
    "NodeType",
    "ExecutionStatus",
    
    # TypedDicts
    "AgentState",
    "ToolCall",
    "ToolResult",
    "ReasoningStep",
    
    # Dataclasses
    "AgentManifest",
    "CognitiveConfig",
    
    # Classes
    "CognitiveAgentBase",
    
    # Node builders
    "create_reasoning_node",
    "create_tool_node",
    
    # Utils
    "validate_agent_state",
    "get_execution_metrics"
]
