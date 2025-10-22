# app/agents/planning_agent.py
# 🧠 VERSIÓN COGNITIVA con LangGraph - Fase 3 Migración

"""
PlanningAgent - Versión Cognitiva (LangGraph)

CAMBIOS PRINCIPALES:
- Hereda de CognitiveAgentBase
- Usa LangGraph para planificación multi-paso adaptativa
- Razonamiento para generar y ajustar planes dinámicamente
- Ejecución de agentes y tools como steps del plan
- Mantiene MISMA firma pública: invoke(inputs: dict) -> str

CARACTERÍSTICAS ESPECIALES:
- Genera planes basados en análisis del usuario
- Ejecuta steps adaptativamente
- Puede replanificar en tiempo real
- Coordina múltiples agentes y tools

MANTIENE COMPATIBILIDAD:
- Mismo nombre de clase: PlanningAgent
- Misma interfaz con orchestrator
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging
import json
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
    ExecutionStatus,
    DecisionType
)

from app.agents._agent_tools import get_tools_for_agent

# LangGraph
from langgraph.graph import StateGraph, END
from langchain.prompts import ChatPromptTemplate

# Services
from app.config.company_config import CompanyConfig
from app.services.openai_service import OpenAIService

logger = logging.getLogger(__name__)


# ============================================================================
# TIPOS ESPECÍFICOS DE PLANNING
# ============================================================================

class PlanStep(Dict):
    """Representa un paso del plan"""
    step_number: int
    action_type: str  # "agent" o "tool"
    action_name: str  # Nombre del agente o tool
    params: Dict[str, Any]
    reason: str
    status: str  # "pending", "running", "completed", "failed"
    result: Optional[Any]


# ============================================================================
# MANIFEST DE CAPACIDADES
# ============================================================================

PLANNING_AGENT_MANIFEST = AgentManifest(
    agent_type="planning",
    display_name="Planning Agent",
    description="Agente cognitivo para planificación y orquestación adaptativa de workflows complejos",
    capabilities=[
        AgentCapabilityDef(
            name="analyze_user_need",
            description="Analizar necesidad del usuario y generar plan",
            tools_required=["knowledge_base_search"],
            priority=2
        ),
        AgentCapabilityDef(
            name="execute_plan_step",
            description="Ejecutar paso del plan (agente o tool)",
            tools_required=[],  # Dinámico
            priority=2
        ),
        AgentCapabilityDef(
            name="evaluate_and_adapt",
            description="Evaluar resultados y adaptar plan",
            tools_required=[],
            priority=2
        ),
        AgentCapabilityDef(
            name="coordinate_agents",
            description="Coordinar múltiples agentes",
            tools_required=[],
            priority=1
        )
    ],
    required_tools=[
        "knowledge_base_search"
    ],
    optional_tools=[
        # Puede usar cualquier tool disponible dinámicamente
    ],
    tags=["planning", "orchestration", "adaptive", "multi-agent", "complex"],
    priority=2,
    max_retries=2,
    timeout_seconds=120,  # Más tiempo para workflows complejos
    metadata={
        "version": "2.0-cognitive",
        "adaptive": True,
        "can_coordinate_agents": True
    }
)


# ============================================================================
# PLANNING AGENT COGNITIVO
# ============================================================================

class PlanningAgent(CognitiveAgentBase):
    """
    Agente de planificación con base cognitiva.
    
    CAPACIDADES ESPECIALES:
    - Análisis de necesidad del usuario
    - Generación de plan multi-paso
    - Ejecución adaptativa
    - Replanificación en tiempo real
    - Coordinación de agentes y tools
    """
    
    def __init__(
        self,
        company_config: CompanyConfig,
        openai_service: OpenAIService,
        orchestrator=None
    ):
        """
        Args:
            company_config: Configuración de la empresa
            openai_service: Servicio de OpenAI
            orchestrator: Orchestrator para ejecutar otros agentes
        """
        self.company_config = company_config
        self.openai_service = openai_service
        self.chat_model = openai_service.get_chat_model()
        self.orchestrator = orchestrator
        
        # LLM más potente para planificación
        self.planner_llm = openai_service.get_chat_model(
            model_name="gpt-4o",
            temperature=0.2
        )
        
        # LLM para decisiones rápidas
        self.decision_llm = openai_service.get_chat_model(
            model_name="gpt-4o-mini",
            temperature=0.0
        )
        
        # Configuración cognitiva
        cognitive_config = CognitiveConfig(
            enable_reasoning_traces=True,
            enable_tool_validation=True,
            enable_guardrails=True,
            max_reasoning_steps=20,  # Muchos pasos para planificación
            require_confirmation_for_critical_actions=True,
            safe_fail_on_tool_error=True,
            persist_state=True
        )
        
        # Inicializar base cognitiva
        super().__init__(
            agent_type=AgentType.PLANNING,
            manifest=PLANNING_AGENT_MANIFEST,
            config=cognitive_config
        )
        
        # Grafo de LangGraph
        self.graph = None
        self.compiled_graph = None
        
        logger.info(
            f"🧠 [{company_config.company_id}] PlanningAgent initialized "
            f"(cognitive mode, ADAPTIVE)"
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
            
            # Añadir contexto específico de planning
            initial_state["context"]["available_agents"] = self._get_available_agents()
            initial_state["context"]["available_tools"] = self._get_available_tools()
            
            # Log inicio
            logger.info(
                f"📋 [{self.company_config.company_id}] PlanningAgent.invoke() "
                f"- Question: {inputs.get('question', '')[:150]}..."
            )
            
            # Ejecutar grafo
            final_state = self.compiled_graph.invoke(initial_state)
            
            # Extraer respuesta
            response = self._build_response_from_state(final_state)
            
            # Log telemetría
            telemetry = self._get_telemetry(final_state)
            plan_executed = final_state["context"].get("plan", [])
            
            logger.info(
                f"✅ [{self.company_config.company_id}] PlanningAgent completed "
                f"- Steps executed: {len(plan_executed)}, "
                f"Reasoning: {telemetry['reasoning_steps']}, "
                f"Latency: {telemetry['total_latency_ms']:.2f}ms"
            )
            
            return response
            
        except Exception as e:
            logger.exception(
                f"💥 [{self.company_config.company_id}] Error in PlanningAgent.invoke()"
            )
            return self._generate_error_response(str(e))
    
    def set_orchestrator(self, orchestrator):
        """Inyectar orchestrator para ejecutar otros agentes"""
        self.orchestrator = orchestrator
        logger.debug(
            f"[{self.company_config.company_id}] Orchestrator injected to PlanningAgent"
        )
    
    # ========================================================================
    # CONSTRUCCIÓN DEL GRAFO LANGGRAPH
    # ========================================================================
    
    def build_graph(self) -> StateGraph:
        """
        Construir grafo de planificación adaptativa.
        
        FLUJO:
        1. Analyze Need → Analizar necesidad del usuario
        2. Generate Plan → Generar plan multi-paso
        3. Execute Step → Ejecutar paso actual
        4. Evaluate Result → Evaluar resultado del paso
        5. Decide Next → Decidir siguiente acción (continuar, replanificar, finalizar)
        
        Returns:
            StateGraph de LangGraph
        """
        # Crear grafo
        workflow = StateGraph(AgentState)
        
        # Añadir nodos
        workflow.add_node("analyze_need", self._analyze_need_node)
        workflow.add_node("generate_plan", self._generate_plan_node)
        workflow.add_node("execute_step", self._execute_step_node)
        workflow.add_node("evaluate_result", self._evaluate_result_node)
        workflow.add_node("decide_next", self._decide_next_node)
        workflow.add_node("finalize_response", self._finalize_response_node)
        
        # Definir edges
        workflow.set_entry_point("analyze_need")
        
        workflow.add_edge("analyze_need", "generate_plan")
        workflow.add_edge("generate_plan", "execute_step")
        workflow.add_edge("execute_step", "evaluate_result")
        workflow.add_edge("evaluate_result", "decide_next")
        
        # Condicional: continuar, replanificar o finalizar
        workflow.add_conditional_edges(
            "decide_next",
            self._routing_decision,
            {
                "continue": "execute_step",      # Siguiente paso
                "replan": "generate_plan",       # Replanificar
                "finalize": "finalize_response"  # Terminar
            }
        )
        
        workflow.add_edge("finalize_response", END)
        
        logger.info(
            f"[{self.company_config.company_id}] LangGraph built for PlanningAgent "
            f"(6 nodes, ADAPTIVE)"
        )
        
        return workflow
    
    # ========================================================================
    # NODOS DEL GRAFO
    # ========================================================================
    
    def _analyze_need_node(self, state: AgentState) -> AgentState:
        """
        Nodo 1: Analizar necesidad del usuario.
        """
        state["current_node"] = "analyze_need"
        
        question = state["question"]
        chat_history = state["chat_history"]
        
        # Analizar con LLM
        analysis = self._analyze_user_need(question, chat_history)
        
        # Registrar razonamiento
        reasoning_step = self._add_reasoning_step(
            state,
            NodeType.REASONING,
            "Analyzing user need",
            thought=f"User asks: '{question[:100]}'",
            observation=f"Analysis: {analysis.get('summary', '')}",
            decision=f"Complexity: {analysis.get('complexity', 'unknown')}",
            confidence=analysis.get("confidence", 0.5)
        )
        
        state["reasoning_steps"].append(reasoning_step)
        
        # Guardar análisis
        state["context"]["need_analysis"] = analysis
        state["confidence_scores"]["need_analysis"] = analysis.get("confidence", 0.5)
        
        logger.info(
            f"[{self.company_config.company_id}] Need analyzed: "
            f"{analysis.get('summary', '')[:100]}..."
        )
        
        return state
    
    def _generate_plan_node(self, state: AgentState) -> AgentState:
        """
        Nodo 2: Generar plan de acción.
        """
        state["current_node"] = "generate_plan"
        
        need_analysis = state["context"].get("need_analysis", {})
        available_agents = state["context"].get("available_agents", [])
        available_tools = state["context"].get("available_tools", [])
        
        # Verificar si es replanificación
        is_replan = state["context"].get("current_step_number", 0) > 0
        
        if is_replan:
            logger.info("Replanning based on previous results...")
            previous_results = state["context"].get("step_results", {})
        else:
            previous_results = {}
        
        # Generar plan con LLM
        plan = self._generate_plan(
            need_analysis=need_analysis,
            available_agents=available_agents,
            available_tools=available_tools,
            previous_results=previous_results,
            state=state
        )
        
        # Registrar razonamiento
        reasoning_step = self._add_reasoning_step(
            state,
            NodeType.DECISION,
            "Generated execution plan" if not is_replan else "Regenerated plan",
            thought=f"Need: {need_analysis.get('summary', '')[:50]}",
            decision=f"Plan with {len(plan)} steps",
            confidence=0.8
        )
        
        state["reasoning_steps"].append(reasoning_step)
        
        # Guardar plan
        state["context"]["plan"] = plan
        state["context"]["current_step_number"] = 0
        state["context"]["step_results"] = {}
        
        logger.info(
            f"[{self.company_config.company_id}] Plan generated with {len(plan)} steps"
        )
        
        # Log plan
        for i, step in enumerate(plan):
            logger.debug(
                f"  Step {i+1}: {step.get('action_type')} - "
                f"{step.get('action_name')} - {step.get('reason')}"
            )
        
        return state
    
    def _execute_step_node(self, state: AgentState) -> AgentState:
        """
        Nodo 3: Ejecutar paso actual del plan.
        """
        state["current_node"] = "execute_step"
        
        plan = state["context"].get("plan", [])
        current_step_number = state["context"].get("current_step_number", 0)
        
        # Verificar si hay más pasos
        if current_step_number >= len(plan):
            state["context"]["should_finalize"] = True
            return state
        
        current_step = plan[current_step_number]
        
        # Log inicio
        logger.info(
            f"[{self.company_config.company_id}] Executing step {current_step_number + 1}/{len(plan)}: "
            f"{current_step.get('action_type')} - {current_step.get('action_name')}"
        )
        
        # Registrar razonamiento
        reasoning_step = self._add_reasoning_step(
            state,
            NodeType.TOOL_EXECUTION,
            f"Executing step {current_step_number + 1}",
            action=f"{current_step.get('action_type')}: {current_step.get('action_name')}",
            observation="Waiting for result..."
        )
        state["reasoning_steps"].append(reasoning_step)
        
        # Ejecutar según tipo
        action_type = current_step.get("action_type")
        action_name = current_step.get("action_name")
        params = current_step.get("params", {})
        
        if action_type == "agent":
            result = self._execute_agent(action_name, params, state)
        elif action_type == "tool":
            result = self._execute_tool_step(action_name, params, state)
        else:
            result = {
                "success": False,
                "error": f"Unknown action type: {action_type}"
            }
        
        # Guardar resultado
        current_step["status"] = "completed" if result.get("success") else "failed"
        current_step["result"] = result
        
        state["context"]["step_results"][current_step_number] = result
        state["context"]["current_step_number"] = current_step_number + 1
        
        # Actualizar observación
        reasoning_step["observation"] = (
            f"Result: {result.get('data', result.get('error', 'unknown'))}"
        )
        
        return state
    
    def _evaluate_result_node(self, state: AgentState) -> AgentState:
        """
        Nodo 4: Evaluar resultado del paso ejecutado.
        """
        state["current_node"] = "evaluate_result"
        
        current_step_number = state["context"].get("current_step_number", 1) - 1
        step_result = state["context"]["step_results"].get(current_step_number, {})
        plan = state["context"].get("plan", [])
        
        if current_step_number >= len(plan):
            # Ya no hay más pasos
            state["context"]["evaluation"] = {
                "satisfactory": True,
                "recommendation": "finalize"
            }
            return state
        
        current_step = plan[current_step_number]
        
        # Evaluar con LLM
        evaluation = self._evaluate_step_result(
            step=current_step,
            result=step_result,
            remaining_plan=plan[current_step_number + 1:],
            state=state
        )
        
        # Registrar razonamiento
        reasoning_step = self._add_reasoning_step(
            state,
            NodeType.DECISION,
            f"Evaluated step {current_step_number + 1} result",
            thought=f"Step was {'successful' if step_result.get('success') else 'failed'}",
            decision=f"Recommendation: {evaluation.get('recommendation')}",
            confidence=evaluation.get("confidence", 0.7)
        )
        
        state["reasoning_steps"].append(reasoning_step)
        
        # Guardar evaluación
        state["context"]["evaluation"] = evaluation
        
        logger.info(
            f"[{self.company_config.company_id}] Step evaluation: "
            f"satisfactory={evaluation.get('satisfactory')}, "
            f"recommendation={evaluation.get('recommendation')}"
        )
        
        return state
    
    def _decide_next_node(self, state: AgentState) -> AgentState:
        """
        Nodo 5: Decidir siguiente acción.
        """
        state["current_node"] = "decide_next"
        
        evaluation = state["context"].get("evaluation", {})
        current_step_number = state["context"].get("current_step_number", 0)
        plan = state["context"].get("plan", [])
        
        # Verificar si debe finalizar
        if state["context"].get("should_finalize", False):
            decision = "finalize"
        elif current_step_number >= len(plan):
            decision = "finalize"
        elif not evaluation.get("satisfactory"):
            # Si el paso falló y era crítico, replanificar
            decision = "replan"
        else:
            # Seguir con el plan
            recommendation = evaluation.get("recommendation", "continue")
            decision = recommendation
        
        state["context"]["next_decision"] = decision
        
        # Registrar razonamiento
        reasoning_step = self._add_reasoning_step(
            state,
            NodeType.DECISION,
            "Decided next action",
            thought=f"Evaluation: {evaluation.get('reason', '')}",
            decision=f"Next: {decision}",
            confidence=0.9
        )
        
        state["reasoning_steps"].append(reasoning_step)
        
        logger.info(f"[{self.company_config.company_id}] Next decision: {decision}")
        
        return state
    
    def _finalize_response_node(self, state: AgentState) -> AgentState:
        """
        Nodo 6: Finalizar y generar respuesta.
        """
        state["current_node"] = "finalize_response"
        
        plan = state["context"].get("plan", [])
        step_results = state["context"].get("step_results", {})
        
        # Generar respuesta final consolidando resultados
        response = self._generate_final_response(
            plan=plan,
            step_results=step_results,
            state=state
        )
        
        state["response"] = response
        state["status"] = ExecutionStatus.SUCCESS.value
        state["completed_at"] = datetime.utcnow().isoformat()
        
        # Registrar razonamiento final
        reasoning_step = self._add_reasoning_step(
            state,
            NodeType.RESPONSE_GENERATION,
            "Generated final consolidated response",
            observation=f"Executed {len(step_results)} steps successfully"
        )
        
        state["reasoning_steps"].append(reasoning_step)
        
        logger.info(
            f"[{self.company_config.company_id}] Planning completed, response generated"
        )
        
        return state
    
    # ========================================================================
    # DECISIONES CONDICIONALES
    # ========================================================================
    
    def _routing_decision(self, state: AgentState) -> str:
        """
        Determinar routing basado en decisión.
        
        Returns:
            "continue", "replan" o "finalize"
        """
        decision = state["context"].get("next_decision", "finalize")
        
        # Validar decisión
        valid_decisions = ["continue", "replan", "finalize"]
        if decision not in valid_decisions:
            logger.warning(f"Invalid decision '{decision}', defaulting to finalize")
            return "finalize"
        
        return decision
    
    # ========================================================================
    # ANÁLISIS Y GENERACIÓN DE PLAN
    # ========================================================================
    
    def _analyze_user_need(
        self,
        question: str,
        chat_history: List
    ) -> Dict[str, Any]:
        """
        Analizar necesidad del usuario con LLM.
        """
        analysis_prompt = f"""Analiza esta consulta del usuario y determina qué necesita.

