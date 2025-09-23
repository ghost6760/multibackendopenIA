<template>
  <div class="enterprise-company-form">
    <!-- Header del formulario -->
    <div class="form-header">
      <h4>
        {{ isEditMode ? '✏️ Editar Empresa Enterprise' : '➕ Crear Nueva Empresa Enterprise' }}
      </h4>
      <p class="form-description">
        {{ isEditMode ? 'Modifica los datos de la empresa enterprise' : 'Complete los datos básicos para crear una nueva empresa enterprise' }}
      </p>
    </div>

    <!-- Formulario principal - ✅ CAMPOS EXACTOS DE script.js -->
    <form @submit.prevent="handleSubmit" class="enterprise-form">
      
      <!-- ✅ SECCIÓN BÁSICA - CAMPOS OBLIGATORIOS EXACTOS como script.js -->
      <div class="form-section">
        <h5>📋 Información Básica</h5>
        
        <div class="form-group">
          <label for="companyId">ID de empresa (solo minúsculas, números y _):</label>
          <input 
            v-model="formData.company_id"
            type="text" 
            id="companyId"
            :disabled="isEditMode"
            required
            pattern="[a-z0-9_]+"
            title="Solo letras minúsculas, números y guiones bajos"
            placeholder="ej: spa_wellness"
            class="form-control"
            :class="{ 'form-error': errors.company_id }"
          />
          <small v-if="errors.company_id" class="form-error-text">{{ errors.company_id }}</small>
          <small v-else class="form-hint">
            {{ isEditMode ? 'El ID no se puede modificar' : 'Identificador único (solo letras minúsculas, números, _)' }}
          </small>
        </div>

        <div class="form-group">
          <label for="companyName">Nombre de empresa:</label>
          <input 
            v-model="formData.company_name"
            type="text" 
            id="companyName"
            required
            placeholder="ej: Wellness Spa & Relax"
            class="form-control"
            :class="{ 'form-error': errors.company_name }"
          />
          <small v-if="errors.company_name" class="form-error-text">{{ errors.company_name }}</small>
        </div>

        <div class="form-group">
          <label for="businessType">Tipo de negocio:</label>
          <select 
            v-model="formData.business_type"
            id="businessType"
            required
            class="form-control"
            :class="{ 'form-error': errors.business_type }"
          >
            <option value="">Seleccionar tipo</option>
            <option value="healthcare">Salud</option>
            <option value="beauty">Belleza</option>
            <option value="dental">Dental</option>
            <option value="general">General</option>
          </select>
          <small v-if="errors.business_type" class="form-error-text">{{ errors.business_type }}</small>
        </div>

        <div class="form-group full-width">
          <label for="services">Servicios ofrecidos:</label>
          <textarea 
            v-model="formData.services"
            id="services"
            required 
            rows="3"
            placeholder="relajación, bienestar y terapias holísticas"
            class="form-control"
            :class="{ 'form-error': errors.services }"
          ></textarea>
          <small v-if="errors.services" class="form-error-text">{{ errors.services }}</small>
        </div>

        <div class="form-group">
          <label for="agentName">Nombre del agente de ventas:</label>
          <input 
            v-model="formData.sales_agent_name"
            type="text" 
            id="agentName"
            required
            placeholder="ej: Ana, terapeuta especialista de Wellness Spa"
            class="form-control"
            :class="{ 'form-error': errors.sales_agent_name }"
          />
          <small v-if="errors.sales_agent_name" class="form-error-text">{{ errors.sales_agent_name }}</small>
        </div>
      </div>

      <!-- ✅ SECCIÓN DE CONFIGURACIÓN - EXACTA como script.js -->
      <div class="form-section">
        <h5>⚙️ Configuración</h5>
        
        <div class="form-group">
          <label for="scheduleUrl">URL del servicio de programación:</label>
          <input 
            v-model="formData.schedule_service_url"
            type="url" 
            id="scheduleUrl"
            placeholder="http://127.0.0.1:4043"
            class="form-control"
          />
          <small class="form-hint">URL del servicio de agendamiento (opcional)</small>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="timezone">Zona horaria:</label>
            <select 
              v-model="formData.timezone"
              id="timezone"
              required
              class="form-control"
            >
              <option value="America/Bogota">America/Bogota</option>
              <option value="America/Mexico_City">America/Mexico_City</option>
              <option value="America/Lima">America/Lima</option>
              <option value="America/New_York">America/New_York</option>
            </select>
          </div>

          <div class="form-group">
            <label for="currency">Moneda:</label>
            <select 
              v-model="formData.currency"
              id="currency"
              required
              class="form-control"
            >
              <option value="COP">COP</option>
              <option value="USD">USD</option>
              <option value="EUR">EUR</option>
              <option value="MXN">MXN</option>
            </select>
          </div>
        </div>

        <div class="form-group">
          <label for="subscriptionTier">Plan de suscripción:</label>
          <select 
            v-model="formData.subscription_tier"
            id="subscriptionTier"
            required
            class="form-control"
          >
            <option value="basic">Basic</option>
            <option value="premium">Premium</option>
            <option value="enterprise">Enterprise</option>
          </select>
        </div>
      </div>

      <!-- Indicador de validación en tiempo real -->
      <div v-if="Object.keys(errors).length > 0" class="validation-summary">
        <h6>⚠️ Errores de validación:</h6>
        <ul>
          <li v-for="(error, field) in errors" :key="field">{{ error }}</li>
        </ul>
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
        class="result-container"
        :class="`result-${operationResult.type}`"
      >
        <h5>{{ operationResult.title }}</h5>
        <p>{{ operationResult.message }}</p>
        
        <!-- ✅ MOSTRAR DETALLES DE SETUP COMO script.js -->
        <div v-if="operationResult.setup_status" class="setup-status">
          <h6>Estado de Configuración:</h6>
          <div class="setup-items">
            <div 
              v-for="(status, key) in operationResult.setup_status" 
              :key="key"
              class="setup-item"
            >
              <span class="status-indicator" :class="`status-${getStatusClass(status)}`"></span>
              {{ formatSetupKey(key) }}: {{ formatSetupValue(status) }}
            </div>
          </div>
        </div>
        
        <!-- ✅ PRÓXIMOS PASOS COMO script.js -->
        <div v-if="operationResult.next_steps" class="next-steps">
          <h6>Próximos Pasos:</h6>
          <ol>
            <li v-for="step in operationResult.next_steps" :key="step">{{ step }}</li>
          </ol>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'

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
  'cancel'
])

