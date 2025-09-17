<template>
  <div id="app" class="app">
    <!-- Loading Overlay Global -->
    <LoadingOverlay v-if="appStore.isLoadingOverlay" />
    
    <!-- Container Principal -->
    <div class="container">
      <!-- Header -->
      <div class="header">
        <h1>🏥 Benova Multi-Tenant Backend</h1>
        <p class="subtitle">Panel de Administración - Sistema Multi-Agente</p>
      </div>
      
      <!-- Company Selector y API Key Status -->
      <div class="company-selector">
        <CompanySelector />
        <ApiKeyStatus />
      </div>
      
      <!-- Tab Navigation -->
      <TabNavigation 
        :activeTab="appStore.activeTab"
        @tab-changed="handleTabChange"
      />
      
      <!-- Tab Content -->
      <div class="tab-contents">
        <!-- Dashboard Tab -->
        <DashboardTab 
          v-show="appStore.activeTab === 'dashboard'"
          :isActive="appStore.activeTab === 'dashboard'"
        />
        
        <!-- Documents Tab -->
        <DocumentsTab 
          v-show="appStore.activeTab === 'documents'"
          :isActive="appStore.activeTab === 'documents'"
        />
        
        <!-- Conversations Tab -->
        <ConversationsTab 
          v-show="appStore.activeTab === 'conversations'"
          :isActive="appStore.activeTab === 'conversations'"
        />
        
        <!-- Multimedia Tab -->
        <MultimediaTab 
          v-show="appStore.activeTab === 'multimedia'"
          :isActive="appStore.activeTab === 'multimedia'"
        />
        
        <!-- Prompts Tab -->
        <PromptsTab 
          v-show="appStore.activeTab === 'prompts'"
          :isActive="appStore.activeTab === 'prompts'"
        />
        
        <!-- Admin Tab -->
        <AdminTab 
          v-show="appStore.activeTab === 'admin'"
          :isActive="appStore.activeTab === 'admin'"
        />
        
        <!-- Enterprise Tab -->
        <EnterpriseTab 
          v-show="appStore.activeTab === 'enterprise'"
          :isActive="appStore.activeTab === 'enterprise'"
        />
        
        <!-- Health Tab -->
        <HealthTab 
          v-show="appStore.activeTab === 'health'"
          :isActive="appStore.activeTab === 'health'"
        />
      </div>
      
      <!-- System Log (Collapsible) -->
      <SystemLog v-if="showSystemLog" />
    </div>
    
    <!-- Notification Container -->
    <AppNotifications />
    
    <!-- Modals Container -->
    <div id="modals-container"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { useNotifications } from '@/composables/useNotifications'
import { useApiRequest } from '@/composables/useApiRequest'

// Components - Shared
import LoadingOverlay from '@/components/shared/LoadingOverlay.vue'
import CompanySelector from '@/components/shared/CompanySelector.vue'
import ApiKeyStatus from '@/components/shared/ApiKeyStatus.vue'
import TabNavigation from '@/components/shared/TabNavigation.vue'
import SystemLog from '@/components/shared/SystemLog.vue'
import AppNotifications from '@/components/shared/AppNotifications.vue'

// Components - Tab Content
import DashboardTab from '@/components/dashboard/DashboardTab.vue'
import DocumentsTab from '@/components/documents/DocumentsTab.vue'
import ConversationsTab from '@/components/conversations/ConversationsTab.vue'
import MultimediaTab from '@/components/multimedia/MultimediaTab.vue'
import PromptsTab from '@/components/prompts/PromptsTab.vue'
import AdminTab from '@/components/admin/AdminTab.vue'
import EnterpriseTab from '@/components/enterprise/EnterpriseTab.vue'
import HealthTab from '@/components/health/HealthTab.vue'

// Stores y Composables
const appStore = useAppStore()
const { showNotification } = useNotifications()
const { apiRequest } = useApiRequest()

