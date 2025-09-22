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
    <form @submit.prevent="handleSubmit" class="enterprise-form">
      <!-- Información básica -->
      <div class="form-section">
        <h5>📋 Información Básica</h5>
        
        <div class="form-group">
          <label for="companyId">ID de la Empresa *:</label>
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
            :class="{ 'error': validationErrors.company_id }"
          />
          <small v-if="validationErrors.company_id" class="error-message">
            {{ validationErrors.company_id }}
          </small>
          <small v-else class="form-hint">
            {{ isEditMode ? 'El ID no se puede modificar' : 'Identificador único (solo letras minúsculas, números, _)' }}
          </small>
        </div>

        <div class="form-group">
          <label for="companyName">Nombre de la Empresa *:</label>
          <input 
            v-model="formData.company_name"
            type="text" 
            id="companyName"
            required
            placeholder="ej: Wellness Spa & Relax"
            class="form-control"
            :class="{ 'error': validationErrors.company_name }"
          />
          <small v-if="validationErrors.company_name" class="error-message">
            {{ validationErrors.company_name }}
          </small>
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

      <!-- Información de negocio -->
      <div class="form-section">
        <h5>🏢 Información de Negocio</h5>
        
        <div class="form-row">
          <div class="form-group">
            <label for="businessType">Tipo de Negocio *:</label>
            <select 
              v-model="formData.business_type"
              id="businessType"
              required
              class="form-control"
            >
              <option value="">Seleccionar tipo</option>
              <option value="spa">SPA & Wellness</option>
              <option value="healthcare">Salud</option>
              <option value="beauty">Belleza</option>
              <option value="dental">Dental</option>
              <option value="retail">Retail</option>
              <option value="technology">Tecnología</option>
              <option value="consulting">Consultoría</option>
              <option value="general">General</option>
            </select>
          </div>

          <div class="form-group">
            <label for="subscriptionTier">Nivel de Suscripción *:</label>
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

        <div class="form-group">
          <label for="services">Servicios Ofrecidos *:</label>
          <textarea 
            v-model="formData.services"
            id="services"
            required 
            rows="3" 
            placeholder="ej: relajación, bienestar y terapias holísticas"
            class="form-control"
            :class="{ 'error': validationErrors.services }"
          ></textarea>
          <small v-if="validationErrors.services" class="error-message">
            {{ validationErrors.services }}
          </small>
        </div>
      </div>

      <!-- Configuración del agente -->
      <div class="form-section">
        <h5>🤖 Configuración del Agente</h5>
        
        <div class="form-group">
          <label for="agentName">Nombre del Agente de Ventas *:</label>
          <input 
            v-model="formData.sales_agent_name"
            type="text" 
            id="agentName"
            required
            placeholder="ej: Ana, terapeuta especialista de Wellness Spa"
            class="form-control"
          />
          <small class="form-hint">
            Nombre y rol del agente que interactuará con los clientes
          </small>
        </div>

        <div class="form-group">
          <label for="scheduleUrl">URL del Servicio de Programación:</label>
          <input 
            v-model="formData.schedule_service_url"
            type="url" 
            id="scheduleUrl"
            placeholder="http://127.0.0.1:4043"
            class="form-control"
            :class="{ 'error': validationErrors.schedule_service_url }"
          />
          <small v-if="validationErrors.schedule_service_url" class="error-message">
            {{ validationErrors.schedule_service_url }}
          </small>
          <small v-else class="form-hint">
            URL del servicio externo para gestión de citas y horarios
          </small>
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
            placeholder="https://api.mi-empresa.com"
            class="form-control"
            :class="{ 'error': validationErrors.api_base_url }"
          />
          <small v-if="validationErrors.api_base_url" class="error-message">
            {{ validationErrors.api_base_url }}
          </small>
          <small v-else class="form-hint">
            URL base para las llamadas API específicas de esta empresa
          </small>
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
            <label for="environment">Entorno *:</label>
            <select 
              v-model="formData.environment"
              id="environment"
              required
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

      <!-- Configuración regional -->
      <div class="form-section">
        <h5>🌍 Configuración Regional</h5>
        
        <div class="form-row">
          <div class="form-group">
            <label for="timezone">Zona Horaria *:</label>
            <select 
              v-model="formData.timezone"
              id="timezone"
              required
              class="form-control"
            >
              <option value="America/Bogota">America/Bogota (UTC-5)</option>
              <option value="America/Mexico_City">America/Mexico_City (UTC-6)</option>
              <option value="America/Lima">America/Lima (UTC-5)</option>
              <option value="America/New_York">America/New_York (UTC-5/-4)</option>
              <option value="Europe/Madrid">Europe/Madrid (UTC+1/+2)</option>
              <option value="America/Los_Angeles">America/Los_Angeles (UTC-8/-7)</option>
            </select>
          </div>

          <div class="form-group">
            <label for="currency">Moneda *:</label>
            <select 
              v-model="formData.currency"
              id="currency"
              required
              class="form-control"
            >
              <option value="COP">COP (Peso Colombiano)</option>
              <option value="USD">USD (Dólar Americano)</option>
              <option value="EUR">EUR (Euro)</option>
              <option value="MXN">MXN (Peso Mexicano)</option>
              <option value="PEN">PEN (Sol Peruano)</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Configuración avanzada -->
      <div class="form-section">
        <h5>🔧 Configuración Avanzada (Opcional)</h5>
        
        <div class="form-group">
          <label for="configuration">Configuración JSON:</label>
          <textarea 
            v-model="configurationJson"
            id="configuration"
            rows="8"
            placeholder='{"database_url": "postgresql://...", "api_keys": {...}, "features": [...]}'
            class="form-control json-editor"
            :class="{ 'json-invalid': !isValidConfigJSON }"
          ></textarea>
          
          <div class="json-validation">
            <span v-if="isValidConfigJSON" class="json-valid">✅ JSON válido</span>
            <span v-else-if="configurationJson" class="json-invalid">❌ JSON inválido</span>
            <span v-else class="json-empty">💡 Configuración opcional</span>
          </div>
          
          <small class="form-hint">
            Configuración avanzada en formato JSON. Deje vacío si no es necesario.
          </small>
        </div>
        
        <div class="form-group">
          <label for="notes">Notas Adicionales:</label>
          <textarea 
            v-model="formData.notes"
            id="notes"
            rows="3"
            placeholder="Notas internas sobre la empresa..."
            class="form-control"
          ></textarea>
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
        class="result-container"
        :class="`result-${operationResult.type}`"
      >
        <h5>{{ operationResult.title }}</h5>
        <p>{{ operationResult.message }}</p>
        
        <!-- Mostrar detalles adicionales si están disponibles -->
        <div v-if="operationResult.details" class="result-details">
          <div v-for="(value, key) in operationResult.details" :key="key" class="detail-item">
            <span class="status-indicator" :class="`status-${getStatusClass(value)}`"></span>
            {{ formatKey(key) }}: {{ formatDetailValue(value) }}
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
import { useEnterprise } from '@/composables/useEnterprise'

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
// COMPOSABLES
// ============================================================================

