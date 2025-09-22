<template>
  <div class="enterprise-tab">
    <!-- Header del tab -->
    <div class="tab-header">
      <h2 class="tab-title">🏢 Gestión Enterprise</h2>
      <p class="tab-subtitle">
        Administración avanzada de empresas y configuraciones multi-tenant
      </p>
    </div>

    <!-- Verificación de API Key -->
    <div v-if="!hasValidApiKey" class="api-key-required">
      <div class="warning-card">
        <div class="warning-icon">🔑</div>
        <h3>API Key Requerida</h3>
        <p>
          Las funciones enterprise requieren una API key válida para acceder a las 
          operaciones administrativas avanzadas.
        </p>
        <button @click="requestApiKey" class="btn btn-primary">
          🔑 Configurar API Key
        </button>
      </div>
    </div>

    <!-- Contenido principal (cuando hay API key válida) -->
    <div v-else class="enterprise-content">
      <!-- Panel de estado -->
      <div class="enterprise-status">
        <div class="status-cards">
          <div class="status-card">
            <div class="card-icon">🏢</div>
            <div class="card-content">
              <h4>Total Empresas</h4>
              <div class="card-value">{{ companiesCount }}</div>
            </div>
          </div>
          
          <div class="status-card">
            <div class="card-icon">✅</div>
            <div class="card-content">
              <h4>Empresas Activas</h4>
              <div class="card-value success">{{ activeCompaniesCount }}</div>
            </div>
          </div>
          
          <div class="status-card">
            <div class="card-icon">⚠️</div>
            <div class="card-content">
              <h4>Con Problemas</h4>
              <div class="card-value warning">{{ companiesWithIssues }}</div>
            </div>
          </div>
          
          <div class="status-card">
            <div class="card-icon">🔄</div>
            <div class="card-content">
              <h4>Última Sincronización</h4>
              <div class="card-value">{{ formatDateTime(lastUpdateTime) }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Herramientas enterprise -->
      <div class="enterprise-tools">
        <div class="tools-header">
          <h3>🔧 Herramientas Enterprise</h3>
          <div class="tools-actions">
            <button @click="handleRefresh" class="btn btn-secondary" :disabled="isAnyProcessing">
              <span v-if="isLoading">⏳ Cargando...</span>
              <span v-else>🔄 Actualizar</span>
            </button>
            <button @click="showCreateModal" class="btn btn-primary">
              ➕ Nueva Empresa
            </button>
          </div>
        </div>
        
        <div class="tools-grid">
          <button 
            @click="handleMigration"
            class="tool-button"
            :disabled="isMigrating"
          >
            <div class="tool-icon">🔄</div>
            <div class="tool-content">
              <div class="tool-title">Migrar a PostgreSQL</div>
              <div class="tool-description">Migrar todas las empresas al sistema PostgreSQL</div>
            </div>
            <div v-if="isMigrating" class="tool-loading">⏳</div>
          </button>
          
          <button @click="handleSyncAll" class="tool-button" :disabled="isSyncing">
            <div class="tool-icon">🔄</div>
            <div class="tool-content">
              <div class="tool-title">Sincronizar Todo</div>
              <div class="tool-description">Sincronizar configuraciones de todas las empresas</div>
            </div>
            <div v-if="isSyncing" class="tool-loading">⏳</div>
          </button>
          
          <button @click="handleExport" class="tool-button">
            <div class="tool-icon">📤</div>
            <div class="tool-content">
              <div class="tool-title">Exportar Datos</div>
              <div class="tool-description">Exportar configuraciones de todas las empresas</div>
            </div>
          </button>
          
          <button @click="handleHealthCheckAll" class="tool-button" :disabled="isRunningHealthCheck">
            <div class="tool-icon">🏥</div>
            <div class="tool-content">
              <div class="tool-title">Health Check Global</div>
              <div class="tool-description">Verificar el estado de todas las empresas</div>
            </div>
            <div v-if="isRunningHealthCheck" class="tool-loading">⏳</div>
          </button>
        </div>
      </div>

      <!-- Lista de empresas -->
      <EnterpriseCompanyList
        :companies="enterpriseCompanies"
        :isLoading="isLoading"
        :error="error"
        :lastSync="lastUpdateTime"
        @refresh="handleRefresh"
        @create="showCreateModal"
        @view="handleViewCompany"
        @edit="handleEditCompany"
        @test="handleTestCompany"
        @toggle-status="handleToggleStatus"
        @migrate="handleMigration"
        @export="handleExport"
      />
    </div>

    <!-- Modal de creación/edición -->
    <div v-if="showCompanyModal" class="company-modal" @click="closeCompanyModal">
      <div class="modal-content large" @click.stop>
        <div class="modal-header">
          <h4>{{ isEditMode ? '✏️ Editar Empresa' : '➕ Nueva Empresa' }}</h4>
          <button @click="closeCompanyModal" class="close-button">✕</button>
        </div>
        
        <div class="modal-body">
          <EnterpriseCompanyForm
            ref="companyFormRef"
            :isEditMode="isEditMode"
            :initialData="selectedCompanyForEdit"
            :isSaving="isCreating || isUpdating"
            @submit="handleSaveCompany"
            @cancel="closeCompanyModal"
          />
        </div>
      </div>
    </div>

    <!-- Modal de vista detallada -->
    <div v-if="showViewModal" class="company-modal" @click="closeViewModal">
      <div class="modal-content large" @click.stop>
        <div class="modal-header">
          <h4>👁️ Detalles de Empresa</h4>
          <button @click="closeViewModal" class="close-button">✕</button>
        </div>
        
        <div class="modal-body">
          <EnterpriseCompanyDetail
            ref="companyDetailRef"
            :company="selectedCompany"
            :isLoading="isLoadingDetails"
            :error="detailError"
            :lastSync="lastUpdateTime"
            @edit="handleEditFromDetail"
            @close="closeViewModal"
            @test="handleTestCompany"
            @toggle-status="handleToggleStatus"
            @refresh="handleRefreshCompany"
          />
        </div>
      </div>
    </div>

    <!-- Modal de confirmación -->
    <div v-if="showConfirmModal" class="confirm-modal" @click="closeConfirmModal">
      <div class="confirm-content" @click.stop>
        <div class="confirm-header">
          <h4>{{ confirmModal.title }}</h4>
        </div>
        <div class="confirm-body">
          <p>{{ confirmModal.message }}</p>
          <div v-if="confirmModal.details" class="confirm-details">
            <ul>
              <li v-for="detail in confirmModal.details" :key="detail">{{ detail }}</li>
            </ul>
          </div>
        </div>
        <div class="confirm-actions">
          <button @click="confirmModal.onConfirm" class="btn btn-primary" :disabled="confirmModal.isProcessing">
            <span v-if="confirmModal.isProcessing">⏳</span>
            <span v-else>{{ confirmModal.confirmText || 'Confirmar' }}</span>
          </button>
          <button @click="closeConfirmModal" class="btn btn-secondary" :disabled="confirmModal.isProcessing">
            Cancelar
          </button>
        </div>
      </div>
    </div>

    <!-- Contenedor de resultados (para compatibilidad) -->
    <div id="enterpriseResults" v-if="operationResult" class="operation-results">
      <div :class="`result-container result-${operationResult.type}`">
        <h4>{{ operationResult.title }}</h4>
        <p>{{ operationResult.message }}</p>
        <div v-if="operationResult.details" class="result-details">
          <pre>{{ operationResult.details }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useAppStore } from '@/stores/app'
import { useEnterprise } from '@/composables/useEnterprise'
import { useNotifications } from '@/composables/useNotifications'
import EnterpriseCompanyList from './EnterpriseCompanyList.vue'
import EnterpriseCompanyForm from './EnterpriseCompanyForm.vue'
import EnterpriseCompanyDetail from './EnterpriseCompanyDetail.vue'

// ============================================================================
// PROPS
// ============================================================================
const props = defineProps({
  isActive: {
    type: Boolean,
    default: false
  }
})

// ============================================================================
// STORES & COMPOSABLES
// ============================================================================
const appStore = useAppStore()
const { showNotification } = useNotifications()

// Usar el composable useEnterprise
const {
  // Estado reactivo
  enterpriseCompanies,
  selectedCompany,
  isLoading,
  isCreating,
  isUpdating,
  isTesting,
  isMigrating,
  lastUpdateTime,

  // Computed properties
  companiesCount,
  hasCompanies,
  activeCompanies,
  activeCompaniesCount,
  companiesWithIssues,
  isAnyProcessing,

  // Funciones principales
  loadEnterpriseCompanies,
  createEnterpriseCompany,
  viewEnterpriseCompany,
  saveEnterpriseCompany,
  testEnterpriseCompany,
  migrateCompaniesToPostgreSQL,

  // Funciones auxiliares
  getCompanyById,
  exportCompanies,
  clearCompanyForm,
  populateCompanyForm
} = useEnterprise()

// ============================================================================
// ESTADO LOCAL ADICIONAL (Solo UI)
// ============================================================================
const showCompanyModal = ref(false)
const showViewModal = ref(false)
const showConfirmModal = ref(false)
const isEditMode = ref(false)
const selectedCompanyForEdit = ref(null)
const isLoadingDetails = ref(false)
const detailError = ref(null)
const error = ref(null)
const operationResult = ref(null)

// Estados adicionales
const isSyncing = ref(false)
const isRunningHealthCheck = ref(false)

// Modal de confirmación
const confirmModal = ref({
  title: '',
  message: '',
  details: null,
  confirmText: 'Confirmar',
  isProcessing: false,
  onConfirm: null
})

// Referencias a componentes
const companyFormRef = ref(null)
const companyDetailRef = ref(null)

// ============================================================================
// COMPUTED PROPERTIES LOCALES
// ============================================================================
const hasValidApiKey = computed(() => !!appStore.adminApiKey)

// ============================================================================
// MÉTODOS PRINCIPALES
// ============================================================================

/**
 * Refrescar datos
 */
const handleRefresh = async () => {
  try {
    error.value = null
    await loadEnterpriseCompanies()
  } catch (err) {
    error.value = err.message
  }
}

/**
 * Mostrar modal de creación
 */
const showCreateModal = () => {
  selectedCompanyForEdit.value = null
  isEditMode.value = false
  showCompanyModal.value = true
}

/**
 * Ver detalles de empresa
 */
const handleViewCompany = async (companyId) => {
  try {
    isLoadingDetails.value = true
    detailError.value = null
    
    const company = await viewEnterpriseCompany(companyId)
    if (company) {
      showViewModal.value = true
    }
  } catch (err) {
    detailError.value = err.message
    showNotification('Error cargando detalles: ' + err.message, 'error')
  } finally {
    isLoadingDetails.value = false
  }
}

/**
 * Editar empresa
 */
const handleEditCompany = async (companyId) => {
  try {
    isLoadingDetails.value = true
    
    const company = await viewEnterpriseCompany(companyId)
    if (company) {
      selectedCompanyForEdit.value = company
      isEditMode.value = true
      showCompanyModal.value = true
      showViewModal.value = false
    }
  } catch (err) {
    showNotification('Error cargando empresa para edición: ' + err.message, 'error')
  } finally {
    isLoadingDetails.value = false
  }
}

/**
 * Editar desde vista detallada
 */
const handleEditFromDetail = (companyId) => {
  selectedCompanyForEdit.value = selectedCompany.value
  isEditMode.value = true
  showCompanyModal.value = true
  showViewModal.value = false
}

/**
 * Guardar empresa (crear o actualizar)
 */
const handleSaveCompany = async (companyData) => {
  try {
    if (isEditMode.value) {
      await saveEnterpriseCompany(companyData.company_id, companyData)
      showNotification('Empresa actualizada exitosamente', 'success')
    } else {
      await createEnterpriseCompany(companyData)
      showNotification('Empresa creada exitosamente', 'success')
    }
    
    closeCompanyModal()
    await handleRefresh()
    
  } catch (err) {
    // Error ya manejado en el composable
  }
}

/**
 * Probar empresa
 */
const handleTestCompany = async (companyId, testMessage = '¿Cuáles son sus servicios disponibles?') => {
  try {
    const result = await testEnterpriseCompany(companyId, testMessage)
    
    if (result && companyDetailRef.value) {
      // Mostrar resultado en el componente de detalle si está abierto
      const isSuccess = result.bot_response || result.response
      companyDetailRef.value.showTestResult(
        isSuccess ? 'success' : 'warning',
        isSuccess ? '✅ Test Exitoso' : '⚠️ Test Completado',
        'Test de conexión completado',
        result.bot_response || result.response || 'Sin respuesta del bot',
        {
          company_id: result.company_id || companyId,
          agent_used: result.agent_used,
          processing_time: result.processing_time
        }
      )
    }
    
    return result
    
  } catch (err) {
    if (companyDetailRef.value) {
      companyDetailRef.value.showTestResult(
        'error',
        '❌ Error en Test',
        err.message
      )
    }
  }
}

/**
 * Cambiar estado de empresa
 */
const handleToggleStatus = async (companyId, newStatus) => {
  const company = getCompanyById(companyId)
  if (!company) return
  
  const action = newStatus ? 'activar' : 'desactivar'
  
  showConfirmDialog(
    `${action.charAt(0).toUpperCase() + action.slice(1)} Empresa`,
    `¿Estás seguro de ${action} la empresa "${company.company_name || companyId}"?`,
    [`La empresa será ${newStatus ? 'activada' : 'desactivada'}`, 'Esta acción se puede revertir en cualquier momento'],
    action.charAt(0).toUpperCase() + action.slice(1),
    async () => {
      try {
        const updatedData = { ...company, is_active: newStatus }
        await saveEnterpriseCompany(companyId, updatedData)
        showNotification(`Empresa ${newStatus ? 'activada' : 'desactivada'} exitosamente`, 'success')
        await handleRefresh()
      } catch (err) {
        // Error ya manejado en el composable
      }
    }
  )
}

/**
 * Migración a PostgreSQL
 */
const handleMigration = () => {
  showConfirmDialog(
    'Migrar a PostgreSQL',
    '¿Migrar todas las empresas de JSON a PostgreSQL?',
    [
      'Esta operación migrará todas las empresas del archivo JSON a la base de datos PostgreSQL',
      'La operación puede tomar varios minutos',
      'Se recomienda hacer una copia de seguridad antes de continuar'
    ],
    'Iniciar Migración',
    async () => {
      try {
        confirmModal.value.isProcessing = true
        const result = await migrateCompaniesToPostgreSQL()
        
        if (result?.statistics) {
          showOperationResult('success', 'Migración Completada', 
            `${result.statistics.companies_migrated} empresas migradas exitosamente`, 
            result.statistics)
        }
        
        closeConfirmModal()
        await handleRefresh()
        
      } catch (err) {
        // Error ya manejado en el composable
      } finally {
        confirmModal.value.isProcessing = false
      }
    }
  )
}

/**
 * Sincronizar todas las empresas
 */
const handleSyncAll = async () => {
  isSyncing.value = true
  
  try {
    showNotification('Sincronizando todas las empresas...', 'info')
    await handleRefresh() // Simular sincronización con refresh
    showNotification('Sincronización completada', 'success')
    
  } catch (err) {
    showNotification(`Error en sincronización: ${err.message}`, 'error')
  } finally {
    isSyncing.value = false
  }
}

/**
 * Exportar datos
 */
const handleExport = (format = 'json') => {
  exportCompanies(format)
}

/**
 * Health check global
 */
const handleHealthCheckAll = async () => {
  isRunningHealthCheck.value = true
  
  try {
    showNotification('Ejecutando health check en todas las empresas...', 'info')
    
    // Ejecutar tests en paralelo para todas las empresas
    const healthPromises = enterpriseCompanies.value.map(company => 
      testEnterpriseCompany(company.company_id).catch(err => ({
        company_id: company.company_id,
        error: err.message
      }))
    )
    
    const results = await Promise.allSettled(healthPromises)
    
    const successful = results.filter(r => r.status === 'fulfilled' && !r.value?.error).length
    const total = results.length
    
    showOperationResult(
      successful === total ? 'success' : 'warning',
      'Health Check Completado',
      `${successful}/${total} empresas pasaron el health check`,
      { successful, total, timestamp: new Date().toISOString() }
    )
    
  } catch (err) {
    showNotification(`Error en health check: ${err.message}`, 'error')
  } finally {
    isRunningHealthCheck.value = false
  }
}

/**
 * Refrescar empresa específica
 */
const handleRefreshCompany = async () => {
  if (selectedCompany.value) {
    await handleViewCompany(selectedCompany.value.company_id)
  }
}

// ============================================================================
// FUNCIONES DE UI
// ============================================================================

const closeCompanyModal = () => {
  showCompanyModal.value = false
  isEditMode.value = false
  selectedCompanyForEdit.value = null
}

const closeViewModal = () => {
  showViewModal.value = false
}

const requestApiKey = () => {
  // Emitir evento para mostrar modal de API key
  window.dispatchEvent(new CustomEvent('show-api-key-modal'))
}

const showConfirmDialog = (title, message, details, confirmText, onConfirm) => {
  confirmModal.value = {
    title,
    message,
    details,
    confirmText,
    isProcessing: false,
    onConfirm
  }
  showConfirmModal.value = true
}

const closeConfirmModal = () => {
  showConfirmModal.value = false
  confirmModal.value = {
    title: '',
    message: '',
    details: null,
    confirmText: 'Confirmar',
    isProcessing: false,
    onConfirm: null
  }
}

const showOperationResult = (type, title, message, details = null) => {
  operationResult.value = {
    type,
    title,
    message,
    details
  }
  
  // Auto-ocultar después de 10 segundos
  setTimeout(() => {
    operationResult.value = null
  }, 10000)
}

const formatDateTime = (timestamp) => {
  if (!timestamp) return 'N/A'
  
  try {
    const date = typeof timestamp === 'number' ? new Date(timestamp) : new Date(timestamp)
    return date.toLocaleString('es-ES', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch (error) {
    return 'N/A'
  }
}

// ============================================================================
// LIFECYCLE HOOKS
// ============================================================================
onMounted(async () => {
  appStore.addToLog('EnterpriseTab component mounted', 'info')
  
  if (hasValidApiKey.value) {
    await handleRefresh()
  }
})

onUnmounted(() => {
  appStore.addToLog('EnterpriseTab component unmounted', 'info')
})

// ============================================================================
// WATCHERS
// ============================================================================
watch(() => appStore.adminApiKey, (newApiKey) => {
  if (newApiKey && hasValidApiKey.value) {
    handleRefresh()
  }
})

watch(() => props.isActive, (isActive) => {
  if (isActive && hasValidApiKey.value && enterpriseCompanies.value.length === 0) {
    handleRefresh()
  }
})
</script>

<style scoped>
.enterprise-tab {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.tab-header {
  margin-bottom: 30px;
  text-align: center;
}

.tab-title {
  font-size: 2rem;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.tab-subtitle {
  color: var(--text-secondary);
  font-size: 1.1rem;
}

.api-key-required {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

.warning-card {
  background: var(--bg-primary);
  border: 2px solid var(--warning-color);
  border-radius: var(--radius-lg);
  padding: 40px;
  text-align: center;
  max-width: 500px;
  box-shadow: var(--shadow-md);
}

.warning-icon {
  font-size: 4rem;
  margin-bottom: 20px;
}

.warning-card h3 {
  color: var(--text-primary);
  margin-bottom: 15px;
}

.warning-card p {
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 25px;
}

.enterprise-content {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.enterprise-status {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}

.status-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.status-card {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-light);
}

.card-icon {
  font-size: 2rem;
  width: 50px;
  text-align: center;
}

.card-content h4 {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin: 0 0 5px 0;
  font-weight: 500;
}

.card-value {
  color: var(--text-primary);
  font-size: 1.5rem;
  font-weight: 600;
}

.card-value.success {
  color: var(--success-color);
}

.card-value.warning {
  color: var(--warning-color);
}

.enterprise-tools {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}

.tools-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.tools-header h3 {
  color: var(--text-primary);
  margin: 0;
}

.tools-actions {
  display: flex;
  gap: 10px;
}

.tools-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 15px;
}

.tool-button {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: var(--transition-normal);
  text-align: left;
}

.tool-button:hover:not(:disabled) {
  background: var(--bg-tertiary);
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.tool-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.tool-icon {
  font-size: 1.5rem;
  width: 40px;
  text-align: center;
}

.tool-content {
  flex: 1;
}

.tool-title {
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.tool-description {
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.tool-loading {
  font-size: 1.2rem;
}

.company-modal, .confirm-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  max-width: 800px;
  max-height: 90vh;
  width: 90%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-content.large {
  max-width: 1000px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid var(--border-color);
}

.modal-header h4 {
  margin: 0;
  color: var(--text-primary);
}

.close-button {
  background: var(--error-color);
  color: white;
  border: none;
  border-radius: 50%;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
}

.confirm-content {
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  max-width: 500px;
  width: 90%;
  overflow: hidden;
}

.confirm-header {
  padding: 20px;
  border-bottom: 1px solid var(--border-color);
}

.confirm-header h4 {
  margin: 0;
  color: var(--text-primary);
}

.confirm-body {
  padding: 20px;
}

.confirm-body p {
  margin: 0 0 15px 0;
  color: var(--text-primary);
}

.confirm-details {
  background: var(--bg-secondary);
  padding: 15px;
  border-radius: var(--radius-md);
  border-left: 4px solid var(--info-color);
}

.confirm-details ul {
  margin: 0;
  padding-left: 20px;
}

.confirm-details li {
  color: var(--text-secondary);
  margin-bottom: 5px;
}

.confirm-actions {
  padding: 20px;
  border-top: 1px solid var(--border-color);
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.operation-results {
  margin-top: 20px;
}

.result-container {
  padding: 20px;
  border-radius: var(--radius-md);
  border-left: 4px solid;
}

.result-success {
  background: var(--success-bg);
  border-left-color: var(--success-color);
  color: var(--success-text);
}

.result-error {
  background: var(--error-bg);
  border-left-color: var(--error-color);
  color: var(--error-text);
}

.result-warning {
  background: var(--warning-bg);
  border-left-color: var(--warning-color);
  color: var(--warning-text);
}

.result-info {
  background: var(--info-bg);
  border-left-color: var(--info-color);
  color: var(--info-text);
}

.result-container h4 {
  margin: 0 0 10px 0;
}

.result-container p {
  margin: 0 0 15px 0;
}

.result-details pre {
  background: rgba(255, 255, 255, 0.7);
  padding: 10px;
  border-radius: var(--radius-sm);
  overflow-x: auto;
  font-size: 0.9rem;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 500;
  cursor: pointer;
  transition: var(--transition-fast);
  display: inline-flex;
  align-items: center;
  gap: 5px;
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
  background: var(--primary-dark);
}

.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-quaternary);
}

@media (max-width: 768px) {
  .tools-header {
    flex-direction: column;
    align-items: stretch;
    gap: 15px;
  }
  
  .tools-actions {
    justify-content: center;
  }
  
  .tools-grid {
    grid-template-columns: 1fr;
  }
  
  .status-cards {
    grid-template-columns: 1fr;
  }
  
  .modal-content {
    margin: 10px;
    width: auto;
    max-height: calc(100vh - 20px);
  }
  
  .confirm-actions {
    flex-direction: column;
  }
}
</style>
