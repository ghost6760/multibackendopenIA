<template>
  <div class="screen-capture">
    <h3 class="capture-title">🖥️ Captura de Pantalla</h3>
    
    <!-- Estado de captura -->
    <div class="capture-status">
      <div :class="['status-indicator', captureStatus]">
        <span class="status-icon">{{ statusIcon }}</span>
        <span class="status-text">{{ statusText }}</span>
      </div>
    </div>

    <!-- Controles principales -->
    <div class="capture-controls">
      <button 
        class="btn btn-primary"
        @click="startCapture"
        :disabled="isCapturing || !isSupported"
      >
        <span v-if="isCapturing">⏳ Capturando...</span>
        <span v-else>📸 Iniciar Captura</span>
      </button>
      
      <button 
        class="btn btn-secondary"
        @click="stopCapture"
        :disabled="!isCapturing"
      >
        🛑 Detener
      </button>
      
      <button 
        class="btn btn-info"
        @click="takeScreenshot"
        :disabled="isCapturing || !isSupported"
      >
        📷 Screenshot
      </button>
    </div>

    <!-- Configuración de captura -->
    <div class="capture-config">
      <h4>⚙️ Configuración</h4>
      
      <div class="config-grid">
        <div class="config-item">
          <label for="captureType">Tipo de captura:</label>
          <select id="captureType" v-model="config.captureType">
            <option value="screen">Pantalla completa</option>
            <option value="window">Ventana específica</option>
            <option value="tab">Pestaña del navegador</option>
          </select>
        </div>
        
        <div class="config-item">
          <label for="quality">Calidad:</label>
          <select id="quality" v-model="config.quality">
            <option value="low">Baja (720p)</option>
            <option value="medium">Media (1080p)</option>
            <option value="high">Alta (1440p)</option>
            <option value="ultra">Ultra (4K)</option>
          </select>
        </div>
        
        <div class="config-item">
          <label for="format">Formato:</label>
          <select id="format" v-model="config.format">
            <option value="png">PNG (Sin pérdida)</option>
            <option value="jpeg">JPEG (Comprimido)</option>
            <option value="webp">WebP (Moderno)</option>
          </select>
        </div>
        
        <div class="config-item">
          <label>
            <input 
              type="checkbox" 
              v-model="config.includeAudio"
            />
            Incluir audio del sistema
          </label>
        </div>
        
        <div class="config-item">
          <label>
            <input 
              type="checkbox" 
              v-model="config.showCursor"
            />
            Mostrar cursor del mouse
          </label>
        </div>
        
        <div class="config-item">
          <label>
            <input 
              type="checkbox" 
              v-model="config.autoDownload"
            />
            Descarga automática
          </label>
        </div>
      </div>
    </div>

    <!-- Preview de la captura activa -->
    <div v-if="isCapturing && previewStream" class="capture-preview">
      <h4>👁️ Vista Previa</h4>
      <div class="preview-container">
        <video 
          ref="previewVideo"
          :srcObject="previewStream"
          autoplay
          muted
          playsinline
        ></video>
        
        <div class="preview-overlay">
          <div class="recording-indicator">
            <span class="recording-dot"></span>
            <span>Capturando</span>
          </div>
          <div class="recording-time">{{ formatTime(recordingDuration) }}</div>
        </div>
      </div>
    </div>

    <!-- Galería de capturas -->
    <div v-if="captures.length > 0" class="captures-gallery">
      <h4>📁 Capturas Realizadas</h4>
      
      <div class="gallery-controls">
        <button @click="clearAllCaptures" class="btn btn-sm btn-secondary">
          🗑️ Limpiar Todo
        </button>
        <button @click="downloadAllCaptures" class="btn btn-sm btn-primary">
          💾 Descargar Todo
        </button>
      </div>
      
      <div class="gallery-grid">
        <div 
          v-for="(capture, index) in captures"
          :key="capture.id"
          class="capture-item"
        >
          <div class="capture-thumbnail">
            <img 
              v-if="capture.type === 'image'"
              :src="capture.url" 
              :alt="`Captura ${index + 1}`"
              @click="viewCapture(capture)"
            />
            <video 
              v-else
              :src="capture.url"
              @click="viewCapture(capture)"
              muted
            ></video>
            
            <div class="capture-overlay">
              <div class="capture-type">
                {{ capture.type === 'image' ? '📷' : '🎥' }}
              </div>
              <div class="capture-size">
                {{ formatFileSize(capture.size) }}
              </div>
            </div>
          </div>
          
          <div class="capture-info">
            <div class="capture-name">{{ capture.name }}</div>
            <div class="capture-time">{{ formatDateTime(capture.timestamp) }}</div>
          </div>
          
          <div class="capture-actions">
            <button @click="downloadCapture(capture)" class="btn btn-xs">
              💾
            </button>
            <button @click="shareCapture(capture)" class="btn btn-xs">
              📤
            </button>
            <button @click="deleteCapture(capture.id)" class="btn btn-xs btn-danger">
              🗑️
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal de vista previa -->
    <div v-if="selectedCapture" class="capture-modal" @click="closeModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h4>{{ selectedCapture.name }}</h4>
          <button @click="closeModal" class="close-button">✕</button>
        </div>
        
        <div class="modal-body">
          <img 
            v-if="selectedCapture.type === 'image'"
            :src="selectedCapture.url" 
            :alt="selectedCapture.name"
          />
          <video 
            v-else
            :src="selectedCapture.url"
            controls
            playsinline
          ></video>
        </div>
        
        <div class="modal-footer">
          <div class="capture-details">
            <span>{{ formatFileSize(selectedCapture.size) }}</span>
            <span>{{ formatDateTime(selectedCapture.timestamp) }}</span>
          </div>
          
          <div class="modal-actions">
            <button @click="downloadCapture(selectedCapture)" class="btn btn-primary">
              💾 Descargar
            </button>
            <button @click="shareCapture(selectedCapture)" class="btn btn-secondary">
              📤 Compartir
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Mensaje de no compatibilidad -->
    <div v-if="!isSupported" class="not-supported">
      <div class="not-supported-icon">⚠️</div>
      <h4>Funcionalidad No Disponible</h4>
      <p>
        Tu navegador no soporta captura de pantalla o la funcionalidad está deshabilitada.
      </p>
      <p>
        Por favor, usa Chrome, Firefox, Edge o Safari moderno con HTTPS.
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { useNotifications } from '@/composables/useNotifications'

