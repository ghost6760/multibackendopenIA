// composables/useChatConversation.js
// ✅ Composable especializado para chat con ConfigAgent
// ✅ 100% reactivo - Sin manipulación DOM
// ✅ Maneja estado conversacional y mensajes

import { ref, computed, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'

export const useChatConversation = () => {
  const appStore = useAppStore()
  const { apiRequest } = useApiRequest()
  const { showNotification, notifyApiError, notifyApiSuccess } = useNotifications()
  
  // ============================================================================
  // ESTADO REACTIVO
  // ============================================================================
  
  const messages = ref([])
  const isTyping = ref(false)
  const isSending = ref(false)
  const currentStage = ref('initial') // initial, gathering, validating, confirming, complete
  const userId = ref(null)
  const conversationId = ref(null)
  const workflowDraft = ref(null)
  const error = ref(null)
  
  // ============================================================================
  // COMPUTED PROPERTIES
  // ============================================================================
  
  const hasMessages = computed(() => messages.value.length > 0)
  const canSendMessage = computed(() => !isSending.value && !isTyping.value)
  const isComplete = computed(() => currentStage.value === 'complete')
  const hasWorkflowDraft = computed(() => workflowDraft.value !== null)
  
  const lastMessage = computed(() => {
    return messages.value.length > 0 
      ? messages.value[messages.value.length - 1]
      : null
  })
  
  // ============================================================================
  // MÉTODOS PRINCIPALES
  // ============================================================================
  
  /**
   * Iniciar nueva conversación
   */
  const startConversation = async () => {
    if (!appStore.currentCompanyId) {
      showNotification('⚠️ Por favor selecciona una empresa primero', 'warning')
      return false
    }
    
    // Generar user_id único para esta conversación
    userId.value = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    conversationId.value = `conv_${Date.now()}`
    
    // Mensaje inicial del sistema
    messages.value = [{
      id: 'msg_0',
      role: 'assistant',
      content: '👋 ¡Hola! Soy el asistente de configuración de workflows.\n\n¿Qué workflow te gustaría crear hoy?',
      timestamp: new Date().toISOString(),
      stage: 'initial'
    }]
    
    currentStage.value = 'initial'
    workflowDraft.value = null
    error.value = null
    
    appStore.addToLog(
      `[${appStore.currentCompanyId}] Started new config conversation: ${userId.value}`,
      'info'
    )
    
    return true
  }
  
  /**
   * Enviar mensaje al ConfigAgent
   */
  const sendMessage = async (messageText) => {
    if (!messageText?.trim()) {
      showNotification('❌ Por favor escribe un mensaje', 'error')
      return null
    }
    
    if (!appStore.currentCompanyId) {
      showNotification('⚠️ Por favor selecciona una empresa primero', 'warning')
      return null
    }
    
    if (!userId.value) {
      await startConversation()
    }
    
    isSending.value = true
    error.value = null
    
    // Agregar mensaje del usuario
    const userMessage = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: messageText.trim(),
      timestamp: new Date().toISOString()
    }
    
    messages.value.push(userMessage)
    
    // Mostrar "typing" indicator
    isTyping.value = true
    
    try {
      appStore.addToLog(
        `[${appStore.currentCompanyId}] Sending message to ConfigAgent: "${messageText.substring(0, 50)}..."`,
        'info'
      )
      
      const response = await apiRequest('/api/workflows/config-chat', {
        method: 'POST',
        body: {
          company_id: appStore.currentCompanyId,
          user_id: userId.value,
          message: messageText
        },
        headers: {
          'X-Company-ID': appStore.currentCompanyId
        }
      })
      
      // Agregar respuesta del agente
      const agentMessage = {
        id: `msg_${Date.now()}`,
        role: 'assistant',
        content: response.response || 'Disculpa, no pude procesar tu mensaje.',
        timestamp: new Date().toISOString(),
        stage: response.stage || 'unknown'
      }
      
      messages.value.push(agentMessage)
      
      // Actualizar estado
      currentStage.value = response.stage || currentStage.value
      
      // Si el agente generó un workflow draft, guardarlo
      if (response.workflow_draft) {
        workflowDraft.value = response.workflow_draft
      }
      
      // Log exitoso
      appStore.addToLog(
        `[${appStore.currentCompanyId}] ConfigAgent response received - Stage: ${response.stage}`,
        'info'
      )
      
      return response
      
    } catch (err) {
      console.error('Error sending message to ConfigAgent:', err)
      error.value = err.message
      
      // Agregar mensaje de error
      const errorMessage = {
        id: `msg_${Date.now()}`,
        role: 'system',
        content: `❌ Error: ${err.message || 'No pude enviar tu mensaje. Por favor intenta de nuevo.'}`,
        timestamp: new Date().toISOString(),
        isError: true
      }
      
      messages.value.push(errorMessage)
      
      notifyApiError('/api/workflows/config-chat', err)
      appStore.addToLog(`ConfigAgent error: ${err.message}`, 'error')
      
      return null
      
    } finally {
      isSending.value = false
      isTyping.value = false
    }
  }
  
  /**
   * Reset conversación
   */
  const resetConversation = async () => {
    if (!userId.value || !appStore.currentCompanyId) {
      // Reset local
      clearConversation()
      return true
    }
    
    try {
      await apiRequest('/api/workflows/config-chat/reset', {
        method: 'POST',
        body: {
          company_id: appStore.currentCompanyId,
          user_id: userId.value
        },
        headers: {
          'X-Company-ID': appStore.currentCompanyId
        }
      })
      
      clearConversation()
      
      showNotification('🔄 Conversación reiniciada', 'success')
      appStore.addToLog(
        `[${appStore.currentCompanyId}] Conversation reset: ${userId.value}`,
        'info'
      )
      
      // Iniciar nueva conversación
      await startConversation()
      
      return true
      
    } catch (err) {
      console.error('Error resetting conversation:', err)
      notifyApiError('/api/workflows/config-chat/reset', err)
      
      // Hacer reset local de todas formas
      clearConversation()
      await startConversation()
      
      return false
    }
  }
  
  /**
   * Limpiar estado local
   */
  const clearConversation = () => {
    messages.value = []
    currentStage.value = 'initial'
    userId.value = null
    conversationId.value = null
    workflowDraft.value = null
    error.value = null
    isTyping.value = false
    isSending.value = false
  }
  
  /**
   * Aprobar workflow draft
   */
  const approveWorkflow = async () => {
    if (!workflowDraft.value) {
      showNotification('❌ No hay workflow para aprobar', 'error')
      return false
    }
    
    // Enviar confirmación al agente
    return await sendMessage('Sí, apruebo el workflow')
  }
  
  /**
   * Rechazar workflow draft
   */
  const rejectWorkflow = async (reason = '') => {
    if (!workflowDraft.value) {
      showNotification('❌ No hay workflow para rechazar', 'error')
      return false
    }
    
    const message = reason 
      ? `No, quiero cambiar: ${reason}`
      : 'No, por favor modifícalo'
    
    return await sendMessage(message)
  }
  
  /**
   * Obtener estado de conversación del servidor
   */
  const getConversationStatus = async () => {
    if (!userId.value || !appStore.currentCompanyId) {
      return null
    }
    
    try {
      const response = await apiRequest('/api/workflows/config-chat/status', {
        method: 'GET',
        params: {
          user_id: userId.value,
          company_id: appStore.currentCompanyId
        },
        headers: {
          'X-Company-ID': appStore.currentCompanyId
        }
      })
      
      return response
      
    } catch (err) {
      console.error('Error getting conversation status:', err)
      return null
    }
  }
  
  /**
   * Exportar conversación como JSON
   */
  const exportConversation = () => {
    if (!hasMessages.value) {
      showNotification('❌ No hay mensajes para exportar', 'error')
      return
    }
    
    const exportData = {
      conversation_id: conversationId.value,
      user_id: userId.value,
      company_id: appStore.currentCompanyId,
      stage: currentStage.value,
      messages: messages.value,
      workflow_draft: workflowDraft.value,
      exported_at: new Date().toISOString()
    }
    
    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json'
    })
    const url = URL.createObjectURL(blob)
    
    const link = document.createElement('a')
    link.href = url
    link.download = `conversation_${conversationId.value}_${Date.now()}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    URL.revokeObjectURL(url)
    
    showNotification('✅ Conversación exportada', 'success')
  }
  
  // ============================================================================
  // MÉTODOS DE UTILIDAD
  // ============================================================================
  
  /**
   * Formatear timestamp
   */
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return ''
    
    try {
      const date = new Date(timestamp)
      const now = new Date()
      const diffMs = now - date
      const diffMins = Math.floor(diffMs / 60000)
      
      if (diffMins < 1) return 'Ahora'
      if (diffMins < 60) return `Hace ${diffMins}m`
      
      const diffHours = Math.floor(diffMins / 60)
      if (diffHours < 24) return `Hace ${diffHours}h`
      
      return date.toLocaleDateString('es-ES', {
        day: '2-digit',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch {
      return ''
    }
  }
  
  /**
   * Obtener color de badge por stage
   */
  const getStageColor = (stage) => {
    const colors = {
      'initial': '#6366f1',      // indigo
      'gathering': '#f59e0b',    // amber
      'validating': '#3b82f6',   // blue
      'confirming': '#10b981',   // green
      'complete': '#22c55e'      // green
    }
    
    return colors[stage] || '#6b7280' // gray
  }
  
  /**
   * Obtener label de stage
   */
  const getStageLabel = (stage) => {
    const labels = {
      'initial': '🎯 Inicio',
      'gathering': '📝 Recopilando info',
      'validating': '🔍 Validando',
      'confirming': '✅ Confirmando',
      'complete': '🎉 Completado'
    }
    
    return labels[stage] || stage
  }
  
  // ============================================================================
  // WATCHERS
  // ============================================================================
  
  // Auto-scroll cuando se agregan mensajes
  watch(() => messages.value.length, () => {
    // El componente UI manejará el scroll
  })
  
  // Limpiar conversación si cambia la empresa
  watch(() => appStore.currentCompanyId, (newCompanyId, oldCompanyId) => {
    if (oldCompanyId && newCompanyId !== oldCompanyId && hasMessages.value) {
      console.log('[USE-CHAT] Company changed, clearing conversation')
      clearConversation()
    }
  })
  
  // ============================================================================
  // CLEANUP
  // ============================================================================
  
  const cleanup = () => {
    clearConversation()
    console.log('✅ [USE-CHAT] Cleanup completed')
  }
  
  // ============================================================================
  // RETURN
  // ============================================================================
  
  return {
    // Estado reactivo
    messages,
    isTyping,
    isSending,
    currentStage,
    userId,
    conversationId,
    workflowDraft,
    error,
    
    // Computed
    hasMessages,
    canSendMessage,
    isComplete,
    hasWorkflowDraft,
    lastMessage,
    
    // Métodos principales
    startConversation,
    sendMessage,
    resetConversation,
    clearConversation,
    approveWorkflow,
    rejectWorkflow,
    getConversationStatus,
    exportConversation,
    
    // Utilidades
    formatTimestamp,
    getStageColor,
    getStageLabel,
    
    // Cleanup
    cleanup
  }
}
