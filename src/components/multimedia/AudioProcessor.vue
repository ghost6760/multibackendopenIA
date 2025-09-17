<template>
  <div class="audio-processor">
    <h3 class="processor-title">🎵 Procesamiento de Audio</h3>
    
    <!-- Área de carga de archivo -->
    <div class="upload-area">
      <div 
        class="file-drop-zone"
        :class="{ 'drag-over': isDragOver, 'has-file': selectedFile }"
        @drop="handleDrop"
        @dragover.prevent="isDragOver = true"
        @dragleave.prevent="isDragOver = false"
        @click="triggerFileInput"
      >
        <input
          ref="fileInput"
          type="file"
          accept="audio/*"
          @change="handleFileSelect"
          hidden
        />
        
        <div v-if="!selectedFile" class="drop-zone-content">
          <div class="drop-icon">🎤</div>
          <p class="drop-text">Arrastra un archivo de audio aquí</p>
          <p class="drop-subtext">o haz clic para seleccionar</p>
          <div class="supported-formats">
            Formatos: MP3, WAV, M4A, AAC, OGG
          </div>
        </div>
        
        <div v-else class="selected-file">
          <div class="file-icon">🎵</div>
          <div class="file-info">
            <div class="file-name">{{ selectedFile.name }}</div>
            <div class="file-details">
              {{ formatFileSize(selectedFile.size) }} • {{ selectedFile.type }}
            </div>
          </div>
          <button @click.stop="clearFile" class="remove-file">✕</button>
        </div>
      </div>
    </div>

    <!-- Configuración de procesamiento -->
    <div class="processing-config">
      <h4>⚙️ Configuración</h4>
      
      <div class="config-grid">
        <div class="config-item">
          <label for="language">Idioma:</label>
          <select id="language" v-model="config.language">
            <option value="auto">Auto-detectar</option>
            <option value="es">Español</option>
            <option value="en">Inglés</option>
            <option value="fr">Francés</option>
            <option value="de">Alemán</option>
            <option value="it">Italiano</option>
            <option value="pt">Portugués</option>
          </select>
        </div>
        
        <div class="config-item">
          <label for="quality">Calidad:</label>
          <select id="quality" v-model="config.quality">
            <option value="standard">Estándar</option>
            <option value="high">Alta</option>
            <option value="ultra">Ultra</option>
          </select>
        </div>
        
        <div class="config-item full-width">
          <label for="prompt">Prompt personalizado (opcional):</label>
          <textarea
            id="prompt"
            v-model="config.prompt"
            placeholder="Proporciona contexto o instrucciones específicas para el procesamiento..."
            rows="3"
          ></textarea>
        </div>
      </div>
    </div>

    <!-- Controles -->
    <div class="processor-controls">
      <button 
        class="btn btn-primary"
        @click="processAudio"
        :disabled="!selectedFile || isProcessing"
      >
        <span v-if="isProcessing">⏳ Procesando...</span>
        <span v-else>🔄 Procesar Audio</span>
      </button>
      
      <button 
        class="btn btn-secondary"
        @click="clearAll"
        :disabled="isProcessing"
      >
        🗑️ Limpiar
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
      <h4>📊 Resultado del Procesamiento</h4>
      
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
        <!-- Transcripción -->
        <div v-if="activeResultTab === 'transcription'" class="result-section">
          <div class="transcription-text">
            {{ result.transcription || 'No se pudo generar transcripción' }}
          </div>
          
          <div class="transcription-actions">
            <button @click="copyToClipboard(result.transcription)" class="btn btn-sm">
              📋 Copiar
            </button>
            <button @click="downloadTranscription" class="btn btn-sm">
              💾 Descargar
            </button>
          </div>
        </div>
        
        <!-- Análisis -->
        <div v-if="activeResultTab === 'analysis'" class="result-section">
          <div v-if="result.analysis" class="analysis-grid">
            <div v-for="(value, key) in result.analysis" :key="key" class="analysis-item">
              <label>{{ formatAnalysisKey(key) }}:</label>
              <span>{{ value }}</span>
            </div>
          </div>
          <div v-else class="no-analysis">
            No hay análisis disponible
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
        
        <!-- Audio procesado -->
        <div v-if="activeResultTab === 'audio' && result.processed_audio" class="result-section">
          <div class="audio-player">
            <audio controls :src="result.processed_audio">
              Tu navegador no soporta el reproductor de audio.
            </audio>
          </div>
          
          <div class="audio-actions">
            <button @click="downloadAudio" class="btn btn-sm">
              💾 Descargar Audio
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Historial reciente -->
    <div v-if="recentResults.length > 0" class="recent-results">
      <h4>📚 Procesamiento Reciente</h4>
      <div class="recent-list">
        <div 
          v-for="(item, index) in recentResults"
          :key="index"
          class="recent-item"
          @click="loadRecentResult(item)"
        >
          <div class="recent-icon">🎵</div>
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
import { ref, computed, onMounted, onUnmounted } from 'vue'
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

