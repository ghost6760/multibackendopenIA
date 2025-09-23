/**
 * useEnterprise.js - Composable Enterprise COMPLETAMENTE ALINEADO con script.js
 * ✅ Endpoints exactos, headers idénticos, validaciones iguales
 * ✅ Estructura de datos consistente, manejo de errores igual
 * ✅ Sin duplicación de lógica, compatible 100%
 */

import { ref, computed } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'
import { useSystemLog } from '@/composables/useSystemLog'

export const useEnterprise = () => {
  const appStore = useAppStore()
  const { apiRequest } = useApiRequest()
  const { showNotification } = useNotifications()
  const { addToLog } = useSystemLog()

  // ============================================================================
  // ESTADO REACTIVO - EXACTO COMO script.js
  // ============================================================================
  const enterpriseCompanies = ref([])
  const selectedCompany = ref(null)
  const isLoading = ref(false)
  const isCreating = ref(false)
  const isUpdating = ref(false)
  const isTesting = ref(false)
  const isMigrating = ref(false)
  const lastUpdateTime = ref(null)

  // Formulario con estructura EXACTA de script.js
  const companyForm = ref({
    company_id: '',
    company_name: '',
    business_type: '',
    services: '',
    sales_agent_name: '',
    schedule_service_url: '',
    timezone: 'America/Bogota',
    currency: 'COP',
    subscription_tier: 'basic'
  })

  const testResults = ref({})
  const migrationResults = ref(null)

  // ============================================================================
  // COMPUTED - OPTIMIZADOS
  // ============================================================================
  const companiesCount = computed(() => enterpriseCompanies.value.length)
  const hasCompanies = computed(() => enterpriseCompanies.value.length > 0)

  const activeCompanies = computed(() =>
    enterpriseCompanies.value.filter(c => c.is_active !== false && c.status !== 'inactive')
  )

  const companyOptions = computed(() =>
    enterpriseCompanies.value.map(c => ({
      value: c.company_id,
      label: `${c.company_name || c.company_id} (${c.company_id})`,
      status: c.status || 'unknown',
      disabled: c.status === 'disabled'
    }))
  )

  const isFormValid = computed(() =>
    companyForm.value.company_id?.toString().trim() &&
    companyForm.value.company_name?.toString().trim() &&
    companyForm.value.services?.toString().trim()
  )

  const isAnyProcessing = computed(() =>
    isLoading.value || isCreating.value || isUpdating.value || isTesting.value || isMigrating.value
  )

  // ============================================================================
  // HELPERS INTERNOS - EXACTOS COMO script.js
  // ============================================================================
  const _adminKeyHeader = () => {
    return { 'X-API-Key': appStore.adminApiKey || '' }
  }

  const _normalizeCompanyFromResponse = (obj) => {
    if (!obj) return null
    if (obj.data && obj.data.company_id) return { ...obj.data }
    if (obj.company_id) return { ...obj }
    if (obj.data && obj.data.company) return { ...obj.data.company }
    return obj
  }

  // ============================================================================
  // CARGAR EMPRESAS - ENDPOINT Y LÓGICA EXACTA DE script.js
  // ============================================================================
  const loadEnterpriseCompanies = async ({ active_only, business_type } = {}) => {
    if (isLoading.value) return []
    
    try {
      isLoading.value = true
      addToLog('Loading enterprise companies', 'info')

      // ✅ ENDPOINT EXACTO como script.js
      let url = '/api/admin/companies'
      const params = []
      if (active_only !== undefined) params.push(`active_only=${encodeURIComponent(String(active_only))}`)
      if (business_type) params.push(`business_type=${encodeURIComponent(business_type)}`)
      if (params.length) url += `?${params.join('&')}`

      // ✅ HEADERS EXACTOS como script.js
      const response = await apiRequest(url, {
        method: 'GET',
        headers: {
          Accept: 'application/json',
          ..._adminKeyHeader()
        }
      })

      // ✅ PROCESAMIENTO EXACTO como script.js
      const companies = response?.companies || response?.data?.companies || response?.data || response
      if (!Array.isArray(companies)) {
        console.error('Invalid response format for companies:', response)
        throw new Error('Formato de respuesta inválido al listar empresas. Se esperaba un array "companies".')
      }

      enterpriseCompanies.value = companies
      lastUpdateTime.value = new Date().toISOString()

      addToLog(`Enterprise companies loaded successfully (${companies.length} companies)`, 'success')
      showNotification(`${companies.length} empresas enterprise cargadas`, 'success')

      return companies
    } catch (error) {
      enterpriseCompanies.value = []
      addToLog(`Error loading enterprise companies: ${error?.message || error}`, 'error')
      showNotification('Error cargando empresas enterprise: ' + (error?.message || error), 'error')
      throw error
    } finally {
      isLoading.value = false
    }
  }

  // ============================================================================
  // CREAR EMPRESA - LÓGICA Y VALIDACIONES EXACTAS DE script.js
  // ============================================================================
  const createEnterpriseCompany = async (companyData) => {
    if (!companyData) {
      addToLog('createEnterpriseCompany called without companyData', 'warning')
      showNotification('Datos de empresa vacíos', 'warning')
      return false
    }

    // ✅ VALIDACIONES EXACTAS como script.js
    if (!companyData.company_id || !companyData.company_name || !companyData.services) {
      const errMsg = 'company_id, company_name y services son requeridos'
      addToLog(`Validation failed: ${errMsg}`, 'error')
      showNotification(errMsg, 'error')
      throw new Error(errMsg)
    }
    
    if (!/^[a-z0-9_]+$/.test(companyData.company_id)) {
      const errMsg = 'El ID de empresa solo puede contener letras minúsculas, números y guiones bajos'
      addToLog(`Validation failed: ${errMsg}`, 'error')
      showNotification(errMsg, 'error')
      throw new Error(errMsg)
    }

    // ✅ VALIDACIÓN TREATMENT_DURATIONS como script.js
    if (companyData.treatment_durations && typeof companyData.treatment_durations === 'object') {
      for (const [k, v] of Object.entries(companyData.treatment_durations)) {
        if (typeof v !== 'number' || !isFinite(v) || v <= 0) {
          const errMsg = `treatment_durations.${k} debe ser número positivo`
          addToLog(`Validation failed: ${errMsg}`, 'error')
          showNotification(errMsg, 'error')
          throw new Error(errMsg)
        }
      }
    }

    try {
      isCreating.value = true
      addToLog(`Creating enterprise company: ${companyData.company_id}`, 'info')
      showNotification('Creando empresa enterprise...', 'info')

      // ✅ ENDPOINT Y HEADERS EXACTOS como script.js
      const response = await apiRequest('/api/admin/companies/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
          ..._adminKeyHeader()
        },
        body: JSON.stringify(companyData)
      })

      const newCompany = _normalizeCompanyFromResponse(response) || response

      // ✅ ACTUALIZAR CACHE como script.js
      enterpriseCompanies.value.push({
        company_id: newCompany.company_id || companyData.company_id,
        company_name: newCompany.company_name || companyData.company_name,
        business_type: newCompany.business_type || companyData.business_type || '',
        is_active: newCompany.is_active !== undefined ? newCompany.is_active : true,
        ...newCompany
      })

      addToLog(`Enterprise company created successfully: ${newCompany.company_id || companyData.company_id}`, 'success')
      showNotification('Empresa enterprise creada exitosamente', 'success')
      return response

    } catch (error) {
      addToLog(`Error creating enterprise company: ${error?.message || error}`, 'error')
      showNotification('Error creando empresa enterprise: ' + (error?.message || error), 'error')
      throw error
    } finally {
      isCreating.value = false
    }
  }

  // ============================================================================
  // VER EMPRESA - ENDPOINT EXACTO como script.js
  // ============================================================================
  const viewEnterpriseCompany = async (companyId) => {
    if (!companyId) {
      showNotification('ID de empresa requerido', 'warning')
      return null
    }

    try {
      addToLog(`Viewing enterprise company: ${companyId}`, 'info')
      
      // ✅ ENDPOINT EXACTO como script.js
      const response = await apiRequest(`/api/admin/companies/${encodeURIComponent(companyId)}`, {
        method: 'GET',
        headers: {
          Accept: 'application/json',
          ..._adminKeyHeader()
        }
      })

      const companyData = _normalizeCompanyFromResponse(response) || response
      selectedCompany.value = companyData

      addToLog(`Enterprise company details loaded: ${companyId}`, 'success')
      return companyData
    } catch (error) {
      addToLog(`Error viewing enterprise company: ${error?.message || error}`, 'error')
      showNotification('Error viendo empresa enterprise: ' + (error?.message || error), 'error')
      return null
    }
  }

  // ============================================================================
  // ACTUALIZAR EMPRESA - ENDPOINT EXACTO como script.js
  // ============================================================================
  const saveEnterpriseCompany = async (companyId, companyData) => {
    if (!companyId || !companyData) {
      showNotification('ID de empresa y datos requeridos', 'warning')
      return false
    }

    try {
      isUpdating.value = true
      addToLog(`Updating enterprise company: ${companyId}`, 'info')
      showNotification('Actualizando empresa enterprise...', 'info')

      // ✅ ENDPOINT Y HEADERS EXACTOS como script.js
      const response = await apiRequest(`/api/admin/companies/${encodeURIComponent(companyId)}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
          ..._adminKeyHeader()
        },
        body: JSON.stringify(companyData)
      })

      const updatedCompany = _normalizeCompanyFromResponse(response) || response

      // ✅ ACTUALIZAR CACHE como script.js
      const idx = enterpriseCompanies.value.findIndex(c => c.company_id === companyId)
      if (idx !== -1) {
        enterpriseCompanies.value[idx] = { ...enterpriseCompanies.value[idx], ...updatedCompany }
      }

      addToLog(`Enterprise company updated successfully: ${companyId}`, 'success')
      showNotification('Empresa enterprise actualizada exitosamente', 'success')

      return response
    } catch (error) {
      addToLog(`Error updating enterprise company: ${error?.message || error}`, 'error')
      showNotification('Error actualizando empresa enterprise: ' + (error?.message || error), 'error')
      throw error
    } finally {
      isUpdating.value = false
    }
  }

  // ============================================================================
  // PROBAR EMPRESA - ENDPOINT EXACTO como script.js
  // ============================================================================
  const testEnterpriseCompany = async (companyId, testMessage = '¿Cuáles son sus servicios disponibles?') => {
    if (!companyId) {
      showNotification('ID de empresa requerido', 'warning')
      return null
    }

    try {
      isTesting.value = true
      addToLog(`Testing enterprise company: ${companyId}`, 'info')
      showNotification('Probando empresa enterprise...', 'info')

      // ✅ ENDPOINT Y HEADERS EXACTOS como script.js
      const url = `/api/conversations/test_user/test?company_id=${encodeURIComponent(companyId)}`
      const response = await apiRequest(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
          'X-Company-ID': companyId
        },
        body: JSON.stringify({ message: testMessage, company_id: companyId })
      })

      testResults.value[companyId] = { ...response, timestamp: new Date().toISOString() }

      addToLog(`Enterprise company test completed: ${companyId}`, 'success')
      showNotification('Test de empresa enterprise completado', 'success')

      return response
    } catch (error) {
      addToLog(`Error testing enterprise company: ${error?.message || error}`, 'error')
      showNotification('Error probando empresa enterprise: ' + (error?.message || error), 'error')
      return null
    } finally {
      isTesting.value = false
    }
  }

  // ============================================================================
  // MIGRAR EMPRESAS - ENDPOINT EXACTO como script.js
  // ============================================================================
  const migrateCompaniesToPostgreSQL = async () => {
    // ✅ CONFIRM EXACTO como script.js
    if (typeof window !== 'undefined') {
      const proceed = window.confirm('¿Estás seguro de migrar las empresas a PostgreSQL? Esta operación puede tomar tiempo.')
      if (!proceed) return false
    }

    try {
      isMigrating.value = true
      addToLog('Starting companies migration to PostgreSQL', 'info')
      showNotification('Iniciando migración de empresas a PostgreSQL...', 'info')

      // ✅ ENDPOINT EXACTO como script.js
      const response = await apiRequest('/api/admin/companies/migrate-from-json', {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          ..._adminKeyHeader()
        }
      })

      migrationResults.value = response

      addToLog('Companies migration to PostgreSQL completed', 'success')
      showNotification('Migración de empresas completada exitosamente', 'success')

      // ✅ RECARGAR como script.js
      await loadEnterpriseCompanies()

      return response
    } catch (error) {
      addToLog(`Error migrating companies: ${error?.message || error}`, 'error')
      showNotification('Error en migración de empresas: ' + (error?.message || error), 'error')
      throw error
    } finally {
      isMigrating.value = false
    }
  }

  // ============================================================================
  // UTILIDADES - EXACTAS como script.js
  // ============================================================================
  const getCompanyById = (companyId) => {
    if (!companyId) return null
    return enterpriseCompanies.value.find(c => c.company_id === companyId) || null
  }

  const clearCompanyForm = () => {
    companyForm.value = {
      company_id: '',
      company_name: '',
      business_type: '',
      services: '',
      sales_agent_name: '',
      schedule_service_url: '',
      timezone: 'America/Bogota',
      currency: 'COP',
      subscription_tier: 'basic'
    }
  }

  const populateCompanyForm = (company) => {
    if (!company) return
    companyForm.value = {
      company_id: company.company_id || '',
      company_name: company.company_name || company.name || '',
      business_type: company.business_type || '',
      services: company.services || '',
      sales_agent_name: company.sales_agent_name || '',
      schedule_service_url: company.schedule_service_url || '',
      timezone: company.timezone || 'America/Bogota',
      currency: company.currency || 'COP',
      subscription_tier: company.subscription_tier || 'basic'
    }
  }

  // ✅ EXPORTAR - LÓGICA EXACTA como script.js
  const exportCompanies = (format = 'json') => {
    try {
      const dataToExport = {
        export_timestamp: new Date().toISOString(),
        companies: enterpriseCompanies.value,
        total_count: enterpriseCompanies.value.length
      }

      let content = ''
      const timestamp = new Date().toISOString().split('T')[0]

      if (format === 'json') {
        content = JSON.stringify(dataToExport, null, 2)
      } else if (format === 'csv') {
        const headers = ['Company_ID', 'Company_Name', 'Business_Type', 'Status', 'Services', 'Last_Modified']
        const rows = enterpriseCompanies.value.map(c => ([
          c.company_id,
          c.company_name || '',
          c.business_type || '',
          c.is_active ? 'Active' : 'Inactive',
          (c.services && typeof c.services === 'string') ? c.services.replace(/"/g, '""') : '',
          c.last_modified || ''
        ]))
        content = headers.join(',') + '\n' + rows.map(r => r.map(cell => `"${String(cell || '')}"`).join(',')).join('\n')
      } else {
        throw new Error('Formato de exportación no soportado')
      }

      const blob = new Blob([content], { type: format === 'json' ? 'application/json' : 'text/csv' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `enterprise_companies_${timestamp}.${format}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)

      addToLog(`Enterprise companies exported to ${format.toUpperCase()} format`, 'success')
      showNotification(`Empresas enterprise exportadas en formato ${format.toUpperCase()}`, 'success')
    } catch (error) {
      addToLog(`Error exporting companies: ${error?.message || error}`, 'error')
      showNotification(`Error exportando empresas: ${error?.message || error}`, 'error')
    }
  }

  // ============================================================================
  // RETURN API - EXACTA como necesitan los componentes
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
    companyForm,
    testResults,
    migrationResults,
    lastUpdateTime,

    // Computed
    companiesCount,
    hasCompanies,
    activeCompanies,
    companyOptions,
    isFormValid,
    isAnyProcessing,

    // Acciones principales
    loadEnterpriseCompanies,
    createEnterpriseCompany,
    viewEnterpriseCompany,
    saveEnterpriseCompany,
    testEnterpriseCompany,
    migrateCompaniesToPostgreSQL,

    // Utilidades
    getCompanyById,
    exportCompanies,
    clearCompanyForm,
    populateCompanyForm
  }
}
