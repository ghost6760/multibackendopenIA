# app/agents/support_agent.py - VERSIÓN COMPLETA con imports corregidos

from app.agents.base_agent import BaseAgent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema.output_parser import StrOutputParser
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class SupportAgent(BaseAgent):
    """Agente de soporte multi-tenant"""
    
    def _initialize_agent(self):
        """Inicializar agente de soporte"""
        self.prompt_template = self._create_prompt_template()
        self.vectorstore_service = None
    
    def set_vectorstore_service(self, vectorstore_service):
        """Inyectar servicio de vectorstore"""
        self.vectorstore_service = vectorstore_service
        self._create_chain()
    
    def _create_chain(self):
        """Crear cadena de soporte con contexto"""
        self.chain = (
            {
                "context": self._get_support_context,
                "question": lambda x: x.get("question", ""),
                "chat_history": lambda x: x.get("chat_history", []),
                "company_name": lambda x: self.company_config.company_name
            }
            | self.prompt_template
            | self.chat_model
            | StrOutputParser()
        )
    
    def _create_prompt_template(self) -> ChatPromptTemplate:
        """Template de soporte personalizado"""
        return ChatPromptTemplate.from_messages([
            ("system", f"""Eres un especialista en soporte al cliente de {self.company_config.company_name}.

OBJETIVO: Resolver consultas generales y facilitar navegación.

SERVICIOS: {self.company_config.services}

TIPOS DE CONSULTA:
- Información del centro (ubicación, horarios)
- Procesos y políticas de {self.company_config.company_name}
- Escalación a especialistas
- Consultas generales

INFORMACIÓN DISPONIBLE:
{{context}}

PROTOCOLO:
1. Respuesta directa a la consulta
2. Información adicional relevante
3. Opciones de seguimiento

TONO: Profesional, servicial, eficiente.
LONGITUD: Máximo 4 oraciones.
EMOJIS: Máximo 3 por respuesta.

Si no puedes resolver completamente: "Te conectaré con un especialista de {self.company_config.company_name} para resolver tu consulta específica. 👩‍⚕️"

Historial de conversación:
{{chat_history}}

Consulta del usuario: {{question}}"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])
    
    def _get_support_context(self, inputs):
        """Obtener contexto de soporte filtrado"""
        try:
            question = inputs.get("question", "")
            
            if not self.vectorstore_service:
                return f"""Información general de {self.company_config.company_name}:
- Centro especializado en {self.company_config.services}
- Atención de calidad y personalizada
- Información institucional disponible
Para consultas específicas, te conectaré con un especialista."""
            
            docs = self.vectorstore_service.search_by_company(question, self.company_config.company_id, k=2)
            
            if not docs:
                return f"Información general de {self.company_config.company_name} disponible."
            
            return "\n\n".join(doc.page_content for doc in docs)
            
        except Exception as e:
            logger.error(f"Error retrieving support context: {e}")
            return f"Información general de {self.company_config.company_name} disponible."
    
    def _execute_agent_chain(self, inputs: Dict[str, Any]) -> str:
        """Ejecutar cadena de soporte"""
        if not hasattr(self, 'chain'):
            return f"Hola, soy el asistente de {self.company_config.company_name}. ¿En qué puedo ayudarte hoy? 😊"
        
        return self.chain.invoke(inputs)
