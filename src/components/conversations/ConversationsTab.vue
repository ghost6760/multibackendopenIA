<template>
  <div class="tab-content" :class="{ 'active': isActive }" id="conversations">
    <!-- Company validation -->
    <div v-if="!appStore.hasCompanySelected" class="warning-message">
      <h3>⚠️ Empresa no seleccionada</h3>
      <p>Selecciona una empresa para ver sus conversaciones.</p>
      <button @click="highlightCompanySelector" class="btn-primary">
        🏢 Seleccionar Empresa
      </button>
    </div>
    
    <!-- Main content when company is selected -->
    <template v-else>
      <!-- Conversation Testing Section -->
      <div class="grid grid-2">
        <!-- Test Conversation Card -->
        <div class="card">
          <h3>🧪 Probar Conversación</h3>
          
          <div class="form-group">
            <label for="testUserId">ID de Usuario (opcional)</label>
            <input 
              type="text" 
              id="testUserId" 
              v-model="testUserId"
              placeholder="user123 (dejar vacío para test-user)"
              :disabled="isTesting"
            >
          </div>
          
          <div class="form-group">
            <label for="testMessage">Mensaje de Prueba</label>
            <textarea 
              id="testMessage"
              v-model="testMessage"
              placeholder="Escribe un mensaje para probar el sistema de conversación..."
              rows="4"
              :disabled="isTesting"
              @keyup.ctrl.enter="handleTestConversation"
            ></textarea>
            <small class="input-hint">💡 Presiona Ctrl+Enter para enviar rápidamente</small>
          </div>
          
          <button 
            class="btn btn-primary" 
            @click="handleTestConversation"
            :disabled="!canTestConversation || !testMessage.trim()"
            :class="{ 'testing': isTesting }"
          >
            <span v-if="isTesting">⏳ Probando...</span>
            <span v-else>🧪 Probar Conversación</span>
          </button>
          
          <!-- Test Results -->
          <div id="conversationResult" class="test-results">
            <ConversationTestResult
              v-if="testResults"
              :results="testResults"
              :loading="isTesting"
            />
            <div v-else-if="!isTesting" class="test-placeholder">
              <p>Los resultados de la prueba aparecerán aquí</p>
            </div>
          </div>
        </div>

        <!-- Conversation Management Card -->
        <div class="card">
          <h3>👤 Gestión de Conversaciones</h3>
          
          <div class="form-group">
            <label for="manageUserId">ID de Usuario</label>
            <input 
              type="text" 
              id="manageUserId"
              v-model="manageUserId"
              placeholder="user123"
              :disabled="isLoadingDetail"
            >
          </div>
          
          <div class="conversation-actions">
            <button 
              class="btn btn-primary" 
              @click="handleGetConversation"
              :disabled="!manageUserId.trim() || isLoadingDetail"
            >
              <span v-if="isLoadingDetail">⏳</span>
              <span v-else>📖</span>
              Ver Conversación
            </button>
            <button 
              class="btn btn-danger" 
              @click="handleDeleteConversation"
              :disabled="!manageUserId.trim()"
            >
              🗑️ Eliminar
            </button>
          </div>
          
          <!-- Conversation Details -->
          <div id="conversationDetails" class="conversation-details">
            <ConversationDetail
              v-if="currentConversation"
              :conversation="currentConversation"
              :loading="isLoadingDetail"
              @refresh="handleGetConversation"
            />
            <div v-else-if="!isLoadingDetail" class="details-placeholder">
              <p>Los detalles de la conversación aparecerán aquí</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Conversations List Section -->
      <div class="card">
        <div class="card-header">
          <h3>📋 Lista de Conversaciones</h3>
          <div class="card-actions">
            <button 
              @click="loadConversations" 
              :disabled="isLoading"
              class="btn btn-secondary"
            >
              <span v-if="isLoading">⏳</span>
              <span v-else>🔄</span>
              Actualizar Lista
            </button>
            
            <!-- Conversation stats -->
            <div class="conversation-stats">
              <span class="stat-item">
                💬 {{ conversationsCount }} conversaciones
              </span>
              <span v-if="recentConversations.length > 0" class="stat-item">
                🕒 {{ recentConversations.length }} recientes
              </span>
              <span v-if="appStore.currentCompanyId" class="stat-item">
                🏢 {{ appStore.currentCompanyId }}
              </span>
            </div>
          </div>
        </div>
        
        <!-- Conversations list -->
        <div class="data-list" id="conversationsList">
          <ConversationsList
            v-if="hasConversations"
            :conversations="conversations"
            :loading="isLoading"
            @view-conversation="handleViewConversation"
            @delete-conversation="handleDeleteFromList"
            @refresh="loadConversations"
          />
          
          <div v-else-if="isLoading" class="loading-placeholder">
            <div class="loading-spinner">⏳</div>
            <p>Cargando conversaciones...</p>
          </div>
          
          <div v-else class="empty-state">
            <div class="empty-icon">💬</div>
            <h4>No hay conversaciones</h4>
            <p>
              {{ appStore.currentCompanyId 
                ? `No hay conversaciones para la empresa "${appStore.currentCompanyId}"`
                : 'Selecciona una empresa y haz clic en "Actualizar Lista" para ver las conversaciones'
              }}
            </p>
            <button 
              v-if="appStore.currentCompanyId" 
              @click="focusTestMessage"
              class="btn-primary"
            >
              🧪 Crear primera conversación
            </button>
          </div>
        </div>
      </div>

      <!-- Quick Actions Section -->
      <div class="card quick-actions-card">
        <h3>⚡ Acciones Rápidas</h3>
        <div class="quick-actions-grid">
          <div class="quick-action" @click="showRecentConversations">
            <div class="action-icon">🕒</div>
            <div class="action-content">
              <h4>Conversaciones Recientes</h4>
              <p>{{ recentConversations.length }} conversaciones con actividad reciente</p>
            </div>
          </div>
          
          <div class="quick-action" @click="testRandomMessage">
            <div class="action-icon">🎲</div>
            <div class="action-content">
              <h4>Mensaje Aleatorio</h4>
              <p>Probar con un mensaje de ejemplo</p>
            </div>
          </div>
          
          <div class="quick-action" @click="showConversationStats">
            <div class="action-icon">📊</div>
            <div class="action-content">
              <h4>Estadísticas</h4>
              <p>Ver estadísticas de conversaciones</p>
            </div>
          </div>
          
          <div class="quick-action" @click="exportConversations" v-if="showAdminActions">
            <div class="action-icon">📥</div>
            <div class="action-content">
              <h4>Exportar</h4>
              <p>Descargar todas las conversaciones</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Admin Functions (if API key is configured) -->
      <div v-if="showAdminActions" class="card admin-functions">
        <div class="api-key-functions">
          <h4>🔧 Funciones Administrativas</h4>
          <div class="admin-actions">
            <button 
              @click="bulkDeleteConversations" 
              class="btn btn-outline btn-danger"
              :disabled="!hasConversations"
            >
              🗑️ Eliminar Todas
            </button>
            <button 
              @click="analyzeConversations" 
              class="btn btn-outline"
              :disabled="!hasConversations"
            >
              📈 Analizar Conversaciones
            </button>
            <button 
              @click="testAllUsers" 
              class="btn btn-outline"
              :disabled="!hasConversations"
            >
              🧪 Probar Todos los Usuarios
            </button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useAppStore } from '@/stores/app'
