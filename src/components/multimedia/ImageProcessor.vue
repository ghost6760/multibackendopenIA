<template>
  <div class="image-processor">
    <h3 class="processor-title">🖼️ Procesamiento de Imágenes</h3>
    
    <!-- Área de carga de imagen -->
    <div class="upload-area">
      <div 
        class="image-drop-zone"
        :class="{ 'drag-over': isDragOver, 'has-image': selectedImage }"
        @drop="handleDrop"
        @dragover.prevent="isDragOver = true"
        @dragleave.prevent="isDragOver = false"
        @click="triggerFileInput"
      >
        <input
          ref="fileInput"
          type="file"
          accept="image/*"
          @change="handleFileSelect"
          hidden
        />
        
        <div v-if="!selectedImage" class="drop-zone-content">
          <div class="drop-icon">📷</div>
          <p class="drop-text">Arrastra una imagen aquí</p>
          <p class="drop-subtext">o haz clic para seleccionar</p>
          <div class="supported-formats">
            Formatos: JPG, PNG, GIF, WebP, BMP
          </div>
        </div>
        
        <div v-else class="selected-image">
          <div class="image-preview">
            <img :src="imagePreviewUrl" :alt="selectedImage.name" />
          </div>
          <div class="image-info">
            <div class="image-name">{{ selectedImage.name }}</div>
            <div class="image-details">
              {{ formatFileSize(selectedImage.size) }} • {{ imageDimensions }}
            </div>
          </div>
          <button @click.stop="clearImage" class="remove-image">✕</button>
        </div>
      </div>
    </div>

    <!-- Campos exactos como script.js -->
    <div class="form-fields">
      <div class="form-group">
        <label for="imageUserId">ID de Usuario:</label>
        <input 
          id="imageUserId"
          type="text" 
          v-model="userId"
          placeholder="usuario_123"
          class="form-input"
        />
      </div>
      
      <div class="form-group">
        <label for="analysisType">Tipo de análisis:</label>
        <select id="analysisType" v-model="config.analysis_type" class="form-select">
          <option value="">General</option>
          <option value="medical">Análisis médico</option>
          <option value="document">Documento/Texto</option>
          <option value="product">Análisis de producto</option>
          <option value="scene">Descripción de escena</option>
          <option value="ocr">Extracción de texto (OCR)</option>
        </select>
      </div>
      
      <div class="form-group full-width">
        <label for="imagePrompt">Prompt personalizado (opcional):</label>
        <textarea
          id="imagePrompt"
          v-model="config.prompt"
          placeholder="Describe qué aspectos específicos quieres analizar en la imagen..."
          rows="3"
          class="form-textarea"
        ></textarea>
      </div>
    </div>

    <!-- Controles -->
    <div class="processor-controls">
      <button 
        class="btn btn-primary"
        @click="processImage"
        :disabled="!selectedImage || !userId.trim() || isProcessing"
      >
        <span v-if="isProcessing">⏳ Analizando...</span>
        <span v-else">🔍 Analizar Imagen</span>
      </button>
      
      <button 
        class="btn btn-secondary"
        @click="clearAll"
        :disabled="isProcessing"
      >
        🗑️ Limpiar
      </button>
      
      <button 
        class="btn btn-info"
        @click="takePhoto"
        :disabled="isProcessing"
        v-if="canUseCamera"
      >
        📸 Tomar Foto
      </button>
    </div>

    <!-- Progreso de procesamiento -->
    <div v-if="isProcessing" class="processing-progress">
      <div class="progress-header">
        <span>{{ processingStage }}</span>
        <span>{{ progress }}%</span>
      </div>
      <div class="progress-bar">
        <div 
          class="progress-fill"
          :style="{ width: progress + '%' }"
        ></div>
      </div>
    </div>

    <!-- Resultados - ESTRUCTURA EXACTA COMO SCRIPT.JS -->
    <div v-if="results" class="processing-result">
      <h4>📊 Resultado del Análisis</h4>
      
      <div class="result-content">
        <!-- Análisis/Descripción -->
        <div class="result-section">
          <h5>📝 Análisis:</h5>
          <div class="analysis-text">
            {{ getAnalysis(results) }}
          </div>
          
          <div class="analysis-actions">
            <button @click="copyToClipboard(getAnalysis(results))" class="btn btn-sm">
              📋 Copiar
            </button>
            <button @click="downloadAnalysis" class="btn btn-sm">
              💾 Descargar
            </button>
          </div>
        </div>
        
        <!-- Respuesta del Bot - COMO SCRIPT.JS CORREGIDO -->
        <div v-if="getBotResponse(results)" class="result-section">
          <h5>🤖 Respuesta del Bot:</h5>
          <div class="bot-response-text">
            {{ getBotResponse(results) }}
          </div>
        </div>
        
        <!-- Texto extraído si está disponible -->
        <div v-if="getExtractedText(results)" class="result-section">
          <h5>📄 Texto Extraído:</h5>
          <div class="extracted-text">
            <pre>{{ getExtractedText(results) }}</pre>
          </div>
          
          <div class="text-actions">
            <button @click="copyToClipboard(getExtractedText(results))" class="btn btn-sm">
              📋 Copiar Texto
            </button>
            <button @click="downloadText" class="btn btn-sm">
              💾 Descargar TXT
            </button>
          </div>
        </div>
        
        <!-- Información técnica -->
        <div class="result-section technical-info">
          <h5>🔧 Información Técnica:</h5>
          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">Empresa:</span>
              <span class="info-value">{{ getCompanyId(results) }}</span>
            </div>
            <div v-if="getProcessingTime(results)" class="info-item">
              <span class="info-label">Tiempo de procesamiento:</span>
              <span class="info-value">{{ getProcessingTime(results) }}ms</span>
            </div>
            <div class="info-item">
              <span class="info-label">Archivo:</span>
              <span class="info-value">{{ selectedImage?.name }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Tamaño:</span>
              <span class="info-value">{{ formatFileSize(selectedImage?.size || 0) }}</span>
            </div>
            <div v-if="imageDimensions" class="info-item">
              <span class="info-label">Dimensiones:</span>
              <span class="info-value">{{ imageDimensions }}</span>
            </div>
          </div>
        </div>

        <!-- Debug Info si disponible -->
        <div v-if="results.debug_info || results.metadata" class="result-section">
          <details>
            <summary>Ver información de depuración</summary>
            <pre>{{ formatJSON(results.debug_info || results.metadata || {}) }}</pre>
          </details>
        </div>
      </div>
    </div>

    <!-- Modal de cámara -->
    <div v-if="showCameraModal" class="camera-modal" @click="closeCameraModal">
      <div class="camera-content" @click.stop>
        <div class="camera-header">
          <h4>📸 Capturar Imagen</h4>
          <button @click="closeCameraModal" class="close-button">✕</button>
        </div>
        
        <div class="camera-container">
          <video ref="videoElement" autoplay playsinline></video>
          <canvas ref="canvasElement" style="display: none;"></canvas>
        </div>
        
        <div class="camera-controls">
          <button @click="capturePhoto" class="btn btn-primary">
            📷 Capturar
          </button>
          <button @click="closeCameraModal" class="btn btn-secondary">
            ❌ Cancelar
          </button>
        </div>
      </div>
    </div>

    <!-- Compatible with DOM manipulation from script.js -->
    <div id="imageResult" style="margin-top: 20px;"></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, defineProps, defineEmits } from 'vue'
