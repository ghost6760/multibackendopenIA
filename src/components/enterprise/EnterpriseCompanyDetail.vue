<template>
  <div class="enterprise-company-detail">
    <!-- Estado de carga -->
    <div v-if="isLoading" class="loading-state">
      <div class="loading-spinner"></div>
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
            {{ company.name || company.company_id }}
          </h3>
          <div class="company-meta">
            <span 
              class="status-badge"
              :class="company.is_active ? 'status-success' : 'status-error'"
            >
              {{ company.is_active ? '✅ Activa' : '❌ Inactiva' }}
            </span>
            <span class="environment-badge" :class="`env-${company.environment || 'development'}`">
              {{ (company.environment || 'development').toUpperCase() }}
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
            <span class="value">{{ company.company_id || company.id }}</span>
          </div>
          
          <div class="info-item">
            <strong>Nombre:</strong>
            <span class="value">{{ company.name || 'N/A' }}</span>
          </div>
          
          <div class="info-item">
            <strong>Tipo de Negocio:</strong>
            <span class="value">{{ company.business_type || 'N/A' }}</span>
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
          
          <div class="info-item full-width" v-if="company.services">
            <strong>Servicios:</strong>
            <span class="value">{{ company.services }}</span>
          </div>
        </div>
      </div>

      <!-- Configuración técnica -->
      <div class="detail-section">
        <h4>⚙️ Configuración Técnica</h4>
        <div class="info-grid">
          <div class="info-item">
            <strong>URL Base API:</strong>
            <span class="value url-value">{{ company.api_base_url || 'No configurada' }}</span>
          </div>
          
          <div class="info-item">
            <strong>Base de Datos:</strong>
            <span class="value">{{ company.database_type || 'No especificada' }}</span>
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

      <!-- Configuración JSON -->
      <div v-if="company.configuration" class="detail-section">
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

      <!-- Resultado de la prueba -->
      <div v-if="testResult" class="detail-section">
        <h4>🧪 Resultado de Prueba de Conexión</h4>
        <div 
          class="test-result"
          :class="`result-container result-${testResult.type}`"
        >
          <div class="test-header">
            <h5>{{ testResult.title }}</h5>
            <span class="test-timestamp">{{ formatDate(testResult.timestamp) }}</span>
          </div>
          
          <p>{{ testResult.message }}</p>
          
          <!-- Detalles del test -->
          <div v-if="testResult.details" class="test-details">
            <h6>Detalles:</h6>
            <div class="details-grid">
              <div 
                v-for="(value, key) in testResult.details" 
                :key="key"
                class="detail-item"
              >
                <span class="status-indicator" :class="`status-${getStatusClass(value)}`"></span>
                <strong>{{ formatKey(key) }}:</strong>
                <span>{{ formatDetailValue(value) }}</span>
              </div>
            </div>
          </div>
          
          <!-- Próximos pasos -->
          <div v-if="testResult.nextSteps" class="next-steps">
            <h6>Próximos Pasos:</h6>
            <ol>
              <li v-for="step in testResult.nextSteps" :key="step">{{ step }}</li>
            </ol>
          </div>
        </div>
      </div>

      <!-- Información del sistema -->
      <div class="detail-section">
        <h4>📊 Información del Sistema</h4>
        <div class="system-info">
          <div class="info-item">
            <strong>Fecha de creación:</strong>
            <span class="value">{{ formatDate(company.created_at) || 'No disponible' }}</span>
          </div>
          
          <div class="info-item">
            <strong>Última actualización:</strong>
            <span class="value">{{ formatDate(company.updated_at) || 'No disponible' }}</span>
          </div>
          
          <div class="info-item">
            <strong>Última sincronización:</strong>
            <span class="value">{{ formatDate(lastSync) || 'No disponible' }}</span>
          </div>
        </div>
      </div>

      <!-- Acciones adicionales -->
      <div class="detail-section">
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
              <small>Verificar conectividad y configuración</small>
            </div>
          </button>
          
          <button 
            @click="$emit('toggle-status', company.company_id || company.id, !company.is_active)"
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
 * Maneja el test de conexión - MIGRADO: testEnterpriseCompany() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const handleTest = async () => {
  if (!props.company) return
  
  isTesting.value = true
  testResult.value = null
  
  try {
    // Emitir evento al componente padre para manejar la prueba
    emit('test', props.company.company_id || props.company.id)
    
    // Simular resultado de prueba (el componente padre manejará el resultado real)
    // Este es solo para mostrar el estado de carga
    
  } catch (error) {
    showTestResult('error', '❌ Error en la Prueba', error.message)
  } finally {
    // isTesting se resetea cuando se recibe el resultado
  }
}

/**
 * Muestra resultado de prueba
 */
const showTestResult = (type, title, message, details = null, nextSteps = null) => {
  testResult.value = {
    type,
    title,
    message,
    details,
    nextSteps,
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
      // Si ya es string, intentar parsearlo y reformatearlo
      const parsed = JSON.parse(config)
      return JSON.stringify(parsed, null, 2)
    } else {
      // Si es objeto, convertirlo a JSON formateado
      return JSON.stringify(config, null, 2)
    }
  } catch (error) {
    // Si hay error en el parsing, devolver como string
    return config.toString()
  }
}

/**
 * Formatea fecha para mostrar - PRESERVAR formato del script.js
 */
const formatDate = (timestamp) => {
  if (!timestamp) return null
  
  try {
    const date = new Date(timestamp)
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
 * Obtiene clase de status para indicadores
 */
const getStatusClass = (value) => {
  if (typeof value === 'boolean') {
    return value ? 'success' : 'error'
  }
  if (typeof value === 'string') {
    const lower = value.toLowerCase()
    if (lower.includes('success') || lower.includes('ok') || lower.includes('active')) {
      return 'success'
    }
    if (lower.includes('error') || lower.includes('fail') || lower.includes('inactive')) {
      return 'error'
    }
  }
  return 'info'
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

// ============================================================================
// EXPOSE METHODS (Para uso desde componente padre)
// ============================================================================

defineExpose({
  showTestResult,
  handleRefresh
})
</script>

<style scoped>
/* ============================================================================ */
/* ESTILOS DEL COMPONENTE DETAIL - Siguiendo el estilo del proyecto */
/* ============================================================================ */

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
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
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

.status-badge, .environment-badge {
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

.environment-badge {
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

.url-value {
  font-family: 'Courier New', monospace;
  background: #f8f9fa;
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 0.9em !important;
}

.plan-badge {
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

.test-details {
  margin: 15px 0;
}

.test-details h6 {
  margin: 0 0 10px 0;
  font-size: 1em;
}

.details-grid {
  display: grid;
  gap: 8px;
}

.detail-item {
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
}
</style>
