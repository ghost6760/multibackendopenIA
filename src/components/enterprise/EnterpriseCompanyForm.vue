<template>
  <div class="enterprise-company-form">
    <!-- Header del formulario -->
    <div class="form-header">
      <h4>
        {{ isEditMode ? '✏️ Editar Empresa Enterprise' : '➕ Crear Nueva Empresa Enterprise' }}
      </h4>
      <p class="form-description">
        {{ isEditMode ? 'Modifica los datos de la empresa enterprise' : 'Complete los datos para crear una nueva empresa enterprise' }}
      </p>
    </div>

    <!-- Formulario principal -->
    <form @submit.prevent="handleSubmit" id="enterpriseCreateForm" class="enterprise-form">
      <!-- Información básica -->
      <div class="form-section">
        <h5>📋 Información Básica</h5>
        
        <div class="form-group">
          <label for="companyId">ID de la Empresa:</label>
          <input 
            v-model="formData.id"
            type="text" 
            id="companyId"
            :disabled="isEditMode"
            required
            pattern="[a-zA-Z0-9_-]+"
            title="Solo letras, números, guiones y guiones bajos"
            placeholder="ej: miempresa_spa"
            class="form-control"
          />
          <small class="form-hint">
            {{ isEditMode ? 'El ID no se puede modificar' : 'Identificador único (solo letras, números, _, -)' }}
          </small>
        </div>

        <div class="form-group">
          <label for="companyName">Nombre de la Empresa:</label>
          <input 
            v-model="formData.name"
            type="text" 
            id="companyName"
            required
            placeholder="ej: Mi Empresa SPA"
            class="form-control"
          />
        </div>

        <div class="form-group">
          <label for="companyDescription">Descripción:</label>
          <textarea 
            v-model="formData.description"
            id="companyDescription"
            rows="3"
            placeholder="Breve descripción de la empresa..."
            class="form-control"
          ></textarea>
        </div>
      </div>

      <!-- Configuración técnica -->
      <div class="form-section">
        <h5>⚙️ Configuración Técnica</h5>
        
        <div class="form-group">
          <label for="apiBaseUrl">URL Base de la API:</label>
          <input 
            v-model="formData.api_base_url"
            type="url" 
            id="apiBaseUrl"
            placeholder="https://mi-api.ejemplo.com"
            class="form-control"
          />
          <small class="form-hint">URL base para las llamadas API de esta empresa</small>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="databaseType">Tipo de Base de Datos:</label>
            <select 
              v-model="formData.database_type"
              id="databaseType"
              class="form-control"
            >
              <option value="">Seleccionar...</option>
              <option value="postgresql">PostgreSQL</option>
              <option value="mysql">MySQL</option>
              <option value="sqlite">SQLite</option>
              <option value="mongodb">MongoDB</option>
              <option value="redis">Redis</option>
            </select>
          </div>

          <div class="form-group">
            <label for="environment">Entorno:</label>
            <select 
              v-model="formData.environment"
              id="environment"
              class="form-control"
            >
              <option value="development">Development</option>
              <option value="staging">Staging</option>
              <option value="production">Production</option>
            </select>
          </div>
        </div>

        <div class="form-group">
          <label class="checkbox-label">
            <input 
              v-model="formData.is_active"
              type="checkbox" 
              id="isActive"
            />
            <span class="checkmark"></span>
            Empresa activa
          </label>
          <small class="form-hint">Solo las empresas activas pueden procesar solicitudes</small>
        </div>
      </div>

      <!-- Información de negocio (para compatibilidad con script.js existente) -->
      <div class="form-section">
        <h5>🏢 Información de Negocio</h5>
        
        <div class="form-row">
          <div class="form-group">
            <label for="businessType">Tipo de Negocio:</label>
            <select 
              v-model="formData.business_type"
              id="businessType"
              class="form-control"
            >
              <option value="">Seleccionar...</option>
              <option value="spa">SPA & Wellness</option>
              <option value="healthcare">Healthcare</option>
              <option value="retail">Retail</option>
              <option value="technology">Technology</option>
              <option value="consulting">Consulting</option>
              <option value="other">Otro</option>
            </select>
          </div>

          <div class="form-group">
            <label for="subscriptionTier">Nivel de Suscripción:</label>
            <select 
              v-model="formData.subscription_tier"
              id="subscriptionTier"
              class="form-control"
            >
              <option value="basic">Basic</option>
              <option value="premium">Premium</option>
              <option value="enterprise">Enterprise</option>
            </select>
          </div>
        </div>

        <div class="form-group">
          <label for="services">Servicios Ofrecidos:</label>
          <textarea 
            v-model="formData.services"
            id="services"
            rows="3"
            placeholder="ej: relajación, bienestar y terapias holísticas"
            class="form-control"
          ></textarea>
        </div>
      </div>

      <!-- Configuración JSON avanzada -->
      <div class="form-section">
        <h5>🔧 Configuración Avanzada (JSON)</h5>
        
        <div class="form-group">
          <label for="configuration">Configuración JSON:</label>
          <textarea 
            v-model="formData.configuration"
            id="configuration"
            rows="8"
            placeholder='{"database_url": "postgresql://...", "api_keys": {...}, "features": [...]}'
            class="form-control json-editor"
            :class="{ 'json-invalid': !isValidJSON }"
          ></textarea>
          
          <div class="json-validation">
            <span v-if="isValidJSON" class="json-valid">✅ JSON válido</span>
            <span v-else-if="formData.configuration" class="json-invalid">❌ JSON inválido</span>
            <span v-else class="json-empty">💡 Configuración opcional</span>
          </div>
          
          <small class="form-hint">
            Configuración avanzada en formato JSON. Deje vacío si no es necesario.
          </small>
        </div>
      </div>

      <!-- Botones de acción -->
      <div class="form-actions">
        <button 
          type="button" 
          @click="handleCancel"
          class="btn btn-secondary"
          :disabled="isSaving"
        >
          ❌ Cancelar
        </button>
        
        <button 
          type="button"
          @click="resetForm"
          class="btn btn-outline"
          :disabled="isSaving"
        >
          🔄 Limpiar
        </button>
        
        <button 
          type="submit" 
          class="btn btn-primary"
          :disabled="isSaving || !isFormValid"
        >
          <span v-if="isSaving">⏳</span>
          <span v-else>{{ isEditMode ? '💾' : '➕' }}</span>
          {{ isSaving ? 'Guardando...' : (isEditMode ? 'Actualizar Empresa' : 'Crear Empresa Enterprise') }}
        </button>
      </div>
    </form>

    <!-- Resultado de la operación -->
    <div v-if="operationResult" class="operation-result">
      <div 
        id="enterpriseCreateResult" 
        class="create-result"
        :class="`result-container result-${operationResult.type}`"
      >
        <h5>{{ operationResult.title }}</h5>
        <p>{{ operationResult.message }}</p>
        
        <!-- Mostrar detalles adicionales si están disponibles -->
        <div v-if="operationResult.details" class="result-details">
          <div v-for="(value, key) in operationResult.details" :key="key" class="detail-item">
            <span class="status-indicator" :class="`status-${getStatusClass(value)}`"></span>
            {{ key }}: {{ formatDetailValue(value) }}
          </div>
        </div>
        
        <!-- Próximos pasos -->
        <div v-if="operationResult.nextSteps" class="next-steps">
          <h6>Próximos Pasos:</h6>
          <ol>
            <li v-for="step in operationResult.nextSteps" :key="step">{{ step }}</li>
          </ol>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'

