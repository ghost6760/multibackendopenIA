<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { useEnterprise } from '@/composables/useEnterprise' // ✅ AGREGAR ESTA LÍNEA
import { useNotifications } from '@/composables/useNotifications'

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

// ✅ USAR EL COMPOSABLE EN LUGAR DE REIMPLEMENTAR TODO
const {
  // Estado reactivo del composable
  enterpriseCompanies: companies,
  selectedCompany,
  isLoading,
  isCreating,
  isUpdating,
  isTesting,
  isMigrating,
  companyForm,
  testResults,
  migrationResults,
  lastUpdateTime,

  // Computed properties del composable
  companiesCount,
  hasCompanies,
  activeCompanies,
  companyOptions,
  isFormValid,
  isAnyProcessing,

  // Funciones principales del composable
  loadEnterpriseCompanies,
  createEnterpriseCompany,
  viewEnterpriseCompany,
  editEnterpriseCompany,
  saveEnterpriseCompany,
  testEnterpriseCompany,
  migrateCompaniesToPostgreSQL,

  // Funciones auxiliares del composable
  getCompanyById,
  exportCompanies,
  clearCompanyForm,
  populateCompanyForm
} = useEnterprise()

// ============================================================================
// ESTADO LOCAL ADICIONAL (Solo lo que no esté en el composable)
// ============================================================================
const showCompanyModal = ref(false)
const showViewModal = ref(false)
const viewingCompany = ref(null)
const isEditMode = ref(false)
const lastSync = ref(null)
const isRunningHealthCheck = ref(false)

// ============================================================================
// COMPUTED PROPERTIES LOCALES
// ============================================================================
const hasValidApiKey = computed(() => !!appStore.adminApiKey)

const activeCompaniesCount = computed(() => {
  return companies.value.filter(company => 
    company.status === 'active' || company.is_active
  ).length
})

const companiesWithIssues = computed(() => {
  return companies.value.filter(company => 
    company.status === 'error' || company.status === 'warning'
  ).length
})

const isValidConfiguration = computed(() => {
  if (!companyForm.value.configuration || !companyForm.value.configuration.trim()) return true
  
  try {
    JSON.parse(companyForm.value.configuration)
    return true
  } catch (error) {
    return false
  }
})

// ============================================================================
// FUNCIONES DE UI LOCALES
// ============================================================================
const showCreateCompanyModal = () => {
  clearCompanyForm()
  isEditMode.value = false
  showCompanyModal.value = true
}

const closeCompanyModal = () => {
  showCompanyModal.value = false
  clearCompanyForm()
}

const closeViewModal = () => {
  showViewModal.value = false
  viewingCompany.value = null
}

const runHealthCheckAllCompanies = async () => {
  isRunningHealthCheck.value = true
  
  try {
    showNotification('Ejecutando health check en todas las empresas...', 'info')
    
    // Simular health check
    await new Promise(resolve => setTimeout(resolve, 3000))
    
    showNotification('Health check completado', 'success')
    await loadEnterpriseCompanies()
    
  } catch (error) {
    showNotification(`Error en health check: ${error.message}`, 'error')
  } finally {
    isRunningHealthCheck.value = false
  }
}

const requestApiKey = () => {
  // Trigger del modal de API key desde el componente padre
  window.dispatchEvent(new CustomEvent('show-api-key-modal'))
}

// ============================================================================
// FUNCIONES DE FORMATEO
// ============================================================================
const getStatusClass = (status) => {
  switch (status) {
    case 'active':
    case 'online':
    case 'success':
      return 'status-success'
    case 'inactive':
    case 'offline':
      return 'status-inactive'
    case 'error':
    case 'failed':
      return 'status-error'
    case 'warning':
      return 'status-warning'
    default:
      return 'status-unknown'
  }
}

const formatDateTime = (dateTime) => {
  if (!dateTime) return 'N/A'
  
  try {
    const date = typeof dateTime === 'number' ? new Date(dateTime) : new Date(dateTime)
    return date.toLocaleString()
  } catch (error) {
    return 'Fecha inválida'
  }
}

const formatJSON = (obj) => {
  try {
    return JSON.stringify(obj, null, 2)
  } catch (error) {
    return 'Error formatting JSON: ' + error.message
  }
}

const parseJSON = (jsonString) => {
  try {
    return typeof jsonString === 'string' ? JSON.parse(jsonString) : jsonString
  } catch (error) {
    return jsonString
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
  
  // EXPONER FUNCIONES GLOBALES PARA COMPATIBILIDAD (si es necesario)
  window.loadEnterpriseCompanies = loadEnterpriseCompanies
  window.createEnterpriseCompany = createEnterpriseCompany
  window.viewEnterpriseCompany = viewEnterpriseCompany
  window.editEnterpriseCompany = editEnterpriseCompany
  window.saveEnterpriseCompany = saveEnterpriseCompany
  window.testEnterpriseCompany = testEnterpriseCompany
  window.migrateCompaniesToPostgreSQL = migrateCompaniesToPostgreSQL
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
  } else {
    companies.value = []
  }
})

// Actualizar lastSync cuando se cargan las empresas
watch(() => companies.value, () => {
  lastSync.value = Date.now()
})
</script>
