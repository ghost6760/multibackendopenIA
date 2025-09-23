// stores/companies.js - Store de Empresas para Pinia
// Migración de lógica de empresas desde script.js preservando funcionalidad exacta

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
  
  // ============================================================================
  // ACCIONES - PRESERVAR NOMBRES Y COMPORTAMIENTO EXACTO
  // ============================================================================
  
  /**
   * Cargar lista de empresas - MANTENER FUNCIÓN EXACTA DE script.js
   */
  const loadCompanies = async () => {
    try {
      isLoadingCompanies.value = true
      companiesError.value = null
      
      console.log('🏢 Loading companies...')
      
      // ✅ MANTENER LLAMADA API EXACTA
      const companiesData = await apiRequest('/api/companies')
      
      companies.value = companiesData
      
      // ✅ PRESERVAR CACHE STRUCTURE
      appStore.cache.companies = companiesData
      appStore.cache.lastUpdate.companies = Date.now()
      
      // ✅ MANTENER LOGGING EXACTO
      appStore.addToLog('Companies loaded successfully', 'info')
      console.log('✅ Companies loaded:', companiesData.length)
      
      return companies.value
      
    } catch (error) {
      companiesError.value = error.message
      appStore.addToLog(`Error loading companies: ${error.message}`, 'error')
      appStore.showNotification('Error loading companies', 'error')
      throw error
    } finally {
      isLoadingCompanies.value = false
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
      await loadEnterpriseCompanies() // Recargar lista
      
      return response
      
    } catch (error) {
      appStore.showNotification(`Error creating company: ${error.message}`, 'error')
      throw error
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
    }
  })
  
  // ============================================================================
  // RETURN PUBLIC API
  // ============================================================================
  
  return {
    // Estado
    companies,
    isLoadingCompanies,
    companiesError,
    companiesStatus,
    lastStatusUpdate,
    enterpriseCompanies,
    isLoadingEnterprise,
    enterpriseError,
    
    // Computed
    availableCompanies,
    currentCompany,
    companiesWithStatus,
    
    // Acciones públicas
    loadCompanies,
    handleCompanyChange,
    validateCompanySelection,
    loadCompaniesStatus,
    reloadCompaniesConfig,
    loadEnterpriseCompanies,
    createEnterpriseCompany
  }
})
