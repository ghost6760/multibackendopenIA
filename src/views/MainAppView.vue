<!-- src/views/MainAppView.vue -->
<!-- ESTE ES TU App.vue ACTUAL, MOVIDO AQUÍ COMPLETO -->
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

// Estado local
const showSystemLog = ref(false)

// ============================================================================
// TODA TU LÓGICA ACTUAL AQUÍ - SIN CAMBIOS
// ============================================================================

const handleTabChange = async (tabName) => {
  const success = appStore.setActiveTab(tabName)
  
  if (success) {
    appStore.syncToGlobal()
    await nextTick()
    appStore.addToLog(`Tab changed to: ${tabName}`, 'info')
  }
}

const onTabContentLoaded = (tabName) => {
  appStore.setLoadingOverlay(false)
  appStore.addToLog(`Tab content loaded: ${tabName}`, 'info')
}

const loadTabContent = async (tabName) => {
  try {
    const shouldShowLoader = ['dashboard', 'prompts', 'documents', 'conversations', 'health'].includes(tabName)
    
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

const initializeTabs = () => {
  const urlParams = new URLSearchParams(window.location.search)
  const defaultTab = urlParams.get('tab')
  
  const validTabs = ['dashboard', 'documents', 'conversations', 'multimedia', 'prompts', 'admin', 'enterprise', 'health']
  
  if (defaultTab && validTabs.includes(defaultTab)) {
    appStore.setActiveTab(defaultTab)
  } else {
    appStore.setActiveTab('dashboard')
  }
  
  appStore.addToLog('Tabs initialized', 'info')
}

const updateTabNotificationCount = (tabName, count) => {
  appStore.addToLog(`Tab notification count: ${tabName} = ${count}`, 'info')
}

const refreshActiveTab = async () => {
  const activeTab = appStore.activeTab
  if (activeTab) {
    appStore.addToLog(`Refreshing active tab: ${activeTab}`, 'info')
    await loadTabContent(activeTab)
  }
}

const getActiveTab = () => {
  return appStore.activeTab
}

const toggleSystemLog = () => {
  showSystemLog.value = !showSystemLog.value
}

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

watch(() => appStore.currentCompanyId, (newCompanyId, oldCompanyId) => {
  if (newCompanyId !== oldCompanyId) {
    appStore.syncToGlobal()
    appStore.addToLog(`Company changed: ${oldCompanyId} → ${newCompanyId}`, 'info')
  }
})

// Exponer funciones globales
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
