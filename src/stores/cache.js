// stores/cache.js - Store de Cache para Pinia  
// Migración del sistema de cache desde script.js preservando estructura exacta

import { defineStore } from 'pinia'
import { ref, computed, watchEffect } from 'vue'

export const useCacheStore = defineStore('cache', () => {
  // ============================================================================
  // ESTADO DE CACHE - MIGRADO EXACTO DE SCRIPT.JS
  // ============================================================================
  
  // ✅ PRESERVAR ESTRUCTURA EXACTA DEL CACHE ORIGINAL
  const cache = ref({
    companies: null,
    systemInfo: null,
    lastUpdate: {}
  })
  
  // Estados de carga para cada tipo de cache
  const loadingStates = ref({
    companies: false,
    systemInfo: false,
    documents: false,
    conversations: false
  })
  
  // Configuración de cache
  const cacheConfig = ref({
    defaultTTL: 5 * 60 * 1000, // 5 minutos en ms
    maxAge: {
      companies: 10 * 60 * 1000, // 10 minutos
      systemInfo: 2 * 60 * 1000,  // 2 minutos
      documents: 30 * 1000,       // 30 segundos
      conversations: 30 * 1000    // 30 segundos
    }
  })
  
  // ============================================================================
  // COMPUTED PROPERTIES
  // ============================================================================
  
  const isCacheValid = computed(() => (cacheKey) => {
    const lastUpdate = cache.value.lastUpdate[cacheKey]
    if (!lastUpdate) return false
    
    const maxAge = cacheConfig.value.maxAge[cacheKey] || cacheConfig.value.defaultTTL
    return (Date.now() - lastUpdate) < maxAge
  })
  
  const cacheStats = computed(() => {
    const stats = {
      totalKeys: Object.keys(cache.value.lastUpdate).length,
      validKeys: 0,
      expiredKeys: 0,
      size: JSON.stringify(cache.value).length
    }
    
    Object.keys(cache.value.lastUpdate).forEach(key => {
      if (isCacheValid.value(key)) {
        stats.validKeys++
      } else {
        stats.expiredKeys++
      }
    })
    
    return stats
  })
  
  const allCacheKeys = computed(() => {
    return Object.keys(cache.value.lastUpdate).map(key => ({
      key,
      lastUpdate: cache.value.lastUpdate[key],
      valid: isCacheValid.value(key),
      age: Date.now() - cache.value.lastUpdate[key]
    }))
  })
  
  // ============================================================================
  // ACCIONES DE CACHE - PRESERVAR FUNCIONALIDAD EXACTA
  // ============================================================================
  
  /**
   * Obtener dato del cache
   * @param {string} key - Clave del cache
   * @returns {any} Dato cached o null si no existe/expired
   */
  const getCacheData = (key) => {
    try {
      // ✅ VERIFICAR SI EXISTE EN CACHE
      if (!cache.value.hasOwnProperty(key)) {
        console.log(`📦 Cache miss: ${key} (not found)`)
        return null
      }
      
      // ✅ VERIFICAR SI ES VÁLIDO
      if (!isCacheValid.value(key)) {
        console.log(`📦 Cache expired: ${key}`)
        return null
      }
      
      console.log(`📦 Cache hit: ${key}`)
      return cache.value[key]
      
    } catch (error) {
      console.error(`Error getting cache data for ${key}:`, error)
      return null
    }
  }
  
  /**
   * Almacenar dato en cache
   * @param {string} key - Clave del cache
   * @param {any} data - Dato a almacenar
   * @param {number} customTTL - TTL personalizado (opcional)
   */
  const setCacheData = (key, data, customTTL = null) => {
    try {
      // ✅ ALMACENAR DATOS
      cache.value[key] = data
      cache.value.lastUpdate[key] = Date.now()
      
      // ✅ CONFIGURAR TTL PERSONALIZADO SI SE PROPORCIONA
      if (customTTL) {
        const currentConfig = { ...cacheConfig.value.maxAge }
        currentConfig[key] = customTTL
        cacheConfig.value.maxAge = currentConfig
      }
      
      console.log(`📦 Cache stored: ${key}`, {
        dataSize: JSON.stringify(data).length,
        ttl: cacheConfig.value.maxAge[key] || cacheConfig.value.defaultTTL
      })
      
    } catch (error) {
      console.error(`Error setting cache data for ${key}:`, error)
    }
  }
  
  /**
   * Invalidar cache específico
   * @param {string} key - Clave del cache a invalidar
   */
  const invalidateCache = (key) => {
    try {
      if (cache.value.hasOwnProperty(key)) {
        delete cache.value[key]
        delete cache.value.lastUpdate[key]
        console.log(`📦 Cache invalidated: ${key}`)
      }
    } catch (error) {
      console.error(`Error invalidating cache for ${key}:`, error)
    }
  }
  
  /**
   * Limpiar todo el cache
   */
  const clearAllCache = () => {
    try {
      // ✅ PRESERVAR ESTRUCTURA ORIGINAL
      cache.value = {
        companies: null,
        systemInfo: null,
        lastUpdate: {}
      }
      
      console.log('📦 All cache cleared')
      
    } catch (error) {
      console.error('Error clearing cache:', error)
    }
  }
  
  /**
   * Limpiar cache expirado
   */
  const cleanupExpiredCache = () => {
    try {
      let cleanedCount = 0
      
      Object.keys(cache.value.lastUpdate).forEach(key => {
        if (!isCacheValid.value(key)) {
          invalidateCache(key)
          cleanedCount++
        }
      })
      
      console.log(`📦 Cleaned ${cleanedCount} expired cache entries`)
      return cleanedCount
      
    } catch (error) {
      console.error('Error cleaning expired cache:', error)
      return 0
    }
  }
  
  /**
   * Obtener o ejecutar función si cache no válido
   * @param {string} key - Clave del cache
   * @param {Function} fetchFunction - Función para obtener datos frescos
   * @param {number} customTTL - TTL personalizado
   * @returns {Promise<any>} Datos del cache o nuevos datos
   */
  const getOrFetch = async (key, fetchFunction, customTTL = null) => {
    try {
      // ✅ INTENTAR OBTENER DEL CACHE PRIMERO
      const cachedData = getCacheData(key)
      if (cachedData !== null) {
        return cachedData
      }
      
      // ✅ MARCAR COMO LOADING
      loadingStates.value[key] = true
      
      try {
        // ✅ EJECUTAR FUNCIÓN DE FETCH
        const freshData = await fetchFunction()
        
        // ✅ ALMACENAR EN CACHE
        setCacheData(key, freshData, customTTL)
        
        return freshData
        
      } finally {
        loadingStates.value[key] = false
      }
      
    } catch (error) {
      loadingStates.value[key] = false
      console.error(`Error in getOrFetch for ${key}:`, error)
      throw error
    }
  }
  
  /**
   * Precargar datos en cache
   * @param {string} key - Clave del cache
   * @param {Function} fetchFunction - Función para obtener datos
   */
  const preloadCache = async (key, fetchFunction) => {
    try {
      if (!isCacheValid.value(key)) {
        console.log(`📦 Preloading cache: ${key}`)
        await getOrFetch(key, fetchFunction)
      }
    } catch (error) {
      console.error(`Error preloading cache for ${key}:`, error)
    }
  }
  
  /**
   * Refrescar cache forzadamente
   * @param {string} key - Clave del cache
   * @param {Function} fetchFunction - Función para obtener datos frescos
   */
  const refreshCache = async (key, fetchFunction) => {
    try {
      console.log(`📦 Force refreshing cache: ${key}`)
      
      // Invalidar cache existente
      invalidateCache(key)
      
      // Obtener datos frescos
      return await getOrFetch(key, fetchFunction)
      
    } catch (error) {
      console.error(`Error refreshing cache for ${key}:`, error)
      throw error
    }
  }
  
  /**
   * Configurar TTL para un tipo de cache
   * @param {string} key - Tipo de cache
   * @param {number} ttl - Tiempo de vida en ms
   */
  const setCacheTTL = (key, ttl) => {
    cacheConfig.value.maxAge[key] = ttl
    console.log(`📦 Cache TTL updated: ${key} = ${ttl}ms`)
  }
  
  // ============================================================================
  // FUNCIONES DE UTILIDAD
  // ============================================================================
  
  /**
   * Obtener información de estado del cache
   */
  const getCacheInfo = () => {
    return {
      cache: cache.value,
      stats: cacheStats.value,
      config: cacheConfig.value,
      loading: loadingStates.value
    }
  }
  
  /**
   * Exportar datos de cache para debugging
   */
  const exportCacheData = () => {
    return {
      timestamp: Date.now(),
      cache: JSON.parse(JSON.stringify(cache.value)),
      config: JSON.parse(JSON.stringify(cacheConfig.value))
    }
  }
  
  // ============================================================================
  // WATCHERS PARA COMPATIBILIDAD GLOBAL
  // ============================================================================
  
  // ✅ MANTENER VARIABLE GLOBAL CACHE SINCRONIZADA
  watchEffect(() => {
    if (typeof window !== 'undefined') {
      window.cache = cache.value
    }
  })
  
  // Auto-cleanup cada 5 minutos
  if (typeof window !== 'undefined') {
    setInterval(() => {
      cleanupExpiredCache()
    }, 5 * 60 * 1000)
  }
  
  // ============================================================================
  // RETURN PUBLIC API
  // ============================================================================
  
  return {
    // Estado reactivo
    cache,
    loadingStates,
    cacheConfig,
    
    // Computed properties
    isCacheValid,
    cacheStats,
    allCacheKeys,
    
    // Acciones principales
    getCacheData,
    setCacheData,
    invalidateCache,
    clearAllCache,
    cleanupExpiredCache,
    
    // Acciones avanzadas
    getOrFetch,
    preloadCache,
    refreshCache,
    setCacheTTL,
    
    // Utilidades
    getCacheInfo,
    exportCacheData
  }
})
