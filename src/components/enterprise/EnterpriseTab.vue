<template>
  <div class="enterprise-tab">
    <!-- Header del tab -->
    <div class="tab-header">
      <h2 class="tab-title">🏢 Gestión Enterprise</h2>
      <p class="tab-subtitle">
        Administración avanzada de empresas multi-tenant - PostgreSQL
      </p>
    </div>

    <!-- ✅ API Key Check - MISMO COMPORTAMIENTO QUE script.js -->
    <div v-if="!hasValidApiKey" class="api-key-required">
      <div class="warning-card">
        <div class="warning-icon">🔑</div>
        <h3>API Key Administrativa Requerida</h3>
        <p>
          Las funciones enterprise requieren una API key administrativa válida para acceder a las 
          operaciones de PostgreSQL y gestión avanzada.
        </p>
        <button @click="showApiKeyModal" class="btn btn-primary">
          🔑 Configurar API Key
        </button>
      </div>
    </div>

    <!-- ✅ CONTENIDO PRINCIPAL (cuando hay API key válida) -->
    <div v-else class="enterprise-content">
      
      <!-- ✅ PANEL DE ESTADO - Información como script.js -->
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
              <h4>Última Actualización</h4>
              <div class="card-value">{{ formatDateTime(lastUpdateTime) }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- ✅ HERRAMIENTAS ENTERPRISE - EXACTAS como script.js -->
      <div class="enterprise-tools">
        <div class="tools-header">
          <h3>🛠️ Herramientas Enterprise</h3>
          <div class="tools-actions">
            <button @click="refreshCompanies" class="btn btn-secondary" :disabled="isLoading">
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
            @click="handleMigrateCompanies"
            class="tool-button"
            :disabled="isMigrating"
          >
            <div class="tool-icon">🔄</div>
            <div class="tool-content">
              <div class="tool-title">Migrar desde JSON</div>
              <div class="tool-description">Migrar empresas del archivo JSON a PostgreSQL</div>
            </div>
            <div v-if="isMigrating" class="tool-loading">⏳</div>
          </button>
          
          <button @click="exportCompaniesData" class="tool-button">
            <div class="tool-icon">📤</div>
            <div class="tool-content">
              <div class="tool-title">Exportar Datos</div>
              <div class="tool-description">Exportar configuraciones en JSON/CSV</div>
            </div>
          </button>
          
          <button @click="runHealthCheckAll" class="tool-button" :disabled="isRunningHealthCheck">
            <div class="tool-icon">🏥</div>
            <div class="tool-content">
              <div class="tool-title">Health Check Global</div>
              <div class="tool-description">Verificar estado de todas las empresas</div>
            </div>
            <div v-if="isRunningHealthCheck" class="tool-loading">⏳</div>
          </button>
          
          <button @click="testApiKeyConnection" class="tool-button">
            <div class="tool-icon">🔧</div>
            <div class="tool-content">
              <div class="tool-title">Test API Key</div>
              <div class="tool-description">Verificar conexión administrativa</div>
            </div>
          </button>
        </div>
      </div>

      <!-- ✅ FORMULARIO DE CREACIÓN - Solo usar el componente -->
      <div v-if="showCreateForm" class="create-section">
        <EnterpriseCompanyForm
          :is-edit-mode="false"
          :is-saving="isCreating"
          @submit="handleCreateCompany"
          @cancel="hideCreateForm"
        />
      </div>

      <!-- ✅ LISTA DE EMPRESAS - Usar componente sin duplicar lógica -->
      <div class="companies-section">
        <EnterpriseCompanyList
          :companies="enterpriseCompanies"
          :is-loading="isLoading"
          :last-sync="lastUpdateTime"
          @refresh="refreshCompanies"
          @create="showCreateModal"
          @view="handleViewCompany"
          @edit="handleEditCompany"
          @test="handleTestCompany"
          @toggle-status="handleToggleStatus"
          @migrate="handleMigrateCompanies"
        />
      </div>
    </div>

    <!-- ✅ MODAL DE VISTA DETALLADA -->
    <div v-if="selectedCompany && showViewModal" class="company-modal" @click="closeViewModal">
      <div class="modal-content large" @click.stop>
        <EnterpriseCompanyDetail
          :company="selectedCompany"
          :is-loading="false"
          :last-sync="lastUpdateTime"
          @edit="handleEditFromDetail"
          @test="handleTestFromDetail"
          @close="closeViewModal"
          @refresh="refreshSelectedCompany"
        />
      </div>
    </div>

    <!-- ✅ MODAL DE EDICIÓN -->
    <div v-if="selectedCompany && showEditModal" class="company-modal" @click="closeEditModal">
      <div class="modal-content large" @click.stop>
        <EnterpriseCompanyForm
          :is-edit-mode="true"
          :initial-data="selectedCompany"
          :is-saving="isUpdating"
          @submit="handleUpdateCompany"
          @cancel="closeEditModal"
        />
      </div>
    </div>

    <!-- ✅ CONTENEDORES DE COMPATIBILIDAD (para funciones de script.js) -->
    <div id="enterpriseResults" class="results-container"></div>
    <div id="enterpriseCompaniesTable" class="compatibility-container"></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useAppStore } from '@/stores/app'