// ============================================================================
// PROPS & EMITS
// ============================================================================

const emit = defineEmits(['capturing', 'completed', 'error'])

// ============================================================================
// STORES & COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const { showNotification } = useNotifications()

// ============================================================================
// REFS
// ============================================================================

const previewVideo = ref(null)

// ============================================================================
// ESTADO LOCAL
// ============================================================================

const isSupported = ref(false)
const isCapturing = ref(false)
const previewStream = ref(null)
const mediaRecorder = ref(null)
const recordingDuration = ref(0)
const recordingInterval = ref(null)
const selectedCapture = ref(null)

// Lista de capturas realizadas
const captures = ref([])

// Configuración de captura
const config = ref({
  captureType: 'screen',
  quality: 'medium',
  format: 'png',
  includeAudio: false,
  showCursor: true,
  autoDownload: true
})

// ============================================================================
// COMPUTED
// ============================================================================

const captureStatus = computed(() => {
  if (!isSupported.value) return 'not-supported'
  if (isCapturing.value) return 'capturing'
  return 'ready'
})

const statusIcon = computed(() => {
  switch (captureStatus.value) {
    case 'not-supported': return '⚠️'
    case 'capturing': return '🔴'
    case 'ready': return '✅'
    default: return '❓'
  }
})

const statusText = computed(() => {
  switch (captureStatus.value) {
    case 'not-supported': return 'No compatible'
    case 'capturing': return 'Capturando...'
    case 'ready': return 'Listo para capturar'
    default: return 'Estado desconocido'
  }
})

