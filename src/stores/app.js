/**
 * stores/app.js - Store Principal de la Aplicación
 * MIGRADO DE: Variables globales y funciones de script.js
 * PRESERVAR: Estado y comportamiento exacto del sistema original
 * SOPORTE: Notificaciones, SystemLog, Empresas, Tabs, Cache
 */

import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'

export const useAppStore = defineStore('app', () => {
  // ============================================================================
  // ESTADO PRINCIPAL - MIGRADO DESDE SCRIPT.JS
  // ============================================================================

  // Empresa actual - CRÍTICO para prompts
  const currentCompanyId = ref('benova') // Default como en script.js
  const companies = ref([])
  const isLoadingCompanies = ref(false)

  // Sistema de tabs
  const activeTab = ref('dashboard')
  const availableTabs = ref([
    'dashboard', 'documents', 'conversations', 
    'multimedia', 'prompts', 'admin', 'enterprise', 'health'
  ])

  // Loading states
  const isLoadingOverlay = ref(false)
  const loadingStates = ref({})

  // API Key management
  const adminApiKey = ref('')
  const isApiKeyValid = ref(false)

  // ============================================================================
  // SISTEMA DE NOTIFICACIONES - REQUERIDO POR USENOTIFICATIONS
  // ============================================================================

  const notifications = ref([])
  let notificationIdCounter = 0

  /**
   * Agrega una notificación al sistema
   * REQUERIDO POR: useNotifications.js
   */
  const addNotification = (message, type = 'info', duration = 5000) => {
    const id = `notification_${++notificationIdCounter}_${Date.now()}`
    
    const notification = {
      id,
      message,
      type,
      timestamp: Date.now(),
      duration,
      visible: true
    }
    
    notifications.value.push(notification)
    
    // Auto-remove si tiene duración
    if (duration > 0) {
      setTimeout(() => {
        removeNotification(id)
      }, duration)
    }
    
    // También crear notificación DOM para compatibilidad con script.js
    createDOMNotification(message, type, duration)
    
    return id
  }

  /**
   * Remueve una notificación específica
   * REQUERIDO POR: useNotifications.js
   */
  const removeNotification = (notificationId) => {
    const index = notifications.value.findIndex(n => n.id === notificationId)
    if (index > -1) {
      notifications.value.splice(index, 1)
    }
  }

  /**
   * Limpia todas las notificaciones
   */
  const clearAllNotifications = () => {
    notifications.value.splice(0)
  }

  /**
   * Crea notificación DOM para compatibilidad con script.js original
   */
  const createDOMNotification = (message, type, duration) => {
    // Buscar o crear container
    let container = document.getElementById('notificationContainer')
    if (!container) {
      container = document.createElement('div')
      container.id = 'notificationContainer'
      container.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 10000;
        pointer-events: none;
      `
      document.body.appendChild(container)
    }
    
    // Crear notificación
    const notification = document.createElement('div')
    notification.className = `notification notification-${type}`
    notification.textContent = message
    notification.style.cssText = `
      margin-bottom: 10px;
      padding: 12px 20px;
      border-radius: 6px;
      color: white;
      font-weight: 500;
      transform: translateX(400px);
      transition: transform 0.3s ease;
      pointer-events: auto;
      ${getNotificationStyles(type)}
    `
    
    container.appendChild(notification)
    
    // Mostrar con animación
    setTimeout(() => {
      notification.style.transform = 'translateX(0)'
    }, 100)
    
    // Ocultar y remover
    if (duration > 0) {
      setTimeout(() => {
        notification.style.transform = 'translateX(400px)'
        setTimeout(() => {
          if (container.contains(notification)) {
            container.removeChild(notification)
          }
        }, 300)
      }, duration)
    }
  }

  /**
   * Estilos para notificaciones DOM
   */
  const getNotificationStyles = (type) => {
    const styles = {
      info: 'background: linear-gradient(135deg, #4299e1 0%, #3182ce 100%);',
      success: 'background: linear-gradient(135deg, #38a169 0%, #2f855a 100%);',
      warning: 'background: linear-gradient(135deg, #ed8936 0%, #dd6b20 100%);',
      error: 'background: linear-gradient(135deg, #e53e3e 0%, #c53030 100%);'
    }
    return styles[type] || styles.info
  }

  // ============================================================================
  // SISTEMA DE LOG - REQUERIDO POR USESYSTEMLOG
  // ============================================================================

  const systemLog = ref([])
  const maxLogEntries = ref(100)

  /**
   * Agrega entrada al log del sistema
   * REQUERIDO POR: useSystemLog.js y script.js original
   */
  const addToLog = (message, level = 'info') => {
    const timestamp = new Date().toISOString().substring(0, 19).replace('T', ' ')
    const logEntry = {
      id: `log_${Date.now()}_${Math.random()}`,
      timestamp,
      level,
      message,
      fullTimestamp: new Date()
    }
    
    systemLog.value.push(logEntry)
    
    // Mantener límite de entradas
    if (systemLog.value.length > maxLogEntries.value) {
      systemLog.value.shift()
    }
    
    // Console log para debugging
    const consoleMethods = {
      info: 'log',
      warning: 'warn', 
      error: 'error',
      success: 'log'
    }
    const method = consoleMethods[level] || 'log'
    console[method](`[${timestamp}] [${level.toUpperCase()}] ${message}`)
    
    // Actualizar DOM log si existe
    updateDOMLogDisplay()
  }

  /**
   * Actualiza la visualización DOM del log para compatibilidad
   */
  const updateDOMLogDisplay = () => {
    const logContainer = document.getElementById('systemLog')
    if (!logContainer) return
    
    const logHTML = systemLog.value.slice(-20).map(entry => `
      <div class="log-entry log-${entry.level}">
        <span class="log-timestamp">[${entry.timestamp}]</span>
        <span class="log-level">[${entry.level.toUpperCase()}]</span>
        <span class="log-message">${entry.message}</span>
      </div>
    `).join('')
    
    logContainer.innerHTML = logHTML
    logContainer.scrollTop = logContainer.scrollHeight
  }

  /**
   * Limpia el log del sistema
   */
  const clearSystemLog = () => {
    const previousLength = systemLog.value.length
    systemLog.value.splice(0)
    addToLog(`System log cleared (${previousLength} entries removed)`, 'info')
  }

  // ============================================================================
  // GESTIÓN DE EMPRESAS - CRÍTICO PARA PROMPTS
  // ============================================================================

  /**
   * Cambia la empresa actual
   * MIGRADO: changeCompany() de script.js
   */
  const setCurrentCompanyId = (companyId) => {
    if (!companyId) {
      addToLog('Invalid company ID provided', 'error')
      return false
    }
    
    const oldCompanyId = currentCompanyId.value
    currentCompanyId.value = companyId
    
    addToLog(`Company changed from ${oldCompanyId} to ${companyId}`, 'info')
    
    // Actualizar variable global para compatibilidad
    if (typeof window !== 'undefined') {
      window.currentCompanyId = companyId
    }
    
    return true
  }

  /**
   * Obtiene la empresa actual
   */
  const getCurrentCompany = () => {
    return companies.value.find(c => c.id === currentCompanyId.value) || null
  }

  // ============================================================================
  // GESTIÓN DE TABS
  // ============================================================================

  /**
   * Cambia el tab activo
   * MIGRADO: switchTab() de script.js
   */
  const setActiveTab = (tabName) => {
    if (!availableTabs.value.includes(tabName)) {
      addToLog(`Invalid tab name: ${tabName}`, 'error')
      return false
    }
    
    const oldTab = activeTab.value
    activeTab.value = tabName
    
    addToLog(`Tab changed from ${oldTab} to ${tabName}`, 'info')
    
    // Emitir evento para compatibilidad
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('tabChanged', { 
        detail: { tabId: tabName, oldTab }
      }))
    }
    
    return true
  }

  // ============================================================================
  // GESTIÓN DE LOADING STATES
  // ============================================================================

  const setLoadingOverlay = (visible) => {
    isLoadingOverlay.value = visible
  }

  const setLoadingState = (key, loading) => {
    loadingStates.value[key] = loading
  }

  const isLoading = (key) => {
    return loadingStates.value[key] || false
  }

  // ============================================================================
  // GESTIÓN DE CACHE - MIGRADO DESDE SCRIPT.JS
  // ============================================================================

  const cache = ref({
    companies: null,
    systemInfo: null,
    lastUpdate: {},
    prompts: {},
    documents: {},
    conversations: {}
  })

  const setCacheData = (key, data) => {
    cache.value[key] = data
    cache.value.lastUpdate[key] = Date.now()
    addToLog(`Cache updated: ${key}`, 'info')
  }

  const getCacheData = (key) => {
    return cache.value[key]
  }

  const clearCache = (key = null) => {
    if (key) {
      delete cache.value[key]
      delete cache.value.lastUpdate[key]
      addToLog(`Cache cleared: ${key}`, 'info')
    } else {
      cache.value = {
        companies: null,
        systemInfo: null,
        lastUpdate: {},
        prompts: {},
        documents: {},
        conversations: {}
      }
      addToLog('All cache cleared', 'info')
    }
  }

  // ============================================================================
  // COMPUTED PROPERTIES
  // ============================================================================

  const hasCompanySelected = computed(() => {
    return currentCompanyId.value && currentCompanyId.value.trim() !== ''
  })

  const notificationCount = computed(() => {
    return notifications.value.length
  })

  const errorNotificationCount = computed(() => {
    return notifications.value.filter(n => n.type === 'error').length
  })

  const recentSystemErrors = computed(() => {
    return systemLog.value.filter(entry => entry.level === 'error').slice(-5)
  })

  const systemLogCount = computed(() => {
    return systemLog.value.length
  })

  const currentCompanyInfo = computed(() => {
    return getCurrentCompany()
  })

  // ============================================================================
  // WATCHERS
  // ============================================================================

  // Watcher para sincronizar con variables globales
  watch(currentCompanyId, (newId) => {
    if (typeof window !== 'undefined') {
      window.currentCompanyId = newId
    }
  })

  // Watcher para limpiar cache cuando cambie la empresa
  watch(currentCompanyId, (newId, oldId) => {
    if (newId !== oldId) {
      // Limpiar cache específico de empresa
      clearCache('prompts')
      clearCache('documents')
      clearCache('conversations')
    }
  })

  // ============================================================================
  // FUNCIONES DE UTILIDAD
  // ============================================================================

  /**
   * Función helper para notificaciones rápidas
   */
  const showNotification = (message, type = 'info', duration = 5000) => {
    return addNotification(message, type, duration)
  }

  /**
   * Reinicia el estado de la aplicación
   */
  const resetAppState = () => {
    clearAllNotifications()
    clearSystemLog()
    clearCache()
    activeTab.value = 'dashboard'
    addToLog('Application state reset', 'info')
  }

  /**
   * Obtiene el estado completo para debugging
   */
  const getAppState = () => {
    return {
      currentCompanyId: currentCompanyId.value,
      activeTab: activeTab.value,
      hasCompanySelected: hasCompanySelected.value,
      notificationCount: notificationCount.value,
      systemLogCount: systemLogCount.value,
      cache: Object.keys(cache.value).reduce((acc, key) => {
        acc[key] = cache.value[key] ? 'present' : 'null'
        return acc
      }, {})
    }
  }

  // ============================================================================
  // RETURN STORE API
  // ============================================================================

  return {
    // Estado principal
    currentCompanyId,
    companies,
    isLoadingCompanies,
    activeTab,
    availableTabs,
    isLoadingOverlay,
    loadingStates,
    adminApiKey,
    isApiKeyValid,

    // Sistema de notificaciones (REQUERIDO POR useNotifications)
    notifications,
    addNotification,
    removeNotification,
    clearAllNotifications,

    // Sistema de log (REQUERIDO POR useSystemLog)
    systemLog,
    maxLogEntries,
    addToLog,
    clearSystemLog,

    // Gestión de empresas
    setCurrentCompanyId,
    getCurrentCompany,

    // Gestión de tabs
    setActiveTab,

    // Loading states
    setLoadingOverlay,
    setLoadingState,
    isLoading,

    // Cache
    cache,
    setCacheData,
    getCacheData,
    clearCache,

    // Computed properties
    hasCompanySelected,
    notificationCount,
    errorNotificationCount,
    recentSystemErrors,
    systemLogCount,
    currentCompanyInfo,

    // Utilidades
    showNotification,
    resetAppState,
    getAppState
  }
})
