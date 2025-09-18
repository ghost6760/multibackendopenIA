<template>
  <div class="conversations-list">
    <!-- Loading state -->
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner">⏳</div>
      <p>Cargando conversaciones...</p>
    </div>
    
    <!-- Conversations grid -->
    <div v-else-if="conversations.length > 0" class="conversations-grid">
      <div
        v-for="conversation in sortedConversations"
        :key="conversation.user_id || conversation.id"
        class="conversation-card"
        :class="{ 'conversation-selected': selectedConversationId === (conversation.user_id || conversation.id) }"
        @click="selectConversation(conversation)"
      >
        <!-- Conversation header -->
        <div class="conversation-header">
          <div class="conversation-icon">
            💬
          </div>
          <div class="conversation-info">
            <h4 class="conversation-title" :title="conversation.user_id || conversation.id">
              {{ conversation.user_id || conversation.id }}
            </h4>
            <div class="conversation-meta">
              <span class="conversation-date">
                🕒 {{ formatDate(conversation.last_message_at || conversation.updated_at || conversation.created_at) }}
              </span>
              <span class="conversation-messages">
                💬 {{ getMessageCount(conversation) }} mensajes
              </span>
              <span v-if="conversation.status" class="conversation-status" :class="getStatusClass(conversation.status)">
                📊 {{ conversation.status }}
              </span>
            </div>
          </div>
        </div>
        
        <!-- Last message preview -->
        <div class="conversation-preview">
          <p class="conversation-excerpt">
            {{ getLastMessagePreview(conversation) }}
          </p>
        </div>
        
        <!-- Conversation actions -->
        <div class="conversation-actions">
          <button
            @click.stop="handleViewConversation(conversation)"
            class="action-btn view-btn"
            title="Ver conversación completa"
          >
            👁️ Ver
          </button>
          
          <button
            @click.stop="handleDeleteConversation(conversation)"
            class="action-btn delete-btn"
            title="Eliminar conversación"
          >
            🗑️ Eliminar
          </button>
          
          <!-- Additional actions dropdown -->
          <div class="dropdown" v-if="showAdditionalActions">
            <button
              @click.stop="toggleActionsDropdown(conversation.user_id || conversation.id)"
              class="action-btn dropdown-toggle"
              title="Más acciones"
            >
              ⋮
            </button>
            
            <div
              v-show="activeDropdown === (conversation.user_id || conversation.id)"
              class="dropdown-menu"
              @click.stop
            >
              <button @click="exportConversation(conversation)" class="dropdown-item">
                📥 Exportar
              </button>
              <button @click="testConversation(conversation)" class="dropdown-item">
                🧪 Probar
              </button>
              <button @click="duplicateConversation(conversation)" class="dropdown-item">
                📋 Duplicar
              </button>
              <div class="dropdown-divider"></div>
              <button @click="archiveConversation(conversation)" class="dropdown-item">
                📦 Archivar
              </button>
            </div>
          </div>
        </div>
        
        <!-- Conversation stats -->
        <div class="conversation-stats">
          <div class="stats-row">
            <span v-if="conversation.company_id" class="stat-badge company">
              🏢 {{ conversation.company_id }}
            </span>
            <span v-if="isRecentConversation(conversation)" class="stat-badge recent">
              🔥 Reciente
            </span>
            <span v-if="conversation.priority" class="stat-badge priority">
              ⭐ {{ conversation.priority }}
            </span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Empty state -->
    <div v-else class="empty-state">
      <div class="empty-icon">💬</div>
      <h4>No hay conversaciones disponibles</h4>
      <p>Las conversaciones aparecerán aquí cuando se generen</p>
      <button @click="$emit('refresh')" class="btn-primary">
        🔄 Actualizar
      </button>
    </div>
    
    <!-- Pagination (if needed) -->
    <div v-if="totalPages > 1" class="pagination">
      <button
        @click="goToPage(currentPage - 1)"
        :disabled="currentPage === 1"
        class="pagination-btn"
      >
        ← Anterior
      </button>
      
      <div class="pagination-pages">
        <button
          v-for="page in visiblePages"
          :key="page"
          @click="goToPage(page)"
          :class="['pagination-btn', { 'active': page === currentPage }]"
        >
          {{ page }}
        </button>
      </div>
      
      <button
        @click="goToPage(currentPage + 1)"
        :disabled="currentPage === totalPages"
        class="pagination-btn"
      >
        Siguiente →
      </button>
    </div>
    
    <!-- Filter and sort controls -->
    <div v-if="conversations.length > 0" class="list-controls">
      <div class="sort-controls">
        <label for="sortBy">Ordenar por:</label>
        <select id="sortBy" v-model="sortBy" @change="handleSortChange">
          <option value="recent">🕒 Más recientes</option>
          <option value="oldest">🕒 Más antiguos</option>
          <option value="messages">💬 Más mensajes</option>
          <option value="user">👤 Usuario (A-Z)</option>
        </select>
      </div>
      
      <div class="filter-controls">
        <label for="filterStatus">Filtrar por estado:</label>
        <select id="filterStatus" v-model="filterStatus" @change="handleFilterChange">
          <option value="">Todos</option>
          <option value="active">Activos</option>
          <option value="completed">Completados</option>
          <option value="archived">Archivados</option>
        </select>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { useNotifications } from '@/composables/useNotifications'

