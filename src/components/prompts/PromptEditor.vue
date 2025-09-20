# PromptEditor.vue - CORRECCIÓN DE REACTIVIDAD
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

    <!-- ✅ DEBUG INFO (temporal) -->
    <div v-if="showDebugInfo" class="debug-info">
      <small>
        <strong>DEBUG:</strong>
        PropData Content: {{ promptData.content?.length || 0 }} chars |
        Internal Content: {{ internalContent.length }} chars |
        Has Changes: {{ hasUnsavedChanges }} |
        Watcher Triggered: {{ watcherTriggerCount }} times
      </small>
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
// ESTADO REACTIVO
// ============================================================================

const internalContent = ref('')
const originalContent = ref('')
const isProcessing = ref(false)
const validationErrors = ref([])

// ✅ DEBUG: Variables para debugging
const showDebugInfo = ref(false) // Cambiar a true para debug
const watcherTriggerCount = ref(0)

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const hasUnsavedChanges = computed(() => {
  return internalContent.value !== originalContent.value
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
// ✅ WATCHERS MEJORADOS CON LOGGING
// ============================================================================

// ✅ CRÍTICO: Watcher mejorado con logging detallado
watch(() => props.promptData, (newData, oldData) => {
  watcherTriggerCount.value++
  
  console.log(`🔄 PromptEditor watcher triggered for ${newData?.displayName}:`, {
    triggerCount: watcherTriggerCount.value,
    hasNewData: !!newData,
    newContent: newData?.content || '',
    newContentLength: newData?.content?.length || 0,
    oldContent: oldData?.content || '',
    oldContentLength: oldData?.content?.length || 0,
    contentChanged: newData?.content !== oldData?.content
  })
  
  if (newData) {
    const newContent = newData.content || ''
    
    // ✅ Siempre actualizar si el contenido ha cambiado
    if (newContent !== internalContent.value) {
      console.log(`📝 Updating internal content for ${newData.displayName}:`, {
        from: internalContent.value.substring(0, 50) + '...',
        to: newContent.substring(0, 50) + '...',
        lengthChange: `${internalContent.value.length} → ${newContent.length}`
      })
      
      internalContent.value = newContent
      originalContent.value = newContent
      
      // ✅ Forzar validación después de actualizar
      nextTick(() => {
        validateContent()
      })
    }
  }
}, { immediate: true, deep: true })

// ✅ NUEVO: Watcher adicional para detectar cambios específicos en content
watch(() => props.promptData?.content, (newContent, oldContent) => {
  console.log(`🔄 Content-specific watcher for ${props.promptData?.displayName}:`, {
    newContent: newContent?.substring(0, 50) + '...',
    oldContent: oldContent?.substring(0, 50) + '...',
    contentLength: newContent?.length || 0,
    changed: newContent !== oldContent
  })
  
  if (newContent !== undefined && newContent !== internalContent.value) {
    console.log(`📝 Content changed, updating internal...`)
    internalContent.value = newContent
    originalContent.value = newContent
    validateContent()
  }
}, { immediate: true })

// ✅ Watcher para cambios en internalContent
watch(internalContent, (newValue, oldValue) => {
  if (newValue !== oldValue) {
    validateContent()
    emit('change', {
      content: newValue,
      hasChanges: hasUnsavedChanges.value,
      isValid: validationErrors.value.length === 0,
      promptData: props.promptData
    })
  }
})

// ============================================================================
// FUNCIONES PRINCIPALES
// ============================================================================

const updatePrompt = async () => {
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
    
    originalContent.value = content
    
    console.log(`🔄 Emitting update for ${props.promptData.id}`)
    emit('update', props.promptData.id || props.promptData.name)
    
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
    
    console.log(`🔄 Emitting reset for ${props.promptData.id}`)
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
    
    console.log(`🔄 Emitting preview for ${props.promptData.id}`)
    emit('preview', props.promptData.id || props.promptData.name)
    
  } finally {
    isProcessing.value = false
  }
}

// ============================================================================
// FUNCIONES DE VALIDACIÓN Y UTILIDADES
// ============================================================================

const validateContent = () => {
  const errors = []
  const content = internalContent.value
  
  if (content.length > 10000) {
    errors.push('El prompt es demasiado largo (máximo 10,000 caracteres)')
  }
  
  if (content.includes('{user_message}') && content.split('{user_message}').length > 2) {
    errors.push('Solo se permite una instancia de {user_message}')
  }
  
  // ✅ CORRECCIÓN: Validación de variables mejorada
  const forbiddenPatterns = [
    { pattern: /\{\{[^}]+\}\}/g, message: 'Usa {variable} en lugar de {{variable}}' },
    { pattern: /\$\{[^}]+\}/g, message: 'Usa {variable} en lugar de ${variable}' },
    { pattern: /\{[^}]+\}\s*[≤<>]\s*\d+/g, message: 'Evita operadores matemáticos cerca de variables' }
  ]
  
  forbiddenPatterns.forEach(({ pattern, message }) => {
    if (pattern.test(content)) {
      errors.push(`Formato de variable no válido: ${message}`)
    }
  })
  
  validationErrors.value = errors
  
  // ✅ LOGGING de validación
  if (errors.length > 0) {
    console.log(`⚠️ Validation errors for ${props.promptData?.displayName}:`, errors)
  }
}

const onContentChange = () => {
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
// ✅ FUNCIÓN DEBUG PARA VERIFICAR ESTADO
// ============================================================================

const debugEditor = () => {
  console.log(`=== 🔍 DEBUG PROMPT EDITOR: ${props.promptData?.displayName} ===`)
  console.log('1. Props promptData:', props.promptData)
  console.log('2. Internal content length:', internalContent.value.length)
  console.log('3. Original content length:', originalContent.value.length)
  console.log('4. Has unsaved changes:', hasUnsavedChanges.value)
  console.log('5. Validation errors:', validationErrors.value)
  console.log('6. Watcher trigger count:', watcherTriggerCount.value)
  console.log('7. Content preview:', internalContent.value.substring(0, 100) + '...')
}

// ============================================================================
// LIFECYCLE
// ============================================================================

onMounted(() => {
  // ✅ LOG de montaje
  console.log(`🔄 PromptEditor mounted for ${props.promptData?.displayName}:`, {
    promptDataContent: props.promptData?.content?.length || 0,
    internalContent: internalContent.value.length,
    hasContent: !!props.promptData?.content
  })
  
  // Validación inicial
  validateContent()
  
  // ✅ EXPONER FUNCIÓN DEBUG GLOBALMENTE
  const agentName = props.promptData.id || props.promptData.name
  if (agentName && typeof window !== 'undefined') {
    window[`debugEditor_${agentName}`] = debugEditor
    window[`updatePrompt_${agentName}`] = updatePrompt
    window[`resetPrompt_${agentName}`] = resetToDefault
    window[`previewPrompt_${agentName}`] = showPreview
  }
})
</script>

<style scoped>
/* ===== ESTILOS EXISTENTES ===== */

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

/* ✅ NUEVO: Estilos para debug info */
.debug-info {
  background: #fff3cd;
  border-bottom: 1px solid #ffeaa7;
  padding: 8px 15px;
  font-family: monospace;
  font-size: 11px;
  color: #856404;
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