import { useConversations } from '@/composables/useConversations'
import { useNotifications } from '@/composables/useNotifications'

// Sub-components
import ConversationTestResult from './ConversationTestResult.vue'
import ConversationDetail from './ConversationDetail.vue'
import ConversationsList from './ConversationsList.vue'

// ============================================================================
// PROPS
// ============================================================================

const props = defineProps({
  isActive: {
    type: Boolean,
    default: false
  }
})

// ============================================================================
// STORES Y COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const {
  conversations,
  currentConversation,
  isLoading,
  isTesting,
  isLoadingDetail,
  testResults,
  hasConversations,
  conversationsCount,
  canTestConversation,
  recentConversations,
  testConversation,
  getConversation,
  deleteConversation,
  loadConversations,
  viewConversationDetail,
  deleteConversationFromList
} = useConversations()

const { showNotification } = useNotifications()

// ============================================================================
// ESTADO LOCAL
// ============================================================================

const testUserId = ref('')
const testMessage = ref('')
const manageUserId = ref('')

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const showAdminActions = computed(() => {
  return appStore.adminApiKey || import.meta.env.DEV
})

// ============================================================================
// MÉTODOS DE TESTING
// ============================================================================

/**
 * Maneja el test de conversación
 */
const handleTestConversation = async () => {
  if (!testMessage.value.trim()) {
    showNotification('❌ Ingresa un mensaje para probar', 'error')
    return
  }
  
  // Actualizar los inputs del DOM para mantener compatibilidad
  const messageInput = document.getElementById('testMessage')
  const userIdInput = document.getElementById('testUserId')
  
  if (messageInput) messageInput.value = testMessage.value
  if (userIdInput) userIdInput.value = testUserId.value
  
  const success = await testConversation()
  
  if (success) {
    // Limpiar solo el mensaje, mantener el userId para próximas pruebas
    testMessage.value = ''
  }
}

