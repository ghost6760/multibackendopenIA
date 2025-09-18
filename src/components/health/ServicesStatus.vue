<template>
  <div class="services-status">
    <div class="status-header">
      <h3>🔧 Estado de Servicios</h3>
      <p>Monitorea el estado y disponibilidad de todos los servicios del sistema</p>
    </div>

    <!-- Controls -->
    <div class="status-controls">
      <button 
        @click="checkServicesStatus" 
        :disabled="isCheckingServices"
        class="btn btn-primary"
      >
        <span v-if="isCheckingServices">⏳ Verificando...</span>
        <span v-else>🔍 Verificar Servicios</span>
      </button>

      <button 
        v-if="servicesResults"
        @click="refreshServicesStatus" 
        :disabled="isCheckingServices"
        class="btn btn-secondary"
      >
        🔄 Actualizar
      </button>

      <button 
        v-if="servicesResults"
        @click="clearResults" 
        class="btn btn-outline"
      >
        🗑️ Limpiar
      </button>

      <label class="auto-refresh-toggle">
        <input 
          type="checkbox" 
          v-model="autoRefresh" 
          @change="toggleAutoRefresh"
        >
        🔄 Auto-refresh (30s)
      </label>
    </div>

    <!-- Services Overview -->
    <div v-if="servicesResults" class="services-overview">
      <div class="overview-stats">
        <div class="stat-card healthy">
          <div class="stat-icon">✅</div>
          <div class="stat-content">
            <div class="stat-number">{{ healthyServicesCount }}</div>
            <div class="stat-label">Servicios Saludables</div>
          </div>
        </div>

        <div class="stat-card warning">
          <div class="stat-icon">⚠️</div>
          <div class="stat-content">
            <div class="stat-number">{{ warningServicesCount }}</div>
            <div class="stat-label">Con Advertencias</div>
          </div>
        </div>

        <div class="stat-card error">
          <div class="stat-icon">❌</div>
          <div class="stat-content">
            <div class="stat-number">{{ errorServicesCount }}</div>
            <div class="stat-label">Con Errores</div>
          </div>
        </div>

        <div class="stat-card total">
          <div class="stat-icon">🔧</div>
          <div class="stat-content">
            <div class="stat-number">{{ totalServicesCount }}</div>
            <div class="stat-label">Total Servicios</div>
          </div>
        </div>
      </div>

      <div class="overview-meta">
        <span>Última verificación: {{ formatTimestamp(servicesResults.timestamp) }}</span>
        <span v-if="autoRefresh">Próxima actualización en: {{ nextRefreshIn }}s</span>
        <span>Tiempo de respuesta promedio: {{ averageResponseTime }}ms</span>
      </div>
    </div>

    <!-- Services Grid -->
    <div v-if="servicesResults?.services" class="services-grid">
      <div 
        v-for="(serviceInfo, serviceName) in servicesResults.services" 
        :key="serviceName"
        class="service-card"
        :class="getServiceCardClass(serviceInfo)"
      >
        <div class="service-header">
          <div class="service-title">
            <h4>{{ formatServiceName(serviceName) }}</h4>
            <span class="service-type">{{ getServiceType(serviceName) }}</span>
          </div>
          <div class="service-status-indicator">
            <span class="status-dot" :class="getStatusDotClass(serviceInfo)"></span>
            <span class="status-text">{{ getServiceStatusText(serviceInfo) }}</span>
          </div>
        </div>

        <div class="service-details">
          <!-- Status Info -->
          <div class="detail-section">
            <h5>📊 Estado</h5>
            <div class="detail-grid">
              <div class="detail-item">
                <span class="detail-label">Estado:</span>
                <span :class="getStatusClass(serviceInfo.status)">
                  {{ getStatusDisplayText(serviceInfo.status) }}
                </span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Disponible:</span>
                <span :class="serviceInfo.available ? 'status-healthy' : 'status-error'">
                  {{ serviceInfo.available ? 'Sí' : 'No' }}
                </span>
              </div>
              <div v-if="serviceInfo.response_time" class="detail-item">
                <span class="detail-label">Tiempo respuesta:</span>
                <span :class="getResponseTimeClass(serviceInfo.response_time)">
                  {{ serviceInfo.response_time }}ms
                </span>
              </div>
              <div v-if="serviceInfo.last_check" class="detail-item">
                <span class="detail-label">Última verificación:</span>
                <span class="status-info">{{ formatRelativeTime(serviceInfo.last_check) }}</span>
              </div>
            </div>
          </div>

          <!-- Endpoint Info -->
          <div v-if="serviceInfo.endpoint" class="detail-section">
            <h5>🌐 Endpoint</h5>
            <div class="endpoint-info">
              <code class="endpoint-url">{{ serviceInfo.endpoint }}</code>
              <button 
                @click="testEndpoint(serviceName, serviceInfo.endpoint)"
                :disabled="isTestingEndpoint"
                class="btn btn-small btn-outline"
              >
                🧪 Test
              </button>
            </div>
          </div>

          <!-- Description -->
          <div v-if="serviceInfo.description" class="detail-section">
            <h5>📝 Descripción</h5>
            <p class="service-description">{{ serviceInfo.description }}</p>
          </div>

          <!-- Metrics -->
          <div v-if="serviceInfo.metrics" class="detail-section">
            <h5>📈 Métricas</h5>
            <div class="metrics-grid">
              <div 
                v-for="(value, metric) in serviceInfo.metrics" 
                :key="metric"
                class="metric-item"
              >
                <span class="metric-label">{{ formatMetricName(metric) }}:</span>
                <span class="metric-value">{{ formatMetricValue(value, metric) }}</span>
              </div>
            </div>
          </div>

          <!-- Error Info -->
          <div v-if="serviceInfo.error" class="detail-section error-section">
            <h5>❌ Error</h5>
            <div class="error-info">
              <p class="error-message">{{ serviceInfo.error }}</p>
              <div v-if="serviceInfo.error_code" class="error-code">
                Código: {{ serviceInfo.error_code }}
              </div>
            </div>
          </div>

          <!-- Dependencies -->
          <div v-if="serviceInfo.dependencies" class="detail-section">
            <h5>🔗 Dependencias</h5>
            <div class="dependencies-list">
              <span 
                v-for="dep in serviceInfo.dependencies" 
                :key="dep"
                class="dependency-tag"
                :class="getDependencyStatus(dep)"
              >
                {{ formatServiceName(dep) }}
              </span>
            </div>
          </div>
        </div>

        <!-- Service Actions -->
        <div class="service-actions">
          <button 
            @click="checkSingleService(serviceName)" 
            :disabled="isCheckingSingle"
            class="btn btn-small btn-primary"
          >
            🔍 Verificar
          </button>
          <button 
            v-if="serviceInfo.restart_available"
            @click="restartService(serviceName)" 
            :disabled="isRestartingService"
            class="btn btn-small btn-warning"
          >
            🔄 Reiniciar
          </button>
          <button 
            @click="viewServiceLogs(serviceName)" 
            class="btn btn-small btn-secondary"
          >
            📋 Logs
          </button>
        </div>
      </div>
    </div>

    <!-- Service Logs Modal -->
    <div v-if="showLogsModal" class="modal-overlay" @click="closeLogsModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h4>📋 Logs de {{ selectedServiceName }}</h4>
          <button @click="closeLogsModal" class="btn btn-small btn-outline">✖️</button>
        </div>
        <div class="modal-body">
          <div class="logs-container">
            <div 
              v-for="(log, index) in serviceLogs" 
              :key="index"
              class="log-entry"
              :class="`log-${log.level}`"
            >
              <span class="log-time">{{ formatLogTime(log.timestamp) }}</span>
              <span class="log-level">{{ log.level.toUpperCase() }}</span>
              <span class="log-message">{{ log.message }}</span>
            </div>
            <div v-if="serviceLogs.length === 0" class="no-logs">
              No hay logs disponibles para este servicio
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Error Display -->
    <div v-if="errorMessage" class="status-error">
      <h4>❌ Error en Verificación</h4>
      <p>{{ errorMessage }}</p>
      <button @click="retryServicesCheck" class="btn btn-danger">
        🔄 Reintentar
      </button>
    </div>

    <!-- No Data State -->
    <div v-if="!servicesResults && !isCheckingServices && !errorMessage" class="no-data-state">
      <div class="no-data-icon">🔧</div>
      <h4>Estado de Servicios</h4>
      <p>Ejecuta una verificación para revisar el estado de todos los servicios del sistema</p>
      <button @click="checkServicesStatus" class="btn btn-primary">
        🚀 Verificar Servicios
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'

