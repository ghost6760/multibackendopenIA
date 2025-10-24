"""
LangGraph Adapters - Arquitectura Híbrida LangChain + LangGraph

Este módulo proporciona adaptadores y grafos de estado para orquestar
agentes LangChain existentes mediante LangGraph, sin romper compatibilidad.

Componentes:
- AgentAdapter: Wrapper genérico para agentes LangChain
- MultiAgentOrchestratorGraph: Grafo de orquestación multi-agente
- ScheduleAgentGraph: Ejemplo de agente con grafo de estado interno
- StateSchemas: Esquemas de estado compartidos

Ejemplo de uso:
    from app.langgraph_adapters import (
        AgentAdapter,
        MultiAgentOrchestratorGraph,
        ScheduleAgentGraph
    )
"""

from app.langgraph_adapters.agent_adapter import (
    AgentAdapter,
    validate_has_question,
    validate_output_length
)
from app.langgraph_adapters.state_schemas import (
    OrchestratorState,
    AgentExecutionState,
    ValidationResult,
    ScheduleAgentState,
    create_initial_orchestrator_state,
    create_initial_schedule_state
)
from app.langgraph_adapters.orchestrator_graph import MultiAgentOrchestratorGraph
from app.langgraph_adapters.schedule_agent_graph import ScheduleAgentGraph

__all__ = [
    # Adaptadores
    "AgentAdapter",
    "validate_has_question",
    "validate_output_length",

    # Grafos
    "MultiAgentOrchestratorGraph",
    "ScheduleAgentGraph",

    # Estados
    "OrchestratorState",
    "AgentExecutionState",
    "ValidationResult",
    "ScheduleAgentState",

    # Helpers
    "create_initial_orchestrator_state",
    "create_initial_schedule_state"
]
