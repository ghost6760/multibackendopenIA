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

# -------------------------
# Helper defensivo para inputs
# -------------------------
def get_inputs_from(obj) -> Dict[str, Any]:
    """
    Obtener 'inputs' de forma defensiva.
    - Si obj tiene atributo 'inputs' lo devuelve.
    - Si obj es dict devuelve obj.get('inputs', {})
    - Si obj es None devuelve {}
    - Si obj expone .get lo usa como fallback.
    Devuelve siempre un dict (vacío por defecto).
    """
    try:
        if obj is None:
            return {}
        # Si es un objeto con atributo 'inputs'
        if hasattr(obj, "inputs"):
            val = getattr(obj, "inputs")
            if isinstance(val, dict):
                return val
            # intentar convertir a dict si es tipo mapeable
            try:
                return dict(val) if val is not None else {}
            except Exception:
                return {}
        # Si es dict
        if isinstance(obj, dict):
            v = obj.get("inputs", {})
            return v if isinstance(v, dict) else {}
        # Si tiene .get (tipo mapping)
        if hasattr(obj, "get"):
            v = obj.get("inputs", None)
            return v if isinstance(v, dict) else {}
        return {}
    except Exception:
        return {}

def get_state_data(state) -> Dict[str, Any]:
    """
    Devuelve un dict mutable que representa el 'data' del state.
    - Si state es dict: se asegura state['data'] existe y es dict.
    - Si state es objeto con atributo .data: lo usa (crea si no existe).
    Devuelve siempre un dict.
    """
    try:
        if isinstance(state, dict):
            if "data" not in state or not isinstance(state["data"], dict):
                state["data"] = {}
            return state["data"]
        # objeto con atributo
        if not hasattr(state, "data") or not isinstance(getattr(state, "data"), dict):
            try:
                setattr(state, "data", {})
            except Exception:
                # fallback: devolver dict temporal (no persistirá en objeto si no puede setear)
                return {}
        return getattr(state, "data")
    except Exception:
        return {}

def set_state_field(state, key: str, value: Any) -> None:
    """
    Establece una clave de primer nivel en state de forma defensiva.
    Si state es dict => state[key] = value
    Si state es objeto => setattr(state, key, value) (safe)
    """
    try:
        if isinstance(state, dict):
            state[key] = value
        else:
            try:
                setattr(state, key, value)
            except Exception:
                # si no se puede, intentar usar data si es dict
                data = get_state_data(state)
                if isinstance(data, dict):
                    data[key] = value
    except Exception:
        # no crashear si no puede escribir
        logger.debug(f"[{getattr(state,'company_id', 'unknown')}] set_state_field failed for key {key}")

