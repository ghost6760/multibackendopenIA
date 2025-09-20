# PromptsTab.vue
<template>
  <div class="prompts-tab" v-if="isActive">
    <!-- Header del Tab -->
    <div class="tab-header">
      <h2>🤖 Sistema de Prompts</h2>
      <p class="tab-description">
        Gestiona y personaliza los prompts de los agentes IA para {{ currentCompanyName }}
      </p>
    </div>

    <!-- Estado del Sistema - PASO 1: ACTIVADO -->
    <PromptsStatus 
      @status-loaded="handleStatusLoaded"
      @migration-complete="handleMigrationComplete"
    />

    <!-- Main Prompts Section -->
    <div class="prompts-main-section">
      
      <!-- Company Info Bar -->
      <div class="company-bar">
        <div class="company-info">
          <span class="company-label">📢 Empresa Activa:</span>
          <span class="company-name">{{ currentCompanyName || currentCompanyId || 'No seleccionada' }}</span>
        </div>
        <div class="actions-bar">
          <button @click="loadPrompts" class="btn-refresh" :disabled="isLoadingPrompts">
            <span v-if="isLoadingPrompts">⏳ Cargando...</span>
            <span v-else>🔄 Recargar Todos</span>
          </button>
          <button @click="repairAllPrompts" class="btn-repair-all" :disabled="isProcessing">
            🔧 Reparar Todos
          </button>
          <button @click="exportPrompts" class="btn-export">
            💾 Exportar
          </button>
        </div>
      </div>

      <!-- Error State -->
      <div v-if="error" class="error-section">
        <p>⚠️ {{ error }}</p>
      </div>

      <!-- Prompts Grid - Los 5 Agentes -->
      <div v-if="hasPrompts" class="prompts-grid">
        
        <!-- Emergency Agent -->
        <div class="agent-card" v-if="agents.emergency_agent">
          <div class="agent-header">
            <h3>🚨 Emergency Agent</h3>
            <span :class="['status-badge', agents.emergency_agent.is_custom ? 'custom' : 'default']">
              {{ agents.emergency_agent.is_custom ? '✅ Personalizado' : '🔵 Por defecto' }}
            </span>
          </div>
          
          <div class="agent-body">
            <textarea
              :id="`prompt-emergency_agent`"
              v-model="agents.emergency_agent.current_prompt"
              class="prompt-textarea"
              rows="8"
              placeholder="Prompt para Emergency Agent..."
              :disabled="isProcessing"
            ></textarea>
            
            <div class="prompt-info">
              <span v-if="agents.emergency_agent.last_modified" class="last-modified">
                📅 Modificado: {{ formatDate(agents.emergency_agent.last_modified) }}
              </span>
              <span class="char-count">
                {{ (agents.emergency_agent.current_prompt || '').length }} caracteres
              </span>
            </div>
          </div>
          
          <div class="agent-actions">
            <button 
              @click="updatePrompt('emergency_agent')"
              class="btn-update"
              :disabled="isProcessing || !agents.emergency_agent.current_prompt"
            >
              💾 Actualizar
            </button>
            <button 
              @click="resetPrompt('emergency_agent')"
              class="btn-reset"
              :disabled="isProcessing || !agents.emergency_agent.is_custom"
            >
              🔄 Resetear
            </button>
            <button 
              @click="previewPrompt('emergency_agent')"
              class="btn-preview"
              :disabled="isProcessing || !agents.emergency_agent.current_prompt"
            >
              👁️ Preview
            </button>
          </div>
        </div>

        <!-- Router Agent -->
        <div class="agent-card" v-if="agents.router_agent">
          <div class="agent-header">
            <h3>🚦 Router Agent</h3>
            <span :class="['status-badge', agents.router_agent.is_custom ? 'custom' : 'default']">
              {{ agents.router_agent.is_custom ? '✅ Personalizado' : '🔵 Por defecto' }}
            </span>
          </div>
          
          <div class="agent-body">
            <textarea
              :id="`prompt-router_agent`"
              v-model="agents.router_agent.current_prompt"
              class="prompt-textarea"
              rows="8"
              placeholder="Prompt para Router Agent..."
              :disabled="isProcessing"
            ></textarea>
            
            <div class="prompt-info">
              <span v-if="agents.router_agent.last_modified" class="last-modified">
                📅 Modificado: {{ formatDate(agents.router_agent.last_modified) }}
              </span>
              <span class="char-count">
                {{ (agents.router_agent.current_prompt || '').length }} caracteres
              </span>
            </div>
          </div>
          
          <div class="agent-actions">
            <button 
              @click="updatePrompt('router_agent')"
              class="btn-update"
              :disabled="isProcessing || !agents.router_agent.current_prompt"
            >
              💾 Actualizar
            </button>
            <button 
              @click="resetPrompt('router_agent')"
              class="btn-reset"
              :disabled="isProcessing || !agents.router_agent.is_custom"
            >
              🔄 Resetear
            </button>
            <button 
              @click="previewPrompt('router_agent')"
              class="btn-preview"
              :disabled="isProcessing || !agents.router_agent.current_prompt"
            >
              👁️ Preview
            </button>
          </div>
        </div>

        <!-- Sales Agent -->
        <div class="agent-card" v-if="agents.sales_agent">
          <div class="agent-header">
            <h3>💼 Sales Agent</h3>
            <span :class="['status-badge', agents.sales_agent.is_custom ? 'custom' : 'default']">
              {{ agents.sales_agent.is_custom ? '✅ Personalizado' : '🔵 Por defecto' }}
            </span>
          </div>
          
          <div class="agent-body">
            <textarea
              :id="`prompt-sales_agent`"
              v-model="agents.sales_agent.current_prompt"
              class="prompt-textarea"
              rows="8"
              placeholder="Prompt para Sales Agent..."
              :disabled="isProcessing"
            ></textarea>
            
            <div class="prompt-info">
              <span v-if="agents.sales_agent.last_modified" class="last-modified">
                📅 Modificado: {{ formatDate(agents.sales_agent.last_modified) }}
              </span>
              <span class="char-count">
                {{ (agents.sales_agent.current_prompt || '').length }} caracteres
              </span>
            </div>
          </div>
          
          <div class="agent-actions">
            <button 
              @click="updatePrompt('sales_agent')"
              class="btn-update"
              :disabled="isProcessing || !agents.sales_agent.current_prompt"
            >
              💾 Actualizar
            </button>
            <button 
              @click="resetPrompt('sales_agent')"
              class="btn-reset"
              :disabled="isProcessing || !agents.sales_agent.is_custom"
            >
              🔄 Resetear
            </button>
            <button 
              @click="previewPrompt('sales_agent')"
              class="btn-preview"
              :disabled="isProcessing || !agents.sales_agent.current_prompt"
            >
              👁️ Preview
            </button>
          </div>
        </div>

        <!-- Schedule Agent -->
        <div class="agent-card" v-if="agents.schedule_agent">
          <div class="agent-header">
            <h3>📅 Schedule Agent</h3>
            <span :class="['status-badge', agents.schedule_agent.is_custom ? 'custom' : 'default']">
              {{ agents.schedule_agent.is_custom ? '✅ Personalizado' : '🔵 Por defecto' }}
            </span>
          </div>
          
          <div class="agent-body">
            <textarea
              :id="`prompt-schedule_agent`"
              v-model="agents.schedule_agent.current_prompt"
              class="prompt-textarea"
              rows="8"
              placeholder="Prompt para Schedule Agent..."
              :disabled="isProcessing"
            ></textarea>
            
            <div class="prompt-info">
              <span v-if="agents.schedule_agent.last_modified" class="last-modified">
                📅 Modificado: {{ formatDate(agents.schedule_agent.last_modified) }}
              </span>
              <span class="char-count">
                {{ (agents.schedule_agent.current_prompt || '').length }} caracteres
              </span>
            </div>
          </div>
          
          <div class="agent-actions">
            <button 
              @click="updatePrompt('schedule_agent')"
              class="btn-update"
              :disabled="isProcessing || !agents.schedule_agent.current_prompt"
            >
              💾 Actualizar
            </button>
            <button 
              @click="resetPrompt('schedule_agent')"
              class="btn-reset"
              :disabled="isProcessing || !agents.schedule_agent.is_custom"
            >
              🔄 Resetear
            </button>
            <button 
              @click="previewPrompt('schedule_agent')"
              class="btn-preview"
              :disabled="isProcessing || !agents.schedule_agent.current_prompt"
            >
              👁️ Preview
            </button>
          </div>
        </div>

        <!-- Support Agent -->
        <div class="agent-card" v-if="agents.support_agent">
          <div class="agent-header">
            <h3>🎧 Support Agent</h3>
            <span :class="['status-badge', agents.support_agent.is_custom ? 'custom' : 'default']">
              {{ agents.support_agent.is_custom ? '✅ Personalizado' : '🔵 Por defecto' }}
            </span>
          </div>
          
          <div class="agent-body">
            <textarea
              :id="`prompt-support_agent`"
              v-model="agents.support_agent.current_prompt"
              class="prompt-textarea"
              rows="8"
              placeholder="Prompt para Support Agent..."
              :disabled="isProcessing"
            ></textarea>
            
            <div class="prompt-info">
              <span v-if="agents.support_agent.last_modified" class="last-modified">
                📅 Modificado: {{ formatDate(agents.support_agent.last_modified) }}
              </span>
              <span class="char-count">
                {{ (agents.support_agent.current_prompt || '').length }} caracteres
              </span>
            </div>
          </div>
          
          <div class="agent-actions">
            <button 
              @click="updatePrompt('support_agent')"
              class="btn-update"
              :disabled="isProcessing || !agents.support_agent.current_prompt"
            >
              💾 Actualizar
            </button>
            <button 
              @click="resetPrompt('support_agent')"
              class="btn-reset"
              :disabled="isProcessing || !agents.support_agent.is_custom"
            >
              🔄 Resetear
            </button>
            <button 
              @click="previewPrompt('support_agent')"
              class="btn-preview"
              :disabled="isProcessing || !agents.support_agent.current_prompt"
            >
              👁️ Preview
            </button>
          </div>
        </div>

      </div>

      <!-- No Prompts State -->
      <div v-else-if="!isLoadingPrompts" class="no-prompts-section">
        <h3>📭 No hay prompts disponibles</h3>
        <p>Selecciona una empresa y haz clic en "Recargar Todos" para ver los prompts.</p>
      </div>

    </div>

    <!-- Loading State -->
    <div v-if="isLoadingPrompts" class="loading-section">
      <div class="loading-spinner"></div>
      <p>Cargando prompts del sistema...</p>
    </div>

    <!-- Preview Modal -->
    <div v-if="showPreview" class="preview-modal-overlay" @click="closePreview">
      <div class="preview-modal" @click.stop>
        <div class="preview-header">
          <h3>🔍 Vista Previa - {{ previewAgent }}</h3>
          <button @click="closePreview" class="close-btn">×</button>
        </div>
        
        <div class="preview-body">
          <!-- Loading state -->
          <div v-if="previewLoading" class="preview-loading">
            <div class="loading-spinner"></div>
            <p>Generando preview...</p>
          </div>
          
          <!-- Preview content -->
          <div v-else-if="previewResponse">
            <!-- Test info -->
            <div class="preview-section">
              <h4>📋 Información del Test</h4>
              <div class="info-row">
                <span class="label">Agente:</span>
                <span class="value">{{ previewAgent }}</span>
              </div>
              <div class="info-row">
                <span class="label">Empresa:</span>
                <span class="value">{{ currentCompanyName }}</span>
              </div>
              <div class="info-row">
                <span class="label">Mensaje de prueba:</span>
                <div class="test-message">{{ previewTestMessage }}</div>
              </div>
            </div>
            
            <!-- Response section if success -->
            <div v-if="previewResponse.success" class="preview-section">
              <h4>🤖 Respuesta Generada</h4>
              <div class="response-content">
                {{ previewResponse.preview }}
              </div>
              
              <!-- Debug info if available -->
              <div v-if="previewResponse.debug_info" class="debug-info">
                <div v-if="previewResponse.prompt_source" class="info-row">
                  <span class="label">Fuente del prompt:</span>
                  <span class="value">{{ previewResponse.prompt_source }}</span>
                </div>
                <div v-if="previewResponse.agent_used" class="info-row">
                  <span class="label">Agente usado:</span>
                  <span class="value">{{ previewResponse.agent_used }}</span>
                </div>
                <div v-if="previewResponse.debug_info.response_length" class="info-row">
                  <span class="label">Longitud respuesta:</span>
                  <span class="value">{{ previewResponse.debug_info.response_length }} caracteres</span>
                </div>
                <div v-if="previewResponse.debug_info.processing_time" class="info-row">
                  <span class="label">Tiempo de procesamiento:</span>
                  <span class="value">{{ previewResponse.debug_info.processing_time }}ms</span>
                </div>
              </div>
            </div>
            
            <!-- Error section if failed -->
            <div v-else-if="!previewResponse.success" class="preview-section error-section">
              <h4>❌ Error en Preview</h4>
              <p>{{ previewResponse.error }}</p>
              
              <!-- Fallback preview if available -->
              <div v-if="previewResponse.fallback" class="fallback-preview">
                <h4>📝 Prompt Actual (sin procesamiento)</h4>
                <div class="prompt-preview">
                  {{ previewResponse.prompt_content || previewContent }}
                </div>
              </div>
            </div>
            
            <!-- Current prompt section -->
            <div class="preview-section">
              <h4>📝 Prompt Actual</h4>
              <div class="prompt-preview">
                {{ previewContent.substring(0, 500) }}{{ previewContent.length > 500 ? '...' : '' }}
              </div>
            </div>
          </div>
        </div>
        
        <div class="preview-footer">
          <button @click="closePreview" class="btn-primary">Cerrar</button>
          <button @click="copyPreviewResponse" class="btn-secondary" v-if="previewResponse?.preview">
            📋 Copiar Respuesta
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<script>
// ===============================================================================
// PASO 2: COMPOSABLE CENTRALIZADO - ELIMINADA TODA LÓGICA API DUPLICADA  
// ===============================================================================
import { usePrompts } from '@/composables/usePrompts'
import PromptsStatus from './PromptsStatus.vue'

