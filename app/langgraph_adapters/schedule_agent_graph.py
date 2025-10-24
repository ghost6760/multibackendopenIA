"""
ScheduleAgentGraph - Ejemplo de Agente con Grafo Interno

Este módulo muestra cómo un agente lineal (ScheduleAgent) puede ser
ejecutado desde un grafo de estado de LangGraph con validaciones paso a paso.

Flujo del grafo:
    START
      ↓
    [Extract Info] → extraer fecha, tratamiento, info de paciente
      ↓
    [Validate Info] → validar información extraída
      ↓
    [Check Availability] → verificar disponibilidad (si fecha válida)
      ↓
    [Generate Response] → generar respuesta usando LLM
      ↓
    END

Ventajas vs implementación actual de ScheduleAgent:
- Separación clara de responsabilidades (extracción vs validación vs respuesta)
- Estado compartido entre pasos
- Validaciones explícitas con logging
- Fácil agregar nuevos pasos (ej: verificar pagos, enviar confirmación)
- Debugging más sencillo (ver estado en cada paso)
"""

from __future__ import annotations
from typing import Dict, Any, List, Literal, TYPE_CHECKING
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import logging
import re
from datetime import datetime, timedelta

from app.langgraph_adapters.state_schemas import (
    ScheduleAgentState,
    create_initial_schedule_state
)

# Avoid circular import: ScheduleAgent imports ScheduleAgentGraph
if TYPE_CHECKING:
    from app.agents.schedule_agent import ScheduleAgent

logger = logging.getLogger(__name__)


