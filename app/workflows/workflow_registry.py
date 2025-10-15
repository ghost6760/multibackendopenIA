# app/workflows/workflow_registry.py

from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import logging

from app.workflows.workflow_models import WorkflowGraph
from app.models import db  # SQLAlchemy
from app.services.redis_service import get_redis_client

logger = logging.getLogger(__name__)

class WorkflowRegistry:
    """
    Registry de workflows con persistencia PostgreSQL + cache Redis.
    
    ✅ Similar a PromptService (misma arquitectura)
    ✅ PostgreSQL como source of truth
    ✅ Redis para cache y performance
    ✅ Multi-tenant (por company_id)
    ✅ Versionado de workflows
    """
    
    def __init__(self):
        self.redis_client = get_redis_client()
        self.cache_ttl = 3600  # 1 hora
        
        logger.info("WorkflowRegistry initialized")
    
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
            existing = self._get_from_database(workflow.id)
            
            if existing:
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
            query = """
                SELECT id, workflow_data 
                FROM workflows 
                WHERE company_id = %s
            """
            
            if enabled_only:
                query += " AND enabled = true"
            
            query += " ORDER BY created_at DESC"
            
            result = db.session.execute(query, (company_id,))
            
            workflows = []
            for row in result:
                try:
                    workflow_data = json.loads(row[1])
                    workflow = WorkflowGraph.from_dict(workflow_data)
                    workflows.append(workflow)
                except Exception as e:
                    logger.error(f"Error parsing workflow {row[0]}: {e}")
            
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
            query = """
                UPDATE workflows 
                SET enabled = false,
                    updated_at = NOW(),
                    updated_by = %s
                WHERE id = %s
            """
            
            db.session.execute(query, (deleted_by, workflow_id))
            db.session.commit()
            
            # Invalidar cache
            self._invalidate_cache(workflow_id)
            
            logger.info(f"Workflow {workflow_id} disabled by {deleted_by}")
            return True
            
        except Exception as e:
            logger.exception(f"Error deleting workflow {workflow_id}: {e}")
            db.session.rollback()
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
        """Insertar workflow en PostgreSQL"""
        try:
            query = """
                INSERT INTO workflows (
                    id, company_id, name, description,
                    workflow_data, version, enabled,
                    tags, created_by, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
                )
            """
            
            tags_json = json.dumps(workflow.tags)
            
            db.session.execute(query, (
                workflow.id,
                workflow.company_id,
                workflow.name,
                workflow.description,
                workflow_json,
                workflow.version,
                workflow.enabled,
                tags_json,
                created_by
            ))
            
            db.session.commit()
            
            # Invalidar cache de empresa
            self._invalidate_company_cache(workflow.company_id)
            
            logger.info(f"Workflow {workflow.id} inserted in database")
            return True
            
        except Exception as e:
            logger.exception(f"Error inserting workflow {workflow.id}: {e}")
            db.session.rollback()
            return False
    
    def _update_in_database(self, workflow: WorkflowGraph, 
                           workflow_json: str, updated_by: str) -> bool:
        """Actualizar workflow en PostgreSQL"""
        try:
            query = """
                UPDATE workflows 
                SET name = %s,
                    description = %s,
                    workflow_data = %s,
                    version = version + 1,
                    enabled = %s,
                    tags = %s,
                    updated_by = %s,
                    updated_at = NOW()
                WHERE id = %s
            """
            
            tags_json = json.dumps(workflow.tags)
            
            db.session.execute(query, (
                workflow.name,
                workflow.description,
                workflow_json,
                workflow.enabled,
                tags_json,
                updated_by,
                workflow.id
            ))
            
            db.session.commit()
            
            # Invalidar cache
            self._invalidate_cache(workflow.id)
            self._invalidate_company_cache(workflow.company_id)
            
            logger.info(f"Workflow {workflow.id} updated in database")
            return True
            
        except Exception as e:
            logger.exception(f"Error updating workflow {workflow.id}: {e}")
            db.session.rollback()
            return False
    
    def _get_from_database(self, workflow_id: str) -> Optional[WorkflowGraph]:
        """Cargar workflow desde PostgreSQL"""
        try:
            query = """
                SELECT workflow_data 
                FROM workflows 
                WHERE id = %s
            """
            
            result = db.session.execute(query, (workflow_id,))
            row = result.fetchone()
            
            if not row:
                return None
            
            workflow_data = json.loads(row[0])
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
            query = """
                INSERT INTO workflow_executions (
                    workflow_id, company_id, status,
                    context, execution_history, errors,
                    started_at, completed_at, duration_ms
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """
            
            # Calcular duración
            started = datetime.fromisoformat(execution_result["started_at"])
            completed = datetime.fromisoformat(execution_result["completed_at"])
            duration_ms = (completed - started).total_seconds() * 1000
            
            db.session.execute(query, (
                workflow_id,
                execution_result["company_id"],
                execution_result["status"],
                json.dumps(execution_result.get("context", {})),
                json.dumps(execution_result.get("execution_history", [])),
                json.dumps(execution_result.get("errors", [])),
                execution_result["started_at"],
                execution_result["completed_at"],
                duration_ms
            ))
            
            db.session.commit()
            
            logger.info(
                f"Execution logged for workflow {workflow_id}: "
                f"{execution_result['status']} ({duration_ms:.0f}ms)"
            )
            
            return True
            
        except Exception as e:
            logger.exception(f"Error logging workflow execution: {e}")
            db.session.rollback()
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
            query = """
                SELECT 
                    id, status, started_at, completed_at, 
                    duration_ms, errors
                FROM workflow_executions 
                WHERE workflow_id = %s
                ORDER BY started_at DESC
                LIMIT %s
            """
            
            result = db.session.execute(query, (workflow_id, limit))
            
            executions = []
            for row in result:
                executions.append({
                    "id": row[0],
                    "status": row[1],
                    "started_at": row[2].isoformat() if row[2] else None,
                    "completed_at": row[3].isoformat() if row[3] else None,
                    "duration_ms": row[4],
                    "errors": json.loads(row[5]) if row[5] else []
                })
            
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
            if company_id:
                query = """
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN enabled = true THEN 1 ELSE 0 END) as enabled,
                        COUNT(DISTINCT company_id) as companies
                    FROM workflows
                    WHERE company_id = %s
                """
                result = db.session.execute(query, (company_id,))
            else:
                query = """
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN enabled = true THEN 1 ELSE 0 END) as enabled,
                        COUNT(DISTINCT company_id) as companies
                    FROM workflows
                """
                result = db.session.execute(query)
            
            row = result.fetchone()
            
            return {
                "total_workflows": row[0] or 0,
                "enabled_workflows": row[1] or 0,
                "companies_with_workflows": row[2] or 0,
                "company_id": company_id
            }
            
        except Exception as e:
            logger.exception("Error getting workflow stats: {e}")
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
