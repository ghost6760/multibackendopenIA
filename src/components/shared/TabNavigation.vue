<template>
  <div class="tabs-container">
    <div class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        :class="[
          'tab',
          { 
            'active': activeTab === tab.id,
            'disabled': tab.disabled,
            'requires-company': tab.requiresCompany && !hasCompanySelected
          }
        ]"
        :data-tab="tab.id"
        @click="handleTabClick(tab)"
        :disabled="tab.disabled"
        :title="getTabTitle(tab)"
      >
        <!-- Tab icon and text -->
        <span class="tab-content">
          <span class="tab-icon">{{ tab.icon }}</span>
          <span class="tab-text">{{ tab.name }}</span>
        </span>
        
        <!-- Notification badge -->
        <span 
          v-if="tab.notificationCount > 0" 
          class="tab-badge"
          :class="{ 'high-count': tab.notificationCount > 99 }"
        >
          {{ tab.notificationCount > 99 ? '99+' : tab.notificationCount }}
        </span>
        
        <!-- Company required indicator -->
        <span v-if="tab.requiresCompany && !hasCompanySelected" class="company-required-indicator" title="Requiere empresa seleccionada">
          🏢
        </span>
      </button>
    </div>
    
    <!-- Tab actions (refresh, etc.) -->
    <div class="tab-actions">
      <button
        @click="refreshActiveTab"
        :disabled="isRefreshing"
        class="tab-action-btn"
        title="Actualizar contenido del tab activo"
      >
        <span v-if="isRefreshing" class="spinning">⏳</span>
        <span v-else>🔄</span>
      </button>
      
      <!-- Admin-only tab actions -->
      <button
        v-if="showAdminActions"
        @click="toggleTabNotifications"
        class="tab-action-btn"
        :title="showNotificationCounts ? 'Ocultar contadores' : 'Mostrar contadores'"
      >
        {{ showNotificationCounts ? '🔕' : '🔔' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { useNotifications } from '@/composables/useNotifications'

// ============================================================================
// PROPS & EMITS
// ============================================================================

const props = defineProps({
  activeTab: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['tab-changed'])

// ============================================================================
// STORES & COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const { showNotification } = useNotifications()

// ============================================================================
// ESTADO LOCAL
// ============================================================================

const isRefreshing = ref(false)
const showNotificationCounts = ref(true)
const tabNotifications = ref({})

// ============================================================================
// TABS CONFIGURATION
// ============================================================================

const tabs = ref([
  {
    id: 'dashboard',
    name: 'Dashboard',
    icon: '📊',
    requiresCompany: false,
    disabled: false,
    notificationCount: 0
  },
  {
    id: 'documents',
    name: 'Documentos',
    icon: '📄',
    requiresCompany: true,
    disabled: false,
    notificationCount: 0
  },
  {
    id: 'conversations',
    name: 'Conversaciones',
    icon: '💬',
    requiresCompany: true,
    disabled: false,
    notificationCount: 0
  },
  {
    id: 'multimedia',
    name: 'Multimedia',
    icon: '🎤',
    requiresCompany: false,
    disabled: false,
    notificationCount: 0
  },
  {
    id: 'prompts',
    name: 'Prompts',
    icon: '🤖',
    requiresCompany: true,
    disabled: false,
    notificationCount: 0
  },
  {
    id: 'admin',
    name: 'Administración',
    icon: '🔧',
    requiresCompany: false,
    disabled: false,
    notificationCount: 0
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    icon: '🏢',
    requiresCompany: false,
    disabled: false,
    notificationCount: 0
  },
  {
    id: 'health',
    name: 'Health Check',
    icon: '🏥',
    requiresCompany: false,
    disabled: false,
    notificationCount: 0
  }
])

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const hasCompanySelected = computed(() => appStore.hasCompanySelected)

const showAdminActions = computed(() => {
  return import.meta.env.DEV || appStore.adminApiKey
})

// ============================================================================
// MÉTODOS PRINCIPALES
// ============================================================================

/**
 * Maneja el click en un tab
 * MIGRADO: Parte de switchTab() de script.js
 */
const handleTabClick = (tab) => {
  if (tab.disabled) {
    return
  }
  
  // Validación para tabs que requieren empresa seleccionada
  if (tab.requiresCompany && !hasCompanySelected.value) {
    showNotification('⚠️ Por favor selecciona una empresa primero', 'warning')
    
    // Resaltar el selector de empresas
    window.dispatchEvent(new CustomEvent('highlightCompanySelector'))
    
    appStore.addToLog(`Tab switch blocked: ${tab.id} requires company selection`, 'warning')
    return
  }
  
  // Emitir evento de cambio de tab
  emit('tab-changed', tab.id)
  
  // Log del cambio
  appStore.addToLog(`Tab clicked: ${tab.id}`, 'info')
}

/**
 * Refresca el contenido del tab activo
 * MIGRADO: refreshActiveTab() de script.js
 */
const refreshActiveTab = async () => {
  if (isRefreshing.value) return
  
  isRefreshing.value = true
  
  try {
    appStore.addToLog(`Refreshing active tab: ${props.activeTab}`, 'info')
    
    // Emitir evento para que el tab activo se recargue
    window.dispatchEvent(new CustomEvent('loadTabContent', {
      detail: { tabName: props.activeTab }
    }))
    
    // Simular delay de refresh
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    showNotification(`✅ Tab ${getTabName(props.activeTab)} actualizado`, 'success', 2000)
    
  } catch (error) {
    console.error('Error refreshing tab:', error)
    showNotification(`Error actualizando tab: ${error.message}`, 'error')
    appStore.addToLog(`Tab refresh error: ${error.message}`, 'error')
    
  } finally {
    isRefreshing.value = false
  }
}

/**
 * Actualiza el contador de notificaciones de un tab
 * MIGRADO: updateTabNotificationCount() de script.js
 */
const updateTabNotificationCount = (tabName, count) => {
  const tab = tabs.value.find(t => t.id === tabName)
  if (tab) {
    tab.notificationCount = Math.max(0, count)
    tabNotifications.value[tabName] = count
    
    appStore.addToLog(`Tab notification count updated: ${tabName} = ${count}`, 'info')
  }
}

/**
 * Obtiene el nombre de un tab por su ID
 */
const getTabName = (tabId) => {
  const tab = tabs.value.find(t => t.id === tabId)
  return tab ? tab.name : tabId
}

/**
 * Obtiene el título/tooltip de un tab
 */
const getTabTitle = (tab) => {
  let title = tab.name
  
  if (tab.requiresCompany && !hasCompanySelected.value) {
    title += ' (Requiere empresa seleccionada)'
  }
  
  if (tab.disabled) {
    title += ' (Deshabilitado)'
  }
  
  if (tab.notificationCount > 0) {
    title += ` (${tab.notificationCount} ${tab.notificationCount === 1 ? 'notificación' : 'notificaciones'})`
  }
  
  return title
}

/**
 * Toggle para mostrar/ocultar contadores de notificaciones
 */
const toggleTabNotifications = () => {
  showNotificationCounts.value = !showNotificationCounts.value
  
  const message = showNotificationCounts.value 
    ? 'Contadores de notificaciones activados'
    : 'Contadores de notificaciones desactivados'
    
  showNotification(message, 'info', 2000)
}

/**
 * Habilita/deshabilita un tab específico
 */
const setTabDisabled = (tabId, disabled) => {
  const tab = tabs.value.find(t => t.id === tabId)
  if (tab) {
    tab.disabled = disabled
    appStore.addToLog(`Tab ${tabId} ${disabled ? 'disabled' : 'enabled'}`, 'info')
  }
}

/**
 * Agrega una notificación visual de cambio de tab
 */
const addTabChangeAnimation = (tabId) => {
  const tabElement = document.querySelector(`[data-tab="${tabId}"]`)
  if (tabElement) {
    tabElement.classList.add('tab-changing')
    setTimeout(() => {
      tabElement.classList.remove('tab-changing')
    }, 500)
  }
}

// ============================================================================
// LIFECYCLE HOOKS
// ============================================================================

onMounted(() => {
  appStore.addToLog('TabNavigation component mounted', 'info')
  
  // Event listeners para actualizar contadores de notificaciones
  window.addEventListener('updateTabNotificationCount', (event) => {
    const { tabName, count } = event.detail
    updateTabNotificationCount(tabName, count)
  })
  
  // Event listener para cambios de tab externos
  window.addEventListener('tabChanged', (event) => {
    const { tabId } = event.detail
    addTabChangeAnimation(tabId)
  })
})

onUnmounted(() => {
  window.removeEventListener('updateTabNotificationCount', () => {})
  window.removeEventListener('tabChanged', () => {})
})

// ============================================================================
// EXPONER FUNCIONES GLOBALES PARA COMPATIBILIDAD
// ============================================================================

onMounted(() => {
  // Exponer funciones globales
  window.updateTabNotificationCount = updateTabNotificationCount
  window.refreshActiveTab = refreshActiveTab
  window.setTabDisabled = setTabDisabled
})

onUnmounted(() => {
  // Limpiar funciones globales
  if (typeof window !== 'undefined') {
    delete window.updateTabNotificationCount
    delete window.refreshActiveTab
    delete window.setTabDisabled
  }
})
</script>

<style scoped>
.tabs-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 15px;
  margin-bottom: 20px;
  padding: 10px 0;
  border-bottom: 2px solid var(--border-color);
}

.tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  flex: 1;
}

.tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 16px;
  background: var(--bg-tertiary);
  border: 2px solid var(--border-color);
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 8px;
  font-size: 0.95em;
  font-weight: 500;
  transition: all 0.3s ease;
  position: relative;
  min-height: 44px; /* Better touch target */
}

