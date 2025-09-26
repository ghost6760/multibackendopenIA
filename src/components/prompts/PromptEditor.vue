<template>
  <div class="prompt-editor-container">
    <!-- Editor Header -->
    <div class="prompt-editor-header">
      <div class="prompt-info">
        <h4 class="prompt-title">{{ safePromptData.icon }} {{ safePromptData.displayName }}</h4>
        <div class="prompt-meta">
          <span class="prompt-status" :class="statusClass">{{ statusText }}</span>
          <span v-if="safePromptData.lastModified" class="prompt-date">
            Modificado: {{ formatDateTime(safePromptData.lastModified) }}
          </span>
        </div>
      </div>
      
      <!-- Quick Actions -->
      <div class="prompt-quick-actions">
        <button 
          v-if="safePromptData.isCustom" 
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
        :id="`prompt-${safePromptData.id}`"
        v-model="internalContent"
        class="prompt-editor"
        :placeholder="safePromptData.placeholder || 'Escribe aquí tu prompt personalizado...'"
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
        :disabled="readonly || isProcessing || !safePromptData.isCustom"
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
import { ref, computed, watch, toRefs, onMounted } from 'vue'

// ============================================================================
// PROPS Y EMITS - ✅ MEJORADO CON DEFAULT SEGURO
// ============================================================================

const props = defineProps({
  promptData: {
    type: Object,
    required: true,
    default: () => ({
      id: '',
      displayName: 'Cargando...',
      content: '',
      icon: '🤖',
      placeholder: 'Cargando prompt...'
    }), // ✅ Default seguro
    validator(value) {
      // Validar estructura requerida pero más permisivo
      return value && 
             typeof value === 'object' &&
             (value.id || value.name) &&
             (value.displayName || value.display_name)
    }
  },
  readonly: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update', 'reset', 'preview', 'change'])

// ============================================================================
// ✅ USAR toRefs PARA EVITAR ACCESO ANTES DE INICIALIZACIÓN
// ============================================================================

const { promptData } = toRefs(props)

// ============================================================================
// ESTADO REACTIVO
// ============================================================================

const internalContent = ref('')
const originalContent = ref('')
const isProcessing = ref(false)
const validationErrors = ref([])

// ============================================================================
// ✅ COMPUTED CON VERIFICACIONES SEGURAS
// ============================================================================

// Datos seguros del prompt con fallbacks
const safePromptData = computed(() => {
  const data = promptData.value
  
  if (!data || typeof data !== 'object') {
    return {
      id: 'loading',
      displayName: 'Cargando...',
      content: '',
      icon: '🤖',
      placeholder: 'Cargando prompt...',
      isCustom: false,
      lastModified: null
    }
  }
  
  return {
    id: data.id || data.name || 'unknown',
    displayName: data.displayName || data.display_name || 'Prompt',
    content: data.content || '',
    icon: data.icon || '🤖',
    placeholder: data.placeholder || 'Escribe aquí tu prompt personalizado...',
    isCustom: data.isCustom || data.is_custom || false,
    lastModified: data.lastModified || data.last_modified || null
  }
})

const hasUnsavedChanges = computed(() => {
  return internalContent.value !== originalContent.value
})

const statusClass = computed(() => {
  const data = safePromptData.value
  return data?.isCustom ? 'custom' : 'default'
})

const statusText = computed(() => {
  const data = safePromptData.value
  
  if (!data) return 'Cargando...' // ✅ Estado seguro
  
  if (data.isCustom) {
    let text = '✅ Personalizado'
    if (data.lastModified) {
      text += ` (${new Date(data.lastModified).toLocaleDateString()})`
    }
    return text
  }
  
  return '🔵 Por defecto'
})

// ============================================================================
// ✅ WATCHERS CON VERIFICACIÓN DE EXISTENCIA
// ============================================================================

watch(promptData, (newData) => {
  if (newData && typeof newData === 'object') {
    // ✅ Procesar datos solo si son válidos
    console.log('Prompt data updated:', newData.displayName || newData.id)
    internalContent.value = newData.content || ''
    originalContent.value = internalContent.value
    validateContent()
  }
}, { immediate: true, deep: true })

watch(internalContent, () => {
  validateContent()
  
  // Emitir cambios con datos seguros
  emit('change', {
    content: internalContent.value,
    hasChanges: hasUnsavedChanges.value,
    isValid: validationErrors.value.length === 0,
    promptData: safePromptData.value
  })
})

// ============================================================================
// FUNCIONES PRINCIPALES - ✅ CON VERIFICACIONES SEGURAS
// ============================================================================

/**
 * ✅ Actualiza el prompt con verificaciones
 */
const updatePrompt = () => {
  const content = internalContent.value.trim()
  const data = safePromptData.value
  
  if (!content) {
    console.warn('El prompt no puede estar vacío')
    return
  }
  
  if (!data?.id) {
    console.warn('ID del prompt no disponible')
    return
  }
  
  if (validationErrors.value.length > 0) {
    console.warn('El prompt tiene errores de validación')
    return
  }
  
  try {
    isProcessing.value = true
    
    // Emitir datos estructurados
    emit('update', {
      agentName: data.id,
      content: content
    })
    
  } finally {
    isProcessing.value = false
  }
}

/**
 * ✅ Resetea el prompt con verificaciones
 */
const resetToDefault = async () => {
  const data = safePromptData.value
  
  if (!data?.isCustom) {
    console.warn('Este prompt ya está en su valor por defecto')
    return
  }
  
  if (!data?.id) {
    console.warn('ID del prompt no disponible')
    return
  }
  
  const agentName = data.displayName || data.id
  
  if (!confirm(`¿Estás seguro de restaurar el prompt por defecto para ${agentName}?`)) {
    return
  }
  
  try {
    isProcessing.value = true
    
    emit('reset', data.id)
    
  } finally {
    isProcessing.value = false
  }
}

/**
 * ✅ Muestra vista previa con verificaciones
 */
const showPreview = async () => {
  const content = internalContent.value.trim()
  const data = safePromptData.value
  
  if (!content) {
    console.warn('El prompt no puede estar vacío')
    return
  }
  
  if (!data?.id) {
    console.warn('ID del prompt no disponible')
    return
  }
  
  try {
    isProcessing.value = true
    
    emit('preview', data.id)
    
  } finally {
    isProcessing.value = false
  }
}

// ============================================================================
// FUNCIONES DE VALIDACIÓN Y UTILIDADES - ✅ SIN CAMBIOS
// ============================================================================

const validateContent = () => {
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
// LIFECYCLE - ✅ CON VERIFICACIONES
// ============================================================================

onMounted(() => {
  // Validación inicial
  validateContent()
  
  // ✅ Exponer funciones globales solo si hay datos válidos
  const data = safePromptData.value
  if (data?.id && typeof window !== 'undefined') {
    window[`updatePrompt_${data.id}`] = updatePrompt
    window[`resetPrompt_${data.id}`] = resetToDefault
    window[`previewPrompt_${data.id}`] = showPreview
  }
})
</script>

<!-- Estilos sin cambios - mantener los existentes -->
<style scoped>
/* ===== ESTILOS PARA PROMPT EDITOR ===== */

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

/* Estados de animación */
.prompt-editor-container.saving {
  opacity: 0.7;
}

.prompt-editor-container.error {
  border-color: #dc3545;
}

.prompt-editor-container.success {
  border-color: #28a745;
}
</style>
