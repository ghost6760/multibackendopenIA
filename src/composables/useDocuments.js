// composables/useDocuments.js
// Composable para gestión de documentos - MIGRACIÓN desde script.js
// CRÍTICO: Mantener comportamiento idéntico para preservar compatibilidad

import { ref, computed } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'

export const useDocuments = () => {
  const appStore = useAppStore()
  const { apiRequest, createFormData } = useApiRequest()
  const { showNotification, notifyApiError, notifyApiSuccess } = useNotifications()
  
  // ============================================================================
  // ESTADO LOCAL
  // ============================================================================
  
  const documents = ref([])
  const searchResults = ref([])
  const isLoading = ref(false)
  const isUploading = ref(false)
  const isSearching = ref(false)
  const currentDocument = ref(null)
  const uploadProgress = ref(0)
  
  // ============================================================================
  // COMPUTED PROPERTIES
  // ============================================================================
  
  const hasDocuments = computed(() => documents.value.length > 0)
  
  const documentsCount = computed(() => documents.value.length)
  
  const hasSearchResults = computed(() => searchResults.value.length > 0)
  
  const canUpload = computed(() => {
    return appStore.hasCompanySelected && !isUploading.value
  })
  
  // ============================================================================
  // MÉTODOS PRINCIPALES - MIGRADOS DESDE SCRIPT.JS
  // ============================================================================
  
  /**
   * Sube un documento al sistema
   * MIGRADO: uploadDocument() de script.js
   * ⚠️ NO MODIFICAR: Debe mantener comportamiento idéntico
   */
  const uploadDocument = async () => {
    if (!appStore.currentCompanyId) {
      showNotification('⚠️ Por favor selecciona una empresa primero', 'warning')
      return false
    }
    
    const titleInput = document.getElementById('documentTitle')
    const contentInput = document.getElementById('documentContent')
    const fileInput = document.getElementById('documentFile')
    
    if (!titleInput || (!contentInput?.value && !fileInput?.files?.length)) {
      showNotification('❌ Por favor proporciona un título y contenido o archivo', 'error')
      return false
    }
    
    const title = titleInput.value.trim()
    const content = contentInput?.value?.trim()
    const file = fileInput?.files?.[0]
    
    if (!title) {
      showNotification('❌ El título del documento es requerido', 'error')
      return false
    }
    
    isUploading.value = true
    uploadProgress.value = 0
    
    try {
      let requestData
      let options = {}
      
      if (file) {
        // Subir archivo
        requestData = createFormData({
          title,
          file,
          content: content || ''
        })
        
        // Para archivos, no enviar Content-Type (FormData lo maneja)
        options.headers = {}
        
      } else {
        // Subir solo contenido de texto
        requestData = {
          title,
          content: content || ''
        }
      }
      
      // Simular progreso de upload
      const progressInterval = setInterval(() => {
        if (uploadProgress.value < 90) {
          uploadProgress.value += Math.random() * 20
        }
      }, 200)
      
      appStore.addToLog(`Uploading document: ${title}`, 'info')
      
      const response = await apiRequest('/api/documents', {
        method: 'POST',
        body: requestData,
        ...options
      })
      
      clearInterval(progressInterval)
      uploadProgress.value = 100
      
      // Limpiar formulario
      titleInput.value = ''
      if (contentInput) contentInput.value = ''
      if (fileInput) fileInput.value = ''
      
      // Actualizar lista de documentos
      await loadDocuments()
      
      notifyApiSuccess('Documento subido')
      appStore.addToLog(`Document uploaded successfully: ${title}`, 'info')
      
      return response
      
    } catch (error) {
      console.error('Error uploading document:', error)
      notifyApiError('/api/documents', error)
      appStore.addToLog(`Document upload error: ${error.message}`, 'error')
      return false
      
    } finally {
      isUploading.value = false
      uploadProgress.value = 0
    }
  }
  
  /**
   * Carga la lista de documentos
   * MIGRADO: loadDocuments() de script.js
   */
  const loadDocuments = async () => {
    if (!appStore.currentCompanyId) {
      showNotification('⚠️ Por favor selecciona una empresa primero', 'warning')
      return []
    }
    
    isLoading.value = true
    
    try {
      appStore.addToLog(`Loading documents for company: ${appStore.currentCompanyId}`, 'info')
      
      const response = await apiRequest('/api/documents')
      
      // Normalizar respuesta
      const documentsList = Array.isArray(response) ? response : 
                          response.documents ? response.documents :
                          response.data ? response.data : []
      
      documents.value = documentsList.map(doc => ({
        ...doc,
        // Asegurar campos requeridos
        id: doc.id || doc._id || Date.now(),
        title: doc.title || doc.name || 'Sin título',
        content: doc.content || doc.text || '',
        created_at: doc.created_at || doc.createdAt || new Date().toISOString(),
        type: doc.type || doc.file_type || 'text'
      }))
      
      appStore.addToLog(`Loaded ${documents.value.length} documents`, 'info')
      
      // Actualizar contador en el tab
      window.dispatchEvent(new CustomEvent('updateTabNotificationCount', {
        detail: { tabName: 'documents', count: documents.value.length }
      }))
      
      return documents.value
      
    } catch (error) {
      console.error('Error loading documents:', error)
      notifyApiError('/api/documents', error)
      appStore.addToLog(`Error loading documents: ${error.message}`, 'error')
      documents.value = []
      return []
      
    } finally {
      isLoading.value = false
    }
  }
  
  /**
   * Busca documentos por query
   * MIGRADO: searchDocuments() de script.js
   */
  const searchDocuments = async (query = null) => {
    if (!appStore.currentCompanyId) {
      showNotification('⚠️ Por favor selecciona una empresa primero', 'warning')
      return []
    }
    
    // Obtener query del input si no se proporciona
    const searchQuery = query || document.getElementById('searchQuery')?.value?.trim()
    
    if (!searchQuery) {
      showNotification('❌ Por favor ingresa un término de búsqueda', 'error')
      return []
    }
    
    isSearching.value = true
    
    try {
      appStore.addToLog(`Searching documents: "${searchQuery}"`, 'info')
      
      const response = await apiRequest('/api/documents/search', {
        method: 'POST',
        body: { query: searchQuery }
      })
      
      // Normalizar respuesta de búsqueda
      const results = Array.isArray(response) ? response :
                     response.results ? response.results :
                     response.data ? response.data : []
      
      searchResults.value = results.map(result => ({
        ...result,
        // Campos adicionales para resultados de búsqueda
        relevance: result.relevance || result.score || 1,
        highlight: result.highlight || result.excerpt || '',
        matched_terms: result.matched_terms || []
      }))
      
      // Mostrar resultados
      displaySearchResults(searchResults.value)
      
      const message = searchResults.value.length > 0 
        ? `✅ Encontrados ${searchResults.value.length} documentos`
        : '❌ No se encontraron documentos'
      
      showNotification(message, searchResults.value.length > 0 ? 'success' : 'info')
      appStore.addToLog(`Search completed: ${searchResults.value.length} results`, 'info')
      
      return searchResults.value
      
    } catch (error) {
      console.error('Error searching documents:', error)
      notifyApiError('/api/documents/search', error)
      appStore.addToLog(`Document search error: ${error.message}`, 'error')
      searchResults.value = []
      return []
      
    } finally {
      isSearching.value = false
    }
  }
  
  /**
   * Visualiza un documento específico
   * MIGRADO: viewDocument() de script.js
   */
  const viewDocument = async (docId) => {
    if (!docId) {
      showNotification('❌ ID de documento no válido', 'error')
      return null
    }
    
    try {
      appStore.addToLog(`Viewing document: ${docId}`, 'info')
      
      const response = await apiRequest(`/api/documents/${docId}`)
      
      currentDocument.value = response
      
      // Mostrar modal con el documento
      showDocumentModal(response)
      
      appStore.addToLog(`Document viewed: ${response.title}`, 'info')
      
      return response
      
    } catch (error) {
      console.error('Error viewing document:', error)
      notifyApiError(`/api/documents/${docId}`, error)
      appStore.addToLog(`Error viewing document ${docId}: ${error.message}`, 'error')
      return null
    }
  }
  
  /**
   * Elimina un documento
   * MIGRADO: deleteDocument() de script.js
   */
  const deleteDocument = async (docId) => {
    if (!docId) {
      showNotification('❌ ID de documento no válido', 'error')
      return false
    }
    
    // Confirmar eliminación
    if (!confirm('¿Estás seguro de que quieres eliminar este documento?')) {
      return false
    }
    
    try {
      appStore.addToLog(`Deleting document: ${docId}`, 'info')
      
      await apiRequest(`/api/documents/${docId}`, {
        method: 'DELETE'
      })
      
      // Remover de la lista local
      documents.value = documents.value.filter(doc => 
        doc.id !== docId && doc._id !== docId
      )
      
      // Remover de resultados de búsqueda si está presente
      searchResults.value = searchResults.value.filter(doc => 
        doc.id !== docId && doc._id !== docId
      )
      
      notifyApiSuccess('Documento eliminado')
      appStore.addToLog(`Document deleted successfully: ${docId}`, 'info')
      
      // Actualizar contador en el tab
      window.dispatchEvent(new CustomEvent('updateTabNotificationCount', {
        detail: { tabName: 'documents', count: documents.value.length }
      }))
      
      return true
      
    } catch (error) {
      console.error('Error deleting document:', error)
      notifyApiError(`/api/documents/${docId}`, error)
      appStore.addToLog(`Error deleting document ${docId}: ${error.message}`, 'error')
      return false
    }
  }
  
  // ============================================================================
  // MÉTODOS DE UTILIDAD
  // ============================================================================
  
  /**
   * Muestra los resultados de búsqueda en el DOM
   * PRESERVAR: Lógica exacta del script.js original
   */
  const displaySearchResults = (results) => {
    const container = document.getElementById('searchResults')
    if (!container) return
    
    if (results.length === 0) {
      container.innerHTML = `
        <div class="no-results">
          <p>❌ No se encontraron documentos que coincidan con la búsqueda</p>
        </div>
      `
      return
    }
    
    container.innerHTML = `
      <div class="search-results-header">
        <h4>📋 Resultados de búsqueda (${results.length})</h4>
      </div>
      <div class="results-list">
        ${results.map(doc => `
          <div class="result-item" data-doc-id="${doc.id || doc._id}">
            <div class="result-header">
              <h5 class="result-title">${escapeHTML(doc.title)}</h5>
              <div class="result-actions">
                <button onclick="window.viewDocument('${doc.id || doc._id}')" class="btn-sm btn-primary">
                  👁️ Ver
                </button>
                <button onclick="window.deleteDocument('${doc.id || doc._id}')" class="btn-sm btn-danger">
                  🗑️ Eliminar
                </button>
              </div>
            </div>
            <div class="result-content">
              ${doc.highlight ? `<p class="result-excerpt">${escapeHTML(doc.highlight)}</p>` : ''}
              ${doc.content ? `<p class="result-preview">${escapeHTML(doc.content.substring(0, 200))}${doc.content.length > 200 ? '...' : ''}</p>` : ''}
            </div>
            <div class="result-meta">
              <span class="result-date">📅 ${formatDate(doc.created_at)}</span>
              ${doc.type ? `<span class="result-type">📄 ${doc.type}</span>` : ''}
              ${doc.relevance ? `<span class="result-relevance">⭐ ${Math.round(doc.relevance * 100)}%</span>` : ''}
            </div>
          </div>
        `).join('')}
      </div>
    `
  }
  
  /**
   * Muestra el modal de visualización de documento
   */
  const showDocumentModal = (document) => {
    // Remover modal existente si hay uno
    const existingModal = document.querySelector('.document-modal')
    if (existingModal) {
      existingModal.remove()
    }
    
    const modal = document.createElement('div')
    modal.className = 'modal-overlay document-modal'
    modal.innerHTML = `
      <div class="modal-content document-modal-content">
        <div class="modal-header">
          <h3>📄 ${escapeHTML(document.title)}</h3>
          <button onclick="window.closeModal()" class="modal-close">✕</button>
        </div>
        <div class="modal-body">
          <div class="document-meta">
            <p><strong>Creado:</strong> ${formatDate(document.created_at)}</p>
            ${document.type ? `<p><strong>Tipo:</strong> ${document.type}</p>` : ''}
            ${document.size ? `<p><strong>Tamaño:</strong> ${formatFileSize(document.size)}</p>` : ''}
          </div>
          <div class="document-content">
            <h4>Contenido:</h4>
            <pre class="document-text">${escapeHTML(document.content || 'Sin contenido disponible')}</pre>
          </div>
        </div>
        <div class="modal-footer">
          <button onclick="window.closeModal()" class="btn-primary">Cerrar</button>
          <button onclick="window.deleteDocument('${document.id || document._id}')" class="btn-danger">
            🗑️ Eliminar
          </button>
        </div>
      </div>
    `
    
    document.body.appendChild(modal)
    modal.onclick = (e) => { if (e.target === modal) window.closeModal() }
  }
  
  /**
   * Obtiene el tipo de archivo desde la extensión
   */
  const getFileType = (filename) => {
    if (!filename) return 'unknown'
    
    const extension = filename.split('.').pop()?.toLowerCase()
    
    const typeMap = {
      'pdf': 'PDF',
      'doc': 'Word',
      'docx': 'Word',
      'txt': 'Texto',
      'md': 'Markdown',
      'json': 'JSON',
      'csv': 'CSV'
    }
    
    return typeMap[extension] || extension?.toUpperCase() || 'Desconocido'
  }
  
  /**
   * Formatea el tamaño del archivo
   */
  const formatFileSize = (bytes) => {
    if (!bytes) return 'Desconocido'
    
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(1024))
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
  }
  
  /**
   * Formatea fecha
   */
  const formatDate = (dateString) => {
    if (!dateString) return 'Desconocida'
    
    try {
      const date = new Date(dateString)
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
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
  // MÉTODOS DE CONFIGURACIÓN DE DRAG & DROP
  // ============================================================================
  
  /**
   * Configura drag and drop para upload de archivos
   */
  const setupFileUploadHandlers = () => {
    const fileInput = document.getElementById('documentFile')
    const uploadArea = document.querySelector('.file-upload')
    
    if (!fileInput || !uploadArea) return
    
    // Configurar drag and drop
    const events = ['dragenter', 'dragover', 'dragleave', 'drop']
    
    events.forEach(eventName => {
      uploadArea.addEventListener(eventName, preventDefaults, false)
    })
    
    function preventDefaults(e) {
      e.preventDefault()
      e.stopPropagation()
    }
    
    uploadArea.addEventListener('dragenter', highlight)
    uploadArea.addEventListener('dragover', highlight)
    uploadArea.addEventListener('dragleave', unhighlight)
    uploadArea.addEventListener('drop', handleDrop)
    
    function highlight() {
      uploadArea.classList.add('drag-over')
    }
    
    function unhighlight() {
      uploadArea.classList.remove('drag-over')
    }
    
    function handleDrop(e) {
      unhighlight()
      const files = e.dataTransfer.files
      
      if (files.length > 0) {
        fileInput.files = files
        showNotification(`📁 Archivo seleccionado: ${files[0].name}`, 'info')
      }
    }
  }
  
  // ============================================================================
  // RETURN DEL COMPOSABLE
  // ============================================================================
  
  return {
    // Estado
    documents,
    searchResults,
    currentDocument,
    isLoading,
    isUploading,
    isSearching,
    uploadProgress,
    
    // Computed
    hasDocuments,
    documentsCount,
    hasSearchResults,
    canUpload,
    
    // Métodos principales
    uploadDocument,
    loadDocuments,
    searchDocuments,
    viewDocument,
    deleteDocument,
    
    // Métodos de utilidad
    displaySearchResults,
    showDocumentModal,
    setupFileUploadHandlers,
    getFileType,
    formatFileSize,
    formatDate,
    escapeHTML
  }
}
