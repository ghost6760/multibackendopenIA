# app/agents/base_agent.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import BaseMessage
from langchain.schema.output_parser import StrOutputParser
from app.config.company_config import CompanyConfig
from app.services.openai_service import OpenAIService
import logging

# 🆕 AGREGAR ESTOS IMPORTS
import json
import os
from datetime import datetime


logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Clase base para todos los agentes del sistema multi-tenant"""
    
    def __init__(self, company_config: CompanyConfig, openai_service: OpenAIService):
        self.company_config = company_config
        self.openai_service = openai_service
        self.chat_model = openai_service.get_chat_model()
        self.agent_name = self.__class__.__name__
        
        # Inicializar el agente específico con soporte para prompts personalizados
        self._initialize_agent()
    
    @abstractmethod
    def _initialize_agent(self):
        """Inicializar configuración específica del agente"""
        pass
    
    def _create_prompt_template(self) -> ChatPromptTemplate:
        """Crear template con soporte para prompts personalizados"""
        
        # 1. Intentar cargar prompt personalizado
        custom_template = self._load_custom_prompt()
        if custom_template:
            return self._build_custom_prompt_template(custom_template)
        
        # 2. Usar prompt por defecto del agente
        return self._create_default_prompt_template()
    
    @abstractmethod
    def _create_default_prompt_template(self) -> ChatPromptTemplate:
        """Crear el template de prompts por defecto del agente - DEBE ser implementado por cada agente"""
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
        return response
    
    def _get_fallback_response(self) -> str:
        """Respuesta de respaldo en caso de error"""
        return f"Disculpa, tuve un problema técnico. Por favor intenta de nuevo o contacta con {self.company_config.company_name}."

    def _load_custom_prompt(self) -> Optional[str]:
        """Cargar prompt personalizado desde custom_prompts.json"""
        try:
            # Construir path del archivo
            custom_prompts_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                'custom_prompts.json'
            )
            
            if not os.path.exists(custom_prompts_file):
                logger.debug(f"Custom prompts file not found: {custom_prompts_file}")
                return None
            
            # Cargar archivo JSON
            with open(custom_prompts_file, 'r', encoding='utf-8') as f:
                custom_prompts = json.load(f)
            
            # Obtener prompts de la empresa
            company_prompts = custom_prompts.get(self.company_config.company_id, {})
            
            # Obtener prompt del agente específico
            agent_key = self._get_agent_key()
            agent_data = company_prompts.get(agent_key, {})
            
            # Retornar template personalizado si existe y no es null
            custom_template = agent_data.get('template')
            if custom_template:
                logger.info(f"[{self.company_config.company_id}] Using custom prompt for {agent_key}")
                return custom_template
            
            return None
            
        except Exception as e:
            logger.warning(f"Error loading custom prompt for {self.company_config.company_id}: {e}")
            return None

    def _get_agent_key(self) -> str:
        """Obtener clave del agente para custom_prompts.json"""
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

    def save_custom_prompt(self, custom_template: str, modified_by: str = "admin") -> bool:
        """Guardar prompt personalizado para este agente"""
        try:
            custom_prompts_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                'custom_prompts.json'
            )
            
            # Cargar prompts existentes o crear estructura vacía
            if os.path.exists(custom_prompts_file):
                with open(custom_prompts_file, 'r', encoding='utf-8') as f:
                    custom_prompts = json.load(f)
            else:
                custom_prompts = {}
            
            # Asegurar que existe la estructura para la empresa
            company_id = self.company_config.company_id
            if company_id not in custom_prompts:
                custom_prompts[company_id] = {}
            
            # Obtener clave del agente
            agent_key = self._get_agent_key()
            
            # Asegurar que existe la estructura para el agente
            if agent_key not in custom_prompts[company_id]:
                custom_prompts[company_id][agent_key] = {
                    "template": None,
                    "is_custom": False,
                    "modified_at": None,
                    "modified_by": None,
                    "default_template": None
                }
            
            # Actualizar con el nuevo prompt personalizado
            custom_prompts[company_id][agent_key].update({
                "template": custom_template,
                "is_custom": True,
                "modified_at": datetime.utcnow().isoformat() + "Z",
                "modified_by": modified_by
            })
            
            # Guardar archivo actualizado
            with open(custom_prompts_file, 'w', encoding='utf-8') as f:
                json.dump(custom_prompts, f, indent=2, ensure_ascii=False)
            
            logger.info(f"[{company_id}] Custom prompt saved for {agent_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving custom prompt: {e}")
            return False

    def remove_custom_prompt(self) -> bool:
        """Remover prompt personalizado (volver a default)"""
        try:
            custom_prompts_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                'custom_prompts.json'
            )
            
            if not os.path.exists(custom_prompts_file):
                return True  # No hay archivo, ya está "limpio"
            
            # Cargar prompts
            with open(custom_prompts_file, 'r', encoding='utf-8') as f:
                custom_prompts = json.load(f)
            
            # Obtener claves
            company_id = self.company_config.company_id
            agent_key = self._get_agent_key()
            
            # Limpiar prompt personalizado
            if (company_id in custom_prompts and 
                agent_key in custom_prompts[company_id]):
                custom_prompts[company_id][agent_key].update({
                    "template": None,
                    "is_custom": False,
                    "modified_at": datetime.utcnow().isoformat() + "Z",
                    "modified_by": "system_reset"
                })
            
            # Guardar archivo actualizado
            with open(custom_prompts_file, 'w', encoding='utf-8') as f:
                json.dump(custom_prompts, f, indent=2, ensure_ascii=False)
            
            logger.info(f"[{company_id}] Custom prompt removed for {agent_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing custom prompt: {e}")
            return False

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
