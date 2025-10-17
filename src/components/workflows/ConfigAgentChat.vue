<template>
  <div class="config-agent-chat">
    <!-- Chat Header -->
    <div class="chat-header">
      <div class="chat-header-info">
        <h3>💬 Asistente de Workflows</h3>
        <div class="chat-status">
          <span class="status-badge" :style="{ background: getStageColor(currentStage) }">
            {{ getStageLabel(currentStage) }}
          </span>
          <span v-if="conversationId" class="conversation-id">
            ID: {{ conversationId.substring(0, 12) }}...
          </span>
        </div>
      </div>
      
      <div class="chat-header-actions">
        <button 
          @click="handleExport"
          :disabled="!hasMessages"
          class="btn-icon"
          title="Exportar conversación"
        >
          📥
        </button>
        <button 
          @click="handleReset"
          :disabled="isSending"
          class="btn-icon"
          title="Nueva conversación"
        >
          🔄
        </button>
      </div>
    </div>
    
    <!-- Messages Container -->
    <div class="chat-messages" ref="messagesContainer">
      <!-- Empty State -->
      <div v-if="!hasMessages" class="chat-empty">
        <div class="empty-icon">🤖</div>
        <h4>Asistente de Configuración de Workflows</h4>
        <p>
          Dime qué workflow quieres crear y yo te ayudaré paso a paso.
        </p>
        <div class="example-prompts">
          <button 
            v-for="example in examplePrompts" 
            :key="example"
            @click="handleExampleClick(example)"
            class="example-prompt-btn"
          >
            {{ example }}
          </button>
        </div>
      </div>
      
      <!-- Message List -->
      <div v-else class="messages-list">
        <div
          v-for="message in messages"
          :key="message.id"
          :class="['message', `message-${message.role}`, { 'message-error': message.isError }]"
        >
          <!-- Message Avatar -->
          <div class="message-avatar">
            <span v-if="message.role === 'user'">👤</span>
            <span v-else-if="message.role === 'assistant'">🤖</span>
            <span v-else>⚠️</span>
          </div>
          
          <!-- Message Content -->
          <div class="message-content">
            <div class="message-header">
              <span class="message-sender">
                {{ message.role === 'user' ? 'Tú' : 'Asistente' }}
              </span>
              <span class="message-time">
                {{ formatTimestamp(message.timestamp) }}
              </span>
            </div>
            
            <div class="message-text" v-html="formatMessageContent(message.content)"></div>
            
            <!-- Workflow Preview (si existe en el mensaje) -->
            <div v-if="message.workflow_preview" class="workflow-preview-inline">
              <WorkflowPreviewCard :workflow="message.workflow_preview" />
            </div>
          </div>
        </div>
        
        <!-- Typing Indicator -->
        <div v-if="isTyping" class="message message-assistant typing-indicator">
          <div class="message-avatar">
            <span>🤖</span>
          </div>
          <div class="message-content">
            <div class="typing-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Workflow Draft Preview (si existe) -->
    <div v-if="hasWorkflowDraft && !isComplete" class="workflow-draft-container">
      <div class="draft-header">
        <span>📋 Workflow Generado</span>
        <button @click="toggleDraftPreview" class="btn-toggle">
          {{ showDraftPreview ? '▼ Ocultar' : '▶ Ver' }}
        </button>
      </div>
      
      <div v-if="showDraftPreview" class="draft-content">
        <WorkflowPreviewCard :workflow="workflowDraft" />
        
        <div class="draft-actions">
          <button 
            @click="handleApprove"
            :disabled="isSending"
            class="btn btn-success"
          >
            ✅ Aprobar y Guardar
          </button>
          <button 
            @click="handleReject"
            :disabled="isSending"
            class="btn btn-outline"
          >
            ❌ Modificar
          </button>
        </div>
      </div>
    </div>
    
    <!-- Chat Input -->
    <div class="chat-input-container">
      <div class="chat-input-wrapper">
        <textarea
          ref="inputElement"
          v-model="messageInput"
          @keydown.enter.exact.prevent="handleSend"
          @keydown.enter.shift.exact="messageInput += '\n'"
          :disabled="isSending || isTyping"
          placeholder="Escribe tu mensaje... (Enter para enviar, Shift+Enter para nueva línea)"
          class="chat-input"
          rows="1"
        ></textarea>
        
        <button
          @click="handleSend"
          :disabled="!canSend"
          class="btn-send"
          title="Enviar mensaje"
        >
          <span v-if="isSending">⏳</span>
          <span v-else>📤</span>
        </button>
      </div>
      
      <!-- Input hints -->
      <div class="chat-hints">
        <span v-if="currentStage === 'confirming'" class="hint-text">
          💡 Responde "sí" para aprobar o describe cambios que quieras hacer
        </span>
        <span v-else-if="currentStage === 'gathering'" class="hint-text">
          💡 Proporciona detalles sobre qué debe hacer el workflow
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { useChatConversation } from '@/composables/useChatConversation'
import { useNotifications } from '@/composables/useNotifications'
import WorkflowPreviewCard from './WorkflowPreviewCard.vue'

