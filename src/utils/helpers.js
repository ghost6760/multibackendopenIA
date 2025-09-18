// utils/helpers.js - Funciones de utilidad
// Migración de funciones helper desde script.js preservando comportamiento exacto

// ============================================================================
// FUNCIONES DE HTML Y SEGURIDAD - PRESERVAR EXACTAS
// ============================================================================

/**
 * Escapar HTML para prevenir XSS - MANTENER FUNCIÓN EXACTA
 * @param {string} text - Texto a escapar
 * @returns {string} Texto escapado
 */
export function escapeHTML(text) {
  if (typeof text !== 'string') {
    return String(text || '')
  }
  
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

/**
 * Desescapar HTML
 * @param {string} html - HTML a desescapar
 * @returns {string} Texto sin escapar
 */
export function unescapeHTML(html) {
  if (typeof html !== 'string') {
    return String(html || '')
  }
  
  const div = document.createElement('div')
  div.innerHTML = html
  return div.textContent || div.innerText || ''
}

// ============================================================================
// FUNCIONES DE FORMATEO JSON - PRESERVAR EXACTAS
// ============================================================================

/**
 * Formatear objeto como JSON bonito - MANTENER FUNCIÓN EXACTA
 * @param {any} obj - Objeto a formatear
 * @param {number} indent - Espacios de indentación
 * @returns {string} JSON formateado
 */
export function formatJSON(obj, indent = 2) {
  try {
    return JSON.stringify(obj, null, indent)
  } catch (error) {
    console.error('Error formatting JSON:', error)
    return 'Error formatting object'
  }
}

/**
 * Parsear JSON de forma segura
 * @param {string} jsonString - String JSON
 * @param {any} defaultValue - Valor por defecto si falla el parse
 * @returns {any} Objeto parseado o valor por defecto
 */
export function safeJSONParse(jsonString, defaultValue = null) {
  try {
    return JSON.parse(jsonString)
  } catch (error) {
    console.warn('JSON parse failed:', error.message)
    return defaultValue
  }
}

// ============================================================================
// FUNCIONES DE FORMATEO DE FECHAS Y TIEMPO
// ============================================================================

/**
 * Formatear timestamp como fecha legible
 * @param {number|string|Date} timestamp - Timestamp a formatear
 * @param {boolean} includeTime - Incluir hora
 * @returns {string} Fecha formateada
 */
export function formatTimestamp(timestamp, includeTime = true) {
  try {
    const date = new Date(typeof timestamp === 'number' ? timestamp * 1000 : timestamp)
    
    if (includeTime) {
      return date.toLocaleString('es-ES', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })
    } else {
      return date.toLocaleDateString('es-ES')
    }
  } catch (error) {
    console.error('Error formatting timestamp:', error)
    return 'Invalid date'
  }
}

/**
 * Obtener tiempo relativo (ej: "hace 5 minutos")
 * @param {number|string|Date} timestamp - Timestamp
 * @returns {string} Tiempo relativo
 */
export function getRelativeTime(timestamp) {
  try {
    const date = new Date(typeof timestamp === 'number' ? timestamp * 1000 : timestamp)
    const now = new Date()
    const diffMs = now - date
    const diffSeconds = Math.floor(diffMs / 1000)
    const diffMinutes = Math.floor(diffSeconds / 60)
    const diffHours = Math.floor(diffMinutes / 60)
    const diffDays = Math.floor(diffHours / 24)
    
    if (diffSeconds < 60) {
      return 'hace unos segundos'
    } else if (diffMinutes < 60) {
      return `hace ${diffMinutes} minuto${diffMinutes !== 1 ? 's' : ''}`
    } else if (diffHours < 24) {
      return `hace ${diffHours} hora${diffHours !== 1 ? 's' : ''}`
    } else if (diffDays < 7) {
      return `hace ${diffDays} día${diffDays !== 1 ? 's' : ''}`
    } else {
      return formatTimestamp(timestamp, false)
    }
  } catch (error) {
    return 'Fecha inválida'
  }
}

