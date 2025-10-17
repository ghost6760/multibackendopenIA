// composables/useWorkflows.js
// ✅ Composable principal para CRUD de workflows
// ✅ 100% reactivo - Sin manipulación DOM
// ✅ Integrado con multi-company context

import { ref, computed, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'

export const useWorkflows = () => {
  const appStore = useAppStore()
  const { apiRequest } = useApiRequest()
  const { showNotification, notifyApiError, notifyApiSuccess } = useNotifications()
  
  // ============================================================================
  // ESTADO REACTIVO
  // ============================================================================
  
  const workflows = ref([])
  const currentWorkflow = ref(null)
  const executionHistory = ref([])
  const workflowStats = ref(null)
  
  const isLoading = ref(false)
  const isExecuting = ref(false)
  const isSaving = ref(false)
  const isLoadingStats = ref(false)
  
  const error = ref(null)
  const validationErrors = ref([])
  const validationWarnings = ref([])
  
  // ============================================================================
  // COMPUTED PROPERTIES
  // ============================================================================
  
  const hasWorkflows = computed(() => workflows.value.length > 0)
  const workflowsCount = computed(() => workflows.value.length)
  const enabledWorkflows = computed(() => {
    return workflows.value.filter(wf => wf.enabled)
  })
  const disabledWorkflows = computed(() => {
    return workflows.value.filter(wf => !wf.enabled)
  })
  
  const canExecute = computed(() => {
    return appStore.hasCompanySelected && !isExecuting.value
  })
  
  const canSave = computed(() => {
    return appStore.hasCompanySelected && !isSaving.value
  })
  
  // ============================================================================
  // MÉTODOS PRINCIPALES - CRUD
  // ============================================================================
  
  /**
   * Cargar workflows de la empresa actual
   */
  const loadWorkflows = async (enabledOnly = false) => {
    if (!appStore.currentCompanyId) {
      showNotification('⚠️ Por favor selecciona una empresa primero', 'warning')
      return []
    }
    
    isLoading.value = true
    error.value = null
    
    try {
      appStore.addToLog(
        `[${appStore.currentCompanyId}] Loading workflows (enabled_only=${enabledOnly})`,
        'info'
      )
      
      const response = await apiRequest('/api/workflows', {
        method: 'GET',
        params: {
          company_id: appStore.currentCompanyId,
          enabled_only: enabledOnly
        },
        headers: {
          'X-Company-ID': appStore.currentCompanyId
        }
      })
      
      workflows.value = response.workflows || []
      
      appStore.addToLog(
        `[${appStore.currentCompanyId}] Loaded ${workflows.value.length} workflows`,
        'info'
      )
      
      return workflows.value
      
    } catch (err) {
      console.error('Error loading workflows:', err)
      error.value = err.message
      notifyApiError('/api/workflows', err)
      appStore.addToLog(`Error loading workflows: ${err.message}`, 'error')
      workflows.value = []
      return []
      
    } finally {
      isLoading.value = false
    }
  }
  
  /**
   * Obtener detalles de un workflow específico
   */
  const getWorkflow = async (workflowId, useCache = true) => {
    if (!workflowId) {
      showNotification('❌ ID de workflow no válido', 'error')
      return null
    }
    
    if (!appStore.currentCompanyId) {
      showNotification('⚠️ Por favor selecciona una empresa primero', 'warning')
      return null
    }
    
    isLoading.value = true
    error.value = null
    
    try {
      appStore.addToLog(
        `[${appStore.currentCompanyId}] Loading workflow: ${workflowId}`,
        'info'
      )
      
      const response = await apiRequest(`/api/workflows/${workflowId}`, {
        method: 'GET',
        params: {
          company_id: appStore.currentCompanyId,
          use_cache: useCache
        },
        headers: {
          'X-Company-ID': appStore.currentCompanyId
        }
      })
      
      currentWorkflow.value = response.workflow
      
      // Guardar validación si existe
      if (response.validation) {
        validationErrors.value = response.validation.errors || []
        validationWarnings.value = response.validation.warnings || []
      }
      
      appStore.addToLog(
        `[${appStore.currentCompanyId}] Workflow loaded: ${response.workflow.name}`,
        'info'
      )
      
      return response.workflow
      
    } catch (err) {
      console.error('Error loading workflow:', err)
      error.value = err.message
      notifyApiError(`/api/workflows/${workflowId}`, err)
      appStore.addToLog(`Error loading workflow ${workflowId}: ${err.message}`, 'error')
      return null
      
    } finally {
      isLoading.value = false
    }
  }
  
  /**
   * Crear nuevo workflow
   */
  const createWorkflow = async (workflowData) => {
    if (!appStore.currentCompanyId) {
      showNotification('⚠️ Por favor selecciona una empresa primero', 'warning')
      return null
    }
    
    if (!workflowData || !workflowData.name) {
      showNotification('❌ Datos del workflow inválidos', 'error')
      return null
    }
    
    isSaving.value = true
    error.value = null
    
    try {
      appStore.addToLog(
        `[${appStore.currentCompanyId}] Creating workflow: ${workflowData.name}`,
        'info'
      )
      
      const response = await apiRequest('/api/workflows', {
        method: 'POST',
        body: {
          company_id: appStore.currentCompanyId,
          name: workflowData.name,
          description: workflowData.description || '',
          workflow_data: workflowData,
          enabled: workflowData.enabled !== undefined ? workflowData.enabled : true,
          tags: workflowData.tags || [],
          created_by: 'web_ui'
        },
        headers: {
          'X-Company-ID': appStore.currentCompanyId
        }
      })
      
      if (response.workflow_id) {
        notifyApiSuccess('Workflow creado')
        appStore.addToLog(
          `[${appStore.currentCompanyId}] Workflow created: ${response.workflow_id}`,
          'info'
        )
        
        // Recargar lista
        await loadWorkflows()
        
        return response
      } else {
        throw new Error('No workflow_id returned')
      }
      
    } catch (err) {
      console.error('Error creating workflow:', err)
      error.value = err.message
      notifyApiError('/api/workflows', err)
      appStore.addToLog(`Error creating workflow: ${err.message}`, 'error')
      return null
      
    } finally {
      isSaving.value = false
    }
  }
  
  /**
   * Actualizar workflow existente
   */
  const updateWorkflow = async (workflowId, updates) => {
    if (!workflowId) {
      showNotification('❌ ID de workflow no válido', 'error')
      return null
    }
    
    if (!appStore.currentCompanyId) {
      showNotification('⚠️ Por favor selecciona una empresa primero', 'warning')
      return null
    }
    
    isSaving.value = true
    error.value = null
    
    try {
      appStore.addToLog(
        `[${appStore.currentCompanyId}] Updating workflow: ${workflowId}`,
        'info'
      )
      
      const response = await apiRequest(`/api/workflows/${workflowId}`, {
        method: 'PUT',
        body: updates,
        params: {
          company_id: appStore.currentCompanyId
        },
        headers: {
          'X-Company-ID': appStore.currentCompanyId
        }
      })
      
      notifyApiSuccess('Workflow actualizado')
      appStore.addToLog(
        `[${appStore.currentCompanyId}] Workflow updated: ${workflowId}`,
        'info'
      )
      
      // Recargar lista
      await loadWorkflows()
      
      return response
      
    } catch (err) {
      console.error('Error updating workflow:', err)
      error.value = err.message
      notifyApiError(`/api/workflows/${workflowId}`, err)
      appStore.addToLog(`Error updating workflow ${workflowId}: ${err.message}`, 'error')
      return null
      
    } finally {
      isSaving.value = false
    }
  }
  
  /**
   * Eliminar workflow
   */
  const deleteWorkflow = async (workflowId) => {
    if (!workflowId) {
      showNotification('❌ ID de workflow no válido', 'error')
      return false
    }
    
    if (!confirm('¿Estás seguro de que quieres eliminar este workflow?')) {
      return false
    }
    
    if (!appStore.currentCompanyId) {
      showNotification('⚠️ Por favor selecciona una empresa primero', 'warning')
      return false
    }
    
    try {
      appStore.addToLog(
        `[${appStore.currentCompanyId}] Deleting workflow: ${workflowId}`,
        'info'
      )
      
      await apiRequest(`/api/workflows/${workflowId}`, {
        method: 'DELETE',
        params: {
          company_id: appStore.currentCompanyId
        },
        headers: {
          'X-Company-ID': appStore.currentCompanyId
        }
      })
      
      // Remover de la lista local
      workflows.value = workflows.value.filter(wf => wf.workflow_id !== workflowId)
      
      // Limpiar workflow actual si es el que se eliminó
      if (currentWorkflow.value?.id === workflowId) {
        currentWorkflow.value = null
      }
      
      notifyApiSuccess('Workflow eliminado')
      appStore.addToLog(
        `[${appStore.currentCompanyId}] Workflow deleted: ${workflowId}`,
        'info'
      )
      
      return true
      
    } catch (err) {
      console.error('Error deleting workflow:', err)
      notifyApiError(`/api/workflows/${workflowId}`, err)
      appStore.addToLog(`Error deleting workflow ${workflowId}: ${err.message}`, 'error')
      return false
    }
  }
  
  // ============================================================================
  // MÉTODOS - EJECUCIÓN
  // ============================================================================
  
  /**
   * Ejecutar workflow
   */
  const executeWorkflow = async (workflowId, context = {}) => {
    if (!workflowId) {
      showNotification('❌ ID de workflow no válido', 'error')
      return null
    }
    
    if (!appStore.currentCompanyId) {
      showNotification('⚠️ Por favor selecciona una empresa primero', 'warning')
      return null
    }
    
    isExecuting.value = true
    error.value = null
    
    try {
      appStore.addToLog(
        `[${appStore.currentCompanyId}] Executing workflow: ${workflowId}`,
        'info'
      )
      
      const response = await apiRequest(`/api/workflows/${workflowId}/execute`, {
        method: 'POST',
        body: {
          company_id: appStore.currentCompanyId,
          context: {
            ...context,
            executed_by: 'web_ui',
            executed_at: new Date().toISOString()
          }
        },
        headers: {
          'X-Company-ID': appStore.currentCompanyId
        }
      })
      
      const execution = response.execution
      
      if (execution.status === 'success') {
        showNotification('✅ Workflow ejecutado exitosamente', 'success')
      } else if (execution.status === 'error') {
        showNotification('❌ Error ejecutando workflow', 'error')
      } else {
        showNotification('⚠️ Ejecución completada con advertencias', 'warning')
      }
      
      appStore.addToLog(
        `[${appStore.currentCompanyId}] Workflow execution completed: ${execution.status}`,
        execution.status === 'success' ? 'info' : 'warning'
      )
      
      return execution
      
    } catch (err) {
      console.error('Error executing workflow:', err)
      error.value = err.message
      notifyApiError(`/api/workflows/${workflowId}/execute`, err)
      appStore.addToLog(`Error executing workflow ${workflowId}: ${err.message}`, 'error')
      return null
      
    } finally {
      isExecuting.value = false
    }
  }
  
  /**
   * Obtener historial de ejecuciones
   */
  const getExecutionHistory = async (workflowId, limit = 50) => {
    if (!workflowId) {
      showNotification('❌ ID de workflow no válido', 'error')
      return []
    }
    
    if (!appStore.currentCompanyId) {
      showNotification('⚠️ Por favor selecciona una empresa primero', 'warning')
      return []
    }
    
    try {
      const response = await apiRequest(`/api/workflows/${workflowId}/executions`, {
        method: 'GET',
        params: {
          company_id: appStore.currentCompanyId,
          limit: limit
        },
        headers: {
          'X-Company-ID': appStore.currentCompanyId
        }
      })
      
      executionHistory.value = response.executions || []
      
      appStore.addToLog(
        `[${appStore.currentCompanyId}] Loaded ${executionHistory.value.length} executions`,
        'info'
      )
      
      return executionHistory.value
      
    } catch (err) {
      console.error('Error loading execution history:', err)
      notifyApiError(`/api/workflows/${workflowId}/executions`, err)
      executionHistory.value = []
      return []
    }
  }
  
  // ============================================================================
  // MÉTODOS - VALIDACIÓN Y UTILIDADES
  // ============================================================================
  
  /**
   * Validar workflow sin guardarlo
   */
  const validateWorkflow = async (workflowData) => {
    if (!appStore.currentCompanyId) {
      showNotification('⚠️ Por favor selecciona una empresa primero', 'warning')
      return null
    }
    
    try {
      const response = await apiRequest('/api/workflows/validate', {
        method: 'POST',
        body: {
          company_id: appStore.currentCompanyId,
          workflow_data: workflowData
        },
        headers: {
          'X-Company-ID': appStore.currentCompanyId
        }
      })
      
      validationErrors.value = response.validation?.errors || []
      validationWarnings.value = response.validation?.warnings || []
      
      if (response.success) {
        showNotification('✅ Workflow válido', 'success', 2000)
      } else {
        showNotification('⚠️ Workflow tiene errores de validación', 'warning')
      }
      
      return response
      
    } catch (err) {
      console.error('Error validating workflow:', err)
      notifyApiError('/api/workflows/validate', err)
      return null
    }
  }
  
  /**
   * Cargar estadísticas de workflows
   */
  const loadWorkflowStats = async () => {
    if (!appStore.currentCompanyId) {
      showNotification('⚠️ Por favor selecciona una empresa primero', 'warning')
      return null
    }
    
    isLoadingStats.value = true
    
    try {
      const response = await apiRequest('/api/workflows/stats', {
        method: 'GET',
        params: {
          company_id: appStore.currentCompanyId
        },
        headers: {
          'X-Company-ID': appStore.currentCompanyId
        }
      })
      
      workflowStats.value = response
      
      appStore.addToLog(
        `[${appStore.currentCompanyId}] Workflow stats loaded`,
        'info'
      )
      
      return workflowStats.value
      
    } catch (err) {
      console.error('Error loading workflow stats:', err)
      notifyApiError('/api/workflows/stats', err)
      return null
      
    } finally {
      isLoadingStats.value = false
    }
  }
  
  /**
   * Validar condición específica
   */
  const validateCondition = async (condition, testContext = {}) => {
    try {
      const response = await apiRequest('/api/workflows/validate-condition', {
        method: 'POST',
        body: {
          condition: condition,
          test_context: testContext
        }
      })
      
      return response
      
    } catch (err) {
      console.error('Error validating condition:', err)
      return {
        success: false,
        validation: {
          valid: false,
          error: err.message
        }
      }
    }
  }
  
  /**
   * Listar templates disponibles
   */
  const listTemplates = async (category = null) => {
    try {
      const params = {}
      if (category) params.category = category
      
      const response = await apiRequest('/api/workflows/templates', {
        method: 'GET',
        params: params
      })
      
      return response.templates || []
      
    } catch (err) {
      console.error('Error loading templates:', err)
      return []
    }
  }
  
  // ============================================================================
  // MÉTODOS DE UTILIDAD
  // ============================================================================
  
  /**
   * Formatear fecha
   */
  const formatDate = (dateString) => {
    if (!dateString) return 'Desconocida'
    
    try {
      const date = new Date(dateString)
      const now = new Date()
      const diffTime = Math.abs(now - date)
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
      
      if (diffDays === 0) return 'Hoy'
      if (diffDays === 1) return 'Ayer'
      if (diffDays < 7) return `Hace ${diffDays} días`
      if (diffDays < 30) return `Hace ${Math.floor(diffDays / 7)} semanas`
      
      return date.toLocaleDateString('es-ES', {
        day: '2-digit',
        month: 'short',
        year: 'numeric'
      })
    } catch {
      return 'Fecha inválida'
    }
  }
  
  /**
   * Obtener icono por tipo de workflow
   */
  const getWorkflowIcon = (workflow) => {
    if (!workflow) return '📋'
    
    // Por tags
    if (workflow.tags?.includes('sales')) return '💰'
    if (workflow.tags?.includes('support')) return '🆘'
    if (workflow.tags?.includes('emergency')) return '🚨'
    if (workflow.tags?.includes('schedule')) return '📅'
    
    // Por nombre
    const name = workflow.name?.toLowerCase() || ''
    if (name.includes('bot')) return '💉'
    if (name.includes('schedule') || name.includes('agenda')) return '📅'
    if (name.includes('emergency') || name.includes('emergencia')) return '🚨'
    if (name.includes('sales') || name.includes('venta')) return '💰'
    
    return '📋'
  }
  
  /**
   * Obtener color de estado
   */
  const getStatusColor = (status) => {
    const colors = {
      'success': '#22c55e',
      'error': '#ef4444',
      'warning': '#f59e0b',
      'pending': '#6b7280',
      'running': '#3b82f6'
    }
    
    return colors[status] || colors.pending
  }
  
  /**
   * Exportar workflow como JSON
   */
  const exportWorkflow = (workflow) => {
    if (!workflow) {
      showNotification('❌ No hay workflow para exportar', 'error')
      return
    }
    
    try {
      const exportData = {
        ...workflow,
        exported_at: new Date().toISOString(),
        exported_by: 'web_ui'
      }
      
      const blob = new Blob([JSON.stringify(exportData, null, 2)], {
        type: 'application/json'
      })
      const url = URL.createObjectURL(blob)
      
      const link = document.createElement('a')
      link.href = url
      link.download = `workflow_${workflow.id}_${Date.now()}.json`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      
      URL.revokeObjectURL(url)
      
      showNotification('✅ Workflow exportado', 'success')
      
    } catch (err) {
      console.error('Error exporting workflow:', err)
      showNotification('❌ Error al exportar workflow', 'error')
    }
  }
  
  /**
   * Duplicar workflow
   */
  const duplicateWorkflow = async (workflow) => {
    if (!workflow) {
      showNotification('❌ No hay workflow para duplicar', 'error')
      return null
    }
    
    const newWorkflowData = {
      ...workflow,
      name: `${workflow.name} (Copia)`,
      enabled: false
    }
    
    // Eliminar IDs para que se generen nuevos
    delete newWorkflowData.id
    delete newWorkflowData.workflow_id
    delete newWorkflowData.created_at
    delete newWorkflowData.updated_at
    
    return await createWorkflow(newWorkflowData)
  }
  
  /**
   * Toggle enabled/disabled
   */
  const toggleWorkflowEnabled = async (workflowId) => {
    const workflow = workflows.value.find(wf => wf.workflow_id === workflowId)
    
    if (!workflow) {
      showNotification('❌ Workflow no encontrado', 'error')
      return false
    }
    
    return await updateWorkflow(workflowId, {
      enabled: !workflow.enabled
    })
  }
  
  // ============================================================================
  // WATCHERS
  // ============================================================================
  
  // Limpiar datos cuando cambia la empresa
  watch(() => appStore.currentCompanyId, (newCompanyId, oldCompanyId) => {
    if (oldCompanyId && newCompanyId !== oldCompanyId) {
      console.log('[USE-WORKFLOWS] Company changed, clearing data')
      clearWorkflowsData()
    }
  })
  
  // ============================================================================
  // CLEANUP
  // ============================================================================
  
  const clearWorkflowsData = () => {
    workflows.value = []
    currentWorkflow.value = null
    executionHistory.value = []
    workflowStats.value = null
    validationErrors.value = []
    validationWarnings.value = []
    error.value = null
  }
  
  const cleanup = () => {
    clearWorkflowsData()
    console.log('✅ [USE-WORKFLOWS] Cleanup completed')
  }
  
  // ============================================================================
  // RETURN
  // ============================================================================
  
  return {
    // Estado reactivo
    workflows,
    currentWorkflow,
    executionHistory,
    workflowStats,
    isLoading,
    isExecuting,
    isSaving,
    isLoadingStats,
    error,
    validationErrors,
    validationWarnings,
    
    // Computed
    hasWorkflows,
    workflowsCount,
    enabledWorkflows,
    disabledWorkflows,
    canExecute,
    canSave,
    
    // CRUD
    loadWorkflows,
    getWorkflow,
    createWorkflow,
    updateWorkflow,
    deleteWorkflow,
    
    // Ejecución
    executeWorkflow,
    getExecutionHistory,
    
    // Validación y utilidades
    validateWorkflow,
    validateCondition,
    loadWorkflowStats,
    listTemplates,
    
    // Utilidades
    formatDate,
    getWorkflowIcon,
    getStatusColor,
    exportWorkflow,
    duplicateWorkflow,
    toggleWorkflowEnabled,
    
    // Cleanup
    clearWorkflowsData,
    cleanup
  }
}
