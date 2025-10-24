# app/services/multi_agent_orchestrator.py
"""
Orquestador Multi-Agente con LangGraph
MIGRADO DIRECTAMENTE - No hay versión V1/V2

MEJORAS CON LANGGRAPH:
- State machine con persistencia de estado
- Decisiones condicionales inteligentes
- Recuperación automática de errores
- Retry logic con fallbacks
- Flujos paralelos preparados
"""

from typing import Dict, Any, List, Optional, Tuple, Literal
from typing_extensions import TypedDict
from datetime import datetime
import logging
import json

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

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
    # Input
    question: str
    user_id: str
    company_id: str
    chat_history: List[Dict[str, str]]
    media_type: str
    media_context: Optional[str]
    
    # Processing
    processed_question: str
    intent: str
    confidence: float
    classification_data: Dict[str, Any]
    
    # Agent execution
    selected_agent: str
    agent_response: str
    fallback_attempted: bool
    
    # RAG and tools
    rag_context: Optional[str]
    tools_used: List[str]
    tool_results: Dict[str, Any]
    
    # Flow control
    needs_clarification: bool
    needs_escalation: bool
    retry_count: int
    max_retries: int
    response_valid: bool
    
    # Metadata
    start_time: float
    execution_path: List[str]
    errors: List[str]


# =============================================================================
# MULTI-AGENT ORCHESTRATOR CON LANGGRAPH
# =============================================================================

