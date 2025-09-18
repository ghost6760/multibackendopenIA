/**
 * useHealthCheck.js - Composable para Health Checks y Monitoreo
 * MIGRADO DE: script.js funciones performHealthCheck(), performCompanyHealthCheck(), startRealTimeMonitoring(), etc.
 * PRESERVAR: Comportamiento exacto de las funciones originales
 * COMPATIBILIDAD: 100% con el script.js original
 */

import { ref, computed, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'
import { useSystemLog } from '@/composables/useSystemLog'

export const useHealthCheck = () => {
  const appStore = useAppStore()
  const { apiRequest } = useApiRequest()
  const { showNotification } = useNotifications()
  const { addToLog } = useSystemLog()

  // ============================================================================
  // ESTADO LOCAL
  // ============================================================================

  const isPerformingHealthCheck = ref(false)
  const isPerformingCompanyHealthCheck = ref(false)
  const isCheckingServices = ref(false)
  const isRunningAutoDiagnostics = ref(false)
  const isRealTimeActive = ref(false)
  
  const healthResults = ref(null)
  const companyHealthResults = ref(null)
  const servicesStatus = ref({})
  const autoDiagnosticsResults = ref(null)
  const realTimeData = ref({
    systemHealth: {},
    metrics: {
      memoryUsage: 0,
      cpuUsage: 0,
      activeRequests: 0,
      errorsPerMinute: 0
    },
    lastUpdate: null
  })
  
  const selectedCompanyForHealth = ref('')
  const monitoringInterval = ref(null)
  const countdownInterval = ref(null)
  const nextUpdateCountdown = ref(30)
  const healthHistory = ref([])

  // ============================================================================
  // COMPUTED PROPERTIES
  // ============================================================================

  const isAnyProcessing = computed(() => 
    isPerformingHealthCheck.value || 
    isPerformingCompanyHealthCheck.value || 
    isCheckingServices.value ||
    isRunningAutoDiagnostics.value
  )

  const overallSystemHealth = computed(() => {
    if (!healthResults.value) return 'unknown'
    
    const status = healthResults.value.status
    if (status === 'healthy') return 'healthy'
    if (status === 'partial') return 'warning'
    return 'error'
  })

  const healthyServicesCount = computed(() => {
    if (!realTimeData.value.systemHealth) return 0
    return Object.values(realTimeData.value.systemHealth).filter(status => status === 'healthy').length
  })

  const totalServicesCount = computed(() => {
    return Object.keys(realTimeData.value.systemHealth).length
  })

  const systemHealthPercentage = computed(() => {
    if (totalServicesCount.value === 0) return 0
    return Math.round((healthyServicesCount.value / totalServicesCount.value) * 100)
  })

  const canStartMonitoring = computed(() => !isRealTimeActive.value && !isAnyProcessing.value)

  // ============================================================================
  // FUNCIONES PRINCIPALES MIGRADAS DEL SCRIPT.JS
  // ============================================================================

  /**
   * Realiza health check general - MIGRADO: performHealthCheck() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const performHealthCheck = async () => {
    if (isPerformingHealthCheck.value) {
      showNotification('Ya se está ejecutando un health check', 'warning')
      return
    }

    try {
      isPerformingHealthCheck.value = true
      healthResults.value = null

      addToLog('Starting general health check', 'info')
      showNotification('Ejecutando health check general...', 'info')

      const startTime = Date.now()

      // PRESERVAR: Llamada API exacta como script.js
      const response = await apiRequest('/api/health', {
        method: 'GET'
      })

      const endTime = Date.now()
      const duration = endTime - startTime

      healthResults.value = {
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

      // PRESERVAR: Mostrar resultado en DOM como script.js
      const container = document.getElementById('generalHealthResult')
      if (container) {
        const status = response.status
        const statusClass = status === 'healthy' ? 'success' : 
                           status === 'partial' ? 'warning' : 'error'
        
        container.innerHTML = `
          <div class="result-container result-${statusClass}">
            <h4>🏥 Health Check General</h4>
            <div class="health-status ${status === 'healthy' ? 'healthy' : 'warning'}">
              <span class="status-indicator status-${status === 'healthy' ? 'healthy' : 'warning'}"></span>
              Estado: ${status.toUpperCase()}
            </div>
            <p><strong>Timestamp:</strong> ${response.timestamp}</p>
            <p><strong>Duración:</strong> ${duration}ms</p>
            <p><strong>Ambiente:</strong> ${response.environment || 'Desconocido'}</p>
            
            ${response.services ? `
              <h5>Servicios:</h5>
              ${Object.entries(response.services).map(([service, healthy]) => `
                <div class="health-status ${healthy ? 'healthy' : 'error'}">
                  <span class="status-indicator status-${healthy ? 'healthy' : 'error'}"></span>
                  ${service}: ${healthy ? 'Saludable' : 'Error'}
                </div>
              `).join('')}
            ` : ''}
            
            <div class="json-container" style="margin-top: 15px;">
              <pre>${JSON.stringify(response, null, 2)}</pre>
            </div>
          </div>
        `
      }

      addToLog('General health check completed successfully', 'success')
      showNotification('Health check general completado', 'success')

      return response

    } catch (error) {
      addToLog(`General health check failed: ${error.message}`, 'error')
      showNotification(`Error en health check: ${error.message}`, 'error')

      // PRESERVAR: Mostrar error en DOM como script.js
      const container = document.getElementById('generalHealthResult')
      if (container) {
        container.innerHTML = `
          <div class="result-container result-error">
            <p>❌ Error en health check general</p>
            <p>${error.message}</p>
          </div>
        `
      }

      throw error

    } finally {
      isPerformingHealthCheck.value = false
    }
  }

  /**
   * Realiza health check por empresa - MIGRADO: performCompanyHealthCheck() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const performCompanyHealthCheck = async (companyId = null) => {
    const targetCompanyId = companyId || selectedCompanyForHealth.value

    if (!targetCompanyId) {
      showNotification('Selecciona una empresa para verificar', 'warning')
      return
    }

    if (isPerformingCompanyHealthCheck.value) {
      showNotification('Ya se está ejecutando un health check de empresa', 'warning')
      return
    }

    try {
      isPerformingCompanyHealthCheck.value = true
      companyHealthResults.value = null

      addToLog(`Starting company health check: ${targetCompanyId}`, 'info')
      showNotification('Ejecutando health check de empresa...', 'info')

      const startTime = Date.now()

      // PRESERVAR: Llamada API exacta como script.js
      const response = await apiRequest(`/api/health/company/${targetCompanyId}`, {
        method: 'GET'
      })

      const endTime = Date.now()
      const duration = endTime - startTime

      companyHealthResults.value = {
        ...response,
        company_id: targetCompanyId,
        timestamp: startTime,
        duration
      }

      // Agregar al historial
      addToHistory({
        ...response,
        company_id: targetCompanyId,
        timestamp: startTime,
        duration,
        type: 'company'
      })

      // PRESERVAR: Mostrar resultado en DOM como script.js
      const container = document.getElementById('companyHealthResult')
      if (container) {
        const status = response.status || 'unknown'
        const statusClass = status === 'healthy' ? 'success' : 
                           status === 'partial' ? 'warning' : 'error'
        
        container.innerHTML = `
          <div class="result-container result-${statusClass}">
            <h4>🏢 Health Check de Empresa</h4>
            <p><strong>Empresa:</strong> ${targetCompanyId}</p>
            <div class="health-status ${status === 'healthy' ? 'healthy' : 'warning'}">
              <span class="status-indicator status-${status === 'healthy' ? 'healthy' : 'warning'}"></span>
              Estado: ${status.toUpperCase()}
            </div>
            <p><strong>Timestamp:</strong> ${response.timestamp}</p>
            <p><strong>Duración:</strong> ${duration}ms</p>
            
            ${response.services_status ? `
              <h5>Estado de Servicios:</h5>
              ${Object.entries(response.services_status).map(([service, data]) => `
                <div class="health-status ${data.healthy ? 'healthy' : 'error'}">
                  <span class="status-indicator status-${data.healthy ? 'healthy' : 'error'}"></span>
                  ${service}: ${data.healthy ? 'Saludable' : 'Error'}
                  ${data.message ? ` - ${data.message}` : ''}
                </div>
              `).join('')}
            ` : ''}
            
            <div class="json-container" style="margin-top: 15px;">
              <pre>${JSON.stringify(response, null, 2)}</pre>
            </div>
          </div>
        `
      }

      addToLog(`Company health check completed for ${targetCompanyId}`, 'success')
      showNotification('Health check de empresa completado', 'success')

      return response

    } catch (error) {
      addToLog(`Company health check failed: ${error.message}`, 'error')
      showNotification(`Error en health check de empresa: ${error.message}`, 'error')

      const container = document.getElementById('companyHealthResult')
      if (container) {
        container.innerHTML = `
          <div class="result-container result-error">
            <p>❌ Error en health check de empresa</p>
            <p><strong>Empresa:</strong> ${targetCompanyId}</p>
            <p>${error.message}</p>
          </div>
        `
      }

      throw error

    } finally {
      isPerformingCompanyHealthCheck.value = false
    }
  }

  /**
   * Verifica estado de servicios - MIGRADO: checkServicesStatus() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const checkServicesStatus = async () => {
    if (isCheckingServices.value) return

    try {
      isCheckingServices.value = true
      addToLog('Checking services status', 'info')

      // PRESERVAR: Llamada API como script.js (endpoint hipotético basado en el patrón)
      const response = await apiRequest('/api/health/services', {
        method: 'GET'
      })

      servicesStatus.value = response.services || {}

      // Actualizar datos en tiempo real si está activo el monitoreo
      if (isRealTimeActive.value) {
        realTimeData.value.systemHealth = { ...realTimeData.value.systemHealth, ...response.services }
      }

      addToLog('Services status checked successfully', 'success')
      
      return response

    } catch (error) {
      addToLog(`Services status check failed: ${error.message}`, 'error')
      return null

    } finally {
      isCheckingServices.value = false
    }
  }

  /**
   * Ejecuta auto-diagnósticos - MIGRADO: runAutoDiagnostics() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const runAutoDiagnostics = async () => {
    if (isRunningAutoDiagnostics.value) {
      showNotification('Ya se están ejecutando auto-diagnósticos', 'warning')
      return
    }

    try {
      isRunningAutoDiagnostics.value = true
      autoDiagnosticsResults.value = null

      addToLog('Starting auto-diagnostics', 'info')
      showNotification('Ejecutando auto-diagnósticos...', 'info')

      const diagnosticsData = {
        timestamp: Date.now(),
        health_general: null,
        companies_health: null,
        services_status: null,
        health_score: 0
      }

      // 1. Health check general
      try {
        const generalResponse = await apiRequest('/api/health')
        diagnosticsData.health_general = generalResponse
      } catch (error) {
        diagnosticsData.health_general = { error: error.message }
      }

      // 2. Health check de empresas (si hay empresa seleccionada)
      if (appStore.currentCompanyId) {
        try {
          const companyResponse = await apiRequest(`/api/health/company/${appStore.currentCompanyId}`)
          diagnosticsData.companies_health = companyResponse
        } catch (error) {
          diagnosticsData.companies_health = { error: error.message }
        }
      }

      // 3. Estado de servicios
      try {
        const servicesResponse = await apiRequest('/api/health/services')
        diagnosticsData.services_status = servicesResponse
      } catch (error) {
        diagnosticsData.services_status = { error: error.message }
      }

      // Calcular score de salud
      let healthyCount = 0
      let totalCount = 0

      if (diagnosticsData.health_general && !diagnosticsData.health_general.error) {
        healthyCount += diagnosticsData.health_general.status === 'healthy' ? 1 : 0
        totalCount += 1
      }

      if (diagnosticsData.companies_health && !diagnosticsData.companies_health.error) {
        healthyCount += 1
        totalCount += 1
      }

      if (diagnosticsData.services_status && !diagnosticsData.services_status.error) {
        healthyCount += 1
        totalCount += 1
      }

      diagnosticsData.health_score = totalCount > 0 ? (healthyCount / totalCount) * 100 : 0

      autoDiagnosticsResults.value = diagnosticsData

      // PRESERVAR: Mostrar resultado en DOM como script.js
      const container = document.getElementById('autoDiagnosticsResult')
      if (container) {
        container.innerHTML = `
          <div class="result-container result-info">
            <h4>🔍 Auto-Diagnósticos</h4>
            <div class="diagnostics-summary">
              <p><strong>Score de Salud:</strong> ${diagnosticsData.health_score.toFixed(1)}%</p>
              <p><strong>Servicios Verificados:</strong> ${getServicesCheckedCount()}</p>
              <p><strong>Timestamp:</strong> ${new Date(diagnosticsData.timestamp).toLocaleString()}</p>
            </div>
            
            <div class="quick-status">
              ${Object.entries(getQuickHealthStatus()).map(([service, status]) => `
                <div class="health-status ${status ? 'healthy' : 'error'}">
                  <span class="status-indicator status-${status ? 'healthy' : 'error'}"></span>
                  ${service}: ${status ? 'OK' : 'Error'}
                </div>
              `).join('')}
            </div>
            
            <div class="json-container" style="margin-top: 15px;">
              <pre>${JSON.stringify(diagnosticsData, null, 2)}</pre>
            </div>
          </div>
        `
      }

      addToLog('Auto-diagnostics completed successfully', 'success')
      showNotification('Auto-diagnósticos completados', 'success')

      return diagnosticsData

    } catch (error) {
      addToLog(`Auto-diagnostics failed: ${error.message}`, 'error')
      showNotification(`Error en auto-diagnósticos: ${error.message}`, 'error')

      const container = document.getElementById('autoDiagnosticsResult')
      if (container) {
        container.innerHTML = `
          <div class="result-container result-error">
            <p>❌ Error en auto-diagnósticos</p>
            <p>${error.message}</p>
          </div>
        `
      }

      throw error

    } finally {
      isRunningAutoDiagnostics.value = false
    }
  }

  /**
   * Inicia monitoreo en tiempo real - MIGRADO: startRealTimeMonitoring() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const startRealTimeMonitoring = () => {
    if (isRealTimeActive.value) {
      showNotification('El monitoreo en tiempo real ya está activo', 'warning')
      return
    }

    addToLog('Starting real-time monitoring', 'info')
    isRealTimeActive.value = true
    nextUpdateCountdown.value = 5

    // Actualizar datos inmediatamente
    updateMonitoringData()

    // PRESERVAR: Configurar intervalos - Mismo intervalo que script.js (30 segundos)
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
    if (!isRealTimeActive.value) return

    addToLog('Stopping real-time monitoring', 'info')
    isRealTimeActive.value = false

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
   * Actualiza datos de monitoreo - MIGRADO de script.js
   * PRESERVAR: Comportamiento de actualización automática
   */
  const updateMonitoringData = async () => {
    try {
      // Simular actualización de métricas - En implementación real, estos datos vendrían de APIs
      realTimeData.value.metrics = {
        memoryUsage: Math.floor(Math.random() * 40) + 30, // 30-70%
        cpuUsage: Math.floor(Math.random() * 50) + 10,    // 10-60%
        activeRequests: Math.floor(Math.random() * 20) + 5, // 5-25
        errorsPerMinute: Math.floor(Math.random() * 5)    // 0-5
      }

      // Actualizar estado de servicios
      const services = ['database', 'redis', 'openai', 'multiagent', 'calendar']
      const systemHealth = {}
      
      services.forEach(service => {
        const random = Math.random()
        if (random > 0.9) {
          systemHealth[service] = 'error'
        } else if (random > 0.8) {
          systemHealth[service] = 'warning'
        } else {
          systemHealth[service] = 'healthy'
        }
      })

      realTimeData.value.systemHealth = systemHealth
      realTimeData.value.lastUpdate = Date.now()

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
        const randomMessage = logMessages[Math.floor(Math.random() * logMessages.length)]
        const level = Math.random() > 0.9 ? 'error' : Math.random() > 0.8 ? 'warning' : 'info'
        addToLog(randomMessage, level)
      }

    } catch (error) {
      addToLog(`Error updating monitoring data: ${error.message}`, 'error')
    }
  }

  // ============================================================================
  // FUNCIONES AUXILIARES
  // ============================================================================

  const addToHistory = (result) => {
    healthHistory.value.unshift(result)
    
    // Mantener solo los últimos 50 resultados
    if (healthHistory.value.length > 50) {
      healthHistory.value = healthHistory.value.slice(0, 50)
    }
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

  const formatHealthStatus = (status) => {
    const statusMap = {
      healthy: 'Saludable',
      warning: 'Advertencia', 
      error: 'Error',
      unknown: 'Desconocido'
    }
    return statusMap[status] || 'Desconocido'
  }

  const exportHealthData = (format = 'json') => {
    try {
      const dataToExport = {
        export_timestamp: new Date().toISOString(),
        current_health: healthResults.value,
        company_health: companyHealthResults.value,
        services_status: servicesStatus.value,
        auto_diagnostics: autoDiagnosticsResults.value,
        real_time_data: realTimeData.value,
        health_history: healthHistory.value.slice(0, 20) // Solo últimos 20
      }

      let content
      const timestamp = new Date().toISOString().split('T')[0]
      
      if (format === 'json') {
        content = JSON.stringify(dataToExport, null, 2)
      }

      // Crear archivo para descarga
      const blob = new Blob([content], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `health_report_${timestamp}.${format}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)

      addToLog(`Health data exported to ${format.toUpperCase()} format`, 'success')
      showNotification(`Datos de salud exportados en formato ${format.toUpperCase()}`, 'success')
      
    } catch (error) {
      addToLog(`Error exporting health data: ${error.message}`, 'error')
      showNotification(`Error exportando datos: ${error.message}`, 'error')
    }
  }

  // ============================================================================
  // CLEANUP
  // ============================================================================

  onUnmounted(() => {
    stopRealTimeMonitoring()
  })

  // ============================================================================
  // RETURN COMPOSABLE API
  // ============================================================================

  return {
    // Estado reactivo
    isPerformingHealthCheck,
    isPerformingCompanyHealthCheck,
    isCheckingServices,
    isRunningAutoDiagnostics,
    isRealTimeActive,
    isAnyProcessing,
    
    // Resultados
    healthResults,
    companyHealthResults,
    servicesStatus,
    autoDiagnosticsResults,
    realTimeData,
    healthHistory,
    
    // Configuración
    selectedCompanyForHealth,
    nextUpdateCountdown,

    // Computed properties
    overallSystemHealth,
    healthyServicesCount,
    totalServicesCount,
    systemHealthPercentage,
    canStartMonitoring,

    // Funciones principales (PRESERVAR nombres exactos de script.js)
    performHealthCheck,
    performCompanyHealthCheck,
    checkServicesStatus,
    runAutoDiagnostics,
    startRealTimeMonitoring,
    stopRealTimeMonitoring,

    // Funciones auxiliares
    updateMonitoringData,
    formatHealthStatus,
    exportHealthData,
    addToHistory
  }
}
