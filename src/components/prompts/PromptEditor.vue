# PromptEditor.vue
<template>
  <div class="prompt-editor-container">
    <!-- Editor Header -->
    <div class="prompt-editor-header">
      <div class="prompt-info">
        <h4 class="prompt-title">{{ promptData.name || promptData.id || 'Prompt' }}</h4>
        <div class="prompt-meta">
          <span class="prompt-status" :class="statusClass">{{ statusText }}</span>
          <span v-if="promptData.last_modified" class="prompt-date">
            Modificado: {{ formatDateTime(promptData.last_modified) }}
          </span>
        </div>
      </div>
      
      <!-- Quick Actions -->
      <div class="prompt-quick-actions">
        <button 
          v-if="promptData.is_custom" 
          @click="resetToDefault"
          class="btn-reset-small"
          :disabled="isProcessing"
          title="Restaurar al valor por defecto"
        >
          🔄
        </button>
        <button 
          @click="showPreview"
          class="btn-preview-small"
          :disabled="isProcessing || !promptContent.trim()"
          title="Vista previa"
        >
          👁️
        </button>
      </div>
    </div>

    <!-- Editor Textarea -->
    <div class="prompt-editor-body">
      <textarea
        :id="`prompt-${promptData.id || promptData.name}`"
        v-model="promptContent"
        class="prompt-editor"
        :placeholder="placeholder"
        :disabled="isProcessing"
        @input="onContentChange"
        @keydown="onKeyDown"
        rows="12"
      ></textarea>
      
      <!-- Character count and validation -->
      <div class="prompt-editor-footer">
        <div class="prompt-stats">
          <span class="char-count">{{ promptContent.length }} caracteres</span>
          <span v-if="hasUnsavedChanges" class="unsaved-indicator">• Cambios sin guardar</span>
        </div>
        
        <div class="validation-messages" v-if="validationErrors.length > 0">
          <div v-for="error in validationErrors" :key="error" class="validation-error">
            ⚠️ {{ error }}
          </div>
        </div>
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="prompt-actions">
      <button 
        @click="updatePrompt"
        class="btn-primary"
        :disabled="isProcessing || !hasUnsavedChanges || validationErrors.length > 0"
      >
        <span v-if="isProcessing">⏳ Actualizando...</span>
        <span v-else>💾 Actualizar</span>
      </button>
      
      <button 
        @click="resetToDefault"
        class="btn-secondary"
        :disabled="isProcessing || !promptData.is_custom"
      >
        <span v-if="isProcessing">⏳ Restaurando...</span>
        <span v-else>🔄 Restaurar</span>
      </button>
      
      <button 
        @click="showPreview"
        class="btn-info"
        :disabled="isProcessing || !promptContent.trim()"
      >
        <span v-if="isProcessing">⏳ Generando...</span>
        <span v-else>👁️ Vista Previa</span>
      </button>
      
      <button 
        v-if="promptData.supports_repair"
        @click="repairPrompt"
        class="btn-repair"
        :disabled="isProcessing"
        title="Reparar prompt desde repositorio"
      >
        🔧 Reparar
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'

// ============================================================================
// PROPS Y EMITS
// ============================================================================