class ScheduleAgentGraph:
    """
    Grafo de estado para ScheduleAgent.

    Permite ejecutar el flujo de agendamiento con validaciones
    paso a paso y gestión de estado explícita.

    Ejemplo de uso:
        schedule_agent = ScheduleAgent(company_config, openai_service)
        graph = ScheduleAgentGraph(schedule_agent)

        response = graph.get_response(
            question="Quiero agendar para mañana",
            user_id="user123",
            chat_history=[]
        )
    """

    def __init__(
        self,
        schedule_agent: ScheduleAgent,
        enable_checkpointing: bool = False
    ):
        """
        Inicializar grafo de agendamiento.

        Args:
            schedule_agent: Instancia de ScheduleAgent
            enable_checkpointing: Habilitar checkpointing para debugging
        """
        self.schedule_agent = schedule_agent
        self.company_id = schedule_agent.company_config.company_id
        self.enable_checkpointing = enable_checkpointing

        # Construir y compilar grafo
        self.graph = self._build_graph()
        checkpointer = MemorySaver() if enable_checkpointing else None
        self.app = self.graph.compile(checkpointer=checkpointer)

        logger.info(
            f"✅ ScheduleAgentGraph initialized for company {self.company_id}"
        )

    def _build_graph(self) -> StateGraph:
        """
        Construir grafo de agendamiento.

        Nodos:
        - extract_info: Extraer fecha, tratamiento, info de paciente
        - validate_info: Validar información extraída
        - check_availability: Verificar disponibilidad (opcional)
        - generate_response: Generar respuesta usando LLM del agent

        Edges:
        - START -> extract_info
        - extract_info -> validate_info
        - validate_info -> check_availability (si fecha válida)
        - validate_info -> generate_response (si solo pregunta sin agendar)
        - check_availability -> generate_response
        - generate_response -> END
        """
        workflow = StateGraph(ScheduleAgentState)

        # Agregar nodos
        workflow.add_node("extract_info", self._extract_info)
        workflow.add_node("validate_info", self._validate_info)
        workflow.add_node("check_availability", self._check_availability)
        workflow.add_node("generate_response", self._generate_response)

        # Entry point
        workflow.set_entry_point("extract_info")

        # Edges
        workflow.add_edge("extract_info", "validate_info")

        workflow.add_conditional_edges(
            "validate_info",
            self._should_check_availability,
            {
                "check": "check_availability",
                "skip": "generate_response"
            }
        )

        workflow.add_edge("check_availability", "generate_response")
        workflow.add_edge("generate_response", END)

        return workflow

    # === NODOS DEL GRAFO === #

    def _extract_info(self, state: ScheduleAgentState) -> ScheduleAgentState:
        """
        Extraer información relevante de la pregunta y historial.

        Extrae:
        - Fecha (DD-MM-YYYY o relativa: hoy, mañana, etc.)
        - Tratamiento (usando configuración de la empresa)
        - Información del paciente (nombre, cédula, etc.)
        """
        logger.info(f"[{self.company_id}] 📍 Node: extract_info")

        question = state["question"]
        chat_history = state.get("chat_history", [])

        # Extraer fecha
        extracted_date = self._extract_date(question, chat_history)
        if extracted_date:
            state["extracted_date"] = extracted_date
            logger.info(f"[{self.company_id}] Extracted date: {extracted_date}")

        # Extraer tratamiento
        extracted_treatment = self._extract_treatment(question)
        if extracted_treatment:
            state["extracted_treatment"] = extracted_treatment
            logger.info(f"[{self.company_id}] Extracted treatment: {extracted_treatment}")

        # Extraer info de paciente del historial
        patient_info = self._extract_patient_info(question, chat_history)
        if patient_info:
            state["extracted_patient_info"] = patient_info
            logger.info(
                f"[{self.company_id}] Extracted patient info: "
                f"{list(patient_info.keys())}"
            )

        state["current_step"] = "extract"
        return state

    def _validate_info(self, state: ScheduleAgentState) -> ScheduleAgentState:
        """
        Validar información extraída.

        Valida:
        - Fecha es válida y futura
        - Tratamiento existe en configuración
        - Información del paciente está completa
        """
        logger.info(f"[{self.company_id}] 📍 Node: validate_info")

        # Validar fecha
        if state.get("extracted_date"):
            try:
                date_obj = datetime.strptime(state["extracted_date"], "%d-%m-%Y")
                if date_obj >= datetime.now():
                    state["date_valid"] = True
                else:
                    state["date_valid"] = False
                    state["errors"].append("La fecha debe ser futura")
            except ValueError:
                state["date_valid"] = False
                state["errors"].append("Formato de fecha inválido")
        else:
            state["date_valid"] = False

        # Validar tratamiento
        if state.get("extracted_treatment"):
            # Verificar que el tratamiento existe en la configuración
            treatments = self.schedule_agent.company_config.treatment_durations
            if state["extracted_treatment"] in treatments:
                state["treatment_valid"] = True
            else:
                state["treatment_valid"] = False
                state["errors"].append("Tratamiento no reconocido")
        else:
            state["treatment_valid"] = False

        # Validar info de paciente
        required_fields = self._get_required_fields()
        state["required_fields"] = required_fields

        missing = []
        for field in required_fields:
            if field not in state["extracted_patient_info"]:
                missing.append(field)

        state["missing_fields"] = missing
        state["patient_info_complete"] = len(missing) == 0

        logger.info(
            f"[{self.company_id}] Validation results: "
            f"date_valid={state['date_valid']}, "
            f"treatment_valid={state['treatment_valid']}, "
            f"patient_complete={state['patient_info_complete']}"
        )

        state["current_step"] = "validate"
        return state

    def _check_availability(self, state: ScheduleAgentState) -> ScheduleAgentState:
        """
        Verificar disponibilidad de horarios.

        Llama al método del ScheduleAgent para verificar slots disponibles.
        """
        logger.info(f"[{self.company_id}] 📍 Node: check_availability")

        if not state["date_valid"] or not state["extracted_date"]:
            logger.warning(f"[{self.company_id}] Cannot check availability, date invalid")
            state["availability_checked"] = False
            return state

        date = state["extracted_date"]
        treatment = state.get("extracted_treatment", "consulta general")

        try:
            # Usar método del ScheduleAgent existente
            availability_data = self.schedule_agent._call_check_availability(
                date, treatment
            )

            if availability_data and availability_data.get("available_slots"):
                state["available_slots"] = availability_data["available_slots"]
                state["availability_checked"] = True
                logger.info(
                    f"[{self.company_id}] Found {len(state['available_slots'])} "
                    f"available slots"
                )
            else:
                state["available_slots"] = []
                state["availability_checked"] = True
                logger.info(f"[{self.company_id}] No available slots found")

        except Exception as e:
            logger.error(f"[{self.company_id}] Error checking availability: {e}")
            state["errors"].append(f"Error consultando disponibilidad: {str(e)}")
            state["availability_checked"] = False

        state["current_step"] = "availability"
        return state

    def _generate_response(self, state: ScheduleAgentState) -> ScheduleAgentState:
        """
        Generar respuesta usando el LLM del ScheduleAgent.

        Construye un contexto rico con:
        - Información extraída
        - Validaciones realizadas
        - Slots disponibles (si se verificaron)
        - Campos faltantes (si aplica)

        Luego delega al ScheduleAgent para generar la respuesta final.
        """
        logger.info(f"[{self.company_id}] 📍 Node: generate_response")

        # Construir contexto para el LLM
        context_parts = []

        # Información de validaciones
        if state["date_valid"] and state["extracted_date"]:
            context_parts.append(f"Fecha solicitada: {state['extracted_date']}")

        if state["treatment_valid"] and state["extracted_treatment"]:
            context_parts.append(f"Tratamiento: {state['extracted_treatment']}")

        # Disponibilidad
        if state["availability_checked"]:
            if state["available_slots"]:
                slots_text = ", ".join(state["available_slots"][:5])
                context_parts.append(f"Horarios disponibles: {slots_text}")
            else:
                context_parts.append("No hay horarios disponibles para esa fecha")

        # Campos faltantes
        if not state["patient_info_complete"]:
            missing = ", ".join(state["missing_fields"])
            context_parts.append(f"Información faltante: {missing}")

        # Errores
        if state["errors"]:
            context_parts.append(f"Errores: {'; '.join(state['errors'])}")

        schedule_context = "\n".join(context_parts)

        # Preparar inputs para el ScheduleAgent
        inputs = {
            "question": state["question"],
            "chat_history": state.get("chat_history", []),
            "context": schedule_context,
            "user_id": state["user_id"],
            "company_id": state["company_id"]
        }

        try:
            # ✅ IMPORTANTE: Llamar directamente al chain para evitar loop de recursión
            # NO usar invoke() porque ese método llama de vuelta al grafo
            if hasattr(self.schedule_agent, 'chain') and self.schedule_agent.chain:
                response = self.schedule_agent.chain.invoke(inputs)
            else:
                # Fallback: usar hybrid_schedule_processor directamente
                response = self.schedule_agent.hybrid_schedule_processor(
                    question=inputs["question"],
                    chat_history=inputs.get("chat_history", []),
                    additional_context=inputs.get("context", "")
                )

            state["agent_response"] = response

            logger.info(
                f"[{self.company_id}] Response generated ({len(response)} chars)"
            )

        except Exception as e:
            logger.error(f"[{self.company_id}] Error generating response: {e}")
            state["errors"].append(f"Error generando respuesta: {str(e)}")
            state["agent_response"] = (
                f"Lo siento, tuve un problema al procesar tu solicitud de "
                f"agendamiento en {self.schedule_agent.company_config.company_name}. "
                f"Por favor, contacta directamente con nosotros."
            )

        state["current_step"] = "respond"
        return state

    # === FUNCIONES DE ROUTING === #

    def _should_check_availability(
        self,
        state: ScheduleAgentState
    ) -> Literal["check", "skip"]:
        """
        Determinar si verificar disponibilidad.

        Solo verificar si:
        - Fecha es válida
        - Tratamiento es válido
        - Usuario parece querer agendar (no solo pregunta)
        """
        if not state["date_valid"]:
            return "skip"

        # Si el usuario solo pregunta, no verificar disponibilidad
        question_lower = state["question"].lower()
        is_just_asking = any(word in question_lower for word in [
            "cuánto cuesta", "precio", "información", "qué es", "en qué consiste"
        ])

        if is_just_asking:
            return "skip"

        # Si tiene fecha y tratamiento válidos, verificar
        if state["treatment_valid"]:
            return "check"

        return "skip"

    # === HELPERS DE EXTRACCIÓN === #

    def _extract_date(
        self,
        question: str,
        chat_history: List[Any]
    ) -> str | None:
        """
        Extraer fecha de la pregunta.

        Usa el método existente del ScheduleAgent.
        """
        return self.schedule_agent._extract_date_from_question(question, chat_history)

    def _extract_treatment(self, question: str) -> str | None:
        """
        Extraer tratamiento de la pregunta.

        Usa el método existente del ScheduleAgent.
        """
        return self.schedule_agent._extract_treatment_from_question(question)

    def _extract_patient_info(
        self,
        question: str,
        chat_history: List[Any]
    ) -> Dict[str, Any]:
        """
        Extraer información del paciente del historial.

        Usa los métodos existentes del ScheduleAgent.
        """
        history_text = " ".join([
            msg.content if hasattr(msg, "content") else str(msg)
            for msg in chat_history
        ])
        history_text += " " + question

        info = {}

        # Nombre
        name = self.schedule_agent._extract_name(history_text.lower())
        if name:
            info["nombre"] = name

        # Cédula
        cedula = self.schedule_agent._extract_cedula(history_text.lower())
        if cedula:
            info["cedula"] = cedula

        # Email
        email = self.schedule_agent._extract_email(history_text.lower())
        if email:
            info["email"] = email

        # Teléfono
        phone = self.schedule_agent._extract_phone(history_text.lower())
        if phone:
            info["telefono"] = phone

        return info

    def _get_required_fields(self) -> List[str]:
        """
        Obtener campos requeridos para agendamiento.

        Usa la configuración del ScheduleAgent.
        """
        if hasattr(self.schedule_agent.company_config, "required_booking_fields"):
            return self.schedule_agent.company_config.required_booking_fields

        return ["nombre", "cedula", "email", "telefono"]

    # === API PÚBLICA === #

    def get_response(
        self,
        question: str,
        user_id: str,
        chat_history: List[Any] = None
    ) -> str:
        """
        Obtener respuesta del grafo de agendamiento.

        ✅ COMPATIBLE CON API EXISTENTE

        Args:
            question: Pregunta del usuario
            user_id: ID del usuario
            chat_history: Historial de conversación

        Returns:
            Respuesta generada
        """
        logger.info(f"[{self.company_id}] 🚀 ScheduleAgentGraph.get_response()")

        # Crear estado inicial
        initial_state = create_initial_schedule_state(
            question=question,
            user_id=user_id,
            company_id=self.company_id,
            chat_history=chat_history or []
        )

        # Ejecutar grafo
        try:
            final_state = self.app.invoke(initial_state)

            # Retornar respuesta
            response = final_state.get("agent_response", "")

            if not response:
                response = (
                    f"Lo siento, tuve un problema procesando tu solicitud de "
                    f"agendamiento en {self.schedule_agent.company_config.company_name}."
                )

            logger.info(
                f"[{self.company_id}] ✅ Schedule response generated "
                f"({len(response)} chars, current_step={final_state['current_step']})"
            )

            return response

        except Exception as e:
            logger.exception(f"[{self.company_id}] Error executing schedule graph: {e}")
            return (
                f"Lo siento, estoy experimentando dificultades técnicas con el "
                f"sistema de agendamiento de {self.schedule_agent.company_config.company_name}. "
                f"Por favor, intenta de nuevo más tarde."
            )
