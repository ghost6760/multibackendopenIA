EmergencyAgent Cognitivo con LangGraph
Toma decisiones sobre severidad y escalación
"""

from app.agents.base_agent import BaseAgent
from langgraph.graph import StateGraph, END
from typing import Dict, Any, List, Optional, TypedDict, Literal
import logging

logger = logging.getLogger(__name__)


# ========================================================================
# ESTADO DEL AGENTE DE EMERGENCIAS
# ========================================================================

class EmergencyAgentState(TypedDict):
    """Estado del agente de emergencias"""
    # Input
    question: str
    chat_history: List
    user_id: str
    company_id: str
    
    # Análisis de emergencia
    severity_level: str  # "critical", "urgent", "moderate", "low"
    symptoms: List[str]
    emergency_protocols: Optional[str]
    
    # Razonamiento
    reasoning_steps: List[str]
    tools_used: List[str]
    current_step: int
    
    # Decisión
    next_action: str  # "search_protocols", "assess_severity", "escalate", "respond"
    confidence: float
    
    # Output
    response: str
    should_escalate: bool
    should_end: bool


# ========================================================================
# AGENTE COGNITIVO DE EMERGENCIAS
# ========================================================================

class CognitiveEmergencyAgent(BaseAgent):
    """
    Agente de emergencias que evalúa severidad y decide protocolo.
    
    ✅ Mantiene compatibilidad con sistema existente
    ✅ Toma decisiones dinámicas sobre escalación
    """
    
    def _initialize_agent(self):
        """Inicializar agente cognitivo de emergencias"""
        self.prompt_template = self._create_prompt_template()
        self.vectorstore_service = None
        
        # Construir grafo cognitivo
        self.cognitive_graph = self._build_cognitive_graph()
        
        logger.info(f"[{self.company_config.company_id}] Cognitive EmergencyAgent initialized")
    
    def set_vectorstore_service(self, vectorstore_service):
        """✅ MANTENER: Inyectar RAG"""
        self.vectorstore_service = vectorstore_service
    
    # ========================================================================
    # CONSTRUCCIÓN DEL GRAFO
    # ========================================================================
    
    def _build_cognitive_graph(self) -> StateGraph:
        """
        Grafo de decisiones para emergencias:
        1. assess_severity → Evalúa qué tan grave es
        2. search_protocols → Busca protocolos específicos
        3. decide_escalation → Decide si escalar
        4. respond → Genera respuesta con instrucciones
        """
        workflow = StateGraph(EmergencyAgentState)
        
        # Nodos
        workflow.add_node("assess_severity", self._assess_severity_node)
        workflow.add_node("search_protocols", self._search_protocols_node)
        workflow.add_node("decide_escalation", self._decide_escalation_node)
        workflow.add_node("respond", self._respond_node)
        
        # Punto de entrada
        workflow.set_entry_point("assess_severity")
        
        # Routing desde severity assessment
        workflow.add_conditional_edges(
            "assess_severity",
            self._route_after_assessment,
            {
                "critical": "respond",  # Crítico → responder inmediatamente
                "search": "search_protocols",  # Otros → buscar protocolos
            }
        )
        
        # Después de buscar protocolos
        workflow.add_edge("search_protocols", "decide_escalation")
        
        # Decisión de escalación
        workflow.add_conditional_edges(
            "decide_escalation",
            self._evaluate_escalation,
            {
                "escalate": "respond",
                "inform": "respond"
            }
        )
        
        # Responder es el final
        workflow.add_edge("respond", END)
        
        return workflow.compile()
    
    # ========================================================================
    # NODOS DEL GRAFO
    # ========================================================================
    
    def _assess_severity_node(self, state: EmergencyAgentState) -> EmergencyAgentState:
        """
        NODO 1: Evaluar severidad de la emergencia
        """
        logger.info(f"[{self.company_config.company_id}] 🚨 Assessing severity...")
        
        question = state["question"]
        
        # Prompt para evaluar severidad
        severity_prompt = f"""Eres un especialista en emergencias médicas de {self.company_config.company_name}.

SITUACIÓN REPORTADA: "{question}"

SERVICIOS: {self.company_config.services}

EVALÚA LA SEVERIDAD:
1. CRITICAL (riesgo de vida inmediato):
   - Sangrado severo incontrolable
   - Dificultad respiratoria severa
   - Dolor de pecho intenso
   - Pérdida de conciencia
   - Reacción alérgica severa (anafilaxis)

2. URGENT (requiere atención pronta):
   - Dolor intenso persistente
   - Sangrado moderado
   - Hinchazón severa
   - Fiebre alta post-procedimiento

3. MODERATE (puede esperar evaluación):
   - Dolor moderado
   - Molestias post-tratamiento
   - Dudas sobre cuidados

4. LOW (consulta informativa):
   - Preguntas generales
   - Información de seguimiento

