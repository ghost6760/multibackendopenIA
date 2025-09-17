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

    <!-- Visualizador de audio -->
    <div class="audio-visualizer" ref="visualizerContainer">
      <canvas 
        ref="visualizerCanvas"
        :width="visualizerWidth"
        :height="visualizerHeight"
      ></canvas>
      
      <div v-if="!isRecording && !hasRecording" class="visualizer-placeholder">
        <div class="placeholder-icon">🎵</div>
        <p>Presiona grabar para ver la forma de onda</p>
      </div>
    </div>

    <!-- Controles principales -->
    <div class="recorder-controls">
      <button 
        class="btn btn-record"
        :class="{ recording: isRecording }"
        @click="toggleRecording"
        :disabled="!isSupported"
      >
        <span v-if="isRecording">⏹️ Detener</span>
        <span v-else>🎙️ Grabar</span>
      </button>
      
      <button 
        class="btn btn-secondary"
        @click="pauseRecording"
        :disabled="!isRecording || isPaused"
      >
        ⏸️ Pausar
      </button>
      
      <button 
        class="btn btn-secondary"
        @click="resumeRecording"
        :disabled="!isRecording || !isPaused"
      >
        ▶️ Continuar
      </button>
      
      <button 
        class="btn btn-danger"
        @click="clearRecording"
        :disabled="isRecording || !hasRecording"
      >
        🗑️ Limpiar
      </button>
    </div>

    <!-- Configuración de grabación -->
    <div class="recording-config">
      <h4>⚙️ Configuración</h4>
      
      <div class="config-grid">
        <div class="config-item">
          <label for="audioQuality">Calidad de audio:</label>
          <select id="audioQuality" v-model="config.quality" :disabled="isRecording">
            <option value="low">Baja (8 kHz)</option>
            <option value="medium">Media (16 kHz)</option>
            <option value="high">Alta (44.1 kHz)</option>
            <option value="ultra">Ultra (48 kHz)</option>
          </select>
        </div>
        
        <div class="config-item">
          <label for="audioFormat">Formato:</label>
          <select id="audioFormat" v-model="config.format" :disabled="isRecording">
            <option value="webm">WebM</option>
            <option value="mp4">MP4</option>
            <option value="wav">WAV</option>
          </select>
        </div>
        
        <div class="config-item">
          <label for="inputSource">Fuente de entrada:</label>
          <select id="inputSource" v-model="config.inputSource" :disabled="isRecording">
            <option value="default">Micrófono por defecto</option>
            <option 
              v-for="device in audioDevices"
              :key="device.deviceId"
              :value="device.deviceId"
            >
              {{ device.label || `Dispositivo ${device.deviceId.slice(0, 8)}...` }}
            </option>
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
              v-model="config.autoGain"
              :disabled="isRecording"
            />
            Ganancia automática
          </label>
        </div>
      </div>
    </div>

    <!-- Control de volumen -->
    <div class="volume-control">
      <h4>🔊 Control de Volumen</h4>
      <div class="volume-meter">
        <div class="volume-label">Nivel de entrada:</div>
        <div class="volume-bar">
          <div 
            class="volume-fill"
            :style="{ width: volumeLevel + '%' }"
            :class="{ 'volume-high': volumeLevel > 80, 'volume-medium': volumeLevel > 50 }"
          ></div>
        </div>
        <div class="volume-value">{{ Math.round(volumeLevel) }}%</div>
      </div>
    </div>

    <!-- Reproductor de grabación -->
    <div v-if="hasRecording" class="recording-player">
      <h4>🎵 Reproducir Grabación</h4>
      
      <div class="player-controls">
        <button @click="togglePlayback" class="btn btn-primary">
          <span v-if="isPlaying">⏸️ Pausar</span>
          <span v-else>▶️ Reproducir</span>
        </button>
        
        <div class="playback-time">
          {{ formatDuration(currentTime) }} / {{ formatDuration(totalDuration) }}
        </div>
      </div>
      
      <div class="progress-bar" @click="seekTo($event)">
        <div 
          class="progress-fill"
          :style="{ width: playbackProgress + '%' }"
        ></div>
      </div>
      
      <audio 
        ref="audioPlayer"
        @timeupdate="updatePlaybackTime"
        @ended="onPlaybackEnded"
        @loadedmetadata="onAudioLoaded"
      ></audio>
    </div>

    <!-- Acciones de archivo -->
    <div v-if="hasRecording" class="file-actions">
      <h4>💾 Acciones</h4>
      
      <div class="action-buttons">
        <button @click="downloadRecording" class="btn btn-primary">
          💾 Descargar
        </button>
        
        <button @click="processWithAPI" class="btn btn-info" :disabled="isProcessing">
          <span v-if="isProcessing">⏳ Procesando...</span>
          <span v-else>🔄 Procesar con IA</span>
        </button>
        
        <button @click="shareRecording" class="btn btn-secondary">
          📤 Compartir
        </button>
        
        <button @click="saveToLibrary" class="btn btn-success">
          📚 Guardar en Biblioteca
        </button>
      </div>
    </div>

    <!-- Biblioteca de grabaciones -->
    <div v-if="recordings.length > 0" class="recordings-library">
      <h4>📚 Biblioteca de Grabaciones</h4>
      
      <div class="library-controls">
        <button @click="clearLibrary" class="btn btn-sm btn-secondary">
          🗑️ Limpiar Biblioteca
        </button>
        <button @click="exportLibrary" class="btn btn-sm btn-primary">
          📤 Exportar Todo
        </button>
      </div>
      
      <div class="recordings-list">
        <div 
          v-for="(recording, index) in recordings"
          :key="recording.id"
          class="recording-item"
        >
          <div class="recording-info">
            <div class="recording-name">{{ recording.name }}</div>
            <div class="recording-details">
              {{ formatDuration(recording.duration) }} • {{ formatFileSize(recording.size) }}
            </div>
            <div class="recording-date">{{ formatDateTime(recording.timestamp) }}</div>
          </div>
          
          <div class="recording-actions">
            <button @click="playLibraryRecording(recording)" class="btn btn-xs">
              ▶️
            </button>
            <button @click="downloadLibraryRecording(recording)" class="btn btn-xs">
              💾
            </button>
            <button @click="deleteLibraryRecording(recording.id)" class="btn btn-xs btn-danger">
              🗑️
            </button>
          </div>
        </div>
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
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'

