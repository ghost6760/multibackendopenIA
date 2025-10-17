<template>
  <div class="workflow-executor">
    <!-- Header -->
    <div class="executor-header">
      <h3>▶️ Ejecutar Workflow</h3>
      <button 
        v-if="!isExecuting"
        @click="$emit('close')"
        class="btn-close"
      >
        ✕
      </button>
    </div>
    
    <!-- Workflow Info -->
    <div v-if="workflow" class="workflow-info">
      <div class="info-row">
        <span class="info-icon">{{ getWorkflowIcon(workflow) }}</span>
        <div class="info-details">
          <h4>{{ workflow.name }}</h4>
          <p v-if="workflow.description">{{ workflow.description }}</p>
        </div>
      </div>
      
      <div class="info-stats">
        <span class="stat">🔢 {{ workflow.total_nodes || 0 }} nodos</span>
        <span class="stat">🔗 {{ workflow.total_edges || 0 }} conexiones</span>
      </div>
    </div>
    
    <!-- Execution Form -->
    <div class="execution-form">
      <!-- Context Configuration -->
      <div class="form-section">
        <h4>⚙️ Configuración de Ejecución</h4>
        
        <!-- User ID -->
        <div class="form-group">
          <label for="userId">
            Usuario ID
            <span class="label-hint">(opcional)</span>
          </label>
          <input
            id="userId"
            v-model="executionContext.user_id"
            type="text"
            placeholder="Ej: user_123"
            :disabled="isExecuting"
          >
        </div>
        
        <!-- User Message -->
        <div class="form-group">
          <label for="userMessage">
            Mensaje del Usuario
            <span class="label-hint">(opcional)</span>
          </label>
          <textarea
            id="userMessage"
            v-model="executionContext.user_message"
            rows="3"
            placeholder="Ej: Quiero información sobre tratamientos de botox"
            :disabled="isExecuting"
          ></textarea>
        </div>
        
        <!-- Custom Parameters -->
        <div class="form-group">
          <label>
            Parámetros Adicionales
            <span class="label-hint">(JSON opcional)</span>
          </label>
          <textarea
            v-model="customParamsJson"
            rows="4"
            placeholder='{"key": "value"}'
            :disabled="isExecuting"
            @blur="validateJsonParams"
          ></textarea>
          <span v-if="jsonParamsError" class="error-message">
            ❌ {{ jsonParamsError }}
          </span>
        </div>
      </div>
      
      <!-- Quick Presets -->
      <div class="form-section">
        <h4>⚡ Presets Rápidos</h4>
        <div class="presets-grid">
          <button
            v-for="preset in presets"
            :key="preset.id"
            @click="applyPreset(preset)"
            :disabled="isExecuting"
            class="preset-btn"
          >
            <span class="preset-icon">{{ preset.icon }}</span>
            <span class="preset-name">{{ preset.name }}</span>
          </button>
        </div>
      </div>
    </div>
    
    <!-- Execution Status -->
    <div v-if="isExecuting || executionResult" class="execution-status">
      <!-- Loading -->
      <div v-if="isExecuting" class="status-loading">
        <div class="loading-spinner">⏳</div>
        <p>Ejecutando workflow...</p>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: `${executionProgress}%` }"></div>
        </div>
      </div>
      
      <!-- Result -->
      <div v-else-if="executionResult" class="status-result">
        <div 
          class="result-header" 
          :class="{
            'result-success': executionResult.status === 'success',
            'result-error': executionResult.status === 'error',
            'result-warning': executionResult.status === 'warning'
          }"
        >
          <span class="result-icon">
            {{ getStatusIcon(executionResult.status) }}
          </span>
          <span class="result-title">
            {{ getStatusTitle(executionResult.status) }}
          </span>
        </div>
        
        <div class="result-details">
          <!-- Execution Info -->
          <div class="detail-row">
            <span class="detail-label">🆔 Ejecución ID:</span>
            <span class="detail-value">{{ executionResult.execution_id || 'N/A' }}</span>
          </div>
          
          <div class="detail-row">
            <span class="detail-label">⏱️ Duración:</span>
            <span class="detail-value">{{ formatDuration(executionResult.duration) }}</span>
          </div>
          
          <div class="detail-row">
            <span class="detail-label">📊 Nodos ejecutados:</span>
            <span class="detail-value">{{ executionResult.nodes_executed || 0 }}</span>
          </div>
          
          <!-- Output -->
          <div v-if="executionResult.output" class="result-output">
            <h5>📋 Resultado:</h5>
            <pre>{{ formatOutput(executionResult.output) }}</pre>
          </div>
          
          <!-- Error -->
          <div v-if="executionResult.error" class="result-error">
            <h5>❌ Error:</h5>
            <pre>{{ executionResult.error }}</pre>
          </div>
          
          <!-- Logs -->
          <div v-if="executionResult.logs && executionResult.logs.length > 0" class="result-logs">
            <h5>📝 Logs:</h5>
            <div class="logs-list">
              <div 
                v-for="(log, index) in executionResult.logs" 
                :key="index"
                class="log-entry"
                :class="`log-${log.level}`"
              >
                <span class="log-time">{{ formatLogTime(log.timestamp) }}</span>
                <span class="log-message">{{ log.message }}</span>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Actions -->
        <div class="result-actions">
          <button @click="resetExecution" class="btn btn-secondary">
            🔄 Nueva Ejecución
          </button>
          <button @click="exportResult" class="btn btn-outline">
            📥 Exportar Resultado
          </button>
        </div>
      </div>
    </div>
    
    <!-- Footer Actions -->
    <div class="executor-footer">
      <button 
        @click="$emit('close')"
        :disabled="isExecuting"
        class="btn btn-secondary"
      >
        Cancelar
      </button>
      
      <button 
        @click="handleExecute"
        :disabled="!canExecute"
        class="btn btn-primary"
      >
        <span v-if="isExecuting">⏳ Ejecutando...</span>
        <span v-else>▶️ Ejecutar Workflow</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { useWorkflows } from '@/composables/useWorkflows'
