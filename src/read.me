# 🔄 Análisis Completo para Migración Vue.js 3 
## Multibackend OpenIA - De Vanilla JS a Vue.js 3

---

## 📊 **PASO 1: ANÁLISIS DEL SCRIPT.JS ACTUAL**

### **🔧 Variables Globales del Estado Actual**
```javascript
// Configuración API
const API_BASE_URL = window.location.origin;
const DEFAULT_COMPANY_ID = 'benova';

// Estado Global - MIGRAR A PINIA STORE
let currentCompanyId = DEFAULT_COMPANY_ID;
let monitoringInterval = null;
let systemLog = [];
let ADMIN_API_KEY = null;

// Cache - MIGRAR A PINIA STORE
const cache = {
    companies: null,
    systemInfo: null,
    lastUpdate: {}
};
```

### **⚡ Funciones Globales Identificadas (50+ funciones)**

#### **🔋 Core Functions (CRÍTICAS para mantener)**
- `apiRequest(endpoint, options)` - **FUNCIÓN BASE PARA TODAS LAS APIS**
- `showNotification(message, type, duration)` 
- `addToLog(message, level)`
- `updateLogDisplay()`
- `toggleLoadingOverlay(show)`
- `escapeHTML(text)`
- `formatJSON(obj)`
- `validateCompanySelection()`

#### **🎯 Tab Management (SISTEMA PRINCIPAL)**
- `switchTab(tabName)`
- `loadTabContent(tabName)` 
- `initializeTabs()`
- `updateTabNotificationCount(tabName, count)`
- `refreshActiveTab()`
- `getActiveTab()`

#### **📊 Dashboard Functions**
- `loadDashboardData()`
- `loadSystemInfo()`
- `loadCompaniesStatus()`
- `updateStats()`

#### **🏢 Company Management**
- `loadCompanies()`
- `handleCompanyChange(companyId)`
- `reloadCompaniesConfig()`

#### **📄 Document Management**
- `uploadDocument()`
- `loadDocuments()`
- `searchDocuments()`
- `viewDocument(docId)`
- `deleteDocument(docId)`
- `loadDocumentsTab()`

#### **💬 Conversation Management**
- `testConversation()`
- `getConversation()`
- `deleteConversation()`
- `loadConversations()`
- `viewConversationDetail(convId)`
- `deleteConversationFromList(convId)`
- `loadConversationsTab()`

#### **🎤 Multimedia Functions**
- `processAudio()`
- `processImage()`
- `testMultimediaIntegration()`
- `captureScreen()`
- `toggleVoiceRecording()`
- `loadMultimediaTab()`

#### **🤖 Prompt Management**
- `loadPromptsTab()`
- `loadCurrentPrompts()`
- `updatePrompt(promptId, content)`
- `resetPrompt(promptId)`
- `previewPrompt(promptId)`
- `showPreviewModal(data)`
- `repairPrompts()`
- `migratePromptsToPostgreSQL()`
- `loadPromptsSystemStatus()`

#### **🏢 Enterprise Functions**
- `loadEnterpriseTab()`
- `loadEnterpriseCompanies()`
- `createEnterpriseCompany()`
- `viewEnterpriseCompany(companyId)`
- `editEnterpriseCompany(companyId)`
- `saveEnterpriseCompany()`
- `testEnterpriseCompany(companyId)`
- `migrateCompaniesToPostgreSQL()`

#### **🏥 Health Check Functions**
- `performHealthCheck()`
- `performCompanyHealthCheck()`
- `checkServicesStatus()`
- `runAutoDiagnostics()`
- `startRealTimeMonitoring()`
- `stopRealTimeMonitoring()`
- `loadHealthCheckTab()`

#### **🔧 Admin Functions**
- `runSystemDiagnostics()`
- `clearSystemLog()`
- `loadAdminTab()`

#### **🔑 API Key Management**
- `showApiKeyModal()`
- `saveApiKey()`
- `closeApiKeyModal()`
- `testApiKey()`
- `updateApiKeyStatus()`

#### **🎛️ Modal & UI Functions**
- `closeModal()`
- `setupFileUploadHandlers()`

### **🌐 APIs Catalogadas (PRESERVAR EXACTAS)**

#### **Core APIs**
```javascript
GET /api/companies
GET /api/system/info
GET /api/health
GET /api/health/company/:id
```

#### **Document APIs**
```javascript
GET /api/documents
POST /api/documents
DELETE /api/documents/:id
POST /api/documents/search
```

#### **Conversation APIs**
```javascript
GET /api/conversations
POST /api/conversations/test
GET /api/conversations/:userId
DELETE /api/conversations/:userId
```

#### **Multimedia APIs**
```javascript
POST /api/multimedia/audio
POST /api/multimedia/image
GET /api/multimedia/test
```