// ============================================================================
// PROPS & EMITS
// ============================================================================

const props = defineProps({
  conversations: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  showAdditionalActions: {
    type: Boolean,
    default: true
  },
  itemsPerPage: {
    type: Number,
    default: 12
  }
})

const emit = defineEmits([
  'view-conversation',
  'delete-conversation', 
  'refresh',
  'export-conversation',
  'test-conversation',
  'archive-conversation'
])

// ============================================================================
// STORES & COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const { showNotification } = useNotifications()

// ============================================================================
// ESTADO LOCAL
// ============================================================================

const selectedConversationId = ref(null)
const activeDropdown = ref(null)
const currentPage = ref(1)
const sortBy = ref('recent')
const filterStatus = ref('')

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const filteredConversations = computed(() => {
  let filtered = props.conversations
  
  // Apply status filter
  if (filterStatus.value) {
    filtered = filtered.filter(conv => conv.status === filterStatus.value)
  }
  
  return filtered
})

const sortedConversations = computed(() => {
  const conversations = [...filteredConversations.value]
  
  switch (sortBy.value) {
    case 'oldest':
      return conversations.sort((a, b) => 
        new Date(a.last_message_at || a.created_at) - new Date(b.last_message_at || b.created_at)
      )
      
    case 'messages':
      return conversations.sort((a, b) => 
        getMessageCount(b) - getMessageCount(a)
      )
      
    case 'user':
      return conversations.sort((a, b) => 
        (a.user_id || a.id).localeCompare(b.user_id || b.id)
      )
      
    case 'recent':
    default:
      return conversations.sort((a, b) => 
        new Date(b.last_message_at || b.created_at) - new Date(a.last_message_at || a.created_at)
      )
  }
})

const totalPages = computed(() => {
  return Math.ceil(sortedConversations.value.length / props.itemsPerPage)
})

const visiblePages = computed(() => {
  const total = totalPages.value
  const current = currentPage.value
  const pages = []
  
  // Show up to 5 pages around current page
  const start = Math.max(1, current - 2)
  const end = Math.min(total, current + 2)
  
  for (let i = start; i <= end; i++) {
    pages.push(i)
  }
  
  return pages
})

const paginatedConversations = computed(() => {
  const start = (currentPage.value - 1) * props.itemsPerPage
  const end = start + props.itemsPerPage
  return sortedConversations.value.slice(start, end)
})