MENSAJE: "{question}"

HISTORIAL RECIENTE:
{self._format_history_for_prompt(chat_history[-3:])}

Responde en JSON:
{{
  "summary": "resumen de lo que necesita el usuario",
  "complexity": "simple|medium|complex",
  "requires_agents": ["lista", "de", "agentes"],
  "requires_tools": ["lista", "de", "tools"],
  "confidence": 0.0-1.0,
  "reasoning": "por qué llegaste a esta conclusión"
}}

Solo responde con el JSON."""
        
        try:
            response = self.planner_llm.invoke([
                {"role": "user", "content": analysis_prompt}
            ])
            
            analysis_json = self._extract_json(response.content)
            analysis = json.loads(analysis_json)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing user need: {e}")
            # Fallback analysis
            return {
                "summary": question[:100],
                "complexity": "medium",
                "requires_agents": ["support"],
                "requires_tools": [],
                "confidence": 0.3,
                "reasoning": "Fallback analysis due to error"
            }
    
    def _generate_plan(
        self,
        need_analysis: Dict[str, Any],
        available_agents: List[str],
        available_tools: List[str],
        previous_results: Dict[int, Any],
        state: AgentState
    ) -> List[Dict[str, Any]]:
        """
        Generar plan de ejecución con LLM.
        """
        planning_prompt = self._build_planning_prompt(
            need_analysis,
            available_agents,
            available_tools,
            previous_results
        )
        
        try:
            response = self.planner_llm.invoke([
                {"role": "user", "content": planning_prompt}
            ])
            
            plan_json = self._extract_json(response.content)
            plan_data = json.loads(plan_json)
            
            # Parsear plan
            plan = plan_data.get("plan", [])
            
            # Validar y normalizar steps
            normalized_plan = []
            for i, step in enumerate(plan):
                normalized_step = {
                    "step_number": i + 1,
                    "action_type": step.get("action_type", "tool"),
                    "action_name": step.get("action_name", "unknown"),
                    "params": step.get("params", {}),
                    "reason": step.get("reason", ""),
                    "status": "pending",
                    "result": None
                }
                normalized_plan.append(normalized_step)
            
            return normalized_plan
            
        except Exception as e:
            logger.error(f"Error generating plan: {e}")
            # Fallback plan simple
            return [{
                "step_number": 1,
                "action_type": "agent",
                "action_name": "support",
                "params": {"question": state["question"]},
                "reason": "Fallback to support agent due to planning error",
                "status": "pending",
                "result": None
            }]
    
    def _build_planning_prompt(
        self,
        need_analysis: Dict[str, Any],
        available_agents: List[str],
        available_tools: List[str],
        previous_results: Dict[int, Any]
    ) -> str:
        """Construir prompt para generación de plan"""
        base_prompt = f"""Genera un plan de acción paso a paso para cumplir esta necesidad del usuario.