// ============================================================================
// FUNCIONES DE VALIDACIÓN
// ============================================================================

/**
 * Validar email
 * @param {string} email - Email a validar
 * @returns {boolean} True si es válido
 */
export function isValidEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

/**
 * Validar URL
 * @param {string} url - URL a validar
 * @returns {boolean} True si es válida
 */
export function isValidURL(url) {
  try {
    new URL(url)
    return true
  } catch {
    return false
  }
}

/**
 * Validar JSON string
 * @param {string} jsonString - String a validar
 * @returns {boolean} True si es JSON válido
 */
export function isValidJSON(jsonString) {
  try {
    JSON.parse(jsonString)
    return true
  } catch {
    return false
  }
}

// ============================================================================
// FUNCIONES DE MANIPULACIÓN DE STRINGS
// ============================================================================

/**
 * Capitalizar primera letra
 * @param {string} str - String a capitalizar
 * @returns {string} String capitalizado
 */
export function capitalize(str) {
  if (!str || typeof str !== 'string') return ''
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase()
}

/**
 * Convertir a kebab-case
 * @param {string} str - String a convertir
 * @returns {string} String en kebab-case
 */
export function toKebabCase(str) {
  if (!str || typeof str !== 'string') return ''
  return str
    .replace(/([a-z])([A-Z])/g, '$1-$2')
    .replace(/[\s_]+/g, '-')
    .toLowerCase()
}

/**
 * Convertir a camelCase
 * @param {string} str - String a convertir
 * @returns {string} String en camelCase
 */
export function toCamelCase(str) {
  if (!str || typeof str !== 'string') return ''
  return str
    .replace(/(?:^\w|[A-Z]|\b\w)/g, (word, index) => {
      return index === 0 ? word.toLowerCase() : word.toUpperCase()
    })
    .replace(/\s+/g, '')
}

/**
 * Truncar texto
 * @param {string} text - Texto a truncar
 * @param {number} maxLength - Longitud máxima
 * @param {string} suffix - Sufijo (ej: "...")
 * @returns {string} Texto truncado
 */
export function truncateText(text, maxLength, suffix = '...') {
  if (!text || typeof text !== 'string') return ''
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength - suffix.length) + suffix
}

// ============================================================================
// FUNCIONES DE MANIPULACIÓN DE ARRAYS Y OBJETOS
// ============================================================================

/**
 * Obtener valor anidado de objeto usando path de puntos
 * @param {object} obj - Objeto fuente
 * @param {string} path - Path con puntos (ej: "user.profile.name")
 * @param {any} defaultValue - Valor por defecto
 * @returns {any} Valor encontrado o valor por defecto
 */
export function getNestedValue(obj, path, defaultValue = undefined) {
  if (!obj || typeof obj !== 'object' || !path) {
    return defaultValue
  }
  
  return path.split('.').reduce((current, key) => {
    return current && current[key] !== undefined ? current[key] : defaultValue
  }, obj)
}

/**
 * Establecer valor anidado en objeto usando path de puntos
 * @param {object} obj - Objeto destino
 * @param {string} path - Path con puntos
 * @param {any} value - Valor a establecer
 * @returns {object} Objeto modificado
 */
export function setNestedValue(obj, path, value) {
  if (!obj || typeof obj !== 'object' || !path) {
    return obj
  }
  
  const keys = path.split('.')
  const lastKey = keys.pop()
  
  const target = keys.reduce((current, key) => {
    if (!current[key] || typeof current[key] !== 'object') {
      current[key] = {}
    }
    return current[key]
  }, obj)
  
  target[lastKey] = value
  return obj
}

/**
 * Remover duplicados de array
 * @param {Array} array - Array fuente
 * @param {string} key - Key para comparar (opcional)
 * @returns {Array} Array sin duplicados
 */
export function removeDuplicates(array, key = null) {
  if (!Array.isArray(array)) return []
  
  if (key) {
    const seen = new Set()
    return array.filter(item => {
      const value = getNestedValue(item, key)
      if (seen.has(value)) {
        return false
      }
      seen.add(value)
      return true
    })
  }
  
  return [...new Set(array)]
}

