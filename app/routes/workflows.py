# app/routes/workflows.py

from flask import Blueprint, request, jsonify, current_app, g
from functools import wraps
from typing import Dict, Any, Optional
import logging
import asyncio
from datetime import datetime
import psycopg2
import os

from app.workflows.workflow_models import WorkflowGraph, WorkflowNode, WorkflowEdge
from app.workflows.workflow_executor import WorkflowExecutor
from app.workflows.workflow_registry import get_workflow_registry
from app.workflows.condition_evaluator import ConditionEvaluator, validate_condition
from app.services.multi_agent_orchestrator import MultiAgentOrchestrator
from app.services.multi_agent_factory import get_orchestrator_for_company
from app.models.conversation import ConversationManager
from app.config.company_config import get_company_config

logger = logging.getLogger(__name__)

# Crear blueprint
workflows_bp = Blueprint('workflows', __name__, url_prefix='/api/workflows')

# ============================================================================
# DECORATORS Y HELPERS - CORREGIDOS
# ============================================================================

def require_company_context(f):
    """
    Decorator para validar contexto de empresa.
    
    FIXED: Manejo correcto de query parameters, headers y body JSON.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        company_id = None
        
        # 1. Intentar desde header
        company_id = request.headers.get('X-Company-ID')
        if company_id:
            logger.debug(f"company_id from header: {company_id}")
        
        # 2. Intentar desde query parameter (CRÍTICO PARA GET)
        if not company_id:
            company_id = request.args.get('company_id')
            if company_id:
                logger.debug(f"company_id from query param: {company_id}")
        
        # 3. Intentar desde JSON body (solo si es POST/PUT)
        if not company_id and request.is_json:
            try:
                json_data = request.get_json(silent=True)
                if json_data and 'company_id' in json_data:
                    company_id = json_data['company_id']
                    logger.debug(f"company_id from JSON body: {company_id}")
            except Exception as e:
                logger.debug(f"Error reading JSON body: {e}")
        
        # 4. Validar que se encontró company_id
        if not company_id:
            logger.warning("company_id not provided in request")
            return jsonify({
                "success": False,
                "error": "company_id is required",
                "message": "Please provide company_id in header, query param, or body"
            }), 400
        
        # 5. Validar que la empresa exista
        try:
            company_config = get_company_config(company_id)
            if not company_config:
                return jsonify({
                    "success": False,
                    "error": "invalid_company",
                    "message": f"Company '{company_id}' not found"
                }), 404
        except Exception as e:
            logger.error(f"Error validating company {company_id}: {e}")
            return jsonify({
                "success": False,
                "error": "company_validation_failed",
                "message": "Could not validate company"
            }), 500
        
        # 6. Agregar al request context
        request.company_id = company_id
        request.company_config = company_config
        
        return f(*args, **kwargs)
    
    return decorated_function

def validate_json_payload(required_fields: list = None):
    """Decorator para validar payload JSON"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({
                    "success": False,
                    "error": "invalid_content_type",
                    "message": "Content-Type must be application/json"
                }), 400
            
            if required_fields:
                json_data = request.get_json(silent=True)
                if not json_data:
                    return jsonify({
                        "success": False,
                        "error": "invalid_json",
                        "message": "Invalid JSON body"
                    }), 400
                
                missing = [field for field in required_fields if field not in json_data]
                if missing:
                    return jsonify({
                        "success": False,
                        "error": "missing_fields",
                        "message": f"Missing required fields: {', '.join(missing)}",
                        "required_fields": required_fields
                    }), 400
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator

def handle_errors(f):
    """Decorator para manejo global de errores"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            logger.error(f"Validation error: {e}")
            return jsonify({
                "success": False,
                "error": "validation_error",
                "message": str(e)
            }), 400
        except Exception as e:
            logger.exception(f"Unexpected error in {f.__name__}: {e}")
            return jsonify({
                "success": False,
                "error": "internal_server_error",
                "message": "An unexpected error occurred"
            }), 500
    
    return decorated_function

# ============================================================================
# ENDPOINTS - CRUD DE WORKFLOWS
# ============================================================================

@workflows_bp.route('', methods=['GET'])
@require_company_context
@handle_errors
def list_workflows():
    """
    GET /api/workflows?company_id=benova&enabled_only=true
    
    Listar workflows de una empresa.
    """
    company_id = request.company_id
    enabled_only = request.args.get('enabled_only', 'true').lower() == 'true'
    
    registry = get_workflow_registry()
    workflows = registry.get_workflows_by_company(company_id, enabled_only=enabled_only)
    
    return jsonify({
        "success": True,
        "company_id": company_id,
        "count": len(workflows),
        "workflows": [
            {
                "workflow_id": wf.id,
                "name": wf.name,
                "description": wf.description,
                "enabled": wf.enabled,
                "version": wf.version,
                "tags": wf.tags,
                "total_nodes": len(wf.nodes),
                "total_edges": len(wf.edges),
                "created_at": wf.created_at,
                "updated_at": wf.updated_at
            }
            for wf in workflows
        ]
    }), 200

@workflows_bp.route('/<workflow_id>', methods=['GET'])
@require_company_context
@handle_errors
def get_workflow(workflow_id: str):
    """
    GET /api/workflows/{workflow_id}?company_id=benova
    
    Obtener detalles completos de un workflow.
    """
    company_id = request.company_id
    use_cache = request.args.get('use_cache', 'true').lower() == 'true'
    
    registry = get_workflow_registry()
    workflow = registry.get_workflow(workflow_id, use_cache=use_cache)
    
    if not workflow:
        return jsonify({
            "success": False,
            "error": "workflow_not_found",
            "message": f"Workflow '{workflow_id}' not found"
        }), 404
    
    # Verificar que pertenece a la empresa
    if workflow.company_id != company_id:
        return jsonify({
            "success": False,
            "error": "unauthorized",
            "message": "Workflow does not belong to this company"
        }), 403
    
    # Obtener validación
    validation = workflow.validate()
    
    return jsonify({
        "success": True,
        "workflow": workflow.to_dict(),
        "validation": validation,
        "summary": workflow.get_execution_summary()
    }), 200

@workflows_bp.route('', methods=['POST'])
@require_company_context
@validate_json_payload(['name', 'workflow_data'])
@handle_errors
def create_workflow():
    """
    POST /api/workflows
    Body: {
        "company_id": "benova",
        "name": "Workflow de Ventas",
        "description": "...",
        "workflow_data": {...},
        "enabled": true,
        "tags": ["sales", "automated"]
    }
    
    Crear nuevo workflow.
    """
    company_id = request.company_id
    data = request.json
    
    # Generar ID único
    import time
    workflow_id = f"wf_{company_id}_{int(time.time())}"
    
    # Crear WorkflowGraph desde datos
    try:
        workflow_data = data['workflow_data']
        workflow_data.update({
            "id": workflow_id,
            "company_id": company_id,
            "name": data['name'],
            "description": data.get('description', ''),
            "enabled": data.get('enabled', True),
            "tags": data.get('tags', []),
            "created_by": data.get('created_by', 'api'),
            "created_at": datetime.utcnow().isoformat()
        })
        
        workflow = WorkflowGraph.from_dict(workflow_data)
        
    except Exception as e:
        logger.exception(f"Error parsing workflow data: {e}")
        return jsonify({
            "success": False,
            "error": "invalid_workflow_data",
            "message": f"Error parsing workflow data: {str(e)}"
        }), 400
    
    # Validar workflow
    validation = workflow.validate()
    if validation["errors"]:
        return jsonify({
            "success": False,
            "error": "invalid_workflow",
            "message": "Workflow validation failed",
            "validation_errors": validation["errors"],
            "validation_warnings": validation["warnings"]
        }), 400
    
    # Guardar en registry
    registry = get_workflow_registry()
    success = registry.save_workflow(workflow, created_by=data.get('created_by', 'api'))
    
    if not success:
        return jsonify({
            "success": False,
            "error": "save_failed",
            "message": "Failed to save workflow"
        }), 500
    
    logger.info(f"Workflow created: {workflow_id} for company {company_id}")
    
    return jsonify({
        "success": True,
        "workflow_id": workflow_id,
        "message": "Workflow created successfully",
        "validation_warnings": validation["warnings"]
    }), 201

@workflows_bp.route('/<workflow_id>', methods=['PUT'])
@require_company_context
@validate_json_payload()
@handle_errors
def update_workflow(workflow_id: str):
    """
    PUT /api/workflows/{workflow_id}?company_id=benova
    Body: {
        "name": "...",
        "description": "...",
        "enabled": true
    }
    
    Actualizar workflow existente.
    """
    company_id = request.company_id
    data = request.json
    
    registry = get_workflow_registry()
    
    # Obtener workflow actual
    existing = registry.get_workflow(workflow_id, use_cache=False)
    if not existing:
        return jsonify({
            "success": False,
            "error": "workflow_not_found",
            "message": f"Workflow '{workflow_id}' not found"
        }), 404
    
    # Verificar permisos
    if existing.company_id != company_id:
        return jsonify({
            "success": False,
            "error": "unauthorized",
            "message": "Workflow does not belong to this company"
        }), 403
    
    # Actualizar campos
    if 'name' in data:
        existing.name = data['name']
    if 'description' in data:
        existing.description = data['description']
    if 'enabled' in data:
        existing.enabled = data['enabled']
    if 'tags' in data:
        existing.tags = data['tags']
    if 'workflow_data' in data:
        # Reconstruir desde datos nuevos pero mantener metadata
        new_data = data['workflow_data']
        new_data.update({
            "id": workflow_id,
            "company_id": company_id,
            "version": existing.version + 1
        })
        existing = WorkflowGraph.from_dict(new_data)
    
    existing.updated_at = datetime.utcnow().isoformat()
    
    # Validar
    validation = existing.validate()
    if validation["errors"]:
        return jsonify({
            "success": False,
            "error": "invalid_workflow",
            "message": "Updated workflow validation failed",
            "validation_errors": validation["errors"]
        }), 400
    
    # Guardar
    success = registry.save_workflow(existing, created_by=data.get('modified_by', 'api'))
    
    if not success:
        return jsonify({
            "success": False,
            "error": "update_failed",
            "message": "Failed to update workflow"
        }), 500
    
    logger.info(f"Workflow updated: {workflow_id}")
    
    return jsonify({
        "success": True,
        "workflow_id": workflow_id,
        "message": "Workflow updated successfully",
        "version": existing.version
    }), 200

@workflows_bp.route('/<workflow_id>', methods=['DELETE'])
@require_company_context
@handle_errors
def delete_workflow(workflow_id: str):
    """
    DELETE /api/workflows/{workflow_id}?company_id=benova
    
    Eliminar (deshabilitar) workflow.
    """
    company_id = request.company_id
    
    registry = get_workflow_registry()
    
    # Verificar que existe y pertenece a la empresa
    existing = registry.get_workflow(workflow_id, use_cache=False)
    if not existing:
        return jsonify({
            "success": False,
            "error": "workflow_not_found",
            "message": f"Workflow '{workflow_id}' not found"
        }), 404
    
    if existing.company_id != company_id:
        return jsonify({
            "success": False,
            "error": "unauthorized",
            "message": "Workflow does not belong to this company"
        }), 403
    
    # Eliminar (soft delete)
    success = registry.delete_workflow(workflow_id, deleted_by='api')
    
    if not success:
        return jsonify({
            "success": False,
            "error": "delete_failed",
            "message": "Failed to delete workflow"
        }), 500
    
    logger.info(f"Workflow deleted: {workflow_id}")
    
    return jsonify({
        "success": True,
        "workflow_id": workflow_id,
        "message": "Workflow deleted successfully"
    }), 200

# ============================================================================
# ENDPOINTS - EJECUCIÓN DE WORKFLOWS
# ============================================================================

@workflows_bp.route('/<workflow_id>/execute', methods=['POST'])
@require_company_context
@validate_json_payload(['context'])
@handle_errors
def execute_workflow(workflow_id: str):
    """
    POST /api/workflows/{workflow_id}/execute
    Body: {
        "company_id": "benova",
        "context": {
            "user_id": "user_123",
            "user_message": "Quiero información sobre botox"
        }
    }
    
    Ejecutar un workflow.
    """
    company_id = request.company_id
    context = request.json['context']
    
    registry = get_workflow_registry()
    
    # Obtener workflow
    workflow = registry.get_workflow(workflow_id)
    if not workflow:
        return jsonify({
            "success": False,
            "error": "workflow_not_found",
            "message": f"Workflow '{workflow_id}' not found"
        }), 404
    
    if workflow.company_id != company_id:
        return jsonify({
            "success": False,
            "error": "unauthorized",
            "message": "Workflow does not belong to this company"
        }), 403
    
    if not workflow.enabled:
        return jsonify({
            "success": False,
            "error": "workflow_disabled",
            "message": "Workflow is currently disabled"
        }), 400
    
    # Obtener orchestrator de la empresa
    orchestrator = get_orchestrator_for_company(company_id)
    if not orchestrator:
        return jsonify({
            "success": False,
            "error": "orchestrator_not_found",
            "message": f"Orchestrator not available for company '{company_id}'"
        }), 500
    
    # Obtener conversation manager
    conversation_manager = ConversationManager()
    
    # Crear executor
    executor = WorkflowExecutor(
        workflow=workflow,
        orchestrator=orchestrator,
        conversation_manager=conversation_manager
    )
    
    # Ejecutar (async)
    try:
        # Crear event loop si no existe
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(executor.execute(context))
        
        # Log ejecución
        registry.log_execution(workflow_id, result)
        
        # Actualizar estadísticas usando psycopg2
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cursor = conn.cursor()
            cursor.execute(
                "SELECT update_workflow_execution_stats(%s, %s)",
                (workflow_id, result['status'])
            )
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            logger.warning(f"Could not update execution stats: {e}")
        
        logger.info(
            f"Workflow executed: {workflow_id} - Status: {result['status']}"
        )
        
        return jsonify({
            "success": result['status'] == 'success',
            "execution": result
        }), 200
        
    except Exception as e:
        logger.exception(f"Error executing workflow {workflow_id}: {e}")
        return jsonify({
            "success": False,
            "error": "execution_failed",
            "message": str(e)
        }), 500

@workflows_bp.route('/<workflow_id>/executions', methods=['GET'])
@require_company_context
@handle_errors
def get_execution_history(workflow_id: str):
    """
    GET /api/workflows/{workflow_id}/executions?company_id=benova&limit=50
    
    Obtener historial de ejecuciones.
    """
    company_id = request.company_id
    limit = int(request.args.get('limit', 50))
    
    registry = get_workflow_registry()
    
    # Verificar permisos
    workflow = registry.get_workflow(workflow_id)
    if not workflow or workflow.company_id != company_id:
        return jsonify({
            "success": False,
            "error": "unauthorized",
            "message": "Workflow not found or unauthorized"
        }), 403
    
    # Obtener historial
    executions = registry.get_execution_history(workflow_id, limit=limit)
    
    return jsonify({
        "success": True,
        "workflow_id": workflow_id,
        "total": len(executions),
        "executions": executions
    }), 200

# ============================================================================
# ENDPOINTS - VALIDACIÓN Y UTILIDADES
# ============================================================================

@workflows_bp.route('/validate', methods=['POST'])
@require_company_context
@validate_json_payload(['workflow_data'])
@handle_errors
def validate_workflow_data():
    """
    POST /api/workflows/validate
    Body: {
        "company_id": "benova",
        "workflow_data": {...}
    }
    
    Validar estructura de workflow sin guardarlo.
    """
    data = request.json
    
    try:
        workflow = WorkflowGraph.from_dict(data['workflow_data'])
        validation = workflow.validate()
        
        return jsonify({
            "success": len(validation["errors"]) == 0,
            "validation": validation,
            "summary": workflow.get_execution_summary()
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "parse_error",
            "message": f"Error parsing workflow data: {str(e)}"
        }), 400

@workflows_bp.route('/validate-condition', methods=['POST'])
@validate_json_payload(['condition'])
@handle_errors
def validate_condition_syntax():
    """
    POST /api/workflows/validate-condition
    Body: {
        "condition": "{{age}} >= 18 and {{verified}} == true",
        "test_context": {"age": 20, "verified": true}
    }
    
    Validar sintaxis de una condición.
    """
    condition = request.json['condition']
    test_context = request.json.get('test_context', {})
    
    # Validar sintaxis
    validation = validate_condition(condition)
    
    # Si hay contexto de prueba, evaluar también
    if test_context and validation["valid"]:
        evaluator = ConditionEvaluator()
        try:
            result = evaluator.evaluate(condition, test_context)
            validation["test_result"] = result
        except Exception as e:
            validation["test_error"] = str(e)
    
    return jsonify({
        "success": validation["valid"],
        "validation": validation
    }), 200

@workflows_bp.route('/templates', methods=['GET'])
@handle_errors
def list_templates():
    """
    GET /api/workflows/templates?category=sales
    
    Listar templates disponibles.
    """
    category = request.args.get('category')
    
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()
        
        query = "SELECT template_id, name, description, category, business_types, required_tools, required_agents, usage_count FROM workflow_templates WHERE is_public = true"
        params = []
        
        if category:
            query += " AND category = %s"
            params.append(category)
        
        query += " ORDER BY usage_count DESC, created_at DESC"
        
        cursor.execute(query, tuple(params) if params else None)
        rows = cursor.fetchall()
        
        templates = []
        for row in rows:
            templates.append({
                "template_id": row[0],
                "name": row[1],
                "description": row[2],
                "category": row[3],
                "business_types": row[4],
                "required_tools": row[5],
                "required_agents": row[6],
                "usage_count": row[7]
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "total": len(templates),
            "templates": templates
        }), 200
        
    except Exception as e:
        logger.exception(f"Error listing templates: {e}")
        return jsonify({
            "success": False,
            "error": "database_error",
            "message": "Could not retrieve templates"
        }), 500

@workflows_bp.route('/stats', methods=['GET'])
@require_company_context
@handle_errors
def get_workflow_stats():
    """
    GET /api/workflows/stats?company_id=benova
    
    Obtener estadísticas de workflows.
    """
    company_id = request.company_id
    
    registry = get_workflow_registry()
    stats = registry.get_stats(company_id=company_id)
    
    return jsonify({
        "success": True,
        **stats
    }), 200

# ============================================================================
# HEALTH CHECK
# ============================================================================

@workflows_bp.route('/health', methods=['GET'])
def health_check():
    """
    GET /api/workflows/health
    
    Verificar salud del sistema de workflows.
    """
    try:
        registry = get_workflow_registry()
        
        # Test básico de registry
        test_stats = registry.get_stats()
        
        return jsonify({
            "success": True,
            "status": "healthy",
            "registry_available": True,
            "total_workflows": test_stats.get("total_workflows", 0),
            "timestamp": datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.exception("Health check failed")
        return jsonify({
            "success": False,
            "status": "unhealthy",
            "error": str(e)
        }), 500

# ═══════════════════════════════════════════════════════════
# CONFIGURATION AGENT - Chat conversacional para crear workflows
# ═══════════════════════════════════════════════════════════

@workflows_bp.route('/config-chat', methods=['POST'])
@handle_errors
def config_agent_chat():
    """
    Chat conversacional para crear workflows mediante lenguaje natural.
    
    POST /api/workflows/config-chat
    Body: {
        "company_id": "benova",
        "user_id": "admin_001",  # Opcional, se auto-genera
        "message": "Quiero crear un workflow para cuando pregunten por botox"
    }
    
    Returns: {
        "success": true,
        "response": "¡Perfecto! Para crear tu workflow necesito saber...",
        "user_id": "admin_001",
        "stage": "gathering"
    }
    """
    data = request.get_json()
    company_id = data.get('company_id')
    user_id = data.get('user_id', f'user_{int(time.time())}')
    message = data.get('message')
    
    if not company_id:
        return jsonify({
            "success": False,
            "error": "company_id is required"
        }), 400
    
    if not message:
        return jsonify({
            "success": False,
            "error": "message is required"
        }), 400
    
    try:
        # Obtener configuración de empresa
        company_config = get_company_config(company_id)
        if not company_config:
            return jsonify({
                "success": False,
                "error": f"Company {company_id} not found"
            }), 404
        
        # Crear ConfigAgent
        from app.workflows.config_agent import ConfigAgent
        from app.services.openai_service import OpenAIService
        
        openai_service = OpenAIService()
        config_agent = ConfigAgent(company_config, openai_service)
        
        # Procesar mensaje
        response_text = config_agent.invoke({
            "user_id": user_id,
            "question": message,
            "company_id": company_id
        })
        
        # Obtener estado actual
        state = config_agent.user_states.get(user_id)
        current_stage = state.stage if state else "complete"
        
        return jsonify({
            "success": True,
            "response": response_text,
            "user_id": user_id,
            "stage": current_stage
        })
        
    except Exception as e:
        logger.exception(f"Error in config agent chat: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Error procesando tu mensaje. Por favor intenta de nuevo."
        }), 500


@workflows_bp.route('/config-chat/reset', methods=['POST'])
@handle_errors
def reset_config_chat():
    """
    Resetear conversación del ConfigAgent.
    
    POST /api/workflows/config-chat/reset
    Body: {
        "company_id": "benova",
        "user_id": "admin_001"
    }
    """
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({
            "success": False,
            "error": "user_id is required"
        }), 400
    
    # En producción real, esto debería limpiar estado en Redis
    # Por ahora, el ConfigAgent maneja estado en memoria
    
    return jsonify({
        "success": True,
        "message": f"Conversation reset for user {user_id}",
        "user_id": user_id
    })


@workflows_bp.route('/config-chat/status', methods=['GET'])
@handle_errors
def config_chat_status():
    """
    Obtener estado actual de conversación.
    
    GET /api/workflows/config-chat/status?user_id=admin_001&company_id=benova
    """
    user_id = request.args.get('user_id')
    company_id = request.args.get('company_id')
    
    if not user_id or not company_id:
        return jsonify({
            "success": False,
            "error": "user_id and company_id are required"
        }), 400
    
    # Retornar info básica
    return jsonify({
        "success": True,
        "user_id": user_id,
        "company_id": company_id,
        "has_active_conversation": False,  # Implementar lookup real
        "endpoints_available": [
            "/api/workflows/config-chat",
            "/api/workflows/config-chat/reset",
            "/api/workflows/config-chat/status"
        ]
    })
