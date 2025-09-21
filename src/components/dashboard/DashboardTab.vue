<template>
  <div class="tab-content" :class="{ 'active': isActive }" id="dashboard">
    <!-- Stats Grid -->
    <div class="stats-grid">
      <StatsCard
        icon="🏢"
        title="Empresa Activa"
        :value="appStore.currentCompanyId || 'Ninguna'"
        :highlight="!appStore.currentCompanyId"
        :loading="isLoadingStats"
      />
      <StatsCard
        icon="📊"
        title="Sistema"
        :value="systemStatus"
        :type="systemStatusType"
        :loading="isLoadingSystem"
      />
      <StatsCard
        icon="📝"
        title="Logs"
        :value="`${appStore.systemStats.totalLogs} entradas`"
        :subtitle="`${appStore.systemStats.errorCount} errores`"
        :loading="false"
      />
      <StatsCard
        icon="⏰"
        title="Última Actividad"
        :value="lastActivityFormatted"
        :loading="false"
      />
    </div>
    
    <!-- Main Content Grid -->
    <div class="grid grid-2">
      <!-- System Info Card -->
      <div class="card">
        <h3>🚀 Información del Sistema</h3>
        <div id="systemInfo">
          <SystemInfo 
            :systemInfo="systemInfo"
            :loading="isLoadingSystem"
            @refresh="loadSystemInfo"
          />
        </div>
      </div>
      
      <!-- Companies Status Card -->
      <div class="card">
        <h3>🏢 Estado de Empresas</h3>
        <button class="btn btn-secondary" @click="loadCompaniesStatus" :disabled="isLoadingCompanies">
          <span v-if="isLoadingCompanies">⏳</span>
          <span v-else>🔄</span>
          Actualizar Estado
        </button>
        <div id="companiesStatus" style="margin-top: 15px;">
          <CompaniesStatus 
            :companiesStatus="companiesStatus"
            :loading="isLoadingCompanies"
            @company-selected="handleCompanySelection"
          />
        </div>
      </div>
    </div>
    
    <!-- Action Cards Grid -->
    <div class="grid grid-3">
      <!-- Quick Actions Card -->
      <div class="card">
        <h3>⚡ Acciones Rápidas</h3>
        <div class="quick-actions">
          <button 
            class="btn btn-primary" 
            @click="switchToDocuments"
            :disabled="!appStore.hasCompanySelected"
          >
            📄 Gestionar Documentos
          </button>
          <button 
            class="btn btn-primary" 
            @click="switchToConversations"
            :disabled="!appStore.hasCompanySelected"
          >
            💬 Ver Conversaciones
          </button>
          <button 
            class="btn btn-secondary" 
            @click="runQuickHealthCheck"
            :disabled="isRunningHealthCheck"
          >
            <span v-if="isRunningHealthCheck">⏳</span>
            <span v-else>🏥</span>
            Health Check
          </button>
        </div>
      </div>
      
      <!-- Recent Activity Card -->
      <div class="card">
        <h3>📋 Actividad Reciente</h3>
        <div class="recent-activity">
          <div 
            v-for="entry in appStore.recentLogEntries.slice(0, 5)" 
            :key="entry.id"
            class="activity-entry"
            :class="`level-${entry.level}`"
          >
            <span class="activity-time">
              {{ formatTime(entry.timestamp) }}
            </span>
            <span class="activity-level">
              [{{ entry.level.toUpperCase() }}]
            </span>
            <span class="activity-message">
              {{ entry.message }}
            </span>
          </div>
          <div v-if="appStore.recentLogEntries.length === 0" class="no-activity">
            No hay actividad reciente
          </div>
        </div>
      </div>
      
      <!-- System Resources Card -->
      <div class="card">
        <h3>💻 Recursos del Sistema</h3>
        <div class="system-resources">
          <div class="resource-item">
            <span class="resource-label">Memoria Cache:</span>
            <span class="resource-value">{{ cacheSize }} KB</span>
          </div>
          <div class="resource-item">
            <span class="resource-label">Conexiones API:</span>
            <span class="resource-value">{{ apiConnectionsStatus }}</span>
          </div>
          <div class="resource-item">
            <span class="resource-label">Uptime:</span>
            <span class="resource-value">{{ uptimeFormatted }}</span>
          </div>
        </div>
        <button class="btn btn-outline" @click="refreshSystemResources">
          🔄 Actualizar
        </button>
      </div>
    </div>
    
    <!-- Debug Info (Solo en desarrollo) -->
    <div v-if="showDebugInfo" class="card debug-card">
      <h3>🔧 Información de Debug</h3>
      <details>
        <summary>Ver estado interno</summary>
        <pre>{{ debugInfo }}</pre>
      </details>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'
import StatsCard from './StatsCard.vue'
import SystemInfo from './SystemInfo.vue'
import CompaniesStatus from './CompaniesStatus.vue'

// ============================================================================
// PROPS Y STORES
// ============================================================================

const props = defineProps({
  isActive: {
    type: Boolean,
    default: false
  }
})

