<template>
  <div class="conversation-manager">
    <div class="manager-header">
      <h3>👤 Gestión de Conversaciones</h3>
      <div v-if="showStats" class="conversation-stats">
        <span class="stat-item">
          Total: {{ totalConversations }}
        </span>
        <span class="stat-item">
          Activas: {{ activeConversations }}
        </span>
      </div>
    </div>
    
    <!-- User ID Input -->
    <div class="form-group">
      <label for="manageUserId">ID de Usuario</label>
      <input 
        type="text" 
        id="manageUserId"
        v-model="userId"
        placeholder="user123"
        :disabled="isLoading"
        @keyup.enter="handleGetConversation"
        class="user-input"
      >
      <small class="input-hint">
        Ingresa el ID del usuario para ver o gestionar su conversación
      </small>
    </div>
    
    <!-- Management Actions -->
    <div class="conversation-actions">
      <button 
        class="btn btn-primary" 
        @click="handleGetConversation"
        :disabled="!canManageConversation || isLoading"
      >
        <span v-if="isLoading">⏳</span>
        <span v-else>📖</span>
        Ver Conversación
      </button>
      
      <button 
        class="btn btn-danger" 
        @click="handleDeleteConversation"
        :disabled="!canManageConversation || isDeleting"
      >
        <span v-if="isDeleting">🔄</span>
        <span v-else>🗑️</span>
        Eliminar
      </button>
      
      <button 
        class="btn btn-secondary" 
        @click="clearDetails"
        :disabled="!hasDetails"
      >
        🧹 Limpiar
      </button>
    </div>
    
    <!-- Quick Actions -->
    <div v-if="showQuickActions" class="quick-actions">
      <button 
        class="btn btn-outline" 
        @click="loadRandomUser"
        :disabled="isLoading"
      >
        🎲 Usuario Aleatorio
      </button>
      
      <button 
        class="btn btn-outline" 
        @click="refreshCurrentConversation"
        :disabled="!userId.trim() || isLoading"
      >
        🔄 Refrescar
      </button>
    </div>
    
    <!-- Conversation Details Container -->
    <div id="conversationDetails" class="conversation-details">
      <!-- Loading State -->
      <div v-if="isLoading" class="loading-state">
        <div class="loading-spinner">⏳</div>
        <p>Cargando conversación...</p>
      </div>
      
      <!-- Conversation Content -->
      <div v-else-if="currentConversation" class="conversation-content">
        <div class="conversation-header">
          <h4>👤 Conversación de {{ escapeHTML(currentConversation.userId) }}</h4>
          <div class="conversation-meta">
            <span class="meta-item">
              <strong>Mensajes:</strong> {{ currentConversation.messageCount || 0 }}
            </span>
            <span class="meta-item">
              <strong>Última actividad:</strong> 
              {{ formatDate(currentConversation.lastMessageAt) }}
            </span>
            <span class="meta-item">
              <strong>Estado:</strong> 
              <span :class="['status', currentConversation.status?.toLowerCase()]">
                {{ currentConversation.status || 'Activo' }}
              </span>
            </span>
          </div>
        </div>
        
        <!-- Conversation History -->
        <div class="conversation-history">
          <div v-if="currentConversation.history && currentConversation.history.length > 0">
            <div 
              v-for="(message, index) in currentConversation.history" 
              :key="index"
              :class="['message', message.role]"
            >
              <div class="message-header">
                <strong class="message-sender">
                  {{ message.role === 'user' ? '👤 Usuario' : '🤖 Bot' }}
                </strong>
                <small class="message-timestamp">
                  {{ formatTimestamp(message.timestamp) }}
                </small>
              </div>
              <div class="message-content">
                {{ message.content }}
              </div>
            </div>
          </div>
          <div v-else class="no-history">
            <p>No hay historial disponible para este usuario</p>
          </div>
        </div>
        
        <!-- Conversation Actions -->
        <div class="conversation-footer">
          <button 
            class="btn btn-small btn-secondary" 
            @click="refreshCurrentConversation"
          >
            🔄 Actualizar
          </button>
          <button 
            class="btn btn-small btn-warning" 
            @click="exportConversation"
            :disabled="!currentConversation.history?.length"
          >
            📥 Exportar
          </button>
        </div>
      </div>
      
      <!-- Error State -->
      <div v-else-if="error" class="error-state">
        <div class="error-icon">❌</div>
        <h4>Error al obtener conversación</h4>
        <p class="error-message">{{ error }}</p>
        <button class="btn btn-primary" @click="handleGetConversation">
          🔄 Reintentar
        </button>
      </div>
      
      <!-- Empty State -->
      <div v-else class="empty-state">
        <div class="empty-icon">💬</div>
        <h4>Gestión de Conversaciones</h4>
        <p>Ingresa un ID de usuario y haz clic en "Ver Conversación" para mostrar los detalles</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'

