# app/services/agent_state_manager.py

"""
Manager de estado para agentes cognitivos.
Proporciona persistencia, reentrancia y debugging de estado de ejecución.

Este servicio permite:
- Guardar estado intermedio de agentes durante ejecución
- Recuperar estado para reentrancia (continuar ejecución interrumpida)
- Debugging detallado del flujo de razonamiento
- Telemetría y analytics por agente/usuario
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json
import logging
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS Y TIPOS
# ============================================================================

class ExecutionStatus(Enum):
    """Estados de ejecución"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class StateSnapshot:
    """Snapshot de estado en un punto del tiempo"""
    execution_id: str
    agent_name: str
    user_id: str
    company_id: str
    step_number: int
    timestamp: str
    state_data: Dict[str, Any]
    status: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StateSnapshot':
        """Crear desde diccionario"""
        return cls(**data)


# ============================================================================
# CLASE PRINCIPAL
# ============================================================================

class AgentStateManager:
    """
    Manager de estado para agentes cognitivos.
    
    Proporciona persistencia en memoria (con opción de Redis/PostgreSQL).
    Para producción, se recomienda usar Redis para estado temporal y
    PostgreSQL para histórico.
    """
    
    def __init__(self, redis_service=None, use_persistence: bool = False):
        """
        Args:
            redis_service: Servicio de Redis (opcional, para persistencia)
            use_persistence: Si usar persistencia real o solo memoria
        """
        self.redis_service = redis_service
        self.use_persistence = use_persistence
        
        # Estado en memoria (fallback)
        self._memory_store: Dict[str, List[StateSnapshot]] = {}
        self._active_executions: Dict[str, Dict[str, Any]] = {}
        
        logger.info(
            f"AgentStateManager initialized "
            f"(persistence={'enabled' if use_persistence else 'disabled'})"
        )
    
    # === GESTIÓN DE EJECUCIONES === #
    
    def start_execution(
        self,
        agent_name: str,
        user_id: str,
        company_id: str,
        initial_state: Dict[str, Any]
    ) -> str:
        """
        Iniciar nueva ejecución y obtener execution_id.
        
        Args:
            agent_name: Nombre del agente
            user_id: ID del usuario
            company_id: ID de la empresa
            initial_state: Estado inicial
        
        Returns:
            execution_id único
        """
        # Generar execution_id único
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        execution_id = f"{agent_name}_{user_id}_{timestamp}"
        
        # Crear registro de ejecución
        execution_record = {
            "execution_id": execution_id,
            "agent_name": agent_name,
            "user_id": user_id,
            "company_id": company_id,
            "status": ExecutionStatus.IN_PROGRESS.value,
            "started_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
            "step_count": 0,
            "initial_state": initial_state
        }
        
        # Guardar en active executions
        self._active_executions[execution_id] = execution_record
        
        # Persistir si está habilitado
        if self.use_persistence and self.redis_service:
            try:
                self.redis_service.set(
                    f"agent_execution:{execution_id}",
                    json.dumps(execution_record),
                    ex=3600  # 1 hora de expiración
                )
            except Exception as e:
                logger.error(f"Error persisting execution: {e}")
        
        logger.info(
            f"[{agent_name}] Execution started: {execution_id} "
            f"(user={user_id}, company={company_id})"
        )
        
        return execution_id
    
    def complete_execution(
        self,
        execution_id: str,
        final_state: Dict[str, Any],
        status: ExecutionStatus = ExecutionStatus.COMPLETED
    ):
        """
        Completar ejecución.
        
        Args:
            execution_id: ID de ejecución
            final_state: Estado final
            status: Estado final (COMPLETED, FAILED, etc.)
        """
        if execution_id not in self._active_executions:
            logger.warning(f"Execution not found: {execution_id}")
            return
        
        execution = self._active_executions[execution_id]
        execution["status"] = status.value
        execution["completed_at"] = datetime.utcnow().isoformat()
        execution["final_state"] = final_state
        
        # Persistir actualización
        if self.use_persistence and self.redis_service:
            try:
                self.redis_service.set(
                    f"agent_execution:{execution_id}",
                    json.dumps(execution),
                    ex=86400  # 24 horas para execuciones completadas
                )
            except Exception as e:
                logger.error(f"Error updating execution: {e}")
        
        # Mover a histórico
        del self._active_executions[execution_id]
        
        logger.info(
            f"[{execution['agent_name']}] Execution completed: {execution_id} "
            f"(status={status.value})"
        )
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtener estado de una ejecución.
        
        Args:
            execution_id: ID de ejecución
        
        Returns:
            Dict con estado o None
        """
        # Buscar en activas
        if execution_id in self._active_executions:
            return self._active_executions[execution_id]
        
        # Buscar en persistencia
        if self.use_persistence and self.redis_service:
            try:
                data = self.redis_service.get(f"agent_execution:{execution_id}")
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.error(f"Error retrieving execution: {e}")
        
        return None
    
    # === PERSISTENCIA DE ESTADO === #
    
    def save_state_snapshot(
        self,
        execution_id: str,
        agent_name: str,
        user_id: str,
        company_id: str,
        state: Dict[str, Any],
        step_number: int,
        status: ExecutionStatus = ExecutionStatus.IN_PROGRESS
    ):
        """
        Guardar snapshot de estado.
        
        Args:
            execution_id: ID de ejecución
            agent_name: Nombre del agente
            user_id: ID del usuario
            company_id: ID de la empresa
            state: Estado actual completo
            step_number: Número de paso
            status: Estado de ejecución
        """
        snapshot = StateSnapshot(
            execution_id=execution_id,
            agent_name=agent_name,
            user_id=user_id,
            company_id=company_id,
            step_number=step_number,
            timestamp=datetime.utcnow().isoformat(),
            state_data=state,
            status=status.value
        )
        
        # Guardar en memoria
        if execution_id not in self._memory_store:
            self._memory_store[execution_id] = []
        
        self._memory_store[execution_id].append(snapshot)
        
        # Limitar snapshots en memoria (solo últimos 20)
        if len(self._memory_store[execution_id]) > 20:
            self._memory_store[execution_id] = self._memory_store[execution_id][-20:]
        
        # Persistir si está habilitado
        if self.use_persistence and self.redis_service:
            try:
                key = f"agent_state:{execution_id}:step_{step_number}"
                self.redis_service.set(
                    key,
                    json.dumps(snapshot.to_dict()),
                    ex=3600  # 1 hora
                )
            except Exception as e:
                logger.error(f"Error persisting snapshot: {e}")
        
        # Actualizar contador de pasos
        if execution_id in self._active_executions:
            self._active_executions[execution_id]["step_count"] = step_number
            self._active_executions[execution_id]["last_updated"] = datetime.utcnow().isoformat()
        
        logger.debug(
            f"[{agent_name}] State snapshot saved: "
            f"execution={execution_id}, step={step_number}"
        )
    
    def get_latest_state(self, execution_id: str) -> Optional[StateSnapshot]:
        """
        Obtener último snapshot de estado.
        
        Args:
            execution_id: ID de ejecución
        
        Returns:
            StateSnapshot más reciente o None
        """
        # Buscar en memoria
        if execution_id in self._memory_store:
            snapshots = self._memory_store[execution_id]
            if snapshots:
                return snapshots[-1]
        
        # Buscar en persistencia
        if self.use_persistence and self.redis_service:
            try:
                execution = self.get_execution_status(execution_id)
                if execution:
                    step_count = execution.get("step_count", 0)
                    key = f"agent_state:{execution_id}:step_{step_count}"
                    data = self.redis_service.get(key)
                    if data:
                        return StateSnapshot.from_dict(json.loads(data))
            except Exception as e:
                logger.error(f"Error retrieving latest state: {e}")
        
        return None
    
    def get_state_history(
        self,
        execution_id: str,
        limit: int = 10
    ) -> List[StateSnapshot]:
        """
        Obtener historial de estados.
        
        Args:
            execution_id: ID de ejecución
            limit: Máximo de snapshots a retornar
        
        Returns:
            Lista de StateSnapshot
        """
        # Obtener de memoria
        if execution_id in self._memory_store:
            snapshots = self._memory_store[execution_id]
            return snapshots[-limit:]
        
        return []
    
    # === REGISTRO DE PASOS DE RAZONAMIENTO === #
    
    def record_step(
        self,
        agent_name: str,
        user_id: str,
        step: Dict[str, Any]
    ):
        """
        Registrar paso de razonamiento (para telemetría).
        
        Args:
            agent_name: Nombre del agente
            user_id: ID del usuario
            step: Dict con información del paso
        """
        logger.debug(
            f"[{agent_name}] Reasoning step: "
            f"user={user_id}, step={step.get('step_number')}, "
            f"thought='{step.get('thought', '')[:50]}...'"
        )
    
    def record_tool_execution(
        self,
        agent_name: str,
        user_id: str,
        tool_record: Dict[str, Any]
    ):
        """
        Registrar ejecución de herramienta (para telemetría).
        
        Args:
            agent_name: Nombre del agente
            user_id: ID del usuario
            tool_record: Dict con información de la tool
        """
        logger.info(
            f"[{agent_name}] Tool executed: "
            f"user={user_id}, tool={tool_record.get('tool_name')}, "
            f"success={tool_record.get('success')}, "
            f"latency={tool_record.get('latency_ms')}ms"
        )
    
    # === REENTRANCIA (CONTINUAR EJECUCIÓN) === #
    
    def can_resume_execution(self, execution_id: str) -> bool:
        """
        Verificar si una ejecución puede resumirse.
        
        Args:
            execution_id: ID de ejecución
        
        Returns:
            True si puede resumirse
        """
        execution = self.get_execution_status(execution_id)
        
        if not execution:
            return False
        
        status = execution.get("status")
        if status not in [
            ExecutionStatus.IN_PROGRESS.value,
            ExecutionStatus.PENDING.value
        ]:
            return False
        
        # Verificar que no esté muy antigua (timeout)
        last_updated = execution.get("last_updated")
        if last_updated:
            try:
                last_update_time = datetime.fromisoformat(last_updated)
                if datetime.utcnow() - last_update_time > timedelta(hours=1):
                    logger.warning(
                        f"Execution {execution_id} too old to resume "
                        f"(last_updated={last_updated})"
                    )
                    return False
            except Exception as e:
                logger.error(f"Error parsing timestamp: {e}")
        
        return True
    
    def resume_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Resumir ejecución interrumpida.
        
        Args:
            execution_id: ID de ejecución
        
        Returns:
            Estado para continuar o None
        """
        if not self.can_resume_execution(execution_id):
            return None
        
        # Obtener último estado
        latest = self.get_latest_state(execution_id)
        
        if not latest:
            logger.warning(f"No state found for execution: {execution_id}")
            return None
        
        logger.info(
            f"[{latest.agent_name}] Resuming execution: {execution_id} "
            f"from step {latest.step_number}"
        )
        
        return latest.state_data
    
    # === LIMPIEZA Y MANTENIMIENTO === #
    
    def cleanup_old_executions(self, hours: int = 24):
        """
        Limpiar ejecuciones antiguas.
        
        Args:
            hours: Horas de antigüedad para considerar "antigua"
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        to_remove = []
        
        for execution_id, execution in self._active_executions.items():
            try:
                started_at = datetime.fromisoformat(execution["started_at"])
                if started_at < cutoff_time:
                    to_remove.append(execution_id)
            except Exception as e:
                logger.error(f"Error parsing timestamp: {e}")
        
        for execution_id in to_remove:
            del self._active_executions[execution_id]
            if execution_id in self._memory_store:
                del self._memory_store[execution_id]
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old executions")
    
    # === ANALYTICS Y DEBUGGING === #
    
    def get_agent_statistics(
        self,
        agent_name: str,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Obtener estadísticas de un agente.
        
        Args:
            agent_name: Nombre del agente
            time_window_hours: Ventana de tiempo en horas
        
        Returns:
            Dict con estadísticas
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        
        total_executions = 0
        completed = 0
        failed = 0
        avg_steps = 0
        total_steps = 0
        
        for execution in self._active_executions.values():
            if execution.get("agent_name") != agent_name:
                continue
            
            try:
                started_at = datetime.fromisoformat(execution["started_at"])
                if started_at < cutoff_time:
                    continue
                
                total_executions += 1
                status = execution.get("status")
                
                if status == ExecutionStatus.COMPLETED.value:
                    completed += 1
                elif status == ExecutionStatus.FAILED.value:
                    failed += 1
                
                total_steps += execution.get("step_count", 0)
                
            except Exception as e:
                logger.error(f"Error processing execution: {e}")
        
        if total_executions > 0:
            avg_steps = total_steps / total_executions
        
        return {
            "agent_name": agent_name,
            "time_window_hours": time_window_hours,
            "total_executions": total_executions,
            "completed": completed,
            "failed": failed,
            "in_progress": total_executions - completed - failed,
            "avg_steps_per_execution": round(avg_steps, 2),
            "success_rate": round(completed / total_executions * 100, 2) if total_executions > 0 else 0
        }


# ============================================================================
# INSTANCIA GLOBAL
# ============================================================================

_manager_instance: Optional[AgentStateManager] = None

def get_agent_state_manager(
    redis_service=None,
    use_persistence: bool = False
) -> AgentStateManager:
    """
    Obtener instancia singleton del state manager.
    
    Args:
        redis_service: Servicio de Redis (opcional)
        use_persistence: Si usar persistencia
    
    Returns:
        AgentStateManager
    """
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = AgentStateManager(redis_service, use_persistence)
    return _manager_instance


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "ExecutionStatus",
    "StateSnapshot",
    "AgentStateManager",
    "get_agent_state_manager"
]
