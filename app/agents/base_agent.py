# ============================================================================
# BASE AGENT ACTUALIZADO PARA USAR POSTGRESQL - CONSTRUCTOR FIXED
# Mantiene la misma API pero usa el servicio de prompts + Fixed constructor signature
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

class BaseAgent:
    """Agente base con soporte para prompts personalizados en PostgreSQL"""
    
    def __init__(self, company_config, openai_service=None):
        """
        FIXED: Constructor que acepta tanto company_config como openai_service opcional
        
        Args:
            company_config: CompanyConfig object
            openai_service: OpenAIService object (opcional, se crea si es None)
        """
        self.company_config = company_config
        
        # Handle OpenAI service - create if not provided for backward compatibility
        if openai_service is not None:
            self.openai_service = openai_service
            # Si tiene método get_chat_model, lo usamos
            if hasattr(openai_service, 'get_chat_model'):
                self.chat_model = openai_service.get_chat_model()
            else:
                self.chat_model = None
        else:
            # Import here to avoid circular imports
            try:
                from app.services.openai_service import OpenAIService
                self.openai_service = OpenAIService()
                self.chat_model = self.openai_service.get_chat_model()
            except Exception as e:
                logger.warning(f"Could not initialize OpenAI service: {e}")
                self.openai_service = None
                self.chat_model = None
        
        # Initialize prompt service
        try:
            self.prompt_service = get_prompt_service()
        except Exception as e:
            logger.warning(f"Could not initialize prompt service: {e}")
            self.prompt_service = None
        
        # Cache del prompt para evitar consultas repetidas
        self._cached_prompt = None
        self._cache_timestamp = None
        
        # Initialize specific agent implementation
        try:
            self._initialize_agent()
        except Exception as e:
            logger.error(f"Error initializing agent {self.__class__.__name__}: {e}")
    
    def _initialize_agent(self):
        """
        Inicializar configuración específica del agente
        Subclasses can override this method for custom initialization
        """
        pass
        
    def get_prompt_template(self) -> ChatPromptTemplate:
        """
        Obtener template de prompt personalizado o por defecto
        Mantiene la misma API que antes
        """
        try:
            # Verificar cache (válido por 5 minutos)
            if (self._cached_prompt and self._cache_timestamp and 
                (datetime.utcnow() - self._cache_timestamp).seconds < 300):
                return self._cached_prompt
            
            # Obtener prompt desde el servicio si está disponible
            if self.prompt_service:
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
            else:
                # Si no hay prompt service, usar template por defecto
                template = self._create_default_prompt_template()
                logger.info(f"[{self.company_config.company_id}] Using default prompt (no prompt service)")
            
            # Actualizar cache
            self._cached_prompt = template
            self._cache_timestamp = datetime.utcnow()
            
            return template
            
        except Exception as e:
            logger.error(f"Error loading prompt template: {e}")
            # Fallback al template por defecto codificado
            return self._create_default_prompt_template()

    def _load_custom_prompt(self) -> Optional[str]:
        """
        DEPRECATED: Mantener por compatibilidad
        Usar get_prompt_template() en su lugar
        """
        try:
            if not self.prompt_service:
                return None
                
            agent_key = self._get_agent_key()
            prompt_data = self.prompt_service.get_prompt(
                self.company_config.company_id, agent_key
            )
            
            if prompt_data['is_custom'] and prompt_data['template']:
                return prompt_data['template']
            return None
            
        except Exception as e:
            logger.warning(f"Error in _load_custom_prompt: {e}")
            return None

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
            # Determinar si el template necesita MessagesPlaceholder para chat_history
            if '{chat_history}' in custom_template:
                return ChatPromptTemplate.from_messages([
                    ("system", custom_template),
                    MessagesPlaceholder(variable_name="chat_history"),
                    ("human", "{question}")
                ])
            else:
                return ChatPromptTemplate.from_messages([
                    ("system", custom_template),
                    ("human", "{question}")
                ])
        except Exception as e:
            logger.error(f"Error building custom prompt template: {e}")
            # Fallback al método por defecto
            return self._create_default_prompt_template()

    def _create_default_prompt_template(self) -> ChatPromptTemplate:
        """
        Crear template por defecto - DEBE ser implementado por cada agente
        """
        # Provide a minimal default template to prevent errors
        return ChatPromptTemplate.from_messages([
            ("system", f"Eres un asistente profesional de {self.company_config.company_name}. Ayuda al usuario de manera amigable y profesional."),
            ("human", "{question}")
        ])

    def save_custom_prompt(self, custom_template: str, modified_by: str = "admin") -> bool:
        """Guardar prompt personalizado para este agente"""
        try:
            if not self.prompt_service:
                logger.warning("No prompt service available")
                return False
                
            agent_key = self._get_agent_key()
            success = self.prompt_service.save_custom_prompt(
                self.company_config.company_id, 
                agent_key, 
                custom_template, 
                modified_by
            )
            
            if success:
                # Invalidar cache
                self._cached_prompt = None
                self._cache_timestamp = None
                logger.info(f"[{self.company_config.company_id}] Custom prompt saved for {agent_key}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error saving custom prompt: {e}")
            return False

    def remove_custom_prompt(self) -> bool:
        """Remover prompt personalizado (volver a default)"""
        try:
            if not self.prompt_service:
                logger.warning("No prompt service available")
                return False
                
            agent_key = self._get_agent_key()
            success = self.prompt_service.delete_custom_prompt(
                self.company_config.company_id, 
                agent_key
            )
            
            if success:
                # Invalidar cache
                self._cached_prompt = None
                self._cache_timestamp = None
                logger.info(f"[{self.company_config.company_id}] Custom prompt removed for {agent_key}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error removing custom prompt: {e}")
            return False

    def has_custom_prompt(self) -> bool:
        """Verificar si este agente tiene prompt personalizado"""
        try:
            if not self.prompt_service:
                return False
                
            agent_key = self._get_agent_key()
            return self.prompt_service.has_custom_prompt(
                self.company_config.company_id, 
                agent_key
            )
        except Exception as e:
            logger.error(f"Error checking custom prompt: {e}")
            return False

    def get_prompt_info(self) -> Dict[str, Any]:
        """Obtener información completa del prompt actual"""
        try:
            if not self.prompt_service:
                return {
                    'template': None,
                    'is_custom': False,
                    'version': 1,
                    'modified_at': None,
                    'modified_by': None
                }
                
            agent_key = self._get_agent_key()
            return self.prompt_service.get_prompt(
                self.company_config.company_id, 
                agent_key
            )
        except Exception as e:
            logger.error(f"Error getting prompt info: {e}")
            return {
                'template': None,
                'is_custom': False,
                'version': 1,
                'modified_at': None,
                'modified_by': None
            }

    def get_prompt_history(self) -> list:
        """Obtener historial de versiones del prompt"""
        try:
            if not self.prompt_service:
                return []
                
            agent_key = self._get_agent_key()
            return self.prompt_service.get_prompt_history(
                self.company_config.company_id, 
                agent_key
            )
        except Exception as e:
            logger.error(f"Error getting prompt history: {e}")
            return []

    def restore_prompt_version(self, version: int, modified_by: str = "admin") -> bool:
        """Restaurar una versión específica del prompt"""
        try:
            if not self.prompt_service:
                logger.warning("No prompt service available")
                return False
                
            agent_key = self._get_agent_key()
            success = self.prompt_service.restore_prompt_version(
                self.company_config.company_id, 
                agent_key, 
                version, 
                modified_by
            )
            
            if success:
                # Invalidar cache
                self._cached_prompt = None
                self._cache_timestamp = None
                logger.info(f"[{self.company_config.company_id}] Prompt version {version} restored for {agent_key}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error restoring prompt version: {e}")
            return False

    def clear_prompt_cache(self):
        """Limpiar cache del prompt (útil después de actualizaciones)"""
        self._cached_prompt = None
        self._cache_timestamp = None

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
        try:
            return self._execute_agent_chain({
                "question": query,
                "chat_history": chat_history or []
            })
        except Exception as e:
            logger.error(f"Error processing query in {self.__class__.__name__}: {e}")
            return self.get_error_message()
    
    def _execute_agent_chain(self, inputs: Dict[str, Any]) -> str:
        """
        Ejecutar la cadena específica del agente
        Subclasses should override this method
        """
        # Default implementation
        question = inputs.get("question", "")
        return f"Procesando consulta: {question} (implementación por defecto)"
    
    def invoke(self, inputs: Dict[str, Any]) -> str:
        """Método principal para invocar el agente (compatibilidad con LangChain)"""
        return self.process_query(
            inputs.get("question", ""),
            inputs.get("chat_history", [])
        )

