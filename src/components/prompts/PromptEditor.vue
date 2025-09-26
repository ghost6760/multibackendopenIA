<template>
  <div class="prompt-editor-container">
    <!-- Editor Header -->
    <div class="prompt-editor-header">
      <div class="prompt-info">
        <h4 class="prompt-title">{{ promptData.icon }} {{ promptData.displayName }}</h4>
        <div class="prompt-meta">
          <span class="prompt-status" :class="statusClass">{{ statusText }}</span>
          <span v-if="promptData.lastModified" class="prompt-date">
            Modificado: {{ formatDateTime(promptData.lastModified) }}
          </span>
        </div>
      </div>
      
      <!-- Quick Actions -->
      <div class="prompt-quick-actions">
        <button 
          v-if="promptData.isCustom" 
          @click="resetToDefault"
          class="btn-reset-small"
          :disabled="readonly || isProcessing"
          title="Restaurar al valor por defecto"
        >
          🔄
        </button>
        <button 
          @click="showPreview"
          class="btn-preview-small"
          :disabled="readonly || isProcessing || !internalContent.trim()"
          title="Vista previa"
        >
          👁️
        </button>
      </div>
    </div>

    <!-- Editor Textarea -->
    <div class="prompt-editor-body">
      <textarea
        :id="`prompt-${promptData.id}`"
        v-model="internalContent"
        class="prompt-editor"
        :placeholder="promptData.placeholder || 'Escribe aquí tu prompt personalizado...'"
        :disabled="readonly || isProcessing"
        @input="onContentChange"
        @keydown="onKeyDown"
        rows="12"
      ></textarea>
      
      <!-- Character count and validation -->
      <div class="prompt-editor-footer">
        <div class="prompt-stats">
          <span class="char-count">{{ internalContent.length }} caracteres</span>
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
        :disabled="readonly || isProcessing || !hasUnsavedChanges || validationErrors.length > 0"
      >
        <span v-if="isProcessing">⏳ Actualizando...</span>
        <span v-else>💾 Actualizar</span>
      </button>
      
      <button 
        @click="resetToDefault"
        class="btn-secondary"
        :disabled="readonly || isProcessing || !promptData.isCustom"
      >
        <span v-if="isProcessing">⏳ Restaurando...</span>
        <span v-else>🔄 Restaurar</span>
      </button>
      
      <button 
        @click="showPreview"
        class="btn-info"
        :disabled="readonly || isProcessing || !internalContent.trim()"
      >
        <span v-if="isProcessing">⏳ Generando...</span>
        <span v-else>👁️ Vista Previa</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'

// ============================================================================
// PROPS Y EMITS
// ============================================================================

