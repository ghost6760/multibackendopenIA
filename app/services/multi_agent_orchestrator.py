# app/services/multi_agent_orchestrator_hybrid.py - VERSIÓN HÍBRIDA CON LANGGRAPH

"""
MultiAgentOrchestrator - Versión Híbrida con LangGraph

Esta versión usa MultiAgentOrchestratorGraph internamente pero mantiene
la misma interfaz externa para compatibilidad total.

CAMBIOS vs versión original:
- Usa LangGraph para orquestación cognitiva
- Estado centralizado en StateGraph
- Validaciones explícitas
- Reintentos automáticos
- Logging estructurado
- Métricas de rendimiento

COMPATIBILIDAD:
- ✅ 100% compatible con API existente
- ✅ Mismo __init__
- ✅ Mismos métodos públicos
- ✅ Mismos parámetros
- ✅ Mismos retornos
"""

from typing import Dict, Any, List, Optional, Tuple
from app.config.company_config import CompanyConfig, get_company_config
from app.agents import (
    RouterAgent, EmergencyAgent, SalesAgent,
    SupportAgent, ScheduleAgent, AvailabilityAgent
)
from app.services.openai_service import OpenAIService
from app.services.vectorstore_service import VectorstoreService
from app.models.conversation import ConversationManager
import logging

# ✅ IMPORTAR GRAFO DE LANGGRAPH
from app.langgraph_adapters.orchestrator_graph import MultiAgentOrchestratorGraph

# ✅ IMPORTAR SHARED STATE STORE
from app.services.shared_state_store import SharedStateStore

logger = logging.getLogger(__name__)


