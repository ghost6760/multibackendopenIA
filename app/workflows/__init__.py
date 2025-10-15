# app/workflows/__init__.py

"""
Workflows module - Conversational workflow creation and execution system
Enhanced with visual workflow builder and state machine execution
"""

# ============================================================================
# CORE MODELS - WorkflowGraph Definition
# ============================================================================
from app.workflows.workflow_models import (
    # Enums
    NodeType,
    EdgeType,
    
    # Core classes
    WorkflowNode,
    WorkflowEdge,
    WorkflowGraph
)

# ============================================================================
# EXECUTION ENGINE - State Machine
# ============================================================================
from app.workflows.workflow_executor import (
    WorkflowExecutor,
    WorkflowState,
    ExecutionStatus
)

# ============================================================================
# CONDITION EVALUATION - Safe expression evaluator
# ============================================================================
from app.workflows.condition_evaluator import (
    ConditionEvaluator,
    evaluate_condition,
    validate_condition
)

# ============================================================================
# PERSISTENCE - PostgreSQL Registry
# ============================================================================
from app.workflows.workflow_registry import (
    WorkflowRegistry,
    get_workflow_registry
)

# ============================================================================
# TOOLS SYSTEM - Existing (mantener compatibilidad)
# ============================================================================
from app.workflows.tools_library import (
    ToolsLibrary,
    ToolDefinition
)

from app.workflows.tool_executor import (
    ToolExecutor
)

# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # === MODELS === #
    'NodeType',
    'EdgeType',
    'WorkflowNode',
    'WorkflowEdge',
    'WorkflowGraph',
    
    # === EXECUTION === #
    'WorkflowExecutor',
    'WorkflowState',
    'ExecutionStatus',
    
    # === CONDITIONS === #
    'ConditionEvaluator',
    'evaluate_condition',
    'validate_condition',
    
    # === PERSISTENCE === #
    'WorkflowRegistry',
    'get_workflow_registry',
    
    # === TOOLS (mantener compatibilidad) === #
    'ToolsLibrary',
    'ToolDefinition',
    'ToolExecutor'
]

# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_workflow(workflow_id: str, company_id: str, name: str, 
                   description: str = "") -> WorkflowGraph:
    """
    Convenience function para crear un workflow vacío.
    
    Args:
        workflow_id: ID único del workflow
        company_id: ID de la empresa dueña
        name: Nombre descriptivo
        description: Descripción opcional
        
    Returns:
        WorkflowGraph vacío listo para agregar nodos
        
    Example:
        >>> workflow = create_workflow("wf_benova_123", "benova", "Workflow de Ventas")
        >>> workflow.add_node(WorkflowNode(...))
    """
    return WorkflowGraph(
        id=workflow_id,
        company_id=company_id,
        name=name,
        description=description
    )

def load_workflow(workflow_id: str) -> WorkflowGraph:
    """
    Convenience function para cargar un workflow desde registry.
    
    Args:
        workflow_id: ID del workflow a cargar
        
    Returns:
        WorkflowGraph cargado desde PostgreSQL
        
    Example:
        >>> workflow = load_workflow("wf_benova_123")
        >>> workflow.validate()
    """
    registry = get_workflow_registry()
    return registry.get_workflow(workflow_id)

def save_workflow(workflow: WorkflowGraph, created_by: str = "system") -> bool:
    """
    Convenience function para guardar un workflow.
    
    Args:
        workflow: WorkflowGraph a guardar
        created_by: Usuario que guarda
        
    Returns:
        True si guardó exitosamente
        
    Example:
        >>> workflow = create_workflow(...)
        >>> workflow.add_node(...)
        >>> save_workflow(workflow, created_by="admin")
    """
    registry = get_workflow_registry()
    return registry.save_workflow(workflow, created_by=created_by)

def execute_workflow_by_id(workflow_id: str, context: dict, 
                          company_id: str = None) -> dict:
    """
    Convenience function para ejecutar un workflow por ID.
    
    Args:
        workflow_id: ID del workflow
        context: Contexto inicial para ejecución
        company_id: ID de empresa (opcional, se infiere del workflow)
        
    Returns:
        Resultado de ejecución
        
    Example:
        >>> result = execute_workflow_by_id(
        ...     "wf_benova_123",
        ...     {"user_message": "Quiero info sobre botox", "user_id": "user_123"}
        ... )
        >>> print(result['status'])
    """
    import asyncio
    from app.services.multi_agent_factory import get_orchestrator_for_company
    from app.models.conversation import ConversationManager
    
    # Cargar workflow
    registry = get_workflow_registry()
    workflow = registry.get_workflow(workflow_id)
    
    if not workflow:
        raise ValueError(f"Workflow {workflow_id} not found")
    
    # Inferir company_id si no se proporciona
    if not company_id:
        company_id = workflow.company_id
    
    # Obtener orchestrator
    orchestrator = get_orchestrator_for_company(company_id)
    if not orchestrator:
        raise ValueError(f"Orchestrator not available for company {company_id}")
    
    # Crear executor
    executor = WorkflowExecutor(
        workflow=workflow,
        orchestrator=orchestrator,
        conversation_manager=ConversationManager()
    )
    
    # Ejecutar (async)
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    result = loop.run_until_complete(executor.execute(context))
    
    # Log ejecución
    registry.log_execution(workflow_id, result)
    
    return result

# ============================================================================
# VERSION INFO
# ============================================================================

__version__ = '1.0.0'
__author__ = 'Multi-Tenant Workflows Team'

def get_module_info() -> dict:
    """
    Obtener información del módulo de workflows.
    
    Returns:
        Dict con información del módulo
    """
    return {
        "module": "app.workflows",
        "version": __version__,
        "components": {
            "models": ["WorkflowGraph", "WorkflowNode", "WorkflowEdge"],
            "execution": ["WorkflowExecutor", "WorkflowState"],
            "conditions": ["ConditionEvaluator"],
            "persistence": ["WorkflowRegistry"],
            "tools": ["ToolsLibrary", "ToolExecutor"]
        },
        "features": [
            "Visual workflow builder",
            "State machine execution",
            "Multi-agent orchestration",
            "Tool execution",
            "Conditional branching",
            "Parallel execution",
            "PostgreSQL persistence",
            "Redis caching",
            "Versionado automático"
        ]
    }
