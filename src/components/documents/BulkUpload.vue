<template>
  <div class="bulk-upload-container">
    <!-- Toggle Button -->
    <div class="bulk-upload-toggle">
      <button 
        @click="toggleBulkMode" 
        class="btn-toggle"
        :class="{ 'active': isBulkMode }"
      >
        <span v-if="isBulkMode">✓ Modo Masivo Activo</span>
        <span v-else>📤 Activar Carga Masiva</span>
      </button>
      
      <div v-if="isBulkMode" class="bulk-info">
        <span class="info-text">
          💡 Sube múltiples documentos a la vez
        </span>
      </div>
    </div>

    <!-- Bulk Upload Panel -->
    <transition name="slide-fade">
      <div v-if="isBulkMode" class="bulk-upload-panel">
        
        <!-- File Selection Area -->
        <div class="upload-section">
          <div 
            class="drop-zone"
            :class="{ 
              'drag-over': isDragOver,
              'has-files': selectedFiles.length > 0,
              'disabled': isUploading
            }"
            @click="triggerFileInput"
            @dragenter.prevent="handleDragEnter"
            @dragover.prevent="handleDragOver"  
            @dragleave.prevent="handleDragLeave"
            @drop.prevent="handleDrop"
          >
            <input 
              ref="fileInputRef"
              type="file" 
              multiple
              accept=".txt,.md,.pdf,.docx,.json,.csv"
              style="display: none;"
              @change="handleFileSelect"
              :disabled="isUploading"
            />
            
            <!-- Empty State -->
            <div v-if="selectedFiles.length === 0" class="drop-zone-content">
              <div class="upload-icon">📁</div>
              <p class="upload-title">Arrastra archivos aquí o haz clic para seleccionar</p>
              <p class="upload-hint">Formatos soportados: TXT, MD, PDF, DOCX, JSON, CSV</p>
              <p class="upload-limit">Máximo recomendado: 50 archivos por carga</p>
            </div>
            
            <!-- Files Preview -->
            <div v-else class="files-preview">
              <div class="preview-header">
                <h4>📋 {{ selectedFiles.length }} archivo(s) seleccionado(s)</h4>
                <button 
                  v-if="!isUploading"
                  @click.stop="clearAllFiles"
                  class="btn-clear-all"
                  title="Limpiar todos los archivos"
                >
                  🗑️ Limpiar Todo
                </button>
              </div>
              
              <div class="files-list">
                <div 
                  v-for="(file, index) in visibleFiles" 
                  :key="index"
                  class="file-item"
                  :class="{ 'file-error': file.error }"
                >
                  <span class="file-icon">{{ getFileIcon(file.type) }}</span>
                  <div class="file-info">
                    <span class="file-name" :title="file.name">{{ file.name }}</span>
                    <span class="file-meta">
                      {{ formatFileSize(file.size) }} • {{ getFileType(file.name) }}
                    </span>
                    <span v-if="file.error" class="file-error-msg">
                      ⚠️ {{ file.error }}
                    </span>
                  </div>
                  <button 
                    v-if="!isUploading"
                    @click.stop="removeFile(index)"
                    class="btn-remove-file"
                    title="Eliminar archivo"
                  >
                    ✕
                  </button>
                </div>
                
                <div v-if="selectedFiles.length > maxVisibleFiles" class="more-files">
                  + {{ selectedFiles.length - maxVisibleFiles }} archivo(s) más
                  <button @click="showAllFiles = !showAllFiles" class="btn-show-more">
                    {{ showAllFiles ? 'Mostrar menos' : 'Mostrar todos' }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Upload Options -->
        <div v-if="selectedFiles.length > 0" class="upload-options">
          <div class="options-grid">
            <label class="option-item">
              <input 
                type="checkbox" 
                v-model="options.useFilenameAsTitle"
                :disabled="isUploading"
              />
              <span>Usar nombre de archivo como título</span>
            </label>
            
            <label class="option-item">
              <input 
                type="checkbox" 
                v-model="options.detectCategory"
                :disabled="isUploading"
              />
              <span>Detectar categoría automáticamente</span>
            </label>
            
            <label class="option-item">
              <input 
                type="checkbox" 
                v-model="options.skipErrors"
                :disabled="isUploading"
              />
              <span>Continuar si hay errores</span>
            </label>
          </div>
        </div>

        <!-- Progress Bar -->
        <transition name="fade">
          <div v-if="isUploading" class="upload-progress">
            <div class="progress-header">
              <span class="progress-status">{{ uploadStatus }}</span>
              <span class="progress-percentage">{{ Math.round(uploadProgress) }}%</span>
            </div>
            <div class="progress-bar">
              <div 
                class="progress-fill"
                :style="{ width: `${uploadProgress}%` }"
              ></div>
            </div>
            <div class="progress-details">
              <span>{{ processedCount }} / {{ selectedFiles.length }} archivos procesados</span>
            </div>
          </div>
        </transition>

        <!-- Actions -->
        <div class="upload-actions">
          <button 
            @click="clearAllFiles"
            :disabled="selectedFiles.length === 0 || isUploading"
            class="btn btn-secondary"
          >
            🗑️ Limpiar
          </button>
          
          <button 
            @click="handleBulkUpload"
            :disabled="!canUpload"
            class="btn btn-primary"
          >
            <span v-if="isUploading">⏳ Subiendo...</span>
            <span v-else>📤 Subir {{ selectedFiles.length }} Documento(s)</span>
          </button>
        </div>

        <!-- Upload Result -->
        <transition name="fade">
          <div v-if="uploadResult" class="upload-result" :class="uploadResult.type">
            <div class="result-header">
              <h4>{{ uploadResult.title }}</h4>
              <button @click="uploadResult = null" class="btn-close-result">✕</button>
            </div>
            
            <div v-if="uploadResult.summary" class="result-summary">
              <div class="summary-grid">
                <div class="summary-item">
                  <span class="summary-label">Total procesados</span>
                  <span class="summary-value">{{ uploadResult.summary.total }}</span>
                </div>
                <div class="summary-item success">
                  <span class="summary-label">✅ Exitosos</span>
                  <span class="summary-value">{{ uploadResult.summary.success }}</span>
                </div>
                <div v-if="uploadResult.summary.failed > 0" class="summary-item error">
                  <span class="summary-label">❌ Fallidos</span>
                  <span class="summary-value">{{ uploadResult.summary.failed }}</span>
                </div>
                <div class="summary-item">
                  <span class="summary-label">🧩 Chunks totales</span>
                  <span class="summary-value">{{ uploadResult.summary.totalChunks }}</span>
                </div>
                <div class="summary-item">
                  <span class="summary-label">📊 Tasa de éxito</span>
                  <span class="summary-value">{{ uploadResult.summary.successRate }}</span>
                </div>
              </div>
            </div>
            
            <div v-if="uploadResult.errors && uploadResult.errors.length > 0" class="result-errors">
              <details>
                <summary>⚠️ Ver errores ({{ uploadResult.errors.length }})</summary>
                <ul class="error-list">
                  <li v-for="(error, index) in uploadResult.errors.slice(0, 10)" :key="index">
                    {{ error }}
                  </li>
                </ul>
                <p v-if="uploadResult.errors.length > 10" class="more-errors">
                  + {{ uploadResult.errors.length - 10 }} error(es) más
                </p>
              </details>
            </div>
          </div>
        </transition>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { useDocuments } from '@/composables/useDocuments'
import { useNotifications } from '@/composables/useNotifications'

// ============================================================================
// EMITS
// ============================================================================

const emit = defineEmits(['uploaded', 'refresh', 'toggle'])

// ============================================================================
// STORES & COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const { showNotification } = useNotifications()
const { 
  bulkUploadDocuments, 
  formatBulkUploadResult,
  isUploading 
} = useDocuments()

// ============================================================================
// STATE
// ============================================================================

const isBulkMode = ref(false)
const selectedFiles = ref([])
const isDragOver = ref(false)
const uploadProgress = ref(0)
const uploadStatus = ref('')
const uploadResult = ref(null)
const fileInputRef = ref(null)
const showAllFiles = ref(false)
const processedCount = ref(0)

// Upload options
const options = ref({
  useFilenameAsTitle: true,
  detectCategory: true,
  skipErrors: true
})

// ============================================================================
// CONSTANTS
// ============================================================================

const maxVisibleFiles = 10
const maxFileSize = 10 * 1024 * 1024 // 10MB
const allowedExtensions = ['.txt', '.md', '.pdf', '.docx', '.json', '.csv']

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const canUpload = computed(() => {
  return selectedFiles.value.length > 0 && 
         !isUploading.value && 
         appStore.hasCompanySelected
})

const visibleFiles = computed(() => {
  return showAllFiles.value 
    ? selectedFiles.value 
    : selectedFiles.value.slice(0, maxVisibleFiles)
})

const totalSize = computed(() => {
  return selectedFiles.value.reduce((sum, file) => sum + file.size, 0)
})

// ============================================================================
// WATCHERS
// ============================================================================

watch(() => appStore.currentCompanyId, (newId, oldId) => {
  if (oldId && newId !== oldId && isBulkMode.value) {
    console.log('[BULK-UPLOAD] Company changed, clearing files')
    clearAllFiles()
  }
})

// ============================================================================
// MAIN METHODS
// ============================================================================

const toggleBulkMode = () => {
  isBulkMode.value = !isBulkMode.value
  
  if (!isBulkMode.value) {
    clearAllFiles()
  }
  
  emit('toggle', isBulkMode.value)
  appStore.addToLog(`Bulk upload mode ${isBulkMode.value ? 'activated' : 'deactivated'}`, 'info')
}

const triggerFileInput = () => {
  if (!isUploading.value && fileInputRef.value) {
    fileInputRef.value.click()
  }
}

const handleFileSelect = (event) => {
  const files = Array.from(event.target.files)
  addFiles(files)
}

const handleDragEnter = () => {
  if (!isUploading.value) {
    isDragOver.value = true
  }
}

const handleDragOver = () => {
  if (!isUploading.value) {
    isDragOver.value = true
  }
}

const handleDragLeave = (event) => {
  if (!event.currentTarget.contains(event.relatedTarget)) {
    isDragOver.value = false
  }
}

const handleDrop = (event) => {
  isDragOver.value = false
  if (isUploading.value) return
  
  const files = Array.from(event.dataTransfer.files)
  addFiles(files)
}

const addFiles = (files) => {
  const validFiles = []
  const invalidFiles = []
  
  files.forEach(file => {
    const extension = '.' + file.name.split('.').pop().toLowerCase()
    
    // Validar extensión
    if (!allowedExtensions.includes(extension)) {
      invalidFiles.push({ file, reason: 'Formato no soportado' })
      return
    }
    
    // Validar tamaño
    if (file.size > maxFileSize) {
      invalidFiles.push({ file, reason: 'Archivo muy grande (máx 10MB)' })
      return
    }
    
    // Validar si ya existe
    const exists = selectedFiles.value.some(f => 
      f.name === file.name && f.size === file.size
    )
    
    if (exists) {
      invalidFiles.push({ file, reason: 'Archivo duplicado' })
      return
    }
    
    validFiles.push(file)
  })
  
  // Agregar archivos válidos
  if (validFiles.length > 0) {
    selectedFiles.value = [...selectedFiles.value, ...validFiles]
    showNotification(
      `✅ ${validFiles.length} archivo(s) agregado(s)`,
      'success',
      2000
    )
  }
  
  // Notificar archivos inválidos
  if (invalidFiles.length > 0) {
    showNotification(
      `⚠️ ${invalidFiles.length} archivo(s) no válido(s)`,
      'warning',
      3000
    )
    
    // Agregar a lista con error
    invalidFiles.forEach(({ file, reason }) => {
      selectedFiles.value.push({
        ...file,
        error: reason
      })
    })
  }
  
  appStore.addToLog(
    `Files added: ${validFiles.length} valid, ${invalidFiles.length} invalid`,
    'info'
  )
}

const removeFile = (index) => {
  const fileName = selectedFiles.value[index].name
  selectedFiles.value.splice(index, 1)
  showNotification(`🗑️ Archivo eliminado: ${fileName}`, 'info', 2000)
}

const clearAllFiles = () => {
  const count = selectedFiles.value.length
  selectedFiles.value = []
  uploadResult.value = null
  uploadProgress.value = 0
  uploadStatus.value = ''
  processedCount.value = 0
  showAllFiles.value = false
  
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
  
  if (count > 0) {
    showNotification(`🗑️ ${count} archivo(s) eliminado(s)`, 'info', 2000)
  }
}

const handleBulkUpload = async () => {
  if (!canUpload.value) return
  
  if (!appStore.currentCompanyId) {
    showNotification('⚠️ Por favor selecciona una empresa primero', 'warning')
    return
  }

  uploadResult.value = null
  uploadProgress.value = 0
  uploadStatus.value = 'Preparando archivos...'
  processedCount.value = 0

  try {
    // Preparar documentos
    uploadStatus.value = 'Leyendo archivos...'
    
    const documentsArray = await Promise.all(
      selectedFiles.value
        .filter(file => !file.error) // Solo archivos válidos
        .map(async (file) => {
          const content = await readFileContent(file)
          const title = options.value.useFilenameAsTitle 
            ? file.name.replace(/\.[^/.]+$/, '') 
            : file.name
          
          const metadata = {
            title: title,
            filename: file.name,
            file_type: file.type || 'text/plain',
            size: file.size,
            source: 'bulk_upload',
            uploaded_at: new Date().toISOString()
          }

          // Detectar categoría si está activado
          if (options.value.detectCategory) {
            metadata.category = detectCategory(file.name)
          }

          return {
            content: content,
            metadata: metadata
          }
        })
    )

    uploadStatus.value = `Subiendo ${documentsArray.length} documentos...`

    // Callback de progreso
    const onProgress = (progressData) => {
      uploadProgress.value = progressData.progress
      processedCount.value = progressData.current || 0
      
      if (progressData.status === 'completed') {
        uploadStatus.value = '✅ Carga completada'
      } else if (progressData.status === 'error') {
        uploadStatus.value = '❌ Error en la carga'
      } else {
        uploadStatus.value = `Procesando... ${processedCount.value}/${documentsArray.length}`
      }
    }

    // Ejecutar bulk upload
    const result = await bulkUploadDocuments(documentsArray, onProgress)

    if (result) {
      const formattedResult = formatBulkUploadResult(result)
      
      uploadResult.value = {
        type: formattedResult.hasErrors && !formattedResult.hasSuccess 
          ? 'result-error' 
          : formattedResult.hasErrors 
          ? 'result-warning' 
          : 'result-success',
        title: formattedResult.hasErrors && !formattedResult.hasSuccess
          ? '❌ Carga masiva falló'
          : formattedResult.hasErrors 
          ? '⚠️ Carga masiva completada con errores'
          : '✅ Carga masiva exitosa',
        summary: formattedResult.summary,
        errors: formattedResult.errors
      }

      // Limpiar archivos después de carga exitosa
      if (formattedResult.hasSuccess) {
        setTimeout(() => {
          clearAllFiles()
        }, 5000)
      }

      // Emitir eventos
      emit('uploaded', result)
      emit('refresh')
      
      appStore.addToLog(
        `Bulk upload completed: ${formattedResult.summary.success} success, ${formattedResult.summary.failed} failed`,
        formattedResult.hasSuccess ? 'info' : 'error'
      )
    }

  } catch (error) {
    console.error('Error in bulk upload:', error)
    uploadResult.value = {
      type: 'result-error',
      title: '❌ Error en la carga masiva',
      message: error.message
    }
    showNotification(`❌ Error: ${error.message}`, 'error')
  }
}

// ============================================================================
// UTILITIES
// ============================================================================

const readFileContent = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    
    reader.onload = (e) => {
      resolve(e.target.result)
    }
    
    reader.onerror = () => {
      reject(new Error(`Error leyendo archivo: ${file.name}`))
    }
    
    reader.readAsText(file)
  })
}

