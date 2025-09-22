/**
 * useEnterprise.js - Composable para Funciones Enterprise - ACTUALIZADO
 * MIGRADO DE: script.js funciones enterprise
 * PRESERVAR: Comportamiento exacto de las funciones originales
 * COMPATIBILIDAD: 100% con el script.js original
 * 🔧 ACTUALIZACIÓN: Endpoints y estructuras de datos alineados
 */

import { ref, computed } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'
import { useSystemLog } from '@/composables/useSystemLog'

export const useEnterprise = () => {
  const appStore = useAppStore()
  const { apiRequest, apiRequestWithKey } = useApiRequest()
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
  
  const companyForm = ref({
    company_id: '',
    company_name: '',
    description: '',
    business_type: '',
    services: '',
    sales_agent_name: '',
    schedule_service_url: '',
    api_base_url: '',
    database_type: '',
    timezone: 'America/Bogota',
    currency: 'COP',
    environment: 'development',
    subscription_tier: 'basic',
    is_active: true,
    configuration: {},
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
      company.is_active !== false && company.status !== 'disabled'
    )
  })

  const activeCompaniesCount = computed(() => activeCompanies.value.length)

  const companiesWithIssues = computed(() => {
    return enterpriseCompanies.value.filter(company => 
      company.status === 'error' || company.status === 'warning'
    ).length
  })

  const companyOptions = computed(() => {
    return enterpriseCompanies.value.map(company => ({
      value: company.company_id,
      label: `${company.company_name || company.company_id} (${company.company_id})`,
      status: company.status || 'unknown',
      disabled: !company.is_active
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
  // FUNCIONES PRINCIPALES - ENDPOINTS ACTUALIZADOS
  // ============================================================================

  /**
   * Carga empresas enterprise - ENDPOINT ACTUALIZADO
   */
  const loadEnterpriseCompanies = async () => {
    if (isLoading.value) return

    try {
      isLoading.value = true
      addToLog('Loading enterprise companies', 'info')

      const response = await apiRequestWithKey('/api/admin/companies', {
        method: 'GET'
      })

      console.log('✅ Enterprise companies response:', response)

      // La API devuelve {companies: Array}
      if (response && response.companies && Array.isArray(response.companies)) {
        enterpriseCompanies.value = response.companies
        lastUpdateTime.value = new Date().toISOString()

        // Actualizar cache
        appStore.cache.enterpriseCompanies = response.companies
        appStore.cache.lastUpdate.enterpriseCompanies = Date.now()

        addToLog(`Enterprise companies loaded successfully (${response.companies.length} companies)`, 'success')
        showNotification(`${response.companies.length} empresas enterprise cargadas`, 'success')
        
        return response.companies

      } else {
        console.error('Invalid response format:', response)
        throw new Error(`Invalid response format: expected object with companies array`)
      }

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
   * Crea nueva empresa enterprise - ESTRUCTURA ACTUALIZADA
   */
  const createEnterpriseCompany = async (companyData = null) => {
    if (!companyData) {
      companyData = { ...companyForm.value }
    }

    try {
      isCreating.value = true
      addToLog(`Creating enterprise company: ${companyData.company_id}`, 'info')
      showNotification('Creando empresa enterprise...', 'info')

      // Validaciones
      if (!companyData.company_id || !companyData.company_name || !companyData.services) {
        throw new Error('company_id, company_name y services son requeridos')
      }

      // Validar formato de company_id
      if (!/^[a-z0-9_]+$/.test(companyData.company_id)) {
        throw new Error('El ID de empresa solo puede contener letras minúsculas, números y guiones bajos')
      }

      // Preparar datos según la estructura esperada por el backend
      const requestData = {
        company_id: companyData.company_id,
        company_name: companyData.company_name,
        description: companyData.description || '',
        business_type: companyData.business_type || 'general',
        services: companyData.services,
        sales_agent_name: companyData.sales_agent_name || '',
        schedule_service_url: companyData.schedule_service_url || '',
        api_base_url: companyData.api_base_url || '',
        database_type: companyData.database_type || '',
        timezone: companyData.timezone || 'America/Bogota',
        currency: companyData.currency || 'COP',
        environment: companyData.environment || 'development',
        subscription_tier: companyData.subscription_tier || 'basic',
        is_active: companyData.is_active !== false,
        configuration: companyData.configuration || {},
        notes: companyData.notes || ''
      }

      const response = await apiRequestWithKey('/api/admin/companies', {
        method: 'POST',
        body: requestData
      })

      // Manejo de respuesta
      let newCompany = response
      if (response.company) {
        newCompany = response.company
      } else if (response.data) {
        newCompany = response.data
      }

      // Actualizar lista local
      enterpriseCompanies.value.push(newCompany)

      addToLog(`Enterprise company created successfully: ${newCompany.company_id}`, 'success')
      showNotification('Empresa enterprise creada exitosamente', 'success')

      // Limpiar formulario
      clearCompanyForm()

      // Recargar lista
      await loadEnterpriseCompanies()

      return response

    } catch (error) {
      addToLog(`Error creating enterprise company: ${error.message}`, 'error')
      showNotification('Error creando empresa enterprise: ' + error.message, 'error')
      throw error

    } finally {
      isCreating.value = false
    }
  }

  /**
   * Ver detalles de empresa enterprise - ENDPOINT ESPECÍFICO
   */
  const viewEnterpriseCompany = async (companyId) => {
    if (!companyId) {
      showNotification('ID de empresa requerido', 'warning')
      return null
    }

    try {
      addToLog(`Viewing enterprise company: ${companyId}`, 'info')

      const response = await apiRequestWithKey(`/api/admin/companies/${companyId}`, {
        method: 'GET'
      })

      // Manejo de respuesta
      let companyData = response
      if (response.company) {
        companyData = response.company
      } else if (response.data) {
        companyData = response.data
      } else if (response.configuration) {
        // Caso especial: si viene con configuration, usar toda la respuesta
        companyData = response.configuration
        companyData.company_id = companyId
      }

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
   * Actualiza empresa enterprise - ENDPOINT ACTUALIZADO
   */
  const saveEnterpriseCompany = async (companyId, companyData = null) => {
    if (!companyId) {
      showNotification('ID de empresa requerido', 'warning')
      return false
    }

    if (!companyData) {
      companyData = { ...companyForm.value }
    }

    try {
      isUpdating.value = true
      addToLog(`Updating enterprise company: ${companyId}`, 'info')
      showNotification('Actualizando empresa enterprise...', 'info')

      // Preparar datos de actualización
      const updateData = {
        company_name: companyData.company_name,
        description: companyData.description,
        business_type: companyData.business_type,
        services: companyData.services,
        sales_agent_name: companyData.sales_agent_name,
        schedule_service_url: companyData.schedule_service_url,
        api_base_url: companyData.api_base_url,
        database_type: companyData.database_type,
        timezone: companyData.timezone,
        currency: companyData.currency,
        environment: companyData.environment,
        subscription_tier: companyData.subscription_tier,
        is_active: companyData.is_active,
        configuration: companyData.configuration,
        notes: companyData.notes
      }

      const response = await apiRequestWithKey(`/api/admin/companies/${companyId}`, {
        method: 'PUT',
        body: updateData
      })

      // Manejo de respuesta
      let updatedCompany = response
      if (response.company) {
        updatedCompany = response.company
      } else if (response.data) {
        updatedCompany = response.data
      }

      // Actualizar en lista local
      const index = enterpriseCompanies.value.findIndex(c => c.company_id === companyId)
      if (index !== -1) {
        enterpriseCompanies.value[index] = updatedCompany
      }

      addToLog(`Enterprise company updated successfully: ${companyId}`, 'success')
      showNotification('Empresa enterprise actualizada exitosamente', 'success')

      // Recargar lista
      await loadEnterpriseCompanies()

      return response

    } catch (error) {
      addToLog(`Error updating enterprise company: ${error.message}`, 'error')
      showNotification('Error actualizando empresa enterprise: ' + error.message, 'error')
      throw error

    } finally {
      isUpdating.value = false
    }
  }

  /**
   * Prueba empresa enterprise - ENDPOINT DE TEST
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

      const response = await apiRequest(`/api/conversations/test_user/test?company_id=${companyId}`, {
        method: 'POST',
        body: {
          message: testMessage,
          company_id: companyId
        }
      })

      testResults.value[companyId] = {
        ...response,
        timestamp: new Date().toISOString()
      }

      const isSuccess = response.status === 'success' || response.bot_response
      const message = isSuccess ? 
        'Test de empresa enterprise completado exitosamente' : 
        'Test de empresa enterprise completado con errores'
      
      addToLog(`Enterprise company test completed: ${companyId}`, isSuccess ? 'success' : 'warning')
      showNotification(message, isSuccess ? 'success' : 'warning')

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
   * Migra empresas a PostgreSQL
   */
  const migrateCompaniesToPostgreSQL = async () => {
    try {
      isMigrating.value = true
      addToLog('Starting companies migration to PostgreSQL', 'info')
      showNotification('Iniciando migración de empresas a PostgreSQL...', 'info')

      const response = await apiRequestWithKey('/api/admin/companies/migrate-from-json', {
        method: 'POST'
      })

      migrationResults.value = response

      addToLog('Companies migration to PostgreSQL completed', 'success')
      showNotification('Migración de empresas completada exitosamente', 'success')

      // Recargar empresas después de la migración
      await loadEnterpriseCompanies()

      return response

    } catch (error) {
      addToLog(`Error migrating companies: ${error.message}`, 'error')
      showNotification('Error en migración de empresas: ' + error.message, 'error')
      throw error

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
      description: '',
      business_type: '',
      services: '',
      sales_agent_name: '',
      schedule_service_url: '',
      api_base_url: '',
      database_type: '',
      timezone: 'America/Bogota',
      currency: 'COP',
      environment: 'development',
      subscription_tier: 'basic',
      is_active: true,
      configuration: {},
      notes: ''
    }
  }

  const populateCompanyForm = (company) => {
    companyForm.value = {
      company_id: company.company_id || '',
      company_name: company.company_name || company.name || '',
      description: company.description || '',
      business_type: company.business_type || '',
      services: company.services || '',
      sales_agent_name: company.sales_agent_name || '',
      schedule_service_url: company.schedule_service_url || '',
      api_base_url: company.api_base_url || '',
      database_type: company.database_type || '',
      timezone: company.timezone || 'America/Bogota',
      currency: company.currency || 'COP',
      environment: company.environment || 'development',
      subscription_tier: company.subscription_tier || 'basic',
      is_active: company.is_active !== false,
      configuration: company.configuration || {},
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
        const headers = 'Company_ID,Company_Name,Status,Business_Type,Services,Environment,Subscription_Tier,Is_Active\n'
        content = headers + enterpriseCompanies.value.map(company => 
          `"${company.company_id}","${company.company_name || ''}","${company.status || ''}","${company.business_type || ''}","${(company.services || '').substring(0, 100)}","${company.environment || ''}","${company.subscription_tier || ''}","${company.is_active}"`
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
  // FUNCIONES DE VALIDACIÓN
  // ============================================================================

  const validateCompanyData = (companyData) => {
    const errors = []

    if (!companyData.company_id?.trim()) {
      errors.push('ID de empresa es requerido')
    } else if (!/^[a-z0-9_]+$/.test(companyData.company_id)) {
      errors.push('ID de empresa solo puede contener letras minúsculas, números y guiones bajos')
    }

    if (!companyData.company_name?.trim()) {
      errors.push('Nombre de empresa es requerido')
    }

    if (!companyData.services?.trim()) {
      errors.push('Servicios son requeridos')
    }

    if (companyData.schedule_service_url && !isValidUrl(companyData.schedule_service_url)) {
      errors.push('URL del servicio de agenda no es válida')
    }

    if (companyData.api_base_url && !isValidUrl(companyData.api_base_url)) {
      errors.push('URL base de API no es válida')
    }

    return errors
  }

  const isValidUrl = (string) => {
    try {
      new URL(string)
      return true
    } catch (_) {
      return false
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
    activeCompaniesCount,
    companiesWithIssues,
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
    populateCompanyForm,
    validateCompanyData
  }
}
