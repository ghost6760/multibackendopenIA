# app/agents/router_node.py
from langgraph.graph import StateGraph
from app.agents._cognitive_base import AgentState, get_inputs_from, get_state_data, set_state_field
from app.services.openai_service import OpenAIService
import logging, json, re

logger = logging.getLogger(__name__)

def build_router_graph(company_config):
    """
    RouterNode híbrido: primero intenta clasificar por keywords,
    si hay ambigüedad usa el modelo LLM para refinar.
    """
    graph = StateGraph(AgentState)
    openai_service = OpenAIService()

    def _router_node(state: AgentState) -> AgentState:
        # Normalizar inputs
        inputs = get_inputs_from(state)
        question = inputs.get("question", "")
        classification = "support"
        confidence = 0.5

        # Acceso/almacenamiento defensivo al state.data
        state_data = get_state_data(state)

        # --- 1️⃣ Clasificación rápida por keywords ---
        q_lower = question.lower() if isinstance(question, str) else ""
        if any(k in q_lower for k in company_config.emergency_keywords):
            classification = "emergency"; confidence = 0.9
        elif any(k in q_lower for k in company_config.sales_keywords):
            classification = "sales"; confidence = 0.9
        elif any(k in q_lower for k in company_config.schedule_keywords):
            classification = "schedule"; confidence = 0.9

        # --- 2️⃣ Si hay duda, usa modelo LLM ---
        if confidence < 0.8:
            system_prompt = (
                f"Eres un clasificador de intenciones para {company_config.company_name}.\n"
                "Categorías válidas: EMERGENCY, SALES, SCHEDULE, SUPPORT.\n"
                "Devuelve JSON: { \"intent\": ..., \"confidence\": ..., \"reasoning\": ... }"
            )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ]
            try:
                response = openai_service.chat_completion(messages)

                # Normalizar response: aceptar dict/obj con .data o str JSON
                if isinstance(response, dict):
                    data = response
                elif hasattr(response, "data"):  # possible SDK object
                    try:
                        # response.data could be list-like
                        data = response.data if isinstance(response.data, dict) else {}
                    except Exception:
                        data = {}
                elif isinstance(response, str):
                    try:
                        data = json.loads(response)
                    except Exception:
                        # intentar extraer JSON embebido
                        m = re.search(r"\{.*\}", response, flags=re.S)
                        data = json.loads(m.group(0)) if m else {}
                else:
                    # fallback defensivo
                    try:
                        data = dict(response)
                    except Exception:
                        data = {}

                intent_raw = data.get("intent") if isinstance(data, dict) else None
                if isinstance(intent_raw, str):
                    classification = intent_raw.lower()
                confidence = data.get("confidence", confidence) or confidence
                state_data["reasoning"] = data.get("reasoning", "")

            except Exception as e:
                logger.warning(f"[RouterNode] fallback to keyword routing: {e}")

        logger.info(f"[RouterNode] classified as {classification} (conf={confidence})")

        # Guardar resultados de forma defensiva en state
        state_data["intent"] = classification
        state_data["confidence"] = confidence

        # Establecer siguiente nodo de forma defensiva
        set_state_field(state, "next_node", f"{classification}_agent")
        return state

    graph.add_node("router", _router_node)

    # ✅ AGREGAR ESTAS 3 LÍNEAS
    from langgraph.graph import END
    graph.set_entry_point("router")
    graph.add_edge("router", END)

    return graph

