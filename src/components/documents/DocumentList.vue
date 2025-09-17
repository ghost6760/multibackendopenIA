<template>
  <div class="document-list">
    <!-- Loading state -->
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner">⏳</div>
      <p>Cargando documentos...</p>
    </div>
    
    <!-- Documents grid -->
    <div v-else-if="documents.length > 0" class="documents-grid">
      <div
        v-for="document in documents"
        :key="document.id || document._id"
        class="document-card"
        :class="{ 'document-selected': selectedDocumentId === document.id }"
      >
        <!-- Document header -->
        <div class="document-header">
          <div class="document-icon">
            {{ getDocumentIcon(document.type) }}
          </div>
          <div class="document-info">
            <h4 class="document-title" :title="document.title">
              {{ document.title }}
            </h4>
            <div class="document-meta">
              <span class="document-date">
                📅 {{ formatDate(document.created_at) }}
              </span>
              <span v-if="document.type" class="document-type">
                📄 {{ document.type }}
              </span>
              <span v-if="document.size" class="document-size">
                💾 {{ formatFileSize(document.size) }}
              </span>
            </div>
          </div>
        </div>
        
        <!-- Document preview -->
        <div class="document-preview">
          <p class="document-excerpt">
            {{ getDocumentExcerpt(document.content) }}
          </p>
        </div>
        
        <!-- Document actions -->
        <div class="document-actions">
          <button
            @click="handleViewDocument(document)"
            class="action-btn view-btn"
            title="Ver documento completo"
          >
            👁️ Ver
          </button>
          
          <button
            v-if="showEditButton"
            @click="handleEditDocument(document)"
            class="action-btn edit-btn"
            title="Editar documento"
          >
            ✏️ Editar
          </button>
          
          <button
            @click="handleDeleteDocument(document)"
            class="action-btn delete-btn"
            title="Eliminar documento"
          >
            🗑️ Eliminar
          </button>
          
          <!-- Additional actions dropdown -->
          <div class="dropdown" v-if="showAdditionalActions">
            <button
              @click="toggleActionsDropdown(document.id)"
              class="action-btn dropdown-toggle"
              title="Más acciones"
            >
              ⋮
            </button>
            
            <div
              v-show="activeDropdown === document.id"
              class="dropdown-menu"
              @click.stop
            >
              <button @click="downloadDocument(document)" class="dropdown-item">
                📥 Descargar
              </button>
              <button @click="shareDocument(document)" class="dropdown-item">
                🔗 Compartir
              </button>
              <button @click="duplicateDocument(document)" class="dropdown-item">
                📋 Duplicar
              </button>
              <div class="dropdown-divider"></div>
              <button @click="moveToTrash(document)" class="dropdown-item danger">
                🗑️ Mover a papelera
              </button>
            </div>
          </div>
        </div>
        
        <!-- Document status indicators -->
        <div class="document-status">
          <span v-if="document.status === 'draft'" class="status-badge draft">
            ✏️ Borrador
          </span>
          <span v-if="document.status === 'published'" class="status-badge published">
            ✅ Publicado
          </span>
          <span v-if="document.encrypted" class="status-badge encrypted">
            🔒 Cifrado
          </span>
          <span v-if="document.shared" class="status-badge shared">
            🔗 Compartido
          </span>
        </div>
      </div>
    </div>
    
    <!-- Empty state -->
    <div v-else class="empty-state">
      <div class="empty-icon">📄</div>
      <h4>No hay documentos disponibles</h4>
      <p>Los documentos que subas aparecerán aquí</p>
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
  documents: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  showEditButton: {
    type: Boolean,
    default: true
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
  'view-document',
  'edit-document', 
  'delete-document',
  'refresh',
  'download-document',
  'share-document',
  'duplicate-document'
])

// ============================================================================
// STORES & COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const { showNotification } = useNotifications()

// ============================================================================
// ESTADO LOCAL
// ============================================================================

