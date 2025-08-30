# Backend Multi-Tenant Chatbot System

## 🏗️ Arquitectura Multi-Tenant

Este es un **backend Flask multi-tenant** completamente refactorizado que soporta múltiples empresas con aislamiento total de datos y configuraciones independientes.

### 🎯 Características Principales

- **✅ Multi-Tenant Completo**: Soporte nativo para múltiples empresas
- **🔒 Aislamiento Total**: Datos completamente separados por empresa
- **🤖 Sistema Multi-Agente**: Agentes especializados por empresa
- **📡 Integración Chatwoot**: Webhooks multi-tenant
- **🎤 Procesamiento Multimedia**: Voz e imágenes por empresa
- **🔍 RAG Personalizado**: Vectorstore independiente por empresa
- **🛡️ Auto-Recuperación**: Sistema de protección por empresa

## 📁 Estructura Multi-Tenant

```
benova-multitenant-backend/
├── companies_config.json           # Configuración de empresas
├── setup_multitenant.py           # Script de migración
├── app/
│   ├── config/
│   │   ├── company_config.py       # 🆕 Gestión multi-tenant
│   │   └── constants.py            # ⬆️ Actualizado
│   ├── agents/                     # 🆕 Sistema modular
│   │   ├── base_agent.py          # Clase base abstracta
│   │   ├── router_agent.py        # Clasificador de intenciones
│   │   ├── emergency_agent.py     # Urgencias médicas
│   │   ├── sales_agent.py         # Ventas con RAG
│   │   ├── support_agent.py       # Soporte general
│   │   ├── schedule_agent.py      # Agendamiento
│   │   └── availability_agent.py  # Consulta disponibilidad
│   ├── services/
│   │   ├── multi_agent_orchestrator.py  # 🆕 Orquestador por empresa
│   │   ├── multi_agent_factory.py       # 🆕 Factory pattern
│   │   ├── vectorstore_service.py       # ⬆️ Multi-tenant
│   │   ├── chatwoot_service.py          # ⬆️ Multi-tenant
│   │   └── vector_auto_recovery.py      # ⬆️ Multi-tenant
│   ├── models/
│   │   ├── conversation.py             # ⬆️ Multi-tenant
│   │   ├── document.py                 # ⬆️ Multi-tenant
│   │   └── schemas.py                  # ⬆️ Campos MT
│   ├── routes/
│   │   ├── webhook.py                  # ⬆️ Multi-tenant
│   │   ├── documents.py                # ⬆️ Multi-tenant
│   │   ├── conversations.py            # ⬆️ Multi-tenant
│   │   ├── health.py                   # ⬆️ Multi-tenant
│   │   ├── multimedia.py               # ⬆️ Multi-tenant
│   │   └── admin.py                    # ⬆️ Multi-tenant
│   └── utils/
│       ├── decorators.py               # ⬆️ require_company_context
│       └── helpers.py                  # ⬆️ Helpers MT
```

## 🏢 Configuración de Empresas

### Archivo `companies_config.json`

```json
{
  "benova": {
    "company_name": "Benova",
    "redis_prefix": "benova:",
    "vectorstore_index": "benova_documents",
    "schedule_service_url": "http://127.0.0.1:4040",
    "sales_agent_name": "María, asesora de Benova",
    "services": "medicina estética y tratamientos de belleza",
    "treatment_durations": {
      "limpieza facial": 60,
      "botox": 30,
      "rellenos": 45
    }
  },
  "medispa": {
    "company_name": "MediSpa Elite",
    "redis_prefix": "medispa:",
    "vectorstore_index": "medispa_documents",
    "schedule_service_url": "http://127.0.0.1:4041",
    "sales_agent_name": "Dr. López de MediSpa",
    "services": "medicina estética avanzada"
  }
}
```

## 🔧 Uso Multi-Tenant

### 1. Especificar Empresa en Requests

#### Método 1: Headers
```bash
curl -X POST /documents \
  -H "X-Company-ID: benova" \
  -H "Content-Type: application/json" \
  -d '{"content": "Información de Benova"}'
```

#### Método 2: Query Parameters
```bash
curl -X GET "/documents?company_id=medispa"
```

#### Método 3: JSON Body
```json
{
  "company_id": "benova",
  "content": "Documento específico de Benova"
}
```

### 2. Webhooks Multi-Tenant

Los webhooks de Chatwoot **detectan automáticamente** la empresa:

```json
{
  "event": "message_created",
  "conversation": {
    "id": 123,
    "account_id": "7",
    "meta": {
      "company_id": "benova"
    }
  }
}
```

**Mapeo automático por account_id:**
- `account_id: "7"` → `company_id: "benova"`
- `account_id: "8"` → `company_id: "medispa"`

