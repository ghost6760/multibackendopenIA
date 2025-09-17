<template>
  <div class="multimedia-tab">
    <!-- Header del tab -->
    <div class="tab-header">
      <h2 class="tab-title">🎤 Procesamiento Multimedia</h2>
      <p class="tab-subtitle">
        Procesamiento de audio, imágenes y captura de pantalla
      </p>
    </div>

    <!-- Grid principal de componentes multimedia -->
    <div class="multimedia-grid">
      <!-- Audio Processor -->
      <div class="multimedia-card">
        <AudioProcessor 
          ref="audioProcessorRef"
          @processing="onAudioProcessing"
          @completed="onAudioCompleted"
          @error="onAudioError"
        />
      </div>

      <!-- Image Processor -->
      <div class="multimedia-card">
        <ImageProcessor 
          ref="imageProcessorRef"
          @processing="onImageProcessing"
          @completed="onImageCompleted" 
          @error="onImageError"
        />
      </div>

      <!-- Screen Capture -->
      <div class="multimedia-card">
        <ScreenCapture 
          ref="screenCaptureRef"
          @capturing="onScreenCapturing"
          @completed="onScreenCaptureCompleted"
          @error="onScreenCaptureError"
        />
      </div>

      <!-- Voice Recorder -->
      <div class="multimedia-card">
        <VoiceRecorder 
          ref="voiceRecorderRef"
          @recording="onVoiceRecording"
          @stopped="onVoiceRecordingStopped"
          @error="onVoiceRecordingError"
        />
      </div>
    </div>

    <!-- Resultados y testing -->
    <div class="multimedia-results">
      <div class="card">
        <h3>🧪 Test de Integración Multimedia</h3>
        <div class="integration-controls">
          <button 
            class="btn btn-primary" 
            @click="testMultimediaIntegration"
            :disabled="isTestingIntegration"
          >
            <span v-if="isTestingIntegration">⏳ Probando...</span>
            <span v-else>🔄 Probar Integración</span>
          </button>
          
          <button 
            class="btn btn-secondary" 
            @click="clearResults"
          >
            🗑️ Limpiar Resultados
          </button>
        </div>
        
        <!-- Resultados del test -->
        <div v-if="integrationResults" class="integration-results">
          <h4>📊 Resultados del Test</h4>
          <div class="result-grid">
            <div 
              v-for="(result, service) in integrationResults" 
              :key="service"
              :class="['result-item', result.status]"
            >
              <div class="result-header">
                <span class="result-icon">{{ result.icon }}</span>
                <span class="result-service">{{ result.service }}</span>
                <span :class="['result-status', result.status]">
                  {{ result.status.toUpperCase() }}
                </span>
              </div>
              
              <div v-if="result.message" class="result-message">
                {{ result.message }}
              </div>
              
              <div v-if="result.details" class="result-details">
                <details>
                  <summary>Ver detalles</summary>
                  <pre>{{ formatJSON(result.details) }}</pre>
                </details>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Sistema de progreso global -->
    <div v-if="globalProgress.active" class="global-progress">
      <div class="progress-header">
        <span class="progress-title">{{ globalProgress.title }}</span>
        <span class="progress-percentage">{{ globalProgress.percentage }}%</span>
      </div>
      <div class="progress-bar">
        <div 
          class="progress-fill" 
          :style="{ width: globalProgress.percentage + '%' }"
        ></div>
      </div>
      <div v-if="globalProgress.message" class="progress-message">
        {{ globalProgress.message }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'
import AudioProcessor from './AudioProcessor.vue'
import ImageProcessor from './ImageProcessor.vue'
import ScreenCapture from './ScreenCapture.vue'
import VoiceRecorder from './VoiceRecorder.vue'

// ============================================================================
// STORES & COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const { apiRequest } = useApiRequest()
const { showNotification } = useNotifications()

// ============================================================================
// REFS A COMPONENTES HIJOS
// ============================================================================

const audioProcessorRef = ref(null)
const imageProcessorRef = ref(null)
const screenCaptureRef = ref(null)
const voiceRecorderRef = ref(null)

// ============================================================================
// ESTADO LOCAL
// ============================================================================

const isTestingIntegration = ref(false)
const integrationResults = ref(null)
const globalProgress = ref({
  active: false,
  title: '',
  message: '',
  percentage: 0
})

// ============================================================================
// FUNCIONES MIGRADAS DEL SCRIPT.JS ORIGINAL
// ============================================================================

/**
 * Procesa archivo de audio - MIGRADO: processAudio() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const processAudio = async (audioFile, options = {}) => {
  if (!audioFile) {
    showNotification('Por favor selecciona un archivo de audio', 'warning')
    return null
  }

  updateGlobalProgress(true, 'Procesando Audio', 'Preparando archivo...', 0)
  
  try {
    appStore.addToLog(`Starting audio processing: ${audioFile.name}`, 'info')
    
    // Crear FormData para el archivo
    const formData = new FormData()
    formData.append('audio', audioFile)
    
    // Agregar opciones adicionales si existen
    if (options.language) formData.append('language', options.language)
    if (options.prompt) formData.append('prompt', options.prompt)
    
    updateGlobalProgress(true, 'Procesando Audio', 'Enviando al servidor...', 25)
    
    // Llamada a la API - PRESERVAR ENDPOINT EXACTO
    const response = await apiRequest('/api/multimedia/audio', {
      method: 'POST',
      body: formData
    })
    
    updateGlobalProgress(true, 'Procesando Audio', 'Procesando respuesta...', 75)
    
    appStore.addToLog('Audio processing completed successfully', 'info')
    showNotification('Audio procesado exitosamente', 'success')
    
    updateGlobalProgress(true, 'Procesando Audio', 'Completado', 100)
    
    setTimeout(() => {
      updateGlobalProgress(false)
    }, 1000)
    
    return response
    
  } catch (error) {
    appStore.addToLog(`Audio processing failed: ${error.message}`, 'error')
    showNotification(`Error procesando audio: ${error.message}`, 'error')
    updateGlobalProgress(false)
    throw error
  }
}

/**
 * Procesa imagen - MIGRADO: processImage() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const processImage = async (imageFile, options = {}) => {
  if (!imageFile) {
    showNotification('Por favor selecciona una imagen', 'warning')
    return null
  }

  updateGlobalProgress(true, 'Procesando Imagen', 'Preparando imagen...', 0)
  
  try {
    appStore.addToLog(`Starting image processing: ${imageFile.name}`, 'info')
    
    // Crear FormData para la imagen
    const formData = new FormData()
    formData.append('image', imageFile)
    
    // Agregar opciones adicionales
    if (options.analysis_type) formData.append('analysis_type', options.analysis_type)
    if (options.prompt) formData.append('prompt', options.prompt)
    
    updateGlobalProgress(true, 'Procesando Imagen', 'Enviando al servidor...', 25)
    
    // Llamada a la API - PRESERVAR ENDPOINT EXACTO
    const response = await apiRequest('/api/multimedia/image', {
      method: 'POST',
      body: formData
    })
    
    updateGlobalProgress(true, 'Procesando Imagen', 'Analizando imagen...', 75)
    
    appStore.addToLog('Image processing completed successfully', 'info')
    showNotification('Imagen procesada exitosamente', 'success')
    
    updateGlobalProgress(true, 'Procesando Imagen', 'Completado', 100)
    
    setTimeout(() => {
      updateGlobalProgress(false)
    }, 1000)
    
    return response
    
  } catch (error) {
    appStore.addToLog(`Image processing failed: ${error.message}`, 'error')
    showNotification(`Error procesando imagen: ${error.message}`, 'error')
    updateGlobalProgress(false)
    throw error
  }
}

/**
 * Prueba la integración multimedia - MIGRADO: testMultimediaIntegration() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const testMultimediaIntegration = async () => {
  isTestingIntegration.value = true
  updateGlobalProgress(true, 'Test de Integración', 'Iniciando pruebas...', 0)
  
  try {
    appStore.addToLog('Starting multimedia integration test', 'info')
    
    updateGlobalProgress(true, 'Test de Integración', 'Probando conexión...', 25)
    
    // Llamada a la API de test - PRESERVAR ENDPOINT EXACTO
    const response = await apiRequest('/api/multimedia/test')
    
    updateGlobalProgress(true, 'Test de Integración', 'Analizando resultados...', 75)
    
    // Procesar resultados
    integrationResults.value = response.results || {}
    
    appStore.addToLog('Multimedia integration test completed', 'info')
    showNotification('Test de integración completado', 'success')
    
    updateGlobalProgress(true, 'Test de Integración', 'Completado', 100)
    
    setTimeout(() => {
      updateGlobalProgress(false)
    }, 1000)
    
  } catch (error) {
    appStore.addToLog(`Multimedia integration test failed: ${error.message}`, 'error')
    showNotification(`Error en test de integración: ${error.message}`, 'error')
    updateGlobalProgress(false)
  } finally {
    isTestingIntegration.value = false
  }
}

/**
 * Captura de pantalla - MIGRADO: captureScreen() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const captureScreen = async () => {
  try {
    appStore.addToLog('Starting screen capture', 'info')
    
    // Verificar soporte del navegador
    if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
      throw new Error('Screen capture no es soportado en este navegador')
    }
    
    showNotification('Iniciando captura de pantalla...', 'info')
    
    // Solicitar captura de pantalla
    const stream = await navigator.mediaDevices.getDisplayMedia({
      video: {
        mediaSource: 'screen',
        width: { ideal: 1920 },
        height: { ideal: 1080 }
      },
      audio: false
    })
    
    // Crear canvas para capturar frame
    const video = document.createElement('video')
    video.srcObject = stream
    video.play()
    
    // Esperar a que el video esté listo
    await new Promise(resolve => {
      video.onloadedmetadata = resolve
    })
    
    // Capturar frame
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    
    const ctx = canvas.getContext('2d')
    ctx.drawImage(video, 0, 0)
    
    // Detener stream
    stream.getTracks().forEach(track => track.stop())
    
    // Convertir a blob
    const blob = await new Promise(resolve => {
      canvas.toBlob(resolve, 'image/png')
    })
    
    appStore.addToLog('Screen capture completed successfully', 'info')
    showNotification('Captura de pantalla completada', 'success')
    
    return blob
    
  } catch (error) {
    appStore.addToLog(`Screen capture failed: ${error.message}`, 'error')
    showNotification(`Error en captura de pantalla: ${error.message}`, 'error')
    throw error
  }
}

/**
 * Toggle grabación de voz - MIGRADO: toggleVoiceRecording() de script.js
 */
const toggleVoiceRecording = () => {
  if (voiceRecorderRef.value) {
    voiceRecorderRef.value.toggleRecording()
  }
}

// ============================================================================
// EVENT HANDLERS PARA COMPONENTES HIJOS
// ============================================================================

const onAudioProcessing = (data) => {
  updateGlobalProgress(true, 'Procesando Audio', data.message || 'Procesando...', data.progress || 0)
}

const onAudioCompleted = (result) => {
  showNotification('Audio procesado exitosamente', 'success')
  updateGlobalProgress(false)
}

const onAudioError = (error) => {
  showNotification(`Error procesando audio: ${error.message}`, 'error')
  updateGlobalProgress(false)
}

const onImageProcessing = (data) => {
  updateGlobalProgress(true, 'Procesando Imagen', data.message || 'Procesando...', data.progress || 0)
}

const onImageCompleted = (result) => {
  showNotification('Imagen procesada exitosamente', 'success')
  updateGlobalProgress(false)
}

const onImageError = (error) => {
  showNotification(`Error procesando imagen: ${error.message}`, 'error')
  updateGlobalProgress(false)
}

const onScreenCapturing = (data) => {
  updateGlobalProgress(true, 'Capturando Pantalla', data.message || 'Capturando...', data.progress || 0)
}

const onScreenCaptureCompleted = (result) => {
  showNotification('Captura de pantalla completada', 'success')
  updateGlobalProgress(false)
}

const onScreenCaptureError = (error) => {
  showNotification(`Error capturando pantalla: ${error.message}`, 'error')
  updateGlobalProgress(false)
}

const onVoiceRecording = (data) => {
  // Voice recording events
}

const onVoiceRecordingStopped = (result) => {
  showNotification('Grabación de voz completada', 'success')
}

const onVoiceRecordingError = (error) => {
  showNotification(`Error en grabación de voz: ${error.message}`, 'error')
}

// ============================================================================
// UTILIDADES
// ============================================================================

const updateGlobalProgress = (active, title = '', message = '', percentage = 0) => {
  globalProgress.value = {
    active,
    title,
    message,
    percentage: Math.min(100, Math.max(0, percentage))
  }
}

const clearResults = () => {
  integrationResults.value = null
  showNotification('Resultados limpiados', 'info')
}

const formatJSON = (obj) => {
  try {
    return JSON.stringify(obj, null, 2)
  } catch (error) {
    return 'Error formatting JSON: ' + error.message
  }
}

// ============================================================================
// LIFECYCLE & WATCHERS
// ============================================================================

onMounted(() => {
  appStore.addToLog('MultimediaTab component mounted', 'info')
  
  // EXPONER FUNCIONES GLOBALES PARA COMPATIBILIDAD
  window.processAudio = processAudio
  window.processImage = processImage
  window.testMultimediaIntegration = testMultimediaIntegration
  window.captureScreen = captureScreen
  window.toggleVoiceRecording = toggleVoiceRecording
})

onUnmounted(() => {
  // Limpiar funciones globales
  if (typeof window !== 'undefined') {
    delete window.processAudio
    delete window.processImage
    delete window.testMultimediaIntegration
    delete window.captureScreen
    delete window.toggleVoiceRecording
  }
  
  appStore.addToLog('MultimediaTab component unmounted', 'info')
})

// Watcher para cargar datos cuando el tab se activa
watch(() => appStore.activeTab, (newTab) => {
  if (newTab === 'multimedia') {
    // Verificar permisos y capacidades del navegador
    checkMultimediaCapabilities()
  }
})

const checkMultimediaCapabilities = () => {
  const capabilities = {
    audio: !!navigator.mediaDevices?.getUserMedia,
    screen: !!navigator.mediaDevices?.getDisplayMedia,
    files: !!window.File && !!window.FileReader
  }
  
  appStore.addToLog(`Multimedia capabilities: ${JSON.stringify(capabilities)}`, 'info')
}
</script>

<style scoped>
.multimedia-tab {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.tab-header {
  margin-bottom: 30px;
  text-align: center;
}

.tab-title {
  font-size: 2rem;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.tab-subtitle {
  color: var(--text-secondary);
  font-size: 1.1rem;
}

.multimedia-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.multimedia-card {
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  transition: var(--transition-normal);
}

.multimedia-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.multimedia-results {
  margin-top: 30px;
}

.card {
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}

.card h3 {
  color: var(--text-primary);
  margin-bottom: 15px;
  font-size: 1.3rem;
}

.integration-controls {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
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

.btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.integration-results {
  margin-top: 20px;
}

.result-grid {
  display: grid;
  gap: 15px;
  margin-top: 15px;
}

.result-item {
  padding: 15px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.result-item.success {
  background: rgba(72, 187, 120, 0.1);
  border-color: var(--success-color);
}

.result-item.error {
  background: rgba(245, 101, 101, 0.1);
  border-color: var(--error-color);
}

.result-item.warning {
  background: rgba(237, 137, 54, 0.1);
  border-color: var(--warning-color);
}

.result-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.result-icon {
  font-size: 1.2rem;
}

.result-service {
  font-weight: 500;
  flex: 1;
}

.result-status {
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
}

.result-status.success {
  background: var(--success-color);
  color: white;
}

.result-status.error {
  background: var(--error-color);
  color: white;
}

.result-status.warning {
  background: var(--warning-color);
  color: white;
}

.result-message {
  color: var(--text-secondary);
  margin-bottom: 10px;
}

.result-details {
  margin-top: 10px;
}

.result-details details {
  cursor: pointer;
}

.result-details pre {
  background: var(--bg-tertiary);
  padding: 10px;
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
  overflow-x: auto;
  margin-top: 8px;
}

.global-progress {
  position: fixed;
  top: 20px;
  right: 20px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 15px;
  box-shadow: var(--shadow-lg);
  min-width: 300px;
  z-index: 1000;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.progress-title {
  font-weight: 500;
  color: var(--text-primary);
}

.progress-percentage {
  color: var(--primary-color);
  font-weight: 600;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-fill {
  height: 100%;
  background: var(--primary-color);
  border-radius: var(--radius-sm);
  transition: width 0.3s ease;
}

.progress-message {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

@media (max-width: 768px) {
  .multimedia-grid {
    grid-template-columns: 1fr;
  }
  
  .global-progress {
    top: 10px;
    right: 10px;
    left: 10px;
    min-width: auto;
  }
  
  .integration-controls {
    flex-direction: column;
  }
  
  .btn {
    justify-content: center;
  }
}
</style>