import { useEnterprise } from '@/composables/useEnterprise'
import { useNotifications } from '@/composables/useNotifications'
import EnterpriseCompanyForm from './EnterpriseCompanyForm.vue'
import EnterpriseCompanyList from './EnterpriseCompanyList.vue'
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

// ✅ USAR COMPOSABLE - NO DUPLICAR LÓGICA
const {
  // Estado reactivo del composable
  enterpriseCompanies,
  selectedCompany,
  isLoading,
  isCreating,
  isUpdating,
  isTesting,
  isMigrating,
  lastUpdateTime,

  // Computed del composable
  companiesCount,
  hasCompanies,
  activeCompanies,
  isAnyProcessing,

  // Funciones principales del composable
  loadEnterpriseCompanies,
  createEnterpriseCompany,
  viewEnterpriseCompany,
  saveEnterpriseCompany,
  testEnterpriseCompany,
  migrateCompaniesToPostgreSQL,

  // Funciones auxiliares del composable
  getCompanyById,
  exportCompanies,
  clearCompanyForm
} = useEnterprise()

// ============================================================================
// ESTADO LOCAL (Solo UI, no lógica de negocio)
// ============================================================================
const showCreateForm = ref(false)
const showViewModal = ref(false)
const showEditModal = ref(false)
const isRunningHealthCheck = ref(false)

// ============================================================================
// COMPUTED PROPERTIES LOCALES
// ============================================================================
const hasValidApiKey = computed(() => !!appStore.adminApiKey)

const activeCompaniesCount = computed(() => {
  return enterpriseCompanies.value.filter(company => 
    company.is_active !== false && company.status !== 'inactive'
  ).length
})

const companiesWithIssues = computed(() => {
  return enterpriseCompanies.value.filter(company => 
    company.status === 'error' || company.status === 'warning' || !company.is_active
  ).length
})

// ============================================================================
// FUNCIONES DE UI (NO DUPLICAR LÓGICA DE NEGOCIO)
// ============================================================================

/**
 * ✅ MOSTRAR/OCULTAR MODALES
 */
const showCreateModal = () => {
  clearCompanyForm()
  showCreateForm.value = true
}

const hideCreateForm = () => {
  showCreateForm.value = false
}

const closeViewModal = () => {
  showViewModal.value = false
  selectedCompany.value = null
}

const closeEditModal = () => {
  showEditModal.value = false
  selectedCompany.value = null
}

/**
 * ✅ REFRESCAR EMPRESAS - Delegar al composable
 */
const refreshCompanies = async () => {
  try {
    await loadEnterpriseCompanies()
  } catch (error) {
    // Error ya manejado en el composable
  }
}

/**
 * ✅ CREAR EMPRESA - Delegar al composable
 */
const handleCreateCompany = async (companyData) => {
  try {
    const result = await createEnterpriseCompany(companyData)
    
    if (result) {
      hideCreateForm()
      
      // ✅ MOSTRAR RESULTADO COMO script.js en contenedor de compatibilidad
      const resultsContainer = document.getElementById('enterpriseResults')
      if (resultsContainer && result.data) {
        const data = result.data
        resultsContainer.innerHTML = `
          <div class="result-container result-success">
            <h4>✅ Empresa Enterprise Creada</h4>
            <p><strong>ID:</strong> ${data.company_id}</p>
            <p><strong>Nombre:</strong> ${data.company_name}</p>
            <p><strong>Arquitectura:</strong> ${data.architecture || 'enterprise_postgresql'}</p>
            
            ${data.setup_status ? `
              <h5>Estado de Configuración:</h5>
              <div class="setup-status">
                ${Object.entries(data.setup_status).map(([key, value]) => `
                  <div class="status-item">
                    <span class="status-indicator ${typeof value === 'boolean' ? (value ? 'success' : 'error') : 'info'}"></span>
                    ${key}: ${typeof value === 'boolean' ? (value ? '✅' : '❌') : value}
                  </div>
                `).join('')}
              </div>
            ` : ''}
            
            ${data.next_steps ? `
              <h5>Próximos Pasos:</h5>
              <ol style="margin-left: 20px;">
                ${data.next_steps.map(step => `<li>${step}</li>`).join('')}
              </ol>
            ` : ''}
          </div>
        `
      }
    }
  } catch (error) {
    // Error ya manejado en el composable
  }
}

