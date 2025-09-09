# app/agents/base_agent.py - Refactorizado para soportar PostgreSQL con fallbacks
# MANTIENE: 100% compatibilidad con agentes existentes
# AÑADE: Carga de prompts desde PostgreSQL con fallbacks automáticos

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import BaseMessage
from langchain.schema.output_parser import StrOutputParser
from app.config.company_config import CompanyConfig
from app.services.openai_service import OpenAIService

# 🆕 NUEVOS IMPORTS PARA POSTGRESQL
from app.services.prompt_service import get_prompt_service
import logging
import json
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """
    Clase base refactorizada para todos los agentes del sistema multi-tenant
    
    CAMBIOS PRINCIPALES:
    - Carga de prompts desde PostgreSQL con fallbacks automáticos
    - Preserva compatibilidad total con agentes existentes
    - Añade funciones para gestión de prompts personalizados
    """
    
    def __init__(self, company_config: CompanyConfig, openai_service: OpenAIService):
        self.company_config = company_config
        self.openai_service = openai_service
        self.chat_model = openai_service.get_chat_model()
        self.agent_name = self.__class__.__name__
        
        # 🆕 NUEVO: Servicio de prompts para PostgreSQL
        self.prompt_service = get_prompt_service()
        
        # 🆕 NUEVO: Cache del prompt actual para rendimiento
        self._current_prompt_template = None
        self._prompt_source = None
        
        # Inicializar el agente específico con soporte para prompts personalizados
        self._initialize_agent()
    
    @abstractmethod
    def _initialize_agent(self):
        """Inicializar configuración específica del agente"""
        pass
    
    def _create_prompt_template(self) -> ChatPromptTemplate:
        """
        Crear template con soporte para prompts personalizados desde PostgreSQL
        
        JERARQUÍA DE CARGA:
        1. PostgreSQL custom_prompts (Personalizado por empresa)
        2. PostgreSQL default_prompts (Por defecto del repositorio)
        3. Método _create_default_prompt_template() (Hardcoded en agente)
        4. Fallback de emergencia (Prompt básico)
        """
        
        # 1. Intentar cargar prompt personalizado desde PostgreSQL
        custom_template = self._load_custom_prompt_from_postgresql()
        if custom_template:
            self._prompt_source = "postgresql_custom"
            self._log_prompt_load("custom", "postgresql")
            return self._build_custom_prompt_template(custom_template)
        
        # 2. Intentar cargar prompt por defecto desde PostgreSQL
        default_template = self._load_default_prompt_from_postgresql()
        if default_template:
            self._prompt_source = "postgresql_default"
            self._log_prompt_load("default", "postgresql")
            return self._build_custom_prompt_template(default_template)
        
        # 3. Fallback a JSON (compatibilidad temporal)
        json_template = self._load_custom_prompt_from_json()
        if json_template:
            self._prompt_source = "json_fallback"
            self._log_prompt_load("custom", "json_fallback")
            return self._build_custom_prompt_template(json_template)
        
        # 4. Fallback a prompt hardcoded del agente
        try:
            self._prompt_source = "hardcoded_agent"
            self._log_prompt_load("default", "hardcoded_agent")
            return self._create_default_prompt_template()
        except Exception as e:
            logger.error(f"Error creating default prompt template: {e}")
        
        # 5. Fallback de emergencia
        self._prompt_source = "emergency_fallback"
        self._log_prompt_load("emergency", "fallback")
        return self._create_emergency_prompt_template()
    
    def _load_custom_prompt_from_postgresql(self) -> Optional[str]:
        """Cargar prompt personalizado desde PostgreSQL"""
        try:
            company_id = self.company_config.company_id
            agent_key = self._get_agent_key()
            
            # Usar el servicio de prompts con fallback automático
            agents_data = self.prompt_service.get_company_prompts(company_id)
            agent_data = agents_data.get(agent_key, {})
            
            # Solo retornar si es personalizado y viene de PostgreSQL
            if (agent_data.get('is_custom', False) and 
                agent_data.get('source') in ['custom', 'postgresql_custom'] and
                agent_data.get('current_prompt')):
                
                logger.info(f"[{company_id}] Loaded custom prompt from PostgreSQL for {agent_key}")
                return agent_data['current_prompt']
            
            return None
            
        except Exception as e:
            logger.warning(f"Error loading custom prompt from PostgreSQL: {e}")
            return None
    
    def _load_default_prompt_from_postgresql(self) -> Optional[str]:
        """Cargar prompt por defecto desde PostgreSQL default_prompts"""
        try:
            company_id = self.company_config.company_id
            agent_key = self._get_agent_key()
            
            # Usar el servicio de prompts
            agents_data = self.prompt_service.get_company_prompts(company_id)
            agent_data = agents_data.get(agent_key, {})
            
            # Solo retornar si viene de default_prompts
            if (agent_data.get('source') in ['default', 'postgresql_default'] and
                agent_data.get('current_prompt')):
                
                logger.info(f"[{company_id}] Loaded default prompt from PostgreSQL for {agent_key}")
                return agent_data['current_prompt']
            
            return None
            
        except Exception as e:
            logger.warning(f"Error loading default prompt from PostgreSQL: {e}")
            return None
    
    def _load_custom_prompt_from_json(self) -> Optional[str]:
        """Fallback: Cargar prompt personalizado desde JSON (compatibilidad temporal)"""
        try:
            custom_prompts_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                'custom_prompts.json'
            )
            
            if not os.path.exists(custom_prompts_file):
                return None
            
            with open(custom_prompts_file, 'r', encoding='utf-8') as f:
                custom_prompts = json.load(f)
            
            company_id = self.company_config.company_id
            agent_key = self._get_agent_key()
            
            # Navegar la estructura JSON
            company_prompts = custom_prompts.get(company_id, {})
            agent_data = company_prompts.get(agent_key, {})
            
            if isinstance(agent_data, dict) and agent_data.get('is_custom', False):
                template = agent_data.get('template')
                if template and template != "null":
                    logger.info(f"[{company_id}] Loaded custom prompt from JSON fallback for {agent_key}")
                    return template
            
            return None
            
        except Exception as e:
            logger.warning(f"Error loading custom prompt from JSON: {e}")
            return None
    
    def _build_custom_prompt_template(self, custom_template: str) -> ChatPromptTemplate:
        """Construir ChatPromptTemplate desde template personalizado"""
        try:
            # Verificar si el template ya incluye variables de contexto
            if "{company_name}" in custom_template or "{services}" in custom_template:
                # Template ya tiene contexto, usar directamente
                return ChatPromptTemplate.from_messages([
                    ("system", custom_template),
                    MessagesPlaceholder(variable_name="chat_history", optional=True),
                    ("human", "{question}")
                ])
            else:
                # Añadir contexto empresarial al template
                enhanced_template = f"""{custom_template}

CONTEXTO DE LA EMPRESA:
- Empresa: {{company_name}}
- Servicios: {{services}}

Responde de manera profesional y acorde a la empresa."""
                
                return ChatPromptTemplate.from_messages([
                    ("system", enhanced_template),
                    MessagesPlaceholder(variable_name="chat_history", optional=True),
                    ("human", "{question}")
                ])
                
        except Exception as e:
            logger.error(f"Error building custom prompt template: {e}")
            # Fallback al template por defecto del agente
            return self._create_default_prompt_template()
    
    def _create_emergency_prompt_template(self) -> ChatPromptTemplate:
        """Template de emergencia cuando todo falla"""
        agent_key = self._get_agent_key()
        emergency_template = f"""Eres un asistente de {self.company_config.company_name}.
Sistema en modo de recuperación - Prompt de emergencia para {agent_key}.

Empresa: {{company_name}}
Servicios: {{services}}

Ayuda al usuario de manera profesional."""
        
        return ChatPromptTemplate.from_messages([
            ("system", emergency_template),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{question}")
        ])
    
    @abstractmethod
    def _create_default_prompt_template(self) -> ChatPromptTemplate:
        """Crear template por defecto - DEBE implementar cada agente"""
        pass
    
    def _get_agent_key(self) -> str:
        """Obtener clave del agente para búsqueda en prompts"""
        # Convertir SalesAgent -> sales_agent
        class_name = self.__class__.__name__
        if class_name.endswith('Agent'):
            agent_name = class_name[:-5]  # Remover 'Agent'
        else:
            agent_name = class_name
        
        # Convertir CamelCase a snake_case
        import re
        agent_key = re.sub('([a-z0-9])([A-Z])', r'\1_\2', agent_name).lower() + '_agent'
        return agent_key
    
    def reload_prompt_template(self):
        """
        🆕 NUEVA FUNCIÓN: Recargar template de prompt
        Útil cuando se actualiza un prompt personalizado
        """
        try:
            old_source = self._prompt_source
            self.prompt_template = self._create_prompt_template()
            
            # Recrear chain si existe
            if hasattr(self, '_create_chain'):
                self._create_chain()
            
            logger.info(f"[{self.company_config.company_id}] Prompt template reloaded: {old_source} -> {self._prompt_source}")
            
        except Exception as e:
            logger.error(f"Error reloading prompt template: {e}")
    
    def get_prompt_info(self) -> Dict[str, Any]:
        """
        🆕 NUEVA FUNCIÓN: Obtener información del prompt actual
        """
        agent_key = self._get_agent_key()
        
        try:
            agents_data = self.prompt_service.get_company_prompts(self.company_config.company_id)
            agent_data = agents_data.get(agent_key, {})
            
            return {
                "agent_key": agent_key,
                "source": self._prompt_source,
                "is_custom": agent_data.get('is_custom', False),
                "last_modified": agent_data.get('last_modified'),
                "version": agent_data.get('version', 1),
                "template_preview": str(self.prompt_template)[:200] + "..." if hasattr(self, 'prompt_template') else None
            }
            
        except Exception as e:
            return {
                "agent_key": agent_key,
                "source": self._prompt_source,
                "error": str(e)
            }
    
    def save_custom_prompt(self, template: str, modified_by: str = "admin") -> bool:
        """
        🆕 NUEVA FUNCIÓN: Guardar prompt personalizado
        """
        try:
            agent_key = self._get_agent_key()
            success = self.prompt_service.save_custom_prompt(
                self.company_config.company_id,
                agent_key,
                template,
                modified_by
            )
            
            if success:
                # Recargar el template
                self.reload_prompt_template()
                self._log_agent_activity("prompt_updated", {
                    "agent_key": agent_key,
                    "modified_by": modified_by
                })
            
            return success
            
        except Exception as e:
            logger.error(f"Error saving custom prompt: {e}")
            return False
    
    def restore_default_prompt(self, modified_by: str = "admin") -> bool:
        """
        🆕 NUEVA FUNCIÓN: Restaurar prompt a default
        """
        try:
            agent_key = self._get_agent_key()
            success = self.prompt_service.restore_default_prompt(
                self.company_config.company_id,
                agent_key,
                modified_by
            )
            
            if success:
                # Recargar el template
                self.reload_prompt_template()
                self._log_agent_activity("prompt_restored", {
                    "agent_key": agent_key,
                    "modified_by": modified_by
                })
            
            return success
            
        except Exception as e:
            logger.error(f"Error restoring default prompt: {e}")
            return False
    
    def _log_prompt_load(self, prompt_type: str, source: str):
        """Log de carga de prompt con contexto"""
        self._log_agent_activity("prompt_loaded", {
            "prompt_type": prompt_type,
            "source": source,
            "agent_key": self._get_agent_key()
        })
    
    def _log_agent_activity(self, action: str, details: Dict[str, Any] = None):
        """Log de actividad del agente con contexto de empresa"""
        log_data = {
            "agent": self.agent_name,
            "company_id": self.company_config.company_id,
            "action": action,
            "prompt_source": self._prompt_source
        }
        if details:
            log_data.update(details)
        
        logger.info(f"[{self.company_config.company_id}] {self.agent_name}: {action}", extra=log_data)

    # ============================================================================
    # FUNCIONES DE COMPATIBILIDAD - MANTENER PARA NO ROMPER AGENTES EXISTENTES
    # ============================================================================
    
    def process_message(self, question: str, chat_history: List[BaseMessage] = None, context: str = "") -> str:
        """
        MANTENER: Función principal de procesamiento de mensajes
        MEJORA INTERNA: Ahora usa prompts desde PostgreSQL
        """
        try:
            if not hasattr(self, 'chain') or not self.chain:
                logger.warning(f"Chain not initialized for {self.agent_name}, attempting to create...")
                if hasattr(self, '_create_chain'):
                    self._create_chain()
                else:
                    raise Exception("Chain creation method not found")
            
            inputs = {
                "question": question,
                "chat_history": chat_history or [],
                "context": context,
                "company_name": self.company_config.company_name,
                "services": self.company_config.services
            }
            
            # Log de procesamiento
            self._log_agent_activity("message_processed", {
                "message_length": len(question),
                "has_context": bool(context),
                "has_history": bool(chat_history)
            })
            
            response = self.chain.invoke(inputs)
            return response
            
        except Exception as e:
            logger.error(f"Error processing message in {self.agent_name}: {e}")
            # Respuesta de fallback
            return f"Lo siento, estoy experimentando dificultades técnicas. Por favor, contacta con {self.company_config.company_name} directamente."

    def get_agent_capabilities(self) -> Dict[str, Any]:
        """
        🆕 NUEVA FUNCIÓN: Obtener capacidades del agente
        """
        return {
            "agent_name": self.agent_name,
            "agent_key": self._get_agent_key(),
            "company_id": self.company_config.company_id,
            "prompt_source": self._prompt_source,
            "supports_custom_prompts": True,
            "supports_context": True,
            "supports_history": True,
            "model_name": getattr(self.chat_model, 'model_name', 'unknown')
        }