const appStore = useAppStore()
const { apiRequest, apiRequestWithCache } = useApiRequest()
const { showNotification } = useNotifications()

// ============================================================================
// ESTADO LOCAL
// ============================================================================

const systemInfo = ref(null)
const companiesStatus = ref(null)
const isLoadingSystem = ref(false)
const isLoadingCompanies = ref(false)
const isLoadingStats = ref(false)
const isRunningHealthCheck = ref(false)
const startTime = ref(Date.now())

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const systemStatus = computed(() => {
  if (!systemInfo.value) return 'Desconocido'
  return systemInfo.value.status || 'Activo'
})

const systemStatusType = computed(() => {
  const status = systemStatus.value.toLowerCase()
  if (status.includes('error') || status.includes('fail')) return 'error'
  if (status.includes('warning') || status.includes('warn')) return 'warning'
  return 'success'
})

const lastActivityFormatted = computed(() => {
  const lastActivity = appStore.systemStats.lastActivity
  if (!lastActivity) return 'Nunca'
  
  const date = new Date(lastActivity)
  return date.toLocaleTimeString()
})

const cacheSize = computed(() => {
  const cache = appStore.cache
  const sizeEstimate = JSON.stringify(cache).length
  return Math.round(sizeEstimate / 1024)
})

const apiConnectionsStatus = computed(() => {
  // Simular estado de conexiones API basado en el último error
  const hasRecentErrors = appStore.systemStats.errorCount > 0
  return hasRecentErrors ? '⚠️ Con errores' : '✅ Estables'
})

const uptimeFormatted = computed(() => {
  const uptime = Date.now() - startTime.value
  const minutes = Math.floor(uptime / 60000)
  const seconds = Math.floor((uptime % 60000) / 1000)
  return `${minutes}m ${seconds}s`
})

const showDebugInfo = computed(() => {
  return import.meta.env.DEV || appStore.adminApiKey
})

const debugInfo = computed(() => {
  return {
    currentCompanyId: appStore.currentCompanyId,
    activeTab: appStore.activeTab,
    cacheKeys: Object.keys(appStore.cache),
    logEntries: appStore.systemLog.length,
    notifications: appStore.notifications.length,
    isMonitoring: appStore.isMonitoringActive
  }
})

// ============================================================================
// MÉTODOS PRINCIPALES - MIGRADOS DESDE SCRIPT.JS
// ============================================================================

/**
 * Carga información del sistema
 * MIGRADO: loadSystemInfo() de script.js
 */
const loadSystemInfo = async () => {
  isLoadingSystem.value = true
  
  try {
    const response = await apiRequestWithCache('/api/system/info', {}, 'systemInfo', 60000)
    systemInfo.value = response
    appStore.updateCache('systemInfo', response)
    
    appStore.addToLog('System info loaded successfully', 'info')
    
  } catch (error) {
    console.error('Error loading system info:', error)
    showNotification(`Error al cargar información del sistema: ${error.message}`, 'error')
    appStore.addToLog(`Error loading system info: ${error.message}`, 'error')
  } finally {
    isLoadingSystem.value = false
  }
}

/**
 * Carga el estado de las empresas
 * MIGRADO: loadCompaniesStatus() de script.js
 */
const loadCompaniesStatus = async () => {
  isLoadingCompanies.value = true
  
  try {
    const response = await apiRequest('/api/health/companies')
    companiesStatus.value = response
    
    appStore.addToLog('Companies status loaded successfully', 'info')
    
  } catch (error) {
    console.error('Error loading companies status:', error)
    showNotification(`Error al cargar estado de empresas: ${error.message}`, 'error')
    appStore.addToLog(`Error loading companies status: ${error.message}`, 'error')
  } finally {
    isLoadingCompanies.value = false
  }
}

/**
 * Actualiza las estadísticas del dashboard
 * MIGRADO: updateStats() de script.js
 */
const updateStats = async () => {
  isLoadingStats.value = true
  
  try {
    // Las estadísticas ya están calculadas en el store
    // Solo necesitamos actualizar el timestamp
    await new Promise(resolve => setTimeout(resolve, 500)) // Simular carga
    
    appStore.addToLog('Dashboard stats updated', 'info')
    
  } catch (error) {
    console.error('Error updating stats:', error)
  } finally {
    isLoadingStats.value = false
  }
}

/**
 * Carga todos los datos del dashboard
 * MIGRADO: loadDashboardData() de script.js
 */
const loadDashboardData = async () => {
  appStore.addToLog('Loading dashboard data...', 'info')
  
  await Promise.all([
    loadSystemInfo(),
    loadCompaniesStatus(),
    updateStats()
  ])
  
  appStore.addToLog('Dashboard data loaded successfully', 'info')
}

// ============================================================================
// MÉTODOS DE ACCIONES
// ============================================================================

/**
 * Cambiar a tab de documentos
 */