// ============================================================================
// MÉTODOS PRINCIPALES
// ============================================================================

/**
 * Handle view conversation
 */
const handleViewConversation = (conversation) => {
  selectedConversationId.value = conversation.user_id || conversation.id
  emit('view-conversation', conversation.user_id || conversation.id)
  appStore.addToLog(`Viewing conversation: ${conversation.user_id || conversation.id}`, 'info')
}

/**
 * Handle delete conversation
 */
const handleDeleteConversation = (conversation) => {
  const userId = conversation.user_id || conversation.id
  const confirmed = confirm(`¿Estás seguro de que quieres eliminar la conversación de "${userId}"?`)
  
  if (confirmed) {
    emit('delete-conversation', userId)
    appStore.addToLog(`Deleting conversation: ${userId}`, 'info')
  }
}

/**
 * Select conversation
 */
const selectConversation = (conversation) => {
  selectedConversationId.value = conversation.user_id || conversation.id
}

/**
 * Toggle actions dropdown
 */
const toggleActionsDropdown = (conversationId) => {
  activeDropdown.value = activeDropdown.value === conversationId ? null : conversationId
}

/**
 * Close all dropdowns when clicking outside
 */
const closeDropdowns = () => {
  activeDropdown.value = null
}

// ============================================================================
// MÉTODOS DE ACCIONES ADICIONALES
// ============================================================================

