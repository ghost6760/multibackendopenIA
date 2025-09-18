// utils/constants.js - Constantes del sistema
// Migración de constantes desde script.js preservando valores exactos

// ============================================================================
// CONFIGURACIÓN DE API - PRESERVAR VALORES EXACTOS
// ============================================================================

// ✅ MANTENER CONFIGURACIÓN EXACTA DE SCRIPT.JS
export const API_BASE_URL = window.location.origin
export const DEFAULT_COMPANY_ID = 'benova'

// ============================================================================
// ENDPOINTS DE API - CATALOGADOS DESDE SCRIPT.JS
// ============================================================================

export const API_ENDPOINTS = {
  // Core endpoints
  COMPANIES: '/api/companies',
  SYSTEM_INFO: '/api/system/info',
  HEALTH: '/api/health',
  HEALTH_COMPANY: '/api/health/company', // + /:id
  
  // Document endpoints
  DOCUMENTS: '/api/documents',
  DOCUMENTS_SEARCH: '/api/documents/search',
  DOCUMENTS_CLEANUP: '/api/documents/cleanup',
  
  // Conversation endpoints
  CONVERSATIONS: '/api/conversations',
  CONVERSATIONS_TEST: '/api/conversations/test',
  
  // Multimedia endpoints
  MULTIMEDIA_AUDIO: '/api/multimedia/audio',
  MULTIMEDIA_IMAGE: '/api/multimedia/image',
  MULTIMEDIA_TEST: '/api/multimedia/test',
  
  // Prompts endpoints
  PROMPTS: '/api/prompts',
  PROMPTS_REPAIR: '/api/prompts/repair',
  PROMPTS_MIGRATE: '/api/prompts/migrate',
  PROMPTS_STATUS: '/api/prompts/system/status',
  
  // Admin endpoints (requieren API key)
  ADMIN_CONFIG: '/api/admin/config',
  ADMIN_STATUS: '/api/admin/status',
  ADMIN_COMPANIES: '/api/admin/companies',
  ADMIN_DIAGNOSTICS: '/api/admin/diagnostics',
  ADMIN_RELOAD_COMPANIES: '/api/admin/reload-companies',
  
  // Enterprise endpoints (requieren API key)
  ENTERPRISE_COMPANIES: '/api/enterprise/companies',
  
  // Google Calendar integration
  GOOGLE_CALENDAR_CONFIG: '/api/google-calendar/config'
}

// ============================================================================
// CONFIGURACIÓN DE TABS - PRESERVAR NOMBRES EXACTOS
// ============================================================================

export const TABS = {
  DASHBOARD: 'dashboard',
  DOCUMENTS: 'documents', 
  CONVERSATIONS: 'conversations',
  MULTIMEDIA: 'multimedia',
  PROMPTS: 'prompts',
  ADMIN: 'admin',
  ENTERPRISE: 'enterprise',
  HEALTH: 'health'
}

export const TAB_LABELS = {
  [TABS.DASHBOARD]: '📊 Dashboard',
  [TABS.DOCUMENTS]: '📄 Documentos',
  [TABS.CONVERSATIONS]: '💬 Conversaciones',
  [TABS.MULTIMEDIA]: '🎤 Multimedia',
  [TABS.PROMPTS]: '🤖 Prompts',
  [TABS.ADMIN]: '🔧 Administración',
  [TABS.ENTERPRISE]: '🏢 Enterprise',
  [TABS.HEALTH]: '🏥 Health Check'
}

// ============================================================================
// TIPOS DE NOTIFICACIONES - PRESERVAR EXACTOS
// ============================================================================

export const NOTIFICATION_TYPES = {
  SUCCESS: 'success',
  ERROR: 'error',
  WARNING: 'warning',
  INFO: 'info'
}

export const NOTIFICATION_ICONS = {
  [NOTIFICATION_TYPES.SUCCESS]: '✅',
  [NOTIFICATION_TYPES.ERROR]: '❌',
  [NOTIFICATION_TYPES.WARNING]: '⚠️',
  [NOTIFICATION_TYPES.INFO]: 'ℹ️'
}

export const NOTIFICATION_DURATIONS = {
  SHORT: 3000,
  MEDIUM: 5000,
  LONG: 8000,
  PERSISTENT: 0 // No se cierra automáticamente
}

// ============================================================================
// NIVELES DE LOG - PRESERVAR EXACTOS DE SCRIPT.JS
// ============================================================================

export const LOG_LEVELS = {
  ERROR: 'error',
  WARNING: 'warning', 
  INFO: 'info',
  DEBUG: 'debug'
}

