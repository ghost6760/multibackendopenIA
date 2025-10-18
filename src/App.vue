<!-- src/App.vue - ORQUESTADOR GLOBAL -->
<template>
  <div id="app" class="app">
    <!-- Loading Overlay Global -->
    <LoadingOverlay v-if="appStore.isLoadingOverlay" />
    
    <!-- Router View - Delega a las vistas -->
    <router-view />
    
    <!-- Notification Container Global -->
    <AppNotifications />
    
    <!-- Modals Container Global -->
    <div id="modals-container"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useAppStore } from '@/stores/app'
import { useNotifications } from '@/composables/useNotifications'

// Componentes Globales
import LoadingOverlay from '@/components/shared/LoadingOverlay.vue'
import AppNotifications from '@/components/shared/AppNotifications.vue'

// Stores y Composables
const appStore = useAppStore()
const { showNotification } = useNotifications()

// Estado local global
const showSystemLog = ref(false)

// ============================================================================
// 🧠 FUNCIONES PRINCIPALES - LÓGICA GLOBAL
// ============================================================================

/**
 * Maneja el cambio de tab
 */
const handleTabChange = async (tabName) => {
  const success = appStore.setActiveTab(tabName)
  
  if (success) {
    appStore.syncToGlobal()
    await nextTick()
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
 */
const loadTabContent = async (tabName) => {
  try {
    const shouldShowLoader = ['dashboard', 'prompts', 'documents', 'workflows', 'conversations', 'health'].includes(tabName)
    
    if (shouldShowLoader) {
      appStore.setLoadingOverlay(true)
    }
    
    appStore.addToLog(`Loading content for tab: ${tabName}`, 'info')
    
  } catch (error) {
    console.error(`Error loading tab content for ${tabName}:`, error)
    showNotification(`Error al cargar ${tabName}: ${error.message}`, 'error')
    appStore.addToLog(`Error loading tab ${tabName}: ${error.message}`, 'error')
    appStore.setLoadingOverlay(false)
  }
}

/**
 * Inicializa los tabs
 */
const initializeTabs = () => {
  const urlParams = new URLSearchParams(window.location.search)
  const defaultTab = urlParams.get('tab')
  
  const validTabs = ['dashboard', 'documents', 'workflows', 'conversations', 'multimedia', 'prompts', 'admin', 'enterprise', 'health']
  
  if (defaultTab && validTabs.includes(defaultTab)) {
    appStore.setActiveTab(defaultTab)
  } else {
    appStore.setActiveTab('dashboard')
  }
  
  appStore.addToLog('Tabs initialized', 'info')
}

/**
 * Actualiza el contador de notificaciones en un tab
 */
const updateTabNotificationCount = (tabName, count) => {
  appStore.addToLog(`Tab notification count: ${tabName} = ${count}`, 'info')
}

/**
 * Refresca el tab activo actual
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
 */
const getActiveTab = () => {
  return appStore.activeTab
}

/**
 * Toggle del system log
 */
const toggleSystemLog = () => {
  showSystemLog.value = !showSystemLog.value
}

/**
 * Configuración inicial de drag and drop para archivos
 */
const setupFileUploadHandlers = () => {
  const preventDefaults = (e) => {
    e.preventDefault()
    e.stopPropagation()
  }
  
  const events = ['dragenter', 'dragover', 'dragleave', 'drop']
  events.forEach(eventName => {
    document.addEventListener(eventName, preventDefaults, false)
  })
}

// ============================================================================
// LIFECYCLE
// ============================================================================

onMounted(async () => {
  appStore.addToLog('Application initializing...', 'info')
  
  try {
    setupFileUploadHandlers()
    initializeTabs()
    appStore.syncToGlobal()
    
    appStore.addToLog('Application initialized successfully', 'info')
    
  } catch (error) {
    console.error('Error during app initialization:', error)
    showNotification(`Error al inicializar la aplicación: ${error.message}`, 'error')
    appStore.addToLog(`App initialization error: ${error.message}`, 'error')
  }
})

onUnmounted(() => {
  appStore.$dispose()
})

// Watcher para cambios de empresa
watch(() => appStore.currentCompanyId, (newCompanyId, oldCompanyId) => {
  if (newCompanyId !== oldCompanyId) {
    appStore.syncToGlobal()
    appStore.addToLog(`Company changed: ${oldCompanyId} → ${newCompanyId}`, 'info')
  }
})

// ============================================================================
// EXPONER FUNCIONES GLOBALES
// ============================================================================

onMounted(() => {
  if (typeof window !== 'undefined') {
    window.switchTab = (tabName) => handleTabChange(tabName)
    window.loadTabContent = loadTabContent
    window.initializeTabs = initializeTabs
    window.updateTabNotificationCount = updateTabNotificationCount
    window.refreshActiveTab = refreshActiveTab
    window.getActiveTab = getActiveTab
    window.toggleSystemLog = toggleSystemLog
    window.addToLog = appStore.addToLog
    window.showNotification = showNotification
    
    appStore.addToLog('Global functions exposed for compatibility', 'info')
  }
})

onUnmounted(() => {
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

<style>
/* Solo estilos globales */
.app {
  min-height: 100vh;
  background-color: var(--bg-primary);
  color: var(--text-primary);
}
</style>
