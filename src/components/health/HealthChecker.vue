<template>
  <div class="health-checker">
    <div class="checker-header">
      <h3>🏥 Health Check General</h3>
      <p>Verifica el estado general del sistema y todos sus componentes</p>
    </div>

    <!-- Control Panel -->
    <div class="checker-controls">
      <button 
        @click="performHealthCheck" 
        :disabled="isPerformingCheck"
        class="btn btn-primary"
      >
        <span v-if="isPerformingCheck">⏳ Verificando...</span>
        <span v-else>🔍 Ejecutar Health Check</span>
      </button>

      <button 
        v-if="healthResults"
        @click="refreshHealthCheck" 
        :disabled="isPerformingCheck"
        class="btn btn-secondary"
      >
        🔄 Actualizar
      </button>

      <button 
        v-if="healthResults"
        @click="clearResults" 
        class="btn btn-outline"
      >
        🗑️ Limpiar
      </button>
    </div>

    <!-- Health Status Overview -->
    <div v-if="healthResults" class="health-overview">
      <div class="status-header">
        <div class="main-status" :class="getMainStatusClass()">
          <div class="status-icon">{{ getStatusIcon() }}</div>
          <div class="status-content">
            <h4>Estado General del Sistema</h4>
            <div class="status-value">{{ getStatusText() }}</div>
            <div class="status-timestamp">
              Última verificación: {{ formatTimestamp(healthResults.timestamp) }}
            </div>
          </div>
        </div>
      </div>

      <div class="status-metrics">
        <div class="metric-item">
          <span class="metric-label">Ambiente:</span>
          <span class="metric-value">{{ healthResults.environment || 'Producción' }}</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">Uptime:</span>
          <span class="metric-value">{{ healthResults.uptime || 'N/A' }}</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">Versión:</span>
          <span class="metric-value">{{ healthResults.version || 'N/A' }}</span>
        </div>
      </div>
    </div>

    <!-- Services Health Grid -->
    <div v-if="healthResults?.services" class="services-health">
      <h4>🔧 Estado de Servicios</h4>
      <div class="services-grid">
        <div 
          v-for="(healthy, serviceName) in healthResults.services" 
          :key="serviceName"
          class="service-item"
          :class="{ 'healthy': healthy, 'unhealthy': !healthy }"
        >
          <div class="service-icon">
            <span v-if="healthy">✅</span>
            <span v-else>❌</span>
          </div>
          <div class="service-content">
            <h5>{{ formatServiceName(serviceName) }}</h5>
            <div class="service-status">
              <span class="status-indicator" :class="healthy ? 'status-healthy' : 'status-error'"></span>
              <span class="status-text">{{ healthy ? 'Operativo' : 'Con problemas' }}</span>
            </div>
          </div>
          <div v-if="getServiceDetails(serviceName)" class="service-details">
            <small>{{ getServiceDetails(serviceName) }}</small>
          </div>
        </div>
      </div>
    </div>

    <!-- Health Metrics -->
    <div v-if="healthResults" class="health-metrics">
      <div class="metrics-grid">
        <!-- Database Health -->
        <div v-if="healthResults.database" class="metric-card">
          <div class="metric-header">
            <h5>🗄️ Base de Datos</h5>
          </div>
          <div class="metric-content">
            <div class="metric-row">
              <span>Estado:</span>
              <span :class="getDatabaseStatusClass()">{{ getDatabaseStatusText() }}</span>
            </div>
            <div class="metric-row" v-if="healthResults.database.connections">
              <span>Conexiones:</span>
              <span>{{ healthResults.database.connections }}</span>
            </div>
            <div class="metric-row" v-if="healthResults.database.response_time">
              <span>Tiempo de respuesta:</span>
              <span>{{ healthResults.database.response_time }}ms</span>
            </div>
          </div>
        </div>

        <!-- API Health -->
        <div v-if="healthResults.api" class="metric-card">
          <div class="metric-header">
            <h5>🌐 API</h5>
          </div>
          <div class="metric-content">
            <div class="metric-row">
              <span>Estado:</span>
              <span :class="getApiStatusClass()">{{ getApiStatusText() }}</span>
            </div>
            <div class="metric-row" v-if="healthResults.api.requests_per_minute">
              <span>Requests/min:</span>
              <span>{{ healthResults.api.requests_per_minute }}</span>
            </div>
            <div class="metric-row" v-if="healthResults.api.average_response_time">
              <span>Tiempo promedio:</span>
              <span>{{ healthResults.api.average_response_time }}ms</span>
            </div>
          </div>
        </div>

        <!-- Memory Usage -->
        <div v-if="healthResults.memory" class="metric-card">
          <div class="metric-header">
            <h5>💾 Memoria</h5>
          </div>
          <div class="metric-content">
            <div class="metric-row">
              <span>Uso actual:</span>
              <span>{{ healthResults.memory.used }} / {{ healthResults.memory.total }}</span>
            </div>
            <div class="metric-row">
              <span>Porcentaje:</span>
              <div class="memory-bar">
                <div 
                  class="memory-fill" 
                  :style="{ width: getMemoryPercentage() + '%' }"
                ></div>
                <span class="memory-text">{{ getMemoryPercentage() }}%</span>
              </div>
            </div>
          </div>
        </div>

        <!-- External Services -->
        <div v-if="healthResults.external_services" class="metric-card">
          <div class="metric-header">
            <h5>🔗 Servicios Externos</h5>
          </div>
          <div class="metric-content">
            <div 
              v-for="(status, service) in healthResults.external_services" 
              :key="service"
              class="metric-row"
            >
              <span>{{ formatServiceName(service) }}:</span>
              <span :class="status ? 'status-healthy' : 'status-error'">
                {{ status ? 'Conectado' : 'Desconectado' }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Detailed JSON View -->
    <div v-if="healthResults && showRawData" class="raw-data-section">
      <h4>📋 Datos Completos del Health Check</h4>
      <pre class="json-container">{{ formatJSON(healthResults) }}</pre>
    </div>

    <!-- Toggle for Raw Data -->
    <div v-if="healthResults" class="data-controls">
      <button 
        @click="showRawData = !showRawData" 
        class="btn btn-small btn-outline"
      >
        {{ showRawData ? '📊 Ocultar JSON' : '🔍 Ver JSON Completo' }}
      </button>
    </div>

    <!-- Error Display -->
    <div v-if="errorMessage" class="health-error">
      <h4>❌ Error en Health Check</h4>
      <p>{{ errorMessage }}</p>
      <button @click="retryHealthCheck" class="btn btn-danger">
        🔄 Reintentar
      </button>
    </div>

    <!-- No Data State -->
    <div v-if="!healthResults && !isPerformingCheck && !errorMessage" class="no-data-state">
      <div class="no-data-icon">🏥</div>
      <h4>Health Check General</h4>
      <p>Ejecuta un health check para verificar el estado de todos los componentes del sistema</p>
      <button @click="performHealthCheck" class="btn btn-primary">
        🚀 Ejecutar Primer Health Check
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

const isPerformingCheck = ref(false)
const healthResults = ref(null)
const errorMessage = ref('')
const showRawData = ref(false)

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const systemStatus = computed(() => {
  return healthResults.value?.status || 'unknown'
})

const isHealthy = computed(() => {
  return systemStatus.value === 'healthy'
})

const hasWarnings = computed(() => {
  return systemStatus.value === 'partial' || systemStatus.value === 'degraded'
})

const hasErrors = computed(() => {
  return systemStatus.value === 'error' || systemStatus.value === 'unhealthy'
})

// ============================================================================
// FUNCIONES PRINCIPALES MIGRADAS DEL SCRIPT.JS
// ============================================================================

/**
 * Realiza un health check general - MIGRADO: performHealthCheck() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const performHealthCheck = async () => {
  isPerformingCheck.value = true
  healthResults.value = null
  errorMessage.value = ''
  
  try {
    appStore.addToLog('Performing general health check', 'info')
    showNotification('Ejecutando health check general...', 'info')
    
    // Llamada a la API - PRESERVAR ENDPOINT EXACTO
    const response = await apiRequest('/api/health')
    
    healthResults.value = {
      ...response,
      timestamp: response.timestamp || Date.now()
    }
    
    // Mostrar notificación basada en el estado - PRESERVAR: Misma lógica que script.js
    const status = response.status
    if (status === 'healthy') {
      showNotification('✅ Sistema saludable - Todos los componentes funcionando correctamente', 'success')
    } else if (status === 'partial' || status === 'degraded') {
      showNotification('⚠️ Sistema parcialmente operativo - Algunos componentes requieren atención', 'warning')
    } else {
      showNotification('❌ Sistema con problemas - Se detectaron errores críticos', 'error')
    }
    
    appStore.addToLog(`Health check completed - Status: ${status}`, 'info')
    
  } catch (error) {
    appStore.addToLog(`Health check failed: ${error.message}`, 'error')
    errorMessage.value = error.message
    showNotification(`Error en health check: ${error.message}`, 'error')
  } finally {
    isPerformingCheck.value = false
  }
}

/**
 * Actualizar health check
 */
const refreshHealthCheck = () => {
  appStore.addToLog('Refreshing health check', 'info')
  performHealthCheck()
}

/**
 * Reintentar health check en caso de error
 */
const retryHealthCheck = () => {
  errorMessage.value = ''
  performHealthCheck()
}

/**
 * Limpiar resultados
 */
const clearResults = () => {
  healthResults.value = null
  errorMessage.value = ''
  showRawData.value = false
  appStore.addToLog('Health check results cleared', 'info')
  showNotification('Resultados del health check limpiados', 'info')
}

// ============================================================================
// FUNCIONES DE UTILIDAD
// ============================================================================

const getMainStatusClass = () => {
  if (isHealthy.value) return 'status-healthy'
  if (hasWarnings.value) return 'status-warning'
  if (hasErrors.value) return 'status-error'
  return 'status-unknown'
}

const getStatusIcon = () => {
  if (isHealthy.value) return '✅'
  if (hasWarnings.value) return '⚠️'
  if (hasErrors.value) return '❌'
  return '❓'
}

const getStatusText = () => {
  const statusMap = {
    healthy: 'SISTEMA SALUDABLE',
    partial: 'PARCIALMENTE OPERATIVO',
    degraded: 'RENDIMIENTO DEGRADADO',
    error: 'ERRORES DETECTADOS',
    unhealthy: 'SISTEMA NO SALUDABLE'
  }
  return statusMap[systemStatus.value] || 'ESTADO DESCONOCIDO'
}

const formatServiceName = (serviceName) => {
  return serviceName
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase())
}

