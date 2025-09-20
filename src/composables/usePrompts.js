/**
 * usePrompts.js - Composable para Gestión de Prompts
 * ✅ CORREGIDO: agentsList incluido en return
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
    return window.currentCompanyId || localStorage.getItem('currentCompanyId') || 'dental_clinic'
  })

  const currentCompanyName = computed(() => {
    return window.currentCompanyName || currentCompanyId.value
  })

  // ✅ CRÍTICO: Este computed debe estar en el return
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

    // ✅ DEBUG: Log para verificar transformación
    console.log('agentsList computed:', result.length, 'agents')
    result.forEach(agent => {
      console.log(`- ${agent.displayName}: ${agent.content ? 'Has content' : 'Empty'}`)
    })

    return result
  })

  // ============================================================================
  // FUNCIONES PRINCIPALES (sin cambios)
  // ============================================================================

  const loadPrompts = async () => {
    if (!currentCompanyId.value) {
      error.value = 'Por favor selecciona una empresa primero'
      return
    }

    try {
      isLoadingPrompts.value = true
      error.value = null
      
      console.log(`Loading prompts for company: ${currentCompanyId.value}`)
      
      const response = await fetch(`/api/admin/prompts?company_id=${currentCompanyId.value}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'X-Company-ID': currentCompanyId.value
        }
      })
      
      const data = await response.json()
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
      
    } catch (err) {
      error.value = `Error cargando prompts: ${err.message}`
      console.error('Error loading prompts:', err)
    } finally {
      isLoadingPrompts.value = false
    }
  }

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
        
        if (data.default_prompt && agents.value[agentName]) {
          agents.value[agentName].current_prompt = data.default_prompt
          agents.value[agentName].is_custom = false
          agents.value[agentName].last_modified = null
        }
        
        showNotification(`Prompt de ${agentName} restaurado exitosamente`, 'success')
        
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

  const previewPrompt = async (agentName) => {
    const testMessage = prompt('Introduce un mensaje de prueba:', '¿Cuánto cuesta un tratamiento?')
    
    if (!testMessage) return
    
    const promptContent = agents.value[agentName]?.current_prompt
    if (!promptContent) {
      showNotification('No hay contenido de prompt para generar vista previa', 'error')
      return
    }
    
    previewAgent.value = agentName
    previewContent.value = promptContent
    previewTestMessage.value = testMessage
    previewResponse.value = null
    previewLoading.value = true
    showPreview.value = true
    
    try {
      console.log(`Generating preview for ${agentName}`)
      
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

  const closePreview = () => {
    showPreview.value = false
    previewAgent.value = ''
    previewContent.value = ''
    previewTestMessage.value = ''
    previewResponse.value = null
    previewLoading.value = false
  }

  const repairAllPrompts = async () => {
    if (!confirm('¿Reparar todos los prompts desde el repositorio? Esto restaurará los prompts corruptos o faltantes.')) {
      return
    }

    try {
      isProcessing.value = true
      
      console.log('Repairing all prompts...')
      
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
  // WATCHERS
  // ============================================================================

  watch(() => appStore.currentCompanyId, async (newCompanyId) => {
    if (newCompanyId) {
      await loadPrompts()
    }
  })

  const debugPrompts = async () => {
    console.log('=== DEBUG PROMPTS ===')
    console.log('1. Current Company ID:', currentCompanyId.value)
    console.log('2. Current Agents State:', JSON.stringify(agents.value, null, 2))
    console.log('3. Has Prompts?:', hasPrompts.value)
    console.log('4. AgentsList Length:', agentsList.value.length)
    console.log('5. AgentsList Content:', agentsList.value)
    console.log('6. Is Loading?:', isLoadingPrompts.value)
    console.log('7. Error?:', error.value)
    
    // ✅ NUEVO: Debug específico para validación
    console.log('8. VALIDATION DEBUG:')
    agentsList.value.forEach(agent => {
      console.log(`\n--- ${agent.displayName} ---`)
      console.log('Content length:', agent.content.length)
      console.log('Has {user_message}:', agent.content.includes('{user_message}'))
      
      // Detectar patrones problemáticos
      const doubleBreaces = agent.content.match(/\{\{[^}]+\}\}/g)
      const dollarVars = agent.content.match(/\$\{[^}]+\}/g)
      const invalidPatterns = agent.content.match(/\{[^}]+\}\s*[≤<>]\s*\d+/g)
      
      if (doubleBreaces) console.log('⚠️ Double braces found:', doubleBreaces)
      if (dollarVars) console.log('⚠️ Dollar variables found:', dollarVars) 
      if (invalidPatterns) console.log('⚠️ Invalid patterns found:', invalidPatterns)
    })
    
    try {
      const response = await fetch(`/api/admin/prompts?company_id=${currentCompanyId.value}`)
      const data = await response.json()
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
  
  const testEndpoints = async () => {
    console.log('=== TESTING ENDPOINTS ===')
    const testAgent = 'emergency_agent'
    
    console.log('\n1. Testing GET /api/admin/prompts')
    try {
      const getResponse = await fetch(`/api/admin/prompts?company_id=${currentCompanyId.value}`)
      console.log('GET Status:', getResponse.status)
      const getData = await getResponse.json()
      console.log('GET Response:', getData)
    } catch (err) {
      console.error('GET Error:', err)
    }
    
    console.log('\n2. Testing PUT /api/admin/prompts/' + testAgent)
    console.log('Endpoint:', `/api/admin/prompts/${testAgent}`)
    console.log('Body:', {
      company_id: currentCompanyId.value,
      prompt_template: 'test'
    })
    
    console.log('\n3. Testing DELETE endpoint')
    console.log('Endpoint:', `/api/admin/prompts/${testAgent}?company_id=${currentCompanyId.value}`)
    
    console.log('\n4. Testing PREVIEW endpoint')
    try {
      const previewResponse = await fetch('/api/admin/prompts/preview', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          agent_name: testAgent,
          company_id: currentCompanyId.value,
          prompt_template: 'test prompt',
          message: 'test message'
        })
      })
      console.log('Preview Status:', previewResponse.status)
      if (previewResponse.status !== 404) {
        const previewData = await previewResponse.json()
        console.log('Preview Response:', previewData)
      } else {
        console.log('Preview endpoint not found (404)')
      }
    } catch (err) {
      console.error('Preview Error:', err)
    }
    
    console.log('\n5. Testing REPAIR endpoint')
    console.log('Endpoint: /api/admin/prompts/repair')
    console.log('Would send:', {
      company_id: currentCompanyId.value,
      agents: Object.keys(agents.value)
    })
  }

  // ============================================================================
  // ✅ RETORNO CORREGIDO - INCLUIR agentsList
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
    agentsList, // ✅ CRÍTICO: Este faltaba!
    
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
    testEndpoints
  }
}
