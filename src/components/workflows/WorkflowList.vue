<template>
  <div class="workflow-list">
    <!-- Loading state -->
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner">⏳</div>
      <p>Cargando workflows...</p>
    </div>
    
    <!-- Workflows grid -->
    <div v-else-if="workflows.length > 0" class="workflows-grid">
      <div
        v-for="workflow in workflows"
        :key="workflow.workflow_id"
        class="workflow-card"
        :class="{ 'workflow-disabled': !workflow.enabled }"
      >
        <!-- Workflow header -->
        <div class="workflow-header">
          <div class="workflow-icon">
            {{ getWorkflowIcon(workflow) }}
          </div>
          <div class="workflow-info">
            <h4 class="workflow-title" :title="workflow.name">
              {{ workflow.name }}
            </h4>
            <div class="workflow-meta">
              <span class="workflow-status" :class="{ 'status-enabled': workflow.enabled }">
                {{ workflow.enabled ? '✅ Activo' : '⏸️ Inactivo' }}
              </span>
              <span class="workflow-date">
                📅 {{ formatDate(workflow.created_at) }}
              </span>
            </div>
          </div>
        </div>
        
        <!-- Workflow description -->
        <div class="workflow-description">
          <p>{{ getDescription(workflow) }}</p>
        </div>
        
        <!-- Workflow stats -->
        <div class="workflow-stats">
          <div class="stat-item">
            <span class="stat-icon">🔢</span>
            <span class="stat-value">{{ workflow.total_nodes || 0 }}</span>
            <span class="stat-label">nodos</span>
          </div>
          <div class="stat-item">
            <span class="stat-icon">🔗</span>
            <span class="stat-value">{{ workflow.total_edges || 0 }}</span>
            <span class="stat-label">conexiones</span>
          </div>
          <div v-if="workflow.version" class="stat-item">
            <span class="stat-icon">📦</span>
            <span class="stat-value">v{{ workflow.version }}</span>
            <span class="stat-label">versión</span>
          </div>
        </div>
        
        <!-- Workflow tags -->
        <div v-if="workflow.tags && workflow.tags.length > 0" class="workflow-tags">
          <span
            v-for="tag in workflow.tags"
            :key="tag"
            class="tag"
          >
            #{{ tag }}
          </span>
        </div>
        
        <!-- Workflow actions -->
        <div class="workflow-actions">
          <button
            @click="$emit('view-workflow', workflow.workflow_id)"
            class="action-btn view-btn"
            title="Ver detalles"
          >
            👁️ Ver
          </button>
          
          <button
            v-if="workflow.enabled"
            @click="$emit('execute-workflow', workflow.workflow_id)"
            class="action-btn execute-btn"
            title="Ejecutar workflow"
          >
            ▶️ Ejecutar
          </button>
          
          <div class="dropdown">
            <button
              @click="toggleDropdown(workflow.workflow_id)"
              class="action-btn dropdown-toggle"
              title="Más acciones"
            >
              ⋮
            </button>
            
            <div
              v-show="activeDropdown === workflow.workflow_id"
              class="dropdown-menu"
              @click.stop
            >
              <button @click="handleToggleEnabled(workflow)" class="dropdown-item">
                {{ workflow.enabled ? '⏸️ Desactivar' : '▶️ Activar' }}
              </button>
              <button @click="handleEdit(workflow)" class="dropdown-item">
                ✏️ Editar
              </button>
              <button @click="handleDuplicate(workflow)" class="dropdown-item">
                📋 Duplicar
              </button>
              <button @click="handleExport(workflow)" class="dropdown-item">
                📥 Exportar
              </button>
              <div class="dropdown-divider"></div>
              <button @click="handleDelete(workflow)" class="dropdown-item danger">
                🗑️ Eliminar
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Empty state -->
    <div v-else class="empty-state">
      <div class="empty-icon">⚙️</div>
      <h4>No hay workflows disponibles</h4>
      <p>Los workflows que crees aparecerán aquí</p>
      <button @click="$emit('refresh')" class="btn-primary">
        🔄 Actualizar
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useNotifications } from '@/composables/useNotifications'

// ============================================================================
// PROPS & EMITS
// ============================================================================

const props = defineProps({
  workflows: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  'view-workflow',
  'execute-workflow',
  'edit-workflow',
  'delete-workflow',
  'toggle-enabled',
  'duplicate-workflow',
  'export-workflow',
  'refresh'
])

// ============================================================================
// COMPOSABLES
// ============================================================================

const { showNotification } = useNotifications()

// ============================================================================
// ESTADO LOCAL
// ============================================================================

const activeDropdown = ref(null)

// ============================================================================
// MÉTODOS PRINCIPALES
// ============================================================================

const toggleDropdown = (workflowId) => {
  activeDropdown.value = activeDropdown.value === workflowId ? null : workflowId
}

const closeDropdowns = () => {
  activeDropdown.value = null
}

const handleToggleEnabled = (workflow) => {
  emit('toggle-enabled', workflow.workflow_id)
  closeDropdowns()
}

const handleEdit = (workflow) => {
  emit('edit-workflow', workflow.workflow_id)
  closeDropdowns()
}

const handleDuplicate = (workflow) => {
  emit('duplicate-workflow', workflow.workflow_id)
  showNotification(`📋 Duplicando: ${workflow.name}`, 'info')
  closeDropdowns()
}

