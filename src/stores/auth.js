// stores/auth.js - Store de Autenticación/API Key Management
// Migración de funcionalidad de API Key desde script.js preservando comportamiento exacto

import { defineStore } from 'pinia'
import { ref, computed, watchEffect } from 'vue'
import { useApiRequest } from '@/composables/useApiRequest'
import { useAppStore } from './app'

export const useAuthStore = defineStore('auth', () => {
  // ============================================================================
  // ESTADO DE AUTENTICACIÓN - MIGRADO DE SCRIPT.JS
  // ============================================================================
  
  const { apiRequest } = useApiRequest()
  const appStore = useAppStore()
  
  // Estado de API Key - PRESERVAR VARIABLE GLOBAL EXACTA
  const adminApiKey = ref(null)
  const apiKeyStatus = ref('not-configured') // 'not-configured', 'valid', 'invalid', 'testing'
  const lastApiKeyTest = ref(null)
  const apiKeyError = ref(null)
  
  // Estado de modal de API Key
  const isApiKeyModalVisible = ref(false)
  const isTestingApiKey = ref(false)
  
  // ============================================================================
  // COMPUTED PROPERTIES
  // ============================================================================
  
  const hasApiKey = computed(() => {
    return Boolean(adminApiKey.value && adminApiKey.value.length > 0)
  })
  
  const isApiKeyValid = computed(() => {
    return apiKeyStatus.value === 'valid'
  })
  
  const apiKeyStatusText = computed(() => {
    switch (apiKeyStatus.value) {
      case 'not-configured':
        return 'API Key requerida'
      case 'valid':
        return 'API Key válida'
      case 'invalid':
        return 'API Key inválida'
      case 'testing':
        return 'Verificando...'
      default:
        return 'Desconocido'
    }
  })
  
  const apiKeyStatusClass = computed(() => {
    switch (apiKeyStatus.value) {
      case 'valid':
        return 'success'
      case 'invalid':
        return 'error'
      case 'testing':
        return 'warning'
      default:
        return 'not-configured'
    }
  })
  
  // ============================================================================
  // ACCIONES - PRESERVAR FUNCIONES EXACTAS DE SCRIPT.JS
  // ============================================================================
  
  /**
   * Mostrar modal de API Key - MANTENER FUNCIÓN EXACTA
   */
  const showApiKeyModal = () => {
    console.log('🔑 Showing API Key modal...')
    isApiKeyModalVisible.value = true
    apiKeyError.value = null
  }
  
  /**
   * Cerrar modal de API Key - MANTENER FUNCIÓN EXACTA
   */
  const closeApiKeyModal = () => {
    console.log('🔑 Closing API Key modal...')
    isApiKeyModalVisible.value = false
    apiKeyError.value = null
  }
  
  /**
   * Guardar API Key - PRESERVAR LÓGICA EXACTA DE SCRIPT.JS
   * @param {string} apiKey - Nueva API key
   */
  const saveApiKey = async (apiKey) => {
    try {
      console.log('🔑 Saving API key...')
      
      if (!apiKey || apiKey.trim().length === 0) {
        throw new Error('API key cannot be empty')
      }
      
      // ✅ ALMACENAR API KEY
      adminApiKey.value = apiKey.trim()
      apiKeyStatus.value = 'testing'
      
      // ✅ PROBAR LA API KEY INMEDIATAMENTE
      const isValid = await testApiKey()
      
      if (isValid) {
        // ✅ MANTENER COMPORTAMIENTO DE ÉXITO
        appStore.showNotification('✅ API key configurada correctamente', 'success')
        closeApiKeyModal()
        
        // ✅ ACTUALIZAR LOG COMO EN EL ORIGINAL
        appStore.addToLog('API key configured successfully', 'info')
        
      } else {
        // ✅ MANTENER COMPORTAMIENTO DE ERROR
        adminApiKey.value = null
        apiKeyStatus.value = 'invalid'
        throw new Error('Invalid API key')
      }
      
    } catch (error) {
      console.error('❌ Error saving API key:', error)
      apiKeyError.value = error.message
      apiKeyStatus.value = 'invalid'
      appStore.showNotification(`Error: ${error.message}`, 'error')
      throw error
    }
  }
  
  /**
   * Probar API Key - MANTENER FUNCIÓN EXACTA DE SCRIPT.JS
   * @returns {boolean} True si la API key es válida
   */
  const testApiKey = async () => {
    console.log('🔑 Testing API key...')
    console.log('🔑 Current API key:', adminApiKey.value ? `SET (length: ${adminApiKey.value.length})` : 'NOT SET')
    
    if (!adminApiKey.value) {
      appStore.showNotification('Primero configura una API key', 'warning')
      showApiKeyModal()
      return false
    }
    
    try {
      isTestingApiKey.value = true
      apiKeyStatus.value = 'testing'
      
      console.log('🔑 Making test request to /api/admin/companies')
      
      // ✅ MANTENER LLAMADA DE TEST EXACTA
      const response = await apiRequestWithKey('/api/admin/companies')
      
      console.log('✅ API key test successful:', response)
      
      // ✅ ACTUALIZAR ESTADO DE ÉXITO
      apiKeyStatus.value = 'valid'
      lastApiKeyTest.value = new Date().toISOString()
      apiKeyError.value = null
      
      appStore.showNotification('✅ API key válida', 'success')
      
      return true
      
    } catch (error) {
      console.error('❌ API key test failed:', error)
      
      // ✅ MANTENER LÓGICA DE ERROR EXACTA
      if (error.message.includes('401') || error.message.includes('Invalid API key')) {
        appStore.showNotification('❌ API key inválida', 'error')
        adminApiKey.value = null
        apiKeyStatus.value = 'invalid'
        showApiKeyModal()
      } else {
        appStore.showNotification('Error probando API key: ' + error.message, 'error')
        apiKeyStatus.value = 'invalid'
      }
      
      apiKeyError.value = error.message
      return false
      
    } finally {
      isTestingApiKey.value = false
    }
  }
  
  /**
   * Realizar request con API Key - FUNCIÓN AUXILIAR
   * @param {string} endpoint - Endpoint de la API
   * @param {object} options - Opciones del request
   * @returns {Promise} Response de la API
   */
  const apiRequestWithKey = async (endpoint, options = {}) => {
    if (!adminApiKey.value) {
      throw new Error('API key required')
    }
    
    // ✅ PRESERVAR FORMATO DE HEADERS EXACTO
    const processedOptions = {
      ...options,
      headers: {
        'X-API-Key': adminApiKey.value,
        'Content-Type': 'application/json',
        ...options.headers
      }
    }
    
    // ✅ MANTENER LÓGICA DE BODY PROCESSING
    if (options.body && !(options.body instanceof FormData)) {
      processedOptions.body = JSON.stringify(options.body)
    }
    
    console.log('🌐 API Request with Key:', endpoint, processedOptions)
    
    return await apiRequest(endpoint, processedOptions)
  }
  
  /**
   * Actualizar estado visual de API Key - MANTENER FUNCIÓN EXACTA
   */
  const updateApiKeyStatus = () => {
    // Esta función actualiza el estado visual del componente
    // El estado reactivo se actualiza automáticamente en Vue
    console.log('🔑 API Key status updated:', apiKeyStatus.value)
  }
  
  /**
   * Limpiar API Key
   */
  const clearApiKey = () => {
    adminApiKey.value = null
    apiKeyStatus.value = 'not-configured'
    lastApiKeyTest.value = null
    apiKeyError.value = null
    
    appStore.addToLog('API key cleared', 'info')
    appStore.showNotification('API key removed', 'warning')
  }
  
  /**
   * Verificar si API Key es requerida para una operación
   * @param {string} operation - Nombre de la operación
   * @returns {boolean} True si requiere API key
   */
  const requiresApiKey = (operation) => {
    const operationsRequiringApiKey = [
      'enterprise',
      'admin',
      'create-company',
      'edit-company',
      'delete-company',
      'system-diagnostics',
      'migrate-data'
    ]
    
    return operationsRequiringApiKey.includes(operation)
  }
  
  /**
   * Verificar y solicitar API Key si es necesaria
   * @param {string} operation - Operación a realizar
   * @returns {boolean} True si puede continuar
   */
  const checkApiKeyForOperation = async (operation) => {
    if (!requiresApiKey(operation)) {
      return true
    }
    
    if (!hasApiKey.value || !isApiKeyValid.value) {
      appStore.showNotification('Esta operación requiere una API key válida', 'warning')
      showApiKeyModal()
      return false
    }
    
    return true
  }
  
  // ============================================================================
  // FUNCIONES DE INICIALIZACIÓN
  // ============================================================================
  
  /**
   * Inicializar estado de API Key al cargar la aplicación
   */
  const initializeApiKeyState = () => {
    // Verificar si hay una API key guardada (en un entorno real, podría ser localStorage)
    // Por ahora, inicializar como no configurada
    
    console.log('🔑 Initializing API key state...')
    
    // Actualizar estado después de un breve delay para que se cargue el DOM
    setTimeout(() => {
      updateApiKeyStatus()
    }, 500)
  }
  
  // ============================================================================
  // WATCHERS PARA COMPATIBILIDAD GLOBAL
  // ============================================================================
  
  // ✅ MANTENER VARIABLE GLOBAL PARA COMPATIBILIDAD
  watchEffect(() => {
    if (typeof window !== 'undefined') {
      window.ADMIN_API_KEY = adminApiKey.value
    }
  })
  
  // Sync con appStore
  watchEffect(() => {
    appStore.adminApiKey = adminApiKey.value
  })
  
  // ============================================================================
  // RETURN PUBLIC API
  // ============================================================================
  
  return {
    // Estado reactivo
    adminApiKey,
    apiKeyStatus,
    lastApiKeyTest,
    apiKeyError,
    isApiKeyModalVisible,
    isTestingApiKey,
    
    // Computed properties
    hasApiKey,
    isApiKeyValid,
    apiKeyStatusText,
    apiKeyStatusClass,
    
    // Acciones principales
    showApiKeyModal,
    closeApiKeyModal,
    saveApiKey,
    testApiKey,
    clearApiKey,
    
    // Utilidades
    apiRequestWithKey,
    updateApiKeyStatus,
    requiresApiKey,
    checkApiKeyForOperation,
    initializeApiKeyState
  }
})
