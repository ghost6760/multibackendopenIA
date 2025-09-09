# ============================================================================
# SERVICIO UNIFICADO DE GESTIÓN DE PROMPTS
# ============================================================================

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from app.services.redis_service import get_redis_client
from app.config.company_manager import get_company_manager

logger = logging.getLogger(__name__)

@dataclass
class PromptData:
    """Estructura de datos para prompts"""
    template: Optional[str]
    is_custom: bool
    modified_at: Optional[str]
    modified_by: Optional[str]
    default_template: Optional[str]
    version: int = 1

class PromptManagerService:
    """Servicio unificado para gestión de prompts con Redis"""
    
    def __init__(self):
        self.redis_client = get_redis_client()
        self.company_manager = get_company_manager()
    
    # ========================================================================
    # MÉTODOS PRINCIPALES DE GESTIÓN
    # ========================================================================
    
    def save_custom_prompt(self, company_id: str, agent_name: str, 
                          prompt_template: str, modified_by: str = "admin") -> bool:
        """Guardar prompt personalizado con transaccionalidad"""
        try:
            # Validar empresa
            if not self.company_manager.validate_company_id(company_id):
                raise ValueError(f"Company ID {company_id} not valid")
            
            # Crear clave Redis
            key = f"{company_id}:prompts:{agent_name}"
            
            # Preparar datos
            prompt_data = {
                "template": prompt_template,
                "is_custom": True,
                "modified_at": datetime.utcnow().isoformat() + "Z",
                "modified_by": modified_by,
                "version": self._get_next_version(key)
            }
            
            # Guardar con transacción Redis
            with self.redis_client.pipeline() as pipe:
                pipe.multi()
                pipe.hset(key, mapping=prompt_data)
                pipe.expire(key, 86400 * 365)  # TTL 1 año
                
                # Backup automático
                backup_key = f"{key}:backup:{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                existing_data = self.redis_client.hgetall(key)
                if existing_data:
                    pipe.hset(backup_key, mapping=existing_data)
                    pipe.expire(backup_key, 86400 * 30)  # TTL 30 días
                
                pipe.execute()
            
            logger.info(f"[{company_id}] Custom prompt saved for {agent_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving custom prompt: {e}")
            return False
    
    def restore_default_prompt(self, company_id: str, agent_name: str) -> bool:
        """Restaurar prompt a valores por defecto"""
        try:
            # Validar empresa
            if not self.company_manager.validate_company_id(company_id):
                raise ValueError(f"Company ID {company_id} not valid")
            
            key = f"{company_id}:prompts:{agent_name}"
            
            # Crear backup antes de restaurar
            existing_data = self.redis_client.hgetall(key)
            if existing_data:
                backup_key = f"{key}:backup:restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                self.redis_client.hset(backup_key, mapping=existing_data)
                self.redis_client.expire(backup_key, 86400 * 30)
            
            # Restaurar a valores por defecto
            default_data = {
                "template": None,
                "is_custom": False,
                "modified_at": datetime.utcnow().isoformat() + "Z",
                "modified_by": "system_restore",
                "version": self._get_next_version(key)
            }
            
            self.redis_client.hset(key, mapping=default_data)
            
            logger.info(f"[{company_id}] Prompt restored to default for {agent_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring default prompt: {e}")
            return False
    
    def get_prompt_data(self, company_id: str, agent_name: str) -> Optional[PromptData]:
        """Obtener datos de prompt"""
        try:
            key = f"{company_id}:prompts:{agent_name}"
            data = self.redis_client.hgetall(key)
            
            if not data:
                return PromptData(
                    template=None,
                    is_custom=False,
                    modified_at=None,
                    modified_by=None,
                    default_template=None
                )
            
            return PromptData(
                template=data.get('template'),
                is_custom=data.get('is_custom', 'false').lower() == 'true',
                modified_at=data.get('modified_at'),
                modified_by=data.get('modified_by'),
                default_template=data.get('default_template'),
                version=int(data.get('version', 1))
            )
            
        except Exception as e:
            logger.error(f"Error getting prompt data: {e}")
            return None
    
    def get_all_prompts(self, company_id: str) -> Dict[str, Dict[str, Any]]:
        """Obtener todos los prompts de una empresa"""
        try:
            pattern = f"{company_id}:prompts:*"
            keys = self.redis_client.keys(pattern)
            
            prompts = {}
            for key in keys:
                agent_name = key.split(':')[-1]
                data = self.redis_client.hgetall(key)
                
                if data:
                    prompts[agent_name] = {
                        "template": data.get('template'),
                        "is_custom": data.get('is_custom', 'false').lower() == 'true',
                        "modified_at": data.get('modified_at'),
                        "modified_by": data.get('modified_by'),
                        "version": int(data.get('version', 1))
                    }
            
            return prompts
            
        except Exception as e:
            logger.error(f"Error getting all prompts: {e}")
            return {}
    
    # ========================================================================
    # MÉTODOS DE MANTENIMIENTO Y BACKUP
    # ========================================================================
    
    def backup_all_prompts(self, company_id: str) -> Optional[str]:
        """Crear backup completo de prompts de una empresa"""
        try:
            prompts = self.get_all_prompts(company_id)
            backup_data = {
                "company_id": company_id,
                "backup_date": datetime.utcnow().isoformat() + "Z",
                "prompts": prompts
            }
            
            backup_key = f"backup:{company_id}:prompts:{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.redis_client.setex(
                backup_key, 
                86400 * 90,  # TTL 90 días
                json.dumps(backup_data, ensure_ascii=False)
            )
            
            logger.info(f"Backup created for {company_id}: {backup_key}")
            return backup_key
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return None
    
    def restore_from_backup(self, backup_key: str) -> bool:
        """Restaurar desde backup"""
        try:
            backup_data = self.redis_client.get(backup_key)
            if not backup_data:
                raise ValueError("Backup not found")
            
            data = json.loads(backup_data)
            company_id = data['company_id']
            prompts = data['prompts']
            
            for agent_name, prompt_data in prompts.items():
                if prompt_data.get('is_custom'):
                    self.save_custom_prompt(
                        company_id=company_id,
                        agent_name=agent_name,
                        prompt_template=prompt_data['template'],
                        modified_by=f"restore_from_{backup_key}"
                    )
            
            logger.info(f"Restored from backup: {backup_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring from backup: {e}")
            return False
    
    def _get_next_version(self, key: str) -> int:
        """Obtener siguiente versión para un prompt"""
        try:
            current_version = self.redis_client.hget(key, 'version')
            return int(current_version) + 1 if current_version else 1
        except:
            return 1