#### **Prompt APIs**
```javascript
GET /api/prompts
PUT /api/prompts/:id
POST /api/prompts/:id/reset
POST /api/prompts/:id/preview
```

#### **Enterprise APIs (con API Key)**
```javascript
GET /api/enterprise/companies
POST /api/enterprise/companies
GET /api/enterprise/companies/:id
PUT /api/enterprise/companies/:id
POST /api/enterprise/companies/:id/test
```

#### **Admin APIs (con API Key)**
```javascript
GET /api/admin/config
POST /api/admin/diagnostics
GET /api/admin/status
```

### **🏗️ Estructura HTML Identificada**

#### **Tabs Principales**
- `dashboard` - Dashboard principal
- `documents` - Gestión de documentos
- `conversations` - Gestión de conversaciones  
- `multimedia` - Procesamiento multimedia
- `prompts` - Gestión de prompts
- `admin` - Panel de administración
- `enterprise` - Funciones enterprise
- `health` - Health checks

#### **Elementos DOM Críticos**
- `#companySelect` - Selector de empresas
- `#notificationContainer` - Contenedor de notificaciones
- `#systemLog` - Log del sistema
- `#loadingOverlay` - Overlay de carga
- `#apiKeyStatus` - Estado del API key
- Cada tab tiene su propio contenedor: `#{tabName}TabContent`

---

## 🏗️ **PASO 2: ESTRUCTURA DE COMPONENTES VUE.JS 3**

### **📁 Estructura de Directorios Propuesta**
```
src/
├── components/
│   ├── shared/
│   │   ├── AppNotifications.vue
│   │   ├── LoadingOverlay.vue
│   │   ├── SystemLog.vue
│   │   ├── CompanySelector.vue
│   │   ├── ApiKeyModal.vue
│   │   └── TabNavigation.vue
│   ├── dashboard/
│   │   ├── DashboardMain.vue
│   │   ├── SystemInfo.vue
│   │   ├── CompaniesStatus.vue
│   │   └── StatsGrid.vue
│   ├── companies/
│   │   ├── CompanyManager.vue
│   │   └── CompanyList.vue
│   ├── documents/
│   │   ├── DocumentsTab.vue
│   │   ├── DocumentUpload.vue
│   │   ├── DocumentSearch.vue
│   │   ├── DocumentList.vue
│   │   └── DocumentModal.vue
│   ├── conversations/
│   │   ├── ConversationsTab.vue
│   │   ├── ConversationTester.vue
│   │   ├── ConversationManager.vue
│   │   ├── ConversationList.vue
│   │   └── ConversationDetail.vue
│   ├── multimedia/
│   │   ├── MultimediaTab.vue
│   │   ├── AudioProcessor.vue
│   │   ├── ImageProcessor.vue
│   │   ├── ScreenCapture.vue
│   │   └── VoiceRecorder.vue
│   ├── prompts/
│   │   ├── PromptsTab.vue
│   │   ├── PromptEditor.vue
│   │   ├── PromptPreview.vue
│   │   └── PromptsStatus.vue
│   ├── enterprise/
│   │   ├── EnterpriseTab.vue
│   │   ├── EnterpriseCompanyList.vue
│   │   ├── EnterpriseCompanyForm.vue
│   │   └── EnterpriseCompanyDetail.vue
│   ├── admin/
│   │   ├── AdminTab.vue
│   │   ├── SystemDiagnostics.vue
│   │   ├── RealTimeMonitoring.vue
│   │   └── AdminTools.vue
│   └── health/
│       ├── HealthTab.vue
│       ├── HealthChecker.vue
│       ├── CompanyHealthChecker.vue
│       └── ServicesStatus.vue
├── composables/
│   ├── useApiRequest.js
│   ├── useNotifications.js
│   ├── useSystemLog.js
│   ├── useCompanies.js
│   ├── useDocuments.js
│   ├── useConversations.js
│   ├── useMultimedia.js
│   ├── usePrompts.js
│   ├── useEnterprise.js
│   ├── useAdmin.js
│   ├── useHealthCheck.js
│   └── useFileUpload.js
├── stores/
│   ├── app.js          # Estado global principal
│   ├── companies.js    # Estado de empresas
│   ├── cache.js        # Sistema de cache
│   └── auth.js         # API Key management
├── services/
│   └── api.js          # Wrapper para preservar apiRequest exacto
├── utils/
│   ├── helpers.js      # Utilidades (escapeHTML, formatJSON, etc.)
│   └── constants.js    # Constantes (API_BASE_URL, etc.)
└── styles/
    ├── main.css
    ├── components.css
    └── tabs.css
```

### **🔄 Composables Principales**

