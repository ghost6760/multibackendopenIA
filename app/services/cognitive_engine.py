# app/services/cognitive_engine.py

"""
Motor de razonamiento compartido para agentes cognitivos.
Proporciona helpers de decisión, heurísticas y lógica de razonamiento
que pueden ser reutilizados por múltiples agentes.

Este servicio NO reemplaza la lógica específica de cada agente,
sino que proporciona utilidades comunes para toma de decisiones.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)


# ============================================================================
# PATRONES Y HEURÍSTICAS
# ============================================================================

# Patrones para detección de intenciones
INTENT_PATTERNS = {
    "schedule_appointment": [
        r"agendar|cita|reservar|programar|turno|agenda",
        r"disponibilidad|horario|cuando.*atender",
        r"quiero.*cita|necesito.*cita"
    ],
    
    "emergency": [
        r"emergencia|urgente|urgencia|dolor.*fuerte",
        r"accidente|sangr|trauma|herida",
        r"necesito.*ya|ahora.*mismo"
    ],
    
    "product_inquiry": [
        r"precio|costo|cuanto.*cuesta|valor",
        r"info.*sobre|que.*es|detalles.*de",
        r"botox|fillers|tratamiento|procedimiento"
    ],
    
    "availability_check": [
        r"disponible|libre|hay.*espacio",
        r"cuando.*puede|horarios",
        r"primer.*cita|proxima.*cita"
    ],
    
    "support": [
        r"ayuda|problema|no.*funciona|error",
        r"como.*hacer|instrucciones|dudas",
        r"preguntas|consulta"
    ]
}


# Indicadores de confianza por tipo de evidencia
CONFIDENCE_WEIGHTS = {
    "exact_match": 1.0,
    "strong_pattern": 0.8,
    "weak_pattern": 0.5,
    "context_clue": 0.6,
    "historical_behavior": 0.7
}


# ============================================================================
# CLASE PRINCIPAL
# ============================================================================

class CognitiveEngine:
    """
    Motor de razonamiento compartido.
    Proporciona métodos de decisión y análisis para agentes cognitivos.
    """
    
    def __init__(self):
        self.intent_patterns = INTENT_PATTERNS
        self.confidence_weights = CONFIDENCE_WEIGHTS
        logger.info("CognitiveEngine initialized")
    
    # === ANÁLISIS DE INTENCIÓN === #
    
    def analyze_intent(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analizar intención del usuario.
        
        Args:
            user_message: Mensaje del usuario
            context: Contexto adicional (historial, metadata)
        
        Returns:
            Dict con intent detectado y score de confianza
        """
        message_lower = user_message.lower()
        scores = {}
        
        # Evaluar cada intención contra patrones
        for intent, patterns in self.intent_patterns.items():
            score = 0.0
            matched_patterns = []
            
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    score += self.confidence_weights["strong_pattern"]
                    matched_patterns.append(pattern)
            
            # Normalizar score
            if matched_patterns:
                scores[intent] = min(score / len(patterns), 1.0)
        
        # Ajustar por contexto si está disponible
        if context:
            scores = self._adjust_scores_by_context(scores, context)
        
        # Determinar intención principal
        if scores:
            primary_intent = max(scores, key=scores.get)
            confidence = scores[primary_intent]
        else:
            primary_intent = "unknown"
            confidence = 0.0
        
        return {
            "primary_intent": primary_intent,
            "confidence": confidence,
            "all_scores": scores,
            "requires_clarification": confidence < 0.6
        }
    
    def _adjust_scores_by_context(
        self,
        scores: Dict[str, float],
        context: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Ajustar scores de intención basado en contexto.
        
        Args:
            scores: Scores actuales
            context: Contexto (historial, metadata)
        
        Returns:
            Scores ajustados
        """
        adjusted = scores.copy()
        
        # Si hay historial de conversación
        chat_history = context.get("chat_history", [])
        if chat_history:
            last_messages = chat_history[-3:]  # Últimos 3 mensajes
            
            # Buscar continuidad de intención
            for msg in last_messages:
                content = msg.get("content", "").lower()
                
                # Boost scores de intenciones mencionadas recientemente
                for intent in scores.keys():
                    if any(
                        re.search(pattern, content)
                        for pattern in self.intent_patterns.get(intent, [])
                    ):
                        adjusted[intent] = min(
                            adjusted[intent] * 1.2,
                            1.0
                        )
        
        return adjusted
    
    # === SELECCIÓN DE HERRAMIENTAS === #
    
    def suggest_tools(
        self,
        intent: str,
        agent_type: str,
        available_tools: List[str]
    ) -> List[Tuple[str, float]]:
        """
        Sugerir herramientas a usar basado en intención.
        
        Args:
            intent: Intención detectada
            agent_type: Tipo de agente
            available_tools: Tools disponibles
        
        Returns:
            Lista de tuplas (tool_name, priority_score)
        """
        suggestions = []
        
        # Mapeo de intención a herramientas recomendadas
        intent_to_tools = {
            "schedule_appointment": [
                ("knowledge_base_search", 0.9),
                ("get_available_slots", 1.0),
                ("create_appointment", 0.8),
                ("validate_appointment_data", 0.7)
            ],
            
            "emergency": [
                ("get_emergency_protocols", 1.0),
                ("escalate_to_human", 0.9),
                ("create_priority_appointment", 0.8)
            ],
            
            "product_inquiry": [
                ("knowledge_base_search", 1.0),
                ("get_product_info", 0.9),
                ("get_pricing", 0.8)
            ],
            
            "availability_check": [
                ("get_available_slots", 1.0),
                ("check_availability", 0.9),
                ("get_calendar_events", 0.6)
            ],
            
            "support": [
                ("knowledge_base_search", 1.0),
                ("get_faq", 0.9),
                ("search_documentation", 0.7)
            ]
        }
        
        # Obtener recomendaciones para la intención
        recommended = intent_to_tools.get(intent, [])
        
        # Filtrar solo las disponibles
        for tool_name, priority in recommended:
            if tool_name in available_tools:
                suggestions.append((tool_name, priority))
        
        # Ordenar por prioridad
        suggestions.sort(key=lambda x: x[1], reverse=True)
        
        logger.debug(
            f"Tool suggestions for intent '{intent}': "
            f"{[t[0] for t in suggestions]}"
        )
        
        return suggestions
    
    # === VALIDACIÓN DE DECISIONES === #
    
    def validate_decision(
        self,
        decision_type: str,
        decision_params: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validar una decisión antes de ejecutarla.
        
        Args:
            decision_type: Tipo de decisión (ej: "create_appointment")
            decision_params: Parámetros de la decisión
            context: Contexto completo
        
        Returns:
            Tupla (es_válida, mensaje_error)
        """
        validators = {
            "create_appointment": self._validate_appointment_decision,
            "escalate_to_human": self._validate_escalation_decision,
            "send_notification": self._validate_notification_decision
        }
        
        validator = validators.get(decision_type)
        
        if not validator:
            logger.warning(f"No validator for decision type: {decision_type}")
            return True, None  # Permitir por defecto
        
        return validator(decision_params, context)
    
    def _validate_appointment_decision(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Validar decisión de crear cita"""
        required_fields = ["datetime", "patient_info", "service"]
        
        # Verificar campos requeridos
        missing = [f for f in required_fields if f not in params]
        if missing:
            return False, f"Missing required fields: {missing}"
        
        # Validar formato de datetime
        datetime_str = params.get("datetime")
        if datetime_str:
            try:
                datetime.fromisoformat(datetime_str)
            except (ValueError, TypeError):
                return False, f"Invalid datetime format: {datetime_str}"
        
        # Validar patient_info
        patient_info = params.get("patient_info", {})
        if not isinstance(patient_info, dict):
            return False, "patient_info must be a dictionary"
        
        if not patient_info.get("name"):
            return False, "patient_info.name is required"
        
        return True, None
    
    def _validate_escalation_decision(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Validar decisión de escalar a humano"""
        if not params.get("reason"):
            return False, "Escalation reason is required"
        
        # Verificar que sea realmente necesario
        priority = params.get("priority", "normal")
        if priority not in ["low", "normal", "high", "critical"]:
            return False, f"Invalid priority: {priority}"
        
        return True, None
    
    def _validate_notification_decision(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Validar decisión de enviar notificación"""
        if not params.get("recipient"):
            return False, "Recipient is required"
        
        if not params.get("message"):
            return False, "Message is required"
        
        return True, None
    
    # === HEURÍSTICAS DE RAZONAMIENTO === #
    
    def should_use_tool(
        self,
        tool_name: str,
        current_state: Dict[str, Any],
        reasoning_history: List[Dict[str, Any]]
    ) -> bool:
        """
        Determinar si se debe usar una herramienta.
        
        Args:
            tool_name: Nombre de la herramienta
            current_state: Estado actual del agente
            reasoning_history: Historial de razonamiento
        
        Returns:
            True si se debe usar
        """
        # Evitar uso repetido de la misma tool
        tools_used = current_state.get("tools_used", [])
        recent_tools = [t["tool_name"] for t in tools_used[-3:]]
        
        if recent_tools.count(tool_name) >= 2:
            logger.warning(
                f"Tool '{tool_name}' already used {recent_tools.count(tool_name)} "
                f"times recently. Consider alternative."
            )
            return False
        
        # Si ya tenemos el resultado, no repetir
        tool_results = current_state.get("tool_results", {})
        if tool_name in tool_results:
            logger.debug(f"Tool '{tool_name}' result already available")
            return False
        
        return True
    
    def calculate_confidence(
        self,
        evidence: List[Dict[str, Any]]
    ) -> float:
        """
        Calcular score de confianza basado en evidencia.
        
        Args:
            evidence: Lista de evidencias con tipo y valor
                     [{"type": "exact_match", "value": 0.9}, ...]
        
        Returns:
            Score de confianza (0.0 - 1.0)
        """
        if not evidence:
            return 0.0
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for item in evidence:
            evidence_type = item.get("type", "unknown")
            value = item.get("value", 0.0)
            
            weight = self.confidence_weights.get(evidence_type, 0.5)
            weighted_sum += value * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        confidence = weighted_sum / total_weight
        return min(max(confidence, 0.0), 1.0)  # Clamp entre 0 y 1
    
    def should_continue_reasoning(
        self,
        reasoning_steps: List[Dict[str, Any]],
        max_steps: int = 10
    ) -> Tuple[bool, Optional[str]]:
        """
        Determinar si el agente debe continuar razonando.
        
        Args:
            reasoning_steps: Pasos de razonamiento realizados
            max_steps: Máximo de pasos permitidos
        
        Returns:
            Tupla (debe_continuar, razón)
        """
        step_count = len(reasoning_steps)
        
        # Límite de pasos
        if step_count >= max_steps:
            return False, f"Max reasoning steps reached ({max_steps})"
        
        # Detectar loops
        if step_count >= 3:
            last_three_actions = [
                step.get("action") for step in reasoning_steps[-3:]
            ]
            if len(set(last_three_actions)) == 1:
                return False, "Detected reasoning loop"
        
        return True, None
    
    # === ANÁLISIS DE CONTEXTO === #
    
    def extract_entities(
        self,
        text: str
    ) -> Dict[str, List[str]]:
        """
        Extraer entidades nombradas del texto.
        
        Args:
            text: Texto a analizar
        
        Returns:
            Dict con entidades por tipo
        """
        entities = {
            "dates": [],
            "times": [],
            "services": [],
            "names": []
        }
        
        # Patrones para fechas
        date_patterns = [
            r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
            r"(lunes|martes|miércoles|jueves|viernes|sábado|domingo)",
            r"(mañana|pasado mañana|hoy|ayer)"
        ]
        
        # Patrones para horas
        time_patterns = [
            r"\d{1,2}:\d{2}\s*(am|pm)?",
            r"\d{1,2}\s*(am|pm|horas)"
        ]
        
        # Buscar fechas
        for pattern in date_patterns:
            matches = re.findall(pattern, text.lower())
            entities["dates"].extend(matches)
        
        # Buscar horas
        for pattern in time_patterns:
            matches = re.findall(pattern, text.lower())
            entities["times"].extend(matches)
        
        # Buscar servicios comunes
        service_keywords = [
            "botox", "fillers", "limpieza", "consulta",
            "tratamiento", "procedimiento", "evaluación"
        ]
        for keyword in service_keywords:
            if keyword in text.lower():
                entities["services"].append(keyword)
        
        return entities


# ============================================================================
# INSTANCIA GLOBAL
# ============================================================================

_engine_instance: Optional[CognitiveEngine] = None

def get_cognitive_engine() -> CognitiveEngine:
    """
    Obtener instancia singleton del motor cognitivo.
    
    Returns:
        CognitiveEngine
    """
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = CognitiveEngine()
    return _engine_instance


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "CognitiveEngine",
    "get_cognitive_engine",
    "INTENT_PATTERNS",
    "CONFIDENCE_WEIGHTS"
]