ANÁLISIS DE NECESIDAD:
{json.dumps(need_analysis, indent=2, ensure_ascii=False)}

AGENTES DISPONIBLES:
{', '.join(available_agents)}

TOOLS DISPONIBLES:
{', '.join(available_tools[:20])}  # Limitar lista

"""
        
        if previous_results:
            base_prompt += f"""
RESULTADOS PREVIOS (para replanificación):
{json.dumps(previous_results, indent=2, ensure_ascii=False)}

"""
        
        base_prompt += """
GENERA un plan en JSON:
{
  "analysis": "análisis de la estrategia",
  "plan": [
    {
      "step": 1,
      "action_type": "agent" | "tool",
      "action_name": "nombre del agente o tool",
      "params": {"key": "value"},
      "reason": "por qué este paso"
    }
  ],
  "expected_outcome": "resultado esperado"
}

REGLAS:
- Máximo 5 steps para eficiencia
- Usa agentes para tareas complejas (sales, schedule, support)
- Usa tools para acciones específicas
- Cada step debe tener propósito claro
- Si hay resultados previos, ajusta el plan

Solo responde con el JSON."""
        
        return base_prompt
    
    # ========================================================================
    # EJECUCIÓN DE STEPS
    # ========================================================================
    
    def _execute_agent(
        self,
        agent_name: str,
        params: Dict[str, Any],
        state: AgentState
    ) -> Dict[str, Any]:
        """
        Ejecutar un agente.
        """
        if not self.orchestrator:
            return {
                "success": False,
                "error": "Orchestrator not configured"
            }
        
        try:
            # Preparar inputs para el agente
            agent_inputs = {
                "question": params.get("question", state["question"]),
                "chat_history": state["chat_history"],
                "user_id": state["user_id"],
                "company_id": state.get("company_id")
            }
            
            # Obtener agente del orchestrator
            agent = self.orchestrator.agents.get(agent_name)
            
            if not agent:
                return {
                    "success": False,
                    "error": f"Agent '{agent_name}' not found"
                }
            
            # Ejecutar agente
            response = agent.invoke(agent_inputs)
            
            return {
                "success": True,
                "data": response,
                "type": "agent",
                "agent_name": agent_name
            }
            
        except Exception as e:
            logger.error(f"Error executing agent '{agent_name}': {e}")
            return {
                "success": False,
                "error": str(e),
                "type": "agent",
                "agent_name": agent_name
            }
    
    def _execute_tool_step(
        self,
        tool_name: str,
        params: Dict[str, Any],
        state: AgentState
    ) -> Dict[str, Any]:
        """
        Ejecutar una tool.
        """
        if not self._tool_executor:
            return {
                "success": False,
                "error": "ToolExecutor not configured"
            }
        
        try:
            result = self._tool_executor.execute(
                tool_name=tool_name,
                params=params,
                company_id=state.get("company_id"),
                user_id=state.get("user_id")
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {e}")
            return {
                "success": False,
                "error": str(e),
                "type": "tool",
                "tool_name": tool_name
            }
    
    # ========================================================================
    # EVALUACIÓN
    # ========================================================================
    
    def _evaluate_step_result(
        self,
        step: Dict[str, Any],
        result: Dict[str, Any],
        remaining_plan: List[Dict[str, Any]],
        state: AgentState
    ) -> Dict[str, Any]:
        """
        Evaluar resultado de un paso con LLM.
        """
        evaluation_prompt = f"""Evalúa si este paso fue exitoso y si debemos continuar con el plan.

