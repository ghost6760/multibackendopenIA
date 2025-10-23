# app/agents/availability_agent.py
# 🧠 VERSIÓN COGNITIVA con LangGraph - Fase 2 Migración

"""
AvailabilityAgent - Versión Cognitiva (LangGraph)

CAMBIOS PRINCIPALES:
- Hereda de CognitiveAgentBase
- Usa LangGraph para decisiones
- Puede delegar a ScheduleAgent o trabajar independientemente
- Mantiene MISMA firma pública: invoke(inputs: dict) -> str

MANTIENE COMPATIBILIDAD:
- Mismo nombre de clase: AvailabilityAgent
- Misma firma pública
- Misma integración con ScheduleAgent
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

# Imports de base cognitiva
from app.agents._cognitive_base import (
    CognitiveAgentBase,
    AgentType,
    AgentState,
    AgentManifest,
    AgentCapabilityDef,
    CognitiveConfig,
    NodeType,
    ExecutionStatus
)

from app.agents._agent_tools import get_tools_for_agent

# LangGraph
from langgraph.graph import StateGraph, END

# Services
from app.config.company_config import CompanyConfig
from app.services.openai_service import OpenAIService

logger = logging.getLogger(__name__)


# ============================================================================
# MANIFEST DE CAPACIDADES
# ============================================================================

AVAILABILITY_AGENT_MANIFEST = AgentManifest(
    agent_type="availability",
    display_name="Availability Agent",
    description="Agente cognitivo para consultas rápidas de disponibilidad",
    capabilities=[
        AgentCapabilityDef(
            name="check_availability",
            description="Verificar disponibilidad de horarios",
            tools_required=["get_available_slots", "check_availability"],
            priority=1
        ),
        AgentCapabilityDef(
            name="delegate_to_schedule",
            description="Delegar consultas complejas a ScheduleAgent",
            tools_required=[],
            priority=0
        )
    ],
    required_tools=[
        "get_available_slots",
        "check_availability"
    ],
    optional_tools=[
        "get_calendar_events",
        "get_business_hours"
    ],
    tags=["availability", "calendar", "delegation"],
    priority=0,
    max_retries=2,
    timeout_seconds=30,
    metadata={
        "version": "2.0-cognitive",
        "can_delegate": True
    }
)


# ============================================================================
# AVAILABILITY AGENT COGNITIVO
# ============================================================================

class AvailabilityAgent(CognitiveAgentBase):
    """
    Agente de disponibilidad con base cognitiva.
    
    Maneja consultas simples de disponibilidad y delega casos complejos
    al ScheduleAgent cuando es necesario.
    """
    
    def __init__(self, company_config: CompanyConfig, openai_service: OpenAIService):
        """
        Args:
            company_config: Configuración de la empresa
            openai_service: Servicio de OpenAI
        """
        self.company_config = company_config
        self.openai_service = openai_service
        self.chat_model = openai_service.get_chat_model()
        
        # Referencia a ScheduleAgent (se inyecta externamente)
        self.schedule_agent = None
        
        # Configuración cognitiva (más simple que ScheduleAgent)
        cognitive_config = CognitiveConfig(
            enable_reasoning_traces=True,
            enable_tool_validation=False,  # No crítico
            enable_guardrails=False,
            max_reasoning_steps=5,  # Menos pasos
            require_confirmation_for_critical_actions=False,
            safe_fail_on_tool_error=True,
            persist_state=False  # No persistir para queries simples
        )
        
        # Inicializar base cognitiva
        super().__init__(
            agent_type=AgentType.AVAILABILITY,
            manifest=AVAILABILITY_AGENT_MANIFEST,
            config=cognitive_config
        )
        
        # Grafo de LangGraph
        self.graph = None
        self.compiled_graph = None
        
        logger.info(
            f"🧠 [{company_config.company_id}] AvailabilityAgent initialized (cognitive mode)"
        )
    
    # ========================================================================
    # INTERFAZ PÚBLICA (MANTENER COMPATIBILIDAD)
    # ========================================================================
    
    def invoke(self, inputs: dict) -> str:
        """
        Punto de entrada principal (mantener firma).
        
        Args:
            inputs: Dict con keys: question, chat_history, user_id
        
        Returns:
            str: Respuesta generada
        """
        try:
            # Validar inputs
            self._validate_inputs(inputs)
            
            # Construir grafo si no existe
            if not self.compiled_graph:
                self.graph = self.build_graph()
                self.compiled_graph = self.graph.compile()
            
            # Crear estado inicial
            initial_state = self._create_initial_state(inputs)
            
            # Log inicio
            logger.info(
                f"🔍 [{self.company_config.company_id}] AvailabilityAgent.invoke() "
                f"- Question: {inputs.get('question', '')[:100]}..."
            )
            
            # Ejecutar grafo
            final_state = self.compiled_graph.invoke(initial_state)
            
            # Extraer respuesta
            response = self._build_response_from_state(final_state)
            
            # Log telemetría
            telemetry = self._get_telemetry(final_state)
            logger.info(
                f"✅ [{self.company_config.company_id}] AvailabilityAgent completed "
                f"- Steps: {telemetry['reasoning_steps']}"
            )
            
            return response
            
        except Exception as e:
            logger.exception(
                f"💥 [{self.company_config.company_id}] Error in AvailabilityAgent.invoke()"
            )
            return self._generate_error_response(str(e))
    
    def set_schedule_agent(self, schedule_agent):
        """Inyectar ScheduleAgent para delegación (mantener firma)"""
        self.schedule_agent = schedule_agent
        logger.debug(
            f"[{self.company_config.company_id}] ScheduleAgent injected to AvailabilityAgent"
        )
    
    # ========================================================================
    # CONSTRUCCIÓN DEL GRAFO LANGGRAPH
    # ========================================================================
    
    def build_graph(self) -> StateGraph:
        """
        Construir grafo de decisión simple.
        
        FLUJO:
        1. Analyze Query → Determinar complejidad
        2. Decide Strategy → Delegar o manejar directamente
        3. Execute → Ejecutar estrategia seleccionada
        
        Returns:
            StateGraph de LangGraph
        """
        # Crear grafo
        workflow = StateGraph(AgentState)
        
        # Añadir nodos
        workflow.add_node("analyze_query", self._analyze_query_node)
        workflow.add_node("handle_simple", self._handle_simple_node)
        workflow.add_node("delegate_complex", self._delegate_complex_node)
        
        # Definir edges
        workflow.set_entry_point("analyze_query")
        
        # Condicional: simple o complejo
        workflow.add_conditional_edges(
            "analyze_query",
            self._decide_strategy,
            {
                "simple": "handle_simple",
                "complex": "delegate_complex"
            }
        )
        
        workflow.add_edge("handle_simple", END)
        workflow.add_edge("delegate_complex", END)
        
        logger.info(
            f"[{self.company_config.company_id}] LangGraph built for AvailabilityAgent"
        )
        
        return workflow
    
    # ========================================================================
    # NODOS DEL GRAFO
    # ========================================================================
    
    def _analyze_query_node(self, state: AgentState) -> AgentState:
        """
        Nodo 1: Analizar query y determinar complejidad.
        """
        state["current_node"] = "analyze_query"
        
        question = state["question"].lower()
        
        # Determinar complejidad
        complexity = self._assess_query_complexity(question, state["chat_history"])
        
        # Registrar razonamiento
        reasoning_step = self._add_reasoning_step(
            state,
            NodeType.REASONING,
            "Analyzing query complexity",
            thought=f"User asks: '{question[:100]}'",
            decision=f"Complexity: {complexity}",
            confidence=0.8
        )
        
        state["reasoning_steps"].append(reasoning_step)
        state["context"]["complexity"] = complexity
        
        logger.debug(
            f"[{self.company_config.company_id}] Query complexity: {complexity}"
        )
        
        return state
    
    def _handle_simple_node(self, state: AgentState) -> AgentState:
        """
        Nodo 2a: Manejar consulta simple directamente.
        """
        state["current_node"] = "handle_simple"
        
        question = state["question"]
        
        # Generar respuesta simple
        response = self._generate_simple_availability_response(question)
        
        state["response"] = response
        state["status"] = ExecutionStatus.SUCCESS.value
        state["completed_at"] = datetime.utcnow().isoformat()
        
        # Registrar razonamiento
        reasoning_step = self._add_reasoning_step(
            state,
            NodeType.RESPONSE_GENERATION,
            "Generated simple availability response",
            observation=f"Response length: {len(response)} chars"
        )
        
        state["reasoning_steps"].append(reasoning_step)
        
        logger.debug(
            f"[{self.company_config.company_id}] Simple response generated"
        )
        
        return state
    
    def _delegate_complex_node(self, state: AgentState) -> AgentState:
        """
        Nodo 2b: Delegar a ScheduleAgent para casos complejos.
        """
        state["current_node"] = "delegate_complex"
        
        # Registrar razonamiento
        reasoning_step = self._add_reasoning_step(
            state,
            NodeType.DECISION,
            "Delegating to ScheduleAgent",
            thought="Query too complex for availability agent",
            decision="Delegate to ScheduleAgent"
        )
        
        state["reasoning_steps"].append(reasoning_step)
        
        # Delegar
        if self.schedule_agent:
            try:
                # Construir contexto para ScheduleAgent
                schedule_context = {
                    "company_id": self.company_config.company_id,
                    "company_name": self.company_config.company_name,
                    "services": self.company_config.services,
                    "question": state["question"],
                    "chat_history": state["chat_history"]
                }
                
                # Invocar ScheduleAgent
                response = self.schedule_agent.check_availability(
                    state["question"],
                    state["chat_history"],
                    schedule_context
                )
                
                state["response"] = response
                state["status"] = ExecutionStatus.SUCCESS.value
                
                logger.info(
                    f"[{self.company_config.company_id}] Successfully delegated to ScheduleAgent"
                )
                
            except Exception as e:
                logger.error(f"Error delegating to ScheduleAgent: {e}")
                state["response"] = self._generate_delegation_error_response()
                state["errors"].append(f"Delegation error: {str(e)}")
        
        else:
            # No hay ScheduleAgent, generar respuesta básica
            logger.warning("ScheduleAgent not available for delegation")
            state["response"] = self._generate_simple_availability_response(
                state["question"]
            )
            state["warnings"].append("ScheduleAgent not configured")
        
        state["completed_at"] = datetime.utcnow().isoformat()
        return state
    
    # ========================================================================
    # DECISIONES CONDICIONALES
    # ========================================================================
    
    def _decide_strategy(self, state: AgentState) -> str:
        """
        Determinar estrategia: simple o delegar.
        
        Returns:
            "simple" o "complex"
        """
        complexity = state["context"].get("complexity", "simple")
        
        if complexity == "complex":
            return "complex"
        else:
            return "simple"
    
    # ========================================================================
    # HELPERS DE ANÁLISIS
    # ========================================================================
    
    def _assess_query_complexity(
        self,
        question: str,
        chat_history: List
    ) -> str:
        """
        Evaluar complejidad de la query.
        
        Returns:
            "simple" o "complex"
        """
        question_lower = question.lower()
        
        # Indicadores de complejidad
        complex_indicators = [
            "agendar", "reservar", "cita", "turno",  # Booking intent
            "crear", "programar",  # Action verbs
            len(question.split()) > 15,  # Long questions
            "?" in question and len([c for c in question if c == "?"]) > 1,  # Multiple questions
        ]
        
        # Indicadores de simplicidad
        simple_indicators = [
            "disponibilidad", "horarios", "cuando", "hay",
            "libre", "puede",
            len(question.split()) < 10
        ]
        
        # Contar indicadores
        complex_count = sum(
            1 for indicator in complex_indicators
            if (isinstance(indicator, str) and indicator in question_lower) or
               (isinstance(indicator, bool) and indicator)
        )
        
        simple_count = sum(
            1 for indicator in simple_indicators
            if (isinstance(indicator, str) and indicator in question_lower) or
               (isinstance(indicator, bool) and indicator)
        )
        
        # Decisión
        if complex_count > simple_count:
            return "complex"
        else:
            return "simple"
    
    # ========================================================================
    # GENERACIÓN DE RESPUESTAS
    # ========================================================================
    
    def _generate_simple_availability_response(self, question: str) -> str:
        """
        Generar respuesta simple de disponibilidad.
        """
        # Formatear servicios
        services_display = self._format_services(self.company_config.services)
        
        return (
            f"Para consultar disponibilidad en {self.company_config.company_name}, "
            f"necesito:\n\n"
            f"📅 Fecha específica (DD-MM-YYYY)\n"
            f"🩺 Tipo de servicio ({services_display})\n\n"
            f"¿Puedes proporcionarme estos datos?"
        )
    
    def _generate_delegation_error_response(self) -> str:
        """Generar respuesta cuando la delegación falla"""
        return (
            f"Disculpa, no pude consultar la disponibilidad en este momento. "
            f"¿Podrías contactar directamente con {self.company_config.company_name}? 🙏"
        )
    
    def _generate_error_response(self, error: str) -> str:
        """Generar respuesta de error"""
        return (
            f"Ocurrió un problema al consultar disponibilidad en "
            f"{self.company_config.company_name}. "
            f"Te conecto con un asesor. 🤝"
        )
    
    def _format_services(self, services: Any) -> str:
        """Formatear servicios para mostrar"""
        if isinstance(services, dict):
            return ", ".join(services.keys())
        elif isinstance(services, list):
            return ", ".join(str(s) for s in services)
        elif isinstance(services, str):
            return services
        else:
            return "servicio disponible"
    
    # ========================================================================
    # MÉTODO LEGACY (MANTENER PARA COMPATIBILIDAD)
    # ========================================================================
    
    def check_availability(
        self,
        question: str,
        chat_history: list,
        schedule_context: Dict[str, Any]
    ) -> str:
        """
        Método legacy llamado por ScheduleAgent.
        
        Redirige a invoke() con formato correcto.
        """
        inputs = {
            "question": question,
            "chat_history": chat_history,
            "user_id": schedule_context.get("user_id", "availability_check"),
            "company_id": schedule_context.get("company_id", self.company_config.company_id)
        }
        
        return self.invoke(inputs)