/**
 * Probar con un mensaje aleatorio
 */
const testRandomMessage = () => {
  const randomMessages = [
    "¡Hola! ¿Cómo estás?",
    "¿Qué servicios ofrecen?",
    "Necesito información sobre tratamientos",
    "¿Cuáles son sus horarios de atención?",
    "Quiero agendar una cita",
    "¿Tienen disponibilidad para mañana?",
    "Necesito más información sobre precios",
    "¿Cómo puedo contactarlos?"
  ]
  
  testMessage.value = randomMessages[Math.floor(Math.random() * randomMessages.length)]
  testUserId.value = `test-user-${Math.floor(Math.random() * 1000)}`
  
  showNotification('🎲 Mensaje aleatorio generado', 'info', 2000)
}

// ============================================================================
// MÉTODOS DE GESTIÓN
// ============================================================================

/**
 * Maneja obtener conversación
 */
const handleGetConversation = async () => {
  if (!manageUserId.value.trim()) {
    showNotification('❌ Ingresa un ID de usuario', 'error')
    return
  }
  
  // Actualizar el input del DOM para mantener compatibilidad
  const userIdInput = document.getElementById('manageUserId')
  if (userIdInput) userIdInput.value = manageUserId.value
  
  await getConversation(manageUserId.value)
}

/**
 * Maneja eliminar conversación
 */
const handleDeleteConversation = async () => {
  if (!manageUserId.value.trim()) {
    showNotification('❌ Ingresa un ID de usuario', 'error')
    return
  }
  
  // Actualizar el input del DOM para mantener compatibilidad
  const userIdInput = document.getElementById('manageUserId')
  if (userIdInput) userIdInput.value = manageUserId.value
  
  const success = await deleteConversation(manageUserId.value)
  
  if (success) {
    manageUserId.value = ''
    // Recargar lista
    await loadConversations()
  }
}

/**
 * Maneja ver detalles desde la lista
 */
const handleViewConversation = async (conversationId) => {
  manageUserId.value = conversationId
  await handleGetConversation()
}

/**
 * Maneja eliminar desde la lista
 */
const handleDeleteFromList = async (conversationId) => {
  const success = await deleteConversationFromList(conversationId)
  
  if (success) {
    // Recargar lista
    await loadConversations()
  }
}

// ============================================================================
// MÉTODOS DE ACCIONES RÁPIDAS
// ============================================================================

/**
 * Mostrar conversaciones recientes
 */
const showRecentConversations = () => {
  if (recentConversations.value.length === 0) {
    showNotification('No hay conversaciones recientes', 'info')
    return
  }
  
  const recentList = recentConversations.value
    .map(conv => `• ${conv.user_id} (${conv.messages_count || 0} mensajes)`)
    .join('\n')
  
  showNotification(`Conversaciones recientes:\n${recentList}`, 'info', 8000)
}

/**
 * Mostrar estadísticas de conversaciones
 */
const showConversationStats = () => {
  if (!hasConversations.value) {
    showNotification('No hay conversaciones para analizar', 'info')
    return
  }
  
  const totalMessages = conversations.value.reduce((sum, conv) => 
    sum + (conv.messages_count || 0), 0
  )
  
  const avgMessages = Math.round(totalMessages / conversations.value.length)
  
  const stats = [
    `📊 Total: ${conversationsCount.value} conversaciones`,
    `📝 Mensajes: ${totalMessages} total (${avgMessages} promedio)`,
    `🕒 Recientes: ${recentConversations.value.length} con actividad`,
    `🏢 Empresa: ${appStore.currentCompanyId}`
  ].join('\n')
  
  showNotification(`Estadísticas:\n${stats}`, 'info', 6000)
}