export const LOG_COLORS = {
  [LOG_LEVELS.ERROR]: '#ef4444',
  [LOG_LEVELS.WARNING]: '#f59e0b',
  [LOG_LEVELS.INFO]: '#3b82f6',
  [LOG_LEVELS.DEBUG]: '#6b7280'
}

// ============================================================================
// ESTADOS DE API KEY - PRESERVAR EXACTOS
// ============================================================================

export const API_KEY_STATUS = {
  NOT_CONFIGURED: 'not-configured',
  VALID: 'valid',
  INVALID: 'invalid',
  TESTING: 'testing'
}

export const API_KEY_STATUS_LABELS = {
  [API_KEY_STATUS.NOT_CONFIGURED]: 'API Key requerida',
  [API_KEY_STATUS.VALID]: 'API Key válida',
  [API_KEY_STATUS.INVALID]: 'API Key inválida',
  [API_KEY_STATUS.TESTING]: 'Verificando...'
}

export const API_KEY_STATUS_CLASSES = {
  [API_KEY_STATUS.NOT_CONFIGURED]: 'not-configured',
  [API_KEY_STATUS.VALID]: 'success',
  [API_KEY_STATUS.INVALID]: 'error',
  [API_KEY_STATUS.TESTING]: 'warning'
}

// ============================================================================
// ESTADOS DE EMPRESAS - CATALOGADOS DE SCRIPT.JS
// ============================================================================

export const COMPANY_STATUS = {
  HEALTHY: 'healthy',
  WARNING: 'warning',
  ERROR: 'error',
  UNKNOWN: 'unknown'
}

export const COMPANY_STATUS_LABELS = {
  [COMPANY_STATUS.HEALTHY]: 'Saludable',
  [COMPANY_STATUS.WARNING]: 'Advertencia',
  [COMPANY_STATUS.ERROR]: 'Error',
  [COMPANY_STATUS.UNKNOWN]: 'Desconocido'
}

export const COMPANY_STATUS_COLORS = {
  [COMPANY_STATUS.HEALTHY]: '#22c55e',
  [COMPANY_STATUS.WARNING]: '#f59e0b', 
  [COMPANY_STATUS.ERROR]: '#ef4444',
  [COMPANY_STATUS.UNKNOWN]: '#6b7280'
}

// ============================================================================
// CONFIGURACIÓN DE CACHE - VALORES DE SCRIPT.JS
// ============================================================================

export const CACHE_KEYS = {
  COMPANIES: 'companies',
  SYSTEM_INFO: 'systemInfo',
  DOCUMENTS: 'documents',
  CONVERSATIONS: 'conversations',
  PROMPTS: 'prompts',
  HEALTH_STATUS: 'healthStatus'
}

export const CACHE_TTL = {
  COMPANIES: 10 * 60 * 1000,      // 10 minutos
  SYSTEM_INFO: 2 * 60 * 1000,    // 2 minutos
  DOCUMENTS: 30 * 1000,          // 30 segundos
  CONVERSATIONS: 30 * 1000,      // 30 segundos
  PROMPTS: 5 * 60 * 1000,        // 5 minutos
  HEALTH_STATUS: 1 * 60 * 1000,  // 1 minuto
  DEFAULT: 5 * 60 * 1000         // 5 minutos por defecto
}

// ============================================================================
// CONFIGURACIÓN DE INTERFAZ
// ============================================================================

export const UI_CONFIG = {
  // Duración de animaciones
  ANIMATION_DURATION: {
    FAST: 150,
    MEDIUM: 300,
    SLOW: 500
  },
  
  // Tamaños de pantalla (breakpoints)
  BREAKPOINTS: {
    MOBILE: 768,
    TABLET: 1024,
    DESKTOP: 1280
  },
  
  // Límites de contenido
  CONTENT_LIMITS: {
    NOTIFICATION_MESSAGE_MAX: 200,
    LOG_MESSAGE_MAX: 500,
    SEARCH_QUERY_MAX: 100,
    DOCUMENT_NAME_MAX: 255
  },
  
  // Configuración de paginación
  PAGINATION: {
    DEFAULT_PAGE_SIZE: 20,
    SMALL_PAGE_SIZE: 10,
    LARGE_PAGE_SIZE: 50
  }
}

// ============================================================================
// FORMATOS DE ARCHIVOS SOPORTADOS
// ============================================================================

