// composables/useApiRequest.js - CORREGIDO
// 🔧 FIX: apiRequestWithKey debe funcionar exactamente como en script.js

import { ref } from 'vue'
import { useAppStore } from '@/stores/app'

export const useApiRequest = () => {
  const appStore = useAppStore()
  const isLoading = ref(false)
  const lastError = ref(null)
  
  /**
   * 🔧 FUNCIÓN PRINCIPAL CORREGIDA - apiRequest
   * PRESERVAR: Comportamiento exacto del script.js original
   */
  const apiRequest = async (endpoint, options = {}) => {
    const url = `${appStore.API_BASE_URL}${endpoint}`
    
    // Headers por defecto - PRESERVAR EXACTO DEL SCRIPT.JS
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
    
    // 🔧 CORRECCIÓN IMPORTANTE: Manejo del body exacto como script.js
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
          errorMessage = errorText || `HTTP ${response.status}: ${response.statusText}`
        }
        
        throw new Error(errorMessage)
      }
      
      const data = await response.json()
      
      // Log de respuesta exitosa - PRESERVAR EXACTO
      console.log(`✅ API Response: ${config.method} ${endpoint}`, data)
      appStore.addToLog(`API Response: ${endpoint} - Success`, 'info')
      
      return data
      
    } catch (error) {
      // Log de error - PRESERVAR EXACTO
      console.error(`❌ API Error: ${config.method} ${endpoint}`, error)
      appStore.addToLog(`API Error: ${endpoint} - ${error.message}`, 'error')
      lastError.value = error
      throw error
    } finally {
      isLoading.value = false
    }
  }
  
  /**
   * 🔧 FUNCIÓN CRÍTICA CORREGIDA - apiRequestWithKey
   * DEBE funcionar exactamente igual que en script.js original
   */
  const apiRequestWithKey = async (endpoint, options = {}) => {
    console.log('🔑 [apiRequestWithKey] Called with:', { endpoint, hasOptions: !!options }) // DEBUG
    
    // 🔧 FIX 1: Detectar correctamente endpoints que requieren API key
    const requiresApiKey = [
      '/api/admin/companies/create',
      '/api/admin/companies/', 
      '/api/admin/companies',
      '/api/admin/prompts',
      '/api/admin/test',
      '/api/admin/config',
      '/api/admin/diagnostics',
      '/api/documents/cleanup'
    ].some(path => endpoint.includes(path)) || 
    // Detectar rutas específicas de empresa (GET/PUT/DELETE /api/admin/companies/{id})
    /^\/api\/admin\/companies\/[^\/]+/.test(endpoint) ||
    // Detectar rutas de admin en general
    endpoint.startsWith('/api/admin/')
    
    console.log('🔑 [apiRequestWithKey] Requires API key:', requiresApiKey) // DEBUG
    console.log('🔑 [apiRequestWithKey] Available API key:', !!appStore.adminApiKey) // DEBUG
    
    // 🔧 FIX 2: Verificación estricta de API key para operaciones que la requieren
    if (requiresApiKey && !appStore.adminApiKey) {
      const error = new Error('API key requerida para esta operación')
      console.error('❌ [apiRequestWithKey] No API key available') // DEBUG
      throw error
    }
    
    // 🔧 FIX 3: Preparar headers de manera robusta
    const processedOptions = { ...options }
    
    // Asegurar que headers siempre sea un objeto válido
    processedOptions.headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    }
    
    // 🔧 FIX 4: Agregar API key de manera consistente
    if (requiresApiKey && appStore.adminApiKey) {
      processedOptions.headers['X-API-Key'] = appStore.adminApiKey
      console.log('🔑 [apiRequestWithKey] API key added to headers') // DEBUG
    }
    
    console.log('🌐 [apiRequestWithKey] Final request:', {
      endpoint,
      method: processedOptions.method || 'GET',
      hasApiKey: !!processedOptions.headers['X-API-Key'],
      hasCompanyId: !!processedOptions.headers['X-Company-ID']
    }) // DEBUG
    
    // 🔧 FIX 5: Llamar a apiRequest con opciones procesadas
    return await apiRequest(endpoint, processedOptions)
  }
  
  /**
   * 🔧 NUEVA: Función para verificar si un endpoint requiere API key
   */
  const requiresApiKey = (endpoint) => {
    const adminEndpoints = [
      '/api/admin/',
      '/api/documents/cleanup'
    ]
    
    return adminEndpoints.some(path => endpoint.includes(path))
  }
  
  /**
   * 🔧 NUEVA: Función para verificar disponibilidad de API key
   */
  const hasValidApiKey = () => {
    return Boolean(appStore.adminApiKey && appStore.adminApiKey.length > 10)
  }
  
  /**
   * 🔧 NUEVA: Wrapper para requests que requieren API key con validación previa
   */
  const secureApiRequest = async (endpoint, options = {}) => {
    if (requiresApiKey(endpoint) && !hasValidApiKey()) {
      // Emitir evento para mostrar modal de API key
      if (typeof window !== 'undefined' && window.dispatchEvent) {
        window.dispatchEvent(new CustomEvent('show-api-key-modal'))
      }
      throw new Error('API key requerida. Configure su API key para continuar.')
    }
    
    return await apiRequestWithKey(endpoint, options)
  }
  
  // ============================================================================
  // WRAPPERS DE CONVENIENCIA
  // ============================================================================
  
  const get = async (endpoint, options = {}) => {
    return apiRequest(endpoint, { ...options, method: 'GET' })
  }
  
  const post = async (endpoint, body, options = {}) => {
    return apiRequest(endpoint, { ...options, method: 'POST', body })
  }
  
  const put = async (endpoint, body, options = {}) => {
    return apiRequest(endpoint, { ...options, method: 'PUT', body })
  }
  
  const del = async (endpoint, options = {}) => {
    return apiRequest(endpoint, { ...options, method: 'DELETE' })
  }
  
  const patch = async (endpoint, body, options = {}) => {
    return apiRequest(endpoint, { ...options, method: 'PATCH', body })
  }
  
  // ============================================================================
  // WRAPPERS SEGUROS (CON API KEY)
  // ============================================================================
  
  const secureGet = async (endpoint, options = {}) => {
    return secureApiRequest(endpoint, { ...options, method: 'GET' })
  }
  
  const securePost = async (endpoint, body, options = {}) => {
    return secureApiRequest(endpoint, { ...options, method: 'POST', body })
  }
  
  const securePut = async (endpoint, body, options = {}) => {
    return secureApiRequest(endpoint, { ...options, method: 'PUT', body })
  }
  
  const secureDel = async (endpoint, options = {}) => {
    return secureApiRequest(endpoint, { ...options, method: 'DELETE' })
  }
  
  // ============================================================================
  // COMPATIBILIDAD GLOBAL - CRÍTICO PARA MANTENER FUNCIONES DEL SCRIPT.JS
  // ============================================================================
  
  // Exponer funciones en el ámbito global para mantener compatibilidad
  if (typeof window !== 'undefined') {
    window.apiRequest = apiRequest
    window.apiRequestWithKey = apiRequestWithKey
  }
  
  return {
    // 🔧 FUNCIONES PRINCIPALES CORREGIDAS
    apiRequest,
    apiRequestWithKey,
    
    // 🔧 NUEVAS funciones de validación
    requiresApiKey,
    hasValidApiKey,
    secureApiRequest,
    
    // Wrappers de conveniencia
    get,
    post,
    put,
    del,
    patch,
    
    // Wrappers seguros
    secureGet,
    securePost,
    securePut,
    secureDel,
    
    // Estado reactivo
    isLoading,
    lastError
  }
}