const exportConversation = (conversation) => {
  try {
    const data = {
      user_id: conversation.user_id || conversation.id,
      company_id: conversation.company_id || appStore.currentCompanyId,
      exported_at: new Date().toISOString(),
      conversation_data: conversation
    }
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    
    const link = document.createElement('a')
    link.href = url
    link.download = `conversation_${data.user_id}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    URL.revokeObjectURL(url)
    
    showNotification(`📥 Conversación exportada: ${data.user_id}`, 'success')
    emit('export-conversation', conversation)
    
  } catch (error) {
    console.error('Error exporting conversation:', error)
    showNotification('❌ Error al exportar conversación', 'error')
  }
  
  closeDropdowns()
}

const testConversation = (conversation) => {
  emit('test-conversation', conversation)
  showNotification(`🧪 Probando conversación: ${conversation.user_id || conversation.id}`, 'info')
  closeDropdowns()
}

const duplicateConversation = (conversation) => {
  showNotification('📋 Función de duplicar en desarrollo', 'warning')
  closeDropdowns()
}

const archiveConversation = (conversation) => {
  const confirmed = confirm(`¿Archivar conversación de "${conversation.user_id || conversation.id}"?`)
  
  if (confirmed) {
    emit('archive-conversation', conversation)
    showNotification(`📦 Conversación archivada: ${conversation.user_id || conversation.id}`, 'success')
  }
  
  closeDropdowns()
}

// ============================================================================
// MÉTODOS DE UTILIDAD
// ============================================================================

/**
 * Get message count for conversation
 */
const getMessageCount = (conversation) => {
  if (conversation.message_count !== undefined) {
    return conversation.message_count
  }
  
  if (conversation.messages && Array.isArray(conversation.messages)) {
    return conversation.messages.length
  }
  
  if (conversation.history && Array.isArray(conversation.history)) {
    return conversation.history.length
  }
  
  return 0
}

/**
 * Get last message preview
 */
const getLastMessagePreview = (conversation) => {
  // Try to get last message from different possible structures
  let lastMessage = null
  
  if (conversation.last_message) {
    lastMessage = conversation.last_message
  } else if (conversation.messages && conversation.messages.length > 0) {
    lastMessage = conversation.messages[conversation.messages.length - 1]
  } else if (conversation.history && conversation.history.length > 0) {
    lastMessage = conversation.history[conversation.history.length - 1]
  }
  
  if (!lastMessage) return 'Sin mensajes'
  
  const content = lastMessage.content || lastMessage.text || lastMessage.message || 'Sin contenido'
  const maxLength = 100
  
  return content.length > maxLength 
    ? content.substring(0, maxLength) + '...'
    : content
}

/**
 * Get status class
 */
const getStatusClass = (status) => {
  const statusMap = {
    'active': 'status-active',
    'completed': 'status-completed',
    'archived': 'status-archived',
    'error': 'status-error'
  }
  return statusMap[status] || 'status-default'
}

/**
 * Check if conversation is recent (less than 24 hours)
 */
const isRecentConversation = (conversation) => {
  const lastActivity = conversation.last_message_at || conversation.updated_at || conversation.created_at
  if (!lastActivity) return false
  
  const now = new Date()
  const activityDate = new Date(lastActivity)
  const diffHours = (now - activityDate) / (1000 * 60 * 60)
  
  return diffHours < 24
}

/**
 * Format date
 */
const formatDate = (dateString) => {
  if (!dateString) return 'Fecha desconocida'
  
  try {
    const date = new Date(dateString)
    const now = new Date()
    const diffTime = Math.abs(now - date)
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
    
    if (diffDays === 1) return 'Ayer'
    if (diffDays < 7) return `Hace ${diffDays} días`
    if (diffDays < 30) return `Hace ${Math.floor(diffDays / 7)} semanas`
    
    return date.toLocaleDateString('es-ES')
  } catch {
    return 'Fecha inválida'
  }
}

// ============================================================================
// PAGINATION & CONTROLS
// ============================================================================

const goToPage = (page) => {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
    closeDropdowns()
  }
}

const handleSortChange = () => {
  appStore.addToLog(`Conversations sorted by: ${sortBy.value}`, 'info')
}

const handleFilterChange = () => {
  currentPage.value = 1 // Reset to first page when filtering
  appStore.addToLog(`Conversations filtered by status: ${filterStatus.value || 'all'}`, 'info')
}

// ============================================================================
// LIFECYCLE HOOKS
// ============================================================================

onMounted(() => {
  // Close dropdowns when clicking outside
  document.addEventListener('click', closeDropdowns)
  
  // Keyboard shortcuts
  document.addEventListener('keydown', handleKeyboard)
})

onUnmounted(() => {
  document.removeEventListener('click', closeDropdowns)
  document.removeEventListener('keydown', handleKeyboard)
})

/**
 * Handle keyboard shortcuts
 */
const handleKeyboard = (event) => {
  // ESC closes dropdowns
  if (event.key === 'Escape') {
    closeDropdowns()
  }
  
  // Arrow keys for navigation (when no input is focused)
  if (!event.target.matches('input, textarea, select')) {
    if (event.key === 'ArrowLeft' && currentPage.value > 1) {
      goToPage(currentPage.value - 1)
    } else if (event.key === 'ArrowRight' && currentPage.value < totalPages.value) {
      goToPage(currentPage.value + 1)
    }
  }
}
</script>

<style scoped>
.conversations-list {
  width: 100%;
}

.loading-state {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-secondary);
}

.loading-spinner {
  font-size: 2em;
  margin-bottom: 10px;
  animation: spin 1s linear infinite;
}

.conversations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

.conversation-card {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  transition: all 0.3s ease;
  cursor: pointer;
  position: relative;
}

.conversation-card:hover {
  border-color: var(--primary-color);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.conversation-card.conversation-selected {
  border-color: var(--primary-color);
  background: rgba(102, 126, 234, 0.05);
}

.conversation-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}

.conversation-icon {
  font-size: 1.5em;
  min-width: 32px;
  text-align: center;
}

.conversation-info {
  flex: 1;
  min-width: 0;
}

.conversation-title {
  margin: 0 0 6px 0;
  font-size: 1.1em;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.3;
  
  /* Text overflow handling */
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conversation-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 0.8em;
  color: var(--text-muted);
}

.conversation-meta span {
  display: inline-block;
}

.conversation-preview {
  margin-bottom: 12px;
}

.conversation-excerpt {
  margin: 0;
  font-size: 0.9em;
  color: var(--text-secondary);
  line-height: 1.4;
  
  /* Multi-line text overflow */
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.conversation-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.action-btn {
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--bg-secondary);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 0.85em;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.action-btn:hover {
  background: var(--bg-primary);
  color: var(--text-primary);
}

.view-btn:hover {
  border-color: var(--info-color);
  color: var(--info-color);
}

.delete-btn:hover {
  border-color: var(--danger-color);
  color: var(--danger-color);
}

.dropdown {
  position: relative;
  display: inline-block;
}

.dropdown-toggle {
  padding: 6px 8px;
  font-weight: bold;
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  right: 0;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  min-width: 150px;
  padding: 4px 0;
}

.dropdown-item {
  width: 100%;
  padding: 8px 12px;
  border: none;
  background: none;
  color: var(--text-primary);
  cursor: pointer;
  font-size: 0.9em;
  text-align: left;
  transition: background-color 0.2s ease;
}

.dropdown-item:hover {
  background: var(--bg-tertiary);
}

.dropdown-divider {
  height: 1px;
  background: var(--border-color);
  margin: 4px 0;
}

.conversation-stats {
  margin-top: 8px;
}

.stats-row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.stat-badge {
  padding: 2px 6px;
  border-radius: 12px;
  font-size: 0.75em;
  font-weight: 500;
  white-space: nowrap;
}

.stat-badge.company {
  background: rgba(102, 126, 234, 0.1);
  color: var(--primary-color);
}

.stat-badge.recent {
  background: rgba(239, 68, 68, 0.1);
  color: var(--danger-color);
}

.stat-badge.priority {
  background: rgba(245, 158, 11, 0.1);
  color: var(--warning-color);
}

.status-active {
  color: var(--success-color);
}

.status-completed {
  color: var(--info-color);
}

.status-archived {
  color: var(--text-muted);
}

.status-error {
  color: var(--danger-color);
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-secondary);
}

.empty-icon {
  font-size: 4em;
  margin-bottom: 20px;
  opacity: 0.5;
}

.empty-state h4 {
  margin: 0 0 10px 0;
  color: var(--text-primary);
}

.empty-state p {
  margin: 0 0 20px 0;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s ease;
}

.btn-primary:hover {
  background: var(--primary-color-dark);
}

/* Pagination */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  margin-top: 20px;
  padding: 20px 0;
}

.pagination-btn {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  background: var(--bg-secondary);
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s ease;
  font-size: 0.9em;
}

.pagination-btn:hover:not(:disabled) {
  background: var(--bg-primary);
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.pagination-btn.active {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: white;
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-pages {
  display: flex;
  gap: 4px;
}

/* List controls */
.list-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 15px;
  margin-top: 20px;
  padding: 15px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  flex-wrap: wrap;
}

.sort-controls,
.filter-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9em;
}

.sort-controls label,
.filter-controls label {
  color: var(--text-secondary);
  font-weight: 500;
}

.sort-controls select,
.filter-controls select {
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 0.9em;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Responsive */
@media (max-width: 768px) {
  .conversations-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
  
  .conversation-header {
    flex-direction: column;
    gap: 8px;
  }
  
  .conversation-info {
    text-align: center;
  }
  
  .conversation-actions {
    justify-content: center;
  }
  
  .action-btn {
    flex: 1;
    text-align: center;
  }
  
  .pagination {
    flex-wrap: wrap;
    gap: 4px;
  }
  
  .pagination-pages {
    order: -1;
    width: 100%;
    justify-content: center;
  }
  
  .list-controls {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }
}

@media (max-width: 480px) {
  .conversation-card {
    padding: 12px;
  }
  
  .conversation-actions {
    flex-direction: column;
  }
  
  .action-btn {
    text-align: center;
  }
}
</style>
