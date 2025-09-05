from app.agents.base_agent import BaseAgent
from langchain.schema.runnable import RunnableLambda
from langchain.prompts import ChatPromptTemplate
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class AvailabilityAgent(BaseAgent):
    """Agente para verificar disponibilidad multi-tenant"""
    
    def _initialize_agent(self):
        """Inicializa la cadena principal"""
        self.schedule_agent = None
        self.chain = RunnableLambda(self._process_availability)
    
    def set_schedule_agent(self, schedule_agent):
        """Permite inyectar el ScheduleAgent"""
        self.schedule_agent = schedule_agent
        logger.debug(f"[{self.company_config.company_id}] ScheduleAgent inyectado en AvailabilityAgent")
    
    def _create_default_prompt_template(self) -> ChatPromptTemplate:
        """No necesita prompt, pero debe devolver algo válido para cumplir con la interfaz"""
        # Retornamos un template mínimo que no se usará realmente
        return ChatPromptTemplate.from_messages([
            ("system", "Agente de disponibilidad - No requiere prompt"),
            ("human", "{question}")
        ])
    
    def _execute_agent_chain(self, inputs: Dict[str, Any]) -> str:
        """Ejecuta el flujo de disponibilidad"""
        return self._process_availability(inputs)
    
    def _process_availability(self, inputs: Dict[str, Any]) -> str:
        question = inputs.get("question", "")
        chat_history = inputs.get("chat_history", [])
        
        self._log_agent_activity("checking_availability", {"question": question[:50]})
        
        try:
            if self.schedule_agent:
                schedule_context = self._build_schedule_context(question, chat_history)
                return self.schedule_agent.check_availability(
                    question, chat_history, schedule_context
                )
            else:
                return self._basic_availability_response()
        except Exception as e:
            logger.error(f"Error verificando disponibilidad en {self.company_config.company_name}: {e}")
            return f"❌ Ocurrió un problema al consultar disponibilidad en {self.company_config.company_name}. Te conecto con un asesor."
    
    def _build_schedule_context(self, question: str, chat_history: list) -> Dict[str, Any]:
        """Construye el contexto para el ScheduleAgent"""
        return {
            "company_id": self.company_config.company_id,
            "company_name": self.company_config.company_name,
            "services": self.company_config.services,
            "question": question,
            "chat_history": chat_history
        }
    
    def _basic_availability_response(self) -> str:
        """Genera una respuesta básica de disponibilidad con lista de servicios"""
        # Normalizamos los servicios para mostrarlos correctamente
        services_display = self._format_services(self.company_config.services)
        
        return (
            f"Para consultar disponibilidad en {self.company_config.company_name}, indícame:\n\n"
            f"📅 Fecha específica (DD-MM-YYYY)\n"
            f"🩺 Tipo de servicio que deseas ({services_display})\n"
        )
    
    def _format_services(self, services: Any) -> str:
        """Convierte services en un string legible, sin errores"""
        if isinstance(services, dict):
            return ", ".join(services.keys())
        elif isinstance(services, list):
            return ", ".join(str(s) for s in services)
        elif isinstance(services, str):
            return services
        return "servicio disponible"  # Fallback