// ============================================================================
// PROPS & EMITS
// ============================================================================

const props = defineProps({
  isEditMode: {
    type: Boolean,
    default: false
  },
  initialData: {
    type: Object,
    default: () => ({})
  },
  isSaving: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  'submit',
  'cancel',
  'update:formData'
])

// ============================================================================
// REACTIVE DATA
// ============================================================================

// Formulario de datos - PRESERVAR estructura exacta del script.js
const formData = ref({
  id: '',
  name: '',
  description: '',
  api_base_url: '',
  database_type: '',
  environment: 'development',
  is_active: true,
  business_type: '',
  subscription_tier: 'basic',
  services: '',
  configuration: ''
})

const operationResult = ref(null)

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

/**
 * Valida si el JSON de configuración es válido - MIGRADO del script.js
 * PRESERVAR: Comportamiento exacto de validación
 */
const isValidJSON = computed(() => {
  if (!formData.value.configuration) return true
  
  try {
    JSON.parse(formData.value.configuration)
    return true
  } catch (error) {
    return false
  }
})

/**
 * Valida si el formulario completo es válido
 */
const isFormValid = computed(() => {
  return formData.value.id && 
         formData.value.name && 
         isValidJSON.value
})

// ============================================================================
// WATCHERS
// ============================================================================

