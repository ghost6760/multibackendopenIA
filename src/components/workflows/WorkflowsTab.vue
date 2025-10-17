const activeSection = ref('chat')
const showEnabledOnly = ref(false)
const showDetailModal = ref(false)
const selectedWorkflow = ref(null)
const showExecutorModal = ref(false)
const workflowToExecute = ref(null)<template>
  <div class="tab-content" :class="{ 'active': isActive }" id="workflows">
    <!-- Company validation -->
    <div v-if="!appStore.hasCompanySelected" class="warning-message">
      <h3>⚠️ Empresa no seleccionada</h3>
      <p>Selecciona una empresa para gestionar sus workflows.</p>
      <button @click="highlightCompanySelector" class="btn-primary">
        🏢 Seleccionar Empresa
      </button>
    </div>
    
    <!-- Main content when company is selected -->
    <template v-else>
      <!-- Header con tabs de secciones -->
      <div class="workflows-header">
        <h2>⚙️ Workflows Automatizados</h2>
        <div class="section-tabs">
          <button 
            @click="activeSection = 'chat'"
            :class="['section-tab', { 'active': activeSection === 'chat' }]"
          >
            💬 Crear Workflow
          </button>
          <button 
            @click="activeSection = 'list'"
            :class="['section-tab', { 'active': activeSection === 'list' }]"
          >
            📋 Mis Workflows ({{ workflowsCount }})
          </button>
          <button 
            @click="activeSection = 'stats'"
            :class="['section-tab', { 'active': activeSection === 'stats' }]"
          >
            📊 Estadísticas
          </button>
        </div>
      </div>
      
      <!-- Section: Chat con ConfigAgent -->
      <div v-if="activeSection === 'chat'" class="section-content">
        <div class="grid grid-2">
          <!-- ConfigAgent Chat -->
          <div class="card">
            <ConfigAgentChat 
              @workflow-created="handleWorkflowCreated"
              @conversation-reset="handleConversationReset"
            />
          </div>
          
          <!-- Info/Help Card -->
          <div class="card">
            <h3>ℹ️ ¿Cómo funciona?</h3>
            <div class="info-content">
              <div class="info-step">
                <span class="step-number">1️⃣</span>
                <div class="step-text">
                  <strong>Describe tu workflow</strong>
                  <p>Dile al asistente qué quieres automatizar</p>
                </div>
              </div>
              
              <div class="info-step">
                <span class="step-number">2️⃣</span>
                <div class="step-text">
                  <strong>Responde preguntas</strong>
                  <p>El asistente te pedirá detalles específicos</p>
                </div>
              </div>
              
              <div class="info-step">
                <span class="step-number">3️⃣</span>
                <div class="step-text">
                  <strong>Revisa y aprueba</strong>
                  <p>Verifica el workflow generado antes de guardarlo</p>
                </div>
              </div>
              
              <div class="info-step">
                <span class="step-number">4️⃣</span>
                <div class="step-text">
                  <strong>¡Listo para usar!</strong>
                  <p>Tu workflow quedará guardado y activo</p>
                </div>
              </div>
            </div>
            
            <div class="examples-section">
              <h4>📌 Ejemplos de workflows:</h4>
              <ul class="examples-list">
                <li>✅ Responder consultas sobre tratamientos específicos (Botox, Ácido Hialurónico)</li>
                <li>✅ Agendar citas automáticamente</li>
                <li>✅ Manejar emergencias médicas</li>
                <li>✅ Enviar recordatorios de citas</li>
                <li>✅ Cotizaciones y consultas de precios</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Section: Lista de Workflows -->
      <div v-if="activeSection === 'list'" class="section-content">
        <div class="card">
          <div class="card-header">
            <h3>📋 Workflows Configurados</h3>
            <div class="card-actions">
              <button 
                @click="loadWorkflows()" 
                :disabled="isLoading"
                class="btn btn-secondary"
              >
                <span v-if="isLoading">⏳</span>
                <span v-else>🔄</span>
                Actualizar
              </button>
              
              <button 
                @click="activeSection = 'chat'"
                class="btn btn-primary"
              >
                ➕ Crear Workflow
              </button>
            </div>
          </div>
          
          <!-- Filters -->
          <div class="filters-bar">
            <div class="filter-group">
              <label>
                <input 
                  type="checkbox" 
                  v-model="showEnabledOnly"
                  @change="handleFilterChange"
                >
                Mostrar solo activos
              </label>
            </div>
          </div>
          
          <!-- Workflows List -->
          <WorkflowList
            v-if="hasWorkflows"
            :workflows="displayedWorkflows"
            :loading="isLoading"
            @view-workflow="handleViewWorkflow"
            @execute-workflow="handleExecuteWorkflow"
            @edit-workflow="handleEditWorkflow"
            @delete-workflow="handleDeleteWorkflow"
            @toggle-enabled="handleToggleEnabled"
            @refresh="loadWorkflows"
          />
          
          <div v-else-if="isLoading" class="loading-placeholder">
            <div class="loading-spinner">⏳</div>
            <p>Cargando workflows...</p>
          </div>
          
          <div v-else class="empty-state">
            <div class="empty-icon">⚙️</div>
            <h4>No hay workflows</h4>
            <p>
              {{ showEnabledOnly 
                ? 'No hay workflows activos. Activa algunos o desactiva el filtro.'
                : 'Aún no has creado ningún workflow.'
              }}
            </p>
            <button 
              @click="activeSection = 'chat'"
              class="btn-primary"
            >
              ➕ Crear primer workflow
            </button>
          </div>
        </div>
      </div>
      
      <!-- Section: Estadísticas -->
      <div v-if="activeSection === 'stats'" class="section-content">
        <div class="card">
          <div class="card-header">
            <h3>📊 Estadísticas de Workflows</h3>
            <button 
              @click="loadWorkflowStats()" 
              :disabled="isLoadingStats"
              class="btn btn-secondary"
            >
              <span v-if="isLoadingStats">⏳</span>
              <span v-else>🔄</span>
              Actualizar
            </button>
          </div>
          
          <!-- Loading state -->
          <div v-if="isLoadingStats" class="loading-placeholder">
            <div class="loading-spinner">⏳</div>
            <p>Cargando estadísticas...</p>
          </div>
          
          <!-- Stats content -->
          <div v-else-if="workflowStats" class="stats-grid">
            <div class="stat-card">
              <div class="stat-icon">📋</div>
              <div class="stat-info">
                <div class="stat-value">{{ workflowStats.total_workflows || 0 }}</div>
                <div class="stat-label">Total Workflows</div>
              </div>
            </div>
            
            <div class="stat-card">
              <div class="stat-icon">✅</div>
              <div class="stat-info">
                <div class="stat-value">{{ workflowStats.enabled_workflows || 0 }}</div>
                <div class="stat-label">Activos</div>
              </div>
            </div>
            
            <div class="stat-card">
              <div class="stat-icon">⏸️</div>
              <div class="stat-info">
                <div class="stat-value">{{ workflowStats.disabled_workflows || 0 }}</div>
                <div class="stat-label">Inactivos</div>
              </div>
            </div>
            
            <div class="stat-card">
              <div class="stat-icon">🔄</div>
              <div class="stat-info">
                <div class="stat-value">{{ workflowStats.total_executions || 0 }}</div>
                <div class="stat-label">Ejecuciones</div>
              </div>
            </div>
            
            <div class="stat-card">
              <div class="stat-icon">✅</div>
              <div class="stat-info">
                <div class="stat-value">{{ workflowStats.successful_executions || 0 }}</div>
                <div class="stat-label">Exitosas</div>
              </div>
            </div>
            
            <div class="stat-card">
              <div class="stat-icon">❌</div>
              <div class="stat-info">
                <div class="stat-value">{{ workflowStats.failed_executions || 0 }}</div>
                <div class="stat-label">Fallidas</div>
              </div>
            </div>
            
            <!-- Success rate -->
            <div v-if="workflowStats.success_rate !== undefined" class="stat-card stat-full">
              <div class="stat-icon">📈</div>
              <div class="stat-info">
                <div class="stat-value">{{ Math.round(workflowStats.success_rate * 100) }}%</div>
                <div class="stat-label">Tasa de Éxito</div>
              </div>
              <div class="stat-progress">
                <div 
                  class="stat-progress-bar" 
                  :style="{ width: `${workflowStats.success_rate * 100}%` }"
                ></div>
              </div>
            </div>
          </div>
          
          <!-- Error state -->
          <div v-else class="stats-error">
            <p>⚠️ No se pudieron cargar las estadísticas</p>
            <button @click="loadWorkflowStats()" class="btn btn-outline">
              🔄 Reintentar
            </button>
          </div>
        </div>
      </div>
    </template>
    
    <!-- Workflow Detail Modal -->
    <WorkflowDetailModal
      v-if="showDetailModal"
      :workflow="selectedWorkflow"
      :loading="isLoading"
      @close="closeDetailModal"
      @execute="handleExecuteFromModal"
      @edit="handleEditFromModal"
      @delete="handleDeleteFromModal"
    />
    
    <!-- Workflow Executor Modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div 
          v-if="showExecutorModal" 
          class="modal-overlay"
          @click="handleExecutorOverlayClick"
        >
          <div class="modal-container" @click.stop>
            <WorkflowExecutor
              :workflow="workflowToExecute"
              @close="closeExecutorModal"
              @executed="handleExecutionComplete"
            />
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useAppStore } from '@/stores/app'
import { useWorkflows } from '@/composables/useWorkflows'
import { useChatConversation } from '@/composables/useChatConversation'
import { useNotifications } from '@/composables/useNotifications'