RESPONDE EN JSON:
{{
    "severity_level": "critical|urgent|moderate|low",
    "symptoms": ["síntoma1", "síntoma2"],
    "reasoning": "por qué esta clasificación",
    "immediate_action_needed": true/false
}}"""

        try:
            response = self.chat_model.invoke([
                {"role": "system", "content": "Eres un evaluador médico preciso y cauteloso."},
                {"role": "user", "content": severity_prompt}
            ])
            
            assessment = self._extract_json(response.content)
            
            state["severity_level"] = assessment.get("severity_level", "moderate")
            state["symptoms"] = assessment.get("symptoms", [])
            state["reasoning_steps"].append(assessment.get("reasoning", "Evaluación inicial"))
            state["current_step"] += 1
            
            logger.info(f"[{self.company_config.company_id}] 📊 Severity: {state['severity_level']}")
            logger.info(f"[{self.company_config.company_id}] 🩺 Symptoms: {', '.join(state['symptoms'])}")
            
        except Exception as e:
            logger.error(f"Error assessing severity: {e}")
            # Por seguridad, asumir urgente si hay error
            state["severity_level"] = "urgent"
            state["symptoms"] = ["síntomas no clasificados"]
        
        return state
    
    def _search_protocols_node(self, state: EmergencyAgentState) -> EmergencyAgentState:
        """
        NODO 2: Buscar protocolos específicos en RAG
        """
        logger.info(f"[{self.company_config.company_id}] 🔍 Searching emergency protocols...")
        
        try:
            if not self.vectorstore_service:
                state["emergency_protocols"] = f"Protocolos generales de {self.company_config.company_name}"
                state["tools_used"].append("search_protocols (no RAG)")
                return state
            
            # Construir query de búsqueda
            symptoms_text = " ".join(state.get("symptoms", []))
            query = f"emergencia protocolo {symptoms_text} {state['question']}"
            
            # Buscar en RAG
            docs = self.vectorstore_service.search_by_company(
                query,
                self.company_config.company_id,
                k=3
            )
            
            if docs:
                # Filtrar solo documentos relevantes a emergencias
                relevant_docs = []
                for doc in docs:
                    content = doc.page_content if hasattr(doc, 'page_content') else doc.get('content', '')
                    if any(word in content.lower() for word in ['emergencia', 'urgencia', 'dolor', 'sangrado', 'reacción', 'protocolo']):
                        relevant_docs.append(content)
                
                if relevant_docs:
                    state["emergency_protocols"] = "\n\n".join(relevant_docs)
                    logger.info(f"[{self.company_config.company_id}] ✅ Found {len(relevant_docs)} relevant protocols")
                else:
                    state["emergency_protocols"] = f"Protocolo general de emergencias de {self.company_config.company_name}"
            else:
                state["emergency_protocols"] = f"Protocolos básicos disponibles para {self.company_config.company_name}"
            
            state["tools_used"].append("search_protocols")
            
        except Exception as e:
            logger.error(f"Error searching protocols: {e}")
            state["emergency_protocols"] = "Protocolo de emergencia estándar"
        
        return state
    
    def _decide_escalation_node(self, state: EmergencyAgentState) -> EmergencyAgentState:
        """
        NODO 3: Decidir si escalar o informar
        """
        logger.info(f"[{self.company_config.company_id}] 🎯 Deciding escalation strategy...")
        
        escalation_prompt = f"""Decide si esta emergencia requiere ESCALACIÓN INMEDIATA.

NIVEL DE SEVERIDAD: {state['severity_level']}
SÍNTOMAS: {', '.join(state['symptoms'])}

PROTOCOLOS ENCONTRADOS:
{state.get('emergency_protocols', 'No disponibles')[:500]}

REGLAS:
- CRITICAL → SIEMPRE escalar inmediatamente
- URGENT → Escalar si no hay protocolo claro
- MODERATE → Informar con protocolo si existe
- LOW → Informar y sugerir seguimiento

RESPONDE EN JSON:
{{
    "decision": "escalate|inform",
    "reasoning": "por qué",
    "urgency_message": "mensaje para el usuario"
}}"""

        try:
            response = self.chat_model.invoke([
                {"role": "system", "content": "Decides escalación médica con criterio conservador."},
                {"role": "user", "content": escalation_prompt}
            ])
            
            decision = self._extract_json(response.content)
            
            state["should_escalate"] = (decision.get("decision") == "escalate")
            state["reasoning_steps"].append(decision.get("reasoning", "Evaluación de escalación"))
            state["next_action"] = decision.get("decision", "inform")
            
            logger.info(f"[{self.company_config.company_id}] 🚨 Escalate: {state['should_escalate']}")
            
        except Exception as e:
            logger.error(f"Error deciding escalation: {e}")
            # Por seguridad, escalar en caso de error
            state["should_escalate"] = True
            state["next_action"] = "escalate"
        
        return state
    
    def _respond_node(self, state: EmergencyAgentState) -> EmergencyAgentState:
        """
        NODO 4: Generar respuesta de emergencia
        """
        logger.info(f"[{self.company_config.company_id}] 💬 Generating emergency response...")
        
        response_prompt = f"""Genera respuesta de EMERGENCIA para {self.company_config.company_name}.

