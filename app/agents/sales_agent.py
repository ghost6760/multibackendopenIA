# app/agents/sales_agent.py
# 🧠 VERSIÓN COGNITIVA con LangGraph - Fase 4 Migración

"""
SalesAgent - Versión Cognitiva (LangGraph)

CAMBIOS PRINCIPALES:
- Hereda de CognitiveAgentBase
- Usa LangGraph para consultas de ventas multi-paso
- Razonamiento para identificar productos/servicios
- Integración con RAG para info de productos
- Mantiene MISMA firma pública: invoke(inputs: dict) -> str

MANTIENE COMPATIBILIDAD:
- Mismo nombre de clase: SalesAgent
- Misma firma pública
- Misma integración con vectorstore
"""

from typing import Dict, Any, List, Optional
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

SALES_AGENT_MANIFEST = AgentManifest(
    agent_type="sales",
    display_name="Sales Agent",
    description="Agente cognitivo para consultas de ventas, productos y cotizaciones",
    capabilities=[
        AgentCapabilityDef(
            name="product_inquiry",
            description="Consultar información de productos y servicios",
            tools_required=["knowledge_base_search", "get_product_info"],
            priority=1
        ),
        AgentCapabilityDef(
            name="pricing_inquiry",
            description="Consultar precios y generar cotizaciones",
            tools_required=["get_pricing", "calculate_estimate"],
            priority=1
        ),
        AgentCapabilityDef(
            name="schedule_consultation",
            description="Agendar consultas de valoración",
            tools_required=["schedule_consultation"],
            priority=0
        )
    ],
    required_tools=[
        "knowledge_base_search",
        "get_product_info"
    ],
    optional_tools=[
        "get_pricing",
        "calculate_estimate",
        "send_quote",
        "schedule_consultation"
    ],
    tags=["sales", "products", "pricing", "quotes", "rag"],
    priority=1,
    max_retries=3,
    timeout_seconds=45,
    metadata={
        "version": "2.0-cognitive",
        "supports_quotes": True
    }
)


# ============================================================================
# SALES AGENT COGNITIVO
# ============================================================================

