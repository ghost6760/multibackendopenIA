<template>
  <div class="tab-content" :class="{ 'active': isActive }" id="documents">
    <!-- Company validation -->
    <div v-if="!appStore.hasCompanySelected" class="warning-message">
      <h3>⚠️ Empresa no seleccionada</h3>
      <p>Selecciona una empresa para gestionar sus documentos.</p>
      <button @click="highlightCompanySelector" class="btn-primary">
        🏢 Seleccionar Empresa
      </button>
    </div>
    
    <!-- Main content when company is selected -->
    <template v-else>
      <!-- Document management grid -->
      <div class="grid grid-2">
        <!-- Upload Document Card -->
        <div class="card">
          <h3>📄 Subir Documento</h3>
          
          <!-- Title input -->
          <div class="form-group">
            <label for="documentTitle">Título del Documento</label>
            <input 
              type="text" 
              id="documentTitle" 
              v-model="documentTitle"
              placeholder="Ej: Protocolo de tratamientos"
              :disabled="isUploading"
              @keyup.enter="handleUpload"
            >
          </div>
          
          <!-- Content textarea -->
          <div class="form-group">
            <label for="documentContent">Contenido</label>
            <textarea 
              id="documentContent"
              v-model="documentContent"
              placeholder="Contenido del documento..."
              rows="4"
              :disabled="isUploading"
            ></textarea>
          </div>
          
          <!-- File upload area -->
          <div class="form-group">
            <label for="documentFile">O subir archivo</label>
            <div 
              class="file-upload"
              :class="{ 
                'drag-over': isDragOver,
                'uploading': isUploading
              }"
              @click="triggerFileSelect"
              @dragenter.prevent="handleDragEnter"
              @dragover.prevent="handleDragOver"  
              @dragleave.prevent="handleDragLeave"
              @drop.prevent="handleDrop"
            >
              <input 
                type="file" 
                id="documentFile" 
                ref="fileInputRef"
                style="display: none;" 
                accept=".txt,.md,.pdf,.docx,.json,.csv"
                @change="handleFileSelect"
                :disabled="isUploading"
              >
              
              <!-- Upload content -->
              <div v-if="!selectedFile && !isUploading" class="upload-content">
                📁 Hacer clic o arrastrar archivo aquí
                <small>Formatos: PDF, Word, TXT, MD, JSON, CSV</small>
              </div>
              
              <!-- Selected file info -->
              <div v-else-if="selectedFile && !isUploading" class="selected-file">
                <div class="file-info">
                  <span class="file-icon">{{ getFileIcon(selectedFile.type) }}</span>
                  <div class="file-details">
                    <div class="file-name">{{ selectedFile.name }}</div>
                    <div class="file-size">{{ formatFileSize(selectedFile.size) }}</div>
                  </div>
                </div>
                <button @click.stop="clearSelectedFile" class="clear-file-btn">✕</button>
              </div>
              
              <!-- Upload progress -->
              <div v-else-if="isUploading" class="upload-progress">
                <div class="progress-info">
                  <span>📤 Subiendo archivo...</span>
                  <span>{{ Math.round(uploadProgress) }}%</span>
                </div>
                <div class="progress-bar">
                  <div 
                    class="progress-fill" 
                    :style="{ width: `${uploadProgress}%` }"
                  ></div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Upload button -->
          <button 
            class="btn btn-primary" 
            @click="handleUpload"
            :disabled="!canUploadDocument"
            :class="{ 'uploading': isUploading }"
          >
            <span v-if="isUploading">⏳ Subiendo...</span>
            <span v-else>📤 Subir Documento</span>
          </button>
        </div>

        <!-- Search Documents Card -->
        <div class="card">
          <h3>🔍 Buscar Documentos</h3>
          
          <div class="form-group">
            <label for="searchQuery">Buscar en documentos</label>
            <div class="search-input-group">
              <input 
                type="text" 
                id="searchQuery"
                v-model="searchQuery"
                placeholder="Ej: tratamientos faciales"
                :disabled="isSearching"
                @keyup.enter="handleSearch"
              >
              <button 
                @click="handleSearch"
                :disabled="!searchQuery.trim() || isSearching"
                class="search-btn"
              >
                <span v-if="isSearching">⏳</span>
                <span v-else>🔍</span>
              </button>
            </div>
          </div>
          
          <!-- 🔧 CRÍTICO: Botón para cerrar modals si hay problemas -->
          <div v-if="isModalOpen" class="modal-alert">
            <div class="alert alert-warning">
              <span>⚠️ Hay un modal abierto</span>
              <button @click="forceCloseModals" class="btn-close-modal">
                ✕ Cerrar Modal
              </button>
            </div>
          </div>
          
          <!-- Search results -->
          <div id="searchResults" class="search-results-container">
            <SearchResults
              v-if="hasSearchResults"
              :results="searchResults"
              :search-query="searchQuery"
              @view-document="viewDocument"
              @delete-document="deleteDocument"
              @clear-results="clearSearchResults"
            />
            <div v-else-if="searchPerformed && !hasSearchResults" class="no-results">
              <p>❌ No se encontraron documentos que coincidan con la búsqueda</p>
            </div>
            <div v-else class="search-placeholder">
              <p>Los resultados de búsqueda aparecerán aquí</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Document List Card -->
      <div class="card">
        <div class="card-header">
          <h3>📋 Lista de Documentos</h3>
          <div class="card-actions">
            <button 
              @click="loadDocuments" 
              :disabled="isLoading"
              class="btn btn-secondary"
            >
              <span v-if="isLoading">⏳</span>
              <span v-else>🔄</span>
              Actualizar Lista
            </button>
            
            <!-- 🔧 NUEVO: Botón de emergencia para cerrar modals -->
            <button 
              v-if="isModalOpen"
              @click="forceCloseModals" 
              class="btn btn-warning"
              title="Cerrar todos los modals abiertos"
            >
              ✕ Cerrar Modals
            </button>
            
            <!-- Document stats -->
            <div class="document-stats">
              <span class="stat-item">
                📄 {{ documentsCount }} documentos
              </span>
              <span v-if="appStore.currentCompanyId" class="stat-item">
                🏢 {{ appStore.currentCompanyId }}
              </span>
            </div>
          </div>
        </div>
        
        <!-- Documents list -->
        <div class="data-list" id="documentsList">
          <DocumentList
            v-if="hasDocuments"
            :documents="documents"
            :loading="isLoading"
            @view-document="viewDocument"
            @delete-document="deleteDocument"
            @refresh="loadDocuments"
          />
          
          <div v-else-if="isLoading" class="loading-placeholder">
            <div class="loading-spinner">⏳</div>
            <p>Cargando documentos...</p>
          </div>
          
          <div v-else class="empty-state">
            <div class="empty-icon">📄</div>
            <h4>No hay documentos</h4>
            <p>
              {{ appStore.currentCompanyId 
                ? `No hay documentos para la empresa "${appStore.currentCompanyId}"`
                : 'Selecciona una empresa y haz clic en "Actualizar Lista" para ver los documentos'
              }}
            </p>
            <button 
              v-if="appStore.currentCompanyId" 
              @click="focusUploadArea"
              class="btn-primary"
            >
              📤 Subir primer documento
            </button>
          </div>
        </div>
      </div>

      <!-- Admin Functions (if API key is configured) -->
      <div v-if="showAdminFunctions" class="card admin-functions">
        <div class="api-key-functions">
          <h4>🔧 Funciones Administrativas</h4>
          <div class="admin-actions">
            <button 
              @click="exportDocuments" 
              class="btn btn-outline"
              :disabled="!hasDocuments"
            >
              📦 Exportar Documentos
            </button>
            <button 
              @click="importDocuments" 
              class="btn btn-outline"
            >
              📥 Importar Documentos
            </button>
            <button 
              @click="runDocumentMaintenance" 
              class="btn btn-secondary"
            >
              🔧 Mantenimiento
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
import { useDocuments } from '@/composables/useDocuments'
import { useNotifications } from '@/composables/useNotifications'

