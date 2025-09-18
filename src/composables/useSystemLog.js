/**
 * useSystemLog.js - Composable para Gestión del Log del Sistema
 * MIGRADO DE: script.js funciones addToLog(), updateLogDisplay()
 * PRESERVAR: Comportamiento exacto de las funciones originales
 * CORRECCIÓN: Eliminar dependencia directa del store para evitar problemas de inicialización
 */

import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

export const useSystemLog = () => {
  // ============================================================================
  // ESTADO LOCAL
  // ============================================================================

  const maxLogEntries = ref(100)
  const autoScroll = ref(true)
  const filterLevel = ref('all')
  const searchQuery = ref('')

  // Función para obtener el store de forma segura
  const getStore = () => {
    try {
      const { useAppStore } = require('@/stores/app')
      return useAppStore()
    } catch (error) {
      return null
    }
  }

  // ============================================================================
  // COMPUTED PROPERTIES
  // ============================================================================

  const systemLog = computed(() => {
    const store = getStore()
    return store ? store.systemLog : []
  })

  const filteredLogs = computed(() => {
    let filtered = systemLog.value

    // Filtrar por nivel
    if (filterLevel.value !== 'all') {
      filtered = filtered.filter(entry => entry.level === filterLevel.value)
    }

    // Filtrar por búsqueda
    if (searchQuery.value.trim()) {
      const query = searchQuery.value.toLowerCase()
      filtered = filtered.filter(entry => 
        entry.message.toLowerCase().includes(query) ||
        entry.level.toLowerCase().includes(query) ||
        entry.timestamp.includes(query)
      )
    }

    return filtered
  })

  const logStats = computed(() => {
    const logs = systemLog.value
    const stats = {
      total: logs.length,
      info: 0,
      warning: 0,
      error: 0,
      success: 0
    }

    logs.forEach(entry => {
      if (stats.hasOwnProperty(entry.level)) {
        stats[entry.level]++
      }
    })

    return stats
  })

  const latestError = computed(() => {
    const errors = systemLog.value.filter(entry => entry.level === 'error')
    return errors.length > 0 ? errors[errors.length - 1] : null
  })

  // ============================================================================
  // FUNCIONES PRINCIPALES MIGRADAS DEL SCRIPT.JS
  // ============================================================================

  /**
   * Agrega una entrada al log del sistema - MIGRADO: addToLog() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   * @param {string} message - Mensaje del log
   * @param {string} level - Nivel del log (info, warning, error, success)
   */
  const addToLog = (message, level = 'info') => {
    // MÉTODO 1: Usar el store si está disponible
    const store = getStore()
    if (store && store.addToLog) {
      store.addToLog(message, level)
      return
    }
    
    // MÉTODO 2: Fallback - crear log directo
    const timestamp = new Date().toISOString().substring(0, 19).replace('T', ' ')
    const logEntry = {
      id: `log_${Date.now()}_${Math.random()}`,
      timestamp,
      level,
      message,
      fullTimestamp: new Date()
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
    updateLogDisplay()
    
    // Emitir evento para notificaciones críticas
    if (level === 'error') {
      if (typeof window !== 'undefined' && window.dispatchEvent) {
        window.dispatchEvent(new CustomEvent('systemError', { 
          detail: { entry: logEntry }
        }))
      }
    }
  }

  /**
   * Actualiza la visualización del log en la UI - MIGRADO: updateLogDisplay() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const updateLogDisplay = () => {
    // En Vue.js, esto se maneja automáticamente por la reactividad
    // Pero mantenemos la función para compatibilidad
    
    if (typeof window !== 'undefined') {
      // Scroll automático al final - PRESERVAR: Mismo comportamiento que script.js
      setTimeout(() => {
        const logContainer = document.getElementById('systemLog')
        if (logContainer && autoScroll.value) {
          logContainer.scrollTop = logContainer.scrollHeight
        }
      }, 50)
    }
  }

  /**
   * Limpia el log del sistema - MIGRADO: clearSystemLog() de script.js
   * PRESERVAR: Comportamiento exacto de la función original
   */
  const clearSystemLog = () => {
    const store = getStore()
    if (store && store.clearSystemLog) {
      store.clearSystemLog()
    } else {
      // Fallback
      console.clear()
      addToLog('System log cleared (fallback mode)', 'info')
    }
  }

  /**
   * Exporta el log del sistema
   */
  const exportLog = (format = 'json') => {
    try {
      const logs = systemLog.value
      let content
      const timestamp = new Date().toISOString().split('T')[0]
      
      if (format === 'json') {
        content = JSON.stringify(logs, null, 2)
      } else if (format === 'txt') {
        content = logs.map(entry => 
          `[${entry.timestamp}] [${entry.level.toUpperCase()}] ${entry.message}`
        ).join('\n')
      } else if (format === 'csv') {
        const headers = 'Timestamp,Level,Message\n'
        content = headers + logs.map(entry => 
          `"${entry.timestamp}","${entry.level}","${entry.message.replace(/"/g, '""')}"`
        ).join('\n')
      }

      // Crear archivo para descarga
      const blob = new Blob([content], { 
        type: format === 'json' ? 'application/json' : 'text/plain' 
      })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `system_log_${timestamp}.${format}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)

      addToLog(`System log exported to ${format.toUpperCase()} format`, 'success')
      
    } catch (error) {
      addToLog(`Error exporting log: ${error.message}`, 'error')
    }
  }

  /**
   * Filtra logs por período de tiempo
   */
  const filterLogsByPeriod = (hours = 24) => {
    const cutoffTime = new Date(Date.now() - (hours * 60 * 60 * 1000))
    return systemLog.value.filter(entry => {
      const entryTime = new Date(entry.timestamp.replace(' ', 'T'))
      return entryTime >= cutoffTime
    })
  }

  /**
   * Obtiene estadísticas del log por período
   */
  const getLogStatsByPeriod = (hours = 24) => {
    const recentLogs = filterLogsByPeriod(hours)
    
    const stats = {
      total: recentLogs.length,
      info: 0,
      warning: 0,
      error: 0,
      success: 0,
      period: `${hours}h`
    }

    recentLogs.forEach(entry => {
      if (stats.hasOwnProperty(entry.level)) {
        stats[entry.level]++
      }
    })

    return stats
  }

  // ============================================================================
  // UTILIDADES
  // ============================================================================

  const formatLogLevel = (level) => {
    const levelMap = {
      info: { emoji: 'ℹ️', class: 'log-info', text: 'INFO' },
      warning: { emoji: '⚠️', class: 'log-warning', text: 'WARN' },
      error: { emoji: '❌', class: 'log-error', text: 'ERROR' },
      success: { emoji: '✅', class: 'log-success', text: 'SUCCESS' }
    }
    return levelMap[level] || levelMap.info
  }

  const formatTimestamp = (timestamp) => {
    try {
      const date = new Date(timestamp.replace(' ', 'T'))
      return date.toLocaleString()
    } catch (error) {
      return timestamp
    }
  }

  const truncateMessage = (message, maxLength = 100) => {
    if (message.length <= maxLength) return message
    return message.slice(0, maxLength) + '...'
  }

  // ============================================================================
  // LIFECYCLE HOOKS
  // ============================================================================

  onMounted(() => {
    // Exponer funciones globales para compatibilidad
    if (typeof window !== 'undefined') {
      window.addToLog = addToLog
      window.updateLogDisplay = updateLogDisplay
      window.clearSystemLog = clearSystemLog
    }
  })

  onUnmounted(() => {
    // Limpiar funciones globales
    if (typeof window !== 'undefined') {
      delete window.addToLog
      delete window.updateLogDisplay
      delete window.clearSystemLog
    }
  })

  // ============================================================================
  // RETURN COMPOSABLE API
  // ============================================================================

  return {
    // Estado reactivo
    systemLog,
    filteredLogs,
    logStats,
    latestError,
    maxLogEntries,
    autoScroll,
    filterLevel,
    searchQuery,

    // Funciones principales (PRESERVAR nombres exactos de script.js)
    addToLog,
    updateLogDisplay,
    clearSystemLog,

    // Nuevas funcionalidades
    exportLog,
    filterLogsByPeriod,
    getLogStatsByPeriod,

    // Utilidades
    formatLogLevel,
    formatTimestamp,
    truncateMessage
  }
}
