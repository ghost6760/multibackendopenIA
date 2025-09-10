# app/agents/support_agent.py - FIXED VERSION

from app.agents.base_agent import BaseAgent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema.output_parser import StrOutputParser
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class SupportAgent(BaseAgent):
    """Agente de soporte multi-tenant - FIXED"""
    
    def _initialize_agent(self):
        """Inicializar agente de soporte"""
        self.prompt_template = self._create_prompt_template()
        self.vectorstore_service = None
    
    def set_vectorstore_service(self, vectorstore_service):
        """Inyectar servicio de vectorstore"""
        self.vectorstore_service = vectorstore_service
        self._create_chain()
    
    def _create_chain(self):
        """Crear cadena de soporte con contexto - FIXED"""
        self.chain = (
            {
                "context": self._get_support_context,
                "question": lambda x: x.get("question", ""),
                "chat_history": lambda x: x.get("chat_history", []),
                "company_name": lambda x: self.company_config.company_name,
                "services": lambda x: ", ".join(self.company_config.services)  # ✅ FIXED: Add services variable
            }
            | self.prompt_template
            | self.chat_model
            | StrOutputParser()
        )
    
    def _create_default_prompt_template(self) -> ChatPromptTemplate:
        """Template por defecto de soporte - FIXED"""
        return ChatPromptTemplate.from_messages([
            ("system", f"""Eres un especialista en soporte al cliente de {{company_name}}.

OBJETIVO: Resolver consultas generales y facilitar navegación.

SERVICIOS: {{services}}

TIPOS DE CONSULTA:
- Información del centro (ubicación, horarios)
- Procesos y políticas de {{company_name}}
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

Si no puedes resolver completamente: "Te conectaré con un especialista de {{company_name}} para resolver tu consulta específica. 👩‍⚕️"

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
- Centro especializado en {", ".join(self.company_config.services)}
- Atención de calidad y personalizada
- Información institucional disponible
Para consultas específicas, te conectaré con un especialista."""
            
            # Si hay vectorstore, buscar contexto relevante
            try:
                search_results = self.vectorstore_service.search_documents(
                    query=question,
                    k=3,
                    filter_criteria={"document_type": "support"}
                )
                
                if search_results:
                    context_parts = []
                    for result in search_results:
                        content = result.get('content', '')
                        if content:
                            context_parts.append(content[:200])  # Limitar longitud
                    
                    if context_parts:
                        return "\n".join(context_parts)
                
            except Exception as e:
                logger.error(f"[{self.company_config.company_id}] Error searching support context: {e}")
            
            # Fallback context
            return f"""Información general de {self.company_config.company_name}:
- Centro especializado en {", ".join(self.company_config.services)}
- Atención de calidad y personalizada
- Información institucional disponible
Para consultas específicas, te conectaré con un especialista."""
            
        except Exception as e:
            logger.error(f"[{self.company_config.company_id}] Error getting support context: {e}")
            return f"Centro {self.company_config.company_name} - Información general disponible"
    
    def process_message(self, message: str, chat_history: List[Dict] = None, **kwargs) -> str:
        """Procesar mensaje de soporte"""
        try:
            logger.info(f"[{self.company_config.company_id}] SupportAgent: message_processed")
            
            if not hasattr(self, 'chain') or self.chain is None:
                return f"Sistema de soporte de {self.company_config.company_name} iniciándose. Por favor, intenta de nuevo en un momento."
            
            # Preparar inputs
            inputs = {
                "question": message,
                "chat_history": chat_history or []
            }
            
            # Generar respuesta
            response = self.chain.invoke(inputs)
            return response
            
        except Exception as e:
            logger.error(f"[{self.company_config.company_id}] Error in SupportAgent.process_message: {e}")
            return f"Disculpa, hay un problema temporal en el sistema de soporte de {self.company_config.company_name}. Te conectaré con un especialista."
