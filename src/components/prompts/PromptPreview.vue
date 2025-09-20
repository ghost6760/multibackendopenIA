# PromptPreview.vue
<template>
  <!-- Modal Overlay -->
  <Teleport to="body">
    <div 
      v-if="visible" 
      class="modal-overlay"
      @click="handleOverlayClick"
    >
      <div 
        class="modal-content" 
        :class="{ 'error-modal': previewData?.error }"
        @click.stop
      >
        <!-- Modal Header -->
        <div class="modal-header" :class="{ 'error-header': previewData?.error }">
          <h3>
            <span v-if="previewData?.error">❌ Error en Vista Previa</span>
            <span v-else>🔍 Vista Previa - {{ escapeHTML(displayAgentName) }}</span>
          </h3>
          <button @click="closeModal" class="modal-close">&times;</button>
        </div>

        <!-- Loading Content -->
        <div v-if="isLoading" class="preview-content">
          <div class="preview-loading">
            <div class="loading-spinner"></div>
            <p>Generando vista previa...</p>
          </div>
        </div>

        <!-- Error Content -->
        <div v-else-if="previewData?.error" class="preview-content">
          <div class="preview-section">
            <h4>📋 Información del Error</h4>
            <p><strong>Agente:</strong> {{ escapeHTML(displayAgentName) }}</p>
            <p><strong>Empresa:</strong> {{ escapeHTML(currentCompanyId) }}</p>
            <p><strong>Mensaje de prueba:</strong></p>
            <div class="test-message-box">{{ escapeHTML(currentTestMessage) }}</div>
          </div>
          
          <div class="preview-section">
            <h4>🚨 Detalles del Error</h4>
            <div class="error-details">
              <p><strong>Error:</strong> {{ escapeHTML(previewData.error) }}</p>
              <p><strong>Tiempo:</strong> {{ formatDateTime(new Date()) }}</p>
            </div>
          </div>

          <!-- Fallback preview if available -->
          <div v-if="previewData.fallback" class="preview-section">
            <h4>📝 Prompt Actual (sin procesamiento)</h4>
            <div class="prompt-preview-content">
              {{ escapeHTML(previewData.prompt_content || currentPromptContent) }}
            </div>
          </div>
        </div>

        <!-- Success Content -->
        <div v-else-if="previewData && !previewData.error" class="preview-content">
          <!-- Información del test -->
          <div class="preview-section">
            <h4>📋 Información del Test</h4>
            <div class="info-grid">
              <div class="info-item">
                <strong>Agente:</strong> 
                {{ escapeHTML(previewData.agent_name || displayAgentName) }}
              </div>
              <div class="info-item" v-if="previewData.agent_used">
                <strong>Agente usado:</strong> 
                {{ escapeHTML(previewData.agent_used) }}
              </div>
              <div class="info-item">
                <strong>Empresa:</strong> 
                {{ escapeHTML(previewData.company_id || currentCompanyId) }}
              </div>
              <div class="info-item full-width">
                <strong>Mensaje de prueba:</strong>
                <div class="test-message-box">{{ escapeHTML(previewData.test_message || currentTestMessage) }}</div>
              </div>
            </div>
          </div>

          <!-- Respuesta del asistente -->
          <div v-if="previewData.preview" class="preview-section">
            <h4>🤖 Respuesta del Asistente</h4>
            <div class="assistant-response">
              <div class="response-content">
                {{ previewData.preview }}
              </div>
            </div>
          </div>

          <!-- Debug info si está disponible -->
          <div v-if="previewData.debug_info" class="preview-section technical-info">
            <h4>🔧 Información Técnica</h4>
            <div class="debug-grid">
              <div v-if="previewData.debug_info.response_length" class="debug-item">
                <strong>Longitud:</strong> {{ previewData.debug_info.response_length }} caracteres
              </div>
              <div v-if="previewData.debug_info.agent_key" class="debug-item">
                <strong>Agent Key:</strong> {{ previewData.debug_info.agent_key }}
              </div>
              <div v-if="previewData.debug_info.prompt_source || previewData.prompt_source" class="debug-item">
                <strong>Fuente:</strong> {{ previewData.debug_info.prompt_source || previewData.prompt_source }}
              </div>
              <div v-if="previewData.debug_info.processing_time" class="debug-item">
                <strong>Tiempo:</strong> {{ previewData.debug_info.processing_time }}ms
              </div>
            </div>
          </div>

          <!-- Prompt preview si está disponible -->
          <div v-if="previewData.prompt_preview" class="preview-section technical-info">
            <h4>📝 Preview del Prompt</h4>
            <div class="prompt-preview-content">
              {{ previewData.prompt_preview }}
            </div>
          </div>

          <!-- Información adicional de debug -->
          <div v-if="previewData.model_info" class="preview-section technical-info">
            <h4>🎯 Información del Modelo</h4>
            <div class="model-info">
              <div v-if="previewData.model_info.model" class="model-item">
                <strong>Modelo:</strong> {{ previewData.model_info.model }}
              </div>
              <div v-if="previewData.model_info.temperature" class="model-item">
                <strong>Temperatura:</strong> {{ previewData.model_info.temperature }}
              </div>
              <div v-if="previewData.model_info.max_tokens" class="model-item">
                <strong>Max Tokens:</strong> {{ previewData.model_info.max_tokens }}
              </div>
            </div>
          </div>

          <!-- Métricas de rendimiento -->
          <div v-if="previewData.metrics" class="preview-section technical-info">
            <h4>📊 Métricas</h4>
            <div class="metrics-grid">
              <div v-if="previewData.metrics.tokens_used" class="metric-item">
                <strong>Tokens usados:</strong> {{ previewData.metrics.tokens_used }}
              </div>
              <div v-if="previewData.metrics.cost" class="metric-item">
                <strong>Costo estimado:</strong> ${{ previewData.metrics.cost }}
              </div>
              <div v-if="previewData.metrics.response_time" class="metric-item">
                <strong>Tiempo de respuesta:</strong> {{ previewData.metrics.response_time }}ms
              </div>
            </div>
          </div>

          <!-- Current prompt section -->
          <div class="preview-section">
            <h4>📝 Prompt Actual</h4>
            <div class="prompt-preview-content">
              {{ currentPromptContent.substring(0, 500) }}{{ currentPromptContent.length > 500 ? '...' : '' }}
            </div>
          </div>
        </div>

        <!-- Modal Footer -->
        <div class="modal-footer">
          <button @click="closeModal" class="btn-primary">Cerrar</button>
          <button 
            v-if="!previewData?.error && !isLoading && previewData?.preview"
            @click="copyResponse"
            class="btn-secondary"
            title="Copiar respuesta al portapapeles"
          >
            📋 Copiar Respuesta
          </button>
          <button 
            v-if="!previewData?.error && !isLoading"
            @click="exportPreview"
            class="btn-info"
            title="Exportar preview completo"
          >
            💾 Exportar
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

