<template>
  <div class="prompts-tab" v-if="isActive">
    <!-- Header del Tab -->
    <div class="tab-header">
      <h2>🤖 Sistema de Prompts</h2>
      <p class="tab-description">
        Gestiona y personaliza los prompts de los agentes IA para {{ currentCompanyName }}
      </p>
    </div>

    <!-- ✅ NUEVO: Estado de inicialización -->
    <div v-if="!componentsReady" class="initializing-section">
      <div class="loading-spinner"></div>
      <p>Inicializando sistema de prompts...</p>
      <small v-if="initializationError" style="color: red;">
        Error: {{ initializationError }}
      </small>
    </div>

    <!-- ✅ PRESERVADO: Todo el contenido original, pero solo cuando está listo -->
    <template v-else>
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
            <button @click="safeLoadPrompts" class="btn-refresh" :disabled="isLoadingPrompts">
              <span v-if="isLoadingPrompts">⏳ Cargando...</span>
              <span v-else>🔄 Recargar Todos</span>
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
    </template>

  </div>
</template>

<script setup>
// ===============================================================================
// IMPORTS MODULARES COMPLETOS + CORRECCIONES DE INICIALIZACIÓN
// ===============================================================================
import { ref, watch, onMounted, onUnmounted, getCurrentInstance, nextTick } from 'vue'

// ✅ CORREGIDO: Importaciones estáticas seguras (no causan problemas de inicialización)
import PromptsStatus from './PromptsStatus.vue'
import PromptEditor from './PromptEditor.vue'
import PromptPreview from './PromptPreview.vue'

// ===============================================================================
// PROPS - PRESERVADO ORIGINAL
// ===============================================================================
const props = defineProps({
  isActive: {
    type: Boolean,
    default: false
  }
})

// ===============================================================================
// ✅ NUEVO: ESTADO DE INICIALIZACIÓN SEGURA
// ===============================================================================
const componentsReady = ref(false)
const initializationError = ref(null)

// ✅ NUEVO: Estado reactivo local (independiente del composable hasta que esté listo)
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

// ✅ NUEVO: Referencia al composable (se inicializa después)
let promptsComposable = null

// ===============================================================================
// ✅ NUEVO: INICIALIZACIÓN SEGURA DEL COMPOSABLE
// ===============================================================================

