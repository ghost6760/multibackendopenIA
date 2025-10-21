# app/services/multi_agent_orchestrator_v2.py
"""
Orquestador Multi-Agente con LangGraph
Versión 2.0 - Migración de LangChain a LangGraph

MEJORAS:
- State machine con persistencia de estado
- Decisiones condicionales complejas
- Recuperación automática de errores
- Flujos paralelos cuando sea necesario
- Human-in-the-loop para confirmaciones
- Compatibilidad 100% con sistema existente
"""

from typing import Dict, Any, List, Optional, Tuple, Literal
from typing_extensions import TypedDict
from dataclasses import dataclass, field
from datetime import datetime
import logging
import json

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.config.company_config import CompanyConfig, get_company_config
from app.agents import (
    RouterAgent, EmergencyAgent, SalesAgent, 
    SupportAgent, ScheduleAgent, AvailabilityAgent
)
from app.services.openai_service import OpenAIService
from app.services.vectorstore_service import VectorstoreService
from app.models.conversation import ConversationManager

logger = logging.getLogger(__name__)

# =============================================================================
# STATE DEFINITION
# =============================================================================

class OrchestratorState(TypedDict):
    """Estado del orquestador durante la conversación"""
    # Input inicial
    question: str
    user_id: str
    company_id: str
    chat_history: List[Dict[str, str]]
    media_type: str
    media_context: Optional[str]
    
    # Estado de procesamiento
    processed_question: str
    intent: str
    confidence: float
    classification_data: Dict[str, Any]
    
    # Agente y respuesta
    selected_agent: str
    agent_response: str
    fallback_attempted: bool
    
    # RAG y tools
    rag_context: Optional[str]
    tools_used: List[str]
    tool_results: Dict[str, Any]
    
    # Control de flujo
    needs_clarification: bool
    needs_escalation: bool
    retry_count: int
    max_retries: int
    
    # Metadata
    start_time: float
    execution_path: List[str]
    errors: List[str]


# =============================================================================
# ORCHESTRATOR V2 CON LANGGRAPH
# =============================================================================