# ============================================================================
# ADAPTADOR PARA MANTENER COMPATIBILIDAD CON API ACTUAL
# ============================================================================

class PromptAPIAdapter:
    """Adaptador para mantener la estructura de respuesta actual del backend"""
    
    def __init__(self):
        self.prompt_service = PromptManagerService()
    
    def get_prompts_for_company(self, company_id: str) -> List[Dict[str, Any]]:
        """
        Mantiene la estructura de respuesta actual para el frontend
        """
        try:
            from app.config.company_manager import get_company_manager
            from app.config.agents import get_company_agents
            
            company_manager = get_company_manager()
            
            # Obtener agentes configurados para la empresa
            agents_config = get_company_agents(company_id)
            if not agents_config:
                return []
            
            prompts_data = []
            
            for agent_name, agent_config in agents_config.items():
                # Obtener datos de prompt desde Redis
                prompt_data = self.prompt_service.get_prompt_data(company_id, agent_name)
                
                # Construir respuesta manteniendo estructura actual
                prompt_info = {
                    "agent_name": agent_name,
                    "display_name": agent_config.get("name", agent_name),
                    "description": agent_config.get("description", ""),
                    "has_custom_prompt": prompt_data.is_custom if prompt_data else False,
                    "modified_at": prompt_data.modified_at if prompt_data else None,
                    "modified_by": prompt_data.modified_by if prompt_data else None,
                    "template": prompt_data.template if prompt_data and prompt_data.is_custom else None,
                    "version": prompt_data.version if prompt_data else 1
                }
                
                prompts_data.append(prompt_info)
            
            return prompts_data
            
        except Exception as e:
            logger.error(f"Error getting prompts for company: {e}")
            return []

# ============================================================================
# INSTANCIA GLOBAL
# ============================================================================

# Singleton para el servicio
_prompt_service_instance = None
_prompt_adapter_instance = None

def get_prompt_service() -> PromptManagerService:
    """Obtener instancia del servicio de prompts"""
    global _prompt_service_instance
    if _prompt_service_instance is None:
        _prompt_service_instance = PromptManagerService()
    return _prompt_service_instance

def get_prompt_api_adapter() -> PromptAPIAdapter:
    """Obtener adaptador para mantener compatibilidad con API"""
    global _prompt_adapter_instance
    if _prompt_adapter_instance is None:
        _prompt_adapter_instance = PromptAPIAdapter()
    return _prompt_adapter_instance

# ============================================================================
# SCRIPT DE MIGRACIÓN AUTOMÁTICA
# ============================================================================

def migrate_from_json_to_redis():
    """Migrar automáticamente desde JSON a Redis"""
    import os
    
    try:
        prompt_service = get_prompt_service()
        
        # Buscar archivo JSON existente
        custom_prompts_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            'custom_prompts.json'
        )
        
        if not os.path.exists(custom_prompts_file):
            logger.info("No JSON file found - migration not needed")
            return True
        
        # Cargar y migrar datos
        with open(custom_prompts_file, 'r', encoding='utf-8') as f:
            custom_prompts = json.load(f)
        
        migrated = 0
        for company_id, company_prompts in custom_prompts.items():
            for agent_name, agent_data in company_prompts.items():
                if agent_data.get('is_custom') and agent_data.get('template'):
                    success = prompt_service.save_custom_prompt(
                        company_id=company_id,
                        agent_name=agent_name,
                        prompt_template=agent_data['template'],
                        modified_by=agent_data.get('modified_by', 'migration')
                    )
                    if success:
                        migrated += 1
        
        # Crear backup del archivo original
        if migrated > 0:
            backup_file = custom_prompts_file + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.rename(custom_prompts_file, backup_file)
            
            # Crear archivo vacío
            with open(custom_prompts_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=2)
        
        logger.info(f"Migration completed: {migrated} prompts migrated")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False