const getServiceDetails = (serviceName) => {
  const details = {
    database: 'Conexión a base de datos principal',
    cache: 'Sistema de cache Redis/Memcached',
    storage: 'Almacenamiento de archivos',
    api: 'API REST principal',
    auth: 'Servicio de autenticación',
    queue: 'Cola de procesamiento de trabajos'
  }
  return details[serviceName] || null
}

const getDatabaseStatusClass = () => {
  const dbStatus = healthResults.value?.database?.status
  if (dbStatus === 'connected' || dbStatus === 'healthy') return 'status-healthy'
  if (dbStatus === 'slow') return 'status-warning'
  return 'status-error'
}

const getDatabaseStatusText = () => {
  const dbStatus = healthResults.value?.database?.status || 'unknown'
  const statusMap = {
    connected: 'Conectada',
    healthy: 'Saludable',
    slow: 'Lenta',
    error: 'Error',
    disconnected: 'Desconectada'
  }
  return statusMap[dbStatus] || 'Desconocido'
}

const getApiStatusClass = () => {
  const apiStatus = healthResults.value?.api?.status
  if (apiStatus === 'operational' || apiStatus === 'healthy') return 'status-healthy'
  if (apiStatus === 'slow') return 'status-warning'
  return 'status-error'
}

const getApiStatusText = () => {
  const apiStatus = healthResults.value?.api?.status || 'unknown'
  const statusMap = {
    operational: 'Operacional',
    healthy: 'Saludable',
    slow: 'Lenta',
    error: 'Error',
    down: 'Inactiva'
  }
  return statusMap[apiStatus] || 'Desconocido'
}

