/**
 * useFileUpload.js - Composable para Carga y Gestión de Archivos
 * MIGRADO DE: script.js funciones uploadDocument(), loadDocuments(), searchDocuments(), viewDocument(), deleteDocument(), etc.
 * PRESERVAR: Comportamiento exacto de las funciones originales
 * COMPATIBILIDAD: 100% con el script.js original
 */

import { ref, computed, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'
import { useSystemLog } from '@/composables/useSystemLog'

export const useFileUpload = () => {
  const appStore = useAppStore()
  const { apiRequest } = useApiRequest()
  const { showNotification } = useNotifications()
  const { addToLog } = useSystemLog()

  // ============================================================================
  // ESTADO LOCAL
  // ============================================================================

  const documents = ref([])
  const selectedFile = ref(null)
  const isUploading = ref(false)
  const isLoading = ref(false)
  const isSearching = ref(false)
  const isDeleting = ref(false)
  
  const uploadProgress = ref(0)
  const searchQuery = ref('')
  const searchResults = ref([])
  const documentDetails = ref(null)
  const uploadResults = ref(null)
  
  const supportedFileTypes = ref([
    'application/pdf',
    'text/plain',
    'text/csv',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'image/jpeg',
    'image/png',
    'image/gif',
    'audio/mpeg',
    'audio/wav',
    'video/mp4'
  ])
  
  const maxFileSize = ref(50 * 1024 * 1024) // 50MB
  const lastUpdateTime = ref(null)

  // ============================================================================
  // COMPUTED PROPERTIES
  // ============================================================================

  const documentsCount = computed(() => documents.value.length)

  const hasDocuments = computed(() => documents.value.length > 0)

  const isAnyProcessing = computed(() => 
    isUploading.value || isLoading.value || isSearching.value || isDeleting.value
  )

  const canUpload = computed(() => 
    !isUploading.value && 
    selectedFile.value && 
    appStore.currentCompanyId
  )

  const filteredDocuments = computed(() => {
    if (!searchQuery.value.trim()) return documents.value
    
    const query = searchQuery.value.toLowerCase()
    return documents.value.filter(doc => 
      doc.name?.toLowerCase().includes(query) ||
      doc.filename?.toLowerCase().includes(query) ||
      doc.content?.toLowerCase().includes(query) ||
      doc.document_type?.toLowerCase().includes(query)
    )
  })

  const documentsByType = computed(() => {
    const grouped = {}
    documents.value.forEach(doc => {
      const type = doc.document_type || 'unknown'
      if (!grouped[type]) grouped[type] = []
      grouped[type].push(doc)
    })
    return grouped
  })

  const uploadStats = computed(() => {
    const stats = {
      total: documents.value.length,
      pdf: 0,
      text: 0,
      image: 0,
      audio: 0,
      video: 0,
      other: 0
    }

    documents.value.forEach(doc => {
      const type = doc.document_type || 'other'
      if (stats.hasOwnProperty(type)) {
        stats[type]++
      } else {
        stats.other++
      }
    })

    return stats
  })

  // ============================================================================
  // FUNCIONES PRINCIPALES MIGRADAS DEL SCRIPT.JS
  // ============================================================================

  /**
   * Sube documento - MIGRADO: uploadDocument() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const uploadDocument = async (file = null) => {
    // PRESERVAR: Validación de empresa como script.js
    if (!appStore.currentCompanyId) {
      showNotification('Por favor selecciona una empresa primero', 'warning')
      return false
    }

    // Si no se pasa archivo, obtenerlo del DOM como script.js
    if (!file) {
      const fileInput = document.getElementById('documentFile')
      if (!fileInput || !fileInput.files[0]) {
        showNotification('Por favor selecciona un archivo', 'warning')
        return false
      }
      file = fileInput.files[0]
    }

    if (isUploading.value) {
      showNotification('Ya se está subiendo un archivo', 'warning')
      return false
    }

    try {
      // PRESERVAR: Validaciones como script.js
      if (!validateFile(file)) {
        return false
      }

      isUploading.value = true
      uploadProgress.value = 0
      uploadResults.value = null
      selectedFile.value = file

      addToLog(`Starting document upload: ${file.name}`, 'info')
      showNotification('Subiendo documento...', 'info')

      // PRESERVAR: Crear FormData como script.js
      const formData = new FormData()
      formData.append('file', file)
      formData.append('company_id', appStore.currentCompanyId)

      // PRESERVAR: Obtener campos adicionales del DOM como script.js
      const documentType = document.getElementById('documentType')?.value || 'general'
      const documentDescription = document.getElementById('documentDescription')?.value || ''
      
      if (documentType) formData.append('document_type', documentType)
      if (documentDescription.trim()) formData.append('description', documentDescription.trim())

      uploadProgress.value = 25

      // PRESERVAR: Llamada API exacta como script.js
      const response = await apiRequest('/api/documents', {
        method: 'POST',
        body: formData
      })

      uploadProgress.value = 100
      uploadResults.value = response

      // Agregar a la lista local
      documents.value.unshift(response)

      // PRESERVAR: Mostrar resultado en DOM como script.js
      const container = document.getElementById('uploadResult')
      if (container) {
        container.innerHTML = `
          <div class="result-container result-success">
            <h4>✅ Documento Subido Exitosamente</h4>
            <p><strong>Nombre:</strong> ${response.name || response.filename}</p>
            <p><strong>Tipo:</strong> ${response.document_type || 'N/A'}</p>
            <p><strong>Tamaño:</strong> ${formatFileSize(file.size)}</p>
            <p><strong>ID:</strong> ${response.id}</p>
            <div class="json-container">
              <pre>${JSON.stringify(response, null, 2)}</pre>
            </div>
          </div>
        `
      }

      // PRESERVAR: Limpiar formulario como script.js
      clearUploadForm()

      addToLog(`Document uploaded successfully: ${response.name || response.filename}`, 'success')
      showNotification('Documento subido exitosamente', 'success')

      // Recargar lista de documentos
      await loadDocuments()

      return response

    } catch (error) {
      addToLog(`Document upload failed: ${error.message}`, 'error')
      showNotification(`Error subiendo documento: ${error.message}`, 'error')

      // PRESERVAR: Mostrar error en DOM como script.js
      const container = document.getElementById('uploadResult')
      if (container) {
        container.innerHTML = `
          <div class="result-container result-error">
            <p>❌ Error al subir documento</p>
            <p>${error.message}</p>
          </div>
        `
      }

      return false

    } finally {
      isUploading.value = false
      uploadProgress.value = 0
      selectedFile.value = null
    }
  }

  /**
   * Carga documentos - MIGRADO: loadDocuments() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const loadDocuments = async () => {
    if (!appStore.currentCompanyId) {
      showNotification('Por favor selecciona una empresa primero', 'warning')
      return
    }

    if (isLoading.value) return

    try {
      isLoading.value = true
      addToLog(`Loading documents for company ${appStore.currentCompanyId}`, 'info')

      // PRESERVAR: Llamada API exacta como script.js
      const response = await apiRequest('/api/documents', {
        method: 'GET',
        headers: {
          'X-Company-ID': appStore.currentCompanyId
        }
      })

      if (Array.isArray(response)) {
        documents.value = response
        lastUpdateTime.value = new Date().toISOString()

        // PRESERVAR: Actualizar cache como script.js
        appStore.cache.documents = response
        appStore.cache.lastUpdate.documents = Date.now()

        // PRESERVAR: Actualizar tabla en DOM como script.js
        updateDocumentsTable(response)

        addToLog(`Documents loaded successfully (${response.length} documents)`, 'success')

      } else {
        throw new Error('Invalid response format: expected array of documents')
      }

      return response

    } catch (error) {
      addToLog(`Error loading documents: ${error.message}`, 'error')
      showNotification('Error cargando documentos: ' + error.message, 'error')

      // PRESERVAR: Mostrar error en DOM como script.js
      const container = document.getElementById('documentsResults')
      if (container) {
        container.innerHTML = `
          <div class="result-container result-error">
            <p>❌ Error al cargar documentos</p>
            <p>${error.message}</p>
          </div>
        `
      }

      throw error

    } finally {
      isLoading.value = false
    }
  }

  /**
   * Busca documentos - MIGRADO: searchDocuments() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const searchDocuments = async (query = null) => {
    if (!appStore.currentCompanyId) {
      showNotification('Por favor selecciona una empresa primero', 'warning')
      return
    }

    // Si no se pasa query, obtenerlo del DOM como script.js
    if (!query) {
      const searchInput = document.getElementById('documentSearch')
      if (!searchInput) {
        showNotification('Campo de búsqueda no encontrado', 'error')
        return
      }
      query = searchInput.value.trim()
    }

    if (!query) {
      showNotification('Por favor introduce un término de búsqueda', 'warning')
      return
    }

    try {
      isSearching.value = true
      searchQuery.value = query
      searchResults.value = []

      addToLog(`Searching documents for: "${query}"`, 'info')
      showNotification('Buscando documentos...', 'info')

      // PRESERVAR: Llamada API exacta como script.js
      const response = await apiRequest('/api/documents/search', {
        method: 'POST',
        headers: {
          'X-Company-ID': appStore.currentCompanyId
        },
        body: {
          query: query,
          limit: 50
        }
      })

      searchResults.value = response.results || response

      // PRESERVAR: Mostrar resultados en DOM como script.js
      const container = document.getElementById('searchResults')
      if (container) {
        if (searchResults.value.length === 0) {
          container.innerHTML = `
            <div class="result-container result-info">
              <p>🔍 No se encontraron documentos para "${query}"</p>
            </div>
          `
        } else {
          container.innerHTML = `
            <div class="result-container result-success">
              <h4>🔍 Resultados de Búsqueda (${searchResults.value.length})</h4>
              <p><strong>Búsqueda:</strong> "${query}"</p>
              <div class="search-results-list">
                ${searchResults.value.map(doc => `
                  <div class="search-result-item">
                    <h5>${doc.name || doc.filename}</h5>
                    <p><strong>Tipo:</strong> ${doc.document_type || 'N/A'}</p>
                    <p><strong>Relevancia:</strong> ${doc.score ? (doc.score * 100).toFixed(1) + '%' : 'N/A'}</p>
                    ${doc.excerpt ? `<p><strong>Extracto:</strong> ${doc.excerpt}</p>` : ''}
                    <div class="result-actions">
                      <button onclick="viewDocument('${doc.id}')" class="btn btn-info btn-small">Ver</button>
                    </div>
                  </div>
                `).join('')}
              </div>
            </div>
          `
        }
      }

      addToLog(`Document search completed: ${searchResults.value.length} results`, 'success')
      showNotification(`Búsqueda completada: ${searchResults.value.length} resultados`, 'success')

      return searchResults.value

    } catch (error) {
      addToLog(`Document search failed: ${error.message}`, 'error')
      showNotification('Error buscando documentos: ' + error.message, 'error')

      const container = document.getElementById('searchResults')
      if (container) {
        container.innerHTML = `
          <div class="result-container result-error">
            <p>❌ Error en búsqueda</p>
            <p>${error.message}</p>
          </div>
        `
      }

      return []

    } finally {
      isSearching.value = false
    }
  }

  /**
   * Ve documento - MIGRADO: viewDocument() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const viewDocument = async (documentId) => {
    if (!documentId) {
      showNotification('ID de documento requerido', 'warning')
      return null
    }

    try {
      addToLog(`Viewing document: ${documentId}`, 'info')

      // PRESERVAR: Llamada API exacta como script.js
      const response = await apiRequest(`/api/documents/${documentId}`, {
        method: 'GET',
        headers: {
          'X-Company-ID': appStore.currentCompanyId
        }
      })

      documentDetails.value = response

      // PRESERVAR: Mostrar modal como script.js
      showDocumentModal(response)

      addToLog(`Document details loaded: ${documentId}`, 'success')
      
      return response

    } catch (error) {
      addToLog(`Error viewing document: ${error.message}`, 'error')
      showNotification('Error viendo documento: ' + error.message, 'error')
      return null
    }
  }

  /**
   * Elimina documento - MIGRADO: deleteDocument() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const deleteDocument = async (documentId) => {
    if (!documentId) {
      showNotification('ID de documento requerido', 'warning')
      return false
    }

    // PRESERVAR: Confirmación como script.js
    if (!confirm('¿Estás seguro de eliminar este documento? Esta acción no se puede deshacer.')) {
      return false
    }

    try {
      isDeleting.value = true
      addToLog(`Deleting document: ${documentId}`, 'info')
      showNotification('Eliminando documento...', 'info')

      // PRESERVAR: Llamada API exacta como script.js
      await apiRequest(`/api/documents/${documentId}`, {
        method: 'DELETE',
        headers: {
          'X-Company-ID': appStore.currentCompanyId
        }
      })

      // Remover de la lista local
      const index = documents.value.findIndex(doc => doc.id === documentId)
      if (index !== -1) {
        documents.value.splice(index, 1)
      }

      addToLog(`Document deleted successfully: ${documentId}`, 'success')
      showNotification('Documento eliminado exitosamente', 'success')

      // Recargar lista
      await loadDocuments()

      return true

    } catch (error) {
      addToLog(`Error deleting document: ${error.message}`, 'error')
      showNotification('Error eliminando documento: ' + error.message, 'error')
      return false

    } finally {
      isDeleting.value = false
    }
  }

  // ============================================================================
  // FUNCIONES AUXILIARES DOM (PRESERVAR COMPATIBILIDAD)
  // ============================================================================

  /**
   * Actualiza tabla de documentos en DOM - PRESERVAR: Como script.js
   */
  const updateDocumentsTable = (docs) => {
    const tableContainer = document.getElementById('documentsTable')
    if (!tableContainer) return

    if (docs.length === 0) {
      tableContainer.innerHTML = '<p>No hay documentos subidos.</p>'
      return
    }

    let tableHtml = `
      <table class="data-table">
        <thead>
          <tr>
            <th>Nombre</th>
            <th>Tipo</th>
            <th>Tamaño</th>
            <th>Fecha</th>
            <th>Estado</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
    `

    docs.forEach(doc => {
      const uploadDate = doc.created_at ? 
        new Date(doc.created_at).toLocaleDateString() : 'N/A'
      const fileSize = doc.size ? formatFileSize(doc.size) : 'N/A'
      
      tableHtml += `
        <tr>
          <td>${doc.name || doc.filename || 'Sin nombre'}</td>
          <td>${doc.document_type || 'N/A'}</td>
          <td>${fileSize}</td>
          <td>${uploadDate}</td>
          <td><span class="status-${doc.status || 'unknown'}">${doc.status || 'Unknown'}</span></td>
          <td>
            <button onclick="viewDocument('${doc.id}')" class="btn btn-info btn-small">Ver</button>
            <button onclick="deleteDocument('${doc.id}')" class="btn btn-danger btn-small">Eliminar</button>
          </td>
        </tr>
      `
    })

    tableHtml += `
        </tbody>
      </table>
    `

    tableContainer.innerHTML = tableHtml
  }

  /**
   * Muestra modal de documento
   */
  const showDocumentModal = (document) => {
    const modalHtml = `
      <div id="documentModal" class="modal" style="display: block;">
        <div class="modal-content">
          <div class="modal-header">
            <h3>Detalles del Documento</h3>
            <span class="close" onclick="closeModal()">&times;</span>
          </div>
          <div class="modal-body">
            <div class="document-details">
              <p><strong>Nombre:</strong> ${document.name || document.filename}</p>
              <p><strong>Tipo:</strong> ${document.document_type || 'N/A'}</p>
              <p><strong>Tamaño:</strong> ${document.size ? formatFileSize(document.size) : 'N/A'}</p>
              <p><strong>Fecha:</strong> ${document.created_at ? new Date(document.created_at).toLocaleString() : 'N/A'}</p>
              <p><strong>Estado:</strong> ${document.status || 'Unknown'}</p>
              ${document.description ? `<p><strong>Descripción:</strong> ${document.description}</p>` : ''}
            </div>
            <div class="json-container">
              <pre>${JSON.stringify(document, null, 2)}</pre>
            </div>
          </div>
          <div class="modal-footer">
            <button onclick="deleteDocument('${document.id}')" class="btn btn-danger">Eliminar</button>
            <button onclick="closeModal()" class="btn btn-secondary">Cerrar</button>
          </div>
        </div>
      </div>
    `

    // Remover modal existente
    const existingModal = document.getElementById('documentModal')
    if (existingModal) existingModal.remove()

    // Agregar nuevo modal
    document.body.insertAdjacentHTML('beforeend', modalHtml)
  }

  /**
   * Limpia formulario de carga
   */
  const clearUploadForm = () => {
    const inputs = ['documentFile', 'documentType', 'documentDescription']
    inputs.forEach(inputId => {
      const input = document.getElementById(inputId)
      if (input) {
        input.value = input.type === 'file' ? '' : (inputId === 'documentType' ? 'general' : '')
      }
    })
  }

  /**
   * Valida archivo antes de subir
   */
  const validateFile = (file) => {
    if (!file) {
      showNotification('No se ha seleccionado ningún archivo', 'error')
      return false
    }

    // PRESERVAR: Validaciones como script.js
    if (file.size > maxFileSize.value) {
      showNotification(`El archivo es demasiado grande. Máximo ${formatFileSize(maxFileSize.value)}`, 'error')
      return false
    }

    // Verificar tipo de archivo si está en la lista restringida
    if (supportedFileTypes.value.length > 0 && !supportedFileTypes.value.includes(file.type)) {
      const allowedTypes = supportedFileTypes.value.map(type => type.split('/')[1]).join(', ')
      showNotification(`Tipo de archivo no soportado. Tipos permitidos: ${allowedTypes}`, 'error')
      return false
    }

    return true
  }

  /**
   * Formatea tamaño de archivo
   */
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  /**
   * Exporta lista de documentos
   */
  const exportDocuments = (format = 'json') => {
    try {
      const dataToExport = {
        export_timestamp: new Date().toISOString(),
        company_id: appStore.currentCompanyId,
        documents: documents.value,
        total_count: documents.value.length,
        stats: uploadStats.value
      }

      let content
      const timestamp = new Date().toISOString().split('T')[0]
      
      if (format === 'json') {
        content = JSON.stringify(dataToExport, null, 2)
      } else if (format === 'csv') {
        const headers = 'ID,Name,Type,Size,Status,Created_Date,Description\n'
        content = headers + documents.value.map(doc => 
          `"${doc.id}","${doc.name || doc.filename || ''}","${doc.document_type || ''}","${doc.size || ''}","${doc.status || ''}","${doc.created_at || ''}","${(doc.description || '').replace(/"/g, '""')}"`
        ).join('\n')
      }

      // Crear archivo para descarga
      const blob = new Blob([content], { 
        type: format === 'json' ? 'application/json' : 'text/csv' 
      })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `documents_${appStore.currentCompanyId}_${timestamp}.${format}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)

      addToLog(`Documents exported to ${format.toUpperCase()} format`, 'success')
      showNotification(`Documentos exportados en formato ${format.toUpperCase()}`, 'success')
      
    } catch (error) {
      addToLog(`Error exporting documents: ${error.message}`, 'error')
      showNotification(`Error exportando documentos: ${error.message}`, 'error')
    }
  }

  // ============================================================================
  // WATCHERS
  // ============================================================================

  // Watcher para recargar cuando cambie la empresa
  watch(() => appStore.currentCompanyId, async (newCompanyId) => {
    if (newCompanyId) {
      documents.value = [] // Limpiar documentos anteriores
      await loadDocuments()
    }
  })

  // ============================================================================
  // RETURN COMPOSABLE API
  // ============================================================================

  return {
    // Estado reactivo
    documents,
    selectedFile,
    isUploading,
    isLoading,
    isSearching,
    isDeleting,
    uploadProgress,
    searchQuery,
    searchResults,
    documentDetails,
    uploadResults,
    lastUpdateTime,

    // Configuración
    supportedFileTypes,
    maxFileSize,

    // Computed properties
    documentsCount,
    hasDocuments,
    isAnyProcessing,
    canUpload,
    filteredDocuments,
    documentsByType,
    uploadStats,

    // Funciones principales (PRESERVAR nombres exactos de script.js)
    uploadDocument,
    loadDocuments,
    searchDocuments,
    viewDocument,
    deleteDocument,

    // Funciones auxiliares
    validateFile,
    formatFileSize,
    clearUploadForm,
    exportDocuments,
    updateDocumentsTable
  }
}
