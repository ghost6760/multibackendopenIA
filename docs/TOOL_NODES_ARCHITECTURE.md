# Tool Nodes Architecture - Separation of Concerns

## Overview

Este documento explica la arquitectura correcta para separar **procesamiento de lenguaje natural** (Agentes) de **ejecución de acciones** (Tool Nodes).

---

## ❌ Arquitectura Incorrecta (Anti-Pattern)

### Problema: Agentes con Acceso Directo a Servicios

```python
class ScheduleAgent:
    def __init__(self, calendar_service, email_service):
        self.calendar_service = calendar_service  # ❌ Acceso directo
        self.email_service = email_service        # ❌ Acceso directo

    def process(self, user_message):
        # Agente procesa Y ejecuta acciones
        slots = self.calendar_service.check_availability(date)  # ❌
        booking = self.calendar_service.create_booking(...)     # ❌
        self.email_service.send_email(...)                      # ❌
```

### Problemas de Este Enfoque

| Problema | Descripción | Impacto |
|----------|-------------|---------|
| **Sin Audit Trail** | Las acciones NO se registran en AuditManager | ❌ No hay trazabilidad |
| **Sin Compensación** | No se puede hacer rollback si algo falla | ❌ No hay recuperación de errores |
| **Sin Control Centralizado** | Cada agente ejecuta acciones de forma diferente | ❌ Inconsistencia |
| **Difícil de Testear** | Las acciones están mezcladas con lógica de NLP | ❌ Tests complejos |
| **Violación de SRP** | El agente tiene múltiples responsabilidades | ❌ Acoplamiento |

---

## ✅ Arquitectura Correcta (Tool Nodes Pattern)

### Principio: Separación de Responsabilidades

```
┌─────────────────────────────────────────────────────────────┐
│                       StateGraph                             │
│                                                              │
│  ┌──────────────┐         ┌────────────────┐               │
│  │   Agents     │────────▶│   Tool Nodes   │               │
│  │              │         │                │               │
│  │ • Sales      │         │ • check_avail  │               │
│  │ • Schedule   │         │ • create_book  │               │
│  │ • Support    │         │ • send_email   │               │
│  │ • Emergency  │         │ • create_tick  │               │
│  └──────────────┘         └────────────────┘               │
│        │                          │                         │
│        │ (NLP only)               │ (Actions only)          │
│        ▼                          ▼                         │
│  Extract info              Execute via ToolExecutor         │
│  Put in shared_context     ✅ Audit Trail                   │
│                            ✅ Compensation                   │
│                            ✅ Centralized Control           │
└─────────────────────────────────────────────────────────────┘
```

### Implementación Correcta

#### 1. Agente SIN Acceso a Servicios

```python
class ScheduleAgent:
    """
    Agente que SOLO procesa lenguaje natural.
    NO ejecuta acciones directamente.
    """

    def __init__(self, llm, company_config):
        self.llm = llm
        self.company_config = company_config
        # ✅ NO tiene calendar_service
        # ✅ NO tiene email_service

    def process(self, user_message, shared_context):
        """
        Solo extrae información y la pone en shared_context.
        NO ejecuta acciones.
        """
        # Procesar con LLM
        response = self.llm.process(user_message)

        # Extraer información estructurada
        date = extract_date(response)
        time = extract_time(response)
        treatment = extract_treatment(response)

        # ✅ Poner en shared_context para que Tool Nodes ejecuten
        schedule_info = {
            "needs_availability_check": True,  # Flag para tool node
            "date": date,
            "time": time,
            "treatment": treatment
        }

        return {
            "agent_response": response,
            "shared_context": {"schedule_info": schedule_info}
        }
```

#### 2. Tool Nodes Ejecutan Acciones