// ============================================================================
// REACTIVE DATA - ✅ ESTRUCTURA EXACTA COMO script.js
// ============================================================================
const formData = ref({
  company_id: '',
  company_name: '',
  business_type: '',
  services: '',
  sales_agent_name: '',
  schedule_service_url: '',
  timezone: 'America/Bogota',
  currency: 'COP',
  subscription_tier: 'basic'
})

const errors = ref({})
const operationResult = ref(null)

// ============================================================================
// COMPUTED PROPERTIES - ✅ VALIDACIONES EXACTAS COMO script.js
// ============================================================================
const isFormValid = computed(() => {
  // ✅ Validaciones obligatorias exactas de script.js
  return formData.value.company_id?.toString().trim() &&
         formData.value.company_name?.toString().trim() &&
         formData.value.services?.toString().trim() &&
         formData.value.business_type &&
         formData.value.sales_agent_name?.toString().trim() &&
         Object.keys(errors.value).length === 0
})

// ============================================================================
// WATCHERS - VALIDACIÓN EN TIEMPO REAL
// ============================================================================
watch(() => formData.value.company_id, (newVal) => {
  if (newVal && !/^[a-z0-9_]*$/.test(newVal)) {
    errors.value.company_id = 'Solo letras minúsculas, números y guiones bajos'
  } else if (newVal && newVal.trim() === '') {
    errors.value.company_id = 'El ID de empresa es obligatorio'
  } else {
    delete errors.value.company_id
  }
})

watch(() => formData.value.company_name, (newVal) => {
  if (!newVal || !newVal.toString().trim()) {
    errors.value.company_name = 'El nombre de empresa es obligatorio'
  } else {
    delete errors.value.company_name
  }
})

watch(() => formData.value.services, (newVal) => {
  if (!newVal || !newVal.toString().trim()) {
    errors.value.services = 'Los servicios son obligatorios'
  } else {
    delete errors.value.services
  }
})

watch(() => formData.value.business_type, (newVal) => {
  if (!newVal) {
    errors.value.business_type = 'El tipo de negocio es obligatorio'
  } else {
    delete errors.value.business_type
  }
})

watch(() => formData.value.sales_agent_name, (newVal) => {
  if (!newVal || !newVal.toString().trim()) {
    errors.value.sales_agent_name = 'El nombre del agente es obligatorio'
  } else {
    delete errors.value.sales_agent_name
  }
})

// Cargar datos iniciales
watch(() => props.initialData, (newData) => {
  if (newData && Object.keys(newData).length > 0) {
    loadInitialData(newData)
  }
}, { immediate: true })

