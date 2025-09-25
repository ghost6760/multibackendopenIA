//DocumentsTab.vue - MEJORADO para manejo robusto de errores y IDs

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
      <!-- Error display -->
      <div v-if="systemError" class="error-banner">
        <div class="error-content">
          <h4>⚠️ Error del Sistema</h4>
          <p>{{ systemError }}</p>
          <div class="error-actions">
            <button @click="clearError" class="btn-secondary">Cerrar</button>
            <button @click="handleRetryLastAction" class="btn-primary">🔄 Reintentar</button>
          </div>
        </div>
      </div>

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
                'dragover': isDragOver,
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
          
          <!-- Search results -->
          <div id="searchResults" class="search-results-container">
            <SearchResults
              v-if="hasSearchResults"
              :results="searchResults"
              :search-query="searchQuery"
              @view-document="handleViewDocument"
              @delete-document="handleDeleteDocument"
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
              @click="handleLoadDocuments" 
              :disabled="isLoading"
              class="btn btn-secondary"
            >
              <span v-if="isLoading">⏳</span>
              <span v-else>🔄</span>
              Actualizar Lista
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
            @view-document="handleViewDocument"
            @delete-document="handleDeleteDocument"
            @refresh="handleLoadDocuments"
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

      <!-- 🆕 DEBUG PANEL (solo en desarrollo) -->
      <div v-if="showDebugPanel" class="card debug-panel">
        <div class="debug-header">
          <h4>🐛 Panel de Debug</h4>
          <button @click="toggleDebugPanel" class="btn-sm">{{ showDebugDetails ? 'Ocultar' : 'Mostrar' }}</button>
        </div>
        
        <div v-if="showDebugDetails" class="debug-content">
          <div class="debug-section">
            <h5>Estado del Sistema</h5>
            <pre>{{ debugInfo }}</pre>
          </div>
          
          <div class="debug-actions">
            <button @click="testDocumentConnection" class="btn-sm btn-outline">🔧 Test Conexión</button>
            <button @click="debugLastDocument" class="btn-sm btn-outline">🔍 Debug Último Doc</button>
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
  currentDocument,
  isLoading,
  isUploading,
  isSearching,
  uploadProgress,
  hasDocuments,
  documentsCount,
  hasSearchResults,
  canUpload,
  uploadDocument,
  loadDocuments,
  searchDocuments,
  viewDocument,
  deleteDocument,
  setupFileUploadHandlers,
  formatFileSize
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

// 🆕 ESTADO PARA MANEJO DE ERRORES
const systemError = ref(null)
const lastFailedAction = ref(null)
const showDebugPanel = ref(import.meta.env.DEV) // Solo en desarrollo
const showDebugDetails = ref(false)

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

const debugInfo = computed(() => {
  return {
    currentCompanyId: appStore.currentCompanyId,
    documentsCount: documentsCount.value,
    searchResultsCount: searchResults.value.length,
    lastDocument: documents.value[0]?.id || 'none',
    isLoading: isLoading.value,
    canUpload: canUpload.value,
    systemError: systemError.value
  }
})

// ============================================================================
// 🔧 MÉTODOS MEJORADOS CON MANEJO DE ERRORES
// ============================================================================

/**
 * Maneja la subida de documento con mejor manejo de errores
 */
const handleUpload = async () => {
  try {
    clearError()
    lastFailedAction.value = 'upload'
    
    if (!canUploadDocument.value) {
      throw new Error('Complete todos los campos requeridos')
    }
    
    // Actualizar los inputs del DOM para mantener compatibilidad
    await updateDOMInputs()
    
    const success = await uploadDocument()
    
    if (success) {
      // Limpiar formulario
      clearUploadForm()
      
      // Recargar lista de documentos
      await loadDocuments()
      
      lastFailedAction.value = null
    } else {
      throw new Error('Error en el proceso de subida')
    }
    
  } catch (error) {
    handleError('Error subiendo documento', error)
  }
}

/**
 * Maneja la carga de documentos con retry automático
 */
const handleLoadDocuments = async (retryCount = 0) => {
  try {
    clearError()
    lastFailedAction.value = 'load'
    
    await loadDocuments()
    lastFailedAction.value = null
    
  } catch (error) {
    if (retryCount < 2) {
      console.log(`Reintentando carga de documentos (${retryCount + 1}/3)`)
      setTimeout(() => handleLoadDocuments(retryCount + 1), 1000)
    } else {
      handleError('Error cargando documentos', error)
    }
  }
}

/**
 * Maneja la búsqueda con validación mejorada
 */
const handleSearch = async () => {
  try {
    clearError()
    lastFailedAction.value = 'search'
    
    if (!searchQuery.value.trim()) {
      throw new Error('Ingresa un término de búsqueda')
    }
    
    // Update DOM input for compatibility
    const searchInput = document.getElementById('searchQuery')
    if (searchInput) {
      searchInput.value = searchQuery.value
    }
    
    searchPerformed.value = true
    await searchDocuments(searchQuery.value)
    lastFailedAction.value = null
    
  } catch (error) {
    handleError('Error en búsqueda', error)
  }
}

