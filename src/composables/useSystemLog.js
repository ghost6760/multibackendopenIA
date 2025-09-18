/**
 * useSystemLog.js - Composable para Gestión del Log del Sistema
 * MIGRADO DE: script.js funciones addToLog(), updateLogDisplay()
 * PRESERVAR: Comportamiento exacto de las funciones originales
 * COMPATIBILIDAD: 100% con el script.js original
 */

import { ref, computed, watch } from 'vue'
import { useAppStore } from '@/stores/app'

export const useSystemLog = () => {
  const appStore = useAppStore()

  // ============================================================================
  // ESTADO LOCAL
  // ============================================================================

  const maxLogEntries = ref(100)
  const autoScroll = ref(true)
  const filterLevel = ref('all')
  const searchQuery = ref('')

  // ============================================================================
  // COMPUTED PROPERTIES
  // ============================================================================

  const filteredLogs = computed(() => {
    let filtered = appStore.systemLog

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
    const stats = {
      total: appStore.systemLog.length,
      info: 0,
      warning: 0,
      error: 0,
      success: 0
    }

    appStore.systemLog.forEach(entry => {
      if (stats.hasOwnProperty(entry.level)) {
        stats[entry.level]++
      }
    })

    return stats
  })

  const latestError = computed(() => {
    const errors = appStore.systemLog.filter(entry => entry.level === 'error')
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
    const timestamp = new Date().toISOString().substring(0, 19).replace('T', ' ')
    const logEntry = {
      timestamp,
      level,
      message,
      id: Date.now() + Math.random() // Para identificación única
    }
    
    appStore.systemLog.push(logEntry)
    
    // Mantener solo los últimos maxLogEntries logs - PRESERVAR: Mismo límite que script.js
    if (appStore.systemLog.length > maxLogEntries.value) {
      appStore.systemLog.shift()
    }
    
    // Actualizar UI del log automáticamente si está habilitado
    if (autoScroll.value) {
      updateLogDisplay()
    }

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
    const previousLength = appStore.systemLog.length
    appStore.systemLog.splice(0) // Limpiar array manteniendo reactividad
    
    addToLog(`System log cleared (${previousLength} entries removed)`, 'info')
    
    if (typeof window !== 'undefined' && window.dispatchEvent) {
      window.dispatchEvent(new CustomEvent('systemLogCleared', { 
        detail: { entriesRemoved: previousLength }
      }))
    }
  }

  /**
   * Exporta el log del sistema - NUEVA FUNCIONALIDAD
   */
  const exportLog = (format = 'json') => {
    try {
      let content
      const timestamp = new Date().toISOString().split('T')[0]
      
      if (format === 'json') {
        content = JSON.stringify(appStore.systemLog, null, 2)
      } else if (format === 'txt') {
        content = appStore.systemLog.map(entry => 
          `[${entry.timestamp}] [${entry.level.toUpperCase()}] ${entry.message}`
        ).join('\n')
      } else if (format === 'csv') {
        const headers = 'Timestamp,Level,Message\n'
        content = headers + appStore.systemLog.map(entry => 
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
    return appStore.systemLog.filter(entry => {
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
  // WATCHERS
  // ============================================================================

  // Watcher para mantener el límite de entradas
  watch(() => appStore.systemLog.length, (newLength) => {
    if (newLength > maxLogEntries.value) {
      const entriesToRemove = newLength - maxLogEntries.value
      appStore.systemLog.splice(0, entriesToRemove)
    }
  })

  // ============================================================================
  // RETURN COMPOSABLE API
  // ============================================================================

  return {
    // Estado reactivo
    systemLog: computed(() => appStore.systemLog),
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
