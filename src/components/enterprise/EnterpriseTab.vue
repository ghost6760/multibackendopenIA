<template>
  <div class="enterprise-tab">
    <!-- Header del tab -->
    <div class="tab-header">
      <h2 class="tab-title">🏢 Gestión Enterprise</h2>
      <p class="tab-subtitle">
        Administración avanzada de empresas y configuraciones multi-tenant
      </p>
    </div>

    <!-- 🔧 FIX: Verificación de API Key mejorada -->
    <div v-if="!canPerformEnterpriseOperations" class="api-key-required">
      <div class="warning-card">
        <div class="warning-icon">🔑</div>
        <h3>{{ hasValidApiKey ? 'API Key Inválida' : 'API Key Requerida' }}</h3>
        <p v-if="!hasValidApiKey">
          Las funciones enterprise requieren una API key válida para acceder a las 
          operaciones administrativas avanzadas.
        </p>
        <p v-else>
          La API key configurada no es válida o ha expirado. Por favor configura una nueva.
        </p>
        <div class="warning-actions">
          <button @click="requestApiKey" class="btn btn-primary">
            🔑 {{ hasValidApiKey ? 'Reconfigurar' : 'Configurar' }} API Key
          </button>
          <button v-if="hasValidApiKey" @click="testCurrentApiKey" class="btn btn-secondary">
            🧪 Probar API Key
          </button>
        </div>
      </div>
    </div>

    <!-- 🔧 FIX: Contenido principal con mejor manejo de estado -->
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
            <div class="card-icon">🔑</div>
            <div class="card-content">
              <h4>API Key</h4>
              <div class="card-value success">Válida</div>
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
            <button @click="handleLoadCompanies" class="btn btn-secondary" :disabled="isLoading">
              <span v-if="isLoading">⏳ Cargando...</span>
              <span v-else>🔄 Actualizar</span>
            </button>
            <button @click="showCreateCompanyModal" class="btn btn-primary">
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
              <div class="tool-title">Migrar a PostgreSQL</div>
              <div class="tool-description">Migrar todas las empresas al sistema PostgreSQL</div>
            </div>
            <div v-if="isMigrating" class="tool-loading">⏳</div>
          </button>
          
          <button @click="handleTestAllCompanies" class="tool-button" :disabled="isTesting">
            <div class="tool-icon">🧪</div>
            <div class="tool-content">
              <div class="tool-title">Test Global</div>
              <div class="tool-description">Probar conexión de todas las empresas</div>
            </div>
            <div v-if="isTesting" class="tool-loading">⏳</div>
          </button>
          
          <button @click="exportCompaniesData" class="tool-button">
            <div class="tool-icon">📤</div>
            <div class="tool-content">
              <div class="tool-title">Exportar Datos</div>
              <div class="tool-description">Exportar configuraciones de todas las empresas</div>
            </div>
          </button>
          
          <button @click="resetEnterpriseState" class="tool-button">
            <div class="tool-icon">🔄</div>
            <div class="tool-content">
              <div class="tool-title">Resetear Estado</div>
              <div class="tool-description">Limpiar cache y recargar datos</div>
            </div>
          </button>
        </div>
      </div>

      <!-- Lista de empresas usando componente -->
      <EnterpriseCompanyList
        :companies="enterpriseCompanies"
        :is-loading="isLoading"
        :error="loadingError"
        :last-sync="lastUpdateTime"
        @refresh="handleLoadCompanies"
        @create="showCreateCompanyModal"
        @view="handleViewCompany"
        @edit="handleEditCompany"
        @test="handleTestCompany"
        @toggle-status="handleToggleCompanyStatus"
        @migrate="handleMigrateCompanies"
      />
    </div>

    <!-- Modal de creación/edición -->
    <EnterpriseCompanyForm
      v-if="showCompanyModal"
      :is-edit-mode="isEditMode"
      :initial-data="editingCompany"
      :is-saving="isCreating || isUpdating"
      @submit="handleSaveCompany"
      @cancel="closeCompanyModal"
    />

    <!-- Modal de detalles -->
    <EnterpriseCompanyDetail
      v-if="viewingCompany"
      :company="viewingCompany"
      :is-loading="false"
      :error="null"
      :last-sync="lastUpdateTime"
      @edit="handleEditCompany"
      @close="closeViewModal"
      @test="handleTestCompany"
      @toggle-status="handleToggleCompanyStatus"
      @refresh="handleLoadCompanies"
    />

    <!-- Resultado de operaciones -->
    <div v-if="operationResult" class="operation-result">
      <div class="result-container" :class="`result-${operationResult.type}`">
        <h4>{{ operationResult.title }}</h4>
        <p>{{ operationResult.message }}</p>
        <div v-if="operationResult.details" class="result-details">
          <pre>{{ JSON.stringify(operationResult.details, null, 2) }}</pre>
        </div>
        <button @click="operationResult = null" class="btn btn-secondary">
          ❌ Cerrar
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useEnterprise } from '@/composables/useEnterprise'
import { useAuthStore } from '@/stores/auth'
import { useNotifications } from '@/composables/useNotifications'
import EnterpriseCompanyList from './EnterpriseCompanyList.vue'
import EnterpriseCompanyForm from './EnterpriseCompanyForm.vue'
import EnterpriseCompanyDetail from './EnterpriseCompanyDetail.vue'

