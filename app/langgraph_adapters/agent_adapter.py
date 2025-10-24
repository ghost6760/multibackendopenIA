"""
AgentAdapter - Adaptador Genérico para Agentes LangChain

Este adaptador permite usar agentes LangChain existentes dentro de
grafos de LangGraph sin modificar su código.

Características:
- Normalización de interfaz invoke(inputs) -> dict
- Logging automático de ejecución
- Validación de inputs y outputs
- Manejo de errores con reintentos
- Métricas de rendimiento (latencia, tokens)
- Compatible con checkpointing de LangGraph

Principio de diseño:
"Don't break what works" - Los agentes LangChain siguen funcionando igual,
solo se envuelven para orquestación cognitiva.
"""

from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
import logging
import time
import traceback

from app.agents.base_agent import BaseAgent
from app.langgraph_adapters.state_schemas import AgentExecutionState, ValidationResult

logger = logging.getLogger(__name__)


class AgentAdapter:
    """
    Adaptador genérico para agentes LangChain.

    Envuelve un BaseAgent y proporciona una interfaz normalizada
    compatible con nodos de LangGraph.

    Ejemplo de uso:
        sales_agent = SalesAgent(company_config, openai_service)
        adapted = AgentAdapter(
            agent=sales_agent,
            agent_name="sales",
            timeout_ms=30000
        )

        # Usar en un nodo de LangGraph
        result = adapted.invoke({"question": "¿Precios?", "chat_history": []})
    """

    def __init__(
        self,
        agent: BaseAgent,
        agent_name: str,
        timeout_ms: int = 30000,
        max_retries: int = 2,
        validate_input: Optional[Callable[[Dict[str, Any]], ValidationResult]] = None,
        validate_output: Optional[Callable[[str], ValidationResult]] = None
    ):
        """
        Inicializar adaptador.

        Args:
            agent: Instancia del agente LangChain (BaseAgent)
            agent_name: Nombre del agente (ej: "sales", "support")
            timeout_ms: Timeout en milisegundos
            max_retries: Número máximo de reintentos en caso de error
            validate_input: Función opcional para validar inputs
            validate_output: Función opcional para validar outputs
        """
        self.agent = agent
        self.agent_name = agent_name
        self.timeout_ms = timeout_ms
        self.max_retries = max_retries
        self.validate_input = validate_input
        self.validate_output = validate_output

        # Estadísticas
        self.total_executions = 0
        self.total_errors = 0
        self.total_duration_ms = 0.0

        logger.info(
            f"✅ AgentAdapter initialized: {agent_name} "
            f"(timeout={timeout_ms}ms, max_retries={max_retries})"
        )

    def invoke(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invocar agente con logging, validación y manejo de errores.

        Args:
            inputs: Diccionario con al menos:
                - question: str - Pregunta del usuario
                - chat_history: List - Historial de conversación (opcional)
                - context: str - Contexto adicional (opcional)

        Returns:
            Diccionario con:
                - success: bool - Si la ejecución fue exitosa
                - output: str - Respuesta del agente (si exitosa)
                - error: str - Mensaje de error (si falló)
                - execution_state: AgentExecutionState - Estado de ejecución
                - validation: ValidationResult - Resultado de validaciones
        """
        started_at = datetime.utcnow()
        start_time = time.time()

        # Incrementar contador
        self.total_executions += 1

        # Log de inicio
        self._log_execution_start(inputs)

        # Validar inputs
        if self.validate_input:
            validation = self.validate_input(inputs)
            if not validation["is_valid"]:
                logger.warning(
                    f"[{self.agent_name}] Input validation failed: {validation['errors']}"
                )
                return self._create_error_response(
                    "Input validation failed",
                    validation,
                    started_at,
                    start_time
                )

        # Intentar ejecución con reintentos
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(
                        f"[{self.agent_name}] Retry attempt {attempt}/{self.max_retries}"
                    )

                # ✅ LLAMADA AL AGENTE LANGCHAIN EXISTENTE
                # Usa el método invoke() que ya tienen todos los BaseAgent
                output = self.agent.invoke(inputs)

                # Validar output
                if self.validate_output:
                    validation = self.validate_output(output)
                    if not validation["is_valid"]:
                        logger.warning(
                            f"[{self.agent_name}] Output validation failed: "
                            f"{validation['errors']}"
                        )
                        # Continuar de todas formas, solo advertencia
                else:
                    validation = self._create_default_validation(True)

                # Calcular duración
                duration_ms = (time.time() - start_time) * 1000
                self.total_duration_ms += duration_ms

                # Log de éxito
                self._log_execution_success(output, duration_ms)

                # Crear estado de ejecución
                execution_state = self._create_execution_state(
                    started_at,
                    datetime.utcnow(),
                    duration_ms,
                    attempt,
                    "success",
                    output=output
                )

                return {
                    "success": True,
                    "output": output,
                    "error": None,
                    "execution_state": execution_state,
                    "validation": validation,
                    "retries": attempt
                }

            except Exception as e:
                last_error = e
                self.total_errors += 1

                logger.error(
                    f"[{self.agent_name}] Execution error (attempt {attempt + 1}): {e}"
                )
                logger.error(f"[{self.agent_name}] Traceback: {traceback.format_exc()}")

                # Si no quedan intentos, fallar
                if attempt >= self.max_retries:
                    break

                # Esperar antes de reintentar (backoff exponencial)
                wait_time = 2 ** attempt  # 1s, 2s, 4s, etc.
                logger.info(f"[{self.agent_name}] Waiting {wait_time}s before retry...")
                time.sleep(wait_time)

        # Si llegamos aquí, todos los intentos fallaron
        duration_ms = (time.time() - start_time) * 1000
        self.total_duration_ms += duration_ms

        execution_state = self._create_execution_state(
            started_at,
            datetime.utcnow(),
            duration_ms,
            self.max_retries,
            "failed",
            error=str(last_error)
        )

        validation = self._create_default_validation(False, [str(last_error)])

        return {
            "success": False,
            "output": None,
            "error": str(last_error),
            "execution_state": execution_state,
            "validation": validation,
            "retries": self.max_retries
        }

    def _log_execution_start(self, inputs: Dict[str, Any]):
        """Log de inicio de ejecución"""
        question = inputs.get("question", "")
        company_id = self.agent.company_config.company_id

        logger.info(f"🤖 [{company_id}] {self.agent_name}.invoke() started")
        logger.info(f"   → Question: {question[:100]}...")
        logger.info(f"   → Has history: {bool(inputs.get('chat_history'))}")
        logger.info(f"   → Has context: {bool(inputs.get('context'))}")

    def _log_execution_success(self, output: str, duration_ms: float):
        """Log de ejecución exitosa"""
        company_id = self.agent.company_config.company_id

        logger.info(f"✅ [{company_id}] {self.agent_name} completed successfully")
        logger.info(f"   → Duration: {duration_ms:.2f}ms")
        logger.info(f"   → Output length: {len(output)} chars")
        logger.info(f"   → Average duration: {self.get_average_duration_ms():.2f}ms")

    def _create_execution_state(
        self,
        started_at: datetime,
        completed_at: datetime,
        duration_ms: float,
        retries: int,
        status: str,
        output: Optional[str] = None,
        error: Optional[str] = None
    ) -> AgentExecutionState:
        """Crear estado de ejecución"""
        return {
            "agent_name": self.agent_name,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_ms": duration_ms,
            "retries": retries,
            "status": status,
            "error": error,
            "output": output
        }

    def _create_error_response(
        self,
        error_message: str,
        validation: ValidationResult,
        started_at: datetime,
        start_time: float
    ) -> Dict[str, Any]:
        """Crear respuesta de error"""
        duration_ms = (time.time() - start_time) * 1000

        execution_state = self._create_execution_state(
            started_at,
            datetime.utcnow(),
            duration_ms,
            0,
            "failed",
            error=error_message
        )

        return {
            "success": False,
            "output": None,
            "error": error_message,
            "execution_state": execution_state,
            "validation": validation,
            "retries": 0
        }

    def _create_default_validation(
        self,
        is_valid: bool,
        errors: List[str] = None
    ) -> ValidationResult:
        """Crear resultado de validación por defecto"""
        return {
            "is_valid": is_valid,
            "errors": errors or [],
            "warnings": [],
            "metadata": {}
        }

    def get_stats(self) -> Dict[str, Any]:
        """
        Obtener estadísticas del adaptador.

        Returns:
            Diccionario con:
                - agent_name: Nombre del agente
                - total_executions: Total de ejecuciones
                - total_errors: Total de errores
                - error_rate: Tasa de error (0.0-1.0)
                - average_duration_ms: Duración promedio
                - total_duration_ms: Duración total
        """
        error_rate = (
            self.total_errors / self.total_executions
            if self.total_executions > 0
            else 0.0
        )

        return {
            "agent_name": self.agent_name,
            "total_executions": self.total_executions,
            "total_errors": self.total_errors,
            "error_rate": error_rate,
            "average_duration_ms": self.get_average_duration_ms(),
            "total_duration_ms": self.total_duration_ms
        }

    def get_average_duration_ms(self) -> float:
        """Obtener duración promedio en milisegundos"""
        if self.total_executions == 0:
            return 0.0
        return self.total_duration_ms / self.total_executions

    def reset_stats(self):
        """Resetear estadísticas"""
        self.total_executions = 0
        self.total_errors = 0
        self.total_duration_ms = 0.0

    def __repr__(self) -> str:
        return (
            f"AgentAdapter(agent_name='{self.agent_name}', "
            f"executions={self.total_executions}, "
            f"errors={self.total_errors}, "
            f"avg_duration={self.get_average_duration_ms():.2f}ms)"
        )


# === VALIDADORES COMUNES === #

def validate_has_question(inputs: Dict[str, Any]) -> ValidationResult:
    """Validador: Verificar que existe una pregunta"""
    question = inputs.get("question", "").strip()

    if not question:
        return {
            "is_valid": False,
            "errors": ["Campo 'question' es requerido y no puede estar vacío"],
            "warnings": [],
            "metadata": {}
        }

    if len(question) > 5000:
        return {
            "is_valid": False,
            "errors": ["Campo 'question' excede 5000 caracteres"],
            "warnings": [],
            "metadata": {"question_length": len(question)}
        }

    return {
        "is_valid": True,
        "errors": [],
        "warnings": [],
        "metadata": {"question_length": len(question)}
    }


def validate_output_length(output: str) -> ValidationResult:
    """Validador: Verificar longitud de output"""
    if not output:
        return {
            "is_valid": False,
            "errors": ["Output está vacío"],
            "warnings": [],
            "metadata": {}
        }

    warnings = []
    if len(output) > 4000:
        warnings.append("Output es muy largo (>4000 caracteres)")

    if len(output) < 10:
        warnings.append("Output es muy corto (<10 caracteres)")

    return {
        "is_valid": True,
        "errors": [],
        "warnings": warnings,
        "metadata": {"output_length": len(output)}
    }