export default {
  name: 'PromptsTab',
  components: {
    PromptsStatus
  },
  props: {
    isActive: {
      type: Boolean,
      default: false
    }
  },
  setup() {
    // ===============================================================================
    // PASO 2: USAR ÚNICAMENTE EL COMPOSABLE - ELIMINAR data(), methods(), etc.
    // ===============================================================================
    const {
      // Estado reactivo del composable
      agents,
      isLoadingPrompts,
      isProcessing,
      error,
      showPreview,
      previewAgent,
      previewContent,
      previewTestMessage,
      previewResponse,
      previewLoading,
      
      // Computed properties del composable
      hasPrompts,
      currentCompanyId,
      currentCompanyName,
      
      // Funciones del composable (nombres exactos que funcionan con backend)
      loadPrompts,
      updatePrompt,
      resetPrompt,
      previewPrompt,
      closePreview,
      repairAllPrompts,
      exportPrompts,
      formatDate
    } = usePrompts()

    // ===============================================================================
    // HANDLERS PARA EVENTOS DE PROMPTSSTATUS.VUE
    // ===============================================================================
    const handleStatusLoaded = (status) => {
      console.log('Status loaded:', status)
      if (status?.postgresql_available && status?.tables_exist) {
        loadPrompts()
      }
    }

    const handleMigrationComplete = () => {
      loadPrompts()
    }

    // ===============================================================================
    // FUNCIÓN PARA COPIAR RESPUESTA DE PREVIEW
    // ===============================================================================
    const copyPreviewResponse = () => {
      if (previewResponse.value?.preview) {
        const textToCopy = previewResponse.value.preview
        
        if (navigator.clipboard) {
          navigator.clipboard.writeText(textToCopy).then(() => {
            alert('Respuesta copiada al portapapeles')
          }).catch(() => {
            fallbackCopy(textToCopy)
          })
        } else {
          fallbackCopy(textToCopy)
        }
      }
    }

    const fallbackCopy = (text) => {
      const textArea = document.createElement('textarea')
      textArea.value = text
      document.body.appendChild(textArea)
      textArea.select()
      document.execCommand('copy')
      document.body.removeChild(textArea)
      alert('Respuesta copiada al portapapeles')
    }

    return {
      // Estado del composable
      agents,
      isLoadingPrompts,
      isProcessing,
      error,
      showPreview,
      previewAgent,
      previewContent,
      previewTestMessage,
      previewResponse,
      previewLoading,
      
      // Computed properties del composable
      hasPrompts,
      currentCompanyId,
      currentCompanyName,
      
      // Funciones del composable
      loadPrompts,
      updatePrompt,
      resetPrompt,
      previewPrompt,
      closePreview,
      repairAllPrompts,
      exportPrompts,
      formatDate,
      
      // Handlers locales
      handleStatusLoaded,
      handleMigrationComplete,
      copyPreviewResponse
    }
  },
  watch: {
    // ===============================================================================
    // CARGAR PROMPTS CUANDO SE ACTIVA EL TAB
    // ===============================================================================
    isActive(newVal) {
      if (newVal) {
        console.log('PromptsTab is now active, loading prompts...')
        this.loadPrompts()
      }
    }
  },
  mounted() {
    console.log('PromptsTab mounted, isActive:', this.isActive)
    
    // Cargar prompts si está activo
    if (this.isActive) {
      console.log('Tab is active on mount, loading prompts...')
      this.loadPrompts()
    }
    
    // ===============================================================================
    // EXPONER FUNCIONES GLOBALES PARA COMPATIBILIDAD CON SCRIPT.JS
    // ===============================================================================
    window.loadCurrentPrompts = () => this.loadPrompts()
    window.updatePrompt = (agentName) => this.updatePrompt(agentName)
    window.resetPrompt = (agentName) => this.resetPrompt(agentName)
    window.previewPrompt = (agentName) => this.previewPrompt(agentName)
    window.repairAllPrompts = () => this.repairAllPrompts()
    window.exportPrompts = () => this.exportPrompts()
    
    // Exponer instancia para debug
    window.PromptsTabInstance = this
  },
  unmounted() {
    // Limpiar funciones globales
    if (typeof window !== 'undefined') {
      delete window.loadCurrentPrompts
      delete window.updatePrompt
      delete window.resetPrompt
      delete window.previewPrompt
      delete window.repairAllPrompts
      delete window.exportPrompts
      delete window.PromptsTabInstance
    }
  }
}
</script>

