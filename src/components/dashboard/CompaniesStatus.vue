<template>
  <div class="companies-status">
    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner">⏳</div>
      <p>Verificando estado de empresas...</p>
    </div>
    
    <!-- Companies Status Content -->
    <div v-else-if="companiesStatus" class="companies-content">
      <!-- Summary Stats -->
      <div class="summary-stats">
        <div class="stat-item total">
          <span class="stat-icon">🏢</span>
          <div class="stat-details">
            <span class="stat-number">{{ totalCompanies }}</span>
            <span class="stat-label">Total</span>
          </div>
        </div>
        
        <div class="stat-item healthy">
          <span class="stat-icon">✅</span>
          <div class="stat-details">
            <span class="stat-number">{{ healthyCompanies }}</span>
            <span class="stat-label">Activas</span>
          </div>
        </div>
        
        <div class="stat-item warning">
          <span class="stat-icon">⚠️</span>
          <div class="stat-details">
            <span class="stat-number">{{ warningCompanies }}</span>
            <span class="stat-label">Advertencias</span>
          </div>
        </div>
        
        <div class="stat-item error">
          <span class="stat-icon">❌</span>
          <div class="stat-details">
            <span class="stat-number">{{ errorCompanies }}</span>
            <span class="stat-label">Errores</span>
          </div>
        </div>
      </div>
      
      <!-- Companies List -->
      <div class="companies-list">
        <div
          v-for="company in sortedCompanies"
          :key="company.id"
          class="company-item"
          :class="getCompanyStatusClass(company.status)"
          @click="selectCompany(company)"
        >
          <!-- Company Header -->
          <div class="company-header">
            <div class="company-info">
              <span class="company-icon">{{ getCompanyIcon(company.type) }}</span>
              <div class="company-details">
                <h4 class="company-name">{{ company.name || company.id }}</h4>
                <p class="company-id">ID: {{ company.id }}</p>
              </div>
            </div>
            
            <div class="company-status">
              <span class="status-badge" :class="getStatusBadgeClass(company.status)">
                {{ getStatusIcon(company.status) }} {{ getStatusText(company.status) }}
              </span>
            </div>
          </div>
          
          <!-- Company Metrics -->
          <div class="company-metrics">
            <div class="metric-group">
              <div class="metric-item">
                <span class="metric-label">Documentos:</span>
                <span class="metric-value">{{ company.documents_count || 0 }}</span>
              </div>
              <div class="metric-item">
                <span class="metric-label">Conversaciones:</span>
                <span class="metric-value">{{ company.conversations_count || 0 }}</span>
              </div>
              <div class="metric-item">
                <span class="metric-label">Última actividad:</span>
                <span class="metric-value">{{ formatLastActivity(company.last_activity) }}</span>
              </div>
            </div>
            
            <!-- Health Indicators -->
            <div class="health-indicators">
              <div
                v-for="service in getCompanyServices(company)"
                :key="service.name"
                class="health-indicator"
                :class="getServiceHealthClass(service.status)"
                :title="`${service.name}: ${service.status}`"
              >
                <span class="service-icon">{{ getServiceIcon(service.name) }}</span>
              </div>
            </div>
          </div>
          
          <!-- Company Actions -->
          <div class="company-actions">
            <button
              @click.stop="switchToCompany(company)"
              class="action-btn primary"
              title="Cambiar a esta empresa"
            >
              🔄 Cambiar
            </button>
            <button
              @click.stop="testCompany(company)"
              class="action-btn secondary"
              title="Probar conexión"
            >
              🧪 Probar
            </button>
            <button
              @click.stop="viewCompanyDetails(company)"
              class="action-btn info"
              title="Ver detalles"
            >
              👁️ Detalles
            </button>
          </div>
          
          <!-- Expandable Details -->
          <Transition name="company-details">
            <div v-if="selectedCompanyId === company.id" class="company-expanded">
              <div class="expanded-content">
                <h5>Configuración</h5>
                <div class="config-grid">
                  <div class="config-item">
                    <span class="config-label">Vectorstore:</span>
                    <span class="config-value">{{ company.vectorstore_status || 'N/A' }}</span>
                  </div>
                  <div class="config-item">
                    <span class="config-label">OpenAI Key:</span>
                    <span class="config-value">{{ company.openai_configured ? '✅ Configurada' : '❌ No configurada' }}</span>
                  </div>
                  <div class="config-item">
                    <span class="config-label">Calendar:</span>
                    <span class="config-value">{{ company.calendar_enabled ? '✅ Habilitado' : '❌ Deshabilitado' }}</span>
                  </div>
                </div>
                
                <div v-if="company.recent_errors && company.recent_errors.length > 0" class="recent-errors">
                  <h5>Errores Recientes</h5>
                  <div class="error-list">
                    <div
                      v-for="(error, index) in company.recent_errors.slice(0, 3)"
                      :key="index"
                      class="error-item"
                    >
                      <span class="error-time">{{ formatTimestamp(error.timestamp) }}</span>
                      <span class="error-message">{{ error.message }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </Transition>
        </div>
      </div>
      
      <!-- No Companies Message -->
      <div v-if="sortedCompanies.length === 0" class="no-companies">
        <div class="no-companies-icon">🏢</div>
        <h4>No hay empresas configuradas</h4>
        <p>Configura al menos una empresa para comenzar.</p>
      </div>
    </div>
    
    <!-- Error State -->
    <div v-else class="error-state">
      <div class="error-icon">❌</div>
      <h4>Error al cargar estado de empresas</h4>
      <p>No se pudo obtener la información del estado de las empresas.</p>
      <button @click="$emit('refresh')" class="retry-btn">
        🔄 Reintentar
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAppStore } from '@/stores/app'
import { useNotifications } from '@/composables/useNotifications'

