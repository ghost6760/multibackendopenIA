<template>
  <div class="company-health-checker">
    <div class="checker-header">
      <h3>🏢 Health Check de Empresas</h3>
      <p>Verifica el estado de salud de todas las empresas configuradas en el sistema</p>
    </div>

    <!-- Controls -->
    <div class="checker-controls">
      <button 
        @click="performCompanyHealthCheck" 
        :disabled="isPerformingCheck"
        class="btn btn-primary"
      >
        <span v-if="isPerformingCheck">⏳ Verificando...</span>
        <span v-else>🔍 Verificar Empresas</span>
      </button>

      <button 
        v-if="companyHealthResults"
        @click="refreshCompanyHealthCheck" 
        :disabled="isPerformingCheck"
        class="btn btn-secondary"
      >
        🔄 Actualizar
      </button>

      <button 
        v-if="companyHealthResults"
        @click="clearResults" 
        class="btn btn-outline"
      >
        🗑️ Limpiar
      </button>

      <button 
        v-if="companyHealthResults && Object.keys(companyHealthResults.companies || {}).length > 0"
        @click="checkSpecificCompany" 
        class="btn btn-info"
      >
        🎯 Verificar Empresa Específica
      </button>
    </div>

    <!-- Company Health Overview -->
    <div v-if="companyHealthResults" class="health-overview">
      <div class="overview-stats">
        <div class="stat-card healthy">
          <div class="stat-icon">✅</div>
          <div class="stat-content">
            <div class="stat-number">{{ healthyCompaniesCount }}</div>
            <div class="stat-label">Empresas Saludables</div>
          </div>
        </div>

        <div class="stat-card warning">
          <div class="stat-icon">⚠️</div>
          <div class="stat-content">
            <div class="stat-number">{{ partialCompaniesCount }}</div>
            <div class="stat-label">Con Advertencias</div>
          </div>
        </div>

        <div class="stat-card error">
          <div class="stat-icon">❌</div>
          <div class="stat-content">
            <div class="stat-number">{{ unhealthyCompaniesCount }}</div>
            <div class="stat-label">Con Problemas</div>
          </div>
        </div>

        <div class="stat-card total">
          <div class="stat-icon">🏢</div>
          <div class="stat-content">
            <div class="stat-number">{{ totalCompaniesCount }}</div>
            <div class="stat-label">Total Empresas</div>
          </div>
        </div>
      </div>

      <div class="overview-meta">
        <span>Última verificación: {{ formatTimestamp(companyHealthResults.timestamp) }}</span>
        <span>Duración: {{ companyHealthResults.check_duration || 'N/A' }}</span>
      </div>
    </div>

    <!-- Companies Grid -->
    <div v-if="companyHealthResults?.companies" class="companies-grid">
      <div 
        v-for="(companyData, companyId) in companyHealthResults.companies" 
        :key="companyId"
        class="company-card"
        :class="getCompanyStatusClass(companyData)"
      >
        <div class="company-header">
          <div class="company-title">
            <h4>{{ companyData.name || companyId }}</h4>
            <span class="company-id">{{ companyId }}</span>
          </div>
          <div class="company-status">
            <span class="status-indicator" :class="getStatusIndicatorClass(companyData)"></span>
            <span class="status-text">{{ getCompanyStatusText(companyData) }}</span>
          </div>
        </div>

        <div class="company-details">
          <!-- System Health -->
          <div class="detail-row">
            <span class="detail-label">Sistema:</span>
            <span :class="companyData.system_healthy ? 'status-healthy' : 'status-error'">
              {{ companyData.system_healthy ? 'Saludable' : 'Con problemas' }}
            </span>
          </div>

          <!-- Database Health -->
          <div class="detail-row">
            <span class="detail-label">Base de Datos:</span>
            <span :class="companyData.database_healthy ? 'status-healthy' : 'status-error'">
              {{ companyData.database_healthy ? 'Conectada' : 'Desconectada' }}
            </span>
          </div>

          <!-- Configuration -->
          <div class="detail-row">
            <span class="detail-label">Configuración:</span>
            <span :class="companyData.config_valid ? 'status-healthy' : 'status-error'">
              {{ companyData.config_valid ? 'Válida' : 'Inválida' }}
            </span>
          </div>

          <!-- Services Count -->
          <div v-if="companyData.services" class="detail-row">
            <span class="detail-label">Servicios:</span>
            <span class="status-info">
              {{ Object.keys(companyData.services).length }} configurados
            </span>
          </div>

          <!-- Last Activity -->
          <div v-if="companyData.last_activity" class="detail-row">
            <span class="detail-label">Última actividad:</span>
            <span class="status-info">{{ formatRelativeTime(companyData.last_activity) }}</span>
          </div>

          <!-- Error Messages -->
          <div v-if="companyData.errors && companyData.errors.length > 0" class="company-errors">
            <h5>⚠️ Errores Detectados:</h5>
            <ul class="error-list">
              <li v-for="error in companyData.errors" :key="error" class="error-item">
                {{ error }}
              </li>
            </ul>
          </div>

          <!-- Services Detail -->
          <div v-if="companyData.services" class="services-detail">
            <h5>🔧 Estado de Servicios:</h5>
            <div class="services-list">
              <div 
                v-for="(serviceData, serviceName) in companyData.services" 
                :key="serviceName"
                class="service-item"
                :class="getServiceStatusClass(serviceData)"
              >
                <span class="service-name">{{ formatServiceName(serviceName) }}</span>
                <span class="service-status">{{ getServiceStatusText(serviceData) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="company-actions">
          <button 
            @click="checkSingleCompany(companyId)" 
            :disabled="isCheckingSingle"
            class="btn btn-small btn-primary"
          >
            🔍 Verificar
          </button>
          <button 
            @click="viewCompanyDetails(companyId, companyData)" 
            class="btn btn-small btn-secondary"
          >
            📋 Detalles
          </button>
        </div>
      </div>
    </div>

    <!-- Company Details Modal -->
    <div v-if="showCompanyModal" class="modal-overlay" @click="closeCompanyModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h4>📊 Detalles de {{ selectedCompany?.name || selectedCompanyId }}</h4>
          <button @click="closeCompanyModal" class="btn btn-small btn-outline">✖️</button>
        </div>
        <div class="modal-body">
          <pre class="json-container">{{ formatJSON(selectedCompany) }}</pre>
        </div>
      </div>
    </div>

    <!-- Error Display -->
    <div v-if="errorMessage" class="health-error">
      <h4>❌ Error en Health Check</h4>
      <p>{{ errorMessage }}</p>
      <button @click="retryHealthCheck" class="btn btn-danger">
        🔄 Reintentar
      </button>
    </div>

    <!-- No Data State -->
    <div v-if="!companyHealthResults && !isPerformingCheck && !errorMessage" class="no-data-state">
      <div class="no-data-icon">🏢</div>
      <h4>Health Check de Empresas</h4>
      <p>Ejecuta una verificación de salud para revisar el estado de todas las empresas configuradas</p>
      <button @click="performCompanyHealthCheck" class="btn btn-primary">
        🚀 Verificar Empresas
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'

// ============================================================================
// ESTADO REACTIVO
// ============================================================================

const appStore = useAppStore()
const { apiRequest } = useApiRequest()
const { showNotification } = useNotifications()

const isPerformingCheck = ref(false)
const isCheckingSingle = ref(false)
const companyHealthResults = ref(null)
const errorMessage = ref('')
const showCompanyModal = ref(false)
const selectedCompany = ref(null)
const selectedCompanyId = ref('')

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const totalCompaniesCount = computed(() => {
  return Object.keys(companyHealthResults.value?.companies || {}).length
})

const healthyCompaniesCount = computed(() => {
  if (!companyHealthResults.value?.companies) return 0
  return Object.values(companyHealthResults.value.companies).filter(company => 
    company.system_healthy && company.database_healthy && company.config_valid
  ).length
})

const partialCompaniesCount = computed(() => {
  if (!companyHealthResults.value?.companies) return 0
  return Object.values(companyHealthResults.value.companies).filter(company => {
    const checks = [company.system_healthy, company.database_healthy, company.config_valid]
    const healthyCount = checks.filter(Boolean).length
    return healthyCount > 0 && healthyCount < checks.length
  }).length
})

const unhealthyCompaniesCount = computed(() => {
  if (!companyHealthResults.value?.companies) return 0
  return Object.values(companyHealthResults.value.companies).filter(company => 
    !company.system_healthy && !company.database_healthy && !company.config_valid
  ).length
})

// ============================================================================
// FUNCIONES PRINCIPALES MIGRADAS DEL SCRIPT.JS
// ============================================================================

/**
 * Realiza health check de empresas - MIGRADO: performCompanyHealthCheck() de script.js
 * PRESERVAR: Comportamiento exacto de la función original
 */
const performCompanyHealthCheck = async () => {
  isPerformingCheck.value = true
  companyHealthResults.value = null
  errorMessage.value = ''
  
  try {
    appStore.addToLog('Performing company health check', 'info')
    showNotification('Ejecutando health check de empresas...', 'info')
    
    const startTime = Date.now()
    
    // Llamada a la API - PRESERVAR ENDPOINT EXACTO
    const response = await apiRequest('/api/health/companies')
    
    const endTime = Date.now()
    
    companyHealthResults.value = {
      ...response,
      timestamp: response.timestamp || Date.now(),
      check_duration: `${endTime - startTime}ms`
    }
    
    // Mostrar notificación basada en resultados - PRESERVAR: Misma lógica que script.js
    const totalCompanies = totalCompaniesCount.value
    const healthyCompanies = healthyCompaniesCount.value
    
    if (healthyCompanies === totalCompanies && totalCompanies > 0) {
      showNotification(`✅ Todas las empresas (${totalCompanies}) están saludables`, 'success')
    } else if (healthyCompanies > 0) {
      showNotification(`⚠️ ${healthyCompanies}/${totalCompanies} empresas saludables`, 'warning')
    } else if (totalCompanies > 0) {
      showNotification(`❌ Todas las empresas tienen problemas`, 'error')
    } else {
      showNotification('ℹ️ No se encontraron empresas configuradas', 'info')
    }
    
    appStore.addToLog(`Company health check completed - ${healthyCompanies}/${totalCompanies} healthy`, 'info')
    
  } catch (error) {
    appStore.addToLog(`Company health check failed: ${error.message}`, 'error')
    errorMessage.value = error.message
    showNotification(`Error en health check de empresas: ${error.message}`, 'error')
  } finally {
    isPerformingCheck.value = false
  }
}

/**
 * Verificar empresa específica - PRESERVAR: Funcionalidad de script.js
 */
const checkSingleCompany = async (companyId) => {
  isCheckingSingle.value = true
  
  try {
    appStore.addToLog(`Checking health for company: ${companyId}`, 'info')
    showNotification(`Verificando empresa ${companyId}...`, 'info')
    
    // Llamada a la API - PRESERVAR ENDPOINT EXACTO
    const response = await apiRequest(`/api/health/company/${companyId}`)
    
    // Actualizar datos de la empresa específica
    if (companyHealthResults.value?.companies) {
      companyHealthResults.value.companies[companyId] = {
        ...companyHealthResults.value.companies[companyId],
        ...response,
        last_checked: Date.now()
      }
    }
    
    const isHealthy = response.system_healthy && response.database_healthy && response.config_valid
    showNotification(
      `${isHealthy ? '✅' : '❌'} Empresa ${companyId}: ${isHealthy ? 'Saludable' : 'Con problemas'}`,
      isHealthy ? 'success' : 'error'
    )
    
    appStore.addToLog(`Single company check completed for ${companyId}`, 'info')
    
  } catch (error) {
    appStore.addToLog(`Single company check failed for ${companyId}: ${error.message}`, 'error')
    showNotification(`Error verificando empresa ${companyId}: ${error.message}`, 'error')
  } finally {
    isCheckingSingle.value = false
  }
}

/**
 * Verificar empresa específica mediante prompt
 */
const checkSpecificCompany = async () => {
  const companyId = prompt('Ingresa el ID de la empresa a verificar:')
  if (companyId) {
    await checkSingleCompany(companyId.trim())
  }
}

/**
 * Actualizar health check de empresas
 */
const refreshCompanyHealthCheck = () => {
  appStore.addToLog('Refreshing company health check', 'info')
  performCompanyHealthCheck()
}

/**
 * Reintentar health check en caso de error
 */
const retryHealthCheck = () => {
  errorMessage.value = ''
  performCompanyHealthCheck()
}

/**
 * Limpiar resultados
 */
const clearResults = () => {
  companyHealthResults.value = null
  errorMessage.value = ''
  appStore.addToLog('Company health check results cleared', 'info')
  showNotification('Resultados del health check limpiados', 'info')
}

/**
 * Ver detalles de empresa
 */
const viewCompanyDetails = (companyId, companyData) => {
  selectedCompanyId.value = companyId
  selectedCompany.value = companyData
  showCompanyModal.value = true
}

/**
 * Cerrar modal de detalles
 */
const closeCompanyModal = () => {
  showCompanyModal.value = false
  selectedCompany.value = null
  selectedCompanyId.value = ''
}

// ============================================================================
// FUNCIONES DE UTILIDAD
// ============================================================================

const getCompanyStatusClass = (companyData) => {
  if (companyData.system_healthy && companyData.database_healthy && companyData.config_valid) {
    return 'company-healthy'
  }
  
  const checks = [companyData.system_healthy, companyData.database_healthy, companyData.config_valid]
  const healthyCount = checks.filter(Boolean).length
  
  if (healthyCount > 0) {
    return 'company-partial'
  }
  
  return 'company-unhealthy'
}

const getStatusIndicatorClass = (companyData) => {
  if (companyData.system_healthy && companyData.database_healthy && companyData.config_valid) {
    return 'status-healthy'
  }
  
  const checks = [companyData.system_healthy, companyData.database_healthy, companyData.config_valid]
  const healthyCount = checks.filter(Boolean).length
  
  if (healthyCount > 0) {
    return 'status-warning'
  }
  
  return 'status-error'
}

const getCompanyStatusText = (companyData) => {
  if (companyData.system_healthy && companyData.database_healthy && companyData.config_valid) {
    return 'Saludable'
  }
  
  const checks = [companyData.system_healthy, companyData.database_healthy, companyData.config_valid]
  const healthyCount = checks.filter(Boolean).length
  
  if (healthyCount > 0) {
    return 'Parcial'
  }
  
  return 'Con problemas'
}

const getServiceStatusClass = (serviceData) => {
  if (typeof serviceData === 'boolean') {
    return serviceData ? 'service-healthy' : 'service-error'
  }
  if (serviceData?.status === 'healthy' || serviceData?.status === 'operational') {
    return 'service-healthy'
  }
  if (serviceData?.status === 'warning' || serviceData?.status === 'degraded') {
    return 'service-warning'
  }
  return 'service-error'
}

const getServiceStatusText = (serviceData) => {
  if (typeof serviceData === 'boolean') {
    return serviceData ? 'Operativo' : 'Error'
  }
  if (serviceData?.status) {
    const statusMap = {
      healthy: 'Saludable',
      operational: 'Operativo',
      warning: 'Advertencia',
      degraded: 'Degradado',
      error: 'Error',
      down: 'Inactivo'
    }
    return statusMap[serviceData.status] || 'Desconocido'
  }
  return 'Desconocido'
}

const formatServiceName = (serviceName) => {
  return serviceName
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase())
}

const formatTimestamp = (timestamp) => {
  return new Date(timestamp).toLocaleString()
}

const formatRelativeTime = (timestamp) => {
  const now = Date.now()
  const diff = now - new Date(timestamp).getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)
  
  if (days > 0) return `Hace ${days} día${days > 1 ? 's' : ''}`
  if (hours > 0) return `Hace ${hours} hora${hours > 1 ? 's' : ''}`
  if (minutes > 0) return `Hace ${minutes} minuto${minutes > 1 ? 's' : ''}`
  return 'Hace un momento'
}

