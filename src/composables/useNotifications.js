// composables/useNotifications.js
// Sistema de notificaciones - MIGRACIÓN desde script.js showNotification()
// CRÍTICO: Mantener comportamiento idéntico para preservar compatibilidad

import { computed } from 'vue'
import { useAppStore } from '@/stores/app'

export const useNotifications = () => {
  const appStore = useAppStore()
  
  /**
   * Muestra una notificación al usuario
   * MIGRADO EXACTO: showNotification() de script.js
   * ⚠️ NO MODIFICAR: Debe mantener comportamiento idéntico
   * 
   * @param {string} message - Mensaje a mostrar
   * @param {string} type - Tipo: 'info', 'success', 'warning', 'error'
   * @param {number} duration - Duración en ms (0 = no auto-ocultar)
   * @returns {string} ID de la notificación
   */
  const showNotification = (message, type = 'info', duration = 5000) => {
    // Usar el store para mantener el estado
    const notificationId = appStore.addNotification(message, type, duration)
    
    // Log de la notificación para debugging
    appStore.addToLog(`Notification: [${type.toUpperCase()}] ${message}`, 'info')
    
    return notificationId
  }
  
  /**
   * Oculta una notificación específica
   */
  const hideNotification = (notificationId) => {
    appStore.removeNotification(notificationId)
  }
  
  /**
   * Oculta todas las notificaciones
   */
  const clearAllNotifications = () => {
    appStore.notifications.forEach(notification => {
      appStore.removeNotification(notification.id)
    })
  }
  
  /**
   * Shortcuts para tipos específicos de notificaciones
   */
  const notifySuccess = (message, duration = 5000) => {
    return showNotification(message, 'success', duration)
  }
  
  const notifyError = (message, duration = 7000) => {
    return showNotification(message, 'error', duration)
  }
  
  const notifyWarning = (message, duration = 6000) => {
    return showNotification(message, 'warning', duration)
  }
  
  const notifyInfo = (message, duration = 5000) => {
    return showNotification(message, 'info', duration)
  }
  
  /**
   * Notificaciones especiales para operaciones comunes
   */
  const notifyApiError = (endpoint, error, duration = 7000) => {
    const message = `Error en ${endpoint}: ${error.message || error}`
    return showNotification(message, 'error', duration)
  }
  
  const notifyApiSuccess = (operation, duration = 3000) => {
    const message = `${operation} completado exitosamente`
    return showNotification(message, 'success', duration)
  }
  
  const notifyValidationError = (field, message, duration = 5000) => {
    const fullMessage = `${field}: ${message}`
    return showNotification(fullMessage, 'warning', duration)
  }
  
  const notifyCompanyRequired = (duration = 5000) => {
    return showNotification('⚠️ Por favor selecciona una empresa primero', 'warning', duration)
  }
  
  /**
   * Notificación con acción (botón)
   */
  const notifyWithAction = (message, type, actionText, actionCallback, duration = 0) => {
    const notification = {
      message,
      type,
      duration,
      action: {
        text: actionText,
        callback: actionCallback
      }
    }
    
    // Para notificaciones con acción, usar duration 0 por defecto (no auto-ocultar)
    return showNotification(notification.message, type, duration)
  }
  
  /**
   * Notificación de carga/progreso
   */
  const notifyLoading = (message, duration = 0) => {
    return showNotification(`⏳ ${message}`, 'info', duration)
  }
  
  /**
   * Actualizar notificación existente (útil para progreso)
   */
  const updateNotification = (notificationId, newMessage, newType = null) => {
    const notification = appStore.notifications.find(n => n.id === notificationId)
    if (notification) {
      notification.message = newMessage
      if (newType) {
        notification.type = newType
      }
      notification.timestamp = Date.now()
    }
  }
  
  /**
   * Notificación con timeout personalizado y callback
   */
  const notifyWithCallback = (message, type, duration, onShow = null, onHide = null) => {
    const notificationId = showNotification(message, type, duration)
    
    if (onShow) {
      onShow(notificationId)
    }
    
    if (onHide && duration > 0) {
      setTimeout(() => {
        onHide(notificationId)
      }, duration)
    }
    
    return notificationId
  }
  
  // ============================================================================
  // COMPUTED PROPERTIES PARA COMPONENTES
  // ============================================================================
  
  const notifications = computed(() => appStore.notifications)
  
  const hasNotifications = computed(() => appStore.notifications.length > 0)
  
  const errorNotifications = computed(() => 
    appStore.notifications.filter(n => n.type === 'error')
  )
  
  const warningNotifications = computed(() => 
    appStore.notifications.filter(n => n.type === 'warning')
  )
  
  const notificationsByType = computed(() => {
    const grouped = {}
    appStore.notifications.forEach(notification => {
      if (!grouped[notification.type]) {
        grouped[notification.type] = []
      }
      grouped[notification.type].push(notification)
    })
    return grouped
  })
  
  // ============================================================================
  // COMPATIBILIDAD GLOBAL - CRÍTICO
  // ============================================================================
  
  // Exponer showNotification en el ámbito global para mantener compatibilidad
  if (typeof window !== 'undefined') {
    window.showNotification = showNotification
  }
  
  return {
    // Función principal (debe mantener el mismo nombre y comportamiento)
    showNotification,
    
    // Gestión de notificaciones
    hideNotification,
    clearAllNotifications,
    updateNotification,
    
    // Shortcuts por tipo
    notifySuccess,
    notifyError,
    notifyWarning,
    notifyInfo,
    
    // Notificaciones especializadas
    notifyApiError,
    notifyApiSuccess,
    notifyValidationError,
    notifyCompanyRequired,
    notifyLoading,
    notifyWithAction,
    notifyWithCallback,
    
    // Estado reactivo
    notifications,
    hasNotifications,
    errorNotifications,
    warningNotifications,
    notificationsByType
  }
}