const qualityConstraints = computed(() => {
  const constraints = {
    low: { width: 1280, height: 720 },
    medium: { width: 1920, height: 1080 },
    high: { width: 2560, height: 1440 },
    ultra: { width: 3840, height: 2160 }
  }
  
  return constraints[config.value.quality] || constraints.medium
})

// ============================================================================
// MÉTODOS PRINCIPALES
// ============================================================================

/**
 * Inicia la captura de pantalla - MIGRADO: captureScreen() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const startCapture = async () => {
  if (!isSupported.value) {
    showNotification('Captura de pantalla no soportada', 'error')
    return
  }
  
  try {
    appStore.addToLog('Starting screen capture', 'info')
    emit('capturing', { message: 'Iniciando captura...', progress: 0 })
    
    // Configurar opciones de captura
    const displayMediaOptions = {
      video: {
        ...qualityConstraints.value,
        cursor: config.value.showCursor ? 'always' : 'never'
      },
      audio: config.value.includeAudio
    }
    
    // Obtener stream de pantalla
    const stream = await navigator.mediaDevices.getDisplayMedia(displayMediaOptions)
    
    previewStream.value = stream
    isCapturing.value = true
    recordingDuration.value = 0
    
    // Configurar MediaRecorder para grabación de video
    setupMediaRecorder(stream)
    
    // Iniciar contador de tiempo
    startRecordingTimer()
    
    // Listener para cuando el usuario detiene la captura
    stream.getVideoTracks()[0].addEventListener('ended', () => {
      stopCapture()
    })
    
    appStore.addToLog('Screen capture started successfully', 'info')
    showNotification('Captura de pantalla iniciada', 'success')
    
    emit('capturing', { message: 'Captura en progreso...', progress: 50 })
    
  } catch (error) {
    appStore.addToLog(`Screen capture failed: ${error.message}`, 'error')
    showNotification(`Error iniciando captura: ${error.message}`, 'error')
    emit('error', error)
    
    // Limpiar estado
    cleanupCapture()
  }
}

/**
 * Detiene la captura actual
 */
const stopCapture = () => {
  if (!isCapturing.value) return
  
  try {
    appStore.addToLog('Stopping screen capture', 'info')
    
    // Detener MediaRecorder
    if (mediaRecorder.value && mediaRecorder.value.state !== 'inactive') {
      mediaRecorder.value.stop()
    }
    
    // Limpiar recursos
    cleanupCapture()
    
    appStore.addToLog('Screen capture stopped', 'info')
    showNotification('Captura detenida', 'info')
    
    emit('completed', { message: 'Captura completada' })
    
  } catch (error) {
    appStore.addToLog(`Error stopping capture: ${error.message}`, 'error')
    showNotification(`Error deteniendo captura: ${error.message}`, 'error')
  }
}

/**
 * Toma una captura de pantalla (imagen estática)
 */
