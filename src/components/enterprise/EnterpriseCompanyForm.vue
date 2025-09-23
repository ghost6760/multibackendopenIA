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
      
      <!-- ✅ SECCIÓN 1: Información básica (EXACTA como script.js) -->
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
          />
          <small class="form-hint">
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
          />
        </div>

        <div class="form-group">
          <label for="businessType">Tipo de negocio:</label>
          <select 
            v-model="formData.business_type"
            id="businessType"
            required
            class="form-control"
          >
            <option value="">Seleccionar tipo</option>
            <option value="healthcare">Salud</option>
            <option value="beauty">Belleza</option>
            <option value="dental">Dental</option>
            <option value="spa">SPA & Wellness</option>
            <option value="general">General</option>
          </select>
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
          ></textarea>
        </div>
      </div>

      <!-- ✅ SECCIÓN 2: Configuración de Agente (EXACTA como script.js) -->
      <div class="form-section">
        <h5>🤖 Configuración de Agente</h5>
        
        <div class="form-group">
          <label for="agentName">Nombre del agente de ventas:</label>
          <input 
            v-model="formData.sales_agent_name"
            type="text" 
            id="agentName"
            required
            placeholder="ej: Ana, terapeuta especialista de Wellness Spa"
            class="form-control"
          />
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="modelName">Modelo:</label>
            <select 
              v-model="formData.model_name"
              id="modelName"
              class="form-control"
            >
              <option value="gpt-4o-mini">gpt-4o-mini</option>
              <option value="gpt-4o">gpt-4o</option>
              <option value="gpt-3.5-turbo">gpt-3.5-turbo</option>
            </select>
          </div>
          
          <div class="form-group">
            <label for="maxTokens">Max Tokens:</label>
            <input 
              v-model.number="formData.max_tokens"
              type="number" 
              id="maxTokens"
              min="50"
              max="500"
              placeholder="150"
              class="form-control"
            />
          </div>
        </div>

        <div class="form-group">
          <label for="temperature">Temperature (0.0 - 1.0):</label>
          <input 
            v-model.number="formData.temperature"
            type="range" 
            id="temperature"
            min="0"
            max="1"
            step="0.1"
            class="form-control"
          />
          <small class="form-hint">Actual: {{ formData.temperature }}</small>
        </div>
      </div>

      <!-- ✅ SECCIÓN 3: Integración de Agenda (EXACTA como script.js) -->
      <div class="form-section">
        <h5>🔗 Integración de Agenda</h5>
        
        <div class="form-group">
          <label for="scheduleUrl">URL del servicio de programación:</label>
          <input 
            v-model="formData.schedule_service_url"
            type="url" 
            id="scheduleUrl"
            placeholder="http://127.0.0.1:4043"
            class="form-control"
          />
          <small class="form-hint">URL del servicio de agendamiento externo</small>
        </div>

        <div class="form-group">
          <label>Duraciones de tratamiento (JSON):</label>
          <textarea 
            v-model="formData.treatment_durations_json"
            rows="4"
            placeholder='{"masaje_relajante": 60, "facial_hidratante": 45, "terapia_corporal": 90}'
            class="form-control json-editor"
            :class="{ 'json-invalid': !isValidTreatmentDurationsJSON }"
          ></textarea>
          <div class="json-validation">
            <span v-if="isValidTreatmentDurationsJSON" class="json-valid">✅ JSON válido</span>
            <span v-else-if="formData.treatment_durations_json" class="json-invalid">❌ JSON inválido</span>
            <span v-else class="json-empty">💡 Configuración opcional</span>
          </div>
        </div>
      </div>

      <!-- ✅ SECCIÓN 4: Configuración Regional (EXACTA como script.js) -->
      <div class="form-section">
        <h5>🌍 Configuración Regional</h5>
        
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
              <option value="Europe/Madrid">Europe/Madrid</option>
            </select>
          </div>

          <div class="form-group">
            <label for="language">Idioma:</label>
            <select 
              v-model="formData.language"
              id="language"
              class="form-control"
            >
              <option value="es">Español</option>
              <option value="en">English</option>
              <option value="pt">Português</option>
            </select>
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="currency">Moneda:</label>
            <select 
              v-model="formData.currency"
              id="currency"
              required
              class="form-control"
            >
              <option value="COP">COP - Peso Colombiano</option>
              <option value="USD">USD - Dólar Americano</option>
              <option value="EUR">EUR - Euro</option>
              <option value="MXN">MXN - Peso Mexicano</option>
              <option value="PEN">PEN - Nuevo Sol</option>
            </select>
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
      </div>

      <!-- ✅ SECCIÓN 5: Configuración Técnica Adicional (Para completitud) -->
      <div class="form-section">
        <h5>⚙️ Configuración Técnica</h5>
        
        <div class="form-row">
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

          <div class="form-group">
            <label for="databaseType">Tipo de base de datos:</label>
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
            </select>
          </div>
        </div>

        <div class="form-group">
          <label for="apiBaseUrl">API Base URL:</label>
          <input 
            v-model="formData.api_base_url"
            type="url" 
            id="apiBaseUrl"
            placeholder="https://api.empresa.com"
            class="form-control"
          />
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

      <!-- ✅ SECCIÓN 6: Notas adicionales -->
      <div class="form-section">
        <h5>📝 Información Adicional</h5>
        
        <div class="form-group">
          <label for="description">Descripción:</label>
          <textarea 
            v-model="formData.description"
            id="description"
            rows="3"
            placeholder="Descripción de la empresa..."
            class="form-control"
          ></textarea>
        </div>

        <div class="form-group">
          <label for="notes">Notas:</label>
          <textarea 
            v-model="formData.notes"
            id="notes"
            rows="3"
            placeholder="Notas adicionales sobre la empresa"
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
  'cancel',
  'update:formData'
])

