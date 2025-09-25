// composables/useDocuments.js - VUE.JS COMPATIBLE VERSION
// FIX: Elimina manipulación directa del DOM para ser compatible con Vue

import { ref, computed, watch, nextTick } from 'vue'
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
  
  // 🔧 COMPATIBLE CON VUE: Estado del modal sin manipular DOM
  const isModalOpen = ref(false)
  const modalDocument = ref(null)
  const modalError = ref(null)
  const modalLoading = ref(false)
  
  // 🔧 NUEVO: Estado para mostrar el modal en el componente
  const showModal = ref(false)
  const modalConfig = ref({
    title: '',
    content: '',
    documentData: null
  })
  
  // ============================================================================
  // WATCHERS PARA AUTO-CERRAR - COMPATIBLE CON VUE
  // ============================================================================
  
  // Watch para cambios de empresa
  watch(() => appStore.currentCompanyId, (newCompanyId, oldCompanyId) => {
    if (oldCompanyId && newCompanyId !== oldCompanyId) {
      console.log('[DOCUMENTS] Company changed, closing modals')
      closeModal()
      searchResults.value = []
    }
  })
  
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
  // MÉTODOS PRINCIPALES
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
        requestData = createFormData({
          title,
          file,
          content: content || '',
          company_id: appStore.currentCompanyId
        })
        options.headers = {}
      } else {
        requestData = {
          title,
          content: content || '',
          company_id: appStore.currentCompanyId
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
          'X-Company-ID': appStore.currentCompanyId,
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
   * Carga la lista de documentos
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
          'X-Company-ID': appStore.currentCompanyId
        }
      })
      
      // Normalizar respuesta
      const documentsList = Array.isArray(response) ? response : 
                          response.documents ? response.documents :
                          response.data ? response.data : []
      
      // Verificar que todos los documentos pertenecen a la empresa correcta
      const filteredDocuments = documentsList.filter(doc => {
        const docCompany = doc.company_id || doc.metadata?.company_id || 
                          (doc.id?.includes('_') ? doc.id.split('_')[0] : null)
        return docCompany === appStore.currentCompanyId
      })
      
      // Normalizar IDs de documentos
      documents.value = filteredDocuments.map(doc => ({
        ...doc,
        id: doc.id || doc._id || doc.doc_id || Date.now(),
        title: doc.title || doc.name || 'Sin título',
        content: doc.content || doc.text || '',
        created_at: doc.created_at || doc.createdAt || new Date().toISOString(),
        type: doc.type || doc.file_type || 'text',
        company_id: appStore.currentCompanyId,
        _id: doc.id || doc._id || doc.doc_id
      }))
      
      appStore.addToLog(`[${appStore.currentCompanyId}] Loaded ${documents.value.length} documents`, 'info')
      
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
   */
  const searchDocuments = async (query = null) => {
    if (!appStore.currentCompanyId) {
      showNotification('⚠️ Por favor selecciona una empresa primero', 'warning')
      return []
    }
    
    // 🔧 VUE COMPATIBLE: Cerrar modal reactivamente
    closeModal()
    
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
          'X-Company-ID': appStore.currentCompanyId
        }
      })
      
      // Normalizar respuesta de búsqueda
      const results = Array.isArray(response) ? response :
                     response.results ? response.results :
                     response.data ? response.data : []
      
      // Verificar que todos los resultados pertenecen a la empresa correcta
      const filteredResults = results.filter(result => {
        const docCompany = result.company_id || result.metadata?.company_id || 
                          (result.id?.includes('_') ? result.id.split('_')[0] : null)
        return docCompany === appStore.currentCompanyId
      })
      
      // Normalizar resultados de búsqueda con IDs correctos
      searchResults.value = filteredResults.map(result => ({
        ...result,
        relevance: result.relevance || result.score || 1,
        highlight: result.highlight || result.excerpt || '',
        matched_terms: result.matched_terms || [],
        company_id: appStore.currentCompanyId,
        id: result.id || result._id || result.doc_id,
        _id: result.id || result._id || result.doc_id
      }))
      
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
   * 🔧 VUE COMPATIBLE: Visualiza un documento usando estado reactivo
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
      const cleanDocId = String(docId).trim()
      
      // 🔧 VUE COMPATIBLE: Mostrar loading en el modal
      modalLoading.value = true
      modalError.value = null
      openModal() // Abrir modal primero
      
      appStore.addToLog(`[${appStore.currentCompanyId}] Viewing document: ${cleanDocId}`, 'info')
      
      const response = await apiRequest(`/api/documents/${cleanDocId}`, {
        headers: {
          'X-Company-ID': appStore.currentCompanyId
        }
      })
      
      // 🔧 VUE COMPATIBLE: Actualizar estado reactivo
      currentDocument.value = response
      modalDocument.value = response
      modalConfig.value = {
        title: response.title || 'Sin título',
        content: response.content || 'Sin contenido disponible',
        documentData: response
      }
      
      appStore.addToLog(`[${appStore.currentCompanyId}] Document viewed: ${response.title}`, 'info')
      
      return response
      
    } catch (error) {
      console.error('Error viewing document:', error)
      modalError.value = error.message
      notifyApiError(`/api/documents/${docId}`, error)
      appStore.addToLog(`Error viewing document ${docId}: ${error.message}`, 'error')
      return null
      
    } finally {
      modalLoading.value = false
    }
  }
  
  /**
   * Elimina un documento
   */
  const deleteDocument = async (docId) => {
    if (!docId) {
      showNotification('❌ ID de documento no válido', 'error')
      return false
    }
    
    if (!confirm('¿Estás seguro de que quieres eliminar este documento?')) {
      return false
    }
    
    try {
      const cleanDocId = String(docId).trim()
      
      appStore.addToLog(`[${appStore.currentCompanyId}] Deleting document: ${cleanDocId}`, 'info')
      
      await apiRequest(`/api/documents/${cleanDocId}`, {
        method: 'DELETE',
        headers: {
          'X-Company-ID': appStore.currentCompanyId
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
      
      // 🔧 VUE COMPATIBLE: Cerrar modal reactivamente si es el documento actual
      if (modalDocument.value && (modalDocument.value.id === docId || modalDocument.value._id === docId)) {
        closeModal()
      }
      
      notifyApiSuccess('Documento eliminado')
      appStore.addToLog(`[${appStore.currentCompanyId}] Document deleted successfully: ${cleanDocId}`, 'info')
      
      return true
      
    } catch (error) {
      console.error('Error deleting document:', error)
      notifyApiError(`/api/documents/${docId}`, error)
      appStore.addToLog(`Error deleting document ${docId}: ${error.message}`, 'error')
      return false
    }
  }
  
  // ============================================================================
  // 🔧 MODAL VUE COMPATIBLE - SIN MANIPULACIÓN DE DOM
  // ============================================================================
  
  /**
   * 🔧 VUE COMPATIBLE: Abrir modal usando estado reactivo
   */
  const openModal = () => {
    showModal.value = true
    isModalOpen.value = true
    modalError.value = null
  }
  
  /**
   * 🔧 VUE COMPATIBLE: Cerrar modal usando estado reactivo
   */
  const closeModal = () => {
    showModal.value = false
    isModalOpen.value = false
    modalDocument.value = null
    currentDocument.value = null
    modalError.value = null
    modalLoading.value = false
    modalConfig.value = {
      title: '',
      content: '',
      documentData: null
    }
    
    appStore.addToLog('Document modal closed', 'info')
  }
  
  /**
   * 🔧 VUE COMPATIBLE: Función simple para cerrar cualquier modal
   */
  const forceCloseAllModals = () => {
    console.log('[MODAL-FORCE-CLOSE] Closing all modals (Vue compatible)')
    closeModal()
  }
  
  // ============================================================================
  // MÉTODOS DE UTILIDAD
  // ============================================================================
  
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
  
  const formatFileSize = (bytes) => {
    if (!bytes) return 'Desconocido'
    
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(1024))
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
  }
  
  const formatDate = (dateString) => {
    if (!dateString) return 'Desconocida'
    
    try {
      const date = new Date(dateString)
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
    } catch {
      return 'Fecha inválida'
    }
  }
  
  const escapeHTML = (text) => {
    if (!text) return ''
    
    const div = document.createElement('div')
    div.textContent = text
    return div.innerHTML
  }
  
  // ============================================================================
  // SETUP DE FUNCIONES GLOBALES - SIMPLIFICADO PARA VUE
  // ============================================================================
  
  const setupFileUploadHandlers = () => {
    // 🔧 VUE COMPATIBLE: Solo drag & drop, sin manipulación DOM compleja
    const fileInput = document.getElementById('documentFile')
    const uploadArea = document.querySelector('.file-upload')
    
    if (!fileInput || !uploadArea) return
    
    // Configurar drag and drop BÁSICO
    const events = ['dragenter', 'dragover', 'dragleave', 'drop']
    
    events.forEach(eventName => {
      uploadArea.addEventListener(eventName, (e) => {
        e.preventDefault()
        e.stopPropagation()
      }, false)
    })
    
    uploadArea.addEventListener('dragenter', () => {
      uploadArea.classList.add('drag-over')
    })
    
    uploadArea.addEventListener('dragover', () => {
      uploadArea.classList.add('drag-over')
    })
    
    uploadArea.addEventListener('dragleave', () => {
      uploadArea.classList.remove('drag-over')
    })
    
    uploadArea.addEventListener('drop', (e) => {
      uploadArea.classList.remove('drag-over')
      const files = e.dataTransfer.files
      
      if (files.length > 0) {
        fileInput.files = files
        showNotification(`📁 Archivo seleccionado: ${files[0].name}`, 'info')
      }
    })
    
    // 🔧 VUE COMPATIBLE: Funciones globales simples SIN manipular DOM
    window.handleViewDocument = (docId) => {
      console.log(`[GLOBAL] handleViewDocument called with ID: ${docId}`)
      viewDocument(docId)
    }
    
    window.handleDeleteDocument = (docId) => {
      console.log(`[GLOBAL] handleDeleteDocument called with ID: ${docId}`)
      deleteDocument(docId)
    }
    
    window.closeDocumentModal = () => {
      console.log('[GLOBAL] closeDocumentModal called')
      closeModal()
    }
    
    window.forceCloseAllDocumentModals = forceCloseAllModals
  }
  
  // ============================================================================
  // CLEANUP FUNCTION SIMPLE
  // ============================================================================
  
  const cleanup = () => {
    closeModal()
    
    // Limpiar funciones globales
    if (typeof window !== 'undefined') {
      delete window.handleViewDocument
      delete window.handleDeleteDocument
      delete window.closeDocumentModal
      delete window.forceCloseAllDocumentModals
    }
  }
  
  // ============================================================================
  // RETURN DEL COMPOSABLE - VUE COMPATIBLE
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
    
    // 🔧 VUE COMPATIBLE: Estado del modal reactivo
    isModalOpen,
    modalDocument,
    modalError,
    modalLoading,
    showModal,
    modalConfig,
    
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
    
    // 🔧 VUE COMPATIBLE: Métodos del modal reactivos
    openModal,
    closeModal,
    forceCloseAllModals,
    
    // Métodos de utilidad
    setupFileUploadHandlers,
    getFileType,
    formatFileSize,
    formatDate,
    escapeHTML,
    cleanup
  }
}
