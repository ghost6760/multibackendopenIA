# app/agents/support_agent.py
# 🧠 VERSIÓN COGNITIVA con LangGraph - Fase 4 Migración

"""
SupportAgent - Versión Cognitiva (LangGraph)

CAMBIOS PRINCIPALES:
- Hereda de CognitiveAgentBase
- Usa LangGraph para soporte multi-paso
- Razonamiento para categorizar problemas
- Integración con RAG para documentación y FAQ
- Mantiene MISMA firma pública: invoke(inputs: dict) -> str

MANTIENE COMPATIBILIDAD:
- Mismo nombre de clase: SupportAgent
- Misma firma pública
- Misma integración con vectorstore
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

# Imports de base cognitiva
from app.agents._cognitive_base import (
    CognitiveAgentBase,
    AgentType,
    AgentState,
    AgentManifest,
    AgentCapabilityDef,
    CognitiveConfig,
    NodeType,
    ExecutionStatus
)

from app.agents._agent_tools import get_tools_for_agent

# LangGraph
from langgraph.graph import StateGraph, END

# Services
from app.config.company_config import CompanyConfig
from app.services.openai_service import OpenAIService

logger = logging.getLogger(__name__)


# ============================================================================
# MANIFEST DE CAPACIDADES
# ============================================================================

SUPPORT_AGENT_MANIFEST = AgentManifest(
    agent_type="support",
    display_name="Support Agent",
    description="Agente cognitivo para soporte técnico, FAQ y resolución de problemas",
    capabilities=[
        AgentCapabilityDef(
            name="answer_faq",
            description="Responder preguntas frecuentes",
            tools_required=["knowledge_base_search", "get_faq"],
            priority=1
        ),
        AgentCapabilityDef(
            name="troubleshoot",
            description="Diagnosticar y resolver problemas",
            tools_required=["search_documentation"],
            priority=1
        ),
        AgentCapabilityDef(
            name="create_ticket",
            description="Crear tickets de soporte",
            tools_required=["create_ticket"],
            priority=0
        )
    ],
    required_tools=[
        "knowledge_base_search",
        "get_faq"
    ],
    optional_tools=[
        "search_documentation",
        "create_ticket",
        "send_followup"
    ],
    tags=["support", "faq", "troubleshooting", "tickets", "rag"],
    priority=0,
    max_retries=2,
    timeout_seconds=40,
    metadata={
        "version": "2.0-cognitive",
        "supports_tickets": True
    }
)


# ============================================================================
# SUPPORT AGENT COGNITIVO
# ============================================================================

class SupportAgent(CognitiveAgentBase):
    """
    Agente de soporte con base cognitiva.
    
    Maneja consultas generales, FAQ, troubleshooting y creación de tickets.
    Usa RAG para documentación y respuestas precisas.
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
            enable_tool_validation=False,
            enable_guardrails=False,
            max_reasoning_steps=6,
            require_confirmation_for_critical_actions=False,
            safe_fail_on_tool_error=True,
            persist_state=False
        )
        
        # Inicializar base cognitiva
        super().__init__(
            agent_type=AgentType.SUPPORT,
            manifest=SUPPORT_AGENT_MANIFEST,
            config=cognitive_config
        )
        
        # Grafo de LangGraph
        self.graph = None
        self.compiled_graph = None
        
        logger.info(
            f"🧠 [{company_config.company_id}] SupportAgent initialized (cognitive mode)"
        )
    
    # ========================================================================
    # INTERFAZ PÚBLICA (MANTENER COMPATIBILIDAD)
    # ========================================================================
    
    def invoke(self, inputs: dict) -> str:
        """
        Punto de entrada principal (mantener firma).
        
        Args:
            inputs: Dict con keys: question, chat_history, user_id
        
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
                f"🔍 [{self.company_config.company_id}] SupportAgent.invoke() "
                f"- Question: {inputs.get('question', '')[:100]}..."
            )
            
            # Ejecutar grafo
            final_state = self.compiled_graph.invoke(initial_state)
            
            # Extraer respuesta
            response = self._build_response_from_state(final_state)
            
            # Log telemetría
            telemetry = self._get_telemetry(final_state)
            logger.info(
                f"✅ [{self.company_config.company_id}] SupportAgent completed "
                f"- Steps: {telemetry['reasoning_steps']}"
            )
            
            return response
            
        except Exception as e:
            logger.exception(
                f"💥 [{self.company_config.company_id}] Error in SupportAgent.invoke()"
            )
            return self._generate_error_response(str(e))
    
    def set_vectorstore_service(self, service):
        """Inyectar servicio de vectorstore (mantener firma)"""
        self._vectorstore_service = service
        logger.debug(
            f"[{self.company_config.company_id}] VectorstoreService injected to SupportAgent"
        )
    
    # ========================================================================
    # CONSTRUCCIÓN DEL GRAFO LANGGRAPH
    # ========================================================================
    
    def build_graph(self) -> StateGraph:
        """
        Construir grafo de decisión.
        
        FLUJO:
        1. Categorize Issue → Clasificar tipo de problema
        2. Search Knowledge → Buscar en FAQ/docs
        3. Evaluate Solution → ¿Se resolvió?
        4. Generate Response → Respuesta o crear ticket
        
        Returns:
            StateGraph de LangGraph
        """
        # Crear grafo
        workflow = StateGraph(AgentState)
        
        # Añadir nodos
        workflow.add_node("categorize_issue", self._categorize_issue_node)
        workflow.add_node("search_knowledge", self._search_knowledge_node)
        workflow.add_node("generate_response", self._generate_response_node)
        
        # Definir edges
        workflow.set_entry_point("categorize_issue")
        
        workflow.add_edge("categorize_issue", "search_knowledge")
        workflow.add_edge("search_knowledge", "generate_response")
        workflow.add_edge("generate_response", END)
        
        logger.info(
            f"[{self.company_config.company_id}] LangGraph built for SupportAgent"
        )
        
        return workflow
    
    # ========================================================================
    # NODOS DEL GRAFO
    # ========================================================================
    
    def _categorize_issue_node(self, state: AgentState) -> AgentState:
        """
        Nodo 1: Categorizar el problema de soporte.
        """
        state["current_node"] = "categorize_issue"
        
        question = state["question"]
        
        # Clasificar tipo de problema
        category = self._classify_support_issue(question)
        urgency = self._assess_urgency(question)
        
        # Guardar en contexto
        state["context"]["category"] = category
        state["context"]["urgency"] = urgency
        
        # Registrar razonamiento
        reasoning_step = self._add_reasoning_step(
            state,
            NodeType.DECISION,
            "Categorized support issue",
            thought=f"Issue classified as {category} with {urgency} urgency",
            decision=f"category={category}, urgency={urgency}"
        )
        
        state["reasoning_steps"].append(reasoning_step)
        
        logger.debug(
            f"[{self.company_config.company_id}] Issue categorized: {category} ({urgency})"
        )
        
        return state
    
    def _search_knowledge_node(self, state: AgentState) -> AgentState:
        """
        Nodo 2: Buscar en knowledge base.
        """
        state["current_node"] = "search_knowledge"
        
        question = state["question"]
        category = state["context"].get("category", "general")
        
        # Construir query optimizada
        search_query = self._build_support_query(question, category)
        
        # Buscar en vectorstore (si está disponible)
        solutions = ""
        
        if self._vectorstore_service:
            try:
                docs = self._vectorstore_service.search(
                    query=search_query,
                    company_id=self.company_config.company_id,
                    k=3
                )
                
                solutions = self._extract_solutions_from_docs(docs)
                
                logger.debug(
                    f"[{self.company_config.company_id}] Found {len(docs)} docs from RAG"
                )
                
            except Exception as e:
                logger.error(f"Error searching vectorstore: {e}")
                solutions = ""
        
        # Fallback: info por defecto
        if not solutions:
            solutions = self._get_default_support_info()
        
        # Guardar en contexto
        state["context"]["solutions"] = solutions
        
        # Registrar razonamiento
        reasoning_step = self._add_reasoning_step(
            state,
            NodeType.TOOL_EXECUTION,
            "Searched knowledge base",
            observation=f"Found solutions: {len(solutions) > 0}"
        )
        
        state["reasoning_steps"].append(reasoning_step)
        
        return state
    
    def _generate_response_node(self, state: AgentState) -> AgentState:
        """
        Nodo 3: Generar respuesta final.
        """
        state["current_node"] = "generate_response"
        
        category = state["context"].get("category", "general")
        urgency = state["context"].get("urgency", "normal")
        solutions = state["context"].get("solutions", "")
        
        # Generar respuesta usando LLM o fallback
        response = self._build_support_response(
            category,
            urgency,
            solutions,
            state
        )
        
        state["response"] = response
        state["status"] = ExecutionStatus.SUCCESS.value
        state["completed_at"] = datetime.utcnow().isoformat()
        
        # Registrar razonamiento
        reasoning_step = self._add_reasoning_step(
            state,
            NodeType.RESPONSE_GENERATION,
            "Generated support response",
            observation=f"Response length: {len(response)} chars"
        )
        
        state["reasoning_steps"].append(reasoning_step)
        
        logger.debug(
            f"[{self.company_config.company_id}] Support response generated"
        )
        
        return state
    
    # ========================================================================
    # HELPERS DE ANÁLISIS
    # ========================================================================
    
    def _classify_support_issue(self, question: str) -> str:
        """
        Clasificar tipo de problema de soporte.
        
        Returns:
            "faq", "technical", "billing", "general", "feedback"
        """
        question_lower = question.lower()
        
        # FAQ
        faq_keywords = [
            "cómo", "qué es", "para qué", "cuándo", "dónde",
            "puedo", "se puede", "horario", "atención"
        ]
        if any(kw in question_lower for kw in faq_keywords):
            return "faq"
        
        # Technical
        tech_keywords = [
            "problema", "error", "no funciona", "falla",
            "ayuda", "no puedo", "bloqueado"
        ]
        if any(kw in question_lower for kw in tech_keywords):
            return "technical"
        
        # Billing
        billing_keywords = [
            "factura", "pago", "cobro", "cargo",
            "cuenta", "reembolso", "precio"
        ]
        if any(kw in question_lower for kw in billing_keywords):
            return "billing"
        
        # Feedback
        feedback_keywords = [
            "queja", "sugerencia", "felicitaciones",
            "opinión", "recomendación", "mejorar"
        ]
        if any(kw in question_lower for kw in feedback_keywords):
            return "feedback"
        
        return "general"
    
    def _assess_urgency(self, question: str) -> str:
        """
        Evaluar urgencia de la consulta.
        
        Returns:
            "low", "normal", "high"
        """
        question_lower = question.lower()
        
        # High urgency
        high_keywords = [
            "urgente", "inmediato", "ahora", "ya",
            "problema grave", "no puedo", "bloqueado"
        ]
        if any(kw in question_lower for kw in high_keywords):
            return "high"
        
        # Low urgency
        low_keywords = [
            "cuando puedas", "no urgente", "cuando tengas tiempo",
            "sugerencia", "idea", "pregunta"
        ]
        if any(kw in question_lower for kw in low_keywords):
            return "low"
        
        return "normal"
    
    def _build_support_query(self, question: str, category: str) -> str:
        """Construir query optimizada para RAG de soporte"""
        category_keywords = {
            "faq": "pregunta frecuente faq respuesta",
            "technical": "problema solución error troubleshooting",
            "billing": "factura pago cobro precio",
            "feedback": "sugerencia mejora opinión",
            "general": "información ayuda soporte"
        }
        
        keywords = category_keywords.get(category, "soporte ayuda")
        return f"{keywords} {question}"
    
    def _extract_solutions_from_docs(self, docs: List) -> str:
        """Extraer soluciones de documentos RAG"""
        if not docs:
            return ""
        
        relevant_content = []
        
        for doc in docs[:3]:
            content = ""
            
            if hasattr(doc, 'page_content'):
                content = doc.page_content
            elif isinstance(doc, dict) and 'content' in doc:
                content = doc['content']
            
            if content:
                relevant_content.append(content)
        
        return "\n\n".join(relevant_content) if relevant_content else ""
    
    def _get_default_support_info(self) -> str:
        """Info de soporte por defecto"""
        return (
            f"Información de contacto de {self.company_config.company_name}:\n"
            f"Servicios: {self.company_config.services}\n\n"
            f"Para asistencia personalizada, nuestro equipo está disponible para ayudarte."
        )
    
    # ========================================================================
    # GENERACIÓN DE RESPUESTA
    # ========================================================================
    
    def _build_support_response(
        self,
        category: str,
        urgency: str,
        solutions: str,
        state: AgentState
    ) -> str:
        """
        Construir respuesta de soporte usando _run_graph_prompt.
        """
        try:
            # Preparar template
            template = """Eres un agente de soporte profesional de {company_name}.