const detectCategory = (filename) => {
  const name = filename.toLowerCase()
  
  if (name.includes('tratamiento') || name.includes('treatment')) return 'tratamientos'
  if (name.includes('precio') || name.includes('price')) return 'precios'
  if (name.includes('servicio') || name.includes('service')) return 'servicios'
  if (name.includes('politica') || name.includes('policy')) return 'politicas'
  if (name.includes('faq') || name.includes('pregunta')) return 'faq'
  if (name.includes('contacto') || name.includes('contact')) return 'contacto'
  
  return 'general'
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

const getFileType = (filename) => {
  const extension = filename.split('.').pop()?.toUpperCase()
  return extension || 'FILE'
}

const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
}
</script>

<style scoped>
/* ============================================================================
   📝 ESTILOS PARA BulkUpload.vue
   Agregar en la sección <style scoped> del componente
   ============================================================================ */

.bulk-upload-container {
  margin-bottom: 20px;
}

/* Toggle Button */
.bulk-upload-toggle {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 15px;
}

.btn-toggle {
  padding: 10px 20px;
  border: 2px solid var(--primary-color);
  border-radius: 8px;
  background: transparent;
  color: var(--primary-color);
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-toggle:hover {
  background: var(--primary-color);
  color: white;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.btn-toggle.active {
  background: var(--primary-color);
  color: white;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4);
}

.bulk-info {
  flex: 1;
}

.info-text {
  color: var(--text-muted);
  font-size: 0.9em;
  font-style: italic;
}

/* Main Panel */
.bulk-upload-panel {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 20px;
}

/* Drop Zone */
.drop-zone {
  border: 2px dashed var(--border-color);
  border-radius: 8px;
  padding: 30px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: var(--bg-tertiary);
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.drop-zone:not(.disabled):hover {
  border-color: var(--primary-color);
  background: rgba(102, 126, 234, 0.05);
  transform: scale(1.01);
}

.drop-zone.drag-over {
  border-color: var(--primary-color);
  background: rgba(102, 126, 234, 0.1);
  border-width: 3px;
  transform: scale(1.02);
}

.drop-zone.has-files {
  padding: 20px;
  min-height: auto;
}

.drop-zone.disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.drop-zone-content {
  width: 100%;
}

.upload-icon {
  font-size: 3em;
  margin-bottom: 15px;
  animation: float 3s ease-in-out infinite;
}

.upload-title {
  font-size: 1.1em;
  color: var(--text-primary);
  margin: 10px 0;
  font-weight: 500;
}

.upload-hint {
  font-size: 0.9em;
  color: var(--text-muted);
  margin: 5px 0;
}

.upload-limit {
  font-size: 0.85em;
  color: var(--warning-color);
  margin-top: 10px;
  font-style: italic;
}

/* Files Preview */
.files-preview {
  width: 100%;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border-color);
}

.preview-header h4 {
  margin: 0;
  color: var(--text-primary);
  font-size: 1.1em;
}

.btn-clear-all {
  padding: 6px 12px;
  background: var(--danger-color);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85em;
  font-weight: 500;
  transition: all 0.2s ease;
}

.btn-clear-all:hover {
  background: #c82333;
  transform: translateY(-1px);
}

.files-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 400px;
  overflow-y: auto;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--bg-primary);
  border-radius: 6px;
  border: 1px solid var(--border-color);
  transition: all 0.2s ease;
}

