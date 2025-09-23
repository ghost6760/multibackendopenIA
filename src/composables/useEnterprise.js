/**
 * useEnterprise.js - Composable Enterprise CORREGIDO
 * ALINEADO CON: script.js endpoints y estructura exacta
 * PRESERVAR: Comportamiento 100% compatible
 */

import { ref, computed, watch } from 'vue'
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
  // ESTADO REACTIVO
  // ============================================================================

  const enterpriseCompanies = ref([])
  const selectedCompany = ref(null)
  const isLoading = ref(false)
  const isCreating = ref(false)
  const isUpdating = ref(false)
  const isTesting = ref(false)
  const isMigrating = ref(false)
  
  const companyForm = ref({
    company_id: '',
    company_name: '',
    business_type: '',
    services: '',
    sales_agent_name: '',
    model_name: 'gpt-4o-mini',
    max_tokens: 150,
    temperature: 0.7,
    schedule_service_url: '',
    treatment_durations: {},
    timezone: 'America/Bogota',
    language: 'es',
    currency: 'COP',
    subscription_tier: 'basic',
    description: '',
    api_base_url: '',
    database_type: '',
    environment: 'development',
    is_active: true,
    notes: ''
  })
  
  const testResults = ref({})
  const migrationResults = ref(null)
  const lastUpdateTime = ref(null)

  // ============================================================================
  // COMPUTED PROPERTIES
  // ============================================================================

  const companiesCount = computed(() => enterpriseCompanies.value.length)
  const hasCompanies = computed(() => enterpriseCompanies.value.length > 0)
  
  const activeCompanies = computed(() => {
    return enterpriseCompanies.value.filter(company => 
      company.is_active !== false && company.status !== 'inactive'
    )
  })

  const companyOptions = computed(() => {
    return enterpriseCompanies.value.map(company => ({
      value: company.company_id,
      label: `${company.company_name || company.company_id} (${company.company_id})`,
      status: company.status || 'unknown',
      disabled: company.status === 'disabled'
    }))
  })

  const isFormValid = computed(() => {
    return companyForm.value.company_id.trim() &&
           companyForm.value.company_name.trim() &&
           companyForm.value.services.trim()
  })

  const isAnyProcessing = computed(() => 
    isLoading.value || isCreating.value || isUpdating.value || isTesting.value || isMigrating.value
  )

  // ============================================================================
  // FUNCIONES PRINCIPALES - ENDPOINTS CORREGIDOS
  // ============================================================================

  /**
   * 🔧 CORREGIDO: Usar endpoint exacto de script.js
   */
  const loadEnterpriseCompanies = async () => {
    if (isLoading.value) return

    try {
      isLoading.value = true
      addToLog('Loading enterprise companies', 'info')

      // ✅ ENDPOINT CORREGIDO: GET /api/admin/companies con API key
      const response = await apiRequest('/api/admin/companies', {
        method: 'GET',
        headers: {
          'X-API-Key': appStore.adminApiKey || ''
        }
      })

      console.log('✅ Enterprise companies response:', response)

      // ✅ ESTRUCTURA CORREGIDA: response.data.companies (no response.companies)
      if (response && response.data && Array.isArray(response.data.companies)) {
        enterpriseCompanies.value = response.data.companies
        lastUpdateTime.value = new Date().toISOString()

        addToLog(`Enterprise companies loaded successfully (${response.data.companies.length} companies)`, 'success')
        showNotification(`${response.data.companies.length} empresas enterprise cargadas`, 'success')
        
      } else {
        console.error('Invalid response format:', response)
        throw new Error(`Invalid response format: expected data.companies array, got ${typeof response}`)
      }

      return response.data.companies

    } catch (error) {
      addToLog(`Error loading enterprise companies: ${error.message}`, 'error')
      showNotification('Error cargando empresas enterprise: ' + error.message, 'error')
      enterpriseCompanies.value = []
      throw error

    } finally {
      isLoading.value = false
    }
  }

  /**
   * 🔧 CORREGIDO: Usar endpoint de creación exacto de script.js
   */
  const createEnterpriseCompany = async (companyData) => {
    if (!companyData) return false

    try {
      isCreating.value = true
      addToLog(`Creating enterprise company: ${companyData.company_id}`, 'info')
      showNotification('Creando empresa enterprise...', 'info')

      // ✅ VALIDACIONES EXACTAS como script.js
      if (!companyData.company_id || !companyData.company_name || !companyData.services) {
        throw new Error('company_id, company_name y services son requeridos')
      }

      // ✅ Validar formato de company_id como script.js
      if (!/^[a-z0-9_]+$/.test(companyData.company_id)) {
        throw new Error('El ID de empresa solo puede contener letras minúsculas, números y guiones bajos')
      }

      // ✅ ENDPOINT CORREGIDO: POST /api/admin/companies/create (no /api/admin/companies)
      const response = await apiRequest('/api/admin/companies/create', {
        method: 'POST',
        headers: {
          'X-API-Key': appStore.adminApiKey || ''
        },
        body: companyData
      })

      // ✅ ESTRUCTURA CORREGIDA: response.data (no response.company)
      const newCompany = response.data || response

      addToLog(`Enterprise company created successfully: ${newCompany.company_id}`, 'success')
      showNotification('Empresa enterprise creada exitosamente', 'success')

      // Actualizar lista local
      enterpriseCompanies.value.push({
        company_id: newCompany.company_id,
        company_name: newCompany.company_name,
        business_type: newCompany.business_type,
        is_active: true,
        ...newCompany
      })

      return response

    } catch (error) {
      addToLog(`Error creating enterprise company: ${error.message}`, 'error')
      showNotification('Error creando empresa enterprise: ' + error.message, 'error')
      return false

    } finally {
      isCreating.value = false
    }
  }

  /**
   * 🔧 CORREGIDO: Ver empresa con endpoint exacto
   */
  const viewEnterpriseCompany = async (companyId) => {
    if (!companyId) {
      showNotification('ID de empresa requerido', 'warning')
      return null
    }

    try {
      addToLog(`Viewing enterprise company: ${companyId}`, 'info')

      // ✅ ENDPOINT EXACTO: GET /api/admin/companies/{id}
      const response = await apiRequest(`/api/admin/companies/${companyId}`, {
        method: 'GET',
        headers: {
          'X-API-Key': appStore.adminApiKey || ''
        }
      })

      // ✅ ESTRUCTURA CORREGIDA: response.data
      const companyData = response.data || response
      selectedCompany.value = companyData

      addToLog(`Enterprise company details loaded: ${companyId}`, 'success')
      return companyData

    } catch (error) {
      addToLog(`Error viewing enterprise company: ${error.message}`, 'error')
      showNotification('Error viendo empresa enterprise: ' + error.message, 'error')
      return null
    }
  }

  /**
   * 🔧 CORREGIDO: Actualizar empresa con endpoint exacto
   */
  const saveEnterpriseCompany = async (companyId, companyData) => {
    if (!companyId || !companyData) {
      showNotification('ID de empresa y datos requeridos', 'warning')
      return false
    }

    try {
      isUpdating.value = true
      addToLog(`Updating enterprise company: ${companyId}`, 'info')
      showNotification('Actualizando empresa enterprise...', 'info')

      // ✅ ENDPOINT EXACTO: PUT /api/admin/companies/{id}
      const response = await apiRequest(`/api/admin/companies/${companyId}`, {
        method: 'PUT',
        headers: {
          'X-API-Key': appStore.adminApiKey || ''
        },
        body: companyData
      })

      // ✅ ESTRUCTURA CORREGIDA: response.data
      const updatedCompany = response.data || response

      // Actualizar en lista local
      const index = enterpriseCompanies.value.findIndex(c => c.company_id === companyId)
      if (index !== -1) {
        enterpriseCompanies.value[index] = { ...enterpriseCompanies.value[index], ...updatedCompany }
      }

      addToLog(`Enterprise company updated successfully: ${companyId}`, 'success')
      showNotification('Empresa enterprise actualizada exitosamente', 'success')

      return response

    } catch (error) {
      addToLog(`Error updating enterprise company: ${error.message}`, 'error')
      showNotification('Error actualizando empresa enterprise: ' + error.message, 'error')
      return false

    } finally {
      isUpdating.value = false
    }
  }

  /**
   * 🔧 CORREGIDO: Test empresa con endpoint exacto (SIN API key - usa company_id)
   */
  const testEnterpriseCompany = async (companyId, testMessage = '¿Cuáles son sus servicios disponibles?') => {
    if (!companyId) {
      showNotification('ID de empresa requerido', 'warning')
      return null
    }

    try {
      isTesting.value = true
      addToLog(`Testing enterprise company: ${companyId}`, 'info')
      showNotification('Probando empresa enterprise...', 'info')

      // ✅ ENDPOINT EXACTO como script.js: sin API key, usa X-Company-ID
      const response = await apiRequest(`/api/conversations/test_user/test?company_id=${companyId}`, {
        method: 'POST',
        headers: {
          'X-Company-ID': companyId
        },
        body: {
          message: testMessage,
          company_id: companyId
        }
      })

      testResults.value[companyId] = {
        ...response,
        timestamp: new Date().toISOString()
      }

      addToLog(`Enterprise company test completed: ${companyId}`, 'success')
      showNotification('Test de empresa enterprise completado', 'success')

      return response

    } catch (error) {
      addToLog(`Error testing enterprise company: ${error.message}`, 'error')
      showNotification('Error probando empresa enterprise: ' + error.message, 'error')
      return null

    } finally {
      isTesting.value = false
    }
  }

  /**
   * 🔧 CORREGIDO: Migración con endpoint exacto
   */
  const migrateCompaniesToPostgreSQL = async () => {
    if (!confirm('¿Estás seguro de migrar las empresas a PostgreSQL? Esta operación puede tomar tiempo.')) {
      return false
    }

    try {
      isMigrating.value = true
      addToLog('Starting companies migration to PostgreSQL', 'info')
      showNotification('Iniciando migración de empresas a PostgreSQL...', 'info')

      // ✅ ENDPOINT EXACTO: POST /api/admin/companies/migrate-from-json
      const response = await apiRequest('/api/admin/companies/migrate-from-json', {
        method: 'POST',
        headers: {
          'X-API-Key': appStore.adminApiKey || ''
        }
      })

      migrationResults.value = response

      addToLog('Companies migration to PostgreSQL completed', 'success')
      showNotification('Migración de empresas completada exitosamente', 'success')

      // Recargar empresas después de la migración
      await loadEnterpriseCompanies()

      return true

    } catch (error) {
      addToLog(`Error migrating companies: ${error.message}`, 'error')
      showNotification('Error en migración de empresas: ' + error.message, 'error')
      return false

    } finally {
      isMigrating.value = false
    }
  }

  // ============================================================================
  // FUNCIONES AUXILIARES
  // ============================================================================

  const getCompanyById = (companyId) => {
    return enterpriseCompanies.value.find(c => c.company_id === companyId) || null
  }

  const clearCompanyForm = () => {
    companyForm.value = {
      company_id: '',
      company_name: '',
      business_type: '',
      services: '',
      sales_agent_name: '',
      model_name: 'gpt-4o-mini',
      max_tokens: 150,
      temperature: 0.7,
      schedule_service_url: '',
      treatment_durations: {},
      timezone: 'America/Bogota',
      language: 'es',
      currency: 'COP',
      subscription_tier: 'basic',
      description: '',
      api_base_url: '',
      database_type: '',
      environment: 'development',
      is_active: true,
      notes: ''
    }
  }

  const populateCompanyForm = (company) => {
    companyForm.value = {
      company_id: company.company_id || '',
      company_name: company.company_name || company.name || '',
      business_type: company.business_type || '',
      services: company.services || '',
      sales_agent_name: company.sales_agent_name || '',
      model_name: company.model_name || 'gpt-4o-mini',
      max_tokens: company.max_tokens || 150,
      temperature: company.temperature || 0.7,
      schedule_service_url: company.schedule_service_url || '',
      treatment_durations: company.treatment_durations || {},
      timezone: company.timezone || 'America/Bogota',
      language: company.language || 'es',
      currency: company.currency || 'COP',
      subscription_tier: company.subscription_tier || 'basic',
      description: company.description || '',
      api_base_url: company.api_base_url || '',
      database_type: company.database_type || '',
      environment: company.environment || 'development',
      is_active: company.is_active !== false,
      notes: company.notes || ''
    }
  }

  const exportCompanies = (format = 'json') => {
    try {
      const dataToExport = {
        export_timestamp: new Date().toISOString(),
        companies: enterpriseCompanies.value,
        total_count: enterpriseCompanies.value.length
      }

      let content
      const timestamp = new Date().toISOString().split('T')[0]
      
      if (format === 'json') {
        content = JSON.stringify(dataToExport, null, 2)
      } else if (format === 'csv') {
        const headers = 'Company_ID,Company_Name,Business_Type,Status,Services_Count,Last_Modified\n'
        content = headers + enterpriseCompanies.value.map(company => 
          `"${company.company_id}","${company.company_name || ''}","${company.business_type || ''}","${company.is_active ? 'Active' : 'Inactive'}","1","${company.last_modified || ''}"`
        ).join('\n')
      }

      // Crear archivo para descarga
      const blob = new Blob([content], { 
        type: format === 'json' ? 'application/json' : 'text/csv' 
      })
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
      addToLog(`Error exporting companies: ${error.message}`, 'error')
      showNotification(`Error exportando empresas: ${error.message}`, 'error')
    }
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
    companyForm,
    testResults,
    migrationResults,
    lastUpdateTime,

    // Computed properties
    companiesCount,
    hasCompanies,
    activeCompanies,
    companyOptions,
    isFormValid,
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
  }
}
