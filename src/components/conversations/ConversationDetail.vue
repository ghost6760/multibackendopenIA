<template>
  <div class="conversation-detail">
    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner">⏳</div>
      <p>Cargando conversación...</p>
    </div>
    
    <!-- Conversation Details -->
    <div v-else-if="conversation" class="conversation-content">
      <!-- Conversation Header -->
      <div class="conversation-header">
        <div class="conversation-info">
          <h4 class="conversation-title">
            👤 Conversación: {{ conversation.user_id || conversation.id }}
          </h4>
          <div class="conversation-meta">
            <span class="meta-item">
              💬 {{ getMessageCount() }} mensajes
            </span>
            <span class="meta-item">
              🕒 {{ formatDate(conversation.last_message_at || conversation.updated_at) }}
            </span>
            <span class="meta-item">
              🏢 {{ conversation.company_id || getCurrentCompany() }}
            </span>
            <span v-if="conversation.status" class="meta-item">
              📊 {{ conversation.status }}
            </span>
          </div>
        </div>
        
        <div class="conversation-actions">
          <button @click="refreshConversation" class="btn btn-secondary" :disabled="loading">
            🔄 Actualizar
          </button>
          <button @click="exportConversation" class="btn btn-info">
            📥 Exportar
          </button>
          <button @click="deleteConversationConfirm" class="btn btn-danger">
            🗑️ Eliminar
          </button>
        </div>
      </div>
      
      <!-- Message History -->
      <div class="message-history">
        <div class="messages-container" ref="messagesContainer">
          <!-- No messages state -->
          <div v-if="!hasMessages" class="no-messages">
            <div class="no-messages-icon">💬</div>
            <p>No hay mensajes en esta conversación</p>
          </div>
          
          <!-- Messages list -->
          <div v-else class="messages-list">
            <div
              v-for="(message, index) in conversationMessages"
              :key="index"
              class="message-item"
              :class="getMessageClass(message.role || message.sender)"
            >
              <!-- Message header -->
              <div class="message-header">
                <span class="message-sender">
                  {{ getMessageSender(message.role || message.sender) }}
                </span>
                <span class="message-timestamp">
                  {{ formatMessageTime(message.timestamp || message.created_at) }}
                </span>
              </div>
              
              <!-- Message content -->
              <div class="message-content">
                <div class="message-text">
                  {{ message.content || message.text || message.message }}
                </div>
                
                <!-- Message metadata -->
                <div v-if="message.metadata" class="message-metadata">
                  <small v-if="message.metadata.model">Modelo: {{ message.metadata.model }}</small>
                  <small v-if="message.metadata.tokens">Tokens: {{ message.metadata.tokens }}</small>
                  <small v-if="message.metadata.processing_time">
                    Tiempo: {{ message.metadata.processing_time }}ms
                  </small>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Conversation Statistics -->
      <div v-if="showStatistics" class="conversation-statistics">
        <h5>📊 Estadísticas de la Conversación</h5>
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-label">Mensajes del usuario:</span>
            <span class="stat-value">{{ getUserMessageCount() }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Respuestas del bot:</span>
            <span class="stat-value">{{ getBotMessageCount() }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Duración:</span>
            <span class="stat-value">{{ getConversationDuration() }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Promedio de respuesta:</span>
            <span class="stat-value">{{ getAverageResponseTime() }}</span>
          </div>
        </div>
      </div>
      
      <!-- Raw JSON View (Expandable) -->
      <div class="raw-data-section">
        <details class="raw-data-details">
          <summary class="raw-data-summary">
            <span class="raw-data-icon">🔧</span>
            <strong>Ver datos raw (JSON)</strong>
            <span class="raw-data-toggle">▼</span>
          </summary>
          <div class="raw-data-content">
            <pre class="raw-data-json">{{ formatConversationJSON() }}</pre>
          </div>
        </details>
      </div>
    </div>
    
    <!-- Empty State -->
    <div v-else class="empty-state">
      <div class="empty-icon">👤</div>
      <p>Los detalles de la conversación aparecerán aquí</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { useNotifications } from '@/composables/useNotifications'

// ============================================================================
// PROPS & EMITS
// ============================================================================

const props = defineProps({
  conversation: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  },
  showStatistics: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['refresh', 'delete'])

// ============================================================================
// STORES & COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const { showNotification } = useNotifications()

// ============================================================================
// ESTADO LOCAL
// ============================================================================

const messagesContainer = ref(null)

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const conversationMessages = computed(() => {
  if (!props.conversation) return []
  
  // Intentar obtener mensajes de diferentes formatos posibles
  const messages = props.conversation.history || 
                  props.conversation.messages || 
                  props.conversation.data || 
                  []
  
  return Array.isArray(messages) ? messages : []
})

const hasMessages = computed(() => {
  return conversationMessages.value.length > 0
})

// ============================================================================
// MÉTODOS PRINCIPALES
// ============================================================================

/**
 * Refresh conversation
 */
const refreshConversation = () => {
  emit('refresh')
  showNotification('🔄 Actualizando conversación...', 'info', 2000)
}

/**
 * Export conversation
 */
const exportConversation = () => {
  try {
    const data = {
      user_id: props.conversation.user_id || props.conversation.id,
      company_id: props.conversation.company_id || getCurrentCompany(),
      exported_at: new Date().toISOString(),
      message_count: getMessageCount(),
      messages: conversationMessages.value,
      metadata: {
        user_messages: getUserMessageCount(),
        bot_messages: getBotMessageCount(),
        duration: getConversationDuration(),
        average_response_time: getAverageResponseTime()
      },
      raw_data: props.conversation
    }
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    
    const link = document.createElement('a')
    link.href = url
    link.download = `conversation_${data.user_id}_${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    URL.revokeObjectURL(url)
    
    showNotification('📥 Conversación exportada correctamente', 'success')
    appStore.addToLog('Conversation exported successfully', 'info')
    
  } catch (error) {
    console.error('Error exporting conversation:', error)
    showNotification('❌ Error al exportar conversación', 'error')
  }
}

/**
 * Delete conversation with confirmation
 */
const deleteConversationConfirm = () => {
  const userId = props.conversation.user_id || props.conversation.id
  const confirmed = confirm(`¿Estás seguro de que quieres eliminar la conversación de ${userId}?`)
  
  if (confirmed) {
    emit('delete', userId)
  }
}

// ============================================================================
// UTILITY METHODS
// ============================================================================

/**
 * Get message count
 */
const getMessageCount = () => {
  if (props.conversation?.message_count) {
    return props.conversation.message_count
  }
  return conversationMessages.value.length
}

/**
 * Get message class based on role
 */
const getMessageClass = (role) => {
  const roleMap = {
    'user': 'message-user',
    'assistant': 'message-assistant',
    'bot': 'message-assistant',
    'system': 'message-system'
  }
  return roleMap[role] || 'message-unknown'
}

/**
 * Get message sender display name
 */
const getMessageSender = (role) => {
  const senderMap = {
    'user': '👤 Usuario',
    'assistant': '🤖 Asistente',
    'bot': '🤖 Bot',
    'system': '⚙️ Sistema'
  }
  return senderMap[role] || `📝 ${role}`
}

/**
 * Get user message count
 */
const getUserMessageCount = () => {
  return conversationMessages.value.filter(msg => 
    (msg.role === 'user' || msg.sender === 'user')
  ).length
}

/**
 * Get bot message count
 */
const getBotMessageCount = () => {
  return conversationMessages.value.filter(msg => 
    (msg.role === 'assistant' || msg.role === 'bot' || msg.sender === 'bot' || msg.sender === 'assistant')
  ).length
}

/**
 * Get conversation duration
 */
const getConversationDuration = () => {
  if (conversationMessages.value.length < 2) return 'N/A'
  
  const firstMessage = conversationMessages.value[0]
  const lastMessage = conversationMessages.value[conversationMessages.value.length - 1]
  
  const startTime = new Date(firstMessage.timestamp || firstMessage.created_at)
  const endTime = new Date(lastMessage.timestamp || lastMessage.created_at)
  
  const diffMs = endTime - startTime
  const diffMinutes = Math.round(diffMs / (1000 * 60))
  
  if (diffMinutes < 1) return 'Menos de 1 minuto'
  if (diffMinutes < 60) return `${diffMinutes} minutos`
  
  const diffHours = Math.round(diffMinutes / 60)
  return `${diffHours} horas`
}

/**
 * Get average response time
 */
const getAverageResponseTime = () => {
  const botMessages = conversationMessages.value.filter(msg => 
    (msg.role === 'assistant' || msg.role === 'bot')
  )
  
  if (botMessages.length === 0) return 'N/A'
  
  const totalTime = botMessages.reduce((sum, msg) => {
    const responseTime = msg.metadata?.processing_time || msg.processing_time || 0
    return sum + responseTime
  }, 0)
  
  const avgTime = Math.round(totalTime / botMessages.length)
  return avgTime > 0 ? `${avgTime}ms` : 'N/A'
}

/**
 * Get current company
 */
const getCurrentCompany = () => {
  return appStore.currentCompanyId || 'N/A'
}

/**
 * Format date
 */
const formatDate = (dateString) => {
  if (!dateString) return 'Fecha desconocida'
  
  try {
    const date = new Date(dateString)
    return date.toLocaleString('es-ES')
  } catch {
    return 'Fecha inválida'
  }
}

/**
 * Format message time
 */
const formatMessageTime = (timestamp) => {
  if (!timestamp) return 'Sin fecha'
  
  try {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('es-ES')
  } catch {
    return 'Fecha inválida'
  }
}

/**
 * Format conversation JSON
 */
const formatConversationJSON = () => {
  return JSON.stringify(props.conversation, null, 2)
}

// ============================================================================
// LIFECYCLE HOOKS
// ============================================================================

onMounted(() => {
  // Scroll to bottom of messages when component mounts
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
})
</script>

<style scoped>
.conversation-detail {
  width: 100%;
}

.loading-state {
  text-align: center;
  padding: 30px 20px;
  color: var(--text-secondary);
}

.loading-spinner {
  font-size: 1.5em;
  margin-bottom: 10px;
  animation: spin 1s linear infinite;
}

.conversation-content {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
}

.conversation-header {
  padding: 15px 20px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 15px;
}

.conversation-info {
  flex: 1;
}

.conversation-title {
  margin: 0 0 8px 0;
  color: var(--text-primary);
  font-size: 1.1em;
}

.conversation-meta {
  display: flex;
  gap: 15px;
  font-size: 0.85em;
  color: var(--text-secondary);
  flex-wrap: wrap;
}

.meta-item {
  white-space: nowrap;
}

.conversation-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.message-history {
  max-height: 400px;
  overflow-y: auto;
}

.messages-container {
  padding: 15px;
}

.no-messages {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-muted);
}

.no-messages-icon {
  font-size: 2em;
  margin-bottom: 10px;
  opacity: 0.5;
}

.messages-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message-item {
  border-radius: 8px;
  padding: 12px;
  border-left: 3px solid;
}

.message-user {
  background: rgba(102, 126, 234, 0.1);
  border-left-color: var(--primary-color);
  margin-left: 20px;
}

.message-assistant {
  background: rgba(34, 197, 94, 0.1);
  border-left-color: var(--success-color);
  margin-right: 20px;
}

.message-system {
  background: rgba(156, 163, 175, 0.1);
  border-left-color: var(--text-muted);
}

.message-unknown {
  background: var(--bg-secondary);
  border-left-color: var(--border-color);
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  font-size: 0.85em;
}

.message-sender {
  font-weight: 600;
  color: var(--text-primary);
}

.message-timestamp {
  color: var(--text-muted);
}

.message-content {
  color: var(--text-primary);
}

.message-text {
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.message-metadata {
  margin-top: 8px;
  display: flex;
  gap: 12px;
  font-size: 0.75em;
  color: var(--text-muted);
}

.conversation-statistics {
  padding: 15px 20px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-secondary);
}

.conversation-statistics h5 {
  margin: 0 0 12px 0;
  color: var(--text-primary);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 10px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.9em;
}

.stat-label {
  color: var(--text-secondary);
}

.stat-value {
  color: var(--text-primary);
  font-weight: 600;
}

.raw-data-section {
  border-top: 1px solid var(--border-color);
}

.raw-data-details {
  background: var(--bg-secondary);
}

.raw-data-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  cursor: pointer;
  user-select: none;
  list-style: none;
  color: var(--text-secondary);
}

.raw-data-summary::-webkit-details-marker {
  display: none;
}

.raw-data-icon {
  font-size: 1.1em;
}

.raw-data-toggle {
  margin-left: auto;
  font-size: 0.8em;
}

.raw-data-details[open] .raw-data-toggle {
  transform: rotate(180deg);
}

.raw-data-content {
  border-top: 1px solid var(--border-color);
  padding: 15px 20px;
  background: var(--bg-primary);
}

.raw-data-json {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 12px;
  font-size: 0.8em;
  color: var(--text-secondary);
  margin: 0;
  overflow-x: auto;
  white-space: pre;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-muted);
}

.empty-icon {
  font-size: 2em;
  margin-bottom: 10px;
  opacity: 0.5;
}

.btn {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85em;
  font-weight: 500;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-primary);
  color: var(--text-primary);
}

.btn-info {
  background: var(--info-color);
  color: white;
}

.btn-info:hover {
  background: var(--info-color-dark);
}

.btn-danger {
  background: var(--danger-color);
  color: white;
}

.btn-danger:hover {
  background: var(--danger-color-dark);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Responsive */
@media (max-width: 768px) {
  .conversation-header {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }
  
  .conversation-actions {
    justify-content: center;
  }
  
  .conversation-meta {
    flex-direction: column;
    gap: 5px;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .stat-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
  
  .message-user {
    margin-left: 10px;
  }
  
  .message-assistant {
    margin-right: 10px;
  }
}

@media (max-width: 480px) {
  .conversation-header {
    padding: 12px 15px;
  }
  
  .messages-container {
    padding: 12px;
  }
  
  .message-item {
    padding: 10px;
  }
  
  .conversation-actions {
    flex-direction: column;
  }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .loading-spinner {
    animation: none;
  }
  
  .raw-data-toggle {
    transition: none;
  }
}
</style>