```python
def check_availability_tool(state):
    """
    Tool Node que ejecuta la acción REAL.

    - Extrae info del shared_context (puesta por el agente)
    - Ejecuta via ToolExecutor
    - ✅ Se registra en Audit Trail automáticamente
    - ✅ Tiene retry y error handling
    - Actualiza shared_context con resultados
    """
    schedule_info = state["shared_context"]["schedule_info"]

    # Ejecutar via ToolExecutor (con audit trail)
    result = tool_executor.execute_tool(
        tool_name="google_calendar",
        parameters={
            "action": "check_availability",
            "date": schedule_info["date"],
            "treatment": schedule_info["treatment"]
        },
        user_id=state["user_id"],
        agent_name="schedule_agent"
    )
    # ✅ Audit trail automático
    # ✅ Duration tracking
    # ✅ Error handling

    # Actualizar shared_context con resultados
    schedule_info["availability_checked"] = True
    schedule_info["available_slots"] = result["data"]["available_slots"]

    return state
```

#### 3. StateGraph Orquesta

```python
# Flujo completo orquestado por StateGraph

User: "Quiero cita para botox el 20 de enero a las 10am"
  │
  ├─▶ Router Agent → Classify: "schedule"
  │
  ├─▶ Schedule Agent → Extract info
  │       └─▶ shared_context = {
  │               "schedule_info": {
  │                   "needs_availability_check": True,
  │                   "date": "2025-01-20",
  │                   "time": "10:00",
  │                   "treatment": "Botox"
  │               }
  │           }
  │
  ├─▶ Conditional Routing → Detect "needs_availability_check"
  │
  ├─▶ Tool Node: check_availability
  │       ├─▶ ToolExecutor.execute_tool("google_calendar", ...)
  │       │   ✅ AuditManager.log_action() → Audit trail
  │       │   ✅ calendar_service.check_availability()
  │       │   ✅ AuditManager.mark_success()
  │       └─▶ shared_context["available_slots"] = ["10:00", "11:00", "15:00"]
  │
  ├─▶ Schedule Agent (2nd pass) → Confirmar con usuario
  │       └─▶ shared_context["has_appointment"] = True
  │
  ├─▶ Tool Node: execute_booking
  │       ├─▶ CompensationOrchestrator.create_saga()
  │       ├─▶ ToolExecutor.execute_tool("google_calendar", action="create_booking")
  │       │   ✅ Audit trail (compensable)
  │       └─▶ Si falla → rollback automático
  │
  ├─▶ Tool Node: send_notification
  │       └─▶ ToolExecutor.execute_tool("send_email", ...)
  │           ✅ Audit trail
  │
  └─▶ Response: "✅ Su cita ha sido confirmada..."
```

---

## Beneficios del Tool Nodes Pattern

| Beneficio | Descripción |
|-----------|-------------|
| **✅ Audit Trail Automático** | Todas las acciones se registran en Redis con metadata completa |
| **✅ Compensación Automática** | Rollback con Saga pattern si algo falla |
| **✅ Control Centralizado** | Todas las acciones pasan por ToolExecutor |
| **✅ Testeable** | Agentes y Tool Nodes se testean por separado |
| **✅ Single Responsibility** | Agentes = NLP, Tool Nodes = Actions |
| **✅ Reusabilidad** | Tool nodes pueden ser usados por cualquier agente |
| **✅ Observabilidad** | Métricas centralizadas de duración, errores, etc. |

---

## Comparación: Antes vs Después

### Antes (Acceso Directo) ❌

```python
# Schedule Agent con acceso directo
class ScheduleAgent:
    def process(self, message):
        # Mezcla NLP con acciones
        slots = self.calendar_service.check_availability(date)  # ❌
        booking = self.calendar_service.create_booking(...)     # ❌
        self.email_service.send_email(...)                      # ❌
        # ❌ Sin audit trail
        # ❌ Sin compensación
        # ❌ Sin retry
```

**Problemas:**
- No hay audit trail
- No hay compensación si email falla (booking ya está creado)
- No hay retry automático
- Difícil de testear
- Violación de SRP

### Después (Tool Nodes) ✅