// ============================================================================
// PROPS & EMITS
// ============================================================================

const props = defineProps({
  autoFocus: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits([
  'workflow-created',
  'conversation-reset'
])

// ============================================================================
// STORES & COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const { showNotification } = useNotifications()

const {
  // Estado
  messages,
  isTyping,
  isSending,
  currentStage,
  conversationId,
  workflowDraft,
  hasMessages,
  hasWorkflowDraft,
  canSendMessage,
  isComplete,
  
  // Métodos
  startConversation,
  sendMessage,
  resetConversation,
  approveWorkflow,
  rejectWorkflow,
  exportConversation,
  
  // Utilidades
  formatTimestamp,
  getStageColor,
  getStageLabel,
  
  // Cleanup
  cleanup
} = useChatConversation()

// ============================================================================
// ESTADO LOCAL
// ============================================================================

const messageInput = ref('')
const messagesContainer = ref(null)
const inputElement = ref(null)
const showDraftPreview = ref(true)

const examplePrompts = [
  '💉 Workflow para consultas de Botox',
  '📅 Workflow de agendamiento automático',
  '🆘 Workflow para emergencias médicas',
  '💰 Workflow de ventas y cotizaciones'
]

// ============================================================================
// COMPUTED
// ============================================================================

const canSend = computed(() => {
  return messageInput.value.trim() && canSendMessage.value
})

// ============================================================================
// MÉTODOS PRINCIPALES
// ============================================================================

const handleSend = async () => {
  if (!canSend.value) return
  
  const text = messageInput.value.trim()
  messageInput.value = ''
  
  // Auto-resize textarea
  if (inputElement.value) {
    inputElement.value.style.height = 'auto'
  }
  
  const response = await sendMessage(text)
  
  if (response) {
    scrollToBottom()
  }
}

const handleExampleClick = (example) => {
  messageInput.value = example
  handleSend()
}

const handleApprove = async () => {
  const success = await approveWorkflow()
  
  if (success && isComplete.value) {
    showNotification('✅ Workflow creado exitosamente', 'success')
    emit('workflow-created', workflowDraft.value)
  }
}

const handleReject = async () => {
  const reason = prompt('¿Qué te gustaría cambiar del workflow?')
  
  if (reason !== null) {
    await rejectWorkflow(reason)
  }
}

const handleReset = async () => {
  const confirmed = confirm('¿Estás seguro de que quieres iniciar una nueva conversación?')
  
  if (confirmed) {
    await resetConversation()
    emit('conversation-reset')
    
    if (inputElement.value) {
      inputElement.value.focus()
    }
  }
}

const handleExport = () => {
  exportConversation()
}

const toggleDraftPreview = () => {
  showDraftPreview.value = !showDraftPreview.value
}

// ============================================================================
// MÉTODOS DE UTILIDAD
// ============================================================================

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

const formatMessageContent = (content) => {
  if (!content) return ''
  
  // Convertir markdown básico a HTML
  let formatted = content
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>')
  
  return formatted
}

// Auto-resize textarea
const autoResizeTextarea = () => {
  if (inputElement.value) {
    inputElement.value.style.height = 'auto'
    inputElement.value.style.height = Math.min(inputElement.value.scrollHeight, 150) + 'px'
  }
}

// ============================================================================
// LIFECYCLE
// ============================================================================

onMounted(async () => {
  // Iniciar conversación automáticamente
  await startConversation()
  
  if (props.autoFocus && inputElement.value) {
    inputElement.value.focus()
  }
  
  appStore.addToLog('ConfigAgentChat mounted', 'info')
})

onUnmounted(() => {
  cleanup()
})

// ============================================================================
// WATCHERS
// ============================================================================

watch(() => messages.value.length, () => {
  scrollToBottom()
})

watch(() => messageInput.value, () => {
  autoResizeTextarea()
})

// Detectar cuando el workflow está completo
watch(() => isComplete.value, (complete) => {
  if (complete) {
    showNotification('🎉 ¡Workflow completado!', 'success', 5000)
  }
})
</script>

<style scoped>
.config-agent-chat {
  display: flex;
  flex-direction: column;
  height: 600px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
}

/* Chat Header */
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-color);
}

.chat-header-info h3 {
  margin: 0 0 5px 0;
  color: var(--text-primary);
  font-size: 1.1em;
}

.chat-status {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.85em;
}

.status-badge {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 12px;
  color: white;
  font-size: 0.85em;
  font-weight: 500;
}

.conversation-id {
  color: var(--text-muted);
  font-family: monospace;
  font-size: 0.8em;
}

.chat-header-actions {
  display: flex;
  gap: 8px;
}

.btn-icon {
  background: none;
  border: 1px solid var(--border-color);
  padding: 6px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1.1em;
  transition: all 0.2s ease;
}

.btn-icon:hover:not(:disabled) {
  background: var(--bg-secondary);
  transform: scale(1.05);
}

