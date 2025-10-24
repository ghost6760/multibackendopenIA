# 🏗️ Diagrama de Arquitectura Híbrida LangChain + LangGraph

## Vista General del Sistema

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                     USUARIO                                     │
│                         "¿Cuánto cuesta el botox?"                             │
└────────────────────────────────────┬────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          MULTI-AGENT ORCHESTRATOR GRAPH                         │
│                              (LangGraph StateGraph)                             │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                           ESTADO COMPARTIDO                             │  │
│  │  {                                                                      │  │
│  │    "question": "¿Cuánto cuesta el botox?",                            │  │
│  │    "user_id": "user123",                                              │  │
│  │    "company_id": "company_abc",                                        │  │
│  │    "intent": "SALES",                                                  │  │
│  │    "confidence": 0.95,                                                 │  │
│  │    "agent_response": "El tratamiento de botox...",                    │  │
│  │    "executions": [...],                                                │  │
│  │    "validations": [...],                                               │  │
│  │    "errors": []                                                         │  │
│  │  }                                                                      │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌──────────┐     ┌────────────────┐     ┌─────────────┐                     │
│  │  START   │ ──▶ │ Validate Input │ ──▶ │ Classify    │                     │
│  └──────────┘     │                │     │ Intent      │                     │
│                    └────────────────┘     └──────┬──────┘                     │
│                                                   │                             │
│                                    ┌──────────────┴──────────────┐             │
│                                    │   Routing Condicional       │             │
│                                    │   (basado en confidence)    │             │
│                                    └──┬────────┬────────┬────────┘             │
│                                       │        │        │                       │
│                   ┌───────────────────┘        │        └───────────────┐       │
│                   │                            │                        │       │
│           ┌───────▼───────┐          ┌────────▼────────┐      ┌────────▼──────┐│
│           │ Execute Sales │          │Execute Support  │      │Execute Emerge.││
│           │               │          │                 │      │               ││
│           └───────┬───────┘          └────────┬────────┘      └────────┬──────┘│
│                   │                            │                        │       │
│                   └─────────────┬──────────────┴────────────────────────┘       │
│                                 │                                               │
│                        ┌────────▼────────┐                                      │
│                        │ Validate Output │                                      │
│                        └────────┬────────┘                                      │
│                                 │                                               │
│                          ┌──────▼──────┐                                        │
│                          │   ¿Retry?   │                                        │
│                          └──┬───────┬──┘                                        │
│                             │       │                                           │
│                         NO  │       │ SÍ                                        │
│                             │       │                                           │
│                   ┌─────────▼──┐    └──▶ [Handle Retry] ──▶ [Escalate]        │
│                   │    END     │                                                │
│                   │  Response  │                                                │
│                   └────────────┘                                                │
└─────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            AGENT ADAPTER LAYER                                  │
│                         (Normalización de Interfaz)                             │
│                                                                                 │
│  ┌───────────────────────┐   ┌───────────────────────┐   ┌──────────────────┐ │
│  │   RouterAdapter       │   │   SalesAdapter        │   │  SupportAdapter  │ │
│  │                       │   │                       │   │                  │ │
│  │ • Logging automático  │   │ • Logging automático  │   │ • Logging auto.  │ │
│  │ • Validación inputs   │   │ • Validación I/O      │   │ • Validación     │ │
│  │ • Métricas            │   │ • Reintentos (max 2)  │   │ • Reintentos     │ │
│  │ • Timeout: 10s        │   │ • Timeout: 30s        │   │ • Timeout: 30s   │ │
│  └───────────┬───────────┘   └───────────┬───────────┘   └────────┬─────────┘ │
│              │                           │                         │           │
│              ▼                           ▼                         ▼           │
└─────────────────────────────────────────────────────────────────────────────────┘
              │                           │                         │
              ▼                           ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          LANGCHAIN AGENTS LAYER                                 │
│                         (Agentes Existentes - Sin Modificar)                    │
│                                                                                 │
│  ┌─────────────────┐   ┌──────────────────┐   ┌──────────────────────────┐    │
│  │  RouterAgent    │   │  SalesAgent      │   │  SupportAgent            │    │
│  │                 │   │                  │   │                          │    │
│  │ • Classify      │   │ • RAG Context    │   │ • RAG Context            │    │
│  │   intent        │   │ • Custom Prompts │   │ • Custom Prompts         │    │
│  │ • JSON output   │   │ • Company Config │   │ • Company Config         │    │
│  └─────────────────┘   └──────────────────┘   └──────────────────────────┘    │
│                                                                                 │
│  ┌─────────────────────────────┐   ┌────────────────────────────────────────┐ │
│  │  EmergencyAgent             │   │  ScheduleAgent                         │ │
│  │                             │   │                                        │ │
│  │ • Urgency detection         │   │ • Date extraction                     │ │
│  │ • RAG Context               │   │ • Availability check                  │ │
│  │ • Escalation protocols      │   │ • Booking API calls                   │ │
│  └─────────────────────────────┘   └────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
              │                           │                         │
              ▼                           ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              SERVICIOS EXTERNOS                                 │