const props = defineProps({
  promptData: {
    type: Object,
    required: true,
    default: () => ({})
  },
  placeholder: {
    type: String,
    default: 'Escribe aquí tu prompt personalizado...'
  },
  readonly: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update', 'reset', 'preview', 'change'])

// ============================================================================
// COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const { apiRequest } = useApiRequest()
const { showNotification } = useNotifications()

// ============================================================================
// ESTADO REACTIVO
// ============================================================================

const promptContent = ref('')
const originalContent = ref('')
const isProcessing = ref(false)
const validationErrors = ref([])

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const hasUnsavedChanges = computed(() => {
  return promptContent.value !== originalContent.value
})

const statusClass = computed(() => {
  if (promptData.value?.is_custom) {
    return 'custom'
  }
  return 'default'
})

const statusText = computed(() => {
  const data = props.promptData
  
  if (data?.is_custom) {
    let text = '✅ Personalizado'
    if (data.last_modified) {
      text += ` (${new Date(data.last_modified).toLocaleDateString()})`
    }
    return text
  }
  
  return '🔵 Por defecto'
})

// ============================================================================
// WATCHERS
// ============================================================================

watch(() => props.promptData, (newData) => {
  if (newData) {
    promptContent.value = newData.content || newData.current_prompt || ''
    originalContent.value = promptContent.value
    validateContent()
  }
}, { immediate: true, deep: true })

watch(promptContent, () => {
  validateContent()
  emit('change', {
    content: promptContent.value,
    hasChanges: hasUnsavedChanges.value,
    isValid: validationErrors.value.length === 0
  })
})

// ============================================================================
// FUNCIONES PRINCIPALES - MIGRADAS DEL SCRIPT.JS
// ============================================================================

/**
 * Actualiza el prompt - MIGRADO: updatePrompt() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const updatePrompt = async () => {
  if (!appStore.currentCompanyId) {
    showNotification('Por favor selecciona una empresa primero', 'warning')
    return
  }
  
  const content = promptContent.value.trim()
  if (!content) {
    showNotification('El prompt no puede estar vacío', 'error')
    return
  }
  
  try {
    isProcessing.value = true
    const agentName = props.promptData.id || props.promptData.name
    
    appStore.addToLog(`Updating prompt for ${agentName} in company ${appStore.currentCompanyId}`, 'info')
    
    // PRESERVAR: Request exacto como en script.js
    const response = await apiRequest(`/api/admin/prompts/${agentName}`, {
      method: 'PUT',
      body: {
        company_id: appStore.currentCompanyId,
        prompt_template: content
      }
    })
    
    // Actualizar contenido original
    originalContent.value = content
    
    // PRESERVAR: Mensaje de éxito con versión si está disponible
    let successMessage = `Prompt de ${agentName} actualizado exitosamente`
    if (response.version) {
      successMessage += ` (v${response.version})`
    }
    
    showNotification(successMessage, 'success')
    appStore.addToLog(`Prompt ${agentName} updated successfully`, 'info')
    
    // Emitir evento para actualizar padre
    emit('update', {
      ...props.promptData,
      content: content,
      is_custom: true,
      last_modified: new Date().toISOString()
    })
    
  } catch (error) {
    appStore.addToLog(`Error updating prompt: ${error.message}`, 'error')
    showNotification('Error al actualizar prompt: ' + error.message, 'error')
  } finally {
    isProcessing.value = false
  }
}

/**
 * Resetea el prompt - MIGRADO: resetPrompt() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const resetToDefault = async () => {
  if (!appStore.currentCompanyId) {
    showNotification('Por favor selecciona una empresa primero', 'warning')
    return
  }
  
  const agentName = props.promptData.id || props.promptData.name
  
  if (!confirm(`¿Estás seguro de restaurar el prompt por defecto para ${agentName}?`)) {
    return
  }
  
  try {
    isProcessing.value = true
    
    appStore.addToLog(`Resetting prompt for ${agentName} in company ${appStore.currentCompanyId}`, 'info')
    
    // PRESERVAR: Request exacto como en script.js
    const response = await apiRequest(`/api/admin/prompts/${agentName}?company_id=${appStore.currentCompanyId}`, {
      method: 'DELETE'
    })
    
    // Actualizar contenido al valor por defecto
    const defaultContent = response.default_prompt || ''
    promptContent.value = defaultContent
    originalContent.value = defaultContent
    
    showNotification(`Prompt de ${agentName} restaurado al valor por defecto`, 'success')
    appStore.addToLog(`Prompt ${agentName} reset successfully`, 'info')
    
    // Emitir evento para actualizar padre
    emit('reset', {
      ...props.promptData,
      content: defaultContent,
      is_custom: false,
      last_modified: null
    })
    
  } catch (error) {
    appStore.addToLog(`Error resetting prompt: ${error.message}`, 'error')
    showNotification('Error al restaurar prompt: ' + error.message, 'error')
  } finally {
    isProcessing.value = false
  }
}

/**
 * Muestra vista previa - MIGRADO: previewPrompt() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const showPreview = async () => {
  if (!appStore.currentCompanyId) {
    showNotification('Por favor selecciona una empresa primero', 'warning')
    return
  }
  
  const content = promptContent.value.trim()
  if (!content) {
    showNotification('El prompt no puede estar vacío', 'error')
    return
  }
  
  // PRESERVAR: Usar prompt() como en script.js original
  const testMessage = prompt('Introduce un mensaje de prueba:', '¿Cuánto cuesta un tratamiento?')
  
  if (!testMessage) {
    showNotification('Operación cancelada', 'info')
    return
  }
  
  try {
    isProcessing.value = true
    const agentName = props.promptData.id || props.promptData.name
    
    appStore.addToLog(`Previewing prompt for ${agentName}`, 'info')
    
    // Emitir evento para mostrar preview en componente padre
    emit('preview', {
      agentName,
      promptContent: content,
      testMessage,
      promptData: props.promptData
    })
    
  } catch (error) {
    appStore.addToLog(`Error previewing prompt: ${error.message}`, 'error')
    showNotification('Error generando vista previa: ' + error.message, 'error')
  } finally {
    isProcessing.value = false
  }
}

/**
 * Reparar prompt - NUEVA FUNCIÓN del script.js
 */
const repairPrompt = async () => {
  if (!appStore.currentCompanyId) {
    showNotification('Por favor selecciona una empresa primero', 'warning')
    return
  }
  
  const agentName = props.promptData.id || props.promptData.name
  
  if (!confirm(`¿Reparar el prompt ${agentName} desde el repositorio?`)) {
    return
  }
  
  try {
    isProcessing.value = true
    
    // PRESERVAR: Endpoint de reparación como en script.js
    const response = await apiRequest(`/api/admin/prompts/repair`, {
      method: 'POST',
      body: {
        company_id: appStore.currentCompanyId,
        agents: [agentName]
      }
    })
    
    showNotification(`Prompt ${agentName} reparado exitosamente`, 'success')
    
    // Recargar contenido si se reparó
    if (response.repaired && response.repaired[agentName]) {
      const repairedContent = response.repaired[agentName]
      promptContent.value = repairedContent
      originalContent.value = repairedContent
    }
    
  } catch (error) {
    showNotification('Error reparando prompt: ' + error.message, 'error')
  } finally {
    isProcessing.value = false
  }
}

// ============================================================================
// FUNCIONES DE VALIDACIÓN Y UTILIDADES
// ============================================================================

const validateContent = () => {
  const errors = []
  const content = promptContent.value
  
  if (content.length > 10000) {
    errors.push('El prompt es demasiado largo (máximo 10,000 caracteres)')
  }
  
  if (content.includes('{user_message}') && content.split('{user_message}').length > 2) {
    errors.push('Solo se permite una instancia de {user_message}')
  }
  
  validationErrors.value = errors
}

const onContentChange = () => {
  // Trigger validation on change
  validateContent()
}

const onKeyDown = (event) => {
  // Ctrl+S para guardar
  if (event.ctrlKey && event.key === 's') {
    event.preventDefault()
    if (hasUnsavedChanges.value && validationErrors.value.length === 0) {
      updatePrompt()
    }
  }
  
  // Ctrl+Enter para vista previa
  if (event.ctrlKey && event.key === 'Enter') {
    event.preventDefault()
    if (promptContent.value.trim()) {
      showPreview()
    }
  }
}

const formatDateTime = (dateString) => {
  if (!dateString) return 'N/A'
  try {
    return new Date(dateString).toLocaleString()
  } catch (error) {
    return 'Fecha inválida'
  }
}

// ============================================================================
// LIFECYCLE
// ============================================================================

onMounted(() => {
  // EXPONER FUNCIONES GLOBALES PARA COMPATIBILIDAD
  const agentName = props.promptData.id || props.promptData.name
  if (agentName && typeof window !== 'undefined') {
    window[`updatePrompt_${agentName}`] = updatePrompt
    window[`resetPrompt_${agentName}`] = resetToDefault
    window[`previewPrompt_${agentName}`] = showPreview
  }
})

onUnmounted(() => {
  // Limpiar funciones globales
  const agentName = props.promptData.id || props.promptData.name
  if (agentName && typeof window !== 'undefined') {
    delete window[`updatePrompt_${agentName}`]
    delete window[`resetPrompt_${agentName}`]
    delete window[`previewPrompt_${agentName}`]
  }
})
</script>

<style scoped>
/* ===== ESTILOS PARA PROMPT EDITOR ===== */

.prompt-editor-container {
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-bottom: 20px;
}

.prompt-editor-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 2px solid #007bff;
}

.prompt-info {
  flex: 1;
}

.prompt-title {
  margin: 0 0 5px 0;
  color: #495057;
  font-size: 1.1em;
  font-weight: bold;
}

.prompt-meta {
  display: flex;
  gap: 15px;
  align-items: center;
  font-size: 0.9em;
}

.prompt-status {
  font-weight: bold;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.85em;
}

.prompt-status.custom {
  color: #28a745;
  background: rgba(40, 167, 69, 0.1);
}

.prompt-status.default {
  color: #6c757d;
  background: rgba(108, 117, 125, 0.1);
}

.prompt-date {
  color: #6c757d;
}

.prompt-quick-actions {
  display: flex;
  gap: 5px;
}

.btn-reset-small,
.btn-preview-small {
  padding: 4px 8px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9em;
  transition: all 0.2s ease;
}

.btn-reset-small {
  background: #6c757d;
  color: white;
}

.btn-reset-small:hover:not(:disabled) {
  background: #545b62;
}

.btn-preview-small {
  background: #17a2b8;
  color: white;
}

.btn-preview-small:hover:not(:disabled) {
  background: #117a8b;
}

.prompt-editor-body {
  margin-bottom: 15px;
}

.prompt-editor {
  width: 100%;
  min-height: 200px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  padding: 12px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
  resize: vertical;
  background: white;
  transition: border-color 0.2s ease;
}

.prompt-editor:focus {
  border-color: #007bff;
  box-shadow: 0 0 0 0.2rem rgba(0,123,255,.25);
  outline: none;
}

.prompt-editor:disabled {
  background: #f8f9fa;
  cursor: not-allowed;
}

.prompt-editor-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #e9ecef;
}

