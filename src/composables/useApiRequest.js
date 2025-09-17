// composables/useApiRequest.js
// Composable para manejar peticiones API - MIGRACIÓN EXACTA desde script.js
// CRÍTICO: Mantener comportamiento idéntico para preservar compatibilidad

import { ref } from 'vue'
import { useAppStore } from '@/stores/app'

export const useApiRequest = () => {
  const appStore = useAppStore()
  const isLoading = ref(false)
  const lastError = ref(null)
  
  /**
   * Realiza una petición HTTP con manejo de errores y headers multi-tenant
   * MIGRADO EXACTO: apiRequest() de script.js
   * ⚠️ NO MODIFICAR: Debe mantener comportamiento idéntico
   * 
   * @param {string} endpoint - Endpoint de la API (ej: '/api/companies')
   * @param {Object} options - Opciones de la petición (method, body, headers, etc.)
   * @returns {Promise<any>} - Respuesta de la API
   */
  const apiRequest = async (endpoint, options = {}) => {
    const url = `${appStore.API_BASE_URL}${endpoint}`
    
    // Headers por defecto - PRESERVAR EXACTO
    const defaultHeaders = {
      'Content-Type': 'application/json'
    }
    
    // Agregar company_id si está seleccionado - PRESERVAR EXACTO
    if (appStore.currentCompanyId) {
      defaultHeaders['X-Company-ID'] = appStore.currentCompanyId
    }
    
    // Combinar headers - PRESERVAR EXACTO
    const headers = { ...defaultHeaders, ...(options.headers || {}) }
    
    // Configuración de la petición - PRESERVAR EXACTO
    const config = {
      method: options.method || 'GET',
      headers,
      ...options
    }
    
    // CORRECCIÓN IMPORTANTE: Asegurar que el body se stringifique correctamente
    // PRESERVAR EXACTA LA LÓGICA ORIGINAL
    if (options.body) {
      if (options.body instanceof FormData) {
        // Para FormData, remover Content-Type para que el browser lo maneje
        delete config.headers['Content-Type']
        config.body = options.body
      } else {
        // Para objetos JSON, asegurar stringify
        config.body = typeof options.body === 'string' 
          ? options.body 
          : JSON.stringify(options.body)
      }
    }
    
    // Estado de loading
    isLoading.value = true
    lastError.value = null
    
    try {
      // Log de petición - PRESERVAR EXACTO
      appStore.addToLog(`API Request: ${config.method} ${endpoint}`, 'info')
      
      const response = await fetch(url, config)
      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.message || `HTTP ${response.status}: ${response.statusText}`)
      }
      
      // Log de respuesta exitosa - PRESERVAR EXACTO
      appStore.addToLog(`API Response: ${endpoint} - Success`, 'info')
      return data
      
    } catch (error) {
      // Log de error - PRESERVAR EXACTO
      appStore.addToLog(`API Error: ${endpoint} - ${error.message}`, 'error')
      lastError.value = error
      throw error
    } finally {
      isLoading.value = false
    }
  }
  
  /**
   * Wrapper para GET requests
   */
  const get = async (endpoint, options = {}) => {
    return apiRequest(endpoint, { ...options, method: 'GET' })
  }
  
  /**
   * Wrapper para POST requests
   */
  const post = async (endpoint, body, options = {}) => {
    return apiRequest(endpoint, { ...options, method: 'POST', body })
  }
  
  /**
   * Wrapper para PUT requests
   */
  const put = async (endpoint, body, options = {}) => {
    return apiRequest(endpoint, { ...options, method: 'PUT', body })
  }
  
  /**
   * Wrapper para DELETE requests
   */
  const del = async (endpoint, options = {}) => {
    return apiRequest(endpoint, { ...options, method: 'DELETE' })
  }
  
  /**
   * Wrapper para PATCH requests
   */
  const patch = async (endpoint, body, options = {}) => {
    return apiRequest(endpoint, { ...options, method: 'PATCH', body })
  }
  
  /**
   * Request con manejo automático de loading overlay
   */
  const apiRequestWithOverlay = async (endpoint, options = {}) => {
    appStore.setLoadingOverlay(true)
    try {
      const result = await apiRequest(endpoint, options)
      return result
    } finally {
      appStore.setLoadingOverlay(false)
    }
  }
  
  /**
   * Request con manejo automático de notificaciones de error
   */
  const apiRequestWithNotification = async (endpoint, options = {}, successMessage = null) => {
    try {
      const result = await apiRequest(endpoint, options)
      
      if (successMessage) {
        appStore.addNotification(successMessage, 'success')
      }
      
      return result
    } catch (error) {
      appStore.addNotification(
        `Error en ${endpoint}: ${error.message}`, 
        'error'
      )
      throw error
    }
  }
  
  /**
   * Request con cache automático
   */
  const apiRequestWithCache = async (endpoint, options = {}, cacheKey = null, maxAge = 300000) => {
    const key = cacheKey || endpoint
    
    // Verificar cache primero (solo para GET requests)
    if ((!options.method || options.method === 'GET') && appStore.isCacheValid(key, maxAge)) {
      appStore.addToLog(`Cache hit: ${endpoint}`, 'info')
      return appStore.cache[key]
    }
    
    // Hacer request y guardar en cache
    const result = await apiRequest(endpoint, options)
    
    if (!options.method || options.method === 'GET') {
      appStore.updateCache(key, result)
    }
    
    return result
  }
  
  /**
   * Request con reintentos automáticos
   */
  const apiRequestWithRetry = async (endpoint, options = {}, maxRetries = 3, delay = 1000) => {
    let lastError
    
    for (let i = 0; i <= maxRetries; i++) {
      try {
        const result = await apiRequest(endpoint, options)
        
        if (i > 0) {
          appStore.addToLog(`Request succeeded after ${i} retries: ${endpoint}`, 'info')
        }
        
        return result
      } catch (error) {
        lastError = error
        
        if (i < maxRetries) {
          appStore.addToLog(`Request failed, retrying in ${delay}ms (${i + 1}/${maxRetries}): ${endpoint}`, 'warning')
          await new Promise(resolve => setTimeout(resolve, delay))
          delay *= 2 // Exponential backoff
        }
      }
    }
    
    throw lastError
  }
  
  /**
   * Helper para construir URLs con query parameters
   */
  const buildUrl = (endpoint, params = {}) => {
    const url = new URL(`${appStore.API_BASE_URL}${endpoint}`)
    
    Object.keys(params).forEach(key => {
      if (params[key] !== null && params[key] !== undefined) {
        url.searchParams.append(key, params[key])
      }
    })
    
    return url.toString()
  }
  
  /**
   * Helper para crear FormData desde objeto
   */
  const createFormData = (data) => {
    const formData = new FormData()
    
    Object.keys(data).forEach(key => {
      if (data[key] !== null && data[key] !== undefined) {
        if (data[key] instanceof File || data[key] instanceof Blob) {
          formData.append(key, data[key])
        } else {
          formData.append(key, String(data[key]))
        }
      }
    })
    
    return formData
  }
  
  // ============================================================================
  // COMPATIBILIDAD GLOBAL - CRÍTICO
  // ============================================================================
  
  // Exponer apiRequest en el ámbito global para mantener compatibilidad
  if (typeof window !== 'undefined') {
    window.apiRequest = apiRequest
  }
  
  return {
    // Función principal (debe mantener el mismo nombre y comportamiento)
    apiRequest,
    
    // Wrappers de conveniencia
    get,
    post,
    put,
    del,
    patch,
    
    // Variants con funcionalidad adicional
    apiRequestWithOverlay,
    apiRequestWithNotification,
    apiRequestWithCache,
    apiRequestWithRetry,
    
    // Helpers
    buildUrl,
    createFormData,
    
    // Estado reactivo
    isLoading,
    lastError
  }
}
