"""
Compensation Orchestrator - Sistema de Compensación para Rollback

Implementa el patrón Saga/Compensating Transactions para revertir
acciones fallidas de forma automática.

Características:
- Rollback automático de acciones compensables
- Patrón Saga para transacciones distribuidas
- Integración con AuditManager
- Ejecución asíncrona de compensaciones
- Retry con backoff exponencial

Patrón Saga:
1. Ejecutar acción principal → Registrar en audit trail
2. Si falla → Compensar acciones previas en orden inverso
3. Si todo funciona → Marcar saga como completada

Ejemplo:
    # Saga: Crear cita + Enviar confirmación
    orchestrator = CompensationOrchestrator(company_id="benova")

    saga = orchestrator.create_saga(
        user_id="user123",
        saga_name="book_appointment"
    )

    # Acción 1: Crear evento en Google Calendar
    orchestrator.add_action(
        saga_id=saga.saga_id,
        action_type="booking",
        action_name="google_calendar.create_event",
        executor=lambda: calendar_service.create_event(...),
        compensator=lambda result: calendar_service.delete_event(result["event_id"])
    )

    # Acción 2: Enviar email de confirmación
    orchestrator.add_action(
        saga_id=saga.saga_id,
        action_type="notification",
        action_name="email.send_confirmation",
        executor=lambda: email_service.send_email(...),
        compensator=None  # Email no se puede "desenviar"
    )

    # Ejecutar saga
    result = orchestrator.execute_saga(saga.saga_id)

    if not result["success"]:
        # Automáticamente compensó todas las acciones
        print(f"Saga failed and rolled back: {result['error']}")
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging
import uuid
import time
from enum import Enum

from app.models.audit_trail import AuditManager, AuditEntry

logger = logging.getLogger(__name__)


class SagaStatus(Enum):
    """Estados de una Saga"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"


@dataclass
class SagaAction:
    """
    Acción individual dentro de una Saga.

    Cada acción tiene:
    - executor: Función que ejecuta la acción
    - compensator: Función que revierte la acción (opcional)
    - audit_id: ID de la entrada de auditoría
    """
    action_id: str
    action_type: str
    action_name: str
    executor: Callable[[], Dict[str, Any]]
    compensator: Optional[Callable[[Any], Dict[str, Any]]] = None
    input_params: Dict[str, Any] = field(default_factory=dict)

    # Estado de ejecución
    executed: bool = False
    execution_result: Optional[Dict[str, Any]] = None
    audit_id: Optional[str] = None

    # Estado de compensación
    compensated: bool = False
    compensation_result: Optional[Dict[str, Any]] = None


@dataclass
class Saga:
    """
    Saga - Secuencia de acciones compensables.

    Una saga agrupa múltiples acciones que deben ejecutarse
    como una unidad lógica. Si alguna falla, todas las
    acciones previas se compensan (rollback).
    """
    saga_id: str
    company_id: str
    user_id: str
    saga_name: str
    actions: List[SagaAction] = field(default_factory=list)

    status: SagaStatus = SagaStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None

    # Resultados
    success: bool = False
    error_message: Optional[str] = None
    failed_action_index: Optional[int] = None


