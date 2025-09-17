<template>
  <div class="conversation-test-result">
    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner">⏳</div>
      <p>Probando conversación...</p>
    </div>
    
    <!-- Test Results -->
    <div v-else-if="results" class="test-results-content">
      <!-- Success/Error Header -->
      <div 
        class="result-header"
        :class="getResultClass(results.status || 'success')"
      >
        <span class="result-icon">{{ getResultIcon(results.status || 'success') }}</span>
        <h4 class="result-title">{{ getResultTitle(results.status || 'success') }}</h4>
      </div>
      
      <!-- Test Details -->
      <div class="test-details">
        <!-- Input Message -->
        <div class="test-section">
          <div class="section-header">
            <span class="section-icon">📤</span>
            <strong>Mensaje enviado:</strong>
          </div>
          <div class="message-content user-message">
            {{ results.message || results.input || 'N/A' }}
          </div>
        </div>
        
        <!-- AI Response -->
        <div class="test-section">
          <div class="section-header">
            <span class="section-icon">📥</span>
            <strong>Respuesta del sistema:</strong>
          </div>
          <div class="message-content assistant-message">
            {{ results.response || 'No se recibió respuesta' }}
          </div>
        </div>
        
        <!-- Metadata Section -->
        <div class="test-metadata">
          <div class="metadata-grid">
            <div class="metadata-item">
              <span class="metadata-label">👤 Usuario:</span>
              <span class="metadata-value">{{ results.user_id || 'test-user' }}</span>
            </div>
            <div class="metadata-item">
              <span class="metadata-label">🕒 Timestamp:</span>
              <span class="metadata-value">{{ formatTimestamp(results.timestamp) }}</span>
            </div>
            <div class="metadata-item">
              <span class="metadata-label">🏢 Empresa:</span>
              <span class="metadata-value">{{ results.company || getCurrentCompany() }}</span>
            </div>
            <div v-if="results.response_time" class="metadata-item">
              <span class="metadata-label">⚡ Tiempo:</span>
              <span class="metadata-value">{{ formatResponseTime(results.response_time) }}</span>
            </div>
          </div>
        </div>
        
        <!-- Debug Information (Expandable) -->
        <div v-if="results.debug_info" class="debug-section">
          <details class="debug-details">
            <summary class="debug-summary">
              <span class="debug-icon">🔧</span>
              <strong>Información de debug</strong>
              <span class="debug-toggle">▼</span>
            </summary>
            <div class="debug-content">
              <pre class="debug-data">{{ formatDebugInfo(results.debug_info) }}</pre>
            </div>
          </details>
        </div>
        
        <!-- Error Details (if any) -->
        <div v-if="results.error || results.errors" class="error-section">
          <div class="section-header error-header">
            <span class="section-icon">❌</span>
            <strong>Detalles del error:</strong>
          </div>
          <div class="error-content">
            <div v-if="results.error" class="error-message">
              {{ results.error }}
            </div>
            <div v-if="results.errors && Array.isArray(results.errors)">
              <div 
                v-for="(error, index) in results.errors"
                :key="index"
                class="error-message"
              >
                {{ error }}
              </div>
            </div>
          </div>
        </div>
        
        <!-- Performance Metrics -->
        <div v-if="hasPerformanceMetrics" class="performance-section">
          <div class="section-header">
            <span class="section-icon">📊</span>
            <strong>Métricas de rendimiento:</strong>
          </div>
          <div class="metrics-grid">
            <div v-if="results.token_count" class="metric-item">
              <span class="metric-label">Tokens:</span>
              <span class="metric-value">{{ results.token_count }}</span>
            </div>
            <div v-if="results.model_used" class="metric-item">
              <span class="metric-label">Modelo:</span>
              <span class="metric-value">{{ results.model_used }}</span>
            </div>
            <div v-if="results.context_size" class="metric-item">
              <span class="metric-label">Contexto:</span>
              <span class="metric-value">{{ results.context_size }} tokens</span>
            </div>
            <div v-if="results.confidence_score" class="metric-item">
              <span class="metric-label">Confianza:</span>
              <span class="metric-value">{{ Math.round(results.confidence_score * 100) }}%</span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Action Buttons -->
      <div class="result-actions">
        <button 
          @click="copyResults"
          class="action-btn copy-btn"
          title="Copiar resultados"
        >
          📋 Copiar
        </button>
        <button 
          @click="shareResults"
          class="action-btn share-btn"
          title="Compartir resultados"
        >
          🔗 Compartir
        </button>
        <button 
          @click="retryTest"
          class="action-btn retry-btn"
          title="Repetir prueba"
        >
          🔄 Repetir
        </button>
        <button 
          v-if="showAdvancedOptions"
          @click="analyzeResults"
          class="action-btn analyze-btn"
          title="Analizar en detalle"
        >
          📈 Analizar
        </button>
      </div>
    </div>
    
    <!-- Empty State -->
    <div v-else class="empty-results">
      <div class="empty-icon">🧪</div>
      <p>Los resultados de la prueba aparecerán aquí</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useAppStore } from '@/stores/app'