// ============================================================================
// PROPS Y EMITS - COMPATIBLE CON USEPROMPTS.JS
// ============================================================================

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  agentName: {
    type: String,
    default: ''
  },
  promptContent: {
    type: String,
    default: ''
  },
  testMessage: {
    type: String,
    default: ''
  },
  previewResponse: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  },
  companyId: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['close', 'preview-complete'])

// ============================================================================
// ESTADO REACTIVO LOCAL
// ============================================================================

const previewData = ref(null)

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const displayAgentName = computed(() => {
  // Convertir nombres de agente a formato legible
  const agentDisplayNames = {
    'emergency_agent': 'Emergency Agent',
    'router_agent': 'Router Agent', 
    'sales_agent': 'Sales Agent',
    'schedule_agent': 'Schedule Agent',
    'support_agent': 'Support Agent'
  }
  
  return agentDisplayNames[props.agentName] || props.agentName
})

const currentCompanyId = computed(() => props.companyId)
const currentTestMessage = computed(() => props.testMessage)
const currentPromptContent = computed(() => props.promptContent)
const isLoading = computed(() => props.loading)

// ============================================================================
// WATCHERS
// ============================================================================

watch(() => props.previewResponse, (newResponse) => {
  if (newResponse) {
    previewData.value = newResponse
  }
}, { immediate: true, deep: true })