/**
 * 🔧 CRÍTICO: Maneja visualización de documento con validación robusta
 */
const handleViewDocument = async (documentId) => {
  try {
    clearError()
    lastFailedAction.value = { action: 'view', documentId }
    
    // 🆕 VALIDACIÓN Y LOGGING MEJORADO
    console.log('🔍 [VIEW] Iniciando visualización:', {
      originalId: documentId,
      type: typeof documentId,
      companyId: appStore.currentCompanyId
    })
    
    if (!documentId) {
      throw new Error('ID de documento no válido')
    }
    
    if (!appStore.currentCompanyId) {
      throw new Error('No hay empresa seleccionada')
    }
    
    // Limpiar y validar ID
    const cleanId = String(documentId).trim()
    
    if (!cleanId) {
      throw new Error('ID de documento vacío después de limpieza')
    }
    
    console.log('🔍 [VIEW] Llamando a viewDocument con ID:', cleanId)
    
    // Llamar al composable
    const result = await viewDocument(cleanId)
    
    if (!result) {
      throw new Error('No se pudo obtener el documento')
    }
    
    console.log('✅ [VIEW] Documento obtenido exitosamente:', result.title)
    lastFailedAction.value = null
    
  } catch (error) {
    console.error('❌ [VIEW] Error en handleViewDocument:', error)
    handleError(`Error visualizando documento (ID: ${documentId})`, error)
  }
}

/**
 * Maneja eliminación de documento con confirmación
 */
const handleDeleteDocument = async (documentId) => {
  try {
    clearError()
    lastFailedAction.value = { action: 'delete', documentId }
    
    if (!documentId) {
      throw new Error('ID de documento no válido')
    }
    
    const cleanId = String(documentId).trim()
    
    const success = await deleteDocument(cleanId)
    
    if (success) {
      lastFailedAction.value = null
      // Recargar documentos para sincronizar
      await loadDocuments()
    } else {
      throw new Error('No se pudo eliminar el documento')
    }
    
  } catch (error) {
    handleError(`Error eliminando documento (ID: ${documentId})`, error)
  }
}

// ============================================================================
// MÉTODOS DE UTILIDAD MEJORADOS
// ============================================================================

/**
 * Actualiza inputs del DOM para compatibilidad
 */
const updateDOMInputs = async () => {
  await nextTick()
  
  const titleInput = document.getElementById('documentTitle')
  const contentInput = document.getElementById('documentContent')
  const fileInput = document.getElementById('documentFile')
  
  if (titleInput) titleInput.value = documentTitle.value
  if (contentInput) contentInput.value = documentContent.value
  if (fileInput && selectedFile.value) {
    const dataTransfer = new DataTransfer()
    dataTransfer.items.add(selectedFile.value)
    fileInput.files = dataTransfer.files
  }
}

/**
 * Limpia el formulario de upload
 */
