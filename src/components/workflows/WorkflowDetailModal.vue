<template>
  <Teleport to="body">
    <Transition name="modal">
      <div 
        v-if="show" 
        class="modal-overlay"
        @click="handleOverlayClick"
        @keydown.esc="$emit('close')"
      >
        <div 
          class="modal-content"
          @click.stop
          role="dialog"
          aria-modal="true"
        >
          <!-- Modal Header -->
          <div class="modal-header">
            <h3 class="modal-title">
              {{ getWorkflowIcon(workflow) }} {{ workflow?.name || 'Workflow' }}
            </h3>
            <button 
              @click="$emit('close')"
              class="modal-close-btn"
              aria-label="Cerrar modal"
            >
              ✕
            </button>
          </div>
          
          <!-- Modal Body -->
          <div class="modal-body">
            <!-- Loading State -->
            <div v-if="loading" class="modal-loading">
              <div class="loading-spinner">⏳</div>
              <p>Cargando detalles...</p>
            </div>
            
            <!-- Workflow Details -->
            <div v-else-if="workflow" class="workflow-details">
              <!-- Status Badge -->
              <div class="status-section">
                <span 
                  class="status-badge" 
                  :class="{ 'badge-enabled': workflow.enabled }"
                >
                  {{ workflow.enabled ? '✅ Activo' : '⏸️ Inactivo' }}
                </span>
                <span v-if="workflow.version" class="version-badge">
                  v{{ workflow.version }}
                </span>
              </div>
              
              <!-- Description -->
              <div v-if="workflow.description" class="detail-section">
                <h4>📝 Descripción</h4>
                <p>{{ workflow.description }}</p>
              </div>
              
              <!-- Metadata -->
              <div class="detail-section">
                <h4>ℹ️ Información</h4>
                <div class="metadata-grid">
                  <div class="metadata-item">
                    <span class="metadata-label">🆔 ID:</span>
                    <span class="metadata-value">{{ workflow.workflow_id || workflow.id }}</span>
                  </div>
                  <div class="metadata-item">
                    <span class="metadata-label">🏢 Empresa:</span>
                    <span class="metadata-value">{{ workflow.company_id }}</span>
                  </div>
                  <div class="metadata-item">
                    <span class="metadata-label">📅 Creado:</span>
                    <span class="metadata-value">{{ formatDate(workflow.created_at) }}</span>
                  </div>
                  <div v-if="workflow.updated_at" class="metadata-item">
                    <span class="metadata-label">✏️ Actualizado:</span>
                    <span class="metadata-value">{{ formatDate(workflow.updated_at) }}</span>
                  </div>
                </div>
              </div>
              
              <!-- Structure -->
              <div class="detail-section">
                <h4>🔧 Estructura</h4>
                <div class="structure-stats">
                  <div class="structure-item">
                    <span class="structure-icon">🔢</span>
                    <span class="structure-value">{{ workflow.total_nodes || 0 }}</span>
                    <span class="structure-label">Nodos</span>
                  </div>
                  <div class="structure-item">
                    <span class="structure-icon">🔗</span>
                    <span class="structure-value">{{ workflow.total_edges || 0 }}</span>
                    <span class="structure-label">Conexiones</span>
                  </div>
                </div>
              </div>
              
              <!-- Nodes List -->
              <div v-if="hasNodes" class="detail-section">
                <h4>📋 Flujo del Workflow</h4>
                <div class="nodes-list">
                  <div 
                    v-for="(node, index) in workflowNodes" 
                    :key="node.id"
                    class="node-item"
                  >
                    <span class="node-number">{{ index + 1 }}</span>
                    <span class="node-icon">{{ getNodeIcon(node.type) }}</span>
                    <div class="node-info">
                      <span class="node-name">{{ node.name }}</span>
                      <span class="node-type">{{ node.type }}</span>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- Tags -->
              <div v-if="workflow.tags && workflow.tags.length > 0" class="detail-section">
                <h4>🏷️ Tags</h4>
                <div class="tags-list">
                  <span
                    v-for="tag in workflow.tags"
                    :key="tag"
                    class="tag"
                  >
                    #{{ tag }}
                  </span>
                </div>
              </div>
              
              <!-- Execution Summary (if available) -->
              <div v-if="hasExecutionSummary" class="detail-section">
                <h4>📊 Historial de Ejecuciones</h4>
                <div class="execution-summary">
                  <div class="summary-item">
                    <span class="summary-icon">🔄</span>
                    <span class="summary-value">{{ executionSummary.total || 0 }}</span>
                    <span class="summary-label">Total</span>
                  </div>
                  <div class="summary-item">
                    <span class="summary-icon">✅</span>
                    <span class="summary-value">{{ executionSummary.successful || 0 }}</span>
                    <span class="summary-label">Exitosas</span>
                  </div>
                  <div class="summary-item">
                    <span class="summary-icon">❌</span>
                    <span class="summary-value">{{ executionSummary.failed || 0 }}</span>
                    <span class="summary-label">Fallidas</span>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Empty State -->
            <div v-else class="modal-empty">
              <div class="empty-icon">⚙️</div>
              <p>No hay información del workflow</p>
            </div>
          </div>
          
          <!-- Modal Footer -->
          <div v-if="workflow" class="modal-footer">
            <div class="footer-left">
              <span class="workflow-path">
                🏢 {{ workflow.company_id }} / ⚙️ {{ workflow.name }}
              </span>
            </div>
            
            <div class="footer-right">
              <button 
                v-if="workflow.enabled"
                @click="$emit('execute', workflow.workflow_id || workflow.id)"
                class="footer-btn execute-btn"
              >
                ▶️ Ejecutar
              </button>
              <button 
                @click="$emit('edit', workflow.workflow_id || workflow.id)"
                class="footer-btn edit-btn"
              >
                ✏️ Editar
              </button>
              <button 
                @click="$emit('delete', workflow.workflow_id || workflow.id)"
                class="footer-btn delete-btn"
              >
                🗑️ Eliminar
              </button>
              <button 
                @click="$emit('close')"
                class="footer-btn close-btn"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, watch, onMounted, onUnmounted } from 'vue'