watch(() => props.visible, (newVisible) => {
  if (!newVisible) {
    // Limpiar datos cuando se cierra
    previewData.value = null
  }
})

// ============================================================================
// FUNCIONES PRINCIPALES
// ============================================================================

/**
 * Cerrar modal
 */
const closeModal = () => {
  emit('close')
}

const handleOverlayClick = (event) => {
  if (event.target === event.currentTarget) {
    closeModal()
  }
}

// ============================================================================
// FUNCIONES DE UTILIDADES
// ============================================================================

const escapeHTML = (text) => {
  if (!text) return ''
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

const formatDateTime = (date) => {
  if (!date) return 'N/A'
  try {
    return new Date(date).toLocaleString()
  } catch (error) {
    return 'Fecha inválida'
  }
}

const copyResponse = async () => {
  if (!previewData.value?.preview) return
  
  try {
    await navigator.clipboard.writeText(previewData.value.preview)
    // Mostrar feedback visual temporal
    const button = event.target
    const originalText = button.textContent
    button.textContent = '✅ Copiado'
    setTimeout(() => {
      button.textContent = originalText
    }, 2000)
  } catch (error) {
    // Fallback para navegadores que no soportan clipboard API
    const textArea = document.createElement('textarea')
    textArea.value = previewData.value.preview
    document.body.appendChild(textArea)
    textArea.select()
    document.execCommand('copy')
    document.body.removeChild(textArea)
    
    // Feedback visual
    const button = event.target
    const originalText = button.textContent
    button.textContent = '✅ Copiado'
    setTimeout(() => {
      button.textContent = originalText
    }, 2000)
  }
}

const exportPreview = () => {
  if (!previewData.value) return
  
  try {
    const exportData = {
      timestamp: new Date().toISOString(),
      agent: props.agentName,
      agent_display_name: displayAgentName.value,
      company: currentCompanyId.value,
      test_message: currentTestMessage.value,
      prompt_content: currentPromptContent.value,
      response: previewData.value.preview,
      debug_info: previewData.value.debug_info,
      model_info: previewData.value.model_info,
      metrics: previewData.value.metrics,
      full_response: previewData.value
    }
    
    const dataStr = JSON.stringify(exportData, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    
    const a = document.createElement('a')
    a.href = URL.createObjectURL(dataBlob)
    a.download = `prompt_preview_${props.agentName}_${new Date().toISOString().slice(0, 10)}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    
    URL.revokeObjectURL(a.href)
    
    // Feedback visual
    const button = event.target
    const originalText = button.textContent
    button.textContent = '✅ Exportado'
    setTimeout(() => {
      button.textContent = originalText
    }, 2000)
    
  } catch (error) {
    console.error('Error exporting preview:', error)
  }
}
</script>

<style scoped>
/* ===== ESTILOS PARA PROMPT PREVIEW MODAL ===== */

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-content {
  background: white;
  border-radius: 8px;
  max-width: 800px;
  max-height: 80vh;
  width: 90%;
  overflow-y: auto;
  box-shadow: 0 4px 20px rgba(0,0,0,0.3);
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from { 
    opacity: 0;
    transform: translateY(-50px);
  }
  to { 
    opacity: 1;
    transform: translateY(0);
  }
}

.modal-content.error-modal {
  border: 2px solid #dc3545;
}

.modal-header {
  background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
  color: white;
  padding: 20px;
  border-radius: 8px 8px 0 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header.error-header {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
}

.modal-header h3 {
  margin: 0;
  font-size: 1.3em;
  font-weight: 600;
}

.modal-close {
  background: none;
  border: none;
  color: white;
  font-size: 24px;
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: background-color 0.2s ease;
}

.modal-close:hover {
  background-color: rgba(255, 255, 255, 0.2);
}

.preview-content {
  padding: 20px;
}

.preview-loading {
  text-align: center;
  padding: 40px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.preview-section {
  margin-bottom: 25px;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  padding: 15px;
  background: #f8f9fa;
}

.preview-section h4 {
  margin: 0 0 15px 0;
  color: #495057;
  font-size: 1.1em;
  font-weight: 600;
  border-bottom: 2px solid #007bff;
  padding-bottom: 8px;
}

.preview-section.technical-info {
  background: #f8f9fa;
  border-left: 4px solid #6c757d;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.info-item.full-width {
  grid-column: 1 / -1;
}

.test-message-box {
  background: white;
  border: 1px solid #ced4da;
  border-left: 4px solid #007bff;
  border-radius: 4px;
  padding: 12px;
  font-family: monospace;
  white-space: pre-wrap;
  word-wrap: break-word;
  margin-top: 5px;
}

.debug-grid,
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 10px;
}

.debug-item,
.metric-item,
.model-item {
  background: white;
  padding: 10px;
  border-radius: 4px;
  border: 1px solid #dee2e6;
}

.prompt-preview-content {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 15px;
  font-family: monospace;
  font-size: 0.9em;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 300px;
  overflow-y: auto;
}

.assistant-response {
  background: white;
  border: 1px solid #ced4da;
  border-radius: 6px;
  overflow: hidden;
}

.response-content {
  padding: 15px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 400px;
  overflow-y: auto;
}

.error-details {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-left: 4px solid #ef4444;
  padding: 15px;
  border-radius: 8px;
  color: #7f1d1d;
}

.model-info {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.modal-footer {
  padding: 20px;
  border-top: 1px solid #e9ecef;
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  background: #f8f9fa;
  border-radius: 0 0 8px 8px;
}

.modal-footer button {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.9em;
  transition: all 0.2s ease;
}

.btn-primary {
  background-color: #007bff;
  color: white;
}

.btn-primary:hover {
  background-color: #0056b3;
  transform: translateY(-1px);
}

.btn-secondary {
  background-color: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background-color: #545b62;
  transform: translateY(-1px);
}

.btn-info {
  background-color: #17a2b8;
  color: white;
}

.btn-info:hover {
  background-color: #117a8b;
  transform: translateY(-1px);
}

/* Responsive design */
@media (max-width: 768px) {
  .modal-content {
    width: 95%;
    max-height: 90vh;
    margin: 20px;
  }
  
  .modal-header {
    padding: 15px;
  }
  
  .modal-header h3 {
    font-size: 1.1em;
  }
  
  .preview-content {
    padding: 15px;
  }
  
  .info-grid {
    grid-template-columns: 1fr;
  }
  
  .debug-grid,
  .metrics-grid {
    grid-template-columns: 1fr;
  }
  
  .modal-footer {
    padding: 15px;
    flex-direction: column;
  }
  
  .modal-footer button {
    width: 100%;
  }
  
  .model-info {
    flex-direction: column;
  }
}

/* Scrollbar styling */
.modal-content::-webkit-scrollbar,
.response-content::-webkit-scrollbar,
.prompt-preview-content::-webkit-scrollbar {
  width: 6px;
}

.modal-content::-webkit-scrollbar-track,
.response-content::-webkit-scrollbar-track,
.prompt-preview-content::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.modal-content::-webkit-scrollbar-thumb,
.response-content::-webkit-scrollbar-thumb,
.prompt-preview-content::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.modal-content::-webkit-scrollbar-thumb:hover,
.response-content::-webkit-scrollbar-thumb:hover,
.prompt-preview-content::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>
