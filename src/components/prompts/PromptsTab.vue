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

    <!-- Herramientas de administración -->
    <div class="admin-tools">
      <div class="tools-grid">
        <button @click="loadCurrentPrompts" class="btn btn-primary" :disabled="isLoading">
          {{ isLoading ? '🔄 Cargando...' : '📥 Cargar Prompts' }}
        </button>
        
        <button @click="repairPrompts" class="btn btn-warning" :disabled="isRepairing">
          {{ isRepairing ? '🔧 Reparando...' : '🔧 Reparar Prompts' }}
        </button>
        
        <button @click="migratePromptsToPostgreSQL" class="btn btn-info" :disabled="isMigrating">
          {{ isMigrating ? '🔄 Migrando...' : '🗄️ Migrar a PostgreSQL' }}
        </button>
        
        <button @click="exportPrompts" class="btn btn-secondary">
          📤 Exportar
        </button>
        
        <button @click="importPrompts" class="btn btn-secondary">
          📥 Importar
        </button>
      </div>
    </div>

    <!-- Lista de prompts -->
    <div class="prompts-container">
      <div v-if="isLoading" class="loading-state">
        <div class="loading-spinner"></div>
        <p>Cargando prompts...</p>
      </div>
      
      <div v-else-if="prompts.length === 0" class="empty-state">
        <p>No hay prompts configurados</p>
        <button @click="loadCurrentPrompts" class="btn btn-primary">
          🔄 Cargar Prompts
        </button>
      </div>
      
      <div v-else class="prompts-grid">
        <div v-for="prompt in prompts" :key="prompt.agent_name" class="prompt-card">
          <div class="prompt-header">
            <h4>{{ prompt.agent_name }}</h4>
            <div class="prompt-actions">
              <button @click="previewPrompt(prompt.agent_name)" class="btn btn-sm btn-info">
                👁️ Preview
              </button>
              <button @click="editPrompt(prompt)" class="btn btn-sm btn-primary">
                ✏️ Editar
              </button>
              <button @click="resetPrompt(prompt.agent_name)" class="btn btn-sm btn-warning">
                🔄 Reset
              </button>
            </div>
          </div>
          
          <div class="prompt-meta">
            <span class="prompt-status" :class="{ 'modified': prompt.is_custom }">
              {{ prompt.is_custom ? '✏️ Modificado' : '📄 Original' }}
            </span>
            <span class="prompt-version">v{{ prompt.version || '1.0' }}</span>
          </div>
          
          <div class="prompt-content">
            <textarea 
              :id="`prompt-${prompt.agent_name}`"
              v-model="prompt.content"
              @input="markAsModified(prompt)"
              class="prompt-textarea"
              rows="8"
              :placeholder="`Prompt para ${prompt.agent_name}...`"
            ></textarea>
          </div>
          
          <div class="prompt-footer">
            <button @click="updatePrompt(prompt.agent_name, prompt.content)" 
                    class="btn btn-success" 
                    :disabled="!prompt.isModified">
              💾 Guardar
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal de Preview -->
    <div v-if="previewData" class="modal-overlay" @click.self="closePreviewModal">
      <div class="modal-content preview-modal">
        <div class="modal-header">
          <h3>👁️ Vista Previa - {{ previewData.agent || 'Prompt' }}</h3>
          <button @click="closePreviewModal" class="btn-close">❌</button>
        </div>
        
        <div class="modal-body">
          <div v-if="previewData.preview" class="preview-response">
            <h5>🤖 Respuesta Generada:</h5>
            <div class="preview-text">
              {{ previewData.preview }}
            </div>
            
            <div v-if="previewData.debug_info" class="preview-debug">
              <h5>🔧 Información Técnica:</h5>
              <div class="info-grid">
                <span><strong>Método:</strong> {{ previewData.method || 'API' }}</span>
                <span><strong>Estado:</strong> {{ previewData.status }}</span>
                <span v-if="previewData.debug_info.response_length">
                  <strong>Longitud:</strong> {{ previewData.debug_info.response_length }} caracteres
                </span>
                <span v-if="previewData.debug_info.agent_key">
                  <strong>Agent Key:</strong> {{ previewData.debug_info.agent_key }}
                </span>
              </div>
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
            Cerrar
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
import { ref, onMounted, onUnmounted, watch } from 'vue'
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

