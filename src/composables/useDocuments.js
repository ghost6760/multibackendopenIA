// composables/useDocuments.js - MODAL COMPLETAMENTE CORREGIDO
// FIX: Modal que se cierra automáticamente al cambiar empresa/pestaña

import { ref, computed, watch } from 'vue'
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
  
  // 🆕 NUEVO: Estado para el modal con mejor gestión
  const isModalOpen = ref(false)
  const modalDocument = ref(null)
  const activeModals = ref(new Set()) // Track all active modals
  
  // ============================================================================
  // 🔧 WATCHERS PARA AUTO-CERRAR MODALS
  // ============================================================================
  
  // Watch para cambios de empresa - CRÍTICO para cerrar modals
  watch(() => appStore.currentCompanyId, (newCompanyId, oldCompanyId) => {
    if (oldCompanyId && newCompanyId !== oldCompanyId) {
      console.log('[MODAL-FIX] Company changed, closing all modals')
      forceCloseAllModals()
      searchResults.value = [] // Clear search results too
    }
  })
  
  // Watch para detectar cambios de pestaña activa
  let currentActiveTab = null
  const watchActiveTab = () => {
    const observer = new MutationObserver(() => {
      const activeTab = document.querySelector('.tab-content.active')
      const activeTabId = activeTab ? activeTab.id : null
      
      if (currentActiveTab && activeTabId !== currentActiveTab) {
        console.log('[MODAL-FIX] Tab changed, closing all modals')
        forceCloseAllModals()
      }
      currentActiveTab = activeTabId
    })
    
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['class']
    })
    
    return observer
  }
  
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
        // Subir archivo
        requestData = createFormData({
          title,
          file,
          content: content || '',
          company_id: appStore.currentCompanyId
        })
        options.headers = {}
      } else {
        // Subir solo contenido de texto
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
   */
  const searchDocuments = async (query = null) => {
    if (!appStore.currentCompanyId) {
      showNotification('⚠️ Por favor selecciona una empresa primero', 'warning')
      return []
    }
    
    // 🔧 CRÍTICO: Cerrar modals antes de nueva búsqueda
    forceCloseAllModals()
    
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
      
      // Mostrar resultados - MEJORADO con cierre automático
      displaySearchResultsSafe(searchResults.value)
      
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
   * 🔧 CORREGIDO: Visualiza un documento específico con modal que se puede cerrar
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
    
    // 🔧 CRÍTICO: Cerrar cualquier modal existente primero
    forceCloseAllModals()
    
    try {
      const cleanDocId = String(docId).trim()
      
      appStore.addToLog(`[${appStore.currentCompanyId}] Viewing document: ${cleanDocId}`, 'info')
      
      const response = await apiRequest(`/api/documents/${cleanDocId}`, {
        headers: {
          'X-Company-ID': appStore.currentCompanyId
        }
      })
      
      currentDocument.value = response
      modalDocument.value = response
      
      // 🔧 NUEVA IMPLEMENTACIÓN: Modal seguro que se puede cerrar
      showDocumentModalSafe(response)
      
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
      
      // 🔧 IMPORTANTE: Cerrar modal si el documento eliminado es el que se está mostrando
      if (modalDocument.value && (modalDocument.value.id === docId || modalDocument.value._id === docId)) {
        forceCloseAllModals()
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
  // 🔧 MODAL SEGURO - NUEVA IMPLEMENTACIÓN ROBUSTA
  // ============================================================================
  
  /**
   * 🔧 NUEVA: Modal completamente seguro que se puede cerrar
   */
  const showDocumentModalSafe = (documentData) => {
    // ID único para este modal
    const modalId = 'docModal_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
    
    // Crear modal con cierre automático mejorado
    const modal = createSafeModal(modalId, documentData)
    
    // Agregar al conjunto de modals activos
    activeModals.value.add(modalId)
    isModalOpen.value = true
    modalDocument.value = documentData
    
    // Insertar en DOM
    document.body.appendChild(modal)
    
    appStore.addToLog(`[${appStore.currentCompanyId}] Safe modal opened: ${modalId}`, 'info')
  }
  
  /**
   * 🔧 FUNCIÓN: Crear modal DOM seguro
   */
  const createSafeModal = (modalId, documentData) => {
    // Crear elemento modal
    const modalOverlay = document.createElement('div')
    modalOverlay.id = modalId
    modalOverlay.className = 'modal-overlay document-modal-safe'
    modalOverlay.style.cssText = `
      position: fixed; 
      top: 0; left: 0; 
      width: 100%; height: 100%; 
      background: rgba(0,0,0,0.6); 
      z-index: 10000; 
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
      box-sizing: border-box;
    `
    
    // Contenido del modal
    modalOverlay.innerHTML = `
      <div class="modal-content" style="
        background: white; 
        border-radius: 8px; 
        width: 100%;
        max-width: 800px;
        max-height: 90vh;
        display: flex;
        flex-direction: column;
        overflow: hidden;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
      ">
        <div class="modal-header" style="
          display: flex; 
          justify-content: space-between; 
          align-items: center; 
          padding: 20px 25px;
          border-bottom: 1px solid #eee;
          background: #f8f9fa;
        ">
          <h3 style="margin: 0; color: #333; font-size: 1.2em;">
            📄 ${escapeHTML(documentData.title || 'Sin título')}
          </h3>
          <button class="modal-close-btn" style="
            background: none; 
            border: none; 
            font-size: 24px; 
            cursor: pointer; 
            color: #666; 
            padding: 0; 
            line-height: 1;
            width: 30px;
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 4px;
            transition: all 0.2s ease;
          " onmouseover="this.style.background='#dc3545'; this.style.color='white';" 
             onmouseout="this.style.background='none'; this.style.color='#666';">
            ✕
          </button>
        </div>
        
        <div class="modal-body" style="
          flex: 1; 
          overflow-y: auto; 
          padding: 20px 25px;
        ">
          <div class="document-meta" style="
            margin-bottom: 20px; 
            padding: 15px; 
            background: #f9f9f9; 
            border-radius: 4px;
            border-left: 4px solid #007bff;
          ">
            <p style="margin: 5px 0; font-size: 0.9em;"><strong>🏢 Empresa:</strong> ${escapeHTML(appStore.currentCompanyId)}</p>
            <p style="margin: 5px 0; font-size: 0.9em;"><strong>📅 Creado:</strong> ${formatDate(documentData.created_at)}</p>
            ${documentData.type ? `<p style="margin: 5px 0; font-size: 0.9em;"><strong>📄 Tipo:</strong> ${escapeHTML(documentData.type)}</p>` : ''}
            ${documentData.size ? `<p style="margin: 5px 0; font-size: 0.9em;"><strong>💾 Tamaño:</strong> ${formatFileSize(documentData.size)}</p>` : ''}
          </div>
          
          <div class="document-content">
            <h4 style="color: #333; margin-bottom: 15px; font-size: 1.1em;">📋 Contenido:</h4>
            <div style="
              max-height: 400px; 
              overflow-y: auto; 
              border: 1px solid #ddd; 
              padding: 20px; 
              background: #fafafa; 
              font-family: 'Courier New', monospace; 
              white-space: pre-wrap; 
              word-wrap: break-word;
              font-size: 0.9em;
              line-height: 1.5;
              border-radius: 4px;
            ">${escapeHTML(documentData.content || 'Sin contenido disponible')}</div>
          </div>
        </div>
        
        <div class="modal-footer" style="
          padding: 15px 25px; 
          border-top: 1px solid #eee; 
          background: #f8f9fa;
          display: flex; 
          gap: 10px; 
          justify-content: flex-end;
        ">
          <button class="modal-delete-btn" style="
            padding: 8px 16px; 
            background: #dc3545; 
            color: white; 
            border: none; 
            border-radius: 4px; 
            cursor: pointer;
            font-weight: 500;
            transition: background-color 0.2s ease;
          " onmouseover="this.style.background='#c82333';" 
             onmouseout="this.style.background='#dc3545';">
            🗑️ Eliminar
          </button>
          <button class="modal-close-btn-secondary" style="
            padding: 8px 16px; 
            background: #6c757d; 
            color: white; 
            border: none; 
            border-radius: 4px; 
            cursor: pointer;
            font-weight: 500;
            transition: background-color 0.2s ease;
          " onmouseover="this.style.background='#5a6268';" 
             onmouseout="this.style.background='#6c757d';">
            Cerrar
          </button>
        </div>
      </div>
    `
    
    // 🔧 CRÍTICO: Event listeners robustos
    const closeModal = () => {
      console.log(`[MODAL-SAFE] Closing modal: ${modalId}`)
      closeSafeModal(modalId)
    }
    
    const deleteDoc = async () => {
      if (confirm(`¿Estás seguro de que quieres eliminar "${documentData.title}"?`)) {
        closeModal() // Cerrar primero
        await deleteDocument(documentData.id || documentData._id)
      }
    }
    
    // Asignar eventos
    modalOverlay.querySelector('.modal-close-btn').addEventListener('click', closeModal)
    modalOverlay.querySelector('.modal-close-btn-secondary').addEventListener('click', closeModal)
    modalOverlay.querySelector('.modal-delete-btn').addEventListener('click', deleteDoc)
    
    // Cerrar al hacer clic en overlay
    modalOverlay.addEventListener('click', (e) => {
      if (e.target === modalOverlay) closeModal()
    })
    
    // 🔧 CRÍTICO: Escape key global para este modal específico
    const handleEscape = (e) => {
      if (e.key === 'Escape' && document.getElementById(modalId)) {
        closeModal()
      }
    }
    
    document.addEventListener('keydown', handleEscape)
    
    // Guardar la función de limpieza
    modalOverlay._cleanupFunction = () => {
      document.removeEventListener('keydown', handleEscape)
    }
    
    return modalOverlay
  }
  
  /**
   * 🔧 FUNCIÓN: Cerrar modal específico de forma segura
   */
  const closeSafeModal = (modalId) => {
    const modal = document.getElementById(modalId)
    if (modal) {
      // Ejecutar función de limpieza si existe
      if (modal._cleanupFunction) {
        modal._cleanupFunction()
      }
      
      // Remover del DOM
      modal.remove()
      
      // Remover del conjunto de modals activos
      activeModals.value.delete(modalId)
      
      // Si no hay más modals, limpiar estado
      if (activeModals.value.size === 0) {
        isModalOpen.value = false
        modalDocument.value = null
        currentDocument.value = null
      }
      
      appStore.addToLog(`[MODAL-SAFE] Modal closed: ${modalId}`, 'info')
    }
  }
  
  /**
   * 🔧 FUNCIÓN CRÍTICA: Forzar cierre de TODOS los modals
   */
  const forceCloseAllModals = () => {
    console.log('[MODAL-FORCE-CLOSE] Closing all modals')
    
    // Cerrar modals tracked
    activeModals.value.forEach(modalId => {
      closeSafeModal(modalId)
    })
    
    // Limpiar cualquier modal huérfano en el DOM
    const orphanModals = document.querySelectorAll('.document-modal, .document-modal-safe, [id^="docModal_"], [id^="documentModal_"]')
    orphanModals.forEach(modal => {
      if (modal._cleanupFunction) {
        modal._cleanupFunction()
      }
      modal.remove()
    })
    
    // Reset completo del estado
    activeModals.value.clear()
    isModalOpen.value = false
    modalDocument.value = null
    currentDocument.value = null
    
    appStore.addToLog('[MODAL-FORCE-CLOSE] All modals closed', 'info')
  }
  
  // ============================================================================
  // 🔧 RESULTADOS DE BÚSQUEDA SEGUROS
  // ============================================================================
  
  /**
   * 🔧 MEJORADO: Muestra los resultados de búsqueda con cierre automático
   */
  const displaySearchResultsSafe = (results) => {
    const container = document.getElementById('searchResults')
    if (!container) return
    
    // 🔧 CRÍTICO: Limpiar cualquier modal antes de mostrar resultados
    forceCloseAllModals()
    
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
        <button class="clear-search-results" style="
          background: #dc3545; 
          color: white; 
          border: none; 
          padding: 6px 12px; 
          border-radius: 4px; 
          cursor: pointer;
          font-size: 0.85em;
          margin-left: auto;
        ">✕ Limpiar</button>
      </div>
      <div class="results-list">
        ${results.map(doc => `
          <div class="result-item" data-doc-id="${doc.id || doc._id}" style="
            background: white;
            border: 1px solid #ddd;
            border-radius: 6px;
            padding: 15px;
            margin-bottom: 10px;
            transition: all 0.2s ease;
          " onmouseover="this.style.borderColor='#007bff'; this.style.boxShadow='0 2px 8px rgba(0,0,0,0.1)';"
             onmouseout="this.style.borderColor='#ddd'; this.style.boxShadow='none';">
            <div class="result-header" style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
              <h5 class="result-title" style="margin: 0; color: #333; font-size: 1.1em;">${escapeHTML(doc.title)}</h5>
              <div class="result-actions" style="display: flex; gap: 8px;">
                <button onclick="window.handleViewDocumentSafe('${doc.id || doc._id}')" style="
                  padding: 6px 10px;
                  background: #007bff;
                  color: white;
                  border: none;
                  border-radius: 4px;
                  cursor: pointer;
                  font-size: 0.8em;
                  font-weight: 500;
                ">👁️ Ver</button>
                <button onclick="window.handleDeleteDocumentSafe('${doc.id || doc._id}')" style="
                  padding: 6px 10px;
                  background: #dc3545;
                  color: white;
                  border: none;
                  border-radius: 4px;
                  cursor: pointer;
                  font-size: 0.8em;
                  font-weight: 500;
                ">🗑️ Eliminar</button>
              </div>
            </div>
            <div class="result-content">
              ${doc.highlight ? `<p class="result-excerpt" style="margin: 5px 0; font-size: 0.9em; color: #666; font-style: italic;"><strong>Extracto:</strong> ${escapeHTML(doc.highlight)}</p>` : ''}
              ${doc.content ? `<p class="result-preview" style="margin: 5px 0; font-size: 0.85em; color: #555;"><strong>Vista previa:</strong> ${escapeHTML(doc.content.substring(0, 200))}${doc.content.length > 200 ? '...' : ''}</p>` : ''}
            </div>
            <div class="result-meta" style="display: flex; gap: 15px; margin-top: 10px; font-size: 0.8em; color: #888;">
              <span class="result-date">📅 ${formatDate(doc.created_at)}</span>
              ${doc.type ? `<span class="result-type">📄 ${doc.type}</span>` : ''}
              ${doc.relevance ? `<span class="result-relevance">⭐ ${Math.round(doc.relevance * 100)}%</span>` : ''}
              <span class="result-company">🏢 ${doc.company_id || appStore.currentCompanyId}</span>
            </div>
          </div>
        `).join('')}
      </div>
    `
    
    // 🔧 AÑADIR: Event listener para limpiar resultados
    const clearBtn = container.querySelector('.clear-search-results')
    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        searchResults.value = []
        container.innerHTML = '<div class="search-placeholder"><p>Los resultados de búsqueda aparecerán aquí</p></div>'
        forceCloseAllModals() // Cerrar cualquier modal abierto
      })
    }
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
  // SETUP DE FUNCIONES GLOBALES - CORREGIDO
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
    
    // 🔧 CRÍTICO: Funciones globales SEGURAS
    window.handleViewDocumentSafe = (docId) => {
      console.log(`[GLOBAL-SAFE] handleViewDocumentSafe called with ID: ${docId}`)
      viewDocument(docId)
    }
    
    window.handleDeleteDocumentSafe = (docId) => {
      console.log(`[GLOBAL-SAFE] handleDeleteDocumentSafe called with ID: ${docId}`)
      deleteDocument(docId)
    }
    
    // 🔧 CRÍTICO: Función global para cerrar TODOS los modals
    window.forceCloseAllDocumentModals = () => {
      console.log('[GLOBAL-SAFE] forceCloseAllDocumentModals called')
      forceCloseAllModals()
    }
    
    // 🔧 NUEVO: Iniciar observer de pestañas
    const tabObserver = watchActiveTab()
    
    // Limpiar observer cuando sea necesario
    window._documentTabObserver = tabObserver
  }
  
  // ============================================================================
  // 🔧 CLEANUP FUNCTION - Limpiar todo al desmontar
  // ============================================================================
  
  const cleanup = () => {
    forceCloseAllModals()
    
    if (window._documentTabObserver) {
      window._documentTabObserver.disconnect()
    }
    
    // Limpiar funciones globales
    if (typeof window !== 'undefined') {
      delete window.handleViewDocumentSafe
      delete window.handleDeleteDocumentSafe
      delete window.forceCloseAllDocumentModals
      delete window._documentTabObserver
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
    
    // Métodos del modal
    forceCloseAllModals,
    
    // Métodos de utilidad
    displaySearchResultsSafe,
    setupFileUploadHandlers,
    getFileType,
    formatFileSize,
    formatDate,
    escapeHTML,
    cleanup
  }
}