// Cargar datos iniciales cuando cambia la prop
watch(() => props.initialData, (newData) => {
  if (newData && Object.keys(newData).length > 0) {
    loadInitialData(newData)
  }
}, { immediate: true })

// Emitir cambios del formulario
watch(formData, (newData) => {
  emit('update:formData', newData)
}, { deep: true })

// ============================================================================
// METHODS
// ============================================================================

/**
 * Carga datos iniciales en el formulario - Para modo edición
 */
const loadInitialData = (data) => {
  formData.value = {
    id: data.id || data.company_id || '',
    name: data.name || '',
    description: data.description || '',
    api_base_url: data.api_base_url || '',
    database_type: data.database_type || '',
    environment: data.environment || 'development',
    is_active: data.is_active !== false,
    business_type: data.business_type || '',
    subscription_tier: data.subscription_tier || 'basic',
    services: data.services || '',
    configuration: data.configuration ? 
      (typeof data.configuration === 'string' ? 
        data.configuration : 
        JSON.stringify(data.configuration, null, 2)
      ) : ''
  }
}

/**
 * Maneja el envío del formulario
 */
const handleSubmit = () => {
  if (!isFormValid.value) {
    showError('Por favor complete todos los campos requeridos')
    return
  }

  if (!isValidJSON.value) {
    showError('La configuración JSON no es válida')
    return
  }

  // Preparar datos para envío - PRESERVAR formato exacto
  const submitData = {
    ...formData.value,
    configuration: formData.value.configuration ? 
      JSON.parse(formData.value.configuration) : {}
  }

  emit('submit', submitData)
}

/**
 * Maneja la cancelación
 */
const handleCancel = () => {
  operationResult.value = null
  emit('cancel')
}

/**
 * Resetea el formulario
 */
const resetForm = () => {
  formData.value = {
    id: '',
    name: '',
    description: '',
    api_base_url: '',
    database_type: '',
    environment: 'development',
    is_active: true,
    business_type: '',
    subscription_tier: 'basic',
    services: '',
    configuration: ''
  }
  operationResult.value = null
}

/**
 * Muestra resultado de operación
 */
const showResult = (type, title, message, details = null, nextSteps = null) => {
  operationResult.value = {
    type,
    title,
    message,
    details,
    nextSteps
  }
  
  // Scroll to result
  nextTick(() => {
    const resultElement = document.getElementById('enterpriseCreateResult')
    if (resultElement) {
      resultElement.scrollIntoView({ behavior: 'smooth' })
    }
  })
}

/**
 * Muestra error
 */
const showError = (message) => {
  showResult('error', '❌ Error', message)
}

/**
 * Obtiene clase de status para indicadores
 */
const getStatusClass = (value) => {
  if (typeof value === 'boolean') {
    return value ? 'success' : 'error'
  }
  return 'info'
}

/**
 * Formatea valor para mostrar
 */
const formatDetailValue = (value) => {
  if (typeof value === 'boolean') {
    return value ? '✅' : '❌'
  }
  return value
}

// ============================================================================
// EXPOSE METHODS (Para uso desde componente padre)
// ============================================================================

defineExpose({
  resetForm,
  showResult,
  showError,
  loadInitialData
})
</script>

<style scoped>
/* ============================================================================ */
/* ESTILOS DEL FORMULARIO - Siguiendo el estilo actual del proyecto */
/* ============================================================================ */

