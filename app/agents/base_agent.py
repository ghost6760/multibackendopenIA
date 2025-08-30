# app/agents/base_agent.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import BaseMessage
from langchain.schema.output_parser import StrOutputParser
from app.config.company_config import CompanyConfig
from app.services.openai_service import OpenAIService
import logging

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Clase base para todos los agentes del sistema multi-tenant"""
    
    def __init__(self, company_config: CompanyConfig, openai_service: OpenAIService):
        self.company_config = company_config
        self.openai_service = openai_service
        self.chat_model = openai_service.get_chat_model()
        self.agent_name = self.__class__.__name__
        
        # Inicializar el agente específico
        self._initialize_agent()
    
    @abstractmethod
    def _initialize_agent(self):
        """Inicializar configuración específica del agente"""
        pass
    
    @abstractmethod
    def _create_prompt_template(self) -> ChatPromptTemplate:
        """Crear el template de prompts para el agente"""
        pass
    
    def invoke(self, inputs: Dict[str, Any]) -> str:
        """Método principal para invocar el agente"""
        try:
            # Agregar contexto de empresa
            inputs = self._enhance_inputs_with_company_context(inputs)
            
            # Ejecutar cadena del agente
            result = self._execute_agent_chain(inputs)
            
            # Post-procesar respuesta
            return self._post_process_response(result, inputs)
            
        except Exception as e:
            logger.error(f"Error in {self.agent_name} for company {self.company_config.company_id}: {e}")
            return self._get_fallback_response()
    
    def _enhance_inputs_with_company_context(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Enriquecer inputs con contexto de empresa"""
        enhanced_inputs = inputs.copy()
        enhanced_inputs.update({
            "company_name": self.company_config.company_name,
            "services": self.company_config.services,
            "agent_name": self.company_config.sales_agent_name,
            "company_id": self.company_config.company_id
        })
        return enhanced_inputs
    
    @abstractmethod
    def _execute_agent_chain(self, inputs: Dict[str, Any]) -> str:
        """Ejecutar la cadena específica del agente"""
        pass
    
    def _post_process_response(self, response: str, inputs: Dict[str, Any]) -> str:
        """Post-procesar respuesta del agente"""
        # Personalizar respuesta con datos de empresa si es necesario
        return response
    
    def _get_fallback_response(self) -> str:
        """Respuesta de respaldo en caso de error"""
        return f"Disculpa, tuve un problema técnico. Por favor intenta de nuevo o contacta con {self.company_config.company_name}. 🔧"
    
    def _log_agent_activity(self, action: str, details: Dict[str, Any] = None):
        """Log de actividad del agente con contexto de empresa"""
        log_data = {
            "agent": self.agent_name,
            "company_id": self.company_config.company_id,
            "action": action
        }
        if details:
            log_data.update(details)
        
        logger.info(f"[{self.company_config.company_id}] {self.agent_name}: {action}", extra=log_data)


# app/agents/router_agent.py
from app.agents.base_agent import BaseAgent
import json

class RouterAgent(BaseAgent):
    """Agente Router multi-tenant para clasificación de intenciones"""
    
    def _initialize_agent(self):
        """Inicializar configuración del router"""
        self.prompt_template = self._create_prompt_template()
        self.chain = self.prompt_template | self.chat_model | StrOutputParser()
    
    def _create_prompt_template(self) -> ChatPromptTemplate:
        """Crear template de prompts personalizado por empresa"""
        return ChatPromptTemplate.from_messages([
            ("system", f"""Eres un clasificador de intenciones para {self.company_config.company_name}.
            
Servicios disponibles: {self.company_config.services}

ANALIZA el mensaje del usuario y clasifica la intención en UNA de estas categorías:

1. **EMERGENCY** - Urgencias médicas:
   - Palabras clave: {', '.join(self.company_config.emergency_keywords)}
   - Síntomas post-tratamiento graves
   - Cualquier situación que requiera atención médica inmediata

2. **SALES** - Consultas comerciales:
   - Información sobre tratamientos y servicios
   - Palabras clave: {', '.join(self.company_config.sales_keywords)}
   - Comparación de procedimientos
   - Beneficios y resultados

3. **SCHEDULE** - Gestión de citas:
   - Palabras clave: {', '.join(self.company_config.schedule_keywords)}
   - Modificar, cancelar o consultar citas
   - Verificar disponibilidad

4. **SUPPORT** - Soporte general:
   - Información general de {self.company_config.company_name}
   - Consultas sobre procesos
   - Cualquier otra consulta

RESPONDE SOLO con el formato JSON:
{{
    "intent": "EMERGENCY|SALES|SCHEDULE|SUPPORT",
    "confidence": 0.0-1.0,
    "keywords": ["palabra1", "palabra2"],
    "reasoning": "breve explicación",
    "company_context": "{self.company_config.company_name}"
}}

Mensaje del usuario: {{question}}"""),
            ("human", "{question}")
        ])
    
    def _execute_agent_chain(self, inputs: Dict[str, Any]) -> str:
        """Ejecutar clasificación de intenciones"""
        self._log_agent_activity("classifying_intent", {"question": inputs.get("question", "")[:50]})
        return self.chain.invoke(inputs)


# app/agents/emergency_agent.py
from app.agents.base_agent import BaseAgent

