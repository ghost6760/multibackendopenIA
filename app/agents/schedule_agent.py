# app/agents/schedule_agent.py
# 🧠 VERSIÓN COGNITIVA con LangGraph - Fase 2 Migración

"""
ScheduleAgent - Versión Cognitiva (LangGraph)

CAMBIOS PRINCIPALES:
- Hereda de CognitiveAgentBase en lugar de BaseAgent
- Usa LangGraph para grafo de decisión multi-paso
- Razonamiento explícito antes de ejecutar herramientas
- Integración con AgentToolsService para ejecución uniforme
- Mantiene MISMA firma pública: invoke(inputs: dict) -> str

MANTIENE COMPATIBILIDAD:
- Mismo nombre de clase: ScheduleAgent
- Misma firma pública: invoke(), set_vectorstore_service()
- Mismo formato entrada/salida
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging
import re

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
    create_reasoning_node,
    create_tool_node
)

from app.agents._agent_tools import (
    get_agent_tools_registry,
    get_tools_for_agent
)

# LangGraph imports
from langgraph.graph import StateGraph, END
from langchain.prompts import ChatPromptTemplate

# Services
from app.config.company_config import CompanyConfig
from app.services.openai_service import OpenAIService

logger = logging.getLogger(__name__)


# ============================================================================
# MANIFEST DE CAPACIDADES
# ============================================================================

SCHEDULE_AGENT_MANIFEST = AgentManifest(
    agent_type="schedule",
    display_name="Schedule Agent",
    description="Agente cognitivo para agendamiento de citas con razonamiento multi-paso",
    capabilities=[
        AgentCapabilityDef(
            name="check_availability",
            description="Verificar disponibilidad de horarios",
            tools_required=["get_available_slots", "check_availability"],
            priority=1
        ),
        AgentCapabilityDef(
            name="create_appointment",
            description="Crear nueva cita",
            tools_required=[
                "create_appointment",
                "validate_appointment_data",
                "send_confirmation"
            ],
            priority=2
        ),
        AgentCapabilityDef(
            name="retrieve_context",
            description="Buscar información sobre tratamientos y preparaciones",
            tools_required=["knowledge_base_search"],
            priority=0
        )
    ],
    required_tools=[
        "knowledge_base_search",
        "get_available_slots",
        "create_appointment",
        "validate_appointment_data"
    ],
    optional_tools=[
        "check_availability",
        "get_calendar_events",
        "send_confirmation"
    ],
    tags=["scheduling", "calendar", "appointments", "rag"],
    priority=1,
    max_retries=3,
    timeout_seconds=60,
    metadata={
        "version": "2.0-cognitive",
        "migration_date": "2024",
        "supports_reasoning": True
    }
)


# ============================================================================
# SCHEDULE AGENT COGNITIVO
# ============================================================================

class ScheduleAgent(CognitiveAgentBase):
    """
    Agente de agendamiento con base cognitiva (LangGraph).
    
    IMPORTANTE: Mantiene la misma interfaz pública que la versión anterior
    pero usa razonamiento multi-paso y ejecución dinámica de tools.
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
        
        # Configuración cognitiva
        cognitive_config = CognitiveConfig(
            enable_reasoning_traces=True,
            enable_tool_validation=True,
            enable_guardrails=True,
            max_reasoning_steps=15,  # Más pasos para agendamiento complejo
            require_confirmation_for_critical_actions=True,
            safe_fail_on_tool_error=True,
            persist_state=True
        )
        
        # Inicializar base cognitiva
        super().__init__(
            agent_type=AgentType.SCHEDULE,
            manifest=SCHEDULE_AGENT_MANIFEST,
            config=cognitive_config
        )
        
        # Grafo de LangGraph (se construye después)
        self.graph = None
        self.compiled_graph = None
        
        # Configuración específica de scheduling
        self.integration_type = self._detect_integration_type()
        self.schedule_service_available = False
        
        logger.info(
            f"🧠 [{company_config.company_id}] ScheduleAgent initialized "
            f"(cognitive mode, integration={self.integration_type})"
        )
    
    # ========================================================================
    # INTERFAZ PÚBLICA (MANTENER COMPATIBILIDAD)
    # ========================================================================
    
    def invoke(self, inputs: dict) -> str:
        """
        Punto de entrada principal (mantener firma).
        
        Args:
            inputs: Dict con keys: question, chat_history, user_id, company_id
        
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
            
            # Log inicio
            logger.info(
                f"🔍 [{self.company_config.company_id}] ScheduleAgent.invoke() "
                f"- Question: {inputs.get('question', '')[:100]}..."
            )
            
            # Ejecutar grafo de LangGraph
            final_state = self.compiled_graph.invoke(initial_state)
            
            # Extraer respuesta final
            response = self._build_response_from_state(final_state)
            
            # Log telemetría
            telemetry = self._get_telemetry(final_state)
            logger.info(
                f"✅ [{self.company_config.company_id}] ScheduleAgent completed "
                f"- Steps: {telemetry['reasoning_steps']}, "
                f"Tools: {len(telemetry['tools_used'])}, "
                f"Latency: {telemetry['total_latency_ms']:.2f}ms"
            )
            
            return response
            
        except Exception as e:
            logger.exception(
                f"💥 [{self.company_config.company_id}] Error in ScheduleAgent.invoke()"
            )
            return self._generate_error_response(str(e))
    
    def set_vectorstore_service(self, service):
        """Inyectar servicio de vectorstore (mantener firma)"""
        self._vectorstore_service = service
        logger.debug(
            f"[{self.company_config.company_id}] VectorstoreService injected to ScheduleAgent"
        )
    
    # ========================================================================
    # CONSTRUCCIÓN DEL GRAFO LANGGRAPH
    # ========================================================================
    
    def build_graph(self) -> StateGraph:
        """
        Construir grafo de decisión con LangGraph.
        
        FLUJO:
        1. Analyze Intent → Determinar qué quiere el usuario
        2. Retrieve Context → Buscar info en RAG si es necesario
        3. Decide Action → Determinar qué herramientas usar
        4. Execute Tools → Ejecutar herramientas seleccionadas
        5. Generate Response → Generar respuesta final
        
        Returns:
            StateGraph de LangGraph
        """
        # Crear grafo
        workflow = StateGraph(AgentState)
        
        # Añadir nodos
        workflow.add_node("analyze_intent", self._analyze_intent_node)
        workflow.add_node("retrieve_context", self._retrieve_context_node)
        workflow.add_node("decide_action", self._decide_action_node)
        workflow.add_node("execute_tools", self._execute_tools_node)
        workflow.add_node("generate_response", self._generate_response_node)
        
        # Definir edges
        workflow.set_entry_point("analyze_intent")
        
        workflow.add_edge("analyze_intent", "retrieve_context")
        workflow.add_edge("retrieve_context", "decide_action")
        
        # Condicional: ejecutar tools o ir directo a respuesta
        workflow.add_conditional_edges(
            "decide_action",
            self._should_execute_tools,
            {
                "execute": "execute_tools",
                "skip": "generate_response"
            }
        )
        
        workflow.add_edge("execute_tools", "generate_response")
        workflow.add_edge("generate_response", END)
        
        logger.info(
            f"[{self.company_config.company_id}] LangGraph built for ScheduleAgent "
            f"(5 nodes)"
        )
        
        return workflow
    
    # ========================================================================
    # NODOS DEL GRAFO
    # ========================================================================
    
    def _analyze_intent_node(self, state: AgentState) -> AgentState:
        """
        Nodo 1: Analizar intención del usuario.
        
        Determina si el usuario quiere:
        - Consultar disponibilidad
        - Agendar una cita
        - Obtener información sobre tratamientos
        """
        state["current_node"] = "analyze_intent"
        
        question = state["question"].lower()
        
        # Analizar intención
        intent = self._detect_scheduling_intent(question)
        confidence = self._calculate_intent_confidence(question, intent)
        
        # Registrar razonamiento
        reasoning_step = self._add_reasoning_step(
            state,
            NodeType.REASONING,
            "Analyzing user intent for scheduling query",
            thought=f"User asks: '{question[:100]}'",
            decision=f"Detected intent: {intent} (confidence: {confidence:.2f})",
            confidence=confidence
        )
        
        state["reasoning_steps"].append(reasoning_step)
        
        # Guardar decisión
        state["decisions"].append({
            "type": "intent_detection",
            "intent": intent,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        state["confidence_scores"]["intent"] = confidence
        
        # Extraer entidades (fechas, tratamientos)
        entities = self._extract_scheduling_entities(question, state["chat_history"])
        state["context"]["entities"] = entities
        state["context"]["intent"] = intent
        
        logger.debug(
            f"[{self.company_config.company_id}] Intent: {intent}, "
            f"Entities: {entities}"
        )
        
        return state
    
    def _retrieve_context_node(self, state: AgentState) -> AgentState:
        """
        Nodo 2: Recuperar contexto desde RAG si es necesario.
        """
        state["current_node"] = "retrieve_context"
        
        question = state["question"]
        intent = state["context"].get("intent", "unknown")
        
        # Determinar si necesita RAG
        needs_rag = self._needs_rag_context(intent, question)
        
        if needs_rag and self._vectorstore_service:
            # Construir query de RAG
            rag_query = self._build_rag_query(question, intent)
            
            # Buscar en vectorstore
            try:
                docs = self._vectorstore_service.search_by_company(
                    rag_query,
                    self.company_config.company_id,
                    k=3
                )
                
                # Extraer contenido relevante
                rag_context = self._extract_rag_content(docs, intent)
                
                state["vectorstore_context"] = rag_context
                
                # Registrar razonamiento
                reasoning_step = self._add_reasoning_step(
                    state,
                    NodeType.REASONING,
                    "Retrieved context from knowledge base",
                    thought=f"Query: '{rag_query}'",
                    observation=f"Found {len(docs)} relevant documents",
                    confidence=0.9 if rag_context else 0.3
                )
                
                state["reasoning_steps"].append(reasoning_step)
                
                logger.debug(
                    f"[{self.company_config.company_id}] RAG context retrieved "
                    f"({len(docs)} docs)"
                )
                
            except Exception as e:
                logger.error(f"Error retrieving RAG context: {e}")
                state["warnings"].append(f"RAG retrieval failed: {str(e)}")
        
        else:
            # No necesita RAG o no está disponible
            state["vectorstore_context"] = self._get_basic_schedule_info()
            
            reasoning_step = self._add_reasoning_step(
                state,
                NodeType.REASONING,
                "Using basic schedule information",
                thought="RAG not needed or not available",
                observation="Using company config defaults"
            )
            
            state["reasoning_steps"].append(reasoning_step)
        
        return state
    
    def _decide_action_node(self, state: AgentState) -> AgentState:
        """
        Nodo 3: Decidir qué herramientas usar.
        """
        state["current_node"] = "decide_action"
        
        intent = state["context"].get("intent", "unknown")
        entities = state["context"].get("entities", {})
        
        # Decidir herramientas basado en intención
        tools_to_use = self._select_tools_for_intent(intent, entities, state)
        
        state["context"]["selected_tools"] = tools_to_use
        
        # Registrar razonamiento
        reasoning_step = self._add_reasoning_step(
            state,
            NodeType.DECISION,
            "Deciding which tools to execute",
            thought=f"Intent: {intent}, Entities: {list(entities.keys())}",
            decision=f"Selected tools: {[t['tool_name'] for t in tools_to_use]}",
            confidence=0.8
        )
        
        state["reasoning_steps"].append(reasoning_step)
        
        logger.debug(
            f"[{self.company_config.company_id}] Selected {len(tools_to_use)} tools"
        )
        
        return state
    
    def _execute_tools_node(self, state: AgentState) -> AgentState:
        """
        Nodo 4: Ejecutar herramientas seleccionadas.
        """
        state["current_node"] = "execute_tools"
        
        selected_tools = state["context"].get("selected_tools", [])
        
        if not selected_tools:
            logger.debug("No tools to execute")
            return state
        
        # Ejecutar cada tool
        for tool_config in selected_tools:
            tool_name = tool_config["tool_name"]
            tool_params = tool_config["params"]
            
            # Registrar inicio
            reasoning_step = self._add_reasoning_step(
                state,
                NodeType.TOOL_EXECUTION,
                f"Executing tool: {tool_name}",
                action=f"Tool: {tool_name}",
                observation="Waiting for result..."
            )
            state["reasoning_steps"].append(reasoning_step)
            
            # Ejecutar tool (con retry y manejo de errores)
            result = self._execute_single_tool(tool_name, tool_params, state)
            
            # Guardar resultado
            if result["success"]:
                state["intermediate_results"][tool_name] = result["data"]
                state["context"][f"{tool_name}_result"] = result["data"]
                
                # Actualizar observación
                reasoning_step["observation"] = f"Success: {result['data']}"
                
            else:
                error_msg = result.get("error", "Unknown error")
                state["errors"].append(f"Tool {tool_name} failed: {error_msg}")
                
                # Safe-fail: continuar con otros tools
                if self.config.safe_fail_on_tool_error:
                    logger.warning(
                        f"Tool {tool_name} failed, continuing with safe-fail"
                    )
                    reasoning_step["observation"] = f"Failed: {error_msg} (safe-fail)"
                else:
                    # Detener ejecución
                    state["should_continue"] = False
                    break
        
        return state
    
    def _generate_response_node(self, state: AgentState) -> AgentState:
        """
        Nodo 5: Generar respuesta final.
        """
        state["current_node"] = "generate_response"
        
        intent = state["context"].get("intent", "unknown")
        entities = state["context"].get("entities", {})
        tool_results = state["intermediate_results"]
        rag_context = state.get("vectorstore_context", "")
        
        # Construir prompt para generación de respuesta
        response = self._build_final_response(
            intent=intent,
            entities=entities,
            tool_results=tool_results,
            rag_context=rag_context,
            state=state
        )
        
        state["response"] = response
        state["status"] = ExecutionStatus.SUCCESS.value
        state["completed_at"] = datetime.utcnow().isoformat()
        
        # Registrar razonamiento final
        reasoning_step = self._add_reasoning_step(
            state,
            NodeType.RESPONSE_GENERATION,
            "Generated final response",
            thought=f"Synthesizing response for intent: {intent}",
            observation=f"Response length: {len(response)} chars",
            confidence=0.9
        )
        
        state["reasoning_steps"].append(reasoning_step)
        
        logger.info(
            f"[{self.company_config.company_id}] Response generated "
            f"({len(response)} chars)"
        )
        
        return state
    
    # ========================================================================
    # DECISIONES CONDICIONALES
    # ========================================================================
    
    def _should_execute_tools(self, state: AgentState) -> str:
        """
        Determinar si ejecutar tools o ir directo a respuesta.
        
        Returns:
            "execute" o "skip"
        """
        selected_tools = state["context"].get("selected_tools", [])
        
        if not selected_tools:
            return "skip"
        
        # Si no hay tool_executor, skip
        if not self._tool_executor:
            logger.warning("ToolExecutor not available, skipping tools")
            state["warnings"].append("ToolExecutor not configured")
            return "skip"
        
        return "execute"
    
    # ========================================================================
    # HELPERS DE INTENCIÓN Y ENTIDADES
    # ========================================================================
    
    def _detect_scheduling_intent(self, question: str) -> str:
        """
        Detectar intención específica de scheduling.
        
        Returns:
            "check_availability", "create_appointment", "get_info", "unknown"
        """
        question_lower = question.lower()
        
        # Patrones de intención
        availability_patterns = [
            r"disponibilidad|disponible|horarios?|cuando.*atender|hay.*espacio",
            r"libre|puede.*atender|primer.*cita"
        ]
        
        booking_patterns = [
            r"agendar|reservar|cita|turno|programar|quiero.*cita",
            r"necesito.*cita|solicitar.*cita"
        ]
        
        info_patterns = [
            r"duracion|tiempo|cuanto.*dura|preparacion|requisitos",
            r"antes.*de|informacion.*sobre|que.*necesito"
        ]
        
        # Evaluar patrones
        for pattern in availability_patterns:
            if re.search(pattern, question_lower):
                return "check_availability"
        
        for pattern in booking_patterns:
            if re.search(pattern, question_lower):
                return "create_appointment"
        
        for pattern in info_patterns:
            if re.search(pattern, question_lower):
                return "get_info"
        
        return "unknown"
    
    def _calculate_intent_confidence(self, question: str, intent: str) -> float:
        """Calcular score de confianza para la intención detectada"""
        # Implementación simple - puede mejorarse con ML
        if intent == "unknown":
            return 0.3
        
        # Contar keywords relacionadas
        question_lower = question.lower()
        
        intent_keywords = {
            "check_availability": ["disponibilidad", "horario", "cuando", "libre"],
            "create_appointment": ["agendar", "cita", "reservar", "turno"],
            "get_info": ["información", "duración", "preparación", "requisitos"]
        }
        
        keywords = intent_keywords.get(intent, [])
        matches = sum(1 for kw in keywords if kw in question_lower)
        
        # Normalizar
        confidence = min(0.5 + (matches * 0.15), 1.0)
        return confidence
    
    def _extract_scheduling_entities(
        self,
        question: str,
        chat_history: List
    ) -> Dict[str, Any]:
        """
        Extraer entidades relevantes para scheduling.
        
        Returns:
            Dict con: date, time, treatment, patient_info
        """
        entities = {
            "date": None,
            "time": None,
            "treatment": None,
            "patient_name": None
        }
        
        # Extraer fecha
        date_match = self._extract_date_from_text(question)
        if date_match:
            entities["date"] = date_match
        
        # Extraer hora
        time_match = self._extract_time_from_text(question)
        if time_match:
            entities["time"] = time_match
        
        # Extraer tratamiento
        treatment = self._extract_treatment_from_text(question)
        if treatment:
            entities["treatment"] = treatment
        
        # Buscar nombre en historial
        if chat_history:
            name = self._extract_name_from_history(chat_history)
            if name:
                entities["patient_name"] = name
        
        return entities
    
    def _extract_date_from_text(self, text: str) -> Optional[str]:
        """Extraer fecha del texto"""
        text_lower = text.lower()
        
        # Patrones de fecha
        date_patterns = [
            r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b',
            r'\b(\d{2,4})[/-](\d{1,2})[/-](\d{1,2})\b'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        
        # Fechas relativas
        from datetime import datetime, timedelta
        today = datetime.now()
        
        relative_dates = {
            'hoy': today,
            'mañana': today + timedelta(days=1),
            'pasado mañana': today + timedelta(days=2)
        }
        
        for word, date_obj in relative_dates.items():
            if word in text_lower:
                return date_obj.strftime("%d-%m-%Y")
        
        return None
    
    def _extract_time_from_text(self, text: str) -> Optional[str]:
        """Extraer hora del texto"""
        time_patterns = [
            r'\b(\d{1,2}):(\d{2})\s*(am|pm)?\b',
            r'\b(\d{1,2})\s*(am|pm|horas)\b'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text.lower())
            if match:
                return match.group(0)
        
        return None
    
    def _extract_treatment_from_text(self, text: str) -> Optional[str]:
        """Extraer tratamiento del texto"""
        text_lower = text.lower()
        
        # Obtener tratamientos de la configuración
        if hasattr(self.company_config, 'treatment_durations'):
            for treatment in self.company_config.treatment_durations.keys():
                if treatment.lower() in text_lower:
                    return treatment
        
        # Palabras clave genéricas
        treatment_keywords = [
            'limpieza', 'consulta', 'valoración', 'tratamiento',
            'procedimiento', 'botox', 'relleno', 'facial'
        ]
        
        for keyword in treatment_keywords:
            if keyword in text_lower:
                return keyword
        
        return None
    
    def _extract_name_from_history(self, chat_history: List) -> Optional[str]:
        """Extraer nombre del paciente del historial"""
        history_text = " ".join([
            msg.content if hasattr(msg, 'content') else str(msg)
            for msg in chat_history
        ]).lower()
        
        patterns = [
            r'mi nombre es ([a-záéíóúñ\s]+)',
            r'me llamo ([a-záéíóúñ\s]+)',
            r'soy ([a-záéíóúñ\s]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, history_text)
            if match:
                name = match.group(1).strip().title()
                if len(name.split()) >= 2:
                    return name
        
        return None
    
    # ========================================================================
    # HELPERS DE RAG
    # ========================================================================
    
    def _needs_rag_context(self, intent: str, question: str) -> bool:
        """Determinar si necesita contexto de RAG"""
        # Siempre usar RAG para info y disponibilidad
        if intent in ["get_info", "check_availability"]:
            return True
        
        # Verificar keywords que sugieren necesidad de info
        rag_keywords = [
            "duración", "tiempo", "preparación", "requisitos",
            "antes", "después", "información", "abono", "costo"
        ]
        
        return any(kw in question.lower() for kw in rag_keywords)
    
    def _build_rag_query(self, question: str, intent: str) -> str:
        """Construir query optimizada para RAG"""
        base_keywords = "cita agenda horario duración preparación requisitos"
        
        if intent == "get_info":
            return f"{base_keywords} información tratamiento {question}"
        elif intent == "check_availability":
            return f"{base_keywords} disponibilidad {question}"
        elif intent == "create_appointment":
            return f"{base_keywords} agendar reservar {question}"
        else:
            return f"{base_keywords} {question}"
    
    def _extract_rag_content(self, docs: List, intent: str) -> str:
        """Extraer contenido relevante de documentos RAG"""
        if not docs:
            return ""
        
        relevant_content = []
        
        # Keywords por intención
        intent_keywords = {
            "get_info": ["duración", "tiempo", "preparación", "requisitos", "abono"],
            "check_availability": ["horario", "disponibilidad", "agenda"],
            "create_appointment": ["agendar", "cita", "reservar", "requisitos"]
        }
        
        keywords = intent_keywords.get(intent, [])
        
        for doc in docs[:3]:  # Max 3 docs
            content = ""
            
            if hasattr(doc, 'page_content'):
                content = doc.page_content
            elif isinstance(doc, dict) and 'content' in doc:
                content = doc['content']
            
            if content:
                content_lower = content.lower()
                
                # Solo incluir si es relevante
                if any(kw in content_lower for kw in keywords):
                    relevant_content.append(content)
        
        return "\n\n".join(relevant_content) if relevant_content else ""
    
    def _get_basic_schedule_info(self) -> str:
        """Info básica de scheduling desde config"""
        info_parts = [
            f"Información de {self.company_config.company_name}:",
            f"Servicios: {self.company_config.services}"
        ]
        
        # Añadir duraciones si existen
        if hasattr(self.company_config, 'treatment_durations'):
            info_parts.append("\nDuraciones de tratamientos:")
            for treatment, duration in self.company_config.treatment_durations.items():
                info_parts.append(f"- {treatment}: {duration} minutos")
        
        return "\n".join(info_parts)
    
    # ========================================================================
    # SELECCIÓN Y EJECUCIÓN DE TOOLS
    # ========================================================================
    
    def _select_tools_for_intent(
        self,
        intent: str,
        entities: Dict[str, Any],
        state: AgentState
    ) -> List[Dict[str, Any]]:
        """
        Seleccionar herramientas basado en intención y entidades disponibles.
        
        Returns:
            Lista de configs de tools: [{"tool_name": str, "params": dict}, ...]
        """
        tools = []
        
        if intent == "check_availability":
            # Verificar disponibilidad
            if entities.get("date") and entities.get("treatment"):
                tools.append({
                    "tool_name": "get_available_slots",
                    "params": {
                        "date": entities["date"],
                        "treatment": entities["treatment"],
                        "company_id": self.company_config.company_id
                    }
                })
            else:
                # Necesita más info, no ejecutar tools aún
                pass
        
        elif intent == "create_appointment":
            # Validar datos primero
            if self._has_complete_booking_info(entities, state):
                tools.append({
                    "tool_name": "validate_appointment_data",
                    "params": {
                        "appointment_data": self._build_appointment_data(entities, state),
                        "company_id": self.company_config.company_id
                    }
                })
                
                # Luego crear cita
                tools.append({
                    "tool_name": "create_appointment",
                    "params": {
                        "datetime": f"{entities['date']} {entities.get('time', '10:00')}",
                        "patient_info": {
                            "name": entities.get("patient_name", "Pendiente"),
                            "treatment": entities.get("treatment", "Consulta general")
                        },
                        "service": entities.get("treatment", "Consulta general"),
                        "company_id": self.company_config.company_id
                    }
                })
        
        elif intent == "get_info":
            # Ya tenemos RAG context, no necesitamos tools adicionales
            pass
        
        return tools
    
    def _has_complete_booking_info(
        self,
        entities: Dict[str, Any],
        state: AgentState
    ) -> bool:
        """Verificar si tenemos info completa para booking"""
        required = ["date", "treatment"]
        return all(entities.get(field) for field in required)
    
    def _build_appointment_data(
        self,
        entities: Dict[str, Any],
        state: AgentState
    ) -> Dict[str, Any]:
        """Construir datos de cita"""
        return {
            "date": entities.get("date"),
            "time": entities.get("time", "10:00"),
            "treatment": entities.get("treatment"),
            "patient_name": entities.get("patient_name"),
            "company_id": self.company_config.company_id
        }
    
    def _execute_single_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
        state: AgentState
    ) -> Dict[str, Any]:
        """
        Ejecutar una herramienta individual.
        
        Usa AgentToolsService si está disponible, sino fallback a lógica directa.
        """
        if not self._tool_executor:
            return {
                "success": False,
                "error": "ToolExecutor not configured"
            }
        
        try:
            # Ejecutar con tool executor
            result = self._tool_executor.execute(
                tool_name=tool_name,
                params=params,
                company_id=self.company_config.company_id,
                user_id=state.get("user_id", "unknown")
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # ========================================================================
    # GENERACIÓN DE RESPUESTA FINAL
    # ========================================================================
    
    def _build_final_response(
        self,
        intent: str,
        entities: Dict[str, Any],
        tool_results: Dict[str, Any],
        rag_context: str,
        state: AgentState
    ) -> str:
        """
        Construir respuesta final sintetizando toda la información.
        """
        # Usar LLM para generar respuesta natural
        try:
            response_prompt = self._create_response_prompt()
            
            prompt_inputs = {
                "intent": intent,
                "entities": entities,
                "tool_results": tool_results,
                "rag_context": rag_context,
                "question": state["question"],
                "company_name": self.company_config.company_name,
                "services": self.company_config.services
            }
            
            # Generar con LLM
            response = (response_prompt | self.chat_model).invoke(prompt_inputs)
            
            if hasattr(response, 'content'):
                return response.content
            else:
                return str(response)
            
        except Exception as e:
            logger.error(f"Error generating response with LLM: {e}")
            
            # Fallback: generar respuesta programática
            return self._build_programmatic_response(
                intent, entities, tool_results, rag_context
            )
    
    def _create_response_prompt(self) -> ChatPromptTemplate:
        """Crear prompt para generación de respuesta"""
        template = """Eres un asistente de agendamiento para {company_name}.