.file-item:hover {
  border-color: var(--primary-color);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.file-item.file-error {
  border-color: var(--danger-color);
  background: rgba(239, 68, 68, 0.05);
}

.file-icon {
  font-size: 1.5em;
  min-width: 32px;
  text-align: center;
}

.file-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.file-name {
  font-weight: 500;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-meta {
  font-size: 0.85em;
  color: var(--text-muted);
}

.file-error-msg {
  font-size: 0.8em;
  color: var(--danger-color);
  font-weight: 500;
}

.btn-remove-file {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 1.1em;
  transition: all 0.2s ease;
}

.btn-remove-file:hover {
  background: var(--danger-color);
  color: white;
}

.more-files {
  text-align: center;
  padding: 12px;
  color: var(--text-muted);
  font-size: 0.9em;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.btn-show-more {
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--primary-color);
  padding: 4px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85em;
  transition: all 0.2s ease;
}

.btn-show-more:hover {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}

/* Upload Options */
.upload-options {
  margin: 20px 0;
  padding: 15px;
  background: var(--bg-tertiary);
  border-radius: 6px;
  border: 1px solid var(--border-color);
}

.options-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.option-item {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: var(--text-primary);
  font-size: 0.9em;
}

.option-item input[type="checkbox"] {
  cursor: pointer;
  width: 16px;
  height: 16px;
}

.option-item:hover {
  color: var(--primary-color);
}

/* Progress Bar */
.upload-progress {
  padding: 15px;
  background: var(--bg-tertiary);
  border-radius: 6px;
  border: 1px solid var(--border-color);
  margin: 20px 0;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.progress-status {
  color: var(--text-primary);
  font-weight: 500;
  font-size: 0.9em;
}

.progress-percentage {
  color: var(--primary-color);
  font-weight: 700;
  font-size: 1.1em;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: var(--bg-primary);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-color), var(--success-color));
  transition: width 0.3s ease;
  border-radius: 4px;
}

.progress-details {
  text-align: center;
  font-size: 0.85em;
  color: var(--text-muted);
}

/* Actions */
.upload-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 20px;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-color-dark);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-secondary);
  color: var(--text-primary);
  border-color: var(--primary-color);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

