<template>
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
      :disabled="!canUploadDocument || isUploading"
      :class="{ 'uploading': isUploading }"
    >
      <span v-if="isUploading">⏳ Subiendo...</span>
      <span v-else>📤 Subir Documento</span>
    </button>
    
    <!-- Upload result -->
    <div v-if="uploadResult" class="upload-result" :class="uploadResult.type">
      <p><strong>{{ uploadResult.title }}</strong></p>
      <p>{{ uploadResult.message }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { useDocuments } from '@/composables/useDocuments' // ✅ USAR composable refactorizado
import { useNotifications } from '@/composables/useNotifications'

// ============================================================================
// EMITS
// ============================================================================

const emit = defineEmits(['uploaded', 'refresh'])

// ============================================================================
// STORES & COMPOSABLES - REFACTORIZADOS
// ============================================================================

const appStore = useAppStore()
const { showNotification } = useNotifications()

// ✅ USAR COMPOSABLE REFACTORIZADO
const { 
  uploadDocument, 
  isUploading, 
  uploadProgress 
} = useDocuments()

// ============================================================================
// ESTADO LOCAL
// ============================================================================

const documentTitle = ref('')
const documentContent = ref('')
const selectedFile = ref(null)
const isDragOver = ref(false)
const uploadResult = ref(null)
const fileInputRef = ref(null)

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const canUploadDocument = computed(() => {
  return appStore.currentCompanyId && 
         documentTitle.value.trim() && 
         (documentContent.value.trim() || selectedFile.value) &&
         !isUploading.value
})

// ============================================================================
// MÉTODOS PRINCIPALES - REFACTORIZADOS
// ============================================================================

/**
 * ✅ REFACTORIZADO - Pasa datos estructurados al composable
 * En lugar de que el composable lea del DOM
 */
const handleUpload = async () => {
  if (!canUploadDocument.value) {
    showNotification('Por favor completa todos los campos requeridos', 'warning')
    return
  }

  if (!appStore.currentCompanyId) {
    showNotification('Por favor selecciona una empresa primero', 'warning')
    return
  }

  try {
    uploadResult.value = null
    
    // ✅ NUEVO - Preparar datos estructurados
    const uploadData = {
      title: documentTitle.value.trim(),
      content: documentContent.value.trim(),
      file: selectedFile.value
    }
    
    // ✅ Pasar datos al composable (en lugar de manipulación DOM)
    const response = await uploadDocument(uploadData)

    if (response) {
      // ✅ Mostrar resultado de éxito
      uploadResult.value = {
        type: 'result-success',
        title: '✅ Documento subido exitosamente',
        message: `"${uploadData.title}" ha sido agregado a la base de datos.`
      }

      // ✅ Limpiar formulario local
      clearForm()
      
      // ✅ Emitir evento a componente padre
      emit('uploaded', response)
      emit('refresh')
      
    } else {
      // Error ya manejado por el composable
      uploadResult.value = {
        type: 'result-error', 
        title: '❌ Error al subir documento',
        message: 'Revisa la consola para más detalles'
      }
    }

  } catch (error) {
    console.error('Error uploading document:', error)
    
    uploadResult.value = {
      type: 'result-error',
      title: '❌ Error al subir documento',
      message: error.message
    }
    
    showNotification('Error al subir documento: ' + error.message, 'error')
  }
}

/**
 * ✅ NUEVO - Limpiar formulario local
 */
const clearForm = () => {
  documentTitle.value = ''
  documentContent.value = ''
  selectedFile.value = null
  
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
  
  // Limpiar resultado después de un tiempo
  setTimeout(() => {
    uploadResult.value = null
  }, 5000)
}

// ============================================================================
// FILE SELECTION METHODS - SIN CAMBIOS
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

// ============================================================================
// DRAG & DROP HANDLERS - SIN CAMBIOS
// ============================================================================

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
// UTILITY METHODS - SIN CAMBIOS
// ============================================================================

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

const formatFileSize = (bytes) => {
  if (!bytes) return 'Desconocido'
  
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
}

// ============================================================================
// LIFECYCLE HOOKS - REFACTORIZADO
// ============================================================================

onMounted(() => {
  // ✅ MANTENER COMPATIBILIDAD - Exponer función global simplificada
  window.uploadDocument = async () => {
    // Usar datos del DOM para mantener compatibilidad
    return await uploadDocument() // Sin parámetros = leer DOM en composable
  }
  
  appStore.addToLog('DocumentUpload component mounted (improved)', 'info')
})
</script>

<style scoped>
/* Estilos sin cambios - mantenemos los existentes */
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

.file-upload.dragover {
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
}

.btn-primary {
  background: var(--primary-color);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-color-dark);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn.uploading {
  background: var(--warning-color);
  cursor: not-allowed;
}

.upload-result {
  margin-top: 15px;
  padding: 12px;
  border-radius: 6px;
  border-left: 4px solid;
}

.result-success {
  background: #f0fff4;
  border-color: var(--success-color);
  color: var(--success-color);
}

.result-error {
  background: #fed7d7;
  border-color: var(--danger-color);
  color: var(--danger-color);
}

/* Responsive */
@media (max-width: 768px) {
  .selected-file {
    flex-direction: column;
    gap: 10px;
  }
  
  .file-info {
    width: 100%;
    justify-content: center;
  }
}
</style>
