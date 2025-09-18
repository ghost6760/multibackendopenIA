/**
 * usePrompts.js - Composable para Gestión de Prompts
 * MIGRADO DE: script.js funciones loadCurrentPrompts(), updatePrompt(), resetPrompt(), previewPrompt(), etc.
 * PRESERVAR: Comportamiento exacto de las funciones originales
 * COMPATIBILIDAD: 100% con el script.js original y backend Flask
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
  // ESTADO LOCAL - ESTRUCTURA COMPATIBLE CON SCRIPT.JS ORIGINAL
  // ============================================================================

  // IMPORTANTE: Mantener como objeto (no array) para compatibilidad con backend
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
  // COMPUTED PROPERTIES - CONVERSIÓN PARA COMPATIBILIDAD CON COMPONENTE
  // ============================================================================

  /**
   * Convierte el objeto de prompts en array para usar en componentes
   * Mantiene compatibilidad con estructura original del backend
   */
  const promptsArray = computed(() => {
    if (!prompts.value || Object.keys(prompts.value).length === 0) {
      return []
    }

    return Object.entries(prompts.value).map(([agentName, promptData]) => {
      const agent = promptData.agent || {}
      
      return {
        name: agentName,
        displayName: agent.display_name || agentName.replace('Agent', '').replace(/([A-Z])/g, ' $1').trim(),
        content: promptData.current_prompt || '',
        isCustom: promptData.is_custom || false,
        isModified: false, // Se manejará en el componente
        lastModified: promptData.last_modified || null,
        version: promptData.version || null,
        fallbackLevel: promptData.fallback_level || null,
        category: agent.category || 'General',
        description: agent.description || '',
        supports_repair: agent.supports_repair !== false
      }
    })
  })

  const customPrompts = computed(() => {
    return promptsArray.value.filter(prompt => prompt.isCustom)
  })

  const defaultPrompts = computed(() => {
    return promptsArray.value.filter(prompt => !prompt.isCustom)
  })

  const promptsCount = computed(() => {
    return Object.keys(prompts.value).length
  })

  const hasPrompts = computed(() => {
    return promptsCount.value > 0
  })

  const isSystemHealthy = computed(() => {
    return systemStatus.value?.healthy === true
  })

  // ============================================================================
  // FUNCIONES PRINCIPALES - PRESERVAR COMPORTAMIENTO EXACTO DE SCRIPT.JS
  // ============================================================================

  /**
   * Carga prompts actuales - MIGRADO: loadCurrentPrompts() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const loadCurrentPrompts = async () => {
    if (!appStore.currentCompanyId) {
      showNotification('Por favor selecciona una empresa primero', 'warning')
      return false
    }

    try {
      isLoading.value = true
      addToLog(`Loading prompts for company: ${appStore.currentCompanyId}`, 'info')

      // PRESERVAR: Endpoint exacto como script.js
      const response = await apiRequest('/api/admin/prompts', {
        method: 'GET'
      })

      if (response && response.agents) {
        // PRESERVAR: Estructura de datos exacta como script.js
        prompts.value = response.agents
        lastUpdateTime.value = new Date().toISOString()

        // PRESERVAR: Actualizar DOM como script.js original
        Object.entries(response.agents).forEach(([agentName, agentData]) => {
          const promptEditor = document.getElementById(`prompt-${agentName}`)
          if (promptEditor) {
            promptEditor.value = agentData.current_prompt || ''
            promptEditor.disabled = false
          }

          // PRESERVAR: Actualizar indicador de estado como script.js
          const statusDiv = document.getElementById(`status-${agentName}`)
          if (statusDiv) {
            const isCustom = agentData.is_custom
            const lastModified = agentData.last_modified
            const fallbackLevel = agentData.fallback_level
            
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
      addToLog(`Prompt updated: ${agentName} v${response.version || 'unknown'}`, 'success')

      // PRESERVAR: Actualizar datos locales
      if (prompts.value[agentName]) {
        prompts.value[agentName] = {
          ...prompts.value[agentName],
          current_prompt: promptContent,
          is_custom: true,
          last_modified: new Date().toISOString(),
          version: response.version
        }
      }

      // PRESERVAR: Actualizar indicador de estado en DOM como script.js
      const statusDiv = document.getElementById(`status-${agentName}`)
      if (statusDiv) {
        statusDiv.textContent = `✅ Personalizado (${new Date().toLocaleDateString()})`
        statusDiv.className = 'prompt-status custom'
      }

      return true

    } catch (error) {
      addToLog(`Error updating prompt ${agentName}: ${error.message}`, 'error')
      showNotification('Error al actualizar prompt: ' + error.message, 'error')
      return false

    } finally {
      isUpdating.value = false
    }
  }

  /**
   * Restaura un prompt - MIGRADO: resetPrompt() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const resetPrompt = async (agentName) => {
    if (!appStore.currentCompanyId) {
      showNotification('Por favor selecciona una empresa primero', 'warning')
      return false
    }

    if (!confirm(`¿Estás seguro de restaurar el prompt de ${agentName} a su estado original?`)) {
      return false
    }

    try {
      isResetting.value = true
      addToLog(`Resetting prompt for ${agentName}`, 'info')

      // PRESERVAR: Request exacto como script.js
      const response = await apiRequest(`/api/admin/prompts/${agentName}`, {
        method: 'DELETE',
        body: {
          company_id: appStore.currentCompanyId
        }
      })

      showNotification(`Prompt de ${agentName} restaurado exitosamente`, 'success')
      addToLog(`Prompt reset: ${agentName}`, 'success')

      // PRESERVAR: Recargar prompts después del reset
      await loadCurrentPrompts()

      return true

    } catch (error) {
      addToLog(`Error resetting prompt ${agentName}: ${error.message}`, 'error')
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
  const previewPrompt = async (promptData) => {
    const agentName = typeof promptData === 'string' ? promptData : promptData.name
    
    try {
      isPreviewing.value = true
      addToLog(`Generating preview for ${agentName}`, 'info')

      let promptContent = ''
      
      if (typeof promptData === 'string') {
        // Si se pasa solo el nombre, obtener del DOM
        const textarea = document.getElementById(`prompt-${agentName}`)
        promptContent = textarea ? textarea.value : ''
      } else {
        // Si se pasa objeto, usar su contenido
        promptContent = promptData.content || ''
      }

      if (!promptContent.trim()) {
        showNotification('No hay contenido de prompt para generar vista previa', 'warning')
        return
      }

      // PRESERVAR: Para script.js, la vista previa es simple
      // Si el backend tiene endpoint de preview, usarlo. Si no, mostrar contenido básico
      try {
        const response = await apiRequest(`/api/admin/prompts/${agentName}/preview`, {
          method: 'POST',
          body: {
            company_id: appStore.currentCompanyId,
            prompt_content: promptContent,
            test_message: 'Mensaje de prueba para vista previa'
          }
        })

        previewData.value = {
          name: agentName,
          displayName: promptData.displayName || agentName,
          content: promptContent,
          preview_result: response
        }

      } catch (previewError) {
        // Si no hay endpoint de preview, mostrar vista previa simple
        addToLog(`Preview endpoint not available, showing simple preview`, 'info')
        
        previewData.value = {
          name: agentName,
          displayName: promptData.displayName || agentName,
          content: promptContent,
          preview_result: null
        }
      }

      addToLog(`Preview generated for ${agentName}`, 'info')

    } catch (error) {
      addToLog(`Error generating preview for ${agentName}: ${error.message}`, 'error')
      showNotification(`Error generando vista previa: ${error.message}`, 'error')
      
      // Mostrar vista previa simple sin procesamiento
      previewData.value = {
        name: agentName,
        displayName: promptData.displayName || agentName,
        content: promptData.content || '',
        preview_result: null
      }

    } finally {
      isPreviewing.value = false
    }
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

      // PRESERVAR: Request como script.js (endpoint puede no existir aún)
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
      showNotification('Iniciando migración a PostgreSQL...', 'info')

      // PRESERVAR: Request como script.js (endpoint puede no existir aún)
      const response = await apiRequest('/api/admin/prompts/migrate', {
        method: 'POST',
        body: {
          company_id: appStore.currentCompanyId
        }
      })

      migrationResults.value = response
      
      showNotification('Migración a PostgreSQL completada', 'success')
      addToLog('Prompts migration to PostgreSQL completed', 'success')

      // Recargar prompts después de la migración
      await loadCurrentPrompts()
      
      return true

    } catch (error) {
      addToLog(`Error migrating prompts: ${error.message}`, 'error')
      showNotification('Error en migración: ' + error.message, 'error')
      return false

    } finally {
      isMigrating.value = false
    }
  }

  /**
   * Carga el estado del sistema de prompts - MIGRADO: loadPromptsSystemStatus() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const loadPromptsSystemStatus = async () => {
    try {
      addToLog('Loading prompts system status', 'info')
      
      // PRESERVAR: Endpoint como script.js (puede no existir aún)
      const response = await apiRequest('/api/admin/prompts/status', {
        method: 'GET'
      })

      systemStatus.value = response.status || response
      addToLog('Prompts system status loaded', 'info')
      
      return response

    } catch (error) {
      addToLog(`Error loading prompts system status: ${error.message}`, 'error')
      // No mostrar error al usuario, solo log
      systemStatus.value = null
      return null
    }
  }

  // ============================================================================
  // FUNCIONES AUXILIARES
  // ============================================================================

  const getPromptById = (agentName) => {
    return prompts.value[agentName] || null
  }

  const exportPrompts = (format = 'json') => {
    try {
      const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '')
      let exportData
      let blob
      
      if (format === 'json') {
        exportData = JSON.stringify(prompts.value, null, 2)
        blob = new Blob([exportData], { type: 'application/json' })
      } else if (format === 'csv') {
        // Crear CSV simple
        const headers = 'Agent,Content,Is_Custom,Last_Modified\n'
        const rows = Object.entries(prompts.value).map(([agentName, data]) => {
          const content = (data.current_prompt || '').replace(/"/g, '""')
          return `"${agentName}","${content}","${data.is_custom}","${data.last_modified || ''}"`
        }).join('\n')
        exportData = headers + rows
        blob = new Blob([exportData], { type: 'text/csv' })
      }

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
      prompt.displayName.toLowerCase().includes(lowerQuery) ||
      (prompt.content || '').toLowerCase().includes(lowerQuery)
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
    repairPrompts,
    migratePromptsToPostgreSQL,
    loadPromptsSystemStatus,

    // Funciones auxiliares
    getPromptById,
    exportPrompts,
    searchPrompts
  }
}