// ============================================================================
// COMPOSABLES Y STORES
// ============================================================================

// 🔧 FIX: Usar el composable corregido
const {
  enterpriseCompanies,
  selectedCompany,
  isLoading,
  isCreating,
  isUpdating,
  isTesting,
  isMigrating,
  testResults,
  lastUpdateTime,
  companiesCount,
  hasCompanies,
  hasValidApiKey,
  canPerformEnterpriseOperations,
  loadEnterpriseCompanies,
  createEnterpriseCompany,
  viewEnterpriseCompany,
  updateEnterpriseCompany,
  testEnterpriseCompany,
  migrateCompaniesToPostgreSQL,
  ensureApiKey,
  resetEnterpriseState
} = useEnterprise()

const authStore = useAuthStore()
const { showNotification } = useNotifications()

// ============================================================================
// ESTADO LOCAL DEL COMPONENTE
// ============================================================================

const showCompanyModal = ref(false)
const viewingCompany = ref(null)
const editingCompany = ref(null)
const isEditMode = ref(false)
const loadingError = ref(null)
const operationResult = ref(null)

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================

const activeCompaniesCount = computed(() => {
  return enterpriseCompanies.value.filter(c => c.is_active !== false).length
})

// ============================================================================
// FUNCIONES DE MANEJO DE EVENTOS
// ============================================================================

/**
 * 🔧 FIX: Función de carga con mejor manejo de errores
 */
const handleLoadCompanies = async () => {
  try {
    loadingError.value = null
    console.log('🏢 [EnterpriseTab] Loading companies...') // DEBUG
    
    if (!(await ensureApiKey())) {
      return
    }
    
    await loadEnterpriseCompanies()
    console.log('✅ [EnterpriseTab] Companies loaded successfully') // DEBUG
    
  } catch (error) {
    console.error('❌ [EnterpriseTab] Error loading companies:', error) // DEBUG
    loadingError.value = error.message
    
    // Si es error de API key, limpiar y solicitar nueva
    if (error.message.includes('401') || error.message.includes('API key')) {
      authStore.clearApiKey()
      requestApiKey()
    }
  }
}

/**
 * 🔧 FIX: Manejo de creación con validación previa
 */
