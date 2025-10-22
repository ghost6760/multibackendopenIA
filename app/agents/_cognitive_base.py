"""
Base cognitiva REFACTORIZADA para agentes LangGraph.

CAMBIOS PRINCIPALES:
- ✅ Integra sistema de prompts PostgreSQL de BaseAgent
- ✅ Soporte para historial de chat con MessagesPlaceholder
- ✅ CompanyConfig para personalización por empresa
- ✅ OpenAI Service integrado
- ✅ Mantiene arquitectura LangGraph cognitiva
- ✅ Compatible con orchestrator

Este módulo define la infraestructura común que todos los agentes cognitivos
deben implementar, incluyendo tipos de estado, interfaces de nodos, contratos
de ejecución Y gestión de prompts/historial.
"""

from typing import TypedDict, Annotated, Sequence, Any, Dict, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from abc import ABC, abstractmethod
import operator
import logging
import uuid

# Imports de LangChain para prompts con historial
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import BaseMessage
from langchain.schema.output_parser import StrOutputParser

# Imports de servicios
from app.config.company_config import CompanyConfig
from app.services.openai_service import OpenAIService
from app.services.prompt_service import get_prompt_service

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
    - ✅ NUEVO: Historial de chat persistente
    """
    # Inputs originales (obligatorios)
    question: str
    chat_history: List[Dict[str, str]]  # ← Historial de conversación
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
    context: Dict[str, Any]  # ✅ Incluye company_name, services, etc.
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
# CLASE BASE REFACTORIZADA
# ============================================================================

class CognitiveAgentBase(ABC):
    """
    Clase base abstracta REFACTORIZADA para agentes cognitivos.
    
    NUEVAS CAPACIDADES:
    - ✅ Sistema de prompts PostgreSQL con fallbacks
    - ✅ Soporte para historial de chat (MessagesPlaceholder)
    - ✅ CompanyConfig para personalización
    - ✅ OpenAI Service integrado
    - ✅ Mantiene arquitectura LangGraph
    
    IMPORTANTE: Las subclases DEBEN:
    1. Mantener el mismo nombre de clase que sus versiones anteriores
    2. Implementar _create_graph() para construir grafo LangGraph
    3. Implementar _create_default_prompt_template() con MessagesPlaceholder
    4. Usar self.prompt_template en nodos de razonamiento
    """
    
    def __init__(
        self,
        company_config: CompanyConfig,      # ← NUEVO
        openai_service: OpenAIService,      # ← NUEVO
        agent_type: AgentType,
        manifest: AgentManifest,
        config: CognitiveConfig
    ):
        """
        Inicializa el agente cognitivo REFACTORIZADO.
        
        Args:
            company_config: Configuración de la empresa
            openai_service: Servicio de OpenAI
            agent_type: Tipo de agente
            manifest: Manifest de capacidades
            config: Configuración cognitiva
        """
        # ✅ NUEVO: Configuración de empresa
        self.company_config = company_config
        self.openai_service = openai_service
        self.chat_model = openai_service.get_chat_model()
        self.agent_name = self.__class__.__name__
        
        # Configuración cognitiva
        self.agent_type = agent_type
        self.manifest = manifest
        self.config = config
        
        # ✅ NUEVO: Sistema de prompts PostgreSQL (migrado de BaseAgent)
        self.prompt_service = get_prompt_service()
        self._current_prompt_template = None
        self._prompt_source = None
        
        # Servicios inyectados (inicialmente None)
        self._tool_executor = None
        self._vectorstore_service = None
        self._state_manager = None
        self._condition_evaluator = None
        
        logger.info(
            f"[{company_config.company_id}] 🏗️ Initializing {self.agent_name} "
            f"(type: {agent_type.value}) with PostgreSQL prompts + LangGraph"
        )
        
        # ✅ NUEVO: Cargar prompt desde PostgreSQL (DESPUÉS de tener company_config)
        self.prompt_template = self._create_prompt_template()
        
        # Estadísticas
        self._stats = {
            "invocations": 0,
            "errors": 0,
            "avg_latency_ms": 0
        }
    
    # ========================================================================
    # SISTEMA DE PROMPTS POSTGRESQL (Migrado de BaseAgent)
    # ========================================================================
    
    def _create_prompt_template(self) -> ChatPromptTemplate:
        """
        Crear template con soporte para prompts personalizados desde PostgreSQL.
        
        JERARQUÍA DE CARGA (igual que BaseAgent):
        1. PostgreSQL custom_prompts (Personalizado por empresa)
        2. PostgreSQL default_prompts (Por defecto del repositorio)
        3. Fallback a JSON (compatibilidad temporal)
        4. Método _create_default_prompt_template() (Hardcoded en agente)
        5. Fallback de emergencia (Prompt básico)
        
        ✅ NUEVO: TODOS los prompts incluyen MessagesPlaceholder para historial
        """
        company_id = self.company_config.company_id
        agent_key = self._get_agent_key()
        
        logger.info(f"🔄 [{company_id}] Creating prompt template for {self.agent_name} (key: {agent_key})")
        
        # 1. Intentar cargar prompt personalizado desde PostgreSQL
        logger.info(f"🔍 [{company_id}] Step 1: Checking PostgreSQL custom prompts...")
        custom_template = self._load_custom_prompt_from_postgresql()
        if custom_template:
            self._prompt_source = "postgresql_custom"
            logger.info(f"✅ [{company_id}] SUCCESS: Using PostgreSQL custom prompt for {agent_key}")
            return self._build_prompt_with_history(custom_template)
        
        # 2. Intentar cargar prompt por defecto desde PostgreSQL
        logger.info(f"🔍 [{company_id}] Step 2: Checking PostgreSQL default prompts...")
        default_template = self._load_default_prompt_from_postgresql()
        if default_template:
            self._prompt_source = "postgresql_default"
            logger.info(f"✅ [{company_id}] SUCCESS: Using PostgreSQL default prompt for {agent_key}")
            return self._build_prompt_with_history(default_template)
        
        # 3. Fallback a método del agente específico
        try:
            self._prompt_source = "hardcoded_agent"
            logger.warning(f"⚠️ [{company_id}] FALLING BACK TO HARDCODED for {agent_key}")
            return self._create_default_prompt_template()
        except Exception as e:
            logger.error(f"💥 [{company_id}] Error creating default prompt template: {e}")
        
        # 4. Fallback de emergencia
        self._prompt_source = "emergency_fallback"
        logger.error(f"🚨 [{company_id}] EMERGENCY FALLBACK for {agent_key}")
        return self._create_emergency_prompt_template()
    
    def _load_custom_prompt_from_postgresql(self) -> Optional[str]:
        """
        Cargar prompt personalizado desde PostgreSQL.
        
        Returns:
            Template string si se encuentra custom prompt, None si no
        """
        try:
            company_id = self.company_config.company_id
            agent_key = self._get_agent_key()
            
            logger.info(f"🔍 [{company_id}] Loading CUSTOM prompt for agent_key: {agent_key}")
            
            if not self.prompt_service:
                logger.error(f"❌ [{company_id}] prompt_service is None!")
                return None
            
            # Usar el servicio de prompts con fallback automático
            agents_data = self.prompt_service.get_company_prompts(company_id)
            agent_data = agents_data.get(agent_key, {})
            
            # Solo retornar si es personalizado y viene de PostgreSQL
            is_custom = agent_data.get('is_custom', False)
            source = agent_data.get('source', 'unknown')
            has_prompt = bool(agent_data.get('current_prompt'))
            
            logger.info(f"🔍 [{company_id}] Evaluation: is_custom={is_custom}, source={source}, has_prompt={has_prompt}")
            
            if (is_custom and 
                source in ['custom', 'postgresql_custom'] and
                has_prompt):
                logger.info(f"✅ [{company_id}] Found custom prompt (length: {len(agent_data['current_prompt'])})")
                return agent_data['current_prompt']
            
            logger.info(f"ℹ️ [{company_id}] No custom prompt found")
            return None
            
        except Exception as e:
            logger.error(f"💥 [{company_id}] Error loading custom prompt: {e}", exc_info=True)
            return None
    
    def _load_default_prompt_from_postgresql(self) -> Optional[str]:
        """
        Cargar prompt por defecto desde PostgreSQL.
        
        Returns:
            Template string si se encuentra default prompt, None si no
        """
        try:
            company_id = self.company_config.company_id
            agent_key = self._get_agent_key()
            
            logger.info(f"🔍 [{company_id}] Loading DEFAULT prompt for agent_key: {agent_key}")
            
            if not self.prompt_service:
                logger.error(f"❌ [{company_id}] prompt_service is None!")
                return None
            
            agents_data = self.prompt_service.get_company_prompts(company_id)
            agent_data = agents_data.get(agent_key, {})
            
            source = agent_data.get('source', 'unknown')
            has_prompt = bool(agent_data.get('current_prompt'))
            
            logger.info(f"🔍 [{company_id}] Evaluation: source={source}, has_prompt={has_prompt}")
            
            if (source in ['default', 'postgresql_default'] and has_prompt):
                logger.info(f"✅ [{company_id}] Found default prompt (length: {len(agent_data['current_prompt'])})")
                return agent_data['current_prompt']
            
            logger.info(f"ℹ️ [{company_id}] No default prompt found")
            return None
            
        except Exception as e:
            logger.error(f"💥 [{company_id}] Error loading default prompt: {e}", exc_info=True)
            return None
    
    def _build_prompt_with_history(self, template: str) -> ChatPromptTemplate:
        """
        ✅ NUEVO: Construir prompt que SIEMPRE incluye MessagesPlaceholder.
        
        Esta es la función CLAVE que asegura que el historial se pase al LLM.
        
        Args:
            template: Template string del prompt
        
        Returns:
            ChatPromptTemplate con system + MessagesPlaceholder + human
        """
        # Verificar si el template ya tiene contexto de empresa
        if "{company_name}" in template or "{services}" in template:
            # Ya tiene contexto, solo añadir historial
            return ChatPromptTemplate.from_messages([
                ("system", template),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{question}")
            ])
        else:
            # Añadir contexto de empresa Y historial
            enhanced = f"""{template}