```python
# Schedule Agent SIN acceso directo
class ScheduleAgent:
    def process(self, message):
        # Solo NLP
        date, time, treatment = self.extract_info(message)
        return {
            "shared_context": {
                "schedule_info": {
                    "needs_availability_check": True,
                    "date": date,
                    "time": time
                }
            }
        }

# Tool Nodes ejecutan acciones
def check_availability_tool(state):
    tool_executor.execute_tool("google_calendar", ...)  # ✅ Audit

def execute_booking_tool(state):
    saga = orchestrator.create_saga(...)
    saga.add_action(
        executor=...,
        compensator=...  # ✅ Rollback si falla
    )

def send_notification_tool(state):
    tool_executor.execute_tool("send_email", ...)  # ✅ Audit
```

**Beneficios:**
- ✅ Audit trail completo
- ✅ Compensación automática (Saga)
- ✅ Retry con exponential backoff
- ✅ Fácil de testear
- ✅ Single Responsibility Principle

---

## Tool Nodes Disponibles

### Calendar Tools

| Tool Node | Descripción | Compensable | Audit Type |
|-----------|-------------|-------------|------------|
| `check_availability` | Verifica slots disponibles en calendario | No | `api_call` |
| `execute_booking` | Crea evento en Google Calendar | **Sí** | `booking` |

### Notification Tools

| Tool Node | Descripción | Compensable | Audit Type |
|-----------|-------------|-------------|------------|
| `send_notification` | Envía email de confirmación | No | `notification` |

### Support Tools

| Tool Node | Descripción | Compensable | Audit Type |
|-----------|-------------|-------------|------------|
| `create_ticket` | Crea ticket de soporte | Sí | `ticket` |

---

## Flujo Detallado: Booking con Disponibilidad

```
┌─────────────────────────────────────────────────────────────────┐
│ User: "Quiero cita para botox el 20 de enero a las 10am"        │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
           ┌───────────────────────┐
           │   Router Agent         │
           │   Intent: "schedule"   │
           └───────────┬───────────┘
                       │
                       ▼
           ┌───────────────────────────────────────┐
           │   Schedule Agent (Pass 1)              │
           │   • Extrae: date, time, treatment      │
           │   • Pone en shared_context:            │
           │     needs_availability_check = True    │
           └───────────┬───────────────────────────┘
                       │
                       ▼
           ┌───────────────────────────────────────┐
           │   Conditional Routing                  │
           │   Detecta: needs_availability_check    │
           └───────────┬───────────────────────────┘
                       │
                       ▼
           ┌───────────────────────────────────────────────┐
           │   Tool Node: check_availability               │
           │   ✅ ToolExecutor.execute_tool()              │
           │   ✅ AuditManager.log_action()                │
           │   ✅ calendar_service.check_availability()    │
           │   ✅ AuditManager.mark_success()              │
           │   ✅ shared_context["available_slots"] = [...] │
           └───────────┬───────────────────────────────────┘
                       │
                       ▼
           ┌───────────────────────────────────────┐
           │   Schedule Agent (Pass 2)              │
           │   • Lee available_slots                │
           │   • Confirma con usuario               │
           │   • shared_context:                    │
           │     has_appointment = True             │
           └───────────┬───────────────────────────┘
                       │
                       ▼
           ┌───────────────────────────────────────────────┐
           │   Tool Node: execute_booking                  │
           │   ✅ CompensationOrchestrator.create_saga()   │
           │   ✅ add_action(create_booking, compensator)  │
           │   ✅ ToolExecutor.execute_tool()              │
           │   ✅ AuditManager.log_action(compensable)     │
           │   ✅ calendar_service.create_booking()        │
           │   ✅ Si falla → rollback automático           │
           └───────────┬───────────────────────────────────┘
                       │
                       ▼
           ┌───────────────────────────────────────────────┐
           │   Tool Node: send_notification               │
           │   ✅ ToolExecutor.execute_tool()              │
           │   ✅ AuditManager.log_action()                │
           │   ✅ email_service.send_template_email()      │
           │   ✅ AuditManager.mark_success()              │
           └───────────┬───────────────────────────────────┘
                       │
                       ▼
           ┌────────────────────────────────────────┐
           │   Response al Usuario                   │
           │   "✅ Su cita ha sido confirmada para   │
           │    botox el 20 de enero a las 10:00 AM" │
           └────────────────────────────────────────┘
```

