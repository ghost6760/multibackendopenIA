<template>
  <div class="system-diagnostics">
    <div class="diagnostics-header">
      <h3>🔍 Diagnósticos del Sistema</h3>
      <p>Ejecuta diagnósticos completos para verificar el estado de todos los componentes del sistema</p>
    </div>
    
    <div class="diagnostics-controls">
      <button 
        @click="runSystemDiagnostics" 
        :disabled="isRunningDiagnostics"
        class="btn btn-primary"
      >
        <span v-if="isRunningDiagnostics">⏳ Ejecutando...</span>
        <span v-else>🚀 Ejecutar Diagnósticos</span>
      </button>
      
      <button 
        v-if="diagnosticsResults"
        @click="clearResults" 
        class="btn btn-secondary"
      >
        🗑️ Limpiar Resultados
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="isRunningDiagnostics" class="diagnostics-loading">
      <div class="spinner"></div>
      <p>Ejecutando diagnósticos del sistema...</p>
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: loadingProgress + '%' }"></div>
      </div>
    </div>

    <!-- Results Display -->
    <div v-if="diagnosticsResults && !isRunningDiagnostics" class="diagnostics-results">
      <div class="results-header">
        <h4>📊 Resultados de Diagnósticos</h4>
        <div class="result-meta">
          <span class="timestamp">{{ formatTimestamp(diagnosticsResults.timestamp) }}</span>
          <span class="duration">Duración: {{ diagnosticsResults.duration }}ms</span>
          <span 
            class="health-score" 
            :class="getHealthScoreClass(diagnosticsResults.health_score)"
          >
            Score: {{ diagnosticsResults.health_score?.toFixed(1) || 'N/A' }}%
          </span>
        </div>
      </div>

      <!-- System Health Summary -->
      <div v-if="diagnosticsResults.system_diagnostics" class="health-summary">
        <h5>🏥 Estado General del Sistema</h5>
        <div class="health-grid">
          <div 
            v-for="(status, component) in diagnosticsResults.system_diagnostics" 
            :key="component"
            class="health-item"
            :class="{ 'healthy': status, 'error': !status }"
          >
            <span class="status-indicator" :class="status ? 'status-healthy' : 'status-error'"></span>
            <span class="component-name">{{ formatComponentName(component) }}</span>
            <span class="status-text">{{ status ? 'OK' : 'ERROR' }}</span>
          </div>
        </div>
      </div>

      <!-- Detailed Information -->
      <div class="diagnostics-details">
        <!-- Database Info -->
        <div v-if="diagnosticsResults.database_info" class="detail-section">
          <h5>🗄️ Base de Datos</h5>
          <div class="detail-grid">
            <div class="detail-item">
              <strong>Tipo:</strong> {{ diagnosticsResults.database_info.type || 'Unknown' }}
            </div>
            <div class="detail-item">
              <strong>Conexiones:</strong> {{ diagnosticsResults.database_info.connections || 'N/A' }}
            </div>
            <div class="detail-item">
              <strong>Estado:</strong>
              <span :class="getDatabaseStatusClass(diagnosticsResults.database_info.status)">
                {{ diagnosticsResults.database_info.status || 'Unknown' }}
              </span>
            </div>
          </div>
        </div>

        <!-- OpenAI Service -->
        <div v-if="diagnosticsResults.openai_model" class="detail-section">
          <h5>🤖 Servicio OpenAI</h5>
          <div class="detail-grid">
            <div class="detail-item">
              <strong>Modelo:</strong> {{ diagnosticsResults.openai_model }}
            </div>
            <div class="detail-item">
              <strong>Estado:</strong>
              <span class="status-healthy">Disponible</span>
            </div>
          </div>
        </div>

        <!-- Multi-Agent Factory -->
        <div v-if="diagnosticsResults.orchestrator_available !== undefined" class="detail-section">
          <h5>🎭 Multi-Agent Factory</h5>
          <div class="detail-grid">
            <div class="detail-item">
              <strong>Orchestrator:</strong>
              <span :class="diagnosticsResults.orchestrator_available ? 'status-healthy' : 'status-error'">
                {{ diagnosticsResults.orchestrator_available ? 'Disponible' : 'No Disponible' }}
              </span>
            </div>
          </div>
        </div>

        <!-- Error Information -->
        <div v-if="hasErrors" class="detail-section error-section">
          <h5>❌ Errores Detectados</h5>
          <div class="error-list">
            <div v-if="diagnosticsResults.database_error" class="error-item">
              <strong>Database Error:</strong> {{ diagnosticsResults.database_error }}
            </div>
            <div v-if="diagnosticsResults.openai_error" class="error-item">
              <strong>OpenAI Error:</strong> {{ diagnosticsResults.openai_error }}
            </div>
            <div v-if="diagnosticsResults.factory_error" class="error-item">
              <strong>Factory Error:</strong> {{ diagnosticsResults.factory_error }}
            </div>
          </div>
        </div>
      </div>

      <!-- Raw JSON View (Optional) -->
      <details class="raw-json-section">
        <summary>🔍 Ver JSON Completo</summary>
        <pre class="json-container">{{ formatJSON(diagnosticsResults) }}</pre>
      </details>
    </div>

    <!-- Error State -->
    <div v-if="errorMessage" class="diagnostics-error">
      <h4>❌ Error en Diagnósticos</h4>
      <p>{{ errorMessage }}</p>
      <button @click="retryDiagnostics" class="btn btn-danger">
        🔄 Reintentar
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'

