<template>
  <!-- Modal Overlay -->
  <Teleport to="body">
    <div 
      v-if="isVisible" 
      class="modal-overlay"
      @click="handleOverlayClick"
      @keydown.esc="closeModal"
      tabindex="0"
      ref="modalOverlay"
    >
      <!-- Modal Content -->
      <div 
        class="modal-content"
        @click.stop
        ref="modalContent"
      >
        <!-- Modal Header -->
        <div class="modal-header">
          <div class="modal-title-section">
            <h3 class="modal-title">
              📄 {{ documentTitle }}
            </h3>
            <div v-if="document" class="modal-meta">
              <span v-if="document.created_at" class="meta-item">
                📅 {{ formatDate(document.created_at) }}
              </span>
              <span v-if="document.type" class="meta-item">
                📄 {{ document.type }}
              </span>
              <span v-if="document.size" class="meta-item">
                💾 {{ formatFileSize(document.size) }}
              </span>
              <span v-if="document.company_id" class="meta-item">
                🏢 {{ document.company_id }}
              </span>
            </div>
          </div>
          
          <div class="modal-header-actions">
            <button 
              v-if="!loading && document"
              @click="downloadDocument"
              class="modal-action-btn download-btn"
              title="Descargar documento"
            >
              📥 Descargar
            </button>
            <button 
              v-if="!loading && document && showEditButton"
              @click="editDocument"
              class="modal-action-btn edit-btn"
              title="Editar documento"
            >
              ✏️ Editar
            </button>
            <button 
              @click="closeModal"
              class="modal-close-btn"
              title="Cerrar modal"
            >
              ✕
            </button>
          </div>
        </div>
        
        <!-- Modal Body -->
        <div class="modal-body">
          <!-- Loading State -->
          <div v-if="loading" class="modal-loading">
            <div class="loading-spinner">⏳</div>
            <p>Cargando documento...</p>
          </div>
          
          <!-- Error State -->
          <div v-else-if="error" class="modal-error">
            <div class="error-icon">❌</div>
            <h4>Error al cargar documento</h4>
            <p>{{ error }}</p>
            <button @click="retryLoad" class="retry-btn">
              🔄 Intentar de nuevo
            </button>
          </div>
          
          <!-- Document Content -->
          <div v-else-if="document" class="document-viewer">
            <!-- Document Info Panel -->
            <div v-if="showDocumentInfo" class="document-info-panel">
              <button 
                @click="toggleDocumentInfo"
                class="info-toggle-btn"
              >
                {{ showDocumentInfo ? '▲ Ocultar info' : '▼ Mostrar info' }}
              </button>
              
              <div class="info-grid">
                <div class="info-item">
                  <span class="info-label">ID:</span>
                  <span class="info-value">{{ document.id || 'N/A' }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">Título:</span>
                  <span class="info-value">{{ document.title || 'Sin título' }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">Tipo:</span>
                  <span class="info-value">{{ document.type || 'Texto' }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">Tamaño:</span>
                  <span class="info-value">{{ formatFileSize(document.size) }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">Creado:</span>
                  <span class="info-value">{{ formatDate(document.created_at) }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">Empresa:</span>
                  <span class="info-value">{{ document.company_id || 'N/A' }}</span>
                </div>
              </div>
            </div>
            
            <!-- Content Display -->
            <div class="document-content-container">
              <!-- Content Toolbar -->
              <div class="content-toolbar">
                <div class="toolbar-left">
                  <button 
                    @click="toggleDocumentInfo"
                    class="toolbar-btn"
                    :class="{ 'active': showDocumentInfo }"
                  >
                    ℹ️ Info
                  </button>
                  <button 
                    @click="toggleWrapText"
                    class="toolbar-btn"
                    :class="{ 'active': wrapText }"
                  >
                    📄 Ajustar texto
                  </button>
                  <button 
                    @click="copyContent"
                    class="toolbar-btn"
                  >
                    📋 Copiar
                  </button>
                </div>
                
                <div class="toolbar-right">
                  <span class="content-stats">
                    {{ getContentStats() }}
                  </span>
                </div>
              </div>
              
              <!-- Actual Content -->
              <div class="document-content-display">
                <pre 
                  class="document-content-text"
                  :class="{ 'wrap-text': wrapText }"
                >{{ documentContent }}</pre>
              </div>
            </div>
          </div>
          
          <!-- Empty State -->
          <div v-else class="modal-empty">
            <div class="empty-icon">📄</div>
            <p>No hay documento para mostrar</p>
          </div>
        </div>
        
        <!-- Modal Footer -->
        <div v-if="!loading && document" class="modal-footer">
          <div class="footer-left">
            <span class="document-path">
              🏢 {{ document.company_id || appStore.currentCompanyId }} / 
              📄 {{ document.title || 'documento.txt' }}
            </span>
          </div>
          
          <div class="footer-right">
            <button 
              v-if="showDeleteButton"
              @click="deleteDocument"
              class="footer-btn delete-btn"
            >
              🗑️ Eliminar
            </button>
            <button 
              @click="shareDocument"
              class="footer-btn share-btn"
            >
              🔗 Compartir
            </button>
            <button 
              @click="closeModal"
              class="footer-btn close-btn"
            >
              Cerrar
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useAppStore } from '@/stores/app'
import { useNotifications } from '@/composables/useNotifications'

// ============================================================================
// PROPS & EMITS
// ============================================================================

const props = defineProps({
  documentId: {
    type: String,
    default: null
  },
  visible: {
    type: Boolean,
    default: false
  },
  document: {
    type: Object,
    default: null
  },
  showEditButton: {
    type: Boolean,
    default: true
  },
  showDeleteButton: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits([
  'close',
  'edit',
  'delete',
  'download',
  'share'
])

// ============================================================================
// STORES & COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const { showNotification } = useNotifications()

// ============================================================================
// ESTADO LOCAL
// ============================================================================

const isVisible = ref(false)
const loading = ref(false)
const error = ref(null)
const currentDocument = ref(null)
const showDocumentInfo = ref(false)
const wrapText = ref(true)

// Refs para elementos del DOM
const modalOverlay = ref(null)
const modalContent = ref(null)

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const document = computed(() => {
  return props.document || currentDocument.value
})

const documentTitle = computed(() => {
  if (loading.value) return 'Cargando...'
  if (error.value) return 'Error'
  return document.value?.title || 'Documento'
})

const documentContent = computed(() => {
  return document.value?.content || 'Sin contenido disponible'
})

// ============================================================================
// WATCHERS
// ============================================================================

watch(() => props.visible, (newValue) => {
  if (newValue) {
    openModal()
  } else {
    closeModal()
  }
})

watch(() => props.documentId, (newId) => {
  if (newId && isVisible.value) {
    loadDocument(newId)
  }
})

// ============================================================================
// MÉTODOS PRINCIPALES
// ============================================================================

/**
 * Open modal - PRESERVAR FUNCIONALIDAD EXACTA
 */
const openModal = async () => {
  isVisible.value = true
  error.value = null
  
  // Focus modal para keyboard navigation
  await nextTick()
  if (modalOverlay.value) {
    modalOverlay.value.focus()
  }
  
  // Cargar documento si tenemos ID pero no documento
  if (props.documentId && !props.document) {
    await loadDocument(props.documentId)
  } else if (props.document) {
    currentDocument.value = props.document
  }
  
  // Prevent body scroll
  document.body.style.overflow = 'hidden'
  
  appStore.addToLog('Document modal opened', 'info')
}

/**
 * Close modal - PRESERVAR FUNCIONALIDAD EXACTA
 */
const closeModal = () => {
  isVisible.value = false
  
  // Restore body scroll
  document.body.style.overflow = ''
  
  // Clear data
  currentDocument.value = null
  error.value = null
  showDocumentInfo.value = false
  
  emit('close')
  appStore.addToLog('Document modal closed', 'info')
}

/**
 * Load document - PRESERVAR API FORMAT EXACTO
 */
const loadDocument = async (docId) => {
  if (!docId) return
  
  try {
    loading.value = true
    error.value = null
    
    const response = await appStore.apiRequest(`/api/documents/${docId}`)
    const doc = response.data || response
    
    currentDocument.value = doc
    appStore.addToLog(`Document loaded in modal: ${doc.title}`, 'info')
    
  } catch (err) {
    console.error('Error loading document:', err)
    error.value = err.message
    appStore.addToLog(`Document load error: ${err.message}`, 'error')
    
  } finally {
    loading.value = false
  }
}

/**
 * Retry loading document
 */
const retryLoad = () => {
  if (props.documentId) {
    loadDocument(props.documentId)
  }
}

/**
 * Handle overlay click (close modal)
 */
const handleOverlayClick = (event) => {
  if (event.target === modalOverlay.value) {
    closeModal()
  }
}

// ============================================================================
// ACTION METHODS
// ============================================================================

/**
 * Download document
 */
const downloadDocument = () => {
  if (!document.value) return
  
  try {
    const content = document.value.content || ''
    const title = document.value.title || 'documento'
    
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    
    const link = document.createElement('a')
    link.href = url
    link.download = `${title}.txt`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    URL.revokeObjectURL(url)
    
    showNotification(`📥 Descargando: ${title}`, 'success')
    emit('download', document.value)
    
  } catch (error) {
    console.error('Error downloading document:', error)
    showNotification('❌ Error al descargar documento', 'error')
  }
}

/**
 * Edit document
 */
const editDocument = () => {
  emit('edit', document.value)
  showNotification('✏️ Abriendo editor...', 'info')
}

/**
 * Delete document
 */
const deleteDocument = () => {
  const confirmed = confirm(`¿Estás seguro de que quieres eliminar "${document.value.title}"?`)
  
  if (confirmed) {
    emit('delete', document.value.id || document.value._id)
    closeModal()
  }
}

/**
 * Share document
 */
const shareDocument = () => {
  if (!document.value) return
  
  try {
    const shareText = `Documento: ${document.value.title}\n\nContenido:\n${documentContent.value}`
    
    if (navigator.share) {
      navigator.share({
        title: document.value.title,
        text: shareText
      })
    } else {
      // Fallback: copy to clipboard
      navigator.clipboard.writeText(shareText).then(() => {
        showNotification('🔗 Contenido copiado al portapapeles', 'success')
      })
    }
    
    emit('share', document.value)
    
  } catch (error) {
    console.error('Error sharing document:', error)
    showNotification('❌ Error al compartir documento', 'error')
  }
}

/**
 * Copy content to clipboard
 */
const copyContent = async () => {
  try {
    await navigator.clipboard.writeText(documentContent.value)
    showNotification('📋 Contenido copiado al portapapeles', 'success')
  } catch (error) {
    console.error('Error copying content:', error)
    showNotification('❌ Error al copiar contenido', 'error')
  }
}

/**
 * Toggle document info panel
 */
const toggleDocumentInfo = () => {
  showDocumentInfo.value = !showDocumentInfo.value
}

/**
 * Toggle text wrapping
 */
const toggleWrapText = () => {
  wrapText.value = !wrapText.value
}

// ============================================================================
// UTILITY METHODS
// ============================================================================

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
    return new Date(dateString).toLocaleString('es-ES')
  } catch {
    return 'Fecha inválida'
  }
}

/**
 * Get content statistics
 */
const getContentStats = () => {
  if (!documentContent.value) return ''
  
  const content = documentContent.value
  const lines = content.split('\n').length
  const words = content.split(/\s+/).filter(word => word.length > 0).length
  const chars = content.length
  
  return `${lines} líneas, ${words} palabras, ${chars} caracteres`
}

// ============================================================================
// LIFECYCLE HOOKS
// ============================================================================

onMounted(() => {
  // Expose global closeModal function for compatibility
  window.closeModal = closeModal
  
  // Handle escape key globally
  document.addEventListener('keydown', handleGlobalKeydown)
})

onUnmounted(() => {
  // Restore body scroll
  document.body.style.overflow = ''
  
  // Clean up global listeners
  document.removeEventListener('keydown', handleGlobalKeydown)
  
  // Remove global function
  if (window.closeModal === closeModal) {
    delete window.closeModal
  }
})

/**
 * Handle global keyboard shortcuts
 */
const handleGlobalKeydown = (event) => {
  if (!isVisible.value) return
  
  switch (event.key) {
    case 'Escape':
      closeModal()
      break
    case 'd':
      if (event.ctrlKey || event.metaKey) {
        event.preventDefault()
        downloadDocument()
      }
      break
    case 'c':
      if (event.ctrlKey || event.metaKey) {
        event.preventDefault()
        copyContent()
      }
      break
    case 'i':
      if (event.ctrlKey || event.metaKey) {
        event.preventDefault()
        toggleDocumentInfo()
      }
      break
  }
}
</script>

<style scoped>
/* Modal Overlay */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 10000;
  backdrop-filter: blur(3px);
  padding: 20px;
}

/* Modal Content */
.modal-content {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  max-width: 90vw;
  width: 1000px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  position: relative;
  animation: modalSlideIn 0.3s ease-out;
}

@keyframes modalSlideIn {
  from {
    opacity: 0;
    transform: translateY(-30px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* Modal Header */
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 20px 25px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
  border-radius: 12px 12px 0 0;
  gap: 15px;
}

.modal-title-section {
  flex: 1;
  min-width: 0;
}

.modal-title {
  margin: 0 0 8px 0;
  color: var(--text-primary);
  font-size: 1.3em;
  font-weight: 600;
  word-wrap: break-word;
}

.modal-meta {
  display: flex;
  gap: 15px;
  font-size: 0.85em;
  color: var(--text-secondary);
  flex-wrap: wrap;
}

.meta-item {
  white-space: nowrap;
}

.modal-header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-shrink: 0;
}

.modal-action-btn {
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--bg-primary);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 0.85em;
  font-weight: 500;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.modal-action-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.download-btn:hover {
  border-color: var(--success-color);
  color: var(--success-color);
}

.edit-btn:hover {
  border-color: var(--warning-color);
  color: var(--warning-color);
}

.modal-close-btn {
  background: none;
  border: none;
  font-size: 20px;
  color: var(--text-muted);
  cursor: pointer;
  padding: 5px;
  border-radius: 4px;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.modal-close-btn:hover {
  background: var(--danger-color);
  color: white;
}

/* Modal Body */
.modal-body {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-loading,
.modal-error,
.modal-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
  color: var(--text-secondary);
}

.loading-spinner {
  font-size: 2em;
  margin-bottom: 15px;
  animation: spin 1s linear infinite;
}

.error-icon,
.empty-icon {
  font-size: 3em;
  margin-bottom: 15px;
  opacity: 0.5;
}

.retry-btn {
  margin-top: 15px;
  padding: 8px 16px;
  background: var(--primary-color);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
}

.retry-btn:hover {
  background: var(--primary-color-dark);
}

/* Document Viewer */
.document-viewer {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.document-info-panel {
  padding: 15px 20px;
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-color);
}

.info-toggle-btn {
  width: 100%;
  padding: 8px;
  background: none;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  cursor: pointer;
  margin-bottom: 15px;
  color: var(--text-secondary);
  transition: all 0.2s ease;
}

.info-toggle-btn:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 10px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.9em;
}

.info-label {
  color: var(--text-secondary);
  font-weight: 500;
}

.info-value {
  color: var(--text-primary);
  font-weight: 600;
  text-align: right;
}

/* Content Container */
.document-content-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.content-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 20px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  gap: 15px;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  gap: 8px;
  align-items: center;
}

.toolbar-btn {
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--bg-primary);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 0.85em;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.toolbar-btn:hover,
.toolbar-btn.active {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: white;
}

.content-stats {
  font-size: 0.8em;
  color: var(--text-muted);
}

/* Document Content Display */
.document-content-display {
  flex: 1;
  overflow: auto;
  padding: 0;
}

.document-content-text {
  margin: 0;
  padding: 20px;
  font-family: 'Courier New', monospace;
  font-size: 0.9em;
  line-height: 1.6;
  color: var(--text-primary);
  background: var(--bg-primary);
  white-space: pre;
  overflow-x: auto;
  min-height: 100%;
}

.document-content-text.wrap-text {
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow-x: hidden;
}

/* Modal Footer */
.modal-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 25px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-secondary);
  border-radius: 0 0 12px 12px;
  gap: 15px;
}

.footer-left {
  flex: 1;
  min-width: 0;
}

.document-path {
  font-size: 0.85em;
  color: var(--text-muted);
  font-family: monospace;
  word-wrap: break-word;
}

.footer-right {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.footer-btn {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--bg-primary);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 0.85em;
  font-weight: 500;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.footer-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.delete-btn:hover {
  border-color: var(--danger-color);
  color: var(--danger-color);
}

.share-btn:hover {
  border-color: var(--info-color);
  color: var(--info-color);
}

.close-btn:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Responsive */
@media (max-width: 768px) {
  .modal-content {
    width: 95vw;
    max-width: none;
    margin: 10px;
  }
  
  .modal-header {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }
  
  .modal-header-actions {
    justify-content: center;
  }
  
  .modal-meta {
    justify-content: center;
  }
  
  .content-toolbar {
    flex-direction: column;
    gap: 10px;
  }
  
  .toolbar-left,
  .toolbar-right {
    justify-content: center;
  }
  
  .modal-footer {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }
  
  .footer-right {
    justify-content: center;
  }
  
  .info-grid {
    grid-template-columns: 1fr;
  }
  
  .info-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
  
  .info-value {
    text-align: left;
  }
}

@media (max-width: 480px) {
  .modal-header,
  .modal-footer {
    padding: 15px;
  }
  
  .document-content-text {
    padding: 15px;
    font-size: 0.8em;
  }
  
  .modal-action-btn,
  .footer-btn {
    flex: 1;
    text-align: center;
  }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .modal-content {
    animation: none;
  }
  
  .loading-spinner {
    animation: none;
  }
}
</style>