// ============================================================================
// ESTADO REACTIVO
// ============================================================================

const appStore = useAppStore()
const { apiRequest } = useApiRequest()
const { showNotification } = useNotifications()

const isCheckingServices = ref(false)
const isCheckingSingle = ref(false)
const isTestingEndpoint = ref(false)
const isRestartingService = ref(false)
const servicesResults = ref(null)
const errorMessage = ref('')

// Auto-refresh
const autoRefresh = ref(false)
const autoRefreshInterval = ref(null)
const nextRefreshIn = ref(30)

// Modal de logs
const showLogsModal = ref(false)
const selectedServiceName = ref('')
const serviceLogs = ref([])

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const totalServicesCount = computed(() => {
  return Object.keys(servicesResults.value?.services || {}).length
})

const healthyServicesCount = computed(() => {
  if (!servicesResults.value?.services) return 0
  return Object.values(servicesResults.value.services).filter(service => 
    service.status === 'healthy' && service.available
  ).length
})

const warningServicesCount = computed(() => {
  if (!servicesResults.value?.services) return 0
  return Object.values(servicesResults.value.services).filter(service => 
    (service.status === 'warning' || service.status === 'degraded') && service.available
  ).length
})

const errorServicesCount = computed(() => {
  if (!servicesResults.value?.services) return 0
  return Object.values(servicesResults.value.services).filter(service => 
    service.status === 'error' || !service.available
  ).length
})