import { useNotifications } from '@/composables/useNotifications'

// ============================================================================
// PROPS & EMITS
// ============================================================================

const props = defineProps({
  workflow: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['close', 'executed'])

// ============================================================================
// STORES & COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const { showNotification } = useNotifications()
const { executeWorkflow, isExecuting } = useWorkflows()

// ============================================================================
// ESTADO LOCAL
// ============================================================================

const executionContext = ref({
  user_id: '',
  user_message: '',
  executed_from: 'workflow_executor'
})

const customParamsJson = ref('')
const jsonParamsError = ref(null)
const executionResult = ref(null)
const executionProgress = ref(0)

// Presets rápidos
const presets = [
  {
    id: 'test',
    name: 'Test',
    icon: '🧪',
    context: {
      user_id: 'test_user',
      user_message: 'Test de ejecución del workflow'
    }
  },
  {
    id: 'botox',
    name: 'Consulta Botox',
    icon: '💉',
    context: {
      user_id: 'user_123',
      user_message: 'Quiero información sobre tratamientos de botox'
    }
  },
  {
    id: 'schedule',
    name: 'Agendar Cita',
    icon: '📅',
    context: {
      user_id: 'user_456',
      user_message: 'Necesito agendar una cita para la próxima semana'
    }
  },
  {
    id: 'emergency',
    name: 'Emergencia',
    icon: '🚨',
    context: {
      user_id: 'user_789',
      user_message: 'Tengo una emergencia médica'
    }
  }
]

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const canExecute = computed(() => {
  return !isExecuting.value && 
         !jsonParamsError.value &&
         props.workflow &&
         appStore.hasCompanySelected
})

// ============================================================================
// MÉTODOS PRINCIPALES
// ============================================================================

const handleExecute = async () => {
  if (!canExecute.value) return
  
  // Construir contexto completo
  const context = {
    ...executionContext.value
  }
  
  // Agregar parámetros custom si hay
  if (customParamsJson.value.trim()) {
    try {
      const customParams = JSON.parse(customParamsJson.value)
      Object.assign(context, customParams)
    } catch (err) {
      showNotification('❌ Parámetros JSON inválidos', 'error')
      return
    }
  }
  
  // Simular progreso
  executionProgress.value = 0
  const progressInterval = setInterval(() => {
    if (executionProgress.value < 90) {
      executionProgress.value += Math.random() * 20
    }
  }, 300)
  
  try {
    const result = await executeWorkflow(
      props.workflow.workflow_id || props.workflow.id,
      context
    )
    
    clearInterval(progressInterval)
    executionProgress.value = 100
    
    executionResult.value = result
    
    emit('executed', result)
    
  } catch (error) {
    clearInterval(progressInterval)
    executionProgress.value = 0
    
    executionResult.value = {
      status: 'error',
      error: error.message,
      execution_id: null,
      duration: 0
    }
  }
}

const resetExecution = () => {
  executionResult.value = null
  executionProgress.value = 0
}

const applyPreset = (preset) => {
  executionContext.value = { ...preset.context, executed_from: 'workflow_executor' }
  customParamsJson.value = ''
  jsonParamsError.value = null
  
  showNotification(`⚡ Preset "${preset.name}" aplicado`, 'info', 2000)
}

const validateJsonParams = () => {
  jsonParamsError.value = null
  
  if (!customParamsJson.value.trim()) return
  
  try {
    JSON.parse(customParamsJson.value)
  } catch (err) {
    jsonParamsError.value = 'JSON inválido: ' + err.message
  }
}

const exportResult = () => {
  if (!executionResult.value) return
  
  const exportData = {
    workflow: {
      id: props.workflow.workflow_id || props.workflow.id,
      name: props.workflow.name
    },
    execution: executionResult.value,
    context: executionContext.value,
    exported_at: new Date().toISOString()
  }
  
  const blob = new Blob([JSON.stringify(exportData, null, 2)], {
    type: 'application/json'
  })
  const url = URL.createObjectURL(blob)
  
  const link = document.createElement('a')
  link.href = url
  link.download = `execution_${executionResult.value.execution_id}_${Date.now()}.json`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  
  URL.revokeObjectURL(url)
  
  showNotification('✅ Resultado exportado', 'success')
}

// ============================================================================
// MÉTODOS DE UTILIDAD
// ============================================================================

const getWorkflowIcon = (workflow) => {
  if (!workflow) return '⚙️'
  
  const name = workflow.name?.toLowerCase() || ''
  if (name.includes('bot')) return '💉'
  if (name.includes('schedule')) return '📅'
  if (name.includes('emergency')) return '🚨'
  if (name.includes('sales')) return '💰'
  
  return '⚙️'
}

const getStatusIcon = (status) => {
  const icons = {
    'success': '✅',
    'error': '❌',
    'warning': '⚠️',
    'pending': '⏳'
  }
  return icons[status] || '❓'
}

const getStatusTitle = (status) => {
  const titles = {
    'success': 'Ejecución Exitosa',
    'error': 'Error en la Ejecución',
    'warning': 'Completado con Advertencias',
    'pending': 'Pendiente'
  }
  return titles[status] || 'Estado Desconocido'
}

const formatDuration = (duration) => {
  if (!duration) return 'N/A'
  
  if (duration < 1000) {
    return `${duration}ms`
  }
  
  const seconds = Math.floor(duration / 1000)
  const ms = duration % 1000
  
  return `${seconds}.${ms}s`
}

const formatOutput = (output) => {
  if (typeof output === 'string') return output
  return JSON.stringify(output, null, 2)
}

const formatLogTime = (timestamp) => {
  if (!timestamp) return ''
  
  try {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('es-ES')
  } catch {
    return timestamp
  }
}

// ============================================================================
// WATCHERS
// ============================================================================

watch(() => props.workflow, () => {
  resetExecution()
  executionContext.value = {
    user_id: '',
    user_message: '',
    executed_from: 'workflow_executor'
  }
  customParamsJson.value = ''
})
</script>

<style scoped>
.workflow-executor {
  display: flex;
  flex-direction: column;
  gap: 20px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 20px;
  max-height: 80vh;
  overflow-y: auto;
}

/* Header */
.executor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 15px;
  border-bottom: 1px solid var(--border-color);
}