import { useAppStore } from '@/stores/app'
import { useNotifications } from '@/composables/useNotifications'

// ============================================================================
// PROPS & EMITS - INTERFACE CON MULTIMEDIATAB
// ============================================================================

const props = defineProps({
  isProcessing: {
    type: Boolean,
    default: false
  },
  results: {
    type: Object,
    default: null
  },
  progress: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['process-image', 'clear-results'])

// ============================================================================
// STORES & COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const { showNotification } = useNotifications()

// ============================================================================
// REFS
// ============================================================================

const fileInput = ref(null)
const videoElement = ref(null)
const canvasElement = ref(null)

// ============================================================================
// ESTADO LOCAL - ESTRUCTURA EXACTA SCRIPT.JS
// ============================================================================

const selectedImage = ref(null)
const imagePreviewUrl = ref('')
const imageDimensions = ref('')
const isDragOver = ref(false)
const processingStage = ref('')
const showCameraModal = ref(false)
const canUseCamera = ref(false)

// Campos exactos como en script.js DOM
const userId = ref('')
const config = ref({
  analysis_type: '',  // Corresponde a script.js analysis_type option
  prompt: ''          // Corresponde a script.js prompt option
})

// ============================================================================
// COMPUTED
// ============================================================================

const canProcess = computed(() => {
  return selectedImage.value && userId.value.trim() && !props.isProcessing && appStore.currentCompanyId
})

// ============================================================================
// MÉTODOS DE MANEJO DE ARCHIVOS - VALIDACIONES EXACTAS SCRIPT.JS
// ============================================================================

const triggerFileInput = () => {
  if (!props.isProcessing) {
    fileInput.value?.click()
  }
}

const handleFileSelect = (event) => {
  const file = event.target.files[0]
  if (file) {
    validateAndSetImage(file)
  }
}

const handleDrop = (event) => {
  event.preventDefault()
  isDragOver.value = false
  
  const files = event.dataTransfer.files
  if (files.length > 0) {
    validateAndSetImage(files[0])
  }
}

const validateAndSetImage = async (file) => {
  // PRESERVAR: Validaciones exactas como script.js
  if (!file.type.startsWith('image/')) {
    showNotification('El archivo debe ser una imagen', 'error')
    return
  }
  
  // PRESERVAR: Límite de tamaño exacto como script.js
  const maxSize = 20 * 1024 * 1024 // 20MB
  if (file.size > maxSize) {
    showNotification('La imagen es demasiado grande. Máximo 20MB', 'error')
    return
  }
  
  selectedImage.value = file
  
  // Crear preview URL
  imagePreviewUrl.value = URL.createObjectURL(file)
  
  // Obtener dimensiones de la imagen
  await getImageDimensions(file)
  
  appStore.addToLog(`Image file selected: ${file.name} (${formatFileSize(file.size)})`, 'info')
}

const getImageDimensions = (file) => {
  return new Promise((resolve) => {
    const img = new Image()
    img.onload = () => {
      imageDimensions.value = `${img.width} × ${img.height}px`
      resolve()
    }
    img.src = URL.createObjectURL(file)
  })
}

const clearImage = () => {
  selectedImage.value = null
  if (imagePreviewUrl.value) {
    URL.revokeObjectURL(imagePreviewUrl.value)
    imagePreviewUrl.value = ''
  }
  imageDimensions.value = ''
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const clearAll = () => {
  clearImage()
  userId.value = ''
  config.value.analysis_type = ''
  config.value.prompt = ''
  emit('clear-results')
}

// ============================================================================
// CÁMARA - FUNCIONALIDAD COMPLETA
// ============================================================================

const takePhoto = async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ 
      video: { 
        facingMode: 'environment' // Preferir cámara trasera
      } 
    })
    
    showCameraModal.value = true
    
    await nextTick()
    
    if (videoElement.value) {
      videoElement.value.srcObject = stream
    }
    
  } catch (error) {
    showNotification('Error accediendo a la cámara: ' + error.message, 'error')
  }
}

