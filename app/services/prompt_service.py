# app/services/prompt_service.py - MEJORADO CON AUTO-RECARGA DE ORCHESTRATOR
# Servicio refactorizado para gestión de prompts con PostgreSQL, fallbacks y auto-recarga

import logging
import json
import os
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

class PromptService:
    """Servicio para gestión de prompts con PostgreSQL, fallbacks, versionado y AUTO-RECARGA"""
    
    def __init__(self, db_connection_string: str = None):
        """
        Inicializar servicio de prompts
        
        Args:
            db_connection_string: String de conexión PostgreSQL
        """
        self.db_connection_string = db_connection_string or os.getenv('DATABASE_URL')
        self.last_fallback_level = None
        self.repair_summary = []
        
        # Información de último fallback usado
        self._last_fallback_info = {"level": "none", "source": "postgresql"}
        self._db_status = "connected"
        
        # Cache para prompts hardcodeados (fallback nivel 3)
        self._hardcoded_prompts = {
            'router_agent': 'Eres un asistente especializado en clasificar intenciones. Responde con: VENTAS, SOPORTE, EMERGENCIA, AGENDAMIENTO, o DISPONIBILIDAD.',
            'sales_agent': 'Eres un especialista en ventas. Proporciona información comercial y promueve la reserva de citas.',
            'support_agent': 'Eres un asistente de soporte. Ayuda a resolver dudas y proporciona información sobre servicios.',
            'emergency_agent': 'Eres un asistente para emergencias médicas. Proporciona primeros auxilios básicos y recomienda atención médica.',
            'schedule_agent': 'Eres un asistente de agendamiento. Ayuda a programar, modificar o cancelar citas médicas.',
            'availability_agent': 'Eres un asistente de disponibilidad. Proporciona información sobre horarios y disponibilidad de servicios.'
        }
    
    # ============================================================================
    # NUEVA FUNCIONALIDAD: AUTO-RECARGA DE ORCHESTRATOR
    # ============================================================================
    
    def _reload_orchestrator_for_company(self, company_id: str) -> bool:
        """
        Recargar orchestrator para una empresa específica después de cambiar prompts
        
        Args:
            company_id: ID de la empresa
            
        Returns:
            bool: True si se recargó exitosamente
        """
        try:
            # Importar aquí para evitar imports circulares
            from app.services.multi_agent_factory import get_multi_agent_factory
            
            logger.info(f"🔄 [AUTO-RELOAD] Reloading orchestrator for {company_id}")
            
            factory = get_multi_agent_factory()
            
            # Verificar si existe el orchestrator actual
            if hasattr(factory, '_orchestrators') and company_id in factory._orchestrators:
                logger.info(f"🔄 [AUTO-RELOAD] Removing cached orchestrator for {company_id}")
                del factory._orchestrators[company_id]
            
            # Crear nuevo orchestrator (esto carga prompts frescos desde la DB)
            new_orchestrator = factory.get_orchestrator(company_id)
            
            if new_orchestrator:
                logger.info(f"✅ [AUTO-RELOAD] Orchestrator reloaded successfully for {company_id}")
                return True
            else:
                logger.warning(f"⚠️ [AUTO-RELOAD] Failed to create new orchestrator for {company_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ [AUTO-RELOAD] Error reloading orchestrator for {company_id}: {e}")
            return False
    
    def _auto_reload_after_prompt_change(self, company_id: str, operation: str, agent_name: str = None) -> None:
        """
        Ejecutar auto-recarga después de cualquier cambio en prompts
        
        Args:
            company_id: ID de la empresa
            operation: Tipo de operación (update, restore, repair)
            agent_name: Nombre del agente (opcional)
        """
        try:
            logger.info(f"🔄 [AUTO-RELOAD] Triggering auto-reload after {operation} for {company_id}")
            
            # Intentar recargar orchestrator
            reload_success = self._reload_orchestrator_for_company(company_id)
            
            if reload_success:
                logger.info(f"✅ [AUTO-RELOAD] Auto-reload completed successfully after {operation}")
            else:
                logger.warning(f"⚠️ [AUTO-RELOAD] Auto-reload failed after {operation}, but prompt operation was successful")
            
            # También limpiar cache del company manager si existe
            try:
                from app.config.company_config import get_company_manager
                company_manager = get_company_manager()
                
                if hasattr(company_manager, '_configs') and company_id in company_manager._configs:
                    # Forzar recarga de configuración específica
                    del company_manager._configs[company_id]
                    logger.info(f"🧹 [AUTO-RELOAD] Cleared company manager cache for {company_id}")
                    
            except Exception as cm_error:
                logger.warning(f"Could not clear company manager cache: {cm_error}")
                
        except Exception as e:
            logger.error(f"❌ [AUTO-RELOAD] Error in auto-reload process: {e}")
            # No fallar la operación principal por errores de recarga
    
    # ============================================================================
    # MÉTODOS EXISTENTES MEJORADOS CON AUTO-RECARGA
    # ============================================================================
    
    def save_custom_prompt(self, company_id: str, agent_name: str, template: str, modified_by: str = "admin") -> bool:
        """
        Guardar prompt personalizado con versionado automático y AUTO-RECARGA
        
        Args:
            company_id: ID de la empresa
            agent_name: Nombre del agente
            template: Template del prompt
            modified_by: Usuario que modifica
            
        Returns:
            bool: True si se guardó exitosamente
        """
        conn = self.get_db_connection()
        if not conn:
            # Fallback a JSON si no hay PostgreSQL
            success = self._save_prompt_to_json(company_id, agent_name, template, modified_by)
            if success:
                self._auto_reload_after_prompt_change(company_id, "update_json", agent_name)
            return success
        
        try:
            with conn.cursor() as cursor:
                # Usar UPSERT para insertar o actualizar
                cursor.execute("""
                    INSERT INTO custom_prompts (company_id, agent_name, template, created_by, modified_by, notes)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (company_id, agent_name) 
                    DO UPDATE SET 
                        template = EXCLUDED.template,
                        modified_by = EXCLUDED.modified_by,
                        modified_at = CURRENT_TIMESTAMP,
                        notes = EXCLUDED.notes,
                        is_active = true
                """, (company_id, agent_name, template, modified_by, modified_by, f"Updated by {modified_by}"))
                
                conn.commit()
                logger.info(f"Prompt saved for {company_id}/{agent_name} by {modified_by}")
                
                # ✅ AUTO-RECARGA DESPUÉS DE GUARDAR
                self._auto_reload_after_prompt_change(company_id, "update", agent_name)
                
                return True
                
        except Exception as e:
            logger.error(f"Error saving prompt to PostgreSQL: {e}")
            conn.rollback()
            # Fallback a JSON
            success = self._save_prompt_to_json(company_id, agent_name, template, modified_by)
            if success:
                self._auto_reload_after_prompt_change(company_id, "update_json_fallback", agent_name)
            return success
        finally:
            conn.close()
    
    def restore_default_prompt(self, company_id: str, agent_name: str, modified_by: str = "admin") -> bool:
        """
        Restaurar prompt a default eliminando personalización y AUTO-RECARGA
        
        Args:
            company_id: ID de la empresa
            agent_name: Nombre del agente
            modified_by: Usuario que restaura
            
        Returns:
            bool: True si se restauró exitosamente
        """
        conn = self.get_db_connection()
        if not conn:
            # Fallback a JSON
            success = self._restore_prompt_in_json(company_id, agent_name)
            if success:
                self._auto_reload_after_prompt_change(company_id, "restore_json", agent_name)
            return success
        
        try:
            with conn.cursor() as cursor:
                # Marcar como inactivo en lugar de eliminar (preservar historial)
                cursor.execute("""
                    UPDATE custom_prompts 
                    SET is_active = false, 
                        modified_by = %s, 
                        modified_at = CURRENT_TIMESTAMP,
                        notes = 'Restored to default'
                    WHERE company_id = %s AND agent_name = %s
                """, (modified_by, company_id, agent_name))
                
                rows_affected = cursor.rowcount
                conn.commit()
                
                if rows_affected > 0:
                    logger.info(f"Prompt restored to default for {company_id}/{agent_name}")
                else:
                    logger.info(f"No custom prompt found to restore for {company_id}/{agent_name}")
                
                # ✅ AUTO-RECARGA DESPUÉS DE RESTAURAR
                self._auto_reload_after_prompt_change(company_id, "restore", agent_name)
                
                return True
                
        except Exception as e:
            logger.error(f"Error restoring prompt in PostgreSQL: {e}")
            conn.rollback()
            # Fallback a JSON
            success = self._restore_prompt_in_json(company_id, agent_name)
            if success:
                self._auto_reload_after_prompt_change(company_id, "restore_json_fallback", agent_name)
            return success
        finally:
            conn.close()
    
    def repair_from_repository(self, company_id: str = None, agent_name: str = None, repair_user: str = "system_repair") -> bool:
        """
        Función REPARAR - Restaura prompts desde repositorio con AUTO-RECARGA
        
        Args:
            company_id: ID de empresa (requerido)
            agent_name: Agente específico (opcional, None = todos)
            repair_user: Usuario que ejecuta la reparación
            
        Returns:
            bool: True si la reparación fue exitosa
        """
        if not company_id:
            logger.error("company_id is required for repair operation")
            return False
        
        self.repair_summary = []
        
        conn = self.get_db_connection()
        if not conn:
            # Fallback: reparar desde hardcoded prompts
            success = self._repair_from_hardcoded(company_id, agent_name, repair_user)
            if success:
                self._auto_reload_after_prompt_change(company_id, "repair_hardcoded", agent_name)
            return success
        
        try:
            with conn.cursor() as cursor:
                # Usar la función SQL de reparación si existe, si no, implementar lógica aquí
                agents_to_repair = [agent_name] if agent_name else list(self._hardcoded_prompts.keys())
                
                for agent in agents_to_repair:
                    try:
                        # Buscar prompt default en PostgreSQL
                        cursor.execute("""
                            SELECT template FROM default_prompts 
                            WHERE company_id = %s AND agent_name = %s
                        """, (company_id, agent))
                        
                        default_result = cursor.fetchone()
                        
                        if default_result:
                            # Restaurar desde default_prompts
                            template = default_result['template']
                            action = "REPAIR_FROM_DEFAULT"
                        else:
                            # Usar hardcoded como fallback
                            template = self._hardcoded_prompts.get(agent)
                            action = "REPAIR_FROM_HARDCODED"
                        
                        if template:
                            # Guardar como custom prompt
                            cursor.execute("""
                                INSERT INTO custom_prompts (company_id, agent_name, template, created_by, modified_by, notes)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                ON CONFLICT (company_id, agent_name) 
                                DO UPDATE SET 
                                    template = EXCLUDED.template,
                                    modified_by = EXCLUDED.modified_by,
                                    modified_at = CURRENT_TIMESTAMP,
                                    notes = EXCLUDED.notes,
                                    is_active = true
                            """, (company_id, agent, template, repair_user, repair_user, f"Repaired by {repair_user}"))
                            
                            self.repair_summary.append({
                                "agent_name": agent,
                                "action": action,
                                "success": True,
                                "message": f"Repaired from {'default_prompts' if default_result else 'hardcoded'}"
                            })
                        else:
                            self.repair_summary.append({
                                "agent_name": agent,
                                "action": "REPAIR_FAILED",
                                "success": False,
                                "message": "No template found"
                            })
                            
                    except Exception as agent_error:
                        logger.error(f"Error repairing agent {agent}: {agent_error}")
                        self.repair_summary.append({
                            "agent_name": agent,
                            "action": "REPAIR_ERROR",
                            "success": False,
                            "message": str(agent_error)
                        })
                
                conn.commit()
                
                success_count = sum(1 for item in self.repair_summary if item['success'])
                total_agents = len(self.repair_summary)
                
                logger.info(f"Repair completed: {success_count}/{total_agents} agents repaired for {company_id}")
                
                # ✅ AUTO-RECARGA DESPUÉS DE REPARAR (solo si hubo cambios exitosos)
                if success_count > 0:
                    self._auto_reload_after_prompt_change(company_id, "repair", agent_name)
                
                return success_count > 0
                
        except Exception as e:
            logger.error(f"Error in repair operation: {e}")
            conn.rollback()
            # Fallback a reparación hardcoded
            success = self._repair_from_hardcoded(company_id, agent_name, repair_user)
            if success:
                self._auto_reload_after_prompt_change(company_id, "repair_fallback", agent_name)
            return success
        finally:
            conn.close()
    
    # ============================================================================
    # MÉTODO MANUAL PARA RECARGA (SI SE NECESITA)
    # ============================================================================
    
    def reload_orchestrator(self, company_id: str) -> bool:
        """
        Método público para recargar orchestrator manualmente
        
        Args:
            company_id: ID de la empresa
            
        Returns:
            bool: True si se recargó exitosamente
        """
        logger.info(f"🔄 [MANUAL-RELOAD] Manual orchestrator reload requested for {company_id}")
        return self._reload_orchestrator_for_company(company_id)
    
    # ============================================================================
    # MÉTODOS EXISTENTES SIN CAMBIOS
    # ============================================================================
    
    def get_last_fallback_info(self) -> dict:
        """Obtener información del último fallback usado"""
        return self._last_fallback_info
    
    def get_db_connection(self) -> Optional[psycopg2.extensions.connection]:
        """Obtener conexión a PostgreSQL con manejo de errores"""
        try:
            if not self.db_connection_string:
                logger.warning("No database connection string provided")
                return None
                
            conn = psycopg2.connect(
                self.db_connection_string,
                cursor_factory=RealDictCursor
            )
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            return None
    
    def get_company_prompts(self, company_id: str, agents: List[str] = None) -> Optional[Dict[str, Dict]]:
        """
        Obtener prompts de una empresa con arquitectura separada
        
        Returns:
            Dict con datos de prompts para cada agente
        """
        if agents is None:
            agents = ['router_agent', 'sales_agent', 'support_agent', 'emergency_agent', 'schedule_agent']
        
        conn = self.get_db_connection()
        if not conn:
            # Fallback a JSON si no hay PostgreSQL
            return self._get_prompts_from_json_fallback(company_id, agents)
        
        try:
            agents_data = {}
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                for agent_name in agents:
                    # Buscar custom prompt (personalizado)
                    cursor.execute("""
                        SELECT template, is_active, version, modified_at, modified_by, notes
                        FROM custom_prompts 
                        WHERE company_id = %s AND agent_name = %s AND is_active = true
                    """, (company_id, agent_name))
                    
                    custom_result = cursor.fetchone()
                    
                    if custom_result:
                        # Tiene prompt personalizado
                        agents_data[agent_name] = {
                            "current_prompt": custom_result['template'],
                            "is_custom": True,
                            "last_modified": custom_result['modified_at'],
                            "modified_by": custom_result['modified_by'],
                            "version": custom_result['version'],
                            "source": "postgresql_custom",
                            "notes": custom_result['notes']
                        }
                    else:
                        # Buscar default prompt (por defecto)
                        cursor.execute("""
                            SELECT template, description, category, updated_at
                            FROM default_prompts 
                            WHERE company_id = %s AND agent_name = %s
                        """, (company_id, agent_name))
                        
                        default_result = cursor.fetchone()
                        
                        if default_result:
                            # Tiene prompt por defecto
                            agents_data[agent_name] = {
                                "current_prompt": default_result['template'],
                                "is_custom": False,
                                "last_modified": default_result['updated_at'],
                                "version": 1,
                                "source": "postgresql_default",
                                "description": default_result['description'],
                                "category": default_result['category']
                            }
                        else:
                            # No tiene ni custom ni default - usar hardcoded
                            hardcoded_prompt = self._hardcoded_prompts.get(agent_name)
                            if hardcoded_prompt:
                                agents_data[agent_name] = {
                                    "current_prompt": hardcoded_prompt,
                                    "is_custom": False,
                                    "last_modified": None,
                                    "version": 0,
                                    "source": "hardcoded_fallback"
                                }
            
            logger.debug(f"Retrieved prompts for {company_id}: {len(agents_data)} agents")
            return agents_data
            
        except Exception as e:
            logger.error(f"Error getting company prompts for {company_id}: {e}")
            # Fallback a JSON en caso de error
            return self._get_prompts_from_json_fallback(company_id, agents)
        finally:
            conn.close()
    
    def _get_prompts_from_json_fallback(self, company_id: str, agents: List[str]) -> Optional[Dict[str, Dict]]:
        """Fallback a custom_prompts.json para compatibilidad temporal"""
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
            agents_data = {}
            
            for agent_name in agents:
                agent_data = company_prompts.get(agent_name, {})
                
                if isinstance(agent_data, dict):
                    # Priorizar template personalizado, luego default_template
                    template = agent_data.get('template')
                    if not template or template == "null":
                        template = agent_data.get('default_template') or self._hardcoded_prompts.get(agent_name)
                    
                    agents_data[agent_name] = {
                        "current_prompt": template,
                        "is_custom": agent_data.get('is_custom', False),
                        "last_modified": agent_data.get('modified_at'),
                        "version": 1,
                        "source": "json_file",
                        "fallback_level": "json_compatibility"
                    }
                else:
                    agents_data[agent_name] = {
                        "current_prompt": self._hardcoded_prompts.get(agent_name, f"Default prompt for {agent_name}"),
                        "is_custom": False,
                        "last_modified": None,
                        "version": 0,
                        "source": "hardcoded",
                        "fallback_level": "json_hardcoded"
                    }
            
            return agents_data
            
        except Exception as e:
            logger.error(f"Error reading JSON prompts: {e}")
            return None
    
    def _save_prompt_to_json(self, company_id: str, agent_name: str, template: str, modified_by: str) -> bool:
        """Fallback para guardar en JSON"""
        try:
            custom_prompts_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                'custom_prompts.json'
            )
            
            # Cargar o crear estructura
            if os.path.exists(custom_prompts_file):
                with open(custom_prompts_file, 'r', encoding='utf-8') as f:
                    custom_prompts = json.load(f)
            else:
                custom_prompts = {}
            
            # Asegurar estructura
            if company_id not in custom_prompts:
                custom_prompts[company_id] = {}
            
            if agent_name not in custom_prompts[company_id]:
                custom_prompts[company_id][agent_name] = {}
            
            # Actualizar
            custom_prompts[company_id][agent_name].update({
                "template": template,
                "is_custom": True,
                "modified_at": datetime.utcnow().isoformat() + "Z",
                "modified_by": modified_by
            })
            
            # Guardar
            with open(custom_prompts_file, 'w', encoding='utf-8') as f:
                json.dump(custom_prompts, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Prompt saved to JSON fallback for {company_id}/{agent_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving prompt to JSON: {e}")
            return False
    
    def _restore_prompt_in_json(self, company_id: str, agent_name: str) -> bool:
        """Fallback para restaurar en JSON"""
        try:
            custom_prompts_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                'custom_prompts.json'
            )
            
            if not os.path.exists(custom_prompts_file):
                return True  # No hay archivo, ya está "restaurado"
            
            with open(custom_prompts_file, 'r', encoding='utf-8') as f:
                custom_prompts = json.load(f)
            
            # Limpiar prompt personalizado
            if (company_id in custom_prompts and 
                agent_name in custom_prompts[company_id]):
                custom_prompts[company_id][agent_name].update({
                    "template": None,
                    "is_custom": False,
                    "modified_at": datetime.utcnow().isoformat() + "Z",
                    "modified_by": "system_restore"
                })
            
            with open(custom_prompts_file, 'w', encoding='utf-8') as f:
                json.dump(custom_prompts, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Prompt restored in JSON fallback for {company_id}/{agent_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring prompt in JSON: {e}")
            return False
    
    def _repair_from_hardcoded(self, company_id: str, agent_name: str = None, repair_user: str = "system_repair") -> bool:
        """Fallback para reparar usando prompts hardcodeados"""
        try:
            agents_to_repair = [agent_name] if agent_name else list(self._hardcoded_prompts.keys())
            
            for agent in agents_to_repair:
                if agent in self._hardcoded_prompts:
                    success = self.save_custom_prompt(
                        company_id, 
                        agent, 
                        self._hardcoded_prompts[agent], 
                        repair_user
                    )
                    
                    self.repair_summary.append({
                        "agent_name": agent,
                        "action": "REPAIR_HARDCODED",
                        "success": success,
                        "message": "Repaired from hardcoded fallback" if success else "Failed to repair"
                    })
            
            success_count = sum(1 for item in self.repair_summary if item['success'])
            logger.info(f"Hardcoded repair completed: {success_count}/{len(agents_to_repair)} agents")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error in hardcoded repair: {e}")
            return False
    
    def get_current_version(self, company_id: str, agent_name: str) -> int:
        """Obtener versión actual de un prompt"""
        conn = self.get_db_connection()
        if not conn:
            return 1  # Versión por defecto
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT version FROM custom_prompts 
                    WHERE company_id = %s AND agent_name = %s AND is_active = true
                """, (company_id, agent_name))
                
                result = cursor.fetchone()
                return result['version'] if result else 1
                
        except Exception as e:
            logger.error(f"Error getting version: {e}")
            return 1
        finally:
            conn.close()
    
    def get_repair_summary(self) -> List[Dict[str, Any]]:
        """Obtener resumen de la última operación de reparación"""
        return self.repair_summary
    
    def get_db_status(self) -> Dict[str, Any]:
        """Obtener estado de la base de datos"""
        try:
            conn = self.get_db_connection()
            if not conn:
                self._db_status = "failed"
                return {
                    "postgresql_available": False,
                    "connection_status": "failed",
                    "tables_exist": False,
                    "fallback_mode": "json_or_hardcoded"
                }
            
            with conn.cursor() as cursor:
                # Verificar que las tablas existen
                cursor.execute("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('custom_prompts', 'prompt_versions', 'default_prompts')
                """)
                
                tables = [row['table_name'] for row in cursor.fetchall()]
                all_tables_exist = len(tables) == 3
                
                # Contar registros
                total_custom = 0
                total_defaults = 0
                
                if 'custom_prompts' in tables:
                    cursor.execute("SELECT COUNT(*) as count FROM custom_prompts WHERE is_active = true")
                    total_custom = cursor.fetchone()['count']
                
                if 'default_prompts' in tables:
                    cursor.execute("SELECT COUNT(*) as count FROM default_prompts")
                    total_defaults = cursor.fetchone()['count']
                
                self._db_status = "connected"
                return {
                    "postgresql_available": True,
                    "connection_status": "connected",
                    "tables_exist": all_tables_exist,
                    "tables_found": tables,
                    "total_custom_prompts": total_custom,
                    "total_default_prompts": total_defaults,
                    "fallback_mode": "none"
                }
                
        except Exception as e:
            logger.error(f"Error checking DB status: {e}")
            self._db_status = f"error: {str(e)}"
            return {
                "postgresql_available": False,
                "connection_status": "error",
                "error": str(e),
                "fallback_mode": "json_or_hardcoded"
            }
        finally:
            if 'conn' in locals():
                conn.close()
    
    def migrate_from_json(self) -> Dict[str, Any]:
        """
        Migrar datos existentes de custom_prompts.json a PostgreSQL
        
        Returns:
            Dict con estadísticas de migración
        """
        migration_stats = {
            "companies_migrated": 0,
            "prompts_migrated": 0,
            "errors": [],
            "success": False
        }
        
        try:
            # Leer archivo JSON existente
            custom_prompts_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                'custom_prompts.json'
            )
            
            if not os.path.exists(custom_prompts_file):
                migration_stats["errors"].append("custom_prompts.json not found")
                return migration_stats
            
            with open(custom_prompts_file, 'r', encoding='utf-8') as f:
                custom_prompts = json.load(f)
            
            conn = self.get_db_connection()
            if not conn:
                migration_stats["errors"].append("PostgreSQL connection failed")
                return migration_stats
            
            # Migrar datos
            with conn.cursor() as cursor:
                for company_id, company_data in custom_prompts.items():
                    try:
                        migration_stats["companies_migrated"] += 1
                        
                        for agent_name, agent_data in company_data.items():
                            if isinstance(agent_data, dict) and agent_data.get('is_custom', False):
                                template = agent_data.get('template')
                                modified_by = agent_data.get('modified_by', 'migration')
                                
                                if template:
                                    cursor.execute("""
                                        INSERT INTO custom_prompts (company_id, agent_name, template, created_by, modified_by, notes)
                                        VALUES (%s, %s, %s, %s, %s, %s)
                                        ON CONFLICT (company_id, agent_name) DO NOTHING
                                    """, (company_id, agent_name, template, 'migration', modified_by, 'Migrated from JSON'))
                                    
                                    migration_stats["prompts_migrated"] += 1
                    
                    except Exception as e:
                        migration_stats["errors"].append(f"Error migrating {company_id}: {str(e)}")
                
                conn.commit()
                migration_stats["success"] = True
                logger.info(f"Migration completed: {migration_stats['prompts_migrated']} prompts from {migration_stats['companies_migrated']} companies")
                
        except Exception as e:
            migration_stats["errors"].append(f"Migration failed: {str(e)}")
            logger.error(f"Migration error: {e}")
            if 'conn' in locals():
                conn.rollback()
        finally:
            if 'conn' in locals():
                conn.close()
        
        return migration_stats
    
    def get_default_prompt_by_company_agent(self, company_id: str, agent_name: str) -> Optional[str]:
        """Obtener prompt por defecto específico para empresa + agente (ARQUITECTURA SEPARADA)"""
        conn = self.get_db_connection()
        if not conn:
            return None
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # ✅ CORREGIDO: Buscar por company_id + agent_name separados
                cursor.execute(
                    "SELECT template FROM default_prompts WHERE company_id = %s AND agent_name = %s",
                    (company_id, agent_name)
                )
                
                result = cursor.fetchone()
                if result:
                    logger.debug(f"Found default prompt for {company_id}/{agent_name}")
                    return result['template']
                
                logger.debug(f"No default prompt found for {company_id}/{agent_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting default prompt for {company_id}/{agent_name}: {e}")
            return None
        finally:
            conn.close()


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

_prompt_service_instance = None

def get_prompt_service() -> PromptService:
    """Factory function para obtener instancia singleton del servicio"""
    global _prompt_service_instance
    
    if _prompt_service_instance is None:
        _prompt_service_instance = PromptService()
    
    return _prompt_service_instance

def init_prompt_service(db_connection_string: str = None) -> PromptService:
    """Inicializar servicio de prompts con configuración específica"""
    global _prompt_service_instance
    _prompt_service_instance = PromptService(db_connection_string)
    return _prompt_service_instance