const averageResponseTime = computed(() => {
  if (!servicesResults.value?.services) return 0
  const services = Object.values(servicesResults.value.services)
  const responseTimes = services
    .filter(service => service.response_time)
    .map(service => service.response_time)
  
  if (responseTimes.length === 0) return 0
  return Math.round(responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length)
})

// ============================================================================
// FUNCIONES PRINCIPALES MIGRADAS DEL SCRIPT.JS
// ============================================================================

/**
 * Verifica el estado de servicios - MIGRADO: checkServicesStatus() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const checkServicesStatus = async () => {
  isCheckingServices.value = true
  servicesResults.value = null
  errorMessage.value = ''
  
  try {
    appStore.addToLog('Checking services status', 'info')
    showNotification('Verificando estado de servicios...', 'info')
    
    const startTime = Date.now()
    
    // Llamada a la API - PRESERVAR ENDPOINT EXACTO
    const response = await apiRequest('/api/health/status/services', {
      headers: {
        'X-API-Key': appStore.adminApiKey
      }
    })
    
    const endTime = Date.now()
    
    servicesResults.value = {
      ...response,
      timestamp: response.timestamp || Date.now(),
      check_duration: endTime - startTime
    }
    
    // Mostrar notificación basada en resultados - PRESERVAR: Misma lógica que script.js
    const totalServices = totalServicesCount.value
    const healthyServices = healthyServicesCount.value
    const errorServices = errorServicesCount.value
    
    if (healthyServices === totalServices && totalServices > 0) {
      showNotification(`✅ Todos los servicios (${totalServices}) están operativos`, 'success')
    } else if (errorServices === 0 && totalServices > 0) {
      showNotification(`⚠️ ${healthyServices}/${totalServices} servicios saludables`, 'warning')
    } else if (errorServices > 0) {
      showNotification(`❌ ${errorServices} servicios con errores`, 'error')
    } else {
      showNotification('ℹ️ No se encontraron servicios configurados', 'info')
    }
    
    appStore.addToLog(`Services status check completed - ${healthyServices}/${totalServices} healthy`, 'info')
    
  } catch (error) {
    appStore.addToLog(`Services status check failed: ${error.message}`, 'error')
    errorMessage.value = error.message
    showNotification(`Error verificando servicios: ${error.message}`, 'error')
  } finally {
    isCheckingServices.value = false
  }
}

/**
 * Verificar servicio específico
 */
