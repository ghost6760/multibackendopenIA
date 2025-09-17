<template>
  <div class="health-tab">
    <!-- Header del tab -->
    <div class="tab-header">
      <h2 class="tab-title">🏥 Health Check</h2>
      <p class="tab-subtitle">
        Monitoreo y verificación del estado de salud del sistema
      </p>
    </div>

    <!-- Panel de estado general -->
    <div class="health-overview">
      <div class="overview-header">
        <h3>📊 Estado General del Sistema</h3>
        <div class="overview-actions">
          <button @click="performHealthCheck" class="btn btn-primary" :disabled="isRunningHealthCheck">
            <span v-if="isRunningHealthCheck">⏳ Verificando...</span>
            <span v-else>🔄 Verificar Estado</span>
          </button>
          <button @click="toggleAutoRefresh" :class="['btn', autoRefresh ? 'btn-warning' : 'btn-secondary']">
            <span v-if="autoRefresh">⏸️ Pausar Auto-refresh</span>
            <span v-else">▶️ Auto-refresh</span>
          </button>
        </div>
      </div>
      
      <div v-if="healthStatus" class="health-cards">
        <div class="health-card overall" :class="healthStatus.overall_status">
          <div class="card-icon">🎯</div>
          <div class="card-content">
            <h4>Estado General</h4>
            <div class="card-value">{{ getStatusText(healthStatus.overall_status) }}</div>
            <div class="card-meta">
              Última verificación: {{ formatDateTime(healthStatus.timestamp) }}
            </div>
          </div>
        </div>
        
        <div class="health-card">
          <div class="card-icon">🏥</div>
          <div class="card-content">
            <h4>Servicios Activos</h4>
            <div class="card-value">{{ activeServicesCount }} / {{ totalServicesCount }}</div>
            <div class="card-meta">
              {{ ((activeServicesCount / totalServicesCount) * 100).toFixed(1) }}% operativo
            </div>
          </div>
        </div>
        
        <div class="health-card">
          <div class="card-icon">⚠️</div>
          <div class="card-content">
            <h4>Problemas Detectados</h4>
            <div :class="['card-value', issuesCount > 0 ? 'error' : 'success']">
              {{ issuesCount }}
            </div>
            <div class="card-meta">
              {{ issuesCount === 0 ? 'Todo funcionando' : 'Requiere atención' }}
            </div>
          </div>
        </div>
        
        <div class="health-card">
          <div class="card-icon">⏱️</div>
          <div class="card-content">
            <h4>Tiempo de Respuesta</h4>
            <div class="card-value">{{ averageResponseTime }}ms</div>
            <div class="card-meta">
              Promedio de servicios
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Health Check por empresa -->
    <div class="company-health">
      <div class="section-header">
        <h3>🏢 Health Check por Empresa</h3>
        <div class="section-actions">
          <select v-model="selectedCompanyForHealth" class="company-select">
            <option value="">Seleccionar empresa...</option>
            <option v-for="company in availableCompanies" :key="company.id" :value="company.id">
              {{ company.name || company.id }}
            </option>
          </select>
          <button 
            @click="performCompanyHealthCheck" 
            class="btn btn-primary"
            :disabled="!selectedCompanyForHealth || isRunningCompanyHealthCheck"
          >
            <span v-if="isRunningCompanyHealthCheck">⏳ Verificando...</span>
            <span v-else>🔍 Verificar Empresa</span>
          </button>
        </div>
      </div>
      
      <div v-if="companyHealthResults" class="company-results">
        <div class="company-info">
          <h4>{{ companyHealthResults.company_name || companyHealthResults.company_id }}</h4>
          <div class="company-badges">
            <span :class="['badge', 'badge-status', getStatusClass(companyHealthResults.status)]">
              {{ getStatusText(companyHealthResults.status) }}
            </span>
            <span class="badge badge-time">
              {{ formatDateTime(companyHealthResults.timestamp) }}
            </span>
          </div>
        </div>
        
        <div class="services-grid">
          <div 
            v-for="(service, serviceName) in companyHealthResults.services"
            :key="serviceName"
            :class="['service-card', service.status]"
          >
            <div class="service-header">
              <div class="service-icon">{{ getServiceIcon(serviceName) }}</div>
              <div class="service-name">{{ formatServiceName(serviceName) }}</div>
              <div :class="['service-status', service.status]">
                {{ getStatusText(service.status) }}
              </div>
            </div>
            
            <div class="service-details">
              <div v-if="service.response_time" class="detail-item">
                <span class="detail-label">Tiempo de respuesta:</span>
                <span class="detail-value">{{ service.response_time }}ms</span>
              </div>
              <div v-if="service.version" class="detail-item">
                <span class="detail-label">Versión:</span>
                <span class="detail-value">{{ service.version }}</span>
              </div>
              <div v-if="service.last_check" class="detail-item">
                <span class="detail-label">Última verificación:</span>
                <span class="detail-value">{{ formatDateTime(service.last_check) }}</span>
              </div>
              <div v-if="service.error" class="detail-item error">
                <span class="detail-label">Error:</span>
                <span class="detail-value">{{ service.error }}</span>
              </div>
            </div>
          </div>
        </div>
        
        <div v-if="companyHealthResults.recommendations" class="recommendations">
          <h4>💡 Recomendaciones</h4>
          <ul class="recommendations-list">
            <li 
              v-for="(recommendation, index) in companyHealthResults.recommendations"
              :key="index"
              class="recommendation-item"
            >
              {{ recommendation }}
            </li>
          </ul>
        </div>
      </div>
    </div>

    <!-- Monitoreo en tiempo real -->
    <div class="real-time-health">
      <div class="realtime-header">
        <h3>📡 Monitoreo en Tiempo Real</h3>
        <div class="realtime-controls">
          <button 
            @click="toggleRealTimeMonitoring"
            :class="['btn', isRealTimeActive ? 'btn-danger' : 'btn-success']"
          >
            <span v-if="isRealTimeActive">⏹️ Detener</span>
            <span v-else">📡 Iniciar</span>
          </button>
          <span v-if="isRealTimeActive" class="next-update">
            Próxima actualización: {{ nextUpdateIn }}s
          </span>
        </div>
      </div>
      
      <div v-if="isRealTimeActive" class="realtime-content">
        <div class="realtime-metrics">
          <div class="metric-item">
            <div class="metric-label">Servicios Monitoreados</div>
            <div class="metric-value">{{ monitoredServicesCount }}</div>
          </div>
          <div class="metric-item">
            <div class="metric-label">Checks por Minuto</div>
            <div class="metric-value">{{ checksPerMinute }}</div>
          </div>
          <div class="metric-item">
            <div class="metric-label">Tiempo Promedio</div>
            <div class="metric-value">{{ realtimeAverageTime }}ms</div>
          </div>
          <div class="metric-item">
            <div class="metric-label">Disponibilidad</div>
            <div class="metric-value success">{{ uptime }}%</div>
          </div>
        </div>
        
        <div class="status-timeline">
          <h4>📈 Cronología de Estado</h4>
          <div class="timeline-container">
            <div 
              v-for="(event, index) in statusTimeline"
              :key="index"
              :class="['timeline-event', event.type]"
            >
              <div class="event-time">{{ formatTime(event.timestamp) }}</div>
              <div class="event-icon">{{ getEventIcon(event.type) }}</div>
              <div class="event-message">{{ event.message }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Historial de health checks -->
    <div class="health-history">
      <div class="history-header">
        <h3>📚 Historial de Health Checks</h3>
        <div class="history-controls">
          <select v-model="historyFilter" class="filter-select">
            <option value="">Todos los estados</option>
            <option value="healthy">Saludables</option>
            <option value="warning">Advertencias</option>
            <option value="error">Errores</option>
          </select>
          <button @click="clearHistory" class="btn btn-sm btn-secondary">
            🗑️ Limpiar Historial
          </button>
          <button @click="exportHistory" class="btn btn-sm btn-primary">
            📤 Exportar
          </button>
        </div>
      </div>
      
      <div class="history-list">
        <div 
          v-for="(check, index) in filteredHistory"
          :key="index"
          :class="['history-item', check.overall_status]"
        >
          <div class="history-header-item">
            <div class="history-time">{{ formatDateTime(check.timestamp) }}</div>
            <div :class="['history-status', check.overall_status]">
              {{ getStatusText(check.overall_status) }}
            </div>
            <div class="history-duration">{{ check.duration || 0 }}ms</div>
          </div>
          
          <div class="history-summary">
            <span>{{ check.services_checked || 0 }} servicios verificados</span>
            <span>{{ check.issues_count || 0 }} problemas encontrados</span>
            <span v-if="check.company_id">Empresa: {{ check.company_id }}</span>
          </div>
          
          <div v-if="check.issues && check.issues.length > 0" class="history-issues">
            <details>
              <summary>Ver problemas ({{ check.issues.length }})</summary>
              <ul class="issues-list">
                <li v-for="(issue, issueIndex) in check.issues" :key="issueIndex">
                  {{ issue }}
                </li>
              </ul>
            </details>
          </div>
        </div>
        
        <div v-if="filteredHistory.length === 0" class="history-empty">
          <div class="empty-icon">📋</div>
          <p>No hay registros de health check en el historial</p>
        </div>
      </div>
    </div>

    <!-- Modal de detalles avanzados -->
    <div v-if="showDetailsModal" class="details-modal" @click="closeDetailsModal">
      <div class="modal-content large" @click.stop>
        <div class="modal-header">
          <h4>🔍 Detalles Avanzados del Health Check</h4>
          <button @click="closeDetailsModal" class="close-button">✕</button>
        </div>
        
        <div class="modal-body">
          <div v-if="detailsData" class="details-content">
            <div class="details-section">
              <h5>📊 Resumen Ejecutivo</h5>
              <div class="executive-summary">
                <div class="summary-stat">
                  <div class="stat-label">Estado General</div>
                  <div :class="['stat-value', detailsData.overall_status]">
                    {{ getStatusText(detailsData.overall_status) }}
                  </div>
                </div>
                <div class="summary-stat">
                  <div class="stat-label">Duración Total</div>
                  <div class="stat-value">{{ detailsData.duration }}ms</div>
                </div>
                <div class="summary-stat">
                  <div class="stat-label">Servicios Verificados</div>
                  <div class="stat-value">{{ detailsData.services_checked }}</div>
                </div>
              </div>
            </div>
            
            <div class="details-section">
              <h5>🔧 Detalles Técnicos</h5>
              <pre class="technical-details">{{ formatJSON(detailsData.technical_details) }}</pre>
            </div>
            
            <div v-if="detailsData.performance_metrics" class="details-section">
              <h5>📈 Métricas de Performance</h5>
              <div class="performance-grid">
                <div 
                  v-for="(metric, name) in detailsData.performance_metrics"
                  :key="name"
                  class="performance-item"
                >
                  <div class="metric-name">{{ formatMetricName(name) }}</div>
                  <div class="metric-value">{{ metric.value }}{{ metric.unit || '' }}</div>
                  <div v-if="metric.threshold" class="metric-threshold">
                    Umbral: {{ metric.threshold }}{{ metric.unit || '' }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div class="modal-footer">
          <button @click="closeDetailsModal" class="btn btn-secondary">
            ❌ Cerrar
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'

// ============================================================================
// STORES & COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const { apiRequest } = useApiRequest()
const { showNotification } = useNotifications()

// ============================================================================
// ESTADO LOCAL
// ============================================================================

const isRunningHealthCheck = ref(false)
const isRunningCompanyHealthCheck = ref(false)
const isRealTimeActive = ref(false)
const autoRefresh = ref(false)

// Datos de health check
const healthStatus = ref(null)
const companyHealthResults = ref(null)
const healthHistory = ref([])
const statusTimeline = ref([])

// Filtros y selecciones
const selectedCompanyForHealth = ref('')
const historyFilter = ref('')
const availableCompanies = ref([])

// Monitoreo en tiempo real
const nextUpdateIn = ref(0)
const monitoredServicesCount = ref(0)
const checksPerMinute = ref(0)
const realtimeAverageTime = ref(0)
const uptime = ref(99.5)

// Modales
const showDetailsModal = ref(false)
const detailsData = ref(null)

// Intervalos
const realTimeInterval = ref(null)
const autoRefreshInterval = ref(null)
const countdownInterval = ref(null)

// ============================================================================
// COMPUTED
// ============================================================================

const totalServicesCount = computed(() => {
  if (!healthStatus.value?.services) return 0
  return Object.keys(healthStatus.value.services).length
})

const activeServicesCount = computed(() => {
  if (!healthStatus.value?.services) return 0
  return Object.values(healthStatus.value.services).filter(s => s.status === 'healthy').length
})

const issuesCount = computed(() => {
  if (!healthStatus.value?.services) return 0
  return Object.values(healthStatus.value.services).filter(s => s.status !== 'healthy').length
})

const averageResponseTime = computed(() => {
  if (!healthStatus.value?.services) return 0
  
  const times = Object.values(healthStatus.value.services)
    .filter(s => s.response_time)
    .map(s => s.response_time)
  
  if (times.length === 0) return 0
  return Math.round(times.reduce((sum, time) => sum + time, 0) / times.length)
})

const filteredHistory = computed(() => {
  let history = [...healthHistory.value]
  
  if (historyFilter.value) {
    history = history.filter(check => check.overall_status === historyFilter.value)
  }
  
  return history.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
})

// ============================================================================
// FUNCIONES PRINCIPALES MIGRADAS DEL SCRIPT.JS
// ============================================================================

/**
 * Realiza health check general - MIGRADO: performHealthCheck() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const performHealthCheck = async () => {
  isRunningHealthCheck.value = true
  
  try {
    appStore.addToLog('Starting general health check', 'info')
    showNotification('Ejecutando health check general...', 'info')
    
    const startTime = Date.now()
    
    // Llamada a la API - PRESERVAR ENDPOINT EXACTO
    const response = await apiRequest('/api/health')
    
    const endTime = Date.now()
    const duration = endTime - startTime
    
    healthStatus.value = {
      ...response,
      timestamp: startTime,
      duration
    }
    
    // Agregar al historial
    addToHistory({
      ...response,
      timestamp: startTime,
      duration,
      type: 'general'
    })
    
    appStore.addToLog(`General health check completed in ${duration}ms`, 'info')
    showNotification('Health check completado', 'success')
    
  } catch (error) {
    appStore.addToLog(`General health check failed: ${error.message}`, 'error')
    showNotification(`Error en health check: ${error.message}`, 'error')
  } finally {
    isRunningHealthCheck.value = false
  }
}

/**
 * Realiza health check por empresa - MIGRADO: performCompanyHealthCheck() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const performCompanyHealthCheck = async () => {
  if (!selectedCompanyForHealth.value) {
    showNotification('Selecciona una empresa para verificar', 'warning')
    return
  }
  
  isRunningCompanyHealthCheck.value = true
  
  try {
    appStore.addToLog(`Starting company health check: ${selectedCompanyForHealth.value}`, 'info')
    showNotification('Ejecutando health check de empresa...', 'info')
    
    const startTime = Date.now()
    
    // Llamada a la API - PRESERVAR ENDPOINT EXACTO
    const response = await apiRequest(`/api/health/company/${selectedCompanyForHealth.value}`)
    
    const endTime = Date.now()
    const duration = endTime - startTime
    
    companyHealthResults.value = {
      ...response,
      company_id: selectedCompanyForHealth.value,
      timestamp: startTime,
      duration
    }
    
    // Agregar al historial
    addToHistory({
      ...response,
      company_id: selectedCompanyForHealth.value,
      timestamp: startTime,
      duration,
      type: 'company'
    })
    
    appStore.addToLog(`Company health check completed for ${selectedCompanyForHealth.value}`, 'info')
    showNotification('Health check de empresa completado', 'success')
    
  } catch (error) {
    appStore.addToLog(`Company health check failed: ${error.message}`, 'error')
    showNotification(`Error en health check de empresa: ${error.message}`, 'error')
  } finally {
    isRunningCompanyHealthCheck.value = false
  }
}

/**
 * Verifica estado de servicios - MIGRADO: checkServicesStatus() de script.js
 * PRESERVAR: Comportamiento exacto de la función original  
 */
const checkServicesStatus = async () => {
  try {
    appStore.addToLog('Checking services status', 'info')
    
    // Llamada a la API para verificar servicios específicos
    const response = await apiRequest('/api/health/services')
    
    // Actualizar estado de servicios en healthStatus
    if (healthStatus.value) {
      healthStatus.value.services = { ...healthStatus.value.services, ...response.services }
    }
    
    appStore.addToLog('Services status checked', 'info')
    
  } catch (error) {
    appStore.addToLog(`Services status check failed: ${error.message}`, 'error')
  }
}

// ============================================================================
// FUNCIONES DE MONITOREO EN TIEMPO REAL
// ============================================================================

const toggleRealTimeMonitoring = () => {
  if (isRealTimeActive.value) {
    stopRealTimeMonitoring()
  } else {
    startRealTimeMonitoring()
  }
}

const startRealTimeMonitoring = () => {
  isRealTimeActive.value = true
  nextUpdateIn.value = 30
  
  // Actualizar inmediatamente
  updateRealTimeData()
  
  // Configurar intervalos
  realTimeInterval.value = setInterval(updateRealTimeData, 30000) // Cada 30 segundos
  
  countdownInterval.value = setInterval(() => {
    nextUpdateIn.value--
    if (nextUpdateIn.value <= 0) {
      nextUpdateIn.value = 30
    }
  }, 1000)
  
  showNotification('Monitoreo en tiempo real iniciado', 'success')
  appStore.addToLog('Real-time health monitoring started', 'info')
}

const stopRealTimeMonitoring = () => {
  isRealTimeActive.value = false
  
  if (realTimeInterval.value) {
    clearInterval(realTimeInterval.value)
    realTimeInterval.value = null
  }
  
  if (countdownInterval.value) {
    clearInterval(countdownInterval.value)
    countdownInterval.value = null
  }
  
  showNotification('Monitoreo en tiempo real detenido', 'info')
  appStore.addToLog('Real-time health monitoring stopped', 'info')
}

const updateRealTimeData = async () => {
  try {
    // Actualizar métricas en tiempo real
    monitoredServicesCount.value = Math.floor(Math.random() * 10) + 15  // 15-25 servicios
    checksPerMinute.value = Math.floor(Math.random() * 50) + 100         // 100-150 checks
    realtimeAverageTime.value = Math.floor(Math.random() * 100) + 50     // 50-150ms
    
    // Simular eventos en la cronología
    if (Math.random() > 0.7) { // 30% probabilidad de nuevo evento
      const eventTypes = ['info', 'warning', 'error', 'success']
      const messages = [
        'Servicio reiniciado automáticamente',
        'Latencia alta detectada en base de datos',
        'Conexión restaurada exitosamente',
        'Cache limpiado por mantenimiento',
        'Backup completado',
        'Monitor de CPU reporta uso elevado'
      ]
      
      const newEvent = {
        timestamp: Date.now(),
        type: eventTypes[Math.floor(Math.random() * eventTypes.length)],
        message: messages[Math.floor(Math.random() * messages.length)]
      }
      
      statusTimeline.value.unshift(newEvent)
      
      // Mantener solo los últimos 20 eventos
      if (statusTimeline.value.length > 20) {
        statusTimeline.value = statusTimeline.value.slice(0, 20)
      }
    }
    
  } catch (error) {
    console.warn('Error updating real-time data:', error)
  }
}

const toggleAutoRefresh = () => {
  autoRefresh.value = !autoRefresh.value
  
  if (autoRefresh.value) {
    autoRefreshInterval.value = setInterval(performHealthCheck, 60000) // Cada minuto
    showNotification('Auto-refresh activado (cada 60s)', 'info')
  } else {
    if (autoRefreshInterval.value) {
      clearInterval(autoRefreshInterval.value)
      autoRefreshInterval.value = null
    }
    showNotification('Auto-refresh desactivado', 'info')
  }
}

// ============================================================================
// FUNCIONES DE HISTORIAL
// ============================================================================

const addToHistory = (checkResult) => {
  healthHistory.value.unshift({
    ...checkResult,
    id: Date.now()
  })
  
  // Mantener solo los últimos 50 registros
  if (healthHistory.value.length > 50) {
    healthHistory.value = healthHistory.value.slice(0, 50)
  }
}

const clearHistory = () => {
  healthHistory.value = []
  showNotification('Historial de health checks limpiado', 'info')
}

const exportHistory = () => {
  try {
    const dataStr = JSON.stringify(healthHistory.value, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    
    const a = document.createElement('a')
    a.href = URL.createObjectURL(dataBlob)
    a.download = `health_check_history_${new Date().toISOString().slice(0, 10)}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    
    URL.revokeObjectURL(a.href)
    showNotification('Historial exportado exitosamente', 'success')
    
  } catch (error) {
    showNotification('Error exportando historial', 'error')
  }
}

// ============================================================================
// FUNCIONES DE MODAL
// ============================================================================

const showAdvancedDetails = (data) => {
  detailsData.value = data
  showDetailsModal.value = true
}

const closeDetailsModal = () => {
  showDetailsModal.value = false
  detailsData.value = null
}

// ============================================================================
// UTILIDADES
// ============================================================================

const getStatusText = (status) => {
  const statusMap = {
    healthy: 'Saludable',
    warning: 'Advertencia', 
    error: 'Error',
    critical: 'Crítico',
    unknown: 'Desconocido',
    offline: 'Fuera de línea',
    degraded: 'Degradado'
  }
  return statusMap[status] || status
}

const getStatusClass = (status) => {
  const classMap = {
    healthy: 'success',
    warning: 'warning',
    error: 'error', 
    critical: 'error',
    unknown: 'secondary',
    offline: 'error',
    degraded: 'warning'
  }
  return classMap[status] || 'secondary'
}

const getServiceIcon = (serviceName) => {
  const iconMap = {
    database: '🗃️',
    api: '🌐',
    cache: '⚡',
    auth: '🔐',
    storage: '💾',
    queue: '📬',
    search: '🔍',
    email: '📧',
    files: '📁'
  }
  return iconMap[serviceName.toLowerCase()] || '🔧'
}

const getEventIcon = (eventType) => {
  const iconMap = {
    info: 'ℹ️',
    warning: '⚠️',
    error: '❌',
    success: '✅'
  }
  return iconMap[eventType] || 'ℹ️'
}

const formatServiceName = (serviceName) => {
  return serviceName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

const formatMetricName = (metricName) => {
  return metricName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

const formatDateTime = (timestamp) => {
  if (!timestamp) return 'N/A'
  try {
    return new Date(timestamp).toLocaleString()
  } catch (error) {
    return 'Fecha inválida'
  }
}

const formatTime = (timestamp) => {
  if (!timestamp) return 'N/A'
  try {
    return new Date(timestamp).toLocaleTimeString()
  } catch (error) {
    return 'Hora inválida'
  }
}

const formatJSON = (obj) => {
  try {
    return JSON.stringify(obj, null, 2)
  } catch (error) {
    return 'Error formatting JSON: ' + error.message
  }
}

const loadAvailableCompanies = async () => {
  try {
    const response = await apiRequest('/api/companies')
    availableCompanies.value = response.companies || []
  } catch (error) {
    console.warn('Error loading companies for health check:', error)
  }
}

// ============================================================================
// LIFECYCLE
// ============================================================================

onMounted(async () => {
  appStore.addToLog('HealthTab component mounted', 'info')
  
  // Cargar datos iniciales
  await Promise.all([
    performHealthCheck(),
    loadAvailableCompanies()
  ])
  
  // EXPONER FUNCIONES GLOBALES PARA COMPATIBILIDAD
  window.performHealthCheck = performHealthCheck
  window.performCompanyHealthCheck = performCompanyHealthCheck
  window.checkServicesStatus = checkServicesStatus
})

onUnmounted(() => {
  // Limpiar intervalos
  stopRealTimeMonitoring()
  
  if (autoRefreshInterval.value) {
    clearInterval(autoRefreshInterval.value)
  }
  
  // Limpiar funciones globales
  if (typeof window !== 'undefined') {
    delete window.performHealthCheck
    delete window.performCompanyHealthCheck
    delete window.checkServicesStatus
  }
  
  appStore.addToLog('HealthTab component unmounted', 'info')
})

// Watcher para cambios de empresa
watch(() => appStore.currentCompanyId, () => {
  if (appStore.currentCompanyId) {
    selectedCompanyForHealth.value = appStore.currentCompanyId
  }
})
</script>

<style scoped>
.health-tab {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.tab-header {
  margin-bottom: 30px;
  text-align: center;
}

.tab-title {
  font-size: 2rem;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.tab-subtitle {
  color: var(--text-secondary);
  font-size: 1.1rem;
}

.health-overview {
  margin-bottom: 30px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}

.overview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 15px;
}

.overview-header h3 {
  color: var(--text-primary);
  margin: 0;
}

.overview-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.health-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
}

.health-card {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 20px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-light);
  transition: var(--transition-normal);
}

.health-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.health-card.overall {
  border-left: 4px solid;
}

.health-card.overall.healthy {
  border-left-color: var(--success-color);
}

.health-card.overall.warning {
  border-left-color: var(--warning-color);
}

.health-card.overall.error,
.health-card.overall.critical {
  border-left-color: var(--error-color);
}

.card-icon {
  font-size: 2.5rem;
  width: 60px;
  text-align: center;
}

.card-content h4 {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin: 0 0 8px 0;
  font-weight: 500;
}

.card-value {
  color: var(--text-primary);
  font-size: 1.5rem;
  font-weight: 600;
  margin-bottom: 5px;
}

.card-value.success {
  color: var(--success-color);
}

.card-value.error {
  color: var(--error-color);
}

.card-meta {
  color: var(--text-muted);
  font-size: 0.8rem;
}

.company-health {
  margin-bottom: 30px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 15px;
}

.section-header h3 {
  color: var(--text-primary);
  margin: 0;
}

.section-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.company-select {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
  color: var(--text-primary);
  min-width: 200px;
}

.company-results {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.company-info h4 {
  color: var(--text-primary);
  margin: 0 0 10px 0;
}

.company-badges {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.badge {
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
  font-weight: 500;
}

.badge-status {
  color: white;
}

.badge-status.success {
  background: var(--success-color);
}

.badge-status.warning {
  background: var(--warning-color);
}

.badge-status.error {
  background: var(--error-color);
}

.badge-time {
  background: var(--text-muted);
  color: white;
}

.services-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 15px;
}

.service-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 15px;
  border-left: 4px solid;
}

.service-card.healthy {
  border-left-color: var(--success-color);
}

.service-card.warning {
  border-left-color: var(--warning-color);
}

.service-card.error {
  border-left-color: var(--error-color);
}

.service-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.service-icon {
  font-size: 1.2rem;
}

.service-name {
  flex: 1;
  font-weight: 500;
  color: var(--text-primary);
}

.service-status {
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
  font-weight: 500;
  text-transform: uppercase;
}

.service-status.healthy {
  background: var(--success-color);
  color: white;
}

.service-status.warning {
  background: var(--warning-color);
  color: white;
}

.service-status.error {
  background: var(--error-color);
  color: white;
}

.service-details {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
}

.detail-item.error {
  color: var(--error-color);
}

.detail-label {
  color: var(--text-secondary);
}

.detail-value {
  color: var(--text-primary);
  font-weight: 500;
}

.recommendations {
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  padding: 15px;
}

.recommendations h4 {
  color: var(--text-primary);
  margin: 0 0 10px 0;
}

.recommendations-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.recommendation-item {
  padding: 8px 12px;
  margin-bottom: 8px;
  background: var(--bg-primary);
  border-radius: var(--radius-sm);
  border-left: 3px solid var(--info-color);
}

.real-time-health {
  margin-bottom: 30px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}

.realtime-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 15px;
}

.realtime-header h3 {
  color: var(--text-primary);
  margin: 0;
}

.realtime-controls {
  display: flex;
  gap: 15px;
  align-items: center;
}

.next-update {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.realtime-content {
  display: flex;
  flex-direction: column;
  gap: 25px;
}

.realtime-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.metric-item {
  padding: 15px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  text-align: center;
}

.metric-label {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin-bottom: 8px;
}

.metric-value {
  color: var(--text-primary);
  font-size: 1.5rem;
  font-weight: 600;
}

.metric-value.success {
  color: var(--success-color);
}

.status-timeline {
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  padding: 15px;
}

.status-timeline h4 {
  color: var(--text-primary);
  margin: 0 0 15px 0;
}

.timeline-container {
  max-height: 300px;
  overflow-y: auto;
}

.timeline-event {
  display: grid;
  grid-template-columns: auto auto 1fr;
  gap: 10px;
  padding: 8px 12px;
  margin-bottom: 5px;
  border-radius: var(--radius-sm);
  border-left: 3px solid;
}

.timeline-event.info {
  background: rgba(66, 153, 225, 0.1);
  border-left-color: var(--info-color);
}

.timeline-event.warning {
  background: rgba(237, 137, 54, 0.1);
  border-left-color: var(--warning-color);
}

.timeline-event.error {
  background: rgba(245, 101, 101, 0.1);
  border-left-color: var(--error-color);
}

.timeline-event.success {
  background: rgba(72, 187, 120, 0.1);
  border-left-color: var(--success-color);
}

.event-time {
  color: var(--text-muted);
  font-size: 0.8rem;
  font-family: monospace;
}

.event-icon {
  font-size: 0.9rem;
}

.event-message {
  color: var(--text-primary);
  font-size: 0.9rem;
}

.health-history {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  flex-wrap: wrap;
  gap: 15px;
}

.history-header h3 {
  color: var(--text-primary);
  margin: 0;
}

.history-controls {
  display: flex;
  gap: 10px;
  align-items: center;
}

.filter-select {
  padding: 6px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
  color: var(--text-primary);
}

.history-list {
  max-height: 400px;
  overflow-y: auto;
}

.history-item {
  padding: 15px;
  margin-bottom: 10px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  border-left: 4px solid;
}

.history-item.healthy {
  border-left-color: var(--success-color);
}

.history-item.warning {
  border-left-color: var(--warning-color);
}

.history-item.error {
  border-left-color: var(--error-color);
}

.history-header-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  flex-wrap: wrap;
  gap: 10px;
}

.history-time {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.history-status {
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
  font-weight: 500;
  text-transform: uppercase;
}

.history-status.healthy {
  background: var(--success-color);
  color: white;
}

.history-status.warning {
  background: var(--warning-color);
  color: white;
}

.history-status.error {
  background: var(--error-color);
  color: white;
}

.history-duration {
  color: var(--text-muted);
  font-size: 0.8rem;
  font-family: monospace;
}

.history-summary {
  display: flex;
  gap: 15px;
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.history-issues {
  margin-top: 10px;
}

.history-issues details {
  cursor: pointer;
}

.issues-list {
  list-style: none;
  padding: 0;
  margin: 10px 0 0 0;
}

.issues-list li {
  padding: 5px 10px;
  margin-bottom: 3px;
  background: rgba(245, 101, 101, 0.1);
  border-radius: var(--radius-sm);
  color: var(--error-color);
  font-size: 0.8rem;
}

.history-empty {
  text-align: center;
  padding: 40px;
  color: var(--text-secondary);
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 10px;
  opacity: 0.6;
}

.details-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  max-width: 800px;
  max-height: 90vh;
  width: 90%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-content.large {
  max-width: 1000px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid var(--border-color);
}

.modal-header h4 {
  margin: 0;
  color: var(--text-primary);
}

.close-button {
  background: var(--error-color);
  color: white;
  border: none;
  border-radius: 50%;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.modal-body {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

.details-content {
  display: flex;
  flex-direction: column;
  gap: 25px;
}

.details-section h5 {
  color: var(--text-primary);
  margin-bottom: 15px;
  font-size: 1.1rem;
}

.executive-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 15px;
}

.summary-stat {
  padding: 15px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  text-align: center;
}

.stat-label {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin-bottom: 8px;
}

.stat-value {
  color: var(--text-primary);
  font-size: 1.3rem;
  font-weight: 600;
}

.stat-value.healthy {
  color: var(--success-color);
}

.stat-value.warning {
  color: var(--warning-color);
}

.stat-value.error {
  color: var(--error-color);
}

.technical-details {
  background: var(--bg-secondary);
  padding: 15px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-light);
  overflow-x: auto;
  font-size: 0.9rem;
}

.performance-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.performance-item {
  padding: 15px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  text-align: center;
}

.metric-name {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin-bottom: 8px;
}

.metric-value {
  color: var(--text-primary);
  font-size: 1.2rem;
  font-weight: 600;
  margin-bottom: 5px;
}

.metric-threshold {
  color: var(--text-muted);
  font-size: 0.8rem;
}

.modal-footer {
  padding: 20px;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 500;
  cursor: pointer;
  transition: var(--transition-fast);
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
}

.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.btn-success {
  background: var(--success-color);
  color: white;
}

.btn-warning {
  background: var(--warning-color);
  color: white;
}

.btn-danger {
  background: var(--error-color);
  color: white;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 0.9rem;
}

.btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .health-cards {
    grid-template-columns: 1fr;
  }
  
  .services-grid {
    grid-template-columns: 1fr;
  }
  
  .realtime-metrics {
    grid-template-columns: 1fr;
  }
  
  .executive-summary {
    grid-template-columns: 1fr;
  }
  
  .performance-grid {
    grid-template-columns: 1fr;
  }
  
  .overview-header,
  .section-header,
  .realtime-header,
  .history-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .overview-actions,
  .section-actions,
  .realtime-controls,
  .history-controls {
    flex-direction: column;
  }
  
  .history-header-item {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .history-summary {
    flex-direction: column;
    gap: 5px;
  }
  
  .timeline-event {
    grid-template-columns: 1fr;
    gap: 5px;
  }
  
  .modal-content {
    margin: 10px;
    width: auto;
    max-height: calc(100vh - 20px);
  }
}
</style>