// Componentes
import ConfigAgentChat from './ConfigAgentChat.vue'
import WorkflowList from './WorkflowList.vue'
import WorkflowDetailModal from './WorkflowDetailModal.vue'
import WorkflowExecutor from './WorkflowExecutor.vue'

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
// STORES Y COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const { showNotification } = useNotifications()

const {
  // Estado
  workflows,
  currentWorkflow,
  workflowStats,
  isLoading,
  isExecuting,
  isLoadingStats,
  hasWorkflows,
  workflowsCount,
  enabledWorkflows,
  disabledWorkflows,
  
  // Métodos
  loadWorkflows,
  getWorkflow,
  executeWorkflow,
  deleteWorkflow,
  toggleWorkflowEnabled,
  loadWorkflowStats,
  
  // Cleanup
  cleanup: cleanupWorkflows
} = useWorkflows()

const {
  cleanup: cleanupChat
} = useChatConversation()

// ============================================================================
// ESTADO LOCAL
// ============================================================================

const activeSection = ref('chat')
const showEnabledOnly = ref(false)
const showDetailModal = ref(false)
const selectedWorkflow = ref(null)

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const displayedWorkflows = computed(() => {
  return showEnabledOnly.value ? enabledWorkflows.value : workflows.value
})

// ============================================================================
// MÉTODOS PRINCIPALES
// ============================================================================