INTENCIÓN DEL USUARIO: {intent}
ENTIDADES DETECTADAS: {entities}
RESULTADOS DE HERRAMIENTAS: {tool_results}
CONTEXTO ADICIONAL:
{rag_context}

PREGUNTA DEL USUARIO: {question}

SERVICIOS DISPONIBLES: {services}

INSTRUCCIONES:
1. Genera una respuesta clara y profesional
2. Si hay resultados de herramientas, úsalos en la respuesta
3. Si hay contexto adicional relevante, menciónalo apropiadamente
4. Sé conciso pero completo
5. Mantén un tono cálido y profesional

RESPUESTA:"""
        
        return ChatPromptTemplate.from_template(template)
    
    def _build_programmatic_response(
        self,
        intent: str,
        entities: Dict[str, Any],
        tool_results: Dict[str, Any],
        rag_context: str
    ) -> str:
        """Generar respuesta programática (fallback)"""
        if intent == "check_availability":
            if "get_available_slots" in tool_results:
                slots = tool_results["get_available_slots"]
                if slots:
                    return self._format_availability_response(slots, entities)
                else:
                    return f"No hay horarios disponibles para la fecha solicitada en {self.company_config.company_name}."
            else:
                return self._generate_availability_request_response(entities)
        
        elif intent == "create_appointment":
            if "create_appointment" in tool_results:
                booking_result = tool_results["create_appointment"]
                return self._format_booking_confirmation(booking_result)
            else:
                return self._generate_booking_request_response(entities)
        
        elif intent == "get_info":
            if rag_context:
                return f"Información sobre tratamientos en {self.company_config.company_name}:\n\n{rag_context[:500]}"
            else:
                return self._get_basic_schedule_info()
        
        else:
            return f"¿En qué puedo ayudarte con tu cita en {self.company_config.company_name}?"
    
    def _format_availability_response(
        self,
        slots: List,
        entities: Dict[str, Any]
    ) -> str:
        """Formatear respuesta de disponibilidad"""
        date = entities.get("date", "la fecha solicitada")
        treatment = entities.get("treatment", "el tratamiento")
        
        slots_text = "\n".join([f"- {slot}" for slot in slots[:5]])
        
        return (
            f"✅ Horarios disponibles para {treatment} el {date} "
            f"en {self.company_config.company_name}:\n\n"
            f"{slots_text}\n\n"
            f"¿Te gustaría reservar alguno de estos horarios?"
        )
    
    def _generate_availability_request_response(self, entities: Dict[str, Any]) -> str:
        """Generar respuesta solicitando más info para disponibilidad"""
        missing = []
        
        if not entities.get("date"):
            missing.append("📅 Fecha específica (DD-MM-YYYY)")
        
        if not entities.get("treatment"):
            missing.append(f"🩺 Tipo de servicio ({self.company_config.services})")
        
        if missing:
            return (
                f"Para consultar disponibilidad en {self.company_config.company_name}, "
                f"necesito:\n\n" + "\n".join(missing)
            )
        
        return "Consultando disponibilidad..."
    
    def _format_booking_confirmation(self, booking_result: Dict[str, Any]) -> str:
        """Formatear confirmación de booking"""
        if booking_result.get("success"):
            return (
                f"✅ ¡Cita agendada exitosamente en {self.company_config.company_name}!\n\n"
                f"Recibirás una confirmación por email con todos los detalles."
            )
        else:
            error = booking_result.get("error", "Error desconocido")
            return (
                f"❌ No pude completar el agendamiento: {error}\n\n"
                f"Te conectaré con un especialista de {self.company_config.company_name}."
            )
    
    def _generate_booking_request_response(self, entities: Dict[str, Any]) -> str:
        """Generar respuesta solicitando más info para booking"""
        required = ["fecha", "tipo de servicio", "nombre completo", "teléfono"]
        
        return (
            f"Para agendar tu cita en {self.company_config.company_name}, necesito:\n\n"
            + "\n".join([f"- {field}" for field in required])
        )
    
    # ========================================================================
    # HELPERS AUXILIARES
    # ========================================================================
    
    def _detect_integration_type(self) -> str:
        """Detectar tipo de integración de calendario"""
        schedule_url = self.company_config.schedule_service_url.lower()
        
        if 'google' in schedule_url:
            return 'google_calendar'
        elif 'calendly' in schedule_url:
            return 'calendly'
        elif 'cal.com' in schedule_url:
            return 'cal_com'
        else:
            return 'generic_rest'
    
    def _generate_error_response(self, error: str) -> str:
        """Generar respuesta de error"""
        return (
            f"Disculpa, tuve un problema procesando tu solicitud en "
            f"{self.company_config.company_name}. "
            f"¿Podrías intentarlo de nuevo o contactar directamente? 🙏"
        )
