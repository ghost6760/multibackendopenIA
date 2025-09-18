/**
 * useCompanies.js - Composable para Gestión de Empresas
 * MIGRADO DE: script.js funciones loadCompanies(), handleCompanyChange(), reloadCompaniesConfig()
 * PRESERVAR: Comportamiento exacto de las funciones originales
 * COMPATIBILIDAD: 100% con el script.js original
 */

import { ref, computed, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { useApiRequest } from '@/composables/useApiRequest'
import { useNotifications } from '@/composables/useNotifications'
import { useSystemLog } from '@/composables/useSystemLog'

export const useCompanies = () => {
  const appStore = useAppStore()
  const { apiRequest } = useApiRequest()
  const { showNotification } = useNotifications()
  const { addToLog } = useSystemLog()

  // ============================================================================
  // ESTADO LOCAL
  // ============================================================================

  const companies = ref([])
  const isLoading = ref(false)
  const lastUpdateTime = ref(null)
  const selectedCompany = ref(null)
  const companiesStatus = ref({})
  const isLoadingStatus = ref(false)

  // ============================================================================
  // COMPUTED PROPERTIES
  // ============================================================================

  const companiesCount = computed(() => companies.value.length)

  const availableCompanies = computed(() => {
    return companies.value.filter(company => 
      company.status !== 'disabled' && 
      company.status !== 'inactive'
    )
  })

  const companyOptions = computed(() => {
    return companies.value.map(company => ({
      value: company.id || company.company_id,
      label: company.name || company.company_name || company.id,
      status: company.status || 'unknown',
      disabled: company.status === 'disabled'
    }))
  })

  const hasValidCompanies = computed(() => availableCompanies.value.length > 0)

  const currentCompany = computed(() => {
    if (!appStore.currentCompanyId) return null
    return companies.value.find(company => 
      (company.id || company.company_id) === appStore.currentCompanyId
    )
  })

  // ============================================================================
  // FUNCIONES PRINCIPALES MIGRADAS DEL SCRIPT.JS
  // ============================================================================

  /**
   * Carga la lista de empresas - MIGRADO: loadCompanies() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const loadCompanies = async () => {
    if (isLoading.value) return

    try {
      isLoading.value = true
      addToLog('Loading companies from API', 'info')
      
      // PRESERVAR: Llamada API exacta como en script.js
      const response = await apiRequest('/api/companies')
      
      if (response && Array.isArray(response)) {
        companies.value = response
        
        // PRESERVAR: Actualizar cache como en script.js
        appStore.cache.companies = response
        appStore.cache.lastUpdate.companies = Date.now()
        
        lastUpdateTime.value = new Date().toISOString()
        
        // PRESERVAR: Logging exacto como script.js
        addToLog(`Companies loaded successfully (${response.length} companies)`, 'success')
        
        // Actualizar selector de empresas si no hay empresa seleccionada
        if (!appStore.currentCompanyId && response.length > 0) {
          const defaultCompany = response.find(c => 
            (c.id || c.company_id) === 'benova'
          ) || response[0]
          
          if (defaultCompany) {
            await handleCompanyChange(defaultCompany.id || defaultCompany.company_id)
          }
        }
        
        return response
        
      } else {
        throw new Error('Invalid response format: expected array of companies')
      }
      
    } catch (error) {
      addToLog(`Error loading companies: ${error.message}`, 'error')
      showNotification('Error cargando empresas: ' + error.message, 'error')
      
      // PRESERVAR: Fallback a cache como en script.js
      if (appStore.cache.companies) {
        companies.value = appStore.cache.companies
        addToLog('Loaded companies from cache as fallback', 'warning')
        showNotification('Empresas cargadas desde cache', 'warning')
      }
      
      throw error
      
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Maneja el cambio de empresa - MIGRADO: handleCompanyChange() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const handleCompanyChange = async (companyId) => {
    if (!companyId) {
      addToLog('Company change attempted with empty companyId', 'warning')
      return false
    }

    const previousCompany = appStore.currentCompanyId

    try {
      addToLog(`Changing company from ${previousCompany} to ${companyId}`, 'info')
      
      // PRESERVAR: Cambio de empresa en store exacto como script.js
      appStore.setCurrentCompany(companyId)
      
      // Buscar información de la empresa
      const company = companies.value.find(c => 
        (c.id || c.company_id) === companyId
      )
      
      selectedCompany.value = company || null
      
      // PRESERVAR: Notificación como script.js
      const companyName = company?.name || company?.company_name || companyId
      showNotification(`Empresa cambiada a: ${companyName}`, 'success')
      
      // PRESERVAR: Log como script.js
      addToLog(`Company changed successfully to ${companyId}`, 'success')
      
      // Limpiar cache relacionado con la empresa anterior
      if (previousCompany !== companyId) {
        clearCompanyRelatedCache()
      }
      
      // Emitir evento para que otros componentes reaccionen
      if (typeof window !== 'undefined' && window.dispatchEvent) {
        window.dispatchEvent(new CustomEvent('companyChanged', {
          detail: { 
            previous: previousCompany, 
            current: companyId,
            company: company
          }
        }))
      }
      
      return true
      
    } catch (error) {
      addToLog(`Error changing company: ${error.message}`, 'error')
      showNotification(`Error cambiando empresa: ${error.message}`, 'error')
      
      // Revertir cambio en caso de error
      if (previousCompany) {
        appStore.setCurrentCompany(previousCompany)
      }
      
      return false
    }
  }

  /**
   * Recarga la configuración de empresas - MIGRADO: reloadCompaniesConfig() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const reloadCompaniesConfig = async () => {
    try {
      addToLog('Reloading companies configuration', 'info')
      showNotification('Recargando configuración de empresas...', 'info')
      
      // PRESERVAR: Limpiar cache como script.js
      appStore.cache.companies = null
      appStore.cache.lastUpdate.companies = null
      
      // Recargar empresas
      await loadCompanies()
      
      // PRESERVAR: Mensaje de éxito como script.js
      showNotification('Configuración de empresas recargada exitosamente', 'success')
      addToLog('Companies configuration reloaded successfully', 'success')
      
      return true
      
    } catch (error) {
      addToLog(`Error reloading companies config: ${error.message}`, 'error')
      showNotification('Error recargando configuración de empresas: ' + error.message, 'error')
      return false
    }
  }

  /**
   * Carga el estado de las empresas - MIGRADO: loadCompaniesStatus() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const loadCompaniesStatus = async () => {
    if (isLoadingStatus.value) return

    try {
      isLoadingStatus.value = true
      addToLog('Loading companies status', 'info')
      
      // PRESERVAR: Si hay empresas cargadas, verificar estado de cada una
      if (companies.value.length > 0) {
        const statusPromises = companies.value.map(async (company) => {
          try {
            const companyId = company.id || company.company_id
            
            // Verificar salud de la empresa específica
            const healthResponse = await apiRequest(`/api/health/company/${companyId}`)
            
            return {
              companyId,
              status: healthResponse.status || 'unknown',
              health: healthResponse,
              lastCheck: new Date().toISOString()
            }
            
          } catch (error) {
            return {
              companyId: company.id || company.company_id,
              status: 'error',
              error: error.message,
              lastCheck: new Date().toISOString()
            }
          }
        })
        
        const results = await Promise.allSettled(statusPromises)
        const statusMap = {}
        
        results.forEach((result, index) => {
          if (result.status === 'fulfilled') {
            const { companyId, ...status } = result.value
            statusMap[companyId] = status
          } else {
            const company = companies.value[index]
            const companyId = company.id || company.company_id
            statusMap[companyId] = {
              status: 'error',
              error: result.reason?.message || 'Unknown error',
              lastCheck: new Date().toISOString()
            }
          }
        })
        
        companiesStatus.value = statusMap
        
        // PRESERVAR: Actualizar cache como script.js
        appStore.cache.companiesStatus = statusMap
        appStore.cache.lastUpdate.companiesStatus = Date.now()
        
        addToLog(`Companies status loaded for ${Object.keys(statusMap).length} companies`, 'success')
      }
      
    } catch (error) {
      addToLog(`Error loading companies status: ${error.message}`, 'error')
      showNotification('Error cargando estado de empresas: ' + error.message, 'error')
    } finally {
      isLoadingStatus.value = false
    }
  }

  // ============================================================================
  // FUNCIONES AUXILIARES
  // ============================================================================

  /**
   * Limpia cache relacionado con empresas
   */
  const clearCompanyRelatedCache = () => {
    const cacheKeys = ['documents', 'conversations', 'prompts', 'multimedia']
    cacheKeys.forEach(key => {
      if (appStore.cache[key]) {
        appStore.cache[key] = null
        appStore.cache.lastUpdate[key] = null
      }
    })
    addToLog('Company-related cache cleared', 'info')
  }

  /**
   * Busca empresa por ID o nombre
   */
  const findCompany = (query) => {
    if (!query) return null
    
    const lowerQuery = query.toLowerCase()
    
    return companies.value.find(company => {
      const id = (company.id || company.company_id || '').toLowerCase()
      const name = (company.name || company.company_name || '').toLowerCase()
      
      return id === lowerQuery || 
             name === lowerQuery || 
             id.includes(lowerQuery) || 
             name.includes(lowerQuery)
    })
  }

  /**
   * Valida si una empresa existe y está disponible
   */
  const validateCompany = (companyId) => {
    if (!companyId) return { valid: false, reason: 'Company ID is required' }
    
    const company = companies.value.find(c => 
      (c.id || c.company_id) === companyId
    )
    
    if (!company) {
      return { valid: false, reason: 'Company not found' }
    }
    
    if (company.status === 'disabled') {
      return { valid: false, reason: 'Company is disabled' }
    }
    
    return { valid: true, company }
  }

  /**
   * Obtiene estadísticas de empresas
   */
  const getCompaniesStats = () => {
    const stats = {
      total: companies.value.length,
      active: 0,
      inactive: 0,
      disabled: 0,
      healthy: 0,
      warning: 0,
      error: 0
    }
    
    companies.value.forEach(company => {
      const status = company.status || 'unknown'
      if (stats.hasOwnProperty(status)) {
        stats[status]++
      }
      
      const companyId = company.id || company.company_id
      const companyStatus = companiesStatus.value[companyId]
      if (companyStatus) {
        const health = companyStatus.status || 'unknown'
        if (stats.hasOwnProperty(health)) {
          stats[health]++
        }
      }
    })
    
    return stats
  }

  // ============================================================================
  // INICIALIZACIÓN
  // ============================================================================

  /**
   * Inicializa el composable con datos existentes
   */
  const initializeCompanies = async () => {
    // Cargar desde cache si está disponible
    if (appStore.cache.companies) {
      companies.value = appStore.cache.companies
      addToLog('Companies loaded from cache', 'info')
    }
    
    if (appStore.cache.companiesStatus) {
      companiesStatus.value = appStore.cache.companiesStatus
    }
    
    // Cargar datos frescos en background
    try {
      await loadCompanies()
      await loadCompaniesStatus()
    } catch (error) {
      // Error ya manejado en loadCompanies
    }
  }

  // ============================================================================
  // WATCHERS
  // ============================================================================

  // Watcher para reaccionar a cambios en la empresa actual
  watch(() => appStore.currentCompanyId, (newCompanyId, oldCompanyId) => {
    if (newCompanyId !== oldCompanyId) {
      addToLog(`Company watcher triggered: ${oldCompanyId} → ${newCompanyId}`, 'info')
      
      // Actualizar empresa seleccionada
      const company = companies.value.find(c => 
        (c.id || c.company_id) === newCompanyId
      )
      selectedCompany.value = company || null
    }
  })

  // ============================================================================
  // RETURN COMPOSABLE API
  // ============================================================================

  return {
    // Estado reactivo
    companies,
    isLoading,
    isLoadingStatus,
    lastUpdateTime,
    selectedCompany,
    companiesStatus,
    
    // Computed properties
    companiesCount,
    availableCompanies,
    companyOptions,
    hasValidCompanies,
    currentCompany,

    // Funciones principales (PRESERVAR nombres exactos de script.js)
    loadCompanies,
    handleCompanyChange,
    reloadCompaniesConfig,
    loadCompaniesStatus,

    // Funciones auxiliares
    findCompany,
    validateCompany,
    getCompaniesStats,
    clearCompanyRelatedCache,

    // Inicialización
    initializeCompanies
  }
}
