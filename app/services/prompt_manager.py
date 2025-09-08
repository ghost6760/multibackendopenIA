# app/services/prompt_manager.py
import json
import os
from typing import Dict, Optional, Any
from datetime import datetime
import redis
import logging

logger = logging.getLogger(__name__)

class PromptManager:
    """Gestor centralizado de prompts para el sistema multi-tenant"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.default_prompts_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'config', 
            'custom_prompts.json'
        )
        self._load_default_prompts()
    
    def _load_default_prompts(self):
        """Cargar prompts por defecto desde archivo JSON"""
        try:
            if os.path.exists(self.default_prompts_path):
                with open(self.default_prompts_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Extraer solo los default_template de cada agente
                    self.default_prompts = {}
                    for company_id, agents in data.items():
                        if company_id.startswith('_'):  # Skip metadata
                            continue
                        self.default_prompts[company_id] = {}
                        for agent_name, agent_data in agents.items():
                            if isinstance(agent_data, dict) and 'default_template' in agent_data:
                                self.default_prompts[company_id][agent_name] = agent_data['default_template']
                            elif isinstance(agent_data, str):
                                # Si es string directo (formato antiguo), usarlo
                                self.default_prompts[company_id][agent_name] = agent_data
                    logger.info(f"Loaded default prompts from {self.default_prompts_path}")
            else:
                logger.warning(f"Default prompts file not found at {self.default_prompts_path}")
                self.default_prompts = {}
        except Exception as e:
            logger.error(f"Error loading default prompts: {str(e)}")
            self.default_prompts = {}
    
    def get_prompt(self, company_id: str, agent_name: str) -> Optional[str]:
        """
        Obtener prompt para un agente específico
        Prioridad: Redis (custom) > Archivo JSON (default) > None
        """
        try:
            # Primero intentar obtener de Redis (prompts personalizados)
            redis_key = f"{company_id}:prompts:{agent_name}"
            custom_data = self.redis.get(redis_key)
            
            if custom_data:
                try:
                    data = json.loads(custom_data.decode('utf-8'))
                    if isinstance(data, dict) and data.get('template'):
                        logger.info(f"[{company_id}] Using custom prompt from Redis for {agent_name}")
                        return data['template']
                except (json.JSONDecodeError, AttributeError):
                    # Si no es JSON, asumir que es string directo (compatibilidad)
                    if custom_data:
                        logger.info(f"[{company_id}] Using custom prompt from Redis for {agent_name} (legacy format)")
                        return custom_data.decode('utf-8')
            
            # Si no hay en Redis, buscar en los prompts por defecto
            if company_id in self.default_prompts:
                if agent_name in self.default_prompts[company_id]:
                    logger.info(f"[{company_id}] Using default prompt for {agent_name}")
                    return self.default_prompts[company_id][agent_name]
            
            # Si tampoco hay en default_prompts, intentar cargar el archivo nuevamente
            self._load_default_prompts()
            if company_id in self.default_prompts:
                if agent_name in self.default_prompts[company_id]:
                    return self.default_prompts[company_id][agent_name]
            
            logger.warning(f"[{company_id}] No prompt found for {agent_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting prompt for {company_id}/{agent_name}: {str(e)}")
            return None
    
    def save_custom_prompt(self, company_id: str, agent_name: str, prompt: str, modified_by: str = "admin") -> bool:
        """Guardar un prompt personalizado en Redis"""
        try:
            redis_key = f"{company_id}:prompts:{agent_name}"
            
            # Crear estructura de datos completa
            prompt_data = {
                "template": prompt,
                "is_custom": True,
                "modified_at": datetime.utcnow().isoformat() + "Z",
                "modified_by": modified_by
            }
            
            # Guardar como JSON
            self.redis.set(redis_key, json.dumps(prompt_data))
            logger.info(f"[{company_id}] Custom prompt saved to Redis for {agent_name}")
            return True
        except Exception as e:
            logger.error(f"Error saving custom prompt: {str(e)}")
            return False
    
    def delete_custom_prompt(self, company_id: str, agent_name: str) -> bool:
        """Eliminar un prompt personalizado de Redis (volver al default)"""
        try:
            redis_key = f"{company_id}:prompts:{agent_name}"
            result = self.redis.delete(redis_key)
            if result:
                logger.info(f"[{company_id}] Custom prompt deleted from Redis for {agent_name}")
            return bool(result)
        except Exception as e:
            logger.error(f"Error deleting custom prompt: {str(e)}")
            return False
    
    def get_all_prompts(self, company_id: str) -> Dict[str, Dict[str, Any]]:
        """Obtener todos los prompts de una empresa con su estado completo"""
        prompts = {}
        
        # Lista de agentes esperados
        agent_names = ['router_agent', 'sales_agent', 'support_agent', 
                      'emergency_agent', 'schedule_agent']
        
        for agent_name in agent_names:
            redis_key = f"{company_id}:prompts:{agent_name}"
            
            # Obtener prompt por defecto
            default_prompt = None
            if company_id in self.default_prompts:
                default_prompt = self.default_prompts[company_id].get(agent_name)
            
            # Verificar si existe un prompt personalizado en Redis
            custom_data = self.redis.get(redis_key)
            
            if custom_data:
                try:
                    # Intentar parsear como JSON
                    data = json.loads(custom_data.decode('utf-8'))
                    if isinstance(data, dict):
                        prompts[agent_name] = {
                            'prompt': data.get('template', default_prompt),
                            'is_custom': True,
                            'source': 'redis',
                            'modified_at': data.get('modified_at'),
                            'modified_by': data.get('modified_by'),
                            'default_template': default_prompt
                        }
                    else:
                        # Si no es dict, asumir string directo
                        prompts[agent_name] = {
                            'prompt': custom_data.decode('utf-8'),
                            'is_custom': True,
                            'source': 'redis',
                            'modified_at': None,
                            'modified_by': None,
                            'default_template': default_prompt
                        }
                except (json.JSONDecodeError, AttributeError):
                    # Si no es JSON válido, usar como string
                    prompts[agent_name] = {
                        'prompt': custom_data.decode('utf-8') if custom_data else default_prompt,
                        'is_custom': True,
                        'source': 'redis',
                        'modified_at': None,
                        'modified_by': None,
                        'default_template': default_prompt
                    }
            else:
                # No hay prompt personalizado, usar default
                if default_prompt:
                    prompts[agent_name] = {
                        'prompt': default_prompt,
                        'is_custom': False,
                        'source': 'default',
                        'modified_at': None,
                        'modified_by': None,
                        'default_template': default_prompt
                    }
                else:
                    # No hay prompt disponible
                    prompts[agent_name] = {
                        'prompt': f"[Prompt por defecto no configurado para {agent_name}]",
                        'is_custom': False,
                        'source': 'none',
                        'modified_at': None,
                        'modified_by': None,
                        'default_template': None
                    }
        
        return prompts
    
    def reset_to_default(self, company_id: str, agent_name: str) -> bool:
        """Resetear un prompt a su valor por defecto"""
        try:
            # Eliminar de Redis
            self.delete_custom_prompt(company_id, agent_name)
            
            # Verificar que existe un prompt por defecto
            if company_id in self.default_prompts:
                if agent_name in self.default_prompts[company_id]:
                    logger.info(f"[{company_id}] Reset {agent_name} to default prompt")
                    return True
            
            logger.warning(f"[{company_id}] No default prompt available for {agent_name}")
            return False
            
        except Exception as e:
            logger.error(f"Error resetting prompt: {str(e)}")
            return False
    
    def export_prompts(self, company_id: str) -> Dict[str, Any]:
        """Exportar todos los prompts de una empresa en formato JSON"""
        all_prompts = self.get_all_prompts(company_id)
        
        export_data = {
            company_id: {},
            "_metadata": {
                "exported_at": datetime.utcnow().isoformat() + "Z",
                "company": company_id,
                "total_prompts": len(all_prompts),
                "custom_prompts": sum(1 for p in all_prompts.values() if p['is_custom'])
            }
        }
        
        for agent_name, prompt_data in all_prompts.items():
            export_data[company_id][agent_name] = {
                "template": prompt_data['prompt'] if prompt_data['is_custom'] else None,
                "is_custom": prompt_data['is_custom'],
                "modified_at": prompt_data.get('modified_at'),
                "modified_by": prompt_data.get('modified_by'),
                "default_template": prompt_data.get('default_template')
            }
        
        return export_data
    
    def import_prompts(self, company_id: str, import_data: Dict[str, Any], modified_by: str = "admin") -> Dict[str, bool]:
        """Importar prompts desde un diccionario JSON"""
        results = {}
        
        if company_id not in import_data:
            logger.error(f"Company {company_id} not found in import data")
            return results
        
        for agent_name, agent_data in import_data[company_id].items():
            if isinstance(agent_data, dict) and agent_data.get('template'):
                # Solo importar si hay un template personalizado
                success = self.save_custom_prompt(
                    company_id, 
                    agent_name, 
                    agent_data['template'],
                    modified_by
                )
                results[agent_name] = success
            else:
                results[agent_name] = True  # No hay nada que importar
        
        return results