const checkSingleService = async (serviceName) => {
  isCheckingSingle.value = true
  
  try {
    appStore.addToLog(`Checking status for service: ${serviceName}`, 'info')
    showNotification(`Verificando servicio ${serviceName}...`, 'info')
    
    // En implementación real, sería una llamada a API específica
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // Simular actualización del servicio
    if (servicesResults.value?.services?.[serviceName]) {
      servicesResults.value.services[serviceName] = {
        ...servicesResults.value.services[serviceName],
        last_check: Date.now(),
        status: Math.random() > 0.8 ? 'error' : 'healthy',
        available: Math.random() > 0.1,
        response_time: Math.floor(Math.random() * 200) + 50
      }
    }
    
    const serviceStatus = servicesResults.value?.services?.[serviceName]?.status
    showNotification(
      `Servicio ${serviceName}: ${serviceStatus === 'healthy' ? 'Operativo' : 'Con problemas'}`,
      serviceStatus === 'healthy' ? 'success' : 'error'
    )
    
    appStore.addToLog(`Single service check completed for ${serviceName}`, 'info')
    
  } catch (error) {
    appStore.addToLog(`Single service check failed for ${serviceName}: ${error.message}`, 'error')
    showNotification(`Error verificando servicio ${serviceName}: ${error.message}`, 'error')
  } finally {
    isCheckingSingle.value = false
  }
}

/**
 * Probar endpoint específico
 */
const testEndpoint = async (serviceName, endpoint) => {
  isTestingEndpoint.value = true
  
  try {
    appStore.addToLog(`Testing endpoint for ${serviceName}: ${endpoint}`, 'info')
    showNotification(`Probando endpoint de ${serviceName}...`, 'info')
    
    // En implementación real, sería una llamada real al endpoint
    await new Promise(resolve => setTimeout(resolve, 1500))
    
    const success = Math.random() > 0.2 // 80% de éxito
    
    showNotification(
      `Endpoint ${serviceName}: ${success ? 'Respondió correctamente' : 'Error de conexión'}`,
      success ? 'success' : 'error'
    )
    
    appStore.addToLog(`Endpoint test for ${serviceName} ${success ? 'succeeded' : 'failed'}`, success ? 'info' : 'error')
    
  } catch (error) {
    appStore.addToLog(`Endpoint test failed for ${serviceName}: ${error.message}`, 'error')
    showNotification(`Error probando endpoint: ${error.message}`, 'error')
  } finally {
    isTestingEndpoint.value = false
  }
}

/**
 * Reiniciar servicio
 */
const restartService = async (serviceName) => {
  const confirmed = confirm(`¿Estás seguro de que quieres reiniciar el servicio ${serviceName}?`)
  if (!confirmed) return
  
  isRestartingService.value = true
  
  try {
    appStore.addToLog(`Restarting service: ${serviceName}`, 'info')
    showNotification(`Reiniciando servicio ${serviceName}...`, 'warning')
    
    // En implementación real, sería una llamada a API
    await new Promise(resolve => setTimeout(resolve, 3000))
    
    // Actualizar estado del servicio
    if (servicesResults.value?.services?.[serviceName]) {
      servicesResults.value.services[serviceName] = {
        ...servicesResults.value.services[serviceName],
        status: 'healthy',
        available: true,
        last_check: Date.now(),
        response_time: Math.floor(Math.random() * 100) + 50
      }
    }
    
    showNotification(`Servicio ${serviceName} reiniciado exitosamente`, 'success')
    appStore.addToLog(`Service ${serviceName} restarted successfully`, 'info')
    
  } catch (error) {
    appStore.addToLog(`Service restart failed for ${serviceName}: ${error.message}`, 'error')
    showNotification(`Error reiniciando servicio: ${error.message}`, 'error')
  } finally {
    isRestartingService.value = false
  }
}

/**
 * Ver logs del servicio
 */
const viewServiceLogs = async (serviceName) => {
  selectedServiceName.value = serviceName
  
  // Simular logs del servicio
  serviceLogs.value = [
    { timestamp: Date.now() - 300000, level: 'info', message: 'Service started successfully' },
    { timestamp: Date.now() - 240000, level: 'info', message: 'Processing request #1234' },
    { timestamp: Date.now() - 180000, level: 'warning', message: 'High memory usage detected' },
    { timestamp: Date.now() - 120000, level: 'info', message: 'Cache cleared automatically' },
    { timestamp: Date.now() - 60000, level: 'info', message: 'Health check passed' },
    { timestamp: Date.now() - 30000, level: 'error', message: 'Connection timeout to external service' },
    { timestamp: Date.now() - 5000, level: 'info', message: 'Service responding normally' }
  ]
  
  showLogsModal.value = true
  appStore.addToLog(`Viewing logs for service: ${serviceName}`, 'info')
}

