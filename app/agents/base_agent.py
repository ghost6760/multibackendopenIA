# ============================================================================
# BASE AGENT ACTUALIZADO PARA USAR POSTGRESQL
# Mantiene la misma API pero usa el servicio de prompts
# ============================================================================

import os
import logging
from typing import Optional, Dict, Any
from langchain.schema import SystemMessage, HumanMessage
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from datetime import datetime

# Importar el servicio de prompts
from app.services.prompt_service import get_prompt_service

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Agente base con soporte para prompts personalizados en PostgreSQL - FIXED"""
    
    def __init__(self, company_config, openai_service=None):
        """
        Fixed constructor to accept both company_config and optional openai_service
        
        Args:
            company_config: CompanyConfig object
            openai_service: OpenAIService object (optional, will be created if None)
        """
        self.company_config = company_config
        
        # Handle OpenAI service - create if not provided for backward compatibility
        if openai_service is not None:
            self.openai_service = openai_service
            self.chat_model = openai_service.get_chat_model()
        else:
            # Import here to avoid circular imports
            from app.services.openai_service import OpenAIService
            self.openai_service = OpenAIService()
            self.chat_model = self.openai_service.get_chat_model()
        
        self.agent_name = self.__class__.__name__
        self.prompt_service = get_prompt_service()
        
        # Cache del prompt para evitar consultas repetidas
        self._cached_prompt = None
        self._cache_timestamp = None
        
        # Initialize the specific agent
        self._initialize_agent()
    
    @abstractmethod
    def _initialize_agent(self):
        """Inicializar configuración específica del agente - MUST be implemented by subclasses"""
        pass
    
    @abstractmethod
    def _create_default_prompt_template(self) -> ChatPromptTemplate:
        """Crear el template de prompts por defecto del agente - MUST be implemented by subclasses"""
        pass
    
    def get_prompt_template(self) -> ChatPromptTemplate:
        """
        Obtener template de prompt personalizado o por defecto
        """
        try:
            # Verificar cache (válido por 5 minutos)
            if (self._cached_prompt and self._cache_timestamp and 
                (datetime.utcnow() - self._cache_timestamp).seconds < 300):
                return self._cached_prompt
            
            # Obtener prompt desde el servicio
            agent_key = self._get_agent_key()
            prompt_data = self.prompt_service.get_prompt(
                self.company_config.company_id, agent_key
            )
            
            # Construir template
            if prompt_data['template']:
                template = self._build_custom_prompt_template(prompt_data['template'])
                logger.info(f"[{self.company_config.company_id}] Using {'custom' if prompt_data['is_custom'] else 'default'} prompt for {agent_key}")
            else:
                template = self._create_default_prompt_template()
                logger.info(f"[{self.company_config.company_id}] Using fallback prompt for {agent_key}")
            
            # Actualizar cache
            self._cached_prompt = template
            self._cache_timestamp = datetime.utcnow()
            
            return template
            
        except Exception as e:
            logger.error(f"Error loading prompt template: {e}")
            # Fallback al template por defecto codificado
            return self._create_default_prompt_template()

    def _get_agent_key(self) -> str:
        """Obtener clave del agente para identificación en BD"""
        class_name = self.__class__.__name__.lower()
        # Convertir "SalesAgent" -> "sales_agent"
        if class_name.endswith('agent'):
            return class_name.replace('agent', '_agent')
        else:
            return f"{class_name}_agent"

    def _build_custom_prompt_template(self, custom_template: str) -> ChatPromptTemplate:
        """Construir ChatPromptTemplate desde template personalizado"""
        try:
            # Intentar parsear como template simple
            return ChatPromptTemplate.from_messages([
                ("system", custom_template),
                ("human", "{question}")
            ])
        except Exception as e:
            logger.error(f"Error building custom prompt template: {e}")
            return self._create_default_prompt_template()
    
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
            "agent_name": getattr(self.company_config, 'sales_agent_name', 'Asistente'),
            "company_id": self.company_config.company_id
        })
        return enhanced_inputs
    
    @abstractmethod
    def _execute_agent_chain(self, inputs: Dict[str, Any]) -> str:
        """Ejecutar la cadena específica del agente - MUST be implemented by subclasses"""
        pass
    
    def _post_process_response(self, response: str, inputs: Dict[str, Any]) -> str:
        """Post-procesar respuesta del agente"""
        return response
    
    def _get_fallback_response(self) -> str:
        """Respuesta de respaldo en caso de error"""
        return f"Disculpa, tuve un problema técnico. Por favor intenta de nuevo o contacta con {self.company_config.company_name}."
    
    def _log_agent_activity(self, activity: str, context: Dict[str, Any] = None):
        """Log agent activity for debugging"""
        context_str = f" - {context}" if context else ""
        logger.debug(f"[{self.company_config.company_id}] {self.agent_name}: {activity}{context_str}")
        
    # ============================================================================
    # MÉTODOS PARA COMPATIBILIDAD CON CÓDIGO EXISTENTE
    # ============================================================================

    def get_error_message(self) -> str:
        """Mensaje de error genérico"""
        return f"Lo siento, hubo un problema procesando tu consulta. " \
               f"Por favor intenta de nuevo o contacta con {self.company_config.company_name}."

    def process_query(self, query: str, chat_history: list = None) -> str:
        """
        Procesar consulta del usuario - DEBE ser implementado por cada agente
        """
        raise NotImplementedError("Subclases deben implementar process_query()")

# ============================================================================
# EJEMPLO DE IMPLEMENTACIÓN EN AGENTE ESPECÍFICO
# ============================================================================

class SalesAgent(BaseAgent):
    """Ejemplo de agente de ventas usando el nuevo sistema"""
    
    def _create_default_prompt_template(self) -> ChatPromptTemplate:
        """Template por defecto para agente de ventas"""
        default_template = """Eres un agente de ventas profesional para {company_name}.
Especializado en medicina estética y tratamientos de belleza.

Tu objetivo es:
- Informar sobre productos y servicios
- Guiar hacia la compra
- Resolver dudas comerciales
- Agendar citas de consulta

Mantén un tono profesional, amigable y orientado a resultados.

Información de contacto:
- Teléfono: {phone}
- Email: {email}
- Dirección: {address}

Contexto del chat: {chat_history}
Consulta del usuario: {question}"""

        return ChatPromptTemplate.from_messages([
            ("system", default_template),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])

    def process_query(self, query: str, chat_history: list = None) -> str:
        """Procesar consulta de ventas"""
        try:
            # Obtener template (personalizado o por defecto)
            prompt_template = self.get_prompt_template()
            
            # Preparar variables para el template
            template_vars = {
                "company_name": self.company_config.company_name,
                "phone": self.company_config.phone,
                "email": self.company_config.email,
                "address": self.company_config.address,
                "question": query,
                "chat_history": chat_history or []
            }
            
            # Aquí iría la lógica de procesamiento con LLM
            # prompt = prompt_template.format(**template_vars)
            # response = self.llm.invoke(prompt)
            
            # Por ahora retornamos un mensaje de ejemplo
            return f"Respuesta de ventas para: {query}"
            
        except Exception as e:
            logger.error(f"Error processing sales query: {e}")
            return self.get_error_message()
