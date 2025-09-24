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

    <!-- Controles principales - SIMPLES COMO SCRIPT.JS -->
    <div class="capture-controls">
      <button 
        class="btn btn-primary"
        @click="captureScreen"
        :disabled="isCapturing || !isSupported"
      >
        <span v-if="isCapturing">⏳ Capturando...</span>
        <span v-else>📸 Capturar Pantalla</span>
      </button>
      
      <button 
        class="btn btn-secondary"
        @click="clearResults"
        :disabled="isCapturing || !results"
      >
        🗑️ Limpiar
      </button>
    </div>

    <!-- Configuración simple -->
    <div class="capture-config">
      <h4>⚙️ Configuración</h4>
      
      <div class="config-grid">
        <div class="config-item">
          <label for="captureQuality">Calidad:</label>
          <select id="captureQuality" v-model="config.quality">
            <option value="standard">Estándar (1080p)</option>
            <option value="high">Alta (1440p)</option>
            <option value="ultra">Ultra (4K)</option>
          </select>
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

    <!-- Resultado de captura - ESTRUCTURA COMO SCRIPT.JS -->
    <div v-if="results" class="capture-result">
      <h4>📸 Captura Realizada</h4>
      
      <div class="result-content">
        <div class="capture-preview">
          <img :src="results.url" alt="Screen capture" />
        </div>
        
        <div class="capture-info">
          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">Dimensiones:</span>
              <span class="info-value">{{ results.dimensions?.width }}×{{ results.dimensions?.height }}px</span>
            </div>
            <div class="info-item">
              <span class="info-label">Tamaño:</span>
              <span class="info-value">{{ formatFileSize(results.blob?.size || 0) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Formato:</span>
              <span class="info-value">PNG</span>
            </div>
            <div class="info-item">
              <span class="info-label">Capturado:</span>
              <span class="info-value">{{ formatDateTime(results.timestamp) }}</span>
            </div>
          </div>
        </div>
        
        <div class="capture-actions">
          <button @click="downloadCapture" class="btn btn-primary">
            💾 Descargar
          </button>
          <button @click="viewFullscreen" class="btn btn-secondary">
            🔍 Ver Completo
          </button>
          <button @click="shareCapture" class="btn btn-info">
            📤 Compartir
          </button>
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

    <!-- Compatible with DOM manipulation from script.js -->
    <div id="screenCaptureResult" style="margin-top: 20px;"></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, defineProps, defineEmits } from 'vue'
import { useAppStore } from '@/stores/app'
import { useNotifications } from '@/composables/useNotifications'

// ============================================================================
// PROPS & EMITS - INTERFACE CON MULTIMEDIATAB
// ============================================================================

const props = defineProps({
  isCapturing: {
    type: Boolean,
    default: false
  },
  results: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['capture-screen', 'clear-results'])

// ============================================================================
// STORES & COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const { showNotification } = useNotifications()

// ============================================================================
// ESTADO LOCAL - SIMPLE COMO SCRIPT.JS
// ============================================================================

const isSupported = ref(false)

// Configuración simple
const config = ref({
  quality: 'standard',
  showCursor: true,
  autoDownload: false
})

// ============================================================================
// COMPUTED
// ============================================================================

const captureStatus = computed(() => {
  if (!isSupported.value) return 'not-supported'
  if (props.isCapturing) return 'capturing'
  return 'ready'
})

const statusIcon = computed(() => {
  switch (captureStatus.value) {
    case 'not-supported': return '⚠️'
    case 'capturing': return '⏳'
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
    standard: { width: 1920, height: 1080 },
    high: { width: 2560, height: 1440 },
    ultra: { width: 3840, height: 2160 }
  }
  
  return constraints[config.value.quality] || constraints.standard
})

// ============================================================================
// MÉTODOS PRINCIPALES - DELEGAR AL COMPOSABLE
// ============================================================================

/**
 * Captura pantalla - DELEGAR AL COMPOSABLE COMO SCRIPT.JS
 */
const captureScreen = async () => {
  if (!isSupported.value) {
    showNotification('Captura de pantalla no soportada', 'error')
    return
  }
  
  try {
    appStore.addToLog('Starting screen capture from component', 'info')
    
    // Configurar opciones según script.js
    const options = {
      quality: config.value.quality,
      showCursor: config.value.showCursor,
      autoDownload: config.value.autoDownload
    }
    
    // Delegar al composable via emit
    const result = await emit('capture-screen', options)
    
    // Auto-descarga si está habilitada
    if (config.value.autoDownload && props.results) {
      downloadCapture()
    }
    
  } catch (error) {
    showNotification(`Error capturando pantalla: ${error.message}`, 'error')
  }
}

const clearResults = () => {
  emit('clear-results')
}

// ============================================================================
// ACCIONES DE ARCHIVO
// ============================================================================

const downloadCapture = () => {
  if (!props.results?.url) return
  
  try {
    const a = document.createElement('a')
    a.href = props.results.url
    a.download = `screen_capture_${new Date().toISOString().replace(/[:.]/g, '-')}.png`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    
    showNotification('Captura descargada', 'success')
  } catch (error) {
    showNotification('Error descargando captura', 'error')
  }
}

const viewFullscreen = () => {
  if (!props.results?.url) return
  
  try {
    window.open(props.results.url, '_blank')
  } catch (error) {
    showNotification('Error abriendo captura', 'error')
  }
}

const shareCapture = async () => {
  if (!props.results?.blob) return
  
  try {
    if (navigator.share && navigator.canShare) {
      const shareData = {
        title: 'Captura de Pantalla',
        files: [new File([props.results.blob], 'screen_capture.png', { 
          type: 'image/png' 
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
        'image/png': props.results.blob
      })
    ])
    
    showNotification('Copiado al portapapeles', 'success')
    
  } catch (error) {
    showNotification('Error compartiendo captura', 'error')
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

const formatDateTime = (timestamp) => {
  if (!timestamp) return 'Desconocido'
  return new Date(timestamp).toLocaleString()
}

const checkSupport = () => {
  isSupported.value = !!(
    navigator.mediaDevices && 
    navigator.mediaDevices.getDisplayMedia &&
    (window.location.protocol === 'https:' || 
     window.location.hostname === 'localhost')
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
})

onUnmounted(() => {
  appStore.addToLog('ScreenCapture component unmounted', 'info')
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
  background: rgba(102, 126, 234, 0.1);
  color: var(--primary-color);
  border: 1px solid var(--primary-color);
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

.capture-result {
  margin-bottom: 25px;
}

.capture-result h4 {
  color: var(--text-primary);
  margin-bottom: 15px;
}

.result-content {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 20px;
}

.capture-preview {
  text-align: center;
  margin-bottom: 20px;
}

.capture-preview img {
  max-width: 100%;
  max-height: 300px;
  object-fit: contain;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.capture-info {
  margin-bottom: 20px;
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

.capture-actions {
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
  .capture-controls {
    flex-direction: column;
  }
  
  .config-grid {
    grid-template-columns: 1fr;
  }
  
  .capture-actions {
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