// ============================================================================
// PROPS & EMITS
// ============================================================================

const props = defineProps({
  companiesStatus: {
    type: [Object, Array],
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['refresh', 'company-selected', 'company-tested'])

// ============================================================================
// STORES & COMPOSABLES
// ============================================================================

const appStore = useAppStore()
const { showNotification } = useNotifications()

// ============================================================================
// ESTADO LOCAL
// ============================================================================

const selectedCompanyId = ref(null)

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const companiesArray = computed(() => {
  if (!props.companiesStatus) return []
  
  // Handle different response formats
  if (Array.isArray(props.companiesStatus)) {
    return props.companiesStatus
  }
  
  if (props.companiesStatus.companies) {
    // If it's an object with companies property
    const companies = props.companiesStatus.companies
    if (Array.isArray(companies)) {
      return companies
    }
    
    // If companies is an object, convert to array
    return Object.keys(companies).map(id => ({
      id,
      ...companies[id]
    }))
  }
  
  return []
})

const sortedCompanies = computed(() => {
  return [...companiesArray.value].sort((a, b) => {
    // Sort by status (errors first, then warnings, then healthy)
    const statusOrder = { 'error': 0, 'warning': 1, 'healthy': 2, 'unknown': 3 }
    const aOrder = statusOrder[a.status] || 3
    const bOrder = statusOrder[b.status] || 3
    
    if (aOrder !== bOrder) {
      return aOrder - bOrder
    }
    
    // Then sort by name
    return (a.name || a.id).localeCompare(b.name || b.id)
  })
})

const totalCompanies = computed(() => companiesArray.value.length)

const healthyCompanies = computed(() => 
  companiesArray.value.filter(c => c.status === 'healthy').length
)

const warningCompanies = computed(() => 
  companiesArray.value.filter(c => c.status === 'warning').length
)

const errorCompanies = computed(() => 
  companiesArray.value.filter(c => c.status === 'error').length
)

// ============================================================================
// MÉTODOS
// ============================================================================

/**
 * Select/deselect company for expanded view
 */
const selectCompany = (company) => {
  selectedCompanyId.value = selectedCompanyId.value === company.id ? null : company.id
}

/**
 * Switch to selected company
 */
const switchToCompany = (company) => {
  emit('company-selected', company.id)
  showNotification(`Cambiando a empresa: ${company.name || company.id}`, 'info')
  appStore.addToLog(`Company selected from status: ${company.id}`, 'info')
}

/**
 * Test company connection
 */
const testCompany = async (company) => {
  try {
    showNotification(`Probando conexión con ${company.name || company.id}...`, 'info')
    
    // Emit test event - parent component should handle the actual testing
    emit('company-tested', company.id)
    
    appStore.addToLog(`Company test initiated: ${company.id}`, 'info')
    
  } catch (error) {
    console.error('Error testing company:', error)
    showNotification(`Error probando empresa: ${error.message}`, 'error')
  }
}

/**
 * View company details
 */
const viewCompanyDetails = (company) => {
  // Toggle expanded view
  selectCompany(company)
  appStore.addToLog(`Viewing company details: ${company.id}`, 'info')
}

/**
 * Get company status class
 */
const getCompanyStatusClass = (status) => {
  const classMap = {
    'healthy': 'company-healthy',
    'warning': 'company-warning', 
    'error': 'company-error',
    'offline': 'company-offline'
  }
  return classMap[status] || 'company-unknown'
}

/**
 * Get status badge class
 */
const getStatusBadgeClass = (status) => {
  const classMap = {
    'healthy': 'badge-healthy',
    'warning': 'badge-warning',
    'error': 'badge-error',
    'offline': 'badge-offline'
  }
  return classMap[status] || 'badge-unknown'
}

/**
 * Get status icon
 */
const getStatusIcon = (status) => {
  const iconMap = {
    'healthy': '✅',
    'warning': '⚠️',
    'error': '❌',
    'offline': '🔌'
  }
  return iconMap[status] || '❓'
}

/**
 * Get status text
 */
const getStatusText = (status) => {
  const textMap = {
    'healthy': 'Saludable',
    'warning': 'Advertencia',
    'error': 'Error',
    'offline': 'Desconectada'
  }
  return textMap[status] || 'Desconocido'
}

/**
 * Get company icon based on type
 */
const getCompanyIcon = (type) => {
  const iconMap = {
    'clinic': '🏥',
    'spa': '🧖‍♀️',
    'dental': '🦷',
    'beauty': '💄',
    'wellness': '🌿'
  }
  return iconMap[type] || '🏢'
}

/**
 * Get company services
 */
const getCompanyServices = (company) => {
  if (company.services) {
    return company.services
  }
  
  // Default services
  return [
    { name: 'API', status: company.api_status || 'healthy' },
    { name: 'Vectorstore', status: company.vectorstore_status || 'healthy' },
    { name: 'OpenAI', status: company.openai_status || 'healthy' }
  ]
}

/**
 * Get service icon
 */
const getServiceIcon = (serviceName) => {
  const iconMap = {
    'API': '🌐',
    'Vectorstore': '📊',
    'OpenAI': '🤖',
    'Calendar': '📅',
    'Storage': '💾'
  }
  return iconMap[serviceName] || '⚙️'
}

/**
 * Get service health class
 */
const getServiceHealthClass = (status) => {
  const classMap = {
    'healthy': 'service-healthy',
    'warning': 'service-warning',
    'error': 'service-error',
    'offline': 'service-offline'
  }
  return classMap[status] || 'service-unknown'
}

/**
 * Format last activity
 */
const formatLastActivity = (lastActivity) => {
  if (!lastActivity) return 'Nunca'
  
  try {
    const date = new Date(lastActivity)
    const now = new Date()
    const diffTime = Math.abs(now - date)
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
    
    if (diffDays === 0) return 'Hoy'
    if (diffDays === 1) return 'Ayer'
    if (diffDays < 7) return `Hace ${diffDays} días`
    if (diffDays < 30) return `Hace ${Math.floor(diffDays / 7)} semanas`
    
    return date.toLocaleDateString('es-ES')
  } catch {
    return 'Fecha inválida'
  }
}

/**
 * Format timestamp
 */
const formatTimestamp = (timestamp) => {
  try {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('es-ES')
  } catch {
    return 'Hora inválida'
  }
}
</script>

<style scoped>
.companies-status {
  width: 100%;
}

.loading-state {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-secondary);
}

.loading-spinner {
  font-size: 2em;
  margin-bottom: 10px;
  animation: spin 1s linear infinite;
}

.companies-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.summary-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  background: var(--bg-tertiary);
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.stat-icon {
  font-size: 1.5em;
}

.stat-details {
  display: flex;
  flex-direction: column;
}

.stat-number {
  font-size: 1.4em;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1;
}

.stat-label {
  font-size: 0.8em;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-item.total {
  border-left: 3px solid var(--info-color);
}

.stat-item.healthy {
  border-left: 3px solid var(--success-color);
}

.stat-item.warning {
  border-left: 3px solid var(--warning-color);
}

.stat-item.error {
  border-left: 3px solid var(--danger-color);
}

.companies-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.company-item {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.company-item:hover {
  border-color: var(--primary-color);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* Company Status Classes */
.company-healthy {
  border-left: 3px solid var(--success-color);
}

.company-warning {
  border-left: 3px solid var(--warning-color);
  background: rgba(245, 158, 11, 0.02);
}

.company-error {
  border-left: 3px solid var(--danger-color);
  background: rgba(239, 68, 68, 0.02);
}

.company-offline {
  border-left: 3px solid var(--text-muted);
  opacity: 0.7;
}

.company-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.company-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.company-icon {
  font-size: 1.5em;
  min-width: 32px;
  text-align: center;
}

.company-details {
  flex: 1;
}

.company-name {
  margin: 0 0 4px 0;
  font-size: 1.1em;
  font-weight: 600;
  color: var(--text-primary);
}

.company-id {
  margin: 0;
  font-size: 0.8em;
  color: var(--text-muted);
  font-family: monospace;
}

.company-status {
  text-align: right;
}

.status-badge {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 0.8em;
  font-weight: 600;
  white-space: nowrap;
}

.badge-healthy {
  background: rgba(34, 197, 94, 0.1);
  color: var(--success-color);
}

.badge-warning {
  background: rgba(245, 158, 11, 0.1);
  color: var(--warning-color);
}

.badge-error {
  background: rgba(239, 68, 68, 0.1);
  color: var(--danger-color);
}

.badge-offline {
  background: rgba(156, 163, 175, 0.1);
  color: var(--text-muted);
}

.company-metrics {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 12px;
}

.metric-group {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.metric-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 0.85em;
}

.metric-label {
  color: var(--text-secondary);
  font-weight: 500;
}

.metric-value {
  color: var(--text-primary);
  font-weight: 600;
}

.health-indicators {
  display: flex;
  gap: 6px;
}

.health-indicator {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8em;
}

.service-healthy {
  background: rgba(34, 197, 94, 0.2);
  color: var(--success-color);
}

.service-warning {
  background: rgba(245, 158, 11, 0.2);
  color: var(--warning-color);
}

.service-error {
  background: rgba(239, 68, 68, 0.2);
  color: var(--danger-color);
}

.service-offline {
  background: rgba(156, 163, 175, 0.2);
  color: var(--text-muted);
}

.company-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.action-btn {
  padding: 6px 12px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8em;
  font-weight: 500;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.action-btn.primary {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: white;
}

.action-btn.primary:hover {
  background: var(--primary-color-dark);
}

.action-btn.secondary {
  background: var(--bg-secondary);
  color: var(--text-secondary);
}

.action-btn.secondary:hover {
  background: var(--bg-primary);
  color: var(--text-primary);
}

.action-btn.info {
  background: var(--info-color);
  border-color: var(--info-color);
  color: white;
}

.action-btn.info:hover {
  background: var(--info-color-dark);
}

.company-expanded {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

.company-details-enter-active,
.company-details-leave-active {
  transition: all 0.3s ease;
  max-height: 300px;
  opacity: 1;
}

.company-details-enter-from,
.company-details-leave-to {
  max-height: 0;
  opacity: 0;
}

.expanded-content h5 {
  margin: 0 0 12px 0;
  font-size: 1em;
  font-weight: 600;
  color: var(--text-primary);
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 8px;
  margin-bottom: 16px;
}

.config-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 8px;
  background: var(--bg-secondary);
  border-radius: 4px;
  font-size: 0.85em;
}

.config-label {
  color: var(--text-secondary);
  font-weight: 500;
}

.config-value {
  color: var(--text-primary);
  font-weight: 600;
}

.recent-errors {
  margin-top: 16px;
}

.error-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.error-item {
  display: flex;
  gap: 8px;
  padding: 6px 8px;
  background: rgba(239, 68, 68, 0.05);
  border-left: 2px solid var(--danger-color);
  border-radius: 4px;
  font-size: 0.8em;
}

.error-time {
  color: var(--text-muted);
  font-family: monospace;
  min-width: 60px;
}

.error-message {
  color: var(--text-secondary);
  flex: 1;
}

.no-companies {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-secondary);
}

.no-companies-icon {
  font-size: 3em;
  margin-bottom: 15px;
  opacity: 0.5;
}

.no-companies h4 {
  margin: 0 0 10px 0;
  color: var(--text-primary);
}

.error-state {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-secondary);
}

.error-icon {
  font-size: 3em;
  margin-bottom: 15px;
}

.error-state h4 {
  margin: 0 0 10px 0;
  color: var(--text-primary);
}

.retry-btn {
  background: var(--primary-color);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s ease;
}

.retry-btn:hover {
  background: var(--primary-color-dark);
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Responsive */
@media (max-width: 768px) {
  .summary-stats {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .company-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .company-metrics {
    flex-direction: column;
    align-items: stretch;
  }
  
  .metric-group {
    justify-content: space-between;
  }
  
  .health-indicators {
    justify-content: center;
  }
  
  .company-actions {
    justify-content: center;
  }
  
  .config-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 480px) {
  .summary-stats {
    grid-template-columns: 1fr;
  }
  
  .company-item {
    padding: 12px;
  }
  
  .action-btn {
    flex: 1;
    text-align: center;
  }
  
  .metric-group {
    flex-direction: column;
    gap: 8px;
  }
}
</style>
