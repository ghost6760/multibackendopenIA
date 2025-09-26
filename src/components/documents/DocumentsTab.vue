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
        <!-- ✅ USAR COMPONENTE ESPECIALIZADO - No duplicar código -->
        <DocumentUpload 
          @uploaded="handleDocumentUploaded"
          @refresh="loadDocuments"
        />

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
          
          <!-- Modal alert simplificado -->
          <div v-if="isModalOpen" class="modal-alert">
            <div class="alert alert-warning">
              <span>⚠️ Hay un modal abierto</span>
              <button @click="forceCloseModals" class="btn-close-modal">
                ✕ Cerrar Modal
              </button>
            </div>
          </div>
          
          <!-- ✅ USAR COMPONENTE ESPECIALIZADO - SearchResults -->
          <div class="search-results-container">
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
        
        <!-- ✅ USAR COMPONENTE ESPECIALIZADO - DocumentList -->
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

    <!-- ✅ USAR COMPONENTE ESPECIALIZADO - DocumentModal -->
    <DocumentModalVue
      :show-modal="showModal"
      :modal-config="modalConfig"
      :modal-loading="modalLoading"
      :modal-error="modalError"
      @close="closeModal"
      @delete="handleModalDelete"
      @download="handleModalDownload"
      @retry="handleModalRetry"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useAppStore } from '@/stores/app'
import { useDocuments } from '@/composables/useDocuments'
import { useNotifications } from '@/composables/useNotifications'

// ✅ COMPONENTES ESPECIALIZADOS - Sin duplicación
import DocumentList from './DocumentList.vue'
import SearchResults from './SearchResults.vue'
import DocumentModalVue from './DocumentModal.vue'
import DocumentUpload from './DocumentUpload.vue' // ✅ USAR COMPONENTE EXISTENTE

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
  isSearching,
  hasDocuments,
  documentsCount,
  hasSearchResults,
  // Modal state
  isModalOpen,
  modalDocument,
  modalError,
  modalLoading,
  showModal,
  modalConfig,
  // Methods
  loadDocuments,
  searchDocuments,
  viewDocument,
  deleteDocument,
  closeModal,
  forceCloseAllModals
} = useDocuments()

const { showNotification } = useNotifications()

// ============================================================================
// ESTADO LOCAL SIMPLIFICADO - Solo lo que no está en componentes
// ============================================================================

const searchQuery = ref('')
const searchPerformed = ref(false)

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const showAdminFunctions = computed(() => {
  return appStore.adminApiKey || import.meta.env.DEV
})

// ============================================================================
// WATCHERS PARA AUTO-CERRAR MODALS
// ============================================================================

watch(() => props.isActive, (newActive, oldActive) => {
  if (oldActive && !newActive) {
    console.log('[DOCUMENTS-TAB] Tab became inactive, closing modals')
    forceCloseModals()
  }
})

watch(() => appStore.currentCompanyId, (newCompanyId, oldCompanyId) => {
  if (oldCompanyId && newCompanyId !== oldCompanyId) {
    console.log('[DOCUMENTS-TAB] Company changed, closing modals and clearing search')
    forceCloseModals()
    clearSearchResults()
  }
})

// ============================================================================
// MÉTODOS DE BÚSQUEDA - SIMPLIFICADOS
// ============================================================================

/**
 * ✅ SIMPLIFICADO - Solo orquestación, lógica en composable
 */
const handleSearch = async () => {
  if (!searchQuery.value.trim()) {
    showNotification('❌ Ingresa un término de búsqueda', 'error')
    return
  }
  
  forceCloseModals()
  searchPerformed.value = true
  await searchDocuments(searchQuery.value)
}

/**
 * ✅ SIMPLIFICADO - Limpiar resultados
 */
const clearSearchResults = () => {
  searchResults.value = []
  searchPerformed.value = false
  searchQuery.value = ''
  forceCloseModals()
  showNotification('🔍 Resultados de búsqueda limpiados', 'info')
}

// ============================================================================
// MÉTODOS DEL MODAL - SIMPLIFICADOS
// ============================================================================

const forceCloseModals = () => {
  console.log('[DOCUMENTS-TAB] forceCloseModals called from component')
  forceCloseAllModals()
}

const handleModalDelete = async (docId) => {
  await deleteDocument(docId)
}

const handleModalDownload = (documentData) => {
  showNotification(`📥 Documento descargado: ${documentData.title}`, 'success')
}

const handleModalRetry = () => {
  if (modalConfig.value.documentData) {
    viewDocument(modalConfig.value.documentData.id || modalConfig.value.documentData._id)
  }
}

// ============================================================================
// EVENTOS DE COMPONENTES
// ============================================================================

/**
 * ✅ NUEVO - Manejar evento de DocumentUpload
 */
const handleDocumentUploaded = async (uploadedDocument) => {
  console.log('[DOCUMENTS-TAB] Document uploaded:', uploadedDocument)
  showNotification('✅ Documento subido exitosamente', 'success')
  
  // Recargar lista de documentos
  await loadDocuments()
}

// ============================================================================
// MÉTODOS DE UTILIDAD - SIMPLIFICADOS
// ============================================================================

const focusUploadArea = () => {
  // ✅ DELEGAR al componente DocumentUpload
  nextTick(() => {
    const uploadComponent = document.querySelector('.document-upload input[type="text"]')
    if (uploadComponent) {
      uploadComponent.focus()
    }
  })
}

const highlightCompanySelector = () => {
  window.dispatchEvent(new CustomEvent('highlightCompanySelector'))
}

// ============================================================================
// MÉTODOS ADMINISTRATIVOS - SIN CAMBIOS
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
// LIFECYCLE HOOKS - SIMPLIFICADOS
// ============================================================================

onMounted(async () => {
  appStore.addToLog('DocumentsTab mounted (Refactored - Modular)', 'info')
  
  // Load documents if company is selected
  if (appStore.hasCompanySelected) {
    await loadDocuments()
  }
  
  window.addEventListener('loadTabContent', handleLoadTabContent)
  window.addEventListener('beforeunload', forceCloseModals)
  
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      console.log('[DOCUMENTS-TAB] Page hidden, closing modals')
      forceCloseModals()
    }
  })
})

onUnmounted(() => {
  console.log('[DOCUMENTS-TAB] Component unmounting, cleaning up (Refactored)')
  
  forceCloseModals()
  
  window.removeEventListener('loadTabContent', handleLoadTabContent)
  window.removeEventListener('beforeunload', forceCloseModals)
})

// Handle load tab content event
const handleLoadTabContent = (event) => {
  if (event.detail.tabName === 'documents' && props.isActive) {
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
// ✅ COMPATIBILIDAD GLOBAL SIMPLIFICADA
// ============================================================================

onMounted(() => {
  // ✅ Funciones globales simples para mantener compatibilidad
  window.loadDocuments = loadDocuments
  window.searchDocuments = searchDocuments  
  window.viewDocument = viewDocument
  window.deleteDocument = deleteDocument
  window.forceCloseAllDocumentModals = forceCloseModals
})

onUnmounted(() => {
  // Cleanup global functions
  if (typeof window !== 'undefined') {
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

/* Modal alert styles */
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

.form-group input {
  width: 100%;
  padding: 10px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 14px;
  transition: border-color 0.2s ease;
}

.form-group input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.form-group input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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
