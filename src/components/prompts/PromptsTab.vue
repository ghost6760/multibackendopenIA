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

    <!-- ✅ Loading State de Inicialización -->
    <div v-if="!isReady" class="initialization-loading">
      <div class="loading-spinner"></div>
      <p>Inicializando sistema de prompts...</p>
    </div>

    <!-- Main Prompts Section - Solo cuando esté listo -->
    <div v-else class="prompts-main-section">
      
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
        <button @click="retryInitialization" class="btn-retry">
          🔄 Reintentar Inicialización
        </button>
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
        <button @click="debugPrompts" class="btn-debug">
          🐛 Debug Prompts
        </button>
      </div>

    </div>

    <!-- Loading State -->
    <div v-if="isLoadingPrompts" class="loading-section">
      <div class="loading-spinner"></div>
      <p>Cargando prompts del sistema...</p>
    </div>

    <!-- PASO 4: PROMPT PREVIEW MODULAR -->
    <PromptPreview
      v-if="isReady"
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
// IMPORTS MODULARES - ✅ SIN CAMBIOS
// ===============================================================================
import { ref, computed, watch, onMounted, onUnmounted, getCurrentInstance, nextTick } from 'vue'
import { usePrompts } from '@/composables/usePrompts'
import PromptsStatus from './PromptsStatus.vue'
import PromptEditor from './PromptEditor.vue'
import PromptPreview from './PromptPreview.vue'

// ===============================================================================
// PROPS - ✅ SIN CAMBIOS
// ===============================================================================
const props = defineProps({
  isActive: {
    type: Boolean,
    default: false
  }
})

// ===============================================================================
// ESTADO LOCAL DEL COMPONENTE - ✅ NUEVO PATRÓN SEGURO
// ===============================================================================

const isReady = ref(false)
const initializationError = ref(null)
let promptsComposable = null

// ===============================================================================
// INICIALIZACIÓN DIFERIDA - ✅ SOLUCIÓN PRINCIPAL
// ===============================================================================

/**
 * ✅ Inicialización diferida del composable para evitar dependencias circulares
 */
const initializeTab = async () => {
  try {
    console.log('🚀 Initializing PromptsTab...')
    
    // Asegurar que Vue esté completamente listo
    await nextTick()
    
    // ✅ Inicialización diferida del composable
    promptsComposable = usePrompts()
    
    // Verificar que el composable se haya inicializado correctamente
    if (!promptsComposable) {
      throw new Error('Failed to initialize prompts composable')
    }
    
    isReady.value = true
    initializationError.value = null
    
    console.log('✅ PromptsTab initialized successfully')
    
    // Cargar datos solo si el tab está activo
    if (props.isActive) {
      console.log('Tab is active, loading prompts...')
      await promptsComposable.loadPrompts()
    }
    
  } catch (error) {
    console.error('❌ Error initializing PromptsTab:', error)
    initializationError.value = error.message
    isReady.value = false
  }
}

/**
 * ✅ Reintento de inicialización
 */
const retryInitialization = async () => {
  initializationError.value = null
  isReady.value = false
  promptsComposable = null
  await initializeTab()
}

// ===============================================================================
// COMPUTED PROPERTIES - ✅ ACCESO SEGURO AL COMPOSABLE
// ===============================================================================

// Estados del composable con verificaciones seguras
const agents = computed(() => {
  return promptsComposable?.agents?.value || {}
})

const isLoadingPrompts = computed(() => {
  return promptsComposable?.isLoadingPrompts?.value || false
})

const isProcessing = computed(() => {
  return promptsComposable?.isProcessing?.value || false
})

const error = computed(() => {
  return initializationError.value || promptsComposable?.error?.value || null
})

const showPreview = computed(() => {
  return promptsComposable?.showPreview?.value || false
})

const previewAgent = computed(() => {
  return promptsComposable?.previewAgent?.value || ''
})

const previewContent = computed(() => {
  return promptsComposable?.previewContent?.value || ''
})

const previewTestMessage = computed(() => {
  return promptsComposable?.previewTestMessage?.value || ''
})

const previewResponse = computed(() => {
  return promptsComposable?.previewResponse?.value || null
})

const previewLoading = computed(() => {
  return promptsComposable?.previewLoading?.value || false
})

const hasPrompts = computed(() => {
  return promptsComposable?.hasPrompts?.value || false
})

const currentCompanyId = computed(() => {
  return promptsComposable?.currentCompanyId?.value || ''
})

const currentCompanyName = computed(() => {
  return promptsComposable?.currentCompanyName?.value || ''
})

const agentsList = computed(() => {
  return promptsComposable?.agentsList?.value || []
})

// ===============================================================================
// MÉTODOS DEL COMPOSABLE - ✅ PROXY SEGURO
// ===============================================================================

/**
 * ✅ Métodos que verifican que el composable esté listo antes de ejecutar
 */
const loadPrompts = async () => {
  if (!promptsComposable || !isReady.value) {
    console.warn('Composable not ready, retrying initialization...')
    await retryInitialization()
    return
  }
  return await promptsComposable.loadPrompts()
}

