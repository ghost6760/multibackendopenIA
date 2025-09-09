# app/services/prompt_service.py - Fixed version
import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
from typing import Optional, Dict, List, Any
from datetime import datetime
from contextlib import contextmanager
import json

logger = logging.getLogger(__name__)

class PromptService:
    """Servicio para gestión de prompts personalizados en PostgreSQL"""
    
    def __init__(self):
        self.pool = None
        self._initialize_connection_pool()
    
    def _initialize_connection_pool(self):
        """Inicializar pool de conexiones a PostgreSQL"""
        try:
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                raise Exception("DATABASE_URL environment variable is required")
            
            self.pool = ThreadedConnectionPool(
                minconn=2,
                maxconn=10,
                dsn=database_url
            )
            logger.info("PostgreSQL connection pool initialized")
            
            # Test connection and create tables if needed
            self._ensure_tables_exist()
            
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise

    def _ensure_tables_exist(self):
        """Ensure database tables exist"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Check if custom_prompts table exists
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = 'custom_prompts'
                        );
                    """)
                    
                    table_exists = cursor.fetchone()[0]
                    if not table_exists:
                        logger.warning("custom_prompts table does not exist. Please run migration script.")
                        raise Exception("Database tables not found. Run migration script first.")
                    
                    logger.info("Database tables verified")
                    
        except Exception as e:
            logger.error(f"Database table verification failed: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """Context manager para obtener conexión del pool"""
        conn = None
        try:
            conn = self.pool.getconn()
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                self.pool.putconn(conn)

    def get_prompt(self, company_id: str, agent_name: str) -> Dict[str, Any]:
        """Obtener prompt para empresa y agente específico"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Buscar prompt personalizado activo
                    cursor.execute("""
                        SELECT template, version, modified_at, modified_by, true as is_custom
                        FROM custom_prompts 
                        WHERE company_id = %s AND agent_name = %s AND is_active = true
                    """, (company_id, agent_name))
                    
                    custom_prompt = cursor.fetchone()
                    
                    if custom_prompt:
                        return {
                            'template': custom_prompt['template'],
                            'is_custom': True,
                            'version': custom_prompt['version'],
                            'modified_at': custom_prompt['modified_at'].isoformat() + 'Z',
                            'modified_by': custom_prompt['modified_by']
                        }
                    
                    # Si no hay personalizado, buscar default
                    cursor.execute("""
                        SELECT template, description
                        FROM default_prompts 
                        WHERE agent_name = %s
                    """, (agent_name,))
                    
                    default_prompt = cursor.fetchone()
                    
                    if default_prompt:
                        return {
                            'template': default_prompt['template'],
                            'is_custom': False,
                            'version': 1,
                            'modified_at': None,
                            'modified_by': None,
                            'default_template': default_prompt['template']
                        }
                    
                    # Si no existe ni personalizado ni default, return None
                    return {
                        'template': None,
                        'is_custom': False,
                        'version': 1,
                        'modified_at': None,
                        'modified_by': None,
                        'default_template': None
                    }
                    
        except Exception as e:
            logger.error(f"Error getting prompt for {company_id}/{agent_name}: {e}")
            # Return a basic fallback response
            return {
                'template': None,
                'is_custom': False,
                'version': 1,
                'modified_at': None,
                'modified_by': None,
                'default_template': None
            }

    def save_custom_prompt(self, company_id: str, agent_name: str, 
                          template: str, modified_by: str = "admin") -> bool:
        """Guardar prompt personalizado"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Verificar si ya existe un prompt personalizado
                    cursor.execute("""
                        SELECT id, version FROM custom_prompts 
                        WHERE company_id = %s AND agent_name = %s AND is_active = true
                    """, (company_id, agent_name))
                    
                    existing = cursor.fetchone()
                    
                    if existing:
                        # Actualizar prompt existente
                        prompt_id, current_version = existing
                        new_version = current_version + 1
                        
                        cursor.execute("""
                            UPDATE custom_prompts 
                            SET template = %s, version = %s, modified_by = %s, modified_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                        """, (template, new_version, modified_by, prompt_id))
                        
                        logger.info(f"Updated custom prompt for {company_id}/{agent_name} (version {new_version})")
                    else:
                        # Crear nuevo prompt personalizado
                        cursor.execute("""
                            INSERT INTO custom_prompts (
                                company_id, agent_name, template, 
                                created_by, modified_by
                            ) VALUES (%s, %s, %s, %s, %s)
                        """, (company_id, agent_name, template, modified_by, modified_by))
                        
                        logger.info(f"Created new custom prompt for {company_id}/{agent_name}")
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            logger.error(f"Error saving custom prompt: {e}")
            return False

    def delete_custom_prompt(self, company_id: str, agent_name: str, 
                           deleted_by: str = "admin") -> bool:
        """Eliminar prompt personalizado (soft delete)"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE custom_prompts 
                        SET is_active = false, modified_by = %s, modified_at = CURRENT_TIMESTAMP
                        WHERE company_id = %s AND agent_name = %s AND is_active = true
                    """, (deleted_by, company_id, agent_name))
                    
                    if cursor.rowcount > 0:
                        conn.commit()
                        logger.info(f"Deleted custom prompt for {company_id}/{agent_name}")
                        return True
                    else:
                        logger.warning(f"No custom prompt found to delete for {company_id}/{agent_name}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error deleting custom prompt: {e}")
            return False

    def restore_default_prompt(self, company_id: str, agent_name: str) -> bool:
        """Restaurar prompt por defecto eliminando customización"""
        return self.delete_custom_prompt(company_id, agent_name)

    def get_company_prompts(self, company_id: str) -> List[Dict[str, Any]]:
        """Obtener todos los prompts de una empresa"""
        agents = ['router_agent', 'sales_agent', 'support_agent', 'emergency_agent', 'schedule_agent']
        prompts = []
        
        for agent_name in agents:
            prompt_data = self.get_prompt(company_id, agent_name)
            prompts.append({
                'agent_name': agent_name,
                **prompt_data
            })
        
        return prompts

    def has_custom_prompt(self, company_id: str, agent_name: str) -> bool:
        """Verificar si existe prompt personalizado"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT 1 FROM custom_prompts 
                        WHERE company_id = %s AND agent_name = %s AND is_active = true
                    """, (company_id, agent_name))
                    
                    return cursor.fetchone() is not None
                    
        except Exception as e:
            logger.error(f"Error checking custom prompt: {e}")
            return False

    def get_modification_date(self, company_id: str, agent_name: str) -> Optional[str]:
        """Obtener fecha de modificación"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT modified_at FROM custom_prompts 
                        WHERE company_id = %s AND agent_name = %s AND is_active = true
                    """, (company_id, agent_name))
                    
                    result = cursor.fetchone()
                    if result and result[0]:
                        return result[0].isoformat() + 'Z'
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting modification date: {e}")
            return None

    def preview_prompt(self, template: str, company_config: dict) -> str:
        """Preview prompt with company data"""
        try:
            # Simple template replacement
            company_name = company_config.get('name', 'Your Company')
            
            # Replace common placeholders
            preview = template.replace('{company_name}', company_name)
            preview = preview.replace('{company_id}', company_config.get('id', 'company'))
            
            return preview
            
        except Exception as e:
            logger.error(f"Error previewing prompt: {e}")
            return template

    def close(self):
        """Cerrar pool de conexiones"""
        if self.pool:
            self.pool.closeall()
            logger.info("PostgreSQL connection pool closed")

# ============================================================================
# INSTANCIA GLOBAL DEL SERVICIO
# ============================================================================

_prompt_service = None

def get_prompt_service() -> PromptService:
    """Obtener instancia del servicio de prompts"""
    global _prompt_service
    if _prompt_service is None:
        _prompt_service = PromptService()
    return _prompt_service

# ============================================================================
# FUNCIONES DE COMPATIBILIDAD 
# ============================================================================

def _has_custom_prompt(company_id: str, agent_name: str) -> bool:
    """Función de compatibilidad"""
    return get_prompt_service().has_custom_prompt(company_id, agent_name)

def _get_prompt_modification_date(company_id: str, agent_name: str) -> Optional[str]:
    """Función de compatibilidad"""
    return get_prompt_service().get_modification_date(company_id, agent_name)

def _save_custom_prompt(company_id: str, agent_name: str, 
                       prompt_template: str, modified_by: str = "admin") -> bool:
    """Función de compatibilidad"""
    return get_prompt_service().save_custom_prompt(
        company_id, agent_name, prompt_template, modified_by
    )

def _delete_custom_prompt(company_id: str, agent_name: str) -> bool:
    """Función de compatibilidad"""
    return get_prompt_service().delete_custom_prompt(company_id, agent_name)