const takeScreenshot = async () => {
  if (!isSupported.value) {
    showNotification('Screenshots no soportados', 'error')
    return
  }
  
  try {
    appStore.addToLog('Taking screenshot', 'info')
    emit('capturing', { message: 'Tomando screenshot...', progress: 0 })
    
    // Obtener stream temporal
    const stream = await navigator.mediaDevices.getDisplayMedia({
      video: {
        ...qualityConstraints.value,
        cursor: config.value.showCursor ? 'always' : 'never'
      }
    })
    
    // Crear video temporal para capturar frame
    const video = document.createElement('video')
    video.srcObject = stream
    video.play()
    
    // Esperar a que el video esté listo
    await new Promise(resolve => {
      video.onloadedmetadata = resolve
    })
    
    emit('capturing', { message: 'Procesando imagen...', progress: 50 })
    
    // Crear canvas y capturar frame
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    
    const ctx = canvas.getContext('2d')
    ctx.drawImage(video, 0, 0)
    
    // Detener stream
    stream.getTracks().forEach(track => track.stop())
    
    // Convertir a blob según formato configurado
    const blob = await new Promise(resolve => {
      const mimeType = `image/${config.value.format}`
      const quality = config.value.format === 'jpeg' ? 0.9 : undefined
      canvas.toBlob(resolve, mimeType, quality)
    })
    
    emit('capturing', { message: 'Guardando captura...', progress: 90 })
    
    // Crear captura
    const capture = createCaptureObject(blob, 'image')
    captures.value.unshift(capture)
    
    // Auto-descarga si está habilitada
    if (config.value.autoDownload) {
      downloadCapture(capture)
    }
    
    appStore.addToLog('Screenshot completed successfully', 'info')
    showNotification('Screenshot tomado exitosamente', 'success')
    
    emit('completed', { capture })
    
  } catch (error) {
    appStore.addToLog(`Screenshot failed: ${error.message}`, 'error')
    showNotification(`Error tomando screenshot: ${error.message}`, 'error')
    emit('error', error)
  }
}

// ============================================================================
// MÉTODOS DE APOYO
// ============================================================================

const setupMediaRecorder = (stream) => {
  try {
    // Determinar formato de video
    const mimeTypes = [
      'video/webm;codecs=vp9',
      'video/webm;codecs=vp8',
      'video/webm',
      'video/mp4'
    ]
    
    let selectedMimeType = mimeTypes.find(type => MediaRecorder.isTypeSupported(type))
    
    if (!selectedMimeType) {
      throw new Error('No hay formatos de video soportados')
    }
    
    mediaRecorder.value = new MediaRecorder(stream, {
      mimeType: selectedMimeType,
      videoBitsPerSecond: getVideoBitrate()
    })
    
    const chunks = []
    
    mediaRecorder.value.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunks.push(event.data)
      }
    }
    
    mediaRecorder.value.onstop = () => {
      const blob = new Blob(chunks, { type: selectedMimeType })
      const capture = createCaptureObject(blob, 'video')
      captures.value.unshift(capture)
      
      if (config.value.autoDownload) {
        downloadCapture(capture)
      }
    }
    
    mediaRecorder.value.start(1000) // Capturar datos cada segundo
    
  } catch (error) {
    throw new Error(`Error configurando MediaRecorder: ${error.message}`)
  }
}

const getVideoBitrate = () => {
  const bitrates = {
    low: 2500000,      // 2.5 Mbps
    medium: 5000000,   // 5 Mbps
    high: 8000000,     // 8 Mbps
    ultra: 15000000    // 15 Mbps
  }
  
  return bitrates[config.value.quality] || bitrates.medium
}

const createCaptureObject = (blob, type) => {
  const timestamp = Date.now()
  const url = URL.createObjectURL(blob)
  
  return {
    id: `capture_${timestamp}`,
    name: `${type}_${new Date(timestamp).toISOString().replace(/[:.]/g, '-')}.${getFileExtension(type)}`,
    type,
    url,
    blob,
    size: blob.size,
    timestamp,
    format: type === 'image' ? config.value.format : 'webm'
  }
}

const getFileExtension = (type) => {
  if (type === 'image') {
    return config.value.format
  }
  return 'webm'
}

const startRecordingTimer = () => {
  recordingInterval.value = setInterval(() => {
    recordingDuration.value += 1
  }, 1000)
}

const cleanupCapture = () => {
  isCapturing.value = false
  
  // Detener stream
  if (previewStream.value) {
    previewStream.value.getTracks().forEach(track => track.stop())
    previewStream.value = null
  }
  
  // Limpiar timer
  if (recordingInterval.value) {
    clearInterval(recordingInterval.value)
    recordingInterval.value = null
  }
  
  recordingDuration.value = 0
}