const capturePhoto = async () => {
  try {
    const video = videoElement.value
    const canvas = canvasElement.value
    
    if (!video || !canvas) return
    
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    
    const ctx = canvas.getContext('2d')
    ctx.drawImage(video, 0, 0)
    
    // Convertir a blob
    const blob = await new Promise(resolve => {
      canvas.toBlob(resolve, 'image/jpeg', 0.8)
    })
    
    // Crear archivo
    const file = new File([blob], `photo_${Date.now()}.jpg`, { type: 'image/jpeg' })
    
    // Detener stream
    const stream = video.srcObject
    if (stream) {
      stream.getTracks().forEach(track => track.stop())
    }
    
    closeCameraModal()
    validateAndSetImage(file)
    
  } catch (error) {
    showNotification('Error capturando foto: ' + error.message, 'error')
  }
}

const closeCameraModal = () => {
  showCameraModal.value = false
  
  // Detener stream si existe
  if (videoElement.value?.srcObject) {
    const stream = videoElement.value.srcObject
    stream.getTracks().forEach(track => track.stop())
    videoElement.value.srcObject = null
  }
}

// ============================================================================
// PROCESAMIENTO - DELEGAR AL COMPOSABLE
// ============================================================================

const processImage = async () => {
  if (!canProcess.value) {
    if (!appStore.currentCompanyId) {
      showNotification('Por favor selecciona una empresa primero', 'warning')
      return
    }
    if (!selectedImage.value) {
      showNotification('Por favor selecciona una imagen', 'warning')
      return
    }
    if (!userId.value.trim()) {
      showNotification('Por favor ingresa un ID de usuario', 'warning')
      return
    }
    return
  }
  
  processingStage.value = 'Preparando imagen para análisis...'
  
  try {
    // ESTRUCTURA EXACTA: Pasar datos como script.js
    const options = {}
    if (config.value.analysis_type) options.analysis_type = config.value.analysis_type
    if (config.value.prompt.trim()) options.prompt = config.value.prompt.trim()
    
    // IMPORTANTE: También actualizar DOM para compatibilidad script.js
    const userIdInput = document.getElementById('imageUserId')
    if (userIdInput) userIdInput.value = userId.value
    
    // Delegar al composable via emit
    await emit('process-image', selectedImage.value, options)
    
  } catch (error) {
    showNotification(`Error procesando imagen: ${error.message}`, 'error')
  }
}

