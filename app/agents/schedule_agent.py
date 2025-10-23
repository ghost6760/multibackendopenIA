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
        Construir grafo de decisión para agendamiento.
        
        FLUJO:
        1. Analyze Intent → Clasificar intención (check/create/info)
        2. Extract Entities → Extraer fecha, hora, servicio, etc.
        3. Retrieve Context → Buscar información en RAG si es necesario
        4. Execute Tools → Ejecutar herramientas de calendario
        5. Generate Response → Respuesta final
        
        Returns:
            StateGraph de LangGraph
        """
        # Crear grafo
        workflow = StateGraph(AgentState)
        
        # Añadir nodos
        workflow.add_node("analyze_intent", self._analyze_intent_node)
        workflow.add_node("extract_entities", self._extract_entities_node)
        workflow.add_node("retrieve_context", self._retrieve_context_node)
        workflow.add_node("execute_tools", self._execute_tools_node)
        workflow.add_node("generate_response", self._generate_response_node)
        
        # Definir edges
        workflow.set_entry_point("analyze_intent")
        
        workflow.add_edge("analyze_intent", "extract_entities")
        workflow.add_edge("extract_entities", "retrieve_context")
        workflow.add_edge("retrieve_context", "execute_tools")
        workflow.add_edge("execute_tools", "generate_response")
        workflow.add_edge("generate_response", END)
        
        logger.info(
            f"[{self.company_config.company_id}] LangGraph built for ScheduleAgent"
        )
        
        return workflow
    
    # ========================================================================
    # NODOS DEL GRAFO
    # ========================================================================
    
    def _analyze_intent_node(self, state: AgentState) -> AgentState:
        """
        Nodo 1: Analizar intención del usuario.
        """
        state["current_node"] = "analyze_intent"
        
        question = state["question"]
        
        # Clasificar intención
        intent = self._classify_intent(question)
        
        # Guardar en contexto
        state["context"]["intent"] = intent
        
        # Registrar razonamiento
        reasoning_step = self._add_reasoning_step(
            state,
            NodeType.DECISION,
            "Analyzed user intent",
            thought=f"User question: '{question[:80]}'",
            decision=f"Intent: {intent}",
            confidence=0.8
        )
        
        state["reasoning_steps"].append(reasoning_step)
        
        logger.debug(
            f"[{self.company_config.company_id}] Intent classified as: {intent}"
        )
        
        return state
    
    def _extract_entities_node(self, state: AgentState) -> AgentState:
        """
        Nodo 2: Extraer entidades (fecha, hora, servicio, nombre, etc.).
        """
        state["current_node"] = "extract_entities"
        
        question = state["question"]
        intent = state["context"].get("intent", "get_info")
        
        # Extraer entidades según el intent
        entities = self._extract_scheduling_entities(question)
        
        # Guardar en contexto
        state["context"]["entities"] = entities
        
        # Registrar razonamiento
        reasoning_step = self._add_reasoning_step(
            state,
            NodeType.REASONING,
            "Extracted entities",
            observation=f"Found: {list(entities.keys())}",
            confidence=0.7
        )
        
        state["reasoning_steps"].append(reasoning_step)
        
        logger.debug(
            f"[{self.company_config.company_id}] Entities extracted: {entities}"
        )
        
        return state
    
    def _retrieve_context_node(self, state: AgentState) -> AgentState:
        """
        Nodo 3: Recuperar contexto de RAG si es necesario.
        """
        state["current_node"] = "retrieve_context"
        
        intent = state["context"].get("intent", "")
        entities = state["context"].get("entities", {})
        question = state["question"]
        
        # Solo buscar contexto si es necesario
        rag_context = ""
        
        if intent == "get_info" or entities.get("treatment"):
            # Construir query para RAG
            treatment = entities.get("treatment", "")
            search_query = f"informacion preparacion {treatment} cita procedimiento"
            
            if self._vectorstore_service:
                try:
                    docs = self._vectorstore_service.search(
                        query=search_query,
                        company_id=self.company_config.company_id,
                        k=2
                    )
                    
                    rag_context = self._extract_relevant_context(docs)
                    
                    logger.debug(
                        f"[{self.company_config.company_id}] Retrieved {len(docs)} docs from RAG"
                    )
                    
                except Exception as e:
                    logger.error(f"Error retrieving context from RAG: {e}")
        
        # Guardar en contexto
        state["context"]["rag_context"] = rag_context
        
        # Registrar razonamiento
        reasoning_step = self._add_reasoning_step(
            state,
            NodeType.TOOL_USE,
            "Retrieved context from RAG",
            observation=f"Context length: {len(rag_context)} chars"
        )
        
        state["reasoning_steps"].append(reasoning_step)
        
        return state
    
    def _execute_tools_node(self, state: AgentState) -> AgentState:
        """
        Nodo 4: Ejecutar herramientas de calendario.
        """
        state["current_node"] = "execute_tools"
        
        intent = state["context"].get("intent", "")
        entities = state["context"].get("entities", {})
        
        tool_results = {}
        
        # Ejecutar herramientas según el intent
        if intent == "create_appointment":
            # Validar datos requeridos
            if self._has_required_booking_data(entities):
                # Ejecutar create_appointment
                result = self._execute_create_appointment(entities, state)
                tool_results["create_appointment"] = result
            
        elif intent == "check_availability":
            # Verificar disponibilidad
            if entities.get("date"):
                result = self._execute_check_availability(entities, state)
                tool_results["get_available_slots"] = result
        
        # Guardar resultados
        state["context"]["tool_results"] = tool_results
        
        # Registrar razonamiento
        reasoning_step = self._add_reasoning_step(
            state,
            NodeType.TOOL_USE,
            "Executed scheduling tools",
            observation=f"Tools executed: {list(tool_results.keys())}"
        )
        
        state["reasoning_steps"].append(reasoning_step)
        
        logger.debug(
            f"[{self.company_config.company_id}] Tools executed: {list(tool_results.keys())}"
        )
        
        return state
    
    def _generate_response_node(self, state: AgentState) -> AgentState:
        """
        Nodo 5: Generar respuesta final.
        """
        state["current_node"] = "generate_response"
        
        intent = state["context"].get("intent", "")
        entities = state["context"].get("entities", {})
        tool_results = state["context"].get("tool_results", {})
        rag_context = state["context"].get("rag_context", "")
        
        # Generar respuesta
        response = self._build_final_response(
            intent,
            entities,
            tool_results,
            rag_context,
            state
        )
        
        state["response"] = response
        state["status"] = ExecutionStatus.SUCCESS.value
        state["completed_at"] = datetime.utcnow().isoformat()
        
        # Registrar razonamiento
        reasoning_step = self._add_reasoning_step(
            state,
            NodeType.RESPONSE_GENERATION,
            "Generated final response",
            observation=f"Response length: {len(response)} chars"
        )
        
        state["reasoning_steps"].append(reasoning_step)
        
        logger.debug(
            f"[{self.company_config.company_id}] Schedule response generated"
        )
        
        return state
    
    # ========================================================================
    # HELPERS DE ANÁLISIS
    # ========================================================================
    
    def _classify_intent(self, question: str) -> str:
        """
        Clasificar intención del usuario.
        
        Returns:
            "create_appointment", "check_availability", "get_info"
        """
        question_lower = question.lower()
        
        # Create appointment
        create_keywords = [
            "agendar", "reservar", "programar", "solicitar",
            "cita", "turno", "hora"
        ]
        if any(kw in question_lower for kw in create_keywords):
            return "create_appointment"
        
        # Check availability
        availability_keywords = [
            "disponibilidad", "horarios", "cuando", "libre",
            "hay", "puede"
        ]
        if any(kw in question_lower for kw in availability_keywords):
            return "check_availability"
        
        # Get info (default)
        return "get_info"
    
    def _extract_scheduling_entities(self, question: str) -> Dict[str, Any]:
        """Extraer entidades de scheduling (fecha, hora, servicio, etc.)"""
        entities = {}
        
        # Extraer fecha (simplificado)
        date_patterns = [
            r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',  # DD-MM-YYYY
            r'mañana',
            r'hoy',
            r'lunes|martes|miercoles|jueves|viernes|sabado|domingo'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, question.lower())
            if match:
                entities["date"] = match.group()
                break
        
        # Extraer hora (simplificado)
        time_patterns = [
            r'\d{1,2}:\d{2}',  # HH:MM
            r'\d{1,2}\s*(am|pm)',
            r'mañana|tarde|noche'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, question.lower())
            if match:
                entities["time"] = match.group()
                break
        
        # Extraer tratamiento/servicio
        services_config = self.company_config.services
        if isinstance(services_config, dict):
            for service_name in services_config.keys():
                if service_name.lower() in question.lower():
                    entities["treatment"] = service_name
                    break
        
        return entities
    
    def _extract_relevant_context(self, docs: List) -> str:
        """Extraer contexto relevante de documentos RAG"""
        if not docs:
            return ""
        
        relevant_content = []
        
        for doc in docs[:2]:
            content = ""
            
            if hasattr(doc, 'page_content'):
                content = doc.page_content
            elif isinstance(doc, dict) and 'content' in doc:
                content = doc['content']
            
            if content:
                relevant_content.append(content)
        
        return "\n\n".join(relevant_content) if relevant_content else ""
    
    def _has_required_booking_data(self, entities: Dict[str, Any]) -> bool:
        """Verificar si tenemos datos mínimos para booking"""
        required = ["date", "treatment"]
        return all(entities.get(field) for field in required)
    
    def _execute_create_appointment(
        self,
        entities: Dict[str, Any],
        state: AgentState
    ) -> Dict[str, Any]:
        """Ejecutar creación de cita (stub - requiere integración real)"""
        # Por ahora, retornar éxito simulado
        # En producción, esto llamaría al servicio de calendario real
        
        logger.info(
            f"[{self.company_config.company_id}] Creating appointment: {entities}"
        )
        
        return {
            "success": True,
            "appointment_id": "mock_id_123",
            "message": "Appointment created successfully"
        }
    
    def _execute_check_availability(
        self,
        entities: Dict[str, Any],
        state: AgentState
    ) -> List[str]:
        """Consultar disponibilidad (stub - requiere integración real)"""
        # Por ahora, retornar horarios simulados
        # En producción, esto consultaría el calendario real
        
        logger.info(
            f"[{self.company_config.company_id}] Checking availability: {entities}"
        )
        
        return [
            "09:00 AM",
            "11:00 AM",
            "02:00 PM",
            "04:00 PM"
        ]
    
    def _get_basic_schedule_info(self) -> str:
        """Información básica de agendamiento"""
        return (
            f"Para agendar una cita en {self.company_config.company_name}, "
            f"puedo ayudarte con:\n\n"
            f"- Consultar disponibilidad de horarios\n"
            f"- Agendar citas para {self.company_config.services}\n"
            f"- Información sobre preparación para procedimientos\n\n"
            f"¿Qué necesitas?"
        )
    
    # ========================================================================
    # GENERACIÓN DE RESPUESTA
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
        Construir respuesta final usando _run_graph_prompt.
        """
        try:
            # Preparar template
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
            
            # Preparar variables
            extra_vars = {
                "intent": intent,
                "entities": str(entities),
                "tool_results": str(tool_results),
                "rag_context": rag_context,
                "question": state["question"],
                "company_name": self.company_config.company_name,
                "services": str(self.company_config.services)
            }
            
            # Usar _run_graph_prompt de base cognitiva
            response_content = self._run_graph_prompt(
                agent_key="schedule",
                template=template,
                extra_vars=extra_vars,
                state=state
            )
            
            return response_content
            
        except Exception as e:
            logger.error(f"Error generating response with LLM: {e}")
            
            # Fallback programático
            return self._build_programmatic_response(
                intent, entities, tool_results, rag_context
            )
    
    def _build_programmatic_response(
        self,
        intent: str,
        entities: Dict[str, Any],
        tool_results: Dict[str, Any],
        rag_context: str
    ) -> str:
        """Generar respuesta programática - VERSIÓN MEJORADA"""
        
        if intent == "create_appointment":
            # Si tools se ejecutaron exitosamente
            if "create_appointment" in tool_results:
                booking_result = tool_results["create_appointment"]
                return self._format_booking_confirmation(booking_result)
            
            # Verificar datos disponibles
            confirmed_data = []
            missing_data = []
            
            if entities.get("date"):
                confirmed_data.append(f"✅ Fecha: {entities['date']}")
            else:
                missing_data.append("📅 Fecha específica (ej: 'el lunes', 'mañana', '15-01-2025')")
            
            if entities.get("time"):
                confirmed_data.append(f"✅ Hora: {entities['time']}")
            else:
                missing_data.append("🕐 Hora preferida")
            
            if entities.get("treatment"):
                confirmed_data.append(f"✅ Servicio: {entities['treatment']}")
            else:
                missing_data.append(f"🩺 Servicio ({self.company_config.services})")
            
            if entities.get("patient_name"):
                confirmed_data.append(f"✅ Nombre: {entities['patient_name']}")
            else:
                missing_data.append("👤 Nombre completo")
            
            # Construir respuesta
            service_name = entities.get("treatment", "cita")
            response = f"Perfecto, te ayudo a agendar tu {service_name} en {self.company_config.company_name}. 📋\n\n"
            
            if confirmed_data:
                response += "**Datos confirmados:**\n" + "\n".join(confirmed_data) + "\n\n"
            
            if missing_data:
                response += "**Para completar tu reserva necesito:**\n" + "\n".join(missing_data)
            else:
                response += "¿Confirmas estos datos para proceder con la reserva?"
            
            return response
        
        elif intent == "check_availability":
            if "get_available_slots" in tool_results:
                slots = tool_results["get_available_slots"]
                if slots:
                    return self._format_availability_response(slots, entities)
                else:
                    return f"No hay horarios disponibles para la fecha solicitada en {self.company_config.company_name}."
            else:
                return self._generate_availability_request_response(entities)
        
        elif intent == "get_info":
            if rag_context:
                return f"Información sobre servicios en {self.company_config.company_name}:\n\n{rag_context[:500]}"
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
    
    # ========================================================================
    # MÉTODOS LEGACY (MANTENER PARA COMPATIBILIDAD)
    # ========================================================================
    
    def check_availability(
        self,
        question: str,
        chat_history: list,
        schedule_context: Dict[str, Any]
    ) -> str:
        """
        Método legacy llamado por otros agentes.
        
        Redirige a invoke() con formato correcto.
        """
        inputs = {
            "question": question,
            "chat_history": chat_history,
            "user_id": schedule_context.get("user_id", "availability_check"),
            "company_id": schedule_context.get("company_id", self.company_config.company_id)
        }
        
        return self.invoke(inputs)
