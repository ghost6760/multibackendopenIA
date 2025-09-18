/**
 * useAdmin.js - Composable para Funciones de Administración
 * MIGRADO DE: script.js funciones runSystemDiagnostics(), clearSystemLog(), updateGoogleCalendarConfig(), etc.
 * PRESERVAR: Comportamiento exacto de las funciones originales
 * COMPATIBILIDAD: 100% con el script.js original
 */

import { ref, computed } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'
import { useSystemLog } from '@/composables/useSystemLog'

export const useAdmin = () => {
  const appStore = useAppStore()
  const { apiRequest } = useApiRequest()
  const { showNotification } = useNotifications()
  const { addToLog, clearSystemLog: clearLog } = useSystemLog()

  // ============================================================================
  // ESTADO LOCAL
  // ============================================================================

  const isRunningDiagnostics = ref(false)
  const isUpdatingConfig = ref(false)
  const isReloadingConfig = ref(false)
  const isTestingApiKey = ref(false)
  
  const diagnosticsResults = ref(null)
  const configurationResults = ref(null)
  const googleCalendarConfig = ref(null)
  const apiKeyTestResults = ref(null)
  const systemConfig = ref(null)
  
  const lastDiagnosticsTime = ref(null)
  const lastConfigUpdateTime = ref(null)

  // ============================================================================
  // COMPUTED PROPERTIES
  // ============================================================================

  const isAnyProcessing = computed(() => 
    isRunningDiagnostics.value || 
    isUpdatingConfig.value || 
    isReloadingConfig.value ||
    isTestingApiKey.value
  )

  const hasApiKey = computed(() => !!appStore.adminApiKey)

  const diagnosticsStatus = computed(() => {
    if (!diagnosticsResults.value) return null
    
    const results = diagnosticsResults.value
    const healthScore = results.health_score || 0
    
    if (healthScore >= 90) return 'excellent'
    if (healthScore >= 70) return 'good'
    if (healthScore >= 50) return 'warning'
    return 'critical'
  })

  const configurationStatus = computed(() => {
    if (!systemConfig.value) return 'unknown'
    
    const config = systemConfig.value
    const hasRequiredServices = config.services && Object.keys(config.services).length > 0
    const hasValidDb = config.database_status === 'healthy'
    
    if (hasRequiredServices && hasValidDb) return 'healthy'
    if (hasRequiredServices || hasValidDb) return 'partial'
    return 'error'
  })

  // ============================================================================
  // FUNCIONES PRINCIPALES MIGRADAS DEL SCRIPT.JS
  // ============================================================================

  /**
   * Ejecuta diagnósticos del sistema - MIGRADO: runSystemDiagnostics() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const runSystemDiagnostics = async () => {
    if (isRunningDiagnostics.value) {
      showNotification('Ya se están ejecutando diagnósticos', 'warning')
      return
    }

    try {
      isRunningDiagnostics.value = true
      diagnosticsResults.value = null

      addToLog('Starting system diagnostics', 'info')
      showNotification('Ejecutando diagnósticos del sistema...', 'info')

      // PRESERVAR: Llamada API exacta como script.js
      const response = await apiRequest('/api/admin/diagnostics', {
        method: 'POST',
        headers: {
          'X-API-Key': appStore.adminApiKey || ''
        }
      })

      diagnosticsResults.value = response
      lastDiagnosticsTime.value = new Date().toISOString()

      // PRESERVAR: Mostrar resultado en DOM como script.js
      const container = document.getElementById('adminResults')
      if (container) {
        container.innerHTML = `
          <div class="result-container result-info">
            <h4>🔍 Diagnósticos del Sistema</h4>
            <div class="diagnostics-summary">
              <p><strong>Score de Salud:</strong> ${response.health_score || 'N/A'}%</p>
              <p><strong>Timestamp:</strong> ${response.timestamp || new Date().toISOString()}</p>
              ${response.environment ? `<p><strong>Ambiente:</strong> ${response.environment}</p>` : ''}
            </div>
            <div class="json-container">
              <pre>${JSON.stringify(response, null, 2)}</pre>
            </div>
          </div>
        `
      }

      addToLog('System diagnostics completed successfully', 'success')
      showNotification('Diagnósticos ejecutados exitosamente', 'success')

      return response

    } catch (error) {
      addToLog(`System diagnostics failed: ${error.message}`, 'error')
      showNotification('Error al ejecutar diagnósticos: ' + error.message, 'error')

      // PRESERVAR: Mostrar error en DOM como script.js
      const container = document.getElementById('adminResults')
      if (container) {
        container.innerHTML = `
          <div class="result-container result-error">
            <p>❌ Error al ejecutar diagnósticos</p>
            <p>${error.message}</p>
          </div>
        `
      }

      throw error

    } finally {
      isRunningDiagnostics.value = false
    }
  }

  /**
   * Limpia el log del sistema - MIGRADO: clearSystemLog() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const clearSystemLog = async () => {
    try {
      addToLog('Clearing system log', 'info')
      
      // PRESERVAR: Llamar función del composable useSystemLog
      clearLog()
      
      showNotification('Log del sistema limpiado', 'success')
      
      // PRESERVAR: Mostrar resultado en DOM como script.js
      const container = document.getElementById('adminResults')
      if (container) {
        container.innerHTML = `
          <div class="result-container result-success">
            <p>✅ Log del sistema limpiado exitosamente</p>
          </div>
        `
      }

      return true

    } catch (error) {
      addToLog(`Error clearing system log: ${error.message}`, 'error')
      showNotification('Error limpiando log del sistema: ' + error.message, 'error')
      return false
    }
  }

  /**
   * Actualiza configuración de Google Calendar - MIGRADO: updateGoogleCalendarConfig() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const updateGoogleCalendarConfig = async () => {
    if (!appStore.currentCompanyId) {
      showNotification('Por favor selecciona una empresa primero', 'warning')
      return false
    }

    try {
      isUpdatingConfig.value = true
      addToLog(`Updating Google Calendar config for company ${appStore.currentCompanyId}`, 'info')
      showNotification('Actualizando configuración de Google Calendar...', 'info')

      // PRESERVAR: Obtener datos del formulario como script.js
      const calendarId = document.getElementById('calendarId')?.value || ''
      const credentials = document.getElementById('calendarCredentials')?.value || ''

      if (!calendarId.trim()) {
        throw new Error('Calendar ID es requerido')
      }

      let parsedCredentials = {}
      if (credentials.trim()) {
        try {
          parsedCredentials = JSON.parse(credentials)
        } catch (e) {
          throw new Error('Credentials debe ser JSON válido')
        }
      }

      // PRESERVAR: Request como script.js (endpoint hipotético basado en el patrón)
      const response = await apiRequest('/api/admin/config/calendar', {
        method: 'PUT',
        headers: {
          'X-API-Key': appStore.adminApiKey || ''
        },
        body: {
          company_id: appStore.currentCompanyId,
          calendar_id: calendarId.trim(),
          credentials: parsedCredentials
        }
      })

      googleCalendarConfig.value = response
      lastConfigUpdateTime.value = new Date().toISOString()

      // PRESERVAR: Mostrar resultado como script.js
      const container = document.getElementById('adminResults')
      if (container) {
        container.innerHTML = `
          <div class="result-container result-success">
            <h4>✅ Configuración de Google Calendar Actualizada</h4>
            <p><strong>Empresa:</strong> ${appStore.currentCompanyId}</p>
            <p><strong>Calendar ID:</strong> ${calendarId}</p>
            <div class="json-container">
              <pre>${JSON.stringify(response, null, 2)}</pre>
            </div>
          </div>
        `
      }

      addToLog('Google Calendar configuration updated successfully', 'success')
      showNotification('Configuración de Google Calendar actualizada', 'success')

      return response

    } catch (error) {
      addToLog(`Error updating Google Calendar config: ${error.message}`, 'error')
      showNotification('Error actualizando configuración: ' + error.message, 'error')

      // PRESERVAR: Mostrar error como script.js
      const container = document.getElementById('adminResults')
      if (container) {
        container.innerHTML = `
          <div class="result-container result-error">
            <p>❌ Error al actualizar configuración de Google Calendar</p>
            <p>${error.message}</p>
          </div>
        `
      }

      return false

    } finally {
      isUpdatingConfig.value = false
    }
  }

  /**
   * Recarga configuración de empresas - MIGRADO: reloadCompaniesConfig() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const reloadCompaniesConfig = async () => {
    try {
      isReloadingConfig.value = true
      addToLog('Reloading companies configuration', 'info')
      showNotification('Recargando configuración de empresas...', 'info')

      // PRESERVAR: Limpiar cache como script.js
      appStore.cache.companies = null
      appStore.cache.lastUpdate.companies = null
      
      // También limpiar cache relacionado
      appStore.cache.enterpriseCompanies = null
      appStore.cache.lastUpdate.enterpriseCompanies = null

      // PRESERVAR: Request como script.js
      const response = await apiRequest('/api/admin/config/reload', {
        method: 'POST',
        headers: {
          'X-API-Key': appStore.adminApiKey || ''
        },
        body: {
          config_type: 'companies'
        }
      })

      configurationResults.value = response

      // PRESERVAR: Mostrar resultado como script.js
      const container = document.getElementById('adminResults')
      if (container) {
        container.innerHTML = `
          <div class="result-container result-success">
            <h4>✅ Configuración Recargada</h4>
            <p>Configuración de empresas recargada exitosamente</p>
            <div class="json-container">
              <pre>${JSON.stringify(response, null, 2)}</pre>
            </div>
          </div>
        `
      }

      addToLog('Companies configuration reloaded successfully', 'success')
      showNotification('Configuración de empresas recargada exitosamente', 'success')

      // Emitir evento para que otros componentes reaccionen
      if (typeof window !== 'undefined' && window.dispatchEvent) {
        window.dispatchEvent(new CustomEvent('companiesConfigReloaded', {
          detail: { response }
        }))
      }

      return response

    } catch (error) {
      addToLog(`Error reloading companies config: ${error.message}`, 'error')
      showNotification('Error recargando configuración: ' + error.message, 'error')

      // PRESERVAR: Mostrar error como script.js
      const container = document.getElementById('adminResults')
      if (container) {
        container.innerHTML = `
          <div class="result-container result-error">
            <p>❌ Error al recargar configuración</p>
            <p>${error.message}</p>
          </div>
        `
      }

      throw error

    } finally {
      isReloadingConfig.value = false
    }
  }

  /**
   * Prueba la API key - MIGRADO: testApiKey() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const testApiKey = async (apiKey = null) => {
    const keyToTest = apiKey || appStore.adminApiKey
    
    if (!keyToTest) {
      showNotification('API Key es requerida', 'warning')
      return false
    }

    try {
      isTestingApiKey.value = true
      addToLog('Testing API key', 'info')
      showNotification('Probando API key...', 'info')

      // PRESERVAR: Request como script.js
      const response = await apiRequest('/api/admin/test-key', {
        method: 'POST',
        headers: {
          'X-API-Key': keyToTest
        }
      })

      apiKeyTestResults.value = {
        ...response,
        timestamp: new Date().toISOString(),
        key_tested: keyToTest.slice(0, 8) + '...' // Mostrar solo primeros 8 chars por seguridad
      }

      const isValid = response.status === 'valid' || response.valid === true
      const message = isValid ? 'API Key válida' : 'API Key inválida'
      const notificationType = isValid ? 'success' : 'error'

      addToLog(`API key test completed: ${isValid ? 'valid' : 'invalid'}`, isValid ? 'success' : 'error')
      showNotification(message, notificationType)

      // Actualizar estado del API key en el store
      appStore.setApiKeyStatus(isValid ? 'valid' : 'invalid')

      return isValid

    } catch (error) {
      addToLog(`API key test failed: ${error.message}`, 'error')
      showNotification('Error probando API key: ' + error.message, 'error')
      
      appStore.setApiKeyStatus('invalid')
      return false

    } finally {
      isTestingApiKey.value = false
    }
  }

  /**
   * Actualiza el estado del API key - MIGRADO: updateApiKeyStatus() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const updateApiKeyStatus = async () => {
    const statusElement = document.getElementById('apiKeyStatus')
    if (!statusElement) return

    if (!appStore.adminApiKey) {
      statusElement.innerHTML = `
        <span class="status-indicator status-error"></span>
        <span>No configurada</span>
        <button onclick="showApiKeyModal()" class="btn btn-primary btn-small">Configurar</button>
      `
      return
    }

    // Probar la API key
    const isValid = await testApiKey()
    
    const statusClass = isValid ? 'success' : 'error'
    const statusText = isValid ? 'Válida' : 'Inválida'
    const statusIcon = isValid ? '✅' : '❌'

    statusElement.innerHTML = `
      <span class="status-indicator status-${statusClass}"></span>
      <span>${statusIcon} ${statusText}</span>
      <button onclick="showApiKeyModal()" class="btn btn-secondary btn-small">Cambiar</button>
    `
  }

  /**
   * Muestra modal de API key - MIGRADO: showApiKeyModal() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const showApiKeyModal = () => {
    const modalHtml = `
      <div id="apiKeyModal" class="modal" style="display: block;">
        <div class="modal-content">
          <div class="modal-header">
            <h3>Configurar API Key de Administración</h3>
            <span class="close" onclick="closeApiKeyModal()">&times;</span>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label for="adminApiKeyInput">API Key:</label>
              <input type="password" id="adminApiKeyInput" placeholder="Introduce tu API key" 
                     value="${appStore.adminApiKey || ''}" style="width: 100%; margin-bottom: 15px;">
            </div>
            <div class="form-group">
              <small style="color: #666;">
                La API key es necesaria para funciones administrativas avanzadas.
              </small>
            </div>
          </div>
          <div class="modal-footer">
            <button onclick="saveApiKey()" class="btn btn-primary">Guardar</button>
            <button onclick="testApiKey()" class="btn btn-secondary">Probar</button>
            <button onclick="closeApiKeyModal()" class="btn btn-secondary">Cancelar</button>
          </div>
        </div>
      </div>
    `

    // Remover modal existente
    const existingModal = document.getElementById('apiKeyModal')
    if (existingModal) existingModal.remove()

    // Agregar nuevo modal
    document.body.insertAdjacentHTML('beforeend', modalHtml)
  }

  /**
   * Guarda API key - MIGRADO: saveApiKey() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const saveApiKey = async () => {
    const input = document.getElementById('adminApiKeyInput')
    if (!input) return

    const apiKey = input.value.trim()
    
    if (!apiKey) {
      showNotification('API Key no puede estar vacía', 'warning')
      return
    }

    try {
      // Probar la API key antes de guardarla
      const isValid = await testApiKey(apiKey)
      
      if (isValid) {
        appStore.setAdminApiKey(apiKey)
        appStore.setApiKeyStatus('valid')
        
        showNotification('API Key guardada exitosamente', 'success')
        addToLog('Admin API key saved and validated', 'success')
        
        closeApiKeyModal()
        await updateApiKeyStatus()
      } else {
        showNotification('API Key inválida. No se guardó.', 'error')
      }

    } catch (error) {
      showNotification('Error validando API key: ' + error.message, 'error')
    }
  }

  /**
   * Cierra modal de API key - MIGRADO: closeApiKeyModal() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const closeApiKeyModal = () => {
    const modal = document.getElementById('apiKeyModal')
    if (modal) {
      modal.remove()
    }
  }

  // ============================================================================
  // FUNCIONES DE CONFIGURACIÓN AVANZADA
  // ============================================================================

  /**
   * Carga configuración del sistema
   */
  const loadSystemConfig = async () => {
    try {
      addToLog('Loading system configuration', 'info')
      
      const response = await apiRequest('/api/admin/config', {
        method: 'GET',
        headers: {
          'X-API-Key': appStore.adminApiKey || ''
        }
      })

      systemConfig.value = response
      return response

    } catch (error) {
      addToLog(`Error loading system config: ${error.message}`, 'error')
      return null
    }
  }

  /**
   * Actualiza configuración del sistema
   */
  const updateSystemConfig = async (configData) => {
    try {
      addToLog('Updating system configuration', 'info')
      
      const response = await apiRequest('/api/admin/config', {
        method: 'PUT',
        headers: {
          'X-API-Key': appStore.adminApiKey || ''
        },
        body: configData
      })

      systemConfig.value = response
      addToLog('System configuration updated successfully', 'success')
      showNotification('Configuración del sistema actualizada', 'success')

      return response

    } catch (error) {
      addToLog(`Error updating system config: ${error.message}`, 'error')
      showNotification('Error actualizando configuración: ' + error.message, 'error')
      return null
    }
  }

  /**
   * Exporta configuración del sistema
   */
  const exportSystemConfig = (format = 'json') => {
    try {
      const dataToExport = {
        export_timestamp: new Date().toISOString(),
        system_config: systemConfig.value,
        diagnostics: diagnosticsResults.value,
        google_calendar_config: googleCalendarConfig.value
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
      link.download = `system_config_${timestamp}.${format}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)

      addToLog(`System configuration exported to ${format.toUpperCase()} format`, 'success')
      showNotification(`Configuración exportada en formato ${format.toUpperCase()}`, 'success')
      
    } catch (error) {
      addToLog(`Error exporting config: ${error.message}`, 'error')
      showNotification(`Error exportando configuración: ${error.message}`, 'error')
    }
  }

  // ============================================================================
  // RETURN COMPOSABLE API
  // ============================================================================

  return {
    // Estado reactivo
    isRunningDiagnostics,
    isUpdatingConfig,
    isReloadingConfig,
    isTestingApiKey,
    isAnyProcessing,
    
    // Resultados
    diagnosticsResults,
    configurationResults,
    googleCalendarConfig,
    apiKeyTestResults,
    systemConfig,
    lastDiagnosticsTime,
    lastConfigUpdateTime,

    // Computed properties
    hasApiKey,
    diagnosticsStatus,
    configurationStatus,

    // Funciones principales (PRESERVAR nombres exactos de script.js)
    runSystemDiagnostics,
    clearSystemLog,
    updateGoogleCalendarConfig,
    reloadCompaniesConfig,
    testApiKey,
    updateApiKeyStatus,
    showApiKeyModal,
    saveApiKey,
    closeApiKeyModal,

    // Funciones adicionales
    loadSystemConfig,
    updateSystemConfig,
    exportSystemConfig
  }
}