/**
 * Focus en el campo de mensaje de prueba
 */
const focusTestMessage = () => {
  nextTick(() => {
    const messageInput = document.getElementById('testMessage')
    if (messageInput) {
      messageInput.focus()
    }
  })
}

/**
 * Highlight company selector
 */
const highlightCompanySelector = () => {
  window.dispatchEvent(new CustomEvent('highlightCompanySelector'))
}

// ============================================================================
// MÉTODOS ADMINISTRATIVOS
// ============================================================================

const exportConversations = async () => {
  if (!hasConversations.value) {
    showNotification('❌ No hay conversaciones para exportar', 'error')
    return
  }
  
  try {
    const data = {
      timestamp: new Date().toISOString(),
      company: appStore.currentCompanyId,
      total_conversations: conversations.value.length,
      conversations: conversations.value
    }
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    
    const link = document.createElement('a')
    link.href = url
    link.download = `conversations_${appStore.currentCompanyId}_${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    URL.revokeObjectURL(url)
    
    showNotification('✅ Conversaciones exportadas correctamente', 'success')
    appStore.addToLog('Conversations exported successfully', 'info')
    
  } catch (error) {
    showNotification('❌ Error al exportar conversaciones', 'error')
    appStore.addToLog(`Export error: ${error.message}`, 'error')
  }
}

const bulkDeleteConversations = async () => {
  if (!hasConversations.value) {
    showNotification('❌ No hay conversaciones para eliminar', 'error')
    return
  }
  
  const confirmed = confirm(`¿Estás seguro de que quieres eliminar TODAS las ${conversations.value.length} conversaciones? Esta acción no se puede deshacer.`)
  
  if (!confirmed) return
  
  try {
    let deleted = 0
    let errors = 0
    
    for (const conversation of conversations.value) {
      try {
        await deleteConversation(conversation.user_id || conversation.id)
        deleted++
      } catch (error) {
        errors++
        console.error('Error deleting conversation:', error)
      }
    }
    
    showNotification(
      `✅ Eliminación completada: ${deleted} eliminadas, ${errors} errores`,
      errors > 0 ? 'warning' : 'success'
    )
    
    // Recargar lista
    await loadConversations()
    
  } catch (error) {
    showNotification('❌ Error en eliminación masiva', 'error')
  }
}

const analyzeConversations = () => {
  showNotification('⚠️ Función de análisis en desarrollo', 'warning')
}

const testAllUsers = () => {
  showNotification('⚠️ Función de test masivo en desarrollo', 'warning')
}

// ============================================================================
// LIFECYCLE HOOKS
// ============================================================================

onMounted(async () => {
  appStore.addToLog('ConversationsTab mounted', 'info')
  
  // Cargar conversaciones si hay empresa seleccionada
  if (appStore.hasCompanySelected) {
    await loadConversations()
  }
  
  // Event listener para carga de contenido del tab
  window.addEventListener('loadTabContent', handleLoadTabContent)
})

onUnmounted(() => {
  window.removeEventListener('loadTabContent', handleLoadTabContent)
})

// Handle load tab content event
const handleLoadTabContent = (event) => {
  if (event.detail.tabName === 'conversations' && props.isActive) {
    loadConversations()
  }
}

// Watch for company changes
watch(() => appStore.currentCompanyId, (newCompanyId) => {
  if (newCompanyId && props.isActive) {
    loadConversations()
  }
})

// ============================================================================
// EXPONER FUNCIONES GLOBALES PARA COMPATIBILIDAD
// ============================================================================

onMounted(() => {
  // Exponer funciones específicas de conversaciones
  window.testConversation = testConversation
  window.getConversation = getConversation
  window.deleteConversation = deleteConversation
  window.loadConversations = loadConversations
  window.viewConversationDetail = viewConversationDetail
  window.deleteConversationFromList = deleteConversationFromList
})

onUnmounted(() => {
  // Limpiar funciones globales
  if (typeof window !== 'undefined') {
    delete window.testConversation
    delete window.getConversation
    delete window.deleteConversation
    delete window.loadConversations
    delete window.viewConversationDetail
    delete window.deleteConversationFromList
  }
})
</script>

<style scoped>
.tab-content {
  display: none;
}

.tab-content.active {
  display: block;
}

.warning-message {
  text-align: center;
  padding: 40px 20px;
  background: var(--warning-bg);
  border: 1px solid var(--warning-color);
  border-radius: 8px;
  margin-bottom: 20px;
}

.warning-message h3 {
  color: var(--warning-color);
  margin: 0 0 10px 0;
}

.grid {
  display: grid;
  gap: 20px;
  margin-bottom: 30px;
}

.grid-2 {
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
}

.card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 20px;
}

.card h3 {
  margin: 0 0 15px 0;
  color: var(--text-primary);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  flex-wrap: wrap;
  gap: 10px;
}

.card-actions {
  display: flex;
  align-items: center;
  gap: 15px;
  flex-wrap: wrap;
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
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
  color: var(--text-primary);
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 14px;
  transition: border-color 0.2s ease;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.form-group input:disabled,
.form-group textarea:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.input-hint {
  display: block;
  margin-top: 4px;
  font-size: 0.8em;
  color: var(--text-muted);
}

.conversation-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 15px;
}

.test-results,
.conversation-details {
  margin-top: 15px;
  min-height: 100px;
}

.test-placeholder,
.details-placeholder {
  text-align: center;
  padding: 20px;
  color: var(--text-muted);
  border: 1px dashed var(--border-color);
  border-radius: 6px;
}

.data-list {
  max-height: 500px;
  overflow-y: auto;
}

.loading-placeholder {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-secondary);
}

.loading-spinner {
  font-size: 2em;
  margin-bottom: 10px;
  animation: spin 1s linear infinite;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-secondary);
}

.empty-icon {
  font-size: 3em;
  margin-bottom: 15px;
  opacity: 0.5;
}

.empty-state h4 {
  margin: 0 0 10px 0;
  color: var(--text-primary);
}

.empty-state p {
  margin: 0 0 20px 0;
  line-height: 1.5;
}

.quick-actions-card {
  background: var(--bg-tertiary);
}

.quick-actions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.quick-action {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 15px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.quick-action:hover {
  border-color: var(--primary-color);
  background: var(--bg-primary);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.action-icon {
  font-size: 1.5em;
  min-width: 32px;
  text-align: center;
}

.action-content h4 {
  margin: 0 0 4px 0;
  font-size: 1em;
  color: var(--text-primary);
}

.action-content p {
  margin: 0;
  font-size: 0.85em;
  color: var(--text-secondary);
}

.admin-functions {
  background: var(--bg-tertiary);
  border-color: var(--warning-color);
}

.api-key-functions h4 {
  color: var(--warning-color);
  margin-bottom: 15px;
}

.admin-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.btn {
  padding: 10px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  text-decoration: none;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-color-dark);
}

.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.btn-danger {
  background: var(--danger-color);
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: var(--danger-color-dark);
}

.btn-outline {
  background: transparent;
  color: var(--primary-color);
  border: 1px solid var(--primary-color);
}

.btn-outline:hover:not(:disabled) {
  background: var(--primary-color);
  color: white;
}

.btn-outline.btn-danger {
  color: var(--danger-color);
  border-color: var(--danger-color);
}

.btn-outline.btn-danger:hover:not(:disabled) {
  background: var(--danger-color);
  color: white;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn.testing {
  background: var(--warning-color);
  cursor: not-allowed;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Responsive */
@media (max-width: 768px) {
  .grid-2 {
    grid-template-columns: 1fr;
  }
  
  .card-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .card-actions {
    justify-content: center;
  }
  
  .conversation-stats {
    justify-content: center;
  }
  
  .conversation-actions,
  .admin-actions {
    flex-direction: column;
  }
  
  .quick-actions-grid {
    grid-template-columns: 1fr;
  }
  
  .quick-action {
    flex-direction: column;
    text-align: center;
    gap: 8px;
  }
}

@media (max-width: 480px) {
  .quick-action {
    padding: 12px;
  }
  
  .action-icon {
    font-size: 1.2em;
  }
}
</style>