// ============================================================================
// PROPS & EMITS
// ============================================================================

const emit = defineEmits(['recording', 'stopped', 'error'])

// ============================================================================
// STORES & COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const { apiRequest } = useApiRequest()
const { showNotification } = useNotifications()

// ============================================================================
// REFS
// ============================================================================

const visualizerContainer = ref(null)
const visualizerCanvas = ref(null)
const audioPlayer = ref(null)

// ============================================================================
// ESTADO LOCAL
// ============================================================================

const isSupported = ref(false)
const isRecording = ref(false)
const isPaused = ref(false)
const hasRecording = ref(false)
const isPlaying = ref(false)
const isProcessing = ref(false)

const recordingDuration = ref(0)
const currentTime = ref(0)
const totalDuration = ref(0)
const volumeLevel = ref(0)

const audioDevices = ref([])
const recordings = ref([])

// Stream y recording objects
const mediaStream = ref(null)
const mediaRecorder = ref(null)
const audioContext = ref(null)
const analyser = ref(null)
const currentRecording = ref(null)

// Timers
const recordingTimer = ref(null)
const volumeTimer = ref(null)
const visualizerAnimationId = ref(null)

// Visualizer
const visualizerWidth = ref(400)
const visualizerHeight = ref(120)

// Configuración de grabación
const config = ref({
  quality: 'high',
  format: 'webm',
  inputSource: 'default',
  echoCancellation: true,
  noiseSuppression: true,
  autoGain: true
})

// ============================================================================
// COMPUTED
// ============================================================================

const recordingStatus = computed(() => {
  if (!isSupported.value) return 'not-supported'
  if (isRecording.value && isPaused.value) return 'paused'
  if (isRecording.value) return 'recording'
  return 'ready'
})

const statusIcon = computed(() => {
  switch (recordingStatus.value) {
    case 'not-supported': return '⚠️'
    case 'recording': return '🔴'
    case 'paused': return '⏸️'
    case 'ready': return '🎙️'
    default: return '❓'
  }
})

