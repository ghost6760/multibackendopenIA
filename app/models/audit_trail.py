"""
Audit Trail Model - Sistema de Auditoría para Acciones Críticas

Este módulo proporciona trazabilidad completa de todas las acciones
ejecutadas por el sistema, incluyendo:
- Llamadas a APIs externas (Google Calendar, Chatwoot)
- Envío de notificaciones (email, WhatsApp)
- Creación/modificación de citas
- Creación de tickets
- Operaciones de agents

Características:
- Persistencia en Redis por empresa (multi-tenant)
- Búsqueda por usuario, acción, fecha
- Soporte para compensating transactions (rollback)
- Registro de metadata completa
- TTL configurable para archivado
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
import json
import logging
import uuid

logger = logging.getLogger(__name__)


@dataclass
class AuditEntry:
    """
    Entrada individual de auditoría.

    Representa una acción ejecutada en el sistema con
    toda su metadata relevante.
    """
    # Identificación
    audit_id: str
    company_id: str
    user_id: str

    # Acción ejecutada
    action_type: str  # "api_call", "notification", "booking", "ticket", "agent_execution"
    action_name: str  # "google_calendar.create_event", "chatwoot.send_message", etc.

    # Contexto
    agent_name: Optional[str] = None
    conversation_id: Optional[str] = None

    # Resultado
    status: str = "pending"  # "pending", "success", "failed", "compensated"
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    # Compensación (para rollback)
    compensable: bool = False  # Si la acción puede ser revertida
    compensation_action: Optional[str] = None  # Acción para revertir
    compensation_params: Optional[Dict[str, Any]] = None
    compensated_at: Optional[str] = None

    # Metadata
    input_params: Dict[str, Any] = field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = None
    duration_ms: Optional[float] = None

    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None

    # Tags para búsqueda
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario para serialización"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuditEntry':
        """Crear desde diccionario"""
        return cls(**data)


class AuditManager:
    """
    Gestor de auditoría multi-tenant.

    Maneja el registro, consulta y compensación de acciones
    ejecutadas en el sistema.

    Redis Key Pattern:
        {company_prefix}audit:{audit_id} - Entrada individual
        {company_prefix}audit:user:{user_id} - Set de audit_ids por usuario
        {company_prefix}audit:action:{action_type} - Set de audit_ids por tipo
        {company_prefix}audit:date:{YYYY-MM-DD} - Set de audit_ids por fecha

    Ejemplo:
        audit = AuditManager(company_id="benova")

        # Registrar acción
        entry = audit.log_action(
            user_id="user123",
            action_type="booking",
            action_name="google_calendar.create_event",
            input_params={"date": "2025-10-26", "service": "toxina"},
            compensable=True,
            compensation_action="google_calendar.delete_event",
            compensation_params={"event_id": "abc123"}
        )

        # Marcar como exitosa
        audit.mark_success(entry.audit_id, result={"event_id": "abc123"})

        # Compensar (rollback)
        audit.compensate(entry.audit_id, reason="User cancelled")
    """

    def __init__(
        self,
        company_id: str,
        redis_client=None,
        ttl_days: int = 90  # Retener auditoría 90 días por defecto
    ):
        """
        Inicializar gestor de auditoría.

        Args:
            company_id: ID de la empresa
            redis_client: Cliente Redis (opcional)
            ttl_days: Días de retención de datos de auditoría
        """
        self.company_id = company_id
        self.ttl_seconds = ttl_days * 24 * 60 * 60

        # Obtener Redis client
        if redis_client:
            self.redis_client = redis_client
        else:
            try:
                from app.services.redis_service import get_redis_client
                self.redis_client = get_redis_client()
            except:
                logger.warning(f"[{company_id}] Redis not available for audit trail")
                self.redis_client = None

        # Configurar prefijo Redis
        from app.config.company_config import get_company_config
        company_config = get_company_config(company_id)
        if company_config:
            self.redis_prefix = company_config.redis_prefix + "audit:"
        else:
            self.redis_prefix = f"{company_id}:audit:"

        logger.info(
            f"✅ AuditManager initialized for {company_id} "
            f"(prefix: {self.redis_prefix}, ttl: {ttl_days} days)"
        )

    def log_action(
        self,
        user_id: str,
        action_type: str,
        action_name: str,
        input_params: Dict[str, Any] = None,
        agent_name: Optional[str] = None,
        conversation_id: Optional[str] = None,
        compensable: bool = False,
        compensation_action: Optional[str] = None,
        compensation_params: Optional[Dict[str, Any]] = None,
        tags: List[str] = None
    ) -> AuditEntry:
        """
        Registrar una acción en el audit trail.

        Args:
            user_id: ID del usuario
            action_type: Tipo de acción (api_call, notification, booking, ticket, agent_execution)
            action_name: Nombre descriptivo de la acción
            input_params: Parámetros de entrada
            agent_name: Nombre del agente que ejecutó la acción
            conversation_id: ID de conversación asociada
            compensable: Si la acción puede ser revertida
            compensation_action: Acción para revertir (si compensable)
            compensation_params: Parámetros para compensación
            tags: Tags adicionales para búsqueda

        Returns:
            AuditEntry creada
        """
        # Generar ID único
        audit_id = str(uuid.uuid4())

        # Crear entrada
        entry = AuditEntry(
            audit_id=audit_id,
            company_id=self.company_id,
            user_id=user_id,
            action_type=action_type,
            action_name=action_name,
            agent_name=agent_name,
            conversation_id=conversation_id,
            input_params=input_params or {},
            compensable=compensable,
            compensation_action=compensation_action,
            compensation_params=compensation_params,
            tags=tags or []
        )

        # Guardar en Redis
        if self.redis_client:
            self._save_entry(entry)

        logger.info(
            f"📝 [{self.company_id}] Audit logged: {action_type}/{action_name} "
            f"(id={audit_id[:8]}, user={user_id})"
        )

        return entry

    def mark_success(
        self,
        audit_id: str,
        result: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None
    ) -> bool:
        """
        Marcar una acción como exitosa.

        Args:
            audit_id: ID de la entrada de auditoría
            result: Resultado de la acción
            output_data: Datos de salida adicionales
            duration_ms: Duración de la ejecución

        Returns:
            True si se actualizó correctamente
        """
        entry = self.get_entry(audit_id)
        if not entry:
            logger.warning(f"[{self.company_id}] Audit entry not found: {audit_id}")
            return False

        entry.status = "success"
        entry.result = result
        entry.output_data = output_data
        entry.duration_ms = duration_ms
        entry.completed_at = datetime.utcnow().isoformat()

        if self.redis_client:
            self._save_entry(entry)

        logger.info(f"✅ [{self.company_id}] Audit success: {audit_id[:8]}")

        return True

    def mark_failed(
        self,
        audit_id: str,
        error_message: str,
        duration_ms: Optional[float] = None
    ) -> bool:
        """
        Marcar una acción como fallida.

        Args:
            audit_id: ID de la entrada de auditoría
            error_message: Mensaje de error
            duration_ms: Duración de la ejecución

        Returns:
            True si se actualizó correctamente
        """
        entry = self.get_entry(audit_id)
        if not entry:
            logger.warning(f"[{self.company_id}] Audit entry not found: {audit_id}")
            return False

        entry.status = "failed"
        entry.error_message = error_message
        entry.duration_ms = duration_ms
        entry.completed_at = datetime.utcnow().isoformat()

        if self.redis_client:
            self._save_entry(entry)

        logger.error(f"❌ [{self.company_id}] Audit failed: {audit_id[:8]} - {error_message}")

        return True

    def compensate(
        self,
        audit_id: str,
        reason: str,
        compensated_by: Optional[str] = None
    ) -> bool:
        """
        Compensar (revertir) una acción.

        Args:
            audit_id: ID de la entrada de auditoría
            reason: Razón de la compensación
            compensated_by: ID de quien ejecutó la compensación

        Returns:
            True si se compensó correctamente
        """
        entry = self.get_entry(audit_id)
        if not entry:
            logger.warning(f"[{self.company_id}] Audit entry not found: {audit_id}")
            return False

        if not entry.compensable:
            logger.warning(
                f"[{self.company_id}] Action {audit_id[:8]} is not compensable"
            )
            return False

        if entry.status == "compensated":
            logger.warning(f"[{self.company_id}] Action {audit_id[:8]} already compensated")
            return False

        entry.status = "compensated"
        entry.compensated_at = datetime.utcnow().isoformat()

        # Agregar metadata de compensación
        if not entry.output_data:
            entry.output_data = {}
        entry.output_data["compensation_reason"] = reason
        entry.output_data["compensated_by"] = compensated_by

        if self.redis_client:
            self._save_entry(entry)

        logger.info(
            f"🔄 [{self.company_id}] Action compensated: {audit_id[:8]} - {reason}"
        )

        return True

    def get_entry(self, audit_id: str) -> Optional[AuditEntry]:
        """
        Obtener una entrada de auditoría por ID.

        Args:
            audit_id: ID de la entrada

        Returns:
            AuditEntry o None si no existe
        """
        if not self.redis_client:
            return None

        key = f"{self.redis_prefix}{audit_id}"
        data = self.redis_client.get(key)

        if not data:
            return None

        try:
            entry_dict = json.loads(data)
            return AuditEntry.from_dict(entry_dict)
        except Exception as e:
            logger.error(f"[{self.company_id}] Error parsing audit entry: {e}")
            return None

    def get_by_user(
        self,
        user_id: str,
        limit: int = 100,
        action_type: Optional[str] = None
    ) -> List[AuditEntry]:
        """
        Obtener entradas de auditoría por usuario.

        Args:
            user_id: ID del usuario
            limit: Máximo de entradas a retornar
            action_type: Filtrar por tipo de acción (opcional)

        Returns:
            Lista de AuditEntry
        """
        if not self.redis_client:
            return []

        # Obtener IDs de auditoría del usuario
        user_key = f"{self.redis_prefix}user:{user_id}"
        audit_ids = self.redis_client.smembers(user_key)

        entries = []
        for audit_id in audit_ids:
            entry = self.get_entry(audit_id)
            if entry:
                if action_type is None or entry.action_type == action_type:
                    entries.append(entry)

        # Ordenar por fecha (más reciente primero)
        entries.sort(key=lambda e: e.created_at, reverse=True)

        return entries[:limit]

    def get_by_action_type(
        self,
        action_type: str,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[AuditEntry]:
        """
        Obtener entradas de auditoría por tipo de acción.

        Args:
            action_type: Tipo de acción
            limit: Máximo de entradas a retornar
            status: Filtrar por status (opcional)

        Returns:
            Lista de AuditEntry
        """
        if not self.redis_client:
            return []

        action_key = f"{self.redis_prefix}action:{action_type}"
        audit_ids = self.redis_client.smembers(action_key)

        entries = []
        for audit_id in audit_ids:
            entry = self.get_entry(audit_id)
            if entry:
                if status is None or entry.status == status:
                    entries.append(entry)

        entries.sort(key=lambda e: e.created_at, reverse=True)

        return entries[:limit]

    def get_compensable_actions(
        self,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> List[AuditEntry]:
        """
        Obtener acciones que pueden ser compensadas (revertidas).

        Args:
            user_id: Filtrar por usuario (opcional)
            conversation_id: Filtrar por conversación (opcional)

        Returns:
            Lista de AuditEntry compensables
        """
        entries = []

        if user_id:
            entries = self.get_by_user(user_id)
        else:
            # Obtener todas las acciones (limitado)
            for action_type in ["booking", "notification", "ticket"]:
                entries.extend(self.get_by_action_type(action_type, limit=50))

        # Filtrar compensables y no compensadas
        compensable = [
            e for e in entries
            if e.compensable and e.status == "success"
        ]

        if conversation_id:
            compensable = [
                e for e in compensable
                if e.conversation_id == conversation_id
            ]

        return compensable

    def get_stats(self) -> Dict[str, Any]:
        """
        Obtener estadísticas de auditoría.

        Returns:
            Diccionario con estadísticas
        """
        if not self.redis_client:
            return {"error": "Redis not available"}

        # Contar entries por tipo
        stats = {
            "company_id": self.company_id,
            "by_action_type": {},
            "by_status": {},
            "total_entries": 0
        }

        # Contar por tipo de acción
        for action_type in ["api_call", "notification", "booking", "ticket", "agent_execution"]:
            key = f"{self.redis_prefix}action:{action_type}"
            count = self.redis_client.scard(key)
            stats["by_action_type"][action_type] = count
            stats["total_entries"] += count

        return stats

    def _save_entry(self, entry: AuditEntry):
        """Guardar entrada en Redis con indexación"""
        if not self.redis_client:
            return

        # Guardar entrada principal
        entry_key = f"{self.redis_prefix}{entry.audit_id}"
        self.redis_client.set(
            entry_key,
            json.dumps(entry.to_dict()),
            ex=self.ttl_seconds
        )

        # Indexar por usuario
        user_key = f"{self.redis_prefix}user:{entry.user_id}"
        self.redis_client.sadd(user_key, entry.audit_id)
        self.redis_client.expire(user_key, self.ttl_seconds)

        # Indexar por tipo de acción
        action_key = f"{self.redis_prefix}action:{entry.action_type}"
        self.redis_client.sadd(action_key, entry.audit_id)
        self.redis_client.expire(action_key, self.ttl_seconds)

        # Indexar por fecha
        date_key = f"{self.redis_prefix}date:{entry.created_at[:10]}"  # YYYY-MM-DD
        self.redis_client.sadd(date_key, entry.audit_id)
        self.redis_client.expire(date_key, self.ttl_seconds)

    def clear_user_data(self, user_id: str):
        """
        Limpiar datos de auditoría de un usuario.

        Args:
            user_id: ID del usuario
        """
        if not self.redis_client:
            return

        user_key = f"{self.redis_prefix}user:{user_id}"
        audit_ids = self.redis_client.smembers(user_key)

        # Eliminar todas las entradas
        for audit_id in audit_ids:
            entry_key = f"{self.redis_prefix}{audit_id}"
            self.redis_client.delete(entry_key)

        # Eliminar índice de usuario
        self.redis_client.delete(user_key)

        logger.info(
            f"🗑️ [{self.company_id}] Cleared audit data for user: {user_id} "
            f"({len(audit_ids)} entries)"
        )
