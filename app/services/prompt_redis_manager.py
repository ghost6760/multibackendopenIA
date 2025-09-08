# app/services/prompt_redis_manager.py
"""
Gestor de prompts personalizados con persistencia en Redis
Mantiene compatibilidad con el sistema actual y añade persistencia distribuida
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import os
from app.services.redis_service import get_redis_client
from app.config.constants import REDIS_TTL

logger = logging.getLogger(__name__)

class PromptRedisManager:
    """Manager para prompts personalizados con persistencia en Redis"""
    
    # Constantes para keys de Redis
    PROMPTS_KEY_PREFIX = "prompts:"
    DEFAULT_PROMPTS_KEY = "default_prompts:"
    PROMPTS_VERSION_KEY = "prompts_version:"
    
    # TTL para prompts (30 días - son configuraciones estables)
    PROMPTS_TTL = None
    
    def __init__(self):
        self.redis_client = get_redis_client()
        self._ensure_defaults_loaded()
    
    def _get_prompt_key(self, company_id: str, agent_name: str) -> str:
        """Generar key de Redis para un prompt específico"""
        return f"{company_id}:{self.PROMPTS_KEY_PREFIX}{agent_name}"
    
    def _get_default_prompt_key(self, agent_name: str) -> str:
        """Generar key de Redis para prompt por defecto"""
        return f"{self.DEFAULT_PROMPTS_KEY}{agent_name}"
    
    def _get_company_prompts_pattern(self, company_id: str) -> str:
        """Patrón para buscar todos los prompts de una empresa"""
        return f"{company_id}:{self.PROMPTS_KEY_PREFIX}*"
    
    def _ensure_defaults_loaded(self):
        """Asegurar que los prompts por defecto estén cargados en Redis"""
        try:
            # Verificar si ya están cargados
            version_key = f"{self.PROMPTS_VERSION_KEY}defaults"
            if self.redis_client.exists(version_key):
                return
            
            # Cargar desde archivo de defaults si existe
            defaults_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'default_prompts.json'
            )
            
            if os.path.exists(defaults_file):
                with open(defaults_file, 'r', encoding='utf-8') as f:
                    defaults = json.load(f)
                
                # Guardar cada prompt por defecto
                for agent_name, template in defaults.items():
                    key = self._get_default_prompt_key(agent_name)
                    self.redis_client.setex(
                        key,
                        self.PROMPTS_TTL,
                        json.dumps({
                            "template": template,
                            "is_default": True,
                            "created_at": datetime.utcnow().isoformat() + "Z"
                        })
                    )
                
                # Marcar como cargado
                self.redis_client.setex(version_key, self.PROMPTS_TTL, "1")
                logger.info("Default prompts loaded into Redis")
                
        except Exception as e:
            logger.warning(f"Could not load default prompts: {e}")
    
    def save_custom_prompt(self, company_id: str, agent_name: str, 
                          prompt_template: str, modified_by: str = "admin") -> bool:
        """
        Guardar prompt personalizado en Redis
        Mantiene compatibilidad con el sistema actual
        """
        try:
            # Primero guardar el prompt por defecto si no existe
            self._save_default_if_not_exists(company_id, agent_name)
            
            # Crear estructura del prompt
            prompt_data = {
                "template": prompt_template,
                "is_custom": True,
                "modified_at": datetime.utcnow().isoformat() + "Z",
                "modified_by": modified_by,
                "company_id": company_id,
                "agent_name": agent_name
            }
            
            # Guardar en Redis con TTL
            key = self._get_prompt_key(company_id, agent_name)
            self.redis_client.setex(
                key,
                self.PROMPTS_TTL,
                json.dumps(prompt_data)
            )
            
            # También mantener sincronizado con archivo JSON para compatibilidad
            self._sync_to_json_file(company_id, agent_name, prompt_data)
            
            logger.info(f"[{company_id}] Custom prompt saved to Redis for {agent_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving custom prompt to Redis: {e}")
            # Fallback al sistema de archivos
            return self._fallback_save_to_file(company_id, agent_name, prompt_template, modified_by)
    
    def load_custom_prompt(self, company_id: str, agent_name: str) -> Optional[str]:
        """
        Cargar prompt personalizado desde Redis
        Con fallback a archivo JSON si no está en Redis
        """
        try:
            # Intentar cargar desde Redis
            key = self._get_prompt_key(company_id, agent_name)
            data = self.redis_client.get(key)
            
            if data:
                prompt_data = json.loads(data)
                if prompt_data.get('is_custom') and prompt_data.get('template'):
                    logger.debug(f"[{company_id}] Loaded custom prompt from Redis for {agent_name}")
                    return prompt_data['template']
            
            # Si no está en Redis, intentar cargar desde archivo y migrar
            return self._migrate_from_file_if_exists(company_id, agent_name)
            
        except Exception as e:
            logger.warning(f"Error loading prompt from Redis: {e}")
            # Fallback al sistema de archivos
            return self._fallback_load_from_file(company_id, agent_name)
    
    def delete_custom_prompt(self, company_id: str, agent_name: str) -> bool:
        """
        Eliminar prompt personalizado (restaurar al default)
        Mantiene el prompt por defecto guardado para poder restaurar
        """
        try:
            # Obtener el prompt por defecto
            default_prompt = self._get_default_prompt(agent_name)
            
            if default_prompt:
                # Actualizar en Redis marcando como no personalizado
                prompt_data = {
                    "template": None,  # Sin template personalizado
                    "is_custom": False,
                    "modified_at": datetime.utcnow().isoformat() + "Z",
                    "modified_by": "system_reset",
                    "default_template": default_prompt,
                    "company_id": company_id,
                    "agent_name": agent_name
                }
                
                key = self._get_prompt_key(company_id, agent_name)
                self.redis_client.setex(
                    key,
                    self.PROMPTS_TTL,
                    json.dumps(prompt_data)
                )
            else:
                # Si no hay default, simplemente eliminar
                key = self._get_prompt_key(company_id, agent_name)
                self.redis_client.delete(key)
            
            # Sincronizar con archivo JSON
            self._sync_delete_to_json_file(company_id, agent_name)
            
            logger.info(f"[{company_id}] Custom prompt deleted from Redis for {agent_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting custom prompt from Redis: {e}")
            return self._fallback_delete_from_file(company_id, agent_name)
    
    def get_all_prompts(self, company_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Obtener todos los prompts de una empresa
        Combina prompts personalizados y defaults
        """
        try:
            prompts = {}
            
            # Buscar todos los prompts de la empresa en Redis
            pattern = self._get_company_prompts_pattern(company_id)
            keys = self.redis_client.keys(pattern)
            
            for key in keys:
                # Extraer nombre del agente del key
                agent_name = key.split(':')[-1]
                data = self.redis_client.get(key)
                
                if data:
                    prompt_data = json.loads(data)
                    prompts[agent_name] = prompt_data
            
            # Si no hay prompts en Redis, migrar desde archivo
            if not prompts:
                prompts = self._migrate_all_from_file(company_id)
            
            # Asegurar que todos los agentes conocidos tengan entrada
            for agent_name in ['router_agent', 'sales_agent', 'support_agent', 
                              'emergency_agent', 'schedule_agent']:
                if agent_name not in prompts:
                    default_template = self._get_default_prompt(agent_name)
                    prompts[agent_name] = {
                        "template": None,
                        "is_custom": False,
                        "default_template": default_template
                    }
            
            return prompts
            
        except Exception as e:
            logger.error(f"Error getting all prompts from Redis: {e}")
            return self._fallback_get_all_from_file(company_id)
    
    def has_custom_prompt(self, company_id: str, agent_name: str) -> bool:
        """Verificar si existe un prompt personalizado"""
        try:
            key = self._get_prompt_key(company_id, agent_name)
            data = self.redis_client.get(key)
            
            if data:
                prompt_data = json.loads(data)
                return prompt_data.get('is_custom', False)
            
            return False
            
        except Exception as e:
            logger.warning(f"Error checking custom prompt in Redis: {e}")
            return self._fallback_has_custom_from_file(company_id, agent_name)
    
    def get_modification_info(self, company_id: str, agent_name: str) -> Dict[str, Any]:
        """Obtener información de modificación del prompt"""
        try:
            key = self._get_prompt_key(company_id, agent_name)
            data = self.redis_client.get(key)
            
            if data:
                prompt_data = json.loads(data)
                return {
                    "modified_at": prompt_data.get('modified_at'),
                    "modified_by": prompt_data.get('modified_by'),
                    "is_custom": prompt_data.get('is_custom', False)
                }
            
            return {
                "modified_at": None,
                "modified_by": None,
                "is_custom": False
            }
            
        except Exception as e:
            logger.warning(f"Error getting modification info from Redis: {e}")
            return {"modified_at": None, "modified_by": None, "is_custom": False}
    
    # ============================================================================
    # MÉTODOS AUXILIARES Y DE MIGRACIÓN
    # ============================================================================
    
    def _save_default_if_not_exists(self, company_id: str, agent_name: str):
        """Guardar el prompt por defecto actual antes de personalizar"""
        try:
            # Si ya existe un prompt guardado, no hacer nada
            key = self._get_prompt_key(company_id, agent_name)
            if self.redis_client.exists(key):
                return
            
            # Obtener el prompt por defecto del agente
            default_prompt = self._get_default_prompt_from_agent(company_id, agent_name)
            if default_prompt:
                # Guardar como referencia por defecto
                default_key = self._get_default_prompt_key(agent_name)
                self.redis_client.setex(
                    default_key,
                    self.PROMPTS_TTL,
                    json.dumps({
                        "template": default_prompt,
                        "is_default": True,
                        "saved_at": datetime.utcnow().isoformat() + "Z"
                    })
                )
                
        except Exception as e:
            logger.warning(f"Could not save default prompt: {e}")
    
    def _get_default_prompt(self, agent_name: str) -> Optional[str]:
        """Obtener el prompt por defecto de un agente"""
        try:
            # Primero buscar en Redis
            default_key = self._get_default_prompt_key(agent_name)
            data = self.redis_client.get(default_key)
            
            if data:
                prompt_data = json.loads(data)
                return prompt_data.get('template')
            
            # Si no está en Redis, obtener del sistema
            return self._get_default_prompt_from_system(agent_name)
            
        except Exception as e:
            logger.warning(f"Error getting default prompt: {e}")
            return None
    
    def _get_default_prompt_from_agent(self, company_id: str, agent_name: str) -> Optional[str]:
        """Obtener el prompt por defecto directamente del agente"""
        try:
            # Este método sería llamado por el agente para obtener su prompt por defecto
            # Por ahora retornamos None para que use su método interno
            return None
        except Exception as e:
            logger.warning(f"Error getting default from agent: {e}")
            return None
    
    def _get_system_default_prompt(self, agent_name: str) -> Optional[str]:
        """Obtener prompt por defecto del sistema"""
        # Prompts por defecto básicos del sistema
        defaults = {
            "router_agent": "You are a routing agent. Direct users to the appropriate specialist.",
            "sales_agent": "You are a sales agent. Help users with product information and purchases.",
            "support_agent": "You are a support agent. Assist users with their questions and issues.",
            "emergency_agent": "You are an emergency response agent. Handle urgent situations promptly.",
            "schedule_agent": "You are a scheduling agent. Help users book and manage appointments."
        }
        return defaults.get(agent_name)
    
    # ============================================================================
    # MÉTODOS DE SINCRONIZACIÓN CON ARCHIVO JSON
    # ============================================================================
    
    def _sync_to_json_file(self, company_id: str, agent_name: str, prompt_data: Dict[str, Any]):
        """Sincronizar cambios con archivo JSON para compatibilidad"""
        try:
            custom_prompts_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'custom_prompts.json'
            )
            
            # Cargar archivo existente o crear nuevo
            if os.path.exists(custom_prompts_file):
                with open(custom_prompts_file, 'r', encoding='utf-8') as f:
                    custom_prompts = json.load(f)
            else:
                custom_prompts = {}
            
            # Actualizar estructura
            if company_id not in custom_prompts:
                custom_prompts[company_id] = {}
            
            custom_prompts[company_id][agent_name] = prompt_data
            
            # Guardar archivo
            with open(custom_prompts_file, 'w', encoding='utf-8') as f:
                json.dump(custom_prompts, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.warning(f"Could not sync to JSON file: {e}")
    
    def _sync_delete_to_json_file(self, company_id: str, agent_name: str):
        """Sincronizar eliminación con archivo JSON"""
        try:
            custom_prompts_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'custom_prompts.json'
            )
            
            if not os.path.exists(custom_prompts_file):
                return
            
            with open(custom_prompts_file, 'r', encoding='utf-8') as f:
                custom_prompts = json.load(f)
            
            if company_id in custom_prompts and agent_name in custom_prompts[company_id]:
                custom_prompts[company_id][agent_name].update({
                    "template": None,
                    "is_custom": False,
                    "modified_at": datetime.utcnow().isoformat() + "Z",
                    "modified_by": "system_reset"
                })
                
                with open(custom_prompts_file, 'w', encoding='utf-8') as f:
                    json.dump(custom_prompts, f, indent=2, ensure_ascii=False)
                    
        except Exception as e:
            logger.warning(f"Could not sync delete to JSON file: {e}")
    
    # ============================================================================
    # MÉTODOS DE MIGRACIÓN DESDE ARCHIVO
    # ============================================================================
    
    def _migrate_from_file_if_exists(self, company_id: str, agent_name: str) -> Optional[str]:
        """Migrar prompt desde archivo a Redis si existe"""
        try:
            custom_prompts_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'custom_prompts.json'
            )
            
            if not os.path.exists(custom_prompts_file):
                return None
            
            with open(custom_prompts_file, 'r', encoding='utf-8') as f:
                custom_prompts = json.load(f)
            
            company_prompts = custom_prompts.get(company_id, {})
            agent_data = company_prompts.get(agent_name, {})
            
            if agent_data and agent_data.get('is_custom'):
                # Migrar a Redis
                key = self._get_prompt_key(company_id, agent_name)
                self.redis_client.setex(
                    key,
                    self.PROMPTS_TTL,
                    json.dumps(agent_data)
                )
                logger.info(f"Migrated prompt from file to Redis: {company_id}/{agent_name}")
                return agent_data.get('template')
            
            return None
            
        except Exception as e:
            logger.warning(f"Error migrating from file: {e}")
            return None
    
    def _migrate_all_from_file(self, company_id: str) -> Dict[str, Dict[str, Any]]:
        """Migrar todos los prompts de una empresa desde archivo"""
        try:
            custom_prompts_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'custom_prompts.json'
            )
            
            if not os.path.exists(custom_prompts_file):
                return {}
            
            with open(custom_prompts_file, 'r', encoding='utf-8') as f:
                custom_prompts = json.load(f)
            
            company_prompts = custom_prompts.get(company_id, {})
            
            # Migrar todos a Redis
            for agent_name, agent_data in company_prompts.items():
                if agent_data:
                    key = self._get_prompt_key(company_id, agent_name)
                    self.redis_client.setex(
                        key,
                        self.PROMPTS_TTL,
                        json.dumps(agent_data)
                    )
            
            logger.info(f"Migrated all prompts for company {company_id} to Redis")
            return company_prompts
            
        except Exception as e:
            logger.warning(f"Error migrating all from file: {e}")
            return {}
    
    # ============================================================================
    # MÉTODOS FALLBACK AL SISTEMA DE ARCHIVOS
    # ============================================================================
    
    def _fallback_save_to_file(self, company_id: str, agent_name: str, 
                               prompt_template: str, modified_by: str) -> bool:
        """Fallback: guardar en archivo si Redis falla"""
        try:
            from app.routes.admin import _save_custom_prompt
            return _save_custom_prompt(company_id, agent_name, prompt_template, modified_by)
        except:
            return False
    
    def _fallback_load_from_file(self, company_id: str, agent_name: str) -> Optional[str]:
        """Fallback: cargar desde archivo si Redis falla"""
        try:
            custom_prompts_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'custom_prompts.json'
            )
            
            if not os.path.exists(custom_prompts_file):
                return None
            
            with open(custom_prompts_file, 'r', encoding='utf-8') as f:
                custom_prompts = json.load(f)
            
            company_prompts = custom_prompts.get(company_id, {})
            agent_data = company_prompts.get(agent_name, {})
            
            if agent_data and agent_data.get('is_custom'):
                return agent_data.get('template')
            
            return None
        except:
            return None
    
    def _fallback_delete_from_file(self, company_id: str, agent_name: str) -> bool:
        """Fallback: eliminar desde archivo si Redis falla"""
        try:
            from app.routes.admin import _delete_custom_prompt
            return _delete_custom_prompt(company_id, agent_name)
        except:
            return False
    
    def _fallback_get_all_from_file(self, company_id: str) -> Dict[str, Dict[str, Any]]:
        """Fallback: obtener todos desde archivo si Redis falla"""
        try:
            from app.routes.admin import _load_default_prompts
            return _load_default_prompts(company_id)
        except:
            return {}
    
    def _fallback_has_custom_from_file(self, company_id: str, agent_name: str) -> bool:
        """Fallback: verificar personalización desde archivo"""
        try:
            from app.routes.admin import _has_custom_prompt
            return _has_custom_prompt(company_id, agent_name)
        except:
            return False

# ============================================================================
# SINGLETON PARA GESTIÓN GLOBAL
# ============================================================================

_prompt_redis_manager = None

def get_prompt_redis_manager() -> PromptRedisManager:
    """Obtener instancia singleton del manager de prompts"""
    global _prompt_redis_manager
    if _prompt_redis_manager is None:
        _prompt_redis_manager = PromptRedisManager()
    return _prompt_redis_manager