/* Upload Result */
.upload-result {
  margin-top: 20px;
  padding: 20px;
  border-radius: 8px;
  border-left: 4px solid;
}

.result-success {
  background: rgba(34, 197, 94, 0.1);
  border-color: var(--success-color);
}

.result-warning {
  background: rgba(245, 158, 11, 0.1);
  border-color: var(--warning-color);
}

.result-error {
  background: rgba(239, 68, 68, 0.1);
  border-color: var(--danger-color);
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.result-header h4 {
  margin: 0;
  font-size: 1.1em;
}

.btn-close-result {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 1.2em;
  transition: all 0.2s ease;
}

.btn-close-result:hover {
  background: var(--bg-primary);
  color: var(--text-primary);
}

.result-summary {
  margin-bottom: 15px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}

.summary-item {
  padding: 12px;
  background: white;
  border-radius: 6px;
  border: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.summary-label {
  font-size: 0.85em;
  color: var(--text-muted);
  font-weight: 500;
}

.summary-value {
  font-size: 1.3em;
  font-weight: 700;
  color: var(--text-primary);
}

.summary-item.success .summary-value {
  color: var(--success-color);
}

.summary-item.error .summary-value {
  color: var(--danger-color);
}

.result-errors {
  margin-top: 15px;
}

.result-errors details {
  cursor: pointer;
}

.result-errors summary {
  padding: 10px;
  background: rgba(239, 68, 68, 0.1);
  border-radius: 4px;
  font-weight: 500;
  color: var(--danger-color);
  list-style: none;
  display: flex;
  align-items: center;
  gap: 8px;
}

.result-errors summary::-webkit-details-marker {
  display: none;
}

.result-errors summary::before {
  content: '▶';
  transition: transform 0.2s ease;
}

.result-errors details[open] summary::before {
  transform: rotate(90deg);
}

.error-list {
  margin: 10px 0 0 0;
  padding-left: 25px;
  color: var(--text-secondary);
  font-size: 0.9em;
}

.error-list li {
  margin-bottom: 8px;
  line-height: 1.4;
}

.more-errors {
  margin-top: 10px;
  padding: 8px;
  text-align: center;
  font-style: italic;
  color: var(--text-muted);
  background: var(--bg-tertiary);
  border-radius: 4px;
}

/* Animations */
@keyframes float {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-10px); }
}

.slide-fade-enter-active {
  transition: all 0.3s ease-out;
}

.slide-fade-leave-active {
  transition: all 0.2s cubic-bezier(1, 0.5, 0.8, 1);
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateY(-20px);
  opacity: 0;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Responsive */
@media (max-width: 768px) {
  .bulk-upload-toggle {
    flex-direction: column;
    align-items: stretch;
  }
  
  .btn-toggle {
    justify-content: center;
  }
  
  .bulk-upload-panel {
    padding: 15px;
  }
  
  .drop-zone {
    padding: 20px 10px;
  }
  
  .preview-header {
    flex-direction: column;
    gap: 10px;
    align-items: stretch;
  }
  
  .options-grid {
    grid-template-columns: 1fr;
  }
  
  .upload-actions {
    flex-direction: column;
  }
  
  .btn {
    width: 100%;
    justify-content: center;
  }
  
  .summary-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 480px) {
  .file-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .file-info {
    width: 100%;
  }
  
  .btn-remove-file {
    align-self: flex-end;
  }
}
</style>