const handleWorkflowCreated = async (workflow) => {
  console.log('[WORKFLOWS-TAB] Workflow created:', workflow)
  showNotification('🎉 ¡Workflow creado exitosamente!', 'success', 5000)
  
  // Cambiar a lista
  activeSection.value = 'list'
  
  // Recargar workflows
  await loadWorkflows()
}

const handleConversationReset = () => {
  console.log('[WORKFLOWS-TAB] Conversation reset')
}

const handleFilterChange = async () => {
  await loadWorkflows(showEnabledOnly.value)
}

const handleViewWorkflow = async (workflowId) => {
  const workflow = await getWorkflow(workflowId)
  
  if (workflow) {
    selectedWorkflow.value = workflow
    showDetailModal.value = true
  }
}

const handleExecuteWorkflow = async (workflowId) => {
  const workflow = workflows.value.find(wf => wf.workflow_id === workflowId)
  
  if (!workflow) {
    showNotification('❌ Workflow no encontrado', 'error')
    return
  }
  
  // Abrir modal de executor
  workflowToExecute.value = workflow
  showExecutorModal.value = true
}

const closeExecutorModal = () => {
  showExecutorModal.value = false
  workflowToExecute.value = null
}

const handleExecutorOverlayClick = (event) => {
  if (event.target.classList.contains('modal-overlay')) {
    closeExecutorModal()
  }
}

