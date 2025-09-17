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

    <!-- Configuración de análisis -->
    <div class="analysis-config">
      <h4>⚙️ Configuración de Análisis</h4>
      
      <div class="config-grid">
        <div class="config-item">
          <label for="analysisType">Tipo de análisis:</label>
          <select id="analysisType" v-model="config.analysisType">
            <option value="general">Análisis general</option>
            <option value="medical">Análisis médico</option>
            <option value="document">Documento/Texto</option>
            <option value="product">Análisis de producto</option>
            <option value="scene">Descripción de escena</option>
            <option value="ocr">Extracción de texto (OCR)</option>
          </select>
        </div>
        
        <div class="config-item">
          <label for="detailLevel">Nivel de detalle:</label>
          <select id="detailLevel" v-model="config.detailLevel">
            <option value="basic">Básico</option>
            <option value="detailed">Detallado</option>
            <option value="comprehensive">Completo</option>
          </select>
        </div>
        
        <div class="config-item full-width">
          <label for="customPrompt">Prompt personalizado (opcional):</label>
          <textarea
            id="customPrompt"
            v-model="config.prompt"
            placeholder="Describe qué aspectos específicos quieres analizar en la imagen..."
            rows="3"
          ></textarea>
        </div>
        
        <div class="config-item">
          <label>
            <input 
              type="checkbox" 
              v-model="config.includeCoordinates"
            />
            Incluir coordenadas de objetos
          </label>
        </div>
        
        <div class="config-item">
          <label>
            <input 
              type="checkbox" 
              v-model="config.extractText"
            />
            Extraer texto automáticamente
          </label>
        </div>
      </div>
    </div>

    <!-- Controles -->
    <div class="processor-controls">
      <button 
        class="btn btn-primary"
        @click="processImage"
        :disabled="!selectedImage || isProcessing"
      >
        <span v-if="isProcessing">⏳ Analizando...</span>
        <span v-else>🔍 Analizar Imagen</span>
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
        <span>{{ processingProgress }}%</span>
      </div>
      <div class="progress-bar">
        <div 
          class="progress-fill"
          :style="{ width: processingProgress + '%' }"
        ></div>
      </div>
    </div>

    <!-- Resultados -->
    <div v-if="result" class="processing-result">
      <h4>📊 Resultado del Análisis</h4>
      
      <div class="result-tabs">
        <button 
          v-for="tab in resultTabs"
          :key="tab.id"
          :class="['result-tab', { active: activeResultTab === tab.id }]"
          @click="activeResultTab = tab.id"
        >
          {{ tab.icon }} {{ tab.name }}
        </button>
      </div>
      
      <div class="result-content">
        <!-- Descripción general -->
        <div v-if="activeResultTab === 'description'" class="result-section">
          <div class="description-text">
            {{ result.description || 'No se pudo generar descripción' }}
          </div>
          
          <div class="description-actions">
            <button @click="copyToClipboard(result.description)" class="btn btn-sm">
              📋 Copiar
            </button>
            <button @click="downloadDescription" class="btn btn-sm">
              💾 Descargar
            </button>
          </div>
        </div>
        
        <!-- Texto extraído -->
        <div v-if="activeResultTab === 'text' && result.extracted_text" class="result-section">
          <div class="extracted-text">
            <pre>{{ result.extracted_text }}</pre>
          </div>
          
          <div class="text-actions">
            <button @click="copyToClipboard(result.extracted_text)" class="btn btn-sm">
              📋 Copiar Texto
            </button>
            <button @click="downloadText" class="btn btn-sm">
              💾 Descargar TXT
            </button>
          </div>
        </div>
        
        <!-- Objetos detectados -->
        <div v-if="activeResultTab === 'objects' && result.objects" class="result-section">
          <div class="objects-grid">
            <div 
              v-for="(obj, index) in result.objects"
              :key="index"
              class="object-item"
              @click="highlightObject(obj)"
            >
              <div class="object-label">{{ obj.label }}</div>
              <div class="object-confidence">
                Confianza: {{ Math.round(obj.confidence * 100) }}%
              </div>
              <div v-if="obj.coordinates" class="object-coordinates">
                Posición: ({{ obj.coordinates.x }}, {{ obj.coordinates.y }})
              </div>
            </div>
          </div>
        </div>
        
        <!-- Análisis detallado -->
        <div v-if="activeResultTab === 'analysis'" class="result-section">
          <div v-if="result.analysis" class="analysis-grid">
            <div v-for="(value, key) in result.analysis" :key="key" class="analysis-item">
              <label>{{ formatAnalysisKey(key) }}:</label>
              <span>{{ value }}</span>
            </div>
          </div>
          <div v-else class="no-analysis">
            No hay análisis detallado disponible
          </div>
        </div>
        
        <!-- Metadatos -->
        <div v-if="activeResultTab === 'metadata'" class="result-section">
          <div class="metadata-content">
            <details>
              <summary>Ver metadatos completos</summary>
              <pre>{{ formatJSON(result.metadata || {}) }}</pre>
            </details>
          </div>
        </div>
        
        <!-- Imagen procesada -->
        <div v-if="activeResultTab === 'processed' && result.processed_image" class="result-section">
          <div class="processed-image">
            <img :src="result.processed_image" alt="Imagen procesada" />
          </div>
          
          <div class="processed-actions">
            <button @click="downloadProcessedImage" class="btn btn-sm">
              💾 Descargar Imagen
            </button>
          </div>
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

    <!-- Historial reciente -->
    <div v-if="recentResults.length > 0" class="recent-results">
      <h4>📚 Análisis Reciente</h4>
      <div class="recent-list">
        <div 
          v-for="(item, index) in recentResults"
          :key="index"
          class="recent-item"
          @click="loadRecentResult(item)"
        >
          <div class="recent-thumbnail">
            <img v-if="item.thumbnail" :src="item.thumbnail" :alt="item.filename" />
            <div v-else class="no-thumbnail">🖼️</div>
          </div>
          <div class="recent-info">
            <div class="recent-name">{{ item.filename }}</div>
            <div class="recent-time">{{ formatTime(item.timestamp) }}</div>
          </div>
          <div class="recent-status">
            {{ item.status === 'success' ? '✅' : '❌' }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'

// ============================================================================
// PROPS & EMITS
// ============================================================================

const emit = defineEmits(['processing', 'completed', 'error'])

// ============================================================================
// STORES & COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const { apiRequest } = useApiRequest()
const { showNotification } = useNotifications()

// ============================================================================
// REFS
// ============================================================================

const fileInput = ref(null)
const videoElement = ref(null)
const canvasElement = ref(null)

// ============================================================================
// ESTADO LOCAL
// ============================================================================

const selectedImage = ref(null)
const imagePreviewUrl = ref('')
const imageDimensions = ref('')
const isDragOver = ref(false)
const isProcessing = ref(false)
const processingStage = ref('')
const processingProgress = ref(0)
const result = ref(null)
const activeResultTab = ref('description')
const recentResults = ref([])
const showCameraModal = ref(false)
const canUseCamera = ref(false)

// Configuración de análisis
const config = ref({
  analysisType: 'general',
  detailLevel: 'detailed',
  prompt: '',
  includeCoordinates: false,
  extractText: false
})

// ============================================================================
// COMPUTED
// ============================================================================

const resultTabs = computed(() => {
  const tabs = [
    { id: 'description', name: 'Descripción', icon: '📝' }
  ]
  
  if (result.value?.extracted_text) {
    tabs.push({ id: 'text', name: 'Texto', icon: '📄' })
  }
  
  if (result.value?.objects?.length > 0) {
    tabs.push({ id: 'objects', name: 'Objetos', icon: '🎯' })
  }
  
  if (result.value?.analysis) {
    tabs.push({ id: 'analysis', name: 'Análisis', icon: '📊' })
  }
  
  if (result.value?.metadata) {
    tabs.push({ id: 'metadata', name: 'Metadatos', icon: '📋' })
  }
  
  if (result.value?.processed_image) {
    tabs.push({ id: 'processed', name: 'Procesada', icon: '🖼️' })
  }
  
  return tabs
})

// ============================================================================
// MÉTODOS DE MANEJO DE ARCHIVOS
// ============================================================================

const triggerFileInput = () => {
  if (!isProcessing.value) {
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
  // Validar tipo de archivo
  if (!file.type.startsWith('image/')) {
    showNotification('Por favor selecciona un archivo de imagen válido', 'error')
    return
  }
  
  // Validar tamaño (max 20MB)
  const maxSize = 20 * 1024 * 1024
  if (file.size > maxSize) {
    showNotification('La imagen es demasiado grande. Máximo 20MB', 'error')
    return
  }
  
  selectedImage.value = file
  result.value = null // Limpiar resultado anterior
  
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
  result.value = null
  config.value.prompt = ''
}

// ============================================================================
// PROCESAMIENTO DE IMAGEN
// ============================================================================

const processImage = async () => {
  if (!selectedImage.value) {
    showNotification('Por favor selecciona una imagen', 'warning')
    return
  }
  
  isProcessing.value = true
  processingProgress.value = 0
  
  try {
    emit('processing', { 
      message: 'Preparando imagen para análisis...', 
      progress: 0 
    })
    
    appStore.addToLog(`Starting image processing: ${selectedImage.value.name}`, 'info')
    
    // Crear FormData
    const formData = new FormData()
    formData.append('image', selectedImage.value)
    
    // Agregar configuración
    formData.append('analysis_type', config.value.analysisType)
    formData.append('detail_level', config.value.detailLevel)
    
    if (config.value.prompt.trim()) {
      formData.append('prompt', config.value.prompt.trim())
    }
    
    if (config.value.includeCoordinates) {
      formData.append('include_coordinates', 'true')
    }
    
    if (config.value.extractText) {
      formData.append('extract_text', 'true')
    }
    
    updateProgress('Enviando imagen al servidor...', 25)
    
    // Llamada a la API - PRESERVAR ENDPOINT EXACTO
    const response = await apiRequest('/api/multimedia/image', {
      method: 'POST',
      body: formData
    })
    
    updateProgress('Analizando imagen...', 75)
    
    // Simular progreso adicional
    await simulateProgress(75, 95, 'Finalizando análisis...')
    
    updateProgress('Completado', 100)
    
    // Guardar resultado
    result.value = response
    activeResultTab.value = 'description'
    
    // Agregar al historial
    addToRecentResults({
      filename: selectedImage.value.name,
      timestamp: Date.now(),
      status: 'success',
      result: response,
      thumbnail: imagePreviewUrl.value
    })
    
    appStore.addToLog('Image processing completed successfully', 'info')
    showNotification('Imagen analizada exitosamente', 'success')
    
    emit('completed', response)
    
  } catch (error) {
    appStore.addToLog(`Image processing failed: ${error.message}`, 'error')
    showNotification(`Error analizando imagen: ${error.message}`, 'error')
    
    // Agregar al historial como error
    addToRecentResults({
      filename: selectedImage.value.name,
      timestamp: Date.now(),
      status: 'error',
      error: error.message,
      thumbnail: imagePreviewUrl.value
    })
    
    emit('error', error)
    
  } finally {
    isProcessing.value = false
    processingProgress.value = 0
    processingStage.value = ''
  }
}

const updateProgress = (stage, progress) => {
  processingStage.value = stage
  processingProgress.value = progress
  
  emit('processing', { 
    message: stage, 
    progress 
  })
}

const simulateProgress = async (start, end, message) => {
  const steps = 10
  const increment = (end - start) / steps
  const delay = 100
  
  for (let i = 0; i < steps; i++) {
    await new Promise(resolve => setTimeout(resolve, delay))
    updateProgress(message, start + (increment * (i + 1)))
  }
}

// ============================================================================
// CÁMARA
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
// UTILIDADES
// ============================================================================

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatTime = (timestamp) => {
  return new Date(timestamp).toLocaleString()
}

const formatJSON = (obj) => {
  try {
    return JSON.stringify(obj, null, 2)
  } catch (error) {
    return 'Error formatting JSON: ' + error.message
  }
}

const formatAnalysisKey = (key) => {
  return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

const copyToClipboard = async (text) => {
  try {
    await navigator.clipboard.writeText(text)
    showNotification('Copiado al portapapeles', 'success')
  } catch (error) {
    showNotification('Error al copiar al portapapeles', 'error')
  }
}

const downloadDescription = () => {
  if (!result.value?.description) return
  
  const blob = new Blob([result.value.description], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  
  const a = document.createElement('a')
  a.href = url
  a.download = `image_description_${selectedImage.value.name.replace(/\.[^/.]+$/, '')}.txt`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  
  URL.revokeObjectURL(url)
  showNotification('Descripción descargada', 'success')
}

const downloadText = () => {
  if (!result.value?.extracted_text) return
  
  const blob = new Blob([result.value.extracted_text], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  
  const a = document.createElement('a')
  a.href = url
  a.download = `extracted_text_${selectedImage.value.name.replace(/\.[^/.]+$/, '')}.txt`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  
  URL.revokeObjectURL(url)
  showNotification('Texto descargado', 'success')
}

const downloadProcessedImage = () => {
  if (!result.value?.processed_image) return
  
  const a = document.createElement('a')
  a.href = result.value.processed_image
  a.download = `processed_${selectedImage.value.name}`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  
  showNotification('Imagen descargada', 'success')
}

const highlightObject = (obj) => {
  // Funcionalidad para resaltar objetos en la imagen
  // Se puede implementar con overlays CSS
  showNotification(`Objeto: ${obj.label} (${Math.round(obj.confidence * 100)}%)`, 'info')
}

// ============================================================================
// HISTORIAL
// ============================================================================

const addToRecentResults = (item) => {
  recentResults.value.unshift(item)
  
  // Mantener solo los últimos 5 resultados
  if (recentResults.value.length > 5) {
    recentResults.value.pop()
  }
  
  // Guardar en localStorage si está disponible
  try {
    localStorage.setItem('imageProcessorRecent', JSON.stringify(recentResults.value))
  } catch (error) {
    // Ignorar errores de localStorage
  }
}

const loadRecentResult = (item) => {
  if (item.status === 'success' && item.result) {
    result.value = item.result
    activeResultTab.value = 'description'
    showNotification('Resultado cargado del historial', 'info')
  }
}

const loadRecentResults = () => {
  try {
    const saved = localStorage.getItem('imageProcessorRecent')
    if (saved) {
      recentResults.value = JSON.parse(saved)
    }
  } catch (error) {
    // Ignorar errores de localStorage
  }
}

// ============================================================================
// LIFECYCLE
// ============================================================================

onMounted(async () => {
  loadRecentResults()
  
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
/* Estilos similares a AudioProcessor pero adaptados para imágenes */
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
  margin-bottom: 25px;
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

.analysis-config {
  margin-bottom: 25px;
}

.analysis-config h4 {
  color: var(--text-primary);
  margin-bottom: 15px;
}

.config-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
}

.config-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.config-item.full-width {
  grid-column: 1 / -1;
}

.config-item label {
  font-weight: 500;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.config-item select,
.config-item textarea {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
  color: var(--text-primary);
}

.config-item textarea {
  resize: vertical;
  min-height: 80px;
}

.config-item input[type="checkbox"] {
  margin: 0;
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

.result-tabs {
  display: flex;
  gap: 2px;
  margin-bottom: 15px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  padding: 4px;
  overflow-x: auto;
}

.result-tab {
  flex: 1;
  padding: 8px 12px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: var(--transition-fast);
  font-size: 0.9rem;
  white-space: nowrap;
  min-width: fit-content;
}

.result-tab.active {
  background: var(--bg-primary);
  color: var(--text-primary);
  box-shadow: var(--shadow-sm);
}

.result-content {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 20px;
}

.description-text {
  background: var(--bg-secondary);
  padding: 15px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-light);
  line-height: 1.6;
  margin-bottom: 15px;
  min-height: 100px;
  white-space: pre-wrap;
}

.description-actions,
.text-actions,
.processed-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
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

.objects-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
}

.object-item {
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  cursor: pointer;
  transition: var(--transition-fast);
}

.object-item:hover {
  background: var(--bg-tertiary);
  transform: translateY(-2px);
}

.object-label {
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.object-confidence {
  font-size: 0.9rem;
  color: var(--text-secondary);
  margin-bottom: 2px;
}

.object-coordinates {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.analysis-grid {
  display: grid;
  gap: 10px;
}

.analysis-item {
  display: flex;
  justify-content: space-between;
  padding: 10px;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
}

.analysis-item label {
  font-weight: 500;
  color: var(--text-primary);
}

.metadata-content pre {
  background: var(--bg-secondary);
  padding: 15px;
  border-radius: var(--radius-md);
  overflow-x: auto;
  font-size: 0.9rem;
}

.processed-image {
  margin-bottom: 15px;
  text-align: center;
}

.processed-image img {
  max-width: 100%;
  max-height: 400px;
  object-fit: contain;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
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

.recent-results {
  margin-top: 30px;
}

.recent-results h4 {
  color: var(--text-primary);
  margin-bottom: 15px;
}

.recent-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.recent-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: var(--transition-fast);
}

.recent-item:hover {
  background: var(--bg-tertiary);
  transform: translateX(4px);
}

.recent-thumbnail {
  width: 50px;
  height: 50px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  flex-shrink: 0;
}

.recent-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.no-thumbnail {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-tertiary);
  font-size: 1.5rem;
}

.recent-info {
  flex: 1;
}

.recent-name {
  font-weight: 500;
  color: var(--text-primary);
}

.recent-time {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.recent-status {
  font-size: 1.1rem;
}

.no-analysis {
  text-align: center;
  color: var(--text-secondary);
  padding: 40px;
}

@media (max-width: 768px) {
  .config-grid {
    grid-template-columns: 1fr;
  }
  
  .processor-controls {
    flex-direction: column;
  }
  
  .result-tabs {
    flex-direction: column;
  }
  
  .description-actions,
  .text-actions,
  .processed-actions {
    flex-direction: column;
  }
  
  .objects-grid {
    grid-template-columns: 1fr;
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