CATEGORÍA DE CONSULTA: {category}
URGENCIA: {urgency}

INFORMACIÓN DE DOCUMENTACIÓN:
{solutions}

PREGUNTA DEL USUARIO: {question}

SERVICIOS: {services}

INSTRUCCIONES:
1. Responde de manera clara y útil
2. Si hay soluciones en la documentación, úsalas
3. Si no hay info completa, ofrece alternativas o contacto directo
4. Mantén un tono profesional y empático
5. Si es urgente, prioriza contacto directo
6. Máximo 5 oraciones, conciso y accionable

RESPUESTA DE SOPORTE:"""
            
            # Preparar variables
            extra_vars = {
                "category": category,
                "urgency": urgency,
                "solutions": solutions,
                "question": state["question"],
                "company_name": self.company_config.company_name,
                "services": self.company_config.services
            }
            
            # Usar _run_graph_prompt de base cognitiva
            response_content = self._run_graph_prompt(
                agent_key="support",
                template=template,
                extra_vars=extra_vars,
                state=state
            )
            
            return response_content
            
        except Exception as e:
            logger.error(f"Error generating support response with LLM: {e}")
            
            # Fallback programático
            return self._build_programmatic_support_response(
                category, urgency, solutions
            )
    
    def _build_programmatic_support_response(
        self,
        category: str,
        urgency: str,
        solutions: str
    ) -> str:
        """Generar respuesta programática (fallback)"""
        if urgency == "high":
            return (
                f"🚨 Entiendo que necesitas ayuda urgente.\n\n"
                f"Te conecto inmediatamente con un especialista de "
                f"{self.company_config.company_name} para atenderte. "
                f"¿Puedes proporcionarme tu número de contacto?"
            )
        
        if category == "faq":
            if solutions:
                return (
                    f"📚 Aquí está la información que necesitas:\n\n"
                    f"{solutions[:400]}\n\n"
                    f"¿Esto resuelve tu duda o necesitas más información?"
                )
            else:
                return (
                    f"Sobre {self.company_config.services} en {self.company_config.company_name}, "
                    f"¿podrías darme más detalles de lo que necesitas saber?"
                )
        
        elif category == "technical":
            return (
                f"🔧 Entiendo que tienes un problema técnico.\n\n"
                f"Nuestro equipo de {self.company_config.company_name} puede ayudarte directamente. "
                f"¿Puedes describirme con más detalle lo que sucede?"
            )
        
        elif category == "feedback":
            return (
                f"💬 Agradecemos tu feedback para {self.company_config.company_name}.\n\n"
                f"Tu opinión es muy importante para nosotros. "
                f"Hemos registrado tus comentarios y los compartiremos con el equipo."
            )
        
        else:
            return (
                f"Hola, estoy aquí para ayudarte con {self.company_config.company_name}.\n\n"
                f"¿En qué puedo asistirte específicamente?"
            )
    
    def _generate_error_response(self, error: str) -> str:
        """Generar respuesta de error"""
        return (
            f"Disculpa, tuve un problema procesando tu consulta. "
            f"Te conecto con un especialista de {self.company_config.company_name} "
            f"para ayudarte directamente. 🤝"
        )