// ============================================================================
// EXTRACTORS - ESTRUCTURA EXACTA COMO SCRIPT.JS CORREGIDO
// ============================================================================

const getAnalysis = (results) => {
  if (!results) return 'Sin análisis'
  
  // PRESERVAR: Orden exacto de campos como script.js corregido
  return results.analysis || results.description || results.image_analysis || 'Sin análisis'
}

const getBotResponse = (results) => {
  if (!results) return null
  
  // PRESERVAR: Orden exacto de campos como script.js corregido
  return results.bot_response || results.response || results.message || null
}

const getExtractedText = (results) => {
  return results?.extracted_text || null
}

const getCompanyId = (results) => {
  return results?.company_id || appStore.currentCompanyId
}

const getProcessingTime = (results) => {
  return results?.processing_time || results?.time || null
}

// ============================================================================
// UTILIDADES
// ============================================================================

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatJSON = (obj) => {
  try {
    return JSON.stringify(obj, null, 2)
  } catch (error) {
    return 'Error formatting JSON: ' + error.message
  }
}

const copyToClipboard = async (text) => {
  try {
    await navigator.clipboard.writeText(text)
    showNotification('Copiado al portapapeles', 'success')
  } catch (error) {
    showNotification('Error al copiar al portapapeles', 'error')
  }
}

