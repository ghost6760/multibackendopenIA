# Coordinación Entre Agentes: ScheduleAgent y SalesAgent

## 📊 Problema Identificado

Durante las pruebas, se detectó inconsistencia en la información de precios entre agentes:

### Caso de Uso Real:
```
User: "quiero agendar toxina botulínica, ¿cuánto cuesta?"
ScheduleAgent: "$1,200" ❌ (INCORRECTO - inventado)
User: "¿segura ese es el precio?"
SalesAgent: "$550,000" ✅ (CORRECTO - del RAG)
```

---

## 🔍 Análisis de Causa Raíz

### **Diferencias en Recuperación RAG**

#### SalesAgent (✅ Funcionamiento Correcto)
```python
# app/agents/sales_agent.py línea 82
docs = self.vectorstore_service.search_by_company(
    question,  # Query sin modificar
    self.company_config.company_id
)
```
- **Query directa** con la pregunta del usuario
- Sin filtros restrictivos
- Recupera información comercial completa

#### ScheduleAgent (❌ Problema Original)
```python
# app/agents/schedule_agent.py línea 299 (ANTES)
schedule_query = f"cita agenda horario duración preparación requisitos abono {question}"
docs = self.vectorstore_service.search_by_company(schedule_query, ...)

# Filtro restrictivo (línea 314)
if any(word in content for word in ['cita', 'agenda', 'horario', ...]):
    # NO incluía: 'precio', 'costo', 'valor'
```

**Problemas:**
1. Query modificada distorsionaba búsqueda semántica
2. Filtro excluía información de precios
3. LLM inventaba precios al no encontrar en contexto

---

## ✅ Solución Implementada (Commit 9491d70)

### 1. **Mejorar Recuperación RAG en ScheduleAgent**

```python
# app/agents/schedule_agent.py línea 298-318
# ✅ Query directa (sin modificar)
docs = self.vectorstore_service.search_by_company(
    question,
    self.company_config.company_id,
    k=5  # Aumentado para mejor cobertura
)

# ✅ Keywords expandidas
relevant_keywords = [
    'cita', 'agenda', 'horario', 'duración', 'preparación',
    'requisitos', 'abono', 'valoración',
    # NUEVO: Incluir keywords comerciales
    'precio', 'costo', 'valor', 'inversión', 'oferta',
    'pago', 'efectivo', 'transferencia', 'promoción'
]
```

### 2. **Instrucciones Explícitas en Prompt**

```python
# app/agents/schedule_agent.py línea 262-265
"""
4. ✅ IMPORTANTE: Si el usuario pregunta por precios/costos,
   SIEMPRE usa la información exacta del CONTEXTO DE AGENDAMIENTO.
   NUNCA inventes o estimates precios.
5. Si el CONTEXTO incluye información de precios (valor, oferta, inversión),
   úsala literalmente
"""
```

---

## 🎯 Resultado Esperado

Ahora ambos agentes deben proporcionar precios consistentes:

```
User: "quiero agendar toxina botulínica, ¿cuánto cuesta?"
ScheduleAgent: "$550,000 en efectivo/transferencia" ✅ (del RAG)
```

---

## 🚀 Recomendaciones para Mejor Coordinación (Fase 3)

### **Opción 1: Detección de Intent Secundario en el Grafo**

Agregar nodo de clasificación que detecte cuando el usuario hace preguntas comerciales durante agendamiento:

```python
# Pseudo-código para MultiAgentOrchestratorGraph
def _detect_secondary_intent(state: OrchestratorState):
    """Detectar si hay pregunta comercial durante agendamiento"""
    if state["intent"] == "schedule":
        # Palabras clave comerciales
        if any(word in state["question"].lower() for word in
               ['precio', 'costo', 'cuánto', 'cuanto', 'valor', 'pagar']):
            logger.info("Detected pricing question during scheduling")
            state["secondary_intent"] = "sales"
            return "route_to_sales"
    return "continue_schedule"
```

**Flujo propuesto:**
```
START
  ↓
[Classify Intent] → "schedule"
  ↓
[Execute Schedule Agent]
  ↓
[Detect Secondary Intent] → "pricing question"
  ↓
[Route to Sales Agent] → Respuesta con precio correcto
  ↓
[Return to Schedule] → Continuar agendamiento
  ↓
END
```

