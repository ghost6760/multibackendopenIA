# app/workflows/workflow_executor.py

from typing import Dict, Any, List, Set, Optional
import asyncio
import logging
from datetime import datetime
from enum import Enum

from app.workflows.workflow_models import (
    WorkflowGraph, WorkflowNode, WorkflowEdge, NodeType, EdgeType
)
from app.services.multi_agent_orchestrator import MultiAgentOrchestrator
from app.models.conversation import ConversationManager

logger = logging.getLogger(__name__)

class ExecutionStatus(Enum):
    """Estados de ejecución del workflow"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

class WorkflowState:
    """
    Estado actual de la ejecución del workflow.
    Almacena variables, historial, y resultados de nodos.
    """
    
    def __init__(self, initial_context: Dict[str, Any] = None):
        # Variables del workflow (mutable por nodos)
        self.variables: Dict[str, Any] = {}
        
        # Contexto inicial (inmutable - datos de entrada)
        self.context: Dict[str, Any] = initial_context or {}
        
        # Historial de ejecución
        self.execution_history: List[Dict] = []
        
        # Nodos actualmente en ejecución (para parallel)
        self.active_nodes: Set[str] = set()
        
        # Output de cada nodo
        self.node_outputs: Dict[str, Any] = {}
        
        # Errores ocurridos
        self.errors: List[Dict] = []
        
        # Timestamp de inicio
        self.started_at: str = datetime.utcnow().isoformat()
    
    def set_variable(self, key: str, value: Any):
        """Setear variable del workflow"""
        self.variables[key] = value
        logger.debug(f"Variable set: {key} = {value}")
    
    def get_variable(self, key: str, default=None) -> Any:
        """Obtener variable del workflow"""
        return self.variables.get(key, default)
    
    def add_execution_record(self, node_id: str, node_name: str, status: str, 
                           output: Any = None, error: str = None, duration_ms: float = None):
        """Registrar ejecución de un nodo"""
        record = {
            "node_id": node_id,
            "node_name": node_name,
            "status": status,
            "output": output,
            "error": error,
            "duration_ms": duration_ms,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.execution_history.append(record)
        
        # Guardar output si existe
        if output is not None:
            self.node_outputs[node_id] = output
        
        # Guardar error si existe
        if error:
            self.errors.append({
                "node_id": node_id,
                "node_name": node_name,
                "error": error,
                "timestamp": datetime.utcnow().isoformat()
            })
    
    def get_full_context(self) -> Dict[str, Any]:
        """
        Obtener contexto completo para evaluación de condiciones.
        Combina context inicial + variables + outputs de nodos.
        """
        return {
            **self.context,
            **self.variables,
            "node_outputs": self.node_outputs,
            "execution_history": self.execution_history
        }

class WorkflowExecutor:
    """
    Ejecutor de workflows basado en state machine.
    
    ✅ USA MultiAgentOrchestrator existente para ejecutar agentes
    ✅ USA ToolExecutor para ejecutar tools
    ✅ Compatible con sistema multi-tenant
    ✅ Maneja grafos complejos (branching, loops, parallel)
    """
    
    def __init__(self, workflow: WorkflowGraph, orchestrator: MultiAgentOrchestrator, 
                 conversation_manager: ConversationManager = None):
        """
        Args:
            workflow: WorkflowGraph a ejecutar
            orchestrator: MultiAgentOrchestrator de la empresa
            conversation_manager: Para mantener historial (opcional)
        """
        self.workflow = workflow
        self.orchestrator = orchestrator
        self.conversation_manager = conversation_manager
        self.state = None  # Se inicializa en execute()
        
        # Validar que orchestrator es de la misma empresa
        if orchestrator.company_id != workflow.company_id:
            raise ValueError(
                f"Orchestrator company ({orchestrator.company_id}) doesn't match "
                f"workflow company ({workflow.company_id})"
            )
        
        logger.info(f"[{workflow.company_id}] WorkflowExecutor initialized for workflow: {workflow.name}")
    
    async def execute(self, initial_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecutar workflow completo.
        
        Args:
            initial_context: Contexto inicial (ej: user_message, user_id, etc.)
            
        Returns:
            Resultado de ejecución con status, historial, outputs, etc.
        """
        logger.info(f"🚀 [{self.workflow.company_id}] Starting workflow execution: {self.workflow.name}")
        
        # Validar workflow antes de ejecutar
        validation = self.workflow.validate()
        if validation["errors"]:
            return {
                "status": ExecutionStatus.FAILED.value,
                "error": "Workflow validation failed",
                "validation_errors": validation["errors"],
                "workflow_id": self.workflow.id
            }
        
        # Inicializar estado
        self.state = WorkflowState(initial_context)
        self.state.variables.update(self.workflow.variables)
        
        result = {
            "workflow_id": self.workflow.id,
            "workflow_name": self.workflow.name,
            "company_id": self.workflow.company_id,
            "status": ExecutionStatus.RUNNING.value,
            "started_at": self.state.started_at,
            "completed_at": None,
            "execution_history": [],
            "final_output": None,
            "errors": []
        }
        
        try:
            # Ejecutar desde start node
            await self._execute_from_node(self.workflow.start_node_id)
            
            # Completado exitosamente
            result["status"] = ExecutionStatus.SUCCESS.value
            result["final_output"] = self.state.variables
            
        except asyncio.TimeoutError:
            logger.error(f"[{self.workflow.company_id}] Workflow execution timeout")
            result["status"] = ExecutionStatus.TIMEOUT.value
            result["errors"].append("Workflow execution timeout")
            
        except Exception as e:
            logger.exception(f"[{self.workflow.company_id}] Workflow execution failed: {e}")
            result["status"] = ExecutionStatus.FAILED.value
            result["errors"].append(str(e))
        
        finally:
            result["completed_at"] = datetime.utcnow().isoformat()
            result["execution_history"] = self.state.execution_history
            result["errors"].extend([err["error"] for err in self.state.errors])
        
        logger.info(
            f"✅ [{self.workflow.company_id}] Workflow execution completed: "
            f"{result['status']} ({len(result['execution_history'])} nodes executed)"
        )
        
        return result
    
    async def _execute_from_node(self, node_id: str, visited: Set[str] = None):
        """
        Ejecutar desde un nodo específico.
        Usa DFS para traversal del grafo.
        """
        if visited is None:
            visited = set()
        
        # Prevenir loops infinitos
        if node_id in visited:
            node = self.workflow.get_node(node_id)
            # Si es un loop intencional, permitir
            if node and node.type != NodeType.LOOP:
                logger.warning(f"[{self.workflow.company_id}] Cycle detected at node {node_id}, skipping")
                return
        
        visited.add(node_id)
        
        # Obtener nodo
        node = self.workflow.get_node(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found in workflow")
        
        if not node.enabled:
            logger.info(f"[{self.workflow.company_id}] Node {node.name} is disabled, skipping")
            return
        
        logger.info(f"📍 [{self.workflow.company_id}] Executing node: {node.name} ({node.type.value})")
        
        start_time = datetime.utcnow()
        
        try:
            # Marcar como activo
            self.state.active_nodes.add(node_id)
            
            # Ejecutar nodo según su tipo
            node_output = await self._execute_node(node)
            
            # Calcular duración
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Registrar ejecución exitosa
            self.state.add_execution_record(
                node_id, 
                node.name,
                "success",
                output=node_output,
                duration_ms=duration_ms
            )
            
            # Determinar siguientes nodos
            next_node_ids = self.workflow.get_next_nodes(
                node_id,
                self.state.get_full_context()
            )
            
            logger.info(
                f"[{self.workflow.company_id}] Node {node.name} completed. "
                f"Next nodes: {next_node_ids}"
            )
            
            # Ejecutar siguientes nodos
            if node.type == NodeType.PARALLEL:
                # Ejecutar branches en paralelo
                await self._execute_parallel_branches(next_node_ids, visited.copy())
            else:
                # Ejecutar secuencialmente
                for next_id in next_node_ids:
                    await self._execute_from_node(next_id, visited.copy())
        
        except Exception as e:
            # Calcular duración hasta el error
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            logger.error(f"[{self.workflow.company_id}] Error executing node {node.name}: {e}")
            self.state.add_execution_record(
                node_id,
                node.name,
                "failed",
                error=str(e),
                duration_ms=duration_ms
            )
            
            # Buscar edge de error (fallback)
            await self._handle_node_error(node_id, e, visited)
        
        finally:
            self.state.active_nodes.discard(node_id)
    
    async def _execute_parallel_branches(self, node_ids: List[str], visited: Set[str]):
        """Ejecutar múltiples branches en paralelo"""
        if not node_ids:
            return
        
        logger.info(f"[{self.workflow.company_id}] Executing {len(node_ids)} branches in parallel")
        
        tasks = [
            self._execute_from_node(node_id, visited.copy())
            for node_id in node_ids
        ]
        
        # Ejecutar en paralelo, continuar si alguno falla
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log errores
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"[{self.workflow.company_id}] Parallel branch {i} failed: {result}")
    
    async def _handle_node_error(self, node_id: str, error: Exception, visited: Set[str]):
        """Manejar error en nodo, buscar edge de fallback"""
        # Buscar edge de tipo ON_ERROR
        outgoing = self.workflow.get_outgoing_edges(node_id)
        error_edges = [e for e in outgoing if e.edge_type == EdgeType.ON_ERROR]
        
        if error_edges:
            logger.info(f"[{self.workflow.company_id}] Following error edge from node {node_id}")
            for edge in error_edges:
                await self._execute_from_node(edge.target_node_id, visited.copy())
        else:
            # No hay fallback, propagar error
            logger.error(f"[{self.workflow.company_id}] No error handler for node {node_id}, propagating")
            raise error
    
    # === NODE EXECUTORS === #
    
    async def _execute_node(self, node: WorkflowNode) -> Any:
        """
        Ejecutar un nodo según su tipo.
        Delega a métodos específicos.
        """
        node_type_executors = {
            NodeType.TRIGGER: self._execute_trigger_node,  # ← AGREGAR ESTA LÍNEA
            NodeType.AGENT: self._execute_agent_node,
            NodeType.TOOL: self._execute_tool_node,
            NodeType.CONDITION: self._execute_condition_node,
            NodeType.VARIABLE: self._execute_variable_node,
            NodeType.WAIT: self._execute_wait_node,
            NodeType.WEBHOOK: self._execute_webhook_node,
            NodeType.LOOP: self._execute_loop_node,
            NodeType.PARALLEL: self._execute_parallel_node,
            NodeType.MERGE: self._execute_merge_node,
            NodeType.END: self._execute_end_node
        }
        
        executor = node_type_executors.get(node.type)
        if not executor:
            raise ValueError(f"No executor for node type: {node.type}")
        
        return await executor(node)

    async def _execute_trigger_node(self, node: WorkflowNode) -> Any:
        """
        Ejecutar nodo trigger.
        Los triggers simplemente pasan el contexto inicial.
        """
        logger.debug(f"Executing trigger node: {node.name}")
        
        # Los triggers no modifican el contexto, solo lo activan
        return {
            "status": "success",
            "triggered": True,
            "trigger_type": node.config.get("trigger", "manual"),
            "trigger_keywords": node.config.get("keywords", []),
            "message": f"Workflow triggered by {node.name}"
        }
        
    async def _execute_agent_node(self, node: WorkflowNode) -> str:
        """
        Ejecutar nodo de agente.
        ✅ USA orchestrator.get_response() del sistema existente
        """
        agent_type = node.config.get("agent_type")
        if not agent_type:
            raise ValueError(f"Node {node.id}: agent_type not specified")
        
        # Obtener mensaje del contexto o variable
        user_message = (
            self.state.context.get("user_message") or 
            self.state.context.get("question") or
            self.state.get_variable("user_message") or
            ""
        )
        
        user_id = (
            self.state.context.get("user_id") or
            self.state.get_variable("user_id") or
            "workflow_execution"
        )
        
        logger.info(
            f"[{self.workflow.company_id}] Executing agent '{agent_type}' "
            f"for user {user_id}"
        )

        conversation_id = (
            self.state.context.get("conversation_id") or
            self.state.get_variable("conversation_id") or
            None
        )
        
        logger.info(
            f"[{self.workflow.company_id}] Executing agent '{agent_type}' "
            f"for user {user_id}, conversation: {conversation_id}"
        )
        
        # ✅ USAR EL ORCHESTRATOR EXISTENTE
        # El orchestrator se encarga de rutear al agente correcto
        response, agent_used = self.orchestrator.get_response(
            question=user_message,
            user_id=user_id,
            conversation_id=conversation_id,
            conversation_manager=self.conversation_manager or ConversationManager(),
            media_type="text",
            media_context=None
        )
        
        # Guardar respuesta en variable si está configurado
        output_var = node.config.get("output_variable")
        if output_var:
            self.state.set_variable(output_var, response)
        
        # También guardar en variable estándar del agente
        self.state.set_variable(f"{agent_type}_response", response)
        
        logger.info(
            f"[{self.workflow.company_id}] Agent '{agent_type}' responded "
            f"({len(response)} chars)"
        )
        
        return response
    
    async def _execute_tool_node(self, node: WorkflowNode) -> Dict[str, Any]:
        """
        Ejecutar nodo de tool.
        ✅ USA orchestrator.execute_tool() del sistema existente
        """
        tool_name = node.config.get("tool_name")
        if not tool_name:
            raise ValueError(f"Node {node.id}: tool_name not specified")
        
        params = node.config.get("params", {})
        
        # Resolver variables en params
        resolved_params = self._resolve_variables(params)
        
        logger.info(
            f"[{self.workflow.company_id}] Executing tool '{tool_name}' "
            f"with params: {resolved_params}"
        )
        
        # ✅ USAR EL ORCHESTRATOR EXISTENTE
        result = self.orchestrator.execute_tool(tool_name, resolved_params)
        
        # Guardar output en variable si está configurado
        output_var = node.config.get("output_variable")
        if output_var:
            self.state.set_variable(output_var, result.get("data"))
        
        # También guardar en variable estándar de la tool
        self.state.set_variable(f"{tool_name}_result", result)
        
        if not result.get("success"):
            logger.warning(
                f"[{self.workflow.company_id}] Tool '{tool_name}' failed: "
                f"{result.get('error')}"
            )
        
        return result
    
    async def _execute_condition_node(self, node: WorkflowNode) -> Dict[str, Any]:
        """
        Ejecutar nodo de condición.
        Este nodo no hace nada por sí mismo, solo evalúa la condición en los edges.
        """
        return {"condition_node": True, "evaluated": "in_edges"}
    
    async def _execute_variable_node(self, node: WorkflowNode) -> Dict[str, Any]:
        """Ejecutar nodo de variable (set/get)"""
        action = node.config.get("action", "set")
        
        if action == "set":
            var_name = node.config.get("variable_name")
            var_value = node.config.get("variable_value")
            
            if not var_name:
                raise ValueError(f"Node {node.id}: variable_name required for set action")
            
            # Resolver valor (puede contener {{variables}})
            resolved_value = self._resolve_variables(var_value)
            
            self.state.set_variable(var_name, resolved_value)
            
            return {"variable": var_name, "value": resolved_value, "action": "set"}
        
        elif action == "get":
            var_name = node.config.get("variable_name")
            if not var_name:
                raise ValueError(f"Node {node.id}: variable_name required for get action")
            
            value = self.state.get_variable(var_name)
            
            return {"variable": var_name, "value": value, "action": "get"}
        
        else:
            raise ValueError(f"Node {node.id}: invalid action '{action}'")
    
    async def _execute_wait_node(self, node: WorkflowNode) -> Dict[str, Any]:
        """Ejecutar nodo de espera/delay"""
        delay_ms = node.config.get("delay_ms", 1000)
        
        logger.info(f"[{self.workflow.company_id}] Waiting {delay_ms}ms...")
        
        await asyncio.sleep(delay_ms / 1000)
        
        return {"waited_ms": delay_ms}
    
    async def _execute_webhook_node(self, node: WorkflowNode) -> Dict[str, Any]:
        """Ejecutar nodo de webhook/HTTP request"""
        import aiohttp
        
        url = node.config.get("url")
        if not url:
            raise ValueError(f"Node {node.id}: url required")
        
        method = node.config.get("method", "POST").upper()
        headers = node.config.get("headers", {})
        body = node.config.get("body", {})
        
        # Resolver variables en URL, headers y body
        url = self._resolve_variables(url)
        headers = self._resolve_variables(headers)
        body = self._resolve_variables(body)
        
        logger.info(f"[{self.workflow.company_id}] Webhook {method} {url}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method, 
                    url, 
                    json=body if body else None, 
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    result_data = await resp.json() if resp.content_type == 'application/json' else await resp.text()
                    
                    result = {
                        "status_code": resp.status,
                        "data": result_data,
                        "success": 200 <= resp.status < 300
                    }
                    
                    # Guardar output en variable
                    output_var = node.config.get("output_variable")
                    if output_var:
                        self.state.set_variable(output_var, result_data)
                    
                    return result
        
        except Exception as e:
            logger.error(f"[{self.workflow.company_id}] Webhook error: {e}")
            raise
    
    async def _execute_loop_node(self, node: WorkflowNode) -> Dict[str, Any]:
        """Ejecutar nodo de loop"""
        loop_config = node.config
        max_iterations = loop_config.get("max_iterations", 100)
        loop_variable = loop_config.get("loop_variable", "i")
        exit_condition = loop_config.get("exit_condition")
        
        logger.info(
            f"[{self.workflow.company_id}] Starting loop "
            f"(max {max_iterations} iterations)"
        )
        
        iterations = 0
        for i in range(max_iterations):
            iterations = i + 1
            self.state.set_variable(loop_variable, i)
            
            # Evaluar condición de salida
            if exit_condition:
                from app.workflows.condition_evaluator import ConditionEvaluator
                evaluator = ConditionEvaluator()
                should_exit = evaluator.evaluate(
                    exit_condition,
                    self.state.get_full_context()
                )
                
                if should_exit:
                    logger.info(f"[{self.workflow.company_id}] Loop exit condition met at iteration {i}")
                    break
        
        return {"iterations": iterations, "loop_variable": loop_variable}
    
    async def _execute_parallel_node(self, node: WorkflowNode) -> Dict[str, Any]:
        """
        Ejecutar nodo paralelo.
        Marca que los siguientes branches deben ejecutarse en paralelo.
        """
        return {"parallel": "marker", "message": "Next branches will execute in parallel"}
    
    async def _execute_merge_node(self, node: WorkflowNode) -> Dict[str, Any]:
        """
        Ejecutar nodo merge.
        Espera a que todos los branches paralelos anteriores terminen.
        """
        return {"merged": True, "message": "Parallel branches merged"}
    
    async def _execute_end_node(self, node: WorkflowNode) -> Dict[str, Any]:
        """Ejecutar nodo de fin"""
        logger.info(f"[{self.workflow.company_id}] Workflow reached END node")
        return {"workflow_completed": True}
    
    # === HELPERS === #
    
    def _resolve_variables(self, value: Any) -> Any:
        """
        Resolver variables en un valor.
        Soporta sintaxis: {{variable_name}}
        
        Ejemplos:
        - "Hola {{user_name}}" → "Hola Juan"
        - {"key": "{{value}}"} → {"key": "resolved_value"}
        - ["{{item1}}", "{{item2}}"] → ["val1", "val2"]
        """
        if isinstance(value, str):
            # Buscar {{variable}}
            import re
            pattern = r'\{\{([^}]+)\}\}'
            
            def replacer(match):
                var_name = match.group(1).strip()
                
                # Buscar en variables y context
                var_value = (
                    self.state.get_variable(var_name) or
                    self.state.context.get(var_name)
                )
                
                return str(var_value) if var_value is not None else match.group(0)
            
            return re.sub(pattern, replacer, value)
        
        elif isinstance(value, dict):
            return {k: self._resolve_variables(v) for k, v in value.items()}
        
        elif isinstance(value, list):
            return [self._resolve_variables(item) for item in value]
        
        else:
            return value