// ============================================================================
// ESTADO REACTIVO
// ============================================================================

const appStore = useAppStore()
const { apiRequest } = useApiRequest()
const { showNotification } = useNotifications()

const isRunningDiagnostics = ref(false)
const diagnosticsResults = ref(null)
const errorMessage = ref('')
const loadingProgress = ref(0)

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const hasErrors = computed(() => {
  if (!diagnosticsResults.value) return false
  return !!(
    diagnosticsResults.value.database_error ||
    diagnosticsResults.value.openai_error ||
    diagnosticsResults.value.factory_error
  )
})

// ============================================================================
// FUNCIONES PRINCIPALES
// ============================================================================

/**
 * Ejecuta diagnósticos del sistema - MIGRADO: runSystemDiagnostics() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const runSystemDiagnostics = async () => {
  isRunningDiagnostics.value = true
  diagnosticsResults.value = null
  errorMessage.value = ''
  loadingProgress.value = 0
  
  try {
    appStore.addToLog('Starting system diagnostics', 'info')
    showNotification('Ejecutando diagnósticos del sistema...', 'info')
    
    // Simular progreso de carga
    const progressInterval = setInterval(() => {
      if (loadingProgress.value < 90) {
        loadingProgress.value += Math.random() * 20
      }
    }, 200)
    
    const startTime = Date.now()
    
    // Llamada a la API - PRESERVAR ENDPOINT EXACTO
    const response = await apiRequest('/api/admin/diagnostics', {
      method: 'POST',
      headers: {
        'X-API-Key': appStore.adminApiKey
      }
    })
    
    clearInterval(progressInterval)
    loadingProgress.value = 100
    
    const endTime = Date.now()
    
    diagnosticsResults.value = {
      ...response,
      timestamp: startTime,
      duration: endTime - startTime
    }
    
    appStore.addToLog('System diagnostics completed successfully', 'info')
    showNotification('Diagnósticos completados exitosamente', 'success')
    
  } catch (error) {
    appStore.addToLog(`System diagnostics failed: ${error.message}`, 'error')
    errorMessage.value = error.message
    showNotification(`Error en diagnósticos: ${error.message}`, 'error')
  } finally {
    isRunningDiagnostics.value = false
    loadingProgress.value = 0
  }
}

/**
 * Reintentar diagnósticos en caso de error
 */
const retryDiagnostics = () => {
  errorMessage.value = ''
  runSystemDiagnostics()
}

/**
 * Limpiar resultados de diagnósticos
 */
const clearResults = () => {
  diagnosticsResults.value = null
  errorMessage.value = ''
  appStore.addToLog('Diagnostics results cleared', 'info')
  showNotification('Resultados de diagnósticos limpiados', 'info')
}

// ============================================================================
// FUNCIONES DE UTILIDAD
// ============================================================================

const formatTimestamp = (timestamp) => {
  return new Date(timestamp).toLocaleString()
}

const formatComponentName = (component) => {
  return component
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase())
}

const getHealthScoreClass = (score) => {
  if (!score) return 'unknown'
  if (score >= 90) return 'excellent'
  if (score >= 70) return 'good'
  if (score >= 50) return 'warning'
  return 'critical'
}

const getDatabaseStatusClass = (status) => {
  if (!status) return 'unknown'
  if (status === 'connected') return 'status-healthy'
  return 'status-error'
}