// ============================================================================
// PROPS & EMITS
// ============================================================================

const props = defineProps({
  showStats: {
    type: Boolean,
    default: true
  },
  showQuickActions: {
    type: Boolean,
    default: true
  },
  autoRefresh: {
    type: Boolean,
    default: false
  },
  refreshInterval: {
    type: Number,
    default: 30000 // 30 segundos
  }
})

const emit = defineEmits([
  'conversation-loaded',
  'conversation-deleted',
  'conversation-error',
  'user-changed'
])

// ============================================================================
// COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const { apiRequest } = useApiRequest()
const { showNotification } = useNotifications()

// ============================================================================
// ESTADO REACTIVO
// ============================================================================

const userId = ref('')
const currentConversation = ref(null)
const isLoading = ref(false)
const isDeleting = ref(false)
const error = ref('')
const totalConversations = ref(0)
const activeConversations = ref(0)

// Auto-refresh timer
let refreshTimer = null

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const canManageConversation = computed(() => {
  return userId.value.trim().length > 0 && appStore.hasCompanySelected
})

const hasDetails = computed(() => {
  return currentConversation.value !== null || error.value !== ''
})

// ============================================================================
// UTILIDADES
// ============================================================================

/**
 * Escapa HTML para prevenir XSS - Mantener función exacta del script.js
 */
const escapeHTML = (str) => {
  if (!str) return ''
  const div = document.createElement('div')
  div.textContent = str
  return div.innerHTML
}

/**
 * Formatea fecha para mostrar
 */
const formatDate = (dateString) => {
  if (!dateString) return 'Sin fecha'
  try {
    return new Date(dateString).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return 'Fecha inválida'
  }
}

/**
 * Formatea timestamp para mensajes
 */
const formatTimestamp = (timestamp) => {
  if (!timestamp) return 'Sin fecha'
  try {
    return new Date(timestamp).toLocaleString('es-ES')
  } catch {
    return 'Sin fecha'
  }
}

/**
 * Valida selección de empresa - Mantener lógica exacta del script.js
 */
const validateCompanySelection = () => {
  if (!appStore.currentCompanyId) {
    showNotification('❌ Selecciona una empresa primero', 'error')
    return false
  }
  return true
}

// ============================================================================
// MÉTODOS PRINCIPALES (MANTENER COMPATIBILIDAD CON SCRIPT.JS)
// ============================================================================

/**
 * Obtiene una conversación específica - MANTENER LÓGICA EXACTA
 */
