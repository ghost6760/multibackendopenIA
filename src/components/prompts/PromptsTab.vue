<template>
  <div class="prompts-tab" v-if="isActive">
    <!-- Header del Tab -->
    <div class="tab-header">
      <h2>🤖 Sistema de Prompts</h2>
      <p class="tab-description">
        Gestiona y personaliza los prompts de los agentes IA para {{ currentCompanyName }}
      </p>
    </div>

    <!-- Initialization Loading -->
    <div v-if="!componentsReady" class="initializing-section">
      <div class="loading-spinner"></div>
      <p>Inicializando sistema de prompts...</p>
      <small v-if="initializationError" style="color: red;">
        Error: {{ initializationError }}
      </small>
    </div>

    <!-- Main Content - Solo cuando todo está listo -->
    <template v-else>
      <!-- Estado del Sistema -->
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
            <button @click="safeLoadPrompts" class="btn-refresh" :disabled="isLoadingPrompts">
              <span v-if="isLoadingPrompts">⏳ Cargando...</span>
              <span v-else">🔄 Recargar Todos</span>
            </button>
            <button @click="safeRepairAllPrompts" class="btn-repair-all" :disabled="isProcessing">
              🔧 Reparar Todos
            </button>
            <button @click="safeExportPrompts" class="btn-export">
              💾 Exportar
            </button>
          </div>
        </div>

        <!-- Error State -->
        <div v-if="error" class="error-section">
          <p>⚠️ {{ error }}</p>
        </div>

        <!-- Prompts Grid -->
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

        <!-- Loading State -->
        <div v-if="isLoadingPrompts" class="loading-section">
          <div class="loading-spinner"></div>
          <p>Cargando prompts del sistema...</p>
        </div>

      </div>

      <!-- Prompt Preview Modal -->
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
    </template>

  </div>
</template>

<script setup>
// ===============================================================================
// IMPORTS SEGUROS - Sin acceso prematuro
// ===============================================================================
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'

// Componentes - importación estática segura
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
// ESTADO DE INICIALIZACIÓN
// ===============================================================================
const componentsReady = ref(false)
const initializationError = ref(null)

// Estado local reactivo (no depende del composable)
const isLoadingPrompts = ref(false)
const isProcessing = ref(false)
const error = ref(null)
const showPreview = ref(false)
const previewAgent = ref('')
const previewContent = ref('')
const previewTestMessage = ref('')
const previewResponse = ref(null)
const previewLoading = ref(false)
const hasPrompts = ref(false)
const currentCompanyId = ref('benova')
const currentCompanyName = ref('benova')
const agentsList = ref([])

// Referencia al composable (se inicializa después)
let promptsComposable = null

// ===============================================================================
// INICIALIZACIÓN SEGURA DEL COMPOSABLE
// ===============================================================================

const initializeComposable = async () => {
  try {
    console.log('[PromptsTab] Starting composable initialization...')
    
    // Esperar a que Vue esté completamente inicializado
    await nextTick()
    
    // ✅ IMPORTACIÓN DINÁMICA SEGURA
    const { usePrompts } = await import('@/composables/usePrompts')
    promptsComposable = usePrompts()
    
    // ✅ Verificar que el composable tenga sus métodos
    if (!promptsComposable.initializeComposables) {
      throw new Error('Composable methods not available')
    }

    // ✅ Inicializar los composables internos
    const ready = promptsComposable.initializeComposables()
    if (!ready) {
      // Reintento después de un breve delay
      await new Promise(resolve => setTimeout(resolve, 200))
      const retryReady = promptsComposable.initializeComposables()
      if (!retryReady) {
        throw new Error('Composables not ready after retry')
      }
    }

    // ✅ Sincronizar estado reactivo
    syncComposableState()
    
    componentsReady.value = true
    console.log('[PromptsTab] ✅ Composable initialized successfully')
    
    // ✅ Cargar prompts si el tab está activo
    if (props.isActive) {
      await safeLoadPrompts()
    }
    
    return true

  } catch (error) {
    console.error('[PromptsTab] Composable initialization error:', error)
    initializationError.value = error.message
    componentsReady.value = false
    return false
  }
}

// ===============================================================================
// SINCRONIZACIÓN DE ESTADO
// ===============================================================================

const syncComposableState = () => {
  if (!promptsComposable || !componentsReady.value) return

  try {
    // ✅ Sincronizar estado reactivo bidireccional
    isLoadingPrompts.value = promptsComposable.isLoadingPrompts.value
    isProcessing.value = promptsComposable.isProcessing.value
    error.value = promptsComposable.error.value
    showPreview.value = promptsComposable.showPreview.value
    previewAgent.value = promptsComposable.previewAgent.value
    previewContent.value = promptsComposable.previewContent.value
    previewTestMessage.value = promptsComposable.previewTestMessage.value
    previewResponse.value = promptsComposable.previewResponse.value
    previewLoading.value = promptsComposable.previewLoading.value
    hasPrompts.value = promptsComposable.hasPrompts.value
    currentCompanyId.value = promptsComposable.currentCompanyId.value
    currentCompanyName.value = promptsComposable.currentCompanyName.value
    agentsList.value = promptsComposable.agentsList.value

    console.log('[PromptsTab] State synchronized with composable')
  } catch (error) {
    console.warn('[PromptsTab] Error syncing state:', error)
  }
}

