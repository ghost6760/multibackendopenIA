# ============================================================================
# SERVICIO DE PROMPTS PERSONALIZADOS CON POSTGRESQL
# Reemplaza el manejo actual con custom_prompts.json
# ============================================================================

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
                # Configuración local para desarrollo
                database_url = (
                    f"postgresql://{os.getenv('DB_USER', 'postgres')}:"
                    f"{os.getenv('DB_PASSWORD', 'password')}@"
                    f"{os.getenv('DB_HOST', 'localhost')}:"
                    f"{os.getenv('DB_PORT', '5432')}/"
                    f"{os.getenv('DB_NAME', 'prompts_db')}"
                )
            
            self.pool = ThreadedConnectionPool(
                minconn=2,
                maxconn=10,
                dsn=database_url
            )
            logger.info("PostgreSQL connection pool initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
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
        """
        Obtener prompt para empresa y agente específico
        Retorna la misma estructura que antes para mantener compatibilidad
        """
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
                    
                    # Si no existe ni personalizado ni default
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
                            SET template = %s, version = %s, modified_by = %s
                            WHERE id = %s
                        """, (template, new_version, modified_by, prompt_id))
                    else:
                        # Crear nuevo prompt personalizado
                        cursor.execute("""
                            INSERT INTO custom_prompts (
                                company_id, agent_name, template, 
                                created_by, modified_by
                            ) VALUES (%s, %s, %s, %s, %s)
                        """, (company_id, agent_name, template, modified_by, modified_by))
                    
                    conn.commit()
                    logger.info(f"Custom prompt saved for {company_id}/{agent_name}")
                    return True
                    
        except Exception as e:
            logger.error(f"Error saving custom prompt: {e}")
            return False

    def delete_custom_prompt(self, company_id: str, agent_name: str) -> bool:
        """Eliminar prompt personalizado (restaurar a default)"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Marcar como inactivo en lugar de eliminar (soft delete)
                    cursor.execute("""
                        UPDATE custom_prompts 
                        SET is_active = false, modified_by = 'system_reset'
                        WHERE company_id = %s AND agent_name = %s AND is_active = true
                    """, (company_id, agent_name))
                    
                    # Crear entrada en historial
                    cursor.execute("""
                        INSERT INTO prompt_versions (
                            prompt_id, company_id, agent_name, template, 
                            version, action, created_by, notes
                        ) 
                        SELECT id, company_id, agent_name, template, 
                               version, 'DELETE', 'system_reset', 'Prompt restaurado a default'
                        FROM custom_prompts 
                        WHERE company_id = %s AND agent_name = %s AND is_active = false
                        ORDER BY modified_at DESC LIMIT 1
                    """, (company_id, agent_name))
                    
                    conn.commit()
                    logger.info(f"Custom prompt deleted for {company_id}/{agent_name}")
                    return True
                    
        except Exception as e:
            logger.error(f"Error deleting custom prompt: {e}")
            return False

    def get_company_prompts(self, company_id: str) -> List[Dict[str, Any]]:
        """Obtener todos los prompts de una empresa"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT ap.agent_name, ap.template, ap.is_custom, 
                               ap.version, ap.modified_at, ap.modified_by
                        FROM active_prompts ap
                        WHERE ap.company_id = %s OR ap.company_id = 'default'
                        ORDER BY ap.agent_name
                    """, (company_id,))
                    
                    prompts = []
                    for row in cursor.fetchall():
                        prompt_data = dict(row)
                        if prompt_data['modified_at']:
                            prompt_data['modified_at'] = prompt_data['modified_at'].isoformat() + 'Z'
                        prompts.append(prompt_data)
                    
                    return prompts
                    
        except Exception as e:
            logger.error(f"Error getting company prompts: {e}")
            return []

    def get_prompt_history(self, company_id: str, agent_name: str) -> List[Dict[str, Any]]:
        """Obtener historial de versiones de un prompt"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT version, action, created_at, created_by, notes,
                               LEFT(template, 100) as template_preview
                        FROM prompt_versions 
                        WHERE company_id = %s AND agent_name = %s
                        ORDER BY created_at DESC
                        LIMIT 50
                    """, (company_id, agent_name))
                    
                    history = []
                    for row in cursor.fetchall():
                        history_item = dict(row)
                        history_item['created_at'] = row['created_at'].isoformat() + 'Z'
                        history.append(history_item)
                    
                    return history
                    
        except Exception as e:
            logger.error(f"Error getting prompt history: {e}")
            return []

    def restore_prompt_version(self, company_id: str, agent_name: str, 
                              version: int, modified_by: str = "admin") -> bool:
        """Restaurar una versión específica del prompt"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Obtener template de la versión específica
                    cursor.execute("""
                        SELECT template FROM prompt_versions 
                        WHERE company_id = %s AND agent_name = %s AND version = %s
                        ORDER BY created_at DESC LIMIT 1
                    """, (company_id, agent_name, version))
                    
                    version_data = cursor.fetchone()
                    if not version_data:
                        logger.warning(f"Version {version} not found for {company_id}/{agent_name}")
                        return False
                    
                    template = version_data[0]
                    
                    # Guardar como nueva versión
                    return self.save_custom_prompt(company_id, agent_name, template, modified_by)
                    
        except Exception as e:
            logger.error(f"Error restoring prompt version: {e}")
            return False

    def has_custom_prompt(self, company_id: str, agent_name: str) -> bool:
        """Verificar si existe prompt personalizado"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT EXISTS(
                            SELECT 1 FROM custom_prompts 
                            WHERE company_id = %s AND agent_name = %s AND is_active = true
                        )
                    """, (company_id, agent_name))
                    
                    return cursor.fetchone()[0]
                    
        except Exception as e:
            logger.error(f"Error checking custom prompt: {e}")
            return False

    def get_modification_date(self, company_id: str, agent_name: str) -> Optional[str]:
        """Obtener fecha de modificación del prompt"""
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

    def close(self):
        """Cerrar pool de conexiones"""
        if self.pool:
            self.pool.closeall()
            logger.info("PostgreSQL connection pool closed")

# ============================================================================
# INSTANCIA GLOBAL DEL SERVICIO
# ============================================================================

# Singleton para evitar múltiples pools de conexión
_prompt_service = None

def get_prompt_service() -> PromptService:
    """Obtener instancia del servicio de prompts"""
    global _prompt_service
    if _prompt_service is None:
        _prompt_service = PromptService()
    return _prompt_service

# ============================================================================
# FUNCIONES DE COMPATIBILIDAD (mantienen la API actual)
# ============================================================================

def _has_custom_prompt(company_id: str, agent_name: str) -> bool:
    """Función de compatibilidad con el código actual"""
    return get_prompt_service().has_custom_prompt(company_id, agent_name)

def _get_prompt_modification_date(company_id: str, agent_name: str) -> Optional[str]:
    """Función de compatibilidad con el código actual"""
    return get_prompt_service().get_modification_date(company_id, agent_name)

def _save_custom_prompt(company_id: str, agent_name: str, 
                       prompt_template: str, modified_by: str = "admin") -> bool:
    """Función de compatibilidad con el código actual"""
    return get_prompt_service().save_custom_prompt(
        company_id, agent_name, prompt_template, modified_by
    )

def _delete_custom_prompt(company_id: str, agent_name: str) -> bool:
    """Función de compatibilidad con el código actual"""
    return get_prompt_service().delete_custom_prompt(company_id, agent_name)
