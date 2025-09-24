<template>
  <div class="multimedia-tab">
    <!-- Header del tab -->
    <div class="tab-header">
      <h2 class="tab-title">🎤 Procesamiento Multimedia</h2>
      <p class="tab-subtitle">
        Procesamiento de audio, imágenes y captura de pantalla
      </p>
      
      <!-- Indicador de capacidades -->
      <div class="capabilities-indicator">
        <div 
          v-for="(available, capability) in multimediaCapabilities"
          :key="capability"
          :class="['capability-badge', { available, unavailable: !available }]"
        >
          {{ getCapabilityIcon(capability) }} {{ formatCapabilityName(capability) }}
        </div>
      </div>
    </div>

    <!-- Grid principal de componentes multimedia -->
    <div class="multimedia-grid">
      <!-- Audio Processor -->
      <div class="multimedia-card">
        <AudioProcessor 
          ref="audioProcessorRef"
          :is-processing="isProcessingAudio"
          :results="audioResults"
          :progress="processingProgress"
          @process-audio="handleProcessAudio"
          @clear-results="clearResults"
        />
      </div>

      <!-- Image Processor -->
      <div class="multimedia-card">
        <ImageProcessor 
          ref="imageProcessorRef"
          :is-processing="isProcessingImage"
          :results="imageResults"
          :progress="processingProgress"
          @process-image="handleProcessImage"
          @clear-results="clearResults"
        />
      </div>

      <!-- Screen Capture -->
      <div class="multimedia-card">
        <ScreenCapture 
          ref="screenCaptureRef"
          :is-capturing="isCapturingScreen"
          :results="screenCaptureResults"
          @capture-screen="handleCaptureScreen"
          @clear-results="clearResults"
        />
      </div>

      <!-- Voice Recorder -->
      <div class="multimedia-card">
        <VoiceRecorder 
          ref="voiceRecorderRef"
          :is-recording="isRecording"
          :duration="recordingDuration"
          :results="voiceRecordingResults"
          @toggle-recording="handleToggleVoiceRecording"
          @clear-results="clearResults"
        />
      </div>
    </div>

    <!-- Test de Integración -->
    <div class="integration-section">
      <div class="card">
        <h3>🧪 Test de Integración Multimedia</h3>
        <div class="integration-controls">
          <button 
            class="btn btn-primary" 
            @click="handleTestIntegration"
            :disabled="isTestingIntegration || isAnyProcessing"
          >
            <span v-if="isTestingIntegration">⏳ Probando...</span>
            <span v-else>🔄 Probar Integración</span>
          </button>
          
          <button 
            class="btn btn-secondary" 
            @click="clearAllResults"
            :disabled="isAnyProcessing"
          >
            🗑️ Limpiar Todo
          </button>
          
          <button 
            class="btn btn-info" 
            @click="checkCapabilities"
          >
            🔍 Verificar Capacidades
          </button>
        </div>
        
        <!-- Resultados del test -->
        <div v-if="integrationResults" class="integration-results">
          <h4>📊 Resultados del Test</h4>
          <div class="result-grid">
            <div 
              v-for="(result, service) in parseIntegrationResults(integrationResults)" 
              :key="service"
              :class="['result-item', getResultStatus(result)]"
            >
              <div class="result-header">
                <span class="result-icon">{{ getServiceIcon(service) }}</span>
                <span class="result-service">{{ formatServiceName(service) }}</span>
                <span :class="['result-status', getResultStatus(result)]">
                  {{ getResultStatus(result).toUpperCase() }}
                </span>
              </div>
              
              <div v-if="result.message || result.description" class="result-message">
                {{ result.message || result.description }}
              </div>
              
              <div v-if="result.details" class="result-details">
                <details>
                  <summary>Ver detalles</summary>
                  <pre>{{ formatJSON(result.details) }}</pre>
                </details>
              </div>
            </div>
          </div>
          
          <!-- Información adicional del test -->
          <div v-if="integrationResults.openai_service_available !== undefined" class="additional-info">
            <div class="info-item">
              <span class="info-label">OpenAI disponible:</span>
              <span :class="['info-value', integrationResults.openai_service_available ? 'success' : 'error']">
                {{ integrationResults.openai_service_available ? '✅ Disponible' : '❌ No disponible' }}
              </span>
            </div>
            <div class="info-item">
              <span class="info-label">Empresa:</span>
              <span class="info-value">{{ integrationResults.company_id || appStore.currentCompanyId }}</span>
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

    <!-- Alertas de estado -->
    <div v-if="!appStore.currentCompanyId" class="company-warning">
      <div class="warning-content">
        <span class="warning-icon">⚠️</span>
        <span class="warning-text">Selecciona una empresa para usar las funciones multimedia</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { useAppStore } from '@/stores/app'
import { useMultimedia } from '@/composables/useMultimedia'
import { useNotifications } from '@/composables/useNotifications'
import AudioProcessor from './AudioProcessor.vue'
import ImageProcessor from './ImageProcessor.vue'
import ScreenCapture from './ScreenCapture.vue'
import VoiceRecorder from './VoiceRecorder.vue'