---

## Cómo Implementar un Nuevo Tool Node

### Paso 1: Agregar Tool a ToolsLibrary

```python
# app/workflows/tools_library.py
tools_catalog = {
    "my_new_tool": ToolDefinition(
        name="my_new_tool",
        category="actions",
        description="Description of what this tool does",
        provider="internal",
        parameters={"param1": "string", "param2": "int"},
        output_type="dict"
    )
}
```

### Paso 2: Implementar en ToolExecutor

```python
# app/workflows/tool_executor.py
def _execute_my_new_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute my new tool"""
    # Implementation here
    result = self.some_service.do_action(params)

    return {
        "success": True,
        "tool": "my_new_tool",
        "data": result
    }

# Add to execute_tool() routing
elif tool_name == "my_new_tool":
    result = self._execute_my_new_tool(parameters)
```

### Paso 3: Agregar Tool Node en StateGraph

```python
# app/langgraph_adapters/orchestrator_graph.py

# 1. Agregar nodo
workflow.add_node("my_new_tool", self._my_new_tool_node)

# 2. Agregar routing
def _should_execute_tools_or_continue(self, state):
    if state.get("needs_my_tool"):
        return "my_new_tool"
    # ... rest of logic

# 3. Agregar edge
workflow.add_edge("my_new_tool", "validate_cross_agent_info")

# 4. Implementar método del nodo
def _my_new_tool_node(self, state):
    """Tool node for my new tool"""
    result = self.tool_executor.execute_tool(
        tool_name="my_new_tool",
        parameters=...,
        user_id=state["user_id"]
    )
    # ✅ Audit trail automático
    # Update state with results
    return state
```

---

## Testing Tool Nodes

### Unit Test para Agente (Sin Acciones)

```python
def test_schedule_agent_extracts_info():
    """Agente solo extrae información, NO ejecuta acciones"""
    agent = ScheduleAgent(llm, config)

    result = agent.process("Quiero cita para botox el 20 de enero")

    # Assert: Extrae info correctamente
    assert result["shared_context"]["schedule_info"]["date"] == "2025-01-20"
    assert result["shared_context"]["schedule_info"]["treatment"] == "Botox"

    # Assert: NO llamó servicios
    # (no hay calendar_service para llamar)
```

### Integration Test para Tool Node

```python
def test_check_availability_tool_node():
    """Tool node ejecuta acción via ToolExecutor"""
    # Setup
    tool_executor = ToolExecutor(...)
    tool_executor.set_calendar_service(mock_calendar)

    state = {
        "shared_context": {
            "schedule_info": {
                "date": "2025-01-20",
                "needs_availability_check": True
            }
        }
    }

    # Execute
    result = check_availability_tool(state)

    # Assert: Tool fue ejecutado
    assert result["shared_context"]["schedule_info"]["availability_checked"]
    assert len(result["shared_context"]["schedule_info"]["available_slots"]) > 0

    # Assert: Audit trail fue creado
    assert audit_manager.log_action.called
```

---

## Conclusión

La arquitectura de **Tool Nodes** separa correctamente las responsabilidades:

1. **Agentes** → Solo procesan lenguaje natural y extraen información
2. **Tool Nodes** → Ejecutan acciones REALES via ToolExecutor
3. **StateGraph** → Orquesta el flujo entre agentes y tool nodes

Esto proporciona:
- ✅ Audit trail completo
- ✅ Compensación automática
- ✅ Control centralizado
- ✅ Testabilidad
- ✅ Observabilidad

**Regla de oro:** Si una operación modifica estado externo (DB, API, Calendar, Email), debe ejecutarse en un Tool Node, NO directamente en el agente.