const handleSaveCompany = async (companyData) => {
  try {
    if (!(await ensureApiKey())) {
      return
    }

    let result
    if (isEditMode.value && editingCompany.value) {
      result = await updateEnterpriseCompany(editingCompany.value.company_id, companyData)
    } else {
      result = await createEnterpriseCompany(companyData)
    }

    if (result) {
      showOperationResult('success', 
        isEditMode.value ? 'Empresa Actualizada' : 'Empresa Creada',
        isEditMode.value ? 'La empresa ha sido actualizada exitosamente' : 'La empresa ha sido creada exitosamente',
        result
      )
      closeCompanyModal()
    }

  } catch (error) {
    showOperationResult('error', 'Error en Operación', error.message)
  }
}

/**
 * 🔧 FIX: Ver empresa con mejor manejo
 */
const handleViewCompany = async (companyId) => {
  try {
    if (!(await ensureApiKey())) {
      return
    }

    const company = await viewEnterpriseCompany(companyId)
    if (company) {
      viewingCompany.value = company
    }

  } catch (error) {
    showNotification('Error viendo empresa: ' + error.message, 'error')
  }
}

/**
 * 🔧 FIX: Editar empresa con carga de datos
 */
const handleEditCompany = async (companyId) => {
  try {
    if (!(await ensureApiKey())) {
      return
    }

    // Buscar empresa en la lista local primero
    let company = enterpriseCompanies.value.find(c => c.company_id === companyId)
    
    // Si no está en local, cargar desde servidor
    if (!company) {
      company = await viewEnterpriseCompany(companyId)
    }

    if (company) {
      editingCompany.value = company
      isEditMode.value = true
      showCompanyModal.value = true
    }

  } catch (error) {
    showNotification('Error cargando empresa para edición: ' + error.message, 'error')
  }
}

/**
 * 🔧 FIX: Test de empresa individual
 */
const handleTestCompany = async (companyId) => {
  try {
    if (!(await ensureApiKey())) {
      return
    }

    const result = await testEnterpriseCompany(companyId)
    if (result) {
      showOperationResult('success', 'Test Completado', 
        `Test de empresa ${companyId} completado exitosamente`, result)
    }

  } catch (error) {
    showOperationResult('error', 'Error en Test', error.message)
  }
}

/**
 * 🔧 NUEVA: Test de todas las empresas
 */
const handleTestAllCompanies = async () => {
  if (!hasCompanies.value) {
    showNotification('No hay empresas para probar', 'warning')
    return
  }

  if (!(await ensureApiKey())) {
    return
  }

  showNotification('Iniciando test de todas las empresas...', 'info')
  
  const results = []
  for (const company of enterpriseCompanies.value) {
    try {
      const result = await testEnterpriseCompany(company.company_id)
      results.push({ company: company.company_id, success: true, result })
    } catch (error) {
      results.push({ company: company.company_id, success: false, error: error.message })
    }
  }

  const successCount = results.filter(r => r.success).length
  showOperationResult('info', 'Test Global Completado',
    `${successCount}/${results.length} empresas pasaron el test`, results)
}

/**
 * 🔧 FIX: Migración con confirmación
 */
const handleMigrateCompanies = async () => {
  try {
    if (!(await ensureApiKey())) {
      return
    }

    const result = await migrateCompaniesToPostgreSQL()
    if (result) {
      showOperationResult('success', 'Migración Completada',
        'Las empresas han sido migradas exitosamente a PostgreSQL')
    }

  } catch (error) {
    showOperationResult('error', 'Error en Migración', error.message)
  }
}

/**
 * 🔧 NUEVA: Toggle status de empresa
 */
const handleToggleCompanyStatus = async (companyId, newStatus) => {
  try {
    if (!(await ensureApiKey())) {
      return
    }

    // Buscar empresa y actualizar su estado
    const company = enterpriseCompanies.value.find(c => c.company_id === companyId)
    if (company) {
      const updatedData = { ...company, is_active: newStatus }
      await updateEnterpriseCompany(companyId, updatedData)
      showNotification(`Empresa ${newStatus ? 'activada' : 'desactivada'} exitosamente`, 'success')
    }

  } catch (error) {
    showNotification('Error actualizando estado: ' + error.message, 'error')
  }
}

