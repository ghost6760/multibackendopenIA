# NUEVO: app/agents/planning_agent.py

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from typing import TypedDict, List, Dict, Any

class PlanningState(TypedDict):
    """Estado del agente planner"""
    user_message: str
    user_id: str
    conversation_id: str
    
    # Plan generado por IA
    plan: List[Dict[str, Any]]  # [{"action": "sales_agent", "params": {...}}, ...]
    current_step: int
    
    # Resultados de ejecución
    step_results: Dict[int, Any]
    
    # Decisiones de IA
    next_decision: str  # "continue", "adjust_plan", "ask_user", "complete"
    
    # Output final
    final_response: str
    messages_to_user: List[str]


class PlanningAgent:
    """
    Agente que DECIDE qué hacer y ejecuta workflows dinámicamente.
    
    ✅ Usa LangGraph para:
       - Analizar necesidad del usuario
       - Generar plan de acción
       - Ejecutar pasos adaptativamente
       - Tomar decisiones en tiempo real
    
    ✅ Usa agentes existentes (LangChain) como herramientas
    """
    
    def __init__(self, company_config, orchestrator):
        self.company_config = company_config
        self.orchestrator = orchestrator
        
        # LLM para planificación (más potente)
        self.planner_llm = ChatOpenAI(
            model="gpt-4o",  # Modelo potente para razonamiento
            temperature=0.2
        )
        
        # LLM para decisiones
        self.decision_llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.0
        )
        
        # Construir grafo de LangGraph
        self.graph = self._build_planning_graph()
    
    def _build_planning_graph(self) -> StateGraph:
        """
        Construir grafo de planificación con LangGraph.
        
        Flujo:
        1. analyze → Analiza mensaje y genera plan
        2. execute_step → Ejecuta paso actual del plan
        3. evaluate → IA evalúa si seguir, ajustar o terminar
        4. decide_next → IA decide siguiente acción
        """
        workflow = StateGraph(PlanningState)
        
        # Nodos
        workflow.add_node("analyze", self._analyze_and_plan)
        workflow.add_node("execute_step", self._execute_current_step)
        workflow.add_node("evaluate", self._evaluate_step_result)
        workflow.add_node("decide_next", self._decide_next_action)
        workflow.add_node("finalize", self._finalize_response)
        
        # Flujo
        workflow.set_entry_point("analyze")
        
        workflow.add_edge("analyze", "execute_step")
        workflow.add_edge("execute_step", "evaluate")
        workflow.add_edge("evaluate", "decide_next")
        
        # Decisión condicional (IA decide)
        workflow.add_conditional_edges(
            "decide_next",
            self._routing_decision,
            {
                "continue": "execute_step",  # Siguiente paso del plan
                "adjust": "analyze",          # Replanificar
                "complete": "finalize",       # Terminar
                "ask_user": "finalize"        # Pedir más info
            }
        )
        
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    # ========================================================================
    # NODOS DEL GRAFO
    # ========================================================================
    
    def _analyze_and_plan(self, state: PlanningState) -> PlanningState:
        """
        IA analiza el mensaje y GENERA PLAN dinámicamente.
        """
        user_message = state["user_message"]
        
        # Prompt para que IA genere plan
        planning_prompt = f"""
Eres un planificador inteligente. Analiza este mensaje del usuario y genera un plan de acción.

MENSAJE: "{user_message}"

AGENTES DISPONIBLES:
- sales_agent: Info de productos/servicios, precios
- schedule_agent: Agendar citas, verificar disponibilidad
- support_agent: Soporte general, resolver dudas
- emergency_agent: Urgencias médicas

TOOLS DISPONIBLES:
- knowledge_base: Buscar en documentos (RAG)
- google_calendar: Calendario
- send_whatsapp: Enviar mensaje

GENERA un plan paso a paso en JSON:
{{
  "analysis": "qué necesita el usuario",
  "plan": [
    {{
      "step": 1,
      "action": "sales_agent",
      "reason": "por qué este paso",
      "params": {{"question": "..."}}
    }},
    {{
      "step": 2,
      "action": "knowledge_base",
      "reason": "buscar info específica",
      "params": {{"query": "..."}}
    }}
  ],
  "expected_outcome": "qué resultado esperamos"
}}

Solo responde con el JSON.
"""
        
        # IA genera el plan
        response = self.planner_llm.invoke([
            {"role": "user", "content": planning_prompt}
        ])
        
        # Parsear plan
        import json
        plan_json = self._extract_json(response.content)
        plan_data = json.loads(plan_json)
        
        # Actualizar estado
        state["plan"] = plan_data["plan"]
        state["current_step"] = 0
        state["step_results"] = {}
        
        logger.info(
            f"[PlanningAgent] Plan generated with {len(state['plan'])} steps"
        )
        
        return state
    
    def _execute_current_step(self, state: PlanningState) -> PlanningState:
        """
        Ejecutar el paso actual del plan.
        """
        current_step = state["current_step"]
        plan = state["plan"]
        
        if current_step >= len(plan):
            state["next_decision"] = "complete"
            return state
        
        step = plan[current_step]
        action = step["action"]
        params = step.get("params", {})
        
        logger.info(
            f"[PlanningAgent] Executing step {current_step + 1}: {action}"
        )
        
        # Ejecutar según tipo de acción
        if action.endswith("_agent"):
            # Es un agente
            agent_type = action.replace("_agent", "")
            
            result, _ = self.orchestrator.get_response(
                question=params.get("question", state["user_message"]),
                user_id=state["user_id"],
                conversation_id=state["conversation_id"]
            )
            
            state["step_results"][current_step] = {
                "type": "agent",
                "agent": agent_type,
                "result": result
            }
            
            # Agregar a mensajes para usuario
            if "messages_to_user" not in state:
                state["messages_to_user"] = []
            state["messages_to_user"].append(result)
        
        elif action == "knowledge_base":
            # Es una tool de búsqueda
            result = self.orchestrator.tool_executor.execute_tool(
                "knowledge_base",
                params
            )
            
            state["step_results"][current_step] = {
                "type": "tool",
                "tool": "knowledge_base",
                "result": result
            }
        
        else:
            # Otra tool
            result = self.orchestrator.tool_executor.execute_tool(
                action,
                params
            )
            
            state["step_results"][current_step] = {
                "type": "tool",
                "tool": action,
                "result": result
            }
        
        # Avanzar al siguiente paso
        state["current_step"] += 1
        
        return state
    
    def _evaluate_step_result(self, state: PlanningState) -> PlanningState:
        """
        IA evalúa el resultado del paso actual.
        """
        current_step = state["current_step"] - 1  # Ya avanzamos en execute
        step_result = state["step_results"].get(current_step, {})
        
        # Prompt para evaluación
        evaluation_prompt = f"""
Evalúa si este paso fue exitoso y si debemos continuar:

PASO EJECUTADO:
{state['plan'][current_step]}

RESULTADO:
{step_result.get('result', '')[:500]}

PLAN RESTANTE:
{state['plan'][current_step + 1:]}

¿El resultado es satisfactorio? ¿Debemos continuar con el plan o ajustarlo?

Responde JSON:
{{
  "satisfactory": true/false,
  "reason": "explicación",
  "recommendation": "continue" | "adjust_plan" | "complete"
}}
"""
        
        response = self.decision_llm.invoke([
            {"role": "user", "content": evaluation_prompt}
        ])
        
        import json
        evaluation = json.loads(self._extract_json(response.content))
        
        # Guardar evaluación
        state["step_results"][current_step]["evaluation"] = evaluation
        
        return state
    
    def _decide_next_action(self, state: PlanningState) -> PlanningState:
        """
        IA decide qué hacer a continuación.
        """
        current_step = state["current_step"] - 1
        evaluation = state["step_results"][current_step].get("evaluation", {})
        
        # Verificar si completamos el plan
        if state["current_step"] >= len(state["plan"]):
            state["next_decision"] = "complete"
            return state
        
        # Decisión basada en evaluación
        recommendation = evaluation.get("recommendation", "continue")
        
        if not evaluation.get("satisfactory"):
            state["next_decision"] = "adjust"
        else:
            state["next_decision"] = recommendation
        
        return state
    
    def _routing_decision(self, state: PlanningState) -> str:
        """Decidir routing basado en next_decision"""
        return state.get("next_decision", "complete")
    
    def _finalize_response(self, state: PlanningState) -> PlanningState:
        """
        Finalizar y preparar respuesta para usuario.
        """
        # Compilar todos los mensajes
        messages = state.get("messages_to_user", [])
        
        # Generar respuesta final consolidada si es necesario
        if len(messages) > 1:
            summary_prompt = f"""
Estos mensajes fueron enviados al usuario:

{chr(10).join(f"{i+1}. {msg}" for i, msg in enumerate(messages))}

Genera un mensaje de cierre apropiado (1-2 oraciones).
"""
            summary = self.decision_llm.invoke([
                {"role": "user", "content": summary_prompt}
            ]).content
            
            messages.append(summary)
        
        state["final_response"] = "\n\n".join(messages)
        state["messages_to_user"] = messages
        
        return state
    
    # ========================================================================
    # INTERFAZ PÚBLICA
    # ========================================================================
    
    def process(
        self,
        user_message: str,
        user_id: str,
        conversation_id: str
    ) -> Dict[str, Any]:
        """
        Procesar mensaje con planificación inteligente.
        
        Returns:
            {
                "messages": [...],  # Mensajes para enviar
                "plan_executed": [...],  # Plan que se ejecutó
                "final_response": "..."
            }
        """
        initial_state: PlanningState = {
            "user_message": user_message,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "plan": [],
            "current_step": 0,
            "step_results": {},
            "next_decision": "continue",
            "final_response": "",
            "messages_to_user": []
        }
        
        # Ejecutar grafo
        final_state = self.graph.invoke(initial_state)
        
        return {
            "messages": final_state["messages_to_user"],
            "plan_executed": final_state["plan"],
            "final_response": final_state["final_response"],
            "steps_completed": len(final_state["step_results"])
        }
    
    def _extract_json(self, text: str) -> str:
        """Extraer JSON de respuesta que puede tener markdown"""
        import re
        
        # Buscar JSON en markdown
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        # Buscar JSON directo
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        return text