### **Opción 2: ScheduleAgent con Contexto de SalesAgent**

Compartir vectorstore service y contexto entre agentes:

```python
class ScheduleAgent:
    def _get_schedule_context(self, inputs):
        # Ya implementado: busca con keywords comerciales incluidas
        # Esto es suficiente para la mayoría de casos
```

### **Opción 3: Routing Dinámico en MultiAgentOrchestrator**

Ya implementado parcialmente en `MultiAgentOrchestratorGraph`:

```python
def _route_to_agent(state):
    """Router con lógica de escalamiento"""
    intent = state["intent"]
    confidence = state["confidence"]

    # Si confianza baja, escalar a ventas
    if confidence < 0.6:
        return "execute_sales"

    # Router normal
    return routing_map[intent]
```

---

## 📈 Mejoras Futuras (Fase 3)

### 1. **Contexto Compartido Entre Agentes**
```python
class SharedContext:
    """Contexto compartido entre múltiples agentes en la conversación"""
    def __init__(self):
        self.pricing_info = {}
        self.schedule_info = {}
        self.user_info = {}
```

### 2. **Handoff Explícito Entre Agentes**
```python
def schedule_agent_with_handoff(state):
    """ScheduleAgent con capacidad de handoff a SalesAgent"""
    if "precio" in state["question"]:
        # Hacer handoff a sales
        return {
            "handoff_to": "sales",
            "handoff_reason": "pricing_inquiry",
            "return_to": "schedule",
            "context": state
        }
```

### 3. **Validación Cruzada de Información**
```python
def _validate_cross_agent_info(state):
    """Validar que información sea consistente entre agentes"""
    schedule_price = extract_price(state["schedule_response"])
    sales_price = extract_price(state["sales_context"])

    if schedule_price and sales_price:
        if schedule_price != sales_price:
            logger.warning(f"Price mismatch: {schedule_price} vs {sales_price}")
            # Usar precio de sales como fuente de verdad
            return sales_price
```

---

## 🧪 Pruebas Recomendadas

### Caso 1: Pregunta de Precio Durante Agendamiento
```
User: "Quiero agendar toxina botulínica, ¿cuánto cuesta?"
Expected: ScheduleAgent proporciona precio correcto del RAG
```

### Caso 2: Precio Seguido de Agendamiento
```
User: "¿Cuánto cuesta toxina botulínica?"
Sales: "$550,000..."
User: "Quiero agendar para mañana"
Expected: ScheduleAgent continúa con agendamiento sin repetir precio
```

### Caso 3: Cambio de Intención Mid-Conversation
```
User: "Quiero agendar" → ScheduleAgent
User: "¿Tienen descuentos?" → SalesAgent (routing dinámico)
User: "Ok, agendar para mañana" → ScheduleAgent (return)
Expected: Router detecta cambio y vuelve a schedule
```

---

## 📋 Checklist de Implementación

- [x] **Fix 1:** Mejorar recuperación RAG en ScheduleAgent (commit 9491d70)
- [x] **Fix 2:** Agregar instrucciones de precio en prompt (commit 9491d70)
- [x] **Mejora 1:** Implementar detección de secondary intent en grafo
- [x] **Mejora 2:** Agregar nodo de handoff entre agentes
- [x] **Mejora 3:** Implementar contexto compartido entre agentes (SharedStateStore)
- [x] **Mejora 4:** Agregar validación cruzada de información
- [ ] **Testing:** Casos de uso con preguntas mixtas schedule+sales

---

## 🎓 Conclusión

**Estado actual:**
- ✅ ScheduleAgent ahora recupera precios correctamente del RAG
- ✅ Ambos agentes usan la misma estrategia de búsqueda semántica
- ✅ Prompts instruyen explícitamente a usar información del contexto

**Próximos pasos (Fase 3):**
- Agregar routing dinámico basado en secondary intent
- Implementar handoff explícito entre agentes
- Crear contexto compartido para información crítica (precios, user data)
- Validación cruzada para garantizar consistencia

