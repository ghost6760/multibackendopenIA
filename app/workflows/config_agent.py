# app/workflows/config_agent.py - VERSIÓN COMPLETA

from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from app.agents.base_agent import BaseAgent
from app.config.company_config import CompanyConfig
from app.services.openai_service import OpenAIService
import logging
import time  # ← AGREGADO
import json  # ← AGREGADO

logger = logging.getLogger(__name__)

class ConfigAgentState:
    """Estado del ConfigAgent durante la conversación"""
    def __init__(self):
        self.messages: List[Dict] = []
        self.workflow_draft: Dict = {"nodes": [], "edges": []}
        self.stage: str = "initial"  # initial, gathering, validating, confirming, complete
        self.extracted_info: Dict = {
            "trigger": None,
            "agents_needed": [],
            "tools_needed": [],
            "conditions": [],
            "description": ""
        }
        self.clarifications: List[str] = []

class ConfigAgent(BaseAgent):
    """
    Agente conversacional para crear workflows mediante chat.
    
    ✅ Hereda de BaseAgent (compatibilidad total)
    ✅ Usa LangGraph internamente para conversación multi-step
    ✅ Genera WorkflowGraph desde lenguaje natural
    """
    
    def __init__(self, company_config: CompanyConfig, openai_service: OpenAIService):
        # Inicializar como BaseAgent normal
        super().__init__(company_config, openai_service)
        
        # LLM específico para parsing (más potente)
        self.parsing_llm = ChatOpenAI(
            model="gpt-4o-mini",  # Cambiado a modelo disponible
            temperature=0.2  # Bajo para consistencia
        )
        
        # State machine de LangGraph
        self.state_machine = self._build_state_machine()
        
        # Estado actual de conversación (por usuario)
        self.user_states: Dict[str, ConfigAgentState] = {}
    
    def _initialize_agent(self):
        """Implementación requerida por BaseAgent"""
        # Crear prompt template para el ConfigAgent
        from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
        
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """Eres un asistente experto en crear workflows automatizados para {company_name}.

Tu trabajo es conversar con el usuario para entender qué workflow quiere crear y luego generarlo.

AGENTES DISPONIBLES:
- router: Clasifica intenciones
- sales: Responde consultas de ventas
- support: Soporte general
- schedule: Agendamiento de citas
- emergency: Manejo de emergencias
- availability: Verificar disponibilidad

TOOLS DISPONIBLES:
- knowledge_base: Búsqueda en base de conocimiento
- google_calendar: Integración con calendario
- send_whatsapp: Enviar mensajes WhatsApp

PROCESO:
1. Pregunta qué workflow quiere crear
2. Identifica: trigger, agentes, tools, condiciones
3. Pregunta lo que falte
4. Genera el workflow
5. Muestra preview
6. Confirma con usuario

Sé conversacional y claro."""),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{question}")
        ])
        
        # Crear chain
        from langchain.schema.output_parser import StrOutputParser
        self.chain = self.prompt_template | self.chat_model | StrOutputParser()
        
        logger.info(f"[{self.company_config.company_id}] ConfigAgent initialized with LangGraph")
    
    def _create_default_prompt_template(self):
        """Implementación requerida por BaseAgent"""
        return self.prompt_template
    
    def _build_state_machine(self) -> StateGraph:
        """Construir state machine con LangGraph"""
        from langgraph.graph import StateGraph, END
        from typing import TypedDict
        
        # Definir schema del estado
        class WorkflowState(TypedDict):
            messages: list
            extracted_info: dict
            needs_clarification: bool
            missing_components: list
            current_question: str
            workflow_graph: dict
            workflow_draft: dict
            preview_text: str
            approved: bool
            stage: str
        
        workflow = StateGraph(WorkflowState)
        
        # Nodos
        workflow.add_node("parse_request", self._parse_request)
        workflow.add_node("extract_components", self._extract_components)
        workflow.add_node("ask_clarifications", self._ask_clarifications)
        workflow.add_node("generate_graph", self._generate_workflow_graph)
        workflow.add_node("preview", self._preview_workflow)
        workflow.add_node("confirm", self._confirm_workflow)
        
        # Edges
        workflow.add_edge("parse_request", "extract_components")
        
        workflow.add_conditional_edges(
            "extract_components",
            lambda s: "clarify" if s.get("needs_clarification") else "generate",
            {
                "clarify": "ask_clarifications",
                "generate": "generate_graph"
            }
        )
        
        workflow.add_edge("ask_clarifications", "extract_components")
        workflow.add_edge("generate_graph", "preview")
        workflow.add_edge("preview", "confirm")
        
        workflow.add_conditional_edges(
            "confirm",
            lambda s: "end" if s.get("approved") else "extract_components",
            {
                "end": END,
                "extract_components": "extract_components"
            }
        )
        
        workflow.set_entry_point("parse_request")
        
        return workflow.compile()
    
    def invoke(self, inputs: Dict[str, Any]) -> str:
        """
        Override de invoke para manejar conversación de creación de workflow.
        
        Compatible con orchestrator existente.
        """
        try:
            user_id = inputs.get("user_id", "default")
            question = inputs.get("question", "")
            
            # Obtener o crear estado de usuario
            if user_id not in self.user_states:
                self.user_states[user_id] = ConfigAgentState()
            
            state = self.user_states[user_id]
            
            # Agregar mensaje
            state.messages.append({"role": "user", "content": question})
            
            # Determinar en qué etapa estamos
            if state.stage == "complete":
                # Workflow completado
                response = self._finalize_and_save(state)
                # Limpiar estado
                del self.user_states[user_id]
                return response
            
            elif state.stage == "initial":
                # Primera vez
                return self._start_conversation(question, state)
            
            else:
                # En progreso - usar state machine
                return self._continue_conversation(question, state)
            
        except Exception as e:
            logger.exception(f"Error in ConfigAgent.invoke: {e}")
            return f"Disculpa, tuve un problema procesando tu request de workflow. Error: {str(e)}"
    
    def _start_conversation(self, question: str, state: ConfigAgentState) -> str:
        """Iniciar conversación de creación de workflow"""
        state.stage = "gathering"
        
        # Parsear descripción inicial
        extracted = self._parse_with_llm(question)
        state.extracted_info.update(extracted)
        
        # Determinar qué falta
        state.clarifications = []
        
        if not state.extracted_info.get("trigger"):
            state.clarifications.append("¿Cuándo debe activarse este workflow? (ej: cuando mencionen 'botox', todos los días a las 9am, etc.)")
        
        if not state.extracted_info.get("agents_needed"):
            state.clarifications.append("¿Qué agentes deben participar? (sales, support, schedule, emergency, availability)")
        
        if state.clarifications:
            questions_text = "\n".join(f"• {q}" for q in state.clarifications)
            return f"Entendido. Para crear tu workflow necesito saber:\n\n{questions_text}"
        else:
            # Tenemos todo, generar
            return self._generate_workflow_response(state)
    
    def _continue_conversation(self, question: str, state: ConfigAgentState) -> str:
        """Continuar conversación basado en estado"""
        # Procesar respuesta del usuario
        if state.clarifications:
            # Responder clarificación
            clarification = state.clarifications.pop(0)
            # Extraer info de la respuesta
            extracted = self._parse_with_llm(f"User answered '{clarification}' with: {question}")
            state.extracted_info.update(extracted)
        
        # Verificar si tenemos todo
        if not state.clarifications and self._has_minimum_info(state):
            return self._generate_workflow_response(state)
        elif state.clarifications:
            return state.clarifications[0]
        else:
            # Pedir algo que falta
            return "Necesito más información. ¿Puedes ser más específico sobre el flujo del workflow?"
    
    def _parse_with_llm(self, text: str) -> Dict:
        """Usar LLM para extraer información estructurada"""
        prompt = f"""Extrae información de workflow de este texto:
"{text}"

Retorna SOLO un JSON válido con esta estructura exacta:
{{
  "trigger": "keyword" o "schedule" o "webhook",
  "trigger_value": "palabras clave" o "horario" o "url",
  "agents_needed": ["sales", "schedule"],
  "tools_needed": ["knowledge_base"],
  "conditions": [],
  "description": "resumen del workflow"
}}

Si no tienes información para un campo, usa null o [].

JSON:"""
        
        try:
            response = self.parsing_llm.invoke([{"role": "user", "content": prompt}])
            
            # Limpiar respuesta (a veces viene con markdown)
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            parsed = json.loads(content)
            
            # Normalizar trigger
            if parsed.get("trigger_value"):
                parsed["trigger"] = {
                    "type": parsed.get("trigger", "keyword"),
                    "value": parsed["trigger_value"]
                }
            
            return parsed
            
        except Exception as e:
            logger.warning(f"Error parsing with LLM: {e}")
            return {}
    
    def _has_minimum_info(self, state: ConfigAgentState) -> bool:
        """Verificar si tenemos info mínima"""
        info = state.extracted_info
        return bool(info.get("trigger") and info.get("agents_needed"))
    
    def _generate_workflow_response(self, state: ConfigAgentState) -> str:
        """Generar workflow y mostrarlo al usuario"""
        try:
            # Generar WorkflowGraph
            workflow_graph = self._create_workflow_graph_from_info(state.extracted_info)
            state.workflow_draft = workflow_graph.to_dict()
            state.stage = "confirming"
            
            # Generar descripción legible
            description = self._describe_workflow(workflow_graph)
            
            return f"""✅ He creado este workflow:

{description}

**Nombre:** {workflow_graph.name}
**Total de pasos:** {len(workflow_graph.nodes)}

¿Te parece correcto? Responde:
- "sí" o "perfecto" para guardarlo
- "no" o "cambia" para modificarlo
- Describe cambios específicos que quieras hacer"""
            
        except Exception as e:
            logger.exception(f"Error generating workflow: {e}")
            return f"Tuve un problema generando el workflow: {str(e)}"
    
    def _create_workflow_graph_from_info(self, info: Dict) -> 'WorkflowGraph':
        """Crear WorkflowGraph desde información extraída"""
        from app.workflows.workflow_models import WorkflowGraph, WorkflowNode, WorkflowEdge, NodeType, EdgeType
        
        # Generar nombre descriptivo
        description = info.get("description", "Workflow generado")
        workflow_name = description[:50] if description else "Nuevo Workflow"
        
        workflow = WorkflowGraph(
            id=f"wf_{self.company_config.company_id}_{int(time.time())}",
            name=workflow_name,
            description=description,
            company_id=self.company_config.company_id
        )
        
        # Crear nodos
        node_id_counter = 1
        
        # 1. Trigger node
        trigger_config = info.get("trigger", {})
        if isinstance(trigger_config, dict):
            trigger_type = trigger_config.get("type", "keyword")
            trigger_value = trigger_config.get("value", "")
        else:
            trigger_type = "keyword"
            trigger_value = str(trigger_config)
        
        trigger_node = WorkflowNode(
            id=f"node_{node_id_counter}",
            type=NodeType.TRIGGER,
            name="Trigger",
            config={
                "trigger": trigger_type,
                "keywords": [trigger_value] if trigger_type == "keyword" else [],
                "schedule": trigger_value if trigger_type == "schedule" else None
            },
            position={"x": 100, "y": 100}
        )
        workflow.add_node(trigger_node)
        last_node_id = trigger_node.id
        node_id_counter += 1
        
        # 2. Agent nodes
        for agent_name in info.get("agents_needed", []):
            agent_node = WorkflowNode(
                id=f"node_{node_id_counter}",
                type=NodeType.AGENT,
                name=f"{agent_name.title()} Agent",
                config={"agent_type": agent_name.lower()},
                position={"x": 100, "y": 100 + (node_id_counter * 100)}
            )
            workflow.add_node(agent_node)
            
            # Edge desde nodo anterior
            workflow.add_edge(WorkflowEdge(
                id=f"edge_{node_id_counter}",
                source_node_id=last_node_id,
                target_node_id=agent_node.id,
                edge_type=EdgeType.DIRECT
            ))
            
            last_node_id = agent_node.id
            node_id_counter += 1
        
        # 3. Tool nodes
        for tool_name in info.get("tools_needed", []):
            tool_node = WorkflowNode(
                id=f"node_{node_id_counter}",
                type=NodeType.TOOL,
                name=tool_name.replace("_", " ").title(),
                config={"tool_name": tool_name},
                position={"x": 100, "y": 100 + (node_id_counter * 100)}
            )
            workflow.add_node(tool_node)
            
            workflow.add_edge(WorkflowEdge(
                id=f"edge_{node_id_counter}",
                source_node_id=last_node_id,
                target_node_id=tool_node.id,
                edge_type=EdgeType.DIRECT
            ))
            
            last_node_id = tool_node.id
            node_id_counter += 1
        
        # 4. End node
        end_node = WorkflowNode(
            id=f"node_{node_id_counter}",
            type=NodeType.END,
            name="End",
            config={},
            position={"x": 100, "y": 100 + (node_id_counter * 100)}
        )
        workflow.add_node(end_node)
        
        workflow.add_edge(WorkflowEdge(
            id=f"edge_{node_id_counter}",
            source_node_id=last_node_id,
            target_node_id=end_node.id,
            edge_type=EdgeType.DIRECT
        ))
        
        return workflow
    
    def _describe_workflow(self, workflow: 'WorkflowGraph') -> str:
        """Generar descripción legible del workflow"""
        lines = []
        for i, node in enumerate(workflow.nodes.values(), 1):
            if node.type.value == "trigger":
                trigger_type = node.config.get('trigger', 'keyword')
                if trigger_type == "keyword":
                    keywords = node.config.get('keywords', [])
                    lines.append(f"{i}. 🎯 **Trigger:** Cuando mencionen {', '.join(keywords)}")
                else:
                    lines.append(f"{i}. 🎯 **Trigger:** {trigger_type}")
                    
            elif node.type.value == "agent":
                agent_type = node.config.get('agent_type', 'unknown')
                lines.append(f"{i}. 🤖 **Agente:** {agent_type.title()}")
                
            elif node.type.value == "tool":
                tool_name = node.config.get('tool_name', 'unknown')
                lines.append(f"{i}. 🔧 **Tool:** {tool_name.replace('_', ' ').title()}")
                
            elif node.type.value == "condition":
                condition = node.config.get('condition', '')
                lines.append(f"{i}. ❓ **Condición:** {condition}")
                
            elif node.type.value == "end":
                lines.append(f"{i}. ✅ **Fin del workflow**")
        
        return "\n".join(lines)
    
    def _finalize_and_save(self, state: ConfigAgentState) -> str:
        """Finalizar y guardar workflow"""
        try:
            from app.workflows.workflow_registry import WorkflowRegistry
            from app.workflows.workflow_models import WorkflowGraph
            
            # Crear WorkflowGraph desde draft
            workflow = WorkflowGraph.from_dict(state.workflow_draft)
            
            # Guardar en registry (PostgreSQL)
            registry = WorkflowRegistry()
            success = registry.save_workflow(workflow, created_by="config_agent")
            
            if success:
                return f"""✅ **¡Workflow creado exitosamente!**

📋 **ID:** `{workflow.id}`
📝 **Nombre:** {workflow.name}
🔢 **Nodos:** {len(workflow.nodes)}
🔗 **Conexiones:** {len(workflow.edges)}

El workflow ya está guardado y listo para usar.
Puedes activarlo desde el panel de workflows o ejecutarlo directamente.

¿Quieres crear otro workflow? Solo dime qué necesitas."""
            else:
                return "❌ Hubo un problema guardando el workflow. Por favor intenta de nuevo."
            
        except Exception as e:
            logger.exception(f"Error saving workflow: {e}")
            return f"❌ Error guardando workflow: {str(e)}"
    
    # ═══════════════════════════════════════════════════════════
    # IMPLEMENTACIONES COMPLETAS DE NODOS LANGGRAPH
    # ═══════════════════════════════════════════════════════════
    
    def _parse_request(self, state: Dict) -> Dict:
        """Nodo LangGraph: parsear request inicial"""
        messages = state.get("messages", [])
        if not messages:
            state["needs_clarification"] = True
            return state
        
        user_message = messages[-1]["content"]
        
        # Usar LLM para extraer intención
        extracted = self._parse_with_llm(user_message)
        
        state["extracted_info"] = extracted
        state["needs_clarification"] = not self._has_minimum_info_dict(extracted)
        
        return state
    
    def _has_minimum_info_dict(self, info: Dict) -> bool:
        """Verificar info mínima desde dict"""
        return bool(info.get("trigger") and info.get("agents_needed"))
    
    def _extract_components(self, state: Dict) -> Dict:
        """Nodo LangGraph: extraer componentes del workflow"""
        extracted = state.get("extracted_info", {})
        
        # Validar completitud
        missing = []
        if not extracted.get("trigger"):
            missing.append("trigger")
        if not extracted.get("agents_needed"):
            missing.append("agents")
        
        state["missing_components"] = missing
        state["needs_clarification"] = len(missing) > 0
        
        return state
    
    def _ask_clarifications(self, state: Dict) -> Dict:
        """Nodo LangGraph: hacer preguntas sobre componentes faltantes"""
        missing = state.get("missing_components", [])
        
        questions = {
            "trigger": "¿Cuándo debe activarse este workflow?",
            "agents": "¿Qué agentes debe usar? (sales, support, schedule, etc.)",
            "tools": "¿Necesita alguna herramienta especial? (calendar, whatsapp, etc.)"
        }
        
        state["current_question"] = questions.get(missing[0]) if missing else None
        
        return state
    
    def _generate_workflow_graph(self, state: Dict) -> Dict:
        """Nodo LangGraph: generar WorkflowGraph"""
        extracted = state.get("extracted_info", {})
        
        # Crear state temporal
        temp_state = ConfigAgentState()
        temp_state.extracted_info = extracted
        
        # Usar método existente
        workflow = self._create_workflow_graph_from_info(extracted)
        
        state["workflow_graph"] = workflow
        state["workflow_draft"] = workflow.to_dict()
        
        return state
    
    def _preview_workflow(self, state: Dict) -> Dict:
        """Nodo LangGraph: mostrar preview del workflow"""
        workflow = state.get("workflow_graph")
        
        if workflow:
            # Crear state temporal
            temp_state = ConfigAgentState()
            temp_state.extracted_info = state.get("extracted_info", {})
            
            description = self._describe_workflow(workflow)
            state["preview_text"] = description
        
        return state
    
    def _confirm_workflow(self, state: Dict) -> Dict:
        """Nodo LangGraph: confirmar con usuario"""
        messages = state.get("messages", [])
        if not messages:
            state["approved"] = False
            return state
        
        last_message = messages[-1]["content"].lower()
        
        # Detectar confirmación
        affirmative = ["si", "sí", "yes", "ok", "dale", "perfecto", "correcto", "exacto", "genial"]
        negative = ["no", "cancel", "cambiar", "modificar", "espera", "cambia"]
        
        if any(word in last_message for word in affirmative):
            state["approved"] = True
            state["stage"] = "complete"
        elif any(word in last_message for word in negative):
            state["approved"] = False
            state["stage"] = "gathering"  # Volver a recolectar
        else:
            state["needs_confirmation"] = True
            state["approved"] = False
        
        return state
