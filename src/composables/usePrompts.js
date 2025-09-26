/**
 * usePrompts.js - CORREGIDO: Inicialización Diferida sin Dependencias Circulares
 * ✅ SOLUCIÓN: Lazy loading de stores y composables para evitar loops de inicialización
 */

import { ref, computed, watch, nextTick } from 'vue'

export const usePrompts = () => {
  // ============================================================================
  // ESTADO LOCAL PRIMERO - Sin dependencias inmediatas
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
  // SERVICIOS COMO LAZY LOADING - ✅ SOLUCIÓN PRINCIPAL
  // ============================================================================

  let appStore = null
  let apiRequest = null
  let showNotification = null

  /**
   * ✅ Inicialización diferida de servicios para evitar dependencias circulares
   */
  const initializeServices = async () => {
    if (!appStore) {
      try {
        // Importación dinámica para evitar dependencias circulares
        const { useAppStore } = await import('@/stores/app')
        const { useApiRequest } = await import('@/composables/useApiRequest')
        const { useNotifications } = await import('@/composables/useNotifications')

        appStore = useAppStore()
        apiRequest = useApiRequest().apiRequest
        showNotification = useNotifications().showNotification

        console.log('✅ Prompts services initialized successfully')
      } catch (error) {
        console.error('❌ Error initializing prompts services:', error)
        throw error
      }
    }
  }

  // ============================================================================
  // COMPUTED PROPERTIES - Con verificaciones seguras
  // ============================================================================

  const hasPrompts = computed(() => {
    return Object.keys(agents.value).some(key => agents.value[key] !== null)
  })

  const currentCompanyId = computed(() => {
    // Fallback seguro sin dependencia inmediata del store
    return appStore?.currentCompanyId || 
           window.currentCompanyId || 
           localStorage.getItem('currentCompanyId') || 
           'dental_clinic'
  })

  const currentCompanyName = computed(() => {
    return appStore?.currentCompanyName || 
           window.currentCompanyName || 
           currentCompanyId.value
  })

  const agentsList = computed(() => {
    const agentConfigs = [
      { name: 'emergency_agent', displayName: 'Emergency Agent', icon: '🚨' },
      { name: 'router_agent', displayName: 'Router Agent', icon: '🚦' },
      { name: 'sales_agent', displayName: 'Sales Agent', icon: '💼' },
      { name: 'schedule_agent', displayName: 'Schedule Agent', icon: '📅' },
      { name: 'support_agent', displayName: 'Support Agent', icon: '🎧' }
    ]

    return agentConfigs
      .filter(config => agents.value[config.name])
      .map(config => ({
        id: config.name,
        name: config.name,
        displayName: config.displayName,
        icon: config.icon,
        content: agents.value[config.name]?.current_prompt || '',
        isCustom: agents.value[config.name]?.is_custom || false,
        lastModified: agents.value[config.name]?.last_modified || null,
        version: agents.value[config.name]?.version || null,
        placeholder: `Prompt para ${config.displayName}...`
      }))
  })

  // ============================================================================
  // FUNCIONES PRINCIPALES - ✅ Con inicialización segura
  // ============================================================================

  /**
   * ✅ Cargar prompts con inicialización diferida
   */
  const loadPrompts = async () => {
    try {
      // Asegurar que los servicios estén inicializados
      await initializeServices()

      if (!currentCompanyId.value) {
        error.value = 'Por favor selecciona una empresa primero'
        return
      }

      isLoadingPrompts.value = true
      error.value = null
      
      console.log(`Loading prompts for company: ${currentCompanyId.value}`)
      
      const data = await apiRequest(`/api/admin/prompts?company_id=${currentCompanyId.value}`)
      
      if (data && data.agents) {
        agents.value = {
          emergency_agent: data.agents.emergency_agent || null,
          router_agent: data.agents.router_agent || null,
          sales_agent: data.agents.sales_agent || null,
          schedule_agent: data.agents.schedule_agent || null,
          support_agent: data.agents.support_agent || null
        }
        
        console.log('✅ Prompts loaded successfully:', agentsList.value.length, 'agents')
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
   * ✅ Actualizar prompt con inicialización diferida
   */
  const updatePrompt = async (agentName, customContent = null) => {
    try {
      await initializeServices()

      if (!currentCompanyId.value) {
        showNotification?.('Por favor selecciona una empresa primero', 'warning')
        return
      }
    
      let promptContent = customContent
      if (!promptContent) {
        promptContent = agents.value[agentName]?.current_prompt
      }
    
      if (!promptContent || !promptContent.trim()) {
        showNotification?.('El prompt no puede estar vacío', 'error')
        return
      }
    
      isProcessing.value = true
      
      const data = await apiRequest(`/api/admin/prompts/${agentName}`, {
        method: 'PUT',
        body: {
          company_id: currentCompanyId.value,
          prompt_template: promptContent
        }
      })
      
      // Actualizar estado local inmediatamente
      if (agents.value[agentName]) {
        agents.value[agentName].current_prompt = promptContent
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
      showNotification?.(successMessage, 'success')
      
    } catch (err) {
      showNotification?.(`Error actualizando prompt: ${err.message}`, 'error')
      console.error('Error updating prompt:', err)
    } finally {
      isProcessing.value = false
    }
  }

  /**
   * ✅ Resetear prompt con inicialización diferida
   */
  const resetPrompt = async (agentName) => {
    try {
      await initializeServices()

      if (!currentCompanyId.value) {
        showNotification?.('Por favor selecciona una empresa primero', 'warning')
        return
      }

      if (!confirm(`¿Estás seguro de restaurar el prompt de ${agentName} a su valor por defecto?`)) {
        return
      }

      isProcessing.value = true
      
      const data = await apiRequest(`/api/admin/prompts/${agentName}?company_id=${currentCompanyId.value}`, {
        method: 'DELETE'
      })
      
      // Actualizar estado local con prompt por defecto
      if (data.default_prompt && agents.value[agentName]) {
        agents.value[agentName].current_prompt = data.default_prompt
        agents.value[agentName].is_custom = false
        agents.value[agentName].last_modified = null
      }
      
      showNotification?.(`Prompt de ${agentName} restaurado exitosamente`, 'success')
      
      // Recargar prompts
      await loadPrompts()
      
    } catch (err) {
      showNotification?.(`Error reseteando prompt: ${err.message}`, 'error')
      console.error('Error resetting prompt:', err)
    } finally {
      isProcessing.value = false
    }
  }

  /**
   * ✅ Preview prompt con inicialización diferida
   */
  const previewPrompt = async (agentName) => {
    try {
      await initializeServices()

      const testMessage = prompt('Introduce un mensaje de prueba:', '¿Cuánto cuesta un tratamiento?')
      
      if (!testMessage) return
      
      const promptContent = agents.value[agentName]?.current_prompt
      if (!promptContent) {
        showNotification?.('No hay contenido de prompt para generar vista previa', 'error')
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
        const data = await apiRequest('/api/admin/prompts/preview', {
          method: 'POST',
          body: {
            agent_name: agentName,
            company_id: currentCompanyId.value,
            prompt_template: promptContent,
            message: testMessage
          }
        })
        
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
        
      } catch (err) {
        console.log('Preview endpoint error:', err)
        previewResponse.value = {
          success: false,
          error: 'Endpoint de preview no disponible',
          fallback: true,
          prompt_content: promptContent,
          timestamp: new Date().toISOString()
        }
      }
      
    } catch (err) {
      console.error('Error in preview prompt:', err)
      showNotification?.(`Error en vista previa: ${err.message}`, 'error')
    } finally {
      previewLoading.value = false
    }
  }

  /**
   * ✅ Reparar todos los prompts con inicialización diferida
   */
  const repairAllPrompts = async () => {
    if (!confirm('¿Restaurar TODOS los prompts a sus valores por defecto del repositorio?\n\nEsto eliminará todas las personalizaciones.')) {
      return
    }
  
    try {
      await initializeServices()
      
      isProcessing.value = true
      
      const agentNames = Object.keys(agents.value).filter(key => agents.value[key] !== null)
      let successCount = 0
      let errorCount = 0
      
      for (const agentName of agentNames) {
        try {
          const data = await apiRequest(`/api/admin/prompts/${agentName}?company_id=${currentCompanyId.value}`, {
            method: 'DELETE'
          })
          
          // Actualizar estado local
          if (data.default_prompt && agents.value[agentName]) {
            agents.value[agentName].current_prompt = data.default_prompt
            agents.value[agentName].is_custom = false
            agents.value[agentName].last_modified = null
          }
          
          successCount++
          
        } catch (error) {
          console.error(`❌ Error restoring ${agentName}:`, error)
          errorCount++
        }
      }
      
      // Mostrar resultado final
      if (errorCount === 0) {
        showNotification?.(`✅ Todos los prompts restaurados exitosamente (${successCount}/${agentNames.length})`, 'success')
      } else {
        showNotification?.(`⚠️ Restauración completada: ${successCount} exitosos, ${errorCount} errores`, 'warning')
      }
      
      await loadPrompts()
      
    } catch (err) {
      showNotification?.(`Error restaurando prompts: ${err.message}`, 'error')
      console.error('Error in repair all prompts:', err)
    } finally {
      isProcessing.value = false
    }
  }

  // ============================================================================
  // FUNCIONES AUXILIARES - Sin cambios pero con verificaciones
  // ============================================================================

  const closePreview = () => {
    showPreview.value = false
    previewAgent.value = ''
    previewContent.value = ''
    previewTestMessage.value = ''
    previewResponse.value = null
    previewLoading.value = false
  }

  const exportPrompts = () => {
    try {
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5)
      
      const exportData = {
        company_id: currentCompanyId.value,
        company_name: currentCompanyName.value,
        exported_at: new Date().toISOString(),
        agents: {}
      }
      
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
      
      showNotification?.('Prompts exportados exitosamente', 'success')
    } catch (err) {
      showNotification?.('Error exportando prompts: ' + err.message, 'error')
      console.error('Error exporting prompts:', err)
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    try {
      return new Date(dateString).toLocaleDateString()
    } catch {
      return 'Fecha inválida'
    }
  }

  // ============================================================================
  // WATCHERS - Con verificaciones seguras
  // ============================================================================

  watch(() => appStore?.currentCompanyId, async (newCompanyId) => {
    if (newCompanyId && appStore) {
      await loadPrompts()
    }
  })

  // ============================================================================
  // FUNCIONES DEBUG - Con inicialización diferida
  // ============================================================================

  const debugPrompts = async () => {
    await initializeServices()
    
    console.log('=== DEBUG PROMPTS (SAFE) ===')
    console.log('1. Current Company ID:', currentCompanyId.value)
    console.log('2. Current Agents State:', JSON.stringify(agents.value, null, 2))
    console.log('3. Has Prompts?:', hasPrompts.value)
    console.log('4. AgentsList Length:', agentsList.value.length)
    console.log('5. Services Initialized?:', !!appStore, !!apiRequest, !!showNotification)
    
    try {
      const data = await apiRequest(`/api/admin/prompts?company_id=${currentCompanyId.value}`)
      console.log('6. RAW API Response:', data)
      return data
    } catch (err) {
      console.error('Debug Error:', err)
      return null
    }
  }
  
  const testEndpoints = async () => {
    await initializeServices()
    
    console.log('=== TESTING ENDPOINTS (SAFE) ===')
    // Resto del código de testing...
  }

  // ============================================================================
  // RETORNO COMPLETO - Todo igual pero con inicialización segura
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
    agentsList,
    
    // Funciones principales (nombres exactos)
    loadPrompts,
    updatePrompt,
    resetPrompt,
    previewPrompt,
    closePreview,
    repairAllPrompts,
    exportPrompts,
    formatDate,
    debugPrompts,
    testEndpoints,

    // ✅ NUEVA: Función para inicializar manualmente si es necesario
    initializeServices
  }
}
