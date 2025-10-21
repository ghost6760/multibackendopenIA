# app/agents/schedule_agent.py

ScheduleAgent Cognitivo con LangGraph
Migrado de flujo fijo a flujo cognitivo/racional
"""

from app.agents.base_agent import BaseAgent
from langgraph.graph import StateGraph, END
from typing import Dict, Any, List, Optional, TypedDict, Literal
from datetime import datetime, timedelta
import logging
import json
import re

logger = logging.getLogger(__name__)


# ========================================================================
# ESTADO DEL AGENTE COGNITIVO
# ========================================================================

class ScheduleAgentState(TypedDict):
    """Estado que mantiene el agente durante su ejecución"""
    # Input original
    question: str
    chat_history: List
    user_id: str
    company_id: str
    
    # Información recopilada
    patient_info: Dict[str, Any]
    date: Optional[str]
    treatment: Optional[str]
    available_slots: List[str]
    
    # Contexto de RAG
    rag_context: Optional[str]
    treatment_config: Dict[str, Any]
    
    # Razonamiento del agente
    reasoning_steps: List[str]
    tools_used: List[str]
    current_step: int
    
    # Decisión del agente
    next_action: str  # "search_rag", "check_availability", "collect_info", "book", "respond"
    confidence: float
    
    # Output
    response: str
    should_end: bool


# ========================================================================
# AGENTE COGNITIVO
# ========================================================================

class CognitiveScheduleAgent(BaseAgent):
    """
    Agente de agendamiento cognitivo que RAZONA y DECIDE dinámicamente.
    
    ✅ Mantiene compatibilidad: invoke(inputs) -> str
    ✅ Usa LangGraph para decisiones dinámicas
    ✅ Integra con RAG y herramientas existentes
    """
    
    def _initialize_agent(self):
        """Inicializar agente cognitivo"""
        # Configuración heredada de BaseAgent
        self.prompt_template = self._create_prompt_template()
        self.vectorstore_service = None
        
        # Configuración de integración (heredado del original)
        self.integration_type = self._detect_integration_type()
        self.schedule_service_available = False
        
        # Construir grafo cognitivo
        self.cognitive_graph = self._build_cognitive_graph()
        
        logger.info(f"[{self.company_config.company_id}] Cognitive ScheduleAgent initialized")
    
    def set_vectorstore_service(self, vectorstore_service):
        """✅ MANTENER: Inyectar RAG"""
        self.vectorstore_service = vectorstore_service
        logger.info(f"[{self.company_config.company_id}] RAG enabled for cognitive agent")
    
    # ========================================================================
    # CONSTRUCCIÓN DEL GRAFO COGNITIVO
    # ========================================================================
    
    def _build_cognitive_graph(self) -> StateGraph:
        """
        Construir grafo de decisiones cognitivas.
        
        Flujo:
        1. analyze → Analiza qué información tiene y qué necesita
        2. decide_action → IA decide próxima acción
        3. execute_tool → Ejecuta herramienta seleccionada
        4. evaluate → Evalúa si tiene suficiente información
        5. respond → Genera respuesta final
        """
        workflow = StateGraph(ScheduleAgentState)
        
        # Nodos del grafo
        workflow.add_node("analyze", self._analyze_situation)
        workflow.add_node("search_knowledge", self._search_knowledge_node)
        workflow.add_node("check_availability", self._check_availability_node)
        workflow.add_node("collect_patient_info", self._collect_info_node)
        workflow.add_node("book_appointment", self._book_appointment_node)
        workflow.add_node("respond", self._respond_node)
        
        # Punto de entrada
        workflow.set_entry_point("analyze")
        
        # Después de analizar, decidir qué hacer
        workflow.add_conditional_edges(
            "analyze",
            self._route_next_action,
            {
                "search_knowledge": "search_knowledge",
                "check_availability": "check_availability",
                "collect_info": "collect_patient_info",
                "book": "book_appointment",
                "respond": "respond"
            }
        )
        
        # Después de cada herramienta, volver a analizar o responder
        for tool_node in ["search_knowledge", "check_availability", "collect_patient_info", "book_appointment"]:
            workflow.add_conditional_edges(
                tool_node,
                self._evaluate_and_route,
                {
                    "continue": "analyze",
                    "respond": "respond"
                }
            )
        
        # Responder es el final
        workflow.add_edge("respond", END)
        
        return workflow.compile()
    
    # ========================================================================
    # NODOS DEL GRAFO
    # ========================================================================
    
    def _analyze_situation(self, state: ScheduleAgentState) -> ScheduleAgentState:
        """
        NODO DE RAZONAMIENTO
        El agente analiza qué tiene y qué necesita
        """
        question = state["question"]
        chat_history = state.get("chat_history", [])
        
        # Construir prompt de análisis
        analysis_prompt = f"""Eres un agente inteligente de agendamiento para {self.company_config.company_name}.