PASO EJECUTADO:
{json.dumps(step, indent=2, ensure_ascii=False)}

RESULTADO:
{json.dumps(result, indent=2, ensure_ascii=False)}

PLAN RESTANTE:
{json.dumps(remaining_plan, indent=2, ensure_ascii=False)}

Responde en JSON:
{{
  "satisfactory": true|false,
  "reason": "explicación",
  "recommendation": "continue" | "replan" | "finalize",
  "confidence": 0.0-1.0
}}

Solo responde con el JSON."""
        
        try:
            response = self.decision_llm.invoke([
                {"role": "user", "content": evaluation_prompt}
            ])
            
            evaluation_json = self._extract_json(response.content)
            evaluation = json.loads(evaluation_json)
            
            return evaluation
            
        except Exception as e:
            logger.error(f"Error evaluating step: {e}")
            # Fallback: continuar si el step tuvo éxito
            return {
                "satisfactory": result.get("success", False),
                "reason": "Automatic evaluation based on success flag",
                "recommendation": "continue" if result.get("success") else "replan",
                "confidence": 0.5
            }
    
    # ========================================================================
    # GENERACIÓN DE RESPUESTA
    # ========================================================================
    
    def _generate_final_response(
        self,
        plan: List[Dict[str, Any]],
        step_results: Dict[int, Any],
        state: AgentState
    ) -> str:
        """
        Generar respuesta final consolidando todos los resultados.
        """
        try:
            # Recopilar mensajes de cada step
            messages = []
            
            for i, step in enumerate(plan):
                result = step_results.get(i, {})
                
                if result.get("success"):
                    data = result.get("data", "")
                    if isinstance(data, str) and data:
                        messages.append(data)
            
            # Si solo hay un mensaje, retornarlo
            if len(messages) == 1:
                return messages[0]
            
            # Si hay múltiples, consolidar con LLM
            if len(messages) > 1:
                consolidation_prompt = f"""Consolida estos mensajes en una respuesta coherente para el usuario.

