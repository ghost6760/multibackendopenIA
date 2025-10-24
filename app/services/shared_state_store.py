"""
Shared State Store - Almacén de contexto compartido entre agentes

Este módulo implementa un store centralizado donde los agentes pueden:
- Leer información compartida (precios, user info, schedule data)
- Escribir datos que otros agentes consumirán
- Coordinar handoffs entre agentes
- Mantener consistencia de información

Soporta almacenamiento:
- En memoria (default) - para desarrollo y testing
- Redis (opcional) - para producción y persistencia

Ejemplo de uso:
    store = SharedStateStore()

    # Agent 1 escribe pricing info
    store.set_pricing_info(user_id, "toxina_botulinica", {"price": "$550,000"})

    # Agent 2 lee pricing info
    pricing = store.get_pricing_info(user_id, "toxina_botulinica")
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
import json
import logging
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class PricingInfo:
    """Información de precios de un servicio/tratamiento"""
    service_name: str
    price: str
    currency: str = "COP"
    payment_methods: List[str] = field(default_factory=list)
    promotions: Optional[str] = None
    source_agent: str = "sales"  # Agente que proporcionó la info
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScheduleInfo:
    """Información de agendamiento"""
    treatment: str
    date: Optional[str] = None
    time: Optional[str] = None
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    status: str = "pending"  # pending, confirmed, cancelled
    booking_id: Optional[str] = None
    source_agent: str = "schedule"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserInfo:
    """Información del usuario extraída durante la conversación"""
    user_id: str
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    preferences: Dict[str, Any] = field(default_factory=dict)
    intent_history: List[str] = field(default_factory=list)  # Historial de intenciones
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ServiceInfo:
    """Información sobre servicios/tratamientos consultados"""
    service_name: str
    category: Optional[str] = None
    description: Optional[str] = None
    mentioned_by_agent: str = "unknown"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SupportInfo:
    """Información de soporte/preguntas generales"""
    question_type: str  # general, complaint, facility, payment_method, etc.
    question: str
    answer: Optional[str] = None
    resolved: bool = False
    source_agent: str = "support"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EmergencyInfo:
    """Información de emergencias médicas"""
    symptoms: List[str] = field(default_factory=list)
    urgency_level: str = "unknown"  # low, medium, high, critical
    action_taken: Optional[str] = None
    detected_by_agent: str = "emergency"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HandoffInfo:
    """Información de handoff entre agentes"""
    from_agent: str
    to_agent: str
    reason: str
    context: Dict[str, Any] = field(default_factory=dict)
    return_to_original: bool = True
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class SharedStateStore:
    """
    Almacén de estado compartido para coordinación entre agentes.

    Gestiona:
    - Pricing information (sales, schedule)
    - Schedule information (schedule, availability)
    - User information (todos los agentes)
    - Agent handoffs (orchestrator)
    """

    def __init__(self, backend: str = "memory", redis_url: Optional[str] = None, ttl_seconds: int = 3600):
        """
        Inicializar store.

        Args:
            backend: Tipo de backend ("memory" o "redis")
            redis_url: URL de Redis (solo si backend="redis")
            ttl_seconds: Tiempo de vida para datos en cache (default: 1 hora)
        """
        self.backend = backend
        self.ttl_seconds = ttl_seconds
        self._lock = Lock()

        if backend == "memory":
            # Almacenamiento en memoria
            self._pricing_store: Dict[str, Dict[str, PricingInfo]] = {}
            self._schedule_store: Dict[str, ScheduleInfo] = {}
            self._user_store: Dict[str, UserInfo] = {}
            self._service_store: Dict[str, List[ServiceInfo]] = {}
            self._support_store: Dict[str, List[SupportInfo]] = {}
            self._emergency_store: Dict[str, EmergencyInfo] = {}
            self._handoff_store: Dict[str, List[HandoffInfo]] = {}
            self._expiration_times: Dict[str, datetime] = {}

            logger.info("SharedStateStore initialized with in-memory backend")

        elif backend == "redis":
            # TODO: Implementar backend de Redis
            try:
                import redis
                self.redis_client = redis.from_url(redis_url or "redis://localhost:6379")
                logger.info(f"SharedStateStore initialized with Redis backend: {redis_url}")
            except ImportError:
                logger.warning("Redis not installed, falling back to memory backend")
                self.backend = "memory"
                self._pricing_store = {}
                self._schedule_store = {}
                self._user_store = {}
                self._service_store = {}
                self._support_store = {}
                self._emergency_store = {}
                self._handoff_store = {}
                self._expiration_times = {}
        else:
            raise ValueError(f"Invalid backend: {backend}. Use 'memory' or 'redis'")

    # ========== PRICING INFO ========== #

    def set_pricing_info(
        self,
        user_id: str,
        service_name: str,
        price: str,
        currency: str = "COP",
        payment_methods: List[str] = None,
        promotions: str = None,
        source_agent: str = "sales",
        metadata: Dict[str, Any] = None
    ):
        """
        Guardar información de precios.

        Args:
            user_id: ID del usuario
            service_name: Nombre del servicio/tratamiento
            price: Precio (ej. "$550,000")
            currency: Moneda
            payment_methods: Métodos de pago aceptados
            promotions: Promociones disponibles
            source_agent: Agente que proporcionó la info
            metadata: Metadata adicional
        """
        with self._lock:
            pricing = PricingInfo(
                service_name=service_name,
                price=price,
                currency=currency,
                payment_methods=payment_methods or [],
                promotions=promotions,
                source_agent=source_agent,
                metadata=metadata or {}
            )

            if self.backend == "memory":
                if user_id not in self._pricing_store:
                    self._pricing_store[user_id] = {}

                self._pricing_store[user_id][service_name] = pricing

                # Establecer expiración
                expiration_key = f"pricing:{user_id}:{service_name}"
                self._expiration_times[expiration_key] = datetime.utcnow() + timedelta(seconds=self.ttl_seconds)

                logger.info(
                    f"Pricing info stored: user={user_id}, service={service_name}, "
                    f"price={price}, agent={source_agent}"
                )

    def get_pricing_info(self, user_id: str, service_name: str = None) -> Optional[Dict[str, Any]]:
        """
        Obtener información de precios.

        Args:
            user_id: ID del usuario
            service_name: Nombre del servicio (opcional, si None retorna todos)

        Returns:
            Dict con pricing info o None si no existe
        """
        with self._lock:
            if self.backend == "memory":
                user_pricing = self._pricing_store.get(user_id, {})

                if service_name:
                    # Verificar expiración
                    expiration_key = f"pricing:{user_id}:{service_name}"
                    if expiration_key in self._expiration_times:
                        if datetime.utcnow() > self._expiration_times[expiration_key]:
                            # Expirado, eliminar
                            logger.info(f"Pricing info expired: {expiration_key}")
                            user_pricing.pop(service_name, None)
                            del self._expiration_times[expiration_key]
                            return None

                    pricing = user_pricing.get(service_name)
                    return asdict(pricing) if pricing else None
                else:
                    # Retornar todos los precios del usuario
                    return {name: asdict(pricing) for name, pricing in user_pricing.items()}

    def get_all_pricing_for_user(self, user_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Obtener toda la información de precios para un usuario.

        Returns:
            Dict con todos los pricing info del usuario
        """
        return self.get_pricing_info(user_id) or {}

    # ========== SCHEDULE INFO ========== #

    def set_schedule_info(
        self,
        user_id: str,
        treatment: str,
        date: str = None,
        time: str = None,
        patient_name: str = None,
        patient_phone: str = None,
        status: str = "pending",
        booking_id: str = None,
        source_agent: str = "schedule",
        metadata: Dict[str, Any] = None
    ):
        """
        Guardar información de agendamiento.

        Args:
            user_id: ID del usuario
            treatment: Tratamiento/servicio
            date: Fecha de la cita
            time: Hora de la cita
            patient_name: Nombre del paciente
            patient_phone: Teléfono del paciente
            status: Estado del agendamiento
            booking_id: ID de booking si ya se creó
            source_agent: Agente que proporcionó la info
            metadata: Metadata adicional
        """
        with self._lock:
            schedule = ScheduleInfo(
                treatment=treatment,
                date=date,
                time=time,
                patient_name=patient_name,
                patient_phone=patient_phone,
                status=status,
                booking_id=booking_id,
                source_agent=source_agent,
                metadata=metadata or {}
            )

            if self.backend == "memory":
                self._schedule_store[user_id] = schedule

                # Establecer expiración
                expiration_key = f"schedule:{user_id}"
                self._expiration_times[expiration_key] = datetime.utcnow() + timedelta(seconds=self.ttl_seconds)

                logger.info(
                    f"Schedule info stored: user={user_id}, treatment={treatment}, "
                    f"status={status}, agent={source_agent}"
                )

    def get_schedule_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtener información de agendamiento.

        Args:
            user_id: ID del usuario

        Returns:
            Dict con schedule info o None si no existe
        """
        with self._lock:
            if self.backend == "memory":
                # Verificar expiración
                expiration_key = f"schedule:{user_id}"
                if expiration_key in self._expiration_times:
                    if datetime.utcnow() > self._expiration_times[expiration_key]:
                        # Expirado, eliminar
                        logger.info(f"Schedule info expired: {expiration_key}")
                        self._schedule_store.pop(user_id, None)
                        del self._expiration_times[expiration_key]
                        return None

                schedule = self._schedule_store.get(user_id)
                return asdict(schedule) if schedule else None

    def update_schedule_status(self, user_id: str, status: str, booking_id: str = None):
        """
        Actualizar estado de agendamiento.

        Args:
            user_id: ID del usuario
            status: Nuevo estado
            booking_id: ID de booking (opcional)
        """
        with self._lock:
            if self.backend == "memory":
                schedule = self._schedule_store.get(user_id)
                if schedule:
                    schedule.status = status
                    if booking_id:
                        schedule.booking_id = booking_id
                    logger.info(f"Schedule status updated: user={user_id}, status={status}")

    # ========== USER INFO ========== #

    def set_user_info(
        self,
        user_id: str,
        name: str = None,
        phone: str = None,
        email: str = None,
        preferences: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ):
        """
        Guardar información del usuario.

        Args:
            user_id: ID del usuario
            name: Nombre
            phone: Teléfono
            email: Email
            preferences: Preferencias del usuario
            metadata: Metadata adicional
        """
        with self._lock:
            if self.backend == "memory":
                existing = self._user_store.get(user_id)

                if existing:
                    # Actualizar solo campos no-None
                    if name:
                        existing.name = name
                    if phone:
                        existing.phone = phone
                    if email:
                        existing.email = email
                    if preferences:
                        existing.preferences.update(preferences)
                    if metadata:
                        existing.metadata.update(metadata)
                    existing.last_updated = datetime.utcnow().isoformat()
                else:
                    # Crear nuevo
                    user_info = UserInfo(
                        user_id=user_id,
                        name=name,
                        phone=phone,
                        email=email,
                        preferences=preferences or {},
                        metadata=metadata or {}
                    )
                    self._user_store[user_id] = user_info

                logger.info(f"User info stored: user={user_id}")

    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtener información del usuario.

        Args:
            user_id: ID del usuario

        Returns:
            Dict con user info o None si no existe
        """
        with self._lock:
            if self.backend == "memory":
                user_info = self._user_store.get(user_id)
                return asdict(user_info) if user_info else None

    def add_intent_to_history(self, user_id: str, intent: str):
        """
        Agregar intención al historial del usuario.

        Args:
            user_id: ID del usuario
            intent: Intención detectada
        """
        with self._lock:
            if self.backend == "memory":
                user_info = self._user_store.get(user_id)
                if user_info:
                    user_info.intent_history.append(intent)
                    user_info.last_updated = datetime.utcnow().isoformat()
                else:
                    # Crear nuevo user_info
                    user_info = UserInfo(user_id=user_id, intent_history=[intent])
                    self._user_store[user_id] = user_info

                logger.info(f"Intent added to history: user={user_id}, intent={intent}")

    # ========== SERVICE INFO ========== #

    def add_service_info(
        self,
        user_id: str,
        service_name: str,
        category: str = None,
        description: str = None,
        mentioned_by_agent: str = "unknown",
        metadata: Dict[str, Any] = None
    ):
        """
        Registrar servicio/tratamiento mencionado.

        Args:
            user_id: ID del usuario
            service_name: Nombre del servicio
            category: Categoría del servicio
            description: Descripción
            mentioned_by_agent: Agente que mencionó el servicio
            metadata: Metadata adicional
        """
        with self._lock:
            if self.backend == "memory":
                service_info = ServiceInfo(
                    service_name=service_name,
                    category=category,
                    description=description,
                    mentioned_by_agent=mentioned_by_agent,
                    metadata=metadata or {}
                )

                if user_id not in self._service_store:
                    self._service_store[user_id] = []

                self._service_store[user_id].append(service_info)

                logger.info(
                    f"Service info added: user={user_id}, service={service_name}, "
                    f"agent={mentioned_by_agent}"
                )

    def get_service_info(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Obtener servicios mencionados para un usuario.

        Args:
            user_id: ID del usuario

        Returns:
            Lista de servicios mencionados
        """
        with self._lock:
            if self.backend == "memory":
                services = self._service_store.get(user_id, [])
                return [asdict(s) for s in services]
            return []

    # ========== SUPPORT INFO ========== #

    def add_support_info(
        self,
        user_id: str,
        question_type: str,
        question: str,
        answer: str = None,
        resolved: bool = False,
        source_agent: str = "support",
        metadata: Dict[str, Any] = None
    ):
        """
        Registrar pregunta de soporte.

        Args:
            user_id: ID del usuario
            question_type: Tipo de pregunta (general, complaint, facility, etc.)
            question: Pregunta del usuario
            answer: Respuesta proporcionada
            resolved: Si la pregunta fue resuelta
            source_agent: Agente que manejó la pregunta
            metadata: Metadata adicional
        """
        with self._lock:
            if self.backend == "memory":
                support_info = SupportInfo(
                    question_type=question_type,
                    question=question,
                    answer=answer,
                    resolved=resolved,
                    source_agent=source_agent,
                    metadata=metadata or {}
                )

                if user_id not in self._support_store:
                    self._support_store[user_id] = []

                self._support_store[user_id].append(support_info)

                logger.info(
                    f"Support info added: user={user_id}, type={question_type}, "
                    f"resolved={resolved}"
                )

    def get_support_info(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Obtener historial de soporte para un usuario.

        Args:
            user_id: ID del usuario

        Returns:
            Lista de consultas de soporte
        """
        with self._lock:
            if self.backend == "memory":
                support = self._support_store.get(user_id, [])
                return [asdict(s) for s in support]
            return []

    # ========== EMERGENCY INFO ========== #

    def set_emergency_info(
        self,
        user_id: str,
        symptoms: List[str] = None,
        urgency_level: str = "unknown",
        action_taken: str = None,
        detected_by_agent: str = "emergency",
        metadata: Dict[str, Any] = None
    ):
        """
        Registrar información de emergencia.

        Args:
            user_id: ID del usuario
            symptoms: Lista de síntomas
            urgency_level: Nivel de urgencia (low, medium, high, critical)
            action_taken: Acción tomada
            detected_by_agent: Agente que detectó la emergencia
            metadata: Metadata adicional
        """
        with self._lock:
            if self.backend == "memory":
                emergency_info = EmergencyInfo(
                    symptoms=symptoms or [],
                    urgency_level=urgency_level,
                    action_taken=action_taken,
                    detected_by_agent=detected_by_agent,
                    metadata=metadata or {}
                )

                self._emergency_store[user_id] = emergency_info

                logger.info(
                    f"Emergency info stored: user={user_id}, urgency={urgency_level}, "
                    f"symptoms={len(symptoms or [])}"
                )

    def get_emergency_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtener información de emergencia.

        Args:
            user_id: ID del usuario

        Returns:
            Dict con emergency info o None si no existe
        """
        with self._lock:
            if self.backend == "memory":
                emergency = self._emergency_store.get(user_id)
                return asdict(emergency) if emergency else None

    # ========== HANDOFF INFO ========== #

    def add_handoff(
        self,
        user_id: str,
        from_agent: str,
        to_agent: str,
        reason: str,
        context: Dict[str, Any] = None,
        return_to_original: bool = True
    ):
        """
        Registrar handoff entre agentes.

        Args:
            user_id: ID del usuario
            from_agent: Agente origen
            to_agent: Agente destino
            reason: Razón del handoff
            context: Contexto adicional
            return_to_original: Si debe volver al agente original
        """
        with self._lock:
            handoff = HandoffInfo(
                from_agent=from_agent,
                to_agent=to_agent,
                reason=reason,
                context=context or {},
                return_to_original=return_to_original
            )

            if self.backend == "memory":
                if user_id not in self._handoff_store:
                    self._handoff_store[user_id] = []

                self._handoff_store[user_id].append(handoff)

                logger.info(
                    f"Handoff registered: user={user_id}, {from_agent} → {to_agent}, "
                    f"reason={reason}"
                )

    def get_handoffs(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Obtener historial de handoffs.

        Args:
            user_id: ID del usuario

        Returns:
            Lista de handoffs
        """
        with self._lock:
            if self.backend == "memory":
                handoffs = self._handoff_store.get(user_id, [])
                return [asdict(h) for h in handoffs]
            return []

    def get_last_handoff(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtener último handoff.

        Args:
            user_id: ID del usuario

        Returns:
            Dict con último handoff o None
        """
        handoffs = self.get_handoffs(user_id)
        return handoffs[-1] if handoffs else None

    # ========== UTILIDADES ========== #

    def clear_user_data(self, user_id: str):
        """
        Limpiar todos los datos de un usuario.

        Args:
            user_id: ID del usuario
        """
        with self._lock:
            if self.backend == "memory":
                self._pricing_store.pop(user_id, None)
                self._schedule_store.pop(user_id, None)
                self._user_store.pop(user_id, None)
                self._handoff_store.pop(user_id, None)

                # Limpiar expiraciones
                keys_to_remove = [
                    key for key in self._expiration_times.keys()
                    if key.startswith(f"pricing:{user_id}:") or key == f"schedule:{user_id}"
                ]
                for key in keys_to_remove:
                    del self._expiration_times[key]

                logger.info(f"All data cleared for user: {user_id}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Obtener estadísticas del store.

        Returns:
            Dict con estadísticas
        """
        with self._lock:
            if self.backend == "memory":
                total_pricing = sum(len(services) for services in self._pricing_store.values())

                return {
                    "backend": self.backend,
                    "ttl_seconds": self.ttl_seconds,
                    "total_users_with_pricing": len(self._pricing_store),
                    "total_pricing_entries": total_pricing,
                    "total_schedules": len(self._schedule_store),
                    "total_users": len(self._user_store),
                    "total_handoffs": sum(len(h) for h in self._handoff_store.values())
                }