import { useNotifications } from '@/composables/useNotifications'

// ============================================================================
// PROPS & EMITS
// ============================================================================

const props = defineProps({
  results: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  },
  showAdvancedOptions: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['retry', 'analyze'])

// ============================================================================
// STORES & COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const { showNotification } = useNotifications()

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const hasPerformanceMetrics = computed(() => {
  if (!props.results) return false
  
  return !!(
    props.results.token_count ||
    props.results.model_used ||
    props.results.context_size ||
    props.results.confidence_score ||
    props.results.response_time
  )
})

// ============================================================================
// MÉTODOS
// ============================================================================

/**
 * Get result class based on status
 */
const getResultClass = (status) => {
  const classMap = {
    'success': 'result-success',
    'error': 'result-error',
    'warning': 'result-warning',
    'partial': 'result-partial'
  }
  return classMap[status] || 'result-success'
}

/**
 * Get result icon based on status
 */
const getResultIcon = (status) => {
  const iconMap = {
    'success': '✅',
    'error': '❌',
    'warning': '⚠️',
    'partial': '🔶'
  }
  return iconMap[status] || '✅'
}

/**
 * Get result title based on status
 */
const getResultTitle = (status) => {
  const titleMap = {
    'success': 'Conversación Probada Exitosamente',
    'error': 'Error en la Prueba de Conversación',
    'warning': 'Prueba Completada con Advertencias',
    'partial': 'Respuesta Parcial Obtenida'
  }
  return titleMap[status] || 'Conversación Probada Exitosamente'
}

/**
 * Format timestamp
 */
const formatTimestamp = (timestamp) => {
  if (!timestamp) return new Date().toLocaleString()
  
  try {
    if (typeof timestamp === 'number') {
      return new Date(timestamp * 1000).toLocaleString()
    }
    return new Date(timestamp).toLocaleString()
  } catch {
    return 'Fecha inválida'
  }
}

/**
 * Format response time
 */
const formatResponseTime = (responseTime) => {
  if (!responseTime) return 'N/A'
  
  if (typeof responseTime === 'number') {
    if (responseTime < 1) {
      return `${Math.round(responseTime * 1000)}ms`
    }
    return `${responseTime.toFixed(2)}s`
  }
  
  return String(responseTime)
}

/**
 * Format debug info
 */
const formatDebugInfo = (debugInfo) => {
  if (typeof debugInfo === 'string') return debugInfo
  return JSON.stringify(debugInfo, null, 2)
}

/**
 * Get current company
 */
const getCurrentCompany = () => {
  return appStore.currentCompanyId || 'N/A'
}

/**
 * Copy results to clipboard
 */
const copyResults = async () => {
  if (!props.results) return
  
  try {
    const text = [
      '=== RESULTADOS DE PRUEBA DE CONVERSACIÓN ===',
      `Usuario: ${props.results.user_id || 'test-user'}`,
      `Empresa: ${props.results.company || getCurrentCompany()}`,
      `Timestamp: ${formatTimestamp(props.results.timestamp)}`,
      '',
      '--- MENSAJE ENVIADO ---',
      props.results.message || props.results.input || 'N/A',
      '',
      '--- RESPUESTA DEL SISTEMA ---',
      props.results.response || 'No se recibió respuesta',
      ''
    ]
    
    if (hasPerformanceMetrics.value) {
      text.push('--- MÉTRICAS ---')
      if (props.results.token_count) text.push(`Tokens: ${props.results.token_count}`)
      if (props.results.model_used) text.push(`Modelo: ${props.results.model_used}`)
      if (props.results.response_time) text.push(`Tiempo: ${formatResponseTime(props.results.response_time)}`)
      text.push('')
    }
    
    if (props.results.debug_info) {
      text.push('--- DEBUG INFO ---')
      text.push(formatDebugInfo(props.results.debug_info))
    }
    
    await navigator.clipboard.writeText(text.join('\n'))
    showNotification('📋 Resultados copiados al portapapeles', 'success', 2000)
    
  } catch (error) {
    console.error('Error copying results:', error)
    showNotification('❌ Error al copiar resultados', 'error')
  }
}

/**
 * Share results
 */
const shareResults = () => {
  if (!navigator.share) {
    copyResults()
    return
  }
  
  const shareData = {
    title: 'Resultados de Prueba de Conversación',
    text: `Prueba exitosa: "${props.results.message}" → "${props.results.response}"`
  }
  
  navigator.share(shareData).catch((error) => {
    console.error('Error sharing:', error)
    copyResults()
  })
}

/**
 * Retry test
 */
const retryTest = () => {
  emit('retry')
  showNotification('🔄 Preparando nueva prueba...', 'info', 2000)
}

/**
 * Analyze results
 */
const analyzeResults = () => {
  emit('analyze', props.results)
  showNotification('📈 Iniciando análisis detallado...', 'info', 2000)
}
</script>

