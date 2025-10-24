# app/services/multi_agent_orchestrator.py - MIGRADO A LANGGRAPH
"""
MultiAgentOrchestrator con LangGraph
Mantiene interfaz get_response() para compatibilidad
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
import json
import time
from datetime import datetime

from langgraph.graph import StateGraph, END
from app.services.multi_agent_orchestrator_types import (
    OrchestratorState, 
    IntentType, 
    RoutingDecision, 
    ValidationDecision
)
from app.config.company_config import CompanyConfig
from app.models.conversation import ConversationManager

logger = logging.getLogger(__name__)

class MultiAgentOrchestrator:
    """
    Orquestador de múltiples agentes usando LangGraph.
    
    ✅ MANTIENE: Interfaz get_response() intacta
    ✅ AÑADE: Estado persistente, retry automático, validación
    ✅ MEJORA: Logging estructurado, visualización de flujo
    """
    
    def __init__(
        self, 
        company_config: CompanyConfig,
        agents: Dict[str, Any],
        conversation_manager: Optional[ConversationManager] = None
    ):
        """
        Inicializar orquestador con LangGraph.
        
        Args:
            company_config: Configuración de la empresa
            agents: Diccionario de agentes {nombre: instancia}
            conversation_manager: Manager de conversaciones
        """
        self.company_config = company_config
        self.agents = agents
        self.conversation_manager = conversation_manager or ConversationManager()
        
        # Construir grafo
        self.graph = self._build_orchestrator_graph()
        
        logger.info(
            f"[{company_config.company_id}] MultiAgentOrchestrator initialized with LangGraph",
            extra={
                "available_agents": list(agents.keys()),
                "has_conversation_manager": conversation_manager is not None
            }
        )
    
    def _build_orchestrator_graph(self) -> StateGraph:
        """
        Construir grafo de orquestación.
        
        Flujo:
        1. load_history → Cargar historial conversacional
        2. classify → Clasificar intención con RouterAgent
        3. route → Decidir agente apropiado
        4. execute_agent → Ejecutar agente seleccionado
        5. validate → Validar calidad de respuesta
        6. save_history → Guardar en DB
        """
        workflow = StateGraph(OrchestratorState)
        
        # ===== NODOS =====
        workflow.add_node("load_history", self._load_history_node)
        workflow.add_node("classify", self._classify_intent_node)
        workflow.add_node("execute_emergency", self._execute_emergency_node)
        workflow.add_node("execute_sales", self._execute_sales_node)
        workflow.add_node("execute_schedule", self._execute_schedule_node)
        workflow.add_node("execute_support", self._execute_support_node)
        workflow.add_node("execute_availability", self._execute_availability_node)
        workflow.add_node("validate_response", self._validate_response_node)
        workflow.add_node("save_history", self._save_history_node)
        workflow.add_node("handle_error", self._handle_error_node)
        
        # ===== FLUJO =====
        workflow.set_entry_point("load_history")
        
        workflow.add_edge("load_history", "classify")
        
        # Routing condicional por intención
        workflow.add_conditional_edges(
            "classify",
            self._route_by_intent,
            {
                "emergency": "execute_emergency",
                "sales": "execute_sales",
                "schedule": "execute_schedule",
                "support": "execute_support",
                "availability": "execute_availability",
                "error": "handle_error"
            }
        )
        
        # Todos los agentes → validación
        for agent in ["execute_emergency", "execute_sales", "execute_schedule", 
                      "execute_support", "execute_availability"]:
            workflow.add_edge(agent, "validate_response")
        
        # Validación decide siguiente paso
        workflow.add_conditional_edges(
            "validate_response",
            self._decide_next_step,
            {
                "save": "save_history",
                "retry": "classify",
                "fallback": "execute_support",
                "end": END
            }
        )
        
        workflow.add_edge("save_history", END)
        workflow.add_edge("handle_error", END)
        
        return workflow.compile()
    
    # =========================================================================
    # NODOS DEL GRAFO
    # =========================================================================
    
    def _load_history_node(self, state: OrchestratorState) -> OrchestratorState:
        """Cargar historial conversacional desde DB"""
        conversation_id = state.get("conversation_id")
        
        try:
            if conversation_id:
                history = self.conversation_manager.get_conversation_history(
                    conversation_id=conversation_id,
                    limit=10
                )
                
                logger.debug(
                    f"[{self.company_config.company_id}] History loaded",
                    extra={
                        "conversation_id": conversation_id,
                        "history_length": len(history)
                    }
                )
            else:
                history = []
            
            return {
                **state,
                "chat_history": history,
                "retry_count": 0,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error loading history: {e}")
            return {**state, "chat_history": [], "retry_count": 0}
    
    def _classify_intent_node(self, state: OrchestratorState) -> OrchestratorState:
        """Clasificar intención usando RouterAgent"""
        try:
            start_time = time.time()
            
            # Ejecutar RouterAgent
            router_response = self.agents["router"].invoke({
                "question": state["question"],
                "chat_history": state.get("chat_history", [])
            })
            
            # Parsear respuesta JSON
            try:
                intent_data = json.loads(router_response)
            except json.JSONDecodeError:
                # Fallback si no es JSON válido
                logger.warning(f"Router returned non-JSON: {router_response[:100]}")
                intent_data = {
                    "intent": "SUPPORT",
                    "confidence": 0.3,
                    "keywords": [],
                    "reasoning": "JSON parse failed"
                }
            
            intent = intent_data.get("intent", "SUPPORT")
            confidence = intent_data.get("confidence", 0.5)
            
            execution_time = time.time() - start_time
            
            logger.info(
                f"[{self.company_config.company_id}] Intent classified",
                extra={
                    "intent": intent,
                    "confidence": confidence,
                    "execution_time": execution_time,
                    "question_preview": state["question"][:50]
                }
            )
            
            return {
                **state,
                "intent": intent,
                "confidence": confidence,
                "keywords": intent_data.get("keywords", []),
                "reasoning": intent_data.get("reasoning", ""),
                "execution_time": execution_time
            }
            
        except Exception as e:
            logger.exception(f"Classification error: {e}")
            return {
                **state,
                "intent": "SUPPORT",
                "confidence": 0.0,
                "error_message": f"Classification failed: {str(e)}"
            }
    
    def _route_by_intent(self, state: OrchestratorState) -> RoutingDecision:
        """
        Decidir ruta basado en intención clasificada.
        
        Lógica:
        - Confianza < 0.3 → SUPPORT (fallback)
        - Intención válida → Agente correspondiente
        - Error → handle_error
        """
        intent = state.get("intent", "SUPPORT")
        confidence = state.get("confidence", 0.0)
        
        # Si hay error en clasificación
        if state.get("error_message"):
            logger.warning("Routing to error handler due to classification error")
            return "error"
        
        # Si confianza muy baja, ir a SUPPORT
        if confidence < 0.3:
            logger.warning(
                f"Low confidence ({confidence:.2f}), routing to SUPPORT",
                extra={"original_intent": intent}
            )
            return "support"
        
        # Mapear intención a agente
        intent_map = {
            "EMERGENCY": "emergency",
            "SALES": "sales",
            "SCHEDULE": "schedule",
            "SUPPORT": "support",
            "AVAILABILITY": "availability"
        }
        
        route = intent_map.get(intent, "support")
        
        logger.debug(f"Routing to: {route}", extra={"intent": intent, "confidence": confidence})
        
        return route
    
    def _execute_emergency_node(self, state: OrchestratorState) -> OrchestratorState:
        """Ejecutar EmergencyAgent"""
        return self._execute_agent(state, "emergency")
    
    def _execute_sales_node(self, state: OrchestratorState) -> OrchestratorState:
        """Ejecutar SalesAgent"""
        return self._execute_agent(state, "sales")
    
    def _execute_schedule_node(self, state: OrchestratorState) -> OrchestratorState:
        """Ejecutar ScheduleAgent"""
        return self._execute_agent(state, "schedule")
    
    def _execute_support_node(self, state: OrchestratorState) -> OrchestratorState:
        """Ejecutar SupportAgent"""
        return self._execute_agent(state, "support")
    
    def _execute_availability_node(self, state: OrchestratorState) -> OrchestratorState:
        """Ejecutar AvailabilityAgent"""
        return self._execute_agent(state, "availability")
    
    def _execute_agent(self, state: OrchestratorState, agent_name: str) -> OrchestratorState:
        """
        Método común para ejecutar cualquier agente.
        
        Mantiene compatibilidad con interfaz invoke() de agentes.
        """
        try:
            start_time = time.time()
            
            # Preparar inputs para el agente
            agent_inputs = {
                "question": state["question"],
                "user_id": state["user_id"],
                "conversation_id": state.get("conversation_id"),
                "chat_history": state.get("chat_history", []),
                "media_type": state.get("media_type", "text"),
                "media_context": state.get("media_context")
            }
            
            # Ejecutar agente
            response = self.agents[agent_name].invoke(agent_inputs)
            
            execution_time = time.time() - start_time
            
            logger.info(
                f"[{self.company_config.company_id}] Agent executed: {agent_name}",
                extra={
                    "agent": agent_name,
                    "execution_time": execution_time,
                    "response_length": len(response) if response else 0
                }
            )
            
            return {
                **state,
                "agent_response": response,
                "current_agent": agent_name,
                "agent_metadata": {
                    "execution_time": execution_time,
                    "timestamp": datetime.utcnow().isoformat()
                },
                "final_response": response
            }
            
        except Exception as e:
            logger.exception(f"Error executing {agent_name}: {e}")
            
            # Respuesta de fallback
            fallback_response = (
                f"Disculpa, tuve un problema procesando tu solicitud en {self.company_config.company_name}. "
                f"¿Puedes intentar de nuevo?"
            )
            
            return {
                **state,
                "agent_response": fallback_response,
                "current_agent": agent_name,
                "is_valid": False,
                "error_message": str(e),
                "final_response": fallback_response
            }
    
    def _validate_response_node(self, state: OrchestratorState) -> OrchestratorState:
        """
        Validar calidad de respuesta del agente.
        
        Criterios de validación:
        - Tiene contenido (> 20 caracteres)
        - Menciona el nombre de la empresa
        - No contiene palabras de error
        - Longitud razonable (< 2000 caracteres)
        """
        response = state.get("agent_response", "")
        
        # Validaciones
        checks = {
            "has_content": len(response) > 20,
            "has_company_name": self.company_config.company_name.lower() in response.lower(),
            "not_error_message": not any(
                word in response.lower() 
                for word in ["error", "fallo", "problema técnico", "no pude"]
            ),
            "reasonable_length": len(response) < 2000,
            "not_empty": bool(response and response.strip())
        }
        
        # Es válida si pasa al menos 3/5 checks
        is_valid = sum(checks.values()) >= 3
        
        # Validaciones que fallan
        failed_checks = [k for k, v in checks.items() if not v]
        
        logger.info(
            f"Response validation: {'PASS' if is_valid else 'FAIL'}",
            extra={
                "checks": checks,
                "failed_checks": failed_checks,
                "agent": state.get("current_agent")
            }
        )
        
        return {
            **state,
            "is_valid": is_valid,
            "validation_errors": failed_checks
        }
    
    def _decide_next_step(self, state: OrchestratorState) -> ValidationDecision:
        """
        Decidir siguiente paso después de validación.
        
        Lógica:
        - Válida → Guardar y terminar
        - Inválida + retry < 2 → Reintentar con clasificación
        - Inválida + retry >= 2 → Fallback a support
        - Error grave → Terminar
        """
        is_valid = state.get("is_valid", False)
        retry_count = state.get("retry_count", 0)
        has_error = bool(state.get("error_message"))
        
        if is_valid:
            # Respuesta válida, guardar y terminar
            logger.debug("Valid response, proceeding to save")
            return "save"
        
        elif retry_count < 2 and not has_error:
            # Reintentar con reclasificación
            logger.warning(f"Invalid response, retrying (attempt {retry_count + 1}/2)")
            state["retry_count"] = retry_count + 1
            return "retry"
        
        elif retry_count >= 2:
            # Demasiados reintentos, usar fallback
            logger.error("Max retries reached, using fallback")
            state["fallback_used"] = True
            return "fallback"
        
        else:
            # Error grave, terminar
            logger.error("Critical error, ending execution")
            return "end"
    
    def _save_history_node(self, state: OrchestratorState) -> OrchestratorState:
        """Guardar conversación en historial"""
        conversation_id = state.get("conversation_id")
        
        if not conversation_id:
            logger.debug("No conversation_id, skipping history save")
            return state
        
        try:
            # Guardar pregunta del usuario
            self.conversation_manager.add_message(
                conversation_id=conversation_id,
                role="user",
                content=state["question"]
            )
            
            # Guardar respuesta del agente
            self.conversation_manager.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=state["final_response"],
                metadata={
                    "agent": state.get("current_agent"),
                    "intent": state.get("intent"),
                    "confidence": state.get("confidence"),
                    "execution_time": state.get("execution_time")
                }
            )
            
            logger.info(
                f"History saved to conversation {conversation_id}",
                extra={"agent": state.get("current_agent")}
            )
            
        except Exception as e:
            logger.error(f"Error saving history: {e}")
        
        return state
    
    def _handle_error_node(self, state: OrchestratorState) -> OrchestratorState:
        """Manejar errores graves"""
        error_msg = state.get("error_message", "Unknown error")
        
        logger.error(
            f"[{self.company_config.company_id}] Error handler activated",
            extra={"error": error_msg}
        )
        
        fallback_response = (
            f"Disculpa, estamos experimentando dificultades técnicas. "
            f"Por favor, contacta directamente con {self.company_config.company_name}."
        )
        
        return {
            **state,
            "final_response": fallback_response,
            "current_agent": "error_handler",
            "fallback_used": True
        }
    
    # =========================================================================
    # INTERFAZ PÚBLICA - MANTENER COMPATIBILIDAD
    # =========================================================================
    
    def get_response(
        self,
        question: str,
        user_id: str,
        conversation_id: Optional[str] = None,
        media_type: str = "text",
        media_context: Optional[Dict[str, Any]] = None,
        conversation_manager: Optional[ConversationManager] = None,
        **kwargs
    ) -> Tuple[str, str]:
        """
        Obtener respuesta del orquestador.
        
        ✅ INTERFAZ MANTENIDA - Compatible con código existente
        
        Args:
            question: Pregunta del usuario
            user_id: ID del usuario
            conversation_id: ID de conversación (opcional)
            media_type: Tipo de media (text, image, audio)
            media_context: Contexto adicional del media
            conversation_manager: Manager de conversación (opcional)
            **kwargs: Argumentos adicionales (ignorados)
        
        Returns:
            Tuple[str, str]: (respuesta, nombre_agente)
        """
        # Override conversation_manager si se proporciona
        if conversation_manager:
            self.conversation_manager = conversation_manager
        
        # Estado inicial
        initial_state: OrchestratorState = {
            "question": question,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "media_type": media_type,
            "media_context": media_context,
            "chat_history": [],
            "intent": None,
            "confidence": 0.0,
            "keywords": [],
            "reasoning": "",
            "current_agent": None,
            "agent_response": None,
            "agent_metadata": {},
            "is_valid": False,
            "validation_errors": [],
            "retry_count": 0,
            "final_response": "",
            "execution_time": 0.0,
            "timestamp": "",
            "error_message": None,
            "fallback_used": False
        }
        
        try:
            # Ejecutar grafo
            logger.debug(
                f"[{self.company_config.company_id}] Executing orchestrator graph",
                extra={"question_preview": question[:50]}
            )
            
            result = self.graph.invoke(initial_state)
            
            # Extraer respuesta y agente
            response = result.get("final_response", "")
            agent_name = result.get("current_agent", "unknown")
            
            logger.info(
                f"[{self.company_config.company_id}] Orchestration completed",
                extra={
                    "agent": agent_name,
                    "intent": result.get("intent"),
                    "is_valid": result.get("is_valid"),
                    "retry_count": result.get("retry_count"),
                    "fallback_used": result.get("fallback_used")
                }
            )
            
            return response, agent_name
            
        except Exception as e:
            logger.exception(
                f"[{self.company_config.company_id}] Critical error in orchestrator: {e}"
            )
            
            # Fallback final
            fallback_response = (
                f"Lo siento, estoy experimentando dificultades. "
                f"Por favor contacta con {self.company_config.company_name}."
            )
            
            return fallback_response, "error"
    
    # =========================================================================
    # UTILIDADES
    # =========================================================================
    
    def visualize_graph(self, output_path: str = "orchestrator_graph.png"):
        """
        Visualizar grafo como imagen.
        
        Requiere: pip install pygraphviz
        """
        try:
            from langgraph.graph import Graph
            
            # Generar visualización
            graph_image = self.graph.get_graph().draw_mermaid_png()
            
            with open(output_path, "wb") as f:
                f.write(graph_image)
            
            logger.info(f"Graph visualization saved to: {output_path}")
            
        except ImportError:
            logger.warning("Install pygraphviz to visualize graph: pip install pygraphviz")
        except Exception as e:
            logger.error(f"Error visualizing graph: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del orquestador"""
        return {
            "company_id": self.company_config.company_id,
            "available_agents": list(self.agents.keys()),
            "graph_nodes": len(self.graph.get_graph().nodes),
            "has_conversation_manager": self.conversation_manager is not None
        }
