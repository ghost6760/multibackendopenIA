# app/services/agent_tools_service.py

"""
Servicio de adaptadores para integrar ToolExecutor con agentes cognitivos LangGraph.

Este servicio proporciona una capa de adaptación entre:
- Nodos de LangGraph (que trabajan con AgentState)
- ToolExecutor existente (que espera parámetros específicos)

Permite a los agentes cognitivos invocar tools de manera uniforme
manteniendo compatibilidad con la infraestructura existente.
"""

from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import logging
import time

from app.workflows.tool_executor import ToolExecutor
from app.agents._cognitive_base import AgentState, ToolExecutionRecord

logger = logging.getLogger(__name__)


# ============================================================================
# CLASE PRINCIPAL
# ============================================================================

class AgentToolsService:
    """
    Servicio de adaptación para ejecución de tools desde agentes cognitivos.
    
    Proporciona:
    - Ejecución uniforme de tools con manejo de errores
    - Retry automático con backoff exponencial
    - Logging y telemetría
    - Validación de inputs/outputs
    """
    
    def __init__(
        self,
        tool_executor: ToolExecutor,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Args:
            tool_executor: Instancia de ToolExecutor
            max_retries: Máximo de reintentos por tool
            retry_delay: Delay inicial entre reintentos (segundos)
        """
        self.tool_executor = tool_executor
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        logger.info(
            f"AgentToolsService initialized "
            f"(max_retries={max_retries}, retry_delay={retry_delay}s)"
        )
    
    # === EJECUCIÓN DE TOOLS === #
    
    def execute_tool(
        self,
        tool_name: str,
        tool_params: Dict[str, Any],
        state: AgentState,
        retry_on_failure: bool = True
    ) -> Dict[str, Any]:
        """
        Ejecutar una herramienta con retry y manejo de errores.
        
        Args:
            tool_name: Nombre de la herramienta
            tool_params: Parámetros para la herramienta
            state: Estado actual del agente
            retry_on_failure: Si reintentar en caso de fallo
        
        Returns:
            Dict con resultado de ejecución
        """
        start_time = time.time()
        attempt = 0
        last_error = None
        
        while attempt < self.max_retries:
            attempt += 1
            
            try:
                logger.debug(
                    f"Executing tool '{tool_name}' (attempt {attempt}/{self.max_retries})"
                )
                
                # Ejecutar tool a través de ToolExecutor
                result = self.tool_executor.execute(
                    tool_name=tool_name,
                    params=tool_params,
                    company_id=state.get("company_id"),
                    user_id=state.get("user_id")
                )
                
                # Calcular latencia
                latency_ms = (time.time() - start_time) * 1000
                
                # Verificar éxito
                success = result.get("success", False)
                
                if success:
                    logger.info(
                        f"Tool '{tool_name}' executed successfully "
                        f"(latency={latency_ms:.2f}ms, attempt={attempt})"
                    )
                    
                    return {
                        "success": True,
                        "data": result.get("data"),
                        "tool_name": tool_name,
                        "latency_ms": latency_ms,
                        "attempts": attempt
                    }
                else:
                    # Tool retornó error
                    error_msg = result.get("error", "Unknown error")
                    last_error = error_msg
                    
                    logger.warning(
                        f"Tool '{tool_name}' failed: {error_msg} "
                        f"(attempt {attempt}/{self.max_retries})"
                    )
                    
                    # Si no debe reintentar, retornar error
                    if not retry_on_failure or attempt >= self.max_retries:
                        break
                    
                    # Esperar antes de reintentar (backoff exponencial)
                    delay = self.retry_delay * (2 ** (attempt - 1))
                    time.sleep(delay)
                    
            except Exception as e:
                last_error = str(e)
                logger.error(
                    f"Exception executing tool '{tool_name}': {e} "
                    f"(attempt {attempt}/{self.max_retries})"
                )
                
                if not retry_on_failure or attempt >= self.max_retries:
                    break
                
                delay = self.retry_delay * (2 ** (attempt - 1))
                time.sleep(delay)
        
        # Si llegamos aquí, todos los intentos fallaron
        latency_ms = (time.time() - start_time) * 1000
        
        logger.error(
            f"Tool '{tool_name}' failed after {attempt} attempts. "
            f"Last error: {last_error}"
        )
        
        return {
            "success": False,
            "error": last_error or "Tool execution failed",
            "tool_name": tool_name,
            "latency_ms": latency_ms,
            "attempts": attempt
        }
    
    def execute_tools_batch(
        self,
        tools: List[Dict[str, Any]],
        state: AgentState,
        stop_on_error: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Ejecutar múltiples tools en batch.
        
        Args:
            tools: Lista de dicts con tool_name y params
            state: Estado actual del agente
            stop_on_error: Si detener en el primer error
        
        Returns:
            Lista de resultados
        """
        results = []
        
        for tool_config in tools:
            tool_name = tool_config.get("tool_name")
            tool_params = tool_config.get("params", {})
            
            if not tool_name:
                logger.warning("Tool config missing 'tool_name', skipping")
                continue
            
            result = self.execute_tool(
                tool_name=tool_name,
                tool_params=tool_params,
                state=state
            )
            
            results.append(result)
            
            # Detener si hay error y stop_on_error está activado
            if stop_on_error and not result.get("success"):
                logger.warning(
                    f"Stopping batch execution due to error in '{tool_name}'"
                )
                break
        
        return results
    
    # === HELPERS DE VALIDACIÓN === #
    
    def validate_tool_params(
        self,
        tool_name: str,
        params: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Validar parámetros de una herramienta.
        
        Args:
            tool_name: Nombre de la herramienta
            params: Parámetros a validar
        
        Returns:
            Tupla (es_válido, mensaje_error)
        """
        # Importar registry
        from app.agents._agent_tools import get_agent_tools_registry
        
        registry = get_agent_tools_registry()
        return registry.validate_tool_params(tool_name, params)
    
    def is_critical_tool(self, tool_name: str) -> bool:
        """
        Verificar si una tool es crítica.
        
        Args:
            tool_name: Nombre de la herramienta
        
        Returns:
            True si es crítica
        """
        from app.agents._agent_tools import get_agent_tools_registry
        
        registry = get_agent_tools_registry()
        metadata = registry.get_tool_metadata(tool_name)
        
        if metadata:
            return metadata.get("critical", False)
        
        return False
    
    # === NODOS DE LANGGRAPH (HELPERS) === #
    
    def create_tool_execution_node(
        self,
        tool_name: str,
        param_extractor: Optional[Callable[[AgentState], Dict[str, Any]]] = None
    ) -> Callable[[AgentState], AgentState]:
        """
        Crear nodo de LangGraph para ejecutar una tool.
        
        Args:
            tool_name: Nombre de la herramienta
            param_extractor: Función para extraer params del state
                            Si es None, se espera que state tenga key 'tool_params'
        
        Returns:
            Función de nodo compatible con LangGraph
        """
        def tool_node(state: AgentState) -> AgentState:
            """Nodo que ejecuta la tool"""
            # Extraer parámetros
            if param_extractor:
                params = param_extractor(state)
            else:
                params = state.get("tool_params", {})
            
            # Ejecutar tool
            result = self.execute_tool(
                tool_name=tool_name,
                tool_params=params,
                state=state
            )
            
            # Actualizar state
            if "tools_used" not in state:
                state["tools_used"] = []
            if "tool_results" not in state:
                state["tool_results"] = {}
            
            # Crear record
            record: ToolExecutionRecord = {
                "tool_name": tool_name,
                "inputs": params,
                "output": result.get("data") if result.get("success") else None,
                "success": result.get("success", False),
                "error": result.get("error"),
                "latency_ms": result.get("latency_ms", 0.0),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            state["tools_used"].append(record)
            state["tool_results"][tool_name] = result.get("data")
            
            # Si hubo error, marcarlo
            if not result.get("success"):
                state["error"] = result.get("error")
            
            return state
        
        return tool_node
    
    def create_conditional_tool_node(
        self,
        tool_name: str,
        condition: Callable[[AgentState], bool],
        param_extractor: Optional[Callable[[AgentState], Dict[str, Any]]] = None
    ) -> Callable[[AgentState], AgentState]:
        """
        Crear nodo condicional que ejecuta tool solo si se cumple condición.
        
        Args:
            tool_name: Nombre de la herramienta
            condition: Función que determina si ejecutar la tool
            param_extractor: Función para extraer params del state
        
        Returns:
            Función de nodo compatible con LangGraph
        """
        base_node = self.create_tool_execution_node(tool_name, param_extractor)
        
        def conditional_node(state: AgentState) -> AgentState:
            """Nodo condicional"""
            if condition(state):
                logger.debug(f"Condition met, executing tool '{tool_name}'")
                return base_node(state)
            else:
                logger.debug(f"Condition not met, skipping tool '{tool_name}'")
                return state
        
        return conditional_node
    
    # === SAFE-FAIL STRATEGIES === #
    
    def execute_with_fallback(
        self,
        primary_tool: str,
        fallback_tool: str,
        params: Dict[str, Any],
        state: AgentState
    ) -> Dict[str, Any]:
        """
        Ejecutar tool con fallback automático.
        
        Args:
            primary_tool: Tool principal
            fallback_tool: Tool de respaldo
            params: Parámetros
            state: Estado del agente
        
        Returns:
            Resultado de ejecución
        """
        # Intentar primary
        result = self.execute_tool(
            tool_name=primary_tool,
            tool_params=params,
            state=state,
            retry_on_failure=False  # No retry, usar fallback directamente
        )
        
        if result.get("success"):
            return result
        
        # Si falla, intentar fallback
        logger.warning(
            f"Primary tool '{primary_tool}' failed, "
            f"trying fallback '{fallback_tool}'"
        )
        
        fallback_result = self.execute_tool(
            tool_name=fallback_tool,
            tool_params=params,
            state=state
        )
        
        # Marcar que fue fallback
        fallback_result["is_fallback"] = True
        fallback_result["primary_tool"] = primary_tool
        
        return fallback_result
    
    def execute_with_degraded_mode(
        self,
        tool_name: str,
        params: Dict[str, Any],
        state: AgentState,
        degraded_response: Any
    ) -> Dict[str, Any]:
        """
        Ejecutar tool con modo degradado en caso de fallo.
        
        Args:
            tool_name: Nombre de la herramienta
            params: Parámetros
            state: Estado del agente
            degraded_response: Respuesta a retornar si falla
        
        Returns:
            Resultado de ejecución o respuesta degradada
        """
        result = self.execute_tool(
            tool_name=tool_name,
            tool_params=params,
            state=state
        )
        
        if not result.get("success"):
            logger.warning(
                f"Tool '{tool_name}' failed, using degraded mode"
            )
            
            return {
                "success": True,  # Marcar como éxito para no romper flujo
                "data": degraded_response,
                "tool_name": tool_name,
                "is_degraded": True,
                "original_error": result.get("error")
            }
        
        return result


# ============================================================================
# INSTANCIA GLOBAL
# ============================================================================

_service_instance: Optional[AgentToolsService] = None

def get_agent_tools_service(
    tool_executor: Optional[ToolExecutor] = None
) -> AgentToolsService:
    """
    Obtener instancia singleton del servicio.
    
    Args:
        tool_executor: ToolExecutor a usar (solo en primera llamada)
    
    Returns:
        AgentToolsService
    """
    global _service_instance
    
    if _service_instance is None:
        if tool_executor is None:
            raise ValueError(
                "tool_executor must be provided on first call to "
                "get_agent_tools_service()"
            )
        _service_instance = AgentToolsService(tool_executor)
    
    return _service_instance


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "AgentToolsService",
    "get_agent_tools_service"
]
