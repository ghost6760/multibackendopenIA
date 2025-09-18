/**
 * usePrompts.js - Composable para Gestión de Prompts
 * MIGRADO DE: script.js funciones loadCurrentPrompts(), updatePrompt(), resetPrompt(), previewPrompt(), etc.
 * PRESERVAR: Comportamiento exacto de las funciones originales
 * COMPATIBILIDAD: 100% con el script.js original
 */

import { ref, computed, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'
import { useSystemLog } from '@/composables/useSystemLog'

export const usePrompts = () => {
  const appStore = useAppStore()
  const { apiRequest } = useApiRequest()
  const { showNotification } = useNotifications()
  const { addToLog } = useSystemLog()

  // ============================================================================
  // ESTADO LOCAL
  // ============================================================================

  const prompts = ref({})
  const isLoading = ref(false)
  const isUpdating = ref(false)
  const isResetting = ref(false)
  const isPreviewing = ref(false)
  const isRepairing = ref(false)
  const isMigrating = ref(false)
  
  const systemStatus = ref(null)
  const previewData = ref(null)
  const repairResults = ref(null)
  const migrationResults = ref(null)
  const lastUpdateTime = ref(null)

  // ============================================================================
  // COMPUTED PROPERTIES
  // ============================================================================

  const promptsArray = computed(() => {
    return Object.entries(prompts.value).map(([agentName, agentData]) => ({
      id: agentName,
      name: agentName,
      ...agentData
    }))
  })

  const customPrompts = computed(() => {
    return promptsArray.value.filter(prompt => prompt.is_custom)
  })

  const defaultPrompts = computed(() => {
    return promptsArray.value.filter(prompt => !prompt.is_custom)
  })

  const promptsCount = computed(() => ({
    total: promptsArray.value.length,
    custom: customPrompts.value.length,
    default: defaultPrompts.value.length
  }))

  const hasPrompts = computed(() => promptsArray.value.length > 0)

  const isSystemHealthy = computed(() => {
    return systemStatus.value?.database_status === 'healthy' && 
           !systemStatus.value?.fallback_used
  })

  // ============================================================================
  // FUNCIONES PRINCIPALES MIGRADAS DEL SCRIPT.JS
  // ============================================================================

  /**
   * Carga los prompts actuales - MIGRADO: loadCurrentPrompts() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const loadCurrentPrompts = async () => {
    if (!appStore.currentCompanyId) {
      showNotification('Por favor selecciona una empresa primero', 'warning')
      return
    }

    if (isLoading.value) return

    try {
      isLoading.value = true
      addToLog(`Loading prompts for company ${appStore.currentCompanyId}`, 'info')

      // PRESERVAR: Llamada API exacta como script.js
      const response = await apiRequest(`/api/admin/prompts?company_id=${appStore.currentCompanyId}`, {
        method: 'GET'
      })

      if (response && response.agents) {
        prompts.value = response.agents
        lastUpdateTime.value = new Date().toISOString()

        // PRESERVAR: Actualizar cache como script.js
        appStore.cache.prompts = response.agents
        appStore.cache.lastUpdate.prompts = Date.now()

        // PRESERVAR: Actualizar estado del sistema como script.js
        if (response.database_status) {
          systemStatus.value = {
            database_status: response.database_status,
            fallback_used: response.fallback_used || false
          }
        }

        // PRESERVAR: Actualizar textareas en DOM como script.js
        Object.entries(response.agents).forEach(([agentName, agentData]) => {
          const textarea = document.getElementById(`prompt-${agentName}`)
          const statusDiv = document.getElementById(`status-${agentName}`)
          
          if (textarea) {
            textarea.value = agentData.current_prompt || ''
            textarea.disabled = false
          }
          
          if (statusDiv) {
            const isCustom = agentData.is_custom || false
            const lastModified = agentData.last_modified
            const fallbackLevel = agentData.fallback_level || 'unknown'
            
            let statusText = isCustom ? 
              `✅ Personalizado${lastModified ? ` (${new Date(lastModified).toLocaleDateString()})` : ''}` : 
              '🔵 Por defecto'
            
            // PRESERVAR: Indicador de nivel de fallback como script.js
            if (fallbackLevel && fallbackLevel !== 'postgresql') {
              statusText += ` - Fallback: ${fallbackLevel}`
            }
            
            statusDiv.textContent = statusText
            statusDiv.className = `prompt-status ${isCustom ? 'custom' : 'default'} ${fallbackLevel}`
          }
        })

        addToLog(`Prompts loaded successfully (${Object.keys(response.agents).length} agents)`, 'success')
        
      } else {
        showNotification('No se encontraron prompts. Puedes crear prompts personalizados.', 'info')
      }

      return response

    } catch (error) {
      addToLog(`Error loading prompts: ${error.message}`, 'error')
      showNotification('Error al cargar prompts: ' + error.message, 'error')

      // PRESERVAR: Habilitar textareas para crear nuevos prompts como script.js
      document.querySelectorAll('.prompt-editor').forEach(textarea => {
        textarea.value = 'Error al cargar el prompt. Puedes escribir uno nuevo aquí.'
        textarea.disabled = false
      })

      throw error

    } finally {
      isLoading.value = false
    }
  }

  /**
   * Actualiza un prompt - MIGRADO: updatePrompt() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const updatePrompt = async (agentName, promptContent = null) => {
    if (!appStore.currentCompanyId) {
      showNotification('Por favor selecciona una empresa primero', 'warning')
      return false
    }

    // Si no se pasa contenido, obtenerlo del DOM como script.js
    if (!promptContent) {
      const textarea = document.getElementById(`prompt-${agentName}`)
      if (!textarea) {
        showNotification(`Error: No se encontró el textarea para ${agentName}`, 'error')
        return false
      }
      promptContent = textarea.value.trim()
    }

    if (!promptContent) {
      showNotification('El prompt no puede estar vacío', 'error')
      return false
    }

    try {
      isUpdating.value = true
      addToLog(`Updating prompt for ${agentName} in company ${appStore.currentCompanyId}`, 'info')

      // PRESERVAR: Request exacto como script.js
      const response = await apiRequest(`/api/admin/prompts/${agentName}`, {
        method: 'PUT',
        body: {
          company_id: appStore.currentCompanyId,
          prompt_template: promptContent
        }
      })

      // PRESERVAR: Mensaje de éxito con versión como script.js
      let successMessage = `Prompt de ${agentName} actualizado exitosamente`
      if (response.version) {
        successMessage += ` (v${response.version})`
      }

      showNotification(successMessage, 'success')
      addToLog(`Prompt ${agentName} updated successfully`, 'info')

      // Actualizar prompts locales
      if (prompts.value[agentName]) {
        prompts.value[agentName] = {
          ...prompts.value[agentName],
          current_prompt: promptContent,
          is_custom: true,
          last_modified: new Date().toISOString()
        }
      }

      // Recargar estado para obtener datos frescos
      await loadCurrentPrompts()
      
      return true

    } catch (error) {
      addToLog(`Error updating prompt: ${error.message}`, 'error')
      showNotification('Error al actualizar prompt: ' + error.message, 'error')
      return false

    } finally {
      isUpdating.value = false
    }
  }

  /**
   * Resetea un prompt - MIGRADO: resetPrompt() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const resetPrompt = async (agentName) => {
    if (!appStore.currentCompanyId) {
      showNotification('Por favor selecciona una empresa primero', 'warning')
      return false
    }

    // PRESERVAR: Confirmación como script.js
    if (!confirm(`¿Estás seguro de restaurar el prompt por defecto para ${agentName}?`)) {
      return false
    }

    try {
      isResetting.value = true
      addToLog(`Resetting prompt for ${agentName} in company ${appStore.currentCompanyId}`, 'info')

      // PRESERVAR: Request exacto como script.js
      const response = await apiRequest(`/api/admin/prompts/${agentName}?company_id=${appStore.currentCompanyId}`, {
        method: 'DELETE'
      })

      showNotification(`Prompt de ${agentName} restaurado al valor por defecto`, 'success')
      addToLog(`Prompt ${agentName} reset successfully`, 'success')

      // Recargar prompts
      await loadCurrentPrompts()
      
      return true

    } catch (error) {
      addToLog(`Error resetting prompt: ${error.message}`, 'error')
      showNotification('Error al restaurar prompt: ' + error.message, 'error')
      return false

    } finally {
      isResetting.value = false
    }
  }

  /**
   * Vista previa de prompt - MIGRADO: previewPrompt() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const previewPrompt = async (agentName = null, testMessage = null) => {
    if (!appStore.currentCompanyId) {
      showNotification('Por favor selecciona una empresa primero', 'warning')
      return null
    }

    try {
      isPreviewing.value = true
      let promptTemplate, messageToTest

      // PRESERVAR: Lógica de obtención de datos como script.js
      if (agentName) {
        // CASO 1: Llamada desde botón en grid de prompts
        const textarea = document.getElementById(`prompt-${agentName}`)
        if (!textarea) {
          showNotification(`Error: No se encontró el textarea para ${agentName}`, 'error')
          return null
        }
        promptTemplate = textarea.value.trim()
        
        if (!testMessage) {
          messageToTest = prompt('Introduce un mensaje de prueba:', '¿Cuánto cuesta un tratamiento?')
          if (!messageToTest) {
            showNotification('Operación cancelada', 'info')
            return null
          }
        } else {
          messageToTest = testMessage
        }
      } else {
        // CASO 2: Llamada desde modal de edición
        const agentSelect = document.getElementById('editAgent')
        const promptTextarea = document.getElementById('editPrompt')
        const messageInput = document.getElementById('previewMessage')
        
        if (!agentSelect || !promptTextarea) {
          showNotification('Error: Elementos de edición no encontrados. Usa el botón "Vista Previa" desde la lista de prompts.', 'error')
          return null
        }
        
        agentName = agentSelect.value
        promptTemplate = promptTextarea.value.trim()
        messageToTest = messageInput ? messageInput.value.trim() : '¿Cuánto cuesta un tratamiento?'
      }

      if (!promptTemplate) {
        showNotification('El prompt no puede estar vacío', 'error')
        return null
      }

      if (!messageToTest) {
        showNotification('El mensaje de prueba no puede estar vacío', 'error')
        return null
      }

      addToLog(`Previewing prompt for ${agentName}`, 'info')

      // PRESERVAR: Request exacto como script.js
      const response = await apiRequest(`/api/admin/prompts/${agentName}/preview`, {
        method: 'POST',
        body: {
          company_id: appStore.currentCompanyId,
          prompt_template: promptTemplate,
          test_message: messageToTest
        }
      })

      previewData.value = {
        agentName,
        promptTemplate,
        testMessage: messageToTest,
        response,
        timestamp: new Date().toISOString()
      }

      // PRESERVAR: Mostrar modal como script.js
      showPreviewModal(response)
      
      addToLog(`Prompt preview completed for ${agentName}`, 'success')
      
      return response

    } catch (error) {
      addToLog(`Error previewing prompt: ${error.message}`, 'error')
      showNotification('Error en vista previa: ' + error.message, 'error')
      return null

    } finally {
      isPreviewing.value = false
    }
  }

  /**
   * Muestra modal de vista previa - MIGRADO: showPreviewModal() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const showPreviewModal = (data) => {
    // PRESERVAR: Crear modal exacto como script.js
    const modalHtml = `
      <div id="previewModal" class="modal" style="display: block;">
        <div class="modal-content">
          <div class="modal-header">
            <h3>Vista Previa del Prompt</h3>
            <span class="close" onclick="closeModal()">&times;</span>
          </div>
          <div class="modal-body">
            <div class="json-container">
              <pre>${JSON.stringify(data, null, 2)}</pre>
            </div>
          </div>
          <div class="modal-footer">
            <button onclick="closeModal()" class="btn btn-secondary">Cerrar</button>
          </div>
        </div>
      </div>
    `

    // Remover modal existente si hay
    const existingModal = document.getElementById('previewModal')
    if (existingModal) {
      existingModal.remove()
    }

    // Agregar nuevo modal
    document.body.insertAdjacentHTML('beforeend', modalHtml)
  }

  /**
   * Repara prompts - MIGRADO: repairPrompts() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const repairPrompts = async (specificAgent = null) => {
    if (!appStore.currentCompanyId) {
      showNotification('Por favor selecciona una empresa primero', 'warning')
      return false
    }

    try {
      isRepairing.value = true
      
      const actionText = specificAgent ? 
        `Reparando prompt de ${specificAgent}` : 
        'Reparando todos los prompts'
      
      addToLog(actionText, 'info')
      showNotification(actionText + '...', 'info')

      // PRESERVAR: Request como script.js (aunque esta función parece estar en desarrollo)
      const endpoint = specificAgent ? 
        `/api/admin/prompts/${specificAgent}/repair` : 
        '/api/admin/prompts/repair'
      
      const response = await apiRequest(endpoint, {
        method: 'POST',
        body: {
          company_id: appStore.currentCompanyId
        }
      })

      repairResults.value = response
      
      showNotification('Reparación de prompts completada', 'success')
      addToLog('Prompts repair completed', 'success')

      // Recargar prompts después de la reparación
      await loadCurrentPrompts()
      
      return true

    } catch (error) {
      addToLog(`Error repairing prompts: ${error.message}`, 'error')
      showNotification('Error en reparación de prompts: ' + error.message, 'error')
      return false

    } finally {
      isRepairing.value = false
    }
  }

  /**
   * Migra prompts a PostgreSQL - MIGRADO: migratePromptsToPostgreSQL() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const migratePromptsToPostgreSQL = async () => {
    if (!appStore.currentCompanyId) {
      showNotification('Por favor selecciona una empresa primero', 'warning')
      return false
    }

    if (!confirm('¿Estás seguro de migrar los prompts a PostgreSQL? Esta operación puede tomar tiempo.')) {
      return false
    }

    try {
      isMigrating.value = true
      addToLog('Starting prompts migration to PostgreSQL', 'info')
      showNotification('Iniciando migración de prompts a PostgreSQL...', 'info')

      // PRESERVAR: Request como script.js
      const response = await apiRequest('/api/admin/prompts/migrate', {
        method: 'POST',
        body: {
          company_id: appStore.currentCompanyId,
          target: 'postgresql'
        }
      })

      migrationResults.value = response
      
      showNotification('Migración de prompts completada exitosamente', 'success')
      addToLog('Prompts migration to PostgreSQL completed', 'success')

      // Recargar prompts después de la migración
      await loadCurrentPrompts()
      await loadPromptsSystemStatus()
      
      return true

    } catch (error) {
      addToLog(`Error migrating prompts: ${error.message}`, 'error')
      showNotification('Error en migración de prompts: ' + error.message, 'error')
      return false

    } finally {
      isMigrating.value = false
    }
  }

  /**
   * Carga estado del sistema de prompts - MIGRADO: loadPromptsSystemStatus() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const loadPromptsSystemStatus = async () => {
    try {
      addToLog('Loading prompts system status', 'info')

      // PRESERVAR: Request como script.js
      const response = await apiRequest('/api/admin/prompts/status', {
        method: 'GET'
      })

      systemStatus.value = response

      // PRESERVAR: Actualizar display como script.js
      updateSystemStatusDisplay(response.database_status, response.fallback_used)
      
      return response

    } catch (error) {
      addToLog(`Error loading prompts system status: ${error.message}`, 'error')
      return null
    }
  }

  /**
   * Actualiza visualización del estado del sistema - MIGRADO de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const updateSystemStatusDisplay = (databaseStatus, fallbackUsed) => {
    const statusContainer = document.getElementById('promptsSystemStatus')
    if (!statusContainer) return

    const statusClass = databaseStatus === 'healthy' ? 'success' : 'warning'
    const statusText = databaseStatus === 'healthy' ? '✅ Sistema Saludable' : '⚠️ Sistema con Problemas'
    const fallbackText = fallbackUsed ? '(usando fallback)' : ''

    statusContainer.innerHTML = `
      <div class="system-status ${statusClass}">
        <span>${statusText} ${fallbackText}</span>
        <small>Base de datos: ${databaseStatus}</small>
      </div>
    `
  }

  // ============================================================================
  // FUNCIONES AUXILIARES
  // ============================================================================

  const getPromptById = (agentName) => {
    return prompts.value[agentName] || null
  }

  const exportPrompts = (format = 'json') => {
    try {
      const dataToExport = {
        company_id: appStore.currentCompanyId,
        export_timestamp: new Date().toISOString(),
        prompts: prompts.value,
        system_status: systemStatus.value
      }

      let content
      const timestamp = new Date().toISOString().split('T')[0]
      
      if (format === 'json') {
        content = JSON.stringify(dataToExport, null, 2)
      } else if (format === 'csv') {
        const headers = 'Agent,Is_Custom,Current_Prompt,Last_Modified\n'
        content = headers + Object.entries(prompts.value).map(([agent, data]) => 
          `"${agent}","${data.is_custom || false}","${(data.current_prompt || '').replace(/"/g, '""')}","${data.last_modified || ''}"`
        ).join('\n')
      }

      // Crear archivo para descarga
      const blob = new Blob([content], { 
        type: format === 'json' ? 'application/json' : 'text/csv' 
      })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `prompts_${appStore.currentCompanyId}_${timestamp}.${format}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)

      addToLog(`Prompts exported to ${format.toUpperCase()} format`, 'success')
      showNotification(`Prompts exportados en formato ${format.toUpperCase()}`, 'success')
      
    } catch (error) {
      addToLog(`Error exporting prompts: ${error.message}`, 'error')
      showNotification(`Error exportando prompts: ${error.message}`, 'error')
    }
  }

  const searchPrompts = (query) => {
    if (!query.trim()) return promptsArray.value
    
    const lowerQuery = query.toLowerCase()
    return promptsArray.value.filter(prompt => 
      prompt.name.toLowerCase().includes(lowerQuery) ||
      (prompt.current_prompt || '').toLowerCase().includes(lowerQuery)
    )
  }

  // ============================================================================
  // WATCHERS
  // ============================================================================

  // Watcher para recargar cuando cambie la empresa
  watch(() => appStore.currentCompanyId, async (newCompanyId) => {
    if (newCompanyId) {
      await loadCurrentPrompts()
      await loadPromptsSystemStatus()
    }
  })

  // ============================================================================
  // RETURN COMPOSABLE API
  // ============================================================================

  return {
    // Estado reactivo
    prompts,
    isLoading,
    isUpdating,
    isResetting,
    isPreviewing,
    isRepairing,
    isMigrating,
    systemStatus,
    previewData,
    repairResults,
    migrationResults,
    lastUpdateTime,

    // Computed properties
    promptsArray,
    customPrompts,
    defaultPrompts,
    promptsCount,
    hasPrompts,
    isSystemHealthy,

    // Funciones principales (PRESERVAR nombres exactos de script.js)
    loadCurrentPrompts,
    updatePrompt,
    resetPrompt,
    previewPrompt,
    showPreviewModal,
    repairPrompts,
    migratePromptsToPostgreSQL,
    loadPromptsSystemStatus,
    updateSystemStatusDisplay,

    // Funciones auxiliares
    getPromptById,
    exportPrompts,
    searchPrompts
  }
}