CONTEXTO DE LA EMPRESA:
- Empresa: {{company_name}}
- Servicios: {{services}}

Responde considerando el historial de conversación."""
            
            return ChatPromptTemplate.from_messages([
                ("system", enhanced),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{question}")
            ])
    
    def _get_agent_key(self) -> str:
        """
        Obtener clave del agente para PostgreSQL.
        
        Returns:
            String con formato "support_agent", "schedule_agent", etc.
        """
        class_name = self.__class__.__name__
        if class_name.endswith('Agent'):
            agent_name = class_name[:-5]
        else:
            agent_name = class_name
        
        import re
        agent_key = re.sub('([a-z0-9])([A-Z])', r'\1_\2', agent_name).lower() + '_agent'
        return agent_key
    
    def _create_emergency_prompt_template(self) -> ChatPromptTemplate:
        """
        Prompt de emergencia cuando todo lo demás falla.
        
        Returns:
            ChatPromptTemplate básico
        """
        return ChatPromptTemplate.from_messages([
            ("system", f"""Eres un asistente de {self.company_config.company_name}.

Servicios disponibles: {{services}}

Responde de manera profesional considerando el historial."""),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{question}")
        ])
    
    @abstractmethod
    def _create_default_prompt_template(self) -> ChatPromptTemplate:
        """
        Template por defecto (hardcoded) - DEBE incluir MessagesPlaceholder.
        
        Cada agente debe implementar este método para definir su prompt
        hardcodeado que se usa como último fallback.
        
        IMPORTANTE: SIEMPRE debe incluir:
        1. ("system", "...contexto...")
        2. MessagesPlaceholder(variable_name="chat_history", optional=True)
        3. ("human", "{question}")
        
        Returns:
            ChatPromptTemplate con historial incluido
        """
        pass
    
    # ========================================================================
    # MÉTODOS DE COMPATIBILIDAD CON ORCHESTRATOR
    # ========================================================================
    
    def invoke(self, inputs: Dict[str, Any]) -> str:
        """
        ✅ IMPLEMENTACIÓN BASE: Método de entrada estándar.
        
        Este método:
        1. Extrae inputs (question, chat_history, context)
        2. Prepara state inicial con historial
        3. Ejecuta grafo LangGraph
        4. Retorna respuesta final
        
        Args:
            inputs: Dict con question, chat_history, context, etc.
        
        Returns:
            str: Respuesta del agente
        """
        try:
            # Extraer inputs
            question = inputs.get("question", "")
            chat_history = inputs.get("chat_history", [])
            context = inputs.get("context", "")
            user_id = inputs.get("user_id", "unknown")
            
            if not question:
                return f"No se proporcionó una pregunta válida para {self.company_config.company_name}."
            
            logger.info(f"🤖 [{self.company_config.company_id}] {self.agent_name}.invoke() called")
            logger.info(f"🤖 [{self.company_config.company_id}] Question: {question[:100]}...")
            logger.info(f"🤖 [{self.company_config.company_id}] Using prompt source: {self._prompt_source}")
            logger.info(f"🤖 [{self.company_config.company_id}] Chat history length: {len(chat_history)}")
            
            # ✅ Preparar state inicial con historial
            state = self._prepare_initial_state(
                question=question,
                chat_history=chat_history,
                context=context,
                user_id=user_id,
                company_id=self.company_config.company_id
            )
            
            # ✅ Ejecutar grafo LangGraph
            logger.info(f"🚀 [{self.company_config.company_id}] Executing LangGraph...")
            final_state = self.graph.invoke(state)
            
            # ✅ Construir respuesta
            response = self._build_response_from_state(final_state)
            
            # Telemetría
            self._stats["invocations"] += 1
            logger.info(f"✅ [{self.company_config.company_id}] Response generated (length: {len(response)})")
            
            return response
            
        except Exception as e:
            logger.exception(f"💥 [{self.company_config.company_id}] Error in invoke: {e}")
            self._stats["errors"] += 1
            return f"Lo siento, estoy experimentando dificultades técnicas. Por favor, contacta con {self.company_config.company_name} directamente."
    
    def _prepare_initial_state(
        self,
        question: str,
        chat_history: List,
        context: str,
        user_id: str,
        company_id: str
    ) -> AgentState:
        """
        ✅ NUEVO: Crear estado inicial incluyendo historial de chat.
        
        Este método asegura que el historial se incluye en el state
        y está disponible para todos los nodos del grafo.
        
        Args:
            question: Pregunta del usuario
            chat_history: Historial de mensajes previos
            context: Contexto adicional
            user_id: ID del usuario
            company_id: ID de la empresa
        
        Returns:
            AgentState inicializado con todos los campos necesarios
        """
        return {
            # Inputs
            "question": question,
            "chat_history": self._convert_chat_history(chat_history),
            "user_id": user_id,
            "company_id": company_id,
            
            # Context de empresa (para personalización)
            "context": {
                "company_name": self.company_config.company_name,
                "services": self.company_config.services,
                "additional_context": context
            },
            "intermediate_results": {},
            
            # Estado de ejecución
            "agent_type": self.agent_type.value,
            "execution_id": str(uuid.uuid4()),
            "status": ExecutionStatus.PENDING.value,
            "current_node": "start",
            
            # Inicializar listas (con annotated operator.add)
            "reasoning_steps": [],
            "tools_called": [],
            "tool_results": [],
            "decisions": [],
            "errors": [],
            "warnings": [],
            
            # Tools disponibles
            "tools_available": self.manifest.required_tools + self.manifest.optional_tools,
            
            # Scores y metadata
            "confidence_scores": {},
            "metadata": {
                "prompt_source": self._prompt_source,
                "agent_version": "cognitive_v2"
            },
            
            # Contexto específico (None inicialmente)
            "vectorstore_context": None,
            "calendar_context": None,
            
            # Output
            "response": None,
            
            # Control de flujo
            "should_continue": True,
            "current_step": 0,
            "retry_count": 0,
            
            # Timestamps
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None
        }
    
    def _convert_chat_history(self, chat_history: List) -> List[Dict[str, str]]:
        """
        Convertir historial de chat a formato estándar.
        
        Soporta:
        - Lista de BaseMessage (LangChain)
        - Lista de dicts {"role": "...", "content": "..."}
        - Lista vacía
        
        Args:
            chat_history: Historial en cualquier formato
        
        Returns:
            Lista de dicts con formato estándar
        """
        if not chat_history:
            return []
        
        converted = []
        for msg in chat_history:
            if isinstance(msg, BaseMessage):
                # LangChain BaseMessage
                converted.append({
                    "role": msg.type,
                    "content": msg.content
                })
            elif isinstance(msg, dict):
                # Ya es dict
                converted.append(msg)
            else:
                logger.warning(f"Unknown message type in chat_history: {type(msg)}")
        
        return converted
    
    # ========================================================================
    # GESTIÓN DE SERVICIOS (Migrado de versión anterior)
    # ========================================================================
    
    def set_tool_executor(self, tool_executor):
        """Inyectar executor de herramientas"""
        self._tool_executor = tool_executor
        logger.info(f"[{self.company_config.company_id}] Tool executor configured")
    
    def set_vectorstore_service(self, vectorstore_service):
        """Inyectar servicio de vectorstore"""
        self._vectorstore_service = vectorstore_service
        logger.info(f"[{self.company_config.company_id}] Vectorstore service configured")
    
    def set_state_manager(self, state_manager):
        """Inyectar state manager"""
        self._state_manager = state_manager
        logger.info(f"[{self.company_config.company_id}] State manager configured")
    
    def set_condition_evaluator(self, condition_evaluator):
        """Inyectar condition evaluator"""
        self._condition_evaluator = condition_evaluator
        logger.info(f"[{self.company_config.company_id}] Condition evaluator configured")
    
    # ========================================================================
    # MÉTODOS ABSTRACTOS (Subclases deben implementar)
    # ========================================================================
    
    @abstractmethod
    def _create_graph(self):
        """
        Crear grafo LangGraph específico del agente.
        
        Este método debe:
        1. Definir nodos (reasoning, tool_execution, etc.)
        2. Definir edges y conditions
        3. Retornar CompiledGraph
        """
        pass
    
    # ========================================================================
    # UTILIDADES PARA NODOS (Helpers para subclases)
    # ========================================================================
    
    def _should_continue(self, state: AgentState) -> bool:
        """
        Determinar si el grafo debe continuar ejecutándose.
        
        Args:
            state: Estado actual
        
        Returns:
            bool: True si debe continuar, False si debe terminar
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
    
    def _build_response_from_state(self, state: AgentState) -> str:
        """
        Construir respuesta final desde el estado.
        
        Args:
            state: Estado final del grafo
        
        Returns:
            str: Respuesta formateada
        """
        if state.get("response"):
            return state["response"]
        
        # Safe-fail: generar respuesta de degradación
        return self._generate_degraded_response(state)
    
    def _generate_degraded_response(self, state: AgentState) -> str:
        """
        Generar respuesta de degradación cuando algo falla.
        
        Args:
            state: Estado actual
        
        Returns:
            str: Respuesta de safe-fail
        """
        errors = state.get("errors", [])
        if errors:
            logger.error(f"[{self.agent_type.value}] Errors during execution: {errors}")
        
        return (
            f"Lo siento, no pude procesar completamente tu solicitud en este momento. "
            f"Por favor, contacta con {self.company_config.company_name} directamente o "
            f"intenta reformular tu pregunta."
        )
    
    def _get_telemetry(self, state: AgentState) -> Dict[str, Any]:
        """
        Obtener telemetría de la ejecución.
        
        Args:
            state: Estado final
        
        Returns:
            Dict con métricas de ejecución
        """
        return {
            "agent_name": self.agent_name,
            "agent_type": self.agent_type.value,
            "company_id": self.company_config.company_id,
            "execution_id": state.get("execution_id"),
            "user_id": state.get("user_id"),
            "reasoning_steps": len(state.get("reasoning_steps", [])),
            "tools_used": [t["tool_name"] for t in state.get("tool_results", [])],
            "total_latency_ms": sum(
                t.get("latency_ms", 0) for t in state.get("tool_results", [])
            ),
            "errors_count": len(state.get("errors", [])),
            "warnings_count": len(state.get("warnings", [])),
            "success": len(state.get("errors", [])) == 0,
            "prompt_source": self._prompt_source,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_agent_capabilities(self) -> Dict[str, Any]:
        """
        ✅ NUEVO: Obtener capacidades del agente.
        
        Returns:
            Dict con información de capacidades
        """
        return {
            "agent_name": self.agent_name,
            "agent_key": self._get_agent_key(),
            "agent_type": self.agent_type.value,
            "company_id": self.company_config.company_id,
            "prompt_source": self._prompt_source,
            "supports_custom_prompts": True,
            "supports_context": True,
            "supports_history": True,
            "supports_langgraph": True,
            "model_name": getattr(self.chat_model, 'model_name', 'unknown'),
            "required_tools": self.manifest.required_tools,
            "optional_tools": self.manifest.optional_tools,
            "capabilities": [c.name for c in self.manifest.capabilities],
            "stats": self._stats
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
        bool: True si es válido
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
        AgentState mergeado
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
    Extraer métricas de ejecución del estado.
    
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
