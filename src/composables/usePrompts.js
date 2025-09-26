/**
 * usePrompts.js - Composable para Gestión de Prompts
 * ✅ CORREGIDO: Headers consistentes + inicialización diferida segura
 * ✅ PRESERVADO: Toda la funcionalidad original
 */

import { ref, computed, watch } from 'vue'

export const usePrompts = () => {
  // ============================================================================
  // INICIALIZACIÓN DIFERIDA - SOLUCIONA "Cannot access 'U' before initialization"
  // ============================================================================

  let appStore = null
  let apiRequest = null
  let showNotification = null

  /**
   * ✅ NUEVA FUNCIÓN: Inicialización segura de composables
   * Solo accede a stores cuando sea necesario
   */
  const initializeComposables = () => {
    if (appStore && apiRequest && showNotification) {
      return true // Ya inicializados
    }

    try {
      if (!appStore) {
        const { useAppStore } = require('@/stores/app')
        appStore = useAppStore()
      }

      if (!apiRequest) {
        const { useApiRequest } = require('@/composables/useApiRequest')
        apiRequest = useApiRequest().apiRequest
      }

      if (!showNotification) {
        const { useNotifications } = require('@/composables/useNotifications')
        showNotification = useNotifications().showNotification
      }

      return true
    } catch (error) {
      console.warn('[usePrompts] Composables not ready:', error.message)
      return false
    }
  }

  // ============================================================================
  // ESTADO REACTIVO - MIGRADO DE PROMPTSTAB.VUE (SIN CAMBIOS)
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
  // COMPUTED PROPERTIES - CON GUARDS DE SEGURIDAD
  // ============================================================================

  const hasPrompts = computed(() => {
    return Object.keys(agents.value).some(key => agents.value[key] !== null)
  })

  // ✅ CORREGIDO: Computed seguro que no accede prematuramente al store
  const currentCompanyId = computed(() => {
    // Prioridad: window > localStorage > store (si está disponible) > fallback
    if (typeof window !== 'undefined' && window.currentCompanyId) {
      return window.currentCompanyId
    }
    
    if (typeof localStorage !== 'undefined') {
      const stored = localStorage.getItem('currentCompanyId')
      if (stored) return stored
    }
    
    // Solo acceder al store si está inicializado
    if (appStore && appStore.currentCompanyId) {
      return appStore.currentCompanyId
    }
    
    return 'dental_clinic' // Fallback original
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

    console.log('agentsList computed:', result.length, 'agents')
    result.forEach(agent => {
      console.log(`- ${agent.displayName}: ${agent.content ? 'Has content' : 'Empty'}`)
    })

    return result
  })

  // ============================================================================
  // FUNCIONES PRINCIPALES - ✅ CORREGIDAS CON GUARDS DE INICIALIZACIÓN
  // ============================================================================

  /**
   * ✅ CORREGIDO: Usa apiRequest + guards de inicialización
   */
  const loadPrompts = async () => {
    // ✅ Guard: Verificar que composables estén listos
    if (!initializeComposables()) {
      console.warn('[usePrompts] Composables not ready, retrying...')
      await new Promise(resolve => setTimeout(resolve, 100))
      
      if (!initializeComposables()) {
        error.value = 'Sistema no inicializado correctamente'
        return []
      }
    }

    if (!currentCompanyId.value) {
      error.value = 'Por favor selecciona una empresa primero'
      return []
    }

    try {
      isLoadingPrompts.value = true
      error.value = null
      
      console.log(`Loading prompts for company: ${currentCompanyId.value}`)
      
      // ✅ FIX: Usar apiRequest en lugar de fetch directo
      const data = await apiRequest(`/api/admin/prompts?company_id=${currentCompanyId.value}`)
      
      console.log('Prompts response:', data)
      
      if (data && data.agents) {
        agents.value = {
          emergency_agent: data.agents.emergency_agent || null,
          router_agent: data.agents.router_agent || null,
          sales_agent: data.agents.sales_agent || null,
          schedule_agent: data.agents.schedule_agent || null,
          support_agent: data.agents.support_agent || null
        }
        
        console.log('✅ Assigned agents:', agents.value)
        console.log('✅ Has prompts?', hasPrompts.value)
        console.log('✅ Agents list length:', agentsList.value.length)
        
      } else {
        error.value = 'No se recibieron prompts del servidor'
      }
      
      return agents.value
      
    } catch (err) {
      error.value = `Error cargando prompts: ${err.message}`
      console.error('Error loading prompts:', err)
      return []
    } finally {
      isLoadingPrompts.value = false
    }
  }

  /**
   * ✅ CORREGIDO: Usa apiRequest + guards de inicialización
   */
  const updatePrompt = async (agentName, customContent = null) => {
    if (!initializeComposables()) {
      console.warn('[usePrompts] Cannot update: composables not ready')
      return false
    }

    if (!currentCompanyId.value) {
      showNotification('Por favor selecciona una empresa primero', 'warning')
      return false
    }
  
    // ✅ FIX: Usar contenido pasado como parámetro o leer del estado
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
      
      console.log(`Updating prompt for ${agentName}`)
      console.log('Content to send:', promptContent.substring(0, 100) + '...')
      
      const data = await apiRequest(`/api/admin/prompts/${agentName}`, {
        method: 'PUT',
        body: {
          company_id: currentCompanyId.value,
          prompt_template: promptContent
        }
      })
      
      console.log('Update response:', data)
      
      // ✅ FIX: Actualizar estado local INMEDIATAMENTE con el contenido enviado
      if (agents.value[agentName]) {
        agents.value[agentName].current_prompt = promptContent // Usar el contenido enviado
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
      
      // ✅ FIX: NO recargar inmediatamente (puede sobrescribir el cambio)
      // await loadPrompts() // Comentar esta línea
      
      return true
      
    } catch (err) {
      showNotification(`Error actualizando prompt: ${err.message}`, 'error')
      console.error('Error updating prompt:', err)
      return false
    } finally {
      isProcessing.value = false
    }
  }

  /**
   * ✅ CORREGIDO: Usa apiRequest + guards de inicialización
   */
  const resetPrompt = async (agentName) => {
    if (!initializeComposables()) {
      console.warn('[usePrompts] Cannot reset: composables not ready')
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
      
      console.log(`Resetting prompt for ${agentName}`)
      
      // ✅ FIX: Usar apiRequest en lugar de fetch directo
      const data = await apiRequest(`/api/admin/prompts/${agentName}?company_id=${currentCompanyId.value}`, {
        method: 'DELETE'
      })
      
      console.log('Reset response data:', data)
      
      // Actualizar estado local con prompt por defecto
      if (data.default_prompt && agents.value[agentName]) {
        agents.value[agentName].current_prompt = data.default_prompt
        agents.value[agentName].is_custom = false
        agents.value[agentName].last_modified = null
      }
      
      showNotification(`Prompt de ${agentName} restaurado exitosamente`, 'success')
      
      // Recargar prompts
      await loadPrompts()
      return true
      
    } catch (err) {
      showNotification(`Error reseteando prompt: ${err.message}`, 'error')
      console.error('Error resetting prompt:', err)
      return false
    } finally {
      isProcessing.value = false
    }
  }

  /**
   * ✅ CORREGIDO: Usa apiRequest + guards de inicialización
   */
  const previewPrompt = async (agentName) => {
    if (!initializeComposables()) {
      console.warn('[usePrompts] Cannot preview: composables not ready')
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
      console.log(`Generating preview for ${agentName}`)
      
      // ✅ FIX: Usar apiRequest en lugar de fetch directo
      const data = await apiRequest('/api/admin/prompts/preview', {
        method: 'POST',
        body: {
          agent_name: agentName,
          company_id: currentCompanyId.value,
          prompt_template: promptContent,
          message: testMessage
        }
      })
      
      console.log('Preview response:', data)
      
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
      console.log('Preview endpoint error:', err)
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
   * ✅ CORREGIDO: Usa apiRequest + guards de inicialización
   */
  const repairAllPrompts = async () => {
    if (!initializeComposables()) {
      console.warn('[usePrompts] Cannot repair: composables not ready')
      return false
    }

    if (!confirm('¿Restaurar TODOS los prompts a sus valores por defecto del repositorio?\n\nEsto eliminará todas las personalizaciones.')) {
      return false
    }
  
    try {
      isProcessing.value = true
      
      console.log('Restoring all prompts to repository defaults...')
      
      const agentNames = Object.keys(agents.value).filter(key => agents.value[key] !== null)
      let successCount = 0
      let errorCount = 0
      
      // ✅ CORRECCIÓN: Hacer DELETE para cada agente (igual que resetPrompt)
      for (const agentName of agentNames) {
        try {
          console.log(`Restoring ${agentName} to default...`)
          
          // Mismo endpoint y método que resetPrompt()
          const data = await apiRequest(`/api/admin/prompts/${agentName}?company_id=${currentCompanyId.value}`, {
            method: 'DELETE'
          })
          
          console.log(`✅ ${agentName} restored successfully`)
          
          // Actualizar estado local con prompt por defecto
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
        showNotification(`✅ Todos los prompts restaurados exitosamente (${successCount}/${agentNames.length})`, 'success')
      } else {
        showNotification(`⚠️ Restauración completada: ${successCount} exitosos, ${errorCount} errores`, 'warning')
      }
      
      // Recargar todos los prompts para sincronizar
      await loadPrompts()
      return true
      
    } catch (err) {
      showNotification(`Error restaurando prompts: ${err.message}`, 'error')
      console.error('Error in repair all prompts:', err)
      return false
    } finally {
      isProcessing.value = false
    }
  }

  // ============================================================================
  // FUNCIONES SIN CAMBIOS CRÍTICOS - PRESERVADAS
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
    if (!initializeComposables()) {
      console.warn('[usePrompts] Cannot export: composables not ready')
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
  // WATCHERS SEGUROS - CON GUARDS
  // ============================================================================

  let watcherCleanup = null

  const setupWatchers = () => {
    if (watcherCleanup) return // Ya configurado
    
    try {
      if (initializeComposables()) {
        watcherCleanup = watch(() => appStore?.currentCompanyId, async (newCompanyId) => {
          if (newCompanyId) {
            await loadPrompts()
          }
        })
      }
    } catch (error) {
      console.warn('[usePrompts] Error setting up watchers:', error)
    }
  }

  // Configurar watchers con delay
  setTimeout(setupWatchers, 100)

  /**
   * ✅ CORREGIDO: debugPrompts usa apiRequest + guards
   */
  const debugPrompts = async () => {
    if (!initializeComposables()) return null

    console.log('=== DEBUG PROMPTS ===')
    console.log('1. Current Company ID:', currentCompanyId.value)
    console.log('2. Current Agents State:', JSON.stringify(agents.value, null, 2))
    console.log('3. Has Prompts?:', hasPrompts.value)
    console.log('4. AgentsList Length:', agentsList.value.length)
    console.log('5. AgentsList Content:', agentsList.value)
    console.log('6. Is Loading?:', isLoadingPrompts.value)
    console.log('7. Error?:', error.value)
    
    try {
      // ✅ FIX: Usar apiRequest para consistencia
      const data = await apiRequest(`/api/admin/prompts?company_id=${currentCompanyId.value}`)
      console.log('8. RAW API Response:', data)
      
      if (data.agents) {
        console.log('9. Agent Keys in Response:', Object.keys(data.agents))
        console.log('10. Agent Values:')
        Object.entries(data.agents).forEach(([key, value]) => {
          console.log(`   ${key}:`, value ? 'Has content' : 'Empty', 
                     value?.current_prompt ? `(${value.current_prompt.substring(0, 50)}...)` : '')
        })
      }
      
      return data
    } catch (err) {
      console.error('Debug Error:', err)
      return null
    }
  }
  
  /**
   * ✅ CORREGIDO: testEndpoints usa apiRequest + guards
   */
  const testEndpoints = async () => {
    if (!initializeComposables()) return null

    console.log('=== TESTING ENDPOINTS ===')
    const testAgent = 'emergency_agent'
    
    // Test GET
    console.log('\n1. Testing GET /api/admin/prompts')
    try {
      const getData = await apiRequest(`/api/admin/prompts?company_id=${currentCompanyId.value}`)
      console.log('GET Response:', getData)
    } catch (err) {
      console.error('GET Error:', err)
    }
    
    // Test UPDATE (estructura)
    console.log('\n2. Testing PUT /api/admin/prompts/' + testAgent)
    console.log('Endpoint:', `/api/admin/prompts/${testAgent}`)
    console.log('Body:', {
      company_id: currentCompanyId.value,
      prompt_template: 'test'
    })
    
    // Test DELETE (estructura)
    console.log('\n3. Testing DELETE endpoint')
    console.log('Endpoint:', `/api/admin/prompts/${testAgent}?company_id=${currentCompanyId.value}`)
    
    // Test PREVIEW
    console.log('\n4. Testing PREVIEW endpoint')
    try {
      const previewData = await apiRequest('/api/admin/prompts/preview', {
        method: 'POST',
        body: {
          agent_name: testAgent,
          company_id: currentCompanyId.value,
          prompt_template: 'test prompt',
          message: 'test message'
        }
      })
      console.log('Preview Response:', previewData)
    } catch (err) {
      if (err.message.includes('404')) {
        console.log('Preview endpoint not found (404)')
      } else {
        console.error('Preview Error:', err)
      }
    }
    
    console.log('\n5. Testing REPAIR endpoint')
    console.log('Endpoint: /api/admin/prompts/repair')
    console.log('Would send:', {
      company_id: currentCompanyId.value,
      agents: Object.keys(agents.value)
    })
  }

  // ============================================================================
  // CLEANUP
  // ============================================================================

  const cleanup = () => {
    if (watcherCleanup) {
      watcherCleanup()
      watcherCleanup = null
    }
    
    // Reset composables
    appStore = null
    apiRequest = null
    showNotification = null
  }

  // ============================================================================
  // RETORNO COMPLETO - PRESERVADO ÍNTEGRAMENTE
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
    
    // Funciones principales (nombres exactos de PromptsTab.vue)
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

    // ✅ NUEVA: Función de utilidad para verificación
    initializeComposables,
    cleanup
  }
}
