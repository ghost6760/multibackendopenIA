"""
Esquemas de Estado para LangGraph

Define las estructuras de estado compartido entre nodos del grafo.
Estos estados son mutables y se pasan entre nodos en el flujo.

Principios de diseño:
- TypedDict para typing estricto
- Anotaciones para reducers personalizados
- Compatibilidad con checkpointing
"""

from typing import TypedDict, List, Dict, Any, Optional, Annotated
from typing_extensions import TypedDict as TypedDictExtended
from datetime import datetime
import operator


class ValidationResult(TypedDict):
    """Resultado de validación de un paso"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]


class AgentExecutionState(TypedDict):
    """Estado de ejecución de un agente individual"""
    agent_name: str
    started_at: str
    completed_at: Optional[str]
    duration_ms: Optional[float]
    retries: int
    status: str  # 'pending', 'running', 'success', 'failed'
    error: Optional[str]
    output: Optional[str]


class OrchestratorState(TypedDict):
    """
    Estado compartido del orquestador multi-agente.

    Este estado se pasa entre todos los nodos del grafo y se modifica
    a medida que avanza el flujo.

    Campos:
    - question: Pregunta del usuario (inmutable)
    - user_id: ID del usuario (inmutable)
    - company_id: ID de la empresa (inmutable)
    - chat_history: Historial de conversación
    - context: Contexto adicional (RAG, etc.)
    - intent: Intención clasificada (SALES, SUPPORT, EMERGENCY, SCHEDULE)
    - confidence: Confianza de la clasificación (0.0-1.0)
    - current_agent: Agente actualmente ejecutándose
    - agent_response: Respuesta del agente ejecutado
    - validations: Lista de validaciones realizadas
    - executions: Historial de ejecuciones de agentes
    - retries: Contador de reintentos
    - errors: Lista de errores ocurridos
    - metadata: Metadatos adicionales
    """

    # === Entradas inmutables === #
    question: str
    user_id: str
    company_id: str

    # === Contexto y historial === #
    chat_history: List[Any]
    context: str

    # === Clasificación de intención === #
    intent: Optional[str]
    confidence: float
    intent_keywords: List[str]

    # === Intención secundaria (detección mid-conversation) === #
    secondary_intent: Optional[str]
    secondary_confidence: float

    # === Estado de ejecución === #
    current_agent: Optional[str]
    agent_response: Optional[str]

    # === Shared context entre agentes === #
    shared_context: Dict[str, Any]  # Contexto compartido (pricing, schedule, etc.)

    # === Handoff entre agentes === #
    handoff_requested: bool
    handoff_from: Optional[str]
    handoff_to: Optional[str]
    handoff_reason: Optional[str]
    handoff_context: Dict[str, Any]
    handoff_completed: bool  # Prevenir handoffs múltiples

    # === Validaciones === #
    validations: Annotated[List[ValidationResult], operator.add]

    # === Historial de ejecución === #
    executions: Annotated[List[AgentExecutionState], operator.add]

    # === Control de flujo === #
    retries: int
    should_retry: bool
    should_escalate: bool

    # === Errores === #
    errors: Annotated[List[str], operator.add]

    # === Metadata === #
    metadata: Dict[str, Any]
    started_at: str
    completed_at: Optional[str]


class ScheduleAgentState(TypedDict):
    """
    Estado específico para el ScheduleAgent con grafo interno.

    Este estado gestiona el flujo de agendamiento con validaciones
    y verificaciones paso a paso.
    """

    # === Entrada === #
    question: str
    user_id: str
    company_id: str
    chat_history: List[Any]

    # === Información extraída === #
    extracted_date: Optional[str]
    extracted_treatment: Optional[str]
    extracted_patient_info: Dict[str, Any]

    # === Validaciones === #
    date_valid: bool
    treatment_valid: bool
    patient_info_complete: bool
    required_fields: List[str]
    missing_fields: List[str]

    # === Disponibilidad === #
    availability_checked: bool
    available_slots: List[str]
    selected_slot: Optional[str]

    # === Reserva === #
    booking_attempted: bool
    booking_success: bool
    booking_id: Optional[str]
    booking_error: Optional[str]

    # === Respuesta === #
    agent_response: str

    # === Control === #
    current_step: str  # 'extract', 'validate', 'availability', 'book', 'respond'
    retries: int
    errors: Annotated[List[str], operator.add]

    # === Metadata === #
    metadata: Dict[str, Any]


def create_initial_orchestrator_state(
    question: str,
    user_id: str,
    company_id: str,
    chat_history: List[Any] = None,
    context: str = ""
) -> OrchestratorState:
    """
    Crear estado inicial del orquestador.

    Función helper para inicializar el estado con valores por defecto.
    """
    return {
        # Entradas
        "question": question,
        "user_id": user_id,
        "company_id": company_id,

        # Contexto
        "chat_history": chat_history or [],
        "context": context,

        # Clasificación
        "intent": None,
        "confidence": 0.0,
        "intent_keywords": [],

        # Intención secundaria
        "secondary_intent": None,
        "secondary_confidence": 0.0,

        # Ejecución
        "current_agent": None,
        "agent_response": None,

        # Shared context
        "shared_context": {},

        # Handoff
        "handoff_requested": False,
        "handoff_from": None,
        "handoff_to": None,
        "handoff_reason": None,
        "handoff_context": {},
        "handoff_completed": False,

        # Validaciones
        "validations": [],

        # Historial
        "executions": [],

        # Control
        "retries": 0,
        "should_retry": False,
        "should_escalate": False,

        # Errores
        "errors": [],

        # Metadata
        "metadata": {},
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": None
    }


def create_initial_schedule_state(
    question: str,
    user_id: str,
    company_id: str,
    chat_history: List[Any] = None
) -> ScheduleAgentState:
    """
    Crear estado inicial para ScheduleAgent.
    """
    return {
        # Entrada
        "question": question,
        "user_id": user_id,
        "company_id": company_id,
        "chat_history": chat_history or [],

        # Información extraída
        "extracted_date": None,
        "extracted_treatment": None,
        "extracted_patient_info": {},

        # Validaciones
        "date_valid": False,
        "treatment_valid": False,
        "patient_info_complete": False,
        "required_fields": [],
        "missing_fields": [],

        # Disponibilidad
        "availability_checked": False,
        "available_slots": [],
        "selected_slot": None,

        # Reserva
        "booking_attempted": False,
        "booking_success": False,
        "booking_id": None,
        "booking_error": None,

        # Respuesta
        "agent_response": "",

        # Control
        "current_step": "extract",
        "retries": 0,
        "errors": [],

        # Metadata
        "metadata": {}
    }
