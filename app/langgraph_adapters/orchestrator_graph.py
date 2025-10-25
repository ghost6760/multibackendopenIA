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
from datetime import datetime
import logging
import json

from app.langgraph_adapters.state_schemas import (
    OrchestratorState,
    create_initial_orchestrator_state,
    ValidationResult
)
from app.langgraph_adapters.agent_adapter import AgentAdapter, validate_has_question
from app.agents.base_agent import BaseAgent
from app.services.shared_state_store import SharedStateStore
from app.models.audit_trail import AuditManager
# CompensationOrchestrator: lazy import to avoid circular dependency

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
        enable_checkpointing: bool = False,
        shared_state_store: SharedStateStore = None,
        tool_executor = None  # ToolExecutor opcional
    ):
        """
        Inicializar grafo de orquestación.

        Args:
            router_agent: Agente de clasificación de intenciones
            agents: Diccionario de agentes especializados
                    {"sales": SalesAgent, "support": SupportAgent, ...}
            company_id: ID de la empresa
            enable_checkpointing: Habilitar checkpointing para debugging
            shared_state_store: Store compartido entre agentes (opcional)
            tool_executor: ToolExecutor para acciones (opcional)
        """
        self.company_id = company_id
        self.enable_checkpointing = enable_checkpointing

        # Shared State Store para coordinación entre agentes
        self.shared_state_store = shared_state_store or SharedStateStore(
            backend="memory",
            ttl_seconds=3600  # 1 hora
        )

        # Audit Trail para registro de acciones críticas
        self.audit_manager = AuditManager(company_id=company_id)

        # Compensation Orchestrator para rollback automático (lazy import)
        from app.workflows.compensation_orchestrator import CompensationOrchestrator
        self.compensation_orchestrator = CompensationOrchestrator(
            company_id=company_id,
            audit_manager=self.audit_manager
        )

        # Tool Executor para acciones (booking, notifications, etc)
        self.tool_executor = tool_executor
        self.tools_enabled = tool_executor is not None

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

        # ✅ Configurar recursion_limit aumentado para prevenir errores
        # Default es 25, aumentamos a 50 para dar más margen
        self.recursion_limit = 50

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
        workflow.add_node("detect_secondary_intent", self._detect_secondary_intent)
        workflow.add_node("execute_sales", self._execute_sales)
        workflow.add_node("execute_support", self._execute_support)
        workflow.add_node("execute_emergency", self._execute_emergency)
        workflow.add_node("execute_schedule", self._execute_schedule)
        workflow.add_node("validate_output", self._validate_output)
        workflow.add_node("handle_agent_handoff", self._handle_agent_handoff)
        workflow.add_node("validate_cross_agent_info", self._validate_cross_agent_info)
        workflow.add_node("handle_retry", self._handle_retry)

        # === NODOS DE TOOLS (ACCIONES) === #
        if self.tools_enabled:
            workflow.add_node("check_availability", self._check_availability_tool)
            workflow.add_node("execute_booking", self._execute_booking_tool)
            workflow.add_node("send_notification", self._send_notification_tool)
            workflow.add_node("create_ticket", self._create_ticket_tool)

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

        # === EDGE DE CLASSIFY_INTENT A DETECT_SECONDARY_INTENT === #
        workflow.add_edge("classify_intent", "detect_secondary_intent")

        # === ROUTING CONDICIONAL DESDE DETECT_SECONDARY_INTENT === #
        workflow.add_conditional_edges(
            "detect_secondary_intent",
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
        if self.tools_enabled:
            workflow.add_conditional_edges(
                "validate_output",
                self._should_execute_tools_or_continue,
                {
                    "check_availability": "check_availability",
                    "execute_booking": "execute_booking",
                    "send_notification": "send_notification",
                    "create_ticket": "create_ticket",
                    "validate_cross_agent": "validate_cross_agent_info",
                    "check_handoff": "handle_agent_handoff",
                    "retry": "handle_retry",
                    "end": END
                }
            )

            # === EDGES DESDE NODOS DE TOOLS === #
            # check_availability vuelve a schedule agent para confirmar
            workflow.add_edge("check_availability", "execute_schedule")
            workflow.add_edge("execute_booking", "validate_cross_agent_info")
            workflow.add_edge("send_notification", "validate_cross_agent_info")
            workflow.add_edge("create_ticket", "validate_cross_agent_info")
        else:
            workflow.add_conditional_edges(
                "validate_output",
                self._should_validate_cross_agent_or_retry,
                {
                    "validate_cross_agent": "validate_cross_agent_info",
                    "check_handoff": "handle_agent_handoff",
                    "retry": "handle_retry",
                    "end": END
                }
            )

        # === EDGE DESDE VALIDATE_CROSS_AGENT_INFO === #
        workflow.add_edge("validate_cross_agent_info", END)

        # === EDGE CONDICIONAL DESDE HANDLE_AGENT_HANDOFF === #
        workflow.add_conditional_edges(
            "handle_agent_handoff",
            self._should_perform_handoff,
            {
                "handoff_to_sales": "execute_sales",
                "handoff_to_schedule": "execute_schedule",
                "handoff_to_support": "execute_support",
                "handoff_to_emergency": "execute_emergency",
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

    def _detect_secondary_intent(self, state: OrchestratorState) -> OrchestratorState:
        """
        Detectar intención secundaria mid-conversation.

        Casos de uso:
        - Usuario pregunta por precio durante agendamiento → secondary_intent = "sales"
        - Usuario pregunta por disponibilidad durante consulta comercial → secondary_intent = "schedule"
        - Usuario pregunta general durante cualquier flujo → secondary_intent = "support"
        - Usuario menciona emergencia/dolor → secondary_intent = "emergency"

        Si se detecta secondary intent con alta confianza, se puede hacer handoff.
        """
        logger.info(f"[{self.company_id}] 📍 Node: detect_secondary_intent")

        question = state["question"].lower()
        primary_intent = state.get("intent", "").lower()

        # ===== KEYWORDS PARA DIFERENTES INTENTS ===== #

        # Keywords comerciales/pricing
        pricing_keywords = [
            "precio", "costo", "cuánto", "cuanto", "valor", "pagar",
            "inversión", "oferta", "promoción", "descuento", "cuesta"
        ]

        # Keywords de agendamiento
        schedule_keywords = [
            "cita", "agenda", "agendar", "reserva", "reservar", "disponibilidad",
            "horario", "turno", "día", "fecha", "hora", "cuando"
        ]

        # Keywords de soporte general
        support_keywords = [
            "parqueadero", "ubicación", "dirección", "donde queda", "dónde",
            "horario de atención", "atienden", "cómo llegar", "como llegar",
            "métodos de pago", "formas de pago", "tarjeta", "efectivo",
            "información", "requisitos", "documentos", "qué necesito",
            "queja", "reclamo", "problema", "ayuda"
        ]

        # Keywords de emergencia (prioridad máxima)
        emergency_keywords = [
            "dolor", "duele", "sangr", "emergencia", "urgente", "urgencia",
            "inmediato", "ahora", "rápido", "ayuda", "mal", "grave",
            "inflamación", "hinchazón", "infección", "fiebre", "mareo"
        ]

        # ===== DETECTAR PRESENCIA DE KEYWORDS ===== #
        has_pricing_query = any(keyword in question for keyword in pricing_keywords)
        has_schedule_query = any(keyword in question for keyword in schedule_keywords)
        has_support_query = any(keyword in question for keyword in support_keywords)
        has_emergency_query = any(keyword in question for keyword in emergency_keywords)

        logger.info(
            f"[{self.company_id}] Detection: primary_intent={primary_intent}, "
            f"pricing={has_pricing_query}, schedule={has_schedule_query}, "
            f"support={has_support_query}, emergency={has_emergency_query}"
        )

        # ===== PRIORIDAD 1: EMERGENCIAS (siempre tiene máxima prioridad) ===== #
        if has_emergency_query and primary_intent != "emergency":
            state["secondary_intent"] = "emergency"
            state["secondary_confidence"] = 0.9  # Alta confianza
            logger.info(
                f"[{self.company_id}] ⚠️ Secondary intent detected: EMERGENCY "
                f"(urgent query from {primary_intent})"
            )

        # ===== PRIORIDAD 2: PRICING (durante schedule o support) ===== #
        elif primary_intent in ["schedule", "support"] and has_pricing_query:
            state["secondary_intent"] = "sales"
            state["secondary_confidence"] = 0.8
            logger.info(
                f"[{self.company_id}] ✅ Secondary intent detected: sales "
                f"(pricing question during {primary_intent})"
            )

        # ===== PRIORIDAD 3: SCHEDULING (durante sales o support) ===== #
        elif primary_intent in ["sales", "support"] and has_schedule_query:
            state["secondary_intent"] = "schedule"
            state["secondary_confidence"] = 0.8
            logger.info(
                f"[{self.company_id}] ✅ Secondary intent detected: schedule "
                f"(scheduling question during {primary_intent})"
            )

        # ===== PRIORIDAD 4: SUPPORT (durante sales o schedule) ===== #
        elif primary_intent in ["sales", "schedule"] and has_support_query:
            state["secondary_intent"] = "support"
            state["secondary_confidence"] = 0.75
            logger.info(
                f"[{self.company_id}] ✅ Secondary intent detected: support "
                f"(general question during {primary_intent})"
            )

        # ===== NO SE DETECTÓ SECONDARY INTENT ===== #
        else:
            state["secondary_intent"] = None
            state["secondary_confidence"] = 0.0
            logger.info(
                f"[{self.company_id}] ❌ No secondary intent detected"
            )

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

            # ✅ Guardar información en shared state store para TODOS los agentes
            user_id = state["user_id"]
            response = result["output"]

            # ===== SALES AGENT: Guardar pricing info ===== #
            if agent_name == "sales":
                has_pricing = any(
                    keyword in response.lower()
                    for keyword in ["$", "cop", "pesos", "precio", "costo", "valor"]
                )
                if has_pricing:
                    logger.info(f"[{self.company_id}] Storing pricing info from {agent_name}")

                state["shared_context"]["sales_info"] = {
                    "response": response,
                    "agent": agent_name,
                    "has_pricing": has_pricing,
                    "timestamp": datetime.utcnow().isoformat()
                }

            # ===== SCHEDULE AGENT: Guardar schedule info ===== #
            elif agent_name == "schedule":
                has_appointment = any(
                    keyword in response.lower()
                    for keyword in ["cita", "agenda", "fecha", "hora", "confirmada"]
                )
                logger.info(f"[{self.company_id}] Storing schedule info from {agent_name}")

                state["shared_context"]["schedule_info"] = {
                    "response": response,
                    "agent": agent_name,
                    "has_appointment": has_appointment,
                    "timestamp": datetime.utcnow().isoformat()
                }

            # ===== SUPPORT AGENT: Guardar support info ===== #
            elif agent_name == "support":
                logger.info(f"[{self.company_id}] Storing support info from {agent_name}")

                state["shared_context"]["support_info"] = {
                    "response": response,
                    "agent": agent_name,
                    "question": state["question"],
                    "timestamp": datetime.utcnow().isoformat()
                }

            # ===== EMERGENCY AGENT: Guardar emergency info ===== #
            elif agent_name == "emergency":
                has_urgency = any(
                    keyword in response.lower()
                    for keyword in ["urgente", "emergencia", "inmediato", "llamar", "contactar"]
                )
                logger.info(f"[{self.company_id}] Storing emergency info from {agent_name}")

                state["shared_context"]["emergency_info"] = {
                    "response": response,
                    "agent": agent_name,
                    "has_urgency": has_urgency,
                    "question": state["question"],
                    "timestamp": datetime.utcnow().isoformat()
                }

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

    def _handle_agent_handoff(self, state: OrchestratorState) -> OrchestratorState:
        """
        Manejar handoff entre agentes.

        Casos de uso:
        - Schedule detecta pregunta de pricing → handoff a Sales
        - Sales detecta pregunta de agendamiento → handoff a Schedule

        El handoff permite que un agente derive a otro temporalmente
        y luego puede volver al agente original.
        """
        logger.info(f"[{self.company_id}] 📍 Node: handle_agent_handoff")

        current_agent = state.get("current_agent")
        secondary_intent = state.get("secondary_intent")
        secondary_confidence = state.get("secondary_confidence", 0.0)

        # ✅ PREVENIR LOOP: Si ya se completó handoff, no hacer otro
        if state.get("handoff_completed", False):
            logger.info(f"[{self.company_id}] Handoff already completed, skipping")
            state["handoff_requested"] = False
            return state

        # Solo hacer handoff si hay secondary intent con alta confianza
        # Y el secondary intent es diferente del agente actual
        if (secondary_intent and
            secondary_confidence >= 0.7 and
            secondary_intent != current_agent):
            # Registrar handoff
            state["handoff_requested"] = True
            state["handoff_from"] = current_agent
            state["handoff_to"] = secondary_intent
            state["handoff_reason"] = "secondary_intent_detected"

            # Guardar contexto del agente original
            state["handoff_context"] = {
                "original_agent": current_agent,
                "original_response": state.get("agent_response"),
                "question": state["question"]
            }

            logger.info(
                f"[{self.company_id}] Handoff requested: {current_agent} → {secondary_intent}"
            )

        else:
            state["handoff_requested"] = False
            if secondary_intent == current_agent:
                logger.info(
                    f"[{self.company_id}] No handoff needed: secondary_intent same as current_agent ({current_agent})"
                )
            else:
                logger.info(f"[{self.company_id}] No handoff needed")

        # ✅ Marcar handoff como completado para prevenir loops
        state["handoff_completed"] = True

        return state

    def _validate_cross_agent_info(self, state: OrchestratorState) -> OrchestratorState:
        """
        Validar consistencia de información entre TODOS los agentes.

        Casos de validación:
        - Si Schedule proporcionó precio, verificar con Sales
        - Si Sales proporcionó disponibilidad, verificar con Schedule
        - Si Support proporcionó precio, verificar con Sales
        - Si cualquier agente proporciona info que debería venir de otro especialista

        Esta validación usa el shared_context para comparar información.
        """
        logger.info(f"[{self.company_id}] 📍 Node: validate_cross_agent_info")

        current_agent = state.get("current_agent")
        agent_response = state.get("agent_response", "")
        shared_context = state.get("shared_context", {})

        # Keywords para diferentes tipos de información
        pricing_keywords = ["$", "cop", "pesos", "precio", "costo", "valor"]
        schedule_keywords = ["cita", "agenda", "disponibilidad", "horario", "fecha"]
        emergency_keywords = ["urgente", "emergencia", "dolor", "inmediato"]

        has_pricing_info = any(keyword in agent_response.lower() for keyword in pricing_keywords)
        has_schedule_info = any(keyword in agent_response.lower() for keyword in schedule_keywords)
        has_emergency_info = any(keyword in agent_response.lower() for keyword in emergency_keywords)

        validation: ValidationResult = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "metadata": {}
        }

        # ===== VALIDAR PRICING INFO ===== #
        # Si un agente NO-SALES proporciona pricing, validar con Sales
        if current_agent != "sales" and has_pricing_info:
            sales_info = shared_context.get("sales_info", {})

            if sales_info and sales_info.get("has_pricing"):
                validation["warnings"].append(
                    f"{current_agent} provided pricing - validated with Sales context"
                )
                validation["metadata"]["has_sales_context"] = True
            else:
                validation["warnings"].append(
                    f"{current_agent} provided pricing without Sales context"
                )

        # ===== VALIDAR SCHEDULE INFO ===== #
        # Si un agente NO-SCHEDULE proporciona schedule info, validar con Schedule
        if current_agent != "schedule" and has_schedule_info:
            schedule_info = shared_context.get("schedule_info", {})

            if schedule_info and schedule_info.get("has_appointment"):
                validation["warnings"].append(
                    f"{current_agent} mentioned scheduling - validated with Schedule context"
                )
                validation["metadata"]["has_schedule_context"] = True
            else:
                validation["warnings"].append(
                    f"{current_agent} mentioned scheduling without Schedule context"
                )

        # ===== VALIDAR EMERGENCY INFO ===== #
        # Si un agente NO-EMERGENCY menciona emergencia, validar con Emergency
        if current_agent != "emergency" and has_emergency_info:
            emergency_info = shared_context.get("emergency_info", {})

            if emergency_info:
                validation["warnings"].append(
                    f"{current_agent} mentioned emergency - validated with Emergency context"
                )
                validation["metadata"]["has_emergency_context"] = True
            else:
                validation["warnings"].append(
                    f"{current_agent} mentioned emergency without Emergency context"
                )

        # ===== LOG SHARED CONTEXT DISPONIBLE ===== #
        available_contexts = [k for k in shared_context.keys()]
        if available_contexts:
            validation["metadata"]["available_contexts"] = available_contexts
            logger.info(
                f"[{self.company_id}] Available contexts: {', '.join(available_contexts)}"
            )

        state["validations"].append(validation)

        logger.info(
            f"[{self.company_id}] Cross-agent validation completed: "
            f"{len(validation['errors'])} errors, {len(validation['warnings'])} warnings"
        )

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

    def _should_validate_cross_agent_or_retry(
        self,
        state: OrchestratorState
    ) -> Literal["validate_cross_agent", "check_handoff", "retry", "end"]:
        """
        Determinar siguiente paso después de validar output.

        Prioridades:
        1. Si hay secondary intent detectado Y NO se ha completado handoff → check_handoff
        2. Si hay información crítica (pricing/schedule) → validate_cross_agent
        3. Si debe reintentar → retry
        4. Sino → end
        """
        # ✅ PREVENIR LOOP: Verificar si ya se completó handoff
        if state.get("handoff_completed", False):
            logger.info(f"[{self.company_id}] Handoff already completed, skipping check")
            return "end"

        # Prioridad 1: Verificar handoff si hay secondary intent Y NO se ha completado
        if (state.get("secondary_intent") and
            state.get("secondary_confidence", 0.0) >= 0.7 and
            not state.get("handoff_completed", False)):
            return "check_handoff"

        # Prioridad 2: Validar cross-agent si hay pricing/schedule info
        current_agent = state.get("current_agent")
        agent_response = state.get("agent_response", "")

        if current_agent == "schedule" and any(
            keyword in agent_response.lower()
            for keyword in ["$", "cop", "pesos", "precio", "costo"]
        ):
            return "validate_cross_agent"

        # Prioridad 3: Reintentar si es necesario
        if state.get("should_retry", False) and state["retries"] < 2:
            return "retry"

        # Default: terminar
        return "end"

    def _should_retry(
        self,
        state: OrchestratorState
    ) -> Literal["retry", "end"]:
        """Determinar si reintentar después de validar output"""
        if state.get("should_retry", False) and state["retries"] < 2:
            return "retry"
        return "end"

    def _should_perform_handoff(
        self,
        state: OrchestratorState
    ) -> Literal["handoff_to_sales", "handoff_to_schedule", "handoff_to_support", "handoff_to_emergency", "end"]:
        """
        Determinar si realizar handoff a otro agente.

        Returns:
            - handoff_to_sales: Hacer handoff a SalesAgent
            - handoff_to_schedule: Hacer handoff a ScheduleAgent
            - handoff_to_support: Hacer handoff a SupportAgent
            - handoff_to_emergency: Hacer handoff a EmergencyAgent
            - end: No hacer handoff, terminar
        """
        if not state.get("handoff_requested", False):
            return "end"

        handoff_to = state.get("handoff_to")

        if handoff_to == "sales":
            return "handoff_to_sales"
        elif handoff_to == "schedule":
            return "handoff_to_schedule"
        elif handoff_to == "support":
            return "handoff_to_support"
        elif handoff_to == "emergency":
            return "handoff_to_emergency"
        else:
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

    # === ROUTING PARA TOOLS === #

    def _should_execute_tools_or_continue(
        self,
        state: OrchestratorState
    ) -> Literal["check_availability", "execute_booking", "send_notification", "create_ticket", "validate_cross_agent", "check_handoff", "retry", "end"]:
        """
        Determinar si ejecutar herramientas (tools) o continuar flujo normal.

        Lógica:
        1. Si el agente es 'schedule' Y necesita verificar disponibilidad → check_availability
        2. Si el agente es 'schedule' Y tiene booking confirmado → execute_booking
        3. Si hay información de cita confirmada → send_notification
        4. Si es support con problema no resuelto → create_ticket
        5. Sino, continuar flujo normal (validate_cross_agent, check_handoff, retry, end)
        """
        current_agent = state.get("current_agent")
        agent_response = state.get("agent_response", "")

        # Detectar si necesitamos verificar disponibilidad (schedule agent)
        if current_agent == "schedule":
            shared_context = state.get("shared_context", {})
            schedule_info = shared_context.get("schedule_info", {})

            # Prioridad 1: Verificar disponibilidad si se solicitó y NO se ha verificado
            if schedule_info.get("needs_availability_check") and not schedule_info.get("availability_checked"):
                logger.info(
                    f"[{self.company_id}] 🔧 Tool detected: Need availability check → check_availability"
                )
                return "check_availability"

            # Prioridad 2: Crear booking si ya se confirmó
            if schedule_info.get("has_appointment"):
                # Marcar que necesitamos crear booking
                state["tools_to_execute"] = state.get("tools_to_execute", [])
                if "booking" not in state["tools_to_execute"]:
                    state["tools_to_execute"].append("booking")

                logger.info(
                    f"[{self.company_id}] 🔧 Tool detected: Appointment confirmed → execute_booking"
                )
                return "execute_booking"

        # Detectar si necesitamos enviar notificación
        # (después de crear booking, enviar confirmación)
        if "booking" in state.get("tools_executed", []):
            logger.info(
                f"[{self.company_id}] 🔧 Tool detected: Booking created → send_notification"
            )
            return "send_notification"

        # Detectar si necesitamos crear ticket (support con problema)
        if current_agent == "support":
            response_lower = agent_response.lower()
            problem_keywords = ["problema", "error", "falla", "no funciona", "queja"]

            if any(keyword in response_lower for keyword in problem_keywords):
                logger.info(
                    f"[{self.company_id}] 🔧 Tool detected: Support issue → create_ticket"
                )
                return "create_ticket"

        # Continuar flujo normal usando lógica existente
        return self._should_validate_cross_agent_or_retry(state)

    # === NODOS DE TOOLS === #

    def _check_availability_tool(self, state: OrchestratorState) -> OrchestratorState:
        """
        Nodo: Verificar disponibilidad en Google Calendar.

        Este nodo se ejecuta cuando el schedule agent necesita verificar
        slots disponibles antes de confirmar una cita.

        Flow:
        1. Extrae fecha y tratamiento del shared_context
        2. Llama a ToolExecutor para check_availability
        3. Actualiza shared_context con slots disponibles
        4. Regresa a schedule agent para que confirme con usuario
        """
        logger.info(f"[{self.company_id}] 📍 Node: check_availability")

        user_id = state.get("user_id", "unknown")
        shared_context = state.get("shared_context", {})
        schedule_info = shared_context.get("schedule_info", {})

        if not self.tool_executor:
            logger.warning(f"[{self.company_id}] ToolExecutor not configured, skipping availability check")
            # Marcar como verificado para evitar loop
            schedule_info["availability_checked"] = True
            schedule_info["available_slots"] = []
            return state

        # Extraer parámetros
        date = schedule_info.get("date")
        treatment = schedule_info.get("treatment", "general")

        if not date:
            logger.warning(f"[{self.company_id}] No date provided for availability check")
            schedule_info["availability_checked"] = True
            schedule_info["available_slots"] = []
            return state

        # Ejecutar tool check_availability via ToolExecutor
        result = self.tool_executor.execute_tool(
            tool_name="google_calendar",
            parameters={
                "action": "check_availability",
                "date": date,
                "treatment": treatment
            },
            user_id=user_id,
            agent_name="schedule_agent",
            conversation_id=state.get("conversation_id")
        )

        if result.get("success"):
            available_slots = result.get("data", {}).get("available_slots", [])

            logger.info(
                f"✅ [{self.company_id}] Availability checked: {len(available_slots)} slots available"
            )

            # Actualizar shared_context con resultados
            schedule_info["availability_checked"] = True
            schedule_info["available_slots"] = available_slots
            schedule_info["needs_availability_check"] = False  # Reset flag

            # Verificar si el slot solicitado está disponible
            requested_time = schedule_info.get("time")
            if requested_time and requested_time in available_slots:
                schedule_info["requested_slot_available"] = True
            elif requested_time:
                schedule_info["requested_slot_available"] = False

            # Guardar en shared state store
            if self.shared_state_store:
                self.shared_state_store.update_context(
                    user_id=user_id,
                    context_update={"schedule_info": schedule_info}
                )

        else:
            logger.error(
                f"❌ [{self.company_id}] Availability check failed: {result.get('error')}"
            )

            # Marcar como verificado con error para evitar loop infinito
            schedule_info["availability_checked"] = True
            schedule_info["availability_check_error"] = result.get("error")
            schedule_info["available_slots"] = []

        # Actualizar estado
        shared_context["schedule_info"] = schedule_info
        state["shared_context"] = shared_context

        # Marcar tool como ejecutado
        state["tools_executed"] = state.get("tools_executed", [])
        state["tools_executed"].append("check_availability")

        return state

    def _execute_booking_tool(self, state: OrchestratorState) -> OrchestratorState:
        """
        Nodo: Ejecutar herramienta de booking (crear cita en Google Calendar).

        Este nodo se ejecuta cuando el schedule agent confirmó una cita.
        Usa CompensationOrchestrator para rollback automático si falla.
        """
        logger.info(f"[{self.company_id}] 📍 Node: execute_booking")

        user_id = state.get("user_id", "unknown")
        shared_context = state.get("shared_context", {})
        schedule_info = shared_context.get("schedule_info", {})

        if not self.tool_executor:
            logger.warning(f"[{self.company_id}] ToolExecutor not configured, skipping booking")
            return state

        # Crear saga para transacción compensable
        saga = self.compensation_orchestrator.create_saga(
            user_id=user_id,
            saga_name="create_appointment"
        )

        # Acción: Crear evento en calendario
        def execute_calendar_booking():
            params = {
                "action": "create_booking",
                "treatment": schedule_info.get("treatment", "Consulta"),
                "date": schedule_info.get("date"),
                "time": schedule_info.get("time"),
                "patient_name": schedule_info.get("patient_name"),
                "patient_phone": schedule_info.get("patient_phone")
            }

            return self.tool_executor.execute_tool("google_calendar", params)

        # Compensación: Eliminar evento si falla algo después
        def compensate_calendar_booking(result):
            if result and result.get("data") and result["data"].get("event_id"):
                event_id = result["data"]["event_id"]

                compensation_params = {
                    "action": "delete_event",
                    "event_id": event_id
                }

                return self.tool_executor.execute_tool("google_calendar", compensation_params)

            return {"success": True, "message": "Nothing to compensate"}

        # Agregar acción a saga
        self.compensation_orchestrator.add_action(
            saga_id=saga.saga_id,
            action_type="booking",
            action_name="google_calendar.create_event",
            executor=execute_calendar_booking,
            compensator=compensate_calendar_booking,
            input_params={
                "treatment": schedule_info.get("treatment"),
                "date": schedule_info.get("date"),
                "time": schedule_info.get("time")
            }
        )

        # Ejecutar saga
        result = self.compensation_orchestrator.execute_saga(saga.saga_id)

        if result["success"]:
            logger.info(
                f"✅ [{self.company_id}] Booking created successfully"
            )

            # Marcar herramienta como ejecutada
            state["tools_executed"] = state.get("tools_executed", [])
            state["tools_executed"].append("booking")

            # Guardar event_id en estado para notification
            if "tool_results" not in state:
                state["tool_results"] = {}
            state["tool_results"]["booking"] = result

        else:
            logger.error(
                f"❌ [{self.company_id}] Booking failed and rolled back: {result.get('error')}"
            )

            # Marcar error
            state["tool_errors"] = state.get("tool_errors", [])
            state["tool_errors"].append({
                "tool": "booking",
                "error": result.get("error")
            })

        return state

    def _send_notification_tool(self, state: OrchestratorState) -> OrchestratorState:
        """
        Nodo: Enviar notificación (email/WhatsApp) de confirmación.

        Se ejecuta después de crear booking exitosamente.
        """
        logger.info(f"[{self.company_id}] 📍 Node: send_notification")

        user_id = state.get("user_id", "unknown")
        shared_context = state.get("shared_context", {})
        schedule_info = shared_context.get("schedule_info", {})
        tool_results = state.get("tool_results", {})
        booking_result = tool_results.get("booking", {})

        if not self.tool_executor:
            logger.warning(f"[{self.company_id}] ToolExecutor not configured, skipping notification")
            return state

        # Obtener email del paciente (asumimos que está en user_info)
        # TODO: Integrar con UserInfo del SharedStateStore
        patient_email = schedule_info.get("patient_email", "patient@example.com")

        # Preparar variables para template
        template_vars = {
            "company_name": self.company_id.capitalize(),
            "patient_name": schedule_info.get("patient_name", "Paciente"),
            "treatment": schedule_info.get("treatment", "Consulta"),
            "date": schedule_info.get("date", ""),
            "time": schedule_info.get("time", "")
        }

        # Registrar en audit trail
        audit_entry = self.audit_manager.log_action(
            user_id=user_id,
            action_type="notification",
            action_name="email.send_confirmation",
            input_params={
                "to_email": patient_email,
                "template": "appointment_confirmation"
            },
            compensable=False  # Email no se puede "desenviar"
        )

        # Enviar email
        email_params = {
            "to_email": patient_email,
            "template_name": "appointment_confirmation",
            "template_vars": template_vars
        }

        result = self.tool_executor.execute_tool("send_email", email_params)

        if result["success"]:
            logger.info(
                f"✅ [{self.company_id}] Notification sent successfully to {patient_email}"
            )

            self.audit_manager.mark_success(audit_entry.audit_id, result=result)

            state["tools_executed"] = state.get("tools_executed", [])
            state["tools_executed"].append("notification")

        else:
            logger.error(
                f"❌ [{self.company_id}] Notification failed: {result.get('error')}"
            )

            self.audit_manager.mark_failed(audit_entry.audit_id, error_message=result.get("error"))

            state["tool_errors"] = state.get("tool_errors", [])
            state["tool_errors"].append({
                "tool": "notification",
                "error": result.get("error")
            })

        return state

    def _create_ticket_tool(self, state: OrchestratorState) -> OrchestratorState:
        """
        Nodo: Crear ticket de soporte.

        Se ejecuta cuando support agent detecta un problema que requiere seguimiento.
        """
        logger.info(f"[{self.company_id}] 📍 Node: create_ticket")

        user_id = state.get("user_id", "unknown")
        agent_response = state.get("agent_response", "")
        question = state.get("question", "")

        if not self.tool_executor:
            logger.warning(f"[{self.company_id}] ToolExecutor not configured, skipping ticket creation")
            return state

        # Registrar en audit trail
        audit_entry = self.audit_manager.log_action(
            user_id=user_id,
            action_type="ticket",
            action_name="ticketing.create_ticket",
            input_params={
                "subject": question[:100],
                "description": agent_response[:500]
            },
            compensable=True,  # Los tickets pueden cerrarse/eliminarse
            compensation_action="ticketing.close_ticket"
        )

        # Crear ticket
        ticket_params = {
            "subject": f"Support Request - {question[:50]}...",
            "description": f"User Question: {question}\n\nAgent Response: {agent_response}",
            "priority": "medium",
            "requester_id": user_id
        }

        result = self.tool_executor.execute_tool("create_ticket", ticket_params)

        if result["success"]:
            logger.info(
                f"✅ [{self.company_id}] Support ticket created successfully"
            )

            self.audit_manager.mark_success(audit_entry.audit_id, result=result)

            state["tools_executed"] = state.get("tools_executed", [])
            state["tools_executed"].append("ticket")

        else:
            logger.error(
                f"❌ [{self.company_id}] Ticket creation failed: {result.get('error')}"
            )

            self.audit_manager.mark_failed(audit_entry.audit_id, error_message=result.get("error"))

            state["tool_errors"] = state.get("tool_errors", [])
            state["tool_errors"].append({
                "tool": "ticket",
                "error": result.get("error")
            })

        return state

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

        # Ejecutar grafo con recursion_limit configurado
        try:
            final_state = self.app.invoke(
                initial_state,
                config={"recursion_limit": self.recursion_limit}
            )

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
