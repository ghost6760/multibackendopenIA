"""
MultiAgentOrchestratorGraph - Grafo de Orquestación Cognitiva

Este módulo implementa un StateGraph de LangGraph que orquesta agentes
LangChain existentes sin romper compatibilidad.

Flujo del grafo:
    START
      ↓
    [Validate Input] → validar pregunta y contexto
      ↓
    [Classify Intent] → usar RouterAgent para clasificar
      ↓
    [Route to Agent] → routing condicional basado en intención
      ↓
    [SALES|SUPPORT|EMERGENCY|SCHEDULE] → ejecutar agente específico
      ↓
    [Validate Output] → verificar respuesta del agente
      ↓
    [Retry?] → si falló, ¿reintentar con otro agente?
      ↓
    END

Ventajas vs implementación actual:
- Estado compartido entre nodos
- Validaciones explícitas en cada paso
- Reintentos automáticos con backoff
- Logging detallado de cada transición
- Checkpointing para debugging
- Escalado a agente de soporte en caso de fallo
"""

from typing import Dict, Any, List, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import logging
import json

from app.langgraph_adapters.state_schemas import (
    OrchestratorState,
    create_initial_orchestrator_state,
    ValidationResult
)
from app.langgraph_adapters.agent_adapter import AgentAdapter, validate_has_question
from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class MultiAgentOrchestratorGraph:
    """
    Orquestador de agentes basado en LangGraph.

    Orquesta múltiples agentes LangChain mediante un grafo de estado
    con validaciones, routing condicional y manejo de errores.

    Ejemplo de uso:
        # Crear agentes (LangChain existentes)
        router = RouterAgent(company_config, openai_service)
        sales = SalesAgent(company_config, openai_service)
        support = SupportAgent(company_config, openai_service)

        # Crear orquestador
        orchestrator = MultiAgentOrchestratorGraph(
            router_agent=router,
            agents={
                "sales": sales,
                "support": support,
                "emergency": emergency,
                "schedule": schedule
            },
            company_id=company_config.company_id
        )

        # Ejecutar (compatible con API actual)
        response, intent = orchestrator.get_response(
            question="¿Cuánto cuesta el tratamiento?",
            user_id="user123",
            chat_history=[]
        )
    """

    def __init__(
        self,
        router_agent: BaseAgent,
        agents: Dict[str, BaseAgent],
        company_id: str,
        enable_checkpointing: bool = False
    ):
        """
        Inicializar grafo de orquestación.

        Args:
            router_agent: Agente de clasificación de intenciones
            agents: Diccionario de agentes especializados
                    {"sales": SalesAgent, "support": SupportAgent, ...}
            company_id: ID de la empresa
            enable_checkpointing: Habilitar checkpointing para debugging
        """
        self.company_id = company_id
        self.enable_checkpointing = enable_checkpointing

        # Crear adaptadores para cada agente
        self.router_adapter = AgentAdapter(
            agent=router_agent,
            agent_name="router",
            timeout_ms=10000,
            validate_input=validate_has_question
        )

        self.agent_adapters: Dict[str, AgentAdapter] = {}
        for agent_name, agent in agents.items():
            self.agent_adapters[agent_name] = AgentAdapter(
                agent=agent,
                agent_name=agent_name,
                timeout_ms=30000,
                max_retries=2,
                validate_input=validate_has_question
            )

        # Construir grafo
        self.graph = self._build_graph()

        # Compilar grafo con checkpointer opcional
        checkpointer = MemorySaver() if enable_checkpointing else None
        self.app = self.graph.compile(checkpointer=checkpointer)

        logger.info(
            f"✅ MultiAgentOrchestratorGraph initialized for company {company_id}"
        )
        logger.info(f"   → Available agents: {list(self.agent_adapters.keys())}")
        logger.info(f"   → Checkpointing: {enable_checkpointing}")

    def _build_graph(self) -> StateGraph:
        """
        Construir grafo de orquestación.

        Nodos:
        - validate_input: Validar entrada del usuario
        - classify_intent: Clasificar intención con RouterAgent
        - execute_sales: Ejecutar SalesAgent
        - execute_support: Ejecutar SupportAgent
        - execute_emergency: Ejecutar EmergencyAgent
        - execute_schedule: Ejecutar ScheduleAgent
        - validate_output: Validar respuesta del agente
        - handle_retry: Manejar reintentos en caso de fallo

        Edges:
        - START -> validate_input
        - validate_input -> classify_intent (si válido)
        - validate_input -> END (si inválido)
        - classify_intent -> [routing condicional basado en intent]
        - execute_* -> validate_output
        - validate_output -> END (si exitoso)
        - validate_output -> handle_retry (si falló)
        - handle_retry -> execute_support (escalado)
        - handle_retry -> END (si ya reintentó)
        """
        workflow = StateGraph(OrchestratorState)

        # === AGREGAR NODOS === #
        workflow.add_node("validate_input", self._validate_input)
        workflow.add_node("classify_intent", self._classify_intent)
        workflow.add_node("execute_sales", self._execute_sales)
        workflow.add_node("execute_support", self._execute_support)
        workflow.add_node("execute_emergency", self._execute_emergency)
        workflow.add_node("execute_schedule", self._execute_schedule)
        workflow.add_node("validate_output", self._validate_output)
        workflow.add_node("handle_retry", self._handle_retry)

        # === EDGE DESDE START === #
        workflow.set_entry_point("validate_input")

        # === EDGE DESDE VALIDATE_INPUT === #
        workflow.add_conditional_edges(
            "validate_input",
            self._should_continue_after_validation,
            {
                "continue": "classify_intent",
                "end": END
            }
        )

        # === ROUTING CONDICIONAL DESDE CLASSIFY_INTENT === #
        workflow.add_conditional_edges(
            "classify_intent",
            self._route_to_agent,
            {
                "sales": "execute_sales",
                "support": "execute_support",
                "emergency": "execute_emergency",
                "schedule": "execute_schedule"
            }
        )

        # === EDGES DESDE AGENTES A VALIDATE_OUTPUT === #
        for agent_name in ["sales", "support", "emergency", "schedule"]:
            workflow.add_edge(f"execute_{agent_name}", "validate_output")

        # === EDGE CONDICIONAL DESDE VALIDATE_OUTPUT === #
        workflow.add_conditional_edges(
            "validate_output",
            self._should_retry,
            {
                "retry": "handle_retry",
                "end": END
            }
        )

        # === EDGE CONDICIONAL DESDE HANDLE_RETRY === #
        workflow.add_conditional_edges(
            "handle_retry",
            self._should_escalate_to_support,
            {
                "escalate": "execute_support",
                "end": END
            }
        )

        return workflow

    # === NODOS DEL GRAFO === #

    def _validate_input(self, state: OrchestratorState) -> OrchestratorState:
        """
        Validar entrada del usuario.

        Validaciones:
        - question no vacía
        - user_id válido
        - company_id coincide
        """
        logger.info(f"[{self.company_id}] 📍 Node: validate_input")

        validation: ValidationResult = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "metadata": {}
        }

        # Validar question
        question = state.get("question", "").strip()
        if not question:
            validation["is_valid"] = False
            validation["errors"].append("Question is empty")

        # Validar user_id
        user_id = state.get("user_id", "").strip()
        if not user_id:
            validation["is_valid"] = False
            validation["errors"].append("User ID is empty")

        # Validar company_id
        if state.get("company_id") != self.company_id:
            validation["is_valid"] = False
            validation["errors"].append("Company ID mismatch")

        # Agregar validación al estado
        state["validations"].append(validation)

        if not validation["is_valid"]:
            logger.warning(
                f"[{self.company_id}] Input validation failed: {validation['errors']}"
            )
            state["errors"].append("Input validation failed")
            state["agent_response"] = (
                "Lo siento, hubo un problema con tu consulta. "
                "Por favor, intenta de nuevo."
            )

        return state

    def _classify_intent(self, state: OrchestratorState) -> OrchestratorState:
        """
        Clasificar intención usando RouterAgent.

        Actualiza:
        - intent: Intención clasificada (SALES, SUPPORT, etc.)
        - confidence: Nivel de confianza (0.0-1.0)
        - intent_keywords: Keywords detectados
        """
        logger.info(f"[{self.company_id}] 📍 Node: classify_intent")

        question = state["question"]
        chat_history = state.get("chat_history", [])

        # Ejecutar RouterAgent mediante adaptador
        result = self.router_adapter.invoke({
            "question": question,
            "chat_history": chat_history
        })

        # Guardar ejecución
        state["executions"].append(result["execution_state"])

        if result["success"]:
            try:
                # Parsear respuesta JSON del router
                classification = json.loads(result["output"])

                state["intent"] = classification.get("intent", "SUPPORT")
                state["confidence"] = classification.get("confidence", 0.5)
                state["intent_keywords"] = classification.get("keywords", [])

                logger.info(
                    f"[{self.company_id}] Intent classified: {state['intent']} "
                    f"(confidence: {state['confidence']:.2f})"
                )

            except json.JSONDecodeError as e:
                logger.error(f"[{self.company_id}] Failed to parse router response: {e}")
                # Fallback a SUPPORT
                state["intent"] = "SUPPORT"
                state["confidence"] = 0.3
                state["intent_keywords"] = []

        else:
            # Si router falló, usar SUPPORT como fallback
            logger.error(
                f"[{self.company_id}] Router execution failed: {result['error']}"
            )
            state["intent"] = "SUPPORT"
            state["confidence"] = 0.0
            state["errors"].append(f"Router failed: {result['error']}")

        return state

    def _execute_sales(self, state: OrchestratorState) -> OrchestratorState:
        """Ejecutar SalesAgent"""
        return self._execute_agent(state, "sales")

    def _execute_support(self, state: OrchestratorState) -> OrchestratorState:
        """Ejecutar SupportAgent"""
        return self._execute_agent(state, "support")

    def _execute_emergency(self, state: OrchestratorState) -> OrchestratorState:
        """Ejecutar EmergencyAgent"""
        return self._execute_agent(state, "emergency")

    def _execute_schedule(self, state: OrchestratorState) -> OrchestratorState:
        """Ejecutar ScheduleAgent"""
        return self._execute_agent(state, "schedule")

    def _execute_agent(
        self,
        state: OrchestratorState,
        agent_name: str
    ) -> OrchestratorState:
        """
        Ejecutar un agente específico mediante su adaptador.

        Args:
            state: Estado actual
            agent_name: Nombre del agente a ejecutar

        Returns:
            Estado actualizado con respuesta del agente
        """
        logger.info(f"[{self.company_id}] 📍 Node: execute_{agent_name}")

        state["current_agent"] = agent_name

        # Obtener adaptador
        adapter = self.agent_adapters.get(agent_name)
        if not adapter:
            error_msg = f"Agent '{agent_name}' not found"
            logger.error(f"[{self.company_id}] {error_msg}")
            state["errors"].append(error_msg)
            state["agent_response"] = "Lo siento, hubo un error interno."
            return state

        # Preparar inputs para el agente
        inputs = {
            "question": state["question"],
            "chat_history": state.get("chat_history", []),
            "context": state.get("context", ""),
            "user_id": state["user_id"],
            "company_id": state["company_id"]
        }

        # Ejecutar agente mediante adaptador
        result = adapter.invoke(inputs)

        # Guardar ejecución en historial
        state["executions"].append(result["execution_state"])

        # Actualizar estado con resultado
        if result["success"]:
            state["agent_response"] = result["output"]
            logger.info(
                f"[{self.company_id}] {agent_name} executed successfully "
                f"({len(result['output'])} chars)"
            )
        else:
            state["errors"].append(f"{agent_name} failed: {result['error']}")
            state["agent_response"] = None
            logger.error(
                f"[{self.company_id}] {agent_name} execution failed: {result['error']}"
            )

        return state

    def _validate_output(self, state: OrchestratorState) -> OrchestratorState:
        """
        Validar respuesta del agente.

        Validaciones:
        - Respuesta no vacía
        - Longitud razonable
        - Sin errores críticos
        """
        logger.info(f"[{self.company_id}] 📍 Node: validate_output")

        validation: ValidationResult = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "metadata": {}
        }

        response = state.get("agent_response")

        if not response:
            validation["is_valid"] = False
            validation["errors"].append("Agent response is empty")

        elif len(response) < 10:
            validation["is_valid"] = False
            validation["errors"].append("Agent response is too short")

        else:
            validation["metadata"]["response_length"] = len(response)

            if len(response) > 4000:
                validation["warnings"].append("Response is very long")

        state["validations"].append(validation)

        if not validation["is_valid"]:
            logger.warning(
                f"[{self.company_id}] Output validation failed: {validation['errors']}"
            )
            state["should_retry"] = True

        return state

    def _handle_retry(self, state: OrchestratorState) -> OrchestratorState:
        """
        Manejar lógica de reintentos.

        Decide si:
        - Reintentar con otro agente
        - Escalar a support
        - Terminar con error
        """
        logger.info(f"[{self.company_id}] 📍 Node: handle_retry")

        state["retries"] += 1

        # Máximo 2 reintentos
        if state["retries"] >= 2:
            logger.warning(
                f"[{self.company_id}] Max retries reached, escalating to support"
            )
            state["should_escalate"] = True
        else:
            # Escalar a support si el agente actual falló
            if not state.get("agent_response"):
                state["should_escalate"] = True

        return state

    # === FUNCIONES DE ROUTING CONDICIONAL === #

    def _should_continue_after_validation(
        self,
        state: OrchestratorState
    ) -> Literal["continue", "end"]:
        """Determinar si continuar después de validar input"""
        if state["errors"]:
            return "end"
        return "continue"

    def _route_to_agent(
        self,
        state: OrchestratorState
    ) -> Literal["sales", "support", "emergency", "schedule"]:
        """
        Routing condicional basado en intención clasificada.

        Lógica:
        - Si confidence > 0.7 y intent está en agentes disponibles -> ir a ese agente
        - Si confidence <= 0.7 -> ir a support
        - Si intent no reconocido -> ir a support
        """
        intent = state.get("intent", "SUPPORT").lower()
        confidence = state.get("confidence", 0.0)

        logger.info(
            f"[{self.company_id}] Routing: intent={intent}, confidence={confidence}"
        )

        # Si confianza es baja, ir a support
        if confidence <= 0.7:
            logger.info(f"[{self.company_id}] Low confidence, routing to support")
            return "support"

        # Verificar que el agente existe
        if intent in self.agent_adapters:
            return intent
        else:
            logger.warning(
                f"[{self.company_id}] Intent '{intent}' not found, routing to support"
            )
            return "support"

    def _should_retry(
        self,
        state: OrchestratorState
    ) -> Literal["retry", "end"]:
        """Determinar si reintentar después de validar output"""
        if state.get("should_retry", False) and state["retries"] < 2:
            return "retry"
        return "end"

    def _should_escalate_to_support(
        self,
        state: OrchestratorState
    ) -> Literal["escalate", "end"]:
        """Determinar si escalar a support"""
        if state.get("should_escalate", False):
            # Solo escalar si no estamos ya en support
            if state.get("current_agent") != "support":
                return "escalate"
        return "end"

    # === API PÚBLICA === #

    def get_response(
        self,
        question: str,
        user_id: str,
        chat_history: List[Any] = None,
        context: str = ""
    ) -> tuple[str, str]:
        """
        Obtener respuesta del sistema multi-agente.

        ✅ COMPATIBLE CON API EXISTENTE

        Args:
            question: Pregunta del usuario
            user_id: ID del usuario
            chat_history: Historial de conversación
            context: Contexto adicional (RAG, etc.)

        Returns:
            Tupla (response, agent_used)
        """
        logger.info(f"[{self.company_id}] 🚀 MultiAgentOrchestratorGraph.get_response()")

        # Crear estado inicial
        initial_state = create_initial_orchestrator_state(
            question=question,
            user_id=user_id,
            company_id=self.company_id,
            chat_history=chat_history or [],
            context=context
        )

        # Ejecutar grafo
        try:
            final_state = self.app.invoke(initial_state)

            # Extraer respuesta y agente usado
            response = final_state.get("agent_response", "")
            agent_used = final_state.get("current_agent", "support")

            # Si no hay respuesta, usar fallback
            if not response:
                response = (
                    "Lo siento, estoy experimentando dificultades técnicas. "
                    "Por favor, intenta de nuevo más tarde."
                )

            logger.info(
                f"[{self.company_id}] ✅ Response generated by {agent_used} "
                f"({len(response)} chars, {final_state['retries']} retries)"
            )

            return response, agent_used

        except Exception as e:
            logger.exception(f"[{self.company_id}] Error executing graph: {e}")
            return (
                "Lo siento, estoy experimentando dificultades técnicas. "
                "Por favor, intenta de nuevo más tarde.",
                "error"
            )

    def get_stats(self) -> Dict[str, Any]:
        """
        Obtener estadísticas de todos los agentes.

        Returns:
            Diccionario con estadísticas de cada adaptador
        """
        stats = {
            "company_id": self.company_id,
            "router": self.router_adapter.get_stats(),
            "agents": {}
        }

        for agent_name, adapter in self.agent_adapters.items():
            stats["agents"][agent_name] = adapter.get_stats()

        return stats

    def reset_stats(self):
        """Resetear estadísticas de todos los agentes"""
        self.router_adapter.reset_stats()
        for adapter in self.agent_adapters.values():
            adapter.reset_stats()