const props = defineProps({
  promptData: {
    type: Object,
    required: true,
    validator(value) {
      return value && 
             typeof value.id === 'string' && 
             typeof value.displayName === 'string' &&
             typeof value.content === 'string'
    }
  },
  readonly: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update', 'reset', 'preview', 'change'])

// ============================================================================
// ESTADO REACTIVO INICIAL SEGURO
// ============================================================================

const internalContent = ref('')
const originalContent = ref('')
const isProcessing = ref(false)
const validationErrors = ref([])
const isInitialized = ref(false) // Flag de inicialización

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const hasUnsavedChanges = computed(() => {
  return isInitialized.value && internalContent.value !== originalContent.value
})

const statusClass = computed(() => {
  if (props.promptData?.isCustom) {
    return 'custom'
  }
  return 'default'
})

const statusText = computed(() => {
  const data = props.promptData
  
  if (data?.isCustom) {
    let text = '✅ Personalizado'
    if (data.lastModified) {
      text += ` (${new Date(data.lastModified).toLocaleDateString()})`
    }
    return text
  }
  
  return '🔵 Por defecto'
})

// ============================================================================
// ✅ FUNCIONES DE INICIALIZACIÓN SEGURAS
// ============================================================================

/**
 * ✅ Inicialización segura del contenido sin watchers immediate
 */
const initializeContent = async () => {
  try {
    await nextTick()
    
    if (props.promptData && typeof props.promptData.content === 'string') {
      internalContent.value = props.promptData.content || ''
      originalContent.value = internalContent.value
      
      // Validar después de asignar contenido
      setTimeout(() => {
        validateContent()
        isInitialized.value = true
      }, 50)
      
      console.log(`[PromptEditor] ✅ Initialized content for ${props.promptData.displayName}`)
    }
  } catch (error) {
    console.warn(`[PromptEditor] Initialization error:`, error)
    // Fallback seguro
    internalContent.value = ''
    originalContent.value = ''
    isInitialized.value = true
  }
}

/**
 * ✅ Actualización manual del contenido cuando cambian los props
 */
const updateContent = async (newData) => {
  if (!newData || typeof newData.content !== 'string') return
  
  try {
    // Solo actualizar si realmente cambió
    if (newData.content !== originalContent.value) {
      internalContent.value = newData.content || ''
      originalContent.value = internalContent.value
      
      await nextTick()
      validateContent()
      
      console.log(`[PromptEditor] Content updated for ${newData.displayName}`)
    }
  } catch (error) {
    console.warn(`[PromptEditor] Error updating content:`, error)
  }
}

// ============================================================================
// ✅ WATCHERS CORREGIDOS - SIN IMMEDIATE
// ============================================================================

/**
 * ✅ CRÍTICO: Watcher SIN immediate para evitar errores de inicialización
 */
watch(() => props.promptData, async (newData, oldData) => {
  if (!newData) return
  
  // Solo actualizar si está inicializado y realmente cambió
  if (isInitialized.value && oldData && newData.content !== oldData.content) {
    await updateContent(newData)
  }
}, { 
  immediate: false, // ✅ CRÍTICO: NO usar immediate
  deep: true 
})

/**
 * ✅ Watcher del contenido interno sin acceso a composables
 */
watch(internalContent, () => {
  try {
    validateContent()
    
    // Solo emitir si está inicializado
    if (isInitialized.value) {
      emit('change', {
        content: internalContent.value,
        hasChanges: hasUnsavedChanges.value,
        isValid: validationErrors.value.length === 0,
        promptData: props.promptData
      })
    }
  } catch (error) {
    console.warn('[PromptEditor] Error in content watcher:', error)
  }
})

// ============================================================================
// FUNCIONES PRINCIPALES - SIN CAMBIOS CRÍTICOS
// ============================================================================

const updatePrompt = () => {
  const content = internalContent.value.trim()
  
  if (!content) {
    console.warn('El prompt no puede estar vacío')
    return
  }
  
  if (validationErrors.value.length > 0) {
    console.warn('El prompt tiene errores de validación')
    return
  }
  
  try {
    isProcessing.value = true
    
    emit('update', {
      agentName: props.promptData.id || props.promptData.name,
      content: content
    })
    
  } finally {
    isProcessing.value = false
  }
}

const resetToDefault = async () => {
  if (!props.promptData.isCustom) {
    console.warn('Este prompt ya está en su valor por defecto')
    return
  }
  
  const agentName = props.promptData.displayName
  
  if (!confirm(`¿Estás seguro de restaurar el prompt por defecto para ${agentName}?`)) {
    return
  }
  
  try {
    isProcessing.value = true
    emit('reset', props.promptData.id || props.promptData.name)
  } finally {
    isProcessing.value = false
  }
}

const showPreview = async () => {
  const content = internalContent.value.trim()
  if (!content) {
    console.warn('El prompt no puede estar vacío')
    return
  }
  
  try {
    isProcessing.value = true
    emit('preview', props.promptData.id || props.promptData.name)
  } finally {
    isProcessing.value = false
  }
}

// ============================================================================
// FUNCIONES DE VALIDACIÓN - SIN CAMBIOS
// ============================================================================

const validateContent = () => {
  try {
    const errors = []
    const content = internalContent.value
    
    // Validación 1: Longitud máxima
    if (content.length > 10000) {
      errors.push('El prompt es demasiado largo (máximo 10,000 caracteres)')
    }
    
    // Validación 2: Solo una instancia de {user_message}
    if (content.includes('{user_message}') && content.split('{user_message}').length > 2) {
      errors.push('Solo se permite una instancia de {user_message}')
    }
    
    validationErrors.value = errors
  } catch (error) {
    console.warn('[PromptEditor] Validation error:', error)
    validationErrors.value = []
  }
}

const onContentChange = () => {
  try {
    validateContent()
  } catch (error) {
    console.warn('[PromptEditor] Content change error:', error)
  }
}

const onKeyDown = (event) => {
  try {
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
      if (internalContent.value.trim()) {
        showPreview()
      }
    }
    
    // Escape para deshacer cambios
    if (event.key === 'Escape' && hasUnsavedChanges.value) {
      if (confirm('¿Deshacer cambios no guardados?')) {
        internalContent.value = originalContent.value
      }
    }
  } catch (error) {
    console.warn('[PromptEditor] Keyboard error:', error)
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
// ✅ LIFECYCLE HOOKS CORREGIDOS CON INICIALIZACIÓN MANUAL
// ============================================================================

onMounted(async () => {
  try {
    console.log(`[PromptEditor] Mounting for ${props.promptData?.displayName || 'unknown'}`)
    
    // ✅ CRÍTICO: Inicialización manual en lugar de watchers immediate
    setTimeout(async () => {
      await initializeContent()
    }, 100)
    
    // Funciones globales solo si están disponibles
    const agentName = props.promptData?.id || props.promptData?.name
    if (agentName && typeof window !== 'undefined') {
      try {
        window[`updatePrompt_${agentName}`] = updatePrompt
        window[`resetPrompt_${agentName}`] = resetToDefault
        window[`previewPrompt_${agentName}`] = showPreview
      } catch (error) {
        console.warn('[PromptEditor] Error setting global functions:', error)
      }
    }
    
  } catch (error) {
    console.error('[PromptEditor] Mount error:', error)
    // Fallback: Asegurar que esté inicializado
    isInitialized.value = true
  }
})

// ============================================================================
// ✅ FUNCIÓN DE VERIFICACIÓN DE SALUD DEL COMPONENTE
// ============================================================================

const healthCheck = () => {
  return {
    isInitialized: isInitialized.value,
    hasContent: Boolean(internalContent.value),
    hasChanges: hasUnsavedChanges.value,
    isValid: validationErrors.value.length === 0,
    agentName: props.promptData?.displayName || 'Unknown',
    contentLength: internalContent.value.length,
    originalContentLength: originalContent.value.length
  }
}

// Exponer para debug
if (typeof window !== 'undefined') {
  window.promptEditorHealthCheck = healthCheck
}
</script>

<style scoped>
/* Estilos preservados del archivo original - sin cambios */
.prompt-editor-container {
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  transition: transform 0.2s, box-shadow 0.2s;
}

.prompt-editor-container:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}

.prompt-editor-header {
  background: #f8f9fa;
  padding: 15px;
  border-bottom: 1px solid #dee2e6;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
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
  padding: 15px;
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
  padding: 15px;
  background: #f8f9fa;
  border-top: 1px solid #dee2e6;
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