const switchToDocuments = () => {
  if (appStore.hasCompanySelected) {
    appStore.setActiveTab('documents')
  } else {
    showNotification('⚠️ Selecciona una empresa primero', 'warning')
  }
}

/**
 * Cambiar a tab de conversaciones
 */
const switchToConversations = () => {
  if (appStore.hasCompanySelected) {
    appStore.setActiveTab('conversations')
  } else {
    showNotification('⚠️ Selecciona una empresa primero', 'warning')
  }
}

/**
 * Ejecutar health check rápido
 */
const runQuickHealthCheck = async () => {
  isRunningHealthCheck.value = true
  
  try {
    const response = await apiRequest('/api/health')
    
    if (response.status === 'healthy') {
      showNotification('✅ Sistema funcionando correctamente', 'success')
    } else {
      showNotification('⚠️ Se detectaron algunos problemas', 'warning')
    }
    
    appStore.addToLog('Quick health check completed', 'info')
    
  } catch (error) {
    showNotification(`❌ Error en health check: ${error.message}`, 'error')
    appStore.addToLog(`Health check error: ${error.message}`, 'error')
  } finally {
    isRunningHealthCheck.value = false
  }
}

/**
 * Maneja la selección de empresa desde el componente
 */
const handleCompanySelection = (companyId) => {
  appStore.setCurrentCompany(companyId)
  showNotification(`Empresa cambiada a: ${companyId}`, 'info')
}

/**
 * Actualiza los recursos del sistema
 */
const refreshSystemResources = () => {
  // Trigger re-computation of computed properties
  startTime.value = Date.now() - (Date.now() - startTime.value)
  showNotification('Recursos del sistema actualizados', 'success')
}

/**
 * Formatea tiempo relativo
 */
const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString()
}

// ============================================================================
// LIFECYCLE HOOKS
// ============================================================================

onMounted(async () => {
  appStore.addToLog('Dashboard tab mounted', 'info')
  
  // Cargar datos iniciales
  await loadDashboardData()
  
  // Event listener para recargar contenido
  window.addEventListener('loadTabContent', handleLoadTabContent)
})

onUnmounted(() => {
  window.removeEventListener('loadTabContent', handleLoadTabContent)
})

// Event handler para carga de contenido
const handleLoadTabContent = (event) => {
  if (event.detail.tabName === 'dashboard') {
    loadDashboardData()
  }
}

// Watcher para recargar cuando cambie la empresa
watch(() => appStore.currentCompanyId, () => {
  if (props.isActive) {
    loadDashboardData()
  }
})

// ============================================================================
// EXPONER FUNCIONES GLOBALES PARA COMPATIBILIDAD
// ============================================================================

onMounted(() => {
  // Exponer funciones específicas del dashboard
  window.loadDashboardData = loadDashboardData
  window.loadSystemInfo = loadSystemInfo
  window.loadCompaniesStatus = loadCompaniesStatus
  window.updateStats = updateStats
})

onUnmounted(() => {
  // Limpiar funciones globales
  if (typeof window !== 'undefined') {
    delete window.loadDashboardData
    delete window.loadSystemInfo
    delete window.loadCompaniesStatus
    delete window.updateStats
  }
})
</script>

<style scoped>
.tab-content {
  display: none;
}

.tab-content.active {
  display: block;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.grid {
  display: grid;
  gap: 20px;
  margin-bottom: 30px;
}

.grid-2 {
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
}

.grid-3 {
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
}

.card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 20px;
}

.card h3 {
  margin: 0 0 15px 0;
  color: var(--text-primary);
  font-size: 1.2em;
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.recent-activity {
  max-height: 200px;
  overflow-y: auto;
}

.activity-entry {
  display: flex;
  gap: 8px;
  padding: 4px 0;
  font-size: 0.9em;
  border-bottom: 1px solid var(--border-light);
}

.activity-time {
  color: var(--text-muted);
  min-width: 60px;
}

.activity-level {
  min-width: 50px;
  font-weight: bold;
}

.activity-level.level-error {
  color: var(--danger-color);
}

.activity-level.level-warning {
  color: var(--warning-color);
}

.activity-level.level-info {
  color: var(--info-color);
}

.activity-message {
  flex: 1;
}

.no-activity {
  text-align: center;
  color: var(--text-muted);
  padding: 20px;
}

.system-resources {
  margin-bottom: 15px;
}

.resource-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-light);
}

.resource-label {
  color: var(--text-secondary);
}

.resource-value {
  font-weight: bold;
  color: var(--text-primary);
}

.debug-card {
  background: var(--bg-tertiary);
  border-color: var(--warning-color);
}

.debug-card pre {
  background: var(--bg-primary);
  padding: 10px;
  border-radius: 4px;
  font-size: 0.8em;
  overflow-x: auto;
}

/* Responsive */
@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .grid-2,
  .grid-3 {
    grid-template-columns: 1fr;
  }
  
  .activity-entry {
    flex-direction: column;
    gap: 4px;
  }
  
  .activity-time,
  .activity-level {
    min-width: auto;
  }
}
</style>
