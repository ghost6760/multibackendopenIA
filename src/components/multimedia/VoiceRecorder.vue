<template>
  <div class="voice-recorder">
    <h3 class="recorder-title">🎙️ Grabación de Voz</h3>
    
    <!-- Estado del grabador -->
    <div class="recorder-status">
      <div :class="['status-indicator', recordingStatus]">
        <span class="status-icon">{{ statusIcon }}</span>
        <span class="status-text">{{ statusText }}</span>
        <span v-if="isRecording" class="recording-duration">{{ formatDuration(duration) }}</span>
      </div>
    </div>

    <!-- Visualizador simple de audio -->
    <div class="audio-visualizer">
      <div v-if="isRecording" class="recording-animation">
        <div class="pulse-dot"></div>
        <div class="sound-bars">
          <div 
            v-for="bar in 8" 
            :key="bar"
            :class="['sound-bar', { active: isRecording }]"
            :style="{ animationDelay: bar * 0.1 + 's' }"
          ></div>
        </div>
      </div>
      
      <div v-else-if="results" class="recording-complete">
        <div class="complete-icon">✅</div>
        <p>Grabación completada ({{ formatDuration(results.duration || 0) }})</p>
      </div>
      
      <div v-else class="visualizer-placeholder">
        <div class="placeholder-icon">🎵</div>
        <p>Presiona grabar para iniciar</p>
      </div>
    </div>

    <!-- Controles principales - EXACTOS A SCRIPT.JS -->
    <div class="recorder-controls">
      <button 
        id="recordVoiceButton"
        class="btn btn-record"
        :class="{ recording: isRecording, 'btn-primary': !isRecording, 'btn-danger': isRecording }"
        @click="toggleRecording"
        :disabled="!isSupported"
      >
        <span v-if="isRecording">⏹️ Detener{{ duration > 0 ? ` (${formatDuration(duration)})` : '' }}</span>
        <span v-else>🎤 Grabar Voz</span>
      </button>
      
      <button 
        class="btn btn-secondary"
        @click="clearRecording"
        :disabled="isRecording || !results"
      >
        🗑️ Limpiar
      </button>
    </div>

    <!-- Campo de Usuario ID - IGUAL QUE AudioProcessor.vue -->
    <div class="user-id-section">
      <div class="form-group">
        <label for="voiceUserId">ID de Usuario:</label>
        <input 
          id="voiceUserId"
          type="text" 
          v-model="userId"
          placeholder="usuario_123"
          class="form-input"
          :disabled="isRecording"
        />
      </div>
    </div>

    <!-- Configuración simple -->
    <div class="recording-config">
      <h4>⚙️ Configuración</h4>
      
      <div class="config-grid">
        <div class="config-item">
          <label for="audioQuality">Calidad de audio:</label>
          <select id="audioQuality" v-model="config.quality" :disabled="isRecording">
            <option value="standard">Estándar (16 kHz)</option>
            <option value="high">Alta (44.1 kHz)</option>
            <option value="ultra">Ultra (48 kHz)</option>
          </select>
        </div>
        
        <div class="config-item">
          <label for="voiceLanguage">Idioma para procesamiento:</label>
          <select id="voiceLanguage" v-model="config.language" :disabled="isRecording">
            <option value="">Auto-detectar</option>
            <option value="es">Español</option>
            <option value="en">Inglés</option>
            <option value="fr">Francés</option>
            <option value="de">Alemán</option>
            <option value="it">Italiano</option>
            <option value="pt">Portugués</option>
          </select>
        </div>
        
        <div class="config-item full-width">
          <label for="voicePrompt">Prompt para procesamiento:</label>
          <textarea
            id="voicePrompt"
            v-model="config.prompt"
            placeholder="Contexto específico para el procesamiento..."
            rows="2"
            :disabled="isRecording"
            class="form-textarea"
          ></textarea>
        </div>
        
        <div class="config-item">
          <label>
            <input 
              type="checkbox" 
              v-model="config.echoCancellation"
              :disabled="isRecording"
            />
            Cancelación de eco
          </label>
        </div>
        
        <div class="config-item">
          <label>
            <input 
              type="checkbox" 
              v-model="config.noiseSuppression"
              :disabled="isRecording"
            />
            Supresión de ruido
          </label>
        </div>
        
        <div class="config-item">
          <label>
            <input 
              type="checkbox" 
              v-model="config.autoProcess"
              :disabled="isRecording"
            />
            Procesamiento automático
          </label>
        </div>
      </div>
    </div>

    <!-- Resultados del procesamiento de grabación de voz -->
    <div v-if="results?.processing" class="voice-processing-result">
      <h4>🤖 Procesamiento de Grabación Completado</h4>
      
      <div class="processing-content">
        <!-- Transcripción -->
        <div class="result-section">
          <h5>📝 Transcripción:</h5>
          <div class="transcription-text">
            {{ results.transcript || results.processing.transcript || results.processing.transcription || 'Sin transcripción' }}
          </div>
          
          <div class="transcription-actions">
            <button @click="copyToClipboard(results.transcript || results.processing.transcript || results.processing.transcription || '')" class="btn btn-sm">
              📋 Copiar
            </button>
          </div>
        </div>
        
        <!-- Respuesta del Bot -->
        <div v-if="results.bot_response || results.processing.bot_response" class="result-section">
          <h5>🤖 Respuesta del Bot:</h5>
          <div class="bot-response-text">
            {{ results.bot_response || results.processing.bot_response || results.processing.response || results.processing.message }}
          </div>
        </div>
        
        <!-- Información técnica del procesamiento -->
        <div class="result-section technical-info">
          <h5>🔧 Información del Procesamiento:</h5>
          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">Empresa:</span>
              <span class="info-value">{{ results.company_id || results.processing.company_id || appStore.currentCompanyId }}</span>
            </div>
            <div v-if="results.processing_time || results.processing.processing_time" class="info-item">
              <span class="info-label">Tiempo de procesamiento:</span>
              <span class="info-value">{{ results.processing_time || results.processing.processing_time }}ms</span>
            </div>
            <div class="info-item">
              <span class="info-label">Duración original:</span>
              <span class="info-value">{{ formatDuration(results.duration || 0) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Reproductor de grabación - COMO SCRIPT.JS -->
    <div v-if="results" class="recording-player">
      <h4>🎵 Grabación Completada</h4>
      
      <div class="player-info">
        <div class="recording-details">
          <div class="detail-item">
            <span class="detail-label">Duración:</span>
            <span class="detail-value">{{ formatDuration(results.duration || 0) }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Tamaño:</span>
            <span class="detail-value">{{ formatFileSize(results.blob?.size || 0) }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Formato:</span>
            <span class="detail-value">WebM</span>
          </div>
        </div>
      </div>
      
      <div class="player-controls">
        <audio v-if="results.url" :src="results.url" controls></audio>
      </div>
      
      <div class="player-actions">
        <button @click="downloadRecording" class="btn btn-primary">
          💾 Descargar
        </button>
        
        <button 
          @click="processRecording" 
          class="btn btn-info"
          :disabled="!appStore.currentCompanyId || !userId.trim()"
        >
          🔄 Procesar con IA
        </button>
        
        <button @click="shareRecording" class="btn btn-secondary">
          📤 Compartir
        </button>
      </div>
    </div>

    <!-- Mensaje de no compatibilidad -->
    <div v-if="!isSupported" class="not-supported">
      <div class="not-supported-icon">⚠️</div>
      <h4>Grabación No Disponible</h4>
      <p>
        Tu navegador no soporta grabación de audio o los permisos están denegados.
      </p>
      <p>
        Por favor, permite el acceso al micrófono y usa un navegador moderno.
      </p>
      <button @click="requestPermissions" class="btn btn-primary">
        🎤 Solicitar Permisos
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, defineProps, defineEmits } from 'vue'
import { useAppStore } from '@/stores/app'
import { useNotifications } from '@/composables/useNotifications'
import { useMultimedia } from '@/composables/useMultimedia'

// ============================================================================
// PROPS & EMITS - INTERFACE CON MULTIMEDIATAB
// ============================================================================

const props = defineProps({
  isRecording: {
    type: Boolean,
    default: false
  },
  duration: {
    type: Number,
    default: 0
  },
  results: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['toggle-recording', 'clear-results'])

// ============================================================================
// STORES & COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const { showNotification } = useNotifications()

// Importar la función específica del composable
const { processVoiceRecording } = useMultimedia()

// ============================================================================
// ESTADO LOCAL - SIMPLE COMO SCRIPT.JS
// ============================================================================

const isSupported = ref(false)
const userId = ref('') // Usuario ID específico para grabación de voz

// Configuración simple
const config = ref({
  quality: 'high',
  echoCancellation: true,
  noiseSuppression: true,
  autoProcess: true,
  language: '', // Para procesamiento opcional
  prompt: ''    // Para contexto opcional
})

// ============================================================================
// COMPUTED
// ============================================================================

const recordingStatus = computed(() => {
  if (!isSupported.value) return 'not-supported'
  if (props.isRecording) return 'recording'
  if (props.results) return 'completed'
  return 'ready'
})

const statusIcon = computed(() => {
  switch (recordingStatus.value) {
    case 'not-supported': return '⚠️'
    case 'recording': return '🔴'
    case 'completed': return '✅'
    case 'ready': return '🎙️'
    default: return '❓'
  }
})

const statusText = computed(() => {
  switch (recordingStatus.value) {
    case 'not-supported': return 'No compatible'
    case 'recording': return 'Grabando...'
    case 'completed': return 'Completado'
    case 'ready': return 'Listo para grabar'
    default: return 'Estado desconocido'
  }
})

const qualitySettings = computed(() => {
  const settings = {
    standard: { sampleRate: 16000, bitrate: 64000 },
    high: { sampleRate: 44100, bitrate: 128000 },
    ultra: { sampleRate: 48000, bitrate: 192000 }
  }
  
  return settings[config.value.quality] || settings.high
})

// ============================================================================
// MÉTODOS PRINCIPALES - DELEGAR AL COMPOSABLE
// ============================================================================

/**
 * Toggle grabación - DELEGAR AL COMPOSABLE COMO SCRIPT.JS
 */
const toggleRecording = async () => {
  if (!isSupported.value) {
    showNotification('Grabación de voz no soportada', 'error')
    return
  }
  
  try {
    appStore.addToLog(`Voice recording toggle - currently recording: ${props.isRecording}`, 'info')
    
    // Delegar al composable via emit
    await emit('toggle-recording', {
      quality: config.value.quality,
      echoCancellation: config.value.echoCancellation,
      noiseSuppression: config.value.noiseSuppression,
      autoProcess: config.value.autoProcess
    })
    
  } catch (error) {
    showNotification(`Error en grabación: ${error.message}`, 'error')
  }
}

const clearRecording = () => {
  emit('clear-results')
}

// ============================================================================
// ACCIONES DE ARCHIVO - COMO SCRIPT.JS
// ============================================================================

const downloadRecording = () => {
  if (!props.results?.url) return
  
  try {
    const a = document.createElement('a')
    a.href = props.results.url
    a.download = `voice_recording_${new Date().toISOString().replace(/[:.]/g, '-')}.webm`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    
    showNotification('Grabación descargada', 'success')
  } catch (error) {
    showNotification('Error descargando grabación', 'error')
  }
}

const processRecording = async () => {
  if (!props.results?.blob) {
    showNotification('No hay grabación para procesar', 'warning')
    return
  }

  if (!appStore.currentCompanyId) {
    showNotification('Por favor selecciona una empresa primero', 'warning')
    return
  }

  if (!userId.value.trim()) {
    showNotification('Por favor ingresa un ID de usuario', 'warning')
    return
  }

  try {
    // Usar la función específica del composable
    await processVoiceRecording(userId.value, {
      language: config.value.language || undefined,
      prompt: config.value.prompt?.trim() || undefined
    })
    
    appStore.addToLog('Voice recording processed successfully', 'info')
    
  } catch (error) {
    showNotification(`Error procesando grabación: ${error.message}`, 'error')
  }
}

const shareRecording = async () => {
  if (!props.results?.blob) return
  
  try {
    if (navigator.share && navigator.canShare) {
      const shareData = {
        title: 'Grabación de Voz',
        files: [new File([props.results.blob], 'voice_recording.webm', { 
          type: 'audio/webm' 
        })]
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
        'audio/webm': props.results.blob
      })
    ])
    
    showNotification('Copiado al portapapeles', 'success')
    
  } catch (error) {
    showNotification('Error compartiendo grabación', 'error')
  }
}

const requestPermissions = async () => {
  try {
    await navigator.mediaDevices.getUserMedia({ audio: true })
    checkSupport()
    showNotification('Permisos concedidos', 'success')
  } catch (error) {
    showNotification('Permisos denegados', 'error')
  }
}

// ============================================================================
// UTILIDADES
// ============================================================================

const formatDuration = (seconds) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const copyToClipboard = async (text) => {
  try {
    await navigator.clipboard.writeText(text)
    showNotification('Copiado al portapapeles', 'success')
  } catch (error) {
    showNotification('Error al copiar al portapapeles', 'error')
  }
}

const checkSupport = async () => {
  try {
    // Verificar APIs necesarias
    isSupported.value = !!(
      navigator.mediaDevices &&
      navigator.mediaDevices.getUserMedia &&
      window.MediaRecorder
    )
    
  } catch (error) {
    isSupported.value = false
    appStore.addToLog('Voice recording not supported in this environment', 'warning')
  }
}

// ============================================================================
// LIFECYCLE
// ============================================================================

onMounted(async () => {
  await checkSupport()
  appStore.addToLog('VoiceRecorder component mounted', 'info')
})

onUnmounted(() => {
  appStore.addToLog('VoiceRecorder component unmounted', 'info')
})
</script>

<style scoped>
.voice-recorder {
  padding: 20px;
  height: 100%;
}

.recorder-title {
  color: var(--text-primary);
  margin-bottom: 20px;
  font-size: 1.4rem;
}

.recorder-status {
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

.status-indicator.recording {
  background: rgba(245, 101, 101, 0.1);
  color: var(--error-color);
  border: 1px solid var(--error-color);
  animation: pulse 1.5s infinite;
}

.status-indicator.completed {
  background: rgba(72, 187, 120, 0.1);
  color: var(--success-color);
  border: 1px solid var(--success-color);
}

.status-indicator.not-supported {
  background: rgba(160, 174, 192, 0.1);
  color: var(--text-muted);
  border: 1px solid var(--text-muted);
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

.status-icon {
  font-size: 1.2rem;
}

.recording-duration {
  margin-left: auto;
  font-family: monospace;
  font-size: 1.1rem;
  font-weight: bold;
}

.audio-visualizer {
  position: relative;
  margin-bottom: 20px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  height: 120px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.recording-animation {
  display: flex;
  align-items: center;
  gap: 20px;
}

.pulse-dot {
  width: 20px;
  height: 20px;
  background: var(--error-color);
  border-radius: 50%;
  animation: pulse-dot 1s infinite;
}

@keyframes pulse-dot {
  0%, 100% { 
    transform: scale(1);
    opacity: 1;
  }
  50% { 
    transform: scale(1.5);
    opacity: 0.7;
  }
}

.sound-bars {
  display: flex;
  gap: 4px;
  align-items: end;
  height: 40px;
}

.sound-bar {
  width: 4px;
  height: 10px;
  background: var(--primary-color);
  border-radius: 2px;
  opacity: 0.3;
  transition: all 0.2s ease;
}

.sound-bar.active {
  animation: sound-bar 0.8s infinite;
}

@keyframes sound-bar {
  0%, 100% { 
    height: 10px;
    opacity: 0.3;
  }
  50% { 
    height: 30px;
    opacity: 1;
  }
}

.recording-complete {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.complete-icon {
  font-size: 2rem;
}

.visualizer-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: var(--text-secondary);
}

.placeholder-icon {
  font-size: 2rem;
  opacity: 0.6;
}

.recorder-controls {
  display: flex;
  gap: 10px;
  margin-bottom: 25px;
  justify-content: center;
}

.user-id-section {
  margin-bottom: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.form-group label {
  font-weight: 500;
  color: var(--text-primary);
}

.form-input {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
  color: var(--text-primary);
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

.btn-record {
  font-size: 1.1rem;
  padding: 12px 20px;
}

.btn-record.recording {
  animation: pulse 1.5s infinite;
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

.recording-config {
  margin-bottom: 25px;
}

.recording-config h4 {
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

.config-item select {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
  color: var(--text-primary);
}

.form-textarea {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
  color: var(--text-primary);
  resize: vertical;
  min-height: 60px;
  font-family: inherit;
}

.config-item input[type="checkbox"] {
  margin: 0;
}

.voice-processing-result {
  margin-bottom: 25px;
}

.voice-processing-result h4 {
  color: var(--text-primary);
  margin-bottom: 15px;
}

.processing-content {
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

.transcription-text,
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

.transcription-actions {
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

.recording-player {
  margin-bottom: 25px;
}

.recording-player h4 {
  color: var(--text-primary);
  margin-bottom: 15px;
}

.player-info {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 15px;
  margin-bottom: 15px;
}

.recording-details {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
}

.detail-item {
  display: flex;
  justify-content: space-between;
  padding: 8px;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
}

.detail-label {
  font-weight: 500;
  color: var(--text-primary);
}

.detail-value {
  color: var(--text-secondary);
}

.player-controls {
  margin-bottom: 15px;
}

.player-controls audio {
  width: 100%;
}

.player-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: center;
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
  .recorder-controls {
    flex-direction: column;
    align-items: stretch;
  }
  
  .config-grid {
    grid-template-columns: 1fr;
  }
  
  .player-actions {
    flex-direction: column;
  }
  
  .recording-details {
    grid-template-columns: 1fr;
  }
}
</style>
