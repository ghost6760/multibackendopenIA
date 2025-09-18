/**
 * useNotifications.js - Sistema de notificaciones corregido
 * MIGRACIÓN desde script.js showNotification()
 * CRÍTICO: Mantener comportamiento idéntico para preservar compatibilidad
 * CORRECCIÓN: Eliminar dependencia circular con store
 */

import { computed } from 'vue'

export const useNotifications = () => {
  
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
    // MÉTODO 1: Usar el store solo si está disponible
    if (typeof window !== 'undefined' && window.useAppStore) {
      try {
        const { useAppStore } = window.useAppStore()
        if (useAppStore && useAppStore.addNotification) {
          return useAppStore.addNotification(message, type, duration)
        }
      } catch (error) {
        console.warn('Store not available, using DOM notifications')
      }
    }
    
    // MÉTODO 2: Fallback - crear notificación DOM directamente
    return createDirectNotification(message, type, duration)
  }
  
  /**
   * Crea notificación DOM directa sin dependencias del store
   * PRESERVAR: Comportamiento idéntico al script.js original
   */
  const createDirectNotification = (message, type, duration) => {
    const notificationId = `notification_${Date.now()}_${Math.random()}`
    
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
    notification.id = notificationId
    notification.style.cssText = `
      margin-bottom: 10px;
      padding: 12px 20px;
      border-radius: 6px;
      color: white;
      font-weight: 500;
      transform: translateX(400px);
      transition: transform 0.3s ease;
      pointer-events: auto;
      min-width: 300px;
      word-wrap: break-word;
      ${getNotificationStyles(type)}
    `
    
    container.appendChild(notification)
    
    // Mostrar con animación
    setTimeout(() => {
      notification.style.transform = 'translateX(0)'
    }, 100)
    
    // Auto-ocultar si tiene duración
    if (duration > 0) {
      setTimeout(() => {
        hideDirectNotification(notificationId)
      }, duration)
    }
    
    // Log a consola
    console.log(`[NOTIFICATION ${type.toUpperCase()}] ${message}`)
    
    return notificationId
  }
  
  /**
   * Oculta notificación directa
   */
  const hideDirectNotification = (notificationId) => {
    const notification = document.getElementById(notificationId)
    if (notification) {
      notification.style.transform = 'translateX(400px)'
      setTimeout(() => {
        notification.remove()
      }, 300)
    }
  }
  
  /**
   * Estilos para notificaciones
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
  
  /**
   * Oculta todas las notificaciones
   */
  const clearAllNotifications = () => {
    const container = document.getElementById('notificationContainer')
    if (container) {
      container.innerHTML = ''
    }
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
  
  const notifyCompanyRequired = (duration = 5000) => {
    return showNotification('⚠️ Por favor selecciona una empresa primero', 'warning', duration)
  }
  
  const notifyLoading = (message, duration = 0) => {
    return showNotification(`⏳ ${message}`, 'info', duration)
  }
  
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
    clearAllNotifications,
    
    // Shortcuts por tipo
    notifySuccess,
    notifyError,
    notifyWarning,
    notifyInfo,
    
    // Notificaciones especializadas
    notifyApiError,
    notifyApiSuccess,
    notifyCompanyRequired,
    notifyLoading
  }
}
