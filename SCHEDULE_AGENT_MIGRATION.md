# 📅 Migración de ScheduleAgent a ScheduleAgentGraph

## 🎯 Objetivo

Migrar `ScheduleAgent` para usar `ScheduleAgentGraph` internamente, obteniendo validaciones paso a paso y mejor trazabilidad, mientras se mantiene 100% compatibilidad con la API existente.

---

## 📊 Comparación: Antes vs Después

### ANTES (ScheduleAgent Original)

```
Usuario: "Quiero agendar para mañana"
   │
   ▼
┌─────────────────────────────────────────┐
│ ScheduleAgent                           │
│                                         │
│ hybrid_schedule_processor():            │
│   ├─ RAG context                        │
│   ├─ LLM genera respuesta               │
│   ├─ if availability_check:             │
│   │     extract_date()                  │
│   │     extract_treatment()             │
│   │     call_check_availability()       │
│   └─ if should_book:                    │
│         validate_info()                 │
│         call_booking_api()              │
│                                         │
│ return response                         │
└─────────────────────────────────────────┘

Problemas:
❌ Lógica mezclada (extracción + validación + respuesta)
❌ Estado disperso en variables locales
❌ Difícil de debuggear (un solo paso grande)
❌ Validaciones implícitas
❌ Difícil agregar nuevos pasos
```

### DESPUÉS (ScheduleAgent Híbrido con Graph)

```
Usuario: "Quiero agendar para mañana"
   │
   ▼
┌─────────────────────────────────────────────────────┐
│ ScheduleAgent (wrapper)                             │
│   └─▶ ScheduleAgentGraph.get_response()            │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│ ScheduleAgentGraph (LangGraph StateGraph)          │
│                                                     │
│  [Extract Info] → Extrae fecha, tratamiento, info  │
│        ↓                                            │
│  [Validate Info] → Valida fecha, tratamiento       │
│        ↓                                            │
│  [Check Availability] → Verifica horarios (si aplica)|
│        ↓                                            │
│  [Generate Response] → LLM genera respuesta        │
│        ↓                                            │
│  END → Response al usuario                         │
└─────────────────────────────────────────────────────┘

Ventajas:
✅ Separación clara de responsabilidades
✅ Estado centralizado en StateGraph
✅ Cada paso es debuggeable independientemente
✅ Validaciones explícitas en nodos dedicados
✅ Fácil agregar pasos (pagos, confirmaciones)
✅ Trazabilidad completa del flujo
```

---

## 🚀 Beneficios de la Migración

### 1. **Separación de Responsabilidades**

| Paso | Responsabilidad | Antes | Después |
|------|----------------|-------|---------|
| **Extracción** | Extraer fecha, tratamiento, info paciente | Mezclado en processor | Nodo dedicado `extract_info` |
| **Validación** | Validar información extraída | Implícita | Nodo dedicado `validate_info` |
| **Disponibilidad** | Verificar horarios | Condicional en processor | Nodo `check_availability` |
| **Respuesta** | Generar respuesta final | Mezclado con lógica | Nodo `generate_response` |

### 2. **Estado Compartido Explícito**

**Antes**:
```python
# Estado disperso en variables locales
def hybrid_schedule_processor(inputs):
    date = extract_date(question)
    treatment = extract_treatment(question)
    patient_info = extract_patient(history)
    # ... lógica con estas variables dispersas
```

**Después**:
```python
# Estado centralizado en ScheduleAgentState
{
    "question": "...",
    "extracted_date": "24-10-2024",
    "extracted_treatment": "limpieza facial",
    "date_valid": True,
    "treatment_valid": True,
    "available_slots": ["14:00", "15:00"],
    "agent_response": "..."
}
```

### 3. **Validaciones Explícitas**

**Antes**:
```python
# Validación implícita
if self._is_availability_check(question):
    date = self._extract_date_from_question(question)
    if date and treatment:  # Validación implícita
        availability = self._call_check_availability(date, treatment)
```

**Después**:
```python
# Nodo dedicado a validación
def _validate_info(state):
    if state["extracted_date"]:
        date_obj = parse_date(state["extracted_date"])
        state["date_valid"] = date_obj >= datetime.now()

    if state["extracted_treatment"]:
        state["treatment_valid"] = treatment in valid_treatments

    return state
```

### 4. **Logging Estructurado**

**Antes**:
```
[INFO] ScheduleAgent: processing_schedule
[INFO] ✅ Chain executed successfully
```

**Después**:
```
[INFO] ScheduleAgentGraph.get_response()
[INFO] 📍 Node: extract_info
[INFO]    → Extracted date: 24-10-2024
[INFO]    → Extracted treatment: limpieza facial
[INFO] 📍 Node: validate_info
[INFO]    → date_valid: True
[INFO]    → treatment_valid: True
[INFO] 📍 Node: check_availability
[INFO]    → Found 3 available slots
[INFO] 📍 Node: generate_response
[INFO] ✅ Response generated (235 chars)
```

### 5. **Debugging Mejorado**

Con el grafo puedes:
- ✅ Ver el estado en cada nodo
- ✅ Identificar en qué paso falló
- ✅ Verificar qué información se extrajo
- ✅ Validar que las condiciones se cumplieron

```python
# Con checkpointing habilitado
graph = ScheduleAgentGraph(agent, enable_checkpointing=True)

# Ver estado en cada paso
for state in graph.app.stream(initial_state, config):
    print(f"Estado en {node}: {state}")
```

### 6. **Extensibilidad**