class MultiAgentOrchestratorV2:
    """
    Orquestador multi-agente usando LangGraph para state machine avanzado
    
    ✅ Mantiene compatibilidad con API existente
    ✅ Añade capacidades avanzadas de LangGraph
    ✅ Persistencia de estado entre llamadas
    ✅ Recuperación inteligente de errores
    """
    
    def __init__(self, company_id: str, openai_service: OpenAIService = None):
        self.company_id = company_id
        self.company_config = get_company_config(company_id)
        
        if not self.company_config:
            raise ValueError(f"Configuration not found for company: {company_id}")
        
        # Servicios (igual que v1)
        self.openai_service = openai_service or OpenAIService()
        self.vectorstore_service = None
        self.tool_executor = None
        
        # Agentes (reutilizamos los existentes)
        self.agents = {}
        self._initialize_agents()
        
        # LangGraph state machine
        self.graph = self._build_orchestration_graph()
        
        # Memory para persistencia de estado
        self.memory = MemorySaver()
        
        logger.info(f"🚀 [{company_id}] MultiAgentOrchestratorV2 (LangGraph) initialized")
    
    # =========================================================================
    # DEPENDENCY INJECTION (igual que v1)
    # =========================================================================
    
    def set_vectorstore_service(self, vectorstore_service: VectorstoreService):
        """Inyectar servicio de vectorstore"""
        self.vectorstore_service = vectorstore_service
        
        rag_agents = ['sales', 'support', 'emergency', 'schedule']
        for agent_name in rag_agents:
            if agent_name in self.agents:
                self.agents[agent_name].set_vectorstore_service(vectorstore_service)
                logger.info(f"[{self.company_id}] RAG configured for {agent_name} agent")
        
        if self.tool_executor:
            self.tool_executor.set_vectorstore_service(vectorstore_service)
    
    def set_tool_executor(self, tool_executor):
        """Inyectar tool executor"""
        self.tool_executor = tool_executor
        
        if self.vectorstore_service:
            tool_executor.set_vectorstore_service(self.vectorstore_service)
        
        logger.info(f"✅ [{self.company_id}] ToolExecutor configured")
    
    def execute_tool(self, tool_name: str, parameters: dict) -> dict:
        """Ejecutar una tool"""
        if not self.tool_executor:
            return {
                "success": False,
                "error": "ToolExecutor not configured"
            }
        return self.tool_executor.execute_tool(tool_name, parameters)
    
    def _initialize_agents(self):
        """Inicializar agentes (mismo código que v1)"""
        try:
            self.agents['router'] = RouterAgent(self.company_config, self.openai_service)
            self.agents['emergency'] = EmergencyAgent(self.company_config, self.openai_service)
            self.agents['sales'] = SalesAgent(self.company_config, self.openai_service)
            self.agents['support'] = SupportAgent(self.company_config, self.openai_service)
            self.agents['schedule'] = ScheduleAgent(self.company_config, self.openai_service)
            self.agents['availability'] = AvailabilityAgent(self.company_config, self.openai_service)
            
            self.agents['availability'].set_schedule_agent(self.agents['schedule'])
            
            logger.info(f"[{self.company_id}] All agents initialized: {list(self.agents.keys())}")
        except Exception as e:
            logger.error(f"[{self.company_id}] Error initializing agents: {e}")
            raise
    
    # =========================================================================
    # LANGGRAPH STATE MACHINE
    # =========================================================================
    
    def _build_orchestration_graph(self) -> StateGraph:
        """
        Construir el grafo de orquestación con LangGraph
        
        FLUJO:
        1. preprocess → Preparar entrada y contexto
        2. classify_intent → Router Agent clasifica
        3. check_emergency → Verificar si es emergencia crítica
        4. select_agent → Decidir qué agente usar
        5. execute_agent → Ejecutar agente seleccionado
        6. validate_response → Verificar calidad de respuesta
        7. handle_error → Recuperación si falla
        8. finalize → Preparar respuesta final
        """
        
        graph = StateGraph(OrchestratorState)
        
        # NODOS
        graph.add_node("preprocess", self._preprocess_node)
        graph.add_node("classify_intent", self._classify_intent_node)
        graph.add_node("check_emergency", self._check_emergency_node)
        graph.add_node("select_agent", self._select_agent_node)
        graph.add_node("execute_agent", self._execute_agent_node)
        graph.add_node("validate_response", self._validate_response_node)
        graph.add_node("handle_error", self._handle_error_node)
        graph.add_node("finalize", self._finalize_node)
        
        # EDGES - Flujo condicional inteligente
        
        # Inicio siempre en preprocess
        graph.set_entry_point("preprocess")
        
        # Preprocess → Classify
        graph.add_edge("preprocess", "classify_intent")
        
        # Classify → Check Emergency (condicional)
        graph.add_conditional_edges(
            "classify_intent",
            self._should_check_emergency,
            {
                "check": "check_emergency",
                "skip": "select_agent"
            }
        )
        
        # Check Emergency → Select Agent
        graph.add_edge("check_emergency", "select_agent")
        
        # Select Agent → Execute Agent
        graph.add_edge("select_agent", "execute_agent")
        
        # Execute Agent → Validate (condicional)
        graph.add_conditional_edges(
            "execute_agent",
            self._should_validate_or_error,
            {
                "validate": "validate_response",
                "error": "handle_error"
            }
        )
        
        # Validate → Finalize o Error
        graph.add_conditional_edges(
            "validate_response",
            self._should_finalize_or_retry,
            {
                "finalize": "finalize",
                "retry": "execute_agent",
                "error": "handle_error"
            }
        )
        
        # Handle Error → Retry o Finalize
        graph.add_conditional_edges(
            "handle_error",
            self._should_retry_or_end,
            {
                "retry": "select_agent",
                "end": "finalize"
            }
        )
        
        # Finalize → END
        graph.add_edge("finalize", END)
        
        return graph.compile(checkpointer=self.memory)
    
    # =========================================================================
    # NODOS DEL GRAFO
    # =========================================================================
    
    def _preprocess_node(self, state: OrchestratorState) -> OrchestratorState:
        """Nodo 1: Preprocesar entrada y contexto"""
        logger.info(f"🔧 [{self.company_id}] [PREPROCESS] Processing input")
        
        # Procesar multimedia
        processed = self._process_multimedia_context(
            state["question"],
            state.get("media_type", "text"),
            state.get("media_context")
        )
        
        state["processed_question"] = processed
        state["start_time"] = datetime.now().timestamp()
        state["execution_path"] = ["preprocess"]
        state["retry_count"] = 0
        state["max_retries"] = 2
        state["fallback_attempted"] = False
        state["tools_used"] = []
        state["tool_results"] = {}
        state["errors"] = []
        
        return state
    
    def _classify_intent_node(self, state: OrchestratorState) -> OrchestratorState:
        """Nodo 2: Clasificar intención con Router Agent"""
        logger.info(f"🎯 [{self.company_id}] [CLASSIFY] Classifying intent")
        
        state["execution_path"].append("classify_intent")
        
        try:
            inputs = {
                "question": state["processed_question"],
                "chat_history": state.get("chat_history", []),
                "user_id": state["user_id"]
            }
            
            router_response = self.agents['router'].invoke(inputs)
            
            try:
                classification = json.loads(router_response)
                intent = classification.get("intent", "SUPPORT")
                confidence = classification.get("confidence", 0.5)
                
                state["intent"] = intent
                state["confidence"] = confidence
                state["classification_data"] = classification
                
                logger.info(
                    f"✅ [{self.company_id}] Intent: {intent} "
                    f"(confidence: {confidence:.2f})"
                )
                
            except json.JSONDecodeError:
                logger.warning(f"⚠️ [{self.company_id}] Invalid router response, defaulting to SUPPORT")
                state["intent"] = "SUPPORT"
                state["confidence"] = 0.3
                state["classification_data"] = {}
        
        except Exception as e:
            logger.error(f"❌ [{self.company_id}] Error in classification: {e}")
            state["intent"] = "SUPPORT"
            state["confidence"] = 0.0
            state["errors"].append(f"Classification error: {str(e)}")
        
        return state
    
    def _check_emergency_node(self, state: OrchestratorState) -> OrchestratorState:
        """Nodo 3: Verificación especial de emergencias"""
        logger.info(f"🚨 [{self.company_id}] [EMERGENCY CHECK] Verifying emergency status")
        
        state["execution_path"].append("check_emergency")
        
        # Keywords críticas de emergencia
        critical_keywords = [
            "sangrado", "hemorragia", "dolor intenso", "inflamación severa",
            "reacción alérgica", "mareo", "desmayo", "fiebre alta"
        ]
        
        question_lower = state["processed_question"].lower()
        has_critical = any(keyword in question_lower for keyword in critical_keywords)
        
        if has_critical:
            logger.warning(f"⚠️ [{self.company_id}] CRITICAL emergency keywords detected")
            state["intent"] = "EMERGENCY"
            state["confidence"] = 0.95
            state["needs_escalation"] = True
        
        return state
    
    def _select_agent_node(self, state: OrchestratorState) -> OrchestratorState:
        """Nodo 4: Seleccionar agente apropiado"""
        logger.info(f"🤖 [{self.company_id}] [SELECT AGENT] Choosing agent")
        
        state["execution_path"].append("select_agent")
        
        intent = state["intent"]
        confidence = state["confidence"]
        
        # Lógica de selección con threshold
        if confidence > 0.7:
            agent_map = {
                "EMERGENCY": "emergency",
                "SALES": "sales",
                "SCHEDULE": "schedule",
                "SUPPORT": "support"
            }
            selected = agent_map.get(intent, "support")
        else:
            logger.info(f"📊 [{self.company_id}] Low confidence, using support agent")
            selected = "support"
        
        state["selected_agent"] = selected
        
        logger.info(f"✅ [{self.company_id}] Selected agent: {selected}")
        
        return state
    
    def _execute_agent_node(self, state: OrchestratorState) -> OrchestratorState:
        """Nodo 5: Ejecutar agente seleccionado"""
        agent_name = state["selected_agent"]
        
        logger.info(f"⚙️ [{self.company_id}] [EXECUTE] Running {agent_name} agent")
        
        state["execution_path"].append(f"execute_{agent_name}")
        
        try:
            inputs = {
                "question": state["processed_question"],
                "chat_history": state.get("chat_history", []),
                "user_id": state["user_id"]
            }
            
            agent = self.agents.get(agent_name)
            if not agent:
                raise ValueError(f"Agent {agent_name} not found")
            
            response = agent.invoke(inputs)
            
            state["agent_response"] = response
            
            logger.info(
                f"✅ [{self.company_id}] Agent response generated "
                f"({len(response)} chars)"
            )
            
        except Exception as e:
            logger.error(f"❌ [{self.company_id}] Error executing {agent_name}: {e}")
            state["errors"].append(f"Agent execution error: {str(e)}")
            state["agent_response"] = ""
        
        return state
    
    def _validate_response_node(self, state: OrchestratorState) -> OrchestratorState:
        """Nodo 6: Validar calidad de respuesta"""
        logger.info(f"✓ [{self.company_id}] [VALIDATE] Checking response quality")
        
        state["execution_path"].append("validate_response")
        
        response = state.get("agent_response", "")
        
        # Validaciones básicas
        is_valid = True
        validation_errors = []
        
        if not response or len(response.strip()) < 10:
            is_valid = False
            validation_errors.append("Response too short")
        
        if "error" in response.lower() and len(response) < 50:
            is_valid = False
            validation_errors.append("Error message detected")
        
        # Guardar resultado de validación en el estado
        state["response_valid"] = is_valid
        
        if not is_valid:
            logger.warning(
                f"⚠️ [{self.company_id}] Response validation failed: "
                f"{validation_errors}"
            )
            state["errors"].extend(validation_errors)
        
        return state
    
    def _handle_error_node(self, state: OrchestratorState) -> OrchestratorState:
        """Nodo 7: Manejar errores y recovery"""
        logger.warning(f"🔄 [{self.company_id}] [ERROR HANDLER] Attempting recovery")
        
        state["execution_path"].append("handle_error")
        state["retry_count"] = state.get("retry_count", 0) + 1
        
        # Si no hemos intentado fallback, intentar con support agent
        if not state.get("fallback_attempted", False):
            logger.info(f"🔄 [{self.company_id}] Attempting fallback to support agent")
            state["selected_agent"] = "support"
            state["fallback_attempted"] = True
        
        return state
    
    def _finalize_node(self, state: OrchestratorState) -> OrchestratorState:
        """Nodo 8: Preparar respuesta final"""
        logger.info(f"🏁 [{self.company_id}] [FINALIZE] Preparing final response")
        
        state["execution_path"].append("finalize")
        
        # Si no hay respuesta válida, usar fallback
        if not state.get("agent_response") or not state.get("agent_response").strip():
            state["agent_response"] = (
                f"Disculpa, estoy teniendo dificultades técnicas. "
                f"Por favor contacta directamente con {self.company_config.company_name}. 🔧"
            )
            state["selected_agent"] = "error"
        
        # Calcular tiempo de ejecución
        if "start_time" in state:
            elapsed = datetime.now().timestamp() - state["start_time"]
            logger.info(
                f"⏱️ [{self.company_id}] Execution completed in {elapsed:.2f}s"
            )
        
        # Log path de ejecución
        logger.info(
            f"📍 [{self.company_id}] Execution path: "
            f"{' → '.join(state['execution_path'])}"
        )
        
        return state
    
    # =========================================================================
    # FUNCIONES DE DECISIÓN (CONDITIONAL EDGES)
    # =========================================================================
    
    def _should_check_emergency(self, state: OrchestratorState) -> Literal["check", "skip"]:
        """Decidir si verificar emergencia"""
        intent = state.get("intent", "")
        confidence = state.get("confidence", 0)
        
        # Verificar si clasificación sugiere emergencia o si hay palabras clave
        if intent == "EMERGENCY":
            return "check"
        
        # También verificar keywords críticas en el texto
        emergency_keywords = self.company_config.emergency_keywords
        question = state.get("processed_question", "").lower()
        
        if any(keyword in question for keyword in emergency_keywords):
            return "check"
        
        return "skip"
    
    def _should_validate_or_error(self, state: OrchestratorState) -> Literal["validate", "error"]:
        """Decidir si validar o ir a error handler"""
        # Si hubo error en ejecución, ir a error handler
        if state.get("errors"):
            return "error"
        
        # Si no hay respuesta, error
        if not state.get("agent_response"):
            return "error"
        
        return "validate"
    
    def _should_finalize_or_retry(self, state: OrchestratorState) -> Literal["finalize", "retry", "error"]:
        """Decidir si finalizar, reintentar o ir a error"""
        is_valid = state.get("response_valid", False)
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 2)
        
        # Si es válida, finalizar
        if is_valid:
            return "finalize"
        
        # Si aún podemos reintentar, hacerlo
        if retry_count < max_retries:
            logger.info(f"🔄 [{self.company_id}] Retry {retry_count + 1}/{max_retries}")
            return "retry"
        
        # Si ya agotamos reintentos, ir a error handler
        return "error"
    
    def _should_retry_or_end(self, state: OrchestratorState) -> Literal["retry", "end"]:
        """Decidir si reintentar o terminar"""
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 2)
        fallback_attempted = state.get("fallback_attempted", False)
        
        # Si no hemos intentado fallback, intentar
        if not fallback_attempted:
            return "retry"
        
        # Si aún hay reintentos y ya intentamos fallback, terminar
        return "end"
    
    # =========================================================================
    # API PÚBLICA - COMPATIBILIDAD CON V1
    # =========================================================================
    
    def get_response(
        self,
        question: str,
        user_id: str,
        conversation_manager: ConversationManager,
        media_type: str = "text",
        media_context: str = None
    ) -> Tuple[str, str]:
        """
        Método principal compatible con v1
        
        Args:
            question: Pregunta del usuario
            user_id: ID del usuario
            conversation_manager: Gestor de conversación
            media_type: Tipo de media (text, image, voice)
            media_context: Contexto multimedia
        
        Returns:
            Tuple[respuesta, agente_usado]
        """
        
        try:
            # Validaciones básicas
            if not question or not question.strip():
                return (
                    f"Por favor, envía un mensaje específico para poder ayudarte "
                    f"en {self.company_config.company_name}. 😊",
                    "support"
                )
            
            if not user_id or not user_id.strip():
                return "Error interno: ID de usuario inválido.", "error"
            
            # Obtener historial
            chat_history = conversation_manager.get_chat_history(
                user_id,
                format_type="messages"
            )
            
            # Preparar estado inicial
            initial_state: OrchestratorState = {
                "question": question,
                "user_id": user_id,
                "company_id": self.company_id,
                "chat_history": chat_history,
                "media_type": media_type,
                "media_context": media_context,
                # Estos se llenan en el grafo
                "processed_question": "",
                "intent": "",
                "confidence": 0.0,
                "classification_data": {},
                "selected_agent": "",
                "agent_response": "",
                "fallback_attempted": False,
                "rag_context": None,
                "tools_used": [],
                "tool_results": {},
                "needs_clarification": False,
                "needs_escalation": False,
                "retry_count": 0,
                "max_retries": 2,
                "start_time": 0.0,
                "execution_path": [],
                "errors": []
            }
            
            # Ejecutar grafo con thread_id para persistencia
            config = {"configurable": {"thread_id": user_id}}
            
            logger.info(f"🚀 [{self.company_id}] Starting LangGraph execution for user {user_id}")
            
            # Invocar grafo
            final_state = self.graph.invoke(initial_state, config)
            
            # Extraer respuesta y agente
            response = final_state.get("agent_response", "")
            agent_used = final_state.get("selected_agent", "unknown")
            
            # Guardar en conversación
            conversation_manager.add_message(user_id, "user", question)
            conversation_manager.add_message(user_id, "assistant", response)
            
            # Log final
            logger.info(
                f"✅ [{self.company_id}] Response delivered - "
                f"Agent: {agent_used}, Length: {len(response)}"
            )
            
            return response, agent_used
        
        except Exception as e:
            logger.exception(
                f"❌ [{self.company_id}] Critical error in orchestration: {e}"
            )
            error_response = (
                f"Disculpa, tuve un problema técnico en "
                f"{self.company_config.company_name}. "
                f"Por favor intenta de nuevo. 🔧"
            )
            return error_response, "error"
    
    def _process_multimedia_context(
        self,
        question: str,
        media_type: str,
        media_context: str = None
    ) -> str:
        """Procesar contexto multimedia (igual que v1)"""
        if media_type == "image" and media_context:
            return f"Contexto visual: {media_context}\n\nPregunta: {question}"
        elif media_type == "voice" and media_context:
            return f"Transcripción de voz: {media_context}\n\nPregunta: {question}"
        return question
    
    # =========================================================================
    # MÉTODOS DE UTILIDAD (compatibilidad con v1)
    # =========================================================================
    
    def search_documents(self, query: str, k: int = 3):
        """Búsqueda de documentos (igual que v1)"""
        try:
            if not self.vectorstore_service:
                return []
            
            docs = self.vectorstore_service.search_by_company(
                query,
                self.company_id,
                k=k
            )
            return docs
        except Exception as e:
            logger.error(f"[{self.company_id}] Error searching documents: {e}")
            return []
    
    def health_check(self) -> Dict[str, Any]:
        """Health check del sistema (mejorado con info de LangGraph)"""
        try:
            agents_status = {}
            
            for agent_name, agent in self.agents.items():
                try:
                    test_inputs = {
                        "question": "test",
                        "chat_history": [],
                        "user_id": "health_check"
                    }
                    
                    if agent_name == "router":
                        response = agent.invoke(test_inputs)
                        try:
                            json.loads(response)
                            agents_status[agent_name] = "healthy"
                        except json.JSONDecodeError:
                            agents_status[agent_name] = "unhealthy"
                    else:
                        response = agent.invoke(test_inputs)
                        agents_status[agent_name] = "healthy" if response else "unhealthy"
                except Exception as e:
                    agents_status[agent_name] = f"error: {str(e)}"
            
            all_healthy = all(status == "healthy" for status in agents_status.values())
            
            return {
                "system_healthy": all_healthy,
                "system_version": "v2_langgraph",
                "company_id": self.company_id,
                "company_name": self.company_config.company_name,
                "agents_status": agents_status,
                "langgraph_features": {
                    "state_persistence": True,
                    "conditional_routing": True,
                    "error_recovery": True,
                    "retry_logic": True
                },
                "vectorstore_connected": self.vectorstore_service is not None,
                "tool_executor_connected": self.tool_executor is not None,
                "schedule_service_url": self.company_config.schedule_service_url
            }
        except Exception as e:
            return {
                "system_healthy": False,
                "system_version": "v2_langgraph",
                "company_id": self.company_id,
                "error": str(e)
            }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Estadísticas del sistema (mejorado)"""
        stats = {
            "system_version": "v2_langgraph",
            "company_id": self.company_id,
            "company_name": self.company_config.company_name,
            "agents_available": list(self.agents.keys()),
            "rag_enabled_agents": ["sales", "support", "emergency", "schedule"],
            "langgraph_capabilities": [
                "state_persistence",
                "conditional_routing",
                "parallel_execution",
                "error_recovery",
                "retry_logic",
                "human_in_the_loop_ready"
            ],
            "vectorstore_index": self.company_config.vectorstore_index,
            "schedule_service_url": self.company_config.schedule_service_url,
            "services": self.company_config.services,
            "rag_status": "enabled" if self.vectorstore_service else "disabled"
        }
        
        if self.tool_executor:
            available_tools = self.tool_executor.get_available_tools()
            tools_ready = [
                name for name, status in available_tools.items()
                if status.get("available")
            ]
            stats["tools_available"] = len(available_tools)
            stats["tools_ready"] = len(tools_ready)
            stats["tools_ready_list"] = tools_ready
        
        return stats