<style scoped>
.prompts-tab {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.tab-header {
  text-align: center;
  margin-bottom: 30px;
}

.tab-header h2 {
  margin: 0 0 10px 0;
  color: #2c3e50;
  font-size: 2em;
}

.tab-description {
  color: #6c757d;
  font-size: 1.1em;
  margin: 0;
}

.prompts-main-section {
  margin-top: 20px;
}

.company-bar {
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 15px 20px;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.company-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.company-label {
  font-weight: 600;
  color: #495057;
}

.company-name {
  color: #007bff;
  font-weight: bold;
  font-size: 1.1em;
}

.actions-bar {
  display: flex;
  gap: 10px;
}

.actions-bar button {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
}

.btn-refresh {
  background: #28a745;
  color: white;
}

.btn-refresh:hover:not(:disabled) {
  background: #218838;
}

.btn-repair-all {
  background: #fd7e14;
  color: white;
}

.btn-repair-all:hover:not(:disabled) {
  background: #e8690b;
}

.btn-export {
  background: #17a2b8;
  color: white;
}

.btn-export:hover:not(:disabled) {
  background: #117a8b;
}

.error-section {
  background: #f8d7da;
  color: #721c24;
  padding: 15px;
  border-radius: 4px;
  margin-bottom: 20px;
}

/* Prompts Grid */
.prompts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 20px;
}

.agent-card {
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  transition: transform 0.2s;
}

.agent-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}