.prompt-stats {
  display: flex;
  gap: 15px;
  align-items: center;
  font-size: 0.85em;
  color: #6c757d;
}

.char-count {
  font-weight: 500;
}

.unsaved-indicator {
  color: #ffc107;
  font-weight: bold;
}

.validation-messages {
  flex: 1;
  text-align: right;
}

.validation-error {
  color: #dc3545;
  font-size: 0.85em;
  margin-bottom: 3px;
}

.prompt-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.prompt-actions button {
  flex: 1;
  min-width: 120px;
  padding: 10px 15px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
  font-size: 0.9em;
  transition: all 0.3s ease;
  position: relative;
}

.btn-primary {
  background-color: #007bff;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: #0056b3;
  transform: translateY(-1px);
}

.btn-secondary {
  background-color: #6c757d;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background-color: #545b62;
  transform: translateY(-1px);
}

.btn-info {
  background-color: #17a2b8;
  color: white;
}

.btn-info:hover:not(:disabled) {
  background-color: #117a8b;
  transform: translateY(-1px);
}

.btn-repair {
  background-color: #fd7e14;
  color: white;
}

.btn-repair:hover:not(:disabled) {
  background-color: #e8690b;
  transform: translateY(-1px);
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none !important;
}

/* Responsive design */
@media (max-width: 768px) {
  .prompt-editor-header {
    flex-direction: column;
    gap: 10px;
  }
  
  .prompt-meta {
    flex-direction: column;
    align-items: flex-start;
    gap: 5px;
  }
  
  .prompt-actions {
    flex-direction: column;
  }
  
  .prompt-actions button {
    min-width: auto;
  }
  
  .prompt-editor-footer {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .validation-messages {
    text-align: left;
  }
}
</style>
