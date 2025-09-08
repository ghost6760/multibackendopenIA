# app/agents/base_agent.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import BaseMessage
from langchain.schema.output_parser import StrOutputParser
from app.config.company_config import CompanyConfig
from app.services.openai_service import OpenAIService
from app.services.prompt_redis_manager import get_prompt_redis_manager
from app.services.prompt_manager import PromptManager
import logging
import json
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Clase base para todos los agentes del sistema multi-tenant con persistencia en Redis"""
    
    def __init__(self, company_config: CompanyConfig, openai_service: OpenAIService):
        self.company_config = company_config
        self.openai_service = openai_service
        self.chat_model = openai_service.get_chat_model()
        self.agent_name = self.__class__.__name__
        
        # Inicializar manager de prompts de Redis (sistema existente)
        self.prompt_redis_manager = get_prompt_redis_manager()
        
        # Inicializar el nuevo PromptManager para gestión mejorada
        redis_client = self.prompt_redis_manager.redis_client if hasattr(self.prompt_redis_manager, 'redis_client') else None
        if redis_client:
            self.prompt_manager = PromptManager(redis_client)
        else:
            # Si no hay redis_client disponible, usar el prompt_redis_manager existente
            self.prompt_manager = self.prompt_redis_manager
        
        # Inicializar el agente específico con soporte para prompts personalizados
        self._initialize_agent()
    
    @abstractmethod
    def _initialize_agent(self):
        """Inicializar configuración específica del agente"""
        pass
    
    def _create_prompt_template(self) -> ChatPromptTemplate:
        """Crear template con soporte para prompts personalizados desde Redis"""
        
        # 1. Intentar cargar prompt personalizado desde Redis primero
        custom_template = self._load_custom_prompt()
        if custom_template:
            return self._build_custom_prompt_template(custom_template)
        
        # 2. Si no hay personalizado, usar el por defecto del agente
        return self._create_default_prompt_template()
    
    @abstractmethod
    def _create_default_prompt_template(self) -> ChatPromptTemplate:
        """Crear el template de prompts por defecto para el agente"""
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
            "company_id": self.company_config.company_id,
            # Agregar más contexto si está disponible
            "business_hours": getattr(self.company_config, 'business_hours', 'Lun-Vie 9:00-18:00'),
            "contact_email": getattr(self.company_config, 'contact_email', 'info@empresa.com'),
            "contact_phone": getattr(self.company_config, 'contact_phone', '+57 300 000 0000')
        })
        return enhanced_inputs
    
    @abstractmethod
    def _execute_agent_chain(self, inputs: Dict[str, Any]) -> str:
        """Ejecutar la cadena específica del agente"""
        pass
    
    def _post_process_response(self, response: str, inputs: Dict[str, Any]) -> str:
        """Post-procesar respuesta del agente"""
        return response
    
    def _get_fallback_response(self) -> str:
        """Respuesta de respaldo en caso de error"""
        return f"Disculpa, tuve un problema técnico. Por favor intenta de nuevo o contacta con {self.company_config.company_name}."

    # ============================================================================
    # MÉTODOS PARA GESTIÓN DE PROMPTS CON REDIS
    # ============================================================================
    
    def _load_custom_prompt(self) -> Optional[str]:
        """Cargar prompt personalizado desde Redis (con fallback a archivo JSON)"""
        try:
            agent_key = self._get_agent_key()
            
            # Primero intentar con el nuevo PromptManager
            if hasattr(self, 'prompt_manager') and isinstance(self.prompt_manager, PromptManager):
                custom_template = self.prompt_manager.get_prompt(
                    self.company_config.company_id,
                    agent_key
                )
                if custom_template:
                    logger.info(f"[{self.company_config.company_id}] Loaded prompt for {agent_key}")
                    return custom_template
            
            # Si no funciona, usar el prompt_redis_manager original
            custom_template = self.prompt_redis_manager.load_custom_prompt(
                self.company_config.company_id, 
                agent_key
            )
            
            if custom_template:
                logger.info(f"[{self.company_config.company_id}] Using custom prompt from Redis for {agent_key}")
                return custom_template
            
            # Si no está en Redis, intentar fallback al archivo (para migración gradual)
            return self._load_custom_prompt_from_file()
            
        except Exception as e:
            logger.warning(f"Error loading custom prompt for {self.company_config.company_id}: {e}")
            # En caso de error, intentar cargar desde archivo
            return self._load_custom_prompt_from_file()
    
    def _load_custom_prompt_from_file(self) -> Optional[str]:
        """Cargar prompt personalizado desde archivo JSON (método legacy para compatibilidad)"""
        try:
            # Primero intentar en la carpeta config (nueva ubicación)
            custom_prompts_file = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                'config',
                'custom_prompts.json'
            )
            
            # Si no existe en config, intentar en la raíz (ubicación legacy)
            if not os.path.exists(custom_prompts_file):
                custom_prompts_file = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                    'custom_prompts.json'
                )
            
            if not os.path.exists(custom_prompts_file):
                return None
            
            with open(custom_prompts_file, 'r', encoding='utf-8') as f:
                custom_prompts = json.load(f)
            
            company_prompts = custom_prompts.get(self.company_config.company_id, {})
            agent_key = self._get_agent_key()
            agent_data = company_prompts.get(agent_key, {})
            
            # Manejar tanto el formato nuevo como el antiguo
            if isinstance(agent_data, dict):
                custom_template = agent_data.get('default_template') or agent_data.get('template')
            else:
                custom_template = agent_data  # String directo (formato muy antiguo)
            
            if custom_template:
                # Si encontramos en archivo, migrar automáticamente a Redis
                logger.info(f"Migrating prompt from file to Redis: {self.company_config.company_id}/{agent_key}")
                
                # Usar el nuevo PromptManager si está disponible
                if hasattr(self, 'prompt_manager') and isinstance(self.prompt_manager, PromptManager):
                    self.prompt_manager.save_custom_prompt(
                        self.company_config.company_id,
                        agent_key,
                        custom_template,
                        'migration'
                    )
                else:
                    self.prompt_redis_manager.save_custom_prompt(
                        self.company_config.company_id,
                        agent_key,
                        custom_template,
                        agent_data.get('modified_by', 'migration') if isinstance(agent_data, dict) else 'migration'
                    )
                return custom_template
            
            return None
            
        except Exception as e:
            logger.warning(f"Error loading custom prompt from file: {e}")
            return None
    
    def _get_agent_key(self) -> str:
        """Obtener clave del agente para custom_prompts"""
        class_name = self.__class__.__name__.lower()
        # Convertir "SalesAgent" -> "sales_agent"
        if class_name.endswith('agent'):
            return class_name.replace('agent', '_agent')
        else:
            return f"{class_name}_agent"
    
    def _build_custom_prompt_template(self, custom_template: str) -> ChatPromptTemplate:
        """Construir ChatPromptTemplate desde template personalizado"""
        try:
            # Procesar variables del template
            custom_template = self.process_prompt_variables(custom_template)
            
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
    
    def process_prompt_variables(self, prompt: str, **kwargs) -> str:
        """Procesar las variables en el prompt"""
        # Variables por defecto del contexto de empresa
        variables = {
            'company_name': self.company_config.company_name,
            'business_hours': getattr(self.company_config, 'business_hours', 'Lun-Vie 9:00-18:00'),
            'contact_email': getattr(self.company_config, 'contact_email', 'info@empresa.com'),
            'contact_phone': getattr(self.company_config, 'contact_phone', '+57 300 000 0000'),
            'services': ', '.join(self.company_config.services[:5]) if self.company_config.services else 'servicios varios',
        }
        
        # Agregar variables adicionales pasadas como kwargs
        variables.update(kwargs)
        
        # Reemplazar variables en el prompt (manteniendo las que no tienen valor)
        processed_prompt = prompt
        for key, value in variables.items():
            placeholder = f'{{{key}}}'
            if placeholder in processed_prompt:
                processed_prompt = processed_prompt.replace(placeholder, str(value))
        
        return processed_prompt
    
    # ============================================================================
    # MÉTODOS PÚBLICOS PARA GESTIÓN DE PROMPTS
    # ============================================================================
    
    def save_custom_prompt(self, custom_template: str, modified_by: str = "admin") -> bool:
        """Guardar prompt personalizado en Redis"""
        try:
            agent_key = self._get_agent_key()
            
            # Usar el nuevo PromptManager si está disponible
            if hasattr(self, 'prompt_manager') and isinstance(self.prompt_manager, PromptManager):
                success = self.prompt_manager.save_custom_prompt(
                    self.company_config.company_id,
                    agent_key,
                    custom_template,
                    modified_by
                )
            else:
                # Usar el manager de Redis original
                success = self.prompt_redis_manager.save_custom_prompt(
                    self.company_config.company_id,
                    agent_key,
                    custom_template,
                    modified_by
                )
            
            if success:
                logger.info(f"[{self.company_config.company_id}] Custom prompt saved to Redis for {agent_key}")
                # Recargar el template del agente para usar el nuevo prompt
                self.prompt_template = self._create_prompt_template()
            
            return success
            
        except Exception as e:
            logger.error(f"Error saving custom prompt: {e}")
            return False
    
    def remove_custom_prompt(self) -> bool:
        """Remover prompt personalizado (volver a default) usando Redis"""
        try:
            agent_key = self._get_agent_key()
            
            # Usar el nuevo PromptManager si está disponible
            if hasattr(self, 'prompt_manager') and isinstance(self.prompt_manager, PromptManager):
                success = self.prompt_manager.delete_custom_prompt(
                    self.company_config.company_id,
                    agent_key
                )
            else:
                # Usar el manager de Redis original
                success = self.prompt_redis_manager.delete_custom_prompt(
                    self.company_config.company_id,
                    agent_key
                )
            
            if success:
                logger.info(f"[{self.company_config.company_id}] Custom prompt removed from Redis for {agent_key}")
                # Recargar el template del agente para usar el prompt por defecto
                self.prompt_template = self._create_default_prompt_template()
            
            return success
            
        except Exception as e:
            logger.error(f"Error removing custom prompt: {e}")
            return False
    
    def has_custom_prompt(self) -> bool:
        """Verificar si el agente tiene un prompt personalizado en Redis"""
        try:
            agent_key = self._get_agent_key()
            
            # Intentar con ambos managers
            if hasattr(self, 'prompt_manager') and isinstance(self.prompt_manager, PromptManager):
                # El nuevo PromptManager no tiene has_custom_prompt, verificar si hay prompt custom
                prompt = self.prompt_manager.get_prompt(self.company_config.company_id, agent_key)
                redis_key = f"{self.company_config.company_id}:prompts:{agent_key}"
                return self.prompt_manager.redis.exists(redis_key) > 0
            
            return self.prompt_redis_manager.has_custom_prompt(
                self.company_config.company_id,
                agent_key
            )
        except Exception as e:
            logger.warning(f"Error checking custom prompt: {e}")
            return False
    
    def get_prompt_info(self) -> Dict[str, Any]:
        """Obtener información del prompt actual"""
        try:
            agent_key = self._get_agent_key()
            
            # Intentar con el nuevo PromptManager
            if hasattr(self, 'prompt_manager') and isinstance(self.prompt_manager, PromptManager):
                all_prompts = self.prompt_manager.get_all_prompts(self.company_config.company_id)
                if agent_key in all_prompts:
                    info = all_prompts[agent_key]
                    info.update({
                        "agent_name": agent_key,
                        "company_id": self.company_config.company_id,
                        "has_custom": info.get('is_custom', False)
                    })
                    return info
            
            # Fallback al manager original
            info = self.prompt_redis_manager.get_modification_info(
                self.company_config.company_id,
                agent_key
            )
            
            # Añadir información adicional
            info.update({
                "agent_name": agent_key,
                "company_id": self.company_config.company_id,
                "has_custom": self.has_custom_prompt()
            })
            
            return info
            
        except Exception as e:
            logger.warning(f"Error getting prompt info: {e}")
            return {
                "agent_name": self._get_agent_key(),
                "company_id": self.company_config.company_id,
                "has_custom": False,
                "error": str(e)
            }
    
    def get_current_prompt_template(self) -> str:
        """Obtener el template del prompt actual (personalizado o default)"""
        try:
            # Primero intentar obtener personalizado desde Redis
            custom_template = self._load_custom_prompt()
            if custom_template:
                return custom_template
            
            # Si no hay personalizado, obtener el default
            default_template = self._create_default_prompt_template()
            if hasattr(default_template, 'messages'):
                # Extraer el contenido del system message
                for message in default_template.messages:
                    if hasattr(message, 'prompt') and hasattr(message.prompt, 'template'):
                        return message.prompt.template
            
            return "Default prompt template"
            
        except Exception as e:
            logger.warning(f"Error getting current prompt template: {e}")
            return "Error retrieving prompt template"
    
    # ============================================================================
    # MÉTODOS DE LOGGING Y MONITOREO
    # ============================================================================
    
    def _log_agent_activity(self, action: str, details: Dict[str, Any] = None):
        """Log de actividad del agente con contexto de empresa"""
        log_data = {
            "agent": self.agent_name,
            "company_id": self.company_config.company_id,
            "action": action,
            "has_custom_prompt": self.has_custom_prompt()
        }
        if details:
            log_data.update(details)
        
        logger.info(f"[{self.company_config.company_id}] {self.agent_name}: {action}", extra=log_data)