// ============================================================================
// PROPS & EMITS
// ============================================================================

const props = defineProps({
  workflow: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  'close',
  'execute',
  'edit',
  'delete'
])

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const show = computed(() => !!props.workflow)

const hasNodes = computed(() => {
  if (!props.workflow) return false
  
  const nodes = props.workflow.nodes
  if (Array.isArray(nodes)) return nodes.length > 0
  if (typeof nodes === 'object' && nodes !== null) {
    return Object.keys(nodes).length > 0
  }
  
  return false
})

const workflowNodes = computed(() => {
  if (!props.workflow?.nodes) return []
  
  if (Array.isArray(props.workflow.nodes)) {
    return props.workflow.nodes
  }
  
  if (typeof props.workflow.nodes === 'object') {
    return Object.values(props.workflow.nodes)
  }
  
  return []
})

const hasExecutionSummary = computed(() => {
  return props.workflow?.execution_summary || 
         props.workflow?.executions_count !== undefined
})

const executionSummary = computed(() => {
  if (props.workflow?.execution_summary) {
    return props.workflow.execution_summary
  }
  
  return {
    total: props.workflow?.executions_count || 0,
    successful: props.workflow?.successful_executions || 0,
    failed: props.workflow?.failed_executions || 0
  }
})

// ============================================================================
// MÉTODOS
// ============================================================================

const handleOverlayClick = (event) => {
  if (event.target.classList.contains('modal-overlay')) {
    emit('close')
  }
}

const getWorkflowIcon = (workflow) => {
  if (!workflow) return '⚙️'
  
  // Por tags
  if (workflow.tags?.includes('sales')) return '💰'
  if (workflow.tags?.includes('support')) return '🆘'
  if (workflow.tags?.includes('emergency')) return '🚨'
  if (workflow.tags?.includes('schedule')) return '📅'
  
  // Por nombre
  const name = workflow.name?.toLowerCase() || ''
  if (name.includes('bot')) return '💉'
  if (name.includes('schedule') || name.includes('agenda')) return '📅'
  if (name.includes('emergency') || name.includes('emergencia')) return '🚨'
  if (name.includes('sales') || name.includes('venta')) return '💰'
  
  return '⚙️'
}

const getNodeIcon = (type) => {
  const icons = {
    'trigger': '🎯',
    'agent': '🤖',
    'tool': '🔧',
    'condition': '❓',
    'end': '🏁',
    'action': '⚡',
    'decision': '🔀'
  }
  
  return icons[type?.toLowerCase()] || '📌'
}

const formatDate = (dateString) => {
  if (!dateString) return 'Desconocida'
  
  try {
    const date = new Date(dateString)
    return date.toLocaleDateString('es-ES', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return 'Fecha inválida'
  }
}

// ============================================================================
// LIFECYCLE HOOKS
// ============================================================================

watch(() => show.value, (isShown) => {
  if (isShown) {
    document.body.style.overflow = 'hidden'
  } else {
    document.body.style.overflow = ''
  }
})

onUnmounted(() => {
  document.body.style.overflow = ''
})
</script>

<style scoped>
/* Modal Overlay */
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

.modal-content {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  max-width: 800px;
  width: 100%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Modal Header */
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 25px;
  border-bottom: 1px solid #eee;
  background: #f8f9fa;
  border-radius: 12px 12px 0 0;
}

.modal-title {
  margin: 0;
  color: #333;
  font-size: 1.3em;
  font-weight: 600;
  word-wrap: break-word;
  flex: 1;
  padding-right: 20px;
}

.modal-close-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: #666;
  cursor: pointer;
  padding: 5px;
  border-radius: 4px;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.modal-close-btn:hover {
  background: #dc3545;
  color: white;
}

/* Modal Body */
.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 25px;
}

.modal-loading,
.modal-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
  color: #666;
}