const handleExecutionComplete = (result) => {
  console.log('[WORKFLOWS-TAB] Execution completed:', result)
  
  if (result.status === 'success') {
    showNotification('✅ Workflow ejecutado exitosamente', 'success', 5000)
  }
  
  // Opcional: cerrar modal después de ejecución exitosa
  // setTimeout(() => {
  //   closeExecutorModal()
  // }, 3000)
}

const handleEditWorkflow = (workflowId) => {
  showNotification('ℹ️ Edición de workflows próximamente', 'info')
  // TODO: Implementar editor de workflows
}

const handleDeleteWorkflow = async (workflowId) => {
  const success = await deleteWorkflow(workflowId)
  
  if (success) {
    // Si era el workflow mostrado en modal, cerrarlo
    if (selectedWorkflow.value?.id === workflowId) {
      closeDetailModal()
    }
  }
}

const handleToggleEnabled = async (workflowId) => {
  await toggleWorkflowEnabled(workflowId)
}

const closeDetailModal = () => {
  showDetailModal.value = false
  selectedWorkflow.value = null
}

const handleExecuteFromModal = (workflowId) => {
  closeDetailModal()
  handleExecuteWorkflow(workflowId)
}

const handleEditFromModal = (workflowId) => {
  closeDetailModal()
  handleEditWorkflow(workflowId)
}

const handleDeleteFromModal = async (workflowId) => {
  closeDetailModal()
  await handleDeleteWorkflow(workflowId)
}

const highlightCompanySelector = () => {
  window.dispatchEvent(new CustomEvent('highlightCompanySelector'))
}

// ============================================================================
// LIFECYCLE HOOKS
// ============================================================================

onMounted(async () => {
  appStore.addToLog('WorkflowsTab mounted', 'info')
  
  if (appStore.hasCompanySelected) {
    await loadWorkflows()
  }
})

onUnmounted(() => {
  console.log('[WORKFLOWS-TAB] Component unmounting, cleaning up')
  cleanupWorkflows()
  cleanupChat()
})

// ============================================================================
// WATCHERS
// ============================================================================

watch(() => appStore.currentCompanyId, async (newCompanyId) => {
  if (newCompanyId && props.isActive) {
    await loadWorkflows()
  }
})

watch(() => props.isActive, async (isActive) => {
  if (isActive && appStore.hasCompanySelected && workflows.value.length === 0) {
    await loadWorkflows()
  }
})
</script>

<style scoped>
.tab-content {
  display: none;
}

.tab-content.active {
  display: block;
}

.warning-message {
  text-align: center;
  padding: 40px 20px;
  background: var(--warning-bg);
  border: 1px solid var(--warning-color);
  border-radius: 8px;
  margin-bottom: 20px;
}

.warning-message h3 {
  color: var(--warning-color);
  margin: 0 0 10px 0;
}

/* Header */
.workflows-header {
  margin-bottom: 30px;
}

.workflows-header h2 {
  margin: 0 0 15px 0;
  color: var(--text-primary);
}

.section-tabs {
  display: flex;
  gap: 10px;
  border-bottom: 2px solid var(--border-color);
}

