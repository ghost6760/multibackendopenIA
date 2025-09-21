<template>
  <div class="realtime-monitoring">
    <div class="monitoring-header">
      <h3>📊 Monitoreo en Tiempo Real</h3>
      <p>Supervisa el estado del sistema y métricas en tiempo real</p>
    </div>

    <!-- Control Panel -->
    <div class="monitoring-controls">
      <button 
        @click="toggleRealTimeMonitoring" 
        :class="isMonitoring ? 'btn btn-danger' : 'btn btn-success'"
      >
        <span v-if="isMonitoring">⏹️ Detener Monitoreo</span>
        <span v-else>▶️ Iniciar Monitoreo</span>
      </button>

      <button 
        @click="runAutoDiagnostics" 
        :disabled="isRunningDiagnostics"
        class="btn btn-primary"
      >
        <span v-if="isRunningDiagnostics">⏳ Ejecutando...</span>
        <span v-else>🚀 Auto-Diagnósticos</span>
      </button>

      <button 
        @click="refreshMonitoringData" 
        :disabled="isRefreshing"
        class="btn btn-secondary"
      >
        <span v-if="isRefreshing">🔄 Actualizando...</span>
        <span v-else>🔄 Actualizar</span>
      </button>
    </div>

    <!-- Status Indicator -->
    <div v-if="isMonitoring" class="monitoring-status">
      <div class="status-indicator status-active"></div>
      <span>Monitoreo activo - Próxima actualización en {{ nextUpdateCountdown }}s</span>
    </div>

    <!-- Real-time Metrics -->
    <div class="metrics-grid">
      <!-- System Performance -->
      <div class="metric-card">
        <div class="metric-header">
          <h4>💻 Rendimiento del Sistema</h4>
        </div>
        <div class="metric-content">
          <div class="metric-item">
            <span class="metric-label">Uso de Memoria:</span>
            <div class="metric-bar">
              <div 
                class="metric-fill memory" 
                :style="{ width: memoryUsagePercent + '%' }"
              ></div>
              <span class="metric-value">{{ memoryUsagePercent }}%</span>
            </div>
          </div>
          <div class="metric-item">
            <span class="metric-label">Uso de CPU:</span>
            <div class="metric-bar">
              <div 
                class="metric-fill cpu" 
                :style="{ width: cpuUsagePercent + '%' }"
              ></div>
              <span class="metric-value">{{ cpuUsagePercent }}%</span>
            </div>
          </div>
          <div class="metric-item">
            <span class="metric-label">Requests Activos:</span>
            <span class="metric-number">{{ activeRequests }}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">Errores/min:</span>
            <span class="metric-number error-count">{{ errorsPerMinute }}</span>
          </div>
        </div>
      </div>

      <!-- System Health -->
      <div class="metric-card">
        <div class="metric-header">
          <h4>🏥 Estado del Sistema</h4>
        </div>
        <div class="metric-content">
          <div class="health-status-grid">
            <div 
              v-for="(status, service) in systemHealth" 
              :key="service"
              class="health-status-item"
              :class="getHealthStatusClass(status)"
            >
              <span class="status-dot" :class="getStatusDotClass(status)"></span>
              <span class="service-name">{{ formatServiceName(service) }}</span>
              <span class="status-text">{{ getStatusText(status) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Activity Log -->
      <div class="metric-card log-card">
        <div class="metric-header">
          <h4>📋 Log en Tiempo Real</h4>
          <button @click="clearRealTimeLog" class="btn btn-small btn-outline">
            🗑️ Limpiar
          </button>
        </div>
        <div class="metric-content">
          <div ref="logContainer" class="realtime-log">
            <div 
              v-for="entry in recentLogEntries" 
              :key="entry.timestamp"
              class="log-entry"
              :class="`log-${entry.level}`"
            >
              <span class="log-time">{{ formatLogTime(entry.timestamp) }}</span>
              <span class="log-level">{{ entry.level.toUpperCase() }}</span>
              <span class="log-message">{{ entry.message }}</span>
            </div>
            <div v-if="recentLogEntries.length === 0" class="log-empty">
              No hay entradas de log recientes
            </div>
          </div>
        </div>
      </div>

      <!-- Auto-Diagnostics Results -->
      <div v-if="autoDiagnosticsResults" class="metric-card diagnostics-card">
        <div class="metric-header">
          <h4>🔍 Resultados Auto-Diagnósticos</h4>
        </div>
        <div class="metric-content">
          <div class="diagnostics-summary">
            <div class="summary-item">
              <span class="summary-label">Última ejecución:</span>
              <span class="summary-value">{{ formatTimestamp(autoDiagnosticsResults.timestamp) }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">Score de salud:</span>
              <span 
                class="summary-value health-score"
                :class="getHealthScoreClass(autoDiagnosticsResults.health_score)"
              >
                {{ autoDiagnosticsResults.health_score?.toFixed(1) || 'N/A' }}%
              </span>
            </div>
            <div class="summary-item">
              <span class="summary-label">Servicios verificados:</span>
              <span class="summary-value">{{ getServicesCheckedCount() }}</span>
            </div>
          </div>

          <!-- Quick Health Indicators -->
          <div class="quick-health">
            <div 
              v-for="(healthy, service) in getQuickHealthStatus()" 
              :key="service"
              class="quick-health-item"
              :class="{ 'healthy': healthy, 'unhealthy': !healthy }"
            >
              <span class="health-dot" :class="healthy ? 'healthy' : 'unhealthy'"></span>
              <span class="service-label">{{ formatServiceName(service) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Error Display -->
    <div v-if="errorMessage" class="monitoring-error">
      <h4>❌ Error en Monitoreo</h4>
      <p>{{ errorMessage }}</p>
      <button @click="clearError" class="btn btn-danger">
        ✖️ Cerrar
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'

// ============================================================================
// ESTADO REACTIVO
// ============================================================================

const appStore = useAppStore()
const { apiRequest } = useApiRequest()
const { showNotification } = useNotifications()

// Monitoreo en tiempo real
const isMonitoring = ref(false)
const monitoringInterval = ref(null)
const countdownInterval = ref(null)
const nextUpdateCountdown = ref(5)
const isRefreshing = ref(false)

// Métricas del sistema
const memoryUsagePercent = ref(35)
const cpuUsagePercent = ref(25)
const activeRequests = ref(12)
const errorsPerMinute = ref(0)

// Estado del sistema
const systemHealth = ref({
  database: 'healthy',
  api: 'healthy',
  cache: 'healthy',
  storage: 'warning',
  external_services: 'healthy'
})

// Log en tiempo real
const recentLogEntries = ref([])
const logContainer = ref(null)

// Auto-diagnósticos
const isRunningDiagnostics = ref(false)
const autoDiagnosticsResults = ref(null)

// Errores
const errorMessage = ref('')

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const healthyServicesCount = computed(() => {
  return Object.values(systemHealth.value).filter(status => status === 'healthy').length
})

const totalServicesCount = computed(() => {
  return Object.keys(systemHealth.value).length
})

// ============================================================================
// FUNCIONES PRINCIPALES MIGRADAS DEL SCRIPT.JS
// ============================================================================

/**
 * Inicia monitoreo en tiempo real - MIGRADO: startRealTimeMonitoring() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const startRealTimeMonitoring = () => {
  if (isMonitoring.value) return
  
  appStore.addToLog('Starting real-time monitoring', 'info')
  isMonitoring.value = true
  nextUpdateCountdown.value = 5
  
  // Actualizar datos inmediatamente
  updateMonitoringData()
  
  // Configurar intervalos - PRESERVAR: Mismo intervalo que script.js (30 segundos)
  monitoringInterval.value = setInterval(updateMonitoringData, 30000)
  
  countdownInterval.value = setInterval(() => {
    nextUpdateCountdown.value--
    if (nextUpdateCountdown.value <= 0) {
      nextUpdateCountdown.value = 30 // Reset to 30 seconds
    }
  }, 1000)
  
  showNotification('Monitoreo en tiempo real iniciado', 'success')
}

/**
 * Detiene monitoreo en tiempo real - MIGRADO: stopRealTimeMonitoring() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const stopRealTimeMonitoring = () => {
  if (!isMonitoring.value) return
  
  appStore.addToLog('Stopping real-time monitoring', 'info')
  isMonitoring.value = false
  
  // Limpiar intervalos
  if (monitoringInterval.value) {
    clearInterval(monitoringInterval.value)
    monitoringInterval.value = null
  }
  
  if (countdownInterval.value) {
    clearInterval(countdownInterval.value)
    countdownInterval.value = null
  }
  
  showNotification('Monitoreo en tiempo real detenido', 'info')
}

/**
 * Toggle monitoreo en tiempo real
 */
const toggleRealTimeMonitoring = () => {
  if (isMonitoring.value) {
    stopRealTimeMonitoring()
  } else {
    startRealTimeMonitoring()
  }
}

/**
 * Ejecuta diagnósticos automáticos - MIGRADO: runAutoDiagnostics() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const runAutoDiagnostics = async () => {
  isRunningDiagnostics.value = true
  errorMessage.value = ''
  
  try {
    appStore.addToLog('Running auto-diagnostics', 'info')
    showNotification('Ejecutando auto-diagnósticos...', 'info')
    
    // Ejecutar múltiples diagnósticos en paralelo - PRESERVAR: Misma lógica que script.js
    const [healthResponse, companiesResponse, servicesResponse] = await Promise.all([
      apiRequest('/api/health').catch(e => ({ error: e.message })),
      apiRequest('/api/health/companies').catch(e => ({ error: e.message })),
      apiRequest('/api/health/status/services').catch(e => ({ error: e.message }))
    ])
    
    // Procesar resultados - PRESERVAR: Misma estructura que script.js
    const diagnosticsData = {
      timestamp: Date.now(),
      health_general: healthResponse,
      companies_health: companiesResponse,
      services_status: servicesResponse
    }
    
    // Calcular score de salud
    let healthyCount = 0
    let totalCount = 0
    
    if (healthResponse && !healthResponse.error) {
      healthyCount += healthResponse.status === 'healthy' ? 1 : 0
      totalCount += 1
    }
    
    if (companiesResponse && !companiesResponse.error) {
      healthyCount += 1
      totalCount += 1
    }
    
    if (servicesResponse && !servicesResponse.error) {
      healthyCount += 1
      totalCount += 1
    }
    
    diagnosticsData.health_score = totalCount > 0 ? (healthyCount / totalCount) * 100 : 0
    
    autoDiagnosticsResults.value = diagnosticsData
    
    appStore.addToLog('Auto-diagnostics completed successfully', 'info')
    showNotification('Auto-diagnósticos completados', 'success')
    
  } catch (error) {
    appStore.addToLog(`Auto-diagnostics failed: ${error.message}`, 'error')
    errorMessage.value = error.message
    showNotification(`Error en auto-diagnósticos: ${error.message}`, 'error')
  } finally {
    isRunningDiagnostics.value = false
  }
}

/**
 * Actualiza datos de monitoreo - MIGRADO de script.js
 * PRESERVAR: Comportamiento de actualización automática
 */
const updateMonitoringData = async () => {
  try {
    // Simular actualización de métricas - En implementación real, estos datos vendrían de APIs
    memoryUsagePercent.value = Math.floor(Math.random() * 40) + 30 // 30-70%
    cpuUsagePercent.value = Math.floor(Math.random() * 50) + 10    // 10-60%
    activeRequests.value = Math.floor(Math.random() * 20) + 5      // 5-25
    errorsPerMinute.value = Math.floor(Math.random() * 5)          // 0-5
    
    // Actualizar estado de servicios aleatoriamente
    const services = Object.keys(systemHealth.value)
    services.forEach(service => {
      const random = Math.random()
      if (random > 0.9) {
        systemHealth.value[service] = 'error'
      } else if (random > 0.8) {
        systemHealth.value[service] = 'warning'
      } else {
        systemHealth.value[service] = 'healthy'
      }
    })
    
    // Agregar entradas al log en tiempo real - PRESERVAR: Mismos tipos de mensajes que script.js
    const logMessages = [
      'Request processed successfully',
      'Cache hit for key: user_data_123',
      'Database connection pool: 15/20 active',
      'Background task completed',
      'Health check passed',
      'Company configuration reloaded',
      'Document indexed successfully'
    ]
    
    if (Math.random() > 0.7) { // 30% de probabilidad de nueva entrada
      const newEntry = {
        timestamp: Date.now(),
        level: Math.random() > 0.9 ? 'error' : Math.random() > 0.8 ? 'warning' : 'info',
        message: logMessages[Math.floor(Math.random() * logMessages.length)]
      }
      
      recentLogEntries.value.push(newEntry)
      
      // Mantener solo las últimas 50 entradas
      if (recentLogEntries.value.length > 50) {
        recentLogEntries.value.shift()
      }
      
      // Auto-scroll del log
      await nextTick()
      if (logContainer.value) {
        logContainer.value.scrollTop = logContainer.value.scrollHeight
      }
    }
    
  } catch (error) {
    console.warn('Error updating monitoring data:', error)
    appStore.addToLog(`Monitoring update error: ${error.message}`, 'warning')
  }
}

/**
 * Refrescar datos de monitoreo manualmente
 */
const refreshMonitoringData = async () => {
  isRefreshing.value = true
  
  try {
    await updateMonitoringData()
    showNotification('Datos de monitoreo actualizados', 'success')
  } catch (error) {
    showNotification(`Error actualizando datos: ${error.message}`, 'error')
  } finally {
    isRefreshing.value = false
  }
}

/**
 * Limpiar log en tiempo real
 */
const clearRealTimeLog = () => {
  recentLogEntries.value = []
  appStore.addToLog('Real-time log cleared', 'info')
  showNotification('Log en tiempo real limpiado', 'info')
}

/**
 * Limpiar mensaje de error
 */
const clearError = () => {
  errorMessage.value = ''
}

// ============================================================================
// FUNCIONES DE UTILIDAD
// ============================================================================

const formatTimestamp = (timestamp) => {
  return new Date(timestamp).toLocaleString()
}

const formatLogTime = (timestamp) => {
  return new Date(timestamp).toLocaleTimeString()
}

const formatServiceName = (service) => {
  return service
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase())
}

const getHealthStatusClass = (status) => {
  return `health-status-${status}`
}

const getStatusDotClass = (status) => {
  return `status-${status}`
}

const getStatusText = (status) => {
  const statusMap = {
    healthy: 'Saludable',
    warning: 'Advertencia',
    error: 'Error'
  }
  return statusMap[status] || 'Desconocido'
}

const getHealthScoreClass = (score) => {
  if (!score) return 'unknown'
  if (score >= 90) return 'excellent'
  if (score >= 70) return 'good'
  if (score >= 50) return 'warning'
  return 'critical'
}

const getServicesCheckedCount = () => {
  if (!autoDiagnosticsResults.value) return 0
  
  let count = 0
  if (autoDiagnosticsResults.value.health_general && !autoDiagnosticsResults.value.health_general.error) count++
  if (autoDiagnosticsResults.value.companies_health && !autoDiagnosticsResults.value.companies_health.error) count++
  if (autoDiagnosticsResults.value.services_status && !autoDiagnosticsResults.value.services_status.error) count++
  
  return count
}

const getQuickHealthStatus = () => {
  if (!autoDiagnosticsResults.value) return {}
  
  const status = {}
  
  if (autoDiagnosticsResults.value.health_general) {
    status.sistema = !autoDiagnosticsResults.value.health_general.error && 
                     autoDiagnosticsResults.value.health_general.status === 'healthy'
  }
  
  if (autoDiagnosticsResults.value.companies_health) {
    status.empresas = !autoDiagnosticsResults.value.companies_health.error
  }
  
  if (autoDiagnosticsResults.value.services_status) {
    status.servicios = !autoDiagnosticsResults.value.services_status.error
  }
  
  return status
}

// ============================================================================
// LIFECYCLE HOOKS
// ============================================================================

onMounted(() => {
  appStore.addToLog('RealTimeMonitoring component mounted', 'info')
  
  // Cargar datos iniciales
  updateMonitoringData()
  
  // EXPONER FUNCIONES GLOBALES PARA COMPATIBILIDAD - PRESERVAR: Mismos nombres que script.js
  window.startRealTimeMonitoring = startRealTimeMonitoring
  window.stopRealTimeMonitoring = stopRealTimeMonitoring
  window.runAutoDiagnostics = runAutoDiagnostics
})

onUnmounted(() => {
  // Detener monitoreo si está activo
  stopRealTimeMonitoring()
  
  // Limpiar funciones globales
  if (typeof window !== 'undefined') {
    delete window.startRealTimeMonitoring
    delete window.stopRealTimeMonitoring
    delete window.runAutoDiagnostics
  }
  
  appStore.addToLog('RealTimeMonitoring component unmounted', 'info')
})
</script>

<style scoped>
.realtime-monitoring {
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  padding: 24px;
  border: 1px solid var(--border-color);
}

.monitoring-header {
  margin-bottom: 24px;
  text-align: center;
}

.monitoring-header h3 {
  color: var(--text-primary);
  margin-bottom: 8px;
  font-size: 1.5rem;
}

.monitoring-header p {
  color: var(--text-secondary);
  font-size: 0.95rem;
}

.monitoring-controls {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  justify-content: center;
  flex-wrap: wrap;
}

.monitoring-status {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
  margin-bottom: 24px;
  padding: 12px;
  background: var(--success-bg);
  border: 1px solid var(--success-color);
  border-radius: var(--radius-md);
  color: var(--success-color);
  font-weight: 500;
}

.status-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.status-active {
  background: var(--success-color);
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
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
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.metric-header h4 {
  color: var(--text-primary);
  margin: 0;
  font-size: 1.1rem;
}

.metric-content {
  padding: 20px;
}

.metric-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.metric-item:last-child {
  margin-bottom: 0;
}

.metric-label {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.metric-bar {
  position: relative;
  width: 120px;
  height: 20px;
  background: var(--border-light);
  border-radius: 10px;
  overflow: hidden;
}

.metric-fill {
  height: 100%;
  border-radius: 10px;
  transition: width 0.3s ease;
}

.metric-fill.memory {
  background: linear-gradient(to right, #4CAF50, #FF9800);
}

.metric-fill.cpu {
  background: linear-gradient(to right, #2196F3, #FF5722);
}

.metric-value {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 0.8rem;
  font-weight: 600;
  color: white;
  text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
}

.metric-number {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.error-count {
  color: var(--error-color);
}

.health-status-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
}

.health-status-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  background: var(--bg-primary);
  border: 1px solid var(--border-light);
}

.health-status-item.health-status-healthy {
  border-color: var(--success-color);
  background: var(--success-bg);
}

.health-status-item.health-status-warning {
  border-color: var(--warning-color);
  background: var(--warning-bg);
}

.health-status-item.health-status-error {
  border-color: var(--error-color);
  background: var(--error-bg);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-healthy { background: var(--success-color); }
.status-warning { background: var(--warning-color); }
.status-error { background: var(--error-color); }

.service-name {
  flex: 1;
  font-size: 0.9rem;
  color: var(--text-primary);
}

.status-text {
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.log-card {
  grid-column: 1 / -1;
}

.realtime-log {
  max-height: 300px;
  overflow-y: auto;
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 0.85rem;
  background: var(--bg-code);
  border-radius: var(--radius-sm);
  padding: 12px;
}

.log-entry {
  display: flex;
  gap: 8px;
  margin-bottom: 4px;
  align-items: center;
}

.log-time {
  color: var(--text-muted);
  font-size: 0.8rem;
  min-width: 80px;
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

.log-empty {
  text-align: center;
  color: var(--text-muted);
  font-style: italic;
  padding: 20px;
}

.diagnostics-card {
  grid-column: 1 / -1;
}

.diagnostics-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-light);
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary-label {
  color: var(--text-secondary);
  font-size: 0.85rem;
}

.summary-value {
  color: var(--text-primary);
  font-weight: 600;
}

.health-score {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.9rem;
}

.health-score.excellent { background: #d4edda; color: #155724; }
.health-score.good { background: #d1ecf1; color: #0c5460; }
.health-score.warning { background: #fff3cd; color: #856404; }
.health-score.critical { background: #f8d7da; color: #721c24; }

.quick-health {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
}

.quick-health-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  background: var(--bg-primary);
  border: 1px solid var(--border-light);
}

.quick-health-item.healthy {
  border-color: var(--success-color);
  background: var(--success-bg);
}

.quick-health-item.unhealthy {
  border-color: var(--error-color);
  background: var(--error-bg);
}

.health-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.health-dot.healthy { background: var(--success-color); }
.health-dot.unhealthy { background: var(--error-color); }

.service-label {
  font-size: 0.85rem;
  color: var(--text-primary);
}

.monitoring-error {
  text-align: center;
  padding: 24px;
  background: var(--error-bg);
  border: 1px solid var(--error-color);
  border-radius: var(--radius-md);
  margin-top: 24px;
}

.monitoring-error h4 {
  color: var(--error-color);
  margin-bottom: 12px;
}

.monitoring-error p {
  color: var(--text-secondary);
  margin-bottom: 16px;
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

.btn-success {
  background: var(--success-color);
  color: white;
}

.btn-success:hover:not(:disabled) {
  background: var(--success-hover);
}

.btn-danger {
  background: var(--error-color);
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: var(--error-hover);
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

.btn-small {
  padding: 4px 8px;
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