.executor-header h3 {
  margin: 0;
  color: var(--text-primary);
}

.btn-close {
  background: none;
  border: none;
  font-size: 1.5em;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.btn-close:hover {
  background: var(--danger-color);
  color: white;
}

/* Workflow Info */
.workflow-info {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 15px;
}

.info-row {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 10px;
}

.info-icon {
  font-size: 2em;
  flex-shrink: 0;
}

.info-details h4 {
  margin: 0 0 4px 0;
  color: var(--text-primary);
}

.info-details p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.9em;
}

.info-stats {
  display: flex;
  gap: 15px;
  font-size: 0.85em;
  color: var(--text-muted);
}

/* Form */
.execution-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-section {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 15px;
}

.form-section h4 {
  margin: 0 0 15px 0;
  color: var(--text-primary);
  font-size: 1em;
}

.form-group {
  margin-bottom: 15px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-weight: 500;
  color: var(--text-primary);
}

.label-hint {
  font-size: 0.85em;
  color: var(--text-muted);
  font-weight: normal;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: inherit;
  font-size: 14px;
  transition: border-color 0.2s ease;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.form-group input:disabled,
.form-group textarea:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-message {
  display: block;
  margin-top: 6px;
  font-size: 0.85em;
  color: var(--danger-color);
}

/* Presets */
.presets-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
}