export const SUPPORTED_FILE_TYPES = {
  DOCUMENTS: {
    PDF: 'application/pdf',
    TXT: 'text/plain',
    DOCX: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    DOC: 'application/msword'
  },
  
  IMAGES: {
    JPEG: 'image/jpeg',
    JPG: 'image/jpg', 
    PNG: 'image/png',
    GIF: 'image/gif',
    WEBP: 'image/webp'
  },
  
  AUDIO: {
    MP3: 'audio/mp3',
    WAV: 'audio/wav',
    OGG: 'audio/ogg',
    M4A: 'audio/m4a'
  }
}

export const MAX_FILE_SIZES = {
  DOCUMENT: 10 * 1024 * 1024,    // 10MB
  IMAGE: 5 * 1024 * 1024,        // 5MB
  AUDIO: 50 * 1024 * 1024        // 50MB
}

// ============================================================================
// EXPRESIONES REGULARES COMUNES
// ============================================================================

export const REGEX_PATTERNS = {
  EMAIL: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  URL: /^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$/,
  UUID: /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
  API_KEY: /^[a-zA-Z0-9_-]{20,}$/,
  COMPANY_ID: /^[a-z_][a-z0-9_]*$/
}

// ============================================================================
// MENSAJES DE ERROR COMUNES
// ============================================================================

export const ERROR_MESSAGES = {
  NETWORK_ERROR: 'Error de conexión. Verifique su conexión a internet.',
  SERVER_ERROR: 'Error del servidor. Intente nuevamente más tarde.',
  UNAUTHORIZED: 'No autorizado. Verifique sus credenciales.',
  FORBIDDEN: 'Acceso denegado. No tiene permisos para esta operación.',
  NOT_FOUND: 'Recurso no encontrado.',
  VALIDATION_ERROR: 'Error de validación. Verifique los datos ingresados.',
  TIMEOUT_ERROR: 'La operación ha excedido el tiempo límite.',
  UNKNOWN_ERROR: 'Ha ocurrido un error inesperado.'
}

// ============================================================================
// MENSAJES DE ÉXITO COMUNES
// ============================================================================

export const SUCCESS_MESSAGES = {
  SAVED: 'Guardado exitosamente',
  DELETED: 'Eliminado exitosamente', 
  UPDATED: 'Actualizado exitosamente',
  UPLOADED: 'Subido exitosamente',
  SENT: 'Enviado exitosamente',
  PROCESSED: 'Procesado exitosamente',
  CONFIGURED: 'Configurado exitosamente'
}

// ============================================================================
// CONFIGURACIÓN DE MONITOREO
// ============================================================================

export const MONITORING_CONFIG = {
  // Intervalos de actualización (en ms)
  INTERVALS: {
    REAL_TIME: 5000,        // 5 segundos
    FAST: 30000,            // 30 segundos  
    MEDIUM: 60000,          // 1 minuto
    SLOW: 300000            // 5 minutos
  },
  
  // Límites para alertas
  ALERT_THRESHOLDS: {
    MEMORY_USAGE: 85,       // 85% de uso de memoria
    CPU_USAGE: 90,          // 90% de uso de CPU
    ERROR_RATE: 10,         // 10% de tasa de errores
    RESPONSE_TIME: 5000     // 5 segundos de tiempo de respuesta
  }
}

// ============================================================================
// CONFIGURACIÓN DE DESARROLLO
// ============================================================================

export const DEV_CONFIG = {
  // Activar logs de debug en desarrollo
  DEBUG_ENABLED: process.env.NODE_ENV === 'development',
  
  // Mostrar información técnica
  SHOW_TECHNICAL_INFO: process.env.NODE_ENV !== 'production',
  
  // Configuración de mock data para desarrollo
  USE_MOCK_DATA: process.env.VITE_USE_MOCK_DATA === 'true'
}

// ============================================================================
// EXPORTACIÓN POR DEFECTO
// ============================================================================

export default {
  API_BASE_URL,
  DEFAULT_COMPANY_ID,
  API_ENDPOINTS,
  TABS,
  TAB_LABELS,
  NOTIFICATION_TYPES,
  NOTIFICATION_ICONS,
  NOTIFICATION_DURATIONS,
  LOG_LEVELS,
  LOG_COLORS,
  API_KEY_STATUS,
  API_KEY_STATUS_LABELS,
  API_KEY_STATUS_CLASSES,
  COMPANY_STATUS,
  COMPANY_STATUS_LABELS,
  COMPANY_STATUS_COLORS,
  CACHE_KEYS,
  CACHE_TTL,
  UI_CONFIG,
  SUPPORTED_FILE_TYPES,
  MAX_FILE_SIZES,
  REGEX_PATTERNS,
  ERROR_MESSAGES,
  SUCCESS_MESSAGES,
  MONITORING_CONFIG,
  DEV_CONFIG
}
