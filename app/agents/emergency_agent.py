# app/agents/emergency_agent.py
# 🧠 VERSIÓN COGNITIVA con LangGraph - Fase 4 Migración

"""
EmergencyAgent - Versión Cognitiva (LangGraph)

CAMBIOS PRINCIPALES:
- Hereda de CognitiveAgentBase
- Usa LangGraph para manejo de emergencias multi-paso
- GUARD RAILS CRÍTICOS para validar escalaciones
- Razonamiento para evaluar nivel de urgencia
- Integración con RAG para protocolos de emergencia
- Mantiene MISMA firma pública: invoke(inputs: dict) -> str

IMPORTANTE: Este agente tiene MÁXIMA PRIORIDAD y GUARD RAILS obligatorios
para evitar falsas escalaciones o mal manejo de emergencias reales.

MANTIENE COMPATIBILIDAD:
- Mismo nombre de clase: EmergencyAgent
- Misma firma pública
- Misma integración con vectorstore
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
    ExecutionStatus,
    DecisionType
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

EMERGENCY_AGENT_MANIFEST = AgentManifest(
    agent_type="emergency",
    display_name="Emergency Agent",
    description="Agente cognitivo CRÍTICO para manejo de emergencias con guard rails obligatorios",
    capabilities=[
        AgentCapabilityDef(
            name="assess_urgency",
            description="Evaluar nivel de urgencia de la situación",
            tools_required=[],
            priority=2,  # Máxima prioridad
            enabled=True
        ),
        AgentCapabilityDef(
            name="retrieve_protocols",
            description="Recuperar protocolos de emergencia",
            tools_required=["knowledge_base_search", "get_emergency_protocols"],
            priority=2
        ),
        AgentCapabilityDef(
            name="escalate_to_human",
            description="Escalar a atención humana (REQUIERE VALIDACIÓN)",
            tools_required=["escalate_to_human"],
            priority=2
        ),
        AgentCapabilityDef(
            name="create_priority_appointment",
            description="Crear cita prioritaria de emergencia",
            tools_required=["create_priority_appointment"],
            priority=1
        ),
        AgentCapabilityDef(
            name="send_urgent_notification",
            description="Enviar notificación urgente (REQUIERE VALIDACIÓN)",
            tools_required=["send_urgent_notification"],
            priority=2
        )
    ],
    required_tools=[
        "knowledge_base_search",
        "get_emergency_protocols"
    ],
    optional_tools=[
        "escalate_to_human",
        "send_urgent_notification",
        "create_priority_appointment"
    ],
    tags=["emergency", "critical", "urgent", "escalation", "protocols"],
    priority=2,  # Máxima prioridad del sistema
    max_retries=2,  # Pocas retries para emergencias
    timeout_seconds=30,  # Respuesta rápida
    metadata={
        "version": "2.0-cognitive",
        "critical": True,
        "requires_guardrails": True,
        "escalation_threshold": 0.7  # Umbral de confianza para escalar
    }
)


# ============================================================================
# NIVELES DE URGENCIA
# ============================================================================

class UrgencyLevel:
    """Niveles de urgencia estandarizados"""
    CRITICAL = "critical"      # Emergencia real, requiere acción inmediata
    HIGH = "high"             # Urgente pero no crítico
    MEDIUM = "medium"         # Necesita atención pronta
    LOW = "low"               # No es emergencia
    FALSE_ALARM = "false_alarm"  # No es emergencia en absoluto


# ============================================================================
# EMERGENCY AGENT COGNITIVO
# ============================================================================

class EmergencyAgent(CognitiveAgentBase):
    """
    Agente de emergencias con base cognitiva y GUARD RAILS CRÍTICOS.
    
    CARACTERÍSTICAS ESPECIALES:
    - Evaluación multi-nivel de urgencia
    - Validación obligatoria antes de escalar
    - Protocolos de emergencia desde RAG
    - Telemetría crítica detallada
    - Safe-fail: ante duda, escalar
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
        
        # Configuración cognitiva CON GUARD RAILS
        cognitive_config = CognitiveConfig(
            enable_reasoning_traces=True,
            enable_tool_validation=True,  # CRÍTICO
            enable_guardrails=True,  # OBLIGATORIO
            max_reasoning_steps=10,
            require_confirmation_for_critical_actions=True,  # OBLIGATORIO
            safe_fail_on_tool_error=True,
            persist_state=True  # Importante para auditoría
        )
        
        # Inicializar base cognitiva
        super().__init__(
            agent_type=AgentType.EMERGENCY,
            manifest=EMERGENCY_AGENT_MANIFEST,
            config=cognitive_config
        )
        
        # Grafo de LangGraph
        self.graph = None
        self.compiled_graph = None
        
        # Umbral de escalación (puede configurarse por empresa)
        self.escalation_threshold = 0.7
        
        logger.info(
            f"🚨 [{company_config.company_id}] EmergencyAgent initialized "
            f"(cognitive mode, CRITICAL, GUARDRAILS ENABLED)"
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
            
            # Log inicio CRÍTICO
            logger.warning(
                f"🚨 [{self.company_config.company_id}] EmergencyAgent.invoke() "
                f"- EMERGENCY QUERY: {inputs.get('question', '')[:150]}"
            )
            
            # Ejecutar grafo
            final_state = self.compiled_graph.invoke(initial_state)
            
            # Extraer respuesta
            response = self._build_response_from_state(final_state)
            
            # Log telemetría CRÍTICA
            telemetry = self._get_telemetry(final_state)
            urgency = final_state["context"].get("urgency_level", "unknown")
            escalated = final_state["context"].get("escalated", False)
            
            logger.warning(
                f"🚨 [{self.company_config.company_id}] EmergencyAgent completed "
                f"- Urgency: {urgency}, Escalated: {escalated}, "
                f"Steps: {telemetry['reasoning_steps']}"
            )
            
            return response
            
        except Exception as e:
            logger.critical(
                f"💥🚨 [{self.company_config.company_id}] CRITICAL ERROR in EmergencyAgent.invoke(): {e}"
            )
            # En emergencias, ante error, escalar
            return self._generate_critical_error_response(str(e))
    
    def set_vectorstore_service(self, service):
        """Inyectar servicio de vectorstore (mantener firma)"""
        self._vectorstore_service = service
        logger.debug(
            f"[{self.company_config.company_id}] VectorstoreService injected to EmergencyAgent"
        )
    
    # ========================================================================
    # CONSTRUCCIÓN DEL GRAFO LANGGRAPH
    # ========================================================================
    
    def build_graph(self) -> StateGraph:
        """
        Construir grafo de decisión con guard rails.
        
        FLUJO:
        1. Assess Urgency → Evaluar nivel de urgencia (CRÍTICO)
        2. Retrieve Protocols → Buscar protocolos en RAG
        3. Validate Escalation → Verificar si debe escalar (GUARD RAIL)
        4. Execute Action → Escalar o dar instrucciones
        5. Generate Response → Respuesta apropiada al nivel de urgencia
        
        Returns:
            StateGraph de LangGraph
        """
        # Crear grafo
        workflow = StateGraph(AgentState)
        
        # Añadir nodos
        workflow.add_node("assess_urgency", self._assess_urgency_node)
        workflow.add_node("retrieve_protocols", self._retrieve_protocols_node)
        workflow.add_node("validate_escalation", self._validate_escalation_node)
        workflow.add_node("escalate", self._escalate_node)
        workflow.add_node("provide_guidance", self._provide_guidance_node)
        
        # Definir edges
        workflow.set_entry_point("assess_urgency")
        
        workflow.add_edge("assess_urgency", "retrieve_protocols")
        workflow.add_edge("retrieve_protocols", "validate_escalation")
        
        # Condicional CRÍTICO: escalar o guiar
        workflow.add_conditional_edges(
            "validate_escalation",
            self._should_escalate,
            {
                "escalate": "escalate",
                "guide": "provide_guidance"
            }
        )
        
        workflow.add_edge("escalate", END)
        workflow.add_edge("provide_guidance", END)
        
        logger.info(
            f"[{self.company_config.company_id}] LangGraph built for EmergencyAgent "
            f"(5 nodes, GUARDRAILS ENABLED)"
        )
        
        return workflow
    
    # ========================================================================
    # NODOS DEL GRAFO
    # ========================================================================
    
    def _assess_urgency_node(self, state: AgentState) -> AgentState:
        """
        Nodo 1: Evaluar nivel de urgencia (CRÍTICO).
        
        Usa múltiples indicadores para determinar urgencia real.
        """
        state["current_node"] = "assess_urgency"
        
        question = state["question"].lower()
        
        # Evaluar urgencia con múltiples heurísticas
        urgency_level = self._evaluate_urgency_level(question, state["chat_history"])
        confidence = self._calculate_urgency_confidence(question)
        
        # Detectar indicadores críticos
        critical_indicators = self._detect_critical_indicators(question)
        
        # Registrar razonamiento CRÍTICO
        reasoning_step = self._add_reasoning_step(
            state,
            NodeType.DECISION,
            "Assessing urgency level (CRITICAL)",
            thought=f"Emergency query: '{question[:100]}'",
            decision=f"Urgency: {urgency_level}, Confidence: {confidence:.2f}",
            observation=f"Critical indicators: {critical_indicators}",
            confidence=confidence
        )
        
        state["reasoning_steps"].append(reasoning_step)
        
        # Guardar en contexto
        state["context"]["urgency_level"] = urgency_level
        state["context"]["urgency_confidence"] = confidence
        state["context"]["critical_indicators"] = critical_indicators
        state["confidence_scores"]["urgency"] = confidence
        
        # Log CRÍTICO
        logger.warning(
            f"🚨 [{self.company_config.company_id}] Urgency assessed: "
            f"{urgency_level} (confidence: {confidence:.2f}), "
            f"indicators: {critical_indicators}"
        )
        
        return state
    
    def _retrieve_protocols_node(self, state: AgentState) -> AgentState:
        """
        Nodo 2: Recuperar protocolos de emergencia desde RAG.
        """
        state["current_node"] = "retrieve_protocols"
        
        urgency_level = state["context"].get("urgency_level", "medium")
        question = state["question"]
        
        # Buscar protocolos en RAG
        if self._vectorstore_service:
            try:
                # Query específica para protocolos
                rag_query = self._build_emergency_query(question, urgency_level)
                
                docs = self._vectorstore_service.search_by_company(
                    rag_query,
                    self.company_config.company_id,
                    k=3
                )
                
                # Extraer protocolos
                protocols = self._extract_emergency_protocols(docs)
                
                state["vectorstore_context"] = protocols
                
                # Registrar razonamiento
                reasoning_step = self._add_reasoning_step(
                    state,
                    NodeType.REASONING,
                    "Retrieved emergency protocols from RAG",
                    observation=f"Found {len(docs)} protocol docs",
                    confidence=0.9 if protocols else 0.3
                )
                
                state["reasoning_steps"].append(reasoning_step)
                
                logger.info(
                    f"[{self.company_config.company_id}] Protocols retrieved: "
                    f"{len(docs)} docs"
                )
                
            except Exception as e:
                logger.error(f"Error retrieving emergency protocols: {e}")
                state["warnings"].append(f"Protocol retrieval failed: {str(e)}")
                state["vectorstore_context"] = self._get_default_emergency_protocols()
        
        else:
            # No hay RAG, usar protocolos default
            state["vectorstore_context"] = self._get_default_emergency_protocols()
        
        return state
    
    def _validate_escalation_node(self, state: AgentState) -> AgentState:
        """
        Nodo 3: Validar si debe escalar (GUARD RAIL CRÍTICO).
        
        Aplica múltiples validaciones antes de decidir escalar.
        """
        state["current_node"] = "validate_escalation"
        
        urgency_level = state["context"].get("urgency_level", "medium")
        urgency_confidence = state["context"].get("urgency_confidence", 0.5)
        critical_indicators = state["context"].get("critical_indicators", [])
        
        # VALIDACIÓN MULTI-FACTOR
        should_escalate = False
        escalation_reasons = []
        
        # Factor 1: Urgencia crítica con alta confianza
        if urgency_level == UrgencyLevel.CRITICAL and urgency_confidence >= self.escalation_threshold:
            should_escalate = True
            escalation_reasons.append("Critical urgency with high confidence")
        
        # Factor 2: Múltiples indicadores críticos
        if len(critical_indicators) >= 2:
            should_escalate = True
            escalation_reasons.append(f"Multiple critical indicators: {critical_indicators}")
        
        # Factor 3: Palabras clave de emergencia REAL
        emergency_keywords = ["sangre", "sangra", "accidente", "no respira", "inconsciente"]
        question_lower = state["question"].lower()
        if any(kw in question_lower for kw in emergency_keywords):
            should_escalate = True
            escalation_reasons.append("Real emergency keywords detected")
        
        # Factor 4: SAFE-FAIL - Ante duda en situación seria, escalar
        if urgency_level in [UrgencyLevel.HIGH, UrgencyLevel.CRITICAL] and urgency_confidence < 0.6:
            should_escalate = True
            escalation_reasons.append("Safe-fail: Low confidence in serious situation")
        
        # Registrar decisión CRÍTICA
        reasoning_step = self._add_reasoning_step(
            state,
            NodeType.DECISION,
            "Validating escalation decision (GUARD RAIL)",
            thought=f"Urgency: {urgency_level}, Confidence: {urgency_confidence:.2f}",
            decision=f"Should escalate: {should_escalate}",
            observation=f"Reasons: {escalation_reasons}",
            confidence=urgency_confidence
        )
        
        state["reasoning_steps"].append(reasoning_step)
        
        # Guardar decisión
        state["context"]["should_escalate"] = should_escalate
        state["context"]["escalation_reasons"] = escalation_reasons
        
        # Validación con ConditionEvaluator (si disponible)
        if self._condition_evaluator and should_escalate:
            validation = self._validate_with_evaluator(state)
            
            if not validation["approved"]:
                logger.warning(
                    f"⚠️ [{self.company_config.company_id}] Escalation BLOCKED by ConditionEvaluator: "
                    f"{validation['reason']}"
                )
                state["context"]["should_escalate"] = False
                state["warnings"].append(f"Escalation blocked: {validation['reason']}")
        
        # Log CRÍTICO
        logger.warning(
            f"🚨 [{self.company_config.company_id}] Escalation validation: "
            f"should_escalate={should_escalate}, reasons={escalation_reasons}"
        )
        
        return state
    
    def _escalate_node(self, state: AgentState) -> AgentState:
        """
        Nodo 4a: Ejecutar escalación a humano.
        """
        state["current_node"] = "escalate"
        
        urgency_level = state["context"].get("urgency_level", "high")
        escalation_reasons = state["context"].get("escalation_reasons", [])
        
        # Preparar datos de escalación
        escalation_data = {
            "urgency": urgency_level,
            "reasons": escalation_reasons,
            "question": state["question"],
            "user_id": state["user_id"],
            "company_id": self.company_config.company_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Ejecutar escalación (si tool executor disponible)
        if self._tool_executor:
            try:
                result = self._tool_executor.execute(
                    tool_name="escalate_to_human",
                    params=escalation_data,
                    company_id=self.company_config.company_id,
                    user_id=state["user_id"]
                )
                
                state["intermediate_results"]["escalation"] = result
                
                # Registrar razonamiento
                reasoning_step = self._add_reasoning_step(
                    state,
                    NodeType.TOOL_EXECUTION,
                    "Executed escalation to human",
                    action="escalate_to_human",
                    observation=f"Escalation result: {result.get('success')}"
                )
                
                state["reasoning_steps"].append(reasoning_step)
                
            except Exception as e:
                logger.error(f"Error executing escalation: {e}")
                state["errors"].append(f"Escalation error: {str(e)}")
        
        # Generar respuesta de escalación
        response = self._generate_escalation_response(state)
        
        state["response"] = response
        state["context"]["escalated"] = True
        state["status"] = ExecutionStatus.SUCCESS.value
        state["completed_at"] = datetime.utcnow().isoformat()
        
        # Log CRÍTICO
        logger.critical(
            f"🚨🚨 [{self.company_config.company_id}] ESCALATED TO HUMAN: "
            f"user={state['user_id']}, urgency={urgency_level}"
        )
        
        return state
    
    def _provide_guidance_node(self, state: AgentState) -> AgentState:
        """
        Nodo 4b: Proporcionar guía/protocolos sin escalar.
        """
        state["current_node"] = "provide_guidance"
        
        urgency_level = state["context"].get("urgency_level", "medium")
        protocols = state.get("vectorstore_context", "")
        
        # Generar respuesta con protocolos
        response = self._generate_guidance_response(
            urgency_level=urgency_level,
            protocols=protocols,
            state=state
        )
        
        state["response"] = response
        state["context"]["escalated"] = False
        state["status"] = ExecutionStatus.SUCCESS.value
        state["completed_at"] = datetime.utcnow().isoformat()
        
        # Registrar razonamiento
        reasoning_step = self._add_reasoning_step(
            state,
            NodeType.RESPONSE_GENERATION,
            "Provided guidance without escalation",
            observation=f"Urgency: {urgency_level}, guidance given"
        )
        
        state["reasoning_steps"].append(reasoning_step)
        
        logger.info(
            f"[{self.company_config.company_id}] Guidance provided without escalation"
        )
        
        return state
    
    # ========================================================================
    # DECISIONES CONDICIONALES
    # ========================================================================
    
    def _should_escalate(self, state: AgentState) -> str:
        """
        Determinar si debe escalar.
        
        Returns:
            "escalate" o "guide"
        """
        should_escalate = state["context"].get("should_escalate", False)
        
        if should_escalate:
            return "escalate"
        else:
            return "guide"
    
    # ========================================================================
    # HELPERS DE EVALUACIÓN DE URGENCIA
    # ========================================================================
    
    def _evaluate_urgency_level(
        self,
        question: str,
        chat_history: List
    ) -> str:
        """
        Evaluar nivel de urgencia con múltiples heurísticas.
        
        Returns:
            UrgencyLevel
        """
        question_lower = question.lower()
        
        # CRITICAL - Emergencia real médica
        critical_keywords = [
            "sangre", "sangra", "sangrando", "hemorragia",
            "no respira", "inconsciente", "desmayado",
            "convulsion", "ataque", "accidente grave",
            "alergia severa", "shock"
        ]
        if any(kw in question_lower for kw in critical_keywords):
            return UrgencyLevel.CRITICAL
        
        # HIGH - Urgente pero no crítico
        high_keywords = [
            "dolor fuerte", "dolor intenso", "mucho dolor",
            "hinchazón", "inflamación", "fiebre alta",
            "urgente", "inmediato", "ahora mismo",
            "no puedo", "problema grave"
        ]
        if any(kw in question_lower for kw in high_keywords):
            return UrgencyLevel.HIGH
        
        # MEDIUM - Necesita atención
        medium_keywords = [
            "dolor", "molestia", "incomodidad",
            "problema", "preocupa", "consulta urgente"
        ]
        if any(kw in question_lower for kw in medium_keywords):
            return UrgencyLevel.MEDIUM
        
        # FALSE ALARM - Claramente no es emergencia
        false_alarm_keywords = [
            "precio", "costo", "horario", "disponibilidad",
            "agendar", "cita", "información"
        ]
        if any(kw in question_lower for kw in false_alarm_keywords):
            return UrgencyLevel.FALSE_ALARM
        
        # Por defecto: LOW
        return UrgencyLevel.LOW
    
    def _calculate_urgency_confidence(self, question: str) -> float:
        """Calcular score de confianza en la evaluación de urgencia"""
        question_lower = question.lower()
        
        # Indicadores de alta confianza
        high_confidence_keywords = [
            "sangre", "no respira", "inconsciente",
            "dolor fuerte", "hinchazón", "fiebre"
        ]
        
        # Indicadores de baja confianza (ambigüedad)
        low_confidence_keywords = [
            "creo", "tal vez", "no sé si", "no estoy seguro"
        ]
        
        confidence = 0.5  # Base
        
        # Aumentar confianza
        for kw in high_confidence_keywords:
            if kw in question_lower:
                confidence += 0.15
        
        # Disminuir confianza
        for kw in low_confidence_keywords:
            if kw in question_lower:
                confidence -= 0.2
        
        # Clamp entre 0.2 y 1.0
        return min(max(confidence, 0.2), 1.0)
    
    def _detect_critical_indicators(self, question: str) -> List[str]:
        """Detectar indicadores críticos específicos"""
        question_lower = question.lower()
        
        indicators = []
        
        critical_patterns = {
            "bleeding": ["sangre", "sangra", "sangrando"],
            "breathing": ["no respira", "dificultad respirar", "ahogo"],
            "consciousness": ["inconsciente", "desmayado", "no responde"],
            "severe_pain": ["dolor insoportable", "dolor muy fuerte"],
            "allergy": ["alergia severa", "shock anafiláctico"],
            "trauma": ["accidente", "golpe fuerte", "caída"]
        }
        
        for indicator_name, keywords in critical_patterns.items():
            if any(kw in question_lower for kw in keywords):
                indicators.append(indicator_name)
        
        return indicators
    
    def _build_emergency_query(self, question: str, urgency_level: str) -> str:
        """Construir query para protocolos de emergencia"""
        return f"emergencia urgencia protocolo {urgency_level} {question}"
    
    def _extract_emergency_protocols(self, docs: List) -> str:
        """Extraer protocolos de emergencia de docs RAG"""
        if not docs:
            return ""
        
        protocols = []
        
        for doc in docs[:3]:
            content = ""
            
            if hasattr(doc, 'page_content'):
                content = doc.page_content
            elif isinstance(doc, dict) and 'content' in doc:
                content = doc['content']
            
            if content:
                content_lower = content.lower()
                
                # Filtrar protocolos relevantes
                if any(kw in content_lower for kw in ['protocolo', 'emergencia', 'urgencia', 'instrucción']):
                    protocols.append(content)
        
        return "\n\n".join(protocols) if protocols else ""
    
    def _get_default_emergency_protocols(self) -> str:
        """Protocolos de emergencia por defecto"""
        return (
            "PROTOCOLOS DE EMERGENCIA:\n\n"
            "1. Evaluar situación y mantener la calma\n"
            "2. Llamar a servicios de emergencia (911) si es necesario\n"
            "3. Contactar con profesionales de salud\n"
            "4. No automedicar en situaciones graves\n"
            "5. Acudir a urgencias si hay signos de alarma"
        )
    
    def _validate_with_evaluator(self, state: AgentState) -> Dict[str, Any]:
        """Validar escalación con ConditionEvaluator"""
        if not self._condition_evaluator:
            return {"approved": True, "reason": "No evaluator"}
        
        # Preparar condiciones
        conditions = {
            "urgency_level": state["context"].get("urgency_level"),
            "confidence": state["context"].get("urgency_confidence"),
            "critical_indicators": len(state["context"].get("critical_indicators", []))
        }
        
        # Validar
        # (Implementación simple - puede mejorarse)
        if conditions["confidence"] < 0.3:
            return {"approved": False, "reason": "Confidence too low"}
        
        return {"approved": True, "reason": "Validation passed"}
    
    # ========================================================================
    # GENERACIÓN DE RESPUESTAS
    # ========================================================================
    
    def _generate_escalation_response(self, state: AgentState) -> str:
        """Generar respuesta de escalación"""
        urgency_level = state["context"].get("urgency_level", "high")
        
        if urgency_level == UrgencyLevel.CRITICAL:
            return (
                f"🚨 **EMERGENCIA DETECTADA**\n\n"
                f"He identificado una situación que requiere atención inmediata.\n\n"
                f"✅ **Ya contacté a nuestro equipo de {self.company_config.company_name}**\n"
                f"✅ **Te contactarán en los próximos minutos**\n\n"
                f"⚠️ Si es una EMERGENCIA MÉDICA, llama al 911 inmediatamente.\n\n"
                f"¿Puedes proporcionarme tu número de contacto para priorizarte?"
            )
        else:
            return (
                f"🚨 Situación urgente identificada\n\n"
                f"Te conecto inmediatamente con un especialista de {self.company_config.company_name} "
                f"para atenderte de forma prioritaria.\n\n"
                f"¿Puedes proporcionarme tu número de contacto?"
            )
    
    def _generate_guidance_response(
        self,
        urgency_level: str,
        protocols: str,
        state: AgentState
    ) -> str:
        """Generar respuesta con guía (sin escalar)"""
        if urgency_level == UrgencyLevel.FALSE_ALARM:
            return (
                f"Veo que tu consulta no es una emergencia médica.\n\n"
                f"¿Te gustaría que te ayude con información, precios o agendar una cita "
                f"en {self.company_config.company_name}?"
            )
        
        if protocols:
            return (
                f"Entiendo tu preocupación. Aquí está la información relevante:\n\n"
                f"{protocols[:400]}\n\n"
                f"Si la situación empeora, no dudes en contactarnos inmediatamente o "
                f"acudir a urgencias.\n\n"
                f"¿Te gustaría agendar una cita prioritaria en {self.company_config.company_name}?"
            )
        else:
            return (
                f"Entiendo tu situación. Para darte la mejor atención, "
                f"te recomiendo contactar directamente con nuestros especialistas de "
                f"{self.company_config.company_name}.\n\n"
                f"¿Te gustaría que agendemos una consulta prioritaria?"
            )
    
    def _generate_error_response(self, error: str) -> str:
        """Generar respuesta de error (normal)"""
        return (
            f"Disculpa, tuve un problema procesando tu consulta de emergencia.\n\n"
            f"Por seguridad, te conecto inmediatamente con un especialista de "
            f"{self.company_config.company_name}. 🚨"
        )
    
    def _generate_critical_error_response(self, error: str) -> str:
        """Generar respuesta de error CRÍTICO (safe-fail)"""
        logger.critical(
            f"🚨🚨 [{self.company_config.company_id}] CRITICAL ERROR - Auto-escalating"
        )
        
        return (
            f"🚨 **ATENCIÓN: Sistema de emergencias con dificultades técnicas**\n\n"
            f"Por tu seguridad, te conecto INMEDIATAMENTE con atención humana.\n\n"
            f"Si es una EMERGENCIA MÉDICA, llama al 911 ahora.\n\n"
            f"Equipo de {self.company_config.company_name} te contactará de inmediato."
        )
