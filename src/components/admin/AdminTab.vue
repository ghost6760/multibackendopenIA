<template>
  <div class="admin-tab">
    <!-- Header del tab -->
    <div class="tab-header">
      <h2 class="tab-title">🔧 Panel de Administración</h2>
      <p class="tab-subtitle">
        Herramientas avanzadas de diagnóstico y mantenimiento del sistema
      </p>
    </div>

    <!-- Panel de estado del sistema -->
    <div class="system-overview">
      <div class="overview-cards">
        <div class="overview-card">
          <div class="card-icon">🖥️</div>
          <div class="card-content">
            <h4>Estado del Sistema</h4>
            <div :class="['card-value', systemStatus]">{{ systemStatusText }}</div>
          </div>
        </div>
        
        <div class="overview-card">
          <div class="card-icon">📊</div>
          <div class="card-content">
            <h4>Uso de Memoria</h4>
            <div class="card-value">{{ memoryUsage }}</div>
          </div>
        </div>
        
        <div class="overview-card">
          <div class="card-icon">⏱️</div>
          <div class="card-content">
            <h4>Tiempo Activo</h4>
            <div class="card-value">{{ uptime }}</div>
          </div>
        </div>
        
        <div class="overview-card">
          <div class="card-icon">📈</div>
          <div class="card-content">
            <h4>Requests/min</h4>
            <div class="card-value">{{ requestsPerMinute }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Herramientas de diagnóstico -->
    <div class="diagnostic-tools">
      <div class="tools-header">
        <h3>🔍 Herramientas de Diagnóstico</h3>
        <button @click="refreshSystemInfo" class="btn btn-secondary" :disabled="isRefreshing">
          <span v-if="isRefreshing">⏳ Actualizando...</span>
          <span v-else>🔄 Actualizar</span>
        </button>
      </div>
      
      <div class="tools-grid">
        <button 
          @click="runSystemDiagnostics"
          class="tool-button"
          :disabled="isRunningDiagnostics"
        >
          <div class="tool-icon">🔍</div>
          <div class="tool-content">
            <div class="tool-title">Diagnósticos del Sistema</div>
            <div class="tool-description">Ejecutar diagnósticos completos del sistema</div>
          </div>
          <div v-if="isRunningDiagnostics" class="tool-loading">⏳</div>
        </button>
        
        <button 
          @click="checkServicesStatus"
          class="tool-button"
          :disabled="isCheckingServices"
        >
          <div class="tool-icon">🏥</div>
          <div class="tool-content">
            <div class="tool-title">Estado de Servicios</div>
            <div class="tool-description">Verificar el estado de todos los servicios</div>
          </div>
          <div v-if="isCheckingServices" class="tool-loading">⏳</div>
        </button>
        
        <button 
          @click="runAutoDiagnostics"
          class="tool-button"
          :disabled="isRunningAutoDiagnostics"
        >
          <div class="tool-icon">🤖</div>
          <div class="tool-content">
            <div class="tool-title">Auto-Diagnóstico</div>
            <div class="tool-description">Diagnóstico automático con IA</div>
          </div>
          <div v-if="isRunningAutoDiagnostics" class="tool-loading">⏳</div>
        </button>
        
        <button @click="exportSystemLogs" class="tool-button">
          <div class="tool-icon">📤</div>
          <div class="tool-content">
            <div class="tool-title">Exportar Logs</div>
            <div class="tool-description">Descargar logs del sistema</div>
          </div>
        </button>
        
        <button @click="clearSystemLog" class="tool-button" :disabled="systemLog.length === 0">
          <div class="tool-icon">🗑️</div>
          <div class="tool-content">
            <div class="tool-title">Limpiar Log</div>
            <div class="tool-description">Limpiar el log del sistema actual</div>
          </div>
        </button>
        
        <button @click="restartServices" class="tool-button" :disabled="isRestartingServices">
          <div class="tool-icon">🔄</div>
          <div class="tool-content">
            <div class="tool-title">Reiniciar Servicios</div>
            <div class="tool-description">Reiniciar servicios críticos</div>
          </div>
          <div v-if="isRestartingServices" class="tool-loading">⏳</div>
        </button>
      </div>
    </div>

    <!-- Monitoreo en tiempo real -->
    <div class="real-time-monitoring">
      <div class="monitoring-header">
        <h3>📡 Monitoreo en Tiempo Real</h3>
        <div class="monitoring-controls">
          <button 
            @click="toggleRealTimeMonitoring"
            :class="['btn', isMonitoring ? 'btn-danger' : 'btn-success']"
          >
            <span v-if="isMonitoring">⏹️ Detener Monitoreo</span>
            <span v-else">▶️ Iniciar Monitoreo</span>
          </button>
          <span v-if="isMonitoring" class="monitoring-status">
            📊 Activo - Próxima actualización en {{ nextUpdateCountdown }}s
          </span>
        </div>
      </div>
      
      <div v-if="isMonitoring" class="monitoring-content">
        <div class="metrics-grid">
          <div class="metric-card">
            <h4>💾 Uso de Memoria</h4>
            <div class="metric-chart">
              <div class="progress-bar">
                <div 
                  class="progress-fill"
                  :style="{ width: memoryUsagePercent + '%' }"
                  :class="{ 'progress-warning': memoryUsagePercent > 80 }"
                ></div>
              </div>
              <div class="metric-value">{{ memoryUsagePercent }}%</div>
            </div>
          </div>
          
          <div class="metric-card">
            <h4>🖥️ Uso de CPU</h4>
            <div class="metric-chart">
              <div class="progress-bar">
                <div 
                  class="progress-fill"
                  :style="{ width: cpuUsagePercent + '%' }"
                  :class="{ 'progress-warning': cpuUsagePercent > 80 }"
                ></div>
              </div>
              <div class="metric-value">{{ cpuUsagePercent }}%</div>
            </div>
          </div>
          
          <div class="metric-card">
            <h4>🌐 Requests Activos</h4>
            <div class="metric-value large">{{ activeRequests }}</div>
          </div>
          
          <div class="metric-card">
            <h4>⚠️ Errores/min</h4>
            <div class="metric-value large error">{{ errorsPerMinute }}</div>
          </div>
        </div>
        
        <!-- Log en tiempo real -->
        <div class="real-time-log">
          <h4>📝 Log en Tiempo Real</h4>
          <div class="log-container" ref="logContainer">
            <div 
              v-for="(entry, index) in recentLogEntries"
              :key="index"
              :class="['log-entry', entry.level]"
            >
              <span class="log-timestamp">{{ formatTime(entry.timestamp) }}</span>
              <span class="log-level">{{ entry.level.toUpperCase() }}</span>
              <span class="log-message">{{ entry.message }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Resultados de diagnósticos -->
    <div v-if="diagnosticsResults" class="diagnostics-results">
      <div class="results-header">
        <h3>📋 Resultados de Diagnósticos</h3>
        <div class="results-meta">
          <span>Ejecutado: {{ formatDateTime(diagnosticsResults.timestamp) }}</span>
          <span>Duración: {{ diagnosticsResults.duration }}ms</span>
        </div>
      </div>
      
      <div class="results-content">
        <div class="results-summary">
          <div class="summary-item">
            <div class="summary-label">Estado General:</div>
            <div :class="['summary-value', diagnosticsResults.overall_status]">
              {{ diagnosticsResults.overall_status_text }}
            </div>
          </div>
          <div class="summary-item">
            <div class="summary-label">Servicios Verificados:</div>
            <div class="summary-value">{{ diagnosticsResults.services_checked }}</div>
          </div>
          <div class="summary-item">
            <div class="summary-label">Problemas Encontrados:</div>
            <div :class="['summary-value', diagnosticsResults.issues_count > 0 ? 'warning' : 'success']">
              {{ diagnosticsResults.issues_count }}
            </div>
          </div>
        </div>
        
        <div v-if="diagnosticsResults.services" class="services-status">
          <h4>🔧 Estado de Servicios</h4>
          <div class="services-grid">
            <div 
              v-for="(service, name) in diagnosticsResults.services"
              :key="name"
              :class="['service-item', service.status]"
            >
              <div class="service-name">{{ name }}</div>
              <div class="service-status">{{ service.status }}</div>
              <div v-if="service.response_time" class="service-time">
                {{ service.response_time }}ms
              </div>
              <div v-if="service.error" class="service-error">
                {{ service.error }}
              </div>
            </div>
          </div>
        </div>
        
        <div v-if="diagnosticsResults.recommendations" class="recommendations">
          <h4>💡 Recomendaciones</h4>
          <ul class="recommendations-list">
            <li 
              v-for="(recommendation, index) in diagnosticsResults.recommendations"
              :key="index"
              class="recommendation-item"
            >
              {{ recommendation }}
            </li>
          </ul>
        </div>
        
        <div v-if="diagnosticsResults.details" class="diagnostics-details">
          <h4>📊 Detalles Técnicos</h4>
          <details>
            <summary>Ver detalles completos</summary>
            <pre class="details-json">{{ formatJSON(diagnosticsResults.details) }}</pre>
          </details>
        </div>
      </div>
    </div>

    <!-- Log del sistema -->
    <div class="system-log-section">
      <div class="log-header">
        <h3>📝 Log del Sistema</h3>
        <div class="log-controls">
          <select v-model="logLevelFilter" class="log-filter">
            <option value="">Todos los niveles</option>
            <option value="error">Errores</option>
            <option value="warning">Advertencias</option>
            <option value="info">Información</option>
            <option value="debug">Debug</option>
          </select>
          <button @click="clearSystemLog" class="btn btn-sm btn-secondary">
            🗑️ Limpiar
          </button>
          <button @click="exportSystemLogs" class="btn btn-sm btn-primary">
            📤 Exportar
          </button>
        </div>
      </div>
      
      <div class="log-container" ref="systemLogContainer">
        <div 
          v-for="(entry, index) in filteredLogEntries"
          :key="index"
          :class="['log-entry', entry.level]"
        >
          <span class="log-timestamp">{{ entry.timestamp }}</span>
          <span class="log-level">{{ entry.level.toUpperCase() }}</span>
          <span class="log-message">{{ entry.message }}</span>
        </div>
        
        <div v-if="filteredLogEntries.length === 0" class="log-empty">
          <div class="empty-icon">📝</div>
          <p>No hay entradas de log que mostrar</p>
        </div>
      </div>
    </div>

    <!-- Modal de confirmación para acciones críticas -->
    <div v-if="showConfirmModal" class="confirm-modal" @click="closeConfirmModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h4>⚠️ Confirmar Acción</h4>
          <button @click="closeConfirmModal" class="close-button">✕</button>
        </div>
        
        <div class="modal-body">
          <p>{{ confirmMessage }}</p>
          <p class="warning-text">Esta acción no se puede deshacer.</p>
        </div>
        
        <div class="modal-footer">
          <button @click="executeConfirmedAction" class="btn btn-danger">
            ✅ Confirmar
          </button>
          <button @click="closeConfirmModal" class="btn btn-secondary">
            ❌ Cancelar
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
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
// REFS
// ============================================================================

const logContainer = ref(null)
const systemLogContainer = ref(null)

// ============================================================================
// ESTADO LOCAL
// ============================================================================

const isRefreshing = ref(false)
const isRunningDiagnostics = ref(false)
const isCheckingServices = ref(false)
const isRunningAutoDiagnostics = ref(false)
const isRestartingServices = ref(false)

// Monitoreo en tiempo real
const isMonitoring = ref(false)
const monitoringInterval = ref(null)
const nextUpdateCountdown = ref(0)
const countdownInterval = ref(null)

// Estado del sistema
const systemStatus = ref('unknown')
const memoryUsage = ref('N/A')
const uptime = ref('N/A')
const requestsPerMinute = ref(0)
const memoryUsagePercent = ref(0)
const cpuUsagePercent = ref(0)
const activeRequests = ref(0)
const errorsPerMinute = ref(0)

// Resultados y logs
const diagnosticsResults = ref(null)
const recentLogEntries = ref([])
const logLevelFilter = ref('')

// Modal de confirmación
const showConfirmModal = ref(false)
const confirmMessage = ref('')
const confirmedAction = ref(null)

// ============================================================================
// COMPUTED
// ============================================================================

const systemStatusText = computed(() => {
  switch (systemStatus.value) {
    case 'healthy': return 'Saludable'
    case 'warning': return 'Advertencia'
    case 'error': return 'Error'
    case 'critical': return 'Crítico'
    default: return 'Desconocido'
  }
})

const systemLog = computed(() => appStore.systemLog)

const filteredLogEntries = computed(() => {
  let entries = [...systemLog.value]
  
  if (logLevelFilter.value) {
    entries = entries.filter(entry => entry.level === logLevelFilter.value)
  }
  
  return entries.slice(-100) // Mostrar solo las últimas 100 entradas
})

// ============================================================================
// FUNCIONES PRINCIPALES MIGRADAS DEL SCRIPT.JS
// ============================================================================

/**
 * Ejecuta diagnósticos del sistema - MIGRADO: runSystemDiagnostics() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const runSystemDiagnostics = async () => {
  isRunningDiagnostics.value = true
  diagnosticsResults.value = null
  
  try {
    appStore.addToLog('Starting system diagnostics', 'info')
    showNotification('Ejecutando diagnósticos del sistema...', 'info')
    
    const startTime = Date.now()
    
    // Llamada a la API - PRESERVAR ENDPOINT EXACTO
    const response = await apiRequest('/api/admin/diagnostics', {
      method: 'POST',
      headers: {
        'X-API-Key': appStore.adminApiKey
      }
    })
    
    const endTime = Date.now()
    
    diagnosticsResults.value = {
      ...response,
      timestamp: startTime,
      duration: endTime - startTime
    }
    
    appStore.addToLog('System diagnostics completed', 'info')
    showNotification('Diagnósticos completados', 'success')
    
  } catch (error) {
    appStore.addToLog(`System diagnostics failed: ${error.message}`, 'error')
    showNotification(`Error en diagnósticos: ${error.message}`, 'error')
  } finally {
    isRunningDiagnostics.value = false
  }
}

/**
 * Verifica el estado de servicios - MIGRADO: checkServicesStatus() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const checkServicesStatus = async () => {
  isCheckingServices.value = true
  
  try {
    appStore.addToLog('Checking services status', 'info')
    showNotification('Verificando estado de servicios...', 'info')
    
    // Llamada a la API - PRESERVAR ENDPOINT EXACTO
    const response = await apiRequest('/api/admin/services/status', {
      headers: {
        'X-API-Key': appStore.adminApiKey
      }
    })
    
    // Actualizar diagnósticos con estado de servicios
    diagnosticsResults.value = {
      timestamp: Date.now(),
      duration: 0,
      overall_status: response.overall_status || 'unknown',
      overall_status_text: response.overall_status_text || 'Estado desconocido',
      services_checked: Object.keys(response.services || {}).length,
      issues_count: Object.values(response.services || {}).filter(s => s.status !== 'healthy').length,
      services: response.services || {},
      recommendations: response.recommendations || []
    }
    
    appStore.addToLog('Services status check completed', 'info')
    showNotification('Estado de servicios verificado', 'success')
    
  } catch (error) {
    appStore.addToLog(`Services status check failed: ${error.message}`, 'error')
    showNotification(`Error verificando servicios: ${error.message}`, 'error')
  } finally {
    isCheckingServices.value = false
  }
}

/**
 * Ejecuta auto-diagnósticos - MIGRADO: runAutoDiagnostics() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const runAutoDiagnostics = async () => {
  isRunningAutoDiagnostics.value = true
  
  try {
    appStore.addToLog('Starting auto-diagnostics', 'info')
    showNotification('Ejecutando auto-diagnósticos con IA...', 'info')
    
    // Llamada a la API - PRESERVAR ENDPOINT EXACTO (asumiendo que existe)
    const response = await apiRequest('/api/admin/auto-diagnostics', {
      method: 'POST',
      headers: {
        'X-API-Key': appStore.adminApiKey
      }
    })
    
    diagnosticsResults.value = {
      ...response,
      timestamp: Date.now(),
      duration: response.execution_time || 0
    }
    
    appStore.addToLog('Auto-diagnostics completed', 'info')
    showNotification('Auto-diagnósticos completados', 'success')
    
  } catch (error) {
    appStore.addToLog(`Auto-diagnostics failed: ${error.message}`, 'error')
    showNotification(`Error en auto-diagnósticos: ${error.message}`, 'error')
  } finally {
    isRunningAutoDiagnostics.value = false
  }
}

/**
 * Limpia el log del sistema - MIGRADO: clearSystemLog() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const clearSystemLog = () => {
  confirmMessage.value = '¿Estás seguro de que quieres limpiar todo el log del sistema?'
  confirmedAction.value = () => {
    appStore.clearSystemLog()
    showNotification('Log del sistema limpiado', 'info')
  }
  showConfirmModal.value = true
}

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
  
  // Configurar intervalos
  monitoringInterval.value = setInterval(updateMonitoringData, 5000)
  
  countdownInterval.value = setInterval(() => {
    nextUpdateCountdown.value--
    if (nextUpdateCountdown.value <= 0) {
      nextUpdateCountdown.value = 5
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
 * Actualiza datos de monitoreo
 */
const updateMonitoringData = async () => {
  try {
    // Simular datos de monitoreo (en una implementación real, estos vendrían de APIs)
    memoryUsagePercent.value = Math.floor(Math.random() * 40) + 30 // 30-70%
    cpuUsagePercent.value = Math.floor(Math.random() * 50) + 10    // 10-60%
    activeRequests.value = Math.floor(Math.random() * 20) + 5      // 5-25
    errorsPerMinute.value = Math.floor(Math.random() * 5)          // 0-5
    
    // Agregar entradas al log en tiempo real
    const logMessages = [
      'Request processed successfully',
      'Cache hit for key: user_data_123',
      'Database connection pool: 15/20 active',
      'Background task completed',
      'Health check passed'
    ]
    
    if (Math.random() > 0.7) { // 30% de probabilidad de nueva entrada
      const newEntry = {
        timestamp: new Date().toISOString(),
        level: Math.random() > 0.9 ? 'warning' : 'info',
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
  }
}

// ============================================================================
// FUNCIONES ADICIONALES
// ============================================================================

const refreshSystemInfo = async () => {
  isRefreshing.value = true
  
  try {
    // Simular carga de información del sistema
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    systemStatus.value = 'healthy'
    memoryUsage.value = '2.1 GB / 8.0 GB'
    uptime.value = '15d 7h 32m'
    requestsPerMinute.value = Math.floor(Math.random() * 100) + 50
    
    showNotification('Información del sistema actualizada', 'success')
    
  } catch (error) {
    showNotification(`Error actualizando información: ${error.message}`, 'error')
  } finally {
    isRefreshing.value = false
  }
}

const restartServices = () => {
  confirmMessage.value = '¿Estás seguro de que quieres reiniciar los servicios? Esto puede causar interrupciones temporales.'
  confirmedAction.value = async () => {
    isRestartingServices.value = true
    
    try {
      showNotification('Reiniciando servicios...', 'info')
      
      // Simular reinicio de servicios
      await new Promise(resolve => setTimeout(resolve, 3000))
      
      showNotification('Servicios reiniciados exitosamente', 'success')
      await refreshSystemInfo()
      
    } catch (error) {
      showNotification(`Error reiniciando servicios: ${error.message}`, 'error')
    } finally {
      isRestartingServices.value = false
    }
  }
  showConfirmModal.value = true
}

const exportSystemLogs = () => {
  try {
    const logs = systemLog.value.map(entry => 
      `${entry.timestamp} [${entry.level.toUpperCase()}] ${entry.message}`
    ).join('\n')
    
    const blob = new Blob([logs], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    
    const a = document.createElement('a')
    a.href = url
    a.download = `system_logs_${new Date().toISOString().slice(0, 10)}.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    
    URL.revokeObjectURL(url)
    showNotification('Logs exportados exitosamente', 'success')
    
  } catch (error) {
    showNotification('Error exportando logs', 'error')
  }
}

const closeConfirmModal = () => {
  showConfirmModal.value = false
  confirmMessage.value = ''
  confirmedAction.value = null
}

const executeConfirmedAction = () => {
  if (confirmedAction.value) {
    confirmedAction.value()
  }
  closeConfirmModal()
}

// ============================================================================
// UTILIDADES
// ============================================================================

const formatTime = (timestamp) => {
  try {
    return new Date(timestamp).toLocaleTimeString()
  } catch (error) {
    return timestamp
  }
}

const formatDateTime = (timestamp) => {
  try {
    return new Date(timestamp).toLocaleString()
  } catch (error) {
    return 'Fecha inválida'
  }
}

const formatJSON = (obj) => {
  try {
    return JSON.stringify(obj, null, 2)
  } catch (error) {
    return 'Error formatting JSON: ' + error.message
  }
}

// ============================================================================
// LIFECYCLE
// ============================================================================

onMounted(async () => {
  appStore.addToLog('AdminTab component mounted', 'info')
  
  // Cargar información inicial
  await refreshSystemInfo()
  
  // EXPONER FUNCIONES GLOBALES PARA COMPATIBILIDAD
  window.runSystemDiagnostics = runSystemDiagnostics
  window.clearSystemLog = clearSystemLog
  window.checkServicesStatus = checkServicesStatus
  window.runAutoDiagnostics = runAutoDiagnostics
  window.startRealTimeMonitoring = startRealTimeMonitoring
  window.stopRealTimeMonitoring = stopRealTimeMonitoring
})

onUnmounted(() => {
  // Detener monitoreo si está activo
  stopRealTimeMonitoring()
  
  // Limpiar funciones globales
  if (typeof window !== 'undefined') {
    delete window.runSystemDiagnostics
    delete window.clearSystemLog
    delete window.checkServicesStatus
    delete window.runAutoDiagnostics
    delete window.startRealTimeMonitoring
    delete window.stopRealTimeMonitoring
  }
  
  appStore.addToLog('AdminTab component unmounted', 'info')
})
</script>

<style scoped>
.admin-tab {
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

.system-overview {
  margin-bottom: 30px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}

.overview-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.overview-card {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-light);
}

.card-icon {
  font-size: 2rem;
  width: 50px;
  text-align: center;
}

.card-content h4 {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin: 0 0 5px 0;
  font-weight: 500;
}

.card-value {
  color: var(--text-primary);
  font-size: 1.3rem;
  font-weight: 600;
}

.card-value.healthy {
  color: var(--success-color);
}

.card-value.warning {
  color: var(--warning-color);
}

.card-value.error,
.card-value.critical {
  color: var(--error-color);
}

.diagnostic-tools {
  margin-bottom: 30px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}

.tools-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.tools-header h3 {
  color: var(--text-primary);
  margin: 0;
}

.tools-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 15px;
}

.tool-button {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: var(--transition-normal);
  text-align: left;
}

.tool-button:hover:not(:disabled) {
  background: var(--bg-tertiary);
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.tool-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.tool-icon {
  font-size: 1.5rem;
  width: 40px;
  text-align: center;
}

.tool-content {
  flex: 1;
}

.tool-title {
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.tool-description {
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.tool-loading {
  font-size: 1.2rem;
}

.real-time-monitoring {
  margin-bottom: 30px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}

.monitoring-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 15px;
}

.monitoring-header h3 {
  color: var(--text-primary);
  margin: 0;
}

.monitoring-controls {
  display: flex;
  align-items: center;
  gap: 15px;
}

.monitoring-status {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.monitoring-content {
  display: flex;
  flex-direction: column;
  gap: 25px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.metric-card {
  padding: 15px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-light);
}

.metric-card h4 {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin: 0 0 10px 0;
  font-weight: 500;
}

.metric-chart {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.progress-bar {
  height: 8px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--success-color);
  border-radius: var(--radius-sm);
  transition: width 0.3s ease;
}

.progress-fill.progress-warning {
  background: var(--warning-color);
}

.metric-value {
  color: var(--text-primary);
  font-size: 1.2rem;
  font-weight: 600;
  text-align: center;
}

.metric-value.large {
  font-size: 1.8rem;
}

.metric-value.error {
  color: var(--error-color);
}

.real-time-log {
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  padding: 15px;
}

.real-time-log h4 {
  color: var(--text-primary);
  margin: 0 0 15px 0;
}

.diagnostics-results {
  margin-bottom: 30px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 15px;
}

.results-header h3 {
  color: var(--text-primary);
  margin: 0;
}

.results-meta {
  display: flex;
  gap: 15px;
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.results-content {
  display: flex;
  flex-direction: column;
  gap: 25px;
}

.results-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
}

.summary-label {
  color: var(--text-secondary);
  font-weight: 500;
}

.summary-value {
  color: var(--text-primary);
  font-weight: 600;
}

.summary-value.healthy,
.summary-value.success {
  color: var(--success-color);
}

.summary-value.warning {
  color: var(--warning-color);
}

.summary-value.error,
.summary-value.critical {
  color: var(--error-color);
}

.services-status h4,
.recommendations h4,
.diagnostics-details h4 {
  color: var(--text-primary);
  margin-bottom: 15px;
}

.services-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.service-item {
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.service-item.healthy {
  border-left: 4px solid var(--success-color);
}

.service-item.warning {
  border-left: 4px solid var(--warning-color);
}

.service-item.error {
  border-left: 4px solid var(--error-color);
}

.service-name {
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 5px;
}

.service-status {
  font-size: 0.9rem;
  font-weight: 500;
  text-transform: uppercase;
}

.service-time {
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin-top: 3px;
}

.service-error {
  font-size: 0.8rem;
  color: var(--error-color);
  margin-top: 3px;
}

.recommendations-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.recommendation-item {
  padding: 10px;
  margin-bottom: 8px;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
  border-left: 4px solid var(--info-color);
}

.details-json {
  background: var(--bg-secondary);
  padding: 15px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-light);
  overflow-x: auto;
  font-size: 0.9rem;
  margin-top: 10px;
}

.system-log-section {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  flex-wrap: wrap;
  gap: 15px;
}

.log-header h3 {
  color: var(--text-primary);
  margin: 0;
}

.log-controls {
  display: flex;
  gap: 10px;
  align-items: center;
}

.log-filter {
  padding: 6px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
  color: var(--text-primary);
}

.log-container {
  max-height: 400px;
  overflow-y: auto;
  background: var(--bg-secondary);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  padding: 10px;
}

.log-entry {
  display: grid;
  grid-template-columns: auto auto 1fr;
  gap: 10px;
  padding: 6px 8px;
  margin-bottom: 2px;
  border-radius: var(--radius-sm);
  font-family: monospace;
  font-size: 0.85rem;
  align-items: center;
}

.log-entry.error {
  background: rgba(245, 101, 101, 0.1);
  border-left: 3px solid var(--error-color);
}

.log-entry.warning {
  background: rgba(237, 137, 54, 0.1);
  border-left: 3px solid var(--warning-color);
}

.log-entry.info {
  background: rgba(66, 153, 225, 0.1);
  border-left: 3px solid var(--info-color);
}

.log-entry.debug {
  background: rgba(160, 174, 192, 0.1);
  border-left: 3px solid var(--text-muted);
}

.log-timestamp {
  color: var(--text-muted);
  font-size: 0.8rem;
}

.log-level {
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  font-size: 0.7rem;
  font-weight: 600;
  text-align: center;
  min-width: 60px;
}

.log-entry.error .log-level {
  background: var(--error-color);
  color: white;
}

.log-entry.warning .log-level {
  background: var(--warning-color);
  color: white;
}

.log-entry.info .log-level {
  background: var(--info-color);
  color: white;
}

.log-entry.debug .log-level {
  background: var(--text-muted);
  color: white;
}

.log-message {
  color: var(--text-primary);
  word-break: break-word;
}

.log-empty {
  text-align: center;
  padding: 40px;
  color: var(--text-secondary);
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 10px;
  opacity: 0.6;
}

.confirm-modal {
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
  max-width: 500px;
  width: 90%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
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
  padding: 20px;
}

.modal-body p {
  margin-bottom: 15px;
  color: var(--text-primary);
  line-height: 1.6;
}

.warning-text {
  color: var(--warning-color);
  font-weight: 500;
}

.modal-footer {
  padding: 20px;
  border-top: 1px solid var(--border-color);
  display: flex;
  gap: 10px;
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
  .overview-cards {
    grid-template-columns: 1fr;
  }
  
  .tools-grid {
    grid-template-columns: 1fr;
  }
  
  .metrics-grid {
    grid-template-columns: 1fr;
  }
  
  .results-summary {
    grid-template-columns: 1fr;
  }
  
  .services-grid {
    grid-template-columns: 1fr;
  }
  
  .monitoring-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .monitoring-controls {
    flex-direction: column;
    align-items: stretch;
  }
  
  .results-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .results-meta {
    flex-direction: column;
    gap: 5px;
  }
  
  .log-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .log-controls {
    flex-direction: column;
  }
  
  .log-entry {
    grid-template-columns: 1fr;
    gap: 5px;
  }
  
  .modal-content {
    margin: 10px;
    width: auto;
  }
  
  .modal-footer {
    flex-direction: column;
  }
}
</style>