const getMemoryPercentage = () => {
  const memory = healthResults.value?.memory
  if (!memory || !memory.used || !memory.total) return 0
  
  // Convertir a números si son strings
  const used = typeof memory.used === 'string' ? 
    parseFloat(memory.used.replace(/[^\d.]/g, '')) : memory.used
  const total = typeof memory.total === 'string' ? 
    parseFloat(memory.total.replace(/[^\d.]/g, '')) : memory.total
  
  return Math.round((used / total) * 100)
}

const formatTimestamp = (timestamp) => {
  return new Date(timestamp).toLocaleString()
}

const formatJSON = (obj) => {
  return JSON.stringify(obj, null, 2)
}

// ============================================================================
// LIFECYCLE HOOKS
// ============================================================================

onMounted(() => {
  appStore.addToLog('HealthChecker component mounted', 'info')
  
  // EXPONER FUNCIÓN GLOBAL PARA COMPATIBILIDAD
  window.performHealthCheck = performHealthCheck
})

onUnmounted(() => {
  // Limpiar función global
  if (typeof window !== 'undefined') {
    delete window.performHealthCheck
  }
  
  appStore.addToLog('HealthChecker component unmounted', 'info')
})
</script>

<style scoped>
.health-checker {
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  padding: 24px;
  border: 1px solid var(--border-color);
}

