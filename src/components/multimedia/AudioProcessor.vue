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
            Formatos: MP3, WAV, M4A, AAC, OGG, WebM
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

    <!-- Campos exactos como script.js -->
    <div class="form-fields">
      <div class="form-group">
        <label for="audioUserId">ID de Usuario:</label>
        <input 
          id="audioUserId"
          type="text" 
          v-model="userId"
          placeholder="usuario_123"
          class="form-input"
        />
      </div>
      
      <div class="form-group">
        <label for="audioLanguage">Idioma (opcional):</label>
        <select id="audioLanguage" v-model="config.language" class="form-select">
          <option value="">Auto-detectar</option>
          <option value="es">Español</option>
          <option value="en">Inglés</option>
          <option value="fr">Francés</option>
          <option value="de">Alemán</option>
          <option value="it">Italiano</option>
          <option value="pt">Portugués</option>
        </select>
      </div>
      
      <div class="form-group full-width">
        <label for="audioPrompt">Prompt personalizado (opcional):</label>
        <textarea
          id="audioPrompt"
          v-model="config.prompt"
          placeholder="Proporciona contexto específico para el procesamiento del audio..."
          rows="3"
          class="form-textarea"
        ></textarea>
      </div>
    </div>

    <!-- Controles -->
    <div class="processor-controls">
      <button 
        class="btn btn-primary"
        @click="processAudio"
        :disabled="!selectedFile || !userId.trim() || isProcessing"
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
        <span>{{ progress }}%</span>
      </div>
      <div class="progress-bar">
        <div 
          class="progress-fill"
          :style="{ width: progress + '%' }"
        ></div>
      </div>
    </div>

    <!-- IMPORTANTE: Resultados SOLO para archivos de audio (NO grabaciones) -->
    <div v-if="results" class="processing-result">
      <h4>📊 Resultado del Procesamiento de Audio</h4>
      
      <div class="result-content">
        <!-- Transcripción -->
        <div class="result-section">
          <h5>📝 Transcripción:</h5>
          <div class="transcription-text">
            {{ getTranscription(results) }}
          </div>
          
          <div class="transcription-actions">
            <button @click="copyToClipboard(getTranscription(results))" class="btn btn-sm">
              📋 Copiar
            </button>
            <button @click="downloadTranscription" class="btn btn-sm">
              💾 Descargar
            </button>
          </div>
        </div>
        
        <!-- Respuesta del Bot -->
        <div v-if="getBotResponse(results)" class="result-section">
          <h5>🤖 Respuesta del Bot:</h5>
          <div class="bot-response-text">
            {{ getBotResponse(results) }}
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
              <span class="info-value">{{ selectedFile?.name }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Tamaño:</span>
              <span class="info-value">{{ formatFileSize(selectedFile?.size || 0) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Tipo:</span>
              <span class="info-value">Archivo subido</span>
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

    <!-- Compatible with DOM manipulation from script.js -->
    <div id="audioResult" style="margin-top: 20px;"></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, defineProps, defineEmits } from 'vue'
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

const emit = defineEmits(['process-audio', 'clear-results'])

// ============================================================================
// STORES & COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const { showNotification } = useNotifications()

// ============================================================================
// REFS
// ============================================================================

const fileInput = ref(null)

// ============================================================================
// ESTADO LOCAL - ESTRUCTURA EXACTA SCRIPT.JS
// ============================================================================

const selectedFile = ref(null)
const isDragOver = ref(false)
const processingStage = ref('')

// Campos exactos como en script.js DOM
const userId = ref('')
const config = ref({
  language: '', // Corresponde a script.js language option
  prompt: ''    // Corresponde a script.js prompt option
})

// ============================================================================
// COMPUTED
// ============================================================================

const canProcess = computed(() => {
  return selectedFile.value && userId.value.trim() && !props.isProcessing && appStore.currentCompanyId
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
  // PRESERVAR: Validaciones exactas como script.js
  if (!file.type.startsWith('audio/')) {
    showNotification('El archivo debe ser de audio', 'error')
    return
  }
  
  // PRESERVAR: Límite de tamaño exacto como script.js
  const maxSize = 50 * 1024 * 1024 // 50MB
  if (file.size > maxSize) {
    showNotification('El archivo es demasiado grande. Máximo 50MB', 'error')
    return
  }
  
  selectedFile.value = file
  
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
  userId.value = ''
  config.value.language = ''
  config.value.prompt = ''
  emit('clear-results')
}

// ============================================================================
// PROCESAMIENTO - DELEGAR AL COMPOSABLE
// ============================================================================

const processAudio = async () => {
  if (!canProcess.value) {
    if (!appStore.currentCompanyId) {
      showNotification('Por favor selecciona una empresa primero', 'warning')
      return
    }
    if (!selectedFile.value) {
      showNotification('Por favor selecciona un archivo de audio', 'warning')
      return
    }
    if (!userId.value.trim()) {
      showNotification('Por favor ingresa un ID de usuario', 'warning')
      return
    }
    return
  }
  
  processingStage.value = 'Preparando archivo de audio...'
  
  try {
    // ESTRUCTURA EXACTA: Pasar datos como script.js
    const options = {}
    if (config.value.language) options.language = config.value.language
    if (config.value.prompt.trim()) options.prompt = config.value.prompt.trim()
    
    // IMPORTANTE: También actualizar DOM para compatibilidad script.js
    const userIdInput = document.getElementById('audioUserId')
    if (userIdInput) userIdInput.value = userId.value
    
    // IMPORTANTE: Usar processAudio (NO processVoiceRecording)
    // Esto va al composable y usa audioResults
    await emit('process-audio', selectedFile.value, options)
    
  } catch (error) {
    showNotification(`Error procesando audio: ${error.message}`, 'error')
  }
}

// ============================================================================
// EXTRACTORS - ESTRUCTURA EXACTA COMO SCRIPT.JS CORREGIDO
// ============================================================================

const getTranscription = (results) => {
  if (!results) return 'Sin transcripción'
  
  // PRESERVAR: Orden exacto de campos como script.js corregido
  return results.transcript || results.transcription || 'Sin transcripción'
}

const getBotResponse = (results) => {
  if (!results) return null
  
  // PRESERVAR: Orden exacto de campos como script.js corregido
  return results.bot_response || results.response || results.message || null
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

const downloadTranscription = () => {
  if (!props.results) return
  
  const transcription = getTranscription(props.results)
  const blob = new Blob([transcription], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  
  const a = document.createElement('a')
  a.href = url
  a.download = `audio_transcription_${selectedFile.value?.name.replace(/\.[^/.]+$/, '') || 'audio'}.txt`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  
  URL.revokeObjectURL(url)
  showNotification('Transcripción descargada', 'success')
}

// ============================================================================
// LIFECYCLE
// ============================================================================

onMounted(() => {
  appStore.addToLog('AudioProcessor component mounted (independent)', 'info')
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
  margin-bottom: 20px;
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
  
  .transcription-actions {
    flex-direction: column;
  }
  
  .info-grid {
    grid-template-columns: 1fr;
  }
  
  .info-item {
    flex-direction: column;
    gap: 4px;
  }
}
</style>