const formatJSON = (obj) => {
  return JSON.stringify(obj, null, 2)
}

// ============================================================================
// LIFECYCLE HOOKS
// ============================================================================

onMounted(() => {
  appStore.addToLog('SystemDiagnostics component mounted', 'info')
  
  // EXPONER FUNCIÓN GLOBAL PARA COMPATIBILIDAD
  window.runSystemDiagnostics = runSystemDiagnostics
})

onUnmounted(() => {
  // Limpiar función global
  if (typeof window !== 'undefined') {
    delete window.runSystemDiagnostics
  }
  
  appStore.addToLog('SystemDiagnostics component unmounted', 'info')
})
</script>

<style scoped>
.system-diagnostics {
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  padding: 24px;
  border: 1px solid var(--border-color);
}

.diagnostics-header {
  margin-bottom: 24px;
  text-align: center;
}

.diagnostics-header h3 {
  color: var(--text-primary);
  margin-bottom: 8px;
  font-size: 1.5rem;
}

.diagnostics-header p {
  color: var(--text-secondary);
  font-size: 0.95rem;
}

.diagnostics-controls {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  justify-content: center;
}

.diagnostics-loading {
  text-align: center;
  padding: 40px 20px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid var(--border-light);
  border-left: 4px solid var(--primary-color);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.progress-bar {
  width: 100%;
  max-width: 300px;
  height: 8px;
  background: var(--border-light);
  border-radius: 4px;
  margin: 16px auto;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--primary-color);
  transition: width 0.3s ease;
}

.diagnostics-results {
  margin-top: 24px;
}

.results-header {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-light);
}

.results-header h4 {
  color: var(--text-primary);
  margin-bottom: 12px;
}

.result-meta {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.health-score {
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 4px;
}

.health-score.excellent { background: #d4edda; color: #155724; }
.health-score.good { background: #d1ecf1; color: #0c5460; }
.health-score.warning { background: #fff3cd; color: #856404; }
.health-score.critical { background: #f8d7da; color: #721c24; }

.health-summary {
  margin-bottom: 24px;
  padding: 20px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
}

.health-summary h5 {
  color: var(--text-primary);
  margin-bottom: 16px;
  font-size: 1.1rem;
}

.health-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.health-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-light);
  background: var(--bg-primary);
}

.health-item.healthy {
  border-color: var(--success-color);
  background: var(--success-bg);
}

.health-item.error {
  border-color: var(--error-color);
  background: var(--error-bg);
}

.status-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-healthy { background: var(--success-color); }
.status-error { background: var(--error-color); }

.component-name {
  flex: 1;
  font-size: 0.9rem;
  color: var(--text-primary);
}

.status-text {
  font-size: 0.8rem;
  font-weight: 600;
}

.diagnostics-details {
  margin-top: 24px;
}

.detail-section {
  margin-bottom: 24px;
  padding: 20px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-light);
}

.detail-section h5 {
  color: var(--text-primary);
  margin-bottom: 16px;
  font-size: 1.1rem;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.detail-item {
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.detail-item strong {
  color: var(--text-primary);
}

.error-section {
  border-color: var(--error-color);
  background: var(--error-bg);
}

.error-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.error-item {
  font-size: 0.9rem;
  color: var(--error-color);
  padding: 8px;
  background: var(--bg-primary);
  border-radius: var(--radius-sm);
}

.raw-json-section {
  margin-top: 24px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
}

.raw-json-section summary {
  padding: 12px 16px;
  background: var(--bg-secondary);
  cursor: pointer;
  font-weight: 500;
  color: var(--text-primary);
}

.json-container {
  padding: 16px;
  background: var(--bg-code);
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 0.8rem;
  color: var(--text-code);
  overflow-x: auto;
  max-height: 400px;
  overflow-y: auto;
}

.diagnostics-error {
  text-align: center;
  padding: 40px 20px;
  background: var(--error-bg);
  border: 1px solid var(--error-color);
  border-radius: var(--radius-md);
}

.diagnostics-error h4 {
  color: var(--error-color);
  margin-bottom: 12px;
}

.diagnostics-error p {
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-hover);
}

.btn-secondary {
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover {
  background: var(--bg-hover);
}

.btn-danger {
  background: var(--error-color);
  color: white;
}

.btn-danger:hover {
  background: var(--error-hover);
}
</style>
