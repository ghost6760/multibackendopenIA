// composables/useConversations.js
// Composable para gestión de conversaciones - MIGRACIÓN desde script.js
// CRÍTICO: Mantener comportamiento idéntico para preservar compatibilidad

import { ref, computed } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'

export const useConversations = () => {
  const appStore = useAppStore()
  const { apiRequest } = useApiRequest()
  const { showNotification, notifyApiError, notifyApiSuccess } = useNotifications()
  
  // ============================================================================
  // ESTADO LOCAL
  // ============================================================================
  
  const conversations = ref([])
  const currentConversation = ref(null)
  const isLoading = ref(false)
  const isTesting = ref(false)
  const isLoadingDetail = ref(false)
  const testResults = ref(null)
  
  // ============================================================================
  // COMPUTED PROPERTIES
  // ============================================================================
  
  const hasConversations = computed(() => conversations.value.length > 0)
  
  const conversationsCount = computed(() => conversations.value.length)
  
  const canTestConversation = computed(() => {
    return appStore.hasCompanySelected && !isTesting.value
  })
  
  const recentConversations = computed(() => {
    return conversations.value
      .filter(conv => conv.last_activity)
      .sort((a, b) => new Date(b.last_activity) - new Date(a.last_activity))
      .slice(0, 10)
  })
  
  // ============================================================================
  // MÉTODOS PRINCIPALES - MIGRADOS DESDE SCRIPT.JS
  // ============================================================================
  
  /**
   * Prueba una conversación con el sistema
   * MIGRADO: testConversation() de script.js
   * ⚠️ NO MODIFICAR: Debe mantener comportamiento idéntico
   */
  const testConversation = async () => {
    if (!appStore.currentCompanyId) {
      showNotification('⚠️ Por favor selecciona una empresa primero', 'warning')
      return false
    }
    
    const messageInput = document.getElementById('testMessage')
    const userIdInput = document.getElementById('testUserId')
    
    if (!messageInput || !userIdInput) {
      showNotification('❌ No se encontraron los campos de entrada', 'error')
      return false
    }
    
    const message = messageInput.value.trim()
    const userId = userIdInput.value.trim() || 'test-user'
    
    if (!message) {
      showNotification('❌ Por favor ingresa un mensaje para probar', 'error')
      return false
    }
    
    isTesting.value = true
    testResults.value = null
    
    try {
      appStore.addToLog(`Testing conversation: "${message}" for user ${userId}`, 'info')
      
      const response = await apiRequest('/api/conversations/test', {
        method: 'POST',
        body: {
          message,
          user_id: userId
        }
      })
      
      testResults.value = response
      
      // Mostrar resultados en el DOM - PRESERVAR COMPORTAMIENTO ORIGINAL
      displayTestResults(response)
      
      notifyApiSuccess('Conversación probada exitosamente')
      appStore.addToLog(`Conversation test completed successfully for user ${userId}`, 'info')
      
      return response
      
    } catch (error) {
      console.error('Error testing conversation:', error)
      notifyApiError('/api/conversations/test', error)
      appStore.addToLog(`Conversation test error: ${error.message}`, 'error')
      return false
      
    } finally {
      isTesting.value = false
    }
  }
  
  /**
   * Obtiene una conversación específica
   * MIGRADO: getConversation() de script.js
   */
  const getConversation = async (userId = null) => {
    if (!appStore.currentCompanyId) {
      showNotification('⚠️ Por favor selecciona una empresa primero', 'warning')
      return null
    }
    
    // Obtener userId del input si no se proporciona
    const targetUserId = userId || document.getElementById('manageUserId')?.value?.trim()
    
    if (!targetUserId) {
      showNotification('❌ Por favor proporciona un ID de usuario', 'error')
      return null
    }
    
    isLoadingDetail.value = true
    
    try {
      appStore.addToLog(`Getting conversation for user: ${targetUserId}`, 'info')
      
      const response = await apiRequest(`/api/conversations/${targetUserId}`)
      
      currentConversation.value = response
      
      // Mostrar detalles en el DOM - PRESERVAR COMPORTAMIENTO ORIGINAL
      displayConversationDetails(response)
      
      appStore.addToLog(`Conversation retrieved for user ${targetUserId}`, 'info')
      
      return response
      
    } catch (error) {
      console.error('Error getting conversation:', error)
      notifyApiError(`/api/conversations/${targetUserId}`, error)
      appStore.addToLog(`Error getting conversation for user ${targetUserId}: ${error.message}`, 'error')
      return null
      
    } finally {
      isLoadingDetail.value = false
    }
  }
  
  /**
   * Elimina una conversación
   * MIGRADO: deleteConversation() de script.js
   */
  const deleteConversation = async (userId = null) => {
    if (!appStore.currentCompanyId) {
      showNotification('⚠️ Por favor selecciona una empresa primero', 'warning')
      return false
    }
    
    // Obtener userId del input si no se proporciona
    const targetUserId = userId || document.getElementById('manageUserId')?.value?.trim()
    
    if (!targetUserId) {
      showNotification('❌ Por favor proporciona un ID de usuario', 'error')
      return false
    }
    
    // Confirmar eliminación
    if (!confirm(`¿Estás seguro de que quieres eliminar la conversación del usuario "${targetUserId}"?`)) {
      return false
    }
    
    try {
      appStore.addToLog(`Deleting conversation for user: ${targetUserId}`, 'info')
      
      await apiRequest(`/api/conversations/${targetUserId}`, {
        method: 'DELETE'
      })
      
      // Remover de la lista local
      conversations.value = conversations.value.filter(conv => 
        conv.user_id !== targetUserId && conv.id !== targetUserId
      )
      
      // Limpiar conversación actual si es la que se eliminó
      if (currentConversation.value?.user_id === targetUserId) {
        currentConversation.value = null
      }
      
      // Limpiar detalles del DOM
      const detailsContainer = document.getElementById('conversationDetails')
      if (detailsContainer) {
        detailsContainer.innerHTML = '<p>Conversación eliminada exitosamente.</p>'
      }
      
      notifyApiSuccess('Conversación eliminada')
      appStore.addToLog(`Conversation deleted for user ${targetUserId}`, 'info')
      
      // Actualizar contador en el tab
      window.dispatchEvent(new CustomEvent('updateTabNotificationCount', {
        detail: { tabName: 'conversations', count: conversations.value.length }
      }))
      
      return true
      
    } catch (error) {
      console.error('Error deleting conversation:', error)
      notifyApiError(`/api/conversations/${targetUserId}`, error)
      appStore.addToLog(`Error deleting conversation for user ${targetUserId}: ${error.message}`, 'error')
      return false
    }
  }
  
  /**
   * Carga la lista de conversaciones
   * MIGRADO: loadConversations() de script.js
   */
  const loadConversations = async () => {
    if (!appStore.currentCompanyId) {
      showNotification('⚠️ Por favor selecciona una empresa primero', 'warning')
      return []
    }
    
    isLoading.value = true
    
    try {
      appStore.addToLog(`Loading conversations for company: ${appStore.currentCompanyId}`, 'info')
      
      const response = await apiRequest('/api/conversations')
      
      // Normalizar respuesta
      const conversationsList = Array.isArray(response) ? response : 
                              response.conversations ? response.conversations :
                              response.data ? response.data : []
      
      conversations.value = conversationsList.map(conv => ({
        ...conv,
        // Asegurar campos requeridos
        id: conv.id || conv.user_id || Date.now(),
        user_id: conv.user_id || conv.id,
        messages_count: conv.messages_count || conv.message_count || 0,
        last_activity: conv.last_activity || conv.updated_at || conv.created_at,
        status: conv.status || 'active'
      }))
      
      // Mostrar lista en el DOM - PRESERVAR COMPORTAMIENTO ORIGINAL
      displayConversationsList(conversations.value)
      
      appStore.addToLog(`Loaded ${conversations.value.length} conversations`, 'info')
      
      // Actualizar contador en el tab
      window.dispatchEvent(new CustomEvent('updateTabNotificationCount', {
        detail: { tabName: 'conversations', count: conversations.value.length }
      }))
      
      return conversations.value
      
    } catch (error) {
      console.error('Error loading conversations:', error)
      notifyApiError('/api/conversations', error)
      appStore.addToLog(`Error loading conversations: ${error.message}`, 'error')
      conversations.value = []
      return []
      
    } finally {
      isLoading.value = false
    }
  }
  
  /**
   * Ver detalles de una conversación específica
   * MIGRADO: viewConversationDetail() de script.js
   */
  const viewConversationDetail = async (conversationId) => {
    if (!conversationId) {
      showNotification('❌ ID de conversación no válido', 'error')
      return null
    }
    
    try {
      // Buscar en la lista local primero
      const conversation = conversations.value.find(conv => 
        conv.id === conversationId || conv.user_id === conversationId
      )
      
      if (conversation) {
        return await getConversation(conversation.user_id || conversation.id)
      } else {
        return await getConversation(conversationId)
      }
      
    } catch (error) {
      console.error('Error viewing conversation detail:', error)
      showNotification(`Error al ver detalles: ${error.message}`, 'error')
      return null
    }
  }
  
  /**
   * Elimina una conversación desde la lista
   * MIGRADO: deleteConversationFromList() de script.js
   */
  const deleteConversationFromList = async (conversationId) => {
    try {
      // Buscar la conversación en la lista
      const conversation = conversations.value.find(conv => 
        conv.id === conversationId || conv.user_id === conversationId
      )
      
      if (conversation) {
        return await deleteConversation(conversation.user_id || conversation.id)
      } else {
        return await deleteConversation(conversationId)
      }
      
    } catch (error) {
      console.error('Error deleting conversation from list:', error)
      showNotification(`Error al eliminar conversación: ${error.message}`, 'error')
      return false
    }
  }
  
  // ============================================================================
  // MÉTODOS DE VISUALIZACIÓN - PRESERVAR LÓGICA DOM ORIGINAL
  // ============================================================================
  
  /**
   * Muestra los resultados del test en el DOM
   * PRESERVAR: Lógica exacta del script.js original
   */
  const displayTestResults = (results) => {
    const container = document.getElementById('conversationResult')
    if (!container) return
    
    if (!results || !results.response) {
      container.innerHTML = `
        <div class="result-container result-error">
          <h4>❌ Error en la prueba</h4>
          <p>No se obtuvo respuesta del sistema de conversación.</p>
        </div>
      `
      return
    }
    
    container.innerHTML = `
      <div class="result-container result-success">
        <h4>✅ Conversación Probada Exitosamente</h4>
        <div class="conversation-test-result">
          <div class="test-message">
            <strong>📤 Mensaje enviado:</strong>
            <p>${escapeHTML(results.message || results.input || 'N/A')}</p>
          </div>
          
          <div class="test-response">
            <strong>📥 Respuesta del sistema:</strong>
            <div class="response-content">
              ${escapeHTML(results.response)}
            </div>
          </div>
          
          ${results.debug_info ? `
            <div class="test-debug">
              <details>
                <summary><strong>🔧 Información de debug</strong></summary>
                <pre>${escapeHTML(JSON.stringify(results.debug_info, null, 2))}</pre>
              </details>
            </div>
          ` : ''}
          
          <div class="test-metadata">
            <small>
              <strong>👤 Usuario:</strong> ${escapeHTML(results.user_id || 'test-user')} | 
              <strong>🕒 Timestamp:</strong> ${new Date().toLocaleString()} |
              <strong>🏢 Empresa:</strong> ${escapeHTML(appStore.currentCompanyId)}
            </small>
          </div>
        </div>
      </div>
    `
  }
  
  /**
   * Muestra los detalles de una conversación en el DOM
   * PRESERVAR: Lógica exacta del script.js original
   */
  const displayConversationDetails = (conversation) => {
    const container = document.getElementById('conversationDetails')
    if (!container) return
    
    if (!conversation) {
      container.innerHTML = `
        <div class="result-container result-warning">
          <h4>⚠️ Conversación no encontrada</h4>
          <p>No se encontró ninguna conversación para este usuario.</p>
        </div>
      `
      return
    }
    
    const messages = conversation.messages || conversation.conversation || []
    const messagesHtml = Array.isArray(messages) 
      ? messages.map(msg => `
          <div class="message-item ${msg.role || 'user'}">
            <div class="message-header">
              <span class="message-role">${msg.role === 'assistant' ? '🤖 Asistente' : '👤 Usuario'}</span>
              <span class="message-time">${formatMessageTime(msg.timestamp || msg.created_at)}</span>
            </div>
            <div class="message-content">${escapeHTML(msg.content || msg.message || '')}</div>
          </div>
        `).join('')
      : '<p>No hay mensajes en esta conversación.</p>'
    
    container.innerHTML = `
      <div class="result-container result-info">
        <h4>💬 Detalles de la Conversación</h4>
        <div class="conversation-details">
          <div class="conversation-meta">
            <div class="meta-item">
              <strong>👤 Usuario ID:</strong> ${escapeHTML(conversation.user_id || conversation.id || 'N/A')}
            </div>
            <div class="meta-item">
              <strong>📊 Total mensajes:</strong> ${messages.length || 0}
            </div>
            <div class="meta-item">
              <strong>🕒 Última actividad:</strong> ${formatLastActivity(conversation.last_activity || conversation.updated_at)}
            </div>
            <div class="meta-item">
              <strong>📍 Estado:</strong> ${escapeHTML(conversation.status || 'activa')}
            </div>
          </div>
          
          <div class="conversation-messages">
            <h5>📝 Historial de mensajes:</h5>
            <div class="messages-list">
              ${messagesHtml}
            </div>
          </div>
          
          ${conversation.metadata ? `
            <div class="conversation-metadata">
              <details>
                <summary><strong>🔧 Metadatos adicionales</strong></summary>
                <pre>${escapeHTML(JSON.stringify(conversation.metadata, null, 2))}</pre>
              </details>
            </div>
          ` : ''}
        </div>
      </div>
    `
  }
  
  /**
   * Muestra la lista de conversaciones en el DOM
   * PRESERVAR: Lógica exacta del script.js original
   */
  const displayConversationsList = (conversationsList) => {
    const container = document.getElementById('conversationsList')
    if (!container) return
    
    if (!conversationsList || conversationsList.length === 0) {
      container.innerHTML = `
        <div class="no-data">
          <div class="no-data-icon">💬</div>
          <h4>No hay conversaciones</h4>
          <p>No hay conversaciones registradas para esta empresa.</p>
        </div>
      `
      return
    }
    
    const conversationsHtml = conversationsList.map(conv => `
      <div class="conversation-list-item" data-user-id="${conv.user_id || conv.id}">
        <div class="conversation-header">
          <div class="conversation-info">
            <h5 class="conversation-user">👤 ${escapeHTML(conv.user_id || conv.id)}</h5>
            <div class="conversation-stats">
              <span class="stat">📝 ${conv.messages_count || 0} mensajes</span>
              <span class="stat">🕒 ${formatLastActivity(conv.last_activity)}</span>
              <span class="stat status-${conv.status || 'active'}">
                📍 ${escapeHTML(conv.status || 'activa')}
              </span>
            </div>
          </div>
          
          <div class="conversation-actions">
            <button onclick="window.viewConversationDetail('${conv.user_id || conv.id}')" class="btn-sm btn-primary">
              👁️ Ver
            </button>
            <button onclick="window.deleteConversationFromList('${conv.user_id || conv.id}')" class="btn-sm btn-danger">
              🗑️ Eliminar
            </button>
          </div>
        </div>
        
        ${conv.last_message ? `
          <div class="conversation-preview">
            <strong>Último mensaje:</strong>
            <p>${escapeHTML(conv.last_message.substring(0, 100))}${conv.last_message.length > 100 ? '...' : ''}</p>
          </div>
        ` : ''}
      </div>
    `).join('')
    
    container.innerHTML = `
      <div class="conversations-list-container">
        <div class="list-header">
          <h4>📋 Conversaciones (${conversationsList.length})</h4>
          <button onclick="window.loadConversations()" class="btn-sm btn-secondary">
            🔄 Actualizar
          </button>
        </div>
        <div class="conversations-grid">
          ${conversationsHtml}
        </div>
      </div>
    `
  }
  
  // ============================================================================
  // MÉTODOS DE UTILIDAD
  // ============================================================================
  
  /**
   * Formatea el tiempo de un mensaje
   */
  const formatMessageTime = (timestamp) => {
    if (!timestamp) return 'Desconocido'
    
    try {
      const date = new Date(timestamp)
      return date.toLocaleTimeString('es-ES')
    } catch {
      return 'Hora inválida'
    }
  }
  
  /**
   * Formatea la última actividad
   */
  const formatLastActivity = (lastActivity) => {
    if (!lastActivity) return 'Nunca'
    
    try {
      const date = new Date(lastActivity)
      const now = new Date()
      const diffTime = Math.abs(now - date)
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
      
      if (diffDays === 0) return 'Hoy'
      if (diffDays === 1) return 'Ayer'
      if (diffDays < 7) return `Hace ${diffDays} días`
      if (diffDays < 30) return `Hace ${Math.floor(diffDays / 7)} semanas`
      
      return date.toLocaleDateString('es-ES')
    } catch {
      return 'Fecha inválida'
    }
  }
  
  /**
   * Escapa HTML para prevenir XSS
   * PRESERVAR: Función exacta del script.js
   */
  const escapeHTML = (text) => {
    if (!text) return ''
    
    const div = document.createElement('div')
    div.textContent = text
    return div.innerHTML
  }
  
  // ============================================================================
  // RETURN DEL COMPOSABLE
  // ============================================================================
  
  return {
    // Estado
    conversations,
    currentConversation,
    isLoading,
    isTesting,
    isLoadingDetail,
    testResults,
    
    // Computed
    hasConversations,
    conversationsCount,
    canTestConversation,
    recentConversations,
    
    // Métodos principales
    testConversation,
    getConversation,
    deleteConversation,
    loadConversations,
    viewConversationDetail,
    deleteConversationFromList,
    
    // Métodos de visualización
    displayTestResults,
    displayConversationDetails,
    displayConversationsList,
    
    // Métodos de utilidad
    formatMessageTime,
    formatLastActivity,
    escapeHTML
  }
}
