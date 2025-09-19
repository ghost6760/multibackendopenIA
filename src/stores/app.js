// stores/app.js - Store Principal de Pinia CORREGIDO
// Migración de variables globales desde script.js a Vue.js 3 + Pinia

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAppStore = defineStore('app', () => {
  // ============================================================================
  // VARIABLES GLOBALES MIGRADAS DESDE SCRIPT.JS - VALORES EXACTOS
  // ============================================================================
  
  // Configuración API - PRESERVAR VALORES EXACTOS
  const API_BASE_URL = ref(window.location.origin)
  const DEFAULT_COMPANY_ID = ref('benova')
  
  // Estado global principal - MIGRADO DE script.js
  const currentCompanyId = ref('benova') // Valor por defecto como en script.js
  const monitoringInterval = ref(null)
  const systemLog = ref([])
  const adminApiKey = ref(null)
  
  // Cache del sistema - MIGRADO DE script.js
  const cache = ref({
    companies: null,
    systemInfo: null,
    lastUpdate: {}
  })
  
  // Estado de UI
  const activeTab = ref('dashboard')
  const isLoadingOverlay = ref(false)
  const notifications = ref([])
  
  // ============================================================================
  // COMPUTED PROPERTIES
  // ============================================================================
  
  const hasCompanySelected = computed(() => {
    return Boolean(currentCompanyId.value && currentCompanyId.value !== '')
  })
  
  const isMonitoringActive = computed(() => {
    return Boolean(monitoringInterval.value)
  })
  
  const recentLogEntries = computed(() => {
    return systemLog.value.slice(-20).reverse()
  })
  
  const systemStats = computed(() => {
    return {
      totalLogs: systemLog.value.length,
      errorCount: systemLog.value.filter(entry => entry.level === 'error').length,
      warningCount: systemLog.value.filter(entry => entry.level === 'warning').length,
      lastActivity: systemLog.value.length > 0 
        ? systemLog.value[systemLog.value.length - 1].timestamp 
        : null
    }
  })
  
  // ============================================================================
  // ACTIONS - MIGRADAS DESDE FUNCIONES GLOBALES DE SCRIPT.JS
  // ============================================================================
  
  /**
   * Agregar entrada al log del sistema
   * MIGRADO: addToLog() de script.js - PRESERVAR COMPORTAMIENTO EXACTO
   */
  const addToLog = (message, level = 'info') => {
    const timestamp = new Date().toISOString().substring(0, 19).replace('T', ' ')
    const logEntry = {
      timestamp,
      level,
      message,
      id: Date.now() + Math.random() // Para keys de Vue
    }
    
    systemLog.value.push(logEntry)
    
    // Mantener solo los últimos 100 logs - PRESERVAR COMPORTAMIENTO ORIGINAL
    if (systemLog.value.length > 100) {
      systemLog.value.shift()
    }
    
    // Log simple sin crear loops
    console.log(`[${level.toUpperCase()}] ${timestamp}: ${message}`)
  }
  
  /**
   * Limpiar log del sistema
   * MIGRADO: clearSystemLog() de script.js
   */
  const clearSystemLog = () => {
    systemLog.value = []
    addToLog('System log cleared', 'info')
  }
  
  /**
   * Cambiar empresa activa
   * MIGRADO: handleCompanyChange() de script.js - PRESERVAR COMPORTAMIENTO EXACTO
   */
  const setCurrentCompany = (companyId) => {
    if (companyId !== currentCompanyId.value) {
      const previousCompany = currentCompanyId.value
      currentCompanyId.value = companyId
      
      // Limpiar cache relacionado con empresas - PRESERVAR COMPORTAMIENTO
      cache.value.lastUpdate = {}
      
      addToLog(`Company changed: ${previousCompany} → ${companyId}`, 'info')
      
      // Sincronizar con variable global INMEDIATAMENTE
      if (typeof window !== 'undefined') {
        window.currentCompanyId = companyId
      }
    }
  }
  
  /**
   * Gestión del overlay de carga
   * MIGRADO: toggleLoadingOverlay() de script.js
   */
  const setLoadingOverlay = (show) => {
    isLoadingOverlay.value = show
  }
  
  /**
   * Agregar notificación
   * MIGRADO: showNotification() de script.js
   */
  const addNotification = (message, type = 'info', duration = 5000) => {
    const notification = {
      id: Date.now() + Math.random(),
      message,
      type,
      duration,
      timestamp: Date.now()
    }
    
    notifications.value.push(notification)
    
    // Auto-remover después de la duración especificada
    if (duration > 0) {
      setTimeout(() => {
        removeNotification(notification.id)
      }, duration)
    }
    
    return notification.id
  }
  
  /**
   * Remover notificación por ID
   */
  const removeNotification = (notificationId) => {
    const index = notifications.value.findIndex(n => n.id === notificationId)
    if (index > -1) {
      notifications.value.splice(index, 1)
    }
  }
  
  /**
   * Cambiar tab activo
   * MIGRADO: switchTab() de script.js (parte de la lógica) - COMPORTAMIENTO EXACTO
   */
  const setActiveTab = (tabName) => {
    // Validación para tabs que requieren empresa seleccionada - EXACTO DE SCRIPT.JS
    const requiresCompany = ['prompts', 'documents', 'conversations']
    
    if (requiresCompany.includes(tabName) && !currentCompanyId.value) {
      addNotification('⚠️ Por favor selecciona una empresa primero', 'warning')
      addToLog(`Tab switch blocked: ${tabName} requires company selection`, 'warning')
      return false
    }
    
    activeTab.value = tabName
    addToLog(`Switched to tab: ${tabName}`, 'info')
    return true
  }
  
  /**
   * Actualizar cache del sistema
   */
  const updateCache = (key, data) => {
    cache.value[key] = data
    cache.value.lastUpdate[key] = Date.now()
  }
  
  /**
   * Verificar si el cache es válido (no expirado)
   */
  const isCacheValid = (key, maxAge = 300000) => { // 5 minutos por defecto
    const lastUpdate = cache.value.lastUpdate[key]
    if (!lastUpdate) return false
    
    return (Date.now() - lastUpdate) < maxAge
  }
  
  /**
   * Inicializar monitoreo en tiempo real
   * MIGRADO: startRealTimeMonitoring() de script.js
   */
  const startMonitoring = (callback, interval = 30000) => {
    if (monitoringInterval.value) {
      clearInterval(monitoringInterval.value)
    }
    
    monitoringInterval.value = setInterval(callback, interval)
    addToLog('Real-time monitoring started', 'info')
  }
  
  /**
   * Detener monitoreo en tiempo real
   * MIGRADO: stopRealTimeMonitoring() de script.js
   */
  const stopMonitoring = () => {
    if (monitoringInterval.value) {
      clearInterval(monitoringInterval.value)
      monitoringInterval.value = null
      addToLog('Real-time monitoring stopped', 'info')
    }
  }
  
  // ============================================================================
  // SINCRONIZACIÓN CON VARIABLES GLOBALES - SIN WATCHEFFECT PROBLEMÁTICO
  // ============================================================================
  
  /**
   * Sincronizar manualmente con variables globales cuando sea necesario
   * REEMPLAZA el watchEffect problemático
   */
  const syncToGlobal = () => {
    if (typeof window !== 'undefined') {
      window.currentCompanyId = currentCompanyId.value
      window.API_BASE_URL = API_BASE_URL.value
      window.DEFAULT_COMPANY_ID = DEFAULT_COMPANY_ID.value
    }
  }
  
  // ============================================================================
  // CLEANUP AL DESTRUIR EL STORE
  // ============================================================================
  
  const $dispose = () => {
    // Limpiar intervalos activos
    if (monitoringInterval.value) {
      clearInterval(monitoringInterval.value)
    }
    
    // Limpiar variables globales
    if (typeof window !== 'undefined') {
      delete window.currentCompanyId
      delete window.systemLog
      delete window.cache
      delete window.ADMIN_API_KEY
    }
  }
  
  // Sincronizar al crear el store
  syncToGlobal()
  
  // ============================================================================
  // RETURN DEL STORE
  // ============================================================================
  
  return {
    // State
    API_BASE_URL,
    DEFAULT_COMPANY_ID,
    currentCompanyId,
    monitoringInterval,
    systemLog,
    adminApiKey,
    cache,
    activeTab,
    isLoadingOverlay,
    notifications,
    
    // Computed
    hasCompanySelected,
    isMonitoringActive,
    recentLogEntries,
    systemStats,
    
    // Actions
    addToLog,
    clearSystemLog,
    setCurrentCompany,
    setLoadingOverlay,
    addNotification,
    removeNotification,
    setActiveTab,
    updateCache,
    isCacheValid,
    startMonitoring,
    stopMonitoring,
    syncToGlobal,
    $dispose
  }
})
