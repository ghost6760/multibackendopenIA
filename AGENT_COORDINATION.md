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
- [ ] **Mejora 1:** Implementar detección de secondary intent en grafo
- [ ] **Mejora 2:** Agregar nodo de handoff entre agentes
- [ ] **Mejora 3:** Implementar contexto compartido entre agentes
- [ ] **Mejora 4:** Agregar validación cruzada de información
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