def get_state_field(state, key: str, default=None):
    """
    Leer campo de primer nivel del state de forma defensiva.
    """
    try:
        if isinstance(state, dict):
            return state.get(key, default)
        return getattr(state, key, default)
    except Exception:
        return default

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
    # DEPENDENCY INJECTION (Compatible con arquitectura existente)
    # ========================================================================
    
    def set_prompt_service(self, service):
        """Inyectar servicio de prompts."""
        self._prompt_service = service
        logger.debug(f"[{self.agent_type.value}] Prompt service injected")
    
    def set_vectorstore_service(self, service):
        """Inyectar servicio de vectorstore."""
        self._vectorstore_service = service
        logger.debug(f"[{self.agent_type.value}] Vectorstore service injected")
    
    def set_tool_executor(self, executor):
        """Inyectar ejecutor de tools."""
        self._tool_executor = executor
        logger.debug(f"[{self.agent_type.value}] Tool executor injected")
    
    def set_state_manager(self, manager):
        """Inyectar gestor de estado."""
        self._state_manager = manager
        logger.debug(f"[{self.agent_type.value}] State manager injected")
    
    def set_condition_evaluator(self, evaluator):
        """Inyectar evaluador de condiciones."""
        self._condition_evaluator = evaluator
        logger.debug(f"[{self.agent_type.value}] Condition evaluator injected")
    
    # ========================================================================
    # PROMPT NODE CONSTRUCTION (NUEVO - Reemplaza ChatPromptTemplate)
    # ========================================================================
    
    def _normalize_chat_history(
        self, 
        chat_history: List[Any]
    ) -> List[Dict[str, str]]:
        """
        Normalizar chat_history a formato estándar List[{"role", "content"}].
        
        Args:
            chat_history: Historial en cualquier formato
        
        Returns:
            Lista normalizada de mensajes con role y content
        """
        normalized = []
        
        if not chat_history:
            return []
        
        for msg in chat_history:
            if isinstance(msg, dict):
                # Ya está en formato dict
                if "role" in msg and "content" in msg:
                    normalized.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
                elif "type" in msg and "content" in msg:
                    # Formato alternativo con type
                    role = "user" if msg["type"] == "human" else "assistant"
                    normalized.append({
                        "role": role,
                        "content": msg["content"]
                    })
            elif hasattr(msg, "type") and hasattr(msg, "content"):
                # Objetos tipo LangChain Message
                role = "user" if msg.type == "human" else "assistant"
                normalized.append({
                    "role": role,
                    "content": msg.content
                })
            else:
                logger.warning(
                    f"[{self.agent_type.value}] Skipping unrecognized message format: {type(msg)}"
                )
        
        return normalized
    
    def _build_prompt_node(
        self,
        company_id: str,
        agent_key: str,
        state: AgentState
    ) -> Dict[str, Any]:
        """
        Construir nodo de prompt nativo desde prompt_service.
        
        Este método reemplaza completamente la construcción de ChatPromptTemplate
        y obtiene la estructura del prompt desde el servicio centralizado.
        
        Args:
            company_id: ID de la empresa
            agent_key: Key del agente (ej. 'sales_agent', 'router_agent')
            state: Estado actual del agente
        
        Returns:
            Dict con estructura de prompt: {
                'system': str,
                'examples': List[Dict],
                'placeholders': Dict,
                'meta': Dict
            }
        """
        if not self._prompt_service:
            logger.warning(
                f"[{self.agent_type.value}] No prompt service available, using fallback"
            )
            return {
                'system': f"Eres un asistente para {agent_key}.",
                'examples': [],
                'placeholders': {},
                'meta': {'source': 'fallback'}
            }
        
        try:
            # Obtener payload estructurado desde prompt_service
            prompt_payload = self._prompt_service.get_prompt_payload(
                company_id, 
                agent_key
            )
            
            if not prompt_payload:
                logger.warning(
                    f"[{self.agent_type.value}] No prompt payload found for "
                    f"{company_id}/{agent_key}, using fallback"
                )
                return {
                    'system': f"Eres un asistente para {agent_key}.",
                    'examples': [],
                    'placeholders': {},
                    'meta': {'source': 'fallback'}
                }
            
            logger.debug(
                f"[{self.agent_type.value}] Prompt payload loaded for {agent_key}: "
                f"system={len(prompt_payload.get('system', ''))} chars, "
                f"examples={len(prompt_payload.get('examples', []))}"
            )
            
            return prompt_payload
            
        except Exception as e:
            logger.error(
                f"[{self.agent_type.value}] Error building prompt node: {e}",
                exc_info=True
            )
            return {
                'system': f"Eres un asistente para {agent_key}.",
                'examples': [],
                'placeholders': {},
                'meta': {'source': 'error_fallback', 'error': str(e)}
            }

    def _run_graph_prompt(
            self,
            state: AgentState,
            prompt_node: Dict[str, Any],
            agent_key: str = None,
            **kwargs
        ) -> Dict[str, Any]:
        """
        Ejecutar StateGraph con prompt estructurado y fallback seguro.
        - Normaliza state si es dict.
        - Ejecuta self.graph.run(graph_inputs) si está disponible.
        - Devuelve diccionario: {'text','raw','metadata'}
        """
        try:
            logger.debug(f"[_run_graph_prompt] called with agent_key={agent_key}")
    
            # --- Normalizar state si vino como dict u objeto con 'inputs' ---
            if isinstance(state, dict):
                # extraer los campos principales y reconstruir AgentState parcial
                inputs_from_state = get_inputs_from(state)
                # conservar el state dict / pero asegurar keys usadas más abajo
                norm_state = state.copy()
                norm_state.setdefault("chat_history", inputs_from_state.get("chat_history", []))
                norm_state.setdefault("question", inputs_from_state.get("question", ""))
                norm_state.setdefault("context", inputs_from_state.get("context", {}))
                state = norm_state  # sustituimos localmente
                logger.debug(f"[_run_graph_prompt] normalized incoming state dict; question_len={len(state.get('question',''))}")
    
            # Normalizar chat_history
            normalized_history = self._normalize_chat_history(
                state.get("chat_history", [])
            )
    
            # Construir inputs para el grafo
            graph_inputs = {
                "system_prompt": (prompt_node or {}).get("system", ""),
                "examples": (prompt_node or {}).get("examples", []),
                "placeholders": (prompt_node or {}).get("placeholders", {}),
                "chat_history": normalized_history,
                "question": state.get("question", ""),
                "context": state.get("context", {}),
                "metadata": {
                    **state.get("metadata", {}),
                    "prompt_source": (prompt_node or {}).get("meta", {}).get("source", "unknown")
                }
            }
    
            # Log minimal para trazabilidad
            logger.info(
                f"[{self.agent_type.value}] Graph prompt ready for agent_key={agent_key} "
                f"history_len={len(normalized_history)} examples={len(graph_inputs['examples'])}"
            )
    
            # --- 1) Intentar ejecutar grafo (LangGraph) si existe ---
            graph_result = None
            if hasattr(self, "graph") and self.graph:
                # si el grafo expone run/compile/invoke
                try:
                    if hasattr(self.graph, "run"):
                        logger.debug(f"[_run_graph_prompt] Running self.graph.run() for agent {agent_key}")
                        graph_result = self.graph.run(graph_inputs)
                    elif hasattr(self.graph, "invoke"):
                        logger.debug(f"[_run_graph_prompt] Running self.graph.invoke() for agent {agent_key}")
                        graph_result = self.graph.invoke(graph_inputs)
                    elif hasattr(self.graph, "compile") and hasattr(self, "compiled_graph") and self.compiled_graph:
                        logger.debug(f"[_run_graph_prompt] Running compiled_graph.invoke() for agent {agent_key}")
                        graph_result = self.compiled_graph.invoke(graph_inputs)
                    else:
                        logger.debug(f"[_run_graph_prompt] No runnable method found on graph for agent {agent_key}.")
                except Exception as e:
                    logger.error(f"[{self.agent_type.value}] Error executing graph.run(): {e}", exc_info=True)
                    graph_result = None
            else:
                logger.debug(f"[_run_graph_prompt] No graph available on agent {self.agent_type}. Skipping graph.run().")
    
            # --- 2) Procesar resultado del grafo si hay ---
            final_text = ""
            raw_out = None
            metadata = {
                'prompt_length': len(graph_inputs['system_prompt']),
                'examples_count': len(graph_inputs['examples']),
                'history_messages': len(normalized_history),
                'execution_timestamp': datetime.utcnow().isoformat()
            }
    
            if graph_result:
                raw_out = graph_result
                # varios formatos posibles: dict con 'text', o objeto con .text, o dict['output']
                try:
                    if isinstance(graph_result, dict):
                        if graph_result.get("text"):
                            final_text = graph_result.get("text")
                        elif graph_result.get("output") and isinstance(graph_result.get("output"), str):
                            final_text = graph_result.get("output")
                        else:
                            # Tal vez el grafo devuelve state-like con 'response'
                            final_text = graph_result.get("response") or graph_result.get("result") or ""
                    elif hasattr(graph_result, "text"):
                        final_text = getattr(graph_result, "text")
                    else:
                        final_text = str(graph_result)
                except Exception as e:
                    logger.error(f"[_run_graph_prompt] Error extracting text from graph_result: {e}", exc_info=True)
                    final_text = ""
    
                logger.debug(f"[_run_graph_prompt] Graph executed; produced_text_len={len(final_text)}")
                metadata['from_graph'] = True
            else:
                # No graph result -> fallback (prompt_node puede ser None)
                logger.warning(f"[_run_graph_prompt] prompt_node is None or malformed for agent {agent_key}; using fallback.")
                raw_out = {"note": "no graph available", "inputs": graph_inputs}
                metadata['from_graph'] = False
    
            # --- 3) Retorno normalizado ---
            return {
                'text': final_text or "",
                'raw': raw_out,
                'metadata': metadata
            }
    
        except Exception as e:
            logger.error(
                f"[{self.agent_type.value}] Error running graph prompt: {e}",
                exc_info=True
            )
            return {
                'text': "Error ejecutando el prompt.",
                'raw': None,
                'metadata': {
                    'error': str(e),
                    'error_timestamp': datetime.utcnow().isoformat()
                }
            }

    # ========================================================================
    # ABSTRACT METHODS (Deben ser implementados por subclases)
    # ========================================================================
    
    @abstractmethod
    def build_graph(self):
        """
        Construir el grafo LangGraph del agente.
        
        Las subclases deben implementar este método para definir:
        - Nodos del grafo
        - Edges y condiciones
        - Flujo de ejecución
        
        Deben usar _build_prompt_node y _run_graph_prompt para manejar prompts.
        """
        pass
    
    @abstractmethod
    def invoke(self, inputs: dict) -> str:
        """
        Método público de invocación del agente (compatible con legacy).
        
        Args:
            inputs: Dict con:
                - question: str
                - chat_history: List
                - user_id: str
                - company_id: str (opcional)
        
        Returns:
            str: Respuesta del agente
        """
        pass
    
    # ========================================================================
    # STATE MANAGEMENT
    # ========================================================================
    
    def _initialize_state(
        self,
        question: str,
        chat_history: List,
        user_id: str,
        company_id: Optional[str] = None,
        **kwargs
    ) -> AgentState:
        """
        Inicializar estado del agente.
        
        Args:
            question: Pregunta del usuario
            chat_history: Historial de conversación
            user_id: ID del usuario
            company_id: ID de la empresa (opcional)
            **kwargs: Campos adicionales
        
        Returns:
            AgentState inicializado
        """
        import uuid
        
        execution_id = f"{self.agent_type.value}_{uuid.uuid4().hex[:8]}"
        
        state: AgentState = {
            # Inputs
            "question": question,
            "chat_history": chat_history or [],
            "user_id": user_id,
            "company_id": company_id,
            
            # Execution
            "agent_type": self.agent_type.value,
            "execution_id": execution_id,
            "status": ExecutionStatus.PENDING.value,
            "current_node": "init",
            
            # Reasoning
            "reasoning_steps": [],
            "tools_called": [],
            "tool_results": [],
            
            # Context
            "context": kwargs.get("context", {}),
            "intermediate_results": {},
            
            # Tools
            "tools_available": self.manifest.required_tools,
            
            # Decisions
            "decisions": [],
            "confidence_scores": {},
            
            # Agent-specific context
            "vectorstore_context": kwargs.get("vectorstore_context"),
            "calendar_context": kwargs.get("calendar_context"),
            
            # Output
            "response": None,
            
            # Metadata
            "metadata": kwargs.get("metadata", {}),
            "errors": [],
            "warnings": [],
            
            # Control
            "should_continue": True,
            "current_step": 0,
            "retry_count": 0,
            
            # Timestamps
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None
        }
        
        return state

    def _validate_inputs(self, inputs: dict):
        """
        Validar inputs mínimos requeridos.
        
        Args:
            inputs: Dict con inputs del usuario
        
        Raises:
            ValueError si faltan campos obligatorios
        """
        required_fields = ["question", "user_id"]
        
        for field in required_fields:
            if field not in inputs:
                logger.error(
                    f"[{self.agent_type.value}] Missing required field: {field}"
                )
                raise ValueError(f"Missing required field: {field}")
            
            if not inputs[field] or not str(inputs[field]).strip():
                logger.error(
                    f"[{self.agent_type.value}] Field '{field}' is empty"
                )
                raise ValueError(f"Field '{field}' cannot be empty")
        
        # Validar chat_history si existe
        if "chat_history" in inputs and inputs["chat_history"] is not None:
            if not isinstance(inputs["chat_history"], list):
                logger.error(
                    f"[{self.agent_type.value}] chat_history must be a list, got {type(inputs['chat_history'])}"
                )
                raise ValueError("chat_history must be a list")
        
        logger.debug(
            f"[{self.agent_type.value}] Inputs validated successfully"
        )
        
    def _should_continue_execution(self, state: AgentState) -> bool:
        """
        Determinar si el agente debe continuar ejecutándose.
        
        Args:
            state: Estado actual
        
        Returns:
            bool: True si debe continuar
        """
        # Verificar errores críticos
        if state.get("status") == ExecutionStatus.FAILED.value:
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

    def _validate_inputs(self, inputs: dict):
        """
        Validar inputs mínimos requeridos.
        
        Args:
            inputs: Dict con inputs del usuario
        
        Raises:
            ValueError si faltan campos obligatorios
        """
        required_fields = ["question", "user_id"]
        
        for field in required_fields:
            if field not in inputs:
                logger.error(
                    f"[{self.agent_type.value}] Missing required field: {field}"
                )
                raise ValueError(f"Missing required field: {field}")
            
            if not inputs[field] or not str(inputs[field]).strip():
                logger.error(
                    f"[{self.agent_type.value}] Field '{field}' is empty"
                )
                raise ValueError(f"Field '{field}' cannot be empty")
        
        # Validar chat_history si existe
        if "chat_history" in inputs and inputs["chat_history"] is not None:
            if not isinstance(inputs["chat_history"], list):
                logger.error(
                    f"[{self.agent_type.value}] chat_history must be a list, got {type(inputs['chat_history'])}"
                )
                raise ValueError("chat_history must be a list")
        
        logger.debug(
            f"[{self.agent_type.value}] Inputs validated successfully"
        )
    
    def _create_initial_state(self, inputs: dict) -> AgentState:
        """
        Crear estado inicial desde dict de inputs (método de conveniencia).
        
        Este método es un wrapper de _initialize_state que acepta un dict
        de inputs y extrae los campos necesarios.
        
        Args:
            inputs: Dict con al menos:
                - question: str
                - user_id: str
                - chat_history: List (opcional)
                - company_id: str (opcional)
                - Otros campos opcionales
        
        Returns:
            AgentState inicializado
        """
        # Extraer campos principales
        question = inputs.get("question", "")
        user_id = inputs.get("user_id", "")
        chat_history = inputs.get("chat_history", [])
        company_id = inputs.get("company_id")
        
        # Extraer campos adicionales
        extra_kwargs = {
            k: v for k, v in inputs.items() 
            if k not in ["question", "chat_history", "user_id", "company_id"]
        }
        
        # Llamar a _initialize_state
        return self._initialize_state(
            question=question,
            chat_history=chat_history,
            user_id=user_id,
            company_id=company_id,
            **extra_kwargs
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
        Crear un paso de razonamiento para agregar al estado.
        
        Este método helper facilita la creación de ReasoningStep con
        campos automáticos como step_id y timestamp.
        
        Args:
            state: Estado actual del agente
            node_type: Tipo de nodo (REASONING, TOOL_EXECUTION, etc.)
            description: Descripción del paso
            thought: Pensamiento/razonamiento
            action: Acción tomada (opcional)
            observation: Observación/resultado (opcional)
            decision: Decisión tomada (opcional)
            confidence: Score de confianza (opcional)
        
        Returns:
            ReasoningStep completo
        """
        import uuid
        
        step_id = f"{state.get('execution_id', 'unknown')}_{uuid.uuid4().hex[:8]}"
        
        reasoning_step: ReasoningStep = {
            "step_id": step_id,
            "node_type": node_type.value if isinstance(node_type, NodeType) else str(node_type),
            "description": description,
            "thought": thought,
            "action": action,
            "observation": observation,
            "decision": decision,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.debug(
            f"[{self.agent_type.value}] Created reasoning step: {description}"
        )
        
        return reasoning_step
    
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
    "get_execution_metrics",
    "get_state_data",
    "set_state_field",
    "get_state_field"
]