const prompts = ref([])
const systemStatus = ref(null)
const previewData = ref(null)

// ============================================================================
// FUNCIONES PRINCIPALES MIGRADAS DEL SCRIPT.JS - ENDPOINTS CORREGIDOS
// ============================================================================

/**
 * Carga los prompts actuales - MIGRADO Y CORREGIDO: loadCurrentPrompts() de script.js
 * ENDPOINT CORREGIDO: /api/admin/prompts con company_id
 */
const loadCurrentPrompts = async () => {
  if (!appStore.currentCompanyId) {
    showNotification('Por favor selecciona una empresa primero', 'warning')
    return
  }

  isLoading.value = true
  
  try {
    appStore.addToLog('Loading current prompts', 'info')
    
    // ✅ ENDPOINT CORREGIDO - Igual que en script.js original
    const response = await apiRequest(`/api/admin/prompts?company_id=${appStore.currentCompanyId}`)
    
    // Procesar respuesta según el formato del script.js original
    if (response.prompts) {
      prompts.value = Object.entries(response.prompts).map(([agentName, data]) => ({
        agent_name: agentName,
        content: data.content || '',
        is_custom: data.is_custom || false,
        version: data.version || '1.0',
        isModified: false // Estado local para track de cambios
      }))
    } else {
      prompts.value = []
    }
    
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
 * Actualiza un prompt - MIGRADO Y CORREGIDO: updatePrompt() de script.js
 * ENDPOINT CORREGIDO: /api/admin/prompts/{agentName} con company_id
 */
const updatePrompt = async (agentName, content) => {
  if (!appStore.currentCompanyId) {
    showNotification('Por favor selecciona una empresa primero', 'warning')
    return
  }

  if (!content.trim()) {
    showNotification('El contenido del prompt no puede estar vacío', 'warning')
    return
  }

  try {
    appStore.addToLog(`Updating prompt for ${agentName}`, 'info')
    
    // ✅ ENDPOINT CORREGIDO - Igual que en script.js original
    const response = await apiRequest(`/api/admin/prompts/${agentName}?company_id=${appStore.currentCompanyId}`, {
      method: 'PUT',
      body: { content }
    })
    
    // Actualizar prompt en la lista local
    const promptIndex = prompts.value.findIndex(p => p.agent_name === agentName)
    if (promptIndex !== -1) {
      prompts.value[promptIndex].isModified = false
      prompts.value[promptIndex].is_custom = true
    }
    
    let successMessage = `Prompt de ${agentName} actualizado correctamente`
    if (response.version) {
      successMessage += ` (v${response.version})`
    }
    
    appStore.addToLog(`Prompt ${agentName} updated successfully`, 'info')
    showNotification(successMessage, 'success')
    
    // Recargar lista para sincronizar
    await loadCurrentPrompts()
    
  } catch (error) {
    appStore.addToLog(`Error updating prompt ${agentName}: ${error.message}`, 'error')
    showNotification(`Error actualizando prompt: ${error.message}`, 'error')
  }
}

/**
 * Restaura un prompt - MIGRADO Y CORREGIDO: resetPrompt() de script.js
 * ENDPOINT CORREGIDO: DELETE /api/admin/prompts/{agentName} con company_id
 */
const resetPrompt = async (agentName) => {
  if (!appStore.currentCompanyId) {
    showNotification('Por favor selecciona una empresa primero', 'warning')
    return
  }
  
  if (!confirm(`¿Estás seguro de restaurar el prompt por defecto para ${agentName}?`)) {
    return
  }
  
  try {
    appStore.addToLog(`Resetting prompt for ${agentName}`, 'info')
    
    // ✅ ENDPOINT CORREGIDO - Igual que en script.js original
    await apiRequest(`/api/admin/prompts/${agentName}?company_id=${appStore.currentCompanyId}`, {
      method: 'DELETE'
    })
    
    showNotification(`Prompt de ${agentName} restaurado al valor por defecto`, 'success')
    await loadCurrentPrompts()
    
  } catch (error) {
    appStore.addToLog(`Error resetting prompt ${agentName}: ${error.message}`, 'error')
    showNotification(`Error restaurando prompt: ${error.message}`, 'error')
  }
}

/**
 * Vista previa de prompt - MIGRADO Y CORREGIDO: previewPrompt() de script.js
 * ENDPOINT CORREGIDO: POST /api/admin/prompts/preview
 */
const previewPrompt = async (agentName) => {
  if (!appStore.currentCompanyId) {
    showNotification('Por favor selecciona una empresa primero', 'warning')
    return
  }

  const textarea = document.getElementById(`prompt-${agentName}`)
  if (!textarea) {
    showNotification(`Error: No se encontró el textarea para ${agentName}`, 'error')
    return
  }

  const promptTemplate = textarea.value.trim()
  const testMessage = prompt('Introduce un mensaje de prueba:', '¿Cuánto cuesta un tratamiento?')
  
  if (!testMessage) {
    showNotification('Operación cancelada', 'info')
    return
  }

  try {
    appStore.addToLog(`Generating preview for ${agentName}`, 'info')
    
    // ✅ ENDPOINT CORREGIDO - Igual que en script.js original
    const response = await apiRequest('/api/admin/prompts/preview', {
      method: 'POST',
      body: {
        agent_name: agentName,
        content: promptTemplate,
        test_message: testMessage
      }
    })
    
    previewData.value = {
      agent: agentName,
      content: promptTemplate,
      test_message: testMessage,
      ...response
    }
    
    appStore.addToLog(`Preview generated for ${agentName}`, 'info')
    
  } catch (error) {
    appStore.addToLog(`Error generating preview for ${agentName}: ${error.message}`, 'error')
    showNotification(`Error generando vista previa: ${error.message}`, 'error')
  }
}

/**
 * Repara prompts - MIGRADO: repairPrompts() de script.js
 */
const repairPrompts = async () => {
  isRepairing.value = true
  
  try {
    appStore.addToLog('Starting prompts repair', 'info')
    showNotification('Iniciando reparación de prompts...', 'info')
    
    const response = await apiRequest('/api/admin/prompts/repair', {
      method: 'POST'
    })
    
    appStore.addToLog('Prompts repair completed', 'info')
    showNotification('Reparación de prompts completada', 'success')
    
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
 */
const migratePromptsToPostgreSQL = async () => {
  isMigrating.value = true
  
  try {
    appStore.addToLog('Starting prompts migration to PostgreSQL', 'info')
    showNotification('Iniciando migración a PostgreSQL...', 'info')
    
    const response = await apiRequest('/api/admin/prompts/migrate', {
      method: 'POST'
    })
    
    appStore.addToLog('Prompts migration to PostgreSQL completed', 'info')
    showNotification('Migración a PostgreSQL completada', 'success')
    
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
 */
const loadPromptsSystemStatus = async () => {
  try {
    appStore.addToLog('Loading prompts system status', 'info')
    
    // ✅ ENDPOINT CORREGIDO - Usar /api/admin/status como en script.js
    const response = await apiRequest('/api/admin/status')
    
    // Buscar en response.prompt_system como en script.js original
    if (response && response.prompt_system) {
      systemStatus.value = response.prompt_system
    } else {
      systemStatus.value = response
    }
    
    appStore.addToLog('Prompts system status loaded', 'info')
    
  } catch (error) {
    appStore.addToLog(`Error loading prompts system status: ${error.message}`, 'error')
    systemStatus.value = null
  }
}

// ============================================================================
// FUNCIONES DE UTILIDAD
// ============================================================================

const markAsModified = (prompt) => {
  prompt.isModified = true
}

const editPrompt = (prompt) => {
  // Scroll al prompt y focus
  const textarea = document.getElementById(`prompt-${prompt.agent_name}`)
  if (textarea) {
    textarea.scrollIntoView({ behavior: 'smooth' })
    textarea.focus()
  }
}

const closePreviewModal = () => {
  previewData.value = null
}

const formatDateTime = (dateString) => {
  if (!dateString) return 'N/A'
  try {
    return new Date(dateString).toLocaleString()
  } catch (error) {
    return 'Fecha inválida'
  }
}

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
    
    showNotification(`Listo para importar ${importedData.length} prompts`, 'info')
    
  } catch (error) {
    showNotification(`Error importando archivo: ${error.message}`, 'error')
  }
  
  event.target.value = ''
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
  
  // ✅ EXPONER FUNCIONES GLOBALES PARA COMPATIBILIDAD - NOMBRES EXACTOS
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
watch(() => appStore.currentCompanyId, (newCompanyId) => {
  if (newCompanyId) {
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

.admin-tools {
  margin-bottom: 30px;
}

.tools-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
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
  margin: 0 auto 20px;
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

.prompts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
  gap: 20px;
}

.prompt-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}

.prompt-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.prompt-header h4 {
  color: var(--text-primary);
  margin: 0;
  font-size: 1.2rem;
}

.prompt-actions {
  display: flex;
  gap: 8px;
}

.prompt-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.prompt-status {
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
  background: var(--bg-secondary);
  color: var(--text-secondary);
}

.prompt-status.modified {
  background: var(--warning-light);
  color: var(--warning-color);
}

.prompt-version {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.prompt-content {
  margin-bottom: 15px;
}

.prompt-textarea {
  width: 100%;
  min-height: 200px;
  padding: 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
  line-height: 1.4;
  resize: vertical;
}

.prompt-textarea:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px var(--primary-light);
}

.prompt-footer {
  text-align: right;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  width: 90%;
  max-width: 800px;
  max-height: 90vh;
  overflow: hidden;
  box-shadow: var(--shadow-lg);
}

.preview-modal {
  max-width: 900px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid var(--border-color);
}

.modal-header h3 {
  margin: 0;
  color: var(--text-primary);
}

.btn-close {
  background: none;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  color: var(--text-secondary);
}

.btn-close:hover {
  color: var(--text-primary);
}

.modal-body {
  padding: 20px;
  max-height: 60vh;
  overflow-y: auto;
}

.modal-footer {
  padding: 20px;
  border-top: 1px solid var(--border-color);
  text-align: right;
}

.preview-response h5 {
  color: var(--text-primary);
  margin-bottom: 10px;
}

.preview-text {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 15px;
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
  line-height: 1.4;
  white-space: pre-wrap;
  color: var(--text-primary);
  margin-bottom: 20px;
}

.preview-debug {
  margin-top: 20px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 10px;
  margin-top: 10px;
}

.info-grid span {
  padding: 8px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
}

/* Button Styles */
.btn {
  padding: 8px 16px;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-weight: 500;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  transition: all 0.2s ease;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 0.8rem;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-dark);
}

.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-secondary);
}

.btn-success {
  background: var(--success-color);
  color: white;
}

.btn-success:hover:not(:disabled) {
  background: var(--success-dark);
}

.btn-warning {
  background: var(--warning-color);
  color: white;
}

.btn-warning:hover:not(:disabled) {
  background: var(--warning-dark);
}

.btn-info {
  background: var(--info-color);
  color: white;
}

.btn-info:hover:not(:disabled) {
  background: var(--info-dark);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* CSS Variables - Asumiendo que están definidas globalmente */
:root {
  --bg-primary: #ffffff;
  --bg-secondary: #f8f9fa;
  --bg-tertiary: #e9ecef;
  --text-primary: #212529;
  --text-secondary: #6c757d;
  --text-muted: #adb5bd;
  --border-color: #dee2e6;
  --primary-color: #007bff;
  --primary-dark: #0056b3;
  --primary-light: rgba(0, 123, 255, 0.25);
  --success-color: #28a745;
  --success-dark: #1e7e34;
  --warning-color: #ffc107;
  --warning-dark: #d39e00;
  --warning-light: rgba(255, 193, 7, 0.1);
  --info-color: #17a2b8;
  --info-dark: #117a8b;
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 4px 6px rgba(0, 0, 0, 0.1);
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  :root {
    --bg-primary: #1a1a1a;
    --bg-secondary: #2d2d2d;
    --bg-tertiary: #404040;
    --text-primary: #ffffff;
    --text-secondary: #adb5bd;
    --text-muted: #6c757d;
    --border-color: #404040;
  }
}
</style>
