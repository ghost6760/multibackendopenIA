/**
 * usePrompts.js - Composable para Gestión de Prompts - CORREGIDO
 * MIGRADO DE: script.js funciones con ENDPOINTS EXACTOS
 * CORRECIÓN: Usar endpoints que realmente existen en el backend
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
  // FUNCIONES PRINCIPALES - ENDPOINTS CORREGIDOS SEGÚN SCRIPT.JS
  // ============================================================================

  /**
   * Carga los prompts actuales - ENDPOINT CORREGIDO
   * ORIGINAL: `/api/admin/prompts?company_id=${currentCompanyId}` ✅
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

      // ✅ ENDPOINT CORRECTO - Exacto del script.js funcional
      const response = await apiRequest(`/api/admin/prompts?company_id=${appStore.currentCompanyId}`, {
        method: 'GET'
      })

      if (response && response.agents) {
        prompts.value = response.agents
        lastUpdateTime.value = new Date().toISOString()

        // Actualizar DOM para compatibilidad con script.js
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
            
            if (fallbackLevel && fallbackLevel !== 'postgresql') {
              statusText += ` - Fallback: ${fallbackLevel}`
            }
            
            statusDiv.textContent = statusText
            statusDiv.className = `prompt-status ${isCustom ? 'custom' : 'default'} ${fallbackLevel}`
          }
        })

        addToLog(`Prompts loaded successfully (${Object.keys(response.agents).length} agents)`, 'success')
        return response

      } else {
        showNotification('No se encontraron prompts. Puedes crear prompts personalizados.', 'info')
      }

    } catch (error) {
      addToLog(`Error loading prompts: ${error.message}`, 'error')
      showNotification('Error al cargar prompts: ' + error.message, 'error')

      // Habilitar textareas para crear nuevos prompts
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
   * Actualiza un prompt - ENDPOINT CORRECTO
   * ORIGINAL: `/api/admin/prompts/${agentName}` ✅
   */
  const updatePrompt = async (agentName, promptContent = null) => {
    if (!appStore.currentCompanyId) {
      showNotification('Por favor selecciona una empresa primero', 'warning')
      return false
    }

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

      // ✅ ENDPOINT CORRECTO - Exacto del script.js funcional
      const response = await apiRequest(`/api/admin/prompts/${agentName}`, {
        method: 'PUT',
        body: {
          company_id: appStore.currentCompanyId,
          prompt_template: promptContent
        }
      })

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
   * Resetea un prompt - ENDPOINT CORRECTO
   * ORIGINAL: DELETE `/api/admin/prompts/${agentName}?company_id=${currentCompanyId}` ✅
   */
  const resetPrompt = async (agentName) => {
    if (!appStore.currentCompanyId) {
      showNotification('Por favor selecciona una empresa primero', 'warning')
      return false
    }

    if (!confirm(`¿Estás seguro de restaurar el prompt por defecto para ${agentName}?`)) {
      return false
    }

    try {
      isResetting.value = true
      addToLog(`Resetting prompt for ${agentName} in company ${appStore.currentCompanyId}`, 'info')

      // ✅ ENDPOINT CORRECTO - Exacto del script.js funcional
      const response = await apiRequest(`/api/admin/prompts/${agentName}?company_id=${appStore.currentCompanyId}`, {
        method: 'DELETE'
      })

      showNotification(`Prompt de ${agentName} restaurado al valor por defecto`, 'success')
      addToLog(`Prompt ${agentName} reset successfully`, 'success')

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
   * Vista previa de prompt - CORREGIDO PARA USAR CONVERSACIONES
   * NOTA: No existe /api/admin/prompts/preview en script.js original
   * El script.js usa el sistema de conversaciones para preview
   */
  const previewPrompt = async (agentName = null, testMessage = null) => {
    if (!appStore.currentCompanyId) {
      showNotification('Por favor selecciona una empresa primero', 'warning')
      return null
    }
  
    try {
      isPreviewing.value = true
      let promptTemplate, messageToTest
  
      if (agentName) {
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
      }
  
      if (!promptTemplate) {
        showNotification('El prompt no puede estar vacío', 'error')
        return null
      }
  
      addToLog(`Previewing prompt for ${agentName}`, 'info')
  
      // ✅ USAR SISTEMA DE CONVERSACIONES COMO EN SCRIPT.JS ORIGINAL
      // El script.js original no tiene endpoint de preview específico
      // Usar el sistema de test de conversaciones
      const response = await apiRequest(`/api/conversations/test_preview/test`, {
        method: 'POST',
        body: {
          message: messageToTest,
          company_id: appStore.currentCompanyId,
          agent_name: agentName,
          custom_prompt: promptTemplate
        }
      })
  
      previewData.value = {
        agentName,
        promptTemplate,
        testMessage: messageToTest,
        response,
        timestamp: new Date().toISOString()
      }
  
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
   * Carga estado del sistema - ENDPOINT CORREGIDO
   * ORIGINAL: `/api/admin/status` NO `/api/admin/prompts/status` ✅
   */
  const loadPromptsSystemStatus = async () => {
    try {
      addToLog('Loading prompts system status', 'info')
  
      // ✅ ENDPOINT CORRECTO - Como en script.js funcional
      const response = await apiRequest('/api/admin/status', {
        method: 'GET'
      })
  
      if (response && response.prompt_system) {
        systemStatus.value = response.prompt_system
        updateSystemStatusDisplay(response.prompt_system)
      } else {
        systemStatus.value = response
      }
      
      return response
  
    } catch (error) {
      addToLog(`Error loading prompts system status: ${error.message}`, 'error')
      return null
    }
  }

  /**
   * Actualizar visualización del estado del sistema
   */
  const updateSystemStatusDisplay = (systemStatusData, fallbackUsed = null) => {
    const statusContainer = document.getElementById('promptsSystemStatus')
    if (!statusContainer) return

    const isHealthy = systemStatusData?.postgresql_available && systemStatusData?.tables_exist
    const statusClass = isHealthy ? 'success' : 'warning'
    const statusText = isHealthy ? '✅ Sistema Saludable' : '⚠️ Sistema con Problemas'
    const fallbackText = fallbackUsed ? '(usando fallback)' : ''

    statusContainer.innerHTML = `
      <div class="system-status ${statusClass}">
        <span>${statusText} ${fallbackText}</span>
        <small>Base de datos: ${systemStatusData?.database_status || 'unknown'}</small>
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
    lastUpdateTime,

    // Computed properties
    promptsArray,
    customPrompts,
    defaultPrompts,
    promptsCount,
    hasPrompts,
    isSystemHealthy,

    // Funciones principales (ENDPOINTS CORREGIDOS)
    loadCurrentPrompts,
    updatePrompt,
    resetPrompt,
    previewPrompt,
    loadPromptsSystemStatus,
    updateSystemStatusDisplay,

    // Funciones auxiliares
    getPromptById,
    exportPrompts,
    searchPrompts
  }
}