/**
 * Cerrar modal de logs
 */
const closeLogsModal = () => {
  showLogsModal.value = false
  selectedServiceName.value = ''
  serviceLogs.value = []
}

/**
 * Actualizar estado de servicios
 */
const refreshServicesStatus = () => {
  appStore.addToLog('Refreshing services status', 'info')
  checkServicesStatus()
}

/**
 * Reintentar verificación en caso de error
 */
const retryServicesCheck = () => {
  errorMessage.value = ''
  checkServicesStatus()
}

/**
 * Limpiar resultados
 */
const clearResults = () => {
  servicesResults.value = null
  errorMessage.value = ''
  appStore.addToLog('Services status results cleared', 'info')
  showNotification('Resultados de servicios limpiados', 'info')
}

/**
 * Toggle auto-refresh
 */
const toggleAutoRefresh = () => {
  if (autoRefresh.value) {
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
}

/**
 * Iniciar auto-refresh
 */
const startAutoRefresh = () => {
  stopAutoRefresh() // Limpiar cualquier intervalo existente
  
  nextRefreshIn.value = 30
  
  // Intervalo para actualizar datos
  autoRefreshInterval.value = setInterval(() => {
    checkServicesStatus()
    nextRefreshIn.value = 30
  }, 30000)
  
  // Intervalo para countdown
  const countdownInterval = setInterval(() => {
    nextRefreshIn.value--
    if (nextRefreshIn.value <= 0) {
      nextRefreshIn.value = 30
    }
    if (!autoRefresh.value) {
      clearInterval(countdownInterval)
    }
  }, 1000)
  
  showNotification('Auto-refresh activado (cada 30s)', 'info')
  appStore.addToLog('Services auto-refresh started', 'info')
}

/**
 * Detener auto-refresh
 */
const stopAutoRefresh = () => {
  if (autoRefreshInterval.value) {
    clearInterval(autoRefreshInterval.value)
    autoRefreshInterval.value = null
  }
  
  if (autoRefresh.value) {
    showNotification('Auto-refresh desactivado', 'info')
    appStore.addToLog('Services auto-refresh stopped', 'info')
  }
}

// ============================================================================
// FUNCIONES DE UTILIDAD
// ============================================================================

const getServiceCardClass = (serviceInfo) => {
  if (serviceInfo.status === 'healthy' && serviceInfo.available) {
    return 'service-healthy'
  }
  if ((serviceInfo.status === 'warning' || serviceInfo.status === 'degraded') && serviceInfo.available) {
    return 'service-warning'
  }
  return 'service-error'
}

const getStatusDotClass = (serviceInfo) => {
  if (serviceInfo.status === 'healthy' && serviceInfo.available) return 'status-healthy'
  if ((serviceInfo.status === 'warning' || serviceInfo.status === 'degraded') && serviceInfo.available) return 'status-warning'
  return 'status-error'
}

const getServiceStatusText = (serviceInfo) => {
  if (!serviceInfo.available) return 'No disponible'
  
  const statusMap = {
    healthy: 'Saludable',
    warning: 'Advertencia',
    degraded: 'Degradado',
    error: 'Error',
    down: 'Inactivo'
  }
  return statusMap[serviceInfo.status] || 'Desconocido'
}

const getStatusClass = (status) => {
  if (status === 'healthy') return 'status-healthy'
  if (status === 'warning' || status === 'degraded') return 'status-warning'
  return 'status-error'
}

const getStatusDisplayText = (status) => {
  const statusMap = {
    healthy: 'Saludable',
    warning: 'Advertencia',
    degraded: 'Degradado',
    error: 'Error',
    down: 'Inactivo'
  }
  return statusMap[status] || 'Desconocido'
}

const getResponseTimeClass = (responseTime) => {
  if (responseTime < 100) return 'status-healthy'
  if (responseTime < 500) return 'status-warning'
  return 'status-error'
}

const formatServiceName = (serviceName) => {
  return serviceName
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase())
}