/**
 * Ordenar array por key
 * @param {Array} array - Array a ordenar
 * @param {string} key - Key por la cual ordenar
 * @param {string} direction - 'asc' o 'desc'
 * @returns {Array} Array ordenado
 */
export function sortBy(array, key, direction = 'asc') {
  if (!Array.isArray(array)) return []
  
  return [...array].sort((a, b) => {
    const aVal = getNestedValue(a, key)
    const bVal = getNestedValue(b, key)
    
    if (aVal < bVal) return direction === 'asc' ? -1 : 1
    if (aVal > bVal) return direction === 'asc' ? 1 : -1
    return 0
  })
}

// ============================================================================
// FUNCIONES DE FORMATEO DE DATOS
// ============================================================================

/**
 * Formatear bytes como string legible
 * @param {number} bytes - Número de bytes
 * @param {number} decimals - Decimales a mostrar
 * @returns {string} String formateado (ej: "1.5 MB")
 */
export function formatBytes(bytes, decimals = 2) {
  if (bytes === 0) return '0 Bytes'
  
  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB']
  
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i]
}

/**
 * Formatear número con separadores de miles
 * @param {number} num - Número a formatear
 * @returns {string} Número formateado
 */
export function formatNumber(num) {
  if (typeof num !== 'number') return '0'
  return num.toLocaleString('es-ES')
}

/**
 * Formatear porcentaje
 * @param {number} value - Valor (0-1 o 0-100)
 * @param {number} decimals - Decimales a mostrar
 * @param {boolean} isAlreadyPercent - Si el valor ya está en formato porcentaje
 * @returns {string} Porcentaje formateado
 */
export function formatPercentage(value, decimals = 1, isAlreadyPercent = false) {
  if (typeof value !== 'number') return '0%'
  
  const percent = isAlreadyPercent ? value : value * 100
  return percent.toFixed(decimals) + '%'
}

// ============================================================================
// FUNCIONES DE UTILIDADES DIVERSAS
// ============================================================================

/**
 * Generar UUID simple
 * @returns {string} UUID generado
 */
export function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}

/**
 * Generar ID aleatorio corto
 * @param {number} length - Longitud del ID
 * @returns {string} ID generado
 */
export function generateShortId(length = 8) {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  let result = ''
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return result
}

/**
 * Sleep/delay function
 * @param {number} ms - Milisegundos a esperar
 * @returns {Promise} Promise que se resuelve después del delay
 */
export function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * Debounce function
 * @param {Function} func - Función a debounce
 * @param {number} wait - Tiempo de espera en ms
 * @returns {Function} Función debounced
 */
export function debounce(func, wait) {
  let timeout
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout)
      func(...args)
    }
    clearTimeout(timeout)
    timeout = setTimeout(later, wait)
  }
}

/**
 * Throttle function
 * @param {Function} func - Función a throttle
 * @param {number} limit - Límite de tiempo en ms
 * @returns {Function} Función throttled
 */
export function throttle(func, limit) {
  let inThrottle
  return function executedFunction(...args) {
    if (!inThrottle) {
      func.apply(this, args)
      inThrottle = true
      setTimeout(() => inThrottle = false, limit)
    }
  }
}

// ============================================================================
// EXPORTACIÓN POR DEFECTO
// ============================================================================

export default {
  // HTML y seguridad
  escapeHTML,
  unescapeHTML,
  
  // JSON
  formatJSON,
  safeJSONParse,
  
  // Fechas
  formatTimestamp,
  getRelativeTime,
  
  // Validaciones
  isValidEmail,
  isValidURL,
  isValidJSON,
  
  // Strings
  capitalize,
  toKebabCase,
  toCamelCase,
  truncateText,
  
  // Objetos y arrays
  getNestedValue,
  setNestedValue,
  removeDuplicates,
  sortBy,
  
  // Formateo
  formatBytes,
  formatNumber,
  formatPercentage,
  
  // Utilidades
  generateUUID,
  generateShortId,
  sleep,
  debounce,
  throttle
}
