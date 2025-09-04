from app.agents.base_agent import BaseAgent
from langchain.schema.runnable import RunnableLambda
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class AvailabilityAgent(BaseAgent):
    """Agente para verificar disponibilidad multi-tenant"""

    def _initialize_agent(self):
        """Inicializa el agente y su cadena de ejecución"""
        self.schedule_agent = None  # Se inyectará externamente
        self.chain = RunnableLambda(self._process_availability)

    def set_schedule_agent(self, schedule_agent):
        """Inyecta el ScheduleAgent para reutilizar su lógica"""
        self.schedule_agent = schedule_agent
        logger.debug(f"[{self.company_config.company_id}] ScheduleAgent inyectado en AvailabilityAgent")

    def _process_availability(self, inputs: Dict[str, Any]) -> str:
        """Procesa la consulta de disponibilidad"""
        question = inputs.get("question", "")
        chat_history = inputs.get("chat_history", [])

        self._log_agent_activity("checking_availability", {"question": question[:50]})

        try:
            if self.schedule_agent:
                schedule_context = self._build_schedule_context(question, chat_history)
                return self.schedule_agent.check_availability(question, chat_history, schedule_context)
            else:
                return self._basic_availability_response(question)

        except Exception as e:
            logger.error(f"Error verificando disponibilidad para {self.company_config.company_name}: {e}")
            return f"❌ Hubo un problema al consultar la disponibilidad en {self.company_config.company_name}. Te conectaré con un asesor."

    def _build_schedule_context(self, question: str, chat_history: list) -> Dict[str, Any]:
        """Construye el contexto necesario para la verificación"""
        return {
            "company_id": self.company_config.company_id,
            "company_name": self.company_config.company_name,
            "services": self.company_config.services,
            "question": question,
            "chat_history": chat_history
        }

    def _basic_availability_response(self, question: str) -> str:
        """Respuesta básica cuando no hay ScheduleAgent disponible"""
        return (
            f"Para consultar disponibilidad en {self.company_config.company_name}, por favor indícame:\n\n"
            f"📅 Fecha específica (DD-MM-YYYY)\n"
            f"🩺 Tipo de servicio que te interesa\n"
        )