SITUACIÓN:
- Severidad: {state['severity_level']}
- Síntomas: {', '.join(state['symptoms'])}
- Debe escalar: {state['should_escalate']}

PROTOCOLOS DISPONIBLES:
{state.get('emergency_protocols', 'No disponibles')[:500]}

FORMATO DE RESPUESTA:
1. Reconocimiento empático de la situación
2. Instrucciones inmediatas si aplican (basadas en protocolos)
3. Indicación clara de escalación
4. Información de contacto urgente

TONO: Profesional, empático, tranquilizador pero urgente.
LONGITUD: Máximo 4 oraciones.

IMPORTANTE:
- Si CRITICAL → Instrucciones de primeros auxilios + "ESCALA AHORA"
- Si URGENT → Indicaciones + "Contacto inmediato necesario"
- Si MODERATE → Información del protocolo + "Te conectamos con especialista"

FINALIZA SIEMPRE con emoji 🚨 y mensaje de escalación a {self.company_config.company_name}"""

        try:
            response = self.chat_model.invoke([
                {"role": "system", "content": f"Eres especialista en emergencias de {self.company_config.company_name}"},
                {"role": "user", "content": response_prompt}
            ])
            
            state["response"] = response.content
            state["should_end"] = True
            
            logger.info(f"[{self.company_config.company_id}] ✅ Emergency response generated")
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            # Respuesta de fallback ultra-segura
            state["response"] = f"""Comprendo tu situación de emergencia. Por tu seguridad, es importante que contactes inmediatamente con {self.company_config.company_name}.

Escalando tu caso de emergencia ahora mismo. 🚨"""
            state["should_end"] = True
        
        return state
    
    # ========================================================================
    # ROUTING
    # ========================================================================
    
    def _route_after_assessment(self, state: EmergencyAgentState) -> str:
        """Routing después de evaluar severidad"""
        severity = state.get("severity_level", "moderate")
        
        # Si es crítico, responder INMEDIATAMENTE sin buscar
        if severity == "critical":
            state["should_escalate"] = True
            return "critical"
        
        # Otros casos, buscar protocolos primero
        return "search"
    
    def _evaluate_escalation(self, state: EmergencyAgentState) -> str:
        """Determinar tipo de respuesta según escalación"""
        return "escalate" if state.get("should_escalate") else "inform"
    
    # ========================================================================
    # INTERFAZ COMPATIBLE
    # ========================================================================
    
    def invoke(self, inputs: Dict[str, Any]) -> str:
        """
        ✅ INTERFAZ COMPATIBLE: invoke(inputs) -> str
        """
        try:
            # Estado inicial
            initial_state: EmergencyAgentState = {
                "question": inputs.get("question", ""),
                "chat_history": inputs.get("chat_history", []),
                "user_id": inputs.get("user_id", "unknown"),
                "company_id": self.company_config.company_id,
                
                # Análisis vacío
                "severity_level": "unknown",
                "symptoms": [],
                "emergency_protocols": None,
                
                # Razonamiento
                "reasoning_steps": [],
                "tools_used": [],
                "current_step": 0,
                
                # Decisión
                "next_action": "assess_severity",
                "confidence": 1.0,
                
                # Output
                "response": "",
                "should_escalate": False,
                "should_end": False
            }
            
            logger.info(f"[{self.company_config.company_id}] 🚨 Emergency assessment starting...")
            
            # Ejecutar grafo cognitivo
            final_state = self.cognitive_graph.invoke(initial_state)
            
            # Log de resumen
            logger.info(f"[{self.company_config.company_id}] 🎬 Emergency handled:")
            logger.info(f"   → Severity: {final_state['severity_level']}")
            logger.info(f"   → Escalated: {final_state['should_escalate']}")
            logger.info(f"   → Tools used: {', '.join(final_state['tools_used'])}")
            
            return final_state.get("response", f"Escalando tu caso en {self.company_config.company_name}. 🚨")
            
        except Exception as e:
            logger.exception(f"[{self.company_config.company_id}] Critical error in emergency agent")
            return f"Situación de emergencia detectada. Contacta inmediatamente con {self.company_config.company_name}. 🚨"
    
    # ========================================================================
    # MÉTODOS AUXILIARES
    # ========================================================================
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extraer JSON de respuesta del LLM"""
        import json
        import re
        
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
            return {"reasoning": text, "severity_level": "moderate"}
        except:
            return {"severity_level": "urgent"}  # Por seguridad
    
    def _create_default_prompt_template(self):
        """✅ MANTENER: Template por defecto"""
        from langchain.prompts import ChatPromptTemplate
        return ChatPromptTemplate.from_messages([
            ("system", f"Especialista en emergencias de {self.company_config.company_name}"),
            ("human", "{question}")
        ])