│                                                                                 │
│  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────────────┐   │
│  │  OpenAI API      │   │  Vectorstore     │   │  Calendar Integration    │   │
│  │                  │   │  (RAG)           │   │  (Google/Calendly)       │   │
│  │ • GPT-4          │   │ • Pinecone       │   │ • Check availability     │   │
│  │ • Embeddings     │   │ • Company filter │   │ • Create bookings        │   │
│  └──────────────────┘   └──────────────────┘   └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Flujo Detallado: Ejecución Exitosa

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ PASO 1: Entrada del Usuario                                                 │
└──────────────────────────────────────────────────────────────────────────────┘

Usuario envía: "¿Cuánto cuesta el tratamiento de botox?"

Estado inicial creado:
{
  "question": "¿Cuánto cuesta el tratamiento de botox?",
  "user_id": "user123",
  "company_id": "company_abc",
  "chat_history": [],
  "context": "",
  "intent": null,
  "confidence": 0.0,
  "agent_response": null,
  "executions": [],
  "validations": [],
  "errors": [],
  "retries": 0
}

        │
        ▼

┌──────────────────────────────────────────────────────────────────────────────┐
│ PASO 2: Nodo - validate_input                                               │
└──────────────────────────────────────────────────────────────────────────────┘

Validaciones realizadas:
  ✅ question no vacía
  ✅ user_id válido
  ✅ company_id coincide

Estado actualizado:
{
  ...
  "validations": [
    {
      "is_valid": true,
      "errors": [],
      "warnings": [],
      "metadata": {"question_length": 46}
    }
  ]
}

Decisión: ¿Continuar? → SÍ

        │
        ▼

┌──────────────────────────────────────────────────────────────────────────────┐
│ PASO 3: Nodo - classify_intent                                              │
└──────────────────────────────────────────────────────────────────────────────┘

Ejecutar RouterAgent mediante AgentAdapter:

  RouterAdapter.invoke({
    "question": "¿Cuánto cuesta el tratamiento de botox?",
    "chat_history": []
  })

  ┌─────────────────────────────────────┐
  │ RouterAgent (LangChain)             │
  │                                     │
  │ 1. Recibe pregunta                  │
  │ 2. Analiza keywords:                │
  │    - "cuánto" → precio              │
  │    - "cuesta" → precio              │
  │    - "botox" → tratamiento          │
  │ 3. Clasifica: SALES                 │
  │ 4. Confianza: 0.95 (muy alta)      │
  │ 5. Retorna JSON:                    │
  │    {                                │
  │      "intent": "SALES",             │
  │      "confidence": 0.95,            │
  │      "keywords": ["cuánto", "cuesta"]
  │    }                                │
  └─────────────────────────────────────┘

Resultado: ✅ Success
Duration: 234.56ms

Estado actualizado:
{
  ...
  "intent": "SALES",
  "confidence": 0.95,
  "intent_keywords": ["cuánto", "cuesta"],
  "executions": [
    {
      "agent_name": "router",
      "status": "success",
      "duration_ms": 234.56,
      "retries": 0
    }
  ]
}

        │
        ▼

┌──────────────────────────────────────────────────────────────────────────────┐
│ PASO 4: Routing Condicional                                                 │
└──────────────────────────────────────────────────────────────────────────────┘

Evaluación:
  intent = "SALES"
  confidence = 0.95 > 0.7 → Alta confianza

Decisión: Ir a → execute_sales

        │
        ▼

┌──────────────────────────────────────────────────────────────────────────────┐
│ PASO 5: Nodo - execute_sales                                                │
└──────────────────────────────────────────────────────────────────────────────┘