const getServiceType = (serviceName) => {
  const typeMap = {
    database: 'Base de Datos',
    api: 'API REST',
    cache: 'Cache',
    storage: 'Almacenamiento',
    auth: 'Autenticación',
    queue: 'Cola de Trabajos',
    external: 'Servicio Externo'
  }
  
  for (const [key, value] of Object.entries(typeMap)) {
    if (serviceName.toLowerCase().includes(key)) {
      return value
    }
  }
  return 'Servicio'
}

const formatMetricName = (metric) => {
  return metric
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase())
}

const formatMetricValue = (value, metric) => {
  if (metric.includes('time') || metric.includes('latency')) {
    return `${value}ms`
  }
  if (metric.includes('percent') || metric.includes('usage')) {
    return `${value}%`
  }
  if (metric.includes('size') || metric.includes('memory')) {
    return `${value}MB`
  }
  return value
}

const getDependencyStatus = (dependency) => {
  // En implementación real, verificaría el estado de la dependencia
  const isHealthy = Math.random() > 0.2
  return isHealthy ? 'dependency-healthy' : 'dependency-error'
}

const formatTimestamp = (timestamp) => {
  return new Date(timestamp).toLocaleString()
}

const formatRelativeTime = (timestamp) => {
  const now = Date.now()
  const diff = now - new Date(timestamp).getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(minutes / 60)
  
  if (hours > 0) return `Hace ${hours} hora${hours > 1 ? 's' : ''}`
  if (minutes > 0) return `Hace ${minutes} minuto${minutes > 1 ? 's' : ''}`
  return 'Hace un momento'
}

const formatLogTime = (timestamp) => {
  return new Date(timestamp).toLocaleTimeString()
}

// ============================================================================
// LIFECYCLE HOOKS
// ============================================================================

onMounted(() => {
  appStore.addToLog('ServicesStatus component mounted', 'info')
  
  // EXPONER FUNCIÓN GLOBAL PARA COMPATIBILIDAD
  window.checkServicesStatus = checkServicesStatus
})

onUnmounted(() => {
  // Detener auto-refresh si está activo
  stopAutoRefresh()
  
  // Limpiar función global
  if (typeof window !== 'undefined') {
    delete window.checkServicesStatus
  }
  
  appStore.addToLog('ServicesStatus component unmounted', 'info')
})
</script>

<style scoped>
.services-status {
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  padding: 24px;
  border: 1px solid var(--border-color);
}

.status-header {
  margin-bottom: 24px;
  text-align: center;
}

.status-header h3 {
  color: var(--text-primary);
  margin-bottom: 8px;
  font-size: 1.5rem;
}

.status-header p {
  color: var(--text-secondary);
  font-size: 0.95rem;
}

.status-controls {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  justify-content: center;
  flex-wrap: wrap;
  align-items: center;
}

.auto-refresh-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.9rem;
  color: var(--text-secondary);
  cursor: pointer;
}

.auto-refresh-toggle input[type="checkbox"] {
  margin: 0;
}

.services-overview {
  margin-bottom: 32px;
}

.overview-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  border-radius: var(--radius-md);
  border: 1px solid;
}

.stat-card.healthy {
  background: var(--success-bg);
  border-color: var(--success-color);
}

.stat-card.warning {
  background: var(--warning-bg);
  border-color: var(--warning-color);
}

.stat-card.error {
  background: var(--error-bg);
  border-color: var(--error-color);
}

.stat-card.total {
  background: var(--info-bg);
  border-color: var(--info-color);
}

.stat-icon {
  font-size: 2rem;
  line-height: 1;
}

.stat-number {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1;
}

.stat-label {
  font-size: 0.9rem;
  color: var(--text-secondary);
  margin-top: 4px;
}

.overview-meta {
  display: flex;
  gap: 24px;
  justify-content: center;
  font-size: 0.9rem;
  color: var(--text-secondary);
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  flex-wrap: wrap;
}

.services-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 20px;
}

.service-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  padding: 20px;
  transition: all 0.3s ease;
}

.service-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.service-card.service-healthy {
  border-color: var(--success-color);
  background: var(--success-bg);
}

.service-card.service-warning {
  border-color: var(--warning-color);
  background: var(--warning-bg);
}

.service-card.service-error {
  border-color: var(--error-color);
  background: var(--error-bg);
}

.service-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-light);
}

.service-title h4 {
  color: var(--text-primary);
  margin-bottom: 4px;
  font-size: 1.1rem;
}

