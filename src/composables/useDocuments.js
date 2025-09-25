// composables/useDocuments.js - MODAL CORREGIDO COMPLETAMENTE
// FIX: Modal que sí se puede cerrar sin conflictos

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
  
  // 🆕 NUEVO: Estado para el modal
  const isModalOpen = ref(false)
  const modalDocument = ref(null)
  
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
  // MÉTODOS PRINCIPALES - CORREGIDOS
  // ============================================================================
  
  /**
   * Sube un documento al sistema
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
          content: content || '',
          company_id: appStore.currentCompanyId // 🔧 CRÍTICO: Asegurar company_id
        })
        options.headers = {}
      } else {
        // Subir solo contenido de texto
        requestData = {
          title,
          content: content || '',
          company_id: appStore.currentCompanyId // 🔧 CRÍTICO: Asegurar company_id
        }
      }
      
      // Simular progreso de upload
      const progressInterval = setInterval(() => {
        if (uploadProgress.value < 90) {
          uploadProgress.value += Math.random() * 20
        }
      }, 200)
      
      appStore.addToLog(`[${appStore.currentCompanyId}] Uploading document: ${title}`, 'info')
      
      const response = await apiRequest('/api/documents', {
        method: 'POST',
        body: requestData,
        headers: {
          'X-Company-ID': appStore.currentCompanyId, // 🔧 CRÍTICO: Header obligatorio
          ...options.headers
        }
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
      appStore.addToLog(`[${appStore.currentCompanyId}] Document uploaded successfully: ${title}`, 'info')
      
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
   * Carga la lista de documentos - CORREGIDO con header empresa
   */
  const loadDocuments = async () => {
    if (!appStore.currentCompanyId) {
      showNotification('⚠️ Por favor selecciona una empresa primero', 'warning')
      return []
    }
    
    isLoading.value = true
    
    try {
      appStore.addToLog(`[${appStore.currentCompanyId}] Loading documents for company`, 'info')
      
      const response = await apiRequest('/api/documents', {
        method: 'GET',
        headers: {
          'X-Company-ID': appStore.currentCompanyId // 🔧 CRÍTICO: Header obligatorio
        }
      })
      
      // Normalizar respuesta
      const documentsList = Array.isArray(response) ? response : 
                          response.documents ? response.documents :
                          response.data ? response.data : []
      
      // 🆕 MEJORADO: Verificar que todos los documentos pertenecen a la empresa correcta
      const filteredDocuments = documentsList.filter(doc => {
        const docCompany = doc.company_id || doc.metadata?.company_id || 
                          (doc.id?.includes('_') ? doc.id.split('_')[0] : null)
        return docCompany === appStore.currentCompanyId
      })
      
      // Normalizar IDs de documentos
      documents.value = filteredDocuments.map(doc => ({
        ...doc,
        // Asegurar campos requeridos
        id: doc.id || doc._id || doc.doc_id || Date.now(),
        title: doc.title || doc.name || 'Sin título',
        content: doc.content || doc.text || '',
        created_at: doc.created_at || doc.createdAt || new Date().toISOString(),
        type: doc.type || doc.file_type || 'text',
        company_id: appStore.currentCompanyId, // 🔧 ASEGURAR empresa correcta
        // CRÍTICO: Asegurar que el ID tenga formato correcto para el backend
        _id: doc.id || doc._id || doc.doc_id
      }))
      
      appStore.addToLog(`[${appStore.currentCompanyId}] Loaded ${documents.value.length} documents`, 'info')
      
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
   * Busca documentos por query - CORREGIDO con header empresa
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
      appStore.addToLog(`[${appStore.currentCompanyId}] Searching documents: "${searchQuery}"`, 'info')
      
      const response = await apiRequest('/api/documents/search', {
        method: 'POST',
        body: { query: searchQuery },
        headers: {
          'X-Company-ID': appStore.currentCompanyId // 🔧 CRÍTICO: Header obligatorio
        }
      })
      
      // Normalizar respuesta de búsqueda
      const results = Array.isArray(response) ? response :
                     response.results ? response.results :
                     response.data ? response.data : []
      
      // 🆕 MEJORADO: Verificar que todos los resultados pertenecen a la empresa correcta
      const filteredResults = results.filter(result => {
        const docCompany = result.company_id || result.metadata?.company_id || 
                          (result.id?.includes('_') ? result.id.split('_')[0] : null)
        return docCompany === appStore.currentCompanyId
      })
      
      // Normalizar resultados de búsqueda con IDs correctos
      searchResults.value = filteredResults.map(result => ({
        ...result,
        // Campos adicionales para resultados de búsqueda
        relevance: result.relevance || result.score || 1,
        highlight: result.highlight || result.excerpt || '',
        matched_terms: result.matched_terms || [],
        company_id: appStore.currentCompanyId, // 🔧 ASEGURAR empresa correcta
        // CRÍTICO: Asegurar ID correcto
        id: result.id || result._id || result.doc_id,
        _id: result.id || result._id || result.doc_id
      }))
      
      // Mostrar resultados - MANTENER para compatibilidad
      displaySearchResults(searchResults.value)
      
      const message = searchResults.value.length > 0 
        ? `✅ [${appStore.currentCompanyId}] Encontrados ${searchResults.value.length} documentos`
        : `❌ [${appStore.currentCompanyId}] No se encontraron documentos`
      
      showNotification(message, searchResults.value.length > 0 ? 'success' : 'info')
      appStore.addToLog(`[${appStore.currentCompanyId}] Search completed: ${searchResults.value.length} results`, 'info')
      
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
   * 🔧 CORREGIDO COMPLETAMENTE: Visualiza un documento específico con modal funcional
   */
  const viewDocument = async (docId) => {
    if (!docId) {
      showNotification('❌ ID de documento no válido', 'error')
      return null
    }
    
    if (!appStore.currentCompanyId) {
      showNotification('❌ No hay empresa seleccionada', 'error')
      return null
    }
    
    try {
      // Limpiar y validar docId
      const cleanDocId = String(docId).trim()
      
      appStore.addToLog(`[${appStore.currentCompanyId}] Viewing document: ${cleanDocId}`, 'info')
      
      const response = await apiRequest(`/api/documents/${cleanDocId}`, {
        headers: {
          'X-Company-ID': appStore.currentCompanyId // 🔧 CRÍTICO: Header obligatorio
        }
      })
      
      currentDocument.value = response
      modalDocument.value = response
      
      // 🔧 CORREGIDO COMPLETAMENTE: Modal que SÍ se puede cerrar
      showDocumentModalV2(response)
      
      appStore.addToLog(`[${appStore.currentCompanyId}] Document viewed: ${response.title}`, 'info')
      
      return response
      
    } catch (error) {
      console.error('Error viewing document:', error)
      notifyApiError(`/api/documents/${docId}`, error)
      appStore.addToLog(`Error viewing document ${docId}: ${error.message}`, 'error')
      return null
    }
  }
  
  /**
   * Elimina un documento - CORREGIDO con header empresa
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
      // Limpiar docId
      const cleanDocId = String(docId).trim()
      
      appStore.addToLog(`[${appStore.currentCompanyId}] Deleting document: ${cleanDocId}`, 'info')
      
      await apiRequest(`/api/documents/${cleanDocId}`, {
        method: 'DELETE',
        headers: {
          'X-Company-ID': appStore.currentCompanyId // 🔧 CRÍTICO: Header obligatorio
        }
      })
      
      // Remover de la lista local
      documents.value = documents.value.filter(doc => 
        doc.id !== docId && doc._id !== docId && doc.doc_id !== docId
      )
      
      // Remover de resultados de búsqueda si está presente
      searchResults.value = searchResults.value.filter(doc => 
        doc.id !== docId && doc._id !== docId && doc.doc_id !== docId
      )
      
      // Cerrar modal si el documento eliminado es el que se está mostrando
      if (modalDocument.value && (modalDocument.value.id === docId || modalDocument.value._id === docId)) {
        closeModal()
      }
      
      notifyApiSuccess('Documento eliminado')
      appStore.addToLog(`[${appStore.currentCompanyId}] Document deleted successfully: ${cleanDocId}`, 'info')
      
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
  // 🔧 MODAL COMPLETAMENTE CORREGIDO - V2
  // ============================================================================
  
  /**
   * 🔧 NUEVA VERSIÓN: Modal que SÍ se puede cerrar sin conflictos
   */
  const showDocumentModalV2 = (documentData) => {
    // Cerrar modal existente primero
    closeModal()
    
    // Crear modal único con ID específico
    const modalId = 'documentModal_' + Date.now()
    isModalOpen.value = true
    modalDocument.value = documentData
    
    const modalHTML = `
      <div id="${modalId}" class="modal-overlay document-modal" style="display: block; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); z-index: 10000;">
        <div class="modal-content" style="background: white; margin: 50px auto; padding: 20px; width: 80%; max-width: 800px; border-radius: 8px; max-height: 80vh; overflow-y: auto;">
          <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 15px;">
            <h3 style="margin: 0; color: #333;">📄 ${escapeHTML(documentData.title || 'Sin título')}</h3>
            <button id="closeBtn_${modalId}" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #666; padding: 0; line-height: 1;">✕</button>
          </div>
          <div class="modal-body">
            <div class="document-meta" style="margin-bottom: 20px; padding: 15px; background: #f9f9f9; border-radius: 4px;">
              <p style="margin: 5px 0;"><strong>Empresa:</strong> ${escapeHTML(appStore.currentCompanyId)}</p>
              <p style="margin: 5px 0;"><strong>Creado:</strong> ${formatDate(documentData.created_at)}</p>
              ${documentData.type ? `<p style="margin: 5px 0;"><strong>Tipo:</strong> ${escapeHTML(documentData.type)}</p>` : ''}
              ${documentData.size ? `<p style="margin: 5px 0;"><strong>Tamaño:</strong> ${formatFileSize(documentData.size)}</p>` : ''}
            </div>
            <div class="document-content">
              <h4 style="color: #333; margin-bottom: 10px;">Contenido:</h4>
              <div style="max-height: 400px; overflow-y: auto; border: 1px solid #ddd; padding: 15px; background: #fafafa; font-family: monospace; white-space: pre-wrap; word-wrap: break-word;">${escapeHTML(documentData.content || 'Sin contenido disponible')}</div>
            </div>
          </div>
          <div class="modal-footer" style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #eee; display: flex; gap: 10px; justify-content: flex-end;">
            <button id="closeBtn2_${modalId}" style="padding: 8px 16px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer;">Cerrar</button>
            <button id="deleteBtn_${modalId}" style="padding: 8px 16px; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer;">🗑️ Eliminar</button>
          </div>
        </div>
      </div>
    `
    
    // Insertar modal en el DOM
    document.body.insertAdjacentHTML('beforeend', modalHTML)
    
    // Obtener referencias a elementos
    const modal = document.getElementById(modalId)
    const closeBtn = document.getElementById(`closeBtn_${modalId}`)
    const closeBtn2 = document.getElementById(`closeBtn2_${modalId}`)
    const deleteBtn = document.getElementById(`deleteBtn_${modalId}`)
    
    // 🔧 CRÍTICO: Funciones de evento que SÍ funcionan
    const handleClose = () => {
      if (modal && modal.parentNode) {
        modal.parentNode.removeChild(modal)
      }
      isModalOpen.value = false
      modalDocument.value = null
    }
    
    const handleDelete = async () => {
      if (confirm(`¿Estás seguro de que quieres eliminar "${documentData.title}"?`)) {
        handleClose() // Cerrar primero
        await deleteDocument(documentData.id || documentData._id)
      }
    }
    
    const handleOverlayClick = (event) => {
      if (event.target === modal) {
        handleClose()
      }
    }
    
    const handleEscapeKey = (event) => {
      if (event.key === 'Escape') {
        handleClose()
      }
    }
    
    // 🔧 CRÍTICO: Asignar eventos correctamente
    if (closeBtn) closeBtn.addEventListener('click', handleClose)
    if (closeBtn2) closeBtn2.addEventListener('click', handleClose)
    if (deleteBtn) deleteBtn.addEventListener('click', handleDelete)
    if (modal) modal.addEventListener('click', handleOverlayClick)
    
    // Escape key
    document.addEventListener('keydown', handleEscapeKey)
    
    // Cleanup function cuando se cierre el modal
    const originalClose = handleClose
    const enhancedClose = () => {
      document.removeEventListener('keydown', handleEscapeKey)
      originalClose()
    }
    
    // Reemplazar todas las referencias de close con la versión mejorada
    if (closeBtn) {
      closeBtn.removeEventListener('click', handleClose)
      closeBtn.addEventListener('click', enhancedClose)
    }
    if (closeBtn2) {
      closeBtn2.removeEventListener('click', handleClose)
      closeBtn2.addEventListener('click', enhancedClose)
    }
    
    // Reemplazar overlay click
    if (modal) {
      modal.removeEventListener('click', handleOverlayClick)
      modal.addEventListener('click', (event) => {
        if (event.target === modal) {
          enhancedClose()
        }
      })
    }
    
    appStore.addToLog(`[${appStore.currentCompanyId}] Document modal opened: ${documentData.title}`, 'info')
  }
  
  /**
   * 🔧 FUNCIÓN DE CERRAR MODAL MEJORADA
   */
  const closeModal = () => {
    // Buscar y remover cualquier modal existente
    const existingModals = document.querySelectorAll('.document-modal, [id^="documentModal_"]')
    existingModals.forEach(modal => {
      if (modal && modal.parentNode) {
        modal.parentNode.removeChild(modal)
      }
    })
    
    // Resetear estado
    isModalOpen.value = false
    modalDocument.value = null
    currentDocument.value = null
    
    appStore.addToLog('Document modal closed', 'info')
  }
  
  // ============================================================================
  // MÉTODOS DE UTILIDAD - MEJORADOS
  // ============================================================================
  
  /**
   * Muestra los resultados de búsqueda en el DOM
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
        <h4>📋 Resultados de búsqueda (${results.length}) - ${appStore.currentCompanyId}</h4>
      </div>
      <div class="results-list">
        ${results.map(doc => `
          <div class="result-item" data-doc-id="${doc.id || doc._id}">
            <div class="result-header">
              <h5 class="result-title">${escapeHTML(doc.title)}</h5>
              <div class="result-actions">
                <button onclick="window.handleViewDocument('${doc.id || doc._id}')" class="btn-sm btn-primary">
                  👁️ Ver
                </button>
                <button onclick="window.handleDeleteDocument('${doc.id || doc._id}')" class="btn-sm btn-danger">
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
              <span class="result-company">🏢 ${doc.company_id || appStore.currentCompanyId}</span>
            </div>
          </div>
        `).join('')}
      </div>
    `
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
   */
  const escapeHTML = (text) => {
    if (!text) return ''
    
    const div = document.createElement('div')
    div.textContent = text
    return div.innerHTML
  }
  
  // ============================================================================
  // SETUP DE FUNCIONES GLOBALES PARA COMPATIBILIDAD - CORREGIDO
  // ============================================================================
  
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
    
    // 🔧 CORREGIDO: Funciones globales que usan el composable correctamente
    window.handleViewDocument = (docId) => {
      console.log(`[GLOBAL] handleViewDocument called with ID: ${docId}`)
      viewDocument(docId)
    }
    
    window.handleDeleteDocument = (docId) => {
      console.log(`[GLOBAL] handleDeleteDocument called with ID: ${docId}`)
      deleteDocument(docId)
    }
    
    // 🔧 NUEVO: Función global para cerrar modal
    window.closeDocumentModal = () => {
      console.log('[GLOBAL] closeDocumentModal called')
      closeModal()
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
    
    // 🆕 NUEVO: Estado del modal
    isModalOpen,
    modalDocument,
    
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
    
    // 🆕 NUEVO: Métodos del modal
    closeModal,
    
    // Métodos de utilidad
    displaySearchResults,
    setupFileUploadHandlers,
    getFileType,
    formatFileSize,
    formatDate,
    escapeHTML
  }
}
