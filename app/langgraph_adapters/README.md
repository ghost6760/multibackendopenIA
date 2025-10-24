# 🧠 Arquitectura Híbrida LangChain + LangGraph

## 📋 Tabla de Contenidos

- [Visión General](#-visión-general)
- [Arquitectura](#-arquitectura)
- [Componentes](#-componentes)
- [Flujo de Ejecución](#-flujo-de-ejecución)
- [Guía de Uso](#-guía-de-uso)
- [Compatibilidad](#-compatibilidad)
- [Ventajas](#-ventajas)
- [Ejemplos](#-ejemplos)

---

## 🎯 Visión General

Este módulo implementa una **arquitectura híbrida** que combina lo mejor de LangChain y LangGraph:

- **Agentes simples (LangChain)**: Permanecen ligeros y eficientes
- **Orquestación cognitiva (LangGraph)**: Gestión de estado, validaciones, routing condicional

### Principio de Diseño

> **"Don't break what works"** - Los agentes existentes NO se modifican, solo se envuelven para orquestación cognitiva.

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                    MultiAgentOrchestratorGraph                  │
│                       (LangGraph StateGraph)                    │
└─────────────────────────────────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │   AgentAdapter Layer    │
                    │   (Normalización)       │
                    └────────────┬────────────┘
                                 │
        ┌───────────┬────────────┼────────────┬───────────┐
        │           │            │            │           │
   ┌────▼────┐ ┌───▼────┐ ┌────▼────┐ ┌────▼────┐ ┌────▼────┐
   │ Router  │ │ Sales  │ │ Support │ │Emergency│ │Schedule │
   │ Agent   │ │ Agent  │ │ Agent   │ │ Agent   │ │ Agent   │
   └─────────┘ └────────┘ └─────────┘ └─────────┘ └─────────┘
         Agentes LangChain Existentes (Sin modificar)
```

### Capas de la Arquitectura

1. **Capa de Grafo (LangGraph)**
   - Gestión de estado compartido
   - Routing condicional
   - Validaciones y reintentos
   - Logging y métricas

2. **Capa de Adaptación (AgentAdapter)**
   - Normaliza interfaz `invoke(inputs) → dict`
   - Manejo de errores con reintentos
   - Logging automático
   - Validación de inputs/outputs

3. **Capa de Agentes (LangChain)**
   - Agentes especializados existentes
   - Sin cambios en su implementación
   - Siguen usando RAG, prompts personalizados, etc.

---

## 🧩 Componentes

### 1. AgentAdapter

**Ubicación**: `app/langgraph_adapters/agent_adapter.py`

**Propósito**: Envolver agentes LangChain para uso en LangGraph

**Características**:
- ✅ Normalización de interfaz
- ✅ Logging automático (inicio, éxito, errores)
- ✅ Validación de inputs y outputs
- ✅ Reintentos con backoff exponencial
- ✅ Métricas de rendimiento (latencia, tasa de error)

**Ejemplo**:
```python
from app.langgraph_adapters import AgentAdapter

# Crear agente LangChain existente
sales_agent = SalesAgent(company_config, openai_service)

# Envolverlo en adaptador
adapted = AgentAdapter(
    agent=sales_agent,
    agent_name="sales",
    timeout_ms=30000,
    max_retries=2
)

# Usar en grafo o standalone
result = adapted.invoke({"question": "¿Precios?", "chat_history": []})
# → {"success": True, "output": "...", "execution_state": {...}}
```

### 2. MultiAgentOrchestratorGraph

**Ubicación**: `app/langgraph_adapters/orchestrator_graph.py`

**Propósito**: Orquestar múltiples agentes mediante un StateGraph

**Flujo del Grafo**:
```
START
  ↓
[Validate Input] → validar pregunta y contexto
  ↓
[Classify Intent] → usar RouterAgent
  ↓
[Route to Agent] → routing condicional
  ↓
[SALES | SUPPORT | EMERGENCY | SCHEDULE]
  ↓
[Validate Output] → verificar respuesta
  ↓
[Retry?] → reintentar si falló
  ↓
END
```

**Ejemplo**:
```python
from app.langgraph_adapters.orchestrator_graph import MultiAgentOrchestratorGraph

# Crear agentes
router = RouterAgent(company_config, openai_service)
sales = SalesAgent(company_config, openai_service)
support = SupportAgent(company_config, openai_service)
emergency = EmergencyAgent(company_config, openai_service)
schedule = ScheduleAgent(company_config, openai_service)

# Crear orquestador
orchestrator = MultiAgentOrchestratorGraph(
    router_agent=router,
    agents={
        "sales": sales,
        "support": support,
        "emergency": emergency,
        "schedule": schedule
    },
    company_id=company_config.company_id
)

# Ejecutar (compatible con API actual)
response, intent = orchestrator.get_response(
    question="¿Cuánto cuesta el botox?",
    user_id="user123",
    chat_history=[]
)
```

### 3. ScheduleAgentGraph

**Ubicación**: `app/langgraph_adapters/schedule_agent_graph.py`

**Propósito**: Ejemplo de agente con grafo interno para validaciones paso a paso

**Flujo del Grafo**:
```
START
  ↓
[Extract Info] → fecha, tratamiento, paciente
  ↓
[Validate Info] → validar extracciones
  ↓
[Check Availability] → verificar horarios disponibles
  ↓
[Generate Response] → usar LLM del agente
  ↓
END
```

**Ventajas**:
- Separación clara de responsabilidades
- Estado compartido entre pasos
- Validaciones explícitas
- Fácil agregar nuevos pasos (pagos, confirmación, etc.)

### 4. State Schemas

**Ubicación**: `app/langgraph_adapters/state_schemas.py`

**Propósito**: Definir esquemas de estado tipados

**Schemas Principales**:

#### OrchestratorState
```python
{
    "question": str,           # Pregunta del usuario
    "user_id": str,           # ID del usuario
    "company_id": str,        # ID de la empresa
    "intent": str,            # Intención (SALES, SUPPORT, etc.)
    "confidence": float,      # Confianza (0.0-1.0)
    "agent_response": str,    # Respuesta del agente
    "executions": List,       # Historial de ejecuciones
    "validations": List,      # Validaciones realizadas
    "errors": List,           # Errores ocurridos
    "retries": int,           # Contador de reintentos
    ...
}
```

#### ScheduleAgentState
```python
{
    "question": str,
    "extracted_date": str,           # Fecha extraída
    "extracted_treatment": str,      # Tratamiento extraído
    "date_valid": bool,             # ¿Fecha válida?
    "treatment_valid": bool,        # ¿Tratamiento válido?
    "patient_info_complete": bool,  # ¿Info completa?
    "available_slots": List,        # Horarios disponibles
    "agent_response": str,          # Respuesta final
    "current_step": str,            # Paso actual
    ...
}
```

---

## 🔄 Flujo de Ejecución

### Flujo Completo del MultiAgentOrchestrator

```
Usuario: "¿Cuánto cuesta el botox?"
   │
   ↓
┌──────────────────────────────┐
│ validate_input               │  ← Validar pregunta, user_id, company_id
│ ✅ OK                        │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ classify_intent              │  ← Ejecutar RouterAgent (LangChain)
│ Intent: SALES                │     via AgentAdapter
│ Confidence: 0.95             │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ route_to_agent               │  ← Routing condicional
│ → sales (confidence > 0.7)   │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ execute_sales                │  ← Ejecutar SalesAgent (LangChain)
│ with RAG context             │     via AgentAdapter
│ ✅ Response generated        │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ validate_output              │  ← Validar respuesta
│ ✅ Length OK, no errors      │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ END                          │  ← Retornar respuesta
│ Response: "El botox..."      │
│ Agent used: sales            │
└──────────────────────────────┘
```

### Flujo con Reintentos

```
Usuario: "Emergencia!"
   │
   ↓
[validate_input] ✅
   ↓
[classify_intent] → Intent: EMERGENCY
   ↓
[execute_emergency] ❌ Error (timeout)
   ↓
[validate_output] → should_retry = True
   ↓
[handle_retry] → retries = 1, should_escalate = True
   ↓
[execute_support] ✅ Fallback al agente de soporte
   ↓
[validate_output] ✅
   ↓
END → Response del agente de soporte
```

---

## 📖 Guía de Uso

### Uso Básico: Reemplazar MultiAgentOrchestrator Actual

**Antes (LangChain puro)**:
```python
from app.services.multi_agent_orchestrator import MultiAgentOrchestrator

orchestrator = MultiAgentOrchestrator(
    company_id="company_123",
    openai_service=openai_service
)

response, intent = orchestrator.get_response(
    question="¿Precios?",
    user_id="user123",
    conversation_manager=conversation_manager
)
```

**Después (LangChain + LangGraph)**:
```python
from app.langgraph_adapters.orchestrator_graph import MultiAgentOrchestratorGraph
from app.agents import (
    RouterAgent, SalesAgent, SupportAgent, EmergencyAgent, ScheduleAgent
)

# Crear agentes (igual que antes)
router = RouterAgent(company_config, openai_service)
sales = SalesAgent(company_config, openai_service)
support = SupportAgent(company_config, openai_service)
emergency = EmergencyAgent(company_config, openai_service)
schedule = ScheduleAgent(company_config, openai_service)

# Crear orquestador con grafo
orchestrator = MultiAgentOrchestratorGraph(
    router_agent=router,
    agents={
        "sales": sales,
        "support": support,
        "emergency": emergency,
        "schedule": schedule
    },
    company_id=company_config.company_id
)

# ✅ API COMPATIBLE: Llamada exactamente igual
response, intent = orchestrator.get_response(
    question="¿Precios?",
    user_id="user123",
    chat_history=[]
)
```

### Uso Avanzado: Crear un Agente con Grafo Interno

**Ejemplo: ScheduleAgent con Validaciones**

```python
from app.langgraph_adapters.schedule_agent_graph import ScheduleAgentGraph
from app.agents.schedule_agent import ScheduleAgent

# Crear agente normal
schedule_agent = ScheduleAgent(company_config, openai_service)

# Envolverlo en grafo
schedule_graph = ScheduleAgentGraph(
    schedule_agent=schedule_agent,
    enable_checkpointing=True  # Para debugging
)

# Usar como agente normal
response = schedule_graph.get_response(
    question="Quiero agendar para mañana",
    user_id="user123",
    chat_history=[]
)
```

### Debugging con Checkpointing

```python
# Habilitar checkpointing
orchestrator = MultiAgentOrchestratorGraph(
    router_agent=router,
    agents=agents,
    company_id=company_id,
    enable_checkpointing=True  # ✅ Habilitar
)

# Ejecutar con thread_id para ver estado en cada paso
config = {"configurable": {"thread_id": "debug_session_1"}}
response = orchestrator.app.invoke(initial_state, config)

# Ver estado en cada nodo
for state in orchestrator.app.stream(initial_state, config):
    print(f"Estado actual: {state}")
```

---

## ✅ Compatibilidad

### API Backward Compatible

La arquitectura híbrida mantiene **100% compatibilidad** con la API existente:

| Método Actual | Compatible | Notas |
|--------------|-----------|-------|
| `orchestrator.get_response(...)` | ✅ | Misma firma, mismo retorno |
| `orchestrator.search_documents(...)` | ✅ | Delegado a vectorstore |
| `orchestrator.health_check()` | ✅ | Extendido con stats de grafo |
| `orchestrator.get_system_stats()` | ✅ | Extendido con métricas de agentes |

### Migración Gradual

No es necesario migrar todo de una vez:

1. **Fase 1**: Usar `MultiAgentOrchestratorGraph` en lugar de `MultiAgentOrchestrator`
   - Drop-in replacement
   - Agentes siguen siendo LangChain

2. **Fase 2**: Migrar agentes complejos a grafos internos
   - Comenzar con `ScheduleAgent` → `ScheduleAgentGraph`
   - Los agentes simples quedan como están

3. **Fase 3**: Agregar validaciones y pasos adicionales
   - Pagos, confirmaciones, etc.

---

## 🚀 Ventajas

### vs Implementación Actual (LangChain puro)

| Aspecto | LangChain (Actual) | LangChain + LangGraph (Nuevo) |
|---------|-------------------|-------------------------------|
| **Estado** | Disperso entre métodos | Centralizado en StateGraph |
| **Validaciones** | Implícitas | Explícitas en cada nodo |
| **Reintentos** | Manual con try/except | Automático con backoff |
| **Logging** | Ad-hoc | Estructurado por nodo |
| **Debugging** | Difícil | Checkpointing integrado |
| **Escalabilidad** | Código lineal | Grafo modular |
| **Testing** | Probar todo junto | Probar nodos individuales |

### Ventajas Específicas

#### 1. Separación de Responsabilidades
Cada nodo tiene una responsabilidad clara:
- `validate_input` → solo validar
- `classify_intent` → solo clasificar
- `execute_sales` → solo ejecutar agente

#### 2. Estado Compartido Explícito
```python
# Antes: Variables dispersas
intent = "SALES"
confidence = 0.95
response = agent.invoke(...)

# Después: Todo en un estado
state = {
    "intent": "SALES",
    "confidence": 0.95,
    "agent_response": "...",
    "executions": [...],
    "validations": [...]
}
```

#### 3. Routing Condicional Declarativo
```python
# Antes: if/else anidados
if confidence > 0.7:
    if intent == "SALES":
        return sales_agent.invoke(...)
    elif intent == "SUPPORT":
        return support_agent.invoke(...)
else:
    return support_agent.invoke(...)

# Después: Routing en grafo
workflow.add_conditional_edges(
    "classify_intent",
    route_to_agent,
    {
        "sales": "execute_sales",
        "support": "execute_support",
        ...
    }
)
```

#### 4. Reintentos Automáticos
```python
# Antes: try/except manual
try:
    response = agent.invoke(...)
except Exception as e:
    # retry logic aquí
    try:
        response = fallback_agent.invoke(...)
    except:
        return error_response

# Después: Automático en AgentAdapter
adapter = AgentAdapter(agent, max_retries=2)
result = adapter.invoke(inputs)
# → Reintentos con backoff exponencial automático
```

#### 5. Métricas y Observabilidad
```python
# Obtener stats de todos los agentes
stats = orchestrator.get_stats()
# → {
#     "router": {"executions": 100, "errors": 2, "avg_duration_ms": 150},
#     "agents": {
#         "sales": {"executions": 45, "error_rate": 0.02, ...},
#         "support": {"executions": 30, ...},
#         ...
#     }
# }
```

---

## 📚 Ejemplos

### Ejemplo 1: Orquestador Simple

```python
from app.langgraph_adapters.orchestrator_graph import MultiAgentOrchestratorGraph
from app.agents import RouterAgent, SalesAgent, SupportAgent

# Setup
company_config = get_company_config("company_123")
openai_service = OpenAIService()

# Crear agentes
router = RouterAgent(company_config, openai_service)
sales = SalesAgent(company_config, openai_service)
support = SupportAgent(company_config, openai_service)

# Crear orquestador
orchestrator = MultiAgentOrchestratorGraph(
    router_agent=router,
    agents={"sales": sales, "support": support},
    company_id="company_123"
)

# Ejecutar
response, intent = orchestrator.get_response(
    question="¿Cuánto cuesta el tratamiento?",
    user_id="user_456",
    chat_history=[]
)

print(f"Intent: {intent}")
print(f"Response: {response}")
```

### Ejemplo 2: ScheduleAgent con Grafo

```python
from app.langgraph_adapters.schedule_agent_graph import ScheduleAgentGraph
from app.agents.schedule_agent import ScheduleAgent

# Crear agente
schedule_agent = ScheduleAgent(company_config, openai_service)

# Envolverlo en grafo
schedule_graph = ScheduleAgentGraph(schedule_agent)

# Ejecutar
response = schedule_graph.get_response(
    question="Quiero agendar botox para el 15-12-2024",
    user_id="user_789",
    chat_history=[]
)

print(response)
# → "Horarios disponibles para 15-12-2024:
#    - 09:00 - 10:00
#    - 11:00 - 12:00
#    ..."
```

### Ejemplo 3: Adaptador Standalone

```python
from app.langgraph_adapters import AgentAdapter
from app.agents import SalesAgent

# Crear agente
sales_agent = SalesAgent(company_config, openai_service)

# Crear adaptador
adapted = AgentAdapter(
    agent=sales_agent,
    agent_name="sales",
    timeout_ms=30000,
    max_retries=2
)

# Usar standalone
result = adapted.invoke({
    "question": "¿Precios?",
    "chat_history": []
})

if result["success"]:
    print(f"Response: {result['output']}")
    print(f"Duration: {result['execution_state']['duration_ms']}ms")
else:
    print(f"Error: {result['error']}")
    print(f"Retries: {result['retries']}")
```

### Ejemplo 4: Validadores Personalizados

```python
from app.langgraph_adapters import AgentAdapter, ValidationResult

def validate_sales_input(inputs: dict) -> ValidationResult:
    """Validador personalizado para SalesAgent"""
    question = inputs.get("question", "")

    if len(question) < 5:
        return {
            "is_valid": False,
            "errors": ["Question is too short"],
            "warnings": [],
            "metadata": {}
        }

    # Verificar que sea una consulta de ventas
    sales_keywords = ["precio", "costo", "cuánto", "inversión"]
    if not any(kw in question.lower() for kw in sales_keywords):
        return {
            "is_valid": False,
            "errors": ["Not a sales question"],
            "warnings": [],
            "metadata": {}
        }

    return {
        "is_valid": True,
        "errors": [],
        "warnings": [],
        "metadata": {"question_length": len(question)}
    }

# Usar validador
adapted = AgentAdapter(
    agent=sales_agent,
    agent_name="sales",
    validate_input=validate_sales_input
)
```

---

## 🔍 Debugging y Troubleshooting

### Ver Estado en Cada Paso

```python
# Habilitar checkpointing
orchestrator = MultiAgentOrchestratorGraph(
    ...,
    enable_checkpointing=True
)

# Stream de ejecución
config = {"configurable": {"thread_id": "debug_1"}}
for state_snapshot in orchestrator.app.stream(initial_state, config):
    node_name, state = state_snapshot
    print(f"\n📍 Nodo: {node_name}")
    print(f"Intent: {state.get('intent')}")
    print(f"Confidence: {state.get('confidence')}")
    print(f"Errors: {state.get('errors')}")
```

### Logs Estructurados

Los componentes generan logs detallados:

```
[company_123] 🚀 MultiAgentOrchestratorGraph.get_response()
[company_123] 📍 Node: validate_input
[company_123] 📍 Node: classify_intent
[company_123] 🤖 router.invoke() started
[company_123]    → Question: ¿Cuánto cuesta...
[company_123] ✅ router completed successfully
[company_123]    → Duration: 245.67ms
[company_123] Intent classified: SALES (confidence: 0.95)
[company_123] Routing: intent=sales, confidence=0.95
[company_123] 📍 Node: execute_sales
[company_123] 🤖 sales.invoke() started
[company_123] ✅ sales completed successfully
[company_123]    → Duration: 1523.45ms
[company_123] 📍 Node: validate_output
[company_123] ✅ Response generated by sales (523 chars, 0 retries)
```

---

## 🎓 Conclusión

La arquitectura híbrida LangChain + LangGraph proporciona:

✅ **Compatibilidad total** con código existente
✅ **Orquestación cognitiva** sin modificar agentes
✅ **Validaciones explícitas** en cada paso
✅ **Reintentos automáticos** con backoff
✅ **Estado compartido** centralizado
✅ **Logging estructurado** para debugging
✅ **Métricas de rendimiento** automáticas
✅ **Escalabilidad** mediante grafos modulares

### Próximos Pasos

1. Migrar `MultiAgentOrchestrator` → `MultiAgentOrchestratorGraph`
2. Probar con usuarios reales
3. Migrar agentes complejos a grafos internos (comenzar con `ScheduleAgent`)
4. Agregar validaciones y pasos adicionales según necesidades

---

**Documentación creada por**: Claude Code
**Fecha**: 2025-10-24
**Versión**: 1.0.0