class SalesAgent(CognitiveAgentBase):
    """
    Agente de ventas con base cognitiva.
    
    Maneja consultas sobre productos, precios, cotizaciones y promociones.
    Usa RAG para información detallada y actualizada de servicios.
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
            max_reasoning_steps=8,
            require_confirmation_for_critical_actions=False,
            safe_fail_on_tool_error=True,
            persist_state=False
        )
        
        # Inicializar base cognitiva
        super().__init__(
            agent_type=AgentType.SALES,
            manifest=SALES_AGENT_MANIFEST,
            config=cognitive_config
        )
        
        # Grafo de LangGraph
        self.graph = None
        self.compiled_graph = None
        
        logger.info(
            f"🧠 [{company_config.company_id}] SalesAgent initialized (cognitive mode)"
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
                f"🔍 [{self.company_config.company_id}] SalesAgent.invoke() "
                f"- Question: {inputs.get('question', '')[:100]}..."
            )
            
            # Ejecutar grafo
            final_state = self.compiled_graph.invoke(initial_state)
            
            # Extraer respuesta
            response = self._build_response_from_state(final_state)
            
            # Log telemetría
            telemetry = self._get_telemetry(final_state)
            logger.info(
                f"✅ [{self.company_config.company_id}] SalesAgent completed "
                f"- Steps: {telemetry['reasoning_steps']}, "
                f"Tools: {len(telemetry['tools_used'])}"
            )
            
            return response
            
        except Exception as e:
            logger.exception(
                f"💥 [{self.company_config.company_id}] Error in SalesAgent.invoke()"
            )
            return self._generate_error_response(str(e))
    
    def set_vectorstore_service(self, service):
        """Inyectar servicio de vectorstore (mantener firma)"""
        self._vectorstore_service = service
        logger.debug(
            f"[{self.company_config.company_id}] VectorstoreService injected to SalesAgent"
        )
    
    # ========================================================================
    # CONSTRUCCIÓN DEL GRAFO LANGGRAPH
    # ========================================================================
    
    def build_graph(self) -> StateGraph:
        """
        Construir grafo de decisión.
        
        FLUJO:
        1. Identify Product → Detectar producto/servicio mencionado
        2. Retrieve Product Info → Buscar en RAG
        3. Check Pricing Need → ¿Necesita precios?
        4. Generate Response → Respuesta con info completa
        
        Returns:
            StateGraph de LangGraph
        """
        # Crear grafo
        workflow = StateGraph(AgentState)
        
        # Añadir nodos
        workflow.add_node("identify_product", self._identify_product_node)
        workflow.add_node("retrieve_product_info", self._retrieve_product_info_node)
        workflow.add_node("get_pricing", self._get_pricing_node)
        workflow.add_node("generate_response", self._generate_response_node)
        
        # Definir edges
        workflow.set_entry_point("identify_product")
        
        workflow.add_edge("identify_product", "retrieve_product_info")
        workflow.add_edge("retrieve_product_info", "get_pricing")
        workflow.add_edge("get_pricing", "generate_response")
        workflow.add_edge("generate_response", END)
        
        logger.info(
            f"[{self.company_config.company_id}] LangGraph built for SalesAgent"
        )
        
        return workflow
    
    # ========================================================================
    # NODOS DEL GRAFO
    # ========================================================================
    
    def _identify_product_node(self, state: AgentState) -> AgentState:
        """
        Nodo 1: Identificar productos mencionados.
        """
        state["current_node"] = "identify_product"
        
        question = state["question"]
        
        # Clasificar tipo de consulta
        inquiry_type = self._classify_sales_inquiry(question)
        
        # Detectar productos mencionados
        products = self._detect_products_in_query(question)
        
        # Guardar en contexto
        state["context"]["inquiry_type"] = inquiry_type
        state["context"]["products"] = products
        
        # Registrar razonamiento
        reasoning_step = self._add_reasoning_step(
            state,
            NodeType.DECISION,
            "Identified sales inquiry",
            thought=f"Type: {inquiry_type}, Products: {products}",
            decision=f"inquiry_type={inquiry_type}"
        )
        
        state["reasoning_steps"].append(reasoning_step)
        
        logger.debug(
            f"[{self.company_config.company_id}] Products identified: {products}"
        )
        
        return state
    
    def _retrieve_product_info_node(self, state: AgentState) -> AgentState:
        """
        Nodo 2: Recuperar información de productos.
        """
        state["current_node"] = "retrieve_product_info"
        
        question = state["question"]
        products = state["context"].get("products", [])
        
        # Construir query
        search_query = self._build_product_query(products, question)
        
        # Buscar en vectorstore
        product_info = ""
        
        if self._vectorstore_service:
            try:
                docs = self._vectorstore_service.search_by_company(
                    query=search_query,
                    company_id=self.company_config.company_id,
                    k=4
                )
                
                product_info = self._extract_product_info_from_docs(docs)
                
                logger.debug(
                    f"[{self.company_config.company_id}] Retrieved {len(docs)} product docs"
                )
                
            except Exception as e:
                logger.error(f"Error searching vectorstore: {e}")
                product_info = ""
        
        # Fallback
        if not product_info:
            product_info = self._get_basic_product_info()
        
        # Guardar en contexto
        state["context"]["product_info"] = product_info
        
        # Registrar razonamiento
        reasoning_step = self._add_reasoning_step(
            state,
            NodeType.TOOL_EXECUTION,
            "Retrieved product information",
            observation=f"Info length: {len(product_info)} chars"
        )
        
        state["reasoning_steps"].append(reasoning_step)
        
        return state
    
    def _get_pricing_node(self, state: AgentState) -> AgentState:
        """
        Nodo 3: Obtener información de precios.
        """
        state["current_node"] = "get_pricing"
        
        inquiry_type = state["context"].get("inquiry_type", "general")
        product_info = state["context"].get("product_info", "")
        products = state["context"].get("products", [])
        
        # Solo buscar precios si es consulta de pricing
        pricing_info = ""
        
        if inquiry_type == "pricing":
            pricing_info = self._extract_pricing_from_context(
                product_info,
                products
            )
        
        # Guardar en contexto
        state["context"]["pricing_info"] = pricing_info
        
        # Registrar razonamiento
        reasoning_step = self._add_reasoning_step(
            state,
            NodeType.DECISION,
            "Checked pricing information",
            observation=f"Pricing needed: {inquiry_type == 'pricing'}"
        )
        
        state["reasoning_steps"].append(reasoning_step)
        
        return state
    
    def _generate_response_node(self, state: AgentState) -> AgentState:
        """
        Nodo 4: Generar respuesta final.
        """
        state["current_node"] = "generate_response"
        
        inquiry_type = state["context"].get("inquiry_type", "general")
        products = state["context"].get("products", [])
        product_info = state["context"].get("product_info", "")
        pricing_info = state["context"].get("pricing_info", "")
        
        # Generar respuesta
        response = self._build_sales_response(
            inquiry_type,
            products,
            product_info,
            pricing_info,
            state
        )
        
        state["response"] = response
        state["status"] = ExecutionStatus.SUCCESS.value
        state["completed_at"] = datetime.utcnow().isoformat()
        
        # Registrar razonamiento
        reasoning_step = self._add_reasoning_step(
            state,
            NodeType.RESPONSE_GENERATION,
            "Generated sales response",
            observation=f"Response length: {len(response)} chars"
        )
        
        state["reasoning_steps"].append(reasoning_step)
        
        logger.debug(
            f"[{self.company_config.company_id}] Sales response generated"
        )
        
        return state
    
    # ========================================================================
    # HELPERS DE ANÁLISIS
    # ========================================================================
    
    def _detect_products_in_query(self, question: str) -> List[str]:
        """Detectar productos mencionados en la query"""
        # Implementación simple - puede mejorarse con NER
        services_config = self.company_config.services
        
        products = []
        question_lower = question.lower()
        
        if isinstance(services_config, dict):
            for service_name in services_config.keys():
                if service_name.lower() in question_lower:
                    products.append(service_name)
        
        return products if products else ["servicios generales"]
    
    def _classify_sales_inquiry(self, question: str) -> str:
        """
        Clasificar tipo de consulta de ventas.
        
        Returns:
            "product_info", "pricing", "comparison", "general"
        """
        question_lower = question.lower()
        
        # Pricing
        pricing_keywords = ["precio", "costo", "cuanto", "valor", "pagar"]
        if any(kw in question_lower for kw in pricing_keywords):
            return "pricing"
        
        # Comparison
        comparison_keywords = ["diferencia", "mejor", "comparar", "vs", "versus"]
        if any(kw in question_lower for kw in comparison_keywords):
            return "comparison"
        
        # Product info
        info_keywords = ["qué es", "cómo funciona", "para qué", "beneficios", "ventajas"]
        if any(kw in question_lower for kw in info_keywords):
            return "product_info"
        
        return "general"
    
    def _build_product_query(self, products: List[str], question: str) -> str:
        """Construir query optimizada para RAG de productos"""
        products_str = " ".join(products)
        return f"productos servicios {products_str} beneficios precio duración {question}"
    
    def _extract_product_info_from_docs(self, docs: List) -> str:
        """Extraer información relevante de documentos RAG"""
        if not docs:
            return ""
        
        relevant_content = []
        
        for doc in docs[:4]:
            content = ""
            
            if hasattr(doc, 'page_content'):
                content = doc.page_content
            elif isinstance(doc, dict) and 'content' in doc:
                content = doc['content']
            
            if content:
                # Filtrar contenido relevante
                content_lower = content.lower()
                
                # Keywords de ventas
                sales_keywords = [
                    "beneficio", "ventaja", "resultado", "efecto",
                    "duración", "sesión", "precio", "costo",
                    "recomend", "indicad", "contraindicad"
                ]
                
                if any(kw in content_lower for kw in sales_keywords):
                    relevant_content.append(content)
        
        return "\n\n".join(relevant_content) if relevant_content else ""
    
    def _extract_pricing_from_context(
        self,
        context: str,
        products: List[str]
    ) -> str:
        """Extraer info de precios del contexto"""
        if not context:
            return ""
        
        # Buscar menciones de precios
        price_patterns = [
            r'\$[\d,]+',
            r'[\d,]+ pesos',
            r'desde \$[\d,]+',
            r'precio.*\$[\d,]+'
        ]
        
        pricing_mentions = []
        
        for pattern in price_patterns:
            matches = re.findall(pattern, context.lower())
            pricing_mentions.extend(matches)
        
        if pricing_mentions:
            return f"Precios mencionados: {', '.join(pricing_mentions[:3])}"
        
        # Buscar secciones que hablen de precios
        lines = context.split('\n')
        pricing_lines = [
            line for line in lines
            if any(kw in line.lower() for kw in ['precio', 'costo', 'inversión', 'valor'])
        ]
        
        return "\n".join(pricing_lines[:3]) if pricing_lines else ""
    
    def _get_basic_product_info(self) -> str:
        """Información básica de productos desde config"""
        return (
            f"Servicios disponibles en {self.company_config.company_name}:\n"
            f"{self.company_config.services}\n\n"
            f"Para información detallada sobre precios, beneficios y procedimientos, "
            f"te invitamos a consultar con nuestros especialistas."
        )
    
    # ========================================================================
    # GENERACIÓN DE RESPUESTA
    # ========================================================================
    
    def _build_sales_response(
        self,
        inquiry_type: str,
        products: List[str],
        product_info: str,
        pricing_info: str,
        state: AgentState
    ) -> str:
        """
        Construir respuesta de ventas usando _run_graph_prompt.
        """
        try:
            # Preparar template
            template = """Eres un asesor de ventas profesional de {company_name}.