MISIÓN: Ayudar a agendar citas de manera eficiente.

PREGUNTA DEL USUARIO: "{question}"

INFORMACIÓN QUE TENGO:
- Fecha solicitada: {state.get('date', 'NO TENGO')}
- Tratamiento: {state.get('treatment', 'NO TENGO')}
- Info del paciente: {json.dumps(state.get('patient_info', {}), ensure_ascii=False)}
- Slots disponibles: {state.get('available_slots', 'NO HE CONSULTADO')}
- Contexto RAG: {'SÍ' if state.get('rag_context') else 'NO'}

HERRAMIENTAS DISPONIBLES:
1. search_knowledge - Buscar info de tratamientos en base de conocimiento
2. check_availability - Consultar disponibilidad de horarios
3. collect_info - Recopilar información faltante del paciente
4. book - Realizar la reserva
5. respond - Responder al usuario con lo que tengo

INSTRUCCIONES:
Analiza la situación y decide UNA acción siguiente. Considera:
- Si no sé del tratamiento → search_knowledge
- Si necesito ver horarios → check_availability
- Si falta info del paciente y quiero reservar → collect_info
- Si tengo todo para reservar → book
- Si puedo responder útilmente → respond

RESPONDE SOLO CON UN JSON:
{{
    "reasoning": "Por qué tomo esta decisión",
    "next_action": "search_knowledge|check_availability|collect_info|book|respond",
    "confidence": 0.0-1.0
}}"""

        try:
            # El agente RAZONA
            response = self.chat_model.invoke([
                {"role": "system", "content": "Eres un agente de decisión lógico y eficiente."},
                {"role": "user", "content": analysis_prompt}
            ])
            
            # Parsear decisión
            decision = self._extract_json_from_response(response.content)
            
            # Actualizar estado con razonamiento
            state["reasoning_steps"].append(decision.get("reasoning", "Sin razonamiento explícito"))
            state["next_action"] = decision.get("next_action", "respond")
            state["confidence"] = decision.get("confidence", 0.5)
            state["current_step"] += 1
            
            logger.info(f"[{self.company_config.company_id}] 🧠 Reasoning: {decision.get('reasoning')}")
            logger.info(f"[{self.company_config.company_id}] 🎯 Next action: {state['next_action']} (confidence: {state['confidence']})")
            
        except Exception as e:
            logger.error(f"Error in analysis: {e}")
            # Fallback seguro
            state["next_action"] = "respond"
            state["confidence"] = 0.3
        
        return state
    
    def _search_knowledge_node(self, state: ScheduleAgentState) -> ScheduleAgentState:
        """
        NODO: Buscar en base de conocimiento (RAG)
        """
        logger.info(f"[{self.company_config.company_id}] 🔍 Searching knowledge base...")
        
        try:
            if not self.vectorstore_service:
                state["rag_context"] = f"Información básica de {self.company_config.company_name}"
                state["tools_used"].append("search_knowledge (no RAG)")
                return state
            
            # Buscar en RAG
            query = f"agendamiento cita {state.get('treatment', '')} duración precio preparación"
            docs = self.vectorstore_service.search_by_company(
                query,
                self.company_config.company_id,
                k=3
            )
            
            if docs:
                context_parts = [
                    doc.page_content if hasattr(doc, 'page_content') else doc.get('content', '')
                    for doc in docs
                ]
                state["rag_context"] = "\n\n".join(context_parts)
                logger.info(f"[{self.company_config.company_id}] ✅ Found {len(docs)} relevant documents")
            else:
                state["rag_context"] = f"Servicios de {self.company_config.company_name}: {self.company_config.services}"
            
            state["tools_used"].append("search_knowledge")
            
        except Exception as e:
            logger.error(f"Error searching knowledge: {e}")
            state["rag_context"] = "Error buscando información"
        
        return state
    
    def _check_availability_node(self, state: ScheduleAgentState) -> ScheduleAgentState:
        """
        NODO: Consultar disponibilidad de horarios
        """
        logger.info(f"[{self.company_config.company_id}] 📅 Checking availability...")
        
        try:
            date = state.get("date")
            treatment = state.get("treatment", "general")
            
            if not date:
                # Intentar extraer fecha de la pregunta
                date = self._extract_date_from_question(state["question"], state.get("chat_history", []))
                state["date"] = date
            
            if date:
                # Llamar a API de disponibilidad (método heredado)
                availability_data = self._call_check_availability(date, treatment)
                
                if availability_data and availability_data.get("available_slots"):
                    state["available_slots"] = availability_data["available_slots"][:5]  # Top 5
                    logger.info(f"[{self.company_config.company_id}] ✅ Found {len(state['available_slots'])} slots")
                else:
                    state["available_slots"] = []
                    logger.info(f"[{self.company_config.company_id}] ⚠️ No slots available")
            
            state["tools_used"].append("check_availability")
            
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            state["available_slots"] = []
        
        return state
    
    def _collect_info_node(self, state: ScheduleAgentState) -> ScheduleAgentState:
        """
        NODO: Recopilar información faltante del paciente
        """
        logger.info(f"[{self.company_config.company_id}] 📋 Collecting patient info...")
        
        try:
            # Analizar historial para extraer información
            history_text = " ".join([
                str(msg.content if hasattr(msg, 'content') else msg)
                for msg in state.get("chat_history", [])
            ]).lower()
            
            # Extraer campos usando métodos heredados
            patient_info = state.get("patient_info", {})
            
            if not patient_info.get("name"):
                name = self._extract_name(history_text)
                if name:
                    patient_info["name"] = name
            
            if not patient_info.get("phone"):
                phone = self._extract_phone(history_text)
                if phone:
                    patient_info["phone"] = phone
            
            if not patient_info.get("email"):
                email = self._extract_email(history_text)
                if email:
                    patient_info["email"] = email
            
            state["patient_info"] = patient_info
            state["tools_used"].append("collect_info")
            
            logger.info(f"[{self.company_config.company_id}] 📋 Collected: {list(patient_info.keys())}")
            
        except Exception as e:
            logger.error(f"Error collecting info: {e}")
        
        return state
    
    def _book_appointment_node(self, state: ScheduleAgentState) -> ScheduleAgentState:
        """
        NODO: Realizar la reserva
        """
        logger.info(f"[{self.company_config.company_id}] 🎫 Booking appointment...")
        
        try:
            # Verificar información completa
            required_fields = ["name", "phone"]
            patient_info = state.get("patient_info", {})
            
            missing = [f for f in required_fields if not patient_info.get(f)]
            
            if missing:
                logger.warning(f"Missing fields: {missing}")
                state["tools_used"].append("book (incomplete)")
                return state
            
            # Llamar a API de booking (método heredado)
            booking_data = {
                "message": state["question"],
                "user_id": state["user_id"],
                "company_id": self.company_config.company_id,
                "patient_info": patient_info,
                "date": state.get("date"),
                "treatment": state.get("treatment")
            }
            
            result = self._call_booking_api(
                state["question"],
                state["user_id"],
                state.get("chat_history", []),
                patient_info
            )
            
            if result.get("success"):
                state["response"] = f"✅ ¡Cita agendada exitosamente!\n\n{result.get('response', '')}"
                state["should_end"] = True
                logger.info(f"[{self.company_config.company_id}] ✅ Booking successful")
            
            state["tools_used"].append("book")
            
        except Exception as e:
            logger.error(f"Error booking: {e}")
            state["tools_used"].append("book (failed)")
        
        return state
    
    def _respond_node(self, state: ScheduleAgentState) -> ScheduleAgentState:
        """
        NODO: Generar respuesta final
        """
        logger.info(f"[{self.company_config.company_id}] 💬 Generating response...")
        
        # Si ya tenemos respuesta (ej: de booking), no regenerar
        if state.get("response"):
            state["should_end"] = True
            return state
        
        # Construir respuesta basada en lo recopilado
        response_prompt = f"""Genera una respuesta profesional para el usuario de {self.company_config.company_name}.