// ============================================================================
// ESTADO LOCAL
// ============================================================================

const selectedFile = ref(null)
const isDragOver = ref(false)
const isProcessing = ref(false)
const processingStage = ref('')
const processingProgress = ref(0)
const result = ref(null)
const activeResultTab = ref('transcription')
const recentResults = ref([])

// Configuración de procesamiento
const config = ref({
  language: 'auto',
  quality: 'standard',
  prompt: ''
})

// ============================================================================
// COMPUTED
// ============================================================================

const resultTabs = computed(() => {
  const tabs = [
    { id: 'transcription', name: 'Transcripción', icon: '📝' }
  ]
  
  if (result.value?.analysis) {
    tabs.push({ id: 'analysis', name: 'Análisis', icon: '📊' })
  }
  
  if (result.value?.metadata) {
    tabs.push({ id: 'metadata', name: 'Metadatos', icon: '📋' })
  }
  
  if (result.value?.processed_audio) {
    tabs.push({ id: 'audio', name: 'Audio', icon: '🎵' })
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
    validateAndSetFile(file)
  }
}

const handleDrop = (event) => {
  event.preventDefault()
  isDragOver.value = false
  
  const files = event.dataTransfer.files
  if (files.length > 0) {
    validateAndSetFile(files[0])
  }
}

const validateAndSetFile = (file) => {
  // Validar tipo de archivo
  if (!file.type.startsWith('audio/')) {
    showNotification('Por favor selecciona un archivo de audio válido', 'error')
    return
  }
  
  // Validar tamaño (max 50MB)
  const maxSize = 50 * 1024 * 1024
  if (file.size > maxSize) {
    showNotification('El archivo es demasiado grande. Máximo 50MB', 'error')
    return
  }
  
  selectedFile.value = file
  result.value = null // Limpiar resultado anterior
  
  appStore.addToLog(`Audio file selected: ${file.name} (${formatFileSize(file.size)})`, 'info')
}

const clearFile = () => {
  selectedFile.value = null
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const clearAll = () => {
  clearFile()
  result.value = null
  config.value.prompt = ''
}

// ============================================================================
// PROCESAMIENTO DE AUDIO
// ============================================================================

const processAudio = async () => {
  if (!selectedFile.value) {
    showNotification('Por favor selecciona un archivo de audio', 'warning')
    return
  }
  
  isProcessing.value = true
  processingProgress.value = 0
  
  try {
    emit('processing', { 
      message: 'Preparando archivo de audio...', 
      progress: 0 
    })
    
    appStore.addToLog(`Starting audio processing: ${selectedFile.value.name}`, 'info')
    
    // Crear FormData
    const formData = new FormData()
    formData.append('audio', selectedFile.value)
    
    // Agregar configuración
    if (config.value.language !== 'auto') {
      formData.append('language', config.value.language)
    }
    formData.append('quality', config.value.quality)
    if (config.value.prompt.trim()) {
      formData.append('prompt', config.value.prompt.trim())
    }
    
    updateProgress('Enviando archivo al servidor...', 25)
    
    // Llamada a la API - PRESERVAR ENDPOINT EXACTO
    const response = await apiRequest('/api/multimedia/audio', {
      method: 'POST',
      body: formData
    })
    
    updateProgress('Procesando audio...', 75)
    
    // Simular progreso adicional si no hay WebSocket
    await simulateProgress(75, 95, 'Finalizando procesamiento...')
    
    updateProgress('Completado', 100)
    
    // Guardar resultado
    result.value = response
    activeResultTab.value = 'transcription'
    
    // Agregar al historial
    addToRecentResults({
      filename: selectedFile.value.name,
      timestamp: Date.now(),
      status: 'success',
      result: response
    })
    
    appStore.addToLog('Audio processing completed successfully', 'info')
    showNotification('Audio procesado exitosamente', 'success')
    
    emit('completed', response)
    
  } catch (error) {
    appStore.addToLog(`Audio processing failed: ${error.message}`, 'error')
    showNotification(`Error procesando audio: ${error.message}`, 'error')
    
    // Agregar al historial como error
    addToRecentResults({
      filename: selectedFile.value.name,
      timestamp: Date.now(),
      status: 'error',
      error: error.message
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

const downloadTranscription = () => {
  if (!result.value?.transcription) return
  
  const blob = new Blob([result.value.transcription], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  
  const a = document.createElement('a')
  a.href = url
  a.download = `transcription_${selectedFile.value.name.replace(/\.[^/.]+$/, '')}.txt`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  
  URL.revokeObjectURL(url)
  showNotification('Transcripción descargada', 'success')
}

const downloadAudio = () => {
  if (!result.value?.processed_audio) return
  
  const a = document.createElement('a')
  a.href = result.value.processed_audio
  a.download = `processed_${selectedFile.value.name}`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  
  showNotification('Audio descargado', 'success')
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
    localStorage.setItem('audioProcessorRecent', JSON.stringify(recentResults.value))
  } catch (error) {
    // Ignorar errores de localStorage
  }
}

const loadRecentResult = (item) => {
  if (item.status === 'success' && item.result) {
    result.value = item.result
    activeResultTab.value = 'transcription'
    showNotification('Resultado cargado del historial', 'info')
  }
}

const loadRecentResults = () => {
  try {
    const saved = localStorage.getItem('audioProcessorRecent')
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

onMounted(() => {
  loadRecentResults()
  appStore.addToLog('AudioProcessor component mounted', 'info')
})

onUnmounted(() => {
  appStore.addToLog('AudioProcessor component unmounted', 'info')
})
</script>

<style scoped>
.audio-processor {
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

.file-drop-zone {
  border: 2px dashed var(--border-color);
  border-radius: var(--radius-lg);
  padding: 30px;
  text-align: center;
  cursor: pointer;
  transition: var(--transition-normal);
  background: var(--bg-secondary);
}

.file-drop-zone:hover {
  border-color: var(--primary-color);
  background: rgba(102, 126, 234, 0.05);
}

.file-drop-zone.drag-over {
  border-color: var(--primary-color);
  background: rgba(102, 126, 234, 0.1);
  transform: scale(1.02);
}

.file-drop-zone.has-file {
  border-color: var(--success-color);
  background: rgba(72, 187, 120, 0.05);
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

.selected-file {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px;
  background: var(--bg-primary);
  border-radius: var(--radius-md);
  border: 1px solid var(--success-color);
}

.file-icon {
  font-size: 2rem;
}

.file-info {
  flex: 1;
  text-align: left;
}

.file-name {
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.file-details {
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.remove-file {
  background: var(--error-color);
  color: white;
  border: none;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 0.8rem;
}

.processing-config {
  margin-bottom: 25px;
}

.processing-config h4 {
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

.processor-controls {
  display: flex;
  gap: 10px;
  margin-bottom: 25px;
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

.transcription-text {
  background: var(--bg-secondary);
  padding: 15px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-light);
  line-height: 1.6;
  margin-bottom: 15px;
  min-height: 100px;
  white-space: pre-wrap;
}

.transcription-actions,
.audio-actions {
  display: flex;
  gap: 10px;
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

.audio-player {
  margin-bottom: 15px;
}

.audio-player audio {
  width: 100%;
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

.recent-icon {
  font-size: 1.2rem;
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
  
  .transcription-actions,
  .audio-actions {
    flex-direction: column;
  }
}
</style>
