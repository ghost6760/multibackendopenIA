<template>
  <div class="enterprise-tab">
    <!-- Header del tab -->
    <div class="tab-header">
      <h2 class="tab-title">🏢 Gestión Enterprise</h2>
      <p class="tab-subtitle">
        Administración avanzada de empresas multi-tenant - PostgreSQL
      </p>
    </div>

    <!-- ✅ API KEY CHECK - MISMO COMPORTAMIENTO QUE script.js -->
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
      
      <!-- ✅ ESTADÍSTICAS - Información como script.js -->
      <div class="enterprise-stats">
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-icon">🏢</div>
            <div class="stat-content">
              <div class="stat-value">{{ companiesCount }}</div>
              <div class="stat-label">Total Empresas</div>
            </div>
          </div>
          
          <div class="stat-card success">
            <div class="stat-icon">✅</div>
            <div class="stat-content">
              <div class="stat-value">{{ activeCompaniesCount }}</div>
              <div class="stat-label">Activas</div>
            </div>
          </div>
          
          <div class="stat-card warning">
            <div class="stat-icon">⚠️</div>
            <div class="stat-content">
              <div class="stat-value">{{ companiesWithIssues }}</div>
              <div class="stat-label">Con Problemas</div>
            </div>
          </div>
          
          <div class="stat-card info">
            <div class="stat-icon">🔄</div>
            <div class="stat-content">
              <div class="stat-value">{{ formatDateTime(lastUpdateTime) || 'N/A' }}</div>
              <div class="stat-label">Última Sync</div>
            </div>
          </div>
        </div>
      </div>

      <!-- ✅ HERRAMIENTAS PRINCIPALES -->
      <div class="enterprise-tools">
        <div class="tools-header">
          <h3>🛠️ Herramientas Enterprise</h3>
          <div class="tools-actions">
            <button 
              @click="refreshCompanies" 
              class="btn btn-info" 
              :disabled="isAnyProcessing"
            >
              <span v-if="isLoading">⏳ Cargando...</span>
              <span v-else>🔄 Recargar</span>
            </button>
            <button @click="toggleCreateForm" class="btn btn-primary">
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
              <div class="tool-description">PostgreSQL ← archivo JSON</div>
            </div>
            <div v-if="isMigrating" class="tool-loading">⏳</div>
          </button>
          
          <button @click="exportData" class="tool-button">
            <div class="tool-icon">📤</div>
            <div class="tool-content">
              <div class="tool-title">Exportar</div>
              <div class="tool-description">Descargar JSON/CSV</div>
            </div>
          </button>
          
          <button @click="runHealthCheck" class="tool-button" :disabled="isRunningHealthCheck">
            <div class="tool-icon">🏥</div>
            <div class="tool-content">
              <div class="tool-title">Health Check</div>
              <div class="tool-description">Verificar todas</div>
            </div>
            <div v-if="isRunningHealthCheck" class="tool-loading">⏳</div>
          </button>
          
          <button @click="testApiConnection" class="tool-button">
            <div class="tool-icon">🔧</div>
            <div class="tool-content">
              <div class="tool-title">Test API Key</div>
              <div class="tool-description">Verificar conexión</div>
            </div>
          </button>
        </div>
      </div>

      <!-- ✅ FORMULARIO DE CREACIÓN (Toggleable) -->
      <div v-if="showCreateForm" class="create-section">
        <div class="section-header">
          <h3>➕ Crear Nueva Empresa Enterprise</h3>
          <button @click="hideCreateForm" class="btn btn-outline btn-sm">✖️ Cerrar</button>
        </div>
        <EnterpriseCompanyForm
          :is-edit-mode="false"
          :is-saving="isCreating"
          @submit="handleCreateCompany"
          @cancel="hideCreateForm"
        />
      </div>

      <!-- ✅ LISTA DE EMPRESAS (Siempre visible) -->
      <div class="companies-section">
        <EnterpriseCompanyList
          :companies="enterpriseCompanies"
          :is-loading="isLoading"
          :last-sync="lastUpdateTime"
          @refresh="refreshCompanies"
          @create="toggleCreateForm"
          @view="handleViewCompany"
          @edit="handleEditCompany"
          @test="handleTestCompany"
          @toggle-status="handleToggleStatus"
          @migrate="handleMigrateCompanies"
        />
      </div>
    </div>

    <!-- ✅ MODALES -->
    <!-- Modal de Vista -->
    <div v-if="selectedCompany && showViewModal" class="modal-overlay" @click="closeViewModal">
      <div class="modal-content large" @click.stop>
        <EnterpriseCompanyDetail
          :company="selectedCompany"
          :is-loading="false"
          :last-sync="lastUpdateTime"
          @edit="handleEditFromDetail"
          @test="handleTestFromDetail"
          @close="closeViewModal"
          @refresh="refreshSelectedCompany"
          @toggle-status="handleToggleStatus"
        />
      </div>
    </div>

    <!-- Modal de Edición -->
    <div v-if="selectedCompany && showEditModal" class="modal-overlay" @click="closeEditModal">
      <div class="modal-content large" @click.stop>
        <div class="modal-header">
          <h3>✏️ Editar {{ selectedCompany.company_name || selectedCompany.company_id }}</h3>
          <button @click="closeEditModal" class="modal-close">✖️</button>
        </div>
        <EnterpriseCompanyForm
          :is-edit-mode="true"
          :initial-data="selectedCompany"
          :is-saving="isUpdating"
          @submit="handleUpdateCompany"
          @cancel="closeEditModal"
        />
      </div>
    </div>

    <!-- ✅ CONTENEDOR DE RESULTADOS (compatibilidad con script.js) -->
    <div id="enterpriseResults" class="results-container"></div>
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
// STORES & COMPOSABLES - ✅ SIN DUPLICACIÓN DE LÓGICA
// ============================================================================
const appStore = useAppStore()
const { showNotification } = useNotifications()

