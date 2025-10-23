# app/agents/router_node.py
from langgraph.graph import StateGraph
from app.agents._cognitive_base import AgentState
import logging

logger = logging.getLogger(__name__)

def build_router_graph(company_config):
    """
    RouterNode: primer paso del orquestador cognitivo.
    Clasifica el mensaje y redirige a un subgrafo (sales, support, etc.)
    """
    graph = StateGraph(AgentState)

    def _router_node(state: AgentState) -> AgentState:
        question = state.inputs.get("question", "")
        classification = "support"

        if any(k in question.lower() for k in company_config.emergency_keywords):
            classification = "emergency"
        elif any(k in question.lower() for k in company_config.sales_keywords):
            classification = "sales"
        elif any(k in question.lower() for k in company_config.schedule_keywords):
            classification = "schedule"

        logger.info(f"[RouterNode] classified as {classification}")
        state.data["intent"] = classification
        state.next_node = f"{classification}_agent"
        return state

    # Registrar nodo
    graph.add_node("router", _router_node)

    return graph
