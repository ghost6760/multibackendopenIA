# app/services/prompt_service.py
# Servicio MINIMALISTA para gestión de prompts estructurados (JSONB puro)
# SIN compatibilidad legacy - Solo LangGraph

import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor, Json

logger = logging.getLogger(__name__)


class PromptService:
    """
    Servicio minimalista para prompts estructurados.
    
    Principios:
    - NO transforma ni normaliza contenido
    - Devuelve JSONB exacto de la base de datos
    - Falla rápido si no encuentra prompt (no fallbacks automáticos)
    - Versionado automático
    """
    
    def __init__(self, db_connection_string: str = None):
        """
        Inicializar servicio de prompts.
        
        Args:
            db_connection_string: String de conexión PostgreSQL
        """
        self.db_connection_string = db_connection_string or os.getenv('DATABASE_URL')
        
        if not self.db_connection_string:
            raise RuntimeError(
                "PromptService requires DATABASE_URL. "
                "Set environment variable or pass connection string."
            )
        
        logger.info("PromptService initialized (LangGraph mode - no legacy support)")
    
    def _get_connection(self) -> psycopg2.extensions.connection:
        """
        Obtener conexión a PostgreSQL.
        
        Raises:
            RuntimeError: Si no puede conectar
        """
        try:
            return psycopg2.connect(
                self.db_connection_string,
                cursor_factory=RealDictCursor
            )
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise RuntimeError(f"Database connection failed: {e}") from e
    
    # ========================================================================
    # CORE METHODS
    # ========================================================================
    
    def get_prompt_payload(
        self, 
        company_id: int, 
        agent_key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Obtener payload estructurado de prompt.
        
        Devuelve el JSONB almacenado sin modificaciones.
        NO hace fallbacks automáticos - devuelve None si no existe.
        
        Args:
            company_id: ID de la empresa
            agent_key: Key del agente (ej. 'sales_agent')
        
        Returns:
            Dict con estructura JSONB exacta o None si no existe
            Estructura esperada:
            {
                'system': str,
                'examples': List[Dict],
                'placeholders': Dict,
                'meta': Dict
            }
        """
        conn = self._get_connection()
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        id,
                        structured_template,
                        version,
                        is_active,
                        created_by,
                        modified_by,
                        created_at,
                        modified_at
                    FROM prompt_catalog
                    WHERE company_id = %s 
                      AND agent_key = %s 
                      AND is_active = true
                    LIMIT 1
                """, (company_id, agent_key))
                
                result = cursor.fetchone()
                
                if not result:
                    logger.info(
                        f"No prompt found for company_id={company_id}, "
                        f"agent_key={agent_key}"
                    )
                    return None
                
                payload = result['structured_template']
                
                logger.debug(
                    f"Loaded prompt: company_id={company_id}, "
                    f"agent_key={agent_key}, version={result['version']}, "
                    f"modified_by={result['modified_by']}"
                )
                
                # Devolver JSONB exacto sin transformaciones
                return payload
                
        except Exception as e:
            logger.error(
                f"Error fetching prompt payload: company_id={company_id}, "
                f"agent_key={agent_key}, error={e}",
                exc_info=True
            )
            raise
        finally:
            conn.close()
    
    def save_prompt_payload(
        self,
        company_id: int,
        agent_key: str,
        structured_template: Dict[str, Any],
        author: str,
        change_reason: Optional[str] = None
    ) -> bool:
        """
        Guardar nuevo prompt payload (crea versión nueva).
        
        Guarda el JSONB exacto sin validar ni transformar contenido.
        Incrementa automáticamente la versión.
        
        Args:
            company_id: ID de la empresa
            agent_key: Key del agente
            structured_template: JSONB con estructura del prompt
            author: Usuario que crea/modifica
            change_reason: Razón del cambio (opcional)
        
        Returns:
            bool: True si se guardó exitosamente
        
        Raises:
            RuntimeError: Si falla la operación
        """
        conn = self._get_connection()
        
        try:
            with conn.cursor() as cursor:
                # 1. Obtener versión actual
                cursor.execute("""
                    SELECT version, id
                    FROM prompt_catalog
                    WHERE company_id = %s 
                      AND agent_key = %s 
                      AND is_active = true
                """, (company_id, agent_key))
                
                current = cursor.fetchone()
                
                if current:
                    # UPDATE: Desactivar versión actual y crear nueva
                    old_version = current['version']
                    old_id = current['id']
                    new_version = old_version + 1
                    
                    # Desactivar versión anterior
                    cursor.execute("""
                        UPDATE prompt_catalog
                        SET is_active = false,
                            modified_at = CURRENT_TIMESTAMP,
                            modified_by = %s
                        WHERE id = %s
                    """, (author, old_id))
                    
                    # Guardar en historial
                    cursor.execute("""
                        INSERT INTO prompt_history (
                            prompt_catalog_id,
                            structured_template,
                            version,
                            changed_by,
                            changed_at,
                            change_reason
                        ) VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
                    """, (
                        old_id,
                        Json(structured_template),
                        old_version,
                        author,
                        change_reason
                    ))
                    
                    logger.info(
                        f"Deactivated prompt v{old_version}: "
                        f"company_id={company_id}, agent_key={agent_key}"
                    )
                else:
                    # INSERT: Primera versión
                    new_version = 1
                    logger.info(
                        f"Creating first prompt version: "
                        f"company_id={company_id}, agent_key={agent_key}"
                    )
                
                # Insertar nueva versión
                cursor.execute("""
                    INSERT INTO prompt_catalog (
                        company_id,
                        agent_key,
                        structured_template,
                        version,
                        is_active,
                        created_by,
                        modified_by,
                        created_at,
                        modified_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, 
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                    RETURNING id
                """, (
                    company_id,
                    agent_key,
                    Json(structured_template),
                    new_version,
                    True,
                    author,
                    author
                ))
                
                new_id = cursor.fetchone()['id']
                
                conn.commit()
                
                logger.info(
                    f"✅ Saved prompt v{new_version}: "
                    f"company_id={company_id}, agent_key={agent_key}, "
                    f"id={new_id}, author={author}"
                )
                
                return True
                
        except Exception as e:
            logger.error(
                f"Error saving prompt: company_id={company_id}, "
                f"agent_key={agent_key}, error={e}",
                exc_info=True
            )
            conn.rollback()
            raise RuntimeError(f"Failed to save prompt: {e}") from e
        finally:
            conn.close()
    
    def list_prompt_versions(
        self,
        company_id: int,
        agent_key: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Listar versiones de un prompt (metadatos, no contenido).
        
        Args:
            company_id: ID de la empresa
            agent_key: Key del agente
            limit: Máximo número de versiones a retornar
        
        Returns:
            Lista de metadatos de versiones ordenadas por versión DESC
        """
        conn = self._get_connection()
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        id,
                        version,
                        is_active,
                        created_by,
                        modified_by,
                        created_at,
                        modified_at
                    FROM prompt_catalog
                    WHERE company_id = %s AND agent_key = %s
                    ORDER BY version DESC
                    LIMIT %s
                """, (company_id, agent_key, limit))
                
                results = cursor.fetchall()
                
                versions = []
                for row in results:
                    versions.append({
                        'id': row['id'],
                        'version': row['version'],
                        'is_active': row['is_active'],
                        'created_by': row['created_by'],
                        'modified_by': row['modified_by'],
                        'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                        'modified_at': row['modified_at'].isoformat() if row['modified_at'] else None
                    })
                
                return versions
                
        except Exception as e:
            logger.error(
                f"Error listing versions: company_id={company_id}, "
                f"agent_key={agent_key}, error={e}",
                exc_info=True
            )
            return []
        finally:
            conn.close()
    
    def activate_version(
        self,
        prompt_id: int,
        modified_by: str
    ) -> bool:
        """
        Activar una versión específica de prompt.
        
        Desactiva todas las otras versiones del mismo company_id/agent_key.
        
        Args:
            prompt_id: ID del prompt a activar
            modified_by: Usuario que realiza el cambio
        
        Returns:
            bool: True si se activó exitosamente
        """
        conn = self._get_connection()
        
        try:
            with conn.cursor() as cursor:
                # Obtener info del prompt
                cursor.execute("""
                    SELECT company_id, agent_key, version
                    FROM prompt_catalog
                    WHERE id = %s
                """, (prompt_id,))
                
                prompt_info = cursor.fetchone()
                
                if not prompt_info:
                    logger.warning(f"Prompt id={prompt_id} not found")
                    return False
                
                company_id = prompt_info['company_id']
                agent_key = prompt_info['agent_key']
                version = prompt_info['version']
                
                # Desactivar todas las versiones
                cursor.execute("""
                    UPDATE prompt_catalog
                    SET is_active = false,
                        modified_at = CURRENT_TIMESTAMP,
                        modified_by = %s
                    WHERE company_id = %s AND agent_key = %s
                """, (modified_by, company_id, agent_key))
                
                # Activar versión específica
                cursor.execute("""
                    UPDATE prompt_catalog
                    SET is_active = true,
                        modified_at = CURRENT_TIMESTAMP,
                        modified_by = %s
                    WHERE id = %s
                """, (modified_by, prompt_id))
                
                conn.commit()
                
                logger.info(
                    f"✅ Activated prompt v{version}: "
                    f"company_id={company_id}, agent_key={agent_key}, "
                    f"id={prompt_id}, by={modified_by}"
                )
                
                return True
                
        except Exception as e:
            logger.error(f"Error activating version: id={prompt_id}, error={e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def deactivate_version(
        self,
        prompt_id: int,
        modified_by: str
    ) -> bool:
        """
        Desactivar una versión específica de prompt.
        
        Args:
            prompt_id: ID del prompt a desactivar
            modified_by: Usuario que realiza el cambio
        
        Returns:
            bool: True si se desactivó exitosamente
        """
        conn = self._get_connection()
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE prompt_catalog
                    SET is_active = false,
                        modified_at = CURRENT_TIMESTAMP,
                        modified_by = %s
                    WHERE id = %s
                """, (modified_by, prompt_id))
                
                conn.commit()
                
                logger.info(f"✅ Deactivated prompt: id={prompt_id}, by={modified_by}")
                return True
                
        except Exception as e:
            logger.error(f"Error deactivating version: id={prompt_id}, error={e}")
            conn.rollback()
            return False
        finally:
            conn.close()


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

_prompt_service_instance: Optional[PromptService] = None


def get_prompt_service() -> PromptService:
    """Obtener instancia singleton del servicio."""
    global _prompt_service_instance
    
    if _prompt_service_instance is None:
        _prompt_service_instance = PromptService()
    
    return _prompt_service_instance


def init_prompt_service(db_connection_string: str) -> PromptService:
    """
    Inicializar servicio con configuración específica.
    
    Args:
        db_connection_string: String de conexión PostgreSQL
    
    Returns:
        Instancia de PromptService
    """
    global _prompt_service_instance
    _prompt_service_instance = PromptService(db_connection_string)
    return _prompt_service_instance