class MultiAgentOrchestrator:
    """
    Orquestador multi-agente multi-tenant con RAG mejorado y tool execution

    VERSIÓN HÍBRIDA: Usa MultiAgentOrchestratorGraph (LangGraph) internamente
    pero mantiene la misma interfaz externa para compatibilidad.
    """

    def __init__(self, company_id: str, openai_service: OpenAIService = None):
        """
        Inicializar orquestador.

        Args:
            company_id: ID de la empresa
            openai_service: Servicio de OpenAI (opcional)
        """
        self.company_id = company_id
        self.company_config = get_company_config(company_id)

        if not self.company_config:
            raise ValueError(f"Configuration not found for company: {company_id}")

        # Servicios
        self.openai_service = openai_service or OpenAIService()
        self.vectorstore_service = None  # Se inyecta externamente
        self.tool_executor = None  # Se inyecta externamente

        # === CREAR AGENTES (igual que antes) === #
        self.agents = {}
        self._initialize_agents()

        # === ✅ CREAR SHARED STATE STORE === #
        self._initialize_shared_state_store()

        # === ✅ CREAR GRAFO DE LANGGRAPH INTERNAMENTE === #
        self._initialize_graph()

        logger.info(
            f"✅ MultiAgentOrchestrator (hybrid) initialized for company: {company_id}"
        )

    def _initialize_agents(self):
        """Inicializar todos los agentes especializados (igual que antes)"""
        try:
            # Router Agent
            self.agents['router'] = RouterAgent(self.company_config, self.openai_service)

            # Emergency Agent
            self.agents['emergency'] = EmergencyAgent(self.company_config, self.openai_service)

            # Sales Agent
            self.agents['sales'] = SalesAgent(self.company_config, self.openai_service)

            # Support Agent
            self.agents['support'] = SupportAgent(self.company_config, self.openai_service)

            # Schedule Agent
            self.agents['schedule'] = ScheduleAgent(self.company_config, self.openai_service)

            # Availability Agent
            self.agents['availability'] = AvailabilityAgent(self.company_config, self.openai_service)

            # Conectar availability agent con schedule agent
            self.agents['availability'].set_schedule_agent(self.agents['schedule'])

            logger.info(f"[{self.company_id}] All agents initialized: {list(self.agents.keys())}")

        except Exception as e:
            logger.error(f"[{self.company_id}] Error initializing agents: {e}")
            raise

    def _initialize_shared_state_store(self):
        """
        ✅ NUEVO: Inicializar Shared State Store con Redis en producción
        """
        try:
            # Intentar obtener Redis client de Flask context
            redis_client = None
            try:
                from flask import has_request_context
                if has_request_context():
                    from app.services.redis_service import get_redis_client
                    redis_client = get_redis_client()
                    logger.info(f"[{self.company_id}] Using Redis client from Flask context")
            except:
                pass

            # Si no hay Redis client de Flask, intentar crear uno nuevo
            if redis_client is None:
                try:
                    import redis
                    import os
                    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
                    redis_client = redis.from_url(redis_url, decode_responses=True)
                    redis_client.ping()
                    logger.info(f"[{self.company_id}] Created new Redis client: {redis_url}")
                except Exception as e:
                    logger.warning(f"[{self.company_id}] Redis connection failed: {e}, using memory backend")
                    redis_client = None

            # Crear SharedStateStore
            if redis_client:
                self.shared_state_store = SharedStateStore(
                    backend="redis",
                    company_id=self.company_id,
                    redis_client=redis_client,
                    ttl_seconds=3600  # 1 hora
                )
                logger.info(f"[{self.company_id}] SharedStateStore initialized with Redis backend")
            else:
                # Fallback a memoria si Redis no está disponible
                self.shared_state_store = SharedStateStore(
                    backend="memory",
                    company_id=self.company_id,
                    ttl_seconds=3600
                )
                logger.info(f"[{self.company_id}] SharedStateStore initialized with memory backend (fallback)")

        except Exception as e:
            logger.error(f"[{self.company_id}] Error initializing shared state store: {e}")
            # Fallback a memoria en caso de error
            self.shared_state_store = SharedStateStore(
                backend="memory",
                company_id=self.company_id,
                ttl_seconds=3600
            )
            logger.info(f"[{self.company_id}] SharedStateStore fallback to memory backend")

    def _initialize_graph(self):
        """
        ✅ NUEVO: Inicializar grafo de LangGraph

        Crea MultiAgentOrchestratorGraph con los agentes existentes.
        """
        try:
            # Filtrar agentes para el grafo (no incluir availability)
            graph_agents = {
                name: agent
                for name, agent in self.agents.items()
                if name not in ['router', 'availability']
            }

            # Crear grafo con shared state store
            self.graph = MultiAgentOrchestratorGraph(
                router_agent=self.agents['router'],
                agents=graph_agents,
                company_id=self.company_id,
                enable_checkpointing=False,  # Deshabilitar por defecto
                shared_state_store=self.shared_state_store  # ✅ Pasar store
            )

            logger.info(
                f"[{self.company_id}] LangGraph orchestrator initialized "
                f"with {self.shared_state_store.backend} backend"
            )

        except Exception as e:
            logger.error(f"[{self.company_id}] Error initializing graph: {e}")
            # Si falla el grafo, el sistema puede seguir funcionando con agentes directos
            self.graph = None

    def set_vectorstore_service(self, vectorstore_service: VectorstoreService):
        """
        Inyectar servicio de vectorstore específico de la empresa

        ✅ ACTUALIZADO: También inyecta al grafo
        """
        self.vectorstore_service = vectorstore_service

        # Configurar RAG para todos los agentes que lo necesitan
        rag_agents = ['sales', 'support', 'emergency', 'schedule']

        for agent_name in rag_agents:
            if agent_name in self.agents:
                self.agents[agent_name].set_vectorstore_service(vectorstore_service)
                logger.info(f"[{self.company_id}] RAG configured for {agent_name} agent")

        # ✅ También inyectar al tool_executor si ya existe
        if self.tool_executor:
            self.tool_executor.set_vectorstore_service(vectorstore_service)
            logger.info(f"[{self.company_id}] RAG configured for tool_executor")

    def set_tool_executor(self, tool_executor):
        """
        Inyectar tool executor al orquestador

        Compatible con implementación anterior.
        """
        self.tool_executor = tool_executor

        # ✅ Si ya tenemos vectorstore, inyectarlo al executor automáticamente
        if self.vectorstore_service:
            tool_executor.set_vectorstore_service(self.vectorstore_service)
            logger.info(f"[{self.company_id}] RAG auto-injected to tool_executor")

        # Log de tools disponibles
        available_tools = tool_executor.get_available_tools()
        tools_ready = [name for name, status in available_tools.items() if status.get("available")]

        logger.info(f"✅ [{self.company_id}] ToolExecutor configured")
        logger.info(f"   → Total tools: {len(available_tools)}")
        logger.info(f"   → Ready tools: {len(tools_ready)}")

    def execute_tool(self, tool_name: str, parameters: dict) -> dict:
        """
        Ejecutar una tool desde el orquestador

        Compatible con implementación anterior.
        """
        if not self.tool_executor:
            logger.warning(f"[{self.company_id}] ToolExecutor not configured")
            return {
                "success": False,
                "error": "ToolExecutor not configured for this company"
            }

        return self.tool_executor.execute_tool(tool_name, parameters)

    def get_response(
        self,
        question: str,
        user_id: str,
        conversation_manager: ConversationManager,
        media_type: str = "text",
        media_context: str = None
    ) -> Tuple[str, str]:
        """
        Método principal para obtener respuesta del sistema multi-agente

        ✅ ACTUALIZADO: Usa MultiAgentOrchestratorGraph si está disponible,
        sino usa implementación directa de fallback.

        Args:
            question: Pregunta del usuario
            user_id: ID del usuario
            conversation_manager: Gestor de conversación
            media_type: Tipo de media (text, image, voice)
            media_context: Contexto multimedia

        Returns:
            Tupla (response: str, agent_used: str)
        """

        try:
            # Procesar contexto multimedia
            processed_question = self._process_multimedia_context(
                question, media_type, media_context
            )

            if not processed_question or not processed_question.strip():
                return (
                    f"Por favor, envía un mensaje específico para poder ayudarte en "
                    f"{self.company_config.company_name}. 😊",
                    "support"
                )

            if not user_id or not user_id.strip():
                return "Error interno: ID de usuario inválido.", "error"

            # Obtener historial de conversación
            chat_history = conversation_manager.get_chat_history(
                user_id, format_type="messages"
            )

            # ✅ USAR GRAFO DE LANGGRAPH SI ESTÁ DISPONIBLE
            if self.graph:
                logger.info(
                    f"[{self.company_id}] Using LangGraph orchestration for user {user_id}"
                )

                response, agent_used = self.graph.get_response(
                    question=processed_question.strip(),
                    user_id=user_id,
                    chat_history=chat_history,
                    context=""
                )
            else:
                # Fallback a implementación directa
                logger.warning(
                    f"[{self.company_id}] LangGraph not available, using direct orchestration"
                )

                response, agent_used = self._orchestrate_response_direct({
                    "question": processed_question.strip(),
                    "chat_history": chat_history,
                    "user_id": user_id,
                    "company_id": self.company_id
                })

            # Guardar en conversación
            conversation_manager.add_message(user_id, "user", processed_question)
            conversation_manager.add_message(user_id, "assistant", response)

            logger.info(
                f"[{self.company_id}] Response generated for user {user_id} "
                f"by {agent_used} ({len(response)} chars)"
            )

            return response, agent_used

        except Exception as e:
            logger.exception(
                f"[{self.company_id}] Error in multi-agent system for user {user_id}"
            )
            error_response = (
                f"Disculpa, tuve un problema técnico en {self.company_config.company_name}. "
                f"Por favor intenta de nuevo. 🔧"
            )
            return error_response, "error"

    def _orchestrate_response_direct(self, inputs: Dict[str, Any]) -> Tuple[str, str]:
        """
        Orquestación directa (fallback si no hay grafo)

        Implementación simplificada para compatibilidad.
        """
        try:
            # Clasificar intención con Router Agent
            router_response = self.agents['router'].invoke(inputs)

            try:
                classification = json.loads(router_response)
                intent = classification.get("intent", "SUPPORT")
                confidence = classification.get("confidence", 0.5)
            except:
                intent = "SUPPORT"
                confidence = 0.3

            # Ejecutar agente apropiado
            agent_name = intent.lower()

            if confidence > 0.7 and agent_name in self.agents:
                response = self.agents[agent_name].invoke(inputs)
            else:
                response = self.agents['support'].invoke(inputs)
                agent_name = "support"

            return response, agent_name

        except Exception as e:
            logger.error(f"[{self.company_id}] Error in direct orchestration: {e}")
            return self.agents['support'].invoke(inputs), "support"

    def _process_multimedia_context(
        self,
        question: str,
        media_type: str,
        media_context: str = None
    ) -> str:
        """Procesar contexto multimedia (igual que antes)"""
        if media_type == "image" and media_context:
            return f"Contexto visual: {media_context}\n\nPregunta: {question}"
        elif media_type == "voice" and media_context:
            return f"Transcripción de voz: {media_context}\n\nPregunta: {question}"
        else:
            return question

    def search_documents(self, query: str, k: int = 3):
        """
        Búsqueda de documentos específica de la empresa

        Compatible con implementación anterior.
        """
        try:
            if not self.vectorstore_service:
                return []

            docs = self.vectorstore_service.search_by_company(
                query, self.company_id, k=k
            )
            return docs

        except Exception as e:
            logger.error(f"[{self.company_id}] Error searching documents: {e}")
            return []

    def health_check(self) -> Dict[str, Any]:
        """
        Verificar salud del sistema multi-agente

        ✅ ACTUALIZADO: Incluye información del grafo
        """
        try:
            # Si hay grafo, usar su health check
            if self.graph:
                # El grafo no tiene health_check, implementar básico
                return {
                    "system_healthy": True,
                    "company_id": self.company_id,
                    "company_name": self.company_config.company_name,
                    "orchestration": "langgraph",
                    "agents_available": list(self.agents.keys()),
                    "vectorstore_connected": self.vectorstore_service is not None,
                    "tool_executor_connected": self.tool_executor is not None,
                    "shared_state_backend": self.shared_state_store.backend if hasattr(self, 'shared_state_store') else "unknown",
                    "system_type": "multi-agent-hybrid-langgraph"
                }
            else:
                # Fallback a health check básico
                return {
                    "system_healthy": True,
                    "company_id": self.company_id,
                    "company_name": self.company_config.company_name,
                    "orchestration": "direct",
                    "agents_available": list(self.agents.keys()),
                    "vectorstore_connected": self.vectorstore_service is not None,
                    "tool_executor_connected": self.tool_executor is not None,
                    "shared_state_backend": self.shared_state_store.backend if hasattr(self, 'shared_state_store') else "unknown",
                    "system_type": "multi-agent-direct"
                }

        except Exception as e:
            return {
                "system_healthy": False,
                "company_id": self.company_id,
                "error": str(e),
                "system_type": "multi-agent-hybrid-langgraph"
            }

    def get_system_stats(self) -> Dict[str, Any]:
        """
        Obtener estadísticas del sistema

        ✅ ACTUALIZADO: Incluye stats del grafo si está disponible
        """
        stats = {
            "company_id": self.company_id,
            "company_name": self.company_config.company_name,
            "agents_available": list(self.agents.keys()),
            "system_type": "multi-agent-hybrid-langgraph" if self.graph else "multi-agent-direct",
            "vectorstore_index": self.company_config.vectorstore_index,
            "schedule_service_url": self.company_config.schedule_service_url,
            "services": self.company_config.services,
            "rag_status": "enabled" if self.vectorstore_service else "disabled",
            "shared_state_backend": self.shared_state_store.backend if hasattr(self, 'shared_state_store') else "unknown"
        }

        # ✅ Agregar stats del shared state store
        if hasattr(self, 'shared_state_store'):
            try:
                store_stats = self.shared_state_store.get_stats()
                stats["shared_state_stats"] = store_stats
            except Exception as e:
                logger.error(f"[{self.company_id}] Error getting shared state stats: {e}")

        # ✅ Agregar stats del grafo si está disponible
        if self.graph:
            try:
                graph_stats = self.graph.get_stats()
                stats["graph_stats"] = graph_stats
            except Exception as e:
                logger.error(f"[{self.company_id}] Error getting graph stats: {e}")

        # Agregar info de tools si está disponible
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
