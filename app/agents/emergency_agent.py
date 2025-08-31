from app.agents.base_agent import BaseAgent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema.output_parser import StrOutputParser
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class EmergencyAgent(BaseAgent):
    """Agente de emergencias médicas multi-tenant con RAG"""
    
    def _initialize_agent(self):
        """Inicializar configuración de emergencias"""
        self.prompt_template = self._create_prompt_template()
        self.vectorstore_service = None  # Se inyecta externamente
        
    def set_vectorstore_service(self, vectorstore_service):
        """Inyectar servicio de vectorstore específico de la empresa"""
        self.vectorstore_service = vectorstore_service
        self._create_chain()
    
    def _create_chain(self):
        """Crear cadena de emergencias con RAG"""
        self.chain = (
            {
                "emergency_protocols": self._get_emergency_context,
                "question": lambda x: x.get("question", ""),
                "chat_history": lambda x: x.get("chat_history", []),
                "company_name": lambda x: self.company_config.company_name,
                "services": lambda x: self.company_config.services
            }
            | self.prompt_template
            | self.chat_model
            | StrOutputParser()
        )
    
    def _create_prompt_template(self) -> ChatPromptTemplate:
        """Template personalizado para emergencias con RAG"""
        return ChatPromptTemplate.from_messages([
            ("system", f"""Eres un especialista en emergencias médicas de {self.company_config.company_name}.

SITUACIÓN DETECTADA: Posible emergencia médica.

SERVICIOS DE EMERGENCIA: {self.company_config.services}

PROTOCOLOS Y INFORMACIÓN DISPONIBLE:
{{emergency_protocols}}

PROTOCOLO DE RESPUESTA:
1. Evalúa la gravedad según protocolos disponibles
2. Proporciona instrucciones inmediatas si están en la información
3. Indica escalación de emergencia a {self.company_config.company_name}
4. Proporciona información de contacto directo

IMPORTANTE:
- Si hay información específica sobre el síntoma/tratamiento en los protocolos, úsala
- Si no hay información específica, usar protocolo general de emergencia
- SIEMPRE escalar a profesional médico

TONO: Profesional, empático, tranquilizador pero urgente.
LONGITUD: Máximo 4 oraciones.

FINALIZA SIEMPRE con: "Escalando tu caso de emergencia en {self.company_config.company_name} ahora mismo. 🚨"

Historial de conversación:
{{chat_history}}

Mensaje del usuario: {{question}}"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])
    
    def _get_emergency_context(self, inputs):
        """Obtener protocolos de emergencia específicos de la empresa"""
        try:
            question = inputs.get("question", "")
            
            if not self.vectorstore_service:
                return f"""Protocolos básicos de emergencia para {self.company_config.company_name}:
- Cualquier dolor intenso o sangrado requiere atención inmediata
- Reacciones alérgicas severas son emergencia médica
- Síntomas post-tratamiento inusuales deben evaluarse
- Contactar inmediatamente con {self.company_config.company_name}"""
            
            # Buscar protocolos específicos de emergencia
            emergency_query = f"emergencia protocolo {question} dolor sangrado reacción"
            docs = self.vectorstore_service.search_by_company(
                emergency_query, 
                self.company_config.company_id, 
                k=3
            )
            
            if not docs:
                return f"""Protocolos generales de emergencia para {self.company_config.company_name}:
- Dolor intenso post-tratamiento: evaluación inmediata
- Sangrado anormal: presión directa y contacto urgente
- Reacciones alérgicas: suspender exposición, contacto inmediato
- Hinchazón severa: aplicar frío, monitorear respiración"""
            
            # Extraer información de protocolos
            context_parts = []
            for doc in docs:
                if hasattr(doc, 'page_content') and doc.page_content:
                    # Filtrar por contenido relacionado con emergencias
                    content = doc.page_content.lower()
                    if any(word in content for word in ['dolor', 'emergencia', 'sangrado', 'reacción', 'protocolo', 'urgencia']):
                        context_parts.append(doc.page_content)
                elif isinstance(doc, dict) and 'content' in doc:
                    content = doc['content'].lower()
                    if any(word in content for word in ['dolor', 'emergencia', 'sangrado', 'reacción', 'protocolo', 'urgencia']):
                        context_parts.append(doc['content'])
            
            if context_parts:
                return f"Protocolos específicos de {self.company_config.company_name}:\n" + "\n\n".join(context_parts)
            else:
                return f"""Protocolos generales de emergencia para {self.company_config.company_name}:
- Evaluación inmediata para síntomas severos
- Contacto directo con especialista disponible 24/7
- Seguimiento de protocolos médicos establecidos"""
            
        except Exception as e:
            logger.error(f"Error retrieving emergency context: {e}")
            return f"Protocolos de emergencia disponibles para {self.company_config.company_name}. Contacto inmediato requerido."
    
    def _execute_agent_chain(self, inputs: Dict[str, Any]) -> str:
        """Ejecutar protocolo de emergencia con RAG"""
        self._log_agent_activity("handling_emergency", {
            "user_id": inputs.get("user_id", "unknown"),
            "urgency": "high",
            "rag_enabled": self.vectorstore_service is not None
        })
        
        if not hasattr(self, 'chain'):
            # Fallback sin RAG
            return f"""Comprendo tu situación de emergencia. Por tu seguridad, es importante que contactes inmediatamente con {self.company_config.company_name}. 

Escalando tu caso de emergencia ahora mismo. 🚨"""
        
        return self.chain.invoke(inputs)