TIPO DE CONSULTA: {inquiry_type}
PRODUCTOS/SERVICIOS: {products}

INFORMACIÓN DE PRODUCTOS:
{product_info}

INFORMACIÓN DE PRECIOS:
{pricing_info}

PREGUNTA DEL CLIENTE: {question}

SERVICIOS DISPONIBLES: {services}

INSTRUCCIONES:
1. Responde de manera profesional y consultiva
2. Destaca beneficios y ventajas de los productos/servicios
3. Si hay información de precios, menciónala apropiadamente
4. Si no tienes info completa, invita a agendar una valoración
5. Sé cálido, profesional y orientado a ayudar
6. Máximo 5-6 oraciones, conciso pero informativo

RESPUESTA DE VENTAS:"""
            
            # Preparar variables
            extra_vars = {
                "inquiry_type": inquiry_type,
                "products": ", ".join(products) if products else "servicios generales",
                "product_info": product_info,
                "pricing_info": pricing_info,
                "question": state["question"],
                "company_name": self.company_config.company_name,
                "services": self.company_config.services
            }
            
            # Usar _run_graph_prompt de base cognitiva
            response_content = self._run_graph_prompt(
                agent_key="sales",
                template=template,
                extra_vars=extra_vars,
                state=state
            )
            
            return response_content
            
        except Exception as e:
            logger.error(f"Error generating sales response with LLM: {e}")
            
            # Fallback programático
            return self._build_programmatic_sales_response(
                inquiry_type, products, product_info, pricing_info
            )
    
    def _build_programmatic_sales_response(
        self,
        inquiry_type: str,
        products: List[str],
        product_info: str,
        pricing_info: str
    ) -> str:
        """Generar respuesta programática (fallback)"""
        products_str = ", ".join(products) if products else "nuestros servicios"
        
        if inquiry_type == "pricing":
            if pricing_info:
                return (
                    f"💰 Información de precios para {products_str} en "
                    f"{self.company_config.company_name}:\n\n"
                    f"{pricing_info}\n\n"
                    f"¿Te gustaría agendar una valoración personalizada?"
                )
            else:
                return (
                    f"Para información detallada sobre precios de {products_str}, "
                    f"te invitamos a agendar una valoración sin costo donde nuestros "
                    f"especialistas evaluarán tu caso y te darán un presupuesto personalizado.\n\n"
                    f"¿Te gustaría agendar tu valoración?"
                )
        
        elif inquiry_type == "product_info":
            if product_info:
                return (
                    f"✨ Información sobre {products_str} en {self.company_config.company_name}:\n\n"
                    f"{product_info[:500]}\n\n"
                    f"¿Te gustaría conocer más detalles o agendar una consulta?"
                )
            else:
                return (
                    f"Ofrecemos {products_str} con tecnología de última generación.\n\n"
                    f"¿Te gustaría agendar una valoración para conocer más detalles?"
                )
        
        else:
            return (
                f"En {self.company_config.company_name} ofrecemos {self.company_config.services}.\n\n"
                f"¿Qué servicio te interesa conocer en detalle?"
            )
    
    def _generate_error_response(self, error: str) -> str:
        """Generar respuesta de error"""
        return (
            f"Disculpa, tuve un problema procesando tu consulta sobre nuestros servicios en "
            f"{self.company_config.company_name}. "
            f"¿Podrías reformular tu pregunta? 🙏"
        )
