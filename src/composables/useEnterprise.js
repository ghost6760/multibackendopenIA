/**
 * useEnterprise.js - CORREGIDO - Composable para Funciones Enterprise
 * 🔧 FIX: Usar apiRequestWithKey en lugar de apiRequest manual
 * 🔧 FIX: Sincronización correcta de API Key entre stores
 * 🔧 FIX: Manejo de errores específicos para API key
 */

import { ref, computed, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth' // 🔧 NUEVO: Usar auth store
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'
import { useSystemLog } from '@/composables/useSystemLog'

export const useEnterprise = () => {
  const appStore = useAppStore()
  const authStore = useAuthStore() // 🔧 NUEVO: Auth store
  const { apiRequest, apiRequestWithKey } = useApiRequest() // 🔧 CRÍTICO: Usar ambas funciones
  const { showNotification } = useNotifications()
  const { addToLog } = useSystemLog()

  // ============================================================================
  // ESTADO LOCAL
  // ============================================================================

  const enterpriseCompanies = ref([])
  const selectedCompany = ref(null)
  const isLoading = ref(false)
  const isCreating = ref(false)
  const isUpdating = ref(false)
  const isTesting = ref(false)
  const isMigrating = ref(false)
  
  const testResults = ref({})
  const migrationResults = ref(null)
  const lastUpdateTime = ref(null)

  // ============================================================================
  // COMPUTED PROPERTIES CON VALIDACIÓN DE API KEY
  // ============================================================================

  const companiesCount = computed(() => enterpriseCompanies.value.length)
  const hasCompanies = computed(() => enterpriseCompanies.value.length > 0)
  
  // 🔧 NUEVO: Validación de API key
  const hasValidApiKey = computed(() => {
    return authStore.hasApiKey && authStore.isApiKeyValid
  })

  const canPerformEnterpriseOperations = computed(() => {
    return hasValidApiKey.value && !isLoading.value
  })

  // ============================================================================
  // FUNCIONES PRINCIPALES CORREGIDAS
  // ============================================================================

  /**
   * 🔧 FUNCIÓN CORREGIDA - Carga empresas enterprise
   * FIX: Usar apiRequestWithKey + manejo correcto de API key
   */
  const loadEnterpriseCompanies = async () => {
    console.log('🏢 [useEnterprise] Loading enterprise companies...') // DEBUG

    // 🔧 FIX 1: Verificación previa de API key
    if (!hasValidApiKey.value) {
      console.log('⚠️ [useEnterprise] No valid API key, requesting configuration') // DEBUG
      showNotification('Se requiere API key válida para funciones enterprise', 'warning')
      authStore.showApiKeyModal()
      return []
    }

    if (isLoading.value) return enterpriseCompanies.value

    try {
      isLoading.value = true
      addToLog('Loading enterprise companies with API key', 'info')

      console.log('🔑 [useEnterprise] API Key available:', !!authStore.adminApiKey) // DEBUG
      console.log('🔑 [useEnterprise] API Key valid:', authStore.isApiKeyValid) // DEBUG

      // 🔧 FIX 2: Usar apiRequestWithKey en lugar de apiRequest manual
      const response = await apiRequestWithKey('/api/admin/companies', {
        method: 'GET'
      })

      console.log('✅ [useEnterprise] Response received:', response) // DEBUG

      // 🔧 FIX 3: Manejo robusto de diferentes formatos de respuesta
      let companies = []
      
      if (response.companies && Array.isArray(response.companies)) {
        companies = response.companies
      } else if (Array.isArray(response)) {
        companies = response
      } else if (response.data && Array.isArray(response.data)) {
        companies = response.data
      } else {
        console.warn('⚠️ [useEnterprise] Unexpected response format:', response)
        companies = []
      }

      enterpriseCompanies.value = companies
      lastUpdateTime.value = new Date().toISOString()

      // 🔧 FIX 4: Actualizar cache en ambos stores
      appStore.cache.enterpriseCompanies = companies
      appStore.cache.lastUpdate.enterpriseCompanies = Date.now()

      console.log(`✅ [useEnterprise] Loaded ${companies.length} enterprise companies`) // DEBUG
      addToLog(`Enterprise companies loaded successfully (${companies.length} companies)`, 'success')
      
      if (companies.length > 0) {
        showNotification(`${companies.length} empresas enterprise cargadas`, 'success')
      } else {
        showNotification('No se encontraron empresas enterprise', 'info')
      }

      return companies

    } catch (error) {
      console.error('❌ [useEnterprise] Error loading companies:', error) // DEBUG
      
      // 🔧 FIX 5: Manejo específico de errores de API key
      if (error.message.includes('401') || error.message.includes('Invalid API key') || error.message.includes('Unauthorized')) {
        console.log('🔑 [useEnterprise] API key invalid, clearing and requesting new') // DEBUG
        authStore.clearApiKey()
        authStore.showApiKeyModal()
        showNotification('API key inválida. Por favor configura una nueva.', 'error')
      } else {
        addToLog(`Error loading enterprise companies: ${error.message}`, 'error')
        showNotification('Error cargando empresas enterprise: ' + error.message, 'error')
      }

      enterpriseCompanies.value = []
      throw error

    } finally {
      isLoading.value = false
    }
  }

  /**
   * 🔧 FUNCIÓN CORREGIDA - Crear nueva empresa enterprise
   */
  const createEnterpriseCompany = async (companyData) => {
    if (!hasValidApiKey.value) {
      authStore.showApiKeyModal()
      return false
    }

    if (!companyData || !companyData.company_id || !companyData.company_name) {
      showNotification('Datos de empresa inválidos', 'error')
      return false
    }

    try {
      isCreating.value = true
      addToLog(`Creating enterprise company: ${companyData.company_id}`, 'info')
      showNotification('Creando empresa enterprise...', 'info')

      // 🔧 FIX: Usar apiRequestWithKey
      const response = await apiRequestWithKey('/api/admin/companies', {
        method: 'POST',
        body: companyData
      })

      // Actualizar lista local
      enterpriseCompanies.value.push(response)
      
      addToLog(`Enterprise company created successfully: ${response.company_id}`, 'success')
      showNotification('Empresa enterprise creada exitosamente', 'success')

      // Recargar lista completa
      await loadEnterpriseCompanies()

      return response

    } catch (error) {
      console.error('❌ [useEnterprise] Error creating company:', error)
      
      if (error.message.includes('401') || error.message.includes('Invalid API key')) {
        authStore.clearApiKey()
        authStore.showApiKeyModal()
        showNotification('API key inválida durante creación', 'error')
      } else {
        addToLog(`Error creating enterprise company: ${error.message}`, 'error')
        showNotification('Error creando empresa enterprise: ' + error.message, 'error')
      }

      return false

    } finally {
      isCreating.value = false
    }
  }

  /**
   * 🔧 FUNCIÓN CORREGIDA - Ver detalles de empresa enterprise
   */
  const viewEnterpriseCompany = async (companyId) => {
    if (!hasValidApiKey.value) {
      authStore.showApiKeyModal()
      return null
    }

    if (!companyId) {
      showNotification('ID de empresa requerido', 'warning')
      return null
    }

    try {
      addToLog(`Viewing enterprise company: ${companyId}`, 'info')

      // 🔧 FIX: Usar apiRequestWithKey
      const response = await apiRequestWithKey(`/api/admin/companies/${companyId}`, {
        method: 'GET'
      })

      selectedCompany.value = response
      addToLog(`Enterprise company details loaded: ${companyId}`, 'success')
      
      return response

    } catch (error) {
      console.error('❌ [useEnterprise] Error viewing company:', error)
      
      if (error.message.includes('401') || error.message.includes('Invalid API key')) {
        authStore.clearApiKey()
        authStore.showApiKeyModal()
      } else {
        addToLog(`Error viewing enterprise company: ${error.message}`, 'error')
        showNotification('Error viendo empresa enterprise: ' + error.message, 'error')
      }
      return null
    }
  }

  /**
   * 🔧 FUNCIÓN CORREGIDA - Actualizar empresa enterprise
   */
  const updateEnterpriseCompany = async (companyId, companyData) => {
    if (!hasValidApiKey.value) {
      authStore.showApiKeyModal()
      return false
    }

    if (!companyId || !companyData) {
      showNotification('Datos de empresa inválidos', 'error')
      return false
    }

    try {
      isUpdating.value = true
      addToLog(`Updating enterprise company: ${companyId}`, 'info')
      showNotification('Actualizando empresa enterprise...', 'info')

      // 🔧 FIX: Usar apiRequestWithKey
      const response = await apiRequestWithKey(`/api/admin/companies/${companyId}`, {
        method: 'PUT',
        body: companyData
      })

      // Actualizar en lista local
      const index = enterpriseCompanies.value.findIndex(c => c.company_id === companyId)
      if (index !== -1) {
        enterpriseCompanies.value[index] = response
      }

      addToLog(`Enterprise company updated successfully: ${companyId}`, 'success')
      showNotification('Empresa enterprise actualizada exitosamente', 'success')

      return response

    } catch (error) {
      console.error('❌ [useEnterprise] Error updating company:', error)
      
      if (error.message.includes('401') || error.message.includes('Invalid API key')) {
        authStore.clearApiKey()
        authStore.showApiKeyModal()
      } else {
        addToLog(`Error updating enterprise company: ${error.message}`, 'error')
        showNotification('Error actualizando empresa enterprise: ' + error.message, 'error')
      }

      return false

    } finally {
      isUpdating.value = false
    }
  }

  /**
   * 🔧 FUNCIÓN CORREGIDA - Probar empresa enterprise
   */
  const testEnterpriseCompany = async (companyId) => {
    if (!hasValidApiKey.value) {
      authStore.showApiKeyModal()
      return null
    }

    if (!companyId) {
      showNotification('ID de empresa requerido', 'warning')
      return null
    }

    try {
      isTesting.value = true
      addToLog(`Testing enterprise company: ${companyId}`, 'info')
      showNotification('Probando empresa enterprise...', 'info')

      // 🔧 FIX: Usar apiRequestWithKey
      const response = await apiRequestWithKey(`/api/admin/companies/${companyId}/test`, {
        method: 'POST'
      })

      testResults.value[companyId] = {
        ...response,
        timestamp: new Date().toISOString()
      }

      const isSuccess = response.status === 'success' || response.overall_status === 'success'
      const message = isSuccess ? 
        'Test de empresa enterprise completado exitosamente' : 
        'Test de empresa enterprise completado con errores'
      
      addToLog(`Enterprise company test completed: ${companyId}`, isSuccess ? 'success' : 'warning')
      showNotification(message, isSuccess ? 'success' : 'warning')

      return response

    } catch (error) {
      console.error('❌ [useEnterprise] Error testing company:', error)
      
      if (error.message.includes('401') || error.message.includes('Invalid API key')) {
        authStore.clearApiKey()
        authStore.showApiKeyModal()
      } else {
        addToLog(`Error testing enterprise company: ${error.message}`, 'error')
        showNotification('Error probando empresa enterprise: ' + error.message, 'error')
      }

      return null

    } finally {
      isTesting.value = false
    }
  }

  /**
   * 🔧 FUNCIÓN CORREGIDA - Migrar empresas a PostgreSQL
   */
  const migrateCompaniesToPostgreSQL = async () => {
    if (!hasValidApiKey.value) {
      authStore.showApiKeyModal()
      return false
    }

    if (!confirm('¿Estás seguro de migrar las empresas a PostgreSQL? Esta operación puede tomar tiempo.')) {
      return false
    }

    try {
      isMigrating.value = true
      addToLog('Starting companies migration to PostgreSQL', 'info')
      showNotification('Iniciando migración de empresas a PostgreSQL...', 'info')

      // 🔧 FIX: Usar apiRequestWithKey
      const response = await apiRequestWithKey('/api/admin/companies/migrate', {
        method: 'POST',
        body: { target: 'postgresql' }
      })

      migrationResults.value = response

      addToLog('Companies migration to PostgreSQL completed', 'success')
      showNotification('Migración de empresas completada exitosamente', 'success')

      // Recargar empresas después de la migración
      await loadEnterpriseCompanies()

      return true

    } catch (error) {
      console.error('❌ [useEnterprise] Error migrating companies:', error)
      
      if (error.message.includes('401') || error.message.includes('Invalid API key')) {
        authStore.clearApiKey()
        authStore.showApiKeyModal()
      } else {
        addToLog(`Error migrating companies: ${error.message}`, 'error')
        showNotification('Error en migración de empresas: ' + error.message, 'error')
      }

      return false

    } finally {
      isMigrating.value = false
    }
  }

  // ============================================================================
  // WATCHER PARA SINCRONIZACIÓN DE API KEY
  // ============================================================================

  // 🔧 NUEVO: Watcher para reaccionar a cambios de API key
  watch(() => authStore.isApiKeyValid, (isValid) => {
    console.log('🔑 [useEnterprise] API key validity changed:', isValid) // DEBUG
    
    if (isValid) {
      // API key válida - cargar empresas automáticamente
      loadEnterpriseCompanies()
    } else {
      // API key inválida - limpiar datos
      enterpriseCompanies.value = []
      selectedCompany.value = null
    }
  })

  // 🔧 NUEVO: Sincronización con appStore para compatibilidad
  watch(() => authStore.adminApiKey, (newKey) => {
    appStore.adminApiKey = newKey
  })

  // ============================================================================
  // FUNCIONES DE UTILIDAD
  // ============================================================================

  /**
   * 🔧 NUEVA: Verificar y solicitar API key si es necesario
   */
  const ensureApiKey = async () => {
    if (!hasValidApiKey.value) {
      console.log('🔑 [useEnterprise] API key required, showing modal') // DEBUG
      authStore.showApiKeyModal()
      return false
    }
    return true
  }

  /**
   * 🔧 NUEVA: Reinicializar estado enterprise
   */
  const resetEnterpriseState = () => {
    enterpriseCompanies.value = []
    selectedCompany.value = null
    testResults.value = {}
    migrationResults.value = null
    lastUpdateTime.value = null
  }

  // ============================================================================
  // RETURN COMPOSABLE API
  // ============================================================================

  return {
    // Estado reactivo
    enterpriseCompanies,
    selectedCompany,
    isLoading,
    isCreating,
    isUpdating,
    isTesting,
    isMigrating,
    testResults,
    migrationResults,
    lastUpdateTime,

    // Computed properties
    companiesCount,
    hasCompanies,
    hasValidApiKey,
    canPerformEnterpriseOperations,

    // 🔧 FUNCIONES CORREGIDAS - Nombres exactos preservados
    loadEnterpriseCompanies,
    createEnterpriseCompany,
    viewEnterpriseCompany,
    updateEnterpriseCompany,
    testEnterpriseCompany,
    migrateCompaniesToPostgreSQL,

    // 🔧 NUEVAS funciones de utilidad
    ensureApiKey,
    resetEnterpriseState
  }
}
