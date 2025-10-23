# app/agents/router_node.py
from langgraph.graph import StateGraph
from app.agents._cognitive_base import AgentState
from app.services.openai_service import OpenAIService
import logging, json

logger = logging.getLogger(__name__)

def build_router_graph(company_config):
    """
    RouterNode híbrido: primero intenta clasificar por keywords,
    si hay ambigüedad usa el modelo LLM para refinar.
    """
    graph = StateGraph(AgentState)
    openai_service = OpenAIService()

    def _router_node(state: AgentState) -> AgentState:
        question = state.inputs.get("question", "")
        classification = "support"
        confidence = 0.5

        # --- 1️⃣ Clasificación rápida por keywords ---
        if any(k in question.lower() for k in company_config.emergency_keywords):
            classification = "emergency"; confidence = 0.9
        elif any(k in question.lower() for k in company_config.sales_keywords):
            classification = "sales"; confidence = 0.9
        elif any(k in question.lower() for k in company_config.schedule_keywords):
            classification = "schedule"; confidence = 0.9

        # --- 2️⃣ Si hay duda, usa modelo LLM ---
        if confidence < 0.8:
            system_prompt = f"""
            Eres un clasificador de intenciones para {company_config.company_name}.
            Categorías válidas: EMERGENCY, SALES, SCHEDULE, SUPPORT.
            Devuelve JSON: {{ "intent": ..., "confidence": ..., "reasoning": ... }}
            """
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ]
            try:
                response = openai_service.chat_completion(messages)
                data = json.loads(response)
                classification = data.get("intent", classification).lower()
                confidence = data.get("confidence", confidence)
                state.data["reasoning"] = data.get("reasoning", "")
            except Exception as e:
                logger.warning(f"[RouterNode] fallback to keyword routing: {e}")

        logger.info(f"[RouterNode] classified as {classification} (conf={confidence})")

        state.data["intent"] = classification
        state.data["confidence"] = confidence
        state.next_node = f"{classification}_agent"
        return state

    graph.add_node("router", _router_node)
    
    # ✅ AGREGAR ESTAS 3 LÍNEAS
    from langgraph.graph import END
    graph.set_entry_point("router")
    graph.add_edge("router", END)
    
    return graph