Ejecutar SalesAgent mediante AgentAdapter:

  SalesAdapter.invoke({
    "question": "¿Cuánto cuesta el tratamiento de botox?",
    "chat_history": [],
    "context": "",
    "user_id": "user123",
    "company_id": "company_abc"
  })

  ┌─────────────────────────────────────────────────────┐
  │ SalesAgent (LangChain)                              │
  │                                                     │
  │ 1. Preparar contexto RAG:                           │
  │    vectorstore.search("botox precio")               │
  │    → [                                              │
  │         "Botox: $300,000 - $500,000",              │
  │         "Duración: 4-6 meses",                     │
  │         "Tratamiento rápido: 15 min"               │
  │       ]                                             │
  │                                                     │
  │ 2. Construir prompt con contexto:                   │
  │    "Eres un especialista en ventas..."             │
  │    "Información disponible: [RAG context]"         │
  │    "Pregunta: ¿Cuánto cuesta el botox?"           │
  │                                                     │
  │ 3. Ejecutar LLM (GPT-4):                           │
  │    chat_model.invoke(prompt)                        │
  │                                                     │
  │ 4. Generar respuesta:                               │
  │    "¡Hola! El tratamiento de botox tiene una       │
  │     inversión entre $300,000 y $500,000.           │
  │     Los resultados duran de 4 a 6 meses y          │
  │     el procedimiento es muy rápido (15 min).       │
  │     ¿Te gustaría agendar tu cita?"                 │
  └─────────────────────────────────────────────────────┘

Resultado: ✅ Success
Duration: 1523.45ms

Estado actualizado:
{
  ...
  "current_agent": "sales",
  "agent_response": "¡Hola! El tratamiento de botox...",
  "executions": [
    {...router execution...},
    {
      "agent_name": "sales",
      "status": "success",
      "duration_ms": 1523.45,
      "retries": 0,
      "output": "¡Hola! El tratamiento de botox..."
    }
  ]
}

        │
        ▼

┌──────────────────────────────────────────────────────────────────────────────┐
│ PASO 6: Nodo - validate_output                                              │
└──────────────────────────────────────────────────────────────────────────────┘

Validaciones realizadas:
  ✅ Response no vacía
  ✅ Longitud razonable (> 10 caracteres)
  ✅ Sin errores en ejecución

Estado actualizado:
{
  ...
  "validations": [
    {...input validation...},
    {
      "is_valid": true,
      "errors": [],
      "warnings": [],
      "metadata": {"response_length": 235}
    }
  ]
}

Decisión: ¿Retry? → NO (validation OK)

        │
        ▼

┌──────────────────────────────────────────────────────────────────────────────┐
│ PASO 7: END                                                                  │
└──────────────────────────────────────────────────────────────────────────────┘

Estado final:
{
  "question": "¿Cuánto cuesta el tratamiento de botox?",
  "user_id": "user123",
  "company_id": "company_abc",
  "intent": "SALES",
  "confidence": 0.95,
  "current_agent": "sales",
  "agent_response": "¡Hola! El tratamiento de botox tiene una inversión...",
  "executions": [
    {router: success, 234.56ms},
    {sales: success, 1523.45ms}
  ],
  "validations": [
    {input: valid},
    {output: valid}
  ],
  "errors": [],
  "retries": 0,
  "started_at": "2025-10-24T10:15:23Z",
  "completed_at": "2025-10-24T10:15:25Z"
}

RETORNO A USUARIO:
  response = "¡Hola! El tratamiento de botox tiene una inversión..."
  agent_used = "sales"