const selectedDocumentId = ref(null)
const activeDropdown = ref(null)
const currentPage = ref(1)

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const totalPages = computed(() => {
  return Math.ceil(props.documents.length / props.itemsPerPage)
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

const paginatedDocuments = computed(() => {
  const start = (currentPage.value - 1) * props.itemsPerPage
  const end = start + props.itemsPerPage
  return props.documents.slice(start, end)
})

// ============================================================================
// MÉTODOS PRINCIPALES
// ============================================================================

/**
 * Handle view document
 */
const handleViewDocument = (document) => {
  selectedDocumentId.value = document.id
  emit('view-document', document.id || document._id)
  appStore.addToLog(`Viewing document: ${document.title}`, 'info')
}

/**
 * Handle edit document
 */
const handleEditDocument = (document) => {
  emit('edit-document', document.id || document._id)
  appStore.addToLog(`Editing document: ${document.title}`, 'info')
}

/**
 * Handle delete document
 */
const handleDeleteDocument = (document) => {
  const confirmed = confirm(`¿Estás seguro de que quieres eliminar "${document.title}"?`)
  
  if (confirmed) {
    emit('delete-document', document.id || document._id)
    appStore.addToLog(`Deleting document: ${document.title}`, 'info')
  }
}

/**
 * Toggle actions dropdown
 */
const toggleActionsDropdown = (documentId) => {
  activeDropdown.value = activeDropdown.value === documentId ? null : documentId
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

const downloadDocument = (document) => {
  try {
    // Create a blob with the document content
    const blob = new Blob([document.content || ''], { 
      type: getDocumentMimeType(document.type) 
    })
    const url = URL.createObjectURL(blob)
    
    // Create download link
    const link = document.createElement('a')
    link.href = url
    link.download = `${document.title}.${getFileExtension(document.type)}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    // Clean up
    URL.revokeObjectURL(url)
    
    showNotification(`✅ Descargando: ${document.title}`, 'success')
    emit('download-document', document)
    
  } catch (error) {
    console.error('Error downloading document:', error)
    showNotification('❌ Error al descargar el documento', 'error')
  }
  
  closeDropdowns()
}

const shareDocument = (document) => {
  // Copy document URL to clipboard
  const url = `${window.location.origin}/documents/${document.id}`
  
  navigator.clipboard.writeText(url).then(() => {
    showNotification('🔗 Enlace copiado al portapapeles', 'success')
  }).catch(() => {
    showNotification('❌ Error al copiar enlace', 'error')
  })
  
  emit('share-document', document)
  closeDropdowns()
}

const duplicateDocument = (document) => {
  emit('duplicate-document', document)
  showNotification(`📋 Duplicando: ${document.title}`, 'info')
  closeDropdowns()
}

const moveToTrash = (document) => {
  const confirmed = confirm(`¿Mover "${document.title}" a la papelera?`)
  
  if (confirmed) {
    // This could be different from permanent delete
    emit('delete-document', document.id || document._id)
    showNotification(`🗑️ ${document.title} movido a papelera`, 'warning')
  }
  
  closeDropdowns()
}

// ============================================================================
// MÉTODOS DE UTILIDAD
// ============================================================================

/**
 * Get document icon based on type
 */
const getDocumentIcon = (type) => {
  const iconMap = {
    'pdf': '📕',
    'word': '📘', 
    'txt': '📄',
    'text': '📄',
    'markdown': '📝',
    'md': '📝',
    'json': '🔧',
    'csv': '📊',
    'excel': '📊',
    'image': '🖼️',
    'video': '🎥',
    'audio': '🎵'
  }
  
  return iconMap[type?.toLowerCase()] || '📄'
}

/**
 * Get document excerpt for preview
 */
const getDocumentExcerpt = (content) => {
  if (!content) return 'Sin contenido disponible'
  
  const maxLength = 120
  const cleaned = content.replace(/\s+/g, ' ').trim()
  
  return cleaned.length > maxLength 
    ? cleaned.substring(0, maxLength) + '...'
    : cleaned
}

/**
 * Format file size
 */
const formatFileSize = (bytes) => {
  if (!bytes) return 'Desconocido'
  
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
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

/**
 * Get MIME type for document
 */
const getDocumentMimeType = (type) => {
  const mimeMap = {
    'pdf': 'application/pdf',
    'word': 'application/msword',
    'txt': 'text/plain',
    'text': 'text/plain',
    'markdown': 'text/markdown',
    'md': 'text/markdown',
    'json': 'application/json',
    'csv': 'text/csv'
  }
  
  return mimeMap[type?.toLowerCase()] || 'text/plain'
}

/**
 * Get file extension for download
 */
const getFileExtension = (type) => {
  const extensionMap = {
    'pdf': 'pdf',
    'word': 'doc',
    'txt': 'txt',
    'text': 'txt',
    'markdown': 'md',
    'md': 'md',
    'json': 'json',
    'csv': 'csv'
  }
  
  return extensionMap[type?.toLowerCase()] || 'txt'
}

// ============================================================================
// PAGINATION METHODS
// ============================================================================

const goToPage = (page) => {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
    closeDropdowns()
  }
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
.document-list {
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

.documents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

.document-card {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  transition: all 0.3s ease;
  cursor: pointer;
  position: relative;
}

.document-card:hover {
  border-color: var(--primary-color);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.document-card.document-selected {
  border-color: var(--primary-color);
  background: rgba(102, 126, 234, 0.05);
}

.document-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}

.document-icon {
  font-size: 1.5em;
  min-width: 32px;
  text-align: center;
}

.document-info {
  flex: 1;
  min-width: 0;
}

.document-title {
  margin: 0 0 6px 0;
  font-size: 1.1em;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.3;
  
  /* Text overflow handling */
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.document-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 0.8em;
  color: var(--text-muted);
}

.document-meta span {
  display: inline-block;
}

.document-preview {
  margin-bottom: 12px;
}

.document-excerpt {
  margin: 0;
  font-size: 0.9em;
  color: var(--text-secondary);
  line-height: 1.4;
  
  /* Multi-line text overflow */
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}

.document-actions {
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

.edit-btn:hover {
  border-color: var(--warning-color);
  color: var(--warning-color);
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

.dropdown-item.danger {
  color: var(--danger-color);
}

.dropdown-item.danger:hover {
  background: rgba(239, 68, 68, 0.1);
}

.dropdown-divider {
  height: 1px;
  background: var(--border-color);
  margin: 4px 0;
}

.document-status {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.status-badge {
  padding: 2px 6px;
  border-radius: 12px;
  font-size: 0.75em;
  font-weight: 500;
  white-space: nowrap;
}

.status-badge.draft {
  background: rgba(245, 158, 11, 0.1);
  color: var(--warning-color);
}

.status-badge.published {
  background: rgba(34, 197, 94, 0.1);
  color: var(--success-color);
}

.status-badge.encrypted {
  background: rgba(99, 102, 241, 0.1);
  color: var(--info-color);
}

.status-badge.shared {
  background: rgba(168, 85, 247, 0.1);
  color: #a855f7;
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

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Responsive */
@media (max-width: 768px) {
  .documents-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
  
  .document-header {
    flex-direction: column;
    gap: 8px;
  }
  
  .document-info {
    text-align: center;
  }
  
  .document-actions {
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
}

@media (max-width: 480px) {
  .document-card {
    padding: 12px;
  }
  
  .document-actions {
    flex-direction: column;
  }
  
  .action-btn {
    text-align: center;
  }
}
</style>
