<template>
  <div class="prompts-tab">
    <!-- Header con filtros y acciones -->
    <div class="prompts-header">
      <div class="header-title">
        <h2>📝 Gestión de Prompts</h2>
        <p class="subtitle">Administra y personaliza los prompts de los agentes de IA</p>
      </div>
      
      <div class="header-actions">
        <button 
          @click="loadCurrentPrompts" 
          :disabled="isLoading"
          class="btn btn-primary"
        >
          <span v-if="isLoading">⏳ Cargando...</span>
          <span v-else>🔄 Recargar</span>
        </button>
        
        <button 
          @click="repairPrompts" 
          :disabled="isRepairing"
          class="btn btn-warning"
        >
          <span v-if="isRepairing">⏳ Reparando...</span>
          <span v-else>🔧 Reparar</span>
        </button>
        
        <button 
          @click="exportPrompts" 
          class="btn btn-info"
        >
          📥 Exportar
        </button>
        
        <button 
          @click="importPrompts" 
          class="btn btn-secondary"
        >
          📤 Importar
        </button>
      </div>
    </div>

    <!-- Filtros -->
    <div class="prompts-filters">
      <div class="filter-group">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="🔍 Buscar prompts..."
          class="filter-input"
        />
        
        <select v-model="selectedCategory" class="filter-select">
          <option value="">Todas las categorías</option>
          <option v-for="category in promptCategories" :key="category" :value="category">
            {{ category }}
          </option>
        </select>
        
        <select v-model="selectedStatus" class="filter-select">
          <option value="">Todos los estados</option>
          <option value="custom">Personalizados</option>
          <option value="default">Por defecto</option>
          <option value="modified">Modificados</option>
        </select>
        
        <button @click="clearFilters" class="btn btn-sm">❌ Limpiar</button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading && !hasPrompts" class="loading-container">
      <div class="loading-spinner"></div>
      <p>Cargando prompts...</p>
    </div>

    <!-- Lista de Prompts -->
    <div v-else-if="hasPrompts" class="prompts-list">
      <div 
        v-for="prompt in filteredPrompts" 
        :key="prompt.name"
        class="prompt-card"
        :class="{ 
          'prompt-custom': prompt.isCustom,
          'prompt-modified': prompt.isModified 
        }"
      >
        <div class="prompt-header">
          <div class="prompt-title">
            <h3>{{ prompt.displayName }}</h3>
            <div class="prompt-badges">
              <span 
                v-if="prompt.isCustom" 
                class="badge badge-custom"
              >
                ✅ Personalizado
              </span>
              <span 
                v-else 
                class="badge badge-default"
              >
                🔵 Por defecto
              </span>
              <span 
                v-if="prompt.fallbackLevel && prompt.fallbackLevel !== 'postgresql'" 
                class="badge badge-fallback"
              >
                Fallback: {{ prompt.fallbackLevel }}
              </span>
            </div>
          </div>
          
          <div class="prompt-actions">
            <button 
              @click="previewPrompt(prompt)"
              class="btn btn-sm btn-info"
            >
              👁️ Vista Previa
            </button>
            
            <button 
              v-if="prompt.isCustom || prompt.isModified"
              @click="resetPrompt(prompt.name)"
              class="btn btn-sm btn-warning"
              :disabled="isResetting"
            >
              🔄 Restaurar
            </button>
          </div>
        </div>

        <div class="prompt-content">
          <textarea
            :id="`prompt-${prompt.name}`"
            v-model="prompt.content"
            @input="markAsModified(prompt)"
            class="prompt-editor"
            :placeholder="`Prompt para ${prompt.displayName}...`"
            rows="8"
          ></textarea>
          
          <div class="prompt-metadata">
            <span v-if="prompt.lastModified" class="metadata-item">
              📅 Modificado: {{ formatDateTime(prompt.lastModified) }}
            </span>
            <span v-if="prompt.version" class="metadata-item">
              🏷️ Versión: {{ prompt.version }}
            </span>
          </div>
        </div>

        <div class="prompt-footer">
          <button 
            @click="updatePrompt(prompt.name)"
            :disabled="isUpdating || !prompt.isModified"
            class="btn btn-primary"
          >
            <span v-if="isUpdating">⏳ Actualizando...</span>
            <span v-else>💾 Actualizar</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Estado vacío -->
    <div v-else class="empty-state">
      <div class="empty-icon">📝</div>
      <h3>No hay prompts disponibles</h3>
      <p>Carga los prompts desde el servidor o crea uno nuevo.</p>
      <button @click="loadCurrentPrompts" class="btn btn-primary">
        🔄 Cargar Prompts
      </button>
    </div>

    <!-- Modal de Vista Previa -->
    <div v-if="previewData" class="modal-overlay" @click="closePreviewModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>👁️ Vista Previa: {{ previewData.displayName }}</h3>
          <button @click="closePreviewModal" class="modal-close">❌</button>
        </div>
        
        <div class="modal-body">
          <div v-if="previewData.preview_result" class="preview-processed">
            <h5>🤖 Respuesta del Agente:</h5>
            <div class="preview-response">
              {{ previewData.preview_result.response || 'Sin respuesta' }}
            </div>
            
            <div v-if="previewData.preview_result.metadata" class="preview-metadata">
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
import { usePrompts } from '@/composables/usePrompts'
import { useAppStore } from '@/stores/app'