const formatJSON = (obj) => {
  return JSON.stringify(obj, null, 2)
}

// ============================================================================
// LIFECYCLE HOOKS
// ============================================================================

onMounted(() => {
  appStore.addToLog('CompanyHealthChecker component mounted', 'info')
  
  // EXPONER FUNCIÓN GLOBAL PARA COMPATIBILIDAD
  window.performCompanyHealthCheck = performCompanyHealthCheck
})

onUnmounted(() => {
  // Limpiar función global
  if (typeof window !== 'undefined') {
    delete window.performCompanyHealthCheck
  }
  
  appStore.addToLog('CompanyHealthChecker component unmounted', 'info')
})
</script>

<style scoped>
.company-health-checker {
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  padding: 24px;
  border: 1px solid var(--border-color);
}

.checker-header {
  margin-bottom: 24px;
  text-align: center;
}

.checker-header h3 {
  color: var(--text-primary);
  margin-bottom: 8px;
  font-size: 1.5rem;
}

.checker-header p {
  color: var(--text-secondary);
  font-size: 0.95rem;
}

.checker-controls {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  justify-content: center;
  flex-wrap: wrap;
}

.health-overview {
  margin-bottom: 32px;
}

.overview-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  border-radius: var(--radius-md);
  border: 1px solid;
}