┌───────────────────────────────────────────────────────────┐
│ ✅ EJECUCIÓN COMPLETADA CON ÉXITO                        │
│                                                           │
│ Total duration: ~1758ms                                   │
│ Nodes executed: 7                                         │
│ Retries: 0                                                │
│ Agent used: sales                                         │
└───────────────────────────────────────────────────────────┘
```

---

## Flujo Alternativo: Con Reintentos y Escalado

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ESCENARIO: EmergencyAgent falla, escalar a SupportAgent                     │
└──────────────────────────────────────────────────────────────────────────────┘

Usuario: "¡Emergencia! Tengo mucho dolor después del tratamiento"

[validate_input] ✅

[classify_intent]
  └─▶ Intent: EMERGENCY, Confidence: 0.98

[execute_emergency]
  └─▶ EmergencyAgent.invoke()
      └─▶ ❌ ERROR: OpenAI API timeout (30s exceeded)

Estado:
{
  ...
  "current_agent": "emergency",
  "agent_response": null,
  "errors": ["emergency failed: OpenAI API timeout"],
  "executions": [
    {
      "agent_name": "emergency",
      "status": "failed",
      "error": "OpenAI API timeout"
    }
  ]
}

[validate_output]
  └─▶ Validation failed: Response is empty
  └─▶ should_retry = True

[handle_retry]
  └─▶ retries = 1 (< max 2)
  └─▶ agent_response is null → should_escalate = True
  └─▶ Decisión: ESCALAR a support

[execute_support]
  └─▶ SupportAgent.invoke()
      └─▶ ✅ Success: "Lo siento por las molestias. Voy a conectarte
                       inmediatamente con nuestro equipo de urgencias..."

Estado final:
{
  ...
  "current_agent": "support",
  "agent_response": "Lo siento por las molestias...",
  "executions": [
    {emergency: failed, timeout},
    {support: success, 892.34ms}
  ],
  "retries": 1
}

[END]

RETORNO:
  response = "Lo siento por las molestias. Voy a conectarte..."
  agent_used = "support"  # ← Escalado desde emergency

┌───────────────────────────────────────────────────────────┐
│ ✅ RECUPERACIÓN EXITOSA VÍA ESCALADO                     │
│                                                           │
│ Original intent: emergency                                │
│ Final agent: support (fallback)                          │
│ Retries: 1                                                │
│ User experience: No se pierde la conversación            │
└───────────────────────────────────────────────────────────┘
```

---

## Comparación: Antes vs Después

### ANTES (LangChain puro)

```
Usuario → get_response()
           │
           ├─▶ RouterAgent.invoke() → JSON
           │
           ├─▶ if intent == "SALES":
           │     └─▶ SalesAgent.invoke() → response
           │
           ├─▶ elif intent == "SUPPORT":
           │     └─▶ SupportAgent.invoke() → response
           │
           ├─▶ else:
           │     └─▶ SupportAgent.invoke() → response
           │
           └─▶ return response

Estado: Disperso en variables locales
Validaciones: Implícitas (try/except)
Reintentos: Manuales
Logging: Ad-hoc
```

### DESPUÉS (LangChain + LangGraph)

```
Usuario → get_response()
           │
           ├─▶ create_initial_state()
           │    └─▶ OrchestratorState
           │
           ├─▶ StateGraph.invoke(state)
           │    │
           │    ├─▶ [validate_input] ─┐
           │    │                      ├─▶ state.validations.append()
           │    │                      └─▶ continue/end
           │    │
           │    ├─▶ [classify_intent] ─┐
           │    │                       ├─▶ RouterAdapter.invoke()
           │    │                       ├─▶ state.executions.append()
           │    │                       └─▶ state.intent = "SALES"
           │    │
           │    ├─▶ [route_to_agent] ─┐
           │    │                      └─▶ conditional: sales/support/...
           │    │
           │    ├─▶ [execute_sales] ─┐
           │    │                     ├─▶ SalesAdapter.invoke()
           │    │                     ├─▶ state.executions.append()
           │    │                     └─▶ state.agent_response = "..."
           │    │
           │    ├─▶ [validate_output] ─┐
           │    │                       ├─▶ state.validations.append()
           │    │                       └─▶ retry/end
           │    │
           │    └─▶ END ─▶ final_state
           │
           └─▶ return final_state.agent_response

Estado: Centralizado en StateGraph
Validaciones: Explícitas en nodos
Reintentos: Automáticos con routing
Logging: Estructurado por nodo
```

---

## Arquitectura de Datos

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FLUJO DE DATOS                                  │
└─────────────────────────────────────────────────────────────────────────┘

INPUT (Usuario):
  {
    "question": "¿Precios?",
    "user_id": "user123",
    "chat_history": []
  }

       ↓

STATE (Durante ejecución - mutable):
  {
    "question": "¿Precios?",          # ← Input original (inmutable)
    "user_id": "user123",             # ← Input original
    "company_id": "company_abc",      # ← Inyectado por orchestrator
    "intent": "SALES",                # ← Agregado por classify_intent
    "confidence": 0.95,               # ← Agregado por classify_intent
    "agent_response": "El precio...", # ← Agregado por execute_sales
    "executions": [...],              # ← Acumulado en cada nodo
    "validations": [...],             # ← Acumulado en validaciones
    "errors": [],                     # ← Acumulado si hay errores
    "retries": 0                      # ← Incrementado en retry
  }

       ↓

OUTPUT (A usuario):
  (
    "El precio de nuestros tratamientos...",  # response
    "sales"                                   # agent_used
  )
```

---

**Diagrama creado por**: Claude Code
**Fecha**: 2025-10-24
**Versión**: 1.0.0