/**
 * ✅ VER EMPRESA - Delegar al composable y mostrar modal
 */
const handleViewCompany = async (companyId) => {
  try {
    await viewEnterpriseCompany(companyId)
    if (selectedCompany.value) {
      showViewModal.value = true
    }
  } catch (error) {
    // Error ya manejado en el composable
  }
}

/**
 * ✅ EDITAR EMPRESA - Delegar al composable y mostrar modal
 */
const handleEditCompany = async (companyId) => {
  try {
    await viewEnterpriseCompany(companyId)
    if (selectedCompany.value) {
      showEditModal.value = true
    }
  } catch (error) {
    // Error ya manejado en el composable
  }
}

/**
 * ✅ ACTUALIZAR EMPRESA - Delegar al composable
 */
const handleUpdateCompany = async (companyData) => {
  if (!selectedCompany.value) return
  
  try {
    const result = await saveEnterpriseCompany(selectedCompany.value.company_id, companyData)
    
    if (result) {
      closeEditModal()
      await refreshCompanies()
    }
  } catch (error) {
    // Error ya manejado en el composable
  }
}

/**
 * ✅ PROBAR EMPRESA - Delegar al composable
 */
const handleTestCompany = async (companyId) => {
  try {
    const testMessage = prompt('Mensaje de prueba:', '¿Cuáles son sus servicios disponibles?')
    if (!testMessage) return
    
    const result = await testEnterpriseCompany(companyId, testMessage)
    
    if (result) {
      // ✅ MOSTRAR RESULTADO COMO script.js
      const resultsContainer = document.getElementById('enterpriseResults')
      if (resultsContainer) {
        resultsContainer.innerHTML = `
          <div class="result-container result-success">
            <h4>🧪 Test Empresa: ${companyId}</h4>
            <div class="test-section">
              <h5>📤 Mensaje enviado:</h5>
              <div class="message-box user">${testMessage}</div>
            </div>
            <div class="test-section">
              <h5>🤖 Respuesta del bot:</h5>
              <div class="message-box bot">${result.bot_response || result.response || 'Sin respuesta'}</div>
            </div>
            <div class="test-section">
              <h5>ℹ️ Información técnica:</h5>
              <div class="tech-info">
                <p><strong>Agente usado:</strong> ${result.agent_used || 'Desconocido'}</p>
                <p><strong>Empresa:</strong> ${result.company_id || companyId}</p>
                ${result.processing_time ? `<p><strong>Tiempo:</strong> ${result.processing_time}ms</p>` : ''}
              </div>
            </div>
          </div>
        `
      }
    }
  } catch (error) {
    // Error ya manejado en el composable
  }
}

/**
 * ✅ FUNCIONES DESDE DETAIL MODAL
 */
const handleEditFromDetail = (companyId) => {
  closeViewModal()
  nextTick(() => {
    handleEditCompany(companyId)
  })
}

const handleTestFromDetail = (companyId) => {
  handleTestCompany(companyId)
}

const refreshSelectedCompany = async () => {
  if (selectedCompany.value) {
    await viewEnterpriseCompany(selectedCompany.value.company_id)
  }
}

/**
 * ✅ TOGGLE STATUS EMPRESA
 */
const handleToggleStatus = async (companyId, newStatus) => {
  try {
    const company = getCompanyById(companyId)
    if (!company) return
    
    const updatedData = { ...company, is_active: newStatus }
    await saveEnterpriseCompany(companyId, updatedData)
    await refreshCompanies()
    
    showNotification(`Empresa ${newStatus ? 'activada' : 'desactivada'} exitosamente`, 'success')
  } catch (error) {
    showNotification(`Error al cambiar estado: ${error.message}`, 'error')
  }
}

/**
 * ✅ MIGRAR EMPRESAS - Delegar al composable
 */
const handleMigrateCompanies = async () => {
  try {
    await migrateCompaniesToPostgreSQL()
  } catch (error) {
    // Error ya manejado en el composable
  }
}

/**
 * ✅ EXPORTAR DATOS - Delegar al composable
 */
const exportCompaniesData = () => {
  exportCompanies('json')
}

/**
 * ✅ HEALTH CHECK GLOBAL
 */
