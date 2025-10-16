# app/workflows/workflow_registry.py

from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
import os

from app.workflows.workflow_models import WorkflowGraph
from app.services.redis_service import get_redis_client

logger = logging.getLogger(__name__)

class WorkflowRegistry:
    """
    Registry de workflows con persistencia PostgreSQL + cache Redis.
    
    ✅ Similar a PromptService (misma arquitectura)
    ✅ PostgreSQL como source of truth (psycopg2 directo)
    ✅ Redis para cache y performance
    ✅ Multi-tenant (por company_id)
    ✅ Versionado de workflows
    """
    
    def __init__(self):
        self.redis_client = get_redis_client()
        self.cache_ttl = 3600  # 1 hora
        self.db_url = os.getenv('DATABASE_URL')
        
        if not self.db_url:
            logger.warning("DATABASE_URL not configured - WorkflowRegistry will have limited functionality")
        
        logger.info("WorkflowRegistry initialized")
    
    def _get_connection(self):
        """Obtener conexión PostgreSQL"""
        if not self.db_url:
            raise ValueError("DATABASE_URL not configured")
        return psycopg2.connect(self.db_url)
    
    # === WORKFLOW CRUD === #
    
    def save_workflow(self, workflow: WorkflowGraph, created_by: str = "system") -> bool:
        """
        Guardar o actualizar workflow en PostgreSQL.
        
        Args:
            workflow: WorkflowGraph a guardar
            created_by: Usuario que crea/modifica
            
        Returns:
            True si éxito, False si error
        """
        try:
            # Validar workflow antes de guardar
            validation = workflow.validate()
            if validation["errors"]:
                logger.error(f"Cannot save invalid workflow {workflow.id}: {validation['errors']}")
                return False
            
            # Serializar a JSON
            workflow_json = workflow.to_json()
            
            # Verificar si ya existe
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM workflows WHERE workflow_id = %s", (workflow.id,))
            exists = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if exists:
                # Update
                return self._update_in_database(workflow, workflow_json, created_by)
            else:
                # Insert
                return self._insert_in_database(workflow, workflow_json, created_by)
            
        except Exception as e:
            logger.exception(f"Error saving workflow {workflow.id}: {e}")
            return False
    
    def get_workflow(self, workflow_id: str, use_cache: bool = True) -> Optional[WorkflowGraph]:
        """
        Obtener workflow por ID.
        
        Flujo:
        1. Buscar en Redis (si use_cache=True)
        2. Buscar en PostgreSQL
        3. Guardar en Redis
        
        Args:
            workflow_id: ID del workflow
            use_cache: Si usar cache Redis
            
        Returns:
            WorkflowGraph o None si no existe
        """
        try:
            # 1. Intentar desde cache
            if use_cache:
                cached = self._get_from_cache(workflow_id)
                if cached:
                    logger.debug(f"Workflow {workflow_id} loaded from cache")
                    return cached
            
            # 2. Cargar desde PostgreSQL
            workflow = self._get_from_database(workflow_id)
            
            if workflow:
                # 3. Guardar en cache
                self._save_to_cache(workflow)
                logger.info(f"Workflow {workflow_id} loaded from PostgreSQL")
                return workflow
            
            logger.warning(f"Workflow {workflow_id} not found")
            return None
            
        except Exception as e:
            logger.exception(f"Error loading workflow {workflow_id}: {e}")
            return None
    
    def get_workflows_by_company(self, company_id: str, 
                                 enabled_only: bool = True) -> List[WorkflowGraph]:
        """
        Obtener todos los workflows de una empresa.
        
        Args:
            company_id: ID de la empresa
            enabled_only: Si solo retornar workflows habilitados
            
        Returns:
            Lista de WorkflowGraph
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT workflow_data 
                FROM workflows 
                WHERE company_id = %s
            """
            
            params = [company_id]
            
            if enabled_only:
                query += " AND enabled = true"
            
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            workflows = []
            for row in rows:
                try:
                    workflow_data = json.loads(row['workflow_data']) if isinstance(row['workflow_data'], str) else row['workflow_data']
                    workflow = WorkflowGraph.from_dict(workflow_data)
                    workflows.append(workflow)
                except Exception as e:
                    logger.error(f"Error parsing workflow: {e}")
            
            cursor.close()
            conn.close()
            
            logger.info(f"Loaded {len(workflows)} workflows for company {company_id}")
            return workflows
            
        except Exception as e:
            logger.exception(f"Error loading workflows for company {company_id}: {e}")
            return []
    
    def delete_workflow(self, workflow_id: str, deleted_by: str = "system") -> bool:
        """
        Eliminar workflow (soft delete).
        
        Args:
            workflow_id: ID del workflow
            deleted_by: Usuario que elimina
            
        Returns:
            True si éxito
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            query = """
                UPDATE workflows 
                SET enabled = false,
                    modified_at = NOW(),
                    modified_by = %s
                WHERE workflow_id = %s
            """
            
            cursor.execute(query, (deleted_by, workflow_id))
            conn.commit()
            
            cursor.close()
            conn.close()
            
            # Invalidar cache
            self._invalidate_cache(workflow_id)
            
            logger.info(f"Workflow {workflow_id} disabled by {deleted_by}")
            return True
            
        except Exception as e:
            logger.exception(f"Error deleting workflow {workflow_id}: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return False
    
    def find_workflow_by_trigger(self, company_id: str, 
                                trigger_data: Dict[str, Any]) -> Optional[WorkflowGraph]:
        """
        Encontrar workflow que matchee un trigger específico.
        
        Args:
            company_id: ID de la empresa
            trigger_data: Datos del trigger (ej: {"type": "keyword", "value": "botox"})
            
        Returns:
            Primer workflow que matchee o None
        """
        try:
            workflows = self.get_workflows_by_company(company_id, enabled_only=True)
            
            for workflow in workflows:
                if self._matches_trigger(workflow, trigger_data):
                    logger.info(f"Workflow {workflow.id} matches trigger")
                    return workflow
            
            logger.debug(f"No workflow found for trigger: {trigger_data}")
            return None
            
        except Exception as e:
            logger.exception(f"Error finding workflow by trigger: {e}")
            return None
    
    def _matches_trigger(self, workflow: WorkflowGraph, 
                        trigger_data: Dict[str, Any]) -> bool:
        """
        Verificar si workflow matchea un trigger.
        """
        for trigger in workflow.triggers:
            trigger_type = trigger.get("type")
            
            if trigger_type == "keyword":
                # Trigger por keyword
                keywords = trigger.get("keywords", [])
                value = trigger_data.get("value", "").lower()
                
                if any(kw.lower() in value for kw in keywords):
                    return True
            
            elif trigger_type == "webhook":
                # Trigger por webhook
                webhook_id = trigger.get("webhook_id")
                if webhook_id == trigger_data.get("webhook_id"):
                    return True
            
            elif trigger_type == "schedule":
                # Trigger por schedule (cron)
                # TODO: Implementar matching de cron
                pass
        
        return False
    
    # === DATABASE OPERATIONS === #
    
    def _insert_in_database(self, workflow: WorkflowGraph, 
                           workflow_json: str, created_by: str) -> bool:
        """Insertar workflow en PostgreSQL - CORREGIDO"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            query = """
                INSERT INTO workflows (
                    workflow_id, company_id, name, description,
                    workflow_data, enabled, version,
                    tags, triggers, variables, start_node_id,
                    total_nodes, total_edges,
                    execution_count, success_count, failure_count,
                    created_by, modified_by
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """
            
            # Convertir tags de lista Python a array PostgreSQL
            tags_array = workflow.tags if workflow.tags else []
            
            cursor.execute(query, (
                workflow.id,
                workflow.company_id,
                workflow.name,
                workflow.description,
                workflow_json,
                workflow.enabled,
                workflow.version,
                tags_array,  # PostgreSQL acepta lista Python para text[]
                '[]',  # triggers (JSONB vacío por ahora)
                '{}',  # variables (JSONB vacío por ahora)
                workflow.start_node_id,
                len(workflow.nodes),
                len(workflow.edges),
                0,  # execution_count
                0,  # success_count
                0,  # failure_count
                created_by,
                created_by  # modified_by = created_by en INSERT
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            # Invalidar cache
            self._invalidate_company_cache(workflow.company_id)
            
            logger.info(f"✅ Workflow {workflow.id} inserted successfully")
            return True
            
        except Exception as e:
            logger.exception(f"❌ Error inserting workflow {workflow.id}: {e}")
            if 'conn' in locals():
                try:
                    conn.rollback()
                    conn.close()
                except:
                    pass
            return False
    
    def _update_in_database(self, workflow: WorkflowGraph, 
                           workflow_json: str, updated_by: str) -> bool:
        """Actualizar workflow en PostgreSQL - CORREGIDO"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            query = """
                UPDATE workflows SET
                    name = %s,
                    description = %s,
                    workflow_data = %s,
                    enabled = %s,
                    version = %s,
                    tags = %s,
                    start_node_id = %s,
                    total_nodes = %s,
                    total_edges = %s,
                    modified_by = %s,
                    modified_at = CURRENT_TIMESTAMP
                WHERE workflow_id = %s
            """
            
            # Convertir tags de lista Python a array PostgreSQL
            tags_array = workflow.tags if workflow.tags else []
            
            cursor.execute(query, (
                workflow.name,
                workflow.description,
                workflow_json,
                workflow.enabled,
                workflow.version,
                tags_array,  # PostgreSQL acepta lista Python para text[]
                workflow.start_node_id,
                len(workflow.nodes),
                len(workflow.edges),
                updated_by,
                workflow.id
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            # Invalidar cache
            self._invalidate_cache(workflow.id)
            self._invalidate_company_cache(workflow.company_id)
            
            logger.info(f"✅ Workflow {workflow.id} updated successfully")
            return True
            
        except Exception as e:
            logger.exception(f"❌ Error updating workflow {workflow.id}: {e}")
            if 'conn' in locals():
                try:
                    conn.rollback()
                    conn.close()
                except:
                    pass
            return False
    
    def _get_from_database(self, workflow_id: str) -> Optional[WorkflowGraph]:
        """Cargar workflow desde PostgreSQL"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT workflow_data 
                FROM workflows 
                WHERE workflow_id = %s
            """
            
            cursor.execute(query, (workflow_id,))
            row = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if not row:
                return None
            
            workflow_data = json.loads(row['workflow_data']) if isinstance(row['workflow_data'], str) else row['workflow_data']
            return WorkflowGraph.from_dict(workflow_data)
            
        except Exception as e:
            logger.exception(f"Error loading workflow {workflow_id} from database: {e}")
            return None
    
    # === CACHE OPERATIONS === #
    
    def _get_from_cache(self, workflow_id: str) -> Optional[WorkflowGraph]:
        """Obtener workflow desde Redis cache"""
        try:
            cache_key = f"workflow:{workflow_id}"
            cached_json = self.redis_client.get(cache_key)
            
            if cached_json:
                workflow_data = json.loads(cached_json)
                return WorkflowGraph.from_dict(workflow_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error reading workflow {workflow_id} from cache: {e}")
            return None
    
    def _save_to_cache(self, workflow: WorkflowGraph):
        """Guardar workflow en Redis cache"""
        try:
            cache_key = f"workflow:{workflow.id}"
            workflow_json = workflow.to_json()
            
            self.redis_client.setex(
                cache_key,
                self.cache_ttl,
                workflow_json
            )
            
            logger.debug(f"Workflow {workflow.id} cached in Redis")
            
        except Exception as e:
            logger.error(f"Error caching workflow {workflow.id}: {e}")
    
    def _invalidate_cache(self, workflow_id: str):
        """Invalidar cache de un workflow"""
        try:
            cache_key = f"workflow:{workflow_id}"
            self.redis_client.delete(cache_key)
            
            logger.debug(f"Cache invalidated for workflow {workflow_id}")
            
        except Exception as e:
            logger.error(f"Error invalidating cache for {workflow_id}: {e}")
    
    def _invalidate_company_cache(self, company_id: str):
        """Invalidar cache de todos los workflows de una empresa"""
        try:
            # Buscar todas las keys de workflows de esta empresa
            pattern = f"workflow:*"
            
            # Redis SCAN para encontrar keys
            cursor = 0
            invalidated = 0
            
            while True:
                cursor, keys = self.redis_client.scan(cursor, match=pattern, count=100)
                
                for key in keys:
                    # Verificar si pertenece a la empresa (requiere cargar)
                    # Por performance, simplemente invalidar todas
                    self.redis_client.delete(key)
                    invalidated += 1
                
                if cursor == 0:
                    break
            
            if invalidated > 0:
                logger.info(f"Cache invalidated for {invalidated} workflows")
            
        except Exception as e:
            logger.error(f"Error invalidating company cache: {e}")
    
    # === EXECUTION LOGS === #
    
    def log_execution(self, workflow_id: str, execution_result: Dict[str, Any]) -> bool:
        """
        Registrar ejecución de workflow.
        
        Args:
            workflow_id: ID del workflow
            execution_result: Resultado de WorkflowExecutor.execute()
            
        Returns:
            True si éxito
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Generar execution_id
            import time
            execution_id = f"exec_{workflow_id}_{int(time.time())}"
            
            # Calcular duración
            started = datetime.fromisoformat(execution_result["started_at"])
            completed = datetime.fromisoformat(execution_result["completed_at"])
            duration_ms = int((completed - started).total_seconds() * 1000)
            
            query = """
                INSERT INTO workflow_executions (
                    execution_id, workflow_id, company_id, status,
                    context, execution_history, errors,
                    started_at, completed_at, duration_ms
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """
            
            cursor.execute(query, (
                execution_id,
                workflow_id,
                execution_result.get("company_id", "unknown"),
                execution_result["status"],
                json.dumps(execution_result.get("context", {})),
                json.dumps(execution_result.get("execution_history", [])),
                json.dumps(execution_result.get("errors", [])),
                execution_result["started_at"],
                execution_result["completed_at"],
                duration_ms
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(
                f"Execution logged for workflow {workflow_id}: "
                f"{execution_result['status']} ({duration_ms}ms)"
            )
            
            return True
            
        except Exception as e:
            logger.exception(f"Error logging workflow execution: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return False
    
    def get_execution_history(self, workflow_id: str, 
                             limit: int = 50) -> List[Dict[str, Any]]:
        """
        Obtener historial de ejecuciones de un workflow.
        
        Args:
            workflow_id: ID del workflow
            limit: Máximo número de ejecuciones a retornar
            
        Returns:
            Lista de ejecuciones
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT 
                    id, status, started_at, completed_at, 
                    duration_ms, errors
                FROM workflow_executions 
                WHERE workflow_id = %s
                ORDER BY started_at DESC
                LIMIT %s
            """
            
            cursor.execute(query, (workflow_id, limit))
            rows = cursor.fetchall()
            
            executions = []
            for row in rows:
                executions.append({
                    "id": row['id'],
                    "status": row['status'],
                    "started_at": row['started_at'].isoformat() if row['started_at'] else None,
                    "completed_at": row['completed_at'].isoformat() if row['completed_at'] else None,
                    "duration_ms": row['duration_ms'],
                    "errors": json.loads(row['errors']) if row['errors'] else []
                })
            
            cursor.close()
            conn.close()
            
            return executions
            
        except Exception as e:
            logger.exception(f"Error getting execution history: {e}")
            return []
    
    # === UTILITY === #
    
    def get_stats(self, company_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtener estadísticas de workflows.
        
        Args:
            company_id: Si se especifica, stats solo de esa empresa
            
        Returns:
            Dict con estadísticas
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            if company_id:
                query = """
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN enabled = true THEN 1 ELSE 0 END) as enabled
                    FROM workflows
                    WHERE company_id = %s
                """
                cursor.execute(query, (company_id,))
            else:
                query = """
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN enabled = true THEN 1 ELSE 0 END) as enabled,
                        COUNT(DISTINCT company_id) as companies
                    FROM workflows
                """
                cursor.execute(query)
            
            row = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return {
                "total_workflows": row['total'] or 0,
                "enabled_workflows": row['enabled'] or 0,
                "companies_with_workflows": row.get('companies', 0),
                "company_id": company_id
            }
            
        except Exception as e:
            logger.exception(f"Error getting workflow stats: {e}")
            return {
                "total_workflows": 0,
                "enabled_workflows": 0,
                "companies_with_workflows": 0,
                "error": str(e)
            }


# === GLOBAL INSTANCE === #

_workflow_registry: Optional[WorkflowRegistry] = None

def get_workflow_registry() -> WorkflowRegistry:
    """Obtener instancia global del registry"""
    global _workflow_registry
    
    if _workflow_registry is None:
        _workflow_registry = WorkflowRegistry()
    
    return _workflow_registry