const statusText = computed(() => {
  switch (recordingStatus.value) {
    case 'not-supported': return 'No compatible'
    case 'recording': return 'Grabando...'
    case 'paused': return 'Pausado'
    case 'ready': return 'Listo para grabar'
    default: return 'Estado desconocido'
  }
})

const playbackProgress = computed(() => {
  if (totalDuration.value === 0) return 0
  return (currentTime.value / totalDuration.value) * 100
})

const qualitySettings = computed(() => {
  const settings = {
    low: { sampleRate: 8000, bitrate: 32000 },
    medium: { sampleRate: 16000, bitrate: 64000 },
    high: { sampleRate: 44100, bitrate: 128000 },
    ultra: { sampleRate: 48000, bitrate: 192000 }
  }
  
  return settings[config.value.quality] || settings.high
})

// ============================================================================
// MÉTODOS PRINCIPALES
// ============================================================================

/**
 * Toggle grabación - MIGRADO: toggleVoiceRecording() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const toggleRecording = async () => {
  if (isRecording.value) {
    stopRecording()
  } else {
    await startRecording()
  }
}

/**
 * Inicia la grabación de voz
 */
const startRecording = async () => {
  if (!isSupported.value) {
    showNotification('Grabación de voz no soportada', 'error')
    return
  }
  
  try {
    appStore.addToLog('Starting voice recording', 'info')
    emit('recording', { message: 'Iniciando grabación...', progress: 0 })
    
    // Obtener permisos y stream de audio
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        deviceId: config.value.inputSource !== 'default' ? config.value.inputSource : undefined,
        sampleRate: qualitySettings.value.sampleRate,
        echoCancellation: config.value.echoCancellation,
        noiseSuppression: config.value.noiseSuppression,
        autoGainControl: config.value.autoGain
      }
    })
    
    mediaStream.value = stream
    
    // Configurar AudioContext para análisis y visualización
    setupAudioAnalysis(stream)
    
    // Configurar MediaRecorder
    setupMediaRecorder(stream)
    
    // Iniciar grabación
    mediaRecorder.value.start()
    isRecording.value = true
    isPaused.value = false
    recordingDuration.value = 0
    hasRecording.value = false
    
    // Iniciar timers
    startRecordingTimer()
    startVolumeMonitoring()
    startVisualization()
    
    appStore.addToLog('Voice recording started successfully', 'info')
    showNotification('Grabación iniciada', 'success')
    
    emit('recording', { message: 'Grabación en progreso...', progress: 50 })
    
  } catch (error) {
    appStore.addToLog(`Voice recording failed: ${error.message}`, 'error')
    showNotification(`Error iniciando grabación: ${error.message}`, 'error')
    emit('error', error)
    
    // Limpiar recursos
    cleanupRecording()
  }
}

/**
 * Detiene la grabación
 */
const stopRecording = () => {
  if (!isRecording.value) return
  
  try {
    appStore.addToLog('Stopping voice recording', 'info')
    
    // Detener MediaRecorder
    if (mediaRecorder.value && mediaRecorder.value.state !== 'inactive') {
      mediaRecorder.value.stop()
    }
    
    // Limpiar recursos
    cleanupRecording()
    
    isRecording.value = false
    isPaused.value = false
    
    appStore.addToLog('Voice recording stopped', 'info')
    showNotification('Grabación detenida', 'info')
    
    emit('stopped', { duration: recordingDuration.value })
    
  } catch (error) {
    appStore.addToLog(`Error stopping recording: ${error.message}`, 'error')
    showNotification(`Error deteniendo grabación: ${error.message}`, 'error')
  }
}

/**
 * Pausa la grabación
 */
const pauseRecording = () => {
  if (!isRecording.value || isPaused.value) return
  
  try {
    if (mediaRecorder.value && mediaRecorder.value.state === 'recording') {
      mediaRecorder.value.pause()
      isPaused.value = true
      
      // Pausar timers
      if (recordingTimer.value) {
        clearInterval(recordingTimer.value)
        recordingTimer.value = null
      }
      
      showNotification('Grabación pausada', 'info')
    }
  } catch (error) {
    showNotification('Error pausando grabación', 'error')
  }
}