const downloadAnalysis = () => {
  if (!props.results) return
  
  const analysis = getAnalysis(props.results)
  const blob = new Blob([analysis], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  
  const a = document.createElement('a')
  a.href = url
  a.download = `image_analysis_${selectedImage.value?.name.replace(/\.[^/.]+$/, '') || 'image'}.txt`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  
  URL.revokeObjectURL(url)
  showNotification('Análisis descargado', 'success')
}

const downloadText = () => {
  if (!props.results) return
  
  const extractedText = getExtractedText(props.results)
  if (!extractedText) return
  
  const blob = new Blob([extractedText], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  
  const a = document.createElement('a')
  a.href = url
  a.download = `extracted_text_${selectedImage.value?.name.replace(/\.[^/.]+$/, '') || 'image'}.txt`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  
  URL.revokeObjectURL(url)
  showNotification('Texto descargado', 'success')
}

// ============================================================================
// LIFECYCLE
// ============================================================================

onMounted(async () => {
  // Verificar disponibilidad de cámara
  if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
    try {
      await navigator.mediaDevices.getUserMedia({ video: true })
      canUseCamera.value = true
    } catch (error) {
      canUseCamera.value = false
    }
  }
  
  appStore.addToLog('ImageProcessor component mounted', 'info')
})

onUnmounted(() => {
  // Limpiar URLs de objeto
  if (imagePreviewUrl.value) {
    URL.revokeObjectURL(imagePreviewUrl.value)
  }
  
  // Detener cámara si está activa
  closeCameraModal()
  
  appStore.addToLog('ImageProcessor component unmounted', 'info')
})
</script>

<style scoped>
.image-processor {
  padding: 20px;
  height: 100%;
}

.processor-title {
  color: var(--text-primary);
  margin-bottom: 20px;
  font-size: 1.4rem;
}

.upload-area {
  margin-bottom: 20px;
}

.image-drop-zone {
  border: 2px dashed var(--border-color);
  border-radius: var(--radius-lg);
  padding: 30px;
  text-align: center;
  cursor: pointer;
  transition: var(--transition-normal);
  background: var(--bg-secondary);
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-drop-zone:hover {
  border-color: var(--primary-color);
  background: rgba(102, 126, 234, 0.05);
}

.image-drop-zone.drag-over {
  border-color: var(--primary-color);
  background: rgba(102, 126, 234, 0.1);
  transform: scale(1.02);
}

.image-drop-zone.has-image {
  border-color: var(--success-color);
  background: rgba(72, 187, 120, 0.05);
  padding: 15px;
}

.drop-zone-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.drop-icon {
  font-size: 3rem;
  opacity: 0.6;
}

.drop-text {
  font-size: 1.1rem;
  color: var(--text-primary);
  margin: 0;
}

.drop-subtext {
  color: var(--text-secondary);
  margin: 0;
}

.supported-formats {
  font-size: 0.9rem;
  color: var(--text-muted);
  margin-top: 10px;
}

.selected-image {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px;
  background: var(--bg-primary);
  border-radius: var(--radius-md);
  border: 1px solid var(--success-color);
  width: 100%;
}

.image-preview {
  flex-shrink: 0;
}

.image-preview img {
  width: 120px;
  height: 120px;
  object-fit: cover;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.image-info {
  flex: 1;
  text-align: left;
}

.image-name {
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.image-details {
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.remove-image {
  background: var(--error-color);
  color: white;
  border: none;
  border-radius: 50%;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 0.9rem;
  flex-shrink: 0;
}

.form-fields {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
  margin-bottom: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.form-group.full-width {
  grid-column: 1 / -1;
}

.form-group label {
  font-weight: 500;
  color: var(--text-primary);
}

.form-input,
.form-select,
.form-textarea {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
  color: var(--text-primary);
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
}

.processor-controls {
  display: flex;
  gap: 10px;
  margin-bottom: 25px;
  flex-wrap: wrap;
}

.btn {
  padding: 10px 16px;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 500;
  cursor: pointer;
  transition: var(--transition-fast);
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
}

.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.btn-info {
  background: var(--info-color);
  color: white;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 0.9rem;
}

.btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.processing-progress {
  margin-bottom: 25px;
  padding: 15px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.progress-bar {
  height: 8px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--primary-color);
  border-radius: var(--radius-sm);
  transition: width 0.3s ease;
}

.processing-result {
  margin-bottom: 25px;
}

.processing-result h4 {
  color: var(--text-primary);
  margin-bottom: 15px;
}

.result-content {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 20px;
}

.result-section {
  margin-bottom: 20px;
}

.result-section:last-child {
  margin-bottom: 0;
}

.result-section h5 {
  color: var(--text-primary);
  margin-bottom: 10px;
}

.analysis-text,
.bot-response-text {
  background: var(--bg-secondary);
  padding: 15px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-light);
  line-height: 1.6;
  margin-bottom: 15px;
  min-height: 60px;
  white-space: pre-wrap;
}

.extracted-text pre {
  background: var(--bg-secondary);
  padding: 15px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-light);
  overflow-x: auto;
  margin-bottom: 15px;
  white-space: pre-wrap;
  max-height: 300px;
  overflow-y: auto;
}

.analysis-actions,
.text-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.technical-info {
  border-top: 1px solid var(--border-color);
  padding-top: 15px;
}

.info-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
}

.info-item {
  display: flex;
  justify-content: space-between;
  padding: 8px;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
}

.info-label {
  font-weight: 500;
  color: var(--text-primary);
}

.info-value {
  color: var(--text-secondary);
}

.camera-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.camera-content {
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  padding: 20px;
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow: hidden;
}

.camera-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.camera-header h4 {
  margin: 0;
  color: var(--text-primary);
}

.close-button {
  background: var(--error-color);
  color: white;
  border: none;
  border-radius: 50%;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.camera-container {
  margin-bottom: 15px;
  text-align: center;
}

.camera-container video {
  width: 100%;
  max-width: 400px;
  border-radius: var(--radius-md);
}

.camera-controls {
  display: flex;
  gap: 10px;
  justify-content: center;
}

details {
  margin-top: 15px;
}

details summary {
  cursor: pointer;
  font-weight: 500;
  color: var(--text-primary);
  padding: 10px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
}

details pre {
  background: var(--bg-secondary);
  padding: 15px;
  border-radius: var(--radius-md);
  overflow-x: auto;
  font-size: 0.9rem;
  margin-top: 10px;
}

@media (max-width: 768px) {
  .form-fields {
    grid-template-columns: 1fr;
  }
  
  .processor-controls {
    flex-direction: column;
  }
  
  .analysis-actions,
  .text-actions {
    flex-direction: column;
  }
  
  .info-grid {
    grid-template-columns: 1fr;
  }
  
  .info-item {
    flex-direction: column;
    gap: 4px;
  }
  
  .camera-content {
    margin: 10px;
    width: auto;
  }
  
  .selected-image {
    flex-direction: column;
    text-align: center;
  }
  
  .image-preview img {
    width: 200px;
    height: 200px;
  }
}
</style>
