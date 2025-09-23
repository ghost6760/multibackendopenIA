/**
 * useEnterprise.js - Composable Enterprise CORREGIDO
 * ALINEADO CON: script.js endpoints y estructura exacta
 * PRESERVAR: Comportamiento 100% compatible
 */

import { ref, computed } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'
import { useSystemLog } from '@/composables/useSystemLog'

/**
 * Nota:
 * - Este composable asume que `apiRequest(url, opts)` devuelve la respuesta ya parseada (objeto JSON)
 *   o lanza en caso de error de red/HTTP. Si tu `useApiRequest` devuelve el objeto `Response`,
 *   ajusta las llamadas (await res.json()) en consecuencia.
 *
 * - Se preserva compatibilidad con script.js: endpoints exactos y headers (X-API-Key para admin,
 *   X-Company-ID cuando corresponde) y Content-Type: application/json + JSON.stringify() en POST/PUT.
 */

export const useEnterprise = () => {
  const appStore = useAppStore()
  const { apiRequest } = useApiRequest()
  const { showNotification } = useNotifications()
  const { addToLog } = useSystemLog()

  // ======================================================================
  // Estado reactivo
  // ======================================================================
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

  // ======================================================================
  // Computed
  // ======================================================================
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

  // ======================================================================
  // Helpers internos
  // ======================================================================
  const _adminKeyHeader = () => {
    // Mantener X-API-Key explícito para compatibilidad con script.js
    return { 'X-API-Key': appStore.adminApiKey || '' }
  }

  const _ensureJsonResponse = (res) => {
    // apiRequest idealmente ya devuelve JSON. Si no, devolvemos lo que venga.
    return res
  }

  const _normalizeCompanyFromResponse = (obj) => {
    // normalizar distintos formatos: response.data, response.company, response directamente
    if (!obj) return null
    if (obj.data && obj.data.company_id) return { ...obj.data }
    if (obj.company_id) return { ...obj }
    if (obj.data && obj.data.company) return { ...obj.data.company }
    return obj
  }

  // ======================================================================
  // ENDPOINTS PRINCIPALES (alineados con script.js)
  // ======================================================================

  /**
   * GET /api/admin/companies
   * Query params: active_only, business_type (opcionales)
   */
  const loadEnterpriseCompanies = async ({ active_only, business_type } = {}) => {
    if (isLoading.value) return []
    try {
      isLoading.value = true
      addToLog('Loading enterprise companies', 'info')

      let url = '/api/admin/companies'
      // construir query params cuando se requiera
      const params = []
      if (active_only !== undefined) params.push(`active_only=${encodeURIComponent(String(active_only))}`)
      if (business_type) params.push(`business_type=${encodeURIComponent(business_type)}`)
      if (params.length) url += `?${params.join('&')}`

      const response = await apiRequest(url, {
        method: 'GET',
        headers: {
          Accept: 'application/json',
          ..._adminKeyHeader()
        }
      })

      const payload = _ensureJsonResponse(response)

      // según logs de la API real: response.companies (fallbacks)
      const companies = payload?.companies || payload?.data?.companies || payload?.data || payload
      if (!Array.isArray(companies)) {
        // si viene en una raiz diferente, intentar normalizar
        console.error('Invalid response format for companies:', payload)
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

  /**
   * POST /api/admin/companies/create
   * Body: JSON (companyData)
   * Headers: Content-Type + X-API-Key
   */
  const createEnterpriseCompany = async (companyData) => {
    if (!companyData) {
      addToLog('createEnterpriseCompany called without companyData', 'warning')
      showNotification('Datos de empresa vacíos', 'warning')
      return false
    }
  
    // Validaciones client-side
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
  
    // Optional: validate treatment_durations entries
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
      addToLog(`Creating enterprise company (attempt full payload): ${companyData.company_id}`, 'info')
      showNotification('Creando empresa enterprise...', 'info')
  
      const bodyStr = JSON.stringify(companyData)
      console.log('🔔 createEnterpriseCompany - request body (full):', bodyStr)
  
      // 1) Intentar crear con payload completo
      try {
        const res = await apiRequest('/api/admin/companies/create', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Accept: 'application/json',
            ..._adminKeyHeader()
          },
          body: bodyStr
        })
  
        const payload = _ensureJsonResponse(res)
        const newCompany = _normalizeCompanyFromResponse(payload) || payload
  
        enterpriseCompanies.value.push({
          company_id: newCompany.company_id || companyData.company_id,
          company_name: newCompany.company_name || companyData.company_name,
          business_type: newCompany.business_type || companyData.business_type || '',
          is_active: newCompany.is_active !== undefined ? newCompany.is_active : true,
          ...newCompany
        })
  
        addToLog(`Enterprise company created successfully (full): ${newCompany.company_id || companyData.company_id}`, 'success')
        showNotification('Empresa enterprise creada exitosamente', 'success')
        return payload
  
      } catch (errFull) {
        // Si falla el POST completo, intentamos fallback
        console.warn('Full create failed, attempting fallback (minimal create + PUT). Error:', errFull)
        addToLog('Full create failed, attempting minimal create', 'warning')
  
        // Intento diagnóstico: intentar fetch raw para capturar body del 500 (no rompe si falla)
        try {
          const fallbackUrl = window.__API_BASE_URL ? `${window.__API_BASE_URL}/api/admin/companies/create` : '/api/admin/companies/create'
          const raw = await fetch(fallbackUrl, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Accept: 'application/json',
              ..._adminKeyHeader()
            },
            body: bodyStr
          })
          const text = await raw.text().catch(() => '')
          let parsed = text
          try { parsed = JSON.parse(text) } catch {}
          addToLog(`Raw server response (full attempt) status ${raw.status}: ${text}`, raw.status >= 500 ? 'error' : 'info')
        } catch (rawErr) {
          console.warn('raw fetch diagnostic failed', rawErr)
        }
  
        // 2) Minimal create
        const minimal = {
          company_id: companyData.company_id,
          company_name: companyData.company_name,
          services: companyData.services
        }
  
        try {
          addToLog(`Attempting minimal create for ${minimal.company_id}`, 'info')
          const minRes = await apiRequest('/api/admin/companies/create', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Accept: 'application/json',
              ..._adminKeyHeader()
            },
            body: JSON.stringify(minimal)
          })
          const minPayload = _ensureJsonResponse(minRes)
          const created = _normalizeCompanyFromResponse(minPayload) || minPayload
  
          enterpriseCompanies.value.push({
            company_id: created.company_id || minimal.company_id,
            company_name: created.company_name || minimal.company_name,
            business_type: created.business_type || '',
            is_active: created.is_active !== undefined ? created.is_active : true,
            ...created
          })
  
          addToLog(`Minimal create succeeded for ${minimal.company_id}`, 'success')
          showNotification('Empresa creada parcialmente. Aplicando configuración adicional...', 'info')
  
          // 3) PUT para aplicar configuración restante (parche)
          try {
            const patch = { ...companyData }
            delete patch.company_id
            delete patch.company_name
            delete patch.services
  
            await apiRequest(`/api/admin/companies/${encodeURIComponent(minimal.company_id)}`, {
              method: 'PUT',
              headers: {
                'Content-Type': 'application/json',
                Accept: 'application/json',
                ..._adminKeyHeader()
              },
              body: JSON.stringify(patch)
            })
  
            addToLog(`Configuration applied via PUT for ${minimal.company_id}`, 'success')
            showNotification('Configuración adicional aplicada correctamente', 'success')
          } catch (putErr) {
            addToLog(`PUT after minimal create failed: ${putErr?.message || putErr}`, 'error')
            showNotification('La empresa fue creada, pero falló aplicar la configuración adicional. Revisa logs.', 'error')
          }
  
          return minPayload
        } catch (minErr) {
          addToLog(`Minimal create failed: ${minErr?.message || minErr}`, 'error')
          showNotification('Error creando empresa enterprise: ' + (minErr?.message || minErr), 'error')
          throw minErr
        }
      }
    } catch (finalErr) {
      addToLog(`Error creating enterprise company (final): ${finalErr?.message || finalErr}`, 'error')
      showNotification('Error creando empresa enterprise: ' + (finalErr?.message || finalErr), 'error')
      throw finalErr
    } finally {
      isCreating.value = false
    }
  }


  /**
   * GET /api/admin/companies/{companyId}
   */
  const viewEnterpriseCompany = async (companyId) => {
    if (!companyId) {
      showNotification('ID de empresa requerido', 'warning')
      return null
    }

    try {
      addToLog(`Viewing enterprise company: ${companyId}`, 'info')
      const response = await apiRequest(`/api/admin/companies/${encodeURIComponent(companyId)}`, {
        method: 'GET',
        headers: {
          Accept: 'application/json',
          ..._adminKeyHeader()
        }
      })

      const payload = _ensureJsonResponse(response)
      const companyData = _normalizeCompanyFromResponse(payload) || payload

      selectedCompany.value = companyData

      addToLog(`Enterprise company details loaded: ${companyId}`, 'success')
      return companyData
    } catch (error) {
      addToLog(`Error viewing enterprise company: ${error?.message || error}`, 'error')
      showNotification('Error viendo empresa enterprise: ' + (error?.message || error), 'error')
      return null
    }
  }

  /**
   * PUT /api/admin/companies/{companyId}
   * Body: JSON patch/updated fields
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

      const response = await apiRequest(`/api/admin/companies/${encodeURIComponent(companyId)}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
          ..._adminKeyHeader()
        },
        body: JSON.stringify(companyData)
      })

      const payload = _ensureJsonResponse(response)
      const updatedCompany = _normalizeCompanyFromResponse(payload) || payload

      // actualizar caché local
      const idx = enterpriseCompanies.value.findIndex(c => c.company_id === companyId)
      if (idx !== -1) {
        enterpriseCompanies.value[idx] = { ...enterpriseCompanies.value[idx], ...updatedCompany }
      }

      addToLog(`Enterprise company updated successfully: ${companyId}`, 'success')
      showNotification('Empresa enterprise actualizada exitosamente', 'success')

      return payload
    } catch (error) {
      addToLog(`Error updating enterprise company: ${error?.message || error}`, 'error')
      showNotification('Error actualizando empresa enterprise: ' + (error?.message || error), 'error')
      throw error
    } finally {
      isUpdating.value = false
    }
  }

  /**
   * POST /api/conversations/test_user/test?company_id={companyId}
   * Headers: Content-Type + X-Company-ID
   * Body: { message, company_id }
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

      const payload = _ensureJsonResponse(response)
      testResults.value[companyId] = { ...payload, timestamp: new Date().toISOString() }

      addToLog(`Enterprise company test completed: ${companyId}`, 'success')
      showNotification('Test de empresa enterprise completado', 'success')

      return payload
    } catch (error) {
      addToLog(`Error testing enterprise company: ${error?.message || error}`, 'error')
      showNotification('Error probando empresa enterprise: ' + (error?.message || error), 'error')
      return null
    } finally {
      isTesting.value = false
    }
  }

  /**
   * POST /api/admin/companies/migrate-from-json
   * Nota: esta acción puede tomar tiempo; confirm en UI.
   */
  const migrateCompaniesToPostgreSQL = async () => {
    // Confirm en UI (preservar comportamiento existente de script.js)
    if (typeof window !== 'undefined') {
      const proceed = window.confirm('¿Estás seguro de migrar las empresas a PostgreSQL? Esta operación puede tomar tiempo.')
      if (!proceed) return false
    }

    try {
      isMigrating.value = true
      addToLog('Starting companies migration to PostgreSQL', 'info')
      showNotification('Iniciando migración de empresas a PostgreSQL...', 'info')

      const response = await apiRequest('/api/admin/companies/migrate-from-json', {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          ..._adminKeyHeader()
        }
        // script.js no envía body por defecto en migración; si necesitas enviar JSON, añade body: JSON.stringify(payload)
      })

      const payload = _ensureJsonResponse(response)
      migrationResults.value = payload

      addToLog('Companies migration to PostgreSQL completed', 'success')
      showNotification('Migración de empresas completada exitosamente', 'success')

      // recargar empresas para sincronizar
      await loadEnterpriseCompanies()

      return payload
    } catch (error) {
      addToLog(`Error migrating companies: ${error?.message || error}`, 'error')
      showNotification('Error en migración de empresas: ' + (error?.message || error), 'error')
      throw error
    } finally {
      isMigrating.value = false
    }
  }

  // ======================================================================
  // Utilidades / auxiliares
  // ======================================================================
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
    if (!company) return
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

  /**
   * Exportar empresas a JSON/CSV (client-side)
   */
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

  // ======================================================================
  // Return (API del composable)
  // ======================================================================
  return {
    // state
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

    // computed
    companiesCount,
    hasCompanies,
    activeCompanies,
    companyOptions,
    isFormValid,
    isAnyProcessing,

    // actions
    loadEnterpriseCompanies,
    createEnterpriseCompany,
    viewEnterpriseCompany,
    saveEnterpriseCompany,
    testEnterpriseCompany,
    migrateCompaniesToPostgreSQL,

    // utils
    getCompanyById,
    exportCompanies,
    clearCompanyForm,
    populateCompanyForm
  }
}
