from app.agents.base_agent import BaseAgent
from langchain.schema.runnable import RunnableLambda
from langchain.prompts import ChatPromptTemplate
from typing import Dict, Any
import logging

class AvailabilityAgent(BaseAgent):
    """Agente de disponibilidad multi-tenant"""
    
    def _initialize_agent(self):
        """Inicializar agente de disponibilidad"""
        self.schedule_agent = None  # Se inyecta externamente
        
        # Crear cadena simple
        self.chain = RunnableLambda(self._process_availability)
    
    def set_schedule_agent(self, schedule_agent):
        """Inyectar schedule agent para reutilizar lógica"""
        self.schedule_agent = schedule_agent
    
    def _create_prompt_template(self):
        """No se usa directamente"""
        pass
    
    def _process_availability(self, inputs):
        """Procesar consulta de disponibilidad"""
        try:
            question = inputs.get("question", "")
            chat_history = inputs.get("chat_history", [])
            
            self._log_agent_activity("checking_availability", {"question": question[:50]})
            
            # Usar la lógica del schedule agent si está disponible
            if self.schedule_agent:
                return self.schedule_agent._handle_availability_check(question, chat_history)
            else:
                # Lógica básica de disponibilidad
                return self._basic_availability_response(question)
                
        except Exception as e:
            logger.error(f"Error in availability check for {self.company_config.company_name}: {e}")
            return f"Error consultando disponibilidad en {self.company_config.company_name}. Te conectaré con un especialista."
    
    def _basic_availability_response(self, question: str):
        """Respuesta básica de disponibilidad"""
        return f"""Para consultar disponibilidad en {self.company_config.company_name}, necesito:

📅 Fecha específica (DD-MM-YYYY)
🩺 Tipo de {self.company_config.services.lower()} que te interesa

¿Puedes proporcionarme estos datos?"""
    
    def _execute_agent_chain(self, inputs: Dict[str, Any]) -> str:
        """Ejecutar cadena de disponibilidad"""
        return self.chain.invoke(inputs)