// ============================================================================
// REACTIVE DATA - ESTRUCTURA EXACTA COMO script.js
// ============================================================================

const formData = ref({
  // ✅ CAMPOS BÁSICOS (obligatorios en script.js)
  company_id: '',
  company_name: '',
  business_type: '',
  services: '',
  
  // ✅ CONFIGURACIÓN DE AGENTE (como script.js)
  sales_agent_name: '',
  model_name: 'gpt-4o-mini',
  max_tokens: 150,
  temperature: 0.7,
  
  // ✅ INTEGRACIÓN DE AGENDA (como script.js)
  schedule_service_url: '',
  treatment_durations: {},
  treatment_durations_json: '',
  
  // ✅ CONFIGURACIÓN REGIONAL (como script.js)
  timezone: 'America/Bogota',
  language: 'es',
  currency: 'COP',
  subscription_tier: 'basic',
  
  // ✅ TÉCNICO ADICIONAL
  environment: 'development',
  database_type: '',
  api_base_url: '',
  is_active: true,
  description: '',
  notes: ''
})

const operationResult = ref(null)

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

/**
 * ✅ VALIDACIÓN EXACTA COMO script.js
 */
const isFormValid = computed(() => {
  // Validaciones obligatorias del script.js
  if (!formData.value.company_id.trim()) return false
  if (!formData.value.company_name.trim()) return false
  if (!formData.value.services.trim()) return false
  if (!formData.value.business_type) return false
  if (!formData.value.sales_agent_name.trim()) return false
  
  // Validar formato de company_id como script.js
  if (!/^[a-z0-9_]+$/.test(formData.value.company_id)) return false
  
  // Validar JSON si se proporciona
  if (!isValidTreatmentDurationsJSON.value) return false
  
  return true
})

/**
 * ✅ VALIDACIÓN DE JSON como script.js
 */