const updatePrompt = async (agentName, customContent = null) => {
  if (!promptsComposable) return
  return await promptsComposable.updatePrompt(agentName, customContent)
}

const resetPrompt = async (agentName) => {
  if (!promptsComposable) return
  return await promptsComposable.resetPrompt(agentName)
}

const previewPrompt = async (agentName) => {
  if (!promptsComposable) return
  return await promptsComposable.previewPrompt(agentName)
}

const closePreview = () => {
  if (!promptsComposable) return
  return promptsComposable.closePreview()
}

const repairAllPrompts = async () => {
  if (!promptsComposable) return
  return await promptsComposable.repairAllPrompts()
}

const exportPrompts = () => {
  if (!promptsComposable) return
  return promptsComposable.exportPrompts()
}

const debugPrompts = async () => {
  if (!promptsComposable) return
  return await promptsComposable.debugPrompts()
}

const testEndpoints = async () => {
  if (!promptsComposable) return
  return await promptsComposable.testEndpoints()
}

// ===============================================================================
// HANDLERS DE EVENTOS - ✅ SIN CAMBIOS EN LA LÓGICA
// ===============================================================================

/**
 * Handler para evento update de PromptEditor
 * ✅ CORREGIDO: Recibe datos estructurados
 */
const handlePromptUpdate = (updateData) => {
  if (typeof updateData === 'string') {
    // Compatibilidad con llamadas antiguas (solo agentName)
    updatePrompt(updateData)
  } else {
    // Usar el nuevo formato con contenido
    updatePrompt(updateData.agentName, updateData.content)
  }
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

// Handlers para eventos de PromptsStatus.vue
const handleStatusLoaded = (status) => {
  console.log('Status loaded:', status)
  if (status?.postgresql_available && status?.tables_exist && isReady.value) {
    loadPrompts()
  }
}

const handleMigrationComplete = () => {
  if (isReady.value) {
    loadPrompts()
  }
}

// ===============================================================================
// WATCHERS - ✅ CON VERIFICACIONES SEGURAS
// ===============================================================================

// Cargar prompts cuando se activa el tab
watch(() => props.isActive, async (newVal) => {
  if (newVal && isReady.value) {
    console.log('PromptsTab is now active, loading prompts...')
    await loadPrompts()
  } else if (newVal && !isReady.value) {
    // Si el tab se activa pero no está listo, intentar inicializar
    console.log('Tab activated but not ready, initializing...')
    await initializeTab()
  }
})

// ===============================================================================
// LIFECYCLE HOOKS - ✅ INICIALIZACIÓN DIFERIDA
// ===============================================================================

onMounted(async () => {
  console.log('PromptsTab mounted, isActive:', props.isActive)
  
  // ✅ INICIALIZACIÓN DIFERIDA usando nextTick
  nextTick(initializeTab)
  
  // ✅ EXPONER FUNCIONES GLOBALES para compatibilidad (solo después de inicialización)
  if (typeof window !== 'undefined') {
    // Funciones proxy que verifican la inicialización
    window.loadCurrentPrompts = () => loadPrompts()
    window.updatePrompt = (agentName, content) => updatePrompt(agentName, content)
    window.resetPrompt = (agentName) => resetPrompt(agentName)
    window.previewPrompt = (agentName) => previewPrompt(agentName)
    window.repairAllPrompts = () => repairAllPrompts()
    window.exportPrompts = () => exportPrompts()
    window.debugPrompts = () => debugPrompts()
    window.testPromptEndpoints = () => testEndpoints()
    
    // Instancia para debug
    window.PromptsTabInstance = getCurrentInstance()
    
    // ✅ NUEVO: Flag para verificar estado de inicialización
    window.isPromptsTabReady = () => isReady.value
  }
})

onUnmounted(() => {
  console.log('PromptsTab unmounting...')
  
  // Limpiar funciones globales
  if (typeof window !== 'undefined') {
    delete window.loadCurrentPrompts
    delete window.updatePrompt
    delete window.resetPrompt
    delete window.previewPrompt
    delete window.repairAllPrompts
    delete window.exportPrompts
    delete window.debugPrompts
    delete window.testPromptEndpoints
    delete window.PromptsTabInstance
    delete window.isPromptsTabReady
  }
  
  // Limpiar referencias
  promptsComposable = null
  isReady.value = false
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

/* ✅ NUEVO: Loading de inicialización */
.initialization-loading {
  text-align: center;
  padding: 60px 20px;
  background: #f8f9fa;
  border: 2px dashed #007bff;
  border-radius: 8px;
  margin-bottom: 20px;
}

.initialization-loading .loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 15px;
}

.initialization-loading p {
  color: #007bff;
  font-weight: 500;
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
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.btn-retry {
  background: #007bff;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
}

.btn-retry:hover {
  background: #0056b3;
}

.btn-debug {
  background: #6f42c1;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
  margin-top: 15px;
}

.btn-debug:hover {
  background: #5a32a3;
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

.no-prompts-section h3 {
  color: #6c757d;
  margin-bottom: 10px;
}

.no-prompts-section p {
  color: #6c757d;
  margin-bottom: 20px;
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
  
  .error-section {
    flex-direction: column;
    gap: 10px;
    text-align: center;
  }
}
</style>