const clearUploadForm = () => {
  documentTitle.value = ''
  documentContent.value = ''
  selectedFile.value = null
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

/**
 * Limpia resultados de búsqueda
 */
const clearSearchResults = () => {
  searchResults.value = []
  searchPerformed.value = false
  searchQuery.value = ''
}

/**
 * 🆕 MANEJO CENTRALIZADO DE ERRORES
 */
const handleError = (message, error) => {
  const errorMessage = error?.message || error || 'Error desconocido'
  systemError.value = `${message}: ${errorMessage}`
  
  showNotification(`❌ ${message}`, 'error')
  appStore.addToLog(`${message}: ${errorMessage}`, 'error')
  
  console.error('System Error:', { message, error, lastFailedAction: lastFailedAction.value })
}

/**
 * Limpia errores del sistema
 */
const clearError = () => {
  systemError.value = null
}

/**
 * Reintenta la última acción fallida
 */
const handleRetryLastAction = async () => {
  if (!lastFailedAction.value) return
  
  try {
    clearError()
    
    if (typeof lastFailedAction.value === 'string') {
      switch (lastFailedAction.value) {
        case 'upload':
          await handleUpload()
          break
        case 'load':
          await handleLoadDocuments()
          break
        case 'search':
          await handleSearch()
          break
      }
    } else if (typeof lastFailedAction.value === 'object') {
      const { action, documentId } = lastFailedAction.value
      
      switch (action) {
        case 'view':
          await handleViewDocument(documentId)
          break
        case 'delete':
          await handleDeleteDocument(documentId)
          break
      }
    }
  } catch (error) {
    handleError('Error en reintento', error)
  }
}

// ============================================================================
// MÉTODOS DE DEBUG
// ============================================================================

const toggleDebugPanel = () => {
  showDebugDetails.value = !showDebugDetails.value
}

const testDocumentConnection = async () => {
  try {
    console.log('🔧 Testing document system connection...')
    
    // Test básico de conexión
    await loadDocuments()
    
    showNotification('✅ Conexión exitosa', 'success')
    
  } catch (error) {
    showNotification('❌ Error en conexión', 'error')
    console.error('Connection test failed:', error)
  }
}

const debugLastDocument = async () => {
  if (!documents.value.length) {
    showNotification('⚠️ No hay documentos para debuggear', 'warning')
    return
  }
  
  const lastDoc = documents.value[0]
  console.log('🐛 Debug info for last document:', lastDoc)
  
  try {
    // Test endpoint de debug si existe
    const response = await fetch(`/api/documents/${lastDoc.id}/debug?company_id=${appStore.currentCompanyId}`)
    const debugData = await response.json()
    
    console.log('🐛 Backend debug data:', debugData)
    showNotification('🐛 Debug info en consola', 'info')
    
  } catch (error) {
    console.log('🐛 Debug endpoint not available, showing local info:', {
      document: lastDoc,
      companyId: appStore.currentCompanyId,
      hasDocuments: hasDocuments.value
    })
  }
}

// ============================================================================
// MÉTODOS EXISTENTES (FILE UPLOAD, etc.)
// ============================================================================

const triggerFileSelect = () => {
  if (!isUploading.value && fileInputRef.value) {
    fileInputRef.value.click()
  }
}

const handleFileSelect = (event) => {
  const files = event.target.files
  if (files.length > 0) {
    selectedFile.value = files[0]
    showNotification(`📁 Archivo seleccionado: ${files[0].name}`, 'info', 2000)
  }
}

const clearSelectedFile = () => {
  selectedFile.value = null
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

// Drag & Drop handlers
const handleDragEnter = () => {
  isDragOver.value = true
}

const handleDragOver = () => {
  isDragOver.value = true
}

const handleDragLeave = (event) => {
  if (!event.currentTarget.contains(event.relatedTarget)) {
    isDragOver.value = false
  }
}

const handleDrop = (event) => {
  isDragOver.value = false
  const files = event.dataTransfer.files
  
  if (files.length > 0) {
    selectedFile.value = files[0]
    
    const dataTransfer = new DataTransfer()
    dataTransfer.items.add(files[0])
    if (fileInputRef.value) {
      fileInputRef.value.files = dataTransfer.files
    }
    
    showNotification(`📁 Archivo seleccionado: ${files[0].name}`, 'info', 2000)
  }
}

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

const focusUploadArea = () => {
  nextTick(() => {
    const titleInput = document.getElementById('documentTitle')
    if (titleInput) {
      titleInput.focus()
    }
  })
}

const highlightCompanySelector = () => {
  window.dispatchEvent(new CustomEvent('highlightCompanySelector'))
}

// Admin functions
const exportDocuments = () => {
  showNotification('📦 Función de exportación en desarrollo', 'info')
}

const importDocuments = () => {
  showNotification('📥 Función de importación en desarrollo', 'info')
}

const runDocumentMaintenance = () => {
  showNotification('🔧 Función de mantenimiento en desarrollo', 'info')
}

// ============================================================================
// LIFECYCLE HOOKS
// ============================================================================

onMounted(async () => {
  appStore.addToLog('DocumentsTab mounted', 'info')
  
  // Setup file upload handlers
  setupFileUploadHandlers()
  
  // Load documents if company is selected
  if (appStore.hasCompanySelected) {
    await handleLoadDocuments()
  }
  
  // Event listener for tab content loading
  window.addEventListener('loadTabContent', handleLoadTabContent)
})

onUnmounted(() => {
  window.removeEventListener('loadTabContent', handleLoadTabContent)
})

// Handle load tab content event
const handleLoadTabContent = (event) => {
  if (event.detail.tabName === 'documents' && props.isActive) {
    handleLoadDocuments()
  }
}

// Watch for company changes
watch(() => appStore.currentCompanyId, (newCompanyId) => {
  if (newCompanyId && props.isActive) {
    handleLoadDocuments()
  }
})
</script>

<style scoped>
/* Estilos existentes + nuevos para error handling */

.error-banner {
  background: #fee2e2;
  border: 1px solid #fca5a5;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 20px;
  color: #991b1b;
}

.error-content h4 {
  margin: 0 0 8px 0;
  color: #dc2626;
}

.error-actions {
  display: flex;
  gap: 10px;
  margin-top: 12px;
}

.debug-panel {
  background: #f3f4f6;
  border: 2px dashed #9ca3af;
}

.debug-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.debug-content pre {
  background: #1f2937;
  color: #e5e7eb;
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 0.8em;
}

.debug-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

/* Resto de estilos existentes... */
.tab-content {
  display: none;
}

.tab-content.active {
  display: block;
}

/* [Incluir todos los estilos existentes del archivo original] */
</style>