// ============================================================================
// COMPOSABLES Y STORES
// ============================================================================

const {
  // Estado reactivo del composable
  prompts,
  isLoading,
  isUpdating,
  isResetting,
  isRepairing,
  systemStatus,
  previewData,
  
  // Computed properties
  promptsArray,
  hasPrompts,
  
  // Funciones principales
  loadCurrentPrompts,
  updatePrompt,
  resetPrompt,
  previewPrompt,
  repairPrompts,
  exportPrompts
} = usePrompts()

const appStore = useAppStore()

// ============================================================================
// ESTADO LOCAL DEL COMPONENTE
// ============================================================================

const fileInput = ref(null)

// Filtros locales
const searchQuery = ref('')
const selectedCategory = ref('')
const selectedStatus = ref('')

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const promptCategories = computed(() => {
  const categories = new Set()
  promptsArray.value.forEach(prompt => {
    if (prompt.category) {
      categories.add(prompt.category)
    }
  })
  return Array.from(categories).sort()
})

const filteredPrompts = computed(() => {
  let filtered = promptsArray.value

  // Filtro por búsqueda
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(prompt => 
      prompt.displayName.toLowerCase().includes(query) ||
      (prompt.content || '').toLowerCase().includes(query)
    )
  }

  // Filtro por categoría
  if (selectedCategory.value) {
    filtered = filtered.filter(prompt => 
      prompt.category === selectedCategory.value
    )
  }

  // Filtro por estado
  if (selectedStatus.value) {
    switch (selectedStatus.value) {
      case 'custom':
        filtered = filtered.filter(prompt => prompt.isCustom)
        break
      case 'default':
        filtered = filtered.filter(prompt => !prompt.isCustom)
        break
      case 'modified':
        filtered = filtered.filter(prompt => prompt.isModified)
        break
    }
  }

  return filtered
})

// ============================================================================
// MÉTODOS LOCALES
// ============================================================================

const markAsModified = (prompt) => {
  // Marcar prompt como modificado para habilitar botón de guardar
  prompt.isModified = true
}

const clearFilters = () => {
  searchQuery.value = ''
  selectedCategory.value = ''
  selectedStatus.value = ''
}

const closePreviewModal = () => {
  previewData.value = null
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
    
    if (!importedData || typeof importedData !== 'object') {
      throw new Error('El archivo debe contener un objeto JSON válido con prompts')
    }
    
    // Aquí podrías implementar la lógica de importación al backend
    // Por ahora solo mostramos una notificación
    appStore.showNotification(`Listo para importar prompts`, 'info')
    
  } catch (error) {
    appStore.showNotification(`Error importando archivo: ${error.message}`, 'error')
  }
  
  // Limpiar input
  event.target.value = ''
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
// LIFECYCLE HOOKS
// ============================================================================