.tab:hover:not(.disabled) {
  background: var(--bg-secondary);
  border-color: var(--primary-color);
  color: var(--text-primary);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.tab.active {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: white;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.tab.disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: var(--bg-muted);
}

.tab.requires-company {
  border-style: dashed;
  opacity: 0.7;
}

.tab.requires-company:hover:not(.disabled) {
  border-style: solid;
}

.tab-content {
  display: flex;
  align-items: center;
  gap: 6px;
}

.tab-icon {
  font-size: 1.1em;
  min-width: 20px;
  text-align: center;
}

.tab-text {
  white-space: nowrap;
}

.tab-badge {
  background: var(--danger-color);
  color: white;
  font-size: 0.75em;
  font-weight: bold;
  padding: 2px 6px;
  border-radius: 10px;
  min-width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-left: 4px;
  animation: pulse-badge 2s infinite;
}

.tab-badge.high-count {
  background: var(--warning-color);
}

@keyframes pulse-badge {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
}

.company-required-indicator {
  font-size: 0.8em;
  opacity: 0.7;
  margin-left: 4px;
}

.tab-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.tab-action-btn {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 1.1em;
  min-width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.tab-action-btn:hover:not(:disabled) {
  background: var(--bg-secondary);
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.tab-action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Tab changing animation */
.tab-changing {
  animation: tab-change 0.5s ease;
}

@keyframes tab-change {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
  }
}

/* Responsive design */
@media (max-width: 1024px) {
  .tabs {
    gap: 6px;
  }
  
  .tab {
    padding: 10px 12px;
    font-size: 0.9em;
  }
  
  .tab-text {
    display: none; /* Hide text, show only icons on medium screens */
  }
  
  .tab-icon {
    font-size: 1.3em;
  }
}

@media (max-width: 768px) {
  .tabs-container {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }
  
  .tabs {
    justify-content: center;
    flex-wrap: wrap;
  }
  
  .tab {
    flex: 1;
    min-width: 60px;
    justify-content: center;
  }
  
  .tab-text {
    display: none; /* Icons only on mobile */
  }
  
  .tab-actions {
    justify-content: center;
  }
}

@media (max-width: 480px) {
  .tabs {
    gap: 4px;
  }
  
  .tab {
    padding: 8px 10px;
    min-width: 50px;
  }
  
  .tab-icon {
    font-size: 1.2em;
  }
}

/* High contrast mode */
@media (prefers-contrast: high) {
  .tab {
    border-width: 3px;
  }
  
  .tab.active {
    border-color: white;
    background: var(--primary-color);
  }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .tab {
    transition: none;
  }
  
  .tab:hover:not(.disabled) {
    transform: none;
  }
  
  .tab-badge {
    animation: none;
  }
  
  .spinning {
    animation: none;
  }
  
  .tab-changing {
    animation: none;
  }
}
</style>