/**
 * Reanuda la grabación
 */
const resumeRecording = () => {
  if (!isRecording.value || !isPaused.value) return
  
  try {
    if (mediaRecorder.value && mediaRecorder.value.state === 'paused') {
      mediaRecorder.value.resume()
      isPaused.value = false
      
      // Reanudar timer
      startRecordingTimer()
      
      showNotification('Grabación reanudada', 'info')
    }
  } catch (error) {
    showNotification('Error reanudando grabación', 'error')
  }
}

/**
 * Limpia la grabación actual
 */
const clearRecording = () => {
  if (isRecording.value) return
  
  try {
    // Limpiar audio player
    if (audioPlayer.value) {
      audioPlayer.value.src = ''
      audioPlayer.value.load()
    }
    
    // Limpiar recording actual
    if (currentRecording.value?.url) {
      URL.revokeObjectURL(currentRecording.value.url)
    }
    
    currentRecording.value = null
    hasRecording.value = false
    isPlaying.value = false
    currentTime.value = 0
    totalDuration.value = 0
    
    // Limpiar canvas
    clearVisualizer()
    
    showNotification('Grabación limpiada', 'info')
    
  } catch (error) {
    showNotification('Error limpiando grabación', 'error')
  }
}

// ============================================================================
// CONFIGURACIÓN DE AUDIO
// ============================================================================

const setupAudioAnalysis = (stream) => {
  try {
    audioContext.value = new (window.AudioContext || window.webkitAudioContext)()
    analyser.value = audioContext.value.createAnalyser()
    
    const source = audioContext.value.createMediaStreamSource(stream)
    source.connect(analyser.value)
    
    analyser.value.fftSize = 256
    analyser.value.smoothingTimeConstant = 0.8
    
  } catch (error) {
    console.warn('Error setting up audio analysis:', error)
  }
}

const setupMediaRecorder = (stream) => {
  try {
    // Determinar formato MIME
    const mimeTypes = [
      `audio/webm;codecs=opus`,
      `audio/webm`,
      `audio/mp4`,
      `audio/wav`
    ]
    
    let selectedMimeType = mimeTypes.find(type => MediaRecorder.isTypeSupported(type))
    
    if (!selectedMimeType) {
      throw new Error('No hay formatos de audio soportados')
    }
    
    mediaRecorder.value = new MediaRecorder(stream, {
      mimeType: selectedMimeType,
      audioBitsPerSecond: qualitySettings.value.bitrate
    })
    
    const chunks = []
    
    mediaRecorder.value.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunks.push(event.data)
      }
    }
    
    mediaRecorder.value.onstop = () => {
      const blob = new Blob(chunks, { type: selectedMimeType })
      const url = URL.createObjectURL(blob)
      
      currentRecording.value = {
        id: `recording_${Date.now()}`,
        name: `voice_${new Date().toISOString().replace(/[:.]/g, '-')}.${getFileExtension(selectedMimeType)}`,
        blob,
        url,
        size: blob.size,
        duration: recordingDuration.value,
        timestamp: Date.now(),
        mimeType: selectedMimeType
      }
      
      // Configurar audio player
      if (audioPlayer.value) {
        audioPlayer.value.src = url
        audioPlayer.value.load()
      }
      
      hasRecording.value = true
      chunks.length = 0 // Limpiar chunks
    }
    
  } catch (error) {
    throw new Error(`Error configurando MediaRecorder: ${error.message}`)
  }
}

// ============================================================================
// TIMERS Y MONITOREO
// ============================================================================

const startRecordingTimer = () => {
  recordingTimer.value = setInterval(() => {
    recordingDuration.value += 1
  }, 1000)
}

const startVolumeMonitoring = () => {
  if (!analyser.value) return
  
  const dataArray = new Uint8Array(analyser.value.frequencyBinCount)
  
  const updateVolume = () => {
    if (!analyser.value || !isRecording.value) return
    
    analyser.value.getByteFrequencyData(dataArray)
    
    // Calcular nivel de volumen promedio
    const average = dataArray.reduce((sum, value) => sum + value, 0) / dataArray.length
    volumeLevel.value = (average / 255) * 100
    
    volumeTimer.value = requestAnimationFrame(updateVolume)
  }
  
  updateVolume()
}