onMounted(async () => {
  appStore.addToLog('PromptsTab component mounted', 'info')
  
  // Cargar datos iniciales solo si hay empresa seleccionada
  if (appStore.currentCompanyId) {
    await loadCurrentPrompts()
  }
  
  // EXPONER FUNCIONES GLOBALES PARA COMPATIBILIDAD CON SCRIPT.JS
  window.loadCurrentPrompts = loadCurrentPrompts
  window.updatePrompt = updatePrompt
  window.resetPrompt = resetPrompt
  window.previewPrompt = previewPrompt
  window.repairPrompts = repairPrompts
})

onUnmounted(() => {
  // Limpiar funciones globales
  if (typeof window !== 'undefined') {
    delete window.loadCurrentPrompts
    delete window.updatePrompt
    delete window.resetPrompt
    delete window.previewPrompt
    delete window.repairPrompts
  }
  
  appStore.addToLog('PromptsTab component unmounted', 'info')
})

// ============================================================================
// WATCHERS
// ============================================================================

// Watcher para recargar cuando cambie la empresa
watch(() => appStore.currentCompanyId, async (newCompanyId) => {
  if (newCompanyId) {
    await loadCurrentPrompts()
  }
})
</script>

<style scoped>
.prompts-tab {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.prompts-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}

.header-title h2 {
  margin: 0 0 8px 0;
  color: #2c3e50;
}

.subtitle {
  margin: 0;
  color: #7f8c8d;
  font-size: 14px;
}

.header-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.prompts-filters {
  background: #f8f9fa;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 24px;
}

.filter-group {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.filter-input,
.filter-select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.filter-input {
  min-width: 200px;
}

.loading-container {
  text-align: center;
  padding: 48px 24px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.prompts-list {
  display: grid;
  gap: 24px;
}

.prompt-card {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 20px;
  transition: all 0.2s;
}

.prompt-card:hover {
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}

.prompt-custom {
  border-left: 4px solid #27ae60;
}

.prompt-modified {
  border-left: 4px solid #f39c12;
}

.prompt-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.prompt-title h3 {
  margin: 0 0 8px 0;
  color: #2c3e50;
}

.prompt-badges {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.badge-custom {
  background: #d5edda;
  color: #155724;
}

.badge-default {
  background: #cce5ff;
  color: #004085;
}

.badge-fallback {
  background: #fff3cd;
  color: #856404;
}

.prompt-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.prompt-content {
  margin-bottom: 16px;
}

.prompt-editor {
  width: 100%;
  min-height: 120px;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.4;
  resize: vertical;
  transition: border-color 0.2s;
}

.prompt-editor:focus {
  outline: none;
  border-color: #3498db;
  box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.1);
}

.prompt-metadata {
  display: flex;
  gap: 16px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.metadata-item {
  font-size: 12px;
  color: #7f8c8d;
}

.prompt-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.empty-state {
  text-align: center;
  padding: 48px 24px;
  color: #7f8c8d;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 8px;
  max-width: 800px;
  max-height: 80vh;
  width: 90%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #eee;
}

.modal-header h3 {
  margin: 0;
}

.modal-close {
  background: none;
  border: none;
  font-size: 16px;
  cursor: pointer;
}

.modal-body {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}

.preview-response {
  background: #f8f9fa;
  padding: 16px;
  border-radius: 4px;
  border-left: 4px solid #3498db;
  margin-bottom: 16px;
  font-family: system-ui;
  line-height: 1.5;
}

.preview-metadata {
  margin-top: 16px;
}

.metadata-json {
  background: #f4f4f4;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  overflow-x: auto;
}

.preview-text {
  background: #f8f9fa;
  padding: 16px;
  border-radius: 4px;
  white-space: pre-wrap;
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 13px;
}

.modal-footer {
  padding: 20px;
  border-top: 1px solid #eee;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* Responsive Design */
@media (max-width: 768px) {
  .prompts-tab {
    padding: 16px;
  }
  
  .prompts-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .header-actions {
    justify-content: center;
  }
  
  .filter-group {
    flex-direction: column;
    align-items: stretch;
  }
  
  .filter-input {
    min-width: unset;
  }
  
  .prompt-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .prompt-actions {
    justify-content: center;
  }
}
</style>
