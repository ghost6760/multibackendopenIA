# app/services/multi_agent_orchestrator.py - FASE 1: BASE COGNITIVA

from typing import Dict, Any, List, Optional, Tuple
from app.config.company_config import CompanyConfig, get_company_config
from app.agents import (
    build_router_graph,  # 🚀 reemplazo moderno del RouterAgent
    EmergencyAgent, SalesAgent, 
    SupportAgent, ScheduleAgent, 
    AvailabilityAgent, PlanningAgent
)
from app.services.openai_service import OpenAIService
from app.services.vectorstore_service import VectorstoreService
from app.services.agent_state_manager import AgentStateManager
from app.services.prompt_service import get_prompt_service
from app.models.conversation import ConversationManager
import logging
import json
import time
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# FEATURE FLAGS Y CONFIGURACIÓN COGNITIVA
# ============================================================================

class CognitiveCapability(Enum):
    """Capacidades cognitivas que se pueden habilitar/deshabilitar por tenant"""
    REASONING = "reasoning"              # Razonamiento multi-paso
    TOOL_USE = "tool_use"               # Uso dinámico de herramientas
    STATE_PERSISTENCE = "state_persistence"  # Persistencia de estado
    GUARDRAILS = "guardrails"           # Validaciones antes de acciones críticas
    TELEMETRY = "telemetry"             # Telemetría detallada
    CONTEXT_ENRICHMENT = "context_enrichment"  # Enriquecimiento de contexto


@dataclass
class CognitiveConfig:
    """Configuración de capacidades cognitivas por tenant"""
    enabled_capabilities: List[CognitiveCapability] = field(default_factory=list)
    max_reasoning_steps: int = 10
    enable_safe_fail: bool = True
    require_validation_for_critical_actions: bool = True
    telemetry_level: str = "detailed"  # basic, detailed, verbose
    
    def is_enabled(self, capability: CognitiveCapability) -> bool:
        """Verificar si una capacidad está habilitada"""
        return capability in self.enabled_capabilities
    
    @classmethod
    def default_config(cls) -> "CognitiveConfig":
        """Configuración por defecto (todas las capacidades)"""
        return cls(
            enabled_capabilities=[
                CognitiveCapability.REASONING,
                CognitiveCapability.TOOL_USE,
                CognitiveCapability.STATE_PERSISTENCE,
                CognitiveCapability.GUARDRAILS,
                CognitiveCapability.TELEMETRY,
                CognitiveCapability.CONTEXT_ENRICHMENT
            ]
        )
    
    @classmethod
    def minimal_config(cls) -> "CognitiveConfig":
        """Configuración mínima (solo básico)"""
        return cls(
            enabled_capabilities=[
                CognitiveCapability.TOOL_USE,
                CognitiveCapability.TELEMETRY
            ]
        )


