<template>
  <div class="enterprise-company-detail">
    <!-- Estado de carga -->
    <div v-if="isLoading" class="loading-state">
      <div class="loading-spinner">🔄</div>
      <p>Cargando detalles de la empresa...</p>
    </div>

    <!-- Error state -->
    <div v-if="error && !isLoading" class="error-state">
      <div class="result-container result-error">
        <h4>❌ Error al cargar empresa</h4>
        <p>{{ error }}</p>
        <button @click="$emit('refresh')" class="btn btn-secondary">
          🔄 Reintentar
        </button>
      </div>
    </div>

    <!-- Detalles de la empresa -->
    <div v-if="company && !isLoading" class="company-detail-content">
      <!-- Header con acciones principales -->
      <div class="detail-header">
        <div class="header-info">
          <h3>
            <span class="company-icon">🏢</span>
            {{ company.company_name || company.company_id }}
          </h3>
          <div class="company-meta">
            <span 
              class="status-badge"
              :class="getStatusClass(company.is_active, company.status)"
            >
              {{ getStatusText(company.is_active, company.status) }}
            </span>
            <span 
              v-if="company.business_type"
              class="business-type-badge" 
              :class="`business-${company.business_type}`"
            >
              {{ formatBusinessType(company.business_type) }}
            </span>
            <span 
              v-if="company.environment" 
              class="environment-badge" 
              :class="`env-${company.environment}`"
            >
              {{ company.environment.toUpperCase() }}
            </span>
          </div>
        </div>

        <div class="header-actions">
          <button 
            @click="$emit('edit', company.company_id)"
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
            {{ isTesting ? 'Probando...' : 'Test Conexión' }}
          </button>
          <button 
            @click="$emit('close')"
            class="btn btn-outline"
          >
            ❌ Cerrar
          </button>
        </div>
      </div>

      <!-- Información básica -->
      <div class="detail-section">
        <h4>📋 Información Básica</h4>
        <div class="info-grid">
          <div class="info-item">
            <strong>ID de Empresa:</strong>
            <span class="value company-id">{{ company.company_id }}</span>
          </div>
          
          <div class="info-item">
            <strong>Nombre:</strong>
            <span class="value">{{ company.company_name || 'N/A' }}</span>
          </div>
          
          <div class="info-item">
            <strong>Tipo de Negocio:</strong>
            <span class="value">{{ formatBusinessType(company.business_type) || 'N/A' }}</span>
          </div>
          
          <div class="info-item">
            <strong>Plan de Suscripción:</strong>
            <span class="value plan-badge" :class="`plan-${company.subscription_tier || 'basic'}`">
              {{ (company.subscription_tier || 'basic').toUpperCase() }}
            </span>
          </div>
          
          <div class="info-item full-width" v-if="company.description">
            <strong>Descripción:</strong>
            <span class="value">{{ company.description }}</span>
          </div>
        </div>
      </div>

      <!-- Servicios -->
      <div v-if="company.services" class="detail-section">
        <h4>⚙️ Servicios Ofrecidos</h4>
        <div class="services-content">
          <p class="services-text">{{ company.services }}</p>
        </div>
      </div>

      <!-- Configuración del agente -->
      <div class="detail-section">
        <h4>🤖 Configuración del Agente</h4>
        <div class="info-grid">
          <div class="info-item">
            <strong>Agente de Ventas:</strong>
            <span class="value">{{ company.sales_agent_name || 'No configurado' }}</span>
          </div>
          
          <div class="info-item">
            <strong>Modelo IA:</strong>
            <span class="value">{{ company.model_name || 'Por defecto' }}</span>
          </div>
          
          <div class="info-item full-width" v-if="company.schedule_service_url">
            <strong>Servicio de Agenda:</strong>
            <span class="value url-value">
              <a :href="company.schedule_service_url" target="_blank" rel="noopener noreferrer">
                {{ company.schedule_service_url }}
              </a>
            </span>
          </div>
        </div>
      </div>

      <!-- Configuración técnica -->
      <div class="detail-section">
        <h4>⚙️ Configuración Técnica</h4>
        <div class="info-grid">
          <div class="info-item" v-if="company.api_base_url">
            <strong>URL Base API:</strong>
            <span class="value url-value">
              <a :href="company.api_base_url" target="_blank" rel="noopener noreferrer">
                {{ company.api_base_url }}
              </a>
            </span>
          </div>
          
          <div class="info-item">
            <strong>Base de Datos:</strong>
            <span class="value">{{ company.database_type ? company.database_type.toUpperCase() : 'No especificada' }}</span>
          </div>
          
          <div class="info-item">
            <strong>Entorno:</strong>
            <span class="value environment-value" :class="`env-${company.environment || 'development'}`">
              {{ (company.environment || 'development').toUpperCase() }}
            </span>
          </div>
          
          <div class="info-item">
            <strong>Estado:</strong>
            <span class="value">
              <span :class="company.is_active ? 'status-active' : 'status-inactive'">
                {{ company.is_active ? '🟢 Activa' : '🔴 Inactiva' }}
              </span>
            </span>
          </div>
        </div>
      </div>

      <!-- Configuración regional -->
      <div class="detail-section">
        <h4>🌍 Configuración Regional</h4>
        <div class="info-grid">
          <div class="info-item">
            <strong>Zona Horaria:</strong>
            <span class="value">{{ company.timezone || 'No configurada' }}</span>
          </div>
          
          <div class="info-item">
            <strong>Moneda:</strong>
            <span class="value currency-badge">{{ company.currency || 'N/A' }}</span>
          </div>
        </div>
      </div>

      <!-- Configuración JSON avanzada -->
      <div v-if="company.configuration && Object.keys(company.configuration).length > 0" class="detail-section">
        <h4>🔧 Configuración Avanzada</h4>
        <div class="configuration-container">
          <div class="config-header">
            <span class="config-label">Configuración JSON:</span>
            <button 
              @click="copyConfiguration"
              class="btn btn-sm btn-outline"
              title="Copiar configuración"
            >
              📋 Copiar
            </button>
          </div>
          <pre class="json-display">{{ formatConfiguration(company.configuration) }}</pre>
        </div>
      </div>

      <!-- Notas -->
      <div v-if="company.notes" class="detail-section">
        <h4>📝 Notas</h4>
        <div class="notes-content">
          <p class="notes-text">{{ company.notes }}</p>
        </div>
      </div>

      <!-- Resultado de la prueba -->
      <div v-if="testResult" class="detail-section">
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
            <div class="test-section">
              <h6>📤 Mensaje de Prueba:</h6>
              <div class="test-message">{{ testResult.testMessage }}</div>
            </div>
            
            <div v-if="testResult.response" class="test-section">
              <h6>🤖 Respuesta del Bot:</h6>
              <div class="test-response">{{ testResult.response }}</div>
            </div>
            
            <div v-if="testResult.details" class="test-section">
              <h6>ℹ️ Detalles Técnicos:</h6>
              <div class="test-details">
                <div v-for="(value, key) in testResult.details" :key="key" class="detail-item">
                  <strong>{{ formatKey(key) }}:</strong>
                  <span>{{ formatDetailValue(value) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Información del sistema -->
      <div class="detail-section">
        <h4>📊 Información del Sistema</h4>
        <div class="system-info">
          <div class="info-item">
            <strong>Fecha de creación:</strong>
            <span class="value">{{ formatDateTime(company.created_at) || 'No disponible' }}</span>
          </div>
          
          <div class="info-item">
            <strong>Última actualización:</strong>
            <span class="value">{{ formatDateTime(company.updated_at || company.last_modified) || 'No disponible' }}</span>
          </div>
          
          <div class="info-item">
            <strong>Última sincronización:</strong>
            <span class="value">{{ formatDateTime(lastSync) || 'No disponible' }}</span>
          </div>
        </div>
      </div>

      <!-- Acciones disponibles -->
      <div class="detail-section">
        <h4>🛠️ Acciones Disponibles</h4>
        <div class="actions-grid">
          <button 
            @click="$emit('edit', company.company_id)"
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
              <small>Verificar conectividad y configuración</small>
            </div>
          </button>
          
          <button 
            @click="$emit('toggle-status', company.company_id, !company.is_active)"
            class="action-card"
          >
            <div class="action-icon">{{ company.is_active ? '⏸️' : '▶️' }}</div>
            <div class="action-content">
              <strong>{{ company.is_active ? 'Desactivar' : 'Activar' }}</strong>
              <small>{{ company.is_active ? 'Suspender operaciones' : 'Reactivar empresa' }}</small>
            </div>
          </button>
          
          <button 
            @click="handleRefresh"
            class="action-card"
          >
            <div class="action-icon">🔄</div>
            <div class="action-content">
              <strong>Actualizar</strong>
              <small>Recargar información</small>
            </div>
          </button>

          <button 
            @click="handleExport"
            class="action-card"
          >
            <div class="action-icon">📤</div>
            <div class="action-content">
              <strong>Exportar</strong>
              <small>Descargar configuración</small>
            </div>
          </button>

          <button 
            v-if="company.api_base_url || company.schedule_service_url"
            @click="handleOpenExternal"
            class="action-card"
          >
            <div class="action-icon">🔗</div>
            <div class="action-content">
              <strong>Abrir Servicios</strong>
              <small>Acceder a servicios externos</small>
            </div>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

// ============================================================================
// PROPS & EMITS
// ============================================================================

const props = defineProps({
  company: {
    type: Object,
    default: null
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
    type: Number,
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
// REACTIVE DATA
// ============================================================================

const isTesting = ref(false)
const testResult = ref(null)

// ============================================================================
// METHODS
// ============================================================================

/**
 * Maneja el test de conexión
 */
const handleTest = async () => {
  if (!props.company) return
  
  isTesting.value = true
  testResult.value = null
  
  try {
    // Emitir evento al componente padre para manejar la prueba
    const result = await emit('test', props.company.company_id)
    
    // El resultado será manejado por el componente padre
    // Este es un placeholder para mostrar que se está probando
    
  } catch (error) {
    showTestResult('error', '❌ Error en la Prueba', error.message)
  } finally {
    // isTesting se resetea cuando se recibe el resultado
  }
}

/**
 * Muestra resultado de prueba
 */
const showTestResult = (type, title, message, response = null, details = null) => {
  testResult.value = {
    type,
    title,
    message,
    response,
    details,
    testMessage: '¿Cuáles son sus servicios disponibles?',
    timestamp: Date.now()
  }
  isTesting.value = false
}

/**
 * Maneja la actualización de datos
 */
const handleRefresh = () => {
  testResult.value = null
  emit('refresh')
}

/**
 * Maneja la exportación de datos de la empresa
 */
const handleExport = () => {
  if (!props.company) return
  
  try {
    const exportData = {
      export_timestamp: new Date().toISOString(),
      company: props.company
    }
    
    const content = JSON.stringify(exportData, null, 2)
    const blob = new Blob([content], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `enterprise_company_${props.company.company_id}_${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    
  } catch (error) {
    console.error('Error exporting company data:', error)
  }
}

/**
 * Abre servicios externos
 */
const handleOpenExternal = () => {
  if (!props.company) return
  
  const urls = []
  if (props.company.api_base_url) urls.push(props.company.api_base_url)
  if (props.company.schedule_service_url) urls.push(props.company.schedule_service_url)
  
  urls.forEach(url => {
    window.open(url, '_blank', 'noopener,noreferrer')
  })
}

/**
 * Copia la configuración JSON al portapapeles
 */
const copyConfiguration = async () => {
  if (!props.company?.configuration) return
  
  try {
    const configText = formatConfiguration(props.company.configuration)
    await navigator.clipboard.writeText(configText)
    // Aquí podrías mostrar una notificación de éxito
  } catch (error) {
    console.error('Error copying configuration:', error)
  }
}

/**
 * Formatea la configuración JSON para mostrar
 */
const formatConfiguration = (config) => {
  if (!config) return 'No configurado'
  
  try {
    if (typeof config === 'string') {
      const parsed = JSON.parse(config)
      return JSON.stringify(parsed, null, 2)
    } else {
      return JSON.stringify(config, null, 2)
    }
  } catch (error) {
    return config.toString()
  }
}

/**
 * Formatea fecha para mostrar
 */
const formatDateTime = (timestamp) => {
  if (!timestamp) return null
  
  try {
    const date = typeof timestamp === 'number' ? new Date(timestamp) : new Date(timestamp)
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

/**
 * Obtiene clase de status
 */
const getStatusClass = (isActive, status) => {
  if (status === 'error') return 'status-error'
  if (isActive === false) return 'status-inactive'
  return 'status-success'
}

/**
 * Obtiene texto de status
 */
const getStatusText = (isActive, status) => {
  if (status === 'error') return '❌ Error'
  if (isActive === false) return '⏸️ Inactiva'
  return '✅ Activa'
}

/**
 * Formatea tipo de negocio
 */
const formatBusinessType = (type) => {
  if (!type) return ''
  
  const types = {
    spa: 'SPA & Wellness',
    healthcare: 'Salud', 
    beauty: 'Belleza',
    dental: 'Dental',
    retail: 'Retail',
    technology: 'Tecnología',
    consulting: 'Consultoría',
    general: 'General'
  }
  return types[type] || type.charAt(0).toUpperCase() + type.slice(1)
}

/**
 * Formatea clave para mostrar más amigable
 */
const formatKey = (key) => {
  return key
    .replace(/_/g, ' ')
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

/**
 * Formatea valor para mostrar en detalles
 */
const formatDetailValue = (value) => {
  if (typeof value === 'boolean') {
    return value ? '✅ Sí' : '❌ No'
  }
  if (typeof value === 'number') {
    return value.toLocaleString()
  }
  return value
}

// ============================================================================
// EXPOSE METHODS (Para uso desde componente padre)
// ============================================================================

defineExpose({
  showTestResult,
  handleRefresh
})
</script>

<style scoped>
.enterprise-company-detail {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

/* Estados de carga y error */
.loading-state, .error-state {
  padding: 40px;
  text-align: center;
}

.loading-spinner {
  font-size: 2em;
  animation: spin 1s linear infinite;
  margin-bottom: 15px;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Header del detalle */
.detail-header {
  background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
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

.status-badge, .business-type-badge, .environment-badge {
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

.status-inactive {
  background: rgba(255, 193, 7, 0.2);
  color: #ffffff;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.status-error {
  background: rgba(220, 53, 69, 0.2);
  color: #ffffff;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.business-type-badge, .environment-badge {
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

/* Secciones del detalle */
.detail-section {
  padding: 25px;
  border-bottom: 1px solid #eee;
}

.detail-section:last-child {
  border-bottom: none;
}

.detail-section h4 {
  margin: 0 0 20px 0;
  color: #333;
  font-size: 1.2em;
  padding-bottom: 10px;
  border-bottom: 2px solid #f8f9fa;
}

/* Grid de información */
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

.info-item .value {
  color: #333;
  font-size: 1em;
  word-break: break-word;
}

.company-id {
  font-family: 'Courier New', monospace;
  background: #f8f9fa;
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 0.9em !important;
}

.url-value a {
  color: #007bff;
  text-decoration: none;
  font-family: 'Courier New', monospace;
  background: #f8f9fa;
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 0.9em;
  display: inline-block;
}

.url-value a:hover {
  text-decoration: underline;
}

.plan-badge, .currency-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.85em !important;
  font-weight: bold;
  text-transform: uppercase;
}

.plan-basic {
  background: #fff3cd;
  color: #856404;
}

.plan-premium {
  background: #cce5ff;
  color: #0066cc;
}

.plan-enterprise {
  background: #d4edda;
  color: #155724;
}

.currency-badge {
  background: #e9ecef;
  color: #495057;
}

.environment-value {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 8px;
  font-size: 0.85em !important;
  font-weight: bold;
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

.status-active {
  color: #28a745;
  font-weight: bold;
}

.status-inactive {
  color: #dc3545;
  font-weight: bold;
}

/* Contenido de servicios y notas */
.services-content, .notes-content {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 6px;
  border-left: 4px solid #007bff;
}

.services-text, .notes-text {
  margin: 0;
  line-height: 1.6;
  color: #333;
}

/* Configuración JSON */
.configuration-container {
  background: #f8f9fa;
  border-radius: 6px;
  overflow: hidden;
}

.config-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #e9ecef;
  border-bottom: 1px solid #dee2e6;
}

.config-label {
  font-weight: 600;
  color: #495057;
}

.btn-sm {
  padding: 4px 8px;
  font-size: 0.8em;
}

.json-display {
  margin: 0;
  padding: 16px;
  background: #fff;
  color: #333;
  font-family: 'Courier New', monospace;
  font-size: 0.9em;
  line-height: 1.4;
  overflow-x: auto;
}

/* Resultado de prueba */
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

.test-section h6 {
  margin: 0 0 8px 0;
  font-size: 1em;
  color: #495057;
}

.test-message, .test-response {
  background: rgba(255, 255, 255, 0.7);
  padding: 10px;
  border-radius: 4px;
  border-left: 3px solid currentColor;
  font-style: italic;
}

.test-details {
  display: grid;
  gap: 8px;
}

.detail-item {
  display: flex;
  gap: 8px;
  font-size: 0.9em;
}

/* Acciones */
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
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
}

.action-card:hover:not(:disabled) {
  background: #e9ecef;
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

/* Información del sistema */
.system-info {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 15px;
}

/* Botones generales */
.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  font-size: 0.9em;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 5px;
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

.btn-outline:hover:not(:disabled) {
  background: #6c757d;
  color: white;
}

/* Result containers */
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
  
  .test-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 5px;
  }
  
  .config-header {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }
}
</style>