class MultiAgentOrchestrator:
    """
    Orquestador multi-agente multi-tenant con LangGraph
    
    ✅ State machine avanzado
    ✅ Recuperación inteligente de errores
    ✅ Retry automático con fallbacks
    ✅ Persistencia de estado
    ✅ API compatible con sistema existente
    """
    
    def __init__(self, company_id: str, openai_service: OpenAIService = None):
        self.company_id = company_id
        self.company_config = get_company_config(company_id)
        
        if not self.company_config:
            raise ValueError(f"Configuration not found for company: {company_id}")
        
        # Servicios (igual que antes)
        self.openai_service = openai_service or OpenAIService()
        self.vectorstore_service = None
        self.tool_executor = None
        
        # Agentes (reutilizamos los existentes)
        self.agents = {}
        self._initialize_agents()
        
        # LangGraph state machine
        self.graph = self._build_orchestration_graph()
        
        # Memory para persistencia
        self.memory = MemorySaver()
        
        logger.info(f"🚀 [{company_id}] MultiAgentOrchestrator (LangGraph) initialized")
    
    # =========================================================================
    # DEPENDENCY INJECTION (sin cambios)
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
            logger.info(f"[{self.company_id}] RAG configured for tool_executor")
    
    def set_tool_executor(self, tool_executor):
        """Inyectar tool executor"""
        self.tool_executor = tool_executor
        
        if self.vectorstore_service:
            tool_executor.set_vectorstore_service(self.vectorstore_service)
            logger.info(f"[{self.company_id}] RAG auto-injected to tool_executor")
        
        available_tools = tool_executor.get_available_tools()
        tools_ready = [name for name, status in available_tools.items() if status.get("available")]
        
        logger.info(f"✅ [{self.company_id}] ToolExecutor configured")
        logger.info(f"   → Total tools: {len(available_tools)}")
        logger.info(f"   → Ready tools: {len(tools_ready)}")
        logger.info(f"   → Tools: {tools_ready}")
    
    def execute_tool(self, tool_name: str, parameters: dict) -> dict:
        """Ejecutar una tool desde el orquestador"""
        if not self.tool_executor:
            logger.warning(f"[{self.company_id}] ToolExecutor not configured")
            return {
                "success": False,
                "error": "ToolExecutor not configured for this company"
            }
        return self.tool_executor.execute_tool(tool_name, parameters)
    
    def _initialize_agents(self):
        """Inicializar agentes (sin cambios)"""
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
        Construir grafo de orquestación con LangGraph
        
        FLUJO:
        preprocess → classify → check_emergency → select → execute → validate → finalize
        Con manejo de errores y retry logic
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
        
        # FLUJO PRINCIPAL
        graph.set_entry_point("preprocess")
        graph.add_edge("preprocess", "classify_intent")
        
        # Decidir si verificar emergencia
        graph.add_conditional_edges(
            "classify_intent",
            self._should_check_emergency,
            {
                "check": "check_emergency",
                "skip": "select_agent"
            }
        )
        
        graph.add_edge("check_emergency", "select_agent")
        graph.add_edge("select_agent", "execute_agent")
        
        # Después de ejecutar agente: validar o error
        graph.add_conditional_edges(
            "execute_agent",
            self._should_validate_or_error,
            {
                "validate": "validate_response",
                "error": "handle_error"
            }
        )
        
        # Después de validar: finalizar, reintentar o error
        graph.add_conditional_edges(
            "validate_response",
            self._should_finalize_or_retry,
            {
                "finalize": "finalize",
                "retry": "execute_agent",
                "error": "handle_error"
            }
        )
        
        # Después de error: reintentar o terminar
        graph.add_conditional_edges(
            "handle_error",
            self._should_retry_or_end,
            {
                "retry": "select_agent",
                "end": "finalize"
            }
        )
        
        graph.add_edge("finalize", END)
        
        return graph.compile(checkpointer=self.memory)
    
    # =========================================================================
    # NODOS DEL GRAFO
    # =========================================================================
    
    def _preprocess_node(self, state: OrchestratorState) -> OrchestratorState:
        """Nodo 1: Preprocesar entrada"""
        logger.info(f"🔧 [{self.company_id}] [PREPROCESS] Processing input")
        
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
        state["response_valid"] = False
        
        return state
    
    def _classify_intent_node(self, state: OrchestratorState) -> OrchestratorState:
        """Nodo 2: Clasificar intención"""
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
                
                logger.info(f"✅ [{self.company_id}] Intent: {intent} (confidence: {confidence:.2f})")
                
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
        """Nodo 3: Verificación de emergencia"""
        logger.info(f"🚨 [{self.company_id}] [EMERGENCY CHECK] Verifying emergency")
        
        state["execution_path"].append("check_emergency")
        
        # Keywords críticas
        critical_keywords = [
            "sangrado", "hemorragia", "dolor intenso", "inflamación severa",
            "reacción alérgica", "mareo", "desmayo", "fiebre alta"
        ]
        
        question_lower = state["processed_question"].lower()
        has_critical = any(keyword in question_lower for keyword in critical_keywords)
        
        if has_critical:
            logger.warning(f"⚠️ [{self.company_id}] CRITICAL emergency detected")
            state["intent"] = "EMERGENCY"
            state["confidence"] = 0.95
            state["needs_escalation"] = True
        
        return state
    
    def _select_agent_node(self, state: OrchestratorState) -> OrchestratorState:
        """Nodo 4: Seleccionar agente"""
        logger.info(f"🤖 [{self.company_id}] [SELECT] Choosing agent")
        
        state["execution_path"].append("select_agent")
        
        intent = state["intent"]
        confidence = state["confidence"]
        
        # Selección con threshold
        if confidence > 0.7:
            agent_map = {
                "EMERGENCY": "emergency",
                "SALES": "sales",
                "SCHEDULE": "schedule",
                "SUPPORT": "support"
            }
            selected = agent_map.get(intent, "support")
        else:
            logger.info(f"📊 [{self.company_id}] Low confidence, using support")
            selected = "support"
        
        state["selected_agent"] = selected
        logger.info(f"✅ [{self.company_id}] Selected: {selected}")
        
        return state
    
    def _execute_agent_node(self, state: OrchestratorState) -> OrchestratorState:
        """Nodo 5: Ejecutar agente"""
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
            
            logger.info(f"✅ [{self.company_id}] Response generated ({len(response)} chars)")
            
        except Exception as e:
            logger.error(f"❌ [{self.company_id}] Error executing {agent_name}: {e}")
            state["errors"].append(f"Agent execution error: {str(e)}")
            state["agent_response"] = ""
        
        return state
    
    def _validate_response_node(self, state: OrchestratorState) -> OrchestratorState:
        """Nodo 6: Validar respuesta"""
        logger.info(f"✓ [{self.company_id}] [VALIDATE] Checking response quality")
        
        state["execution_path"].append("validate_response")
        
        response = state.get("agent_response", "")
        
        # Validaciones
        is_valid = True
        validation_errors = []
        
        if not response or len(response.strip()) < 10:
            is_valid = False
            validation_errors.append("Response too short")
        
        if "error" in response.lower() and len(response) < 50:
            is_valid = False
            validation_errors.append("Error message detected")
        
        state["response_valid"] = is_valid
        
        if not is_valid:
            logger.warning(f"⚠️ [{self.company_id}] Validation failed: {validation_errors}")
            state["errors"].extend(validation_errors)
        
        return state
    
    def _handle_error_node(self, state: OrchestratorState) -> OrchestratorState:
        """Nodo 7: Manejar errores"""
        logger.warning(f"🔄 [{self.company_id}] [ERROR] Attempting recovery")
        
        state["execution_path"].append("handle_error")
        state["retry_count"] = state.get("retry_count", 0) + 1
        
        # Fallback a support si no se ha intentado
        if not state.get("fallback_attempted", False):
            logger.info(f"🔄 [{self.company_id}] Fallback to support agent")
            state["selected_agent"] = "support"
            state["fallback_attempted"] = True
        
        return state
    
    def _finalize_node(self, state: OrchestratorState) -> OrchestratorState:
        """Nodo 8: Finalizar"""
        logger.info(f"🏁 [{self.company_id}] [FINALIZE] Preparing final response")
        
        state["execution_path"].append("finalize")
        
        # Fallback si no hay respuesta válida
        if not state.get("agent_response") or not state.get("agent_response").strip():
            state["agent_response"] = (
                f"Disculpa, estoy teniendo dificultades técnicas. "
                f"Por favor contacta directamente con {self.company_config.company_name}. 🔧"
            )
            state["selected_agent"] = "error"
        
        # Log tiempo de ejecución
        if "start_time" in state:
            elapsed = datetime.now().timestamp() - state["start_time"]
            logger.info(f"⏱️ [{self.company_id}] Completed in {elapsed:.2f}s")
        
        logger.info(f"📍 [{self.company_id}] Path: {' → '.join(state['execution_path'])}")
        
        return state
    
    # =========================================================================
    # FUNCIONES DE DECISIÓN
    # =========================================================================
    
    def _should_check_emergency(self, state: OrchestratorState) -> Literal["check", "skip"]:
        """Decidir si verificar emergencia"""
        intent = state.get("intent", "")
        
        if intent == "EMERGENCY":
            return "check"
        
        # Verificar keywords en pregunta
        emergency_keywords = self.company_config.emergency_keywords
        question = state.get("processed_question", "").lower()
        
        if any(keyword in question for keyword in emergency_keywords):
            return "check"
        
        return "skip"
    
    def _should_validate_or_error(self, state: OrchestratorState) -> Literal["validate", "error"]:
        """Decidir si validar o manejar error"""
        if state.get("errors"):
            return "error"
        
        if not state.get("agent_response"):
            return "error"
        
        return "validate"
    
    def _should_finalize_or_retry(self, state: OrchestratorState) -> Literal["finalize", "retry", "error"]:
        """Decidir si finalizar, reintentar o error"""
        is_valid = state.get("response_valid", False)
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 2)
        
        if is_valid:
            return "finalize"
        
        if retry_count < max_retries:
            logger.info(f"🔄 [{self.company_id}] Retry {retry_count + 1}/{max_retries}")
            return "retry"
        
        return "error"
    
    def _should_retry_or_end(self, state: OrchestratorState) -> Literal["retry", "end"]:
        """Decidir si reintentar o terminar"""
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 2)
        fallback_attempted = state.get("fallback_attempted", False)
        
        if not fallback_attempted:
            return "retry"
        
        return "end"
    
    # =========================================================================
    # API PÚBLICA (COMPATIBLE CON SISTEMA EXISTENTE)
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
        Método principal - API compatible con sistema existente
        AHORA USA LANGGRAPH INTERNAMENTE
        """
        
        try:
            # Validaciones
            if not question or not question.strip():
                return (
                    f"Por favor, envía un mensaje específico para poder ayudarte "
                    f"en {self.company_config.company_name}. 😊",
                    "support"
                )
            
            if not user_id or not user_id.strip():
                return "Error interno: ID de usuario inválido.", "error"
            
            # Obtener historial
            chat_history = conversation_manager.get_chat_history(user_id, format_type="messages")
            
            # Preparar estado inicial
            initial_state: OrchestratorState = {
                "question": question,
                "user_id": user_id,
                "company_id": self.company_id,
                "chat_history": chat_history,
                "media_type": media_type,
                "media_context": media_context,
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
                "response_valid": False,
                "start_time": 0.0,
                "execution_path": [],
                "errors": []
            }
            
            # Ejecutar grafo con thread_id para persistencia
            config = {"configurable": {"thread_id": user_id}}
            
            logger.info(f"🚀 [{self.company_id}] Starting LangGraph execution for {user_id}")
            
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
            logger.exception(f"❌ [{self.company_id}] Critical error: {e}")
            error_response = (
                f"Disculpa, tuve un problema técnico en {self.company_config.company_name}. "
                f"Por favor intenta de nuevo. 🔧"
            )
            return error_response, "error"
    
    def _process_multimedia_context(
        self,
        question: str,
        media_type: str,
        media_context: str = None
    ) -> str:
        """Procesar contexto multimedia"""
        if media_type == "image" and media_context:
            return f"Contexto visual: {media_context}\n\nPregunta: {question}"
        elif media_type == "voice" and media_context:
            return f"Transcripción de voz: {media_context}\n\nPregunta: {question}"
        return question
    
    # =========================================================================
    # MÉTODOS DE UTILIDAD (sin cambios)
    # =========================================================================
    
    def search_documents(self, query: str, k: int = 3):
        """Búsqueda de documentos"""
        try:
            if not self.vectorstore_service:
                return []
            
            docs = self.vectorstore_service.search_by_company(query, self.company_id, k=k)
            return docs
        except Exception as e:
            logger.error(f"[{self.company_id}] Error searching documents: {e}")
            return []
    
    def health_check(self) -> Dict[str, Any]:
        """Health check del sistema"""
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
                "system_version": "langgraph",
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
                "system_version": "langgraph",
                "company_id": self.company_id,
                "error": str(e)
            }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Estadísticas del sistema"""
        stats = {
            "system_version": "langgraph",
            "company_id": self.company_id,
            "company_name": self.company_config.company_name,
            "agents_available": list(self.agents.keys()),
            "rag_enabled_agents": ["sales", "support", "emergency", "schedule"],
            "langgraph_capabilities": [
                "state_persistence",
                "conditional_routing",
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