const handleExport = (workflow) => {
  emit('export-workflow', workflow.workflow_id)
  closeDropdowns()
}

const handleDelete = (workflow) => {
  const confirmed = confirm(`¿Estás seguro de que quieres eliminar "${workflow.name}"?`)
  
  if (confirmed) {
    emit('delete-workflow', workflow.workflow_id)
  }
  
  closeDropdowns()
}

// ============================================================================
// MÉTODOS DE UTILIDAD
// ============================================================================

const getWorkflowIcon = (workflow) => {
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

const getDescription = (workflow) => {
  if (workflow.description) {
    return workflow.description.length > 120
      ? workflow.description.substring(0, 120) + '...'
      : workflow.description
  }
  return 'Sin descripción'
}

const formatDate = (dateString) => {
  if (!dateString) return 'Fecha desconocida'
  
  try {
    const date = new Date(dateString)
    const now = new Date()
    const diffTime = Math.abs(now - date)
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
    
    if (diffDays === 0) return 'Hoy'
    if (diffDays === 1) return 'Ayer'
    if (diffDays < 7) return `Hace ${diffDays} días`
    if (diffDays < 30) return `Hace ${Math.floor(diffDays / 7)} semanas`
    
    return date.toLocaleDateString('es-ES', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    })
  } catch {
    return 'Fecha inválida'
  }
}

// ============================================================================
// LIFECYCLE HOOKS
// ============================================================================

onMounted(() => {
  // Close dropdowns when clicking outside
  document.addEventListener('click', closeDropdowns)
})

onUnmounted(() => {
  document.removeEventListener('click', closeDropdowns)
})
</script>

<style scoped>
.workflow-list {
  width: 100%;
}

.loading-state {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-secondary);
}

.loading-spinner {
  font-size: 2em;
  margin-bottom: 10px;
  animation: spin 1s linear infinite;
}

.workflows-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.workflow-card {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.workflow-card:hover {
  border-color: var(--primary-color);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.workflow-card.workflow-disabled {
  opacity: 0.6;
}

.workflow-header {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.workflow-icon {
  font-size: 2em;
  flex-shrink: 0;
}

.workflow-info {
  flex: 1;
  min-width: 0;
}

.workflow-title {
  margin: 0 0 6px 0;
  font-size: 1.1em;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workflow-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 0.85em;
}

.workflow-status {
  display: inline-block;
  color: var(--text-muted);
}

.workflow-status.status-enabled {
  color: var(--success-color);
}

.workflow-date {
  color: var(--text-muted);
}

.workflow-description {
  color: var(--text-secondary);
  font-size: 0.9em;
  line-height: 1.4;
}

.workflow-description p {
  margin: 0;
}

.workflow-stats {
  display: flex;
  gap: 15px;
  padding-top: 10px;
  border-top: 1px solid var(--border-color);
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.85em;
}

.stat-icon {
  font-size: 1em;
}

.stat-value {
  color: var(--text-primary);
  font-weight: 600;
}

.stat-label {
  color: var(--text-muted);
}

.workflow-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag {
  display: inline-block;
  padding: 3px 8px;
  background: rgba(102, 126, 234, 0.1);
  color: var(--primary-color);
  border-radius: 12px;
  font-size: 0.75em;
  font-weight: 500;
}

.workflow-actions {
  display: flex;
  gap: 8px;
  padding-top: 10px;
  border-top: 1px solid var(--border-color);
}

.action-btn {
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--bg-secondary);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 0.85em;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.action-btn:hover {
  background: var(--bg-primary);
  color: var(--text-primary);
}

.view-btn:hover {
  border-color: var(--info-color);
  color: var(--info-color);
}

.execute-btn:hover {
  border-color: var(--success-color);
  color: var(--success-color);
}

.dropdown {
  position: relative;
  margin-left: auto;
}

.dropdown-toggle {
  padding: 6px 8px;
  font-weight: bold;
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  right: 0;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  min-width: 150px;
  padding: 4px 0;
  margin-top: 4px;
}

.dropdown-item {
  width: 100%;
  padding: 8px 12px;
  border: none;
  background: none;
  color: var(--text-primary);
  cursor: pointer;
  font-size: 0.9em;
  text-align: left;
  transition: background-color 0.2s ease;
  display: flex;
  align-items: center;
  gap: 8px;
}

.dropdown-item:hover {
  background: var(--bg-tertiary);
}

.dropdown-item.danger {
  color: var(--danger-color);
}

.dropdown-item.danger:hover {
  background: rgba(239, 68, 68, 0.1);
}

.dropdown-divider {
  height: 1px;
  background: var(--border-color);
  margin: 4px 0;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-secondary);
}

.empty-icon {
  font-size: 4em;
  margin-bottom: 20px;
  opacity: 0.5;
}

.empty-state h4 {
  margin: 0 0 10px 0;
  color: var(--text-primary);
}

.empty-state p {
  margin: 0 0 20px 0;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s ease;
}

.btn-primary:hover {
  background: var(--primary-color-dark);
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Responsive */
@media (max-width: 768px) {
  .workflows-grid {
    grid-template-columns: 1fr;
  }
  
  .workflow-actions {
    flex-wrap: wrap;
  }
  
  .action-btn {
    flex: 1;
    min-width: 80px;
  }
  
  .dropdown {
    margin-left: 0;
  }
}
</style>