// ===============================================================================
// FUNCIONES SEGURAS - Solo llaman al composable si está listo
// ===============================================================================

const safeLoadPrompts = async () => {
  if (!componentsReady.value || !promptsComposable) {
    console.warn('[PromptsTab] Cannot load prompts: not ready')
    return
  }
  
  try {
    await promptsComposable.loadPrompts()
    syncComposableState()
  } catch (error) {
    console.error('[PromptsTab] Error loading prompts:', error)
  }
}

const safeRepairAllPrompts = async () => {
  if (!componentsReady.value || !promptsComposable) {
    console.warn('[PromptsTab] Cannot repair prompts: not ready')
    return
  }
  
  try {
    await promptsComposable.repairAllPrompts()
    syncComposableState()
  } catch (error) {
    console.error('[PromptsTab] Error repairing prompts:', error)
  }
}

const safeExportPrompts = () => {
  if (!componentsReady.value || !promptsComposable) {
    console.warn('[PromptsTab] Cannot export prompts: not ready')
    return
  }
  
  try {
    promptsComposable.exportPrompts()
  } catch (error) {
    console.error('[PromptsTab] Error exporting prompts:', error)
  }
}

// ===============================================================================
// EVENT HANDLERS - Con guards de seguridad
// ===============================================================================

const handlePromptUpdate = (updateData) => {
  if (!componentsReady.value || !promptsComposable) return
  
  try {
    if (typeof updateData === 'string') {
      promptsComposable.updatePrompt(updateData)
    } else {
      promptsComposable.updatePrompt(updateData.agentName, updateData.content)
    }
    syncComposableState()
  } catch (error) {
    console.error('[PromptsTab] Error updating prompt:', error)
  }
}

const handlePromptReset = (agentName) => {
  if (!componentsReady.value || !promptsComposable) return
  
  try {
    promptsComposable.resetPrompt(agentName)
    syncComposableState()
  } catch (error) {
    console.error('[PromptsTab] Error resetting prompt:', error)
  }
}

const handlePromptPreview = (agentName) => {
  if (!componentsReady.value || !promptsComposable) return
  
  try {
    promptsComposable.previewPrompt(agentName)
    syncComposableState()
  } catch (error) {
    console.error('[PromptsTab] Error previewing prompt:', error)
  }
}

const closePreview = () => {
  if (!componentsReady.value || !promptsComposable) return
  
  try {
    promptsComposable.closePreview()
    syncComposableState()
  } catch (error) {
    console.error('[PromptsTab] Error closing preview:', error)
  }
}

// ===============================================================================
// EVENT HANDLERS PARA PROMPTS STATUS
// ===============================================================================
const handleStatusLoaded = (status) => {
  console.log('[PromptsTab] Status loaded:', status)
  if (status?.postgresql_available && status?.tables_exist) {
    safeLoadPrompts()
  }
}

const handleMigrationComplete = () => {
  safeLoadPrompts()
}

// ===============================================================================
// WATCHERS SEGUROS
// ===============================================================================

// Watch para activación del tab
watch(() => props.isActive, async (newVal) => {
  if (newVal) {
    console.log('[PromptsTab] Tab activated')
    
    if (!componentsReady.value) {
      console.log('[PromptsTab] Components not ready, initializing...')
      await initializeComposable()
    } else {
      console.log('[PromptsTab] Components ready, loading prompts...')
      await safeLoadPrompts()
    }
  }
})

// ===============================================================================
// LIFECYCLE HOOKS
// ===============================================================================

onMounted(async () => {
  console.log('[PromptsTab] Component mounted, isActive:', props.isActive)
  
  // ✅ Inicializar de forma diferida para evitar problemas de timing
  setTimeout(async () => {
    await initializeComposable()
  }, 100)
  
  // ✅ FUNCIONES GLOBALES MÍNIMAS para compatibilidad
  if (typeof window !== 'undefined') {
    window.loadCurrentPrompts = () => safeLoadPrompts()
    window.repairAllPrompts = () => safeRepairAllPrompts()
    window.exportPrompts = () => safeExportPrompts()
  }
})

onUnmounted(() => {
  console.log('[PromptsTab] Component unmounting, cleaning up...')
  
  // Cleanup composable
  if (promptsComposable?.cleanup) {
    promptsComposable.cleanup()
  }
  
  // Cleanup global functions
  if (typeof window !== 'undefined') {
    delete window.loadCurrentPrompts
    delete window.repairAllPrompts
    delete window.exportPrompts
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

.initializing-section {
  text-align: center;
  padding: 60px 20px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #dee2e6;
}

.initializing-section .loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
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