.stat-card.healthy {
  background: var(--success-bg);
  border-color: var(--success-color);
}

.stat-card.warning {
  background: var(--warning-bg);
  border-color: var(--warning-color);
}

.stat-card.error {
  background: var(--error-bg);
  border-color: var(--error-color);
}

.stat-card.total {
  background: var(--info-bg);
  border-color: var(--info-color);
}

.stat-icon {
  font-size: 2rem;
  line-height: 1;
}

.stat-number {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1;
}

.stat-label {
  font-size: 0.9rem;
  color: var(--text-secondary);
  margin-top: 4px;
}

.overview-meta {
  display: flex;
  gap: 24px;
  justify-content: center;
  font-size: 0.9rem;
  color: var(--text-secondary);
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
}

.companies-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 20px;
}

.company-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  padding: 20px;
  transition: all 0.3s ease;
}

.company-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.company-card.company-healthy {
  border-color: var(--success-color);
  background: var(--success-bg);
}

.company-card.company-partial {
  border-color: var(--warning-color);
  background: var(--warning-bg);
}

.company-card.company-unhealthy {
  border-color: var(--error-color);
  background: var(--error-bg);
}

.company-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-light);
}

.company-title h4 {
  color: var(--text-primary);
  margin-bottom: 4px;
  font-size: 1.1rem;
}