// ============================================================================
// STORES & COMPOSABLES - SIN DUPLICAR FUNCIONES
// ============================================================================

const appStore = useAppStore()
const { showNotification } = useNotifications()

// USAR COMPOSABLE - EVITAR DUPLICACIONES
const {
  // Estado reactivo
  isProcessingAudio,
  isProcessingImage,
  isTestingIntegration,
  isRecording,
  isCapturingScreen,
  isAnyProcessing,
  processingProgress,
  recordingDuration,
  
  // Resultados
  audioResults,
  imageResults,
  integrationResults,
  screenCaptureResults,
  voiceRecordingResults,
  
  // Capacidades
  multimediaCapabilities,

  // Funciones principales - USAR COMPOSABLE DIRECTAMENTE
  processAudio,
  processImage,
  testMultimediaIntegration,
  captureScreen,
  toggleVoiceRecording,

  // Funciones auxiliares
  checkMultimediaCapabilities,
  clearResults,
  formatFileSize
} = useMultimedia()

// ============================================================================
// REFS A COMPONENTES HIJOS
// ============================================================================

const audioProcessorRef = ref(null)
const imageProcessorRef = ref(null)
const screenCaptureRef = ref(null)
const voiceRecorderRef = ref(null)

// ============================================================================
// ESTADO LOCAL DEL COMPONENTE - SOLO LO NECESARIO
// ============================================================================

const globalProgress = ref({
  active: false,
  title: '',
  message: '',
  percentage: 0
})

// ============================================================================
// COMPUTED
// ============================================================================

const canUseMultimedia = computed(() => {
  return !!appStore.currentCompanyId && Object.values(multimediaCapabilities.value).some(Boolean)
})

// ============================================================================
// EVENT HANDLERS - DELEGAR AL COMPOSABLE
// ============================================================================

/**
 * Maneja procesamiento de audio - DELEGAR AL COMPOSABLE
 */
const handleProcessAudio = async (audioFile, options = {}) => {
  updateGlobalProgress(true, 'Procesando Audio', 'Iniciando...', 0)
  
  try {
    const result = await processAudio(audioFile, options)
    updateGlobalProgress(true, 'Procesando Audio', 'Completado', 100)
    
    setTimeout(() => {
      updateGlobalProgress(false)
    }, 1000)
    
    return result
    
  } catch (error) {
    updateGlobalProgress(false)
    throw error
  }
}

/**
 * Maneja procesamiento de imagen - DELEGAR AL COMPOSABLE
 */
const handleProcessImage = async (imageFile, options = {}) => {
  updateGlobalProgress(true, 'Procesando Imagen', 'Iniciando...', 0)
  
  try {
    const result = await processImage(imageFile, options)
    updateGlobalProgress(true, 'Procesando Imagen', 'Completado', 100)
    
    setTimeout(() => {
      updateGlobalProgress(false)
    }, 1000)
    
    return result
    
  } catch (error) {
    updateGlobalProgress(false)
    throw error
  }
}

/**
 * Maneja captura de pantalla - DELEGAR AL COMPOSABLE
 */
const handleCaptureScreen = async (options = {}) => {
  updateGlobalProgress(true, 'Capturando Pantalla', 'Iniciando...', 0)
  
  try {
    const result = await captureScreen(options)
    updateGlobalProgress(true, 'Capturando Pantalla', 'Completado', 100)
    
    setTimeout(() => {
      updateGlobalProgress(false)
    }, 1000)
    
    return result
    
  } catch (error) {
    updateGlobalProgress(false)
    throw error
  }
}

/**
 * Maneja grabación de voz - DELEGAR AL COMPOSABLE
 */
const handleToggleVoiceRecording = async () => {
  try {
    await toggleVoiceRecording()
  } catch (error) {
    showNotification(`Error en grabación: ${error.message}`, 'error')
  }
}

/**
 * Maneja test de integración - DELEGAR AL COMPOSABLE
 */
const handleTestIntegration = async () => {
  updateGlobalProgress(true, 'Test de Integración', 'Iniciando...', 0)
  
  try {
    const result = await testMultimediaIntegration()
    updateGlobalProgress(true, 'Test de Integración', 'Completado', 100)
    
    setTimeout(() => {
      updateGlobalProgress(false)
    }, 1000)
    
    return result
    
  } catch (error) {
    updateGlobalProgress(false)
    throw error
  }
}

// ============================================================================
// UTILIDADES DEL COMPONENTE
// ============================================================================

const updateGlobalProgress = (active, title = '', message = '', percentage = 0) => {
  globalProgress.value = {
    active,
    title,
    message,
    percentage: Math.min(100, Math.max(0, percentage))
  }
}

const clearAllResults = () => {
  clearResults()
  globalProgress.value.active = false
}

const checkCapabilities = () => {
  const capabilities = checkMultimediaCapabilities()
  
  const availableCount = Object.values(capabilities).filter(Boolean).length
  const totalCount = Object.keys(capabilities).length
  
  showNotification(
    `Capacidades multimedia: ${availableCount}/${totalCount} disponibles`, 
    availableCount > 0 ? 'success' : 'warning'
  )
}