**Beneficios:**
- Experiencia de usuario más fluida
- Información consistente sin importar qué agente responde
- Capacidad de cambiar de agente mid-conversation
- Mejor gestión de conversaciones complejas con múltiples intenciones

---

## 🔧 Implementación: Shared State Store

### **Arquitectura del Shared State Store**

Se implementó un almacén centralizado de estado compartido que permite a los agentes coordinarse mediante lectura/escritura de información crítica.

#### **Componentes Implementados**

1. **SharedStateStore** (`app/services/shared_state_store.py`)
   - Almacenamiento en memoria (con soporte futuro para Redis)
   - TTL configurable (default: 1 hora)
   - Thread-safe con locks

2. **Tipos de Información Gestionada:**

```python
@dataclass
class PricingInfo:
    """Información de precios compartida entre Sales y Schedule"""
    service_name: str
    price: str
    currency: str
    payment_methods: List[str]
    promotions: Optional[str]
    source_agent: str  # Quién proporcionó la info

@dataclass
class ScheduleInfo:
    """Información de agendamiento compartida"""
    treatment: str
    date: Optional[str]
    time: Optional[str]
    patient_name: Optional[str]
    status: str  # pending, confirmed, cancelled
    source_agent: str

@dataclass
class UserInfo:
    """Información del usuario extraída durante la conversación"""
    user_id: str
    name: Optional[str]
    phone: Optional[str]
    intent_history: List[str]  # Historial de intenciones

@dataclass
class HandoffInfo:
    """Registro de handoffs entre agentes"""
    from_agent: str
    to_agent: str
    reason: str
    context: Dict[str, Any]
    return_to_original: bool
```

#### **Integración en OrchestratorGraph**

**1. Extensión de OrchestratorState:**
```python
# app/langgraph_adapters/state_schemas.py

class OrchestratorState(TypedDict):
    # ... campos existentes ...

    # ✅ NUEVO: Intención secundaria
    secondary_intent: Optional[str]
    secondary_confidence: float

    # ✅ NUEVO: Shared context
    shared_context: Dict[str, Any]

    # ✅ NUEVO: Handoff info
    handoff_requested: bool
    handoff_from: Optional[str]
    handoff_to: Optional[str]
    handoff_reason: Optional[str]
    handoff_context: Dict[str, Any]
```

**2. Nuevos Nodos en el Grafo:**

```python
# Nodo 1: Detectar intención secundaria
def _detect_secondary_intent(state):
    """
    Detecta cuando usuario hace pregunta de pricing durante scheduling
    o pregunta de scheduling durante sales.
    """
    if intent == "schedule" and has_pricing_keywords:
        state["secondary_intent"] = "sales"
        state["secondary_confidence"] = 0.8

# Nodo 2: Manejar handoff entre agentes
def _handle_agent_handoff(state):
    """
    Ejecuta handoff cuando se detecta secondary intent.
    Schedule → Sales (para pricing)
    Sales → Schedule (para agendamiento)
    """
    if secondary_intent and secondary_confidence >= 0.7:
        state["handoff_requested"] = True
        state["handoff_to"] = secondary_intent

# Nodo 3: Validar consistencia cross-agent
def _validate_cross_agent_info(state):
    """
    Valida que información proporcionada sea consistente.
    Ej: Si Schedule da precio, verificar con datos de Sales.
    """
    if agent == "schedule" and has_pricing_in_response:
        if sales_pricing_differs:
            log_warning("Price mismatch detected")
```

**3. Flujo Actualizado:**

```
START
  ↓
[Validate Input]
  ↓
[Classify Intent] → intent="schedule"
  ↓
[Detect Secondary Intent] → secondary_intent="sales" (detected pricing keywords)
  ↓
[Route to Agent] → execute_schedule
  ↓
[Execute Schedule Agent]
  ↓
  ├─ Guardar schedule_info en shared_context
  ↓
[Validate Output]
  ↓
[Check Handoff?] → Yes (secondary_intent detected)
  ↓
[Handle Agent Handoff]
  ↓
  ├─ handoff_to="sales"
  ↓
[Execute Sales Agent] → proporcionar precio correcto
  ↓
  ├─ Guardar sales_pricing en shared_context
  ↓
[Validate Cross-Agent Info]
  ↓
  ├─ Comparar pricing de Schedule vs Sales
  ├─ Log warnings si difieren
  ↓
END
```