.enterprise-company-form {
  background: white;
  border-radius: 8px;
  padding: 25px;
  margin: 20px 0;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

/* Header */
.form-header {
  margin-bottom: 25px;
  padding-bottom: 15px;
  border-bottom: 2px solid #e9ecef;
}

.form-header h4 {
  margin: 0 0 8px 0;
  color: #333;
  font-size: 1.3em;
}

.form-description {
  margin: 0;
  color: #6c757d;
  font-size: 1em;
}

/* Secciones del formulario */
.form-section {
  margin-bottom: 30px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 6px;
  border-left: 4px solid #007bff;
}

.form-section h5 {
  margin: 0 0 20px 0;
  color: #333;
  font-size: 1.1em;
  padding-bottom: 10px;
  border-bottom: 1px solid #dee2e6;
}

/* Grupos de formulario */
.form-group {
  margin-bottom: 20px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-weight: 600;
  color: #495057;
  font-size: 0.95em;
}

.form-control {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 0.95em;
  transition: border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
}

.form-control:focus {
  outline: 0;
  border-color: #80bdff;
  box-shadow: 0 0 0 0.2rem rgba(0,123,255,.25);
}

.form-control:disabled {
  background-color: #e9ecef;
  opacity: 1;
}

/* Textarea específico para JSON */
.json-editor {
  font-family: 'Courier New', monospace;
  font-size: 0.9em;
}

.json-invalid {
  border-color: #dc3545 !important;
  box-shadow: 0 0 0 0.2rem rgba(220,53,69,.25) !important;
}

/* Validación de JSON */
.json-validation {
  margin-top: 6px;
  font-size: 0.85em;
}

.json-valid {
  color: #28a745;
  font-weight: 600;
}

.json-invalid {
  color: #dc3545;
  font-weight: 600;
}

.json-empty {
  color: #6c757d;
}

/* Checkbox personalizado */
.checkbox-label {
  display: flex !important;
  align-items: center;
  cursor: pointer;
  margin-bottom: 0 !important;
  font-weight: normal !important;
}

.checkbox-label input[type="checkbox"] {
  margin-right: 10px;
  transform: scale(1.2);
}

/* Hints */
.form-hint {
  display: block;
  margin-top: 4px;
  color: #6c757d;
  font-size: 0.85em;
}

/* Acciones */
.form-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #dee2e6;
  flex-wrap: wrap;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  font-size: 0.95em;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: #007bff;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #0056b3;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #545b62;
}

.btn-outline {
  background: transparent;
  color: #007bff;
  border: 1px solid #007bff;
}

.btn-outline:hover:not(:disabled) {
  background: #007bff;
  color: white;
}

/* Resultado de operación */
.operation-result {
  margin-top: 25px;
}

.result-container {
  padding: 20px;
  border-radius: 6px;
  border-left: 4px solid;
}

.result-success {
  background: #d4edda;
  border-left-color: #28a745;
  color: #155724;
}

.result-error {
  background: #f8d7da;
  border-left-color: #dc3545;
  color: #721c24;
}

.result-info {
  background: #d1ecf1;
  border-left-color: #17a2b8;
  color: #0c5460;
}

.result-container h5 {
  margin: 0 0 10px 0;
  font-size: 1.1em;
}

.result-container p {
  margin: 0 0 15px 0;
}

/* Detalles del resultado */
.result-details {
  margin: 15px 0;
}

.detail-item {
  display: flex;
  align-items: center;
  margin-bottom: 6px;
  font-size: 0.9em;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 8px;
}

.status-success {
  background: #28a745;
}

.status-error {
  background: #dc3545;
}

.status-info {
  background: #17a2b8;
}

/* Próximos pasos */
.next-steps {
  margin-top: 15px;
}

.next-steps h6 {
  margin: 0 0 8px 0;
  font-size: 1em;
}

.next-steps ol {
  margin: 0;
  padding-left: 20px;
}

.next-steps li {
  margin-bottom: 4px;
  font-size: 0.9em;
}

/* Responsive */
@media (max-width: 768px) {
  .form-row {
    grid-template-columns: 1fr;
  }
  
  .form-actions {
    flex-direction: column;
  }
  
  .btn {
    justify-content: center;
  }
}
</style>