### 3. Aislamiento de Datos

#### Redis Keys por Empresa
```
benova:conversation:user123
benova:document:doc456
benova:bot_status:conv789

medispa:conversation:user123
medispa:document:doc456  
medispa:bot_status:conv789
```

#### Vector Stores Independientes
- **Benova**: `benova_documents`
- **MediSpa**: `medispa_documents`
- **Dental**: `dental_documents`

## 🚀 Nuevas Rutas Multi-Tenant

### Gestión de Empresas
- `GET /companies` - Listar empresas configuradas
- `GET /company/{company_id}/status` - Estado específico
- `POST /admin/companies/reload-config` - Recargar configuración

### Health Checks por Empresa  
- `GET /health/company/{company_id}` - Health específico
- `GET /health/companies` - Overview todas las empresas

### Endpoints con Contexto de Empresa
Todos los endpoints principales ahora soportan multi-tenant:

- `POST /documents` + `X-Company-ID: benova`
- `GET /conversations?company_id=medispa`
- `POST /multimedia/process-voice` + `company_id` en form

## 🤖 Sistema Multi-Agente por Empresa

### Orquestadores Independientes
```python
# Cada empresa tiene su propio orquestador
factory = get_multi_agent_factory()
benova_orchestrator = factory.get_orchestrator("benova")
medispa_orchestrator = factory.get_orchestrator("medispa")

# Respuesta personalizada por empresa
response, agent = benova_orchestrator.get_response(
    question="¿Cuánto cuesta un botox?",
    user_id="user123",
    conversation_manager=ConversationManager("benova")
)
```

### Prompts Personalizados por Empresa
```python
# Sales Agent para Benova
f"Eres María, asesora especializada de Benova en medicina estética..."

# Sales Agent para MediSpa  
f"Eres Dr. López, especialista de MediSpa Elite en medicina estética avanzada..."
```

### Configuraciones Específicas
```python
# Duraciones por empresa
benova_config.treatment_durations = {
    "limpieza facial": 60,
    "botox": 30
}

medispa_config.treatment_durations = {
    "consulta dermatológica": 45,
    "tratamiento láser": 90
}
```

## 🔄 Migración de Single-Tenant

### Script de Migración Automática
```bash
python setup_multitenant.py
```

**El script realiza:**
1. ✅ Migra conversaciones existentes a `benova:`
2. ✅ Migra documentos existentes a `benova:`  
3. ✅ Actualiza metadata de vectores con `company_id`
4. ✅ Crea `companies_config.json` por defecto
5. ✅ Valida la configuración multi-tenant

### Compatibilidad Retroactiva
- **Empresa por defecto**: `benova` 
- **Sin breaking changes**: El código existente sigue funcionando
- **Headers opcionales**: Si no se especifica empresa, usa `benova`

## 📊 Monitoring y Observabilidad

### Logging Contextual
```
[2024-01-15 10:30:45] [benova] WEBHOOK RECEIVED - Event: message_created
[2024-01-15 10:30:46] [benova] Processing message from conversation 123
[2024-01-15 10:30:47] [benova] Sales Agent: Retrieving context for query
[2024-01-15 10:30:48] [benova] Document added with 5 chunks
```

### Health Check Completo
```json
{
  "status": "healthy",
  "system_type": "multi-tenant-multi-agent",
  "companies": {
    "total": 4,
    "configured": ["benova", "medispa", "dental", "wellness"],
    "health": {
      "benova": {"system_healthy": true},
      "medispa": {"system_healthy": true}
    },
    "stats": {
      "benova": {"conversations": 50, "documents": 25},
      "medispa": {"conversations": 30, "documents": 15}
    }
  }
}
```

### Métricas por Empresa
```json
{
  "company_id": "benova", 
  "statistics": {
    "conversations": 45,
    "documents": 23,
    "active_bots": 12
  },
  "orchestrator": {
    "system_healthy": true,
    "agents_available": ["router", "emergency", "sales", "support", "schedule"]
  }
}
```

## 🛡️ Seguridad Multi-Tenant

### Validación de Empresa
- ✅ Verificación en cada endpoint
- ✅ Validación de `company_id` válido
- ✅ Verificación de propiedad de documentos

### Aislamiento de Datos
- ✅ Prefijos Redis únicos por empresa
- ✅ Índices de vectorstore separados  
- ✅ Conversaciones completamente aisladas
- ✅ Zero-risk de contaminación cruzada

### Headers de Autenticación
```bash
# Empresa específica + API Key
curl -X DELETE /documents/doc123 \
  -H "X-Company-ID: benova" \
  -H "X-API-Key: your-secure-api-key"
```

## 🎯 Casos de Uso

