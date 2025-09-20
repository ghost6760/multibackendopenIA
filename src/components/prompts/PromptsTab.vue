# PromptsTab.vue - FUNCIONES GLOBALES CORREGIDAS
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

<script setup>
// ===============================================================================
// IMPORTS MODULARES COMPLETOS + CORRECCIONES
// ===============================================================================
import { watch, onMounted, onUnmounted, getCurrentInstance } from 'vue'
import { usePrompts } from '@/composables/usePrompts'
import PromptsStatus from './PromptsStatus.vue'
import PromptEditor from './PromptEditor.vue'
import PromptPreview from './PromptPreview.vue'

// ===============================================================================
// PROPS
// ===============================================================================
const props = defineProps({
  isActive: {
    type: Boolean,
    default: false
  }
})

// ===============================================================================
// COMPOSABLE - OBTENER TODAS LAS FUNCIONES INCLUYENDO DEBUG
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
  
  // Funciones principales (nombres exactos que funcionan con backend)
  loadPrompts,
  updatePrompt,
  resetPrompt,
  previewPrompt,
  closePreview,
  repairAllPrompts,
  exportPrompts,
  formatDate,
  
  // Funciones debug del composable
  debugPrompts,
  testEndpoints
} = usePrompts()

// ===============================================================================
// HANDLERS CORREGIDOS - RECIBEN SOLO agentName
// ===============================================================================

/**
 * Handler para evento update de PromptEditor
 */
const handlePromptUpdate = (agentName) => {
  updatePrompt(agentName)
}

/**
 * Handler para evento reset de PromptEditor  
 */
const handlePromptReset = (agentName) => {
  resetPrompt(agentName)
}

/**
 * Handler para evento preview de PromptEditor
 */
const handlePromptPreview = (agentName) => {
  previewPrompt(agentName)
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

// ===============================================================================
// WATCHERS - CARGAR PROMPTS CUANDO SE ACTIVA EL TAB
// ===============================================================================
watch(() => props.isActive, (newVal) => {
  if (newVal) {
    console.log('PromptsTab is now active, loading prompts...')
    loadPrompts()
  }
})

// ===============================================================================
// LIFECYCLE HOOKS CON CORRECCIONES COMPLETAS
// ===============================================================================

onMounted(() => {
  console.log('PromptsTab mounted, isActive:', props.isActive)
  
  // Cargar prompts si está activo
  if (props.isActive) {
    console.log('Tab is active on mount, loading prompts...')
    loadPrompts()
  }
  
  // ✅ CORRECCIÓN CRÍTICA: EXPONER FUNCIONES Y DATOS CORRECTAMENTE
  if (typeof window !== 'undefined') {
    // ✅ EXPONER DATOS DEL COMPOSABLE DIRECTAMENTE
    window.PromptsTabData = {
      // Estado reactivo
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
      
      // Computed properties
      hasPrompts,
      currentCompanyId,
      currentCompanyName,
      agentsList, // ✅ CRÍTICO: Esto ahora estará disponible
      
      // Funciones
      loadPrompts,
      updatePrompt,
      resetPrompt,
      previewPrompt,
      closePreview,
      repairAllPrompts,
      exportPrompts,
      formatDate,
      debugPrompts,
      testEndpoints
    }
    
    // ✅ FUNCIONES GLOBALES INDIVIDUALES (igual que el monolito)
    window.loadCurrentPrompts = () => loadPrompts()
    window.updatePrompt = (agentName) => updatePrompt(agentName)
    window.resetPrompt = (agentName) => resetPrompt(agentName)
    window.previewPrompt = (agentName) => previewPrompt(agentName)
    window.repairAllPrompts = () => repairAllPrompts()
    window.exportPrompts = () => exportPrompts()
    window.debugPrompts = () => debugPrompts()
    window.testPromptEndpoints = () => testEndpoints()
    
    // ✅ INSTANCIA PARA COMPATIBILIDAD (pero con datos correctos)
    const instance = getCurrentInstance()
    window.PromptsTabInstance = {
      // Datos reactivos del composable
      agents,
      agentsList, // ✅ AHORA ESTARÁ DISPONIBLE
      hasPrompts,
      currentCompanyId,
      currentCompanyName,
      isLoadingPrompts,
      isProcessing,
      error,
      
      // Funciones
      debugPrompts,
      testEndpoints,
      loadPrompts,
      updatePrompt,
      resetPrompt,
      previewPrompt,
      
      // Instancia Vue para casos avanzados
      vueInstance: instance
    }
    
    console.log('✅ Global functions exposed:', {
      PromptsTabData: !!window.PromptsTabData,
      PromptsTabInstance: !!window.PromptsTabInstance,
      agentsList: !!window.PromptsTabInstance.agentsList,
      debugPrompts: typeof window.debugPrompts
    })
  }
})

onUnmounted(() => {
  // ✅ LIMPIAR TODAS las funciones globales
  if (typeof window !== 'undefined') {
    delete window.PromptsTabData
    delete window.PromptsTabInstance
    delete window.loadCurrentPrompts
    delete window.updatePrompt
    delete window.resetPrompt
    delete window.previewPrompt
    delete window.repairAllPrompts
    delete window.exportPrompts
    delete window.debugPrompts
    delete window.testPromptEndpoints
  }
})
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