.agent-header {
  background: #f8f9fa;
  padding: 15px;
  border-bottom: 1px solid #dee2e6;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.agent-header h3 {
  margin: 0;
  font-size: 1.1em;
  color: #495057;
}

.status-badge {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 0.85em;
  font-weight: 600;
}

.status-badge.custom {
  background: rgba(40, 167, 69, 0.1);
  color: #28a745;
}

.status-badge.default {
  background: rgba(108, 117, 125, 0.1);
  color: #6c757d;
}

.agent-body {
  padding: 15px;
}

.prompt-textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
  resize: vertical;
  transition: border-color 0.2s;
}

.prompt-textarea:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 0.2rem rgba(0,123,255,.25);
}

.prompt-info {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
  font-size: 0.85em;
  color: #6c757d;
}

.agent-actions {
  padding: 15px;
  background: #f8f9fa;
  border-top: 1px solid #dee2e6;
  display: flex;
  gap: 10px;
}

.agent-actions button {
  flex: 1;
  padding: 8px 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.9em;
  transition: all 0.2s;
}

.btn-update {
  background: #007bff;
  color: white;
}

.btn-update:hover:not(:disabled) {
  background: #0056b3;
}

.btn-reset {
  background: #6c757d;
  color: white;
}

.btn-reset:hover:not(:disabled) {
  background: #545b62;
}