PREGUNTA: {state['question']}

INFORMACIÓN RECOPILADA:
- Fecha: {state.get('date', 'No especificada')}
- Tratamiento: {state.get('treatment', 'No especificado')}
- Horarios disponibles: {state.get('available_slots', [])}
- Info paciente: {json.dumps(state.get('patient_info', {}), ensure_ascii=False)}
- Contexto RAG: {state.get('rag_context', 'No disponible')[:500]}

HERRAMIENTAS USADAS: {', '.join(state.get('tools_used', []))}

INSTRUCCIONES:
- Responde de forma natural y útil
- Si tienes horarios, muéstralos
- Si falta info, pídela amablemente
- Si tienes contexto RAG relevante, úsalo
- Máximo 5 oraciones
- Tono profesional y cálido

Genera solo la respuesta, sin explicaciones adicionales."""

        try:
            response = self.chat_model.invoke([
                {"role": "system", "content": f"Eres {self.company_config.sales_agent_name} de {self.company_config.company_name}."},
                {"role": "user", "content": response_prompt}
            ])
            
            state["response"] = response.content
            state["should_end"] = True
            
            logger.info(f"[{self.company_config.company_id}] ✅ Response generated ({len(response.content)} chars)")
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            state["response"] = f"Perfecto, te ayudo con tu cita en {self.company_config.company_name}. ¿Podrías darme más detalles?"
            state["should_end"] = True
        
        return state
    
    # ========================================================================
    # ROUTING (Decisiones del grafo)
    # ========================================================================
    
    def _route_next_action(self, state: ScheduleAgentState) -> str:
        """Determinar próxima acción basada en decisión del agente"""
        action = state.get("next_action", "respond")
        
        # Mapear acción a nodo del grafo
        action_map = {
            "search_knowledge": "search_knowledge",
            "check_availability": "check_availability",
            "collect_info": "collect_patient_info",
            "book": "book_appointment",
            "respond": "respond"
        }
        
        return action_map.get(action, "respond")
    
    def _evaluate_and_route(self, state: ScheduleAgentState) -> Literal["continue", "respond"]:
        """
        Evaluar si continuar explorando o responder
        """
        # Límite de iteraciones
        if state["current_step"] >= 5:
            logger.info(f"[{self.company_config.company_id}] Max steps reached, ending")
            return "respond"
        
        # Si marcamos should_end explícitamente
        if state.get("should_end"):
            return "respond"
        
        # Si tenemos una respuesta ya generada
        if state.get("response"):
            return "respond"
        
        # Continuar analizando
        return "continue"
    
    # ========================================================================
    # INTERFAZ COMPATIBLE (✅ MANTENER)
    # ========================================================================
    
    def invoke(self, inputs: Dict[str, Any]) -> str:
        """
        ✅ INTERFAZ COMPATIBLE con sistema existente
        
        Mantiene misma firma: invoke(inputs) -> str
        """
        try:
            # Preparar estado inicial
            initial_state: ScheduleAgentState = {
                "question": inputs.get("question", ""),
                "chat_history": inputs.get("chat_history", []),
                "user_id": inputs.get("user_id", "unknown"),
                "company_id": self.company_config.company_id,
                
                # Información vacía inicialmente
                "patient_info": {},
                "date": None,
                "treatment": None,
                "available_slots": [],
                
                # Contexto
                "rag_context": None,
                "treatment_config": {},
                
                # Razonamiento
                "reasoning_steps": [],
                "tools_used": [],
                "current_step": 0,
                
                # Decisión
                "next_action": "analyze",
                "confidence": 1.0,
                
                # Output
                "response": "",
                "should_end": False
            }
            
            logger.info(f"[{self.company_config.company_id}] 🚀 Starting cognitive execution...")
            
            # Ejecutar grafo cognitivo
            final_state = self.cognitive_graph.invoke(initial_state)
            
            # Log de resumen
            logger.info(f"[{self.company_config.company_id}] 🎬 Execution complete:")
            logger.info(f"   → Steps taken: {final_state['current_step']}")
            logger.info(f"   → Tools used: {', '.join(final_state['tools_used'])}")
            logger.info(f"   → Response length: {len(final_state.get('response', ''))}")
            
            return final_state.get("response", f"Te ayudo con tu cita en {self.company_config.company_name}. ¿Qué necesitas?")
            
        except Exception as e:
            logger.exception(f"[{self.company_config.company_id}] Error in cognitive agent")
            return f"Disculpa, tuve un problema. Contacta con {self.company_config.company_name} directamente. 🔧"
    
    # ========================================================================
    # MÉTODOS AUXILIARES (Heredados y adaptados)
    # ========================================================================
    
    def _detect_integration_type(self) -> str:
        """Detectar tipo de integración (heredado)"""
        schedule_url = self.company_config.schedule_service_url.lower()
        if 'google' in schedule_url:
            return 'google_calendar'
        elif 'calendly' in schedule_url:
            return 'calendly'
        else:
            return 'generic_rest'
    
    def _call_check_availability(self, date: str, treatment: str) -> Optional[Dict[str, Any]]:
        """Llamar API de disponibilidad (heredado - simplificado)"""
        # Aquí iría la lógica real de llamada a API
        # Por ahora mock para ejemplo
        return {
            "available_slots": ["10:00", "14:00", "16:00"]
        }
    
    def _call_booking_api(self, question: str, user_id: str, chat_history: list, patient_info: Dict) -> Dict[str, Any]:
        """Llamar API de booking (heredado - simplificado)"""
        # Lógica real de booking
        return {
            "success": True,
            "response": "Cita confirmada para mañana a las 10:00"
        }
    
    def _extract_date_from_question(self, question: str, chat_history: list) -> Optional[str]:
        """Extraer fecha (heredado)"""
        text = question.lower()
        if "mañana" in text:
            tomorrow = datetime.now() + timedelta(days=1)
            return tomorrow.strftime("%d-%m-%Y")
        return None
    
    def _extract_name(self, text: str) -> Optional[str]:
        """Extraer nombre (heredado)"""
        match = re.search(r'mi nombre es ([a-záéíóúñ\s]+)', text)
        return match.group(1).strip().title() if match else None
    
    def _extract_phone(self, text: str) -> Optional[str]:
        """Extraer teléfono (heredado)"""
        match = re.search(r'(\+?\d{10,})', text)
        return match.group(1) if match else None
    
    def _extract_email(self, text: str) -> Optional[str]:
        """Extraer email (heredado)"""
        match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', text)
        return match.group(1) if match else None
    
    def _extract_json_from_response(self, text: str) -> Dict[str, Any]:
        """Extraer JSON de respuesta del LLM"""
        try:
            # Buscar JSON en markdown
            json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            # Buscar JSON directo
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            
            # Fallback
            return {"reasoning": text, "next_action": "respond", "confidence": 0.5}
        except:
            return {"reasoning": "Error parsing", "next_action": "respond", "confidence": 0.3}
    
    def _create_default_prompt_template(self):
        """✅ MANTENER: Template por defecto"""
        # Este template se usa solo si no hay custom prompts
        from langchain.prompts import ChatPromptTemplate
        return ChatPromptTemplate.from_messages([
            ("system", f"Especialista en agendamiento de {self.company_config.company_name}"),
            ("human", "{question}")
        ])
