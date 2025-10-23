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
            # Construir prompt que devuelva JSON con keys intent/confidence/reasoning
            system_prompt = f"""
            Eres un clasificador de intenciones para {company_config.company_name}.
            Categorías válidas: EMERGENCY, SALES, SCHEDULE, SUPPORT.
            Devuelve JSON EXACTO en una sola línea: {{ "intent": "...", "confidence": 0.0, "reasoning": "..." }}
            """
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ]
            try:
                # Usar wrapper seguro del servicio OpenAI
                # Puede devolver texto con JSON - intentamos parsearlo
                response_text = openai_service.invoke_with_messages(messages, model=None)
                
                # Si viene como objeto ya parseado (raro) lo normalizamos
                if isinstance(response_text, dict):
                    data = response_text
                else:
                    # Intentar parsear JSON; si falla, buscar primera línea JSON en el texto
                    try:
                        data = json.loads(response_text)
                    except Exception:
                        # Buscar JSON embebido (defensivo)
                        import re
                        m = re.search(r'(\{.*\})', str(response_text), re.DOTALL)
                        if m:
                            try:
                                data = json.loads(m.group(1))
                            except Exception:
                                data = {}
                        else:
                            data = {}
                
                # Si parseamos bien, aplicar resultado
                if data and isinstance(data, dict):
                    classification = data.get("intent", classification).lower()
                    confidence = float(data.get("confidence", confidence))
                    # Guardar razonamiento si viene
                    reasoning_text = data.get("reasoning") or data.get("explanation") or ""
                    # LangGraph state in router_node uses state.data or state['data'] depending on impl.
                    try:
                        # Some state shapes expose .data
                        if hasattr(state, "data"):
                            state.data["reasoning"] = reasoning_text
                        elif isinstance(state, dict):
                            state.setdefault("data", {})["reasoning"] = reasoning_text
                    except Exception:
                        logger.debug("[RouterNode] could not set state.data.reasoning")
                else:
                    logger.warning("[RouterNode] LLM returned no JSON, falling back to keywords")
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