/**
 * 🔧 NUEVA: Solicitar API key
 */
const requestApiKey = () => {
  authStore.showApiKeyModal()
}

/**
 * 🔧 NUEVA: Probar API key actual
 */
const testCurrentApiKey = async () => {
  try {
    const isValid = await authStore.testApiKey()
    if (isValid) {
      showNotification('API Key válida', 'success')
      await handleLoadCompanies()
    }
  } catch (error) {
    showNotification('Error probando API Key: ' + error.message, 'error')
  }
}

/**
 * 🔧 NUEVA: Exportar datos de empresas
 */
const exportCompaniesData = () => {
  try {
    const dataToExport = {
      export_timestamp: new Date().toISOString(),
      total_companies: enterpriseCompanies.value.length,
      companies: enterpriseCompanies.value,
      test_results: testResults.value
    }

    const dataStr = JSON.stringify(dataToExport, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    
    const a = document.createElement('a')
    a.href = URL.createObjectURL(dataBlob)
    a.download = `enterprise_companies_${new Date().toISOString().slice(0, 10)}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    
    URL.revokeObjectURL(a.href)
    showNotification('Datos exportados exitosamente', 'success')
    
  } catch (error) {
    showNotification('Error exportando datos: ' + error.message, 'error')
  }
}

/**
 * Mostrar modal de creación
 */
const showCreateCompanyModal = () => {
  editingCompany.value = null
  isEditMode.value = false
  showCompanyModal.value = true
}

/**
 * Cerrar modal de empresa
 */
const closeCompanyModal = () => {
  showCompanyModal.value = false
  editingCompany.value = null
  isEditMode.value = false
}

/**
 * Cerrar modal de vista
 */
const closeViewModal = () => {
  viewingCompany.value = null
}

/**
 * Mostrar resultado de operación
 */
const showOperationResult = (type, title, message, details = null) => {
  operationResult.value = { type, title, message, details }
}

/**
 * Formatear fecha/hora
 */
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
  console.log('🏢 [EnterpriseTab] Component mounted') // DEBUG
  
  // 🔧 FIX: Solo cargar si tenemos API key válida
  if (hasValidApiKey.value) {
    await handleLoadCompanies()
  }
})

onUnmounted(() => {
  console.log('🏢 [EnterpriseTab] Component unmounted') // DEBUG
})

// ============================================================================
// EXPONER FUNCIONES PARA COMPATIBILIDAD (SI ES NECESARIO)
// ============================================================================

defineExpose({
  loadEnterpriseCompanies: handleLoadCompanies,
  createEnterpriseCompany,
  viewEnterpriseCompany,
  testEnterpriseCompany,
  migrateCompaniesToPostgreSQL
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

.warning-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
  flex-wrap: wrap;
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

.operation-result {
  position: fixed;
  bottom: 20px;
  right: 20px;
  max-width: 400px;
  z-index: 1000;
}

.result-container {
  padding: 20px;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
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

.result-info {
  background: var(--info-bg);
  border-left-color: var(--info-color);
  color: var(--info-text);
}

.result-container h4 {
  margin: 0 0 10px 0;
  font-size: 1.1rem;
}

.result-container p {
  margin: 0 0 15px 0;
}

.result-details {
  margin: 15px 0;
  padding: 10px;
  background: rgba(0, 0, 0, 0.1);
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
  max-height: 200px;
  overflow-y: auto;
}

.result-details pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
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
  .warning-actions {
    flex-direction: column;
  }
  
  .tools-header {
    flex-direction: column;
    align-items: stretch;
    gap: 15px;
  }
  
  .tools-actions {
    justify-content: stretch;
  }
  
  .tools-grid {
    grid-template-columns: 1fr;
  }
  
  .status-cards {
    grid-template-columns: 1fr;
  }
  
  .operation-result {
    bottom: 10px;
    right: 10px;
    left: 10px;
    max-width: none;
  }
}
</style>