.btn-preview {
  background: #17a2b8;
  color: white;
}

.btn-preview:hover:not(:disabled) {
  background: #117a8b;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.no-prompts-section {
  text-align: center;
  padding: 60px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 2px dashed #dee2e6;
}

.loading-section {
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

/* Responsive */
@media (max-width: 768px) {
  .prompts-grid {
    grid-template-columns: 1fr;
  }
  
  .company-bar {
    flex-direction: column;
    gap: 15px;
  }
  
  .actions-bar {
    width: 100%;
    flex-direction: column;
  }
  
  .actions-bar button {
    width: 100%;
  }
}

/* Preview Modal Styles */
.preview-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
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

.preview-modal {
  background: white;
  border-radius: 8px;
  width: 90%;
  max-width: 800px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from { 
    opacity: 0;
    transform: translateY(-30px);
  }
  to { 
    opacity: 1;
    transform: translateY(0);
  }
}

.preview-header {
  padding: 20px;
  background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
  color: white;
  border-radius: 8px 8px 0 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preview-header h3 {
  margin: 0;
  font-size: 1.3em;
}

.close-btn {
  background: none;
  border: none;
  color: white;
  font-size: 28px;
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: background 0.2s;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

.preview-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.preview-loading {
  text-align: center;
  padding: 40px;
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

.info-row {
  display: flex;
  align-items: flex-start;
  margin-bottom: 10px;
}

.info-row .label {
  font-weight: 600;
  color: #495057;
  min-width: 150px;
  margin-right: 15px;
}

.info-row .value {
  flex: 1;
  color: #212529;
}

.test-message {
  background: white;
  border: 1px solid #ced4da;
  border-left: 4px solid #007bff;
  border-radius: 4px;
  padding: 10px;
  margin-top: 5px;
  font-family: monospace;
}

.response-content {
  background: white;
  border: 1px solid #ced4da;
  border-radius: 6px;
  padding: 15px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 300px;
  overflow-y: auto;
}

.debug-info {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid #dee2e6;
}

.error-section {
  background: #f8d7da;
  border-color: #f5c6cb;
}

.error-section h4 {
  color: #721c24;
  border-bottom-color: #dc3545;
}

.fallback-preview {
  margin-top: 20px;
}

.prompt-preview {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 15px;
  font-family: monospace;
  font-size: 0.9em;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 200px;
  overflow-y: auto;
}

.preview-footer {
  padding: 20px;
  border-top: 1px solid #e9ecef;
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  background: #f8f9fa;
  border-radius: 0 0 8px 8px;
}

.preview-footer button {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
}

.preview-footer .btn-primary {
  background: #007bff;
  color: white;
}

.preview-footer .btn-primary:hover {
  background: #0056b3;
}

.preview-footer .btn-secondary {
  background: #6c757d;
  color: white;
}

.preview-footer .btn-secondary:hover {
  background: #545b62;
}

/* Responsive modal */
@media (max-width: 768px) {
  .preview-modal {
    width: 95%;
    max-height: 90vh;
    margin: 10px;
  }
  
  .info-row {
    flex-direction: column;
  }
  
  .info-row .label {
    margin-bottom: 5px;
    min-width: auto;
  }
  
  .preview-footer {
    flex-direction: column;
  }
  
  .preview-footer button {
    width: 100%;
  }
}
</style>