const isValidTreatmentDurationsJSON = computed(() => {
  if (!formData.value.treatment_durations_json.trim()) return true
  
  try {
    JSON.parse(formData.value.treatment_durations_json)
    return true
  } catch (error) {
    return false
  }
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
 * ✅ CARGA DATOS INICIALES - Compatible con estructura de script.js
 */
const loadInitialData = (data) => {
  formData.value = {
    company_id: data.company_id || data.id || '',
    company_name: data.company_name || data.name || '',
    business_type: data.business_type || '',
    services: data.services || '',
    sales_agent_name: data.sales_agent_name || '',
    model_name: data.model_name || 'gpt-4o-mini',
    max_tokens: data.max_tokens || 150,
    temperature: data.temperature || 0.7,
    schedule_service_url: data.schedule_service_url || '',
    treatment_durations: data.treatment_durations || {},
    treatment_durations_json: data.treatment_durations ? 
      JSON.stringify(data.treatment_durations, null, 2) : '',
    timezone: data.timezone || 'America/Bogota',
    language: data.language || 'es',
    currency: data.currency || 'COP',
    subscription_tier: data.subscription_tier || 'basic',
    environment: data.environment || 'development',
    database_type: data.database_type || '',
    api_base_url: data.api_base_url || '',
    is_active: data.is_active !== false,
    description: data.description || '',
    notes: data.notes || ''
  }
}

/**
 * ✅ MANEJO DE ENVÍO - Preparar datos como script.js
 */
const handleSubmit = () => {
  if (!isFormValid.value) {
    showError('Por favor complete todos los campos requeridos correctamente')
    return
  }

  // ✅ PREPARAR DATOS EXACTO COMO script.js
  const submitData = {
    company_id: formData.value.company_id.trim(),
    company_name: formData.value.company_name.trim(),
    business_type: formData.value.business_type,
    services: formData.value.services.trim(),
    sales_agent_name: formData.value.sales_agent_name.trim(),
    model_name: formData.value.model_name,
    max_tokens: formData.value.max_tokens,
    temperature: formData.value.temperature,
    schedule_service_url: formData.value.schedule_service_url || '',
    treatment_durations: formData.value.treatment_durations_json ? 
      JSON.parse(formData.value.treatment_durations_json) : {},
    timezone: formData.value.timezone,
    language: formData.value.language,
    currency: formData.value.currency,
    subscription_tier: formData.value.subscription_tier,
    environment: formData.value.environment,
    database_type: formData.value.database_type,
    api_base_url: formData.value.api_base_url,
    is_active: formData.value.is_active,
    description: formData.value.description,
    notes: formData.value.notes
  }

  emit('submit', submitData)
}

/**
 * ✅ CANCELAR
 */
const handleCancel = () => {
  operationResult.value = null
  emit('cancel')
}

/**
 * ✅ RESETEAR FORMULARIO
 */
const resetForm = () => {
  formData.value = {
    company_id: '',
    company_name: '',
    business_type: '',
    services: '',
    sales_agent_name: '',
    model_name: 'gpt-4o-mini',
    max_tokens: 150,
    temperature: 0.7,
    schedule_service_url: '',
    treatment_durations: {},
    treatment_durations_json: '',
    timezone: 'America/Bogota',
    language: 'es',
    currency: 'COP',
    subscription_tier: 'basic',
    environment: 'development',
    database_type: '',
    api_base_url: '',
    is_active: true,
    description: '',
    notes: ''
  }
  operationResult.value = null
}

/**
 * ✅ MOSTRAR RESULTADO - Compatible con respuesta de script.js
 */
const showResult = (type, title, message, details = null) => {
  operationResult.value = {
    type,
    title,
    message,
    setup_status: details?.setup_status,
    next_steps: details?.next_steps
  }
}

/**
 * ✅ MOSTRAR ERROR
 */
const showError = (message) => {
  showResult('error', '❌ Error', message)
}

/**
 * ✅ HELPERS PARA DISPLAY
 */
const getStatusClass = (value) => {
  if (typeof value === 'boolean') {
    return value ? 'success' : 'error'
  }
  if (typeof value === 'string') {
    if (value.includes('success') || value.includes('✅')) return 'success'
    if (value.includes('error') || value.includes('❌')) return 'error'
  }
  return 'info'
}

const formatSetupKey = (key) => {
  return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

const formatSetupValue = (value) => {
  if (typeof value === 'boolean') {
    return value ? '✅ Configurado' : '❌ Pendiente'
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
/* Mantener todos los estilos del formulario original */
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
