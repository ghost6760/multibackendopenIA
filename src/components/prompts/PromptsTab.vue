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

      <!-- Prompts Grid - PASO 3: USAR PROMPT EDITOR MODULAR -->
      <div v-if="hasPrompts" class="prompts-grid">
        <PromptEditor
          v-for="agent in agentsList"
          :key="agent.id"
          :prompt-data="agent"
          :readonly="isProcessing"
          @update="handlePromptUpdate"
          @reset="handlePromptReset"
          @preview="handlePromptPreview"
        />
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

    <!-- PASO 4: PROMPT PREVIEW MODULAR -->
    <PromptPreview
      :visible="showPreview"
      :agent-name="previewAgent"
      :prompt-content="previewContent"
      :test-message="previewTestMessage"
      :preview-response="previewResponse"
      :loading="previewLoading"
      :company-id="currentCompanyId"
      @close="closePreview"
    />

  </div>
</template>

<script>
// ===============================================================================
// PASO 4: IMPORTS MODULARES COMPLETOS
// ===============================================================================
import { usePrompts } from '@/composables/usePrompts'
import PromptsStatus from './PromptsStatus.vue'
import PromptEditor from './PromptEditor.vue'
import PromptPreview from './PromptPreview.vue'

export default {
  name: 'PromptsTab',
  components: {
    PromptsStatus,
    PromptEditor,
    PromptPreview
  },
  props: {
    isActive: {
      type: Boolean,
      default: false
    }
  },
  setup() {
    // ===============================================================================
    // PASO 3: USAR COMPOSABLE + AGENTES MODULARES
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
      agentsList,
      
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
    // PASO 3: HANDLERS PARA EVENTOS DE PROMPT EDITOR
    // ===============================================================================
    const handlePromptUpdate = (promptData) => {
      // PromptEditor emite el objeto completo, extraer el nombre del agente
      updatePrompt(promptData.id || promptData.name)
    }

    const handlePromptReset = (promptData) => {
      // PromptEditor emite el objeto completo, extraer el nombre del agente
      resetPrompt(promptData.id || promptData.name)
    }

    const handlePromptPreview = (promptData) => {
      // PromptEditor emite el objeto completo, extraer el nombre del agente
      previewPrompt(promptData.id || promptData.name)
    }

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
      agentsList,
      
      // Funciones del composable
      loadPrompts,
      updatePrompt,
      resetPrompt,
      previewPrompt,
      closePreview,
      repairAllPrompts,
      exportPrompts,
      formatDate,
      
      // Handlers para PromptsStatus
      handleStatusLoaded,
      handleMigrationComplete,
      
      // PASO 3: Handlers para PromptEditor
      handlePromptUpdate,
      handlePromptReset,
      handlePromptPreview
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
</style>