// Sub-components
import DocumentList from './DocumentList.vue'
import SearchResults from './SearchResults.vue'

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
  documents,
  searchResults,
  isLoading,
  isUploading,
  isSearching,
  uploadProgress,
  hasDocuments,
  documentsCount,
  hasSearchResults,
  canUpload,
  // 🆕 NUEVO: Estado del modal
  isModalOpen,
  modalDocument,
  uploadDocument,
  loadDocuments,
  searchDocuments,
  viewDocument,
  deleteDocument,
  // 🆕 NUEVO: Función para cerrar modals
  forceCloseAllModals,
  setupFileUploadHandlers,
  formatFileSize,
  cleanup
} = useDocuments()

const { showNotification } = useNotifications()

// ============================================================================
// ESTADO LOCAL
// ============================================================================

const documentTitle = ref('')
const documentContent = ref('')
const searchQuery = ref('')
const selectedFile = ref(null)
const isDragOver = ref(false)
const searchPerformed = ref(false)
const fileInputRef = ref(null)

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const canUploadDocument = computed(() => {
  return canUpload.value && 
         documentTitle.value.trim() && 
         (documentContent.value.trim() || selectedFile.value)
})

const showAdminFunctions = computed(() => {
  return appStore.adminApiKey || import.meta.env.DEV
})