.preset-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.preset-btn:hover:not(:disabled) {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
  transform: translateY(-2px);
}

.preset-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.preset-icon {
  font-size: 1.5em;
}

.preset-name {
  font-size: 0.85em;
  font-weight: 500;
}

/* Execution Status */
.execution-status {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 20px;
}

.status-loading {
  text-align: center;
  padding: 20px;
}

.loading-spinner {
  font-size: 2em;
  margin-bottom: 10px;
  animation: spin 1s linear infinite;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: var(--bg-secondary);
  border-radius: 4px;
  overflow: hidden;
  margin-top: 15px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-color), var(--success-color));
  transition: width 0.3s ease;
}

/* Result */
.status-result {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-radius: 6px;
  font-weight: 600;
}

.result-header.result-success {
  background: rgba(34, 197, 94, 0.1);
  color: var(--success-color);
}

.result-header.result-error {
  background: rgba(239, 68, 68, 0.1);
  color: var(--danger-color);
}

.result-header.result-warning {
  background: rgba(245, 158, 11, 0.1);
  color: var(--warning-color);
}

.result-icon {
  font-size: 1.5em;
}

.result-details {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
  font-size: 0.9em;
}

.detail-label {
  color: var(--text-secondary);
}

.detail-value {
  color: var(--text-primary);
  font-weight: 600;
  font-family: monospace;
}

.result-output,
.result-error,
.result-logs {
  margin-top: 10px;
}

.result-output h5,
.result-error h5,
.result-logs h5 {
  margin: 0 0 8px 0;
  color: var(--text-primary);
  font-size: 0.9em;
}

.result-output pre,
.result-error pre {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 12px;
  overflow-x: auto;
  font-size: 0.85em;
  line-height: 1.4;
  margin: 0;
}

.result-error pre {
  color: var(--danger-color);
}

.logs-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 200px;
  overflow-y: auto;
}

.log-entry {
  display: flex;
  gap: 10px;
  padding: 6px 10px;
  background: var(--bg-primary);
  border-radius: 4px;
  font-size: 0.85em;
}

.log-time {
  color: var(--text-muted);
  font-family: monospace;
  flex-shrink: 0;
}

.log-message {
  color: var(--text-secondary);
  flex: 1;
}

.log-entry.log-error {
  background: rgba(239, 68, 68, 0.05);
  border-left: 3px solid var(--danger-color);
}

.log-entry.log-warning {
  background: rgba(245, 158, 11, 0.05);
  border-left: 3px solid var(--warning-color);
}

.result-actions {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}

/* Footer */
.executor-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 15px;
  border-top: 1px solid var(--border-color);
}

/* Buttons */
.btn {
  padding: 10px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-color-dark);
}

.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.btn-outline {
  background: transparent;
  color: var(--primary-color);
  border: 1px solid var(--primary-color);
}

.btn-outline:hover:not(:disabled) {
  background: var(--primary-color);
  color: white;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Responsive */
@media (max-width: 768px) {
  .presets-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .detail-row {
    flex-direction: column;
    gap: 4px;
  }
  
  .executor-footer {
    flex-direction: column-reverse;
  }
  
  .result-actions {
    flex-direction: column;
  }
}
</style>