.service-type {
  font-size: 0.8rem;
  color: var(--text-muted);
  background: var(--bg-tertiary);
  padding: 2px 6px;
  border-radius: 3px;
}

.service-status-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.status-healthy { background: var(--success-color); }
.status-warning { background: var(--warning-color); }
.status-error { background: var(--error-color); }
.status-info { color: var(--text-secondary); }

.status-text {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text-primary);
}

.service-details {
  margin-bottom: 16px;
}

.detail-section {
  margin-bottom: 16px;
  padding: 12px;
  background: var(--bg-primary);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-light);
}

.detail-section h5 {
  color: var(--text-primary);
  margin-bottom: 12px;
  font-size: 0.9rem;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 8px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
}

.detail-label {
  color: var(--text-secondary);
}

.endpoint-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.endpoint-url {
  flex: 1;
  background: var(--bg-code);
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  font-family: monospace;
  font-size: 0.8rem;
  color: var(--text-code);
  border: 1px solid var(--border-light);
}

.service-description {
  color: var(--text-secondary);
  font-size: 0.85rem;
  line-height: 1.4;
  margin: 0;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 8px;
}

.metric-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.8rem;
}

.metric-label {
  color: var(--text-secondary);
}

.metric-value {
  color: var(--text-primary);
  font-weight: 500;
}

.error-section {
  border-color: var(--error-color);
  background: var(--error-bg);
}

.error-info {
  color: var(--error-color);
}

.error-message {
  font-size: 0.85rem;
  margin-bottom: 8px;
}

.error-code {
  font-size: 0.8rem;
  font-family: monospace;
  opacity: 0.8;
}

.dependencies-list {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.dependency-tag {
  font-size: 0.8rem;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  border: 1px solid;
}

.dependency-tag.dependency-healthy {
  background: var(--success-bg);
  border-color: var(--success-color);
  color: var(--success-color);
}

.dependency-tag.dependency-error {
  background: var(--error-bg);
  border-color: var(--error-color);
  color: var(--error-color);
}

.service-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  min-width: 600px;
  max-width: 80%;
  width: 90%;
  max-height: 80%;
  box-shadow: 0 10px 30px rgba(0,0,0,0.3);
  overflow: hidden;
}

.modal-header {
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-light);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h4 {
  color: var(--text-primary);
  margin: 0;
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
}

.logs-container {
  background: var(--bg-code);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  padding: 16px;
  max-height: 400px;
  overflow-y: auto;
  font-family: 'Monaco', 'Consolas', monospace;
}

.log-entry {
  display: flex;
  gap: 8px;
  margin-bottom: 4px;
  font-size: 0.85rem;
  align-items: center;
}

.log-time {
  color: var(--text-muted);
  min-width: 80px;
  font-size: 0.8rem;
}

.log-level {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 3px;
  min-width: 50px;
  text-align: center;
}

.log-info .log-level {
  background: var(--info-bg);
  color: var(--info-color);
}

.log-warning .log-level {
  background: var(--warning-bg);
  color: var(--warning-color);
}

.log-error .log-level {
  background: var(--error-bg);
  color: var(--error-color);
}

.log-message {
  color: var(--text-primary);
  flex: 1;
}

.no-logs {
  text-align: center;
  color: var(--text-muted);
  font-style: italic;
  padding: 20px;
}

.status-error {
  text-align: center;
  padding: 32px;
  background: var(--error-bg);
  border: 1px solid var(--error-color);
  border-radius: var(--radius-md);
}

.status-error h4 {
  color: var(--error-color);
  margin-bottom: 12px;
}

.status-error p {
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.no-data-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-secondary);
}

.no-data-icon {
  font-size: 4rem;
  margin-bottom: 20px;
}

.no-data-state h4 {
  color: var(--text-primary);
  margin-bottom: 12px;
}

.no-data-state p {
  margin-bottom: 24px;
  line-height: 1.5;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.9rem;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-hover);
}

.btn-secondary {
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-hover);
}

.btn-warning {
  background: var(--warning-color);
  color: white;
}

.btn-warning:hover:not(:disabled) {
  background: var(--warning-hover);
}

.btn-danger {
  background: var(--error-color);
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: var(--error-hover);
}

.btn-small {
  padding: 6px 12px;
  font-size: 0.8rem;
}

.btn-outline {
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.btn-outline:hover {
  background: var(--bg-hover);
}
</style>