// ============================================================================
// PARSERS Y FORMATTERS
// ============================================================================

const parseIntegrationResults = (results) => {
  if (!results || !results.multimedia_integration) return {}
  
  const integration = results.multimedia_integration
  
  return {
    fully_integrated: {
      status: integration.fully_integrated,
      message: integration.fully_integrated ? 'Integración completa' : 'Integración incompleta'
    },
    transcribe_audio: {
      status: integration.transcribe_audio_from_url,
      message: integration.transcribe_audio_from_url ? 'Transcripción disponible' : 'Transcripción no disponible'
    },
    analyze_image: {
      status: integration.analyze_image_from_url,
      message: integration.analyze_image_from_url ? 'Análisis disponible' : 'Análisis no disponible'
    },
    process_attachment: {
      status: integration.process_attachment,
      message: integration.process_attachment ? 'Procesamiento disponible' : 'Procesamiento no disponible'
    }
  }
}

const getResultStatus = (result) => {
  if (typeof result === 'boolean') return result ? 'success' : 'error'
  if (result && typeof result === 'object') {
    return result.status === true ? 'success' : 
           result.status === false ? 'error' : 'warning'
  }
  return 'warning'
}

const getServiceIcon = (service) => {
  const icons = {
    fully_integrated: '✅',
    transcribe_audio: '🎤',
    analyze_image: '🖼️',
    process_attachment: '📎'
  }
  return icons[service] || '🔧'
}

const formatServiceName = (service) => {
  const names = {
    fully_integrated: 'Integración Completa',
    transcribe_audio: 'Transcripción de Audio',
    analyze_image: 'Análisis de Imagen',
    process_attachment: 'Procesamiento de Archivos'
  }
  return names[service] || service
}

const getCapabilityIcon = (capability) => {
  const icons = {
    audio: '🎤',
    screen: '🖥️',
    files: '📁',
    webrtc: '🌐',
    webgl: '🎮'
  }
  return icons[capability] || '❓'
}

const formatCapabilityName = (capability) => {
  const names = {
    audio: 'Audio',
    screen: 'Pantalla',
    files: 'Archivos',
    webrtc: 'WebRTC',
    webgl: 'WebGL'
  }
  return names[capability] || capability
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
  
  // EXPONER FUNCIONES GLOBALES PARA COMPATIBILIDAD CON script.js
  window.processAudio = processAudio
  window.processImage = processImage
  window.testMultimediaIntegration = testMultimediaIntegration
  window.captureScreen = captureScreen
  window.toggleVoiceRecording = toggleVoiceRecording
  
  // Verificar capacidades iniciales
  checkCapabilities()
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

// Watcher para empresa seleccionada
watch(() => appStore.currentCompanyId, (newCompany, oldCompany) => {
  if (newCompany !== oldCompany) {
    clearAllResults()
    if (newCompany) {
      appStore.addToLog(`Multimedia tab activated for company: ${newCompany}`, 'info')
    }
  }
})

// Watcher para mostrar progreso en tiempo real
watch([processingProgress, isAnyProcessing], ([progress, processing]) => {
  if (processing && globalProgress.value.active) {
    globalProgress.value.percentage = progress
  }
})
</script>

<style scoped>
.multimedia-tab {
  padding: 20px;
  max-width: 1400px;
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
  margin-bottom: 20px;
}

.capabilities-indicator {
  display: flex;
  gap: 10px;
  justify-content: center;
  flex-wrap: wrap;
}

.capability-badge {
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
  font-weight: 500;
}

.capability-badge.available {
  background: rgba(72, 187, 120, 0.1);
  color: var(--success-color);
  border: 1px solid var(--success-color);
}

.capability-badge.unavailable {
  background: rgba(160, 174, 192, 0.1);
  color: var(--text-muted);
  border: 1px solid var(--text-muted);
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

.integration-section {
  margin: 30px 0;
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

.btn-info {
  background: var(--info-color);
  color: white;
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

.additional-info {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid var(--border-color);
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px 0;
}

.info-label {
  font-weight: 500;
  color: var(--text-primary);
}

.info-value {
  font-weight: 500;
}

.info-value.success {
  color: var(--success-color);
}

.info-value.error {
  color: var(--error-color);
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

.company-warning {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(237, 137, 54, 0.1);
  border: 1px solid var(--warning-color);
  border-radius: var(--radius-lg);
  padding: 15px;
  z-index: 999;
}

.warning-content {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--warning-color);
  font-weight: 500;
}

.warning-icon {
  font-size: 1.2rem;
}

@media (max-width: 768px) {
  .multimedia-grid {
    grid-template-columns: 1fr;
  }
  
  .capabilities-indicator {
    justify-content: center;
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
  
  .info-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 5px;
  }
  
  .company-warning {
    left: 10px;
    right: 10px;
    transform: none;
  }
}
</style>