.section-tab {
  background: none;
  border: none;
  padding: 10px 20px;
  cursor: pointer;
  color: var(--text-secondary);
  font-weight: 500;
  transition: all 0.2s ease;
  border-bottom: 3px solid transparent;
  margin-bottom: -2px;
}

.section-tab:hover {
  color: var(--text-primary);
  background: var(--bg-tertiary);
}

.section-tab.active {
  color: var(--primary-color);
  border-bottom-color: var(--primary-color);
}

/* Section Content */
.section-content {
  margin-top: 20px;
}

/* Grid */
.grid {
  display: grid;
  gap: 20px;
  margin-bottom: 30px;
}

.grid-2 {
  grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
}

/* Card */
.card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 20px;
}

.card h3 {
  margin: 0 0 15px 0;
  color: var(--text-primary);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  flex-wrap: wrap;
  gap: 10px;
}

.card-actions {
  display: flex;
  gap: 10px;
}

/* Info Content */
.info-content {
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin-bottom: 20px;
}

.info-step {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.step-number {
  font-size: 1.5em;
  flex-shrink: 0;
}

.step-text strong {
  display: block;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.step-text p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.9em;
}

.examples-section {
  background: var(--bg-tertiary);
  padding: 15px;
  border-radius: 6px;
  margin-top: 15px;
}

.examples-section h4 {
  margin: 0 0 10px 0;
  color: var(--text-primary);
}

.examples-list {
  margin: 0;
  padding-left: 20px;
  color: var(--text-secondary);
  line-height: 1.8;
}

/* Filters */
.filters-bar {
  display: flex;
  gap: 15px;
  margin-bottom: 15px;
  padding: 10px;
  background: var(--bg-tertiary);
  border-radius: 6px;
}

.filter-group label {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: var(--text-secondary);
}

.filter-group input[type="checkbox"] {
  cursor: pointer;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.stat-card {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 15px;
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  border-color: var(--primary-color);
}

.stat-card.stat-full {
  grid-column: 1 / -1;
  flex-direction: column;
  align-items: stretch;
}

.stat-icon {
  font-size: 2em;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 2em;
  font-weight: 700;
  color: var(--primary-color);
  line-height: 1;
  margin-bottom: 5px;
}

.stat-label {
  font-size: 0.9em;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-progress {
  width: 100%;
  height: 8px;
  background: var(--bg-secondary);
  border-radius: 4px;
  overflow: hidden;
  margin-top: 10px;
}

.stat-progress-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-color), var(--success-color));
  transition: width 0.5s ease;
}

/* Loading & Empty States */
.loading-placeholder,
.empty-state,
.stats-error {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-secondary);
}

.loading-spinner {
  font-size: 2em;
  margin-bottom: 10px;
  animation: spin 1s linear infinite;
}

.empty-icon {
  font-size: 3em;
  margin-bottom: 15px;
  opacity: 0.5;
}

.empty-state h4,
.stats-error p {
  margin: 0 0 10px 0;
  color: var(--text-primary);
}

.empty-state p {
  margin: 0 0 20px 0;
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
  display: inline-flex;
  align-items: center;
  gap: 6px;
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
  .grid-2 {
    grid-template-columns: 1fr;
  }
  
  .section-tabs {
    flex-wrap: wrap;
  }
  
  .section-tab {
    flex: 1;
    min-width: 120px;
    text-align: center;
  }
  
  .card-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .card-actions {
    justify-content: stretch;
  }
  
  .card-actions .btn {
    flex: 1;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .modal-container {
    width: 95vw;
    max-height: 90vh;
  }
}

/* Modal Overlay para Executor */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 10000;
  padding: 20px;
  box-sizing: border-box;
}

.modal-container {
  max-width: 800px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

/* Modal Transitions */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .modal-container,
.modal-leave-active .modal-container {
  transition: transform 0.3s ease;
}

.modal-enter-from .modal-container,
.modal-leave-to .modal-container {
  transform: scale(0.95) translateY(-30px);
}
</style>