// ✅ USAR COMPOSABLE COMPLETO - Toda la lógica de negocio viene del composable
const {
  // Estado del composable
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

  // Funciones del composable
  loadEnterpriseCompanies,
  createEnterpriseCompany,
  viewEnterpriseCompany,
  saveEnterpriseCompany,
  testEnterpriseCompany,
  migrateCompaniesToPostgreSQL,
  getCompanyById,
  exportCompanies
} = useEnterprise()

// ============================================================================
// ESTADO LOCAL (Solo para UI, no lógica de negocio)
// ============================================================================
const showCreateForm = ref(false)
const showViewModal = ref(false)
const showEditModal = ref(false)
const isRunningHealthCheck = ref(false)

// ============================================================================
// COMPUTED LOCALES (Solo para UI)
// ============================================================================
const hasValidApiKey = computed(() => !!appStore.adminApiKey)

const activeCompaniesCount = computed(() => {
  return activeCompanies.value.length
})

const companiesWithIssues = computed(() => {
  return enterpriseCompanies.value.filter(company => 
    company.status === 'error' || company.status === 'warning' || !company.is_active
  ).length
})

// ============================================================================
// MÉTODOS DE UI (Sin duplicar lógica de negocio)
// ============================================================================

/**
 * ✅ GESTIÓN DE FORMULARIOS
 */
const toggleCreateForm = () => {
  showCreateForm.value = !showCreateForm.value
}

const hideCreateForm = () => {
  showCreateForm.value = false
}

/**
 * ✅ GESTIÓN DE MODALES
 */
const closeViewModal = () => {
  showViewModal.value = false
  selectedCompany.value = null
}

const closeEditModal = () => {
  showEditModal.value = false
  selectedCompany.value = null
}

/**
 * ✅ OPERACIONES PRINCIPALES (Delegando al composable)
 */
const refreshCompanies = async () => {
  try {
    await loadEnterpriseCompanies()
  } catch (error) {
    // Error ya manejado en el composable
  }
}

const handleCreateCompany = async (companyData) => {
  try {
    const result = await createEnterpriseCompany(companyData)
    
    if (result) {
      hideCreateForm()
      showResultInContainer(result)
    }
  } catch (error) {
    // Error ya manejado en el composable
  }
}

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

const handleTestCompany = async (companyId) => {
  try {
    const testMessage = prompt('Mensaje de prueba:', '¿Cuáles son sus servicios disponibles?')
    if (!testMessage) return
    
    const result = await testEnterpriseCompany(companyId, testMessage)
    
    if (result) {
      showTestResultInContainer(companyId, testMessage, result)
    }
  } catch (error) {
    // Error ya manejado en el composable
  }
}

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

const handleMigrateCompanies = async () => {
  try {
    await migrateCompaniesToPostgreSQL()
  } catch (error) {
    // Error ya manejado en el composable
  }
}

/**
 * ✅ HERRAMIENTAS ADICIONALES
 */
const exportData = () => {
  exportCompanies('json')
}

const runHealthCheck = async () => {
  if (enterpriseCompanies.value.length === 0) {
    showNotification('No hay empresas para verificar', 'warning')
    return
  }
  
  isRunningHealthCheck.value = true
  
  try {
    showNotification('Ejecutando health check...', 'info')
    
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
      `Health check: ${successCount} exitosos, ${errorCount} con errores`, 
      errorCount === 0 ? 'success' : 'warning'
    )
    
  } catch (error) {
    showNotification(`Error en health check: ${error.message}`, 'error')
  } finally {
    isRunningHealthCheck.value = false
  }
}