.checker-header {
  margin-bottom: 24px;
  text-align: center;
}

.checker-header h3 {
  color: var(--text-primary);
  margin-bottom: 8px;
  font-size: 1.5rem;
}

.checker-header p {
  color: var(--text-secondary);
  font-size: 0.95rem;
}

.checker-controls {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  justify-content: center;
  flex-wrap: wrap;
}

.health-overview {
  margin-bottom: 32px;
}

.status-header {
  margin-bottom: 20px;
}

.main-status {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 24px;
  border-radius: var(--radius-lg);
  border: 2px solid;
}

.main-status.status-healthy {
  background: var(--success-bg);
  border-color: var(--success-color);
}

.main-status.status-warning {
  background: var(--warning-bg);
  border-color: var(--warning-color);
}

.main-status.status-error {
  background: var(--error-bg);
  border-color: var(--error-color);
}

.main-status.status-unknown {
  background: var(--bg-secondary);
  border-color: var(--border-color);
}

.status-icon {
  font-size: 3rem;
  line-height: 1;
}

.status-content h4 {
  color: var(--text-primary);
  margin-bottom: 8px;
  font-size: 1.3rem;
}

.status-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.status-timestamp {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.status-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  padding: 20px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
}

.metric-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.metric-label {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.metric-value {
  color: var(--text-primary);
  font-weight: 600;
}

.services-health {
  margin-bottom: 32px;
}

.services-health h4 {
  color: var(--text-primary);
  margin-bottom: 20px;
  font-size: 1.2rem;
}

.services-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
}

.service-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-light);
  background: var(--bg-secondary);
}

.service-item.healthy {
  border-color: var(--success-color);
  background: var(--success-bg);
}

.service-item.unhealthy {
  border-color: var(--error-color);
  background: var(--error-bg);
}

.service-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.service-content {
  flex: 1;
}

.service-content h5 {
  color: var(--text-primary);
  margin-bottom: 4px;
  font-size: 1rem;
}

.service-status {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-healthy { background: var(--success-color); }
.status-warning { background: var(--warning-color); }
.status-error { background: var(--error-color); }

.status-text {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.service-details {
  font-size: 0.8rem;
  color: var(--text-muted);
  max-width: 120px;
}

.health-metrics {
  margin-bottom: 24px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
}

.metric-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.metric-header {
  padding: 16px 20px;
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-light);
}

.metric-header h5 {
  color: var(--text-primary);
  margin: 0;
  font-size: 1rem;
}

.metric-content {
  padding: 16px 20px;
}

.metric-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-size: 0.9rem;
}

.metric-row:last-child {
  margin-bottom: 0;
}

.metric-row span:first-child {
  color: var(--text-secondary);
}

.metric-row span:last-child {
  color: var(--text-primary);
  font-weight: 500;
}

.memory-bar {
  position: relative;
  width: 100px;
  height: 16px;
  background: var(--border-light);
  border-radius: 8px;
  overflow: hidden;
}

.memory-fill {
  height: 100%;
  background: linear-gradient(to right, var(--success-color), var(--warning-color), var(--error-color));
  transition: width 0.3s ease;
}

.memory-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 0.7rem;
  font-weight: 600;
  color: white;
  text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
}

.raw-data-section {
  margin-bottom: 20px;
}

.raw-data-section h4 {
  color: var(--text-primary);
  margin-bottom: 16px;
  font-size: 1.1rem;
}

.json-container {
  background: var(--bg-code);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  padding: 16px;
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 0.85rem;
  color: var(--text-code);
  overflow-x: auto;
  max-height: 400px;
  overflow-y: auto;
}

.data-controls {
  text-align: center;
  margin-bottom: 20px;
}

.health-error {
  text-align: center;
  padding: 32px;
  background: var(--error-bg);
  border: 1px solid var(--error-color);
  border-radius: var(--radius-md);
}

.health-error h4 {
  color: var(--error-color);
  margin-bottom: 12px;
}

.health-error p {
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
  padding: 10px 20px;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  display: inline-flex;
  align-items: center;
  gap: 8px;
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