.loading-spinner {
  font-size: 2em;
  margin-bottom: 15px;
  animation: spin 1s linear infinite;
}

.empty-icon {
  font-size: 3em;
  margin-bottom: 15px;
  opacity: 0.5;
}

/* Workflow Details */
.workflow-details {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.status-section {
  display: flex;
  gap: 10px;
  align-items: center;
}

.status-badge {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 0.9em;
  font-weight: 500;
  background: #e5e7eb;
  color: #6b7280;
}

.status-badge.badge-enabled {
  background: rgba(34, 197, 94, 0.1);
  color: #22c55e;
}

.version-badge {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 0.85em;
  font-weight: 500;
  background: rgba(102, 126, 234, 0.1);
  color: #667eea;
}

.detail-section {
  background: #f9f9f9;
  border-radius: 8px;
  padding: 15px;
  border-left: 4px solid #667eea;
}

.detail-section h4 {
  margin: 0 0 12px 0;
  color: #333;
  font-size: 1em;
}

.detail-section p {
  margin: 0;
  color: #666;
  line-height: 1.5;
}

/* Metadata Grid */
.metadata-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.metadata-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metadata-label {
  font-size: 0.85em;
  color: #666;
  font-weight: 500;
}

.metadata-value {
  color: #333;
  font-weight: 600;
  word-break: break-word;
  font-family: monospace;
  font-size: 0.9em;
}

/* Structure Stats */
.structure-stats {
  display: flex;
  gap: 20px;
}

.structure-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 10px;
  background: white;
  border-radius: 8px;
  flex: 1;
}

.structure-icon {
  font-size: 1.5em;
}

.structure-value {
  font-size: 1.5em;
  font-weight: 700;
  color: #667eea;
}

.structure-label {
  font-size: 0.85em;
  color: #666;
}

/* Nodes List */
.nodes-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.node-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  background: white;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
}

.node-number {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: #667eea;
  color: white;
  border-radius: 50%;
  font-size: 0.85em;
  font-weight: 600;
  flex-shrink: 0;
}

.node-icon {
  font-size: 1.3em;
  flex-shrink: 0;
}

.node-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
}

.node-name {
  color: #333;
  font-weight: 500;
}

.node-type {
  font-size: 0.8em;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Tags */
.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag {
  display: inline-block;
  padding: 4px 10px;
  background: rgba(102, 126, 234, 0.1);
  color: #667eea;
  border-radius: 16px;
  font-size: 0.85em;
  font-weight: 500;
}

/* Execution Summary */
.execution-summary {
  display: flex;
  gap: 15px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px;
  background: white;
  border-radius: 8px;
  flex: 1;
}

.summary-icon {
  font-size: 1.5em;
}

.summary-value {
  font-size: 1.5em;
  font-weight: 700;
  color: #667eea;
}

.summary-label {
  font-size: 0.85em;
  color: #666;
}

/* Modal Footer */
.modal-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 25px;
  border-top: 1px solid #eee;
  background: #f8f9fa;
  border-radius: 0 0 12px 12px;
  gap: 15px;
  flex-wrap: wrap;
}

.footer-left {
  flex: 1;
  min-width: 0;
}

.workflow-path {
  font-size: 0.85em;
  color: #666;
  font-family: monospace;
  word-wrap: break-word;
}

.footer-right {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
  flex-wrap: wrap;
}

.footer-btn {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
  color: #666;
  cursor: pointer;
  font-size: 0.85em;
  font-weight: 500;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.footer-btn:hover {
  background: #f8f9fa;
  color: #333;
}

.execute-btn:hover {
  border-color: #22c55e;
  color: #22c55e;
}

.edit-btn:hover {
  border-color: #f59e0b;
  color: #f59e0b;
}

.delete-btn:hover {
  border-color: #dc3545;
  color: #dc3545;
}

.close-btn:hover {
  border-color: #667eea;
  color: #667eea;
}

/* Transitions */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .modal-content,
.modal-leave-active .modal-content {
  transition: transform 0.3s ease;
}

.modal-enter-from .modal-content,
.modal-leave-to .modal-content {
  transform: scale(0.95) translateY(-30px);
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Responsive */
@media (max-width: 768px) {
  .modal-content {
    width: 95vw;
    margin: 10px;
  }
  
  .modal-header {
    padding: 15px;
  }
  
  .modal-body {
    padding: 15px;
  }
  
  .modal-footer {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
    padding: 15px;
  }
  
  .footer-right {
    justify-content: stretch;
  }
  
  .footer-btn {
    flex: 1;
    text-align: center;
  }
  
  .metadata-grid {
    grid-template-columns: 1fr;
  }
  
  .structure-stats,
  .execution-summary {
    flex-direction: column;
  }
}

@media (max-width: 480px) {
  .modal-content {
    margin: 5px;
  }
  
  .modal-title {
    font-size: 1.1em;
  }
  
  .nodes-list {
    gap: 6px;
  }
  
  .node-item {
    padding: 8px;
  }
}
</style>