class EmergencyAgent(BaseAgent):
    """Agente de emergencias médicas multi-tenant"""
    
    def _initialize_agent(self):
        """Inicializar configuración de emergencias"""
        self.prompt_template = self._create_prompt_template()
        self.chain = self.prompt_template | self.chat_model | StrOutputParser()
    
    def _create_prompt_template(self) -> ChatPromptTemplate:
        """Template personalizado para emergencias"""
        return ChatPromptTemplate.from_messages([
            ("system", f"""Eres un especialista en emergencias médicas de {self.company_config.company_name}.

SITUACIÓN DETECTADA: Posible emergencia médica.

PROTOCOLO DE RESPUESTA:
1. Expresa empatía y preocupación inmediata
2. Solicita información básica del síntoma
3. Indica que el caso será escalado de emergencia a {self.company_config.company_name}
4. Proporciona información de contacto directo si es necesario

SERVICIOS DE EMERGENCIA: {self.company_config.services}

TONO: Profesional, empático, tranquilizador pero urgente.
EMOJIS: Máximo 3 por respuesta.
LONGITUD: Máximo 3 oraciones.

FINALIZA SIEMPRE con: "Escalando tu caso de emergencia en {self.company_config.company_name} ahora mismo. 🚨"

Historial de conversación:
{{chat_history}}

Mensaje del usuario: {{question}}"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])
    
    def _execute_agent_chain(self, inputs: Dict[str, Any]) -> str:
        """Ejecutar protocolo de emergencia"""
        self._log_agent_activity("handling_emergency", {
            "user_id": inputs.get("user_id", "unknown"),
            "urgency": "high"
        })
        return self.chain.invoke(inputs)


# app/agents/sales_agent.py  
from app.agents.base_agent import BaseAgent
from langchain.schema.runnable import RunnableLambda

class SalesAgent(BaseAgent):
    """Agente de ventas multi-tenant con RAG personalizado"""
    
    def _initialize_agent(self):
        """Inicializar agente de ventas con RAG"""
        self.prompt_template = self._create_prompt_template()
        self.vectorstore_service = None  # Se inyecta externamente
        
    def set_vectorstore_service(self, vectorstore_service):
        """Inyectar servicio de vectorstore específico de la empresa"""
        self.vectorstore_service = vectorstore_service
        self._create_chain()
    
    def _create_chain(self):
        """Crear cadena con RAG personalizado"""
        self.chain = (
            {
                "context": self._get_sales_context,
                "question": lambda x: x.get("question", ""),
                "chat_history": lambda x: x.get("chat_history", []),
                "company_name": lambda x: self.company_config.company_name,
                "services": lambda x: self.company_config.services,
                "agent_name": lambda x: self.company_config.sales_agent_name
            }
            | self.prompt_template
            | self.chat_model
            | StrOutputParser()
        )
    
    def _create_prompt_template(self) -> ChatPromptTemplate:
        """Template personalizado para ventas"""
        return ChatPromptTemplate.from_messages([
            ("system", f"""Eres {self.company_config.sales_agent_name}, especializada en {self.company_config.services}.

OBJETIVO: Proporcionar información comercial precisa y persuasiva para {self.company_config.company_name}.

INFORMACIÓN DISPONIBLE:
{{context}}

ESTRUCTURA DE RESPUESTA:
1. Saludo personalizado (si es nuevo cliente)
2. Información del tratamiento/servicio solicitado
3. Beneficios principales (máximo 3)
4. Inversión (si disponible en contexto)
5. Llamada a la acción para agendar

TONO: Cálido, profesional, persuasivo.
EMOJIS: Máximo 3 por respuesta.
LONGITUD: Máximo 5 oraciones.

FINALIZA SIEMPRE con: "¿Te gustaría agendar tu cita en {self.company_config.company_name}? 📅"

Historial de conversación:
{{chat_history}}

Pregunta del usuario: {{question}}"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])
    
    def _get_sales_context(self, inputs):
        """Obtener contexto RAG filtrado por empresa"""
        try:
            question = inputs.get("question", "")
            self._log_agent_activity("retrieving_context", {"query": question[:50]})
            
            if not self.vectorstore_service:
                return f"""Información básica de {self.company_config.company_name}:
- Servicios: {self.company_config.services}
- Atención personalizada y profesional
- Tratamientos de calidad certificados
Para información específica, te conectaré con un especialista."""
            
            # Buscar documentos con filtro de empresa
            docs = self.vectorstore_service.search_by_company(question, self.company_config.company_id)
            
            if not docs:
                return f"""Información general de {self.company_config.company_name}:
- Centro especializado en {self.company_config.services}
- Atención personalizada de calidad
- Profesionales certificados
Para información específica de tratamientos, te conectaré con un especialista."""
            
            return "\n\n".join(doc.page_content for doc in docs)
            
        except Exception as e:
            logger.error(f"Error retrieving sales context: {e}")
            return f"Información básica disponible de {self.company_config.company_name}. Te conectaré con un especialista para detalles específicos."
    
    def _execute_agent_chain(self, inputs: Dict[str, Any]) -> str:
        """Ejecutar cadena de ventas"""
        if not hasattr(self, 'chain'):
            # Chain no creado, usar respuesta básica
            return f"Hola, soy {self.company_config.sales_agent_name}. Estamos especializados en {self.company_config.services}. ¿En qué puedo ayudarte? 😊"
        
        return self.chain.invoke(inputs)


# app/agents/support_agent.py
from app.agents.base_agent import BaseAgent

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