// ============================================================================
// METHODS - ✅ COMPATIBLES CON script.js
// ============================================================================
const loadInitialData = (data) => {
  // ✅ Solo cargar campos que usa script.js
  formData.value = {
    company_id: data.company_id || data.id || '',
    company_name: data.company_name || data.name || '',
    business_type: data.business_type || '',
    services: data.services || '',
    sales_agent_name: data.sales_agent_name || '',
    schedule_service_url: data.schedule_service_url || '',
    timezone: data.timezone || 'America/Bogota',
    currency: data.currency || 'COP',
    subscription_tier: data.subscription_tier || 'basic'
  }
  // Limpiar errores al cargar datos
  errors.value = {}
}

const handleSubmit = () => {
  // ✅ Validación final exacta como script.js
  if (!isFormValid.value) {
    showError('Por favor complete todos los campos requeridos correctamente')
    return
  }

  // ✅ Preparar datos exacto como script.js (estructura idéntica)
  const submitData = {
    company_id: formData.value.company_id.toString().trim(),
    company_name: formData.value.company_name.toString().trim(),
    business_type: formData.value.business_type,
    services: formData.value.services.toString().trim(),
    sales_agent_name: formData.value.sales_agent_name.toString().trim(),
    schedule_service_url: formData.value.schedule_service_url?.toString().trim() || '',
    timezone: formData.value.timezone,
    currency: formData.value.currency,
    subscription_tier: formData.value.subscription_tier
  }

  emit('submit', submitData)
}

const handleCancel = () => {
  operationResult.value = null
  emit('cancel')
}

const resetForm = () => {
  // ✅ Reset exacto como script.js
  formData.value = {
    company_id: '',
    company_name: '',
    business_type: '',
    services: '',
    sales_agent_name: '',
    schedule_service_url: '',
    timezone: 'America/Bogota',
    currency: 'COP',
    subscription_tier: 'basic'
  }
  errors.value = {}
  operationResult.value = null
}

const showResult = (type, title, message, details = null) => {
  operationResult.value = {
    type,
    title,
    message,
    setup_status: details?.setup_status,
    next_steps: details?.next_steps
  }
}

const showError = (message) => {
  showResult('error', '❌ Error', message)
}

// ============================================================================
// HELPERS PARA DISPLAY - ✅ COMPATIBLES CON script.js
// ============================================================================
const getStatusClass = (value) => {
  if (typeof value === 'boolean') {
    return value ? 'success' : 'error'
  }
  if (typeof value === 'string') {
    const v = value.toLowerCase()
    if (v.includes('success') || v.includes('ok') || v.includes('✅')) return 'success'
    if (v.includes('error') || v.includes('fail') || v.includes('❌')) return 'error'
  }
  return 'info'
}

const formatSetupKey = (key) => {
  if (!key) return ''
  return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

const formatSetupValue = (value) => {
  if (typeof value === 'boolean') {
    return value ? '✅ Configurado' : '❌ Pendiente'
  }
  return value
}

// ============================================================================
// EXPOSE METHODS
// ============================================================================
defineExpose({
  resetForm,
  showResult,
  showError,
  loadInitialData
})

// onMounted - protección adicional
onMounted(() => {
  if (props.initialData && Object.keys(props.initialData).length > 0) {
    loadInitialData(props.initialData)
  }
})
</script>

<style scoped>
/* ✅ ESTILOS OPTIMIZADOS - Diseño limpio y consistente */
.enterprise-company-form {
  background: white;
  border-radius: 8px;
  padding: 25px;
  margin: 20px 0;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

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

.form-group {
  margin-bottom: 20px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.form-group.full-width {
  grid-column: 1 / -1;
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

.form-control.form-error {
  border-color: #dc3545;
  box-shadow: 0 0 0 0.2rem rgba(220,53,69,.25);
}

.form-hint {
  display: block;
  margin-top: 4px;
  color: #6c757d;
  font-size: 0.85em;
}

.form-error-text {
  display: block;
  margin-top: 4px;
  color: #dc3545;
  font-size: 0.85em;
  font-weight: 500;
}

.validation-summary {
  background: #f8d7da;
  border: 1px solid #f5c6cb;
  border-radius: 4px;
  padding: 15px;
  margin: 20px 0;
  color: #721c24;
}

.validation-summary h6 {
  margin: 0 0 10px 0;
}

.validation-summary ul {
  margin: 0;
  padding-left: 20px;
}

.validation-summary li {
  margin-bottom: 5px;
}

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
  transform: translateY(-1px);
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

.result-container h5 {
  margin: 0 0 10px 0;
  font-size: 1.1em;
}

.result-container p {
  margin: 0 0 15px 0;
}

.setup-status {
  margin: 15px 0;
}

.setup-status h6 {
  margin: 0 0 10px 0;
  font-size: 1em;
}

.setup-items {
  display: grid;
  gap: 8px;
}

.setup-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9em;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
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
