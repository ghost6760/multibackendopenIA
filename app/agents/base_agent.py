# app/agents/base_agent.py - Refactorizado para soportar PostgreSQL con fallbacks
# MANTIENE: 100% compatibilidad con agentes existentes
# AÑADE: Carga de prompts desde PostgreSQL con fallbacks automáticos
# CORRIGE: Logging detallado para diagnosticar problemas de carga

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
    - CORRIGE: Logging detallado para diagnosticar problemas
    """
    
    def __init__(self, company_config: CompanyConfig, openai_service: OpenAIService):
        self.company_config = company_config
        self.openai_service = openai_service
        self.chat_model = openai_service.get_chat_model()
        self.agent_name = self.__class__.__name__
        
        # 🆕 NUEVO: Servicio de prompts para PostgreSQL
        self.prompt_service = get_prompt_service()

        # ✅ AGREGAR - Tools library (opcional)
        self.tools_library = None  # Se inyecta externamente si se necesita
        
        # 🆕 NUEVO: Cache del prompt actual para rendimiento
        self._current_prompt_template = None
        self._prompt_source = None
        
        # 🔧 LOGGING INICIAL
        logger.info(f"🏗️ [{self.company_config.company_id}] Initializing {self.agent_name}")
        
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
        3. Fallback a JSON (compatibilidad temporal)
        4. Método _create_default_prompt_template() (Hardcoded en agente)
        5. Fallback de emergencia (Prompt básico)
        """
        
        company_id = self.company_config.company_id
        agent_key = self._get_agent_key()
        
        logger.info(f"🔄 [{company_id}] Creating prompt template for {self.agent_name} (key: {agent_key})")
        
        # 1. Intentar cargar prompt personalizado desde PostgreSQL
        logger.info(f"🔍 [{company_id}] Step 1: Checking PostgreSQL custom prompts...")
        custom_template = self._load_custom_prompt_from_postgresql()
        if custom_template:
            self._prompt_source = "postgresql_custom"
            self._log_prompt_load("custom", "postgresql")
            logger.info(f"✅ [{company_id}] SUCCESS: Using PostgreSQL custom prompt for {agent_key}")
            return self._build_custom_prompt_template(custom_template)
        
        # 2. Intentar cargar prompt por defecto desde PostgreSQL
        logger.info(f"🔍 [{company_id}] Step 2: Checking PostgreSQL default prompts...")
        default_template = self._load_default_prompt_from_postgresql()
        if default_template:
            self._prompt_source = "postgresql_default"
            self._log_prompt_load("default", "postgresql")
            logger.info(f"✅ [{company_id}] SUCCESS: Using PostgreSQL default prompt for {agent_key}")
            return self._build_custom_prompt_template(default_template)
        
        # 3. Fallback a JSON (compatibilidad temporal)
        logger.info(f"🔍 [{company_id}] Step 3: Checking JSON fallback...")
        json_template = self._load_custom_prompt_from_json()
        if json_template:
            self._prompt_source = "json_fallback"
            self._log_prompt_load("custom", "json_fallback")
            logger.warning(f"⚠️ [{company_id}] Using JSON fallback prompt for {agent_key}")
            return self._build_custom_prompt_template(json_template)
        
        # 🆕 VERIFICACIÓN ADICIONAL: ¿Por qué no hay prompts en DB?
        logger.warning(f"🚨 [{company_id}] No prompts found in PostgreSQL or JSON for {agent_key}")
        try:
            # Verificar conectividad a DB
            db_status = self.prompt_service.get_db_status()
            logger.info(f"🔍 [{company_id}] DB Status: {db_status}")
            
            if db_status.get('postgresql_available', False):
                logger.error(f"🚨 [{company_id}] PostgreSQL is available but no prompts found!")
                logger.error(f"🚨 [{company_id}] This indicates a configuration or data problem")
                
                # Log todas las empresas y agentes disponibles
                try:
                    all_agents = self.prompt_service.get_company_prompts(company_id)
                    logger.error(f"🔍 [{company_id}] Available agents in DB: {list(all_agents.keys())}")
                    for ag_name, ag_data in all_agents.items():
                        logger.error(f"🔍 [{company_id}]   - {ag_name}: {ag_data.get('source', 'unknown')}")
                except Exception as debug_error:
                    logger.error(f"💥 [{company_id}] Error getting debug info: {debug_error}")
        except Exception as e:
            logger.error(f"💥 [{company_id}] Error checking DB status: {e}")
        
        # 4. Fallback a prompt hardcoded del agente
        try:
            self._prompt_source = "hardcoded_agent"
            self._log_prompt_load("default", "hardcoded_agent")
            logger.error(f"🚨 [{company_id}] FALLING BACK TO HARDCODED for {agent_key} - THIS SHOULD BE FIXED!")
            return self._create_default_prompt_template()
        except Exception as e:
            logger.error(f"💥 [{company_id}] Error creating default prompt template: {e}")
        
        # 5. Fallback de emergencia
        self._prompt_source = "emergency_fallback"
        self._log_prompt_load("emergency", "fallback")
        logger.error(f"🚨 [{company_id}] EMERGENCY FALLBACK for {agent_key}")
        return self._create_emergency_prompt_template()
    
    def _load_custom_prompt_from_postgresql(self) -> Optional[str]:
        """Cargar prompt personalizado desde PostgreSQL - VERSIÓN MEJORADA CON LOGGING"""
        try:
            company_id = self.company_config.company_id
            agent_key = self._get_agent_key()
            
            logger.info(f"🔍 [{company_id}] Loading CUSTOM prompt for agent_key: {agent_key}")
            
            # Verificar servicio de prompts
            if not self.prompt_service:
                logger.error(f"❌ [{company_id}] prompt_service is None!")
                return None
            
            # Usar el servicio de prompts con fallback automático
            logger.info(f"🔍 [{company_id}] Calling prompt_service.get_company_prompts({company_id})")
            agents_data = self.prompt_service.get_company_prompts(company_id)
            
            logger.info(f"🔍 [{company_id}] Available agents in response: {list(agents_data.keys())}")
            
            agent_data = agents_data.get(agent_key, {})
            logger.info(f"🔍 [{company_id}] Data for {agent_key}: {agent_data}")
            
            # Solo retornar si es personalizado y viene de PostgreSQL
            is_custom = agent_data.get('is_custom', False)
            source = agent_data.get('source', 'unknown')
            has_prompt = bool(agent_data.get('current_prompt'))
            
            logger.info(f"🔍 [{company_id}] Evaluation: is_custom={is_custom}, source={source}, has_prompt={has_prompt}")
            
            if (is_custom and 
                source in ['custom', 'postgresql_custom'] and
                has_prompt):
                
                prompt_content = agent_data['current_prompt']
                logger.info(f"✅ [{company_id}] Found CUSTOM prompt for {agent_key} (length: {len(prompt_content)})")
                logger.info(f"✅ [{company_id}] Prompt preview: {prompt_content[:100]}...")
                return prompt_content
            
            logger.info(f"❌ [{company_id}] No custom prompt found for {agent_key}")
            return None
            
        except Exception as e:
            logger.exception(f"💥 [{company_id}] Error loading custom prompt from PostgreSQL: {e}")
            return None
    
    def _load_default_prompt_from_postgresql(self) -> Optional[str]:
        """Cargar prompt por defecto desde PostgreSQL - VERSIÓN MEJORADA CON LOGGING"""
        try:
            if not self.prompt_service:
                logger.error(f"❌ prompt_service is None!")
                return None
            
            company_id = self.company_config.company_id
            agent_key = self._get_agent_key()
            
            logger.info(f"🔍 [{company_id}] Loading DEFAULT prompt for agent_key: {agent_key}")
            
            # Usar el servicio que busca con company_id + agent_name separados
            logger.info(f"🔍 [{company_id}] Calling prompt_service.get_company_prompts({company_id}) for defaults")
            agents_data = self.prompt_service.get_company_prompts(company_id)
            
            logger.info(f"🔍 [{company_id}] Available agents for defaults: {list(agents_data.keys())}")
            
            if agent_key in agents_data:
                agent_data = agents_data[agent_key]
                logger.info(f"🔍 [{company_id}] Default data for {agent_key}: {agent_data}")
                
                source = agent_data.get('source', 'unknown')
                has_prompt = bool(agent_data.get('current_prompt'))
                
                logger.info(f"🔍 [{company_id}] Default evaluation: source={source}, has_prompt={has_prompt}")
                
                if (source in ['default', 'postgresql_default'] and has_prompt):
                    prompt_content = agent_data['current_prompt']
                    logger.info(f"✅ [{company_id}] Found DEFAULT prompt for {agent_key} (length: {len(prompt_content)})")
                    logger.info(f"✅ [{company_id}] Default prompt preview: {prompt_content[:100]}...")
                    
                    if source == 'postgresql_default':
                        logger.info(f"✅ [{company_id}] Using company-specific default prompt for {agent_key}")
                    else:
                        logger.info(f"✅ [{company_id}] Using fallback default prompt for {agent_key}")
                    
                    return prompt_content
                else:
                    logger.info(f"❌ [{company_id}] Default prompt doesn't meet criteria for {agent_key}")
            else:
                logger.warning(f"❌ [{company_id}] Agent key {agent_key} not found in agents_data")
                logger.warning(f"❌ [{company_id}] Available keys: {list(agents_data.keys())}")
            
            return None
            
        except Exception as e:
            logger.exception(f"💥 [{company_id if 'company_id' in locals() else 'unknown'}] Error loading default prompt from PostgreSQL: {e}")
            return None
    
    def _load_custom_prompt_from_json(self) -> Optional[str]:
        """Fallback: Cargar prompt personalizado desde JSON (compatibilidad temporal)"""
        try:
            custom_prompts_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                'custom_prompts.json'
            )
            
            company_id = self.company_config.company_id
            agent_key = self._get_agent_key()
            
            logger.info(f"🔍 [{company_id}] Checking JSON file: {custom_prompts_file}")
            
            if not os.path.exists(custom_prompts_file):
                logger.info(f"❌ [{company_id}] JSON file does not exist")
                return None
            
            with open(custom_prompts_file, 'r', encoding='utf-8') as f:
                custom_prompts = json.load(f)
            
            logger.info(f"🔍 [{company_id}] JSON companies available: {list(custom_prompts.keys())}")
            
            # Navegar la estructura JSON
            company_prompts = custom_prompts.get(company_id, {})
            if not company_prompts:
                logger.info(f"❌ [{company_id}] Company not found in JSON")
                return None
            
            logger.info(f"🔍 [{company_id}] JSON agents for company: {list(company_prompts.keys())}")
            
            agent_data = company_prompts.get(agent_key, {})
            
            if isinstance(agent_data, dict) and agent_data.get('is_custom', False):
                template = agent_data.get('template')
                if template and template != "null":
                    logger.info(f"✅ [{company_id}] Found JSON custom prompt for {agent_key}")
                    return template
            
            logger.info(f"❌ [{company_id}] No valid JSON prompt for {agent_key}")
            return None
            
        except Exception as e:
            logger.exception(f"💥 [{self.company_config.company_id if hasattr(self, 'company_config') else 'unknown'}] Error loading custom prompt from JSON: {e}")
            return None
    
    def _build_custom_prompt_template(self, custom_template: str) -> ChatPromptTemplate:
        """Construir ChatPromptTemplate desde template personalizado"""
        try:
            company_id = self.company_config.company_id
            logger.info(f"🔧 [{company_id}] Building custom prompt template (length: {len(custom_template)})")
            
            # Verificar si el template ya incluye variables de contexto
            if "{company_name}" in custom_template or "{services}" in custom_template:
                # Template ya tiene contexto, usar directamente
                logger.info(f"🔧 [{company_id}] Template already has context variables")
                return ChatPromptTemplate.from_messages([
                    ("system", custom_template),
                    MessagesPlaceholder(variable_name="chat_history", optional=True),
                    ("human", "{question}")
                ])
            else:
                # Añadir contexto empresarial al template
                logger.info(f"🔧 [{company_id}] Adding context variables to template")
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
            logger.exception(f"💥 [{self.company_config.company_id}] Error building custom prompt template: {e}")
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

    def invoke(self, inputs: Dict[str, Any]) -> str:
        """
        🆕 NUEVO MÉTODO: Invoke compatible con orchestrator
        Mapea la interfaz estándar de LangChain a nuestro process_message
        """
        try:
            question = inputs.get("question", "")
            chat_history = inputs.get("chat_history", [])
            context = inputs.get("context", "")
            
            if not question:
                return f"No se proporcionó una pregunta válida para {self.company_config.company_name}."
            
            # 🆕 LOGGING ANTES DE PROCESAR
            logger.info(f"🤖 [{self.company_config.company_id}] {self.agent_name}.invoke() called")
            logger.info(f"🤖 [{self.company_config.company_id}] Question: {question[:100]}...")
            logger.info(f"🤖 [{self.company_config.company_id}] Using prompt source: {self._prompt_source}")
            
            # Usar el método existente process_message
            result = self.process_message(question, chat_history, context)
            
            logger.info(f"🤖 [{self.company_config.company_id}] Response generated (length: {len(result)})")
            return result
            
        except Exception as e:
            logger.exception(f"💥 [{self.company_config.company_id}] Error in invoke method for {self.agent_name}: {e}")
            return f"Lo siento, estoy experimentando dificultades técnicas. Por favor, contacta con {self.company_config.company_name} directamente."

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
            
            # 🆕 LOGGING DETALLADO ANTES DE ENVIAR A OPENAI
            logger.info(f"🔧 [{self.company_config.company_id}] Preparing chain inputs:")
            logger.info(f"🔧 [{self.company_config.company_id}]   - question: {question[:100]}...")
            logger.info(f"🔧 [{self.company_config.company_id}]   - company_name: {self.company_config.company_name}")
            logger.info(f"🔧 [{self.company_config.company_id}]   - services: {self.company_config.services}")
            logger.info(f"🔧 [{self.company_config.company_id}]   - prompt_source: {self._prompt_source}")
            
            # Log de procesamiento
            self._log_agent_activity("message_processed", {
                "message_length": len(question),
                "has_context": bool(context),
                "has_history": bool(chat_history)
            })
            
            # 🚨 AQUÍ SE EJECUTA LA CHAIN QUE VA A OPENAI
            logger.info(f"🚀 [{self.company_config.company_id}] Executing chain.invoke()...")
            response = self.chain.invoke(inputs)
            
            logger.info(f"✅ [{self.company_config.company_id}] Chain executed successfully, response length: {len(response)}")
            return response
            
        except Exception as e:
            logger.exception(f"💥 [{self.company_config.company_id}] Error processing message in {self.agent_name}: {e}")
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