const getConversation = async (userIdParam = null) => {
  if (!validateCompanySelection()) return false
  
  const targetUserId = userIdParam || userId.value.trim()
  if (!targetUserId) {
    showNotification('Por favor ingresa un ID de usuario', 'warning')
    return false
  }
  
  isLoading.value = true
  error.value = ''
  
  try {
    // MANTENER ENDPOINT EXACTO del script.js
    const response = await apiRequest(`/api/conversations/${targetUserId}`)
    const conversation = response.data || response
    
    // Estructurar datos para el componente Vue
    currentConversation.value = {
      userId: targetUserId,
      history: conversation.history || [],
      messageCount: conversation.history?.length || 0,
      lastMessageAt: conversation.last_message_at || conversation.lastMessageAt,
      status: conversation.status || 'Activo'
    }
    
    // Actualizar el DOM element para compatibilidad con script.js original
    await nextTick()
    const container = document.getElementById('conversationDetails')
    if (container && conversation.history) {
      // Generar HTML exactamente como en script.js para mantener compatibilidad
      const historyHTML = conversation.history.map(msg => `
        <div class="message" style="margin-bottom: 15px; padding: 10px; border-radius: 8px; background: ${msg.role === 'user' ? '#f0fff4' : '#ebf8ff'};">
          <strong>${msg.role === 'user' ? '👤 Usuario' : '🤖 Bot'}:</strong> ${escapeHTML(msg.content)}
          <br><small style="color: #718096;">${msg.timestamp || 'Sin fecha'}</small>
        </div>
      `).join('')
      
      // Actualizar contenido del DOM para compatibilidad
      const compatibilityDiv = document.createElement('div')
      compatibilityDiv.style.display = 'none'
      compatibilityDiv.innerHTML = `
        <div class="result-container result-info">
          <h4>👤 Conversación de ${escapeHTML(targetUserId)}</h4>
          <div class="conversation-history" style="max-height: 300px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px;">
            ${historyHTML || '<p>No hay historial disponible</p>'}
          </div>
        </div>
      `
      container.appendChild(compatibilityDiv)
    }
    
    emit('conversation-loaded', currentConversation.value)
    appStore.addToLog(`Conversación cargada: ${targetUserId}`, 'info')
    
    return true
    
  } catch (err) {
    console.error('Error getting conversation:', err)
    error.value = err.message
    
    // Actualizar DOM para compatibilidad con script.js
    await nextTick()
    const container = document.getElementById('conversationDetails')
    if (container) {
      const errorDiv = document.createElement('div')
      errorDiv.style.display = 'none'
      errorDiv.innerHTML = `
        <div class="result-container result-error">
          <p>❌ Error al obtener conversación</p>
          <p>${escapeHTML(err.message)}</p>
        </div>
      `
      container.appendChild(errorDiv)
    }
    
    emit('conversation-error', err)
    appStore.addToLog(`Error cargando conversación: ${err.message}`, 'error')
    
    return false
  } finally {
    isLoading.value = false
  }
}

/**
 * Elimina una conversación - MANTENER LÓGICA EXACTA
 */
const deleteConversation = async (userIdParam = null) => {
  if (!validateCompanySelection()) return false
  
  const targetUserId = userIdParam || userId.value.trim()
  if (!targetUserId) {
    showNotification('Por favor ingresa un ID de usuario', 'warning')
    return false
  }
  
  // Confirmación exacta como en script.js
  if (!confirm(`¿Estás seguro de que quieres eliminar la conversación de ${targetUserId}?`)) {
    return false
  }
  
  isDeleting.value = true
  
  try {
    // MANTENER ENDPOINT EXACTO del script.js
    await apiRequest(`/api/conversations/${targetUserId}`, {
      method: 'DELETE'
    })
    
    showNotification('Conversación eliminada exitosamente', 'success')
    
    // Limpiar detalles mostrados - IGUAL que script.js
    currentConversation.value = null
    error.value = ''
    
    // Limpiar DOM container para compatibilidad
    const container = document.getElementById('conversationDetails')
    if (container) {
      container.innerHTML = ''
    }
    
    emit('conversation-deleted', targetUserId)
    appStore.addToLog(`Conversación eliminada: ${targetUserId}`, 'info')
    
    return true
    
  } catch (err) {
    console.error('Error deleting conversation:', err)
    showNotification('Error al eliminar conversación: ' + err.message, 'error')
    
    emit('conversation-error', err)
    appStore.addToLog(`Error eliminando conversación: ${err.message}`, 'error')
    
    return false
  } finally {
    isDeleting.value = false
  }
}

// ============================================================================
// MÉTODOS DE INTERFAZ
// ============================================================================

/**
 * Maneja obtener conversación desde la UI
 */
const handleGetConversation = async () => {
  await getConversation()
}

/**
 * Maneja eliminar conversación desde la UI
 */
const handleDeleteConversation = async () => {
  const success = await deleteConversation()
  if (success) {
    userId.value = ''
  }
}

/**
 * Limpia los detalles mostrados
 */
const clearDetails = () => {
  currentConversation.value = null
  error.value = ''
  
  // Limpiar DOM para compatibilidad
  const container = document.getElementById('conversationDetails')
  if (container) {
    container.innerHTML = ''
  }
}

/**
 * Carga un usuario aleatorio para testing
 */
