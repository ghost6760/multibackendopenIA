# 🔄 Guía de Migración a Arquitectura Híbrida

## 📋 Tabla de Contenidos

- [Introducción](#introducción)
- [Estrategias de Migración](#estrategias-de-migración)
- [Opción Recomendada: Wrapper Híbrido](#opción-1-wrapper-híbrido-recomendado)
- [Opción Alternativa: Reemplazo de Archivo](#opción-2-reemplazo-de-archivo)
- [Opción Avanzada: Cambiar Imports](#opción-3-cambiar-imports-en-todo-el-código)
- [Testing y Validación](#testing-y-validación)
- [Rollback](#rollback)

---

## 📖 Introducción

Este documento explica **cómo migrar** de `MultiAgentOrchestrator` (LangChain puro) a `MultiAgentOrchestratorGraph` (LangChain + LangGraph).

### ✅ Objetivos de la Migración

- Usar LangGraph para orquestación cognitiva
- Mantener 100% compatibilidad con código existente
- Poder hacer rollback fácilmente si hay problemas
- Migración gradual sin downtime

---

## 🎯 Estrategias de Migración

Hay **3 opciones** principales:

| Opción | Dificultad | Compatibilidad | Rollback | Recomendado |
|--------|-----------|----------------|----------|-------------|
| **1. Wrapper Híbrido** | ⭐ Fácil | ✅ 100% | ✅ Fácil | ✅ **SÍ** |
| **2. Reemplazo de Archivo** | ⭐⭐ Media | ✅ 100% | ⚠️ Manual | ❌ No |
| **3. Cambiar Imports** | ⭐⭐⭐ Difícil | ✅ 100% | ❌ Difícil | ❌ No |

---

## 🌟 Opción 1: Wrapper Híbrido (RECOMENDADO)

### ¿Qué es?

Modificar `multi_agent_orchestrator.py` para que **internamente use el grafo**, pero mantenga la misma interfaz externa.

### ✅ Ventajas

- **No hay que cambiar imports** en ningún otro archivo
- **100% compatible** con código existente
- **Rollback fácil** (solo revertir un archivo)
- **Testing gradual** (activar/desactivar con flag)

### 📝 Pasos de Implementación

#### Paso 1: Hacer Backup del Archivo Actual

```bash
# Hacer backup del archivo original
cp app/services/multi_agent_orchestrator.py app/services/multi_agent_orchestrator.backup.py
```

#### Paso 2: Reemplazar con Versión Híbrida

```bash
# Opción A: Usar el archivo híbrido que ya creé
mv app/services/multi_agent_orchestrator_hybrid.py app/services/multi_agent_orchestrator.py

# Opción B: Modificar manualmente (ver código abajo)
```

#### Paso 3: Código de la Versión Híbrida

Si prefieres modificar manualmente, aquí está el código clave a cambiar:

```python
# app/services/multi_agent_orchestrator.py

# ✅ AGREGAR IMPORT
from app.langgraph_adapters.orchestrator_graph import MultiAgentOrchestratorGraph

class MultiAgentOrchestrator:
    """Orquestador multi-agente - VERSIÓN HÍBRIDA"""

    def __init__(self, company_id: str, openai_service: OpenAIService = None):
        # ... código existente de inicialización ...

        # ✅ AGREGAR: Inicializar agentes
        self._initialize_agents()

        # ✅ AGREGAR: Crear grafo de LangGraph
        self._initialize_graph()

    def _initialize_graph(self):
        """Inicializar grafo de LangGraph"""
        try:
            # Filtrar agentes para el grafo
            graph_agents = {
                name: agent
                for name, agent in self.agents.items()
                if name not in ['router', 'availability']
            }

            # Crear grafo
            self.graph = MultiAgentOrchestratorGraph(
                router_agent=self.agents['router'],
                agents=graph_agents,
                company_id=self.company_id,
                enable_checkpointing=False
            )

            logger.info(f"[{self.company_id}] LangGraph orchestrator initialized")

        except Exception as e:
            logger.error(f"[{self.company_id}] Error initializing graph: {e}")
            # Si falla, el sistema puede seguir funcionando
            self.graph = None

    def get_response(self, question, user_id, conversation_manager, ...):
        """Método principal - MODIFICADO"""

        # ... código de preparación ...

        # ✅ USAR GRAFO SI ESTÁ DISPONIBLE
        if self.graph:
            logger.info(f"Using LangGraph orchestration")
            response, agent_used = self.graph.get_response(
                question=processed_question,
                user_id=user_id,
                chat_history=chat_history,
                context=""
            )
        else:
            # Fallback a implementación directa
            logger.warning(f"Using direct orchestration (fallback)")
            response, agent_used = self._orchestrate_response_direct(inputs)

        # ... resto del código ...

        return response, agent_used
```

#### Paso 4: Probar Localmente

```bash
# Iniciar servidor
python main.py

# Hacer request de prueba
curl -X POST http://localhost:8080/conversations/company_default/user123 \
  -H "Content-Type: application/json" \
  -d '{"message": "¿Cuánto cuesta el botox?"}'
```

#### Paso 5: Verificar Logs

Buscar en los logs:

```
✅ ÉXITO (usando grafo):
[company_id] Using LangGraph orchestration for user user123
[company_id] 🚀 MultiAgentOrchestratorGraph.get_response()
[company_id] 📍 Node: validate_input
[company_id] 📍 Node: classify_intent
...

❌ FALLBACK (si falla grafo):
[company_id] Using direct orchestration (fallback)
```

### 🎛️ Configuración Opcional: Feature Flag

Para mayor seguridad, puedes agregar un feature flag:

```python
# app/config/settings.py
ENABLE_LANGGRAPH = os.getenv("ENABLE_LANGGRAPH", "true").lower() == "true"

# app/services/multi_agent_orchestrator.py
from app.config.settings import ENABLE_LANGGRAPH

def _initialize_graph(self):
    if not ENABLE_LANGGRAPH:
        logger.info(f"[{self.company_id}] LangGraph disabled by feature flag")
        self.graph = None
        return

    # ... resto del código ...
```

Entonces puedes activar/desactivar sin cambiar código:

```bash
# Activar LangGraph
export ENABLE_LANGGRAPH=true
python main.py

# Desactivar LangGraph (usar implementación directa)
export ENABLE_LANGGRAPH=false
python main.py
```

---

## 📁 Opción 2: Reemplazo de Archivo

### ¿Qué es?

Reemplazar completamente el código de `multi_agent_orchestrator.py` con el código de `orchestrator_graph.py`.

### ⚠️ Desventajas

- Requiere modificar mucho código
- No hay fallback automático
- Rollback manual

### ❌ No Recomendado

Esta opción **NO es recomendada** porque:
- Pierdes la implementación original
- No puedes hacer rollback fácil
- Cambias demasiado código de una vez

---

## 🔧 Opción 3: Cambiar Imports en Todo el Código

### ¿Qué es?

Buscar todos los archivos que importan `MultiAgentOrchestrator` y cambiar el import a `MultiAgentOrchestratorGraph`.

### Archivos a Modificar

Buscar en el código:

```bash
# Buscar todos los imports
grep -r "from app.services.multi_agent_orchestrator import" app/
grep -r "from app.services import.*MultiAgentOrchestrator" app/
```

Probablemente encontrarás imports en:
- `app/routes/conversations.py`
- `app/routes/conversations_extended.py`
- `app/services/multi_agent_factory.py`
- Otros archivos de rutas

### Cambios Necesarios

```python
# ANTES
from app.services.multi_agent_orchestrator import MultiAgentOrchestrator

orchestrator = MultiAgentOrchestrator(company_id, openai_service)

# DESPUÉS
from app.langgraph_adapters import MultiAgentOrchestratorGraph
from app.agents import RouterAgent, SalesAgent, ...

# Crear agentes
router = RouterAgent(company_config, openai_service)
sales = SalesAgent(company_config, openai_service)
# ... crear todos los agentes ...

# Crear orquestador
orchestrator = MultiAgentOrchestratorGraph(
    router_agent=router,
    agents={"sales": sales, "support": support, ...},
    company_id=company_id
)
```

### ❌ No Recomendado

Esta opción **NO es recomendada** porque:
- Hay que cambiar múltiples archivos
- Más posibilidad de introducir bugs
- Rollback muy difícil
- No es necesario (Opción 1 es mejor)

---

## ✅ Testing y Validación

### 1. Tests Unitarios

Crear tests para verificar compatibilidad:

```python
# test_orchestrator_compatibility.py

def test_orchestrator_api_compatibility():
    """Verificar que la API es compatible"""

    from app.services.multi_agent_orchestrator import MultiAgentOrchestrator
    from app.models.conversation import ConversationManager

    # Crear orquestador
    orchestrator = MultiAgentOrchestrator("company_default")

    # Verificar métodos existen
    assert hasattr(orchestrator, 'get_response')
    assert hasattr(orchestrator, 'health_check')
    assert hasattr(orchestrator, 'get_system_stats')
    assert hasattr(orchestrator, 'set_vectorstore_service')
    assert hasattr(orchestrator, 'set_tool_executor')

def test_get_response_signature():
    """Verificar firma de get_response"""

    orchestrator = MultiAgentOrchestrator("company_default")
    conv_manager = ConversationManager()

    # Llamar método (debería funcionar sin errores)
    response, agent_used = orchestrator.get_response(
        question="Test",
        user_id="test_user",
        conversation_manager=conv_manager
    )

    # Verificar tipos de retorno
    assert isinstance(response, str)
    assert isinstance(agent_used, str)
```

### 2. Tests de Integración

```bash
# Probar endpoints existentes
curl -X POST http://localhost:8080/conversations/company_default/user123 \
  -H "Content-Type: application/json" \
  -d '{"message": "¿Cuánto cuesta el botox?"}'

curl -X GET http://localhost:8080/health
```

### 3. Verificar Logs

```bash
# Ver logs en tiempo real
tail -f logs/app.log | grep -E "(LangGraph|orchestration|Node:)"
```

Deberías ver:

```
[INFO] Using LangGraph orchestration for user user123
[INFO] 📍 Node: validate_input
[INFO] 📍 Node: classify_intent
[INFO] Intent classified: SALES (confidence: 0.95)
[INFO] 📍 Node: execute_sales
[INFO] ✅ sales completed successfully
```

### 4. Comparar Respuestas

```python
# Script de comparación
import requests
import json

# Hacer request
response = requests.post(
    "http://localhost:8080/conversations/company_default/user123",
    json={"message": "¿Cuánto cuesta el botox?"}
)

data = response.json()

print(f"Response: {data['response'][:100]}...")
print(f"Agent used: {data['agent_used']}")
print(f"Status: {response.status_code}")
```

---

## 🔙 Rollback

### Si Algo Sale Mal

#### Opción 1 (Wrapper Híbrido)

```bash
# Restaurar backup
cp app/services/multi_agent_orchestrator.backup.py app/services/multi_agent_orchestrator.py

# Reiniciar servidor
pkill -f "python main.py"
python main.py
```

#### Opción 1B (Con Feature Flag)

```bash
# Solo deshabilitar el flag
export ENABLE_LANGGRAPH=false
pkill -f "python main.py"
python main.py
```

#### Opción 2 o 3 (Si cambiaste imports)

```bash
# Revertir commit de git
git revert <commit_hash>

# O restaurar archivo específico
git checkout HEAD~1 -- app/services/multi_agent_orchestrator.py
```

---

## 📊 Checklist de Migración

### Antes de Migrar

- [ ] Hacer backup de `multi_agent_orchestrator.py`
- [ ] Leer documentación de la arquitectura híbrida
- [ ] Preparar plan de rollback
- [ ] Notificar al equipo

### Durante la Migración

- [ ] Implementar cambios (Opción 1 recomendada)
- [ ] Probar localmente
- [ ] Verificar logs
- [ ] Hacer tests de integración

### Después de Migrar

- [ ] Monitorear métricas en producción
- [ ] Verificar que no hay errores
- [ ] Comparar performance (latencia, errores)
- [ ] Documentar resultados

### Métricas a Monitorear

```python
# Obtener stats del sistema
stats = orchestrator.get_system_stats()

print(f"System type: {stats['system_type']}")
# → "multi-agent-hybrid-langgraph" (si está usando grafo)
# → "multi-agent-direct" (si está usando fallback)

# Si tiene graph_stats
if 'graph_stats' in stats:
    graph_stats = stats['graph_stats']
    print(f"Router executions: {graph_stats['router']['total_executions']}")
    print(f"Router avg duration: {graph_stats['router']['average_duration_ms']:.2f}ms")

    for agent_name, agent_stats in graph_stats['agents'].items():
        print(f"{agent_name}:")
        print(f"  - Executions: {agent_stats['total_executions']}")
        print(f"  - Error rate: {agent_stats['error_rate']:.2%}")
        print(f"  - Avg duration: {agent_stats['average_duration_ms']:.2f}ms")
```

---

## 🎓 Conclusión

### Opción Recomendada: Wrapper Híbrido

1. **Hacer backup** del archivo original
2. **Reemplazar** `multi_agent_orchestrator.py` con versión híbrida
3. **Probar** localmente
4. **Verificar** logs y métricas
5. **Desplegar** a producción
6. **Monitorear** y estar listo para rollback si es necesario

### Ventajas de Esta Estrategia

✅ **Mínimo riesgo**: Rollback fácil
✅ **Sin cambios externos**: No hay que modificar otros archivos
✅ **100% compatible**: API exactamente igual
✅ **Fallback automático**: Si falla el grafo, usa implementación directa
✅ **Testing gradual**: Puede activarse/desactivarse con flag

---

**Documentación creada por**: Claude Code
**Fecha**: 2025-10-24
**Versión**: 1.0.0