const startVisualization = () => {
  if (!analyser.value || !visualizerCanvas.value) return
  
  const canvas = visualizerCanvas.value
  const ctx = canvas.getContext('2d')
  const dataArray = new Uint8Array(analyser.value.frequencyBinCount)
  
  const draw = () => {
    if (!analyser.value || !isRecording.value) return
    
    analyser.value.getByteFrequencyData(dataArray)
    
    // Limpiar canvas
    ctx.fillStyle = 'rgba(0, 0, 0, 0.1)'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    
    // Dibujar barras de frecuencia
    const barWidth = canvas.width / dataArray.length
    let x = 0
    
    for (let i = 0; i < dataArray.length; i++) {
      const barHeight = (dataArray[i] / 255) * canvas.height
      
      // Gradiente de color basado en frecuencia
      const hue = (i / dataArray.length) * 360
      ctx.fillStyle = `hsl(${hue}, 70%, 60%)`
      
      ctx.fillRect(x, canvas.height - barHeight, barWidth, barHeight)
      x += barWidth
    }
    
    visualizerAnimationId.value = requestAnimationFrame(draw)
  }
  
  draw()
}

const cleanupRecording = () => {
  // Detener stream
  if (mediaStream.value) {
    mediaStream.value.getTracks().forEach(track => track.stop())
    mediaStream.value = null
  }
  
  // Limpiar AudioContext
  if (audioContext.value) {
    audioContext.value.close()
    audioContext.value = null
  }
  
  // Limpiar timers
  if (recordingTimer.value) {
    clearInterval(recordingTimer.value)
    recordingTimer.value = null
  }
  
  if (volumeTimer.value) {
    cancelAnimationFrame(volumeTimer.value)
    volumeTimer.value = null
  }
  
  if (visualizerAnimationId.value) {
    cancelAnimationFrame(visualizerAnimationId.value)
    visualizerAnimationId.value = null
  }
  
  volumeLevel.value = 0
}

// ============================================================================
// REPRODUCCIÓN
// ============================================================================

const togglePlayback = () => {
  if (!audioPlayer.value || !hasRecording.value) return
  
  if (isPlaying.value) {
    audioPlayer.value.pause()
  } else {
    audioPlayer.value.play()
  }
}

const seekTo = (event) => {
  if (!audioPlayer.value || totalDuration.value === 0) return
  
  const rect = event.currentTarget.getBoundingClientRect()
  const percent = (event.clientX - rect.left) / rect.width
  const newTime = percent * totalDuration.value
  
  audioPlayer.value.currentTime = newTime
}

const updatePlaybackTime = () => {
  if (audioPlayer.value) {
    currentTime.value = audioPlayer.value.currentTime
    isPlaying.value = !audioPlayer.value.paused
  }
}

const onPlaybackEnded = () => {
  isPlaying.value = false
  currentTime.value = 0
}

const onAudioLoaded = () => {
  if (audioPlayer.value) {
    totalDuration.value = audioPlayer.value.duration || 0
  }
}

// ============================================================================
// ACCIONES DE ARCHIVO
// ============================================================================

const downloadRecording = () => {
  if (!currentRecording.value) return
  
  try {
    const a = document.createElement('a')
    a.href = currentRecording.value.url
    a.download = currentRecording.value.name
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    
    showNotification('Grabación descargada', 'success')
  } catch (error) {
    showNotification('Error descargando grabación', 'error')
  }
}

const processWithAPI = async () => {
  if (!currentRecording.value) return
  
  isProcessing.value = true
  
  try {
    const formData = new FormData()
    formData.append('audio', currentRecording.value.blob, currentRecording.value.name)
    
    const response = await apiRequest('/api/multimedia/audio', {
      method: 'POST',
      body: formData
    })
    
    showNotification('Audio procesado exitosamente', 'success')
    
    // Mostrar resultados (aquí podrías abrir un modal o navegar a otra vista)
    console.log('API Response:', response)
    
  } catch (error) {
    showNotification(`Error procesando audio: ${error.message}`, 'error')
  } finally {
    isProcessing.value = false
  }
}