// Estado local
const showSystemLog = ref(false)

// ============================================================================
// FUNCIONES PRINCIPALES - MIGRADAS DESDE SCRIPT.JS
// ============================================================================

/**
 * Maneja el cambio de tab
 * MIGRADO: switchTab() de script.js
 */
const handleTabChange = (tabName) => {
  const success = appStore.setActiveTab(tabName)
  
  if (success) {
    // Cargar contenido específico del tab según sea necesario
    loadTabContent(tabName)
  }
}

/**
 * Carga el contenido específico de cada tab
 * MIGRADO: loadTabContent() de script.js
 */
const loadTabContent = async (tabName) => {
  try {
    const shouldShowLoader = ['dashboard', 'prompts', 'documents', 'conversations', 'health'].includes(tabName)
    
    if (shouldShowLoader) {
      appStore.setLoadingOverlay(true)
    }
    
    // Emitir evento para que el componente del tab específico cargue sus datos
    window.dispatchEvent(new CustomEvent('loadTabContent', { 
      detail: { tabName }
    }))
    
  } catch (error) {
    console.error(`Error loading tab content for ${tabName}:`, error)
    showNotification(`Error al cargar ${tabName}: ${error.message}`, 'error')
    appStore.addToLog(`Error loading tab ${tabName}: ${error.message}`, 'error')
  } finally {
    appStore.setLoadingOverlay(false)
  }
}

/**
 * Inicializa los tabs - MIGRADO: initializeTabs() de script.js
 */
const initializeTabs = () => {
  // Verificar si hay un tab por defecto en la URL
  const urlParams = new URLSearchParams(window.location.search)
  const defaultTab = urlParams.get('tab')
  
  if (defaultTab && ['dashboard', 'documents', 'conversations', 'multimedia', 'prompts', 'admin', 'enterprise', 'health'].includes(defaultTab)) {
    appStore.setActiveTab(defaultTab)
  } else {
    // Cargar dashboard por defecto
    appStore.setActiveTab('dashboard')
  }
  
  appStore.addToLog('Tabs initialized', 'info')
}

/**
 * Actualiza el contador de notificaciones en un tab
 * MIGRADO: updateTabNotificationCount() de script.js
 */
const updateTabNotificationCount = (tabName, count) => {
  // Emitir evento para que TabNavigation maneje la actualización
  window.dispatchEvent(new CustomEvent('updateTabNotificationCount', { 
    detail: { tabName, count }
  }))
}

/**
 * Refresca el tab activo actual
 * MIGRADO: refreshActiveTab() de script.js
 */
const refreshActiveTab = async () => {
  const activeTab = appStore.activeTab
  if (activeTab) {
    appStore.addToLog(`Refreshing active tab: ${activeTab}`, 'info')
    await loadTabContent(activeTab)
  }
}

/**
 * Obtiene el tab activo actual
 * MIGRADO: getActiveTab() de script.js
 */
const getActiveTab = () => {
  return appStore.activeTab
}

// ============================================================================
// FUNCIONES DE UTILIDAD
// ============================================================================

/**
 * Toggle del system log
 */
const toggleSystemLog = () => {
  showSystemLog.value = !showSystemLog.value
}

/**
 * Configuración inicial de drag and drop para archivos
 * MIGRADO: setupFileUploadHandlers() de script.js
 */
const setupFileUploadHandlers = () => {
  // Prevenir comportamiento por defecto del drag and drop en toda la aplicación
  const preventDefaults = (e) => {
    e.preventDefault()
    e.stopPropagation()
  }
  
  // Eventos para toda la aplicación
  const events = ['dragenter', 'dragover', 'dragleave', 'drop']
  events.forEach(eventName => {
    document.addEventListener(eventName, preventDefaults, false)
  })
  
  // Highlight al arrastrar archivos
  const highlight = () => {
    document.body.classList.add('drag-highlight')
  }
  
  const unhighlight = () => {
    document.body.classList.remove('drag-highlight')
  }
  
  document.addEventListener('dragenter', highlight, false)
  document.addEventListener('dragover', highlight, false)
  document.addEventListener('dragleave', unhighlight, false)
  document.addEventListener('drop', unhighlight, false)
}

