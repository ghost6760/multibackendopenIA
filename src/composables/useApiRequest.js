// composables/useApiRequest.js
// Composable para manejar peticiones API - MIGRACIÓN EXACTA desde script.js
// CRÍTICO: Mantener comportamiento idéntico para preservar compatibilidad

import { ref } from 'vue'
import { useAppStore } from '@/stores/app'

// ============================================================================
// VARIABLE GLOBAL PARA API KEY ADMINISTRATIVA - MIGRADA DEL SCRIPT.JS
// ============================================================================

let ADMIN_API_KEY = null

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
    
    // ✅ Headers por defecto - PRESERVAR EXACTO DEL SCRIPT.JS
    const defaultHeaders = {
      'Content-Type': 'application/json'
    }
    
    // ✅ Agregar company_id si está seleccionado - PRESERVAR EXACTO
    if (appStore.currentCompanyId) {
      defaultHeaders['X-Company-ID'] = appStore.currentCompanyId
    }
    
    // ✅ AGREGAR API KEY ADMINISTRATIVA - MIGRADO DEL SCRIPT.JS
    if (ADMIN_API_KEY) {
      defaultHeaders['X-API-Key'] = ADMIN_API_KEY
    }
    
    // Combinar headers - PRESERVAR EXACTO
    const headers = { ...defaultHeaders, ...(options.headers || {}) }
    
    // Configuración de la petición - PRESERVAR EXACTO
    const config = {
      method: options.method || 'GET',
      headers,
      ...options
    }
    
    // ✅ CORRECCIÓN IMPORTANTE: Asegurar que el body se stringifique correctamente
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
      // ✅ Log de petición - PRESERVAR EXACTO
      console.log(`🔄 API Request: ${config.method} ${endpoint}`)
      appStore.addToLog(`API Request: ${config.method} ${endpoint}`, 'info')
      
      const response = await fetch(url, config)
      
      if (!response.ok) {
        const errorText = await response.text()
        let errorMessage
        
        try {
          const errorJson = JSON.parse(errorText)
          errorMessage = errorJson.error || errorJson.message || `HTTP ${response.status}: ${response.statusText}`
        } catch {
          // 🔧 CORRECCIÓN: Mejorar detección de endpoints inexistentes
          if (response.status === 404) {
            errorMessage = `API endpoint not found: ${endpoint}`
          } else {
            errorMessage = `HTTP ${response.status}: ${response.statusText}`
          }
        }
        
        throw new Error(errorMessage)
      }
      
      const data = await response.json()
      
      // ✅ Log de respuesta exitosa - PRESERVAR EXACTO
      console.log(`✅ API Response: ${config.method} ${endpoint}`, data)
      appStore.addToLog(`API Response: ${endpoint} - Success`, 'info')
      
      return data
      
    } catch (error) {
      // ✅ Log de error - PRESERVAR EXACTO
      console.error(`❌ API Error: ${config.method} ${endpoint}`, error)
      appStore.addToLog(`API Error: ${endpoint} - ${error.message}`, 'error')
      lastError.value = error
      throw error
    } finally {
      isLoading.value = false
    }
  }
  
  // ============================================================================
  // FUNCIONES PARA GESTIÓN DE API KEY ADMINISTRATIVA - MIGRADAS DEL SCRIPT.JS
  // ============================================================================
  
  /**
   * Establecer API Key administrativa - MIGRADO: setAdminApiKey() del script.js
   */
  const setAdminApiKey = (apiKey) => {
    ADMIN_API_KEY = apiKey
    
    // ✅ Mantener compatibilidad global
    if (typeof window !== 'undefined') {
      window.ADMIN_API_KEY = apiKey
    }
    
    console.log('🔑 Admin API Key configured')
  }
  
  /**
   * Obtener API Key administrativa actual
   */
  const getAdminApiKey = () => {
    return ADMIN_API_KEY
  }
  
  /**
   * Limpiar API Key administrativa
   */
  const clearAdminApiKey = () => {
    ADMIN_API_KEY = null
    
    // ✅ Limpiar también de window
    if (typeof window !== 'undefined') {
      window.ADMIN_API_KEY = null
    }
    
    console.log('🗑️ Admin API Key cleared')
  }
  
  /**
   * Verificar si hay API Key configurada
   */
  const hasAdminApiKey = () => {
    return Boolean(ADMIN_API_KEY)
  }
  
  /**
   * Probar API Key - MIGRADO: testApiKey() del script.js
   */
  const testApiKey = async (apiKey = null) => {
    const keyToTest = apiKey || ADMIN_API_KEY
    
    if (!keyToTest) {
      return { success: false, message: 'No API key provided' }
    }
    
    try {
      // ✅ Usar el mismo endpoint que el script.js original
      const response = await apiRequest('/api/admin/test', {
        method: 'GET',
        headers: {
          'X-API-Key': keyToTest
        }
      })
      
      if (response.status === 'success' || response.authenticated === true) {
        return { success: true, message: 'API Key válida' }
      } else {
        return { success: false, message: 'API Key inválida' }
      }
      
    } catch (error) {
      // Si el endpoint no existe, hacer validación básica
      if (error.message.includes('404') || error.message.includes('not found')) {
        // Validación básica: API key debe tener formato válido
        const isValid = keyToTest.length >= 16 && typeof keyToTest === 'string'
        return {
          success: isValid,
          message: isValid ? 'API Key válida (validación básica)' : 'API Key inválida'
        }
      }
      
      return { success: false, message: `Error: ${error.message}` }
    }
  }
  
  /**
   * 🔧 FUNCIÓN AGREGADA: apiRequestWithKey - CRÍTICA PARA ENTERPRISE
   * Función helper para requests que requieren API key - MIGRADA DEL SCRIPT.JS
   */
  const apiRequestWithKey = async (endpoint, options = {}) => {
    // 🔧 CORRECCIÓN: Usar misma detección que script.js
    const requiresApiKey = [
      '/api/admin/companies/create',
      '/api/admin/companies/',
      '/api/admin/companies',
      '/api/documents/cleanup'
    ].some(path => endpoint.includes(path)) || 
    // 🔧 NUEVO: Detectar rutas específicas de empresa (GET/PUT /api/admin/companies/{id})
    /^\/api\/admin\/companies\/[^\/]+$/.test(endpoint)

    if (requiresApiKey && !ADMIN_API_KEY && !appStore.adminApiKey) {
      if (appStore.addNotification) {
        appStore.addNotification('Se requiere API key para esta función', 'warning')
      }
      throw new Error('API key requerida')
    }

    // Asegurar que headers siempre sea un objeto válido
    const headers = { 
      'Content-Type': 'application/json',
      ...(options.headers || {})
    }

    // 🔧 CORRECCIÓN CRÍTICA: Usar header exacto del script.js
    if (requiresApiKey && (ADMIN_API_KEY || appStore.adminApiKey)) {
      headers['X-API-Key'] = ADMIN_API_KEY || appStore.adminApiKey  // ✅ MISMO HEADER QUE SCRIPT.JS
      console.log('🔑 API Key added to request:', endpoint)
    }

    // Asegurar stringify del body si es objeto
    let processedOptions = { ...options, headers }

    if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
      processedOptions.body = JSON.stringify(options.body)
    }

    console.log('🌐 API Request with Key:', endpoint, processedOptions)

    return await apiRequest(endpoint, processedOptions)
  }
  
  // ============================================================================
  // WRAPPERS DE CONVENIENCIA - PRESERVAR DEL ARCHIVO ORIGINAL
  // ============================================================================
  
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
      
      if (successMessage && appStore.addNotification) {
        appStore.addNotification(successMessage, 'success')
      }
      
      return result
    } catch (error) {
      if (appStore.addNotification) {
        appStore.addNotification(
          `Error en ${endpoint}: ${error.message}`, 
          'error'
        )
      }
      throw error
    }
  }
  
  /**
   * Request con cache automático
   */
  const apiRequestWithCache = async (endpoint, options = {}, cacheKey = null, maxAge = 300000) => {
    const key = cacheKey || endpoint
    
    // Verificar cache primero (solo para GET requests)
    if ((!options.method || options.method === 'GET') && appStore.isCacheValid && appStore.isCacheValid(key, maxAge)) {
      appStore.addToLog(`Cache hit: ${endpoint}`, 'info')
      return appStore.cache[key]
    }
    
    // Hacer request y guardar en cache
    const result = await apiRequest(endpoint, options)
    
    if ((!options.method || options.method === 'GET') && appStore.updateCache) {
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
  // COMPATIBILIDAD GLOBAL - CRÍTICO PARA MANTENER FUNCIONES DEL SCRIPT.JS
  // ============================================================================
  
  // ✅ Exponer funciones en el ámbito global para mantener compatibilidad
  if (typeof window !== 'undefined') {
    window.apiRequest = apiRequest
    window.setAdminApiKey = setAdminApiKey
    window.getAdminApiKey = getAdminApiKey
    window.clearAdminApiKey = clearAdminApiKey
    window.testApiKey = testApiKey
    window.hasAdminApiKey = hasAdminApiKey
    // 🔧 AGREGAR: Exponer función crítica para enterprise
    window.apiRequestWithKey = apiRequestWithKey
  }
  
  return {
    // ✅ Función principal (debe mantener el mismo nombre y comportamiento)
    apiRequest,
    
    // ✅ Funciones de API Key administrativa - NUEVAS
    setAdminApiKey,
    getAdminApiKey,
    clearAdminApiKey,
    hasAdminApiKey,
    testApiKey,
    
    // 🔧 FUNCIÓN CRÍTICA AGREGADA para enterprise
    apiRequestWithKey,
    
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
