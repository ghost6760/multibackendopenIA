<!-- src/App.vue - CON RUTAS AGREGADAS -->
<template>
  <div id="app" class="app">
    <!-- Loading Overlay Global -->
    <LoadingOverlay v-if="appStore.isLoadingOverlay" />
    
    <!-- 🆕 ROUTER VIEW - Solo se muestra en rutas específicas (no en "/") -->
    <router-view v-if="route && route.name !== 'Home'" v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
    
    <!-- ✅ CONTENIDO ORIGINAL - Se muestra en la ruta "/" -->
    <template v-else>
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
            v-if="appStore.activeTab === 'dashboard'"
            :isActive="appStore.activeTab === 'dashboard'"
            @content-loaded="onTabContentLoaded"
          />
          
          <!-- Documents Tab -->
          <DocumentsTab 
            v-if="appStore.activeTab === 'documents'"
            :isActive="appStore.activeTab === 'documents'"
            @content-loaded="onTabContentLoaded"
          />
          
          <!-- Conversations Tab -->
          <ConversationsTab 
            v-if="appStore.activeTab === 'conversations'"
            :isActive="appStore.activeTab === 'conversations'"
            @content-loaded="onTabContentLoaded"
          />
          
          <!-- Multimedia Tab -->
          <MultimediaTab 
            v-if="appStore.activeTab === 'multimedia'"
            :isActive="appStore.activeTab === 'multimedia'"
            @content-loaded="onTabContentLoaded"
          />
          
          <!-- Prompts Tab -->
          <PromptsTab 
            v-if="appStore.activeTab === 'prompts'"
            :isActive="appStore.activeTab === 'prompts'"
            @content-loaded="onTabContentLoaded"
          />
          
          <!-- Admin Tab -->
          <AdminTab 
            v-if="appStore.activeTab === 'admin'"
            :isActive="appStore.activeTab === 'admin'"
            @content-loaded="onTabContentLoaded"
          />
          
          <!-- Enterprise Tab -->
          <EnterpriseTab 
            v-if="appStore.activeTab === 'enterprise'"
            :isActive="appStore.activeTab === 'enterprise'"
            @content-loaded="onTabContentLoaded"
          />
          
          <!-- Health Tab -->
          <HealthTab 
            v-if="appStore.activeTab === 'health'"
            :isActive="appStore.activeTab === 'health'"
            @content-loaded="onTabContentLoaded"
          />
        </div>
        
        <!-- System Log (Collapsible) -->
        <SystemLog v-if="showSystemLog" />
      </div>
    </template>
    
    <!-- Notification Container -->
    <AppNotifications />
    
    <!-- Modals Container -->
    <div id="modals-container"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useAppStore } from '@/stores/app'
import { useNotifications } from '@/composables/useNotifications'
import { useRoute } from 'vue-router' // 🆕 AGREGADO

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
const route = useRoute() // 🆕 AGREGADO

// Estado local
const showSystemLog = ref(false)

// ============================================================================
// FUNCIONES PRINCIPALES - MIGRADAS DESDE SCRIPT.JS - NOMBRES EXACTOS
// ============================================================================

/**
 * Maneja el cambio de tab
 * MIGRADO: switchTab() de script.js - PRESERVAR COMPORTAMIENTO EXACTO
 */
const handleTabChange = async (tabName) => {
  const success = appStore.setActiveTab(tabName)
  
  if (success) {
    // Sincronizar variables globales inmediatamente
    appStore.syncToGlobal()
    
    // Esperar al siguiente tick para que Vue renderice el componente
    await nextTick()
    
    // Los componentes hijos se encargan de cargar su propio contenido
    appStore.addToLog(`Tab changed to: ${tabName}`, 'info')
  }
}

/**
 * Maneja cuando un tab termina de cargar su contenido
 */
const onTabContentLoaded = (tabName) => {
  appStore.setLoadingOverlay(false)
  appStore.addToLog(`Tab content loaded: ${tabName}`, 'info')
}

/**
 * Carga el contenido específico de cada tab
 * MIGRADO: loadTabContent() de script.js - PRESERVAR NOMBRE Y COMPORTAMIENTO
 */