Agregar nuevos pasos es trivial:

```python
# Agregar paso de verificación de pago
workflow.add_node("verify_payment", self._verify_payment)

# Agregar a la secuencia
workflow.add_edge("check_availability", "verify_payment")
workflow.add_edge("verify_payment", "generate_response")
```

---

## 🔄 Flujo Detallado del Grafo

### Estado Inicial
```python
{
    "question": "Quiero agendar limpieza facial para mañana",
    "user_id": "user123",
    "company_id": "benova",
    "chat_history": [],

    # Campos que se llenarán
    "extracted_date": None,
    "extracted_treatment": None,
    "date_valid": False,
    "available_slots": [],
    "agent_response": ""
}
```

### Paso 1: Extract Info
```python
def _extract_info(state):
    question = state["question"]

    # Extraer fecha
    if "mañana" in question.lower():
        tomorrow = datetime.now() + timedelta(days=1)
        state["extracted_date"] = tomorrow.strftime("%d-%m-%Y")

    # Extraer tratamiento
    if "limpieza facial" in question.lower():
        state["extracted_treatment"] = "limpieza facial"

    return state
```

**Estado después**:
```python
{
    ...,
    "extracted_date": "25-10-2024",
    "extracted_treatment": "limpieza facial"
}
```

### Paso 2: Validate Info
```python
def _validate_info(state):
    # Validar fecha
    if state["extracted_date"]:
        date_obj = datetime.strptime(state["extracted_date"], "%d-%m-%Y")
        state["date_valid"] = date_obj >= datetime.now()

    # Validar tratamiento
    treatments = get_valid_treatments()
    state["treatment_valid"] = state["extracted_treatment"] in treatments

    return state
```

**Estado después**:
```python
{
    ...,
    "date_valid": True,
    "treatment_valid": True
}
```

### Paso 3: Check Availability (condicional)
```python
def _should_check_availability(state):
    # Solo si fecha y tratamiento son válidos
    if state["date_valid"] and state["treatment_valid"]:
        return "check"
    return "skip"

def _check_availability(state):
    availability = call_api(state["extracted_date"], state["extracted_treatment"])
    state["available_slots"] = availability["slots"]
    return state
```

**Estado después**:
```python
{
    ...,
    "available_slots": ["14:00-15:00", "16:00-17:00"]
}
```

### Paso 4: Generate Response
```python
def _generate_response(state):
    # Construir contexto
    context = f"""
    Fecha: {state['extracted_date']}
    Tratamiento: {state['extracted_treatment']}
    Horarios: {state['available_slots']}
    """

    # Ejecutar LLM
    response = agent.invoke({"question": state["question"], "context": context})
    state["agent_response"] = response

    return state
```

**Estado final**:
```python
{
    "question": "Quiero agendar limpieza facial para mañana",
    "extracted_date": "25-10-2024",
    "extracted_treatment": "limpieza facial",
    "date_valid": True,
    "treatment_valid": True,
    "available_slots": ["14:00-15:00", "16:00-17:00"],
    "agent_response": "Tenemos disponibilidad mañana 25/10 en:\n- 14:00-15:00\n- 16:00-17:00\n¿Cuál horario prefieres?"
}
```

---

## 📖 Guía de Migración

### Paso 1: Hacer Backup

```bash
cp app/agents/schedule_agent.py app/agents/schedule_agent.backup.py
```

### Paso 2: Reemplazar con Versión Híbrida

```bash
mv app/agents/schedule_agent_hybrid.py app/agents/schedule_agent.py
```

### Paso 3: Reiniciar y Probar

```bash
# Reiniciar servidor
pkill -f "python main.py"
python main.py

# Hacer request de prueba
curl -X POST http://localhost:8080/conversations/company_default/user123 \
  -H "Content-Type: application/json" \
  -d '{"message": "Quiero agendar para mañana"}'
```

### Paso 4: Verificar Logs

Buscar en logs:
```
✅ USANDO GRAFO:
[INFO] Using ScheduleAgentGraph for scheduling
[INFO] 📍 Node: extract_info
[INFO] 📍 Node: validate_info
...

⚠️ FALLBACK (si falla):
[WARNING] ScheduleAgentGraph not available, using direct chain
```

---

## 🔙 Rollback

Si algo sale mal:

```bash
# Restaurar backup
cp app/agents/schedule_agent.backup.py app/agents/schedule_agent.py

# Reiniciar
pkill -f "python main.py"
python main.py
```

---

## 🎓 Conclusión

La migración de ScheduleAgent a usar ScheduleAgentGraph proporciona:

✅ **Separación clara** de responsabilidades (extract → validate → check → respond)
✅ **Estado centralizado** en StateGraph (no variables dispersas)
✅ **Validaciones explícitas** en nodos dedicados
✅ **Mejor debugging** (ver estado en cada paso)
✅ **Logging estructurado** (log por cada nodo)
✅ **Extensibilidad** (agregar pasos es trivial)
✅ **Trazabilidad completa** del flujo
✅ **100% compatible** con API existente

### Próximos Pasos Opcionales (Fase 3)

Una vez migrado, puedes agregar fácilmente:
- 💰 Nodo de verificación de pagos/abonos
- 📧 Nodo de envío de confirmaciones por email
- 🔔 Nodo de notificaciones
- 📝 Nodo de creación de documentos
- 🔄 Nodo de sincronización con sistemas externos

---

**Documentación creada por**: Claude Code
**Fecha**: 2025-10-24
**Versión**: 1.0.0