// ============================================================================
// 🔧 WATCHERS PARA AUTO-CERRAR MODALS
// ============================================================================

// 🔧 CRÍTICO: Watch para cambios de pestaña activa
watch(() => props.isActive, (newActive, oldActive) => {
  if (oldActive && !newActive) {
    console.log('[DOCUMENTS-TAB] Tab became inactive, closing modals')
    forceCloseModals()
  }
})

// 🔧 CRÍTICO: Watch para cambios de empresa
watch(() => appStore.currentCompanyId, (newCompanyId, oldCompanyId) => {
  if (oldCompanyId && newCompanyId !== oldCompanyId) {
    console.log('[DOCUMENTS-TAB] Company changed, closing modals and clearing search')
    forceCloseModals()
    clearSearchResults()
  }
})

// ============================================================================
// MÉTODOS DE UPLOAD
// ============================================================================

/**
 * Maneja la subida de documento
 */
const handleUpload = async () => {
  if (!canUploadDocument.value) {
    showNotification('❌ Complete todos los campos requeridos', 'error')
    return
  }
  
  // 🔧 IMPORTANTE: Cerrar cualquier modal antes del upload
  forceCloseModals()
  
  // Actualizar los inputs del DOM para mantener compatibilidad
  const titleInput = document.getElementById('documentTitle')
  const contentInput = document.getElementById('documentContent')
  const fileInput = document.getElementById('documentFile')
  
  if (titleInput) titleInput.value = documentTitle.value
  if (contentInput) contentInput.value = documentContent.value
  if (fileInput && selectedFile.value) {
    // Crear un nuevo FileList con el archivo seleccionado
    const dataTransfer = new DataTransfer()
    dataTransfer.items.add(selectedFile.value)
    fileInput.files = dataTransfer.files
  }
  
  const success = await uploadDocument()
  
  if (success) {
    // Limpiar formulario
    documentTitle.value = ''
    documentContent.value = ''
    selectedFile.value = null
    
    // Recargar lista de documentos
    await loadDocuments()
  }
}

/**
 * Trigger file selection
 */
const triggerFileSelect = () => {
  if (!isUploading.value && fileInputRef.value) {
    fileInputRef.value.click()
  }
}

/**
 * Handle file selection from input
 */
const handleFileSelect = (event) => {
  const files = event.target.files
  if (files.length > 0) {
    selectedFile.value = files[0]
    showNotification(`📁 Archivo seleccionado: ${files[0].name}`, 'info', 2000)
  }
}

/**
 * Clear selected file
 */