const { validateCompanyData } = useEnterprise()

// ============================================================================
// REACTIVE DATA
// ============================================================================

// Formulario de datos - estructura exacta del composable
const formData = ref({
  company_id: '',
  company_name: '',
  description: '',
  business_type: '',
  services: '',
  sales_agent_name: '',
  schedule_service_url: '',
  api_base_url: '',
  database_type: '',
  timezone: 'America/Bogota',
  currency: 'COP',
  environment: 'development',
  subscription_tier: 'basic',
  is_active: true,
  configuration: {},
  notes: ''
})

const configurationJson = ref('')
const operationResult = ref(null)
const validationErrors = ref({})

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

/**
 * Valida si el JSON de configuración es válido
 */
const isValidConfigJSON = computed(() => {
  if (!configurationJson.value.trim()) return true
  
  try {
    JSON.parse(configurationJson.value)
    return true
  } catch (error) {
    return false
  }
})

/**
 * Valida si el formulario completo es válido
 */
const isFormValid = computed(() => {
  return formData.value.company_id.trim() && 
         formData.value.company_name.trim() && 
         formData.value.services.trim() &&
         isValidConfigJSON.value &&
         Object.keys(validationErrors.value).length === 0
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

// Validar en tiempo real
watch(formData, (newData) => {
  validateForm(newData)
}, { deep: true })

// Sincronizar configuración JSON con formData
watch(configurationJson, (newJson) => {
  if (isValidConfigJSON.value) {
    try {
      formData.value.configuration = newJson ? JSON.parse(newJson) : {}
    } catch (error) {
      // JSON inválido, mantener configuración anterior
    }
  }
})

// ============================================================================
// METHODS
// ============================================================================

/**
 * Carga datos iniciales en el formulario
 */
const loadInitialData = (data) => {
  formData.value = {
    company_id: data.company_id || '',
    company_name: data.company_name || data.name || '',
    description: data.description || '',
    business_type: data.business_type || '',
    services: data.services || '',
    sales_agent_name: data.sales_agent_name || '',
    schedule_service_url: data.schedule_service_url || '',
    api_base_url: data.api_base_url || '',
    database_type: data.database_type || '',
    timezone: data.timezone || 'America/Bogota',
    currency: data.currency || 'COP',
    environment: data.environment || 'development',
    subscription_tier: data.subscription_tier || 'basic',
    is_active: data.is_active !== false,
    configuration: data.configuration || {},
    notes: data.notes || ''
  }

  // Cargar configuración JSON
  configurationJson.value = data.configuration ? 
    JSON.stringify(data.configuration, null, 2) : ''
}

/**
 * Validar formulario usando el composable
 */
const validateForm = (data) => {
  const errors = validateCompanyData(data)
  validationErrors.value = {}
  
  errors.forEach(error => {
    if (error.includes('ID de empresa')) {
      validationErrors.value.company_id = error
    } else if (error.includes('Nombre de empresa')) {
      validationErrors.value.company_name = error
    } else if (error.includes('Servicios')) {
      validationErrors.value.services = error
    } else if (error.includes('URL del servicio de agenda')) {
      validationErrors.value.schedule_service_url = error
    } else if (error.includes('URL base de API')) {
      validationErrors.value.api_base_url = error
    }
  })
}

/**
 * Maneja el envío del formulario
 */
const handleSubmit = () => {
  if (!isFormValid.value) {
    showError('Por favor complete todos los campos requeridos correctamente')
    return
  }

  if (!isValidConfigJSON.value) {
    showError('La configuración JSON no es válida')
    return
  }

  // Preparar datos para envío con configuración parseada
  const submitData = {
    ...formData.value,
    configuration: configurationJson.value ? 
      JSON.parse(configurationJson.value) : {}
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
    company_id: '',
    company_name: '',
    description: '',
    business_type: '',
    services: '',
    sales_agent_name: '',
    schedule_service_url: '',
    api_base_url: '',
    database_type: '',
    timezone: 'America/Bogota',
    currency: 'COP',
    environment: 'development',
    subscription_tier: 'basic',
    is_active: true,
    configuration: {},
    notes: ''
  }
  configurationJson.value = ''
  operationResult.value = null
  validationErrors.value = {}
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
    const resultElement = document.querySelector('.operation-result')
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
  if (typeof value === 'string') {
    const lower = value.toLowerCase()
    if (lower.includes('success') || lower.includes('ok')) return 'success'
    if (lower.includes('error') || lower.includes('fail')) return 'error'
    if (lower.includes('warning')) return 'warning'
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

/**
 * Formatea clave para mostrar
 */
const formatKey = (key) => {
  return key
    .replace(/_/g, ' ')
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

// ============================================================================
// EXPOSE METHODS (Para uso desde componente padre)
// ============================================================================

defineExpose({
  resetForm,
  showResult,
  showError,
  loadInitialData,
  validateForm
})
</script>

<style scoped>
/* Reutilizar estilos del original con mejoras para validación */
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

/* Estados de error */
.form-control.error {
  border-color: #dc3545;
  box-shadow: 0 0 0 0.2rem rgba(220,53,69,.25);
}

.error-message {
  display: block;
  margin-top: 4px;
  color: #dc3545;
  font-size: 0.85em;
  font-weight: 500;
}

.json-editor {
  font-family: 'Courier New', monospace;
  font-size: 0.9em;
}

.json-invalid {
  border-color: #dc3545 !important;
  box-shadow: 0 0 0 0.2rem rgba(220,53,69,.25) !important;
}

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

.form-hint {
  display: block;
  margin-top: 4px;
  color: #6c757d;
  font-size: 0.85em;
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

.status-warning {
  background: #ffc107;
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
