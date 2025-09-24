<template>
  <div class="voice-recorder">
    <h3 class="recorder-title">🎙️ Grabación de Voz</h3>
    
    <!-- Estado del grabador -->
    <div class="recorder-status">
      <div :class="['status-indicator', recordingStatus]">
        <span class="status-icon">{{ statusIcon }}</span>
        <span class="status-text">{{ statusText }}</span>
        <span v-if="isRecording" class="recording-duration">{{ formatDuration(recordingDuration) }}</span>
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
      
      <div v-else-if="voiceRecordingResults" class="recording-complete">
        <div class="complete-icon">✅</div>
        <p>Grabación completada ({{ formatDuration(voiceRecordingResults.duration || 0) }})</p>
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
        <span v-if="isRecording">⏹️ Detener{{ recordingDuration > 0 ? ` (${formatDuration(recordingDuration)})` : '' }}</span>
        <span v-else>🎤 Grabar Voz</span>
      </button>
      
      <button 
        class="btn btn-secondary"
        @click="clearRecording"
        :disabled="isRecording || !voiceRecordingResults"
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

    <!-- Reproductor de grabación - COMO SCRIPT.JS -->
    <div v-if="voiceRecordingResults" class="recording-player">
      <h4>🎵 Grabación Completada</h4>
      
      <div class="player-info">
        <div class="recording-details">
          <div class="detail-item">
            <span class="detail-label">Duración:</span>
            <span class="detail-value">{{ formatDuration(voiceRecordingResults.duration || 0) }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Tamaño:</span>
            <span class="detail-value">{{ formatFileSize(voiceRecordingResults.blob?.size || 0) }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Formato:</span>
            <span class="detail-value">WebM</span>
          </div>
        </div>
      </div>
      
      <div class="player-controls">
        <audio v-if="voiceRecordingResults.url" :src="voiceRecordingResults.url" controls></audio>
      </div>
      
      <div class="player-actions">
        <button @click="downloadRecording" class="btn btn-primary">
          💾 Descargar
        </button>
        
        <button 
          @click="processRecording" 
          class="btn btn-info"
          :disabled="!appStore.currentCompanyId"
        >
          🔄 Procesar con IA
        </button>
        
        <button @click="shareRecording" class="btn btn-secondary">
          📤 Compartir
        </button>
      </div>
    </div>

    <!-- Contenedor específico para la respuesta del procesamiento de la grabación.
         useMultimedia.processAudio(..., { source: 'recorder' }) escribirá aquí (si existe). -->
    <div id="voiceResult" style="margin-top: 16px;"></div>

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

    <!-- Hidden input que usa el composable: audioUserId -->
    <input id="audioUserId" type="hidden" :value="userId" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { useNotifications } from '@/composables/useNotifications'
import { useMultimedia } from '@/composables/useMultimedia'

// Composable principal
const {
  isRecording,
  toggleVoiceRecording,
  recordingDuration,
  voiceRecordingResults,
  clearResults,
  processAudio
} = useMultimedia()

const appStore = useAppStore()
const { showNotification } = useNotifications()

// Local state
const userId = ref('')
const isSupported = ref(false)
const config = ref({
  quality: 'high',
  echoCancellation: true,
  noiseSuppression: true,
  autoProcess: true
})

// Expose useful values to template
// recordingDuration and isRecording and voiceRecordingResults come from composable

// --- computed helpers for status UI ---
const recordingStatus = computed(() => {
  if (!isSupported.value) return 'not-supported'
  if (isRecording.value) return 'recording'
  if (voiceRecordingResults.value) return 'completed'
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

// update hidden input audioUserId whenever visible userId changes (so composable.finds it)
watch(userId, (val) => {
  let el = document.getElementById('audioUserId')
  if (!el) {
    el = document.createElement('input')
    el.type = 'hidden'
    el.id = 'audioUserId'
    document.body.appendChild(el)
  }
  el.value = val || ''
})

// helper functions
const formatDuration = (seconds) => {
  const mins = Math.floor((seconds || 0) / 60)
  const secs = (seconds || 0) % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

const formatFileSize = (bytes) => {
  if (!bytes) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// Toggle recording delegating to the composable
const toggleRecordingHandler = async () => {
  if (!isSupported.value) {
    showNotification('Grabación de voz no soportada', 'error')
    return
  }

  try {
    // Ensure hidden input exists and is up-to-date before toggling (composable reads it)
    const el = document.getElementById('audioUserId')
    if (el) el.value = userId.value || ''

    await toggleVoiceRecording()
  } catch (err) {
    showNotification(`Error en grabación: ${err?.message || err}`, 'error')
  }
}

// use the name conflict with the composable's function
const toggleRecording = toggleRecordingHandler

const clearRecording = () => {
  // limpiar composable y DOM containers
  clearResults()
  // also clear local userId? keep as is (user may want to reuse)
}

// download
const downloadRecording = () => {
  if (!voiceRecordingResults.value?.url) return
  try {
    const a = document.createElement('a')
    a.href = voiceRecordingResults.value.url
    a.download = `voice_recording_${new Date().toISOString().replace(/[:.]/g, '-')}.webm`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    showNotification('Grabación descargada', 'success')
  } catch (error) {
    showNotification('Error descargando grabación', 'error')
  }
}

// process recording (manually invoked by user)
const processRecording = async () => {
  const blob = voiceRecordingResults.value?.blob
  if (!blob) {
    showNotification('No hay grabación para procesar', 'warning')
    return
  }

  if (!appStore.currentCompanyId) {
    showNotification('Por favor selecciona una empresa primero', 'warning')
    return
  }

  try {
    const file = new File([blob], `voice_recording_${Date.now()}.webm`, { type: 'audio/webm' })
    showNotification('Iniciando procesamiento de grabación...', 'info')

    // ensure hidden input has userId value for composable fallback
    const el = document.getElementById('audioUserId')
    if (el) el.value = userId.value || ''

    // call composable processAudio with source 'recorder' so response goes to #voiceResult
    await processAudio(file, { source: 'recorder' })
  } catch (error) {
    showNotification(`Error procesando grabación: ${error?.message || error}`, 'error')
  }
}

// share recording
const shareRecording = async () => {
  const blob = voiceRecordingResults.value?.blob
  if (!blob) {
    showNotification('No hay grabación para compartir', 'warning')
    return
  }

  try {
    if (navigator.share) {
      const file = new File([blob], 'voice_recording.webm', { type: 'audio/webm' })
      const shareData = { title: 'Grabación de Voz', files: [file] }
      // some browsers require navigator.canShare
      if (navigator.canShare && !navigator.canShare(shareData)) {
        throw new Error('El dispositivo no soporta compartir archivos')
      }
      await navigator.share(shareData)
      showNotification('Compartido exitosamente', 'success')
      return
    }

    // fallback: copy the blob to clipboard (may not be supported everywhere)
    if (navigator.clipboard && window.ClipboardItem) {
      await navigator.clipboard.write([new ClipboardItem({ 'audio/webm': blob })])
      showNotification('Grabación copiada al portapapeles', 'success')
      return
    }

    showNotification('Compartir no soportado en este navegador', 'warning')
  } catch (error) {
    showNotification('Error compartiendo grabación', 'error')
  }
}

// request mic permissions
const requestPermissions = async () => {
  try {
    await navigator.mediaDevices.getUserMedia({ audio: true })
    checkSupport()
    showNotification('Permisos concedidos', 'success')
  } catch (error) {
    showNotification('Permisos denegados', 'error')
  }
}

// check support
const checkSupport = () => {
  isSupported.value = !!(
    navigator.mediaDevices &&
    navigator.mediaDevices.getUserMedia &&
    window.MediaRecorder
  )
}

// lifecycle
onMounted(() => {
  checkSupport()
  // ensure hidden input exists for composable
  let el = document.getElementById('audioUserId')
  if (!el) {
    el = document.createElement('input')
    el.type = 'hidden'
    el.id = 'audioUserId'
    document.body.appendChild(el)
  }
  el.value = userId.value || ''
})

onUnmounted(() => {
  // nothing special to cleanup here; composable handles its own cleanup
})
</script>

<style scoped>
/* --- (estilos exactamente como pegaste) --- */
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