#### **useApiRequest (CRÍTICO)**
```javascript
// composables/useApiRequest.js
import { ref } from 'vue';
import { useAppStore } from '@/stores/app';

export const useApiRequest = () => {
  const appStore = useAppStore();

  const apiRequest = async (endpoint, options = {}) => {
    const url = `${API_BASE_URL}${endpoint}`;
    
    const defaultHeaders = {
      'Content-Type': 'application/json'
    };
    
    // PRESERVAR EXACTO: Header de company
    if (appStore.currentCompanyId) {
      defaultHeaders['X-Company-ID'] = appStore.currentCompanyId;
    }
    
    // PRESERVAR EXACTO: Lógica de headers y body
    const headers = { ...defaultHeaders, ...(options.headers || {}) };
    
    const config = {
      method: options.method || 'GET',
      headers,
      ...options
    };
    
    if (options.body) {
      if (options.body instanceof FormData) {
        delete config.headers['Content-Type'];
        config.body = options.body;
      } else {
        config.body = typeof options.body === 'string' 
          ? options.body 
          : JSON.stringify(options.body);
      }
    }
    
    try {
      appStore.addToLog(`API Request: ${config.method} ${endpoint}`, 'info');
      
      const response = await fetch(url, config);
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.message || `HTTP ${response.status}: ${response.statusText}`);
      }
      
      appStore.addToLog(`API Response: ${endpoint} - Success`, 'info');
      return data;
      
    } catch (error) {
      appStore.addToLog(`API Error: ${endpoint} - ${error.message}`, 'error');
      throw error;
    }
  };

  return { apiRequest };
};
```

### **🗄️ Stores Pinia Principales**

#### **stores/app.js (ESTADO PRINCIPAL)**
```javascript
import { defineStore } from 'pinia';
import { ref, computed, watchEffect } from 'vue';

export const useAppStore = defineStore('app', () => {
  // Variables globales migradas
  const currentCompanyId = ref('benova');
  const monitoringInterval = ref(null);
  const systemLog = ref([]);
  const adminApiKey = ref(null);
  
  // Cache migrado
  const cache = ref({
    companies: null,
    systemInfo: null,
    lastUpdate: {}
  });

  // Funciones de log
  const addToLog = (message, level = 'info') => {
    const timestamp = new Date().toISOString().substring(0, 19).replace('T', ' ');
    const logEntry = { timestamp, level, message };
    
    systemLog.value.push(logEntry);
    
    if (systemLog.value.length > 100) {
      systemLog.value.shift();
    }
  };

  const clearSystemLog = () => {
    systemLog.value = [];
    addToLog('System log cleared', 'info');
  };

  // MANTENER COMPATIBILIDAD GLOBAL
  watchEffect(() => {
    window.currentCompanyId = currentCompanyId.value;
    window.systemLog = systemLog.value;
    window.cache = cache.value;
    window.ADMIN_API_KEY = adminApiKey.value;
  });

  return {
    currentCompanyId,
    monitoringInterval,
    systemLog,
    adminApiKey,
    cache,
    addToLog,
    clearSystemLog
  };
});
```

---

## 🔄 **PASO 3: PLAN DE MIGRACIÓN FUNCIÓN POR FUNCIÓN**

### **📋 Orden de Migración (Por Prioridad)**

#### **FASE 1: CORE SYSTEM (Crítico)**
1. ✅ `apiRequest` → `useApiRequest` composable
2. ✅ Variables globales → Pinia stores
3. ✅ `showNotification` → `useNotifications`
4. ✅ `addToLog` / `systemLog` → Store integrado
5. ✅ `switchTab` → Vue router o state management

#### **FASE 2: COMPANY MANAGEMENT**
6. ✅ `loadCompanies` → `useCompanies` composable
7. ✅ `handleCompanyChange` → Reactive store management
8. ✅ Company selector → `CompanySelector.vue` componente

#### **FASE 3: TAB CONTENT LOADERS**
9. ✅ `loadTabContent` → Vue router navigation guards
10. ✅ `loadDashboardData` → `DashboardMain.vue`
11. ✅ `loadSystemInfo` → `SystemInfo.vue` componente
12. ✅ `loadCompaniesStatus` → `CompaniesStatus.vue`

#### **FASE 4: DOCUMENT SYSTEM**
13. ✅ `uploadDocument` → `useDocuments` composable
14. ✅ `loadDocuments` → `DocumentList.vue` componente
15. ✅ `searchDocuments` → `DocumentSearch.vue`
16. ✅ `viewDocument` / `deleteDocument` → Modal components

#### **FASE 5: CONVERSATION SYSTEM**
17. ✅ `testConversation` → `ConversationTester.vue`
18. ✅ `loadConversations` → `ConversationList.vue`
19. ✅ `viewConversationDetail` → `ConversationDetail.vue`

#### **FASE 6: MULTIMEDIA & PROMPTS**
20. ✅ Multimedia functions → `MultimediaTab.vue`
21. ✅ Prompt management → `PromptsTab.vue`