const shareRecording = async () => {
  if (!currentRecording.value) return
  
  try {
    if (navigator.share && navigator.canShare) {
      const shareData = {
        title: currentRecording.value.name,
        files: [new File([currentRecording.value.blob], currentRecording.value.name, { 
          type: currentRecording.value.mimeType 
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
        [currentRecording.value.mimeType]: currentRecording.value.blob
      })
    ])
    
    showNotification('Copiado al portapapeles', 'success')
    
  } catch (error) {
    showNotification('Error compartiendo grabación', 'error')
  }
}

const saveToLibrary = () => {
  if (!currentRecording.value) return
  
  try {
    recordings.value.unshift({ ...currentRecording.value })
    
    // Guardar en localStorage si está disponible
    try {
      const recordingsData = recordings.value.map(r => ({
        ...r,
        url: undefined, // No guardar URLs
        blob: undefined // No guardar blobs en localStorage
      }))
      localStorage.setItem('voiceRecorderLibrary', JSON.stringify(recordingsData))
    } catch (error) {
      // Ignorar errores de localStorage
    }
    
    showNotification('Grabación guardada en biblioteca', 'success')
    
  } catch (error) {
    showNotification('Error guardando en biblioteca', 'error')
  }
}

// ============================================================================
// GESTIÓN DE BIBLIOTECA
// ============================================================================

const playLibraryRecording = (recording) => {
  if (audioPlayer.value && recording.url) {
    audioPlayer.value.src = recording.url
    audioPlayer.value.load()
    audioPlayer.value.play()
  }
}

const downloadLibraryRecording = (recording) => {
  if (recording.url) {
    const a = document.createElement('a')
    a.href = recording.url
    a.download = recording.name
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }
}

const deleteLibraryRecording = (recordingId) => {
  const index = recordings.value.findIndex(r => r.id === recordingId)
  if (index !== -1) {
    const recording = recordings.value[index]
    if (recording.url) {
      URL.revokeObjectURL(recording.url)
    }
    recordings.value.splice(index, 1)
    showNotification('Grabación eliminada de biblioteca', 'info')
  }
}

const clearLibrary = () => {
  recordings.value.forEach(recording => {
    if (recording.url) {
      URL.revokeObjectURL(recording.url)
    }
  })
  recordings.value = []
  
  try {
    localStorage.removeItem('voiceRecorderLibrary')
  } catch (error) {
    // Ignorar errores
  }
  
  showNotification('Biblioteca limpiada', 'info')
}

const exportLibrary = () => {
  recordings.value.forEach(recording => {
    setTimeout(() => downloadLibraryRecording(recording), 100)
  })
}

// ============================================================================
// UTILIDADES
// ============================================================================

const formatDuration = (seconds) => {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }
  return `${minutes}:${secs.toString().padStart(2, '0')}`
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

const getFileExtension = (mimeType) => {
  if (mimeType.includes('webm')) return 'webm'
  if (mimeType.includes('mp4')) return 'm4a'
  if (mimeType.includes('wav')) return 'wav'
  return 'audio'
}

const clearVisualizer = () => {
  if (visualizerCanvas.value) {
    const ctx = visualizerCanvas.value.getContext('2d')
    ctx.clearRect(0, 0, visualizerCanvas.value.width, visualizerCanvas.value.height)
  }
}

const requestPermissions = async () => {
  try {
    await navigator.mediaDevices.getUserMedia({ audio: true })
    await checkSupport()
    showNotification('Permisos concedidos', 'success')
  } catch (error) {
    showNotification('Permisos denegados', 'error')
  }
}

const loadAudioDevices = async () => {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices()
    audioDevices.value = devices.filter(device => device.kind === 'audioinput')
  } catch (error) {
    console.warn('Error loading audio devices:', error)
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
    
    if (isSupported.value) {
      await loadAudioDevices()
    }
    
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
  
  // Configurar tamaño del visualizador
  await nextTick()
  if (visualizerContainer.value) {
    visualizerWidth.value = visualizerContainer.value.clientWidth
  }
  
  appStore.addToLog('VoiceRecorder component mounted', 'info')
  
  // EXPONER FUNCIÓN GLOBAL PARA COMPATIBILIDAD
  window.toggleVoiceRecording = toggleRecording
})