#### **Ejemplos de Uso**

**Caso 1: Pricing durante scheduling (Schedule → Sales)**
```python
User: "Quiero agendar toxina botulínica, ¿cuánto cuesta?"

# 1. Router clasifica intent="schedule"
# 2. Detect Secondary Intent detecta keywords de pricing → secondary_intent="sales"
# 3. Execute Schedule Agent responde sobre agendamiento
# 4. Handle Agent Handoff detecta secondary_intent → handoff a Sales
# 5. Execute Sales Agent proporciona precio correcto: "$550,000"
# 6. Validate Cross-Agent Info verifica consistencia
# 7. Respuesta final combina información de ambos agentes ✅
```

**Caso 2: Pregunta general durante ventas (Sales → Support)**
```python
User: "¿Cuánto cuesta la toxina? ¿Tienen parqueadero?"

# 1. Router clasifica intent="sales"
# 2. Execute Sales Agent responde sobre pricing
# 3. Detect Secondary Intent detecta keywords de support → secondary_intent="support"
# 4. Handle Agent Handoff → handoff a Support
# 5. Execute Support Agent proporciona info de parqueadero
# 6. Respuesta combina pricing + facilities info ✅
```

**Caso 3: Emergencia durante cualquier flujo (Any → Emergency)**
```python
User: "Quiero agendar... me duele mucho la zona tratada"

# 1. Router clasifica intent="schedule"
# 2. Detect Secondary Intent detecta keywords de EMERGENCY → secondary_intent="emergency" (prioridad máxima)
# 3. Execute Schedule Agent (breve)
# 4. Handle Agent Handoff → handoff URGENTE a Emergency
# 5. Execute Emergency Agent prioriza atención médica
# 6. Shared context guarda emergency_info para seguimiento ⚠️
```

#### **Beneficios Implementados**

✅ **Detección de Intención Secundaria (EXTENDIDA)**
- **Pricing**: Schedule/Support → Sales
- **Scheduling**: Sales/Support → Schedule
- **Support general**: Schedule/Sales → Support
- **Emergency (PRIORIDAD MÁXIMA)**: Cualquier agente → Emergency
- Keywords-based con confianza del 75-90%

✅ **Agent Handoff Multi-Direccional**
- Schedule ↔ Sales (pricing/scheduling)
- Schedule ↔ Support (general questions)
- Sales ↔ Support (facilities, payment methods)
- **ANY → Emergency** (máxima prioridad para urgencias)
- Contexto preservado durante handoff
- Prevención de loops infinitos

✅ **Contexto Compartido (TODOS LOS AGENTES)**
- **sales_info**: pricing, payment methods, promotions
- **schedule_info**: appointments, availability, booking IDs
- **support_info**: general questions, facilities, complaints
- **emergency_info**: symptoms, urgency level, actions taken
- **service_info**: treatments/services mentioned
- **user_info**: contact info, intent history

✅ **Validación Cruzada (COMPREHENSIVA)**
- Valida pricing entre Schedule/Support con Sales
- Valida scheduling entre Sales/Support con Schedule
- Valida emergency mentions con Emergency context
- Logs disponibles de contextos compartidos
- Warnings para debugging e inconsistencias

#### **Próximos Pasos**

1. **Backend Redis** (opcional para producción)
   ```python
   store = SharedStateStore(
       backend="redis",
       redis_url="redis://localhost:6379",
       ttl_seconds=3600
   )
   ```

2. **Extracción Mejorada con NER/LLM**
   - Usar NER para extraer precios precisos
   - Usar LLM para extraer info de agendamiento

3. **Métricas y Monitoreo**
   - Tracking de handoffs realizados
   - Tasa de detección de secondary intent
   - Inconsistencias detectadas

4. **Testing**
   - Casos de uso mixtos (schedule + pricing)
   - Handoffs múltiples
   - Validación de consistencia
