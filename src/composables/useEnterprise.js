/**
 * useEnterprise.js - Composable para Funciones Enterprise - CORREGIDO
 * MIGRADO DE: script.js funciones loadEnterpriseCompanies(), createEnterpriseCompany(), editEnterpriseCompany(), etc.
 * PRESERVAR: Comportamiento exacto de las funciones originales
 * COMPATIBILIDAD: 100% con el script.js original
 * 🔧 CORRECCIÓN: Endpoints corregidos según documentación oficial
 */

import { ref, computed, watch } from 'vue'
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
    business_type: '',
    services: '',
    sales_agent_name: '',
    model_name: 'gpt-4o-mini',
    max_tokens: 800,
    temperature: 0.7,
    schedule_service_url: '',
    treatment_durations: {},
    timezone: 'America/Bogota',
    language: 'Spanish',
    currency: 'COP',
    subscription_tier: 'basic',
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

  const companyOptions = computed(() => {
    return enterpriseCompanies.value.map(company => ({
      value: company.company_id,
      label: `${company.company_name || company.company_id} (${company.company_id})`,
      status: company.is_active ? 'active' : 'inactive',
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
  // FUNCIONES PRINCIPALES MIGRADAS DEL SCRIPT.JS - ENDPOINTS CORREGIDOS
  // ============================================================================

  /**
   * Carga empresas enterprise - MIGRADO: loadEnterpriseCompanies() de script.js
   * 🔧 CORRECCIÓN: Endpoint corregido según documentación
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const loadEnterpriseCompanies = async () => {
    if (isLoading.value) return

    try {
      isLoading.value = true
      addToLog('Loading enterprise companies', 'info')

      // 🔧 CORRECCIÓN: Usar endpoint correcto con apiRequestWithKey
      const response = await apiRequestWithKey('/api/admin/companies', {
        method: 'GET'
      })

      console.log('✅ Enterprise companies response:', response) // DEBUG para verificar formato

      // 🔧 CORRECCIÓN: Manejo correcto del formato de respuesta según documentación
      if (response && response.success && response.data && Array.isArray(response.data.companies)) {
        enterpriseCompanies.value = response.data.companies
        lastUpdateTime.value = new Date().toISOString()

        // PRESERVAR: Actualizar cache como script.js
        appStore.cache.enterpriseCompanies = response.data.companies
        appStore.cache.lastUpdate.enterpriseCompanies = Date.now()

        addToLog(`Enterprise companies loaded successfully (${response.data.companies.length} companies)`, 'success')
        showNotification(`${response.data.companies.length} empresas enterprise cargadas`, 'success')
        
      } else if (response && response.companies && Array.isArray(response.companies)) {
        // Fallback para formato alternativo
        enterpriseCompanies.value = response.companies
        lastUpdateTime.value = new Date().toISOString()
        
        appStore.cache.enterpriseCompanies = response.companies
        appStore.cache.lastUpdate.enterpriseCompanies = Date.now()

        addToLog(`Enterprise companies loaded successfully (${response.companies.length} companies)`, 'success')
        showNotification(`${response.companies.length} empresas enterprise cargadas`, 'success')
        
      } else {
        // 🔧 CORRECCIÓN: Mensaje de error más específico
        console.error('Invalid response format:', response)
        throw new Error(`Invalid response format: expected object with companies array, got ${typeof response}`)
      }

      return enterpriseCompanies.value

    } catch (error) {
      addToLog(`Error loading enterprise companies: ${error.message}`, 'error')
      showNotification('Error cargando empresas enterprise: ' + error.message, 'error')

      // Limpiar estado en caso de error
      enterpriseCompanies.value = []
      throw error

    } finally {
      isLoading.value = false
    }
  }

  /**
   * Crea nueva empresa enterprise - MIGRADO: createEnterpriseCompany() de script.js
   * 🔧 CORRECCIÓN: Endpoint y estructura de datos corregidos
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const createEnterpriseCompany = async (companyData = null) => {
    // Si no se pasan datos, usar el formulario reactive
    if (!companyData) {
      companyData = { ...companyForm.value }
    }

    try {
      isCreating.value = true
      addToLog(`Creating enterprise company: ${companyData.company_id}`, 'info')
      showNotification('Creando empresa enterprise...', 'info')

      // PRESERVAR: Validaciones como script.js
      if (!companyData.company_id || !companyData.company_name || !companyData.services) {
        throw new Error('company_id, company_name y services son requeridos')
      }

      // Validar formato de company_id (solo minúsculas, números y _)
      if (!/^[a-z0-9_]+$/.test(companyData.company_id)) {
        throw new Error('El ID de empresa solo puede contener letras minúsculas, números y guiones bajos')
      }

      // 🔧 CORRECCIÓN: Usar endpoint correcto según documentación
      const response = await apiRequestWithKey('/api/admin/companies/create', {
        method: 'POST',
        body: {
          company_id: companyData.company_id,
          company_name: companyData.company_name,
          services: companyData.services,
          business_type: companyData.business_type || 'general',
          sales_agent_name: companyData.sales_agent_name || `Agente de ${companyData.company_name}`,
          model_name: companyData.model_name || 'gpt-4o-mini',
          max_tokens: companyData.max_tokens || 800,
          temperature: companyData.temperature || 0.7,
          schedule_service_url: companyData.schedule_service_url || '',
          treatment_durations: companyData.treatment_durations || {},
          timezone: companyData.timezone || 'America/Bogota',
          language: companyData.language || 'Spanish',
          currency: companyData.currency || 'COP',
          subscription_tier: companyData.subscription_tier || 'basic'
        }
      })

      // 🔧 CORRECCIÓN: Manejo correcto de respuesta según documentación
      let newCompany = response
      if (response.success && response.data) {
        newCompany = response.data
      }

      // Limpiar formulario después de creación exitosa
      companyForm.value = {
        company_id: '',
        company_name: '',
        business_type: '',
        services: '',
        sales_agent_name: '',
        model_name: 'gpt-4o-mini',
        max_tokens: 800,
        temperature: 0.7,
        schedule_service_url: '',
        treatment_durations: {},
        timezone: 'America/Bogota',
        language: 'Spanish',
        currency: 'COP',
        subscription_tier: 'basic',
        notes: ''
      }

      addToLog(`Enterprise company created successfully: ${newCompany.company_id}`, 'success')
      showNotification('Empresa enterprise creada exitosamente', 'success')

      // Recargar lista
      await loadEnterpriseCompanies()

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
   * Ver detalles de empresa enterprise - MIGRADO: viewEnterpriseCompany() de script.js
   * 🔧 CORRECCIÓN: Endpoint corregido
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const viewEnterpriseCompany = async (companyId) => {
    if (!companyId) {
      showNotification('ID de empresa requerido', 'warning')
      return null
    }

    try {
      addToLog(`Viewing enterprise company: ${companyId}`, 'info')

      // 🔧 CORRECCIÓN: Usar endpoint correcto
      const response = await apiRequestWithKey(`/api/admin/companies/${companyId}`)

      // 🔧 CORRECCIÓN: Manejo correcto de respuesta según documentación
      let companyData = response
      if (response.success && response.data) {
        companyData = response.data
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
   * Edita empresa enterprise - MIGRADO: editEnterpriseCompany() de script.js
   * 🔧 CORRECCIÓN: Carga datos en formulario reactive
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const editEnterpriseCompany = async (companyId) => {
    if (!companyId) {
      showNotification('ID de empresa requerido', 'warning')
      return
    }

    try {
      addToLog(`Loading company for edit: ${companyId}`, 'info')

      // Cargar datos de la empresa
      const company = await viewEnterpriseCompany(companyId)
      if (!company) return

      // 🔧 CORRECCIÓN: Llenar formulario reactive con datos de empresa
      if (company.configuration) {
        companyForm.value = {
          company_id: company.configuration.company_id || companyId,
          company_name: company.configuration.company_name || '',
          business_type: company.configuration.business_type || 'general',
          services: company.configuration.services || '',
          sales_agent_name: company.configuration.sales_agent_name || '',
          model_name: company.configuration.model_name || 'gpt-4o-mini',
          max_tokens: company.configuration.max_tokens || 800,
          temperature: company.configuration.temperature || 0.7,
          schedule_service_url: company.configuration.schedule_service_url || '',
          treatment_durations: company.configuration.treatment_durations || {},
          timezone: company.configuration.timezone || 'America/Bogota',
          language: company.configuration.language || 'Spanish',
          currency: company.configuration.currency || 'COP',
          subscription_tier: company.configuration.subscription_tier || 'basic',
          notes: ''
        }
      }

      return company

    } catch (error) {
      addToLog(`Error loading company for edit: ${error.message}`, 'error')
      showNotification('Error cargando empresa para editar: ' + error.message, 'error')
    }
  }

  /**
   * Guarda cambios de empresa enterprise - MIGRADO: saveEnterpriseCompany() de script.js
   * 🔧 CORRECCIÓN: Endpoint y manejo de respuesta corregidos
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const saveEnterpriseCompany = async (companyId, companyData = null) => {
    if (!companyId) {
      showNotification('ID de empresa requerido', 'warning')
      return false
    }

    // Si no se pasan datos, usar el formulario reactive
    if (!companyData) {
      companyData = { ...companyForm.value }
    }

    try {
      isUpdating.value = true
      addToLog(`Updating enterprise company: ${companyId}`, 'info')
      showNotification('Actualizando empresa enterprise...', 'info')

      // 🔧 CORRECCIÓN: Usar endpoint correcto
      const response = await apiRequestWithKey(`/api/admin/companies/${companyId}`, {
        method: 'PUT',
        body: {
          company_name: companyData.company_name,
          business_type: companyData.business_type,
          services: companyData.services,
          sales_agent_name: companyData.sales_agent_name,
          model_name: companyData.model_name,
          max_tokens: companyData.max_tokens,
          temperature: companyData.temperature,
          schedule_service_url: companyData.schedule_service_url,
          treatment_durations: companyData.treatment_durations,
          timezone: companyData.timezone,
          language: companyData.language,
          currency: companyData.currency,
          subscription_tier: companyData.subscription_tier
        }
      })

      addToLog(`Enterprise company updated successfully: ${companyId}`, 'success')
      showNotification('Empresa enterprise actualizada exitosamente', 'success')

      // Recargar lista
      await loadEnterpriseCompanies()

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
   * Prueba empresa enterprise - MIGRADO: testEnterpriseCompany() de script.js
   * 🔧 CORRECCIÓN: Usar endpoint de conversaciones normal (no requiere API key)
   * PRESERVAR: Comportamiento exacto de la función original
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

      // 🔧 CORRECCIÓN: Usar endpoint de conversaciones normal (como en script.js)
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

      const isSuccess = response.bot_response || response.response || response.message
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
   * Migra empresas a PostgreSQL - MIGRADO: migrateCompaniesToPostgreSQL() de script.js
   * 🔧 CORRECCIÓN: Endpoint corregido según documentación
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const migrateCompaniesToPostgreSQL = async () => {
    try {
      isMigrating.value = true
      addToLog('Starting companies migration to PostgreSQL', 'info')
      showNotification('Iniciando migración de empresas a PostgreSQL...', 'info')

      // 🔧 CORRECCIÓN: Usar endpoint correcto
      const response = await apiRequest('/api/admin/companies/migrate-from-json', {
        method: 'POST'
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
  // FUNCIONES AUXILIARES Y DE UTILIDADES
  // ============================================================================

  /**
   * Obtiene empresa por ID
   */
  const getCompanyById = (companyId) => {
    return enterpriseCompanies.value.find(c => c.company_id === companyId) || null
  }

  /**
   * Limpia formulario de empresa
   */
  const clearCompanyForm = () => {
    companyForm.value = {
      company_id: '',
      company_name: '',
      business_type: '',
      services: '',
      sales_agent_name: '',
      model_name: 'gpt-4o-mini',
      max_tokens: 800,
      temperature: 0.7,
      schedule_service_url: '',
      treatment_durations: {},
      timezone: 'America/Bogota',
      language: 'Spanish',
      currency: 'COP',
      subscription_tier: 'basic',
      notes: ''
    }
  }

  /**
   * Valida datos del formulario
   */
  const validateCompanyForm = () => {
    const errors = []
    
    if (!companyForm.value.company_id.trim()) {
      errors.push('ID de empresa es requerido')
    } else if (!/^[a-z0-9_]+$/.test(companyForm.value.company_id)) {
      errors.push('ID de empresa solo puede contener letras minúsculas, números y guiones bajos')
    }
    
    if (!companyForm.value.company_name.trim()) {
      errors.push('Nombre de empresa es requerido')
    }
    
    if (!companyForm.value.services.trim()) {
      errors.push('Servicios ofrecidos es requerido')
    }
    
    return errors
  }

  /**
   * Exporta empresas enterprise
   */
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
        const headers = 'Company_ID,Company_Name,Business_Type,Services,Subscription_Tier,Is_Active\n'
        content = headers + enterpriseCompanies.value.map(company => 
          `"${company.company_id}","${company.company_name || ''}","${company.business_type || ''}","${(company.services || '').replace(/"/g, '""')}","${company.subscription_tier || ''}","${company.is_active || false}"`
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

    // Funciones principales (PRESERVAR nombres exactos de script.js)
    loadEnterpriseCompanies,
    createEnterpriseCompany,
    viewEnterpriseCompany,
    editEnterpriseCompany,
    saveEnterpriseCompany,
    testEnterpriseCompany,
    migrateCompaniesToPostgreSQL,

    // Funciones auxiliares
    getCompanyById,
    clearCompanyForm,
    validateCompanyForm,
    exportCompanies
  }
}