.company-id {
  font-size: 0.8rem;
  color: var(--text-muted);
  background: var(--bg-tertiary);
  padding: 2px 6px;
  border-radius: 3px;
}

.company-status {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.status-healthy { background: var(--success-color); }
.status-warning { background: var(--warning-color); }
.status-error { background: var(--error-color); }
.status-info { color: var(--text-secondary); }

.status-text {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text-primary);
}

.company-details {
  margin-bottom: 16px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 0.9rem;
}

.detail-label {
  color: var(--text-secondary);
}

.company-errors {
  margin: 16px 0;
  padding: 12px;
  background: var(--error-bg);
  border-radius: var(--radius-sm);
  border: 1px solid var(--error-color);
}

.company-errors h5 {
  color: var(--error-color);
  margin-bottom: 8px;
  font-size: 0.9rem;
}

.error-list {
  margin: 0;
  padding-left: 16px;
}

.error-item {
  color: var(--error-color);
  font-size: 0.85rem;
  margin-bottom: 4px;
}

.services-detail {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--border-light);
}

.services-detail h5 {
  color: var(--text-primary);
  margin-bottom: 12px;
  font-size: 0.9rem;
}

.services-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 8px;
}

.service-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
}

.service-item.service-healthy {
  background: var(--success-bg);
  border: 1px solid var(--success-color);
}

