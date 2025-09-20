/**
 * usePrompts.js - Composable para Gestión de Prompts
 * MIGRADO DE: PromptsTab.vue - todas las llamadas API
 * PRESERVAR: Comportamiento exacto de las funciones originales
 * COMPATIBILIDAD: 100% con el backend Flask
 */

import { ref, computed, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'

export const usePrompts = () => {
  const appStore = useAppStore()
  const { apiRequest } = useApiRequest()
  const { showNotification } = useNotifications()

  // ============================================================================
  // ESTADO REACTIVO - MIGRADO DE PROMPTSTAB.VUE
  // ============================================================================

  const agents = ref({
    emergency_agent: null,
    router_agent: null,
    sales_agent: null,
    schedule_agent: null,
    support_agent: null
  })

  const isLoadingPrompts = ref(false)
  const isProcessing = ref(false)
  const error = ref(null)

  // Preview state
  const showPreview = ref(false)
  const previewAgent = ref('')
  const previewContent = ref('')
  const previewTestMessage = ref('')
  const previewResponse = ref(null)
  const previewLoading = ref(false)

  // ============================================================================
  // COMPUTED PROPERTIES
  // ============================================================================

  const hasPrompts = computed(() => {
    return Object.keys(agents.value).some(key => agents.value[key] !== null)
  })

  const currentCompanyId = computed(() => {
    return appStore.currentCompanyId
  })

  const currentCompanyName = computed(() => {
    return appStore.currentCompanyName || currentCompanyId.value
  })

  // ============================================================================
  // FUNCIONES PRINCIPALES - MIGRADAS EXACTAS DE PROMPTSTAB.VUE
  // ============================================================================

  /**
   * Carga prompts - MIGRADA EXACTA de PromptsTab.vue loadPrompts()
   */
  const loadPrompts = async () => {
    if (!currentCompanyId.value) {
      error.value = 'Por favor selecciona una empresa primero'
      return
    }

    try {
      isLoadingPrompts.value = true
      error.value = null
      
      console.log(`Loading prompts for company: ${currentCompanyId.value}`)
      
      // PRESERVAR: Request exacto como PromptsTab.vue
      const response = await fetch(`/api/admin/prompts?company_id=${currentCompanyId.value}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'X-Company-ID': currentCompanyId.value
        }
      })
      
      const data = await response.json()
      console.log('Prompts response:', data)
      console.log('Agents detail:', JSON.stringify(data.agents, null, 2))
      
      if (data && data.agents) {
        // PRESERVAR: Estructura exacta como PromptsTab.vue
        agents.value = {
          emergency_agent: data.agents.emergency_agent || null,
          router_agent: data.agents.router_agent || null,
          sales_agent: data.agents.sales_agent || null,
          schedule_agent: data.agents.schedule_agent || null,
          support_agent: data.agents.support_agent || null
        }
        
        console.log('Assigned agents:', agents.value)
        console.log('Has prompts?', hasPrompts.value)
        console.log(`Loaded ${Object.keys(data.agents).length} prompts`)
        
      } else {
        error.value = 'No se recibieron prompts del servidor'
      }
      
    } catch (err) {
      error.value = `Error cargando prompts: ${err.message}`
      console.error('Error loading prompts:', err)
    } finally {
      isLoadingPrompts.value = false
    }
  }

  /**
   * Actualiza prompt - MIGRADA EXACTA de PromptsTab.vue updatePrompt()
   */
  const updatePrompt = async (agentName) => {
    if (!currentCompanyId.value) {
      showNotification('Por favor selecciona una empresa primero', 'warning')
      return
    }

    const promptContent = agents.value[agentName]?.current_prompt
    if (!promptContent || !promptContent.trim()) {
      showNotification('El prompt no puede estar vacío', 'error')
      return
    }

    try {
      isProcessing.value = true
      
      console.log(`Updating prompt for ${agentName}`)
      
      // PRESERVAR: Request exacto como PromptsTab.vue
      const response = await fetch(`/api/admin/prompts/${agentName}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          company_id: currentCompanyId.value,
          prompt_template: promptContent
        })
      })
      
      const data = await response.json()
      console.log('Update response:', data)
      
      if (response.ok) {
        // PRESERVAR: Actualización de estado local
        if (agents.value[agentName]) {
          agents.value[agentName].is_custom = true
          agents.value[agentName].last_modified = new Date().toISOString()
          if (data.version) {
            agents.value[agentName].version = data.version
          }
        }
        
        let successMessage = `Prompt de ${agentName} actualizado exitosamente`
        if (data.version) {
          successMessage += ` (v${data.version})`
        }
        showNotification(successMessage, 'success')
        
        // Recargar los prompts para sincronizar
        await loadPrompts()
      } else {
        throw new Error(data.error || data.message || 'Error actualizando prompt')
      }
      
    } catch (err) {
      showNotification(`Error actualizando prompt: ${err.message}`, 'error')
      console.error('Error updating prompt:', err)
    } finally {
      isProcessing.value = false
    }
  }

  /**
   * Resetea prompt - MIGRADA EXACTA de PromptsTab.vue resetPrompt()
   */
  const resetPrompt = async (agentName) => {
    if (!currentCompanyId.value) {
      showNotification('Por favor selecciona una empresa primero', 'warning')
      return
    }

    if (!confirm(`¿Estás seguro de restaurar el prompt de ${agentName} a su valor por defecto?`)) {
      return
    }

    try {
      isProcessing.value = true
      
      console.log(`Resetting prompt for ${agentName}`)
      
      // PRESERVAR: Request exacto como PromptsTab.vue
      const response = await fetch(`/api/admin/prompts/${agentName}?company_id=${currentCompanyId.value}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json'
        }
      })
      
      console.log('Reset response status:', response.status)
      
      if (response.ok) {
        const data = await response.json()
        console.log('Reset response data:', data)
        
        // PRESERVAR: Actualización con prompt por defecto
        if (data.default_prompt && agents.value[agentName]) {
          agents.value[agentName].current_prompt = data.default_prompt
          agents.value[agentName].is_custom = false
          agents.value[agentName].last_modified = null
        }
        
        showNotification(`Prompt de ${agentName} restaurado exitosamente`, 'success')
        
        // Recargar los prompts
        await loadPrompts()
      } else {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.error || errorData.message || 'Error reseteando prompt')
      }
      
    } catch (err) {
      showNotification(`Error reseteando prompt: ${err.message}`, 'error')
      console.error('Error resetting prompt:', err)
    } finally {
      isProcessing.value = false
    }
  }

  /**
   * Vista previa de prompt - MIGRADA EXACTA de PromptsTab.vue previewPrompt()
   */
  const previewPrompt = async (agentName) => {
    const testMessage = prompt('Introduce un mensaje de prueba:', '¿Cuánto cuesta un tratamiento?')
    
    if (!testMessage) return
    
    const promptContent = agents.value[agentName]?.current_prompt
    if (!promptContent) {
      showNotification('No hay contenido de prompt para generar vista previa', 'error')
      return
    }
    
    // Preparar datos del preview
    previewAgent.value = agentName
    previewContent.value = promptContent
    previewTestMessage.value = testMessage
    previewResponse.value = null
    previewLoading.value = true
    showPreview.value = true
    
    try {
      console.log(`Generating preview for ${agentName}`)
      
      // PRESERVAR: Request exacto como PromptsTab.vue
      const response = await fetch('/api/admin/prompts/preview', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          agent_name: agentName,
          company_id: currentCompanyId.value,
          prompt_template: promptContent,
          message: testMessage
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        console.log('Preview response:', data)
        
        // PRESERVAR: Estructura de respuesta
        previewResponse.value = {
          success: true,
          preview: data.preview || data.response || '',
          agent_used: data.agent_used || agentName,
          prompt_source: data.prompt_source || 'custom',
          debug_info: data.debug_info || {},
          model_info: data.model_info || {},
          metrics: data.metrics || {},
          timestamp: new Date().toISOString()
        }
      } else {
        const errorData = await response.json().catch(() => ({}))
        previewResponse.value = {
          success: false,
          error: errorData.error || errorData.message || 'Error generando preview',
          timestamp: new Date().toISOString()
        }
      }
      
    } catch (err) {
      console.log('Preview endpoint error:', err)
      previewResponse.value = {
        success: false,
        error: 'Endpoint de preview no disponible',
        fallback: true,
        prompt_content: promptContent,
        timestamp: new Date().toISOString()
      }
    } finally {
      previewLoading.value = false
    }
  }

  /**
   * Cierra preview
   */
  const closePreview = () => {
    showPreview.value = false
    previewAgent.value = ''
    previewContent.value = ''
    previewTestMessage.value = ''
    previewResponse.value = null
    previewLoading.value = false
  }

  /**
   * Repara todos los prompts - MIGRADA EXACTA de PromptsTab.vue repairAllPrompts()
   */
  const repairAllPrompts = async () => {
    if (!confirm('¿Reparar todos los prompts desde el repositorio? Esto restaurará los prompts corruptos o faltantes.')) {
      return
    }

    try {
      isProcessing.value = true
      
      console.log('Repairing all prompts...')
      
      // PRESERVAR: Request exacto como PromptsTab.vue
      const response = await fetch('/api/admin/prompts/repair', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          company_id: currentCompanyId.value,
          agents: Object.keys(agents.value)
        })
      })
      
      console.log('Repair response status:', response.status)
      
      if (response.ok) {
        const data = await response.json()
        console.log('Repair response:', data)
        
        let message = 'Prompts reparados exitosamente'
        if (data.repaired_count !== undefined) {
          message += ` (${data.repaired_count} prompts reparados)`
        }
        if (data.details) {
          console.log('Repair details:', data.details)
        }
        
        showNotification(message, 'success')
        
        // Recargar los prompts después de la reparación
        await loadPrompts()
      } else {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.error || errorData.message || 'Error reparando prompts')
      }
      
    } catch (err) {
      showNotification(`Error reparando prompts: ${err.message}`, 'error')
      console.error('Error repairing prompts:', err)
    } finally {
      isProcessing.value = false
    }
  }

  /**
   * Exporta prompts
   */
  const exportPrompts = () => {
    try {
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5)
      
      const exportData = {
        company_id: currentCompanyId.value,
        company_name: currentCompanyName.value,
        exported_at: new Date().toISOString(),
        agents: {}
      }
      
      // Incluir solo los datos relevantes de cada agente
      Object.entries(agents.value).forEach(([key, agent]) => {
        if (agent) {
          exportData.agents[key] = {
            current_prompt: agent.current_prompt,
            is_custom: agent.is_custom,
            last_modified: agent.last_modified,
            version: agent.version || null
          }
        }
      })
      
      const dataStr = JSON.stringify(exportData, null, 2)
      const dataBlob = new Blob([dataStr], { type: 'application/json' })
      
      const link = document.createElement('a')
      link.href = URL.createObjectURL(dataBlob)
      link.download = `prompts_${currentCompanyId.value}_${timestamp}.json`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(link.href)
      
      showNotification('Prompts exportados exitosamente', 'success')
    } catch (err) {
      showNotification('Error exportando prompts: ' + err.message, 'error')
      console.error('Error exporting prompts:', err)
    }
  }

  /**
   * Formatea fecha
   */
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    try {
      return new Date(dateString).toLocaleDateString()
    } catch {
      return 'Fecha inválida'
    }
  }

  // ============================================================================
  // WATCHERS
  // ============================================================================

  // Recargar cuando cambie la empresa
  watch(() => appStore.currentCompanyId, async (newCompanyId) => {
    if (newCompanyId) {
      await loadPrompts()
    }
  })

  // ============================================================================
  // RETORNO DEL COMPOSABLE
  // ============================================================================

  return {
    // Estado reactivo
    agents,
    isLoadingPrompts,
    isProcessing,
    error,
    
    // Preview state
    showPreview,
    previewAgent,
    previewContent,
    previewTestMessage,
    previewResponse,
    previewLoading,
    
    // Computed properties
    hasPrompts,
    currentCompanyId,
    currentCompanyName,
    
    // Funciones principales (nombres exactos de PromptsTab.vue)
    loadPrompts,
    updatePrompt,
    resetPrompt,
    previewPrompt,
    closePreview,
    repairAllPrompts,
    exportPrompts,
    formatDate
  }
}
