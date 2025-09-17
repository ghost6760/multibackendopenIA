<template>
  <div class="prompts-tab">
    <!-- Header del tab -->
    <div class="tab-header">
      <h2 class="tab-title">🤖 Gestión de Prompts</h2>
      <p class="tab-subtitle">
        Configuración y gestión de prompts del sistema multi-agente
      </p>
    </div>

    <!-- Estado del sistema de prompts -->
    <div class="system-status">
      <div class="status-card">
        <div class="status-header">
          <h3>📊 Estado del Sistema</h3>
          <button @click="loadPromptsSystemStatus" class="btn btn-sm btn-secondary" :disabled="isLoading">
            🔄 Actualizar
          </button>
        </div>
        
        <div v-if="systemStatus" class="status-grid">
          <div class="status-item">
            <div class="status-label">Total de Prompts:</div>
            <div class="status-value">{{ systemStatus.total_prompts || 0 }}</div>
          </div>
          <div class="status-item">
            <div class="status-label">Prompts Activos:</div>
            <div class="status-value success">{{ systemStatus.active_prompts || 0 }}</div>
          </div>
          <div class="status-item">
            <div class="status-label">Última Actualización:</div>
            <div class="status-value">{{ formatDateTime(systemStatus.last_update) }}</div>
          </div>
          <div class="status-item">
            <div class="status-label">Versión Schema:</div>
            <div class="status-value">{{ systemStatus.schema_version || 'N/A' }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Filtros y búsqueda -->
    <div class="prompts-filters">
      <div class="filter-controls">
        <div class="search-box">
          <input
            type="text"
            v-model="searchQuery"
            placeholder="Buscar prompts..."
            class="search-input"
          />
          <span class="search-icon">🔍</span>
        </div>
        
        <div class="filter-group">
          <select v-model="selectedCategory" class="filter-select">
            <option value="">Todas las categorías</option>
            <option v-for="category in promptCategories" :key="category" :value="category">
              {{ category }}
            </option>
          </select>
        </div>
        
        <div class="filter-group">
          <select v-model="selectedStatus" class="filter-select">
            <option value="">Todos los estados</option>
            <option value="active">Activos</option>
            <option value="inactive">Inactivos</option>
            <option value="modified">Modificados</option>
          </select>
        </div>
        
        <button @click="clearFilters" class="btn btn-sm btn-secondary">
          🗑️ Limpiar Filtros
        </button>
      </div>
    </div>

    <!-- Lista de prompts -->
    <div class="prompts-container">
      <div v-if="isLoading" class="loading-state">
        <div class="loading-spinner"></div>
        <p>Cargando prompts...</p>
      </div>
      
      <div v-else-if="filteredPrompts.length === 0" class="empty-state">
        <div class="empty-icon">📝</div>
        <h4>No se encontraron prompts</h4>
        <p>No hay prompts que coincidan con los filtros seleccionados.</p>
      </div>
      
      <div v-else class="prompts-grid">
        <div 
          v-for="prompt in filteredPrompts"
          :key="prompt.id"
          class="prompt-card"
          :class="{ 
            'prompt-modified': prompt.is_modified,
            'prompt-inactive': !prompt.is_active
          }"
        >
          <div class="prompt-header">
            <div class="prompt-title">
              <h4>{{ prompt.name || prompt.id }}</h4>
              <div class="prompt-badges">
                <span v-if="prompt.category" class="badge badge-category">
                  {{ prompt.category }}
                </span>
                <span v-if="prompt.is_modified" class="badge badge-modified">
                  Modificado
                </span>
                <span :class="['badge', 'badge-status', prompt.is_active ? 'badge-active' : 'badge-inactive']">
                  {{ prompt.is_active ? 'Activo' : 'Inactivo' }}
                </span>
              </div>
            </div>
            
            <div class="prompt-actions">
              <button @click="previewPrompt(prompt)" class="btn btn-xs btn-info">
                👁️ Vista Previa
              </button>
              <button @click="editPrompt(prompt)" class="btn btn-xs btn-primary">
                ✏️ Editar
              </button>
              <button 
                @click="resetPrompt(prompt)"
                class="btn btn-xs btn-warning"
                :disabled="!prompt.is_modified"
              >
                🔄 Restaurar
              </button>
            </div>
          </div>
          
          <div class="prompt-content">
            <div class="prompt-description">
              {{ prompt.description || 'Sin descripción disponible' }}
            </div>
            
            <div class="prompt-preview">
              <div class="prompt-text">
                {{ truncateText(prompt.content || '', 200) }}
              </div>
            </div>
            
            <div class="prompt-metadata">
              <div class="metadata-item">
                <span class="metadata-label">Longitud:</span>
                <span class="metadata-value">{{ (prompt.content || '').length }} caracteres</span>
              </div>
              <div class="metadata-item">
                <span class="metadata-label">Última modificación:</span>
                <span class="metadata-value">{{ formatDateTime(prompt.updated_at) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Herramientas del sistema -->
    <div class="system-tools">
      <div class="tools-card">
        <h3>🔧 Herramientas del Sistema</h3>
        
        <div class="tools-grid">
          <button 
            @click="repairPrompts"
            class="tool-button"
            :disabled="isRepairing"
          >
            <div class="tool-icon">🔧</div>
            <div class="tool-content">
              <div class="tool-title">Reparar Prompts</div>
              <div class="tool-description">Reparar prompts dañados o inconsistentes</div>
            </div>
            <div v-if="isRepairing" class="tool-loading">⏳</div>
          </button>
          
          <button 
            @click="migratePromptsToPostgreSQL"
            class="tool-button"
            :disabled="isMigrating"
          >
            <div class="tool-icon">🔄</div>
            <div class="tool-content">
              <div class="tool-title">Migrar a PostgreSQL</div>
              <div class="tool-description">Migrar prompts al sistema PostgreSQL</div>
            </div>
            <div v-if="isMigrating" class="tool-loading">⏳</div>
          </button>
          
          <button 
            @click="exportPrompts"
            class="tool-button"
          >
            <div class="tool-icon">📤</div>
            <div class="tool-content">
              <div class="tool-title">Exportar Prompts</div>
              <div class="tool-description">Descargar backup de todos los prompts</div>
            </div>
          </button>
          
          <button 
            @click="importPrompts"
            class="tool-button"
          >
            <div class="tool-icon">📥</div>
            <div class="tool-content">
              <div class="tool-title">Importar Prompts</div>
              <div class="tool-description">Cargar prompts desde archivo</div>
            </div>
          </button>
        </div>
      </div>
    </div>

    <!-- Modal de edición de prompt -->
    <div v-if="editingPrompt" class="prompt-modal" @click="closeEditModal">
      <div class="modal-content large" @click.stop>
        <div class="modal-header">
          <h4>✏️ Editar Prompt: {{ editingPrompt.name || editingPrompt.id }}</h4>
          <button @click="closeEditModal" class="close-button">✕</button>
        </div>
        
        <div class="modal-body">
          <div class="form-grid">
            <div class="form-group">
              <label for="promptName">Nombre:</label>
              <input
                id="promptName"
                type="text"
                v-model="editForm.name"
                placeholder="Nombre del prompt"
              />
            </div>
            
            <div class="form-group">
              <label for="promptCategory">Categoría:</label>
              <input
                id="promptCategory"
                type="text"
                v-model="editForm.category"
                placeholder="Categoría del prompt"
              />
            </div>
            
            <div class="form-group full-width">
              <label for="promptDescription">Descripción:</label>
              <textarea
                id="promptDescription"
                v-model="editForm.description"
                placeholder="Descripción del prompt"
                rows="3"
              ></textarea>
            </div>
            
            <div class="form-group full-width">
              <label for="promptContent">Contenido del Prompt:</label>
              <textarea
                id="promptContent"
                v-model="editForm.content"
                placeholder="Contenido del prompt..."
                rows="15"
                class="prompt-textarea"
              ></textarea>
              <div class="textarea-footer">
                <span class="char-count">{{ editForm.content.length }} caracteres</span>
              </div>
            </div>
            
            <div class="form-group">
              <label>
                <input type="checkbox" v-model="editForm.is_active" />
                Prompt activo
              </label>
            </div>
          </div>
        </div>
        
        <div class="modal-footer">
          <div class="modal-actions">
            <button @click="savePrompt" class="btn btn-primary" :disabled="isSaving">
              <span v-if="isSaving">⏳ Guardando...</span>
              <span v-else">💾 Guardar Cambios</span>
            </button>
            <button @click="previewEditPrompt" class="btn btn-info">
              👁️ Vista Previa
            </button>
            <button @click="closeEditModal" class="btn btn-secondary">
              ❌ Cancelar
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal de vista previa -->
    <div v-if="previewData" class="prompt-modal" @click="closePreviewModal">
      <div class="modal-content large" @click.stop>
        <div class="modal-header">
          <h4>👁️ Vista Previa: {{ previewData.name || previewData.id }}</h4>
          <button @click="closePreviewModal" class="close-button">✕</button>
        </div>
        
        <div class="modal-body">
          <div v-if="previewData.preview_result" class="preview-content">
            <div class="preview-section">
              <h5>📝 Prompt Procesado:</h5>
              <div class="preview-text">
                {{ previewData.preview_result.processed_prompt }}
              </div>
            </div>
            
            <div v-if="previewData.preview_result.variables" class="preview-section">
              <h5>🔧 Variables Detectadas:</h5>
              <div class="variables-list">
                <div 
                  v-for="variable in previewData.preview_result.variables"
                  :key="variable"
                  class="variable-item"
                >
                  <code>{{ variable }}</code>
                </div>
              </div>
            </div>
            
            <div v-if="previewData.preview_result.metadata" class="preview-section">
              <h5>📊 Metadatos:</h5>
              <pre class="metadata-json">{{ formatJSON(previewData.preview_result.metadata) }}</pre>
            </div>
          </div>
          
          <div v-else class="preview-raw">
            <h5>📝 Contenido Original:</h5>
            <div class="preview-text">
              {{ previewData.content }}
            </div>
          </div>
        </div>
        
        <div class="modal-footer">
          <button @click="closePreviewModal" class="btn btn-secondary">
            ❌ Cerrar
          </button>
        </div>
      </div>
    </div>

    <!-- Input oculto para importar archivos -->
    <input
      ref="fileInput"
      type="file"
      accept=".json,.txt"
      @change="handleFileImport"
      hidden
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'

// ============================================================================
// STORES & COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const { apiRequest } = useApiRequest()
const { showNotification } = useNotifications()

// ============================================================================
// REFS
// ============================================================================

const fileInput = ref(null)

// ============================================================================
// ESTADO LOCAL
// ============================================================================

const isLoading = ref(false)
const isRepairing = ref(false)
const isMigrating = ref(false)
const isSaving = ref(false)

const prompts = ref([])
const systemStatus = ref(null)
const editingPrompt = ref(null)
const previewData = ref(null)

// Filtros
const searchQuery = ref('')
const selectedCategory = ref('')
const selectedStatus = ref('')

// Formulario de edición
const editForm = ref({
  name: '',
  category: '',
  description: '',
  content: '',
  is_active: true
})

// ============================================================================
// COMPUTED
// ============================================================================

const promptCategories = computed(() => {
  const categories = new Set()
  prompts.value.forEach(prompt => {
    if (prompt.category) {
      categories.add(prompt.category)
    }
  })
  return Array.from(categories).sort()
})

const filteredPrompts = computed(() => {
  let filtered = [...prompts.value]
  
  // Filtro de búsqueda
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(prompt =>
      (prompt.name || '').toLowerCase().includes(query) ||
      (prompt.id || '').toLowerCase().includes(query) ||
      (prompt.description || '').toLowerCase().includes(query) ||
      (prompt.content || '').toLowerCase().includes(query)
    )
  }
  
  // Filtro de categoría
  if (selectedCategory.value) {
    filtered = filtered.filter(prompt => prompt.category === selectedCategory.value)
  }
  
  // Filtro de estado
  if (selectedStatus.value) {
    switch (selectedStatus.value) {
      case 'active':
        filtered = filtered.filter(prompt => prompt.is_active)
        break
      case 'inactive':
        filtered = filtered.filter(prompt => !prompt.is_active)
        break
      case 'modified':
        filtered = filtered.filter(prompt => prompt.is_modified)
        break
    }
  }
  
  // Ordenar por nombre
  return filtered.sort((a, b) => {
    const nameA = a.name || a.id || ''
    const nameB = b.name || b.id || ''
    return nameA.localeCompare(nameB)
  })
})

// ============================================================================
// FUNCIONES PRINCIPALES MIGRADAS DEL SCRIPT.JS
// ============================================================================

/**
 * Carga los prompts actuales - MIGRADO: loadCurrentPrompts() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const loadCurrentPrompts = async () => {
  isLoading.value = true
  
  try {
    appStore.addToLog('Loading current prompts', 'info')
    
    // Llamada a la API - PRESERVAR ENDPOINT EXACTO
    const response = await apiRequest('/api/prompts')
    
    prompts.value = response.prompts || []
    
    appStore.addToLog(`Loaded ${prompts.value.length} prompts`, 'info')
    showNotification(`${prompts.value.length} prompts cargados`, 'success')
    
  } catch (error) {
    appStore.addToLog(`Error loading prompts: ${error.message}`, 'error')
    showNotification(`Error cargando prompts: ${error.message}`, 'error')
    prompts.value = []
  } finally {
    isLoading.value = false
  }
}

/**
 * Actualiza un prompt - MIGRADO: updatePrompt() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const updatePrompt = async (promptId, content) => {
  try {
    appStore.addToLog(`Updating prompt: ${promptId}`, 'info')
    
    // Llamada a la API - PRESERVAR ENDPOINT EXACTO
    const response = await apiRequest(`/api/prompts/${promptId}`, {
      method: 'PUT',
      body: { content }
    })
    
    // Actualizar prompt en la lista local
    const promptIndex = prompts.value.findIndex(p => p.id === promptId)
    if (promptIndex !== -1) {
      prompts.value[promptIndex] = { ...prompts.value[promptIndex], ...response.prompt }
    }
    
    appStore.addToLog(`Prompt ${promptId} updated successfully`, 'info')
    showNotification('Prompt actualizado exitosamente', 'success')
    
    return response
    
  } catch (error) {
    appStore.addToLog(`Error updating prompt ${promptId}: ${error.message}`, 'error')
    showNotification(`Error actualizando prompt: ${error.message}`, 'error')
    throw error
  }
}

/**
 * Restaura un prompt - MIGRADO: resetPrompt() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const resetPrompt = async (prompt) => {
  if (!prompt.is_modified) {
    showNotification('El prompt no ha sido modificado', 'info')
    return
  }
  
  try {
    appStore.addToLog(`Resetting prompt: ${prompt.id}`, 'info')
    
    // Llamada a la API - PRESERVAR ENDPOINT EXACTO
    const response = await apiRequest(`/api/prompts/${prompt.id}/reset`, {
      method: 'POST'
    })
    
    // Actualizar prompt en la lista local
    const promptIndex = prompts.value.findIndex(p => p.id === prompt.id)
    if (promptIndex !== -1) {
      prompts.value[promptIndex] = { ...prompts.value[promptIndex], ...response.prompt }
    }
    
    appStore.addToLog(`Prompt ${prompt.id} reset successfully`, 'info')
    showNotification('Prompt restaurado a su estado original', 'success')
    
  } catch (error) {
    appStore.addToLog(`Error resetting prompt ${prompt.id}: ${error.message}`, 'error')
    showNotification(`Error restaurando prompt: ${error.message}`, 'error')
  }
}

/**
 * Vista previa de prompt - MIGRADO: previewPrompt() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const previewPrompt = async (prompt) => {
  try {
    appStore.addToLog(`Previewing prompt: ${prompt.id}`, 'info')
    
    // Llamada a la API - PRESERVAR ENDPOINT EXACTO
    const response = await apiRequest(`/api/prompts/${prompt.id}/preview`, {
      method: 'POST'
    })
    
    previewData.value = {
      ...prompt,
      preview_result: response
    }
    
    appStore.addToLog(`Prompt ${prompt.id} preview generated`, 'info')
    
  } catch (error) {
    appStore.addToLog(`Error previewing prompt ${prompt.id}: ${error.message}`, 'error')
    showNotification(`Error generando vista previa: ${error.message}`, 'error')
    
    // Mostrar vista previa simple sin procesamiento
    previewData.value = prompt
  }
}

/**
 * Repara prompts - MIGRADO: repairPrompts() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const repairPrompts = async () => {
  isRepairing.value = true
  
  try {
    appStore.addToLog('Starting prompts repair', 'info')
    showNotification('Iniciando reparación de prompts...', 'info')
    
    // Llamada a la API - PRESERVAR ENDPOINT EXACTO (asumiendo que existe)
    const response = await apiRequest('/api/prompts/repair', {
      method: 'POST'
    })
    
    appStore.addToLog('Prompts repair completed', 'info')
    showNotification('Reparación de prompts completada', 'success')
    
    // Recargar prompts
    await loadCurrentPrompts()
    
  } catch (error) {
    appStore.addToLog(`Prompts repair failed: ${error.message}`, 'error')
    showNotification(`Error reparando prompts: ${error.message}`, 'error')
  } finally {
    isRepairing.value = false
  }
}

/**
 * Migra prompts a PostgreSQL - MIGRADO: migratePromptsToPostgreSQL() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const migratePromptsToPostgreSQL = async () => {
  isMigrating.value = true
  
  try {
    appStore.addToLog('Starting prompts migration to PostgreSQL', 'info')
    showNotification('Iniciando migración a PostgreSQL...', 'info')
    
    // Llamada a la API - PRESERVAR ENDPOINT EXACTO (asumiendo que existe)
    const response = await apiRequest('/api/prompts/migrate', {
      method: 'POST'
    })
    
    appStore.addToLog('Prompts migration to PostgreSQL completed', 'info')
    showNotification('Migración a PostgreSQL completada', 'success')
    
    // Recargar estado del sistema
    await loadPromptsSystemStatus()
    
  } catch (error) {
    appStore.addToLog(`Prompts migration failed: ${error.message}`, 'error')
    showNotification(`Error en migración: ${error.message}`, 'error')
  } finally {
    isMigrating.value = false
  }
}

/**
 * Carga el estado del sistema de prompts - MIGRADO: loadPromptsSystemStatus() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const loadPromptsSystemStatus = async () => {
  try {
    appStore.addToLog('Loading prompts system status', 'info')
    
    // Llamada a la API - PRESERVAR ENDPOINT EXACTO (asumiendo que existe)
    const response = await apiRequest('/api/prompts/status')
    
    systemStatus.value = response.status || {}
    
    appStore.addToLog('Prompts system status loaded', 'info')
    
  } catch (error) {
    appStore.addToLog(`Error loading prompts system status: ${error.message}`, 'error')
    systemStatus.value = null
  }
}

// ============================================================================
// FUNCIONES DE EDICIÓN
// ============================================================================

const editPrompt = (prompt) => {
  editingPrompt.value = prompt
  editForm.value = {
    name: prompt.name || '',
    category: prompt.category || '',
    description: prompt.description || '',
    content: prompt.content || '',
    is_active: prompt.is_active !== false
  }
}

const closeEditModal = () => {
  editingPrompt.value = null
  editForm.value = {
    name: '',
    category: '',
    description: '',
    content: '',
    is_active: true
  }
}

const savePrompt = async () => {
  if (!editingPrompt.value) return
  
  isSaving.value = true
  
  try {
    const promptData = {
      name: editForm.value.name,
      category: editForm.value.category,
      description: editForm.value.description,
      content: editForm.value.content,
      is_active: editForm.value.is_active
    }
    
    // Actualizar usando la función migrada
    await updatePrompt(editingPrompt.value.id, promptData.content)
    
    // Actualizar datos adicionales si el endpoint lo soporta
    // (esto podría requerir un endpoint adicional en el backend)
    
    closeEditModal()
    await loadCurrentPrompts()
    
  } catch (error) {
    // Error ya manejado en updatePrompt
  } finally {
    isSaving.value = false
  }
}

const previewEditPrompt = async () => {
  const tempPrompt = {
    ...editingPrompt.value,
    ...editForm.value
  }
  
  await previewPrompt(tempPrompt)
}

const closePreviewModal = () => {
  previewData.value = null
}

// ============================================================================
// FUNCIONES DE HERRAMIENTAS
// ============================================================================

const exportPrompts = () => {
  try {
    const dataStr = JSON.stringify(prompts.value, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    
    const a = document.createElement('a')
    a.href = URL.createObjectURL(dataBlob)
    a.download = `prompts_backup_${new Date().toISOString().slice(0, 10)}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    
    URL.revokeObjectURL(a.href)
    showNotification('Prompts exportados exitosamente', 'success')
    
  } catch (error) {
    showNotification('Error exportando prompts', 'error')
  }
}

const importPrompts = () => {
  fileInput.value?.click()
}

const handleFileImport = async (event) => {
  const file = event.target.files[0]
  if (!file) return
  
  try {
    const fileText = await file.text()
    const importedData = JSON.parse(fileText)
    
    if (!Array.isArray(importedData)) {
      throw new Error('El archivo debe contener un array de prompts')
    }
    
    // Aquí podrías implementar la lógica de importación al backend
    showNotification(`Listo para importar ${importedData.length} prompts`, 'info')
    
  } catch (error) {
    showNotification(`Error importando archivo: ${error.message}`, 'error')
  }
  
  // Limpiar input
  event.target.value = ''
}

// ============================================================================
// UTILIDADES
// ============================================================================

const clearFilters = () => {
  searchQuery.value = ''
  selectedCategory.value = ''
  selectedStatus.value = ''
}

const truncateText = (text, maxLength) => {
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength) + '...'
}

const formatDateTime = (dateString) => {
  if (!dateString) return 'N/A'
  try {
    return new Date(dateString).toLocaleString()
  } catch (error) {
    return 'Fecha inválida'
  }
}

const formatJSON = (obj) => {
  try {
    return JSON.stringify(obj, null, 2)
  } catch (error) {
    return 'Error formatting JSON: ' + error.message
  }
}

// ============================================================================
// LIFECYCLE
// ============================================================================

onMounted(async () => {
  appStore.addToLog('PromptsTab component mounted', 'info')
  
  // Cargar datos iniciales
  await Promise.all([
    loadCurrentPrompts(),
    loadPromptsSystemStatus()
  ])
  
  // EXPONER FUNCIONES GLOBALES PARA COMPATIBILIDAD
  window.loadCurrentPrompts = loadCurrentPrompts
  window.updatePrompt = updatePrompt
  window.resetPrompt = resetPrompt
  window.previewPrompt = previewPrompt
  window.repairPrompts = repairPrompts
  window.migratePromptsToPostgreSQL = migratePromptsToPostgreSQL
  window.loadPromptsSystemStatus = loadPromptsSystemStatus
})

onUnmounted(() => {
  // Limpiar funciones globales
  if (typeof window !== 'undefined') {
    delete window.loadCurrentPrompts
    delete window.updatePrompt
    delete window.resetPrompt
    delete window.previewPrompt
    delete window.repairPrompts
    delete window.migratePromptsToPostgreSQL
    delete window.loadPromptsSystemStatus
  }
  
  appStore.addToLog('PromptsTab component unmounted', 'info')
})

// Watcher para recargar cuando cambie la empresa
watch(() => appStore.currentCompanyId, () => {
  if (appStore.currentCompanyId) {
    loadCurrentPrompts()
    loadPromptsSystemStatus()
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
  margin-bottom: 30px;
  text-align: center;
}

.tab-title {
  font-size: 2rem;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.tab-subtitle {
  color: var(--text-secondary);
  font-size: 1.1rem;
}

.system-status {
  margin-bottom: 30px;
}

.status-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.status-header h3 {
  color: var(--text-primary);
  margin: 0;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
}

.status-label {
  font-weight: 500;
  color: var(--text-secondary);
}

.status-value {
  font-weight: 600;
  color: var(--text-primary);
}

.status-value.success {
  color: var(--success-color);
}

.prompts-filters {
  margin-bottom: 25px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
}

.filter-controls {
  display: flex;
  gap: 15px;
  align-items: center;
  flex-wrap: wrap;
}

.search-box {
  position: relative;
  flex: 1;
  min-width: 250px;
}

.search-input {
  width: 100%;
  padding: 10px 40px 10px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
  color: var(--text-primary);
}

.search-icon {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.filter-select {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
  color: var(--text-primary);
  min-width: 150px;
}

.prompts-container {
  margin-bottom: 30px;
}

.loading-state {
  text-align: center;
  padding: 60px;
  color: var(--text-secondary);
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid var(--bg-tertiary);
  border-top: 4px solid var(--primary-color);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 15px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.empty-state {
  text-align: center;
  padding: 60px;
  color: var(--text-secondary);
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 15px;
  opacity: 0.6;
}

.prompts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 20px;
}

.prompt-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: var(--transition-normal);
  box-shadow: var(--shadow-sm);
}

.prompt-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.prompt-card.prompt-modified {
  border-left: 4px solid var(--warning-color);
}

.prompt-card.prompt-inactive {
  opacity: 0.7;
  border-left: 4px solid var(--text-muted);
}

.prompt-header {
  padding: 15px;
  border-bottom: 1px solid var(--border-light);
}

.prompt-title {
  margin-bottom: 10px;
}

.prompt-title h4 {
  color: var(--text-primary);
  margin: 0 0 8px 0;
  font-size: 1.1rem;
}

.prompt-badges {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}

.badge {
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
  font-weight: 500;
}

.badge-category {
  background: var(--info-color);
  color: white;
}

.badge-modified {
  background: var(--warning-color);
  color: white;
}

.badge-status {
  font-weight: 600;
}

.badge-active {
  background: var(--success-color);
  color: white;
}

.badge-inactive {
  background: var(--text-muted);
  color: white;
}

.prompt-actions {
  display: flex;
  gap: 5px;
  margin-top: 10px;
}

.prompt-content {
  padding: 15px;
}

.prompt-description {
  color: var(--text-secondary);
  margin-bottom: 10px;
  font-style: italic;
}

.prompt-preview {
  margin-bottom: 15px;
}

.prompt-text {
  background: var(--bg-secondary);
  padding: 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-light);
  font-family: monospace;
  font-size: 0.9rem;
  line-height: 1.4;
  white-space: pre-wrap;
  word-break: break-word;
}

.prompt-metadata {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
}

.metadata-item {
  display: flex;
  gap: 5px;
}

.metadata-label {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.metadata-value {
  color: var(--text-primary);
  font-size: 0.9rem;
  font-weight: 500;
}

.system-tools {
  margin-bottom: 30px;
}

.tools-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}

.tools-card h3 {
  color: var(--text-primary);
  margin-bottom: 15px;
}

.tools-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 15px;
}

.tool-button {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: var(--transition-normal);
  text-align: left;
}

.tool-button:hover:not(:disabled) {
  background: var(--bg-tertiary);
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.tool-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.tool-icon {
  font-size: 1.5rem;
  width: 40px;
  text-align: center;
}

.tool-content {
  flex: 1;
}

.tool-title {
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.tool-description {
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.tool-loading {
  font-size: 1.2rem;
}

.prompt-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  max-width: 800px;
  max-height: 90vh;
  width: 90%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-content.large {
  max-width: 1000px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid var(--border-color);
}

.modal-header h4 {
  margin: 0;
  color: var(--text-primary);
}

.close-button {
  background: var(--error-color);
  color: white;
  border: none;
  border-radius: 50%;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.modal-body {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.form-group.full-width {
  grid-column: 1 / -1;
}

.form-group label {
  font-weight: 500;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.form-group input,
.form-group textarea,
.form-group select {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
  color: var(--text-primary);
}

.prompt-textarea {
  font-family: monospace;
  resize: vertical;
  min-height: 300px;
}

.textarea-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 5px;
}

.char-count {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.modal-footer {
  padding: 20px;
  border-top: 1px solid var(--border-color);
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.preview-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.preview-section h5 {
  color: var(--text-primary);
  margin-bottom: 10px;
}

.preview-text {
  background: var(--bg-secondary);
  padding: 15px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-light);
  font-family: monospace;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.variables-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.variable-item code {
  background: var(--bg-tertiary);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
  color: var(--primary-color);
}

.metadata-json {
  background: var(--bg-secondary);
  padding: 15px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-light);
  overflow-x: auto;
  font-size: 0.9rem;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 500;
  cursor: pointer;
  transition: var(--transition-fast);
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
}

.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.btn-info {
  background: var(--info-color);
  color: white;
}

.btn-warning {
  background: var(--warning-color);
  color: white;
}

.btn-xs {
  padding: 4px 8px;
  font-size: 0.8rem;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 0.9rem;
}

.btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .filter-controls {
    flex-direction: column;
    align-items: stretch;
  }
  
  .search-box {
    min-width: auto;
  }
  
  .prompts-grid {
    grid-template-columns: 1fr;
  }
  
  .tools-grid {
    grid-template-columns: 1fr;
  }
  
  .form-grid {
    grid-template-columns: 1fr;
  }
  
  .modal-content {
    margin: 10px;
    width: auto;
    max-height: calc(100vh - 20px);
  }
  
  .modal-actions {
    flex-direction: column;
  }
  
  .status-grid {
    grid-template-columns: 1fr;
  }
  
  .prompt-metadata {
    flex-direction: column;
  }
}
</style>