onUnmounted(() => {
  // Limpiar recursos
  cleanupRecording()
  clearRecording()
  clearLibrary()
  
  // Limpiar función global
  if (typeof window !== 'undefined') {
    delete window.toggleVoiceRecording
  }
  
  appStore.addToLog('VoiceRecorder component unmounted', 'info')
})

// Watchers
watch(() => config.value.quality, () => {
  appStore.addToLog(`Voice recording quality changed to: ${config.value.quality}`, 'info')
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
}

.status-indicator.paused {
  background: rgba(237, 137, 54, 0.1);
  color: var(--warning-color);
  border: 1px solid var(--warning-color);
}

.status-indicator.not-supported {
  background: rgba(160, 174, 192, 0.1);
  color: var(--text-muted);
  border: 1px solid var(--text-muted);
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
}

.audio-visualizer canvas {
  width: 100%;
  height: 100%;
  background: linear-gradient(45deg, #1a1a2e, #16213e);
}

.visualizer-placeholder {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
}

.placeholder-icon {
  font-size: 2rem;
  margin-bottom: 10px;
  opacity: 0.6;
}

.recorder-controls {
  display: flex;
  gap: 10px;
  margin-bottom: 25px;
  flex-wrap: wrap;
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
  background: var(--primary-color);
  color: white;
  font-size: 1.1rem;
  padding: 12px 20px;
}

.btn-record.recording {
  background: var(--error-color);
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
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

.btn-success {
  background: var(--success-color);
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

.volume-control {
  margin-bottom: 25px;
}

.volume-control h4 {
  color: var(--text-primary);
  margin-bottom: 15px;
}

.volume-meter {
  display: flex;
  align-items: center;
  gap: 15px;
}

.volume-label {
  color: var(--text-primary);
  font-weight: 500;
  min-width: 120px;
}

.volume-bar {
  flex: 1;
  height: 12px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  overflow: hidden;
  position: relative;
}

.volume-fill {
  height: 100%;
  background: var(--success-color);
  border-radius: var(--radius-sm);
  transition: width 0.1s ease;
}

.volume-fill.volume-medium {
  background: var(--warning-color);
}

.volume-fill.volume-high {
  background: var(--error-color);
}

.volume-value {
  color: var(--text-primary);
  font-weight: 500;
  min-width: 40px;
  text-align: right;
}

.recording-player {
  margin-bottom: 25px;
}

.recording-player h4 {
  color: var(--text-primary);
  margin-bottom: 15px;
}

.player-controls {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 10px;
}

.playback-time {
  color: var(--text-secondary);
  font-family: monospace;
}

.progress-bar {
  height: 8px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  margin-bottom: 15px;
}

.progress-fill {
  height: 100%;
  background: var(--primary-color);
  border-radius: var(--radius-sm);
  transition: width 0.1s ease;
}

.file-actions {
  margin-bottom: 25px;
}

.file-actions h4 {
  color: var(--text-primary);
  margin-bottom: 15px;
}

.action-buttons {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.recordings-library {
  margin-bottom: 25px;
}

.recordings-library h4 {
  color: var(--text-primary);
  margin-bottom: 15px;
}

.library-controls {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
}

.recordings-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.recording-item {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.recording-info {
  flex: 1;
}

.recording-name {
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.recording-details {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin-bottom: 2px;
}

.recording-date {
  color: var(--text-muted);
  font-size: 0.8rem;
}

.recording-actions {
  display: flex;
  gap: 5px;
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
  
  .volume-meter {
    flex-direction: column;
    align-items: stretch;
  }
  
  .volume-label {
    min-width: auto;
  }
  
  .player-controls {
    flex-direction: column;
    align-items: stretch;
    text-align: center;
  }
  
  .action-buttons {
    flex-direction: column;
  }
  
  .library-controls {
    flex-direction: column;
  }
  
  .recording-item {
    flex-direction: column;
    text-align: center;
  }
  
  .recording-actions {
    justify-content: center;
  }
}
</style>