.btn-icon:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Messages Container */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: var(--bg-primary);
}

.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  padding: 40px 20px;
  color: var(--text-secondary);
}

.empty-icon {
  font-size: 4em;
  margin-bottom: 20px;
  opacity: 0.5;
}

.chat-empty h4 {
  margin: 0 0 10px 0;
  color: var(--text-primary);
}

.chat-empty p {
  margin: 0 0 20px 0;
  line-height: 1.5;
}

.example-prompts {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  max-width: 400px;
}

.example-prompt-btn {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  padding: 10px 15px;
  border-radius: 6px;
  cursor: pointer;
  color: var(--text-primary);
  transition: all 0.2s ease;
  text-align: left;
}

.example-prompt-btn:hover {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
  transform: translateX(5px);
}

/* Messages */
.messages-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.message {
  display: flex;
  gap: 12px;
  animation: slideIn 0.3s ease;
}

.message-user {
  flex-direction: row-reverse;
}

.message-avatar {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2em;
  background: var(--bg-tertiary);
}

.message-user .message-avatar {
  background: var(--primary-color);
}

.message-content {
  flex: 1;
  max-width: 70%;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 12px 15px;
}

.message-user .message-content {
  background: rgba(102, 126, 234, 0.1);
  border-color: var(--primary-color);
}

.message-error .message-content {
  background: rgba(239, 68, 68, 0.1);
  border-color: var(--danger-color);
}

.message-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
  font-size: 0.85em;
}

.message-sender {
  font-weight: 600;
  color: var(--text-primary);
}

.message-time {
  color: var(--text-muted);
}

.message-text {
  color: var(--text-secondary);
  line-height: 1.5;
  word-wrap: break-word;
}

.message-text :deep(strong) {
  color: var(--text-primary);
  font-weight: 600;
}

.message-text :deep(code) {
  background: var(--bg-tertiary);
  padding: 2px 6px;
  border-radius: 3px;
  font-family: monospace;
  font-size: 0.9em;
}

/* Typing Indicator */
.typing-indicator .message-content {
  padding: 15px 20px;
}

.typing-dots {
  display: flex;
  gap: 4px;
}

.typing-dots span {
  width: 8px;
  height: 8px;
  background: var(--text-muted);
  border-radius: 50%;
  animation: typing 1.4s infinite;
}

.typing-dots span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-dots span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.5;
  }
  30% {
    transform: translateY(-10px);
    opacity: 1;
  }
}

/* Workflow Draft */
.workflow-draft-container {
  border-top: 1px solid var(--border-color);
  background: var(--bg-tertiary);
  padding: 15px;
}

.draft-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  font-weight: 600;
  color: var(--text-primary);
}

.btn-toggle {
  background: none;
  border: 1px solid var(--border-color);
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85em;
  color: var(--text-secondary);
}

.btn-toggle:hover {
  background: var(--bg-secondary);
}

.draft-content {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 15px;
}

.draft-actions {
  display: flex;
  gap: 10px;
  margin-top: 15px;
}

/* Chat Input */
.chat-input-container {
  border-top: 1px solid var(--border-color);
  background: var(--bg-secondary);
  padding: 15px;
}

.chat-input-wrapper {
  display: flex;
  gap: 10px;
  align-items: flex-end;
}

.chat-input {
  flex: 1;
  padding: 10px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: inherit;
  font-size: 14px;
  resize: none;
  max-height: 150px;
  min-height: 40px;
  transition: border-color 0.2s ease;
}

.chat-input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.chat-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-send {
  background: var(--primary-color);
  border: none;
  color: white;
  padding: 10px 15px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1.2em;
  transition: background-color 0.2s ease;
  flex-shrink: 0;
}

.btn-send:hover:not(:disabled) {
  background: var(--primary-color-dark);
}

.btn-send:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.chat-hints {
  margin-top: 8px;
  font-size: 0.85em;
}

.hint-text {
  color: var(--text-muted);
  font-style: italic;
}

/* Buttons */
.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9em;
  font-weight: 500;
  transition: all 0.2s ease;
}

.btn-success {
  background: var(--success-color);
  color: white;
}

.btn-success:hover:not(:disabled) {
  background: #16a34a;
}

.btn-outline {
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.btn-outline:hover:not(:disabled) {
  background: var(--bg-primary);
  color: var(--text-primary);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Animations */
@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Scrollbar */
.chat-messages::-webkit-scrollbar {
  width: 8px;
}

.chat-messages::-webkit-scrollbar-track {
  background: var(--bg-secondary);
}

.chat-messages::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 4px;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: var(--text-muted);
}

/* Responsive */
@media (max-width: 768px) {
  .config-agent-chat {
    height: 500px;
  }
  
  .chat-header {
    padding: 12px 15px;
  }
  
  .chat-messages {
    padding: 15px;
  }
  
  .message-content {
    max-width: 85%;
  }
  
  .example-prompts {
    max-width: 100%;
  }
  
  .draft-actions {
    flex-direction: column;
  }
}
</style>
