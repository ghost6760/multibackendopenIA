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
import json
import time

logger = logging.getLogger(__name__)

class MultiAgentOrchestrator:
    """Orquestador multi-agente multi-tenant con RAG mejorado"""
    
    def __init__(self, company_id: str, openai_service: OpenAIService = None):
        self.company_id = company_id
        self.company_config = get_company_config(company_id)
        
        if not self.company_config:
            raise ValueError(f"Configuration not found for company: {company_id}")
        
        # Servicios
        self.openai_service = openai_service or OpenAIService()
        self.vectorstore_service = None  # Se inyecta externamente
        
        # Agentes
        self.agents = {}
        self._initialize_agents()
        
        logger.info(f"MultiAgentOrchestrator initialized for company: {company_id}")
    
    def set_vectorstore_service(self, vectorstore_service: VectorstoreService):
        """Inyectar servicio de vectorstore específico de la empresa - ACTUALIZADO"""
        self.vectorstore_service = vectorstore_service
        
        # ACTUALIZADO: Configurar RAG para todos los agentes que lo necesitan
        rag_agents = ['sales', 'support', 'emergency', 'schedule']
        
        for agent_name in rag_agents:
            if agent_name in self.agents:
                self.agents[agent_name].set_vectorstore_service(vectorstore_service)
                logger.info(f"[{self.company_id}] RAG configured for {agent_name} agent")
    
    def _initialize_agents(self):
        """Inicializar todos los agentes especializados"""
        try:
            # Router Agent (siempre necesario)
            self.agents['router'] = RouterAgent(self.company_config, self.openai_service)
            
            # Emergency Agent - ACTUALIZADO con RAG
            self.agents['emergency'] = EmergencyAgent(self.company_config, self.openai_service)
            
            # Sales Agent - Con RAG
            self.agents['sales'] = SalesAgent(self.company_config, self.openai_service)
            
            # Support Agent - Con RAG
            self.agents['support'] = SupportAgent(self.company_config, self.openai_service)
            
            # Schedule Agent - ACTUALIZADO con RAG
            self.agents['schedule'] = ScheduleAgent(self.company_config, self.openai_service)
            
            # Availability Agent (sin RAG, usa schedule agent)
            self.agents['availability'] = AvailabilityAgent(self.company_config, self.openai_service)
            
            # Conectar availability agent con schedule agent
            self.agents['availability'].set_schedule_agent(self.agents['schedule'])
            
            logger.info(f"[{self.company_id}] All agents initialized: {list(self.agents.keys())}")
            logger.info(f"[{self.company_id}] RAG-enabled agents: sales, support, emergency, schedule")
            
        except Exception as e:
            logger.error(f"[{self.company_id}] Error initializing agents: {e}")
            raise
    
    def get_response(self, question: str, user_id: str, conversation_manager: ConversationManager,
                     media_type: str = "text", media_context: str = None) -> Tuple[str, str]:
        """Método principal para obtener respuesta del sistema multi-agente"""
        
        try:
            # Procesar contexto multimedia
            processed_question = self._process_multimedia_context(question, media_type, media_context)
            
            if not processed_question or not processed_question.strip():
                return f"Por favor, envía un mensaje específico para poder ayudarte en {self.company_config.company_name}. 😊", "support"
            
            if not user_id or not user_id.strip():
                return "Error interno: ID de usuario inválido.", "error"
            
            # Obtener historial de conversación
            chat_history = conversation_manager.get_chat_history(user_id, format_type="messages")
            
            # Preparar inputs
            inputs = {
                "question": processed_question.strip(),
                "chat_history": chat_history,
                "user_id": user_id,
                "company_id": self.company_id
            }
            
            # Log de inicio
            self._log_query_start(inputs)
            
            # Orquestar respuesta
            response, agent_used = self._orchestrate_response(inputs)
            
            # Guardar en conversación
            conversation_manager.add_message(user_id, "user", processed_question)
            conversation_manager.add_message(user_id, "assistant", response)
            
            # Log de finalización
            self._log_query_completion(agent_used, response)
            
            return response, agent_used
            
        except Exception as e:
            logger.exception(f"[{self.company_id}] Error in multi-agent system for user {user_id}")
            error_response = f"Disculpa, tuve un problema técnico en {self.company_config.company_name}. Por favor intenta de nuevo. 🔧"
            return error_response, "error"
    
    def _process_multimedia_context(self, question: str, media_type: str, media_context: str = None) -> str:
        """Procesar contexto multimedia"""
        if media_type == "image" and media_context:
            return f"Contexto visual: {media_context}\n\nPregunta: {question}"
        elif media_type == "voice" and media_context:
            return f"Transcripción de voz: {media_context}\n\nPregunta: {question}"
        else:
            return question
    
    def _orchestrate_response(self, inputs: Dict[str, Any]) -> Tuple[str, str]:
        """Orquestador principal que coordina los agentes"""
        try:
            # Clasificar intención con Router Agent
            router_response = self.agents['router'].invoke(inputs)
            
            try:
                classification = json.loads(router_response)
                intent = classification.get("intent", "SUPPORT")
                confidence = classification.get("confidence", 0.5)
                
                logger.info(f"[{self.company_id}] Intent classified: {intent} (confidence: {confidence})")
                
            except json.JSONDecodeError:
                intent = "SUPPORT"
                confidence = 0.3
                logger.warning(f"[{self.company_id}] Router response was not valid JSON, defaulting to SUPPORT")
            
            # Seleccionar y ejecutar agente apropiado
            response = self._execute_selected_agent(intent, confidence, inputs)
            
            return response, intent.lower()
            
        except Exception as e:
            logger.error(f"[{self.company_id}] Error in orchestration: {e}")
            # Fallback al support agent
            return self.agents['support'].invoke(inputs), "support"
    
    def _execute_selected_agent(self, intent: str, confidence: float, inputs: Dict[str, Any]) -> str:
        """Ejecutar el agente seleccionado"""
        
        # Threshold de confianza más alto para intenciones específicas
        if confidence > 0.7:
            if intent == "EMERGENCY":
                return self.agents['emergency'].invoke(inputs)
            elif intent == "SALES":
                return self.agents['sales'].invoke(inputs)
            elif intent == "SCHEDULE":
                return self.agents['schedule'].invoke(inputs)
            elif intent == "SUPPORT":
                return self.agents['support'].invoke(inputs)
        
        # Si confianza es baja, usar support por defecto
        logger.info(f"[{self.company_id}] Low confidence ({confidence}), using support agent")
        return self.agents['support'].invoke(inputs)
    
    def _log_query_start(self, inputs: Dict[str, Any]):
        """Log inicio de consulta"""
        question = inputs.get("question", "")
        user_id = inputs.get("user_id", "unknown")
        
        logger.info(f"🔍 [{self.company_id}] QUERY START - User: {user_id}")
        logger.info(f"   → Question: {question[:100]}...")
        
        # Detectar si puede necesitar RAG
        might_need_rag = self._might_need_rag(question)
        if might_need_rag:
            rag_status = "available" if self.vectorstore_service else "not configured"
            logger.info(f"   → Possible RAG query detected for {self.company_config.company_name} (RAG: {rag_status})")
    
    def _log_query_completion(self, agent_used: str, response: str):
        """Log finalización de consulta"""
        logger.info(f"🤖 [{self.company_id}] RESPONSE GENERATED - Agent: {agent_used}")
        logger.info(f"   → Response length: {len(response)} characters")
        logger.info(f"   → Company: {self.company_config.company_name}")
        
        # Log si el agente usado tiene RAG
        rag_agents = ['sales', 'support', 'emergency', 'schedule']
        if agent_used in rag_agents:
            rag_status = "enabled" if self.vectorstore_service else "disabled"
            logger.info(f"   → RAG status for {agent_used}: {rag_status}")
    
    def _might_need_rag(self, question: str) -> bool:
        """Determinar si consulta podría necesitar RAG"""
        rag_keywords = [
            "precio", "costo", "inversión", "duración", "tiempo",
            "tratamiento", "procedimiento", "servicio", "beneficio",
            "horario", "disponibilidad", "agendar", "cita", "información",
            "dolor", "emergencia", "protocolo", "preparación", "requisitos"
        ]
        return any(keyword in question.lower() for keyword in rag_keywords)
    
    def search_documents(self, query: str, k: int = 3):
        """Búsqueda de documentos específica de la empresa - método de compatibilidad"""
        try:
            if not self.vectorstore_service:
                return []
            
            # Buscar documentos filtrados por empresa
            docs = self.vectorstore_service.search_by_company(query, self.company_id, k=k)
            return docs
            
        except Exception as e:
            logger.error(f"[{self.company_id}] Error searching documents: {e}")
            return []
    
    def health_check(self) -> Dict[str, Any]:
        """Verificar salud del sistema multi-agente - ACTUALIZADO"""
        try:
            agents_status = {}
            
            for agent_name, agent in self.agents.items():
                try:
                    # Test básico de cada agente
                    test_inputs = {
                        "question": "test",
                        "chat_history": [],
                        "user_id": "health_check"
                    }
                    
                    # Para router, verificar que devuelve JSON válido
                    if agent_name == "router":
                        response = agent.invoke(test_inputs)
                        try:
                            json.loads(response)
                            agents_status[agent_name] = "healthy"
                        except json.JSONDecodeError:
                            agents_status[agent_name] = "unhealthy"
                    else:
                        # Para otros agentes, verificar que no lancen excepción
                        response = agent.invoke(test_inputs)
                        agents_status[agent_name] = "healthy" if response else "unhealthy"
                        
                except Exception as e:
                    agents_status[agent_name] = f"error: {str(e)}"
            
            # Estado del sistema
            all_healthy = all(status == "healthy" for status in agents_status.values())
            
            # NUEVO: Información sobre RAG
            rag_info = {
                "rag_available": self.vectorstore_service is not None,
                "rag_enabled_agents": ["sales", "support", "emergency", "schedule"],
                "rag_disabled_agents": ["router", "availability"]
            }
            
            return {
                "system_healthy": all_healthy,
                "company_id": self.company_id,
                "company_name": self.company_config.company_name,
                "agents_status": agents_status,
                "vectorstore_connected": self.vectorstore_service is not None,
                "schedule_service_url": self.company_config.schedule_service_url,
                "system_type": "multi-agent-multi-tenant",
                "rag_status": rag_info
            }
            
        except Exception as e:
            return {
                "system_healthy": False,
                "company_id": self.company_id,
                "error": str(e),
                "system_type": "multi-agent-multi-tenant"
            }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del sistema - ACTUALIZADO"""
        return {
            "company_id": self.company_id,
            "company_name": self.company_config.company_name,
            "agents_available": list(self.agents.keys()),
            "rag_enabled_agents": ["sales", "support", "emergency", "schedule"],
            "system_type": "multi-agent-multi-tenant-rag",
            "vectorstore_index": self.company_config.vectorstore_index,
            "schedule_service_url": self.company_config.schedule_service_url,
            "services": self.company_config.services,
            "rag_status": "enabled" if self.vectorstore_service else "disabled"
        }