// ============================================================================
// LIFECYCLE Y WATCHERS
// ============================================================================

onMounted(async () => {
  appStore.addToLog('Application initializing...', 'info')
  
  try {
    // Configurar handlers de archivo
    setupFileUploadHandlers()
    
    // Inicializar tabs
    initializeTabs()
    
    // Cargar datos iniciales
    await loadTabContent(appStore.activeTab)
    
    appStore.addToLog('Application initialized successfully', 'info')
    
  } catch (error) {
    console.error('Error during app initialization:', error)
    showNotification(`Error al inicializar la aplicación: ${error.message}`, 'error')
    appStore.addToLog(`App initialization error: ${error.message}`, 'error')
  }
})

onUnmounted(() => {
  // Limpiar intervalos y recursos
  appStore.$dispose()
})

// Watcher para cambios de empresa
watch(() => appStore.currentCompanyId, (newCompanyId, oldCompanyId) => {
  if (newCompanyId !== oldCompanyId) {
    // Recargar el tab activo cuando cambie la empresa
    if (appStore.activeTab !== 'dashboard') {
      loadTabContent(appStore.activeTab)
    }
  }
})

// ============================================================================
// EXPONER FUNCIONES GLOBALES PARA COMPATIBILIDAD - CRÍTICO
// ============================================================================

onMounted(() => {
  // Exponer funciones principales en window para mantener compatibilidad
  window.switchTab = (tabName) => handleTabChange(tabName)
  window.loadTabContent = loadTabContent
  window.initializeTabs = initializeTabs
  window.updateTabNotificationCount = updateTabNotificationCount
  window.refreshActiveTab = refreshActiveTab
  window.getActiveTab = getActiveTab
  
  // Funciones de utilidad
  window.toggleSystemLog = toggleSystemLog
  
  // Log de funciones expuestas
  appStore.addToLog('Global functions exposed for compatibility', 'info')
})

onUnmounted(() => {
  // Limpiar funciones globales
  if (typeof window !== 'undefined') {
    delete window.switchTab
    delete window.loadTabContent
    delete window.initializeTabs
    delete window.updateTabNotificationCount
    delete window.refreshActiveTab
    delete window.getActiveTab
    delete window.toggleSystemLog
  }
})
</script>

<style scoped>
.app {
  min-height: 100vh;
  background-color: var(--bg-primary);
  color: var(--text-primary);
}

.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

.header {
  text-align: center;
  margin-bottom: 30px;
  padding: 20px;
  background: var(--bg-secondary);
  border-radius: 12px;
  border: 1px solid var(--border-color);
}

.header h1 {
  margin: 0 0 10px 0;
  font-size: 2.5em;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.subtitle {
  margin: 0;
  color: var(--text-secondary);
  font-size: 1.1em;
}

.company-selector {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  padding: 15px;
  background: var(--bg-secondary);
  border-radius: 8px;
  border: 1px solid var(--border-color);
  flex-wrap: wrap;
  gap: 15px;
}

.tab-contents {
  margin-top: 20px;
}

/* Estilos globales para drag and drop */
:global(.drag-highlight) {
  background-color: rgba(102, 126, 234, 0.1);
}

:global(.drag-highlight::after) {
  content: '📁 Suelta los archivos aquí';
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(102, 126, 234, 0.9);
  color: white;
  padding: 20px 40px;
  border-radius: 8px;
  font-size: 1.2em;
  z-index: 10000;
  pointer-events: none;
}

/* Responsive */
@media (max-width: 768px) {
  .container {
    padding: 10px;
  }
  
  .header h1 {
    font-size: 2em;
  }
  
  .company-selector {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
