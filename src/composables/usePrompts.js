/**
 * usePrompts.js - Composable para Gestión de Prompts
 * ✅ CORREGIDO: import() dinámico en lugar de require() + inicialización ultra-segura
 */

import { ref, computed, watch } from 'vue'

export const usePrompts = () => {
  // ============================================================================
  // INICIALIZACIÓN DIFERIDA ULTRA-SEGURA - ✅ CORREGIDO: Solo import() dinámico
  // ============================================================================

  let appStore = null
  let apiRequest = null
  let showNotification = null
  let initializationAttempted = false

  /**
   * ✅ CORREGIDO: Inicialización con import() dinámico (compatible con browser)
   */
  const initializeComposables = async () => {
    if (appStore && apiRequest && showNotification) {
      return true // Ya inicializados
    }

    if (initializationAttempted) {
      console.warn('[usePrompts] Already attempted initialization')
      return false
    }

    initializationAttempted = true

    try {
      console.log('[usePrompts] Starting dynamic imports...')

      // ✅ FIX: Usar import() dinámico en lugar de require()
      if (!appStore) {
        const { useAppStore } = await import('@/stores/app')
        appStore = useAppStore()
      }

      if (!apiRequest) {
        const { useApiRequest } = await import('@/composables/useApiRequest')
        const composable = useApiRequest()
        apiRequest = composable.apiRequest
      }

      if (!showNotification) {
        const { useNotifications } = await import('@/composables/useNotifications')
        const composable = useNotifications()
        showNotification = composable.showNotification
      }

      console.log('[usePrompts] ✅ All composables initialized successfully')
      return true

    } catch (error) {
      console.error('[usePrompts] Initialization error:', error)
      initializationAttempted = false // Permitir reintentos
      return false
    }
  }

  // ============================================================================
  // ESTADO REACTIVO - SIN CAMBIOS
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
  // COMPUTED PROPERTIES - CON FALLBACKS SEGUROS
  // ============================================================================

  const hasPrompts = computed(() => {
    return Object.keys(agents.value).some(key => agents.value[key] !== null)
  })

  // ✅ CORREGIDO: Computed ultra-seguro sin acceso prematuro
  const currentCompanyId = computed(() => {
    // Orden de prioridad seguro
    if (typeof window !== 'undefined') {
      if (window.currentCompanyId) return window.currentCompanyId
      if (localStorage?.getItem('currentCompanyId')) {
        return localStorage.getItem('currentCompanyId')
      }
    }
    
    // Solo usar store como último recurso si está disponible
    if (appStore?.currentCompanyId) {
      return appStore.currentCompanyId
    }
    
    return 'benova' // Fallback seguro
  })

  const currentCompanyName = computed(() => {
    return window.currentCompanyName || currentCompanyId.value
  })

  const agentsList = computed(() => {
    const agentConfigs = [
      { name: 'emergency_agent', displayName: 'Emergency Agent', icon: '🚨' },
      { name: 'router_agent', displayName: 'Router Agent', icon: '🚦' },
      { name: 'sales_agent', displayName: 'Sales Agent', icon: '💼' },
      { name: 'schedule_agent', displayName: 'Schedule Agent', icon: '📅' },
      { name: 'support_agent', displayName: 'Support Agent', icon: '🎧' }
    ]

    const result = agentConfigs
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

    console.log('[usePrompts] agentsList computed:', result.length, 'agents')
    return result
  })

  // ============================================================================
  // FUNCIONES PRINCIPALES - ✅ CORREGIDAS CON INICIALIZACIÓN SEGURA
  // ============================================================================

  /**
   * ✅ CORREGIDO: loadPrompts con inicialización automática
   */
  const loadPrompts = async () => {
    console.log('[usePrompts] loadPrompts called')

    // ✅ Auto-inicializar si es necesario
    const isReady = await initializeComposables()
    if (!isReady) {
      error.value = 'No se pudieron inicializar los composables'
      console.error('[usePrompts] Failed to initialize composables')
      return []
    }

    if (!currentCompanyId.value) {
      error.value = 'Por favor selecciona una empresa primero'
      return []
    }

    try {
      isLoadingPrompts.value = true
      error.value = null
      
      console.log(`[usePrompts] Loading prompts for company: ${currentCompanyId.value}`)
      
      const data = await apiRequest(`/api/admin/prompts?company_id=${currentCompanyId.value}`)
      
      console.log('[usePrompts] Prompts response:', data)
      
      if (data && data.agents) {
        agents.value = {
          emergency_agent: data.agents.emergency_agent || null,
          router_agent: data.agents.router_agent || null,
          sales_agent: data.agents.sales_agent || null,
          schedule_agent: data.agents.schedule_agent || null,
          support_agent: data.agents.support_agent || null
        }
        
        console.log('[usePrompts] ✅ Agents loaded:', Object.keys(agents.value).filter(k => agents.value[k]))
        
      } else {
        error.value = 'No se recibieron prompts del servidor'
      }
      
      return agents.value
      
    } catch (err) {
      error.value = `Error cargando prompts: ${err.message}`
      console.error('[usePrompts] Error loading prompts:', err)
      return []
    } finally {
      isLoadingPrompts.value = false
    }
  }

  /**
   * ✅ CORREGIDO: updatePrompt con inicialización automática
   */
  const updatePrompt = async (agentName, customContent = null) => {
    const isReady = await initializeComposables()
    if (!isReady) {
      console.error('[usePrompts] Cannot update: composables not ready')
      return false
    }

    if (!currentCompanyId.value) {
      showNotification('Por favor selecciona una empresa primero', 'warning')
      return false
    }
  
    let promptContent = customContent
    if (!promptContent) {
      promptContent = agents.value[agentName]?.current_prompt
    }
  
    if (!promptContent || !promptContent.trim()) {
      showNotification('El prompt no puede estar vacío', 'error')
      return false
    }
  
    try {
      isProcessing.value = true
      
      const data = await apiRequest(`/api/admin/prompts/${agentName}`, {
        method: 'PUT',
        body: {
          company_id: currentCompanyId.value,
          prompt_template: promptContent
        }
      })
      
      // Actualizar estado local
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
      showNotification(successMessage, 'success')
      
      return true
      
    } catch (err) {
      showNotification(`Error actualizando prompt: ${err.message}`, 'error')
      console.error('[usePrompts] Error updating prompt:', err)
      return false
    } finally {
      isProcessing.value = false
    }
  }

  /**
   * ✅ CORREGIDO: resetPrompt con inicialización automática
   */
  const resetPrompt = async (agentName) => {
    const isReady = await initializeComposables()
    if (!isReady) {
      console.error('[usePrompts] Cannot reset: composables not ready')
      return false
    }

    if (!currentCompanyId.value) {
      showNotification('Por favor selecciona una empresa primero', 'warning')
      return false
    }

    if (!confirm(`¿Estás seguro de restaurar el prompt de ${agentName} a su valor por defecto?`)) {
      return false
    }

    try {
      isProcessing.value = true
      
      const data = await apiRequest(`/api/admin/prompts/${agentName}?company_id=${currentCompanyId.value}`, {
        method: 'DELETE'
      })
      
      // Actualizar estado local
      if (data.default_prompt && agents.value[agentName]) {
        agents.value[agentName].current_prompt = data.default_prompt
        agents.value[agentName].is_custom = false
        agents.value[agentName].last_modified = null
      }
      
      showNotification(`Prompt de ${agentName} restaurado exitosamente`, 'success')
      
      await loadPrompts()
      return true
      
    } catch (err) {
      showNotification(`Error reseteando prompt: ${err.message}`, 'error')
      console.error('[usePrompts] Error resetting prompt:', err)
      return false
    } finally {
      isProcessing.value = false
    }
  }

  /**
   * ✅ CORREGIDO: previewPrompt con inicialización automática
   */
  const previewPrompt = async (agentName) => {
    const isReady = await initializeComposables()
    if (!isReady) {
      console.error('[usePrompts] Cannot preview: composables not ready')
      return false
    }

    const testMessage = prompt('Introduce un mensaje de prueba:', '¿Cuánto cuesta un tratamiento?')
    if (!testMessage) return false
    
    const promptContent = agents.value[agentName]?.current_prompt
    if (!promptContent) {
      showNotification('No hay contenido de prompt para generar vista previa', 'error')
      return false
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
      
      return true
      
    } catch (err) {
      console.log('[usePrompts] Preview endpoint error:', err)
      previewResponse.value = {
        success: false,
        error: 'Endpoint de preview no disponible',
        fallback: true,
        prompt_content: promptContent,
        timestamp: new Date().toISOString()
      }
      return false
    } finally {
      previewLoading.value = false
    }
  }

  /**
   * ✅ CORREGIDO: repairAllPrompts con inicialización automática
   */
  const repairAllPrompts = async () => {
    const isReady = await initializeComposables()
    if (!isReady) {
      console.error('[usePrompts] Cannot repair: composables not ready')
      return false
    }

    if (!confirm('¿Restaurar TODOS los prompts a sus valores por defecto del repositorio?\n\nEsto eliminará todas las personalizaciones.')) {
      return false
    }
  
    try {
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
          console.error(`[usePrompts] Error restoring ${agentName}:`, error)
          errorCount++
        }
      }
      
      if (errorCount === 0) {
        showNotification(`✅ Todos los prompts restaurados exitosamente (${successCount}/${agentNames.length})`, 'success')
      } else {
        showNotification(`⚠️ Restauración completada: ${successCount} exitosos, ${errorCount} errores`, 'warning')
      }
      
      await loadPrompts()
      return true
      
    } catch (err) {
      showNotification(`Error restaurando prompts: ${err.message}`, 'error')
      console.error('[usePrompts] Error in repair all prompts:', err)
      return false
    } finally {
      isProcessing.value = false
    }
  }

  // ============================================================================
  // FUNCIONES AUXILIARES - SIN CAMBIOS
  // ============================================================================

  const closePreview = () => {
    showPreview.value = false
    previewAgent.value = ''
    previewContent.value = ''
    previewTestMessage.value = ''
    previewResponse.value = null
    previewLoading.value = false
  }

  const exportPrompts = async () => {
    const isReady = await initializeComposables()
    if (!isReady) {
      console.error('[usePrompts] Cannot export: composables not ready')
      return
    }

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
      
      showNotification('Prompts exportados exitosamente', 'success')
    } catch (err) {
      showNotification('Error exportando prompts: ' + err.message, 'error')
      console.error('[usePrompts] Error exporting prompts:', err)
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
  // DEBUG FUNCTIONS - ✅ CORREGIDAS
  // ============================================================================

  const debugPrompts = async () => {
    const isReady = await initializeComposables()
    if (!isReady) {
      console.log('[usePrompts] Cannot debug: composables not ready')
      return null
    }

    console.log('=== DEBUG PROMPTS ===')
    console.log('1. Current Company ID:', currentCompanyId.value)
    console.log('2. Current Agents State:', JSON.stringify(agents.value, null, 2))
    console.log('3. Has Prompts?:', hasPrompts.value)
    console.log('4. AgentsList Length:', agentsList.value.length)
    console.log('5. Is Loading?:', isLoadingPrompts.value)
    console.log('6. Error?:', error.value)
    
    try {
      const data = await apiRequest(`/api/admin/prompts?company_id=${currentCompanyId.value}`)
      console.log('7. RAW API Response:', data)
      return data
    } catch (err) {
      console.error('Debug Error:', err)
      return null
    }
  }
  
  const testEndpoints = async () => {
    const isReady = await initializeComposables()
    if (!isReady) {
      console.log('[usePrompts] Cannot test: composables not ready')
      return null
    }

    console.log('=== TESTING ENDPOINTS ===')
    const testAgent = 'emergency_agent'
    
    try {
      const getData = await apiRequest(`/api/admin/prompts?company_id=${currentCompanyId.value}`)
      console.log('✅ GET Response:', getData)
    } catch (err) {
      console.error('❌ GET Error:', err)
    }
  }

  // ============================================================================
  // WATCHERS CON INICIALIZACIÓN DIFERIDA
  // ============================================================================

  let watcherCleanup = null

  const setupWatchers = async () => {
    if (watcherCleanup) return // Ya configurado
    
    try {
      const isReady = await initializeComposables()
      if (isReady && appStore) {
        watcherCleanup = watch(() => appStore.currentCompanyId, async (newCompanyId) => {
          if (newCompanyId) {
            console.log('[usePrompts] Company changed to:', newCompanyId)
            await loadPrompts()
          }
        })
        console.log('[usePrompts] ✅ Watchers configured')
      }
    } catch (error) {
      console.warn('[usePrompts] Error setting up watchers:', error)
    }
  }

  // ✅ Configurar watchers cuando sea posible
  setTimeout(setupWatchers, 1000)

  // ============================================================================
  // CLEANUP
  // ============================================================================

  const cleanup = () => {
    if (watcherCleanup) {
      watcherCleanup()
      watcherCleanup = null
    }
    
    appStore = null
    apiRequest = null
    showNotification = null
    initializationAttempted = false
  }

  // ============================================================================
  // RETURN - PRESERVADO ÍNTEGRAMENTE
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
    
    // Funciones principales
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

    // Funciones de utilidad
    initializeComposables,
    cleanup
  }
}