@dataclass
class ExecutionMetrics:
    """Métricas de ejecución de un agente"""
    agent_name: str
    agent_type: str
    execution_id: str
    user_id: str
    company_id: str
    
    # Tiempos
    started_at: str
    completed_at: Optional[str] = None
    latency_ms: Optional[float] = None
    
    # Razonamiento
    reasoning_steps: int = 0
    reasoning_traces: List[Dict] = field(default_factory=list)
    
    # Tools
    tools_used: List[str] = field(default_factory=list)
    tools_succeeded: int = 0
    tools_failed: int = 0
    tool_latency_ms: float = 0
    
    # Resultados
    success: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Context
    had_rag_context: bool = False
    had_tool_execution: bool = False
    had_validation: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializar métricas"""
        return {
            "agent_name": self.agent_name,
            "agent_type": self.agent_type,
            "execution_id": self.execution_id,
            "user_id": self.user_id,
            "company_id": self.company_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "latency_ms": self.latency_ms,
            "reasoning_steps": self.reasoning_steps,
            "tools_used": self.tools_used,
            "tools_succeeded": self.tools_succeeded,
            "tools_failed": self.tools_failed,
            "tool_latency_ms": self.tool_latency_ms,
            "success": self.success,
            "errors": self.errors,
            "warnings": self.warnings,
            "had_rag_context": self.had_rag_context,
            "had_tool_execution": self.had_tool_execution,
            "had_validation": self.had_validation
        }


# ============================================================================
# ORCHESTRATOR CON BASE COGNITIVA
# ============================================================================

class MultiAgentOrchestrator:
    """
    Orquestador multi-agente con base cognitiva (LangGraph).
    
    ✅ FASE 1: Enfoque único en agentes cognitivos
    ✅ Inyección uniforme de servicios
    ✅ Feature flags por tenant
    ✅ Guard rails con ConditionEvaluator
    ✅ Telemetría detallada
    """
    
    def __init__(self, company_id: str, openai_service: OpenAIService = None):
        self.company_id = company_id
        self.company_config = get_company_config(company_id)
        
        if not self.company_config:
            raise ValueError(f"Configuration not found for company: {company_id}")
        
        # Servicios core
        self.openai_service = openai_service or OpenAIService()
        self.vectorstore_service = None  # Se inyecta externamente
        self.tool_executor = None  # Se inyecta externamente

        # ✅ AGREGAR EL IMPORT AQUÍ (línea ~164)
        from app.workflows.condition_evaluator import ConditionEvaluator
        
        # ✅ NUEVOS: Servicios cognitivos
        self.prompt_service = get_prompt_service()
        self.state_manager = AgentStateManager()
        self.condition_evaluator = ConditionEvaluator()
        
        # ✅ NUEVO: Configuración cognitiva (feature flags)
        self.cognitive_config = self._load_cognitive_config()
        
        # Agentes (se inicializan con inyección completa)
        self.agents = {}
        self._initialize_agents()
        
        # ✅ NUEVO: Registro de ejecuciones
        self.execution_history: List[ExecutionMetrics] = []
        
        logger.info(
            f"🧠 [{company_id}] MultiAgentOrchestrator initialized with cognitive base"
        )
        logger.info(
            f"   → Cognitive capabilities: {[c.value for c in self.cognitive_config.enabled_capabilities]}"
        )
    
    def _load_cognitive_config(self) -> CognitiveConfig:
        """
        Cargar configuración cognitiva desde config de empresa.
        
        Permite feature flags por tenant.
        """
        # Verificar si la empresa tiene config cognitiva personalizada
        if hasattr(self.company_config, 'cognitive_config'):
            config_data = self.company_config.cognitive_config
            
            # Parsear capabilities
            capabilities = []
            for cap_name in config_data.get('enabled_capabilities', []):
                try:
                    capabilities.append(CognitiveCapability(cap_name))
                except ValueError:
                    logger.warning(f"Unknown cognitive capability: {cap_name}")
            
            return CognitiveConfig(
                enabled_capabilities=capabilities,
                max_reasoning_steps=config_data.get('max_reasoning_steps', 10),
                enable_safe_fail=config_data.get('enable_safe_fail', True),
                require_validation_for_critical_actions=config_data.get(
                    'require_validation_for_critical_actions', True
                ),
                telemetry_level=config_data.get('telemetry_level', 'detailed')
            )
        
        # Por defecto: todas las capacidades habilitadas
        return CognitiveConfig.default_config()
    
    def set_vectorstore_service(self, vectorstore_service: VectorstoreService):
        """Inyectar servicio de vectorstore específico de la empresa"""
        self.vectorstore_service = vectorstore_service
        
        # ✅ Inyectar a todos los agentes que necesitan RAG
        rag_agents = ['sales', 'support', 'emergency', 'schedule']
        
        for agent_name in rag_agents:
            if agent_name in self.agents:
                self.agents[agent_name].set_vectorstore_service(vectorstore_service)
                logger.info(f"[{self.company_id}] RAG injected to {agent_name} agent")
        
        # También inyectar al tool_executor si existe
        if self.tool_executor:
            self.tool_executor.set_vectorstore_service(vectorstore_service)
            logger.info(f"[{self.company_id}] RAG injected to tool_executor")
    
    def set_tool_executor(self, tool_executor):
        """
        ✅ Inyectar tool executor al orquestador y a todos los agentes.
        """
        self.tool_executor = tool_executor
        
        # Auto-inyectar vectorstore si ya lo tenemos
        if self.vectorstore_service:
            tool_executor.set_vectorstore_service(self.vectorstore_service)
            logger.info(f"[{self.company_id}] RAG auto-injected to tool_executor")
        
        # ✅ NUEVO: Inyectar tool_executor a cada agente
        for agent_name, agent in self.agents.items():
            if hasattr(agent, 'set_tool_executor'):
                agent.set_tool_executor(tool_executor)
                logger.info(f"[{self.company_id}] ToolExecutor injected to {agent_name}")
        
        # Log de tools disponibles
        available_tools = tool_executor.get_available_tools()
        tools_ready = [name for name, status in available_tools.items() if status.get("available")]
        
        logger.info(f"✅ [{self.company_id}] ToolExecutor configured")
        logger.info(f"   → Total tools: {len(available_tools)}")
        logger.info(f"   → Ready tools: {len(tools_ready)}")
    
    def _initialize_agents(self):
        """
        Inicializar todos los agentes cognitivos con INYECCIÓN UNIFORME de servicios.
        
        ✅ FASE 1: LangGraph-ready
           - RouterNode reemplaza RouterAgent
           - Cada agente recibe:
             * openai_service
             * prompt_service
             * state_manager
             * condition_evaluator
        """
        try:
            from app.agents import (
                build_router_graph,
                EmergencyAgent, SalesAgent,
                SupportAgent, ScheduleAgent,
                AvailabilityAgent, PlanningAgent
            )

            # ✅ 1. Crear Router Graph (nuevo reemplazo de RouterAgent)
            self.agents["router_graph"] = build_router_graph(self.company_config)
            logger.info(f"[{self.company_id}] RouterNode graph initialized successfully")

            # ✅ 2. Inicializar los agentes cognitivos
            agent_classes = {
                "emergency": EmergencyAgent,
                "sales": SalesAgent,
                "support": SupportAgent,
                "schedule": ScheduleAgent,
                "availability": AvailabilityAgent,
                "planner": PlanningAgent
            }

            for name, cls in agent_classes.items():
                self.agents[name] = cls(self.company_config, self.openai_service)
                self._inject_cognitive_services(self.agents[name], name)

            # ✅ 3. Conectar dependencias internas (ej: availability → schedule)
            if "availability" in self.agents and "schedule" in self.agents:
                self.agents["availability"].set_schedule_agent(self.agents["schedule"])

            logger.info(f"[{self.company_id}] All cognitive agents initialized with cognitive services (LangGraph mode)")

        except Exception as e:
            logger.error(f"[{self.company_id}] Error initializing agents: {e}")
            raise

    
    def _inject_cognitive_services(self, agent, agent_name: str):
        """
        ✅ INYECCIÓN UNIFORME de servicios cognitivos a un agente.
        
        Args:
            agent: Instancia del agente
            agent_name: Nombre del agente para logging
        """
        # Inyectar prompt_service (si el agente lo soporta)
        if hasattr(agent, 'set_prompt_service'):
            agent.set_prompt_service(self.prompt_service)
            logger.debug(f"  → PromptService injected to {agent_name}")
        
        # Inyectar state_manager (para agentes cognitivos)
        if hasattr(agent, 'set_state_manager'):
            agent.set_state_manager(self.state_manager)
            logger.debug(f"  → StateManager injected to {agent_name}")
        
        # Inyectar condition_evaluator (para guard rails)
        if hasattr(agent, 'set_condition_evaluator'):
            agent.set_condition_evaluator(self.condition_evaluator)
            logger.debug(f"  → ConditionEvaluator injected to {agent_name}")
    
    # ========================================================================
    # EJECUCIÓN CON GUARD RAILS
    # ========================================================================
    
    def execute_tool(self, tool_name: str, parameters: dict) -> dict:
        """
        ✅ Ejecutar una tool con GUARD RAILS opcionales.
        
        Si la tool es crítica (ej: create_appointment, delete_data),
        valida la decisión antes de ejecutar.
        """
        if not self.tool_executor:
            logger.warning(f"[{self.company_id}] ToolExecutor not configured")
            return {
                "success": False,
                "error": "ToolExecutor not configured for this company"
            }
        
        # ✅ NUEVO: Verificar si es acción crítica
        if self._is_critical_action(tool_name):
            # Validar con guard rails
            validation_result = self._validate_critical_action(tool_name, parameters)
            
            if not validation_result["approved"]:
                logger.warning(
                    f"[{self.company_id}] Critical action '{tool_name}' BLOCKED by guard rails: "
                    f"{validation_result['reason']}"
                )
                return {
                    "success": False,
                    "error": "Action blocked by validation",
                    "validation": validation_result
                }
        
        # Ejecutar tool
        return self.tool_executor.execute_tool(tool_name, parameters)
    
    def _is_critical_action(self, tool_name: str) -> bool:
        """
        Determinar si una acción es crítica y requiere validación.
        """
        critical_actions = [
            "create_appointment",
            "cancel_appointment",
            "delete_data",
            "send_whatsapp",
            "send_email",
            "create_booking",
            "process_payment"
        ]
        return tool_name in critical_actions
    
    def _validate_critical_action(self, tool_name: str, parameters: dict) -> dict:
        """
        ✅ GUARD RAILS: Validar acción crítica antes de ejecutar.
        
        Usa ConditionEvaluator para verificar condiciones de seguridad.
        """
        # Si guardrails no está habilitado, aprobar siempre
        if not self.cognitive_config.is_enabled(CognitiveCapability.GUARDRAILS):
            return {"approved": True, "reason": "Guardrails disabled"}
        
        validation_rules = {
            "create_appointment": {
                "required_fields": ["datetime", "patient_info", "service"],
                "conditions": [
                    "{{patient_info}} is not None",
                    "{{datetime}} is not None"
                ]
            },
            "send_whatsapp": {
                "required_fields": ["conversation_id", "message"],
                "conditions": [
                    "{{message}} is not None"
                ]
            }
        }
        
        rules = validation_rules.get(tool_name)
        if not rules:
            # No hay reglas específicas, aprobar
            return {"approved": True, "reason": "No validation rules defined"}
        
        # Verificar campos requeridos
        for field in rules.get("required_fields", []):
            if field not in parameters or not parameters[field]:
                return {
                    "approved": False,
                    "reason": f"Missing required field: {field}"
                }
        
        # Evaluar condiciones
        try:
            for condition in rules.get("conditions", []):
                # Resolver variables en la condición
                resolved_condition = condition
                for key, value in parameters.items():
                    resolved_condition = resolved_condition.replace(
                        f"{{{{{key}}}}}", 
                        repr(value)
                    )
                
                # Evaluar (simple check, puede mejorarse)
                if "is not None" in resolved_condition:
                    var = resolved_condition.split(" ")[0]
                    if var not in parameters or parameters[var] is None:
                        return {
                            "approved": False,
                            "reason": f"Validation failed: {condition}"
                        }
        except Exception as e:
            logger.error(f"Error in validation: {e}")
            # Por seguridad, rechazar si hay error
            return {
                "approved": False,
                "reason": f"Validation error: {str(e)}"
            }
        
        return {"approved": True, "reason": "All validations passed"}
    
    # ========================================================================
    # MÉTODO PRINCIPAL CON TELEMETRÍA
    # ========================================================================
    
    def get_response(self, question: str, user_id: str, conversation_manager: ConversationManager,
                     media_type: str = "text", media_context: str = None) -> Tuple[str, str]:
        """
        Método principal con TELEMETRÍA DETALLADA.
        """
        # Generar execution_id
        execution_id = f"exec_{self.company_id}_{user_id}_{int(time.time() * 1000)}"
        
        # Iniciar métricas
        metrics = ExecutionMetrics(
            agent_name="orchestrator",
            agent_type="multi_agent",
            execution_id=execution_id,
            user_id=user_id,
            company_id=self.company_id,
            started_at=datetime.utcnow().isoformat()
        )
        
        try:
            # Procesar contexto multimedia
            processed_question = self._process_multimedia_context(question, media_type, media_context)
            
            if not processed_question or not processed_question.strip():
                response = f"Por favor, envía un mensaje específico para poder ayudarte en {self.company_config.company_name}. 😊"
                metrics.success = True
                metrics.completed_at = datetime.utcnow().isoformat()
                self._finalize_metrics(metrics)
                return response, "support"
            
            if not user_id or not user_id.strip():
                response = "Error interno: ID de usuario inválido."
                metrics.success = False
                metrics.errors.append("Invalid user_id")
                self._finalize_metrics(metrics)
                return response, "error"
            
            # Obtener historial de conversación
            chat_history = conversation_manager.get_chat_history(user_id, format_type="messages")
            
            # Preparar inputs
            inputs = {
                "question": processed_question.strip(),
                "chat_history": chat_history,
                "user_id": user_id,
                "company_id": self.company_id
            }
            
            # ✅ Log de inicio con telemetría
            self._log_query_start(inputs, metrics)
            
            # Orquestar respuesta
            response, agent_used = self._orchestrate_response(inputs, metrics)
            
            # Guardar en conversación
            conversation_manager.add_message(user_id, "user", processed_question)
            conversation_manager.add_message(user_id, "assistant", response)
            
            # ✅ Finalizar métricas
            metrics.success = True
            metrics.completed_at = datetime.utcnow().isoformat()
            self._finalize_metrics(metrics)
            
            # ✅ Log de finalización
            self._log_query_completion(agent_used, response, metrics)
            
            return response, agent_used
            
        except Exception as e:
            logger.exception(f"[{self.company_id}] Error in multi-agent system for user {user_id}")
            
            metrics.success = False
            metrics.errors.append(str(e))
            metrics.completed_at = datetime.utcnow().isoformat()
            self._finalize_metrics(metrics)
            
            error_response = f"Disculpa, tuve un problema técnico en {self.company_config.company_name}. Por favor intenta de nuevo. 🔧"
            return error_response, "error"
    
    def _finalize_metrics(self, metrics: ExecutionMetrics):
        """Calcular latencia y guardar métricas"""
        if metrics.started_at and metrics.completed_at:
            started = datetime.fromisoformat(metrics.started_at)
            completed = datetime.fromisoformat(metrics.completed_at)
            metrics.latency_ms = (completed - started).total_seconds() * 1000
        
        # ✅ Guardar en historial
        self.execution_history.append(metrics)
        
        # ✅ Si telemetría está habilitada, persistir
        if self.cognitive_config.is_enabled(CognitiveCapability.TELEMETRY):
            self._persist_metrics(metrics)
    
    def _persist_metrics(self, metrics: ExecutionMetrics):
        """Persistir métricas (en state_manager o logging estructurado)"""
        try:
            if self.cognitive_config.is_enabled(CognitiveCapability.STATE_PERSISTENCE):
                # Guardar en state_manager
                self.state_manager.record_execution(
                    agent_name=metrics.agent_name,
                    user_id=metrics.user_id,
                    company_id=self.company_id,
                    metrics=metrics.to_dict()
                )
            
            # Log estructurado
            logger.info(
                f"📊 [{self.company_id}] Execution metrics",
                extra=metrics.to_dict()
            )
            
        except Exception as e:
            logger.error(f"Error persisting metrics: {e}")
    
    # ========================================================================
    # MÉTODOS AUXILIARES (mantener compatibilidad)
    # ========================================================================
    
    def _process_multimedia_context(self, question: str, media_type: str, media_context: str = None) -> str:
        """Procesar contexto multimedia"""
        if media_type == "image" and media_context:
            return f"Contexto visual: {media_context}\n\nPregunta: {question}"
        elif media_type == "voice" and media_context:
            return f"Transcripción de voz: {media_context}\n\nPregunta: {question}"
        else:
            return question
    
    def _orchestrate_response(self, inputs: Dict[str, Any], metrics: ExecutionMetrics) -> Tuple[str, str]:
        """Orquestador principal que coordina los agentes mediante RouterNode (LangGraph)"""
        try:
            from app.agents._cognitive_base import AgentState
    
            # 🧭 1. Ejecutar Router Graph (clasificación inicial)
            router_graph = self.agents.get("router_graph")
            if not router_graph:
                raise RuntimeError("RouterGraph not initialized")
    
            # ✅ Crear state como dict de AgentState
            state: AgentState = {
                # Inputs originales (obligatorios)
                "question": inputs.get("question", ""),
                "chat_history": inputs.get("chat_history", []),
                "user_id": inputs.get("user_id", ""),
                "company_id": inputs.get("company_id", self.company_id),
                
                # Estado de ejecución
                "agent_type": "router",
                "execution_id": metrics.execution_id,
                "status": "pending",
                "current_node": "router",
                
                # Razonamiento y decisiones
                "reasoning_steps": [],
                "tools_called": [],
                "tool_results": [],
                
                # Contexto y memoria
                "context": {},
                "intermediate_results": {},
                
                # Herramientas disponibles
                "tools_available": [],
                
                # Decisiones tomadas
                "decisions": [],
                "confidence_scores": {},
                
                # Contexto específico por tipo de agente
                "vectorstore_context": None,
                "calendar_context": None,
                
                # Output final
                "response": None,
                
                # Metadata y telemetría
                "metadata": {},
                "errors": [],
                "warnings": [],
                
                # Control de flujo
                "should_continue": True,
                "current_step": 0,
                "retry_count": 0,
                
                # Timestamps
                "started_at": metrics.started_at,
                "completed_at": None
            }
            
            # Compilar y ejecutar router
            compiled_router = router_graph.compile()
            result = compiled_router.invoke(state)
    
            # ✅ CORREGIDO: Acceder a result como dict, no como .data
            intent = result.get("context", {}).get("intent", "support").upper()
            confidence = result.get("context", {}).get("confidence", 0.5)
            
            logger.info(f"[{self.company_id}] RouterNode classified intent: {intent} (confidence: {confidence})")
    
            # 🧩 2. Registrar trazas cognitivas
            metrics.reasoning_steps += 1
            metrics.reasoning_traces.append({
                "step": "router_node_classification",
                "intent": intent,
                "confidence": confidence,
                "timestamp": datetime.utcnow().isoformat()
            })
    
            # 🧠 3. Seleccionar y ejecutar agente correspondiente
            response = self._execute_selected_agent(intent, confidence, inputs, metrics)
            return response, intent.lower()
    
        except Exception as e:
            logger.error(f"[{self.company_id}] Error in orchestration: {e}")
            metrics.errors.append(f"Orchestration error: {str(e)}")
            return self.agents["support"].invoke(inputs), "support"

    
    def _execute_selected_agent(self, intent: str, confidence: float, 
                                inputs: Dict[str, Any], metrics: ExecutionMetrics) -> str:
        """Ejecutar el agente seleccionado"""
        
        # Threshold de confianza
        if confidence > 0.7:
            agent_map = {
                "EMERGENCY": self.agents['emergency'],
                "SALES": self.agents['sales'],
                "SCHEDULE": self.agents['schedule'],
                "SUPPORT": self.agents['support']
            }
            
            agent = agent_map.get(intent)
            if agent:
                metrics.agent_name = intent.lower()
                return agent.invoke(inputs)
        
        # Si confianza es baja, usar support por defecto
        logger.info(f"[{self.company_id}] Low confidence ({confidence}), using support agent")
        metrics.agent_name = "support"
        metrics.warnings.append(f"Low confidence classification: {confidence}")
        return self.agents['support'].invoke(inputs)
    
    def _log_query_start(self, inputs: Dict[str, Any], metrics: ExecutionMetrics):
        """Log inicio de consulta con telemetría"""
        question = inputs.get("question", "")
        user_id = inputs.get("user_id", "unknown")
        
        logger.info(f"🔍 [{self.company_id}] QUERY START - User: {user_id}")
        logger.info(f"   → Question: {question[:100]}...")
        logger.info(f"   → Execution ID: {metrics.execution_id}")
        
        # Detectar si puede necesitar RAG
        might_need_rag = self._might_need_rag(question)
        if might_need_rag:
            rag_status = "available" if self.vectorstore_service else "not configured"
            logger.info(f"   → Possible RAG query detected (RAG: {rag_status})")
            metrics.had_rag_context = self.vectorstore_service is not None
    
    def _log_query_completion(self, agent_used: str, response: str, metrics: ExecutionMetrics):
        """Log finalización de consulta con métricas"""
        logger.info(f"🤖 [{self.company_id}] RESPONSE GENERATED")
        logger.info(f"   → Agent: {agent_used}")
        logger.info(f"   → Response length: {len(response)} characters")
        logger.info(f"   → Latency: {metrics.latency_ms:.2f}ms")
        logger.info(f"   → Tools used: {len(metrics.tools_used)}")
        logger.info(f"   → Reasoning steps: {metrics.reasoning_steps}")
        
        if metrics.errors:
            logger.warning(f"   ⚠️ Errors: {len(metrics.errors)}")
    
    def _might_need_rag(self, question: str) -> bool:
        """Determinar si consulta podría necesitar RAG"""
        rag_keywords = [
            "precio", "costo", "inversión", "duración", "tiempo",
            "tratamiento", "procedimiento", "servicio", "beneficio",
            "horario", "disponibilidad", "agendar", "cita", "información",
            "dolor", "emergencia", "protocolo", "preparación", "requisitos"
        ]
        return any(keyword in question.lower() for keyword in rag_keywords)
    
    # ========================================================================
    # MÉTODOS DE COMPATIBILIDAD Y UTILIDAD
    # ========================================================================
    
    def search_documents(self, query: str, k: int = 3):
        """Búsqueda de documentos específica de la empresa"""
        try:
            if not self.vectorstore_service:
                return []
            
            docs = self.vectorstore_service.search_by_company(query, self.company_id, k=k)
            return docs
            
        except Exception as e:
            logger.error(f"[{self.company_id}] Error searching documents: {e}")
            return []
    
    def get_cognitive_status(self) -> Dict[str, Any]:
        """
        ✅ NUEVO: Obtener estado de las capacidades cognitivas.
        """
        return {
            "company_id": self.company_id,
            "cognitive_config": {
                "enabled_capabilities": [c.value for c in self.cognitive_config.enabled_capabilities],
                "max_reasoning_steps": self.cognitive_config.max_reasoning_steps,
                "enable_safe_fail": self.cognitive_config.enable_safe_fail,
                "require_validation": self.cognitive_config.require_validation_for_critical_actions,
                "telemetry_level": self.cognitive_config.telemetry_level
            },
            "services_injected": {
                "vectorstore": self.vectorstore_service is not None,
                "tool_executor": self.tool_executor is not None,
                "prompt_service": self.prompt_service is not None,
                "state_manager": self.state_manager is not None,
                "condition_evaluator": self.condition_evaluator is not None
            },
            "execution_stats": {
                "total_executions": len(self.execution_history),
                "successful": sum(1 for m in self.execution_history if m.success),
                "failed": sum(1 for m in self.execution_history if not m.success),
                "avg_latency_ms": sum(m.latency_ms or 0 for m in self.execution_history) / len(self.execution_history) if self.execution_history else 0
            }
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Verificar salud del sistema multi-agente con info cognitiva"""
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
                "company_id": self.company_id,
                "company_name": self.company_config.company_name,
                "agents_status": agents_status,
                "cognitive_status": self.get_cognitive_status(),
                "vectorstore_connected": self.vectorstore_service is not None,
                "tool_executor_connected": self.tool_executor is not None,
                "system_type": "multi-agent-cognitive-base"
            }
            
        except Exception as e:
            return {
                "system_healthy": False,
                "company_id": self.company_id,
                "error": str(e),
                "system_type": "multi-agent-cognitive-base"
            }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del sistema con info cognitiva"""
        stats = {
            "company_id": self.company_id,
            "company_name": self.company_config.company_name,
            "agents_available": list(self.agents.keys()),
            "system_type": "multi-agent-cognitive-base",
            "cognitive_enabled": True,
            "cognitive_capabilities": [c.value for c in self.cognitive_config.enabled_capabilities]
        }
        
        # Agregar info de tools si está disponible
        if self.tool_executor:
            available_tools = self.tool_executor.get_available_tools()
            tools_ready = [name for name, status in available_tools.items() if status.get("available")]
            stats["tools_available"] = len(available_tools)
            stats["tools_ready"] = len(tools_ready)
            stats["tools_ready_list"] = tools_ready
        
        # Agregar stats de ejecución
        if self.execution_history:
            stats["execution_stats"] = {
                "total": len(self.execution_history),
                "successful": sum(1 for m in self.execution_history if m.success),
                "failed": sum(1 for m in self.execution_history if not m.success),
                "avg_latency_ms": sum(m.latency_ms or 0 for m in self.execution_history) / len(self.execution_history)
            }
        
        return stats