class CompensationOrchestrator:
    """
    Orquestador de compensaciones usando patrón Saga.

    Coordina la ejecución de acciones y su compensación
    automática en caso de errores.

    Ejemplo de uso:
        orchestrator = CompensationOrchestrator(
            company_id="benova",
            audit_manager=audit_manager
        )

        # Crear saga
        saga = orchestrator.create_saga(
            user_id="user123",
            saga_name="create_appointment_with_notifications"
        )

        # Agregar acciones
        orchestrator.add_action(
            saga_id=saga.saga_id,
            action_type="booking",
            action_name="create_calendar_event",
            executor=create_event_func,
            compensator=delete_event_func,
            input_params={"treatment": "toxina", "date": "2025-10-26"}
        )

        # Ejecutar
        result = orchestrator.execute_saga(saga.saga_id)
    """

    def __init__(
        self,
        company_id: str,
        audit_manager: Optional[AuditManager] = None,
        max_retries: int = 3,
        retry_delay: int = 2
    ):
        """
        Inicializar orquestador de compensación.

        Args:
            company_id: ID de la empresa
            audit_manager: Gestor de auditoría (opcional, se crea si no se provee)
            max_retries: Máximo de reintentos por acción
            retry_delay: Segundos entre reintentos
        """
        self.company_id = company_id
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # AuditManager para trazabilidad
        self.audit_manager = audit_manager or AuditManager(company_id=company_id)

        # Sagas activas en memoria
        self._sagas: Dict[str, Saga] = {}

        logger.info(
            f"✅ CompensationOrchestrator initialized for {company_id} "
            f"(max_retries={max_retries})"
        )

    def create_saga(
        self,
        user_id: str,
        saga_name: str,
        conversation_id: Optional[str] = None
    ) -> Saga:
        """
        Crear una nueva saga.

        Args:
            user_id: ID del usuario
            saga_name: Nombre descriptivo de la saga
            conversation_id: ID de conversación (opcional)

        Returns:
            Saga creada
        """
        saga_id = str(uuid.uuid4())

        saga = Saga(
            saga_id=saga_id,
            company_id=self.company_id,
            user_id=user_id,
            saga_name=saga_name
        )

        self._sagas[saga_id] = saga

        logger.info(
            f"🔄 [{self.company_id}] Saga created: {saga_name} "
            f"(id={saga_id[:8]}, user={user_id})"
        )

        return saga

    def add_action(
        self,
        saga_id: str,
        action_type: str,
        action_name: str,
        executor: Callable[[], Dict[str, Any]],
        compensator: Optional[Callable[[Any], Dict[str, Any]]] = None,
        input_params: Dict[str, Any] = None
    ) -> bool:
        """
        Agregar una acción a una saga.

        Args:
            saga_id: ID de la saga
            action_type: Tipo de acción (booking, notification, etc.)
            action_name: Nombre de la acción
            executor: Función que ejecuta la acción
            compensator: Función que compensa/revierte (opcional)
            input_params: Parámetros de entrada

        Returns:
            True si se agregó correctamente
        """
        saga = self._sagas.get(saga_id)
        if not saga:
            logger.error(f"[{self.company_id}] Saga not found: {saga_id}")
            return False

        if saga.status != SagaStatus.PENDING:
            logger.error(
                f"[{self.company_id}] Cannot add actions to saga in status: {saga.status}"
            )
            return False

        action_id = str(uuid.uuid4())

        action = SagaAction(
            action_id=action_id,
            action_type=action_type,
            action_name=action_name,
            executor=executor,
            compensator=compensator,
            input_params=input_params or {}
        )

        saga.actions.append(action)

        logger.info(
            f"   ➕ [{self.company_id}] Action added to saga {saga_id[:8]}: "
            f"{action_type}/{action_name} (compensable={compensator is not None})"
        )

        return True

    def execute_saga(self, saga_id: str) -> Dict[str, Any]:
        """
        Ejecutar una saga completa.

        Ejecuta todas las acciones en secuencia. Si alguna falla,
        compensa (rollback) todas las acciones previas ejecutadas.

        Args:
            saga_id: ID de la saga

        Returns:
            Dict con resultado:
            {
                "success": bool,
                "saga_id": str,
                "actions_executed": int,
                "actions_compensated": int,
                "error": Optional[str]
            }
        """
        saga = self._sagas.get(saga_id)
        if not saga:
            return {
                "success": False,
                "error": f"Saga not found: {saga_id}"
            }

        logger.info(
            f"🚀 [{self.company_id}] Executing saga: {saga.saga_name} "
            f"({len(saga.actions)} actions)"
        )

        saga.status = SagaStatus.IN_PROGRESS

        # Ejecutar acciones en secuencia
        for index, action in enumerate(saga.actions):
            logger.info(
                f"   ▶️  [{self.company_id}] Executing action {index + 1}/{len(saga.actions)}: "
                f"{action.action_type}/{action.action_name}"
            )

            # Registrar en audit trail ANTES de ejecutar
            audit_entry = self.audit_manager.log_action(
                user_id=saga.user_id,
                action_type=action.action_type,
                action_name=action.action_name,
                input_params=action.input_params,
                compensable=action.compensator is not None,
                compensation_action=f"{action.action_name}.compensate" if action.compensator else None,
                tags=[f"saga:{saga.saga_name}", f"saga_id:{saga_id}"]
            )

            action.audit_id = audit_entry.audit_id

            # Ejecutar acción con reintentos
            execution_result = self._execute_action_with_retry(action)

            if execution_result["success"]:
                # Marcar como exitosa en audit trail
                self.audit_manager.mark_success(
                    audit_entry.audit_id,
                    result=execution_result.get("data"),
                    duration_ms=execution_result.get("duration_ms")
                )

                action.executed = True
                action.execution_result = execution_result

                logger.info(
                    f"   ✅ [{self.company_id}] Action {index + 1} completed successfully"
                )

            else:
                # Acción falló
                error_message = execution_result.get("error", "Unknown error")

                # Marcar como fallida en audit trail
                self.audit_manager.mark_failed(
                    audit_entry.audit_id,
                    error_message=error_message,
                    duration_ms=execution_result.get("duration_ms")
                )

                logger.error(
                    f"   ❌ [{self.company_id}] Action {index + 1} failed: {error_message}"
                )

                # Marcar saga como fallida
                saga.status = SagaStatus.FAILED
                saga.error_message = error_message
                saga.failed_action_index = index

                # COMPENSAR todas las acciones previas ejecutadas
                logger.warning(
                    f"🔄 [{self.company_id}] Starting compensation (rollback) of {index} actions"
                )

                compensation_result = self._compensate_saga(saga, up_to_index=index)

                saga.status = SagaStatus.COMPENSATED
                saga.completed_at = datetime.utcnow().isoformat()

                return {
                    "success": False,
                    "saga_id": saga_id,
                    "saga_name": saga.saga_name,
                    "actions_executed": index,
                    "actions_compensated": compensation_result["compensated_count"],
                    "failed_action": action.action_name,
                    "error": error_message
                }

        # Todas las acciones se ejecutaron exitosamente
        saga.status = SagaStatus.COMPLETED
        saga.success = True
        saga.completed_at = datetime.utcnow().isoformat()

        logger.info(
            f"✅ [{self.company_id}] Saga completed successfully: {saga.saga_name} "
            f"({len(saga.actions)} actions)"
        )

        return {
            "success": True,
            "saga_id": saga_id,
            "saga_name": saga.saga_name,
            "actions_executed": len(saga.actions),
            "actions_compensated": 0
        }

    def compensate_saga(self, saga_id: str, reason: str = "Manual compensation") -> Dict[str, Any]:
        """
        Compensar manualmente una saga completada.

        Args:
            saga_id: ID de la saga
            reason: Razón de la compensación

        Returns:
            Resultado de la compensación
        """
        saga = self._sagas.get(saga_id)
        if not saga:
            return {
                "success": False,
                "error": f"Saga not found: {saga_id}"
            }

        if saga.status not in [SagaStatus.COMPLETED, SagaStatus.FAILED]:
            return {
                "success": False,
                "error": f"Cannot compensate saga in status: {saga.status}"
            }

        logger.info(
            f"🔄 [{self.company_id}] Manually compensating saga: {saga.saga_name} - {reason}"
        )

        result = self._compensate_saga(saga, reason=reason)

        saga.status = SagaStatus.COMPENSATED
        saga.completed_at = datetime.utcnow().isoformat()

        return result

    def _execute_action_with_retry(self, action: SagaAction) -> Dict[str, Any]:
        """Ejecutar acción con reintentos"""
        start_time = time.time()
        last_error = None

        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    wait_time = self.retry_delay * (2 ** (attempt - 1))
                    logger.info(
                        f"      Retry {attempt}/{self.max_retries - 1} "
                        f"after {wait_time}s..."
                    )
                    time.sleep(wait_time)

                # Ejecutar función
                result = action.executor()

                duration_ms = (time.time() - start_time) * 1000

                # Validar resultado
                if isinstance(result, dict):
                    if result.get("success", True):
                        return {
                            "success": True,
                            "data": result,
                            "duration_ms": duration_ms,
                            "attempts": attempt + 1
                        }
                    else:
                        last_error = result.get("error", "Action returned success=False")
                else:
                    # Resultado no es dict, asumimos éxito
                    return {
                        "success": True,
                        "data": result,
                        "duration_ms": duration_ms,
                        "attempts": attempt + 1
                    }

            except Exception as e:
                last_error = str(e)
                logger.error(f"      Action execution error (attempt {attempt + 1}): {e}")

        # Todos los intentos fallaron
        duration_ms = (time.time() - start_time) * 1000

        return {
            "success": False,
            "error": last_error,
            "duration_ms": duration_ms,
            "attempts": self.max_retries
        }

    def _compensate_saga(
        self,
        saga: Saga,
        up_to_index: Optional[int] = None,
        reason: str = "Saga failed"
    ) -> Dict[str, Any]:
        """
        Compensar (rollback) acciones de una saga.

        Args:
            saga: Saga a compensar
            up_to_index: Compensar hasta este índice (None = todas)
            reason: Razón de la compensación

        Returns:
            Resultado de la compensación
        """
        saga.status = SagaStatus.COMPENSATING

        if up_to_index is None:
            up_to_index = len(saga.actions)

        # Compensar en orden INVERSO
        compensated_count = 0
        failed_compensations = []

        for index in range(up_to_index - 1, -1, -1):
            action = saga.actions[index]

            if not action.executed:
                continue

            if not action.compensator:
                logger.info(
                    f"   ⚠️  [{self.company_id}] Action {index + 1} is not compensable: "
                    f"{action.action_name}"
                )
                continue

            logger.info(
                f"   🔄 [{self.company_id}] Compensating action {index + 1}: "
                f"{action.action_name}"
            )

            try:
                # Ejecutar compensador
                compensation_result = action.compensator(action.execution_result)

                action.compensated = True
                action.compensation_result = compensation_result

                # Marcar en audit trail
                if action.audit_id:
                    self.audit_manager.compensate(
                        action.audit_id,
                        reason=reason,
                        compensated_by="CompensationOrchestrator"
                    )

                compensated_count += 1

                logger.info(
                    f"   ✅ [{self.company_id}] Action {index + 1} compensated successfully"
                )

            except Exception as e:
                logger.error(
                    f"   ❌ [{self.company_id}] Compensation failed for action {index + 1}: {e}"
                )
                failed_compensations.append({
                    "action_index": index,
                    "action_name": action.action_name,
                    "error": str(e)
                })

        logger.info(
            f"🔄 [{self.company_id}] Compensation completed: "
            f"{compensated_count} actions rolled back, "
            f"{len(failed_compensations)} failed"
        )

        return {
            "success": len(failed_compensations) == 0,
            "compensated_count": compensated_count,
            "failed_compensations": failed_compensations
        }

    def get_saga(self, saga_id: str) -> Optional[Saga]:
        """Obtener una saga por ID"""
        return self._sagas.get(saga_id)

    def get_sagas_by_user(self, user_id: str) -> List[Saga]:
        """Obtener todas las sagas de un usuario"""
        return [
            saga for saga in self._sagas.values()
            if saga.user_id == user_id
        ]

    def get_failed_sagas(self) -> List[Saga]:
        """Obtener sagas fallidas"""
        return [
            saga for saga in self._sagas.values()
            if saga.status == SagaStatus.FAILED
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas de compensaciones"""
        total_sagas = len(self._sagas)
        by_status = {}

        for status in SagaStatus:
            count = len([s for s in self._sagas.values() if s.status == status])
            by_status[status.value] = count

        return {
            "company_id": self.company_id,
            "total_sagas": total_sagas,
            "by_status": by_status
        }
