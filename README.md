# 🤖 multibackendopenIA - Backend Multi-Tenant

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/tu-usuario/multibackendopenIA)
[![Python](https://img.shields.io/badge/python-3.11+-green.svg)](https://www.python.org/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4.1--mini-412991.svg)](https://openai.com/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)
[![Deployed on Railway](https://img.shields.io/badge/deployed-railway-purple.svg)](https://railway.app/)

## 📋 Descripción

**Sistema de automatización de atención al cliente multi-agente para el sector médico** construido con Flask, LangChain y Redis. Sistema multi-tenant completo con aislamiento total de datos, que integra 6 agentes de IA especializados (router, emergency, sales, support, schedule, availability) con Chatwoot, WhatsApp, Google Calendar y procesamiento multimedia avanzado.

### 🎯 Características Principales

- ✅ **Multi-Tenant Completo**: Soporte nativo para múltiples empresas con aislamiento total
- ✅ **Sistema Multi-Agente**: 6 agentes especializados (router + 5 ejecutores) con routing inteligente
- ✅ **RAG (Retrieval-Augmented Generation)**: Vectorstore Redis independiente por empresa
- ✅ **Integración Google Calendar**: Calendar API + integración legacy opcional
- ✅ **Multimedia Avanzado**: Whisper (voz), Vision (imágenes), TTS (texto a voz)
- ✅ **Alta Disponibilidad**: Auto-recovery de vectorstore + health checks por empresa
- ✅ **Frontend Integrado**: Vue.js SPA con panel de administración multi-tenant
- ✅ **Enterprise Ready**: Soporte PostgreSQL para configuración avanzada

---

## 📊 Estadísticas del Proyecto

```
Total Archivos Python:     46 archivos
Total Líneas de Código:    ~15,000 líneas
Arquitectura:              Modular (7 módulos principales)
Agentes IA:                6 agentes (1 router + 5 especializados)
Endpoints API:             40+ rutas REST
Empresas Soportadas:       Ilimitadas (multi-tenant nativo)
Performance:               <1s respuesta promedio, 100+ req/s
Modelo OpenAI:             GPT-4.1-mini-2025-04-14 / GPT-4o-mini
```

---

## 🧠 Modelos de IA Utilizados

```python
# Modelo Principal de Chat
MODEL_NAME = "gpt-4.1-mini-2025-04-14"
# Fallback: "gpt-4o-mini"

# Embeddings para RAG
EMBEDDING_MODEL = "text-embedding-3-small"

# Multimedia
WHISPER_MODEL = "whisper-1"        # Transcripción de voz
VISION_MODEL = "gpt-4o-mini"       # Análisis de imágenes
TTS_MODEL = "tts-1"                # Texto a voz
TTS_VOICE = "alloy"                # Voz por defecto
```

---

## 🏗️ Arquitectura del Sistema

```mermaid
graph TB
    subgraph "🌐 Frontend Layer"
        VUE[Vue.js SPA]
        ADMIN[Admin Panel Multi-Tenant]
    end
    
    subgraph "🔗 API Gateway - Flask"
        FLASK[Flask Application]
        AUTH[@require_company_context]
        WEBHOOK[Webhook Handler]
    end
    
    subgraph "🤖 Multi-Agent System"
        ROUTER[Router Agent<br/>🧠 Clasificador de Intención]
        EMERGENCY[Emergency Agent<br/>🚨 Urgencias + RAG]
        SALES[Sales Agent<br/>💼 Ventas + RAG]
        SUPPORT[Support Agent<br/>🛠️ Soporte + RAG]
        SCHEDULE[Schedule Agent<br/>📅 Agendamiento + Calendar API]
        AVAILABILITY[Availability Agent<br/>⏰ Consulta Disponibilidad]
    end
    
    subgraph "💾 Data Layer - Isolated by Company"
        REDIS[(Redis Multi-Tenant<br/>{company_id}:key)]
        VECTORS[(Vectorstore per Company<br/>{company_id}_documents)]
        POSTGRES[(PostgreSQL Enterprise<br/>company_id columns)]
    end
    
    subgraph "🔌 External Integrations"
        CHATWOOT[Chatwoot<br/>account_id → company_id]
        OPENAI[OpenAI API<br/>GPT-4.1-mini / GPT-4o-mini]
        CALENDAR[Google Calendar API<br/>OAuth2 Integration]
        MULTIMEDIA[Multimedia Services<br/>Whisper + Vision + TTS]
    end
    
    VUE --> FLASK
    ADMIN --> FLASK
    FLASK --> AUTH
    AUTH --> WEBHOOK
    WEBHOOK --> ROUTER
    ROUTER --> EMERGENCY
    ROUTER --> SALES
    ROUTER --> SUPPORT
    ROUTER --> SCHEDULE
    ROUTER --> AVAILABILITY
    SCHEDULE --> AVAILABILITY
    SALES --> VECTORS
    SUPPORT --> VECTORS
    EMERGENCY --> VECTORS
    SCHEDULE --> VECTORS
    FLASK --> REDIS
    FLASK --> POSTGRES
    CHATWOOT --> WEBHOOK
    FLASK --> OPENAI
    FLASK --> MULTIMEDIA
    SCHEDULE --> CALENDAR
```

---

## 📁 Estructura del Proyecto (Detallada)

```
app/
├── 📋 __init__.py                     # 815 líneas - Factory Pattern + Multi-tenant Setup
│                                       # • Inicialización servicios (Redis, OpenAI)
│                                       # • Setup sistema multi-tenant
│                                       # • Registro de blueprints
│                                       # • Servir frontend Vue.js como SPA
│                                       # • Endpoints: /api/system/info, /api/health/full
│
├── 🤖 agents/                         # Sistema Multi-Agente (1 router + 5 especializados)
│   │
│   ├── base_agent.py                  # 562 líneas - Clase Abstracta Base (ABC)
│   │                                  # • Interface común para todos los agentes
│   │                                  # • Métodos: _initialize_agent, _create_default_prompt_template
│   │                                  # • Integración con OpenAIService y PromptService
│   │                                  # • Logging contextual por empresa
│   │                                  # ⚠️ CRÍTICO: Cambiar firmas aquí rompe TODOS los agentes
│   │
│   ├── router_agent.py                # 64 líneas - Clasificador de Intenciones
│   │                                  # • Analiza mensaje y determina agente apropiado
│   │                                  # • Clasifica en: emergency, sales, support, schedule, availability
│   │                                  # • Métodos: _execute_agent_chain
│   │                                  # • NO usa RAG (solo análisis semántico)
│   │
│   ├── sales_agent.py                 # 111 líneas - Ventas + RAG
│   │                                  # • Consultas de precios, promociones, servicios
│   │                                  # • Métodos: set_vectorstore_service, _get_sales_context
│   │                                  # • Usa RAG para buscar en catálogo de tratamientos
│   │                                  # • Depende de: VectorstoreService, PromptService
│   │
│   ├── support_agent.py               # 116 líneas - Soporte + RAG
│   │                                  # • FAQ, políticas, información general
│   │                                  # • Métodos: set_vectorstore_service, _get_support_context
│   │                                  # • Usa RAG para manual de procedimientos
│   │                                  # • Depende de: VectorstoreService, PromptService
│   │
│   ├── emergency_agent.py             # 139 líneas - Urgencias + RAG
│   │                                  # • Detección y escalación de emergencias médicas
│   │                                  # • Métodos: set_vectorstore_service, _get_emergency_context
│   │                                  # • Usa RAG para protocolos médicos
│   │                                  # • Depende de: VectorstoreService, PromptService
│   │
│   ├── schedule_agent.py              # 1241 líneas ⚠️ - Agendamiento + Google Calendar
│   │                                  # • ARCHIVO MÁS GRANDE - Candidato a refactorizar
│   │                                  # • Integración Google Calendar API (OAuth2)
│   │                                  # • Métodos: hybrid_schedule_processor, _detect_integration_type
│   │                                  # • Función interna compleja para agendar citas
│   │                                  # • Depende de: CalendarIntegrationService, AvailabilityAgent
│   │                                  # 🔴 REFACTORIZAR: Separar lógica de Google Calendar
│   │
│   └── availability_agent.py          # 83 líneas - Consulta Disponibilidad
│                                       # • Verifica horarios disponibles sin agendar
│                                       # • Métodos: set_schedule_agent, _build_schedule_context
│                                       # • Trabaja en conjunto con schedule_agent
│                                       # • NO usa RAG (consulta directa a calendario)
│
├── ⚙️ config/                         # Configuración Multi-Tenant
│   │
│   ├── settings.py                    # 83 líneas - Config por Ambiente
│   │                                  # • DevelopmentConfig, ProductionConfig, TestingConfig
│   │                                  # • Variables: MODEL_NAME, REDIS_URL, CHATWOOT_API_KEY
│   │                                  # • Configura: OpenAI, Redis, Chatwoot, Multimedia
│   │
│   ├── constants.py                   # 85 líneas - Constantes Globales
│   │                                  # • Mapeo account_id → company_id (si existe)
│   │                                  # • Constantes de sistema
│   │
│   ├── company_config.py              # 613 líneas - Configuración Base por Empresa
│   │                                  # • CompanyConfig (dataclass)
│   │                                  # • Campos: company_id, redis_prefix, vectorstore_index
│   │                                  # • CompanyConfigManager (gestor singleton)
│   │                                  # • Métodos: get_config, validate_company_context
│   │                                  # • Carga desde JSON o PostgreSQL
│   │                                  # ⚠️ CRÍTICO: REQUIRED_FIELDS no se pueden eliminar
│   │
│   └── extended_company_config.py     # 408 líneas - Config Extendida
│                                       # • AgendaConfig, TreatmentConfig
│                                       # • Duraciones de tratamientos por empresa
│                                       # • Configuración de agendamiento avanzada
│
├── 📦 models/                         # Modelos de Datos Multi-Tenant
│   │
│   ├── conversation.py                # 308 líneas - ConversationManager
│   │                                  # • Gestión de historial por empresa en Redis
│   │                                  # • Keys: {company_id}:conversation:{user_id}
│   │                                  # • Métodos: add_message, get_history, clear_history
│   │                                  # • Windowing de mensajes (MAX_CONTEXT_MESSAGES)
│   │
│   ├── document.py                    # 597 líneas - DocumentManager
│   │                                  # • CRUD documentos con company_id
│   │                                  # • DocumentChangeTracker para auditoría
│   │                                  # • Métodos: add_document, search, delete
│   │                                  # • Embeddings en vectorstore aislado
│   │                                  # ⚠️ CRÍTICO: Cambiar company_id rompe multi-tenant
│   │
│   └── schemas.py                     # 83 líneas - Pydantic Schemas
│                                       # • Validación con campos multi-tenant
│                                       # • MultiTenantMixin (company_id obligatorio)
│                                       # • Schemas: DocumentInput, WebhookData, etc.
│
├── 🛣️ routes/                         # Endpoints API (40+ rutas)
│   │
│   ├── webhook.py                     # 123 líneas - Webhook Principal
│   │                                  # • POST /chatwoot - Webhook principal desde Chatwoot
│   │                                  # • POST /test - Webhook de prueba
│   │                                  # • Flujo: extract_company_id → validate → orchestrator
│   │                                  # ⚠️ CRÍTICO: Punto de entrada del sistema
│   │                                  # • Depende de: ChatwootService, MultiAgentFactory
│   │
│   ├── admin.py                       # 1585 líneas ⚠️ - Panel SuperAdmin
│   │                                  # • ARCHIVO MÁS GRANDE - Candidato a refactorizar
│   │                                  # • CRUD empresas completo
│   │                                  # • Gestión configuración multi-tenant
│   │                                  # • Diagnósticos y troubleshooting
│   │                                  # 🔴 REFACTORIZAR: Dividir en módulos más pequeños
│   │
│   ├── companies.py                   # 584 líneas - Gestión de Empresas
│   │                                  # • GET /companies - Listar empresas
│   │                                  # • GET /companies/<id> - Info específica
│   │                                  # • GET /companies/<id>/status - Estado empresa
│   │                                  # • POST /companies/reload-config - Recargar config
│   │                                  # • GET /companies/health - Health de todas
│   │                                  # • GET /companies/<id>/agents - Agentes empresa
│   │                                  # • GET /companies/<id>/metrics - Métricas empresa
│   │
│   ├── documents.py                   # 776 líneas - CRUD Documentos RAG
│   │                                  # • POST /documents - Subir documento
│   │                                  # • GET /documents - Listar documentos
│   │                                  # • POST /documents/search - Búsqueda RAG
│   │                                  # • GET /documents/<id> - Info documento
│   │                                  # • GET /documents/<id>/debug - Debug documento
│   │                                  # • POST /documents/bulk - Subida masiva
│   │                                  # • DELETE /documents/<id> - Eliminar documento
│   │                                  # • POST /documents/cleanup - Limpiar vectores huérfanos
│   │                                  # • GET /documents/diagnostics - Diagnóstico
│   │                                  # • GET /documents/<id>/vectors - Ver vectores
│   │                                  # • GET /documents/stats - Estadísticas
│   │
│   ├── conversations.py               # 157 líneas - Historial Conversaciones
│   │                                  # • GET /conversations - Listar conversaciones
│   │                                  # • GET /conversations/<user_id> - Historial usuario
│   │                                  # • DELETE /conversations/<user_id> - Limpiar historial
│   │                                  # • POST /conversations/<user_id>/test - Chat test
│   │
│   ├── conversations_extended.py      # 182 líneas - Funcionalidad Avanzada
│   │                                  # • Analytics de conversaciones
│   │                                  # • Endpoints extendidos
│   │
│   ├── multimedia.py                  # 337 líneas - Procesamiento Multimedia
│   │                                  # • POST /multimedia/process-voice - Transcripción audio
│   │                                  # • POST /multimedia/process-image - Análisis imagen
│   │                                  # • POST /multimedia/test-multimedia - Test multimedia
│   │                                  # • GET /multimedia/capabilities/<id> - Capacidades empresa
│   │                                  # • GET /multimedia/stats - Estadísticas multimedia
│   │                                  # • Usa: Whisper, Vision, TTS
│   │
│   ├── health.py                      # 172 líneas - Health Checks
│   │                                  # • GET /health - Health general del sistema
│   │                                  # • GET /health/company/<id> - Health específico empresa
│   │                                  # • GET /health/companies - Overview todas empresas
│   │
│   ├── status.py                      # 281 líneas - Estado del Sistema
│   │                                  # • Métricas en tiempo real
│   │                                  # • Estadísticas del sistema
│   │
│   └── diagnostic.py                  # 474 líneas - Troubleshooting
│                                       # • Diagnósticos de conexiones
│                                       # • Tests de servicios por empresa
│
├── 🔧 services/                       # Lógica de Negocio Multi-Tenant
│   │
│   ├── multi_agent_orchestrator.py   # 301 líneas - Orquestador Principal
│   │                                  # • Clase: MultiAgentOrchestrator
│   │                                  # • Métodos principales:
│   │                                  #   - __init__(company_id)
│   │                                  #   - set_vectorstore_service
│   │                                  #   - _initialize_agents
│   │                                  #   - get_response
│   │                                  #   - _orchestrate_response
│   │                                  #   - _execute_selected_agent
│   │                                  #   - search_documents
│   │                                  #   - health_check
│   │                                  #   - get_system_stats
│   │                                  # • Depende de: Todos los agentes, OpenAIService,
│   │                                  #               VectorstoreService, ConversationManager
│   │
│   ├── multi_agent_factory.py        # 135 líneas - Factory Pattern
│   │                                  # • Cache de orquestadores por empresa
│   │                                  # • Función: get_orchestrator_for_company(company_id)
│   │                                  # • Lazy loading de servicios
│   │                                  # ⚠️ CRÍTICO: Gestiona un orquestador por empresa
│   │
│   ├── openai_service.py              # 323 líneas - Cliente OpenAI
│   │                                  # • Clase: OpenAIService
│   │                                  # • Modelos:
│   │                                  #   - Chat: gpt-4.1-mini-2025-04-14
│   │                                  #   - Fallback: gpt-4o-mini
│   │                                  #   - Embeddings: text-embedding-3-small
│   │                                  #   - Whisper: whisper-1
│   │                                  #   - Vision: gpt-4o-mini
│   │                                  #   - TTS: tts-1
│   │                                  # • Métodos: get_chat_model, generate_embeddings
│   │                                  # • Gestión de tokens y costos
│   │
│   ├── prompt_service.py              # 898 líneas ⚠️ - Sistema de Prompts
│   │                                  # • ARCHIVO GRANDE - Candidato a refactorizar
│   │                                  # • Prompts dinámicos por empresa
│   │                                  # • Carga desde JSON o PostgreSQL
│   │                                  # • Métodos: get_prompt, get_sales_prompt, etc.
│   │                                  # 🔴 REFACTORIZAR: Agregar cache Redis
│   │
│   ├── vectorstore_service.py        # 361 líneas - Redis Vector Store
│   │                                  # • Clase: VectorstoreService
│   │                                  # • Métodos principales:
│   │                                  #   - __init__(company_id)
│   │                                  #   - _initialize_vectorstore
│   │                                  #   - get_retriever
│   │                                  #   - search_by_company
│   │                                  #   - add_texts
│   │                                  #   - create_chunks
│   │                                  #   - find_vectors_by_doc_id
│   │                                  #   - delete_vectors
│   │                                  #   - check_health
│   │                                  # • Índice por empresa: {company_id}_documents
│   │                                  # • Embeddings aislados
│   │                                  # • Búsqueda semántica con filtros
│   │
│   ├── vector_auto_recovery.py       # 461 líneas - Auto-Recuperación
│   │                                  # • RedisVectorAutoRecovery
│   │                                  # • VectorstoreProtectionMiddleware
│   │                                  # • Monitoreo de salud por empresa
│   │                                  # • Recuperación automática de índices
│   │
│   ├── redis_service.py               # 50 líneas - Cliente Redis Base
│   │                                  # • Prefijos por empresa
│   │                                  # • Función: get_redis_client()
│   │
│   ├── chatwoot_service.py            # 473 líneas - Integración Chatwoot
│   │                                  # • Clase: ChatwootService
│   │                                  # • Métodos: send_message, process_incoming_message
│   │                                  # • Mapeo account_id → company_id (si configurado)
│   │                                  # • Envío de respuestas por empresa
│   │                                  # • Depende de: MultiAgentOrchestrator, ConversationManager
│   │
│   ├── calendar_integration_service.py # 543 líneas - Google Calendar API
│   │                                  # • Clase: CalendarIntegrationService
│   │                                  # • Integración Google Calendar (OAuth2)
│   │                                  # • Métodos: create_event, check_availability
│   │                                  # • Depende de: google-api-python-client
│   │                                  # • Soporta: Google Calendar
│   │
│   ├── multimedia_service.py          # 174 líneas - Procesamiento Multimedia
│   │                                  # • Clase: MultimediaService
│   │                                  # • Whisper API para transcripción audio
│   │                                  # • Vision API para análisis imágenes
│   │                                  # • TTS para generación de voz
│   │
│   └── company_config_service.py      # 631 líneas - Config Empresarial
│                                       # • EnterpriseCompanyConfig
│                                       # • EnterpriseCompanyConfigService
│                                       # • PostgreSQL para enterprise
│                                       # • Migración JSON → PostgreSQL
│
└── 🛠️ utils/                          # Utilidades Multi-Tenant
    │
    ├── decorators.py                  # 91 líneas - Decoradores Clave
    │                                  # • @handle_errors - Manejo centralizado errores
    │                                  # • @require_api_key - Autenticación API
    │                                  # • @cache_result(timeout) - Cache de funciones
    │                                  # • @require_company_context - Validación multi-tenant
    │                                  # ⚠️ CRÍTICO: @require_company_context usado en todos los endpoints
    │
    ├── error_handlers.py              # 127 líneas - Manejo de Errores
    │                                  # • Error handlers centralizados
    │                                  # • Logging contextual
    │                                  # • ServiceError, ValidationError, WebhookError
    │
    ├── validators.py                  # 123 líneas - Validadores
    │                                  # • validate_company_id()
    │                                  # • validate_webhook_data()
    │                                  # • Validación de datos de entrada
    │
    └── helpers.py                     # 159 líneas - Funciones Auxiliares
                                        # • extract_company_id()
                                        # • create_success_response()
                                        # • create_error_response()
                                        # • Funciones comunes
```

### 📊 Archivos Más Grandes (Candidatos a Refactorización)

```
🔴 CRÍTICO - Refactorizar AHORA:
1. admin.py                 1585 líneas ⚠️  → Dividir en módulos por funcionalidad
2. schedule_agent.py        1241 líneas ⚠️  → Separar lógica Google Calendar
3. prompt_service.py         898 líneas ⚠️  → Agregar cache Redis, modularizar

🟡 IMPORTANTE - Próximas 2-4 semanas:
4. __init__.py               815 líneas     → Separar setup de routes
5. documents.py              776 líneas     → Modularizar endpoints CRUD
6. company_config_service.py 631 líneas     → Simplificar lógica enterprise
```

---

## 🔗 MAPA DE DEPENDENCIAS CRÍTICAS

> ⚠️ **IMPORTANTE**: Usa este mapa antes de modificar cualquier componente para entender qué más se verá afectado.

### 🎯 Si modificas un AGENTE (agents/*.py)

**Dependencias Directas (TODOS los agentes heredan de base_agent.py):**
```python
✅ base_agent.py              # Clase base abstracta (ABC)
✅ openai_service.py          # Para llamadas GPT
✅ prompt_service.py          # get_prompt_service()
✅ company_config.py          # CompanyConfig para configuración

# SOLO agentes con RAG (sales, support, emergency, schedule):
✅ vectorstore_service.py     # set_vectorstore_service()
```

**Dependencias Indirectas:**
```python
⚡ multi_agent_orchestrator.py    # Invoca a los agentes vía _execute_selected_agent
⚡ multi_agent_factory.py         # Instancia el orquestador
⚡ router_agent.py                # Clasifica qué agente usar
⚡ webhook.py                      # Punto de entrada del sistema
```

**⚠️ ZONA DE PELIGRO - Cambios que ROMPEN todo:**
```python
# ❌ CAMBIAR ESTO EN base_agent.py ROMPE TODOS LOS AGENTES:
class BaseAgent(ABC):
    @abstractmethod
    def _initialize_agent(self):  # Firma obligatoria
        pass
    
    @abstractmethod  
    def _create_default_prompt_template(self) -> ChatPromptTemplate:  # Firma obligatoria
        pass
    
    @abstractmethod
    def _execute_agent_chain(self, inputs: Dict[str, Any]) -> str:  # Firma obligatoria
        pass

# ✅ SEGURO CAMBIAR (métodos privados de agentes específicos):
class SalesAgent(BaseAgent):
    def _get_sales_context(self, inputs):  # Método privado del agente
        pass
```

**Checklist para modificar un agente:**
- [ ] ¿Mantiene la firma de métodos abstractos de BaseAgent?
- [ ] ¿set_vectorstore_service() se llama si usa RAG?
- [ ] ¿Importa correctamente CompanyConfig?
- [ ] ¿Usa get_prompt_service() para obtener prompts?
- [ ] ¿Testear con multi_agent_orchestrator.py?

---

### 🏭 Si creas un NUEVO ORQUESTADOR

**CHECKLIST COMPLETO para crear NuevoOrquestador:**

#### 1. **Imports Obligatorios**
```python
from app.config.company_config import CompanyConfig, get_company_config
from app.agents import (
    RouterAgent, SalesAgent, SupportAgent, 
    EmergencyAgent, ScheduleAgent, AvailabilityAgent
)
from app.services.openai_service import OpenAIService
from app.services.vectorstore_service import VectorstoreService
from app.models.conversation import ConversationManager
```

#### 2. **Estructura Mínima Requerida**
```python
class NuevoOrquestador:
    def __init__(self, company_id: str, openai_service: OpenAIService = None):
        # ✅ OBLIGATORIO: Guardar company_id
        self.company_id = company_id
        
        # ✅ OBLIGATORIO: Cargar config de empresa
        self.company_config = get_company_config(company_id)
        
        # ✅ OBLIGATORIO: Inicializar OpenAIService
        self.openai_service = openai_service or OpenAIService()
        
        # ✅ OBLIGATORIO: Inicializar VectorstoreService
        self.vectorstore_service = None
        
        # ✅ OBLIGATORIO: Inicializar agentes
        self._initialize_agents()
    
    def set_vectorstore_service(self, vectorstore_service: VectorstoreService):
        """✅ OBLIGATORIO: Método para inyectar vectorstore"""
        self.vectorstore_service = vectorstore_service
        # Propagar a agentes que usan RAG
        self.sales_agent.set_vectorstore_service(vectorstore_service)
        self.support_agent.set_vectorstore_service(vectorstore_service)
        self.emergency_agent.set_vectorstore_service(vectorstore_service)
    
    def _initialize_agents(self):
        """✅ OBLIGATORIO: Inicializar todos los agentes"""
        self.router_agent = RouterAgent(self.company_config, self.openai_service)
        self.sales_agent = SalesAgent(self.company_config, self.openai_service)
        # ... otros agentes
    
    def get_response(self, question: str, user_id: str, 
                     conversation_manager: ConversationManager,
                     media_type: str = "text", media_context: str = None) -> Tuple[str, str]:
        """
        ✅ OBLIGATORIO: Método principal de respuesta
        
        Args:
            question: Pregunta del usuario
            user_id: ID del usuario
            conversation_manager: Gestor de conversaciones
            media_type: Tipo de media (text/voice/image)
            media_context: Contexto adicional de multimedia
            
        Returns:
            Tuple[str, str]: (respuesta, agente_usado)
        """
        pass
    
    def health_check(self) -> Dict[str, Any]:
        """✅ OBLIGATORIO: Health check del orquestador"""
        return {
            "status": "healthy",
            "company_id": self.company_id,
            "agents_available": 6
        }
```

#### 3. **Actualizar webhook.py**
```python
# ⚠️ CRÍTICO: Debes actualizar routes/webhook.py línea ~50

# ANTES:
from app.services.multi_agent_factory import get_orchestrator_for_company
orchestrator = get_orchestrator_for_company(company_id)

# DESPUÉS (si quieres usar tu nuevo orquestador):
from app.services.nuevo_orquestador import NuevoOrquestador
from app.services.vectorstore_service import VectorstoreService

orchestrator = NuevoOrquestador(company_id)
vectorstore_service = VectorstoreService(company_id)
orchestrator.set_vectorstore_service(vectorstore_service)
```

#### 4. **Actualizar multi_agent_factory.py (Opcional)**
```python
# services/multi_agent_factory.py

_orchestrators_cache = {}

def get_orchestrator_for_company(company_id: str, orchestrator_type: str = "default"):
    """Factory con soporte para múltiples tipos"""
    cache_key = f"{company_id}:{orchestrator_type}"
    
    if cache_key in _orchestrators_cache:
        return _orchestrators_cache[cache_key]
    
    if orchestrator_type == "nuevo":
        from app.services.nuevo_orquestador import NuevoOrquestador
        orchestrator = NuevoOrquestador(company_id)
    else:
        orchestrator = MultiAgentOrchestrator(company_id)
    
    # Inicializar vectorstore
    vectorstore_service = VectorstoreService(company_id)
    orchestrator.set_vectorstore_service(vectorstore_service)
    
    _orchestrators_cache[cache_key] = orchestrator
    return orchestrator
```

#### 5. **Testing Obligatorio**
```python
def test_nuevo_orquestador_basic():
    """Test básico de funcionamiento"""
    orchestrator = NuevoOrquestador("benova")
    assert orchestrator.company_id == "benova"
    assert orchestrator.router_agent is not None
    
def test_nuevo_orquestador_aislamiento():
    """Test de aislamiento multi-tenant"""
    orch_benova = NuevoOrquestador("benova")
    orch_medispa = NuevoOrquestador("medispa")
    
    # No deben compartir datos
    assert orch_benova.company_id != orch_medispa.company_id
    assert orch_benova.company_config.redis_prefix != orch_medispa.company_config.redis_prefix
    
def test_nuevo_orquestador_response():
    """Test de generación de respuesta"""
    orchestrator = NuevoOrquestador("benova")
    vectorstore = VectorstoreService("benova")
    orchestrator.set_vectorstore_service(vectorstore)
    
    conversation_manager = ConversationManager("benova")
    response, agent_used = orchestrator.get_response(
        question="Hola",
        user_id="test_user",
        conversation_manager=conversation_manager
    )
    
    assert response is not None
    assert agent_used in ["sales", "support", "emergency", "schedule", "availability"]
```

---

### 📄 Si modificas DOCUMENTOS/RAG (models/document.py)

**⚠️ ZONA DE ALTO RIESGO - Afecta TODA la búsqueda semántica:**

```python
# Componentes que dependen de document.py:
✅ vectorstore_service.py     # create_chunks, add_texts, delete_vectors
✅ vector_auto_recovery.py    # RedisVectorAutoRecovery
✅ sales_agent.py             # set_vectorstore_service, _get_sales_context
✅ support_agent.py           # set_vectorstore_service, _get_support_context
✅ emergency_agent.py         # set_vectorstore_service, _get_emergency_context
✅ schedule_agent.py          # set_vectorstore_service (menos crítico)
✅ routes/documents.py        # add_document, search_documents, delete_document
✅ Redis Vector Store         # Índices: {company_id}_documents
```

**❌ CAMBIOS PELIGROSOS:**
```python
class Document:
    # ❌ CAMBIAR ESTO ROMPE MULTI-TENANT:
    company_id: str    # Campo obligatorio para aislamiento
    
    # ❌ CAMBIAR ESTO ROMPE EMBEDDINGS:
    chunk_text: str    # Texto embebido en vectorstore
    content: str       # Contenido original del documento
    
    # ⚠️ CAMBIAR CON CUIDADO (migración necesaria):
    metadata: dict     # Puedes AGREGAR campos, NO ELIMINAR
```

**✅ CAMBIOS SEGUROS:**
```python
class Document:
    # ✅ Agregar campos nuevos está bien:
    version: int = 1
    tags: List[str] = []
    author: str = ""
    
    # ✅ Métodos privados están bien:
    def _validate_format(self):
        pass
    
    def _enrich_metadata(self):
        pass
```

**Flujo de impacto si modificas document.py:**
```
document.py modificado
    ↓
vectorstore_service.py debe actualizarse
    ↓
Agentes con RAG (sales, support, emergency) deben actualizarse
    ↓
routes/documents.py debe actualizarse
    ↓
REINDEXAR todos los documentos de todas las empresas
```

**Checklist para modificar document.py:**
- [ ] ¿Mantiene company_id como campo obligatorio?
- [ ] ¿Mantiene chunk_text y content para embeddings?
- [ ] ¿Metadatos nuevos son opcionales (no rompen docs existentes)?
- [ ] ¿Actualizar vectorstore_service.py si cambia estructura?
- [ ] ¿Plan de migración para documentos existentes en Redis?
- [ ] ¿Tests de indexación y búsqueda pasan?

---

### 🔌 Si modificas WEBHOOKS (routes/webhook.py)

**⚠️ AFECTA TODA LA ENTRADA DEL SISTEMA - Flujo crítico:**

```
Chatwoot → Webhook Handler → Orchestrator → Agents → Response → Chatwoot
```

**Dependencias de webhook.py:**
```python
✅ chatwoot_service.py            # ChatwootService.process_incoming_message
✅ multi_agent_factory.py         # get_orchestrator_for_company
✅ conversation_manager.py        # ConversationManager
✅ company_config.py              # extract_company_id_from_webhook, validate_company_context
✅ utils/validators.py            # validate_webhook_data
✅ utils/decorators.py            # @handle_errors
```

**Flujo Paso a Paso (NO ROMPER NINGUNO):**
```python
@bp.route('/chatwoot', methods=['POST'])
@handle_errors
def chatwoot_webhook():
    # PASO 1: ❌ NO ROMPER - Recibir y validar datos
    data = request.json
    validate_webhook_data(data)
    
    # PASO 2: ❌ NO ROMPER - Extraer company_id
    company_id = extract_company_id_from_webhook(data)
    
    # PASO 3: ❌ NO ROMPER - Validar contexto de empresa
    if not validate_company_context(company_id):
        return {"error": "Invalid company"}, 400
    
    # PASO 4: ❌ NO ROMPER - Inicializar servicios
    chatwoot_service = ChatwootService(company_id=company_id)
    conversation_manager = ConversationManager(company_id=company_id)
    
    # PASO 5: ❌ NO ROMPER - Obtener orquestador
    orchestrator = get_orchestrator_for_company(company_id)
    if not orchestrator:
        return {"error": "Orchestrator not available"}, 500
    
    # PASO 6: ❌ NO ROMPER - Procesar mensaje
    result = chatwoot_service.process_incoming_message(
        data, 
        conversation_manager, 
        orchestrator
    )
    
    # PASO 7: ❌ NO ROMPER - Retornar respuesta
    result["company_id"] = company_id
    return result, 200
```

**Si cambias la estructura del webhook:**
1. Actualizar `utils/validators.py` → `validate_webhook_data()`
2. Actualizar `company_config.py` → `extract_company_id_from_webhook()`
3. Actualizar `chatwoot_service.py` → `process_incoming_message()`
4. Actualizar tests de integración
5. Probar con datos reales de Chatwoot

---

### ⚙️ Si modificas CONFIGURACIÓN (config/*.py)

**⚠️ IMPACTO GLOBAL - Afecta TODAS las empresas:**

**config/company_config.py - ZONA DE MÁXIMO PELIGRO:**
```python
@dataclass
class CompanyConfig:
    # ❌ CAMPOS REQUERIDOS - NO SE PUEDEN ELIMINAR:
    company_id: str                  # Identificador único
    company_name: str                # Nombre de empresa
    redis_prefix: str                # Prefijo Redis: {prefix}:key
    vectorstore_index: str           # Índice vectorstore: {company_id}_documents
    
    # ⚠️ CAMPOS OPCIONALES - Pueden tener defaults:
    model_name: str = "gpt-4o-mini"  # Modelo GPT por empresa
    max_documents: int = 1000         # Límite de documentos
    
    # ✅ SEGURO AGREGAR CAMPOS NUEVOS CON DEFAULTS:
    nuevo_campo: str = "default_value"
```

**Componentes que usan CompanyConfig:**
```python
✅ Todos los agentes (agents/*.py)      # CompanyConfig en __init__
✅ Todos los servicios (services/*.py)  # get_company_config(company_id)
✅ multi_agent_orchestrator.py          # self.company_config
✅ routes/admin.py                      # Gestión de configuración
✅ routes/companies.py                  # CRUD de empresas
```

**Si cambias REQUIRED_FIELDS:**
```python
# Pasos obligatorios para migración:
1. Actualizar companies_config.json con nuevos campos
2. Ejecutar migración PostgreSQL (si aplica)
3. Actualizar validators.py → validate_company_id()
4. Actualizar routes/admin.py → crear/actualizar empresa
5. Actualizar todos los tests
6. Deploy con downtime planificado
```

**config/settings.py - Variables de Entorno:**
```python
# ⚠️ CAMBIAR ESTAS VARIABLES REQUIERE RESTART:
MODEL_NAME = os.getenv('MODEL_NAME', 'gpt-4o-mini')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
CHATWOOT_API_KEY = os.getenv('CHATWOOT_API_KEY')

# Si cambias defaults, impacta comportamiento global del sistema
```

---

### 🔴 DEPENDENCIAS DE REDIS

**Redis se usa para 3 cosas CRÍTICAS:**

#### 1. **Historial de Conversación**
```python
# Keys por empresa:
{company_id}:conversation:{user_id}

# Gestión:
ConversationManager(company_id).add_message(user_id, message)
ConversationManager(company_id).get_history(user_id)

# Si Redis cae:
❌ No hay historial de conversación
❌ Agentes pierden contexto previo
✅ Sistema sigue funcionando pero sin memoria
✅ ConversationManager tiene manejo de errores
```

#### 2. **Vector Store (Embeddings para RAG)**
```python
# Índices por empresa:
{company_id}_documents

# Gestión:
VectorstoreService(company_id).search_by_company(query)
VectorstoreService(company_id).add_texts(texts, metadatas)

# Si Redis cae:
❌ RAG no funciona (no hay embeddings)
❌ Búsqueda semántica falla
✅ Agentes sin RAG siguen funcionando (router, availability)
✅ VectorstoreProtectionMiddleware intenta auto-recuperar
```

#### 3. **Caché de Configuración (Opcional)**
```python
# Cache opcional de config:
{company_id}:config:cache

# Si Redis cae:
✅ Config se carga desde JSON/PostgreSQL directamente
```

**Auto-Recuperación:**
```python
# vector_auto_recovery.py maneja auto-recuperación automáticamente
class RedisVectorAutoRecovery:
    def monitor_and_recover(self, company_id: str):
        """Monitorea salud y recupera automáticamente"""
        if not self.check_health(company_id):
            self.rebuild_index(company_id)

# Middleware activo si:
VECTORSTORE_AUTO_RECOVERY = os.getenv('VECTORSTORE_AUTO_RECOVERY', 'true')
```

**Verificación de Redis:**
```bash
# Health check de Redis por empresa
curl http://localhost:8080/health/company/benova

# Response esperado:
{
  "redis_healthy": true,
  "vectorstore_healthy": true,
  "vectorstore_index": "benova_documents"
}
```

---

### 🔴 DEPENDENCIAS DE POSTGRESQL (Enterprise)

**PostgreSQL se usa para (OPCIONAL - fallback a JSON):**

#### 1. **Prompts por Empresa**
```sql
SELECT * FROM prompts WHERE company_id = 'benova';
```

#### 2. **Configuración de Empresas**
```sql
SELECT * FROM companies WHERE company_id = 'benova';
SELECT * FROM agent_configs WHERE company_id = 'benova';
```

#### 3. **Metadatos de Documentos (Opcional)**
```sql
SELECT * FROM documents WHERE company_id = 'benova';
```

**Si PostgreSQL cae:**
```
❌ No se pueden cargar prompts customizados → Usa prompts por defecto
❌ Config enterprise no disponible → Fallback a JSON
✅ Sistema sigue funcionando con configuración básica
✅ Fallback automático a companies_config.json
```

**Fallback a JSON (Automático):**
```python
# company_config_service.py tiene fallback automático:
try:
    config = load_from_postgresql(company_id)
    logger.info(f"Config cargada desde PostgreSQL: {company_id}")
except Exception as e:
    logger.warning(f"PostgreSQL no disponible, usando JSON fallback: {e}")
    config = load_from_json(company_id)
```

**Migración PostgreSQL → JSON:**
```bash
# Si necesitas volver a JSON:
python migrate_postgresql_to_json.py

# Configurar variable de entorno:
EXTENDED_CONFIG_ENABLED=false
```

---

## 🚀 Endpoints API (COMPLETO Y VERIFICADO)

### 📨 **Webhook - Punto de Entrada Principal**

```http
POST /api/webhook/chatwoot
Content-Type: application/json

# Request (desde Chatwoot)
{
  "event": "message_created",
  "message_type": "incoming",
  "content": "Hola, quiero agendar una cita para botox",
  "conversation": {
    "id": 123,
    "account_id": "7",  # Mapea a company_id vía constants.py
    "contact_inbox": {
      "contact_id": 456
    }
  },
  "sender": {
    "name": "Juan Pérez",
    "phone_number": "+573001234567"
  }
}

# Response
{
  "status": "success",
  "company_id": "benova",
  "agent_used": "sales",
  "response_sent": true,
  "conversation_id": 123
}
```

```http
POST /api/webhook/test
Content-Type: application/json

# Request (para testing)
{
  "company_id": "benova",
  "user_id": "test_user",
  "message": "Hola"
}

# Response
{
  "status": "success",
  "response": "¡Hola! Soy María...",
  "agent_used": "support"
}
```

### 🏢 **Companies - Gestión de Empresas**

```http
GET /api/companies
# Listar todas las empresas configuradas

Response 200:
{
  "total": 4,
  "companies": [
    {
      "company_id": "benova",
      "company_name": "Benova Medicina Estética",
      "subscription_tier": "premium",
      "active": true
    },
    ...
  ]
}
```

```http
GET /api/companies/{company_id}
# Obtener configuración específica de empresa

Response 200:
{
  "company_id": "benova",
  "company_name": "Benova Medicina Estética",
  "business_type": "medicina_estetica",
  "model_name": "gpt-4o-mini",
  "redis_prefix": "benova:",
  "vectorstore_index": "benova_documents",
  "agents": [
    {"name": "router", "status": "active"},
    {"name": "sales", "status": "active", "rag_enabled": true},
    {"name": "support", "status": "active", "rag_enabled": true},
    {"name": "emergency", "status": "active", "rag_enabled": true},
    {"name": "schedule", "status": "active"},
    {"name": "availability", "status": "active"}
  ]
}
```

```http
GET /api/companies/{company_id}/status
# Estado operacional de la empresa

Response 200:
{
  "company_id": "benova",
  "status": "operational",
  "agents_healthy": true,
  "vectorstore_healthy": true,
  "redis_healthy": true,
  "last_message": "2024-10-14T10:30:00Z"
}
```

```http
POST /api/companies/reload-config
# Recargar configuración de todas las empresas

Response 200:
{
  "status": "success",
  "companies_reloaded": 4,
  "timestamp": "2024-10-14T10:30:00Z"
}
```

```http
GET /api/companies/health
# Overview de salud de todas las empresas

Response 200:
{
  "total_companies": 4,
  "healthy_companies": 4,
  "companies": {
    "benova": {"status": "healthy", "agents": 6},
    "medispa": {"status": "healthy", "agents": 6}
  }
}
```

```http
GET /api/companies/{company_id}/agents
# Información de agentes de la empresa

Response 200:
{
  "company_id": "benova",
  "agents": [
    {
      "name": "router",
      "type": "classifier",
      "status": "active",
      "rag_enabled": false
    },
    {
      "name": "sales",
      "type": "executor",
      "status": "active",
      "rag_enabled": true,
      "vectorstore_index": "benova_documents"
    },
    ...
  ]
}
```

```http
GET /api/companies/{company_id}/metrics
# Métricas de la empresa

Response 200:
{
  "company_id": "benova",
  "metrics": {
    "total_conversations": 245,
    "messages_today": 89,
    "documents_indexed": 123,
    "agent_usage": {
      "sales": 45,
      "support": 32,
      "schedule": 12
    },
    "avg_response_time": "0.8s"
  }
}
```

### 📄 **Documents - Sistema RAG**

```http
POST /api/documents
Content-Type: multipart/form-data
Headers: X-Company-ID: benova

file: documento.pdf
metadata: {
  "category": "tratamientos",
  "subcategory": "botox"
}

Response 201:
{
  "status": "success",
  "document_id": "doc_12345",
  "company_id": "benova",
  "chunks_created": 15,
  "vectorstore_index": "benova_documents",
  "embeddings_created": true
}
```

```http
GET /api/documents?company_id=benova&page=1&limit=20
# Listar documentos de la empresa

Response 200:
{
  "total": 123,
  "page": 1,
  "limit": 20,
  "documents": [
    {
      "id": "doc_12345",
      "filename": "botox_info.pdf",
      "category": "tratamientos",
      "chunks": 15,
      "created_at": "2024-01-15T10:30:00Z"
    },
    ...
  ]
}
```

```http
POST /api/documents/search
Headers: X-Company-ID: benova
Content-Type: application/json

{
  "query": "¿Cuánto cuesta el botox?",
  "top_k": 5,
  "filter": {"category": "tratamientos"}
}

Response 200:
{
  "results": [
    {
      "content": "El botox tiene un costo de $300.000 COP...",
      "score": 0.92,
      "metadata": {
        "category": "tratamientos",
        "subcategory": "botox",
        "document_id": "doc_12345"
      }
    },
    ...
  ],
  "total_results": 5,
  "company_id": "benova"
}
```

```http
GET /api/documents/{doc_id}?company_id=benova
# Obtener información de un documento específico

Response 200:
{
  "id": "doc_12345",
  "filename": "botox_info.pdf",
  "company_id": "benova",
  "metadata": {...},
  "chunks": 15,
  "created_at": "2024-01-15T10:30:00Z"
}
```

```http
GET /api/documents/{doc_id}/debug?company_id=benova
# Información de debug del documento

Response 200:
{
  "document_id": "doc_12345",
  "chunks_detail": [...],
  "vectorstore_status": "indexed",
  "embeddings_count": 15
}
```

```http
POST /api/documents/bulk
Headers: X-Company-ID: benova
Content-Type: application/json

{
  "documents": [
    {"content": "...", "metadata": {...}},
    {"content": "...", "metadata": {...}}
  ]
}

Response 201:
{
  "status": "success",
  "documents_created": 10,
  "total_chunks": 150
}
```

```http
DELETE /api/documents/{doc_id}?company_id=benova
# Eliminar documento y sus vectores

Response 200:
{
  "status": "success",
  "document_id": "doc_12345",
  "chunks_deleted": 15,
  "vectorstore_cleaned": true
}
```

```http
POST /api/documents/cleanup?company_id=benova
# Limpiar vectores huérfanos

Response 200:
{
  "status": "success",
  "orphaned_vectors_deleted": 5
}
```

```http
GET /api/documents/diagnostics?company_id=benova
# Diagnóstico del sistema de documentos

Response 200:
{
  "company_id": "benova",
  "total_documents": 123,
  "total_chunks": 1845,
  "vectorstore_healthy": true,
  "orphaned_vectors": 0
}
```

```http
GET /api/documents/{doc_id}/vectors?company_id=benova
# Ver vectores de un documento específico

Response 200:
{
  "document_id": "doc_12345",
  "vectors": [
    {"id": "vec_123", "content": "...", "score": 0.95},
    ...
  ],
  "total": 15
}
```

```http
GET /api/documents/stats?company_id=benova
# Estadísticas de documentos

Response 200:
{
  "company_id": "benova",
  "total_documents": 123,
  "total_chunks": 1845,
  "categories": {
    "tratamientos": 45,
    "politicas": 30,
    "procedimientos": 48
  }
}
```

### 💬 **Conversations - Historial de Conversaciones**

```http
GET /api/conversations?company_id=benova
# Listar todas las conversaciones

Response 200:
{
  "total": 245,
  "conversations": [
    {
      "user_id": "user123",
      "last_message": "Gracias por la información",
      "last_updated": "2024-10-14T10:30:00Z",
      "message_count": 15
    },
    ...
  ]
}
```

```http
GET /api/conversations/{user_id}?company_id=benova
# Obtener historial de un usuario específico

Response 200:
{
  "user_id": "user123",
  "company_id": "benova",
  "messages": [
    {
      "role": "user",
      "content": "Hola",
      "timestamp": "2024-10-14T10:30:00Z"
    },
    {
      "role": "assistant",
      "content": "¡Hola! ¿En qué puedo ayudarte?",
      "timestamp": "2024-10-14T10:30:01Z",
      "agent": "support"
    },
    ...
  ],
  "total_messages": 15
}
```

```http
DELETE /api/conversations/{user_id}?company_id=benova
# Eliminar historial de un usuario

Response 200:
{
  "status": "success",
  "user_id": "user123",
  "messages_deleted": 15
}
```

```http
POST /api/conversations/{user_id}/test?company_id=benova
Content-Type: application/json

{
  "message": "Hola, ¿qué servicios ofrecen?"
}

Response 200:
{
  "user_id": "user123",
  "company_id": "benova",
  "agent_used": "sales",
  "bot_response": "¡Hola! Soy María, asesora de Benova...",
  "rag_context_used": true
}
```

### 🎙️ **Multimedia - Procesamiento de Voz e Imágenes**

```http
POST /api/multimedia/process-voice
Content-Type: multipart/form-data

audio: grabacion.wav
company_id: benova
user_id: user456

Response 200:
{
  "status": "success",
  "transcription": "Hola, quiero agendar una cita para botox",
  "language": "es",
  "confidence": 0.95,
  "bot_response": "¡Claro! Para agendar tu cita...",
  "agent_used": "schedule"
}
```

```http
POST /api/multimedia/process-image
Content-Type: application/json

{
  "company_id": "benova",
  "user_id": "user789",
  "image_base64": "data:image/jpeg;base64,...",
  "action": "analyze"
}

Response 200:
{
  "status": "success",
  "analysis": "La imagen muestra arrugas de expresión...",
  "recommendation": "Para este caso recomendamos botox...",
  "agent_used": "sales",
  "vision_model": "gpt-4o-mini"
}
```

```http
POST /api/multimedia/test-multimedia
Content-Type: application/json

{
  "company_id": "benova",
  "media_type": "voice",
  "test_data": {...}
}

Response 200:
{
  "status": "success",
  "capabilities": {
    "voice_enabled": true,
    "image_enabled": true,
    "whisper_available": true,
    "vision_available": true
  }
}
```

```http
GET /api/multimedia/capabilities/{company_id}
# Capacidades multimedia de la empresa

Response 200:
{
  "company_id": "benova",
  "voice_enabled": true,
  "image_enabled": true,
  "whisper_model": "whisper-1",
  "vision_model": "gpt-4o-mini",
  "tts_enabled": true,
  "tts_model": "tts-1"
}
```

```http
GET /api/multimedia/stats?company_id=benova
# Estadísticas de uso multimedia

Response 200:
{
  "company_id": "benova",
  "voice_messages_processed": 145,
  "images_analyzed": 67,
  "total_transcriptions": 145,
  "avg_transcription_time": "2.3s"
}
```

### 🏥 **Health - Monitoreo del Sistema**

```http
GET /api/health
# Health check general

Response 200:
{
  "status": "healthy",
  "version": "1.0.0",
  "system_type": "multi-tenant-multi-agent",
  "timestamp": "2024-10-14T10:30:00Z",
  "companies_configured": 4,
  "redis_healthy": true,
  "postgresql_healthy": true,
  "openai_healthy": true
}
```

```http
GET /api/health/company/{company_id}
# Health check específico de empresa

Response 200:
{
  "company_id": "benova",
  "status": "healthy",
  "redis_healthy": true,
  "vectorstore_healthy": true,
  "vectorstore_index": "benova_documents",
  "agents_available": 6,
  "agents_status": {
    "router": "active",
    "sales": "active",
    "support": "active",
    "emergency": "active",
    "schedule": "active",
    "availability": "active"
  },
  "rag_enabled": true,
  "documents_indexed": 123
}
```

```http
GET /api/health/companies
# Overview de salud de todas las empresas

Response 200:
{
  "total_companies": 4,
  "healthy_companies": 4,
  "companies": {
    "benova": {
      "status": "healthy",
      "agents_available": 6,
      "documents": 123,
      "vectorstore": "healthy"
    },
    "medispa": {
      "status": "healthy",
      "agents_available": 6,
      "documents": 87,
      "vectorstore": "healthy"
    }
  }
}
```

---

## 💾 Aislamiento de Datos Multi-Tenant

### Redis Keys por Empresa

```python
# Estructura de keys por empresa:

# BENOVA:
benova:conversation:user123               # Historial conversación
benova:document:doc456                    # Metadata documento
benova:bot_status:conv789                 # Estado bot activo
benova:vectorstore_health:status          # Health vectorstore

# MEDISPA (completamente aislado):
medispa:conversation:user123              # No contamina con Benova
medispa:document:doc456
medispa:bot_status:conv789
medispa:vectorstore_health:status

# VERIFICACIÓN DE AISLAMIENTO:
# ✅ Benova nunca puede acceder a keys de MediSpa
# ✅ Cada empresa tiene su propio "namespace" en Redis
```

### Vector Stores Independientes

```python
# Cada empresa tiene su propio índice Redis:
VECTORSTORE_INDICES = {
    "benova": "benova_documents",        # 123 documentos
    "medispa": "medispa_documents",      # 87 documentos
    "dental": "dental_documents",        # 56 documentos
    "wellness": "wellness_documents"     # 92 documentos
}

# GARANTÍA DE AISLAMIENTO:
# ✅ Búsqueda en benova_documents NUNCA devuelve docs de medispa
# ✅ Embeddings completamente separados
# ✅ Imposible contaminación cruzada de datos

# Código de verificación:
vectorstore_benova = VectorstoreService("benova")
results = vectorstore_benova.search_by_company("query")
# → Solo busca en "benova_documents"
```

### PostgreSQL Enterprise (Opcional)

```sql
-- Todas las tablas tienen company_id como columna
-- Aislamiento garantizado por WHERE company_id = 'benova'

-- Configuración de empresas:
SELECT * FROM companies WHERE company_id = 'benova';

-- Configuración de agentes:
SELECT * FROM agent_configs 
WHERE company_id = 'benova' AND agent_type = 'sales';

-- Prompts personalizados:
SELECT * FROM prompts 
WHERE company_id = 'benova' AND prompt_type = 'sales';

-- Documentos metadata (si se usa PostgreSQL):
SELECT * FROM documents 
WHERE company_id = 'benova' 
ORDER BY created_at DESC;

-- Conversaciones analytics:
SELECT * FROM conversations 
WHERE company_id = 'benova' 
AND created_at >= NOW() - INTERVAL '7 days';
```

---

## 🛠️ Variables de Entorno (COMPLETO - Verificado desde Railway)

```bash
# ============================================
# OPENAI CONFIGURATION
# ============================================
OPENAI_API_KEY=sk-your-openai-api-key-here
MODEL_NAME=gpt-4.1-mini-2025-04-14        # Modelo principal
# Alternativo: gpt-4o-mini

EMBEDDING_MODEL=text-embedding-3-small    # Para RAG
MAX_TOKENS=1500                           # Límite de tokens por respuesta
TEMPERATURE=0.7                           # Creatividad del modelo

# Multimedia Models
WHISPER_MODEL=whisper-1                   # Transcripción de voz
VISION_MODEL=gpt-4o-mini                  # Análisis de imágenes
TTS_MODEL=tts-1                           # Texto a voz
TTS_VOICE=alloy                           # Voz por defecto (alloy/echo/fable/onyx/nova/shimmer)

# ============================================
# REDIS CONFIGURATION
# ============================================
REDIS_URL=redis://default:password@host:port
# Ejemplo Railway: redis://default:xxxxx@redis.railway.internal:6379

# ============================================
# POSTGRESQL (OPCIONAL - Enterprise)
# ============================================
DATABASE_URL=postgresql://user:pass@host:port/dbname
# Ejemplo Railway: postgresql://postgres:xxxxx@postgres.railway.internal:5432/railway

PGHOST=postgres.railway.internal
PGPASSWORD=your-pg-password
PGPORT=5432
PGHOST=railway

# ============================================
# CHATWOOT INTEGRATION
# ============================================
CHATWOOT_API_KEY=your-chatwoot-api-key
CHATWOOT_BASE_URL=https://app.chatwoot.com
# URL base sin trailing slash

ACCOUNT_ID=7                              # Account ID por defecto (si no hay mapeo)

# ============================================
# MULTI-TENANT CONFIGURATION
# ============================================
# Si no usas PostgreSQL, especifica el archivo JSON:
# COMPANIES_CONFIG_FILE=companies_config.json

EXTENDED_CONFIG_ENABLED=true              # Habilitar config extendida
EXTENDED_CONFIG_FILE=extended_companies_config.json

# ============================================
# FLASK APPLICATION
# ============================================
SECRET_KEY=your-secret-key-change-in-production
FLASK_ENV=production
# Opciones: development, production, testing

ENVIRONMENT=production
RAILWAY_ENVIRONMENT=production

# ============================================
# SYSTEM SETTINGS
# ============================================
LOG_LEVEL=INFO
# Opciones: DEBUG, INFO, WARNING, ERROR, CRITICAL

MAX_CONTEXT_MESSAGES=10                   # Mensajes de contexto por conversación
SIMILARITY_THRESHOLD=0.7                  # Umbral de similitud para RAG
MAX_RETRIEVED_DOCS=3                      # Documentos a recuperar en RAG

# ============================================
# FEATURE FLAGS
# ============================================
VOICE_ENABLED=true                        # Habilitar procesamiento de voz
IMAGE_ENABLED=true                        # Habilitar análisis de imágenes
WEBHOOK_DEBUG=false                       # Debug de webhooks (logs verbosos)

VECTORSTORE_AUTO_RECOVERY=true            # Auto-recuperación de vectorstore

# ============================================
# EXTERNAL INTEGRATIONS
# ============================================
SCHEDULE_SERVICE_URL=http://127.0.0.1:4040
# URL del servicio de agendamiento (si aplica)

# Google Calendar (si usas OAuth2):
# GOOGLE_CALENDAR_CREDENTIALS={"type": "service_account", ...}
# O especificar archivo:
# GOOGLE_CALENDAR_CREDENTIALS_FILE=credentials.json

# ============================================
# SECURITY
# ============================================
API_KEY=your-internal-api-key
# Para endpoints que requieren autenticación adicional
```

---

## 🚀 Deployment en Railway

### Setup Rápido

```bash
# 1. Conectar repositorio GitHub
railway link

# 2. Configurar variables de entorno
railway variables set OPENAI_API_KEY=sk-...
railway variables set REDIS_URL=redis://...
railway variables set DATABASE_URL=postgresql://...

# 3. Desplegar
railway up

# 4. Ver logs
railway logs --tail
```

### Dockerfile Multi-Stage (Vue.js + Flask)

```dockerfile
# Stage 1: Build Frontend (Vue.js)
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY src/package*.json ./
RUN npm ci
COPY src/ .
RUN npm run build

# Stage 2: Backend (Flask)
FROM python:3.11-slim
WORKDIR /app

# Copiar frontend build
COPY --from=frontend-builder /app/frontend/dist /app/static

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código backend
COPY app/ app/
COPY wsgi.py .

# Puerto
EXPOSE 8080

# Comando
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", "wsgi:app"]
```

---

## 🔧 Puntos de Mejora para Ser Competitivo

### 🔴 CRÍTICO (Hacer AHORA)

#### 1. **Refactorizar archivos grandes**
```python
# admin.py (1585 líneas) →
app/routes/admin/
  ├── __init__.py
  ├── companies.py      # CRUD empresas
  ├── diagnostics.py    # Diagnósticos
  ├── configuration.py  # Gestión config
  └── monitoring.py     # Monitoreo

# schedule_agent.py (1241 líneas) →
app/agents/schedule/
  ├── __init__.py
  ├── schedule_agent.py    # Lógica principal
  ├── google_calendar.py   # Integración Calendar API
  └── validators.py        # Validación de datos

# prompt_service.py (898 líneas) →
app/services/prompts/
  ├── __init__.py
  ├── prompt_service.py    # Servicio principal
  ├── cache.py             # Cache Redis de prompts
  └── loaders.py           # Carga desde JSON/PostgreSQL
```

#### 2. **Testing (0% coverage actual)**
```bash
# Instalar pytest
pip install pytest pytest-cov pytest-mock

# Estructura de tests:
tests/
├── conftest.py                # Fixtures compartidos
├── test_agents/
│   ├── test_sales_agent.py
│   ├── test_support_agent.py
│   └── test_router_agent.py
├── test_services/
│   ├── test_vectorstore.py
│   └── test_orchestrator.py
└── test_routes/
    ├── test_webhook.py
    └── test_documents.py

# Objetivo: 80% coverage
pytest --cov=app --cov-report=html
```

#### 3. **Documentación de API (Swagger/OpenAPI)**
```python
# Instalar flasgger
pip install flasgger

# En app/__init__.py:
from flasgger import Swagger

app = Flask(__name__)
swagger = Swagger(app, template={
    "info": {
        "title": "multibackendopenIA API",
        "version": "1.0.0",
        "description": "Sistema Multi-Tenant Multi-Agente"
    }
})

# En cada endpoint:
@bp.route('/documents', methods=['POST'])
def add_document():
    """
    Subir un documento para RAG
    ---
    tags:
      - Documents
    parameters:
      - name: X-Company-ID
        in: header
        required: true
        type: string
      - name: file
        in: formData
        required: true
        type: file
    responses:
      201:
        description: Documento creado exitosamente
    """
    pass
```

#### 4. **Monitoreo y Observabilidad**
```bash
# Instalar prometheus_flask_exporter
pip install prometheus-flask-exporter

# app/__init__.py:
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
metrics = PrometheusMetrics(app)

# Expone métricas en /metrics:
# - http_request_duration_seconds
# - http_request_total
# - http_request_exceptions_total

# Dashboard Grafana para visualizar
```

### 🟡 IMPORTANTE (Próximas 2-4 semanas)

#### 5. **Rate Limiting por Empresa**
```python
# Instalar flask-limiter
pip install Flask-Limiter

# app/__init__.py:
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=lambda: request.headers.get('X-Company-ID', get_remote_address()),
    default_limits=["200 per day", "50 per hour"]
)

# Por empresa:
RATE_LIMITS = {
    "benova": "1000 per day",    # Premium
    "medispa": "500 per day"     # Basic
}
```

#### 6. **Cache de Prompts en Redis**
```python
# services/prompts/cache.py

class PromptCache:
    def __init__(self, redis_client, ttl=3600):
        self.redis = redis_client
        self.ttl = ttl
    
    def get(self, company_id: str, prompt_type: str) -> Optional[str]:
        key = f"{company_id}:prompt:{prompt_type}"
        return self.redis.get(key)
    
    def set(self, company_id: str, prompt_type: str, prompt: str):
        key = f"{company_id}:prompt:{prompt_type}"
        self.redis.setex(key, self.ttl, prompt)

# Reducir carga en PostgreSQL/JSON
```

#### 7. **Async Processing con Celery**
```python
# Instalar Celery + Redis
pip install celery redis

# celery_app.py:
from celery import Celery

celery = Celery('multibackendopenIA', broker='redis://localhost:6379/0')

@celery.task
def process_document_embeddings(company_id: str, doc_id: str):
    """Procesar embeddings en background"""
    vectorstore = VectorstoreService(company_id)
    # Procesar...
    return {"status": "completed"}

# Webhook responde instantáneamente
# Procesamiento pesado en background
```

#### 8. **Versionado de API**
```python
# app/routes/v1/documents.py
from flask import Blueprint

bp_v1 = Blueprint('documents_v1', __name__, url_prefix='/api/v1/documents')

# app/routes/v2/documents.py
bp_v2 = Blueprint('documents_v2', __name__, url_prefix='/api/v2/documents')

# Permite evolucionar API sin romper clientes existentes
```

### 🟢 Nice to Have (Futuro)

#### 9. **GraphQL API**
```python
# Instalar graphene-flask
pip install graphene-flask

# Para queries complejas:
query {
  company(id: "benova") {
    documents {
      id
      filename
      chunks {
        content
        score
      }
    }
    agents {
      name
      status
    }
  }
}
```

#### 10. **Streaming de Respuestas (SSE)**
```python
@app.route('/stream')
def stream_response():
    """Server-Sent Events para respuestas en tiempo real"""
    def generate():
        for chunk in agent.stream_response():
            yield f"data: {chunk}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')
```

#### 11. **CI/CD Pipeline**
```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: |
          pip install -r requirements.txt
          pytest --cov=app
      
      - name: Deploy to Railway
        if: github.ref == 'refs/heads/main'
        run: railway up
```

#### 12. **Internacionalización (i18n)**
```python
# Respuestas multi-idioma según empresa
LANGUAGES = {
    "benova": "es",      # Español
    "medispa": "es",     # Español
    "wellness": "en"     # Inglés
}

# Prompts y respuestas en idioma configurado
```

---

## 🐛 Troubleshooting Común

### Redis Connection Failed
```bash
# Verificar
curl http://localhost:8080/health/company/benova

# Si redis_healthy: false
# 1. Verificar REDIS_URL en .env
# 2. Verificar que Redis esté corriendo
docker ps | grep redis

# 3. Test manual de conexión
redis-cli -u $REDIS_URL ping
# Debe responder: PONG
```

### OpenAI Rate Limit
```bash
# Verificar en logs:
grep "rate limit" logs/app.log

# Solución temporal: Cambiar a modelo más económico
MODEL_NAME=gpt-4o-mini  # Más económico que gpt-4.1-mini
```

### Webhook no responde
```bash
# 1. Verificar logs Railway
railway logs --tail

# 2. Verificar health
curl https://tu-app.railway.app/health

# 3. Verificar configuración Chatwoot
# Account ID correcto en webhook settings
```

### RAG no encuentra documentos
```python
# Verificar índice Redis
from app.services.vectorstore_service import VectorstoreService
vs = VectorstoreService("benova")
vs.check_health()

# Debe mostrar:
# {
#   "status": "healthy",
#   "index": "benova_documents",
#   "document_count": 123
# }

# Si no hay documentos: Re-indexar
python scripts/reindex_documents.py --company-id benova
```

### Agente no responde correctamente
```bash
# Test específico de agente
curl -X POST http://localhost:8080/conversations/test_user/test?company_id=benova \
  -H "Content-Type: application/json" \
  -d '{"message": "Hola"}'

# Verificar en logs qué agente se usó y por qué
grep "agent_used" logs/app.log | tail -20
```

---

## 📚 Recursos Adicionales

- **LangChain Docs**: https://python.langchain.com/
- **OpenAI API**: https://platform.openai.com/docs
- **Redis Vector Store**: https://redis.io/docs/stack/search/
- **Flask Best Practices**: https://flask.palletsprojects.com/
- **Google Calendar API**: https://developers.google.com/calendar

---

## 🤝 Contribución

Este proyecto sigue arquitectura modular. Al agregar features:

1. ✅ Respeta el patrón de dependencias (ver mapa)
2. ✅ Agrega tests unitarios (pytest)
3. ✅ Actualiza este README con cambios
4. ✅ Usa logging consistente por empresa
5. ✅ Documenta cambios en CHANGELOG.md
6. ✅ Verifica aislamiento multi-tenant

---

## 📄 Licencia

MIT License - Ver [LICENSE](LICENSE) para más detalles

---

## 👨‍💻 Autor

**Juan Felipe Rúa Cadavid**  
Senior Backend Engineer - AI & Automation  
📧 Email: [tu-email]  
🔗 LinkedIn: [linkedin.com/in/juan-felipe-rúa-cadavid-3a3a3b143](https://www.linkedin.com/in/juan-felipe-rúa-cadavid-3a3a3b143)

---

**Version:** 1.0.0  
**Last Updated:** Octubre 2025  
**Status:** 🟢 Producción (Railway)  
**Modelo IA:** GPT-4.1-mini-2025-04-14 / GPT-4o-mini