# ============================================================================
# EJEMPLO DE IMPLEMENTACIÓN EN AGENTE ESPECÍFICO (ACTUALIZADO)
# ============================================================================

class SalesAgent(BaseAgent):
    """Ejemplo de agente de ventas usando el nuevo sistema"""
    
    def _create_default_prompt_template(self) -> ChatPromptTemplate:
        """Template por defecto para agente de ventas"""
        default_template = f"""Eres un agente de ventas profesional para {self.company_config.company_name}.
Especializado en medicina estética y tratamientos de belleza.

Tu objetivo es:
- Informar sobre productos y servicios
- Guiar hacia la compra
- Resolver dudas comerciales
- Agendar citas de consulta

Mantén un tono profesional, amigable y orientado a resultados.

Servicios disponibles: {getattr(self.company_config, 'services', 'Servicios generales')}

Contexto del chat: {{chat_history}}
Consulta del usuario: {{question}}"""

        return ChatPromptTemplate.from_messages([
            ("system", default_template),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])

    def _execute_agent_chain(self, inputs: Dict[str, Any]) -> str:
        """Procesar consulta de ventas"""
        try:
            # Obtener template (personalizado o por defecto)
            prompt_template = self.get_prompt_template()
            
            # Preparar variables para el template
            template_vars = {
                "company_name": self.company_config.company_name,
                "question": inputs.get("question", ""),
                "chat_history": inputs.get("chat_history", [])
            }
            
            # Aquí iría la lógica de procesamiento con LLM si está disponible
            if self.chat_model:
                # prompt = prompt_template.format(**template_vars)
                # response = self.chat_model.invoke(prompt)
                pass
            
            # Por ahora retornamos un mensaje de ejemplo
            return f"Respuesta de ventas para: {inputs.get('question', '')}"
            
        except Exception as e:
            logger.error(f"Error processing sales query: {e}")
            return self.get_error_message()