const loadRandomUser = () => {
  const randomUsers = [
    'test-user-1',
    'test-user-2', 
    'demo-user',
    'chatwoot_contact_123',
    'user-' + Math.floor(Math.random() * 1000)
  ]
  
  userId.value = randomUsers[Math.floor(Math.random() * randomUsers.length)]
  showNotification('🎲 Usuario aleatorio cargado', 'info', 2000)
}

/**
 * Refresca la conversación actual
 */
const refreshCurrentConversation = async () => {
  if (userId.value.trim()) {
    await getConversation()
  }
}

/**
 * Exporta la conversación actual
 */
const exportConversation = () => {
  if (!currentConversation.value?.history?.length) {
    showNotification('❌ No hay historial para exportar', 'warning')
    return
  }
  
  try {
    const exportData = {
      userId: currentConversation.value.userId,
      exportedAt: new Date().toISOString(),
      messageCount: currentConversation.value.messageCount,
      lastMessageAt: currentConversation.value.lastMessageAt,
      history: currentConversation.value.history
    }
    
    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json'
    })
    
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `conversacion-${currentConversation.value.userId}-${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    
    showNotification('✅ Conversación exportada', 'success')
    
  } catch (err) {
    console.error('Error exporting conversation:', err)
    showNotification('❌ Error al exportar conversación', 'error')
  }
}

// ============================================================================
// FUNCIONES DE COMPATIBILIDAD CON SCRIPT.JS
// ============================================================================

/**
 * Función para ver detalles desde lista - MANTENER NOMBRE EXACTO
 */
const viewConversationDetail = (userIdParam) => {
  userId.value = userIdParam
  
  // Actualizar DOM input para compatibilidad
  const input = document.getElementById('manageUserId')
  if (input) {
    input.value = userIdParam
  }
  
  getConversation(userIdParam)
}

/**
 * Función para eliminar desde lista - MANTENER NOMBRE EXACTO  
 */
const deleteConversationFromList = async (userIdParam) => {
  userId.value = userIdParam
  
  // Actualizar DOM input para compatibilidad
  const input = document.getElementById('manageUserId')
  if (input) {
    input.value = userIdParam
  }
  
  return await deleteConversation(userIdParam)
}

// ============================================================================
// AUTO-REFRESH
// ============================================================================

const startAutoRefresh = () => {
  if (props.autoRefresh && props.refreshInterval > 0) {
    refreshTimer = setInterval(() => {
      if (userId.value.trim() && currentConversation.value) {
        refreshCurrentConversation()
      }
    }, props.refreshInterval)
  }
}

const stopAutoRefresh = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

// ============================================================================
// LIFECYCLE HOOKS
// ============================================================================

onMounted(async () => {
  appStore.addToLog('ConversationManager mounted', 'info')
  
  // Inicializar auto-refresh si está habilitado
  startAutoRefresh()
  
  // EXPONER FUNCIONES GLOBALES PARA COMPATIBILIDAD CON SCRIPT.JS
  window.getConversation = getConversation
  window.deleteConversation = deleteConversation
  window.viewConversationDetail = viewConversationDetail
  window.deleteConversationFromList = deleteConversationFromList
})

onUnmounted(() => {
  stopAutoRefresh()
  
  // LIMPIAR FUNCIONES GLOBALES
  if (typeof window !== 'undefined') {
    delete window.getConversation
    delete window.deleteConversation  
    delete window.viewConversationDetail
    delete window.deleteConversationFromList
  }
})

// ============================================================================
// WATCHERS
// ============================================================================

// Watch para cambios de empresa
watch(() => appStore.currentCompanyId, (newCompanyId) => {
  if (newCompanyId) {
    // Limpiar estado al cambiar empresa
    clearDetails()
    appStore.addToLog(`ConversationManager: Empresa cambiada a ${newCompanyId}`, 'info')
  }
})

// Watch para cambios de usuario
watch(userId, (newUserId) => {
  emit('user-changed', newUserId)
  
  // Actualizar DOM input para mantener sincronización
  const input = document.getElementById('manageUserId')
  if (input && input.value !== newUserId) {
    input.value = newUserId
  }
})

// Watch para auto-refresh setting
watch(() => props.autoRefresh, (enabled) => {
  if (enabled) {
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
})
</script>

<style scoped>
.conversation-manager {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 20px;
}

.manager-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 10px;
}

.manager-header h3 {
  margin: 0;
  color: var(--text-primary);
}

.conversation-stats {
  display: flex;
  gap: 15px;
  font-size: 0.9em;
  color: var(--text-secondary);
}

.stat-item {
  white-space: nowrap;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: var(--text-primary);
}

.user-input {
  width: 100%;
  padding: 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 14px;
  transition: all 0.2s ease;
}

.user-input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.user-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.input-hint {
  display: block;
  margin-top: 6px;
  font-size: 0.8em;
  color: var(--text-muted);
}

.conversation-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 15px;
}

.quick-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 20px;
  padding-top: 10px;
  border-top: 1px solid var(--border-color);
}

.conversation-details {
  min-height: 120px;
  margin-top: 20px;
}

.loading-state,
.empty-state,
.error-state {
  text-align: center;
  padding: 40px 20px;
  border: 1px dashed var(--border-color);
  border-radius: 8px;
  background: var(--bg-tertiary);
}

.loading-spinner {
  font-size: 2em;
  margin-bottom: 15px;
  animation: spin 1s linear infinite;
}

.empty-icon,
.error-icon {
  font-size: 3em;
  margin-bottom: 15px;
  opacity: 0.6;
}

.error-state {
  border-color: var(--error-color);
  background: var(--error-bg);
}

.error-state .error-icon {
  color: var(--error-color);
}

.error-message {
  color: var(--error-color);
  font-weight: 500;
  margin: 10px 0;
}

.conversation-content {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
}

.conversation-header {
  padding: 20px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
}

.conversation-header h4 {
  margin: 0 0 12px 0;
  color: var(--text-primary);
}

.conversation-meta {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
  font-size: 0.9em;
  color: var(--text-secondary);
}

.meta-item {
  white-space: nowrap;
}

.status {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.8em;
  font-weight: 500;
  text-transform: uppercase;
}

.status.activo {
  background: var(--success-bg);
  color: var(--success-color);
}

.status.inactivo {
  background: var(--warning-bg);
  color: var(--warning-color);
}

.conversation-history {
  max-height: 400px;
  overflow-y: auto;
  padding: 20px;
}

.message {
  margin-bottom: 16px;
  padding: 12px;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.message.user {
  background: #f0fff4;
  border-left: 3px solid var(--success-color);
}

.message.assistant {
  background: #ebf8ff;
  border-left: 3px solid var(--primary-color);
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.message-sender {
  color: var(--text-primary);
  font-size: 0.9em;
}

.message-timestamp {
  color: var(--text-muted);
  font-size: 0.8em;
}

.message-content {
  color: var(--text-primary);
  line-height: 1.5;
  word-wrap: break-word;
}

.no-history {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-muted);
}

.conversation-footer {
  padding: 15px 20px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-secondary);
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.btn {
  padding: 10px 16px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-primary);
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  text-decoration: none;
  white-space: nowrap;
}

.btn:hover:not(:disabled) {
  background: var(--bg-secondary);
  border-color: var(--primary-color);
  transform: translateY(-1px);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-dark);
  border-color: var(--primary-dark);
}

.btn-danger {
  background: var(--error-color);
  color: white;
  border-color: var(--error-color);
}

.btn-danger:hover:not(:disabled) {
  background: var(--error-dark);
  border-color: var(--error-dark);
}

.btn-secondary {
  background: var(--bg-secondary);
  color: var(--text-secondary);
}

.btn-warning {
  background: var(--warning-color);
  color: white;
  border-color: var(--warning-color);
}

.btn-outline {
  background: transparent;
  color: var(--text-secondary);
  border-color: var(--border-color);
}

.btn-outline:hover:not(:disabled) {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.btn-small {
  padding: 6px 12px;
  font-size: 12px;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Responsive design */
@media (max-width: 768px) {
  .conversation-actions,
  .quick-actions {
    flex-direction: column;
  }
  
  .manager-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .conversation-meta {
    flex-direction: column;
    gap: 8px;
  }
  
  .conversation-footer {
    flex-direction: column;
  }
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .message.user {
    background: rgba(34, 197, 94, 0.1);
  }
  
  .message.assistant {
    background: rgba(59, 130, 246, 0.1);
  }
}
</style>
