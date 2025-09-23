<template>
  <div class="enterprise-company-detail">
    
    <!-- Header con información principal -->
    <div class="detail-header">
      <div class="header-info">
        <h3>
          <span class="company-icon">🏢</span>
          {{ company.company_name || company.name || company.company_id || company.id }}
        </h3>
        <div class="company-meta">
          <span 
            class="status-badge"
            :class="getStatusClass(company.is_active, company.status)"
          >
            {{ getStatusText(company.is_active, company.status) }}
          </span>
          <span v-if="company.environment" class="environment-badge" :class="`env-${company.environment}`">
            {{ company.environment.toUpperCase() }}
          </span>
          <span v-if="company.subscription_tier" class="tier-badge" :class="`tier-${company.subscription_tier}`">
            {{ company.subscription_tier.toUpperCase() }}
          </span>
        </div>
      </div>

      <div class="header-actions">
        <button 
          @click="$emit('edit', company.company_id || company.id)"
          class="btn btn-secondary"
        >
          ✏️ Editar
        </button>
        <button 
          @click="handleTest"
          :disabled="isTesting"
          class="btn btn-info"
        >
          <span v-if="isTesting">⏳</span>
          <span v-else>🧪</span>
          {{ isTesting ? 'Probando...' : 'Test' }}
        </button>
        <button 
          @click="$emit('refresh')"
          class="btn btn-outline"
          title="Actualizar información"
        >
          🔄 Actualizar
        </button>
        <button 
          @click="$emit('close')"
          class="btn btn-outline"
        >
          ❌ Cerrar
        </button>
      </div>
    </div>

    <!-- Contenido principal en pestañas -->
    <div class="detail-content">
      
      <!-- Navegación de pestañas -->
      <div class="detail-tabs">
        <button 
          v-for="tab in availableTabs" 
          :key="tab.key"
          @click="activeTab = tab.key"
          class="tab-button"
          :class="{ active: activeTab === tab.key }"
        >
          {{ tab.icon }} {{ tab.label }}
        </button>
      </div>

      <!-- Contenido de pestañas -->
      <div class="tab-content">
        
        <!-- Pestaña: Información General -->
        <div v-if="activeTab === 'general'" class="tab-panel">
          <div class="detail-section">
            <h4>📋 Información Básica</h4>
            <div class="info-grid">
              <div class="info-item">
                <strong>ID de Empresa:</strong>
                <span class="company-id">{{ company.company_id || company.id }}</span>
              </div>
              
              <div class="info-item">
                <strong>Nombre:</strong>
                <span>{{ company.company_name || company.name || 'N/A' }}</span>
              </div>
              
              <div class="info-item">
                <strong>Tipo de Negocio:</strong>
                <span class="business-type">{{ formatBusinessType(company.business_type) }}</span>
              </div>
              
              <div class="info-item">
                <strong>Plan de Suscripción:</strong>
                <span class="subscription-tier" :class="`tier-${company.subscription_tier}`">
                  {{ (company.subscription_tier || 'basic').toUpperCase() }}
                </span>
              </div>
              
              <div class="info-item" v-if="company.description">
                <strong>Descripción:</strong>
                <span>{{ company.description }}</span>
              </div>
              
              <div class="info-item full-width" v-if="company.services">
                <strong>Servicios Ofrecidos:</strong>
                <div class="services-display">{{ company.services }}</div>
              </div>
            </div>
          </div>

          <!-- Información del sistema -->
          <div class="detail-section">
            <h4>📊 Información del Sistema</h4>
            <div class="info-grid">
              <div class="info-item">
                <strong>Fecha de creación:</strong>
                <span>{{ formatDateTime(company.created_at) || 'No disponible' }}</span>
              </div>
              
              <div class="info-item">
                <strong>Última actualización:</strong>
                <span>{{ formatDateTime(company.updated_at || company.last_modified) || 'No disponible' }}</span>
              </div>
              
              <div class="info-item">
                <strong>Versión:</strong>
                <span>{{ company.version || 'N/A' }}</span>
              </div>
              
              <div class="info-item">
                <strong>Arquitectura:</strong>
                <span class="architecture-badge">{{ company.architecture || 'enterprise_postgresql' }}</span>
              </div>
              
              <div class="info-item">
                <strong>Estado del sistema:</strong>
                <span :class="company.system_ready ? 'status-ready' : 'status-not-ready'">
                  {{ company.system_ready ? '✅ Listo' : '⚠️ Configuración pendiente' }}
                </span>
              </div>
              
              <div class="info-item">
                <strong>Última sincronización:</strong>
                <span>{{ formatDateTime(lastSync) || 'No disponible' }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Pestaña: Configuración de Agente -->
        <div v-if="activeTab === 'agent'" class="tab-panel">
          <div class="detail-section">
            <h4>🤖 Configuración del Agente</h4>
            <div class="info-grid">
              <div class="info-item">
                <strong>Nombre del Agente:</strong>
                <span>{{ company.sales_agent_name || 'No configurado' }}</span>
              </div>
              
              <div class="info-item">
                <strong>Modelo de IA:</strong>
                <span class="model-badge">{{ company.model_name || 'gpt-4o-mini' }}</span>
              </div>
              
              <div class="info-item">
                <strong>Max Tokens:</strong>
                <span>{{ company.max_tokens || 150 }}</span>
              </div>
              
              <div class="info-item">
                <strong>Temperature:</strong>
                <span>{{ company.temperature || 0.7 }}</span>
              </div>
              
              <div class="info-item">
                <strong>Idioma:</strong>
                <span class="language-badge">{{ formatLanguage(company.language) }}</span>
              </div>
              
              <div class="info-item">
                <strong>Zona Horaria:</strong>
                <span>{{ company.timezone || 'America/Bogota' }}</span>
              </div>
              
              <div class="info-item">
                <strong>Moneda:</strong>
                <span class="currency-badge">{{ company.currency || 'COP' }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Pestaña: Configuración Técnica -->
        <div v-if="activeTab === 'technical'" class="tab-panel">
          <div class="detail-section">
            <h4>⚙️ Configuración Técnica</h4>
            <div class="info-grid">
              <div class="info-item">
                <strong>URL Base API:</strong>
                <span class="url-value">{{ company.api_base_url || 'No configurada' }}</span>
              </div>
              
              <div class="info-item">
                <strong>Base de Datos:</strong>
                <span>{{ company.database_type || 'postgresql' }}</span>
              </div>
              
              <div class="info-item">
                <strong>Entorno:</strong>
                <span class="environment-value" :class="`env-${company.environment}`">
                  {{ (company.environment || 'development').toUpperCase() }}
                </span>
              </div>
              
              <div class="info-item">
                <strong>Estado:</strong>
                <span :class="company.is_active ? 'status-active' : 'status-inactive'">
                  {{ company.is_active ? '🟢 Activa' : '🔴 Inactiva' }}
                </span>
              </div>
            </div>
          </div>

          <!-- Configuración de Agenda -->
          <div class="detail-section" v-if="company.schedule_service_url || company.treatment_durations">
            <h4>📅 Configuración de Agenda</h4>
            <div class="info-grid">
              <div class="info-item" v-if="company.schedule_service_url">
                <strong>URL del Servicio:</strong>
                <span class="url-value">{{ company.schedule_service_url }}</span>
              </div>
              
              <div class="info-item full-width" v-if="company.treatment_durations">
                <strong>Duraciones de Tratamiento:</strong>
                <div class="treatment-durations">
                  <div 
                    v-for="(duration, treatment) in parseTreatmentDurations(company.treatment_durations)" 
                    :key="treatment"
                    class="duration-item"
                  >
                    <span class="treatment-name">{{ formatTreatmentName(treatment) }}:</span>
                    <span class="duration-value">{{ duration }} min</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Endpoints Disponibles -->
          <div class="detail-section" v-if="company.endpoints_available">
            <h4>🔗 Endpoints Disponibles</h4>
            <div class="endpoints-list">
              <div 
                v-for="endpoint in company.endpoints_available" 
                :key="endpoint"
                class="endpoint-item"
              >
                <span class="endpoint-method">GET</span>
                <span class="endpoint-path">{{ endpoint }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Pestaña: Estado de Configuración -->
        <div v-if="activeTab === 'setup'" class="tab-panel">
          <div class="detail-section">
            <h4>🔧 Estado de Configuración</h4>
            
            <div v-if="company.setup_status" class="setup-status">
              <div 
                v-for="(status, key) in company.setup_status" 
                :key="key"
                class="setup-item"
              >
                <div class="setup-indicator">
                  <span class="status-dot" :class="getSetupStatusClass(status)"></span>
                </div>
                <div class="setup-content">
                  <div class="setup-title">{{ formatSetupKey(key) }}</div>
                  <div class="setup-description">{{ formatSetupStatus(status) }}</div>
                </div>
              </div>
            </div>

            <!-- Próximos pasos si están disponibles -->
            <div v-if="company.next_steps" class="detail-section">
              <h5>📋 Próximos Pasos</h5>
              <ol class="next-steps-list">
                <li v-for="step in company.next_steps" :key="step">{{ step }}</li>
              </ol>
            </div>
          </div>
        </div>

        <!-- Pestaña: JSON Raw -->
        <div v-if="activeTab === 'raw'" class="tab-panel">
          <div class="detail-section">
            <h4>📝 Configuración Completa (JSON)</h4>
            <div class="json-container">
              <div class="json-header">
                <span class="json-label">Configuración completa de la empresa</span>
                <button 
                  @click="copyConfiguration"
                  class="btn btn-sm btn-outline"
                  title="Copiar configuración"
                >
                  📋 Copiar
                </button>
              </div>
              <pre class="json-display">{{ formatConfiguration(company) }}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Sección de pruebas -->
    <div v-if="testResult" class="test-section">
      <h4>🧪 Resultado de Prueba de Conexión</h4>
      <div 
        class="test-result"
        :class="`result-container result-${testResult.type}`"
      >
        <div class="test-header">
          <h5>{{ testResult.title }}</h5>
          <span class="test-timestamp">{{ formatDateTime(testResult.timestamp) }}</span>
        </div>
        
        <div class="test-content">
          <div class="test-section-item">
            <strong>Mensaje enviado:</strong>
            <div class="message-box user">{{ testResult.message }}</div>
          </div>
          
          <div class="test-section-item" v-if="testResult.response">
            <strong>Respuesta del bot:</strong>
            <div class="message-box bot">{{ testResult.response }}</div>
          </div>
          
          <div class="test-section-item" v-if="testResult.details">
            <strong>Información técnica:</strong>
            <div class="tech-details">
              <div v-for="(value, key) in testResult.details" :key="key" class="tech-item">
                <span class="tech-key">{{ formatKey(key) }}:</span>
                <span class="tech-value">{{ value }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Acciones adicionales -->
    <div class="detail-actions">
      <h4>🛠️ Acciones Disponibles</h4>
      <div class="actions-grid">
        <button 
          @click="$emit('edit', company.company_id || company.id)"
          class="action-card"
        >
          <div class="action-icon">✏️</div>
          <div class="action-content">
            <strong>Editar Empresa</strong>
            <small>Modificar configuración y datos</small>
          </div>
        </button>
        
        <button 
          @click="handleTest"
          :disabled="isTesting"
          class="action-card"
        >
          <div class="action-icon">🧪</div>
          <div class="action-content">
            <strong>{{ isTesting ? 'Probando...' : 'Test Conexión' }}</strong>
            <small>Verificar funcionamiento del agente</small>
          </div>
        </button>
        
        <button 
          @click="toggleCompanyStatus"
          class="action-card"
        >
          <div class="action-icon">{{ company.is_active ? '⏸️' : '▶️' }}</div>
          <div class="action-content">
            <strong>{{ company.is_active ? 'Desactivar' : 'Activar' }}</strong>
            <small>{{ company.is_active ? 'Suspender operaciones' : 'Reactivar empresa' }}</small>
          </div>
        </button>
        
        <button 
          @click="$emit('refresh')"
          class="action-card"
        >
          <div class="action-icon">🔄</div>
          <div class="action-content">
            <strong>Actualizar</strong>
            <small>Recargar información desde PostgreSQL</small>
          </div>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

// ============================================================================
// PROPS & EMITS
// ============================================================================

const props = defineProps({
  company: {
    type: Object,
    required: true
  },
  isLoading: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: null
  },
  lastSync: {
    type: [Number, String],
    default: null
  }
})

const emit = defineEmits([
  'edit',
  'close',
  'test',
  'toggle-status',
  'refresh'
])

// ============================================================================
// ESTADO LOCAL
// ============================================================================

const activeTab = ref('general')
const isTesting = ref(false)
const testResult = ref(null)

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const availableTabs = computed(() => {
  const tabs = [
    { key: 'general', label: 'General', icon: '📋' },
    { key: 'agent', label: 'Agente', icon: '🤖' },
    { key: 'technical', label: 'Técnico', icon: '⚙️' }
  ]
  
  // Agregar pestaña de setup si hay información disponible
  if (props.company.setup_status || props.company.next_steps) {
    tabs.push({ key: 'setup', label: 'Setup', icon: '🔧' })
  }
  
  // Agregar pestaña raw
  tabs.push({ key: 'raw', label: 'JSON', icon: '📝' })
  
  return tabs
})

// ============================================================================
// METHODS
// ============================================================================

/**
 * Manejar test de empresa
 */
const handleTest = async () => {
  const testMessage = prompt('Mensaje de prueba:', '¿Cuáles son sus servicios disponibles?')
  if (!testMessage) return
  
  isTesting.value = true
  testResult.value = null
  
  try {
    // Emitir evento al componente padre
    emit('test', props.company.company_id || props.company.id, testMessage)
    
  } catch (error) {
    showTestResult('error', '❌ Error en la Prueba', error.message, null, testMessage)
  } finally {
    // isTesting se resetea cuando se recibe el resultado
  }
}

/**
 * Mostrar resultado de prueba
 */
const showTestResult = (type, title, response, details = null, message = '') => {
  testResult.value = {
    type,
    title,
    message,
    response,
    details,
    timestamp: Date.now()
  }
  isTesting.value = false
}

/**
 * Toggle status de empresa
 */
const toggleCompanyStatus = () => {
  const newStatus = !props.company.is_active
  const action = newStatus ? 'activar' : 'desactivar'
  
  if (confirm(`¿Estás seguro de ${action} la empresa ${props.company.company_name || props.company.company_id}?`)) {
    emit('toggle-status', props.company.company_id || props.company.id, newStatus)
  }
}

/**
 * Copiar configuración al portapapeles
 */
const copyConfiguration = async () => {
  try {
    const configText = formatConfiguration(props.company)
    await navigator.clipboard.writeText(configText)
    // Mostrar feedback visual
    const button = event.target
    const originalText = button.textContent
    button.textContent = '✅ Copiado'
    setTimeout(() => {
      button.textContent = originalText
    }, 2000)
  } catch (error) {
    console.error('Error copying configuration:', error)
  }
}

// ============================================================================
// FUNCIONES DE FORMATO
// ============================================================================

const getStatusClass = (isActive, status) => {
  if (!isActive) return 'status-inactive'
  if (status === 'error') return 'status-error'
  if (status === 'warning') return 'status-warning'
  return 'status-success'
}

const getStatusText = (isActive, status) => {
  if (!isActive) return '❌ Inactiva'
  if (status === 'error') return '🔴 Error'
  if (status === 'warning') return '⚠️ Advertencia'
  return '✅ Activa'
}

const formatBusinessType = (type) => {
  const types = {
    healthcare: 'Salud',
    beauty: 'Belleza',
    dental: 'Dental',
    spa: 'SPA & Wellness',
    general: 'General'
  }
  return types[type] || type || 'No especificado'
}

const formatLanguage = (lang) => {
  const languages = {
    es: 'Español',
    en: 'English',
    pt: 'Português'
  }
  return languages[lang] || lang || 'es'
}

const formatDateTime = (dateTime) => {
  if (!dateTime) return null
  
  try {
    const date = typeof dateTime === 'number' ? new Date(dateTime) : new Date(dateTime)
    return date.toLocaleString('es-ES', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  } catch (error) {
    return 'Fecha inválida'
  }
}

const formatConfiguration = (config) => {
  try {
    return JSON.stringify(config, null, 2)
  } catch (error) {
    return 'Error formatting configuration: ' + error.message
  }
}

const formatSetupKey = (key) => {
  return key
    .replace(/_/g, ' ')
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

const formatSetupStatus = (status) => {
  if (typeof status === 'boolean') {
    return status ? '✅ Configurado correctamente' : '❌ Configuración pendiente'
  }
  if (typeof status === 'string') {
    if (status.includes('✅') || status.includes('success')) {
      return '✅ Configurado correctamente'
    }
    if (status.includes('❌') || status.includes('error')) {
      return '❌ Error en configuración'
    }
  }
  return status
}

const getSetupStatusClass = (status) => {
  if (typeof status === 'boolean') {
    return status ? 'status-success' : 'status-error'
  }
  if (typeof status === 'string') {
    if (status.includes('✅') || status.includes('success')) return 'status-success'
    if (status.includes('❌') || status.includes('error')) return 'status-error'
  }
  return 'status-info'
}

const parseTreatmentDurations = (durations) => {
  if (!durations) return {}
  
  try {
    if (typeof durations === 'string') {
      return JSON.parse(durations)
    }
    return durations
  } catch (error) {
    return {}
  }
}

const formatTreatmentName = (name) => {
  return name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

const formatKey = (key) => {
  return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

// ============================================================================
// LIFECYCLE
// ============================================================================

onMounted(() => {
  // Auto-focus en la primera pestaña disponible
  if (availableTabs.value.length > 0) {
    activeTab.value = availableTabs.value[0].key
  }
})

// ============================================================================
// EXPOSE METHODS
// ============================================================================

defineExpose({
  showTestResult,
  activeTab
})
</script>

<style scoped>
/* Componente principal */
.enterprise-company-detail {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

/* Header */
.detail-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 25px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 20px;
}

.header-info h3 {
  margin: 0 0 10px 0;
  font-size: 1.4em;
  display: flex;
  align-items: center;
  gap: 10px;
}

.company-icon {
  font-size: 1.2em;
}

.company-meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.status-badge, .environment-badge, .tier-badge {
  padding: 4px 12px;
  border-radius: 15px;
  font-size: 0.85em;
  font-weight: bold;
}

.status-success {
  background: rgba(40, 167, 69, 0.2);
  color: #ffffff;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.status-error {
  background: rgba(220, 53, 69, 0.2);
  color: #ffffff;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.status-inactive {
  background: rgba(108, 117, 125, 0.2);
  color: #ffffff;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.environment-badge, .tier-badge {
  background: rgba(255, 255, 255, 0.2);
  color: #ffffff;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.header-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.header-actions .btn {
  padding: 8px 16px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.1);
  color: white;
  border-radius: 4px;
  font-size: 0.9em;
}

.header-actions .btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.2);
}

/* Contenido principal */
.detail-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Tabs */
.detail-tabs {
  display: flex;
  background: #f8f9fa;
  border-bottom: 1px solid #dee2e6;
  overflow-x: auto;
}

.tab-button {
  padding: 12px 20px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 0.9em;
  color: #6c757d;
  border-bottom: 3px solid transparent;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.tab-button:hover {
  background: #e9ecef;
  color: #495057;
}

.tab-button.active {
  color: #007bff;
  border-bottom-color: #007bff;
  background: white;
}

/* Contenido de tabs */
.tab-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.tab-panel {
  display: flex;
  flex-direction: column;
  gap: 25px;
}

/* Secciones */
.detail-section {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 20px;
  border: 1px solid #e9ecef;
}

.detail-section h4 {
  margin: 0 0 20px 0;
  color: #333;
  font-size: 1.2em;
  padding-bottom: 10px;
  border-bottom: 2px solid #dee2e6;
}

.detail-section h5 {
  margin: 20px 0 15px 0;
  color: #495057;
  font-size: 1.1em;
}

/* Grids de información */
.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.info-item.full-width {
  grid-column: 1 / -1;
}

.info-item strong {
  color: #495057;
  font-size: 0.9em;
  font-weight: 600;
}

.info-item span {
  color: #333;
  font-size: 1em;
  word-break: break-word;
}

/* Badges especiales */
.company-id {
  font-family: 'Courier New', monospace;
  background: #e9ecef;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.9em !important;
}

.business-type {
  background: #d1ecf1;
  color: #0c5460;
  padding: 4px 8px;
  border-radius: 4px;
  font-weight: 500;
}

.subscription-tier {
  padding: 4px 8px;
  border-radius: 4px;
  font-weight: bold;
  font-size: 0.85em !important;
}

.tier-basic {
  background: #e2e3e5;
  color: #383d41;
}

.tier-premium {
  background: #fff3cd;
  color: #856404;
}

.tier-enterprise {
  background: #d4edda;
  color: #155724;
}

.model-badge {
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  padding: 4px 8px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.9em !important;
}

.language-badge, .currency-badge {
  background: #e7f3ff;
  color: #0066cc;
  padding: 4px 8px;
  border-radius: 4px;
  font-weight: 500;
}

.url-value {
  font-family: 'Courier New', monospace;
  background: #f8f9fa;
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 0.9em !important;
  word-break: break-all;
}

.environment-value {
  padding: 4px 8px;
  border-radius: 4px;
  font-weight: bold;
  font-size: 0.85em !important;
}

.env-development {
  background: #fff3cd;
  color: #856404;
}

.env-staging {
  background: #cce5ff;
  color: #0066cc;
}

.env-production {
  background: #d4edda;
  color: #155724;
}

.architecture-badge {
  background: #e7f3ff;
  color: #0066cc;
  padding: 4px 8px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.9em !important;
}

.status-active {
  color: #28a745;
  font-weight: bold;
}

.status-inactive {
  color: #dc3545;
  font-weight: bold;
}

.status-ready {
  color: #28a745;
  font-weight: bold;
}

.status-not-ready {
  color: #ffc107;
  font-weight: bold;
}

/* Servicios */
.services-display {
  background: white;
  padding: 12px;
  border-radius: 6px;
  border: 1px solid #dee2e6;
  font-style: italic;
  line-height: 1.5;
}

/* Tratamientos */
.treatment-durations {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 10px;
  background: white;
  padding: 12px;
  border-radius: 6px;
  border: 1px solid #dee2e6;
}

.duration-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px;
  background: #f8f9fa;
  border-radius: 4px;
}

.treatment-name {
  font-weight: 500;
  color: #495057;
}

.duration-value {
  font-weight: bold;
  color: #007bff;
  background: white;
  padding: 2px 6px;
  border-radius: 3px;
}

/* Endpoints */
.endpoints-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.endpoint-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 4px;
}

.endpoint-method {
  background: #28a745;
  color: white;
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 0.8em;
  font-weight: bold;
  min-width: 40px;
  text-align: center;
}

.endpoint-path {
  font-family: 'Courier New', monospace;
  color: #495057;
  font-size: 0.9em;
}

/* Setup status */
.setup-status {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.setup-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 15px;
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 6px;
}

.setup-indicator {
  flex-shrink: 0;
  margin-top: 2px;
}

.status-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: block;
}

.status-dot.status-success {
  background: #28a745;
}

.status-dot.status-error {
  background: #dc3545;
}

.status-dot.status-info {
  background: #17a2b8;
}

.setup-content {
  flex: 1;
}

.setup-title {
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}

.setup-description {
  color: #6c757d;
  font-size: 0.9em;
}

/* Próximos pasos */
.next-steps-list {
  background: white;
  padding: 15px 15px 15px 35px;
  border-radius: 6px;
  border: 1px solid #dee2e6;
  margin: 0;
}

.next-steps-list li {
  margin-bottom: 8px;
  line-height: 1.5;
}

/* JSON */
.json-container {
  background: #f8f9fa;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid #dee2e6;
}

.json-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #e9ecef;
  border-bottom: 1px solid #dee2e6;
}

.json-label {
  font-weight: 600;
  color: #495057;
}

.json-display {
  margin: 0;
  padding: 16px;
  background: white;
  color: #333;
  font-family: 'Courier New', monospace;
  font-size: 0.85em;
  line-height: 1.4;
  overflow-x: auto;
  max-height: 400px;
  overflow-y: auto;
}

/* Sección de pruebas */
.test-section {
  margin: 20px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #dee2e6;
}

.test-section h4 {
  margin: 0 0 15px 0;
  color: #333;
}

.test-result {
  border-radius: 6px;
  padding: 20px;
}

.test-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.test-header h5 {
  margin: 0;
  font-size: 1.1em;
}

.test-timestamp {
  font-size: 0.85em;
  opacity: 0.8;
}

.test-content {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.test-section-item strong {
  display: block;
  margin-bottom: 8px;
  color: #495057;
}

.message-box {
  background: white;
  padding: 12px;
  border-radius: 6px;
  border-left: 4px solid;
  word-wrap: break-word;
}

.message-box.user {
  border-left-color: #007bff;
}

.message-box.bot {
  border-left-color: #28a745;
}

.tech-details {
  background: white;
  padding: 12px;
  border-radius: 6px;
  border: 1px solid #dee2e6;
}

.tech-item {
  display: flex;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 0.9em;
}

.tech-key {
  font-weight: 600;
  color: #495057;
  min-width: 120px;
}

.tech-value {
  color: #333;
}

/* Acciones */
.detail-actions {
  margin: 20px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #dee2e6;
}

.detail-actions h4 {
  margin: 0 0 20px 0;
  color: #333;
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.action-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
}

.action-card:hover:not(:disabled) {
  background: #f8f9fa;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.action-card:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.action-icon {
  font-size: 1.5em;
  flex-shrink: 0;
}

.action-content {
  flex-grow: 1;
}

.action-content strong {
  display: block;
  margin-bottom: 2px;
  color: #333;
  font-size: 0.95em;
}

.action-content small {
  color: #6c757d;
  font-size: 0.85em;
}

/* Botones */
.btn {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  font-size: 0.85em;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: #007bff;
  color: white;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-info {
  background: #17a2b8;
  color: white;
}

.btn-outline {
  background: transparent;
  color: #6c757d;
  border: 1px solid #6c757d;
}

.btn-sm {
  padding: 4px 8px;
  font-size: 0.8em;
}

.btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

/* Resultado containers */
.result-container {
  border-left: 4px solid;
  padding: 15px;
  border-radius: 6px;
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

/* Responsive */
@media (max-width: 768px) {
  .detail-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .header-actions {
    justify-content: stretch;
  }
  
  .header-actions .btn {
    flex: 1;
    justify-content: center;
  }
  
  .info-grid {
    grid-template-columns: 1fr;
  }
  
  .actions-grid {
    grid-template-columns: 1fr;
  }
  
  .treatment-durations {
    grid-template-columns: 1fr;
  }
  
  .test-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
}
</style>
