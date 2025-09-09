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

class BaseAgent:
    """Agente base con soporte para prompts personalizados en PostgreSQL"""
    
    def __init__(self, company_config):
        self.company_config = company_config
        self.prompt_service = get_prompt_service()
        
        # Cache del prompt para evitar consultas repetidas
        self._cached_prompt = None
        self._cache_timestamp = None
        
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

    def _load_custom_prompt(self) -> Optional[str]:
        """
        DEPRECATED: Mantener por compatibilidad
        Usar get_prompt_template() en su lugar
        """
        try:
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
        raise NotImplementedError("Subclases deben implementar _create_default_prompt_template()")

    def save_custom_prompt(self, custom_template: str, modified_by: str = "admin") -> bool:
        """Guardar prompt personalizado para este agente"""
        try:
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
