<template>
  <!-- 🔧 VUE COMPATIBLE: Modal usando Teleport y estado reactivo -->
  <Teleport to="body">
    <Transition name="modal">
      <div 
        v-if="showModal && isVisible" 
        class="modal-overlay-vue"
        @click="handleOverlayClick"
        @keydown.esc="closeModal"
      >
        <div 
          class="modal-content-vue"
          @click.stop
          role="dialog"
          aria-modal="true"
          :aria-labelledby="modalId + '-title'"
        >
          <!-- Modal Header -->
          <div class="modal-header-vue">
            <h3 :id="modalId + '-title'" class="modal-title-vue">
              📄 {{ modalConfig.title || 'Documento' }}
            </h3>
            <button 
              @click="closeModal"
              class="modal-close-btn-vue"
              aria-label="Cerrar modal"
              type="button"
            >
              ✕
            </button>
          </div>
          
          <!-- Modal Body -->
          <div class="modal-body-vue">
            <!-- Loading State -->
            <div v-if="modalLoading" class="modal-loading-vue">
              <div class="loading-spinner-vue">⏳</div>
              <p>Cargando documento...</p>
            </div>
            
            <!-- Error State -->
            <div v-else-if="modalError" class="modal-error-vue">
              <div class="error-icon-vue">❌</div>
              <h4>Error al cargar documento</h4>
              <p>{{ modalError }}</p>
              <button @click="retryLoad" class="retry-btn-vue">
                🔄 Intentar de nuevo
              </button>
            </div>
            
            <!-- Document Content -->
            <div v-else-if="modalConfig.documentData" class="document-viewer-vue">
              <!-- Document Meta -->
              <div class="document-meta-vue">
                <div class="meta-grid-vue">
                  <div class="meta-item-vue">
                    <span class="meta-label-vue">🏢 Empresa:</span>
                    <span class="meta-value-vue">{{ currentCompanyId }}</span>
                  </div>
                  <div class="meta-item-vue">
                    <span class="meta-label-vue">📅 Creado:</span>
                    <span class="meta-value-vue">{{ formatDate(modalConfig.documentData.created_at) }}</span>
                  </div>
                  <div v-if="modalConfig.documentData.type" class="meta-item-vue">
                    <span class="meta-label-vue">📄 Tipo:</span>
                    <span class="meta-value-vue">{{ modalConfig.documentData.type }}</span>
                  </div>
                  <div v-if="modalConfig.documentData.size" class="meta-item-vue">
                    <span class="meta-label-vue">💾 Tamaño:</span>
                    <span class="meta-value-vue">{{ formatFileSize(modalConfig.documentData.size) }}</span>
                  </div>
                </div>
              </div>
              
              <!-- Document Content -->
              <div class="document-content-vue">
                <h4 class="content-title-vue">📋 Contenido:</h4>
                <div class="content-display-vue">
                  <pre class="content-text-vue">{{ modalConfig.content }}</pre>
                </div>
              </div>
            </div>
            
            <!-- Empty State -->
            <div v-else class="modal-empty-vue">
              <div class="empty-icon-vue">📄</div>
              <p>No hay documento para mostrar</p>
            </div>
          </div>
          
          <!-- Modal Footer -->
          <div v-if="!modalLoading && modalConfig.documentData" class="modal-footer-vue">
            <div class="footer-left-vue">
              <span class="document-path-vue">
                🏢 {{ currentCompanyId }} / 📄 {{ modalConfig.title }}
              </span>
            </div>
            
            <div class="footer-right-vue">
              <button 
                @click="downloadDocument"
                class="footer-btn-vue download-btn-vue"
                type="button"
              >
                📥 Descargar
              </button>
              <button 
                @click="deleteDocument"
                class="footer-btn-vue delete-btn-vue"
                type="button"
              >
                🗑️ Eliminar
              </button>
              <button 
                @click="closeModal"
                class="footer-btn-vue close-btn-vue"
                type="button"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
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
  showModal: {
    type: Boolean,
    default: false
  },
  modalConfig: {
    type: Object,
    default: () => ({
      title: '',
      content: '',
      documentData: null
    })
  },
  modalLoading: {
    type: Boolean,
    default: false
  },
  modalError: {
    type: String,
    default: null
  },
  isVisible: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits([
  'close',
  'delete',
  'download',
  'retry'
])

// ============================================================================
// STORES & COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const { showNotification } = useNotifications()

// ============================================================================
// ESTADO LOCAL
// ============================================================================

const modalId = ref('modal-' + Date.now())

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const currentCompanyId = computed(() => {
  return appStore.currentCompanyId || 'No seleccionada'
})

// ============================================================================
// MÉTODOS PRINCIPALES
// ============================================================================

/**
 * Cerrar modal
 */
const closeModal = () => {
  emit('close')
  appStore.addToLog('Vue modal closed', 'info')
}

/**
 * Handle overlay click
 */
const handleOverlayClick = (event) => {
  if (event.target.classList.contains('modal-overlay-vue')) {
    closeModal()
  }
}

/**
 * Retry loading
 */
const retryLoad = () => {
  emit('retry')
}

/**
 * Download document
 */
const downloadDocument = () => {
  if (!props.modalConfig.documentData) return
  
  try {
    const content = props.modalConfig.content || ''
    const title = props.modalConfig.title || 'documento'
    
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
    emit('download', props.modalConfig.documentData)
    
  } catch (error) {
    console.error('Error downloading document:', error)
    showNotification('❌ Error al descargar documento', 'error')
  }
}

/**
 * Delete document
 */