.service-item.service-warning {
  background: var(--warning-bg);
  border: 1px solid var(--warning-color);
}

.service-item.service-error {
  background: var(--error-bg);
  border: 1px solid var(--error-color);
}

.service-name {
  color: var(--text-primary);
  font-weight: 500;
}

.service-status {
  color: var(--text-secondary);
}

.company-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  min-width: 500px;
  max-width: 80%;
  width: 90%;
  max-height: 80%;
  box-shadow: 0 10px 30px rgba(0,0,0,0.3);
  overflow: hidden;
}

.modal-header {
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-light);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h4 {
  color: var(--text-primary);
  margin: 0;
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
}

.json-container {
  background: var(--bg-code);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  padding: 16px;
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 0.85rem;
  color: var(--text-code);
  overflow-x: auto;
  max-height: 400px;
  overflow-y: auto;
}

.health-error {
  text-align: center;
  padding: 32px;
  background: var(--error-bg);
  border: 1px solid var(--error-color);
  border-radius: var(--radius-md);
}

.health-error h4 {
  color: var(--error-color);
  margin-bottom: 12px;
}

.health-error p {
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.no-data-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-secondary);
}

.no-data-icon {
  font-size: 4rem;
  margin-bottom: 20px;
}

.no-data-state h4 {
  color: var(--text-primary);
  margin-bottom: 12px;
}

.no-data-state p {
  margin-bottom: 24px;
  line-height: 1.5;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.9rem;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-hover);
}

.btn-secondary {
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-hover);
}

.btn-info {
  background: var(--info-color);
  color: white;
}

.btn-info:hover:not(:disabled) {
  background: var(--info-hover);
}

.btn-danger {
  background: var(--error-color);
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: var(--error-hover);
}

.btn-small {
  padding: 6px 12px;
  font-size: 0.8rem;
}

.btn-outline {
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.btn-outline:hover {
  background: var(--bg-hover);
}
</style>
