// services/api.js - Servicio API para Vue.js 3
// Wrapper que preserva la función apiRequest exacta de script.js

import { ref } from 'vue'

// ============================================================================
// CONFIGURACIÓN API - PRESERVAR VALORES EXACTOS DE SCRIPT.JS
// ============================================================================

const API_BASE_URL = window.location.origin
const DEFAULT_COMPANY_ID = 'benova'

// Estado global para compatibilidad
const currentCompanyId = ref(DEFAULT_COMPANY_ID)

// ============================================================================
// FUNCIÓN apiRequest EXACTA - NO MODIFICAR
// ============================================================================

/**
 * Función apiRequest preservada exactamente desde script.js
 * CRÍTICO: NO cambiar ningún comportamiento, header, formato, etc.
 * @param {string} endpoint - Endpoint de la API (ej: '/api/companies')
 * @param {object} options - Opciones de fetch (method, body, headers, etc.)
 * @returns {Promise<any>} - Response parseado como JSON
 */
export async function apiRequest(endpoint, options = {}) {
  try {
    // ✅ CONSTRUIR URL EXACTA COMO EN SCRIPT.JS
    const url = `${API_BASE_URL}${endpoint}`
    
    // ✅ HEADERS POR DEFECTO EXACTOS
    const defaultHeaders = {
      'Content-Type': 'application/json'
    }
    
    // ✅ AGREGAR COMPANY ID SI EXISTE - LÓGICA EXACTA
    if (currentCompanyId.value) {
      defaultHeaders['X-Company-ID'] = currentCompanyId.value
    }
    
    // ✅ MERGE HEADERS PRESERVANDO COMPORTAMIENTO
    const headers = {
      ...defaultHeaders,
      ...options.headers
    }
    
    // ✅ CONFIGURACIÓN DE FETCH EXACTA
    const config = {
      method: 'GET', // Default method
      ...options,
      headers
    }
    
    // ✅ CONVERTIR BODY A JSON SI NO ES FormData - LÓGICA EXACTA
    if (config.body && !(config.body instanceof FormData) && typeof config.body !== 'string') {
      config.body = JSON.stringify(config.body)
    }
    
    // ✅ LOG PARA DEBUG - MANTENER FORMATO
    console.log(`🌐 API Request: ${config.method} ${url}`, {
      headers: config.headers,
      body: config.body ? (config.body instanceof FormData ? '[FormData]' : config.body) : undefined
    })
    
    // ✅ REALIZAR FETCH
    const response = await fetch(url, config)
    
    // ✅ LOG DE RESPONSE - MANTENER FORMATO
    console.log(`📡 API Response: ${response.status} ${response.statusText}`)
    
    // ✅ MANEJAR ERRORES HTTP - LÓGICA EXACTA
    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`
      
      try {
        // Intentar parsear error como JSON
        const errorData = await response.json()
        if (errorData.error) {
          errorMessage = errorData.error
        } else if (errorData.message) {
          errorMessage = errorData.message
        }
      } catch (parseError) {
        // Si no es JSON, usar texto plano
        try {
          const errorText = await response.text()
          if (errorText) {
            errorMessage = errorText
          }
        } catch (textError) {
          // Mantener mensaje original si no se puede parsear
        }
      }
      
      console.error('❌ API Error:', errorMessage)
      throw new Error(errorMessage)
    }
    
    // ✅ PARSEAR RESPONSE - MANEJAR DIFERENTES CONTENT TYPES
    let data
    const contentType = response.headers.get('content-type')
    
    if (contentType && contentType.includes('application/json')) {
      data = await response.json()
    } else {
      data = await response.text()
    }
    
    // ✅ LOG SUCCESS - MANTENER FORMATO
    console.log('✅ API Success:', {
      endpoint,
      method: config.method,
      responseType: typeof data,
      dataLength: typeof data === 'string' ? data.length : Object.keys(data || {}).length
    })
    
    return data
    
  } catch (error) {
    // ✅ LOG ERROR - MANTENER FORMATO
    console.error('❌ API Request Failed:', {
      endpoint,
      error: error.message,
      stack: error.stack
    })
    
    // Re-throw para mantener comportamiento exacto
    throw error
  }
}

// ============================================================================
// COMPOSABLE PARA USO EN COMPONENTES VUE
// ============================================================================

/**
 * Composable para usar apiRequest en componentes Vue
 * @returns {object} Objeto con apiRequest y utilidades
 */
export function useApiRequest() {
  // ✅ EXPONER FUNCIÓN EXACTA
  const apiRequestFn = apiRequest
  
  // Estado reactivo para loading y errores
  const isLoading = ref(false)
  const lastError = ref(null)
  const lastResponse = ref(null)
  
  /**
   * Wrapper reactivo de apiRequest
   * @param {string} endpoint - Endpoint de la API
   * @param {object} options - Opciones de fetch
   * @returns {Promise<any>} Response de la API
   */
  const makeRequest = async (endpoint, options = {}) => {
    try {
      isLoading.value = true
      lastError.value = null
      
      const response = await apiRequest(endpoint, options)
      
      lastResponse.value = response
      return response
      
    } catch (error) {
      lastError.value = error
      throw error
    } finally {
      isLoading.value = false
    }
  }
  
  /**
   * Request con retry automático
   * @param {string} endpoint - Endpoint de la API
   * @param {object} options - Opciones de fetch
   * @param {number} maxRetries - Máximo número de reintentos
   * @returns {Promise<any>} Response de la API
   */
  const makeRequestWithRetry = async (endpoint, options = {}, maxRetries = 3) => {
    let lastError
    
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        return await makeRequest(endpoint, options)
      } catch (error) {
        lastError = error
        
        if (attempt === maxRetries) {
          throw error
        }
        
        // Wait before retry (exponential backoff)
        const delay = Math.min(1000 * Math.pow(2, attempt - 1), 5000)
        console.log(`🔄 Retrying API request (${attempt}/${maxRetries}) after ${delay}ms...`)
        await new Promise(resolve => setTimeout(resolve, delay))
      }
    }
    
    throw lastError
  }
  
  return {
    // ✅ FUNCIÓN ORIGINAL EXACTA
    apiRequest: apiRequestFn,
    
    // Versiones reactivas
    makeRequest,
    makeRequestWithRetry,
    
    // Estado reactivo
    isLoading,
    lastError,
    lastResponse,
    
    // Utilidades
    currentCompanyId
  }
}

// ============================================================================
// FUNCIONES DE UTILIDAD PARA COMPATIBILIDAD
// ============================================================================

/**
 * Cambiar empresa activa globalmente
 * @param {string} companyId - ID de la empresa
 */
export function setCurrentCompany(companyId) {
  currentCompanyId.value = companyId
  
  // ✅ MANTENER COMPATIBILIDAD CON VARIABLE GLOBAL
  if (typeof window !== 'undefined') {
    window.currentCompanyId = companyId
  }
  
  console.log('🏢 Current company changed to:', companyId)
}

/**
 * Obtener empresa activa
 * @returns {string} ID de la empresa actual
 */
export function getCurrentCompany() {
  return currentCompanyId.value
}

/**
 * Construir endpoint con parámetros
 * @param {string} baseEndpoint - Endpoint base
 * @param {object} params - Parámetros para URL
 * @returns {string} Endpoint con parámetros
 */
export function buildEndpoint(baseEndpoint, params = {}) {
  let endpoint = baseEndpoint
  
  // Reemplazar parámetros de path (ej: /api/users/:id)
  Object.entries(params).forEach(([key, value]) => {
    endpoint = endpoint.replace(`:${key}`, encodeURIComponent(value))
  })
  
  return endpoint
}

/**
 * Construir query string
 * @param {object} queryParams - Parámetros de query
 * @returns {string} Query string
 */
export function buildQueryString(queryParams = {}) {
  const params = new URLSearchParams()
  
  Object.entries(queryParams).forEach(([key, value]) => {
    if (value !== null && value !== undefined) {
      params.append(key, String(value))
    }
  })
  
  const queryString = params.toString()
  return queryString ? `?${queryString}` : ''
}

// ============================================================================
// EXPORTACIÓN PARA COMPATIBILIDAD GLOBAL
// ============================================================================

// ✅ EXPONER FUNCIÓN GLOBALMENTE PARA COMPATIBILIDAD
if (typeof window !== 'undefined') {
  window.apiRequest = apiRequest
  window.currentCompanyId = currentCompanyId.value
}

// ============================================================================
// CONFIGURACIÓN POR DEFECTO EXPORTADA
// ============================================================================

export default {
  apiRequest,
  useApiRequest,
  setCurrentCompany,
  getCurrentCompany,
  buildEndpoint,
  buildQueryString,
  API_BASE_URL,
  DEFAULT_COMPANY_ID
}
