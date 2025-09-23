// stores/companies.js - Store de Empresas para Pinia
// Migración de lógica de empresas desde script.js preservando funcionalidad exacta
// 🔥 ACTUALIZADO: Con sincronización unificada Enterprise ↔ CompanySelector

import { defineStore } from 'pinia'
import { ref, computed, watchEffect } from 'vue'
import { useApiRequest } from '@/composables/useApiRequest'
import { useAppStore } from './app'

export const useCompaniesStore = defineStore('companies', () => {
  // ============================================================================
  // ESTADO REACTIVO - MIGRADO DE SCRIPT.JS
  // ============================================================================
  
  const appStore = useAppStore()
  const { apiRequest } = useApiRequest()
  
  // Lista de empresas cargadas
  const companies = ref([])
  const isLoadingCompanies = ref(false)
  const companiesError = ref(null)
  
  // Estado de configuración de empresas
  const companiesStatus = ref({})
  const lastStatusUpdate = ref(null)
  
  // Empresas enterprise (requiere API key)
  const enterpriseCompanies = ref([])
  const isLoadingEnterprise = ref(false)
  const enterpriseError = ref(null)
  
  // 🔥 NUEVO: Estado para sincronización
  const lastSyncTime = ref(null)
  const pendingSyncs = ref(new Set())
  
  // ============================================================================
  // COMPUTED PROPERTIES
  // ============================================================================
  
  const availableCompanies = computed(() => {
    return companies.value.filter(company => company.active !== false)
  })
  
  const currentCompany = computed(() => {
    return companies.value.find(company => company.id === appStore.currentCompanyId)
  })
  
  const companiesWithStatus = computed(() => {
    return companies.value.map(company => ({
      ...company,
      status: companiesStatus.value[company.id] || 'unknown',
      lastCheck: lastStatusUpdate.value
    }))
  })
  
  // 🔥 NUEVO: Computed para verificar si hay sincronizaciones pendientes
  const hasPendingSyncs = computed(() => pendingSyncs.value.size > 0)
  
  // ============================================================================
  // ACCIONES - PRESERVAR NOMBRES Y COMPORTAMIENTO EXACTO
  // ============================================================================
  
  /**
   * Cargar lista de empresas - MANTENER FUNCIÓN EXACTA DE script.js
   * 🔥 ACTUALIZADO: Con soporte para diferentes fuentes
   */
  const loadCompanies = async (source = 'general') => {
    try {
      isLoadingCompanies.value = true
      companiesError.value = null
      
      console.log(`🏢 Loading companies from source: ${source}`)
      
      let endpoint = '/api/companies'
      let headers = {}
      
      // Usar endpoint específico según la fuente
      if (source === 'enterprise') {
        endpoint = '/api/admin/companies'
        if (appStore.adminApiKey) {
          headers['X-API-Key'] = appStore.adminApiKey
        }
      }
      
      // ✅ LLAMADA API CON ENDPOINT DINÁMICO
      const response = await apiRequest(endpoint, { headers })
      
      let companiesData = []
      
      // Normalizar respuesta según el endpoint
      if (source === 'enterprise') {
        companiesData = Array.isArray(response) ? response : 
                       response.companies ? Object.values(response.companies) : []
        
        // Actualizar también la lista enterprise
        enterpriseCompanies.value = companiesData
      } else {
        // Para endpoint general /api/companies
        if (response.companies && typeof response.companies === 'object') {
          companiesData = Object.keys(response.companies).map(companyId => ({
            id: companyId,
            company_id: companyId,
            name: response.companies[companyId].company_name || companyId,
            company_name: response.companies[companyId].company_name || companyId,
            ...response.companies[companyId]
          }))
        } else if (Array.isArray(response)) {
          companiesData = response
        } else {
          companiesData = response
        }
      }
      
      companies.value = companiesData
      
      // ✅ PRESERVAR CACHE STRUCTURE
      appStore.cache.companies = companiesData
      appStore.cache.lastUpdate.companies = Date.now()
      
      // 🔥 ACTUALIZAR TIEMPO DE SINCRONIZACIÓN
      lastSyncTime.value = new Date().toISOString()
      
      // ✅ MANTENER LOGGING EXACTO
      appStore.addToLog(`Companies loaded successfully from ${source}`, 'info')
      console.log(`✅ Companies loaded from ${source}:`, companiesData.length)
      
      return companies.value
      
    } catch (error) {
      companiesError.value = error.message
      appStore.addToLog(`Error loading companies from ${source}: ${error.message}`, 'error')
      appStore.showNotification('Error loading companies', 'error')
      throw error
    } finally {
      isLoadingCompanies.value = false
    }
  }
  
  /**
   * 🔥 NUEVA FUNCIÓN: Actualizar empresa unificada (funciona para ambos módulos)
   */
  const updateCompany = async (companyId, companyData, source = 'general') => {
    if (!companyId) {
      throw new Error('Company ID is required')
    }
    
    // Agregar a sincronizaciones pendientes
    pendingSyncs.value.add(companyId)
    
    try {
      console.log(`🔄 Updating company ${companyId} from ${source}`)
      appStore.addToLog(`Updating company ${companyId} from ${source}`, 'info')
      
      let endpoint = `/api/companies/${companyId}`
      let headers = { 'Content-Type': 'application/json' }
      
      // Usar endpoint y headers específicos según la fuente  
      if (source === 'enterprise') {
        endpoint = `/api/admin/companies/${encodeURIComponent(companyId)}`
        
        // Agregar headers de admin
        if (appStore.adminApiKey) {
          headers['X-API-Key'] = appStore.adminApiKey
        }
      }
      
      const response = await apiRequest(endpoint, {
        method: 'PUT',
        headers,
        body: JSON.stringify(companyData)
      })
      
      // 🔥 ACTUALIZAR EN AMBAS LISTAS (companies y enterpriseCompanies)
      const updateCompanyInList = (list, data) => {
        const index = list.findIndex(c => 
          (c.id || c.company_id) === companyId
        )
        
        if (index !== -1) {
          list[index] = { 
            ...list[index], 
            ...companyData,
            ...data 
          }
          return list[index]
        }
        return null
      }
      
      // Actualizar en lista general
      const updatedCompany = updateCompanyInList(companies.value, response)
      
      // Actualizar en lista enterprise si existe
      if (enterpriseCompanies.value.length > 0) {
        updateCompanyInList(enterpriseCompanies.value, response)
      }
      
      // 🔥 INVALIDAR CACHE PARA FORZAR RECARGA COMPLETA
      appStore.cache.companies = null
      delete appStore.cache.lastUpdate.companies
      
      // 🔥 EMITIR EVENTO GLOBAL PARA NOTIFICAR A TODOS LOS COMPONENTES
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('companyUpdatedGlobal', {
          detail: { 
            companyId, 
            updatedData: companyData, 
            updatedCompany,
            source,
            timestamp: Date.now()
          }
        }))
        
        // También emitir el evento original para compatibilidad
        window.dispatchEvent(new CustomEvent('companyUpdated', {
          detail: { 
            companyId, 
            updatedData: companyData, 
            source
          }
        }))
      }
      
      // 🔥 NOTIFICAR SINCRONIZACIÓN A OTROS COMPONENTES
      await notifyComponentsOfUpdate(companyId, companyData, source)
      
      console.log(`✅ Company ${companyId} updated successfully from ${source}`)
      appStore.addToLog(`Company ${companyId} updated successfully from ${source}`, 'success')
      appStore.showNotification('✅ Empresa actualizada exitosamente', 'success')
      
      return response
      
    } catch (error) {
      console.error(`Error updating company from ${source}:`, error)
      appStore.addToLog(`Error updating company from ${source}: ${error.message}`, 'error')
      appStore.showNotification(`Error actualizando empresa: ${error.message}`, 'error')
      throw error
    } finally {
      // Remover de sincronizaciones pendientes
      pendingSyncs.value.delete(companyId)
    }
  }
  
  /**
   * 🔥 NUEVA FUNCIÓN: Notificar a componentes específicos del update
   */
  const notifyComponentsOfUpdate = async (companyId, companyData, source) => {
    try {
      // Notificar al CompanySelector si viene de Enterprise
      if (source === 'enterprise' && window.refreshCompanies) {
        setTimeout(async () => {
          try {
            await window.refreshCompanies()
            console.log('✅ CompanySelector refreshed after enterprise update')
          } catch (error) {
            console.error('Error refreshing CompanySelector:', error)
          }
        }, 100)
      }
      
      // Notificar al Enterprise module si viene de general
      if (source === 'general' && window.refreshEnterpriseCompanies) {
        setTimeout(async () => {
          try {
            await window.refreshEnterpriseCompanies()
            console.log('✅ Enterprise module refreshed after general update')
          } catch (error) {
            console.error('Error refreshing Enterprise module:', error)
          }
        }, 100)
      }
      
      // Mostrar notificación de sincronización
      setTimeout(() => {
        appStore.showNotification('🔄 Todos los componentes sincronizados', 'success', 2000)
      }, 500)
      
    } catch (error) {
      console.error('Error notifying components:', error)
    }
  }
  
  /**
   * 🔥 NUEVA FUNCIÓN: Refrescar desde fuente específica
   */
  const refreshFromSource = async (source = 'general') => {
    try {
      console.log(`🔄 Refreshing companies from ${source}`)
      
      // Limpiar cache
      appStore.cache.companies = null
      delete appStore.cache.lastUpdate.companies
      
      // Recargar desde la fuente especificada
      await loadCompanies(source)
      
      appStore.showNotification('✅ Lista de empresas actualizada', 'success')
      appStore.addToLog(`Companies refreshed from ${source}`, 'success')
      
      return companies.value
      
    } catch (error) {
      appStore.addToLog(`Error refreshing from ${source}: ${error.message}`, 'error')
      throw error
    }
  }
  
  /**
   * 🔥 NUEVA FUNCIÓN: Sincronizar ambas listas
   */
  const syncAllLists = async () => {
    try {
      console.log('🔄 Syncing all company lists...')
      
      // Cargar desde ambas fuentes
      await Promise.allSettled([
        loadCompanies('general'),
        loadCompanies('enterprise')
      ])
      
      lastSyncTime.value = new Date().toISOString()
      appStore.addToLog('All company lists synchronized', 'success')
      
    } catch (error) {
      appStore.addToLog(`Error syncing lists: ${error.message}`, 'error')
      throw error
    }
  }
  
  /**
   * Cambiar empresa activa - MANTENER FUNCIÓN EXACTA
   * @param {string} companyId - ID de la empresa
   */
  const handleCompanyChange = async (companyId) => {
    try {
      console.log('🏢 Changing company to:', companyId)
      
      // ✅ PRESERVAR LÓGICA EXACTA DE script.js
      if (companyId && companyId !== appStore.currentCompanyId) {
        appStore.currentCompanyId = companyId
        
        // ✅ MANTENER LOGGING
        appStore.addToLog(`Company changed to: ${companyId}`, 'info')
        
        // ✅ PRESERVAR VALIDACIÓN
        const isValid = await validateCompanySelection()
        
        if (isValid) {
          // ✅ MANTENER COMPORTAMIENTO DE RECARGA
          if (typeof window.refreshActiveTab === 'function') {
            window.refreshActiveTab()
          }
          
          appStore.showNotification(`Switched to company: ${companyId}`, 'success')
        }
      }
      
    } catch (error) {
      appStore.addToLog(`Error changing company: ${error.message}`, 'error')
      appStore.showNotification('Error changing company', 'error')
    }
  }
  
  /**
   * Validar selección de empresa - PRESERVAR FUNCIÓN EXACTA
   */
  const validateCompanySelection = async () => {
    try {
      if (!appStore.currentCompanyId) {
        appStore.showNotification('Please select a company', 'warning')
        return false
      }
      
      const company = companies.value.find(c => c.id === appStore.currentCompanyId)
      if (!company) {
        appStore.showNotification('Selected company not found', 'error')
        return false
      }
      
      return true
      
    } catch (error) {
      console.error('Error validating company:', error)
      return false
    }
  }
  
  /**
   * Cargar estado de empresas - MANTENER FUNCIÓN EXACTA
   */
  const loadCompaniesStatus = async () => {
    try {
      console.log('📊 Loading companies status...')
      
      const statusData = {}
      
      // ✅ PRESERVAR LÓGICA DE VERIFICACIÓN POR EMPRESA
      for (const company of companies.value) {
        try {
          const healthCheck = await apiRequest(`/api/health/company/${company.id}`)
          statusData[company.id] = healthCheck.status || 'healthy'
        } catch (error) {
          statusData[company.id] = 'error'
          console.warn(`Health check failed for ${company.id}:`, error.message)
        }
      }
      
      companiesStatus.value = statusData
      lastStatusUpdate.value = new Date().toISOString()
      
      appStore.addToLog('Companies status updated', 'info')
      
    } catch (error) {
      appStore.addToLog(`Error loading companies status: ${error.message}`, 'error')
    }
  }
  
  /**
   * Recargar configuración de empresas - MANTENER FUNCIÓN EXACTA
   */
  const reloadCompaniesConfig = async () => {
    try {
      appStore.addToLog('Reloading companies configuration...', 'info')
      
      // ✅ MANTENER LLAMADA EXACTA
      const response = await apiRequest('/api/admin/reload-companies', {
        method: 'POST'
      })
      
      appStore.showNotification('Companies configuration reloaded', 'success')
      appStore.addToLog('Companies configuration reloaded successfully', 'info')
      
      // Recargar lista después de la configuración
      await loadCompanies()
      
      return response
      
    } catch (error) {
      appStore.addToLog(`Error reloading companies config: ${error.message}`, 'error')
      appStore.showNotification('Error reloading companies configuration', 'error')
      throw error
    }
  }
  
  // ============================================================================
  // FUNCIONES ENTERPRISE - REQUIEREN API KEY
  // ============================================================================
  
  /**
   * Cargar empresas enterprise - CON API KEY
   * 🔥 ACTUALIZADO: Con sincronización automática
   */
  const loadEnterpriseCompanies = async () => {
    try {
      isLoadingEnterprise.value = true
      enterpriseError.value = null
      
      if (!appStore.adminApiKey) {
        throw new Error('API key required for enterprise operations')
      }
      
      console.log('🏢 Loading enterprise companies...')
      
      const response = await apiRequest('/api/admin/companies', {
        headers: {
          'X-API-Key': appStore.adminApiKey
        }
      })
      
      enterpriseCompanies.value = response.companies || []
      
      // 🔥 SINCRONIZAR CON LISTA GENERAL SI NO ESTÁ CARGADA
      if (companies.value.length === 0) {
        companies.value = enterpriseCompanies.value
        appStore.cache.companies = enterpriseCompanies.value
        appStore.cache.lastUpdate.companies = Date.now()
      }
      
      appStore.addToLog('Enterprise companies loaded', 'info')
      
      return enterpriseCompanies.value
      
    } catch (error) {
      enterpriseError.value = error.message
      appStore.addToLog(`Error loading enterprise companies: ${error.message}`, 'error')
      throw error
    } finally {
      isLoadingEnterprise.value = false
    }
  }
  
  /**
   * Crear nueva empresa enterprise
   * 🔥 ACTUALIZADO: Con sincronización automática
   */
  const createEnterpriseCompany = async (companyData) => {
    try {
      if (!appStore.adminApiKey) {
        throw new Error('API key required')
      }
      
      const response = await apiRequest('/api/admin/companies', {
        method: 'POST',
        headers: {
          'X-API-Key': appStore.adminApiKey
        },
        body: companyData
      })
      
      appStore.showNotification('Enterprise company created successfully', 'success')
      
      // 🔥 RECARGAR AMBAS LISTAS DESPUÉS DE CREAR
      await Promise.allSettled([
        loadEnterpriseCompanies(),
        loadCompanies('general')
      ])
      
      return response
      
    } catch (error) {
      appStore.showNotification(`Error creating company: ${error.message}`, 'error')
      throw error
    }
  }
  
  // ============================================================================
  // 🔥 NUEVAS FUNCIONES DE UTILIDAD
  // ============================================================================
  
  /**
   * Encontrar empresa por ID en cualquier lista
   */
  const findCompanyById = (companyId) => {
    // Buscar primero en la lista general
    let company = companies.value.find(c => 
      (c.id || c.company_id) === companyId
    )
    
    // Si no se encuentra, buscar en la lista enterprise
    if (!company && enterpriseCompanies.value.length > 0) {
      company = enterpriseCompanies.value.find(c => 
        (c.id || c.company_id) === companyId
      )
    }
    
    return company
  }
  
  /**
   * Validar si el cache es válido
   */
  const isCacheValid = (maxAge = 300000) => { // 5 minutos por defecto
    return appStore.cache.companies && 
           appStore.cache.lastUpdate.companies && 
           (Date.now() - appStore.cache.lastUpdate.companies) < maxAge
  }
  
  /**
   * Obtener estadísticas de sincronización
   */
  const getSyncStats = () => {
    return {
      lastSyncTime: lastSyncTime.value,
      pendingSyncs: Array.from(pendingSyncs.value),
      generalCount: companies.value.length,
      enterpriseCount: enterpriseCompanies.value.length,
      cacheValid: isCacheValid()
    }
  }
  
  // ============================================================================
  // WATCHERS PARA COMPATIBILIDAD GLOBAL
  // ============================================================================
  
  // Sincronizar con variables globales para compatibilidad
  watchEffect(() => {
    if (typeof window !== 'undefined') {
      window.companiesData = companies.value
      window.companiesStatus = companiesStatus.value
      window.enterpriseCompanies = enterpriseCompanies.value
      
      // 🔥 EXPONER NUEVAS FUNCIONES GLOBALES
      window.updateCompanyUnified = updateCompany
      window.refreshFromSource = refreshFromSource
      window.syncAllCompanyLists = syncAllLists
    }
  })
  
  // ============================================================================
  // RETURN PUBLIC API
  // ============================================================================
  
  return {
    // Estado original
    companies,
    isLoadingCompanies,
    companiesError,
    companiesStatus,
    lastStatusUpdate,
    enterpriseCompanies,
    isLoadingEnterprise,
    enterpriseError,
    
    // 🔥 NUEVO: Estado de sincronización
    lastSyncTime,
    pendingSyncs,
    hasPendingSyncs,
    
    // Computed originales
    availableCompanies,
    currentCompany,
    companiesWithStatus,
    
    // Acciones originales
    loadCompanies,
    handleCompanyChange,
    validateCompanySelection,
    loadCompaniesStatus,
    reloadCompaniesConfig,
    loadEnterpriseCompanies,
    createEnterpriseCompany,
    
    // 🔥 NUEVAS ACCIONES DE SINCRONIZACIÓN
    updateCompany,
    refreshFromSource,
    syncAllLists,
    notifyComponentsOfUpdate,
    
    // 🔥 NUEVAS UTILIDADES
    findCompanyById,
    isCacheValid,
    getSyncStats
  }
})
