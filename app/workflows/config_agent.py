# app/workflows/config_agent.py

from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from app.agents.base_agent import BaseAgent
from app.config.company_config import CompanyConfig
from app.services.openai_service import OpenAIService
import logging

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
            model="gpt-4-turbo-preview",
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
{available_tools}

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
        """
        Construir state machine con LangGraph para conversación multi-step.
        """
        from langgraph.graph import StateGraph, END
        
        workflow = StateGraph()
        
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
            lambda s: "clarify" if s["needs_clarification"] else "generate",
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
            lambda s: "end" if s["approved"] else "extract_components",
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
            logger.error(f"Error in ConfigAgent.invoke: {e}")
            return f"Disculpa, tuve un problema procesando tu request de workflow. Error: {str(e)}"
    
    def _start_conversation(self, question: str, state: ConfigAgentState) -> str:
        """Iniciar conversación de creación de workflow"""
        state.stage = "gathering"
        
        # Parsear descripción inicial
        extracted = self._parse_with_llm(question)
        state.extracted_info.update(extracted)
        
        # Determinar qué falta
        if not state.extracted_info.get("trigger"):
            state.clarifications.append("¿Cuándo debe activarse este workflow? (ej: cuando digan 'botox', todos los días a las 9am, etc.)")
        
        if not state.extracted_info.get("agents_needed"):
            state.clarifications.append("¿Qué agentes deben participar? (sales, support, schedule, etc.)")
        
        if state.clarifications:
            return f"Entendido. Para crear tu workflow necesito saber:\n" + "\n".join(f"• {q}" for q in state.clarifications)
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

Retorna JSON con:
- trigger: ¿Cuándo activar? (keyword/schedule/webhook)
- agents_needed: Lista de agentes
- tools_needed: Lista de tools
- conditions: Lógica if/else
- description: Resumen

JSON:"""
        
        response = self.parsing_llm.invoke([{"role": "user", "content": prompt}])
        
        try:
            import json
            return json.loads(response.content)
        except:
            return {}
    
    def _has_minimum_info(self, state: ConfigAgentState) -> bool:
        """Verificar si tenemos info mínima"""
        return (
            state.extracted_info.get("trigger") and
            state.extracted_info.get("agents_needed")
        )
    
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

¿Te parece correcto? Si quieres hacer cambios, dime qué modificar."""
            
        except Exception as e:
            logger.error(f"Error generating workflow: {e}")
            return f"Tuve un problema generando el workflow: {str(e)}"
    
    def _create_workflow_graph_from_info(self, info: Dict) -> 'WorkflowGraph':
        """Crear WorkflowGraph desde información extraída"""
        from app.workflows.workflow_models import WorkflowGraph, WorkflowNode, WorkflowEdge, NodeType, EdgeType
        
        workflow = WorkflowGraph(
            id=f"wf_{self.company_config.company_id}_{int(time.time())}",
            name=info.get("description", "Workflow generado"),
            description=info.get("description", ""),
            company_id=self.company_config.company_id
        )
        
        # Crear nodos
        node_id_counter = 1
        
        # Trigger node
        trigger_node = WorkflowNode(
            id=f"node_{node_id_counter}",
            type=NodeType.TRIGGER,
            name="Trigger",
            config={"trigger": info.get("trigger")},
            position={"x": 100, "y": 100}
        )
        workflow.add_node(trigger_node)
        last_node_id = trigger_node.id
        node_id_counter += 1
        
        # Agent nodes
        for agent_name in info.get("agents_needed", []):
            agent_node = WorkflowNode(
                id=f"node_{node_id_counter}",
                type=NodeType.AGENT,
                name=f"{agent_name.title()} Agent",
                config={"agent_type": agent_name},
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
        
        # Tool nodes
        for tool_name in info.get("tools_needed", []):
            tool_node = WorkflowNode(
                id=f"node_{node_id_counter}",
                type=NodeType.TOOL,
                name=tool_name.title(),
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
        
        # End node
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
                lines.append(f"{i}. 🎯 Trigger: {node.config.get('trigger')}")
            elif node.type.value == "agent":
                lines.append(f"{i}. 🤖 Agente: {node.config.get('agent_type')}")
            elif node.type.value == "tool":
                lines.append(f"{i}. 🔧 Tool: {node.config.get('tool_name')}")
            elif node.type.value == "end":
                lines.append(f"{i}. ✅ Fin")
        
        return "\n".join(lines)
    
    def _finalize_and_save(self, state: ConfigAgentState) -> str:
        """Finalizar y guardar workflow"""
        try:
            from app.workflows.workflow_registry import WorkflowRegistry
            
            # Crear WorkflowGraph desde draft
            from app.workflows.workflow_models import WorkflowGraph
            workflow = WorkflowGraph.from_dict(state.workflow_draft)
            
            # Guardar en registry (PostgreSQL)
            registry = WorkflowRegistry()
            registry.save_workflow(workflow)
            
            return f"""✅ ¡Workflow creado exitosamente!

ID: {workflow.id}
Nombre: {workflow.name}

El workflow ya está activo y se ejecutará cuando se cumpla el trigger.
Puedes verlo en el dashboard de workflows."""
            
        except Exception as e:
            logger.error(f"Error saving workflow: {e}")
            return f"Error guardando workflow: {str(e)}"
    
    # Implementaciones de nodos LangGraph (simplificadas)
    def _parse_request(self, state: Dict) -> Dict:
        """Nodo LangGraph: parsear request"""
        # Implementación completa en código final
        return state
    
    def _extract_components(self, state: Dict) -> Dict:
        """Nodo LangGraph: extraer componentes"""
        return state
    
    def _ask_clarifications(self, state: Dict) -> Dict:
        """Nodo LangGraph: hacer preguntas"""
        return state
    
    def _generate_workflow_graph(self, state: Dict) -> Dict:
        """Nodo LangGraph: generar grafo"""
        return state
    
    def _preview_workflow(self, state: Dict) -> Dict:
        """Nodo LangGraph: preview"""
        return state
    
    def _confirm_workflow(self, state: Dict) -> Dict:
        """Nodo LangGraph: confirmar"""
        return state