const deleteDocument = () => {
  if (!props.modalConfig.documentData) return
  
  const confirmed = confirm(`¿Estás seguro de que quieres eliminar "${props.modalConfig.title}"?`)
  
  if (confirmed) {
    emit('delete', props.modalConfig.documentData.id || props.modalConfig.documentData._id)
    closeModal()
  }
}

// ============================================================================
// MÉTODOS DE UTILIDAD
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
  if (!dateString) return 'Desconocida'
  
  try {
    const date = new Date(dateString)
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
  } catch {
    return 'Fecha inválida'
  }
}

// ============================================================================
// LIFECYCLE HOOKS
// ============================================================================

onMounted(() => {
  // Focus management for accessibility
  if (props.showModal) {
    nextTick(() => {
      const modal = document.querySelector('.modal-content-vue')
      if (modal) {
        modal.focus()
      }
    })
  }
})

// ============================================================================
// WATCHERS
// ============================================================================

// Watch para changes en showModal para accessibility
watch(() => props.showModal, (newValue) => {
  if (newValue) {
    // Prevent body scroll when modal is open
    document.body.style.overflow = 'hidden'
  } else {
    // Restore body scroll when modal is closed
    document.body.style.overflow = ''
  }
})

// Cleanup when component unmounts
onUnmounted(() => {
  document.body.style.overflow = ''
})
</script>

<style scoped>
/* 🔧 VUE MODAL STYLES - NO CONFLICTS WITH EXISTING */
.modal-overlay-vue {
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
  padding: 20px;
  box-sizing: border-box;
}

.modal-content-vue {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  max-width: 800px;
  width: 100%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  outline: none;
}

.modal-header-vue {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 25px;
  border-bottom: 1px solid #eee;
  background: #f8f9fa;
  border-radius: 12px 12px 0 0;
}

.modal-title-vue {
  margin: 0;
  color: #333;
  font-size: 1.3em;
  font-weight: 600;
  word-wrap: break-word;
}

.modal-close-btn-vue {
  background: none;
  border: none;
  font-size: 24px;
  color: #666;
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

.modal-close-btn-vue:hover {
  background: #dc3545;
  color: white;
}

.modal-body-vue {
  flex: 1;
  overflow-y: auto;
  padding: 20px 25px;
}

.modal-loading-vue,
.modal-error-vue,
.modal-empty-vue {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
  color: #666;
}

.loading-spinner-vue {
  font-size: 2em;
  margin-bottom: 15px;
  animation: spin-vue 1s linear infinite;
}

.error-icon-vue,
.empty-icon-vue {
  font-size: 3em;
  margin-bottom: 15px;
  opacity: 0.5;
}

.retry-btn-vue {
  margin-top: 15px;
  padding: 8px 16px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s ease;
}

.retry-btn-vue:hover {
  background: #0056b3;
}

.document-viewer-vue {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.document-meta-vue {
  padding: 15px;
  background: #f9f9f9;
  border-radius: 6px;
  border-left: 4px solid #007bff;
}

.meta-grid-vue {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 10px;
}

.meta-item-vue {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.9em;
}

.meta-label-vue {
  color: #666;
  font-weight: 500;
}

.meta-value-vue {
  color: #333;
  font-weight: 600;
  text-align: right;
  word-break: break-word;
}

.document-content-vue {
  flex: 1;
}

.content-title-vue {
  color: #333;
  margin-bottom: 15px;
  font-size: 1.1em;
}

.content-display-vue {
  border: 1px solid #ddd;
  border-radius: 6px;
  overflow: hidden;
}

.content-text-vue {
  margin: 0;
  padding: 20px;
  background: #fafafa;
  font-family: 'Courier New', monospace;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-size: 0.9em;
  line-height: 1.5;
  color: #333;
  max-height: 400px;
  overflow-y: auto;
}

.modal-footer-vue {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 25px;
  border-top: 1px solid #eee;
  background: #f8f9fa;
  border-radius: 0 0 12px 12px;
  gap: 15px;
}

.footer-left-vue {
  flex: 1;
  min-width: 0;
}

.document-path-vue {
  font-size: 0.85em;
  color: #666;
  font-family: monospace;
  word-wrap: break-word;
}

.footer-right-vue {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.footer-btn-vue {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
  color: #666;
  cursor: pointer;
  font-size: 0.85em;
  font-weight: 500;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.footer-btn-vue:hover {
  background: #f8f9fa;
  color: #333;
}

.download-btn-vue:hover {
  border-color: #28a745;
  color: #28a745;
}

.delete-btn-vue:hover {
  border-color: #dc3545;
  color: #dc3545;
}

.close-btn-vue:hover {
  border-color: #007bff;
  color: #007bff;
}

/* Vue Transition */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .modal-content-vue,
.modal-leave-active .modal-content-vue {
  transition: transform 0.3s ease;
}

.modal-enter-from .modal-content-vue,
.modal-leave-to .modal-content-vue {
  transform: scale(0.95) translateY(-30px);
}

@keyframes spin-vue {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Responsive */
@media (max-width: 768px) {
  .modal-content-vue {
    width: 95vw;
    margin: 10px;
  }
  
  .modal-header-vue {
    padding: 15px;
  }
  
  .modal-body-vue {
    padding: 15px;
  }
  
  .modal-footer-vue {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
    padding: 15px;
  }
  
  .footer-right-vue {
    justify-content: center;
  }
  
  .meta-grid-vue {
    grid-template-columns: 1fr;
  }
  
  .meta-item-vue {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
  
  .meta-value-vue {
    text-align: left;
  }
}

@media (max-width: 480px) {
  .modal-content-vue {
    margin: 5px;
  }
  
  .content-text-vue {
    padding: 15px;
    font-size: 0.8em;
  }
  
  .footer-btn-vue {
    flex: 1;
    text-align: center;
  }
}
</style>