#### **FASE 7: ENTERPRISE & ADMIN**
22. ✅ Enterprise functions → `EnterpriseTab.vue`
23. ✅ Admin functions → `AdminTab.vue`
24. ✅ Health check → `HealthTab.vue`

### **🛡️ Wrapper Functions (PRESERVAR COMPATIBILIDAD)**

Para cada función migrada, crear wrapper global:

```vue
<!-- Ejemplo: DocumentsTab.vue -->
<script setup>
import { onMounted, onUnmounted } from 'vue';
import { useDocuments } from '@/composables/useDocuments';

const { uploadDocument, loadDocuments, searchDocuments, viewDocument, deleteDocument } = useDocuments();

// WRAPPERS PARA MANTENER COMPATIBILIDAD
onMounted(() => {
  window.uploadDocument = uploadDocument;
  window.loadDocuments = loadDocuments;
  window.searchDocuments = searchDocuments;
  window.viewDocument = viewDocument;
  window.deleteDocument = deleteDocument;
});

onUnmounted(() => {
  delete window.uploadDocument;
  delete window.loadDocuments;
  delete window.searchDocuments;
  delete window.viewDocument;
  delete window.deleteDocument;
});
</script>
```

---

## ⚡ **PASO 4: WRAPPERS DE COMPATIBILIDAD**

### **🎯 Funciones que REQUIEREN Wrappers Globales**

Todas las funciones que están en `window.*` deben mantenerse:

```javascript
// Lista completa de funciones a preservar en window
window.captureScreen = captureScreen;
window.toggleVoiceRecording = toggleVoiceRecording;
window.switchTab = switchTab;
window.loadTabContent = loadTabContent;
window.initializeTabs = initializeTabs;
// ... (todas las 50+ funciones)
```

### **🔄 Patrón de Wrapper Estándar**

```javascript
// En cada componente Vue
onMounted(() => {
  // Exponer funciones al ámbito global
  window.functionName = localVueFunction;
});

onUnmounted(() => {
  // Limpiar referencias globales
  delete window.functionName;
});
```

---

## ✅ **PASO 5: TESTING DE COMPATIBILIDAD**

### **🧪 Tests a Realizar**

#### **API Compatibility Tests**
```javascript
// Verificar que cada endpoint se llama exactamente igual
const testApiCompatibility = async () => {
  // Test original vs Vue implementation
  const originalResponse = await originalApiRequest('/api/companies');
  const vueResponse = await useApiRequest().apiRequest('/api/companies');
  
  console.assert(
    JSON.stringify(originalResponse) === JSON.stringify(vueResponse),
    'API responses must be identical'
  );
};
```

#### **Function Compatibility Tests**
```javascript
// Verificar que cada función global existe
const testGlobalFunctions = () => {
  const requiredFunctions = [
    'switchTab', 'loadTabContent', 'uploadDocument',
    'loadDocuments', 'testConversation', 'showNotification'
    // ... todas las funciones
  ];
  
  requiredFunctions.forEach(fnName => {
    console.assert(
      typeof window[fnName] === 'function',
      `Global function ${fnName} must exist`
    );
  });
};
```

#### **State Compatibility Tests**
```javascript
// Verificar que el estado global se mantiene
const testGlobalState = () => {
  console.assert(
    window.currentCompanyId !== undefined,
    'currentCompanyId must be globally accessible'
  );
  
  console.assert(
    Array.isArray(window.systemLog),
    'systemLog must be globally accessible array'
  );
};
```

---

## 📊 **RESUMEN DE LA MIGRACIÓN**

### **✅ Funcionalidad Preservada al 100%**
- ✅ Todas las APIs mantienen formato exacto
- ✅ Todas las funciones globales disponibles
- ✅ Comportamiento idéntico del usuario
- ✅ Backend sin modificaciones
- ✅ Estado global sincronizado

### **🚀 Beneficios de Vue.js 3**
- ✅ Código modular y mantenible
- ✅ Composition API como Chatwoot
- ✅ Gestión de estado reactivo con Pinia
- ✅ Componentes reutilizables
- ✅ Preparado para integración Chatwoot

### **⚠️ Puntos Críticos**
- ❗ Nunca modificar formato de APIs
- ❗ Preservar nombres exactos de funciones
- ❗ Mantener variables globales sincronizadas
- ❗ Testing exhaustivo antes de deploy

### **📈 Siguientes Pasos**
1. **Configurar proyecto Vue.js 3** con Vite + Pinia
2. **Migrar por fases** siguiendo el plan establecido
3. **Testing continuo** de compatibilidad
4. **Deploy gradual** tab por tab
5. **Preparación para Chatwoot** integration

---

**🎯 OBJETIVO CUMPLIDO: Plan completo de migración que preserva 100% de funcionalidad mientras moderniza la arquitectura a Vue.js 3 + Composition API.**
