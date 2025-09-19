# PromptsTab.vue
<template>
  <div class="prompts-tab" v-if="isActive">
    <!-- Header del Tab -->
    <div class="tab-header">
      <h2>🤖 Sistema de Prompts</h2>
      <p class="tab-description">
        Gestiona y personaliza los prompts de los agentes IA
      </p>
    </div>

    <!-- Estado del Sistema -->
    <PromptsStatus 
      @status-loaded="handleStatusLoaded"
      @migration-complete="handleMigrationComplete"
    />

    <!-- Loading State -->
    <div v-if="isLoading" class="loading-section">
      <div class="loading-spinner"></div>
      <p>Cargando sistema de prompts...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-section">
      <h3>❌ Error en el Sistema de Prompts</h3>
      <p>{{ error }}</p>
      <button @click="retryLoad" class="btn-retry">
        🔄 Reintentar Carga
      </button>
    </div>

    <!-- Main Content -->
    <div v-else-if="systemReady" class="prompts-content">
      
      <!-- Company & Agent Selector -->
      <div class="prompts-selector-section">
        <div class="selector-row">
          <div class="company-info">
            <h4>📢 Empresa Actual</h4>
            <p>{{ currentCompany?.name || currentCompanyId }}</p>
          </div>
          
          <div class="agent-selector">
            <label for="agent-select">🤖 Seleccionar Agente:</label>
            <select 
              id="agent-select"
              v-model="selectedAgent"
              @change="loadAgentPrompts"
              :disabled="isLoadingAgent"
            >
              <option value="">-- Selecciona un agente --</option>
              <option 
                v-for="agent in availableAgents" 
                :key="agent.name"
                :value="agent.name"
              >
                {{ agent.display_name || agent.name }}
                ({{ agent.status === 'active' ? '✅' : '❌' }})
              </option>
            </select>
          </div>
        </div>
      </div>

      <!-- Agent Prompts Management -->
      <div v-if="selectedAgent" class="agent-prompts-section">
        <div class="agent-header">
          <h3>🔧 Prompts para: {{ selectedAgent }}</h3>
          <div class="agent-actions">
            <button 
              @click="refreshAgentPrompts"
              :disabled="isLoadingAgent"
              class="btn-refresh"
            >
              <span v-if="isLoadingAgent">⏳</span>
              <span v-else>🔄</span>
              Actualizar
            </button>
            
            <button 
              @click="resetAllPrompts"
              :disabled="isLoadingAgent"
              class="btn-reset"
              title="Resetear todos los prompts a valores por defecto"
            >
              🔄 Reset All
            </button>
          </div>
        </div>

        <!-- Agent Prompt Editor -->
        <div v-if="currentPromptData" class="prompt-editor-section">
          <PromptEditor
            :promptData="currentPromptData"
            :placeholder="`Personaliza el prompt para el agente ${selectedAgent}...`"
            @update="handlePromptUpdate"
            @reset="handlePromptReset"
            @preview="handlePromptPreview"
            @change="handlePromptChange"
          />
        </div>

        <!-- Agent Status Info -->
        <div v-if="agentStatus" class="agent-status-info">
          <h4>📊 Estado del Agente</h4>
          <div class="status-grid">
            <div class="status-item">
              <span class="status-label">Estado:</span>
              <span :class="['status-value', agentStatus.active ? 'active' : 'inactive']">
                {{ agentStatus.active ? '🟢 Activo' : '🔴 Inactivo' }}
              </span>
            </div>
            <div class="status-item">
              <span class="status-label">Prompt Personalizado:</span>
              <span :class="['status-value', currentPromptData?.is_custom ? 'custom' : 'default']">
                {{ currentPromptData?.is_custom ? '✅ Sí' : '🔵 Por defecto' }}
              </span>
            </div>
            <div class="status-item" v-if="currentPromptData?.last_modified">
              <span class="status-label">Última Modificación:</span>
              <span class="status-value">
                {{ formatDateTime(currentPromptData.last_modified) }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- No Agent Selected -->
      <div v-else class="no-agent-section">
        <div class="no-agent-message">
          <h3>🤖 Selecciona un Agente</h3>
          <p>Elige un agente de la lista para ver y editar sus prompts</p>
        </div>
      </div>
    </div>

    <!-- Preview Modal -->
    <PromptPreview
      :visible="showPreview"
      :agentName="selectedAgent"
      :promptContent="previewPromptContent"
      :testMessage="previewTestMessage"
      :promptData="currentPromptData"
      @close="closePreview"
      @preview-complete="handlePreviewComplete"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'

// Components
import PromptsStatus from './PromptsStatus.vue'
import PromptEditor from './PromptEditor.vue'
import PromptPreview from './PromptPreview.vue'

// ============================================================================
// PROPS
// ============================================================================

const props = defineProps({
  isActive: {
    type: Boolean,
    default: false
  }
})

// ============================================================================
// COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const { apiRequest } = useApiRequest()
const { showNotification } = useNotifications()

// ============================================================================
// ESTADO REACTIVO
// ============================================================================

const isLoading = ref(false)
const isLoadingAgent = ref(false)
const error = ref(null)
const systemReady = ref(false)
const systemStatus = ref(null)

// Agent Management
const selectedAgent = ref('')
const availableAgents = ref([])
const currentPromptData = ref(null)
const agentStatus = ref(null)

// Preview Management
const showPreview = ref(false)
const previewPromptContent = ref('')
const previewTestMessage = ref('test')

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const currentCompany = computed(() => appStore.currentCompany)
const currentCompanyId = computed(() => appStore.currentCompanyId)

// ============================================================================
// FUNCIONES PRINCIPALES - MIGRADAS DESDE SCRIPT.JS
// ============================================================================

/**
 * Carga los agentes disponibles para la empresa actual
 * MIGRADO: loadAgents() de script.js
 */
const loadAvailableAgents = async () => {
  try {
    isLoading.value = true
    error.value = null
    
    appStore.addToLog('Loading available agents for prompts...', 'info')
    
    const response = await apiRequest('/api/prompts/agents')
    
    if (response.success) {
      availableAgents.value = response.agents || []
      appStore.addToLog(`Loaded ${availableAgents.value.length} agents`, 'info')
      
      // Auto-seleccionar el primer agente si hay alguno
      if (availableAgents.value.length > 0 && !selectedAgent.value) {
        selectedAgent.value = availableAgents.value[0].name
        await loadAgentPrompts()
      }
    } else {
      throw new Error(response.error || 'Error loading agents')
    }
    
  } catch (err) {
    error.value = `Error loading agents: ${err.message}`
    appStore.addToLog(error.value, 'error')
    showNotification(error.value, 'error')
  } finally {
    isLoading.value = false
  }
}

/**
 * Carga los prompts del agente seleccionado
 * MIGRADO: loadAgentPrompts() de script.js
 */
const loadAgentPrompts = async () => {
  if (!selectedAgent.value) {
    currentPromptData.value = null
    agentStatus.value = null
    return
  }
  
  try {
    isLoadingAgent.value = true
    
    appStore.addToLog(`Loading prompts for agent: ${selectedAgent.value}`, 'info')
    
    const response = await apiRequest(`/api/prompts/agent/${selectedAgent.value}`)
    
    if (response.success) {
      currentPromptData.value = response.prompt_data
      agentStatus.value = response.agent_status
      
      appStore.addToLog(`Prompts loaded for ${selectedAgent.value}`, 'info')
    } else {
      throw new Error(response.error || 'Error loading agent prompts')
    }
    
  } catch (err) {
    const errorMsg = `Error loading prompts for ${selectedAgent.value}: ${err.message}`
    appStore.addToLog(errorMsg, 'error')
    showNotification(errorMsg, 'error')
  } finally {
    isLoadingAgent.value = false
  }
}

/**
 * Actualiza un prompt del agente
 * MIGRADO: updateAgentPrompt() de script.js
 */
const handlePromptUpdate = async (promptData) => {
  try {
    appStore.addToLog(`Updating prompt for agent: ${selectedAgent.value}`, 'info')
    
    const response = await apiRequest(`/api/prompts/agent/${selectedAgent.value}`, {
      method: 'POST',
      body: {
        prompt_content: promptData.content,
        action: 'update'
      }
    })
    
    if (response.success) {
      currentPromptData.value = response.prompt_data
      showNotification(`Prompt actualizado para ${selectedAgent.value}`, 'success')
      appStore.addToLog(`Prompt updated successfully for ${selectedAgent.value}`, 'info')
    } else {
      throw new Error(response.error || 'Error updating prompt')
    }
    
  } catch (err) {
    const errorMsg = `Error updating prompt: ${err.message}`
    appStore.addToLog(errorMsg, 'error')
    showNotification(errorMsg, 'error')
  }
}

/**
 * Resetea un prompt a su valor por defecto
 * MIGRADO: resetAgentPrompt() de script.js
 */
const handlePromptReset = async () => {
  try {
    appStore.addToLog(`Resetting prompt for agent: ${selectedAgent.value}`, 'info')
    
    const response = await apiRequest(`/api/prompts/agent/${selectedAgent.value}`, {
      method: 'POST',
      body: {
        action: 'reset'
      }
    })
    
    if (response.success) {
      currentPromptData.value = response.prompt_data
      showNotification(`Prompt reseteado para ${selectedAgent.value}`, 'success')
      appStore.addToLog(`Prompt reset successfully for ${selectedAgent.value}`, 'info')
    } else {
      throw new Error(response.error || 'Error resetting prompt')
    }
    
  } catch (err) {
    const errorMsg = `Error resetting prompt: ${err.message}`
    appStore.addToLog(errorMsg, 'error')
    showNotification(errorMsg, 'error')
  }
}

/**
 * Muestra la vista previa del prompt
 * MIGRADO: showPromptPreview() de script.js
 */
const handlePromptPreview = (previewData) => {
  previewPromptContent.value = previewData.content
  previewTestMessage.value = previewData.testMessage || 'test'
  showPreview.value = true
}

/**
 * Maneja cambios en el prompt editor
 */
const handlePromptChange = (changeData) => {
  // Lógica adicional para manejar cambios si es necesario
  appStore.addToLog(`Prompt content changed for ${selectedAgent.value}`, 'debug')
}

/**
 * Refresca los prompts del agente actual
 */
const refreshAgentPrompts = async () => {
  if (selectedAgent.value) {
    await loadAgentPrompts()
  }
}

/**
 * Resetea todos los prompts
 */
const resetAllPrompts = async () => {
  if (!confirm('¿Estás seguro de que quieres resetear TODOS los prompts a sus valores por defecto?')) {
    return
  }
  
  try {
    appStore.addToLog('Resetting all prompts...', 'info')
    
    const response = await apiRequest('/api/prompts/reset-all', {
      method: 'POST'
    })
    
    if (response.success) {
      showNotification('Todos los prompts han sido reseteados', 'success')
      await loadAgentPrompts() // Recargar el agente actual
      appStore.addToLog('All prompts reset successfully', 'info')
    } else {
      throw new Error(response.error || 'Error resetting all prompts')
    }
    
  } catch (err) {
    const errorMsg = `Error resetting all prompts: ${err.message}`
    appStore.addToLog(errorMsg, 'error')
    showNotification(errorMsg, 'error')
  }
}

/**
 * Cierra el modal de preview
 */
const closePreview = () => {
  showPreview.value = false
  previewPromptContent.value = ''
  previewTestMessage.value = 'test'
}

/**
 * Maneja la finalización del preview
 */
const handlePreviewComplete = (previewResult) => {
  appStore.addToLog(`Preview completed for ${selectedAgent.value}`, 'info')
  // Lógica adicional si es necesario
}

/**
 * Maneja cuando el sistema de prompts está listo
 */
const handleStatusLoaded = (statusData) => {
  systemStatus.value = statusData
  systemReady.value = true
  
  if (statusData?.postgresql_available && statusData?.tables_exist) {
    loadAvailableAgents()
  }
}

/**
 * Maneja la finalización de migración
 */
const handleMigrationComplete = () => {
  systemReady.value = true
  loadAvailableAgents()
}

/**
 * Reintenta cargar el sistema
 */
const retryLoad = () => {
  error.value = null
  systemReady.value = false
  // El componente PromptsStatus se reiniciará automáticamente
}

/**
 * Formatea una fecha/hora
 */
const formatDateTime = (dateString) => {
  if (!dateString) return 'N/A'
  try {
    return new Date(dateString).toLocaleString()
  } catch {
    return 'Fecha inválida'
  }
}

// ============================================================================
// WATCHERS
// ============================================================================

// Recargar agentes cuando cambie la empresa
watch(() => appStore.currentCompanyId, async (newCompanyId) => {
  if (newCompanyId && systemReady.value) {
    selectedAgent.value = ''
    currentPromptData.value = null
    agentStatus.value = null
    await loadAvailableAgents()
  }
})

// Recargar cuando el tab se active
watch(() => props.isActive, async (isActive) => {
  if (isActive && systemReady.value && availableAgents.value.length === 0) {
    await loadAvailableAgents()
  }
})

// ============================================================================
// LIFECYCLE
// ============================================================================

onMounted(async () => {
  appStore.addToLog('PromptsTab component mounted', 'info')
  
  // Configurar listeners de eventos
  window.addEventListener('loadTabContent', handleLoadTabContent)
  
  // EXPONER FUNCIONES GLOBALES PARA COMPATIBILIDAD
  if (typeof window !== 'undefined') {
    window.loadPromptsTab = loadAvailableAgents
    window.refreshPromptsTab = refreshAgentPrompts
    window.resetAllPromptsTab = resetAllPrompts
    window.getSelectedAgent = () => selectedAgent.value
    window.setSelectedAgent = (agentName) => {
      selectedAgent.value = agentName
      loadAgentPrompts()
    }
  }
})

onUnmounted(() => {
  // Limpiar listeners
  window.removeEventListener('loadTabContent', handleLoadTabContent)
  
  // Limpiar funciones globales
  if (typeof window !== 'undefined') {
    delete window.loadPromptsTab
    delete window.refreshPromptsTab
    delete window.resetAllPromptsTab
    delete window.getSelectedAgent
    delete window.setSelectedAgent
  }
  
  appStore.addToLog('PromptsTab component unmounted', 'info')
})

// ============================================================================
// EVENT HANDLERS
// ============================================================================

const handleLoadTabContent = (event) => {
  if (event.detail?.tabName === 'prompts' && props.isActive) {
    if (systemReady.value) {
      loadAvailableAgents()
    }
  }
}
</script>

<style scoped>
/* ===== ESTILOS PARA PROMPTS TAB ===== */

.prompts-tab {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.tab-header {
  margin-bottom: 20px;
  text-align: center;
}

.tab-header h2 {
  margin: 0 0 8px 0;
  color: #2c3e50;
  font-size: 2em;
}

.tab-description {
  margin: 0;
  color: #6c757d;
  font-size: 1.1em;
}

/* Loading & Error States */
.loading-section, .error-section {
  text-align: center;
  padding: 40px 20px;
  background: #f8f9fa;
  border-radius: 8px;
  margin: 20px 0;
}

.loading-spinner {
  border: 4px solid #f3f3f3;
  border-top: 4px solid #007bff;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 2s linear infinite;
  margin: 0 auto 15px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-section h3 {
  color: #dc3545;
  margin-bottom: 10px;
}

.btn-retry {
  background-color: #17a2b8;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
  margin-top: 15px;
}

.btn-retry:hover {
  background-color: #117a8b;
}

/* Selector Section */
.prompts-selector-section {
  background: #fff;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}

.selector-row {
  display: flex;
  align-items: center;
  gap: 30px;
  flex-wrap: wrap;
}

.company-info h4 {
  margin: 0 0 5px 0;
  color: #495057;
  font-size: 1em;
}

.company-info p {
  margin: 0;
  font-weight: bold;
  color: #007bff;
  font-size: 1.1em;
}

.agent-selector {
  flex: 1;
  min-width: 300px;
}

.agent-selector label {
  display: block;
  margin-bottom: 8px;
  font-weight: bold;
  color: #495057;
}

.agent-selector select {
  width: 100%;
  padding: 10px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 1em;
  background-color: white;
}

.agent-selector select:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
}

/* Agent Prompts Section */
.agent-prompts-section {
  background: #fff;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}

.agent-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #dee2e6;
}

.agent-header h3 {
  margin: 0;
  color: #2c3e50;
}

.agent-actions {
  display: flex;
  gap: 10px;
}

.btn-refresh, .btn-reset {
  padding: 8px 15px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
  transition: all 0.3s ease;
}

.btn-refresh {
  background-color: #28a745;
  color: white;
}

.btn-refresh:hover:not(:disabled) {
  background-color: #218838;
}

.btn-reset {
  background-color: #ffc107;
  color: #212529;
}

.btn-reset:hover:not(:disabled) {
  background-color: #e0a800;
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Prompt Editor Section */
.prompt-editor-section {
  margin-bottom: 20px;
}

/* Agent Status Info */
.agent-status-info {
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  padding: 15px;
}

.agent-status-info h4 {
  margin: 0 0 15px 0;
  color: #495057;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 15px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
}

.status-label {
  font-weight: bold;
  color: #6c757d;
}

.status-value {
  font-weight: bold;
}

.status-value.active {
  color: #28a745;
}

.status-value.inactive {
  color: #dc3545;
}

.status-value.custom {
  color: #17a2b8;
}

.status-value.default {
  color: #6c757d;
}

/* No Agent Section */
.no-agent-section {
  text-align: center;
  padding: 60px 20px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 2px dashed #dee2e6;
}

.no-agent-message h3 {
  margin: 0 0 10px 0;
  color: #6c757d;
  font-size: 1.5em;
}

.no-agent-message p {
  margin: 0;
  color: #adb5bd;
  font-size: 1.1em;
}

/* Responsive Design */
@media (max-width: 768px) {
  .prompts-tab {
    padding: 15px;
  }
  
  .selector-row {
    flex-direction: column;
    align-items: stretch;
    gap: 15px;
  }
  
  .agent-header {
    flex-direction: column;
    align-items: stretch;
    gap: 15px;
  }
  
  .agent-actions {
    justify-content: stretch;
  }
  
  .agent-actions button {
    flex: 1;
  }
  
  .status-grid {
    grid-template-columns: 1fr;
  }
  
  .status-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 5px;
  }
}
</style>