// ============================================================================
// GESTIÓN DE GALERÍA
// ============================================================================

const viewCapture = (capture) => {
  selectedCapture.value = capture
}

const closeModal = () => {
  selectedCapture.value = null
}

const downloadCapture = (capture) => {
  try {
    const a = document.createElement('a')
    a.href = capture.url
    a.download = capture.name
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    
    showNotification(`${capture.type === 'image' ? 'Imagen' : 'Video'} descargado`, 'success')
  } catch (error) {
    showNotification('Error descargando archivo', 'error')
  }
}

const shareCapture = async (capture) => {
  try {
    if (navigator.share && navigator.canShare) {
      const shareData = {
        title: capture.name,
        files: [new File([capture.blob], capture.name, { type: capture.blob.type })]
      }
      
      if (navigator.canShare(shareData)) {
        await navigator.share(shareData)
        showNotification('Compartido exitosamente', 'success')
        return
      }
    }
    
    // Fallback: copiar al portapapeles
    await navigator.clipboard.write([
      new ClipboardItem({
        [capture.blob.type]: capture.blob
      })
    ])
    
    showNotification('Copiado al portapapeles', 'success')
    
  } catch (error) {
    showNotification('Error compartiendo archivo', 'error')
  }
}

const deleteCapture = (captureId) => {
  const index = captures.value.findIndex(c => c.id === captureId)
  if (index !== -1) {
    const capture = captures.value[index]
    URL.revokeObjectURL(capture.url)
    captures.value.splice(index, 1)
    showNotification('Captura eliminada', 'info')
  }
}

const clearAllCaptures = () => {
  captures.value.forEach(capture => {
    URL.revokeObjectURL(capture.url)
  })
  captures.value = []
  selectedCapture.value = null
  showNotification('Todas las capturas eliminadas', 'info')
}

const downloadAllCaptures = () => {
  captures.value.forEach(capture => {
    setTimeout(() => downloadCapture(capture), 100)
  })
}

// ============================================================================
// UTILIDADES
// ============================================================================

const formatTime = (seconds) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