const testApiConnection = async () => {
  try {
    await loadEnterpriseCompanies()
    showNotification('✅ Conexión API key válida', 'success')
  } catch (error) {
    showNotification(`❌ Error de conexión: ${error.message}`, 'error')
  }
}

/**
 * ✅ OPERACIONES DESDE MODALES
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
 * ✅ MOSTRAR RESULTADOS (compatible con script.js)
 */
const showResultInContainer = (result) => {
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
          <ol>
            ${data.next_steps.map(step => `<li>${step}</li>`).join('')}
          </ol>
        ` : ''}
      </div>
    `
  }
}

const showTestResultInContainer = (companyId, testMessage, result) => {
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

/**
 * ✅ UTILIDADES
 */
const showApiKeyModal = () => {
  window.dispatchEvent(new CustomEvent('show-api-key-modal'))
}

const formatDateTime = (dateTime) => {
  if (!dateTime) return null
  try {
    const date = typeof dateTime === 'number' ? new Date(dateTime) : new Date(dateTime)
    return date.toLocaleTimeString()
  } catch (error) {
    return null
  }
}

// ============================================================================
// LIFECYCLE
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
/* ✅ ESTILOS OPTIMIZADOS - Diseño limpio y moderno */
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
  color: #333;
  margin-bottom: 8px;
}

.tab-subtitle {
  color: #6c757d;
  font-size: 1.1rem;
}

.api-key-required {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

.warning-card {
  background: white;
  border: 2px solid #ffc107;
  border-radius: 12px;
  padding: 40px;
  text-align: center;
  max-width: 500px;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

.warning-icon {
  font-size: 4rem;
  margin-bottom: 20px;
}

.warning-card h3 {
  color: #333;
  margin-bottom: 15px;
}

.warning-card p {
  color: #6c757d;
  line-height: 1.6;
  margin-bottom: 25px;
}

.enterprise-content {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

/* Estadísticas */
.enterprise-stats {
  background: white;
  border-radius: 12px;
  padding: 25px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e9ecef;
  transition: transform 0.2s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}

.stat-card.success {
  border-left: 4px solid #28a745;
}

.stat-card.warning {
  border-left: 4px solid #ffc107;
}

.stat-card.info {
  border-left: 4px solid #17a2b8;
}

.stat-icon {
  font-size: 2rem;
  width: 60px;
  text-align: center;
}

.stat-value {
  font-size: 1.8rem;
  font-weight: 600;
  color: #333;
}

.stat-label {
  color: #6c757d;
  font-size: 0.9rem;
  margin-top: 4px;
}

/* Herramientas */
.enterprise-tools {
  background: white;
  border-radius: 12px;
  padding: 25px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.tools-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 15px;
}

.tools-header h3 {
  color: #333;
  margin: 0;
}

.tools-actions {
  display: flex;
  gap: 10px;
}

.tools-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.tool-button {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px;
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
}

.tool-button:hover:not(:disabled) {
  background: #e9ecef;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
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
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}

.tool-description {
  font-size: 0.9rem;
  color: #6c757d;
}

.tool-loading {
  font-size: 1.2rem;
}

/* Secciones */
.create-section, .companies-section {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 25px;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.section-header h3 {
  margin: 0;
  color: #333;
}

/* Modales */
.modal-overlay {
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
  background: white;
  border-radius: 12px;
  max-width: 800px;
  max-height: 90vh;
  width: 90%;
  overflow-y: auto;
  box-shadow: 0 10px 30px rgba(0,0,0,0.3);
}

.modal-content.large {
  max-width: 1000px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 25px;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.modal-header h3 {
  margin: 0;
  color: #333;
}

.modal-close {
  background: transparent;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  padding: 5px;
}

/* Resultados */
.results-container {
  margin-top: 20px;
}

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

/* Botones */
.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  text-decoration: none;
}

.btn-primary {
  background: #007bff;
  color: white;
}

.btn-info {
  background: #17a2b8;
  color: white;
}

.btn-outline {
  background: transparent;
  color: #6c757d;
  border: 1px solid #ced4da;
}

.btn-sm {
  padding: 4px 8px;
  font-size: 0.85em;
}

.btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Responsive */
@media (max-width: 768px) {
  .tools-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .tools-actions {
    width: 100%;
    justify-content: stretch;
  }
  
  .tools-grid {
    grid-template-columns: 1fr;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .modal-content {
    margin: 10px;
    width: auto;
    max-height: calc(100vh - 20px);
  }
}
</style>