const loadTabContent = async (tabName) => {
  try {
    const shouldShowLoader = ['dashboard', 'prompts', 'documents', 'conversations', 'health'].includes(tabName)
    
    if (shouldShowLoader) {
      appStore.setLoadingOverlay(true)
    }
    
    // Los componentes individuales se encargan de cargar su contenido
    // cuando son activados a través del prop :isActive
    
    appStore.addToLog(`Loading content for tab: ${tabName}`, 'info')
    
  } catch (error) {
    console.error(`Error loading tab content for ${tabName}:`, error)
    showNotification(`Error al cargar ${tabName}: ${error.message}`, 'error')
    appStore.addToLog(`Error loading tab ${tabName}: ${error.message}`, 'error')
    appStore.setLoadingOverlay(false)
  }
}

/**
 * Inicializa los tabs - MIGRADO: initializeTabs() de script.js - EXACTO
 */
const initializeTabs = () => {
  // Verificar si hay un tab por defecto en la URL
  const urlParams = new URLSearchParams(window.location.search)
  const defaultTab = urlParams.get('tab')
  
  const validTabs = ['dashboard', 'documents', 'conversations', 'multimedia', 'prompts', 'admin', 'enterprise', 'health']
  
  if (defaultTab && validTabs.includes(defaultTab)) {
    appStore.setActiveTab(defaultTab)
  } else {
    // Cargar dashboard por defecto - EXACTO COMO SCRIPT.JS
    appStore.setActiveTab('dashboard')
  }
  
  appStore.addToLog('Tabs initialized', 'info')
}

/**
 * Actualiza el contador de notificaciones en un tab
 * MIGRADO: updateTabNotificationCount() de script.js - PRESERVAR NOMBRE EXACTO
 */
const updateTabNotificationCount = (tabName, count) => {
  // Esta función se mantiene para compatibilidad
  appStore.addToLog(`Tab notification count: ${tabName} = ${count}`, 'info')
}

/**
 * Refresca el tab activo actual
 * MIGRADO: refreshActiveTab() de script.js - PRESERVAR NOMBRE EXACTO
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
 * MIGRADO: getActiveTab() de script.js - PRESERVAR NOMBRE EXACTO
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
 * MIGRADO: setupFileUploadHandlers() de script.js - SIMPLIFICADO PARA EVITAR CONFLICTOS
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
}

// ============================================================================
// LIFECYCLE - SIMPLIFICADO PARA EVITAR CONFLICTOS
// ============================================================================

onMounted(async () => {
  appStore.addToLog('Application initializing...', 'info')
  
  try {
    // Configurar handlers de archivo
    setupFileUploadHandlers()
    
    // Inicializar tabs
    initializeTabs()
    
    // Sincronizar variables globales
    appStore.syncToGlobal()
    
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

// Watcher para cambios de empresa - SIMPLIFICADO
watch(() => appStore.currentCompanyId, (newCompanyId, oldCompanyId) => {
  if (newCompanyId !== oldCompanyId) {
    // Sincronizar inmediatamente
    appStore.syncToGlobal()
    appStore.addToLog(`Company changed: ${oldCompanyId} → ${newCompanyId}`, 'info')
  }
})

// ============================================================================
// EXPONER FUNCIONES GLOBALES PARA COMPATIBILIDAD - EXACTAS DE SCRIPT.JS
// ============================================================================

onMounted(() => {
  // Exponer funciones principales en window para mantener compatibilidad con script.js
  if (typeof window !== 'undefined') {
    // Funciones principales - NOMBRES EXACTOS DE SCRIPT.JS
    window.switchTab = (tabName) => handleTabChange(tabName)
    window.loadTabContent = loadTabContent
    window.initializeTabs = initializeTabs
    window.updateTabNotificationCount = updateTabNotificationCount
    window.refreshActiveTab = refreshActiveTab
    window.getActiveTab = getActiveTab
    
    // Funciones de utilidad
    window.toggleSystemLog = toggleSystemLog
    
    // Funciones del store expuestas globalmente
    window.addToLog = appStore.addToLog
    window.showNotification = showNotification
    
    // Log de funciones expuestas
    appStore.addToLog('Global functions exposed for compatibility', 'info')
  }
})

onUnmounted(() => {
  // Limpiar funciones globales
  if (typeof window !== 'undefined') {
    const functionsToClean = [
      'switchTab', 'loadTabContent', 'initializeTabs', 
      'updateTabNotificationCount', 'refreshActiveTab', 'getActiveTab',
      'toggleSystemLog', 'addToLog', 'showNotification'
    ]
    
    functionsToClean.forEach(func => {
      delete window[func]
    })
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

/* 🆕 AGREGADO - Transiciones para router-view */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
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