const formatDateTime = (timestamp) => {
  return new Date(timestamp).toLocaleString()
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const checkSupport = () => {
  isSupported.value = !!(
    navigator.mediaDevices && 
    navigator.mediaDevices.getDisplayMedia &&
    window.location.protocol === 'https:' || 
    window.location.hostname === 'localhost'
  )
  
  if (!isSupported.value) {
    appStore.addToLog('Screen capture not supported in this environment', 'warning')
  }
}

// ============================================================================
// LIFECYCLE
// ============================================================================

onMounted(() => {
  checkSupport()
  appStore.addToLog('ScreenCapture component mounted', 'info')
  
  // EXPONER FUNCIÓN GLOBAL PARA COMPATIBILIDAD
  window.captureScreen = takeScreenshot
})

onUnmounted(() => {
  // Limpiar recursos
  cleanupCapture()
  clearAllCaptures()
  
  // Limpiar función global
  if (typeof window !== 'undefined') {
    delete window.captureScreen
  }
  
  appStore.addToLog('ScreenCapture component unmounted', 'info')
})

// Watchers para logging de cambios
watch(() => config.value.quality, (newQuality) => {
  appStore.addToLog(`Screen capture quality changed to: ${newQuality}`, 'info')
})
</script>

<style scoped>
.screen-capture {
  padding: 20px;
  height: 100%;
}

.capture-title {
  color: var(--text-primary);
  margin-bottom: 20px;
  font-size: 1.4rem;
}

.capture-status {
  margin-bottom: 20px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  font-weight: 500;
}

.status-indicator.ready {
  background: rgba(72, 187, 120, 0.1);
  color: var(--success-color);
  border: 1px solid var(--success-color);
}

.status-indicator.capturing {
  background: rgba(245, 101, 101, 0.1);
  color: var(--error-color);
  border: 1px solid var(--error-color);
}

.status-indicator.not-supported {
  background: rgba(237, 137, 54, 0.1);
  color: var(--warning-color);
  border: 1px solid var(--warning-color);
}

.status-icon {
  font-size: 1.2rem;
}

.capture-controls {
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

.btn-danger {
  background: var(--error-color);
  color: white;
}

.btn-xs {
  padding: 4px 8px;
  font-size: 0.8rem;
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

.capture-config {
  margin-bottom: 25px;
}

.capture-config h4 {
  color: var(--text-primary);
  margin-bottom: 15px;
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.config-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.config-item label {
  font-weight: 500;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.config-item select {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
  color: var(--text-primary);
}

.config-item input[type="checkbox"] {
  margin: 0;
}

.capture-preview {
  margin-bottom: 25px;
}

.capture-preview h4 {
  color: var(--text-primary);
  margin-bottom: 15px;
}

.preview-container {
  position: relative;
  background: #000;
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.preview-container video {
  width: 100%;
  max-height: 300px;
  object-fit: contain;
}

.preview-overlay {
  position: absolute;
  top: 15px;
  left: 15px;
  right: 15px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.recording-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
}

.recording-dot {
  width: 8px;
  height: 8px;
  background: #ff4444;
  border-radius: 50%;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.recording-time {
  background: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  font-family: monospace;
  font-size: 0.9rem;
}

.captures-gallery {
  margin-bottom: 25px;
}

.captures-gallery h4 {
  color: var(--text-primary);
  margin-bottom: 15px;
}

.gallery-controls {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
}

.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 15px;
}

.capture-item {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: var(--transition-normal);
}

.capture-item:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.capture-thumbnail {
  position: relative;
  aspect-ratio: 16/9;
  overflow: hidden;
  background: var(--bg-tertiary);
}

.capture-thumbnail img,
.capture-thumbnail video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  cursor: pointer;
}

.capture-overlay {
  position: absolute;
  top: 8px;
  left: 8px;
  right: 8px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.capture-type {
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
}

.capture-size {
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  font-size: 0.7rem;
}

.capture-info {
  padding: 12px;
}

.capture-name {
  font-weight: 500;
  color: var(--text-primary);
  font-size: 0.9rem;
  margin-bottom: 4px;
  word-break: break-all;
}

.capture-time {
  color: var(--text-secondary);
  font-size: 0.8rem;
}

.capture-actions {
  display: flex;
  gap: 5px;
  padding: 8px 12px;
  background: var(--bg-secondary);
  justify-content: center;
}

.capture-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  max-width: 90vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  border-bottom: 1px solid var(--border-color);
}

.modal-header h4 {
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

.modal-body {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: #000;
}

.modal-body img,
.modal-body video {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.modal-footer {
  padding: 15px 20px;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 15px;
}

.capture-details {
  display: flex;
  gap: 15px;
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.modal-actions {
  display: flex;
  gap: 10px;
}

.not-supported {
  text-align: center;
  padding: 40px;
  color: var(--text-secondary);
}

.not-supported-icon {
  font-size: 4rem;
  margin-bottom: 20px;
}

.not-supported h4 {
  color: var(--text-primary);
  margin-bottom: 15px;
}

.not-supported p {
  margin-bottom: 10px;
  line-height: 1.6;
}

@media (max-width: 768px) {
  .capture-controls {
    flex-direction: column;
  }
  
  .config-grid {
    grid-template-columns: 1fr;
  }
  
  .gallery-grid {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  }
  
  .gallery-controls {
    flex-direction: column;
  }
  
  .modal-content {
    margin: 10px;
    max-width: calc(100vw - 20px);
    max-height: calc(100vh - 20px);
  }
  
  .modal-footer {
    flex-direction: column;
    align-items: stretch;
  }
  
  .capture-details {
    justify-content: center;
  }
  
  .modal-actions {
    justify-content: center;
  }
}
</style>