const initializeComposable = async () => {
  try {
    console.log('[PromptsTab] Starting composable initialization...')
    
    // Esperar a que Vue esté completamente inicializado
    await nextTick()
    
    // ✅ IMPORTACIÓN DINÁMICA SEGURA - Evita acceso prematuro a stores
    const { usePrompts } = await import('@/composables/usePrompts')
    promptsComposable = usePrompts()
    
    // ✅ Verificar que el composable tenga todas las funciones necesarias
    if (!promptsComposable.loadPrompts || !promptsComposable.updatePrompt) {
      throw new Error('Composable methods not available')
    }

    // ✅ Sincronizar estado reactivo con el composable
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
// ✅ NUEVO: SINCRONIZACIÓN DE ESTADO CON COMPOSABLE
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
// ✅ NUEVO: FUNCIONES SEGURAS QUE VERIFICAN INICIALIZACIÓN
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
// HANDLERS CORREGIDOS - PRESERVADO ORIGINAL CON GUARDS DE SEGURIDAD
// ===============================================================================

/**
 * ✅ PRESERVADO: Handler para evento update de PromptEditor
 * ✅ CORREGIDO: Con guard de seguridad + sync
 */
const handlePromptUpdate = (updateData) => {
  if (!componentsReady.value || !promptsComposable) return

  try {
    if (typeof updateData === 'string') {
      // Compatibilidad con llamadas antiguas (solo agentName)
      promptsComposable.updatePrompt(updateData)
    } else {
      // ✅ FIX: Usar el nuevo formato con contenido
      promptsComposable.updatePrompt(updateData.agentName, updateData.content)
    }
    syncComposableState()
  } catch (error) {
    console.error('[PromptsTab] Error updating prompt:', error)
  }
}

/**
 * ✅ PRESERVADO: Handler para evento reset de PromptEditor  
 * ✅ CORREGIDO: Con guard de seguridad + sync
 */
const handlePromptReset = (agentName) => {
  if (!componentsReady.value || !promptsComposable) return

  try {
    promptsComposable.resetPrompt(agentName)
    syncComposableState()
  } catch (error) {
    console.error('[PromptsTab] Error resetting prompt:', error)
  }
}

/**
 * ✅ PRESERVADO: Handler para evento preview de PromptEditor
 * ✅ CORREGIDO: Con guard de seguridad + sync
 */
const handlePromptPreview = (agentName) => {
  if (!componentsReady.value || !promptsComposable) return

  try {
    promptsComposable.previewPrompt(agentName)
    syncComposableState()
  } catch (error) {
    console.error('[PromptsTab] Error previewing prompt:', error)
  }
}

/**
 * ✅ PRESERVADO: Close preview con guard
 */
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
// HANDLERS PARA EVENTOS DE PROMPTSSTATUS.VUE - PRESERVADO ORIGINAL
// ===============================================================================
const handleStatusLoaded = (status) => {
  console.log('Status loaded:', status)
  if (status?.postgresql_available && status?.tables_exist) {
    safeLoadPrompts()
  }
}

const handleMigrationComplete = () => {
  safeLoadPrompts()
}

// ===============================================================================
// WATCHERS - PRESERVADO ORIGINAL CON CORRECCIONES DE SEGURIDAD
// ===============================================================================

// ✅ PRESERVADO: Watch para activación del tab
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
// LIFECYCLE HOOKS - PRESERVADO ORIGINAL CON CORRECCIONES DE INICIALIZACIÓN
// ===============================================================================

onMounted(async () => {
  console.log('[PromptsTab] Component mounted, isActive:', props.isActive)
  
  // ✅ CORREGIDO: Inicialización diferida para evitar problemas de timing
  setTimeout(async () => {
    await initializeComposable()
  }, 100)
  
  // ✅ PRESERVADO: FUNCIONES GLOBALES EXACTAS DEL MONOLITO (solo las esenciales al inicio)
  if (typeof window !== 'undefined') {
    // Funciones básicas para compatibilidad inmediata
    window.loadCurrentPrompts = () => safeLoadPrompts()
    window.repairAllPrompts = () => safeRepairAllPrompts()
    window.exportPrompts = () => safeExportPrompts()
  }
})

onUnmounted(() => {
  console.log('[PromptsTab] Component unmounting, cleaning up...')

  // ✅ PRESERVADO: Limpiar TODAS las funciones globales
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
  }
})

// ===============================================================================
// ✅ NUEVO: CONFIGURACIÓN DIFERIDA DE FUNCIONES GLOBALES COMPLETAS
// ===============================================================================

// ✅ Configurar todas las funciones globales después de la inicialización
watch(componentsReady, (ready) => {
  if (ready && promptsComposable && typeof window !== 'undefined') {
    // ✅ PRESERVADO: EXPONER FUNCIONES GLOBALES EXACTAS DEL MONOLITO
    window.loadCurrentPrompts = () => safeLoadPrompts()
    window.updatePrompt = (agentName) => {
      if (promptsComposable) {
        promptsComposable.updatePrompt(agentName)
        syncComposableState()
      }
    }
    window.resetPrompt = (agentName) => {
      if (promptsComposable) {
        promptsComposable.resetPrompt(agentName) 
        syncComposableState()
      }
    }
    window.previewPrompt = (agentName) => {
      if (promptsComposable) {
        promptsComposable.previewPrompt(agentName)
        syncComposableState()
      }
    }
    window.repairAllPrompts = () => safeRepairAllPrompts()
    window.exportPrompts = () => safeExportPrompts()
    
    // ✅ PRESERVADO: Funciones debug faltantes (igual que el monolito)
    window.debugPrompts = () => {
      if (promptsComposable) {
        return promptsComposable.debugPrompts()
      }
    }
    window.testPromptEndpoints = () => {
      if (promptsComposable) {
        return promptsComposable.testEndpoints()
      }
    }
    
    // ✅ PRESERVADO: Instancia para debug (igual que el monolito)
    window.PromptsTabInstance = getCurrentInstance()
    
    console.log('[PromptsTab] ✅ All global functions configured')
  }
})
</script>

<style scoped>
/* ✅ PRESERVADO: Todos los estilos originales */
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

/* ✅ NUEVO: Estilos para inicialización */
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