MENSAJES:
{chr(10).join(f"{i+1}. {msg}" for i, msg in enumerate(messages))}

PREGUNTA ORIGINAL: {state["question"]}

INSTRUCCIONES:
- Genera una respuesta fluida y coherente
- No pierdas información importante
- Máximo 3-4 párrafos
- Tono profesional y amigable

RESPUESTA CONSOLIDADA:"""
                
                response = self.decision_llm.invoke([
                    {"role": "user", "content": consolidation_prompt}
                ])
                
                return response.content
            
            # Si no hay mensajes, generar respuesta genérica
            return (
                f"He analizado tu consulta en {self.company_config.company_name}. "
                f"¿Hay algo específico en lo que pueda ayudarte?"
            )
            
        except Exception as e:
            logger.error(f"Error generating final response: {e}")
            return (
                f"He procesado tu consulta en {self.company_config.company_name}. "
                f"¿Necesitas ayuda con algo más?"
            )
    
    # ========================================================================
    # HELPERS
    # ========================================================================
    
    def _get_available_agents(self) -> List[str]:
        """Obtener lista de agentes disponibles"""
        if self.orchestrator:
            return list(self.orchestrator.agents.keys())
        return ["sales", "support", "schedule", "emergency"]
    
    def _get_available_tools(self) -> List[str]:
        """Obtener lista de tools disponibles"""
        if self._tool_executor:
            available_tools = self._tool_executor.get_available_tools()
            return [
                name for name, status in available_tools.items()
                if status.get("available")
            ]
        return []
    
    def _format_history_for_prompt(self, history: List) -> str:
        """Formatear historial para prompt"""
        formatted = []
        for msg in history[-5:]:
            if hasattr(msg, 'content'):
                role = msg.__class__.__name__
                formatted.append(f"{role}: {msg.content[:100]}")
        return "\n".join(formatted) if formatted else "(sin historial)"
    
    def _extract_json(self, text: str) -> str:
        """Extraer JSON de respuesta (puede tener markdown)"""
        # Buscar JSON en markdown
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        # Buscar JSON directo
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        return text
    
    def _generate_error_response(self, error: str) -> str:
        """Generar respuesta de error"""
        return (
            f"Disculpa, tuve un problema procesando tu solicitud compleja en "
            f"{self.company_config.company_name}. "
            f"¿Podrías simplificar tu consulta? 🙏"
        )