const clearSelectedFile = () => {
  selectedFile.value = null
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

// ============================================================================
// MÉTODOS DE DRAG & DROP
// ============================================================================

const handleDragEnter = () => {
  isDragOver.value = true
}

const handleDragOver = () => {
  isDragOver.value = true
}

const handleDragLeave = (event) => {
  // Only remove highlight if we're leaving the drop zone completely
  if (!event.currentTarget.contains(event.relatedTarget)) {
    isDragOver.value = false
  }
}

const handleDrop = (event) => {
  isDragOver.value = false
  const files = event.dataTransfer.files
  
  if (files.length > 0) {
    selectedFile.value = files[0]
    
    // Update the file input as well
    const dataTransfer = new DataTransfer()
    dataTransfer.items.add(files[0])
    if (fileInputRef.value) {
      fileInputRef.value.files = dataTransfer.files
    }
    
    showNotification(`📁 Archivo seleccionado: ${files[0].name}`, 'info', 2000)
  }
}

// ============================================================================
// MÉTODOS DE BÚSQUEDA
// ============================================================================

/**
 * Handle search - MEJORADO con cierre de modals
 */
const handleSearch = async () => {
  if (!searchQuery.value.trim()) {
    showNotification('❌ Ingresa un término de búsqueda', 'error')
    return
  }
  
  // 🔧 CRÍTICO: Cerrar cualquier modal antes de nueva búsqueda
  forceCloseModals()
  
  // Update DOM input for compatibility
  const searchInput = document.getElementById('searchQuery')
  if (searchInput) {
    searchInput.value = searchQuery.value
  }
  
  searchPerformed.value = true
  await searchDocuments(searchQuery.value)
}

/**
 * 🔧 NUEVO: Limpiar resultados de búsqueda
 */
const clearSearchResults = () => {
  searchResults.value = []
  searchPerformed.value = false
  searchQuery.value = ''
  
  // Limpiar también el input DOM
  const searchInput = document.getElementById('searchQuery')
  if (searchInput) {
    searchInput.value = ''
  }
  
  // Cerrar cualquier modal abierto
  forceCloseModals()
  
  showNotification('🔍 Resultados de búsqueda limpiados', 'info')
}

// ============================================================================
// 🔧 MÉTODOS DE GESTIÓN DE MODALS - NUEVOS
// ============================================================================

/**
 * 🔧 CRÍTICO: Función para forzar cierre de modals desde el componente
 */
const forceCloseModals = () => {
  console.log('[DOCUMENTS-TAB] forceCloseModals called from component')
  forceCloseAllModals()
}

// ============================================================================
// MÉTODOS DE UTILIDAD
// ============================================================================

/**
 * Get file icon based on type
 */
const getFileIcon = (type) => {
  const iconMap = {
    'application/pdf': '📕',
    'application/msword': '📘',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '📘',
    'text/plain': '📄',
    'text/markdown': '📝',
    'application/json': '🔧',
    'text/csv': '📊'
  }
  
  return iconMap[type] || '📄'
}

/**
 * Focus upload area
 */
const focusUploadArea = () => {
  nextTick(() => {
    const titleInput = document.getElementById('documentTitle')
    if (titleInput) {
      titleInput.focus()
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

const exportDocuments = async () => {
  if (!hasDocuments.value) {
    showNotification('❌ No hay documentos para exportar', 'error')
    return
  }
  
  try {
    const data = JSON.stringify(documents.value, null, 2)
    const blob = new Blob([data], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    
    const link = document.createElement('a')
    link.href = url
    link.download = `documents_${appStore.currentCompanyId}_${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    URL.revokeObjectURL(url)
    
    showNotification('✅ Documentos exportados correctamente', 'success')
    appStore.addToLog('Documents exported successfully', 'info')
    
  } catch (error) {
    showNotification('❌ Error al exportar documentos', 'error')
    appStore.addToLog(`Export error: ${error.message}`, 'error')
  }
}

const importDocuments = () => {
  showNotification('⚠️ Función de importación en desarrollo', 'warning')
}

const runDocumentMaintenance = () => {
  showNotification('⚠️ Función de mantenimiento en desarrollo', 'warning')
}

// ============================================================================
// LIFECYCLE HOOKS - MEJORADOS
// ============================================================================

onMounted(async () => {
  appStore.addToLog('DocumentsTab mounted', 'info')
  
  // 🔧 IMPORTANTE: Setup file upload handlers
  setupFileUploadHandlers()
  
  // Load documents if company is selected
  if (appStore.hasCompanySelected) {
    await loadDocuments()
  }
  
  // Event listener for tab content loading
  window.addEventListener('loadTabContent', handleLoadTabContent)
  
  // 🔧 NUEVO: Event listeners para cerrar modals en casos especiales
  window.addEventListener('beforeunload', forceCloseModals)
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      console.log('[DOCUMENTS-TAB] Page hidden, closing modals')
      forceCloseModals()
    }
  })
})

onUnmounted(() => {
  console.log('[DOCUMENTS-TAB] Component unmounting, cleaning up')
  
  // 🔧 CRÍTICO: Limpiar todo antes de desmontar
  forceCloseModals()
  cleanup()
  
  // Remove event listeners
  window.removeEventListener('loadTabContent', handleLoadTabContent)
  window.removeEventListener('beforeunload', forceCloseModals)
})

// Handle load tab content event
const handleLoadTabContent = (event) => {
  if (event.detail.tabName === 'documents' && props.isActive) {
    // 🔧 NUEVO: Cerrar modals al cargar pestaña
    forceCloseModals()
    loadDocuments()
  }
}

// Watch for company changes
watch(() => appStore.currentCompanyId, (newCompanyId) => {
  if (newCompanyId && props.isActive) {
    loadDocuments()
  }
})

// ============================================================================
// EXPONER FUNCIONES GLOBALES PARA COMPATIBILIDAD - ACTUALIZADAS
// ============================================================================

onMounted(() => {
  // 🔧 ACTUALIZADO: Exponer funciones con cierre de modals
  window.uploadDocument = async () => {
    forceCloseModals()
    return await uploadDocument()
  }
  
  window.loadDocuments = async () => {
    forceCloseModals()
    return await loadDocuments()
  }
  
  window.searchDocuments = async (query) => {
    forceCloseModals()
    return await searchDocuments(query)
  }
  
  window.viewDocument = async (docId) => {
    // No cerrar modals aquí porque viewDocument va a abrir uno nuevo
    return await viewDocument(docId)
  }
  
  window.deleteDocument = async (docId) => {
    return await deleteDocument(docId)
  }
  
  // 🔧 NUEVA: Función global para forzar cierre desde cualquier lugar
  window.forceCloseAllDocumentModals = forceCloseModals
})

onUnmounted(() => {
  // Limpiar funciones globales
  if (typeof window !== 'undefined') {
    delete window.uploadDocument
    delete window.loadDocuments
    delete window.searchDocuments
    delete window.viewDocument
    delete window.deleteDocument
    delete window.forceCloseAllDocumentModals
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

/* 🔧 NUEVO: Estilos para alerta de modal */
.modal-alert {
  margin-bottom: 15px;
}

.alert {
  padding: 10px 15px;
  border-radius: 6px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.alert-warning {
  background: #fff3cd;
  border: 1px solid #ffecb3;
  color: #856404;
}

.btn-close-modal {
  background: #dc3545;
  color: white;
  border: none;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8em;
  font-weight: 500;
}

.btn-close-modal:hover {
  background: #c82333;
}

.btn-warning {
  background: #ffc107;
  color: #212529;
  border: 1px solid #ffc107;
}

.btn-warning:hover:not(:disabled) {
  background: #e0a800;
  border-color: #e0a800;
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

.document-stats {
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

.file-upload {
  border: 2px dashed var(--border-color);
  border-radius: 8px;
  padding: 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: var(--bg-tertiary);
  min-height: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.file-upload:hover:not(.uploading) {
  border-color: var(--primary-color);
  background: rgba(102, 126, 234, 0.05);
}

.file-upload.drag-over {
  border-color: var(--primary-color);
  background: rgba(102, 126, 234, 0.1);
  transform: scale(1.02);
}

.file-upload.uploading {
  cursor: not-allowed;
  opacity: 0.8;
}

.upload-content {
  color: var(--text-secondary);
}

.upload-content small {
  display: block;
  margin-top: 5px;
  font-size: 0.8em;
  color: var(--text-muted);
}

.selected-file {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 10px;
  background: var(--bg-secondary);
  border-radius: 6px;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.file-icon {
  font-size: 1.5em;
}

.file-details {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.file-name {
  font-weight: 500;
  color: var(--text-primary);
}

.file-size {
  font-size: 0.8em;
  color: var(--text-secondary);
}

.clear-file-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.clear-file-btn:hover {
  background: var(--danger-color);
  color: white;
}

.upload-progress {
  width: 100%;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
  font-size: 0.9em;
  color: var(--text-primary);
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: var(--bg-primary);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-color), var(--success-color));
  transition: width 0.3s ease;
}

.search-input-group {
  display: flex;
  gap: 8px;
}

.search-input-group input {
  flex: 1;
}

.search-btn {
  background: var(--primary-color);
  border: none;
  color: white;
  padding: 10px 15px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.2s ease;
  font-size: 1.1em;
}

.search-btn:hover:not(:disabled) {
  background: var(--primary-color-dark);
}

.search-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.search-results-container {
  margin-top: 15px;
  max-height: 400px;
  overflow-y: auto;
}

.search-placeholder,
.no-results {
  text-align: center;
  padding: 20px;
  color: var(--text-muted);
}

.no-results {
  color: var(--text-secondary);
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

.btn-outline {
  background: transparent;
  color: var(--primary-color);
  border: 1px solid var(--primary-color);
}

.btn-outline:hover:not(:disabled) {
  background: var(--primary-color);
  color: white;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn.uploading {
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
  
  .document-stats {
    justify-content: center;
  }
  
  .search-input-group {
    flex-direction: column;
  }
  
  .admin-actions {
    flex-direction: column;
  }
  
  .alert {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }
}
</style>