<style scoped>
.conversation-test-result {
  width: 100%;
  min-height: 100px;
}

.loading-state {
  text-align: center;
  padding: 30px 20px;
  color: var(--text-secondary);
}

.loading-spinner {
  font-size: 1.5em;
  margin-bottom: 10px;
  animation: spin 1s linear infinite;
}

.test-results-content {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 15px 20px;
  border-bottom: 1px solid var(--border-color);
}

.result-success {
  background: rgba(34, 197, 94, 0.1);
  border-color: var(--success-color);
}

.result-error {
  background: rgba(239, 68, 68, 0.1);
  border-color: var(--danger-color);
}

.result-warning {
  background: rgba(245, 158, 11, 0.1);
  border-color: var(--warning-color);
}

.result-partial {
  background: rgba(59, 130, 246, 0.1);
  border-color: var(--info-color);
}

.result-icon {
  font-size: 1.3em;
}

.result-title {
  margin: 0;
  font-size: 1.1em;
  color: var(--text-primary);
}

.test-details {
  padding: 20px;
}

.test-section {
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  color: var(--text-primary);
  font-weight: 500;
}

.section-icon {
  font-size: 1.1em;
}

.message-content {
  padding: 12px 15px;
  border-radius: 8px;
  line-height: 1.5;
  word-wrap: break-word;
  white-space: pre-wrap;
}

.user-message {
  background: rgba(102, 126, 234, 0.1);
  border-left: 3px solid var(--primary-color);
  color: var(--text-primary);
}

.assistant-message {
  background: rgba(34, 197, 94, 0.1);
  border-left: 3px solid var(--success-color);
  color: var(--text-primary);
}

.test-metadata {
  margin: 20px 0;
  padding: 15px;
  background: var(--bg-secondary);
  border-radius: 6px;
}

.metadata-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 10px;
}

.metadata-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.9em;
}

.metadata-label {
  color: var(--text-secondary);
  font-weight: 500;
}

.metadata-value {
  color: var(--text-primary);
  font-weight: 600;
  font-family: monospace;
}

.debug-section {
  margin-top: 20px;
}

.debug-details {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
}

.debug-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 15px;
  cursor: pointer;
  user-select: none;
  list-style: none;
}

.debug-summary::-webkit-details-marker {
  display: none;
}

.debug-icon {
  font-size: 1.1em;
}

.debug-toggle {
  margin-left: auto;
  font-size: 0.8em;
  color: var(--text-muted);
}

.debug-details[open] .debug-toggle {
  transform: rotate(180deg);
}

.debug-content {
  border-top: 1px solid var(--border-color);
  padding: 15px;
}

.debug-data {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 10px;
  font-size: 0.8em;
  color: var(--text-secondary);
  margin: 0;
  overflow-x: auto;
  white-space: pre;
}

.error-section {
  margin-top: 20px;
}

.error-header {
  color: var(--danger-color);
}

.error-content {
  background: rgba(239, 68, 68, 0.05);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 6px;
  padding: 12px 15px;
}

.error-message {
  color: var(--danger-color);
  margin-bottom: 8px;
  line-height: 1.4;
}

.error-message:last-child {
  margin-bottom: 0;
}

.performance-section {
  margin-top: 20px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
  margin-top: 10px;
}

.metric-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--bg-secondary);
  border-radius: 4px;
  font-size: 0.9em;
}

.metric-label {
  color: var(--text-secondary);
  font-weight: 500;
}

.metric-value {
  color: var(--text-primary);
  font-weight: 600;
}

.result-actions {
  display: flex;
  gap: 8px;
  padding: 15px 20px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-secondary);
  flex-wrap: wrap;
}

.action-btn {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--bg-primary);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 0.85em;
  font-weight: 500;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.action-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.copy-btn:hover {
  border-color: var(--info-color);
  color: var(--info-color);
}

.share-btn:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.retry-btn:hover {
  border-color: var(--warning-color);
  color: var(--warning-color);
}

.analyze-btn:hover {
  border-color: var(--success-color);
  color: var(--success-color);
}

.empty-results {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-muted);
}

.empty-icon {
  font-size: 2em;
  margin-bottom: 10px;
  opacity: 0.5;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Responsive */
@media (max-width: 768px) {
  .metadata-grid {
    grid-template-columns: 1fr;
  }
  
  .metrics-grid {
    grid-template-columns: 1fr;
  }
  
  .result-actions {
    flex-direction: column;
  }
  
  .action-btn {
    text-align: center;
  }
  
  .metadata-item,
  .metric-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
}

@media (max-width: 480px) {
  .test-details {
    padding: 15px;
  }
  
  .result-header {
    padding: 12px 15px;
  }
  
  .message-content {
    padding: 10px 12px;
  }
  
  .section-header {
    flex-wrap: wrap;
    gap: 6px;
  }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .loading-spinner {
    animation: none;
  }
  
  .debug-toggle {
    transition: none;
  }
}
</style>