### 1. Webhook de Chatwoot (Automático)
```json
POST /webhook/chatwoot
{
  "event": "message_created",
  "conversation": {"account_id": "7"},
  "content": "¿Cuánto cuesta un botox?"
}
```
→ **Detecta automáticamente**: `company_id = "benova"`
→ **Usa orquestrador específico** de Benova
→ **Respuesta personalizada** con agente de Benova

### 2. Subir Documento por Empresa
```bash
curl -X POST /documents \
  -H "X-Company-ID: medispa" \
  -d '{"content": "Información de tratamientos láser"}'
```
→ **Se almacena en**: `medispa:document:...`
→ **Vector store**: `medispa_documents`
→ **Solo accesible** por MediSpa

### 3. Chat Test por Empresa
```bash
curl -X POST /conversations/user123/test?company_id=dental \
  -d '{"message": "¿Hacen implantes dentales?"}'
```
→ **Usa orquestador** de `dental`
→ **Busca en RAG** de clínica dental
→ **Respuesta con agente** especializado en odontología

### 4. Multimedia por Empresa
```bash
curl -X POST /multimedia/process-voice \
  -F "audio=@grabacion.mp3" \
  -F "company_id=wellness" \
  -F "user_id=user456"
```
→ **Transcripción de audio**
→ **Procesamiento con agente** de spa wellness
→ **Respuesta especializada** en relajación y bienestar

## 📈 Escalabilidad

### Factory Pattern
- **Cache inteligente** de orquestadores
- **Creación bajo demanda** por empresa
- **Gestión eficiente** de recursos

### Redis Optimizado
- **Prefijos específicos** por empresa
- **TTL independientes** por tipo de dato
- **Cleanup selectivo** por empresa

### Auto-Recovery por Empresa
- **Monitoreo independiente** de cada vectorstore
- **Recuperación automática** sin afectar otras empresas
- **Health checks específicos** por empresa

## 🔧 Variables de Entorno

```bash
# Configuración multi-tenant
COMPANIES_CONFIG_FILE=companies_config.json
DEFAULT_COMPANY_ID=benova

# Auto-recovery por empresa  
VECTORSTORE_AUTO_RECOVERY=true
VECTORSTORE_HEALTH_CHECK_INTERVAL=30

# Configuración base (compartida)
OPENAI_API_KEY=sk-your-key
REDIS_URL=redis://localhost:6379
CHATWOOT_API_KEY=your-chatwoot-key
```

## 🚀 Despliegue

### Desarrollo Local
```bash
# 1. Configurar empresas
cp companies_config.json.example companies_config.json

# 2. Migrar datos existentes (opcional)
python setup_multitenant.py

# 3. Iniciar aplicación
python run.py
```

### Producción
```bash
# Railway/Docker
ENV COMPANIES_CONFIG_FILE=companies_config.json
ENV DEFAULT_COMPANY_ID=benova
ENV VECTORSTORE_AUTO_RECOVERY=true

# El sistema detecta automáticamente configuración multi-tenant
```

## 🧪 Testing Multi-Tenant

### Test por Empresa
```python
def test_benova_response():
    response = client.post('/conversations/user123/test', 
                          headers={'X-Company-ID': 'benova'},
                          json={'message': 'Hola'})
    assert 'Benova' in response.json()['bot_response']

def test_medispa_response():
    response = client.post('/conversations/user123/test',
                          headers={'X-Company-ID': 'medispa'}, 
                          json={'message': 'Hola'})
    assert 'MediSpa' in response.json()['bot_response']
```

### Aislamiento de Datos
```python
def test_data_isolation():
    # Subir documento a Benova
    client.post('/documents', 
               headers={'X-Company-ID': 'benova'},
               json={'content': 'Benova data'})
    
    # Buscar desde MediSpa (no debe encontrar)
    response = client.post('/documents/search',
                          headers={'X-Company-ID': 'medispa'},
                          json={'query': 'Benova data'})
    
    assert response.json()['results_count'] == 0
```

---

## 🎉 Sistema Multi-Tenant Completamente Funcional

El backend ahora soporta **múltiples empresas** de forma nativa con:

- ✅ **Aislamiento total** de datos
- ✅ **Configuración independiente** por empresa  
- ✅ **Agentes especializados** por empresa
- ✅ **RAG personalizado** por empresa
- ✅ **Auto-recovery** por empresa
- ✅ **Monitoring granular** por empresa
- ✅ **APIs multi-tenant** completas
- ✅ **Migración automática** desde single-tenant
- ✅ **Compatibilidad retroactiva** 100%

**El sistema está listo para escalar a múltiples empresas manteniendo la máxima seguridad y aislamiento de datos.**