const runHealthCheckAll = async () => {
  if (enterpriseCompanies.value.length === 0) {
    showNotification('No hay empresas para verificar', 'warning')
    return
  }
  
  isRunningHealthCheck.value = true
  
  try {
    showNotification('Ejecutando health check en todas las empresas...', 'info')
    
    let successCount = 0
    let errorCount = 0
    
    for (const company of enterpriseCompanies.value) {
      try {
        await testEnterpriseCompany(company.company_id, '¿Están funcionando correctamente?')
        successCount++
      } catch (error) {
        errorCount++
      }
    }
    
    showNotification(
      `Health check completado: ${successCount} exitosos, ${errorCount} con errores`, 
      errorCount === 0 ? 'success' : 'warning'
    )
    
  } catch (error) {
    showNotification(`Error en health check: ${error.message}`, 'error')
  } finally {
    isRunningHealthCheck.value = false
  }
}

/**
 * ✅ TEST API KEY CONNECTION
 */
const testApiKeyConnection = async () => {
  try {
    await loadEnterpriseCompanies()
    showNotification('✅ Conexión API key válida', 'success')
  } catch (error) {
    showNotification(`❌ Error de conexión: ${error.message}`, 'error')
  }
}

/**
 * ✅ MOSTRAR MODAL API KEY
 */
const showApiKeyModal = () => {
  // Emitir evento global para el modal de API key
  window.dispatchEvent(new CustomEvent('show-api-key-modal'))
}

// ============================================================================
// FUNCIONES DE FORMATO
// ============================================================================
const formatDateTime = (dateTime) => {
  if (!dateTime) return 'N/A'
  
  try {
    const date = typeof dateTime === 'number' ? new Date(dateTime) : new Date(dateTime)
    return date.toLocaleString()
  } catch (error) {
    return 'Fecha inválida'
  }
}

// ============================================================================
// LIFECYCLE HOOKS
// ============================================================================
onMounted(async () => {
  appStore.addToLog('EnterpriseTab component mounted', 'info')
  
  if (hasValidApiKey.value) {
    await loadEnterpriseCompanies()
  }
  
  // ✅ EXPONER FUNCIONES GLOBALES PARA COMPATIBILIDAD CON script.js
  window.loadEnterpriseCompanies = loadEnterpriseCompanies
  window.createEnterpriseCompany = createEnterpriseCompany
  window.viewEnterpriseCompany = handleViewCompany
  window.editEnterpriseCompany = handleEditCompany
  window.saveEnterpriseCompany = saveEnterpriseCompany
  window.testEnterpriseCompany = handleTestCompany
  window.migrateCompaniesToPostgreSQL = handleMigrateCompanies
})

onUnmounted(() => {
  // Limpiar funciones globales
  if (typeof window !== 'undefined') {
    delete window.loadEnterpriseCompanies
    delete window.createEnterpriseCompany
    delete window.viewEnterpriseCompany
    delete window.editEnterpriseCompany
    delete window.saveEnterpriseCompany
    delete window.testEnterpriseCompany
    delete window.migrateCompaniesToPostgreSQL
  }
  
  appStore.addToLog('EnterpriseTab component unmounted', 'info')
})

// ============================================================================
// WATCHERS
// ============================================================================
watch(() => appStore.adminApiKey, (newApiKey) => {
  if (newApiKey && hasValidApiKey.value) {
    loadEnterpriseCompanies()
  }
})
</script>

<style scoped>
/* ✅ MANTENER TODOS LOS ESTILOS ORIGINALES */
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

.create-section {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.companies-section {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.company-modal {
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
  overflow-y: auto;
  box-shadow: var(--shadow-lg);
}

.modal-content.large {
  max-width: 1000px;
}

.results-container {
  margin-top: 20px;
}

.compatibility-container {
  display: none;
}

/* Estilos para resultados compatibles con script.js */
.result-container {
  padding: 20px;
  border-radius: 8px;
  margin: 10px 0;
}

.result-success {
  background: #d4edda;
  border: 1px solid #c3e6cb;
  color: #155724;
}

.result-error {
  background: #f8d7da;
  border: 1px solid #f5c6cb;
  color: #721c24;
}

.setup-status {
  margin: 15px 0;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 5px 0;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-indicator.success {
  background: #28a745;
}

.status-indicator.error {
  background: #dc3545;
}

.status-indicator.info {
  background: #17a2b8;
}

.message-box {
  background: #f8f9fa;
  padding: 10px;
  border-radius: 5px;
  margin: 10px 0;
  border-left: 4px solid;
}

.message-box.user {
  border-left-color: #007bff;
}

.message-box.bot {
  border-left-color: #28a745;
}

.tech-info {
  background: #f8f9fa;
  padding: 10px;
  border-radius: 5px;
  font-size: 0.9em;
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

.btn-primary {
  background: var(--primary-color);
  color: white;
}

.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .tools-header {
    flex-direction: column;
    gap: 15px;
  }
  
  .tools-actions {
    width: 100%;
    justify-content: stretch;
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
}
</style>
