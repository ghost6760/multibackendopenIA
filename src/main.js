// main.js - Configuración corregida para eliminar errores de Vue
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import './styles/main.css'

// ============================================================================
// CONFIGURACIÓN DE LA APLICACIÓN
// ============================================================================

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)

// ============================================================================
// MANEJO DE ERRORES Y WARNINGS - VERSIÓN CORREGIDA
// ============================================================================

// Configuración mejorada para manejo de errores
app.config.errorHandler = (err, instance, info) => {
  // Crear objeto de error seguro
  const errorInfo = {
    message: err?.message || String(err),
    info: String(info),
    componentName: getComponentName(instance),
    timestamp: new Date().toISOString(),
    stack: err?.stack || 'No stack available'
  }
  
  console.error('🚨 Vue Error:', errorInfo)
  
  // Log al sistema si está disponible
  if (typeof window !== 'undefined' && window.addToLog) {
    try {
      window.addToLog(`Vue Error: ${errorInfo.message} (${errorInfo.info})`, 'error')
    } catch (logError) {
      console.warn('Failed to log to system:', logError)
    }
  }
  
  // Mostrar notificación al usuario si está disponible
  if (typeof window !== 'undefined' && window.showNotification) {
    try {
      window.showNotification(`Error de la aplicación: ${errorInfo.message}`, 'error')
    } catch (notifyError) {
      console.warn('Failed to show notification:', notifyError)
    }
  }
}

// Configuración mejorada del warn handler solo en desarrollo
if (import.meta.env.DEV) {
  app.config.warnHandler = (msg, instance, trace) => {
    // Validar y sanitizar inputs
    const safeMessage = typeof msg === 'string' ? msg : String(msg || 'Unknown warning')
    const componentName = getComponentName(instance)
    const safeTrace = trace || 'No trace available'
    
    // Filtrar warnings conocidos que no son críticos
    const ignoredWarnings = [
      'Failed to resolve component',
      'Component is missing template',
      'Invalid prop type'
    ]
    
    const shouldIgnore = ignoredWarnings.some(warning => 
      safeMessage.toLowerCase().includes(warning.toLowerCase())
    )
    
    if (!shouldIgnore) {
      console.warn(`⚠️ Vue Warning: ${safeMessage}`)
      
      if (componentName !== 'Unknown') {
        console.warn(`📍 Component: ${componentName}`)
      }
      
      if (safeTrace && safeTrace !== 'No trace available') {
        console.warn(`🔍 Trace:`, safeTrace)
      }
    }
    
    // Log simplificado al sistema si está disponible
    if (typeof window !== 'undefined' && window.addToLog && !shouldIgnore) {
      try {
        window.addToLog(`Vue Warning: ${safeMessage} (${componentName})`, 'warning')
      } catch (logError) {
        console.warn('Failed to log warning to system:', logError)
      }
    }
  }
}

// ============================================================================
// FUNCIONES HELPER SEGURAS
// ============================================================================

/**
 * Extrae el nombre del componente de forma segura
 * @param {Object} instance - Instancia del componente Vue
 * @returns {string} Nombre del componente o 'Unknown'
 */
function getComponentName(instance) {
  if (!instance) return 'Unknown'
  
  try {
    // Intentar diferentes formas de obtener el nombre del componente
    return (
      instance.$options?.name ||
      instance.$?.type?.name ||
      instance.$?.type?.__name ||
      instance.type?.name ||
      instance.type?.__name ||
      'Anonymous Component'
    )
  } catch (error) {
    return 'Unknown'
  }
}

// ============================================================================
// PROPIEDADES GLOBALES DE LA APLICACIÓN
// ============================================================================

app.config.globalProperties.$log = (message, level = 'info') => {
  const timestamp = new Date().toISOString()
  console.log(`[${level.toUpperCase()}] ${timestamp}:`, message)
  
  if (typeof window !== 'undefined' && window.addToLog) {
    try {
      window.addToLog(message, level)
    } catch (error) {
      console.warn('Failed to add to log:', error)
    }
  }
}

app.config.globalProperties.$notify = (message, type = 'info', duration = 5000) => {
  if (typeof window !== 'undefined' && window.showNotification) {
    try {
      return window.showNotification(message, type, duration)
    } catch (error) {
      console.warn('Failed to show notification:', error)
    }
  }
  console.log(`[NOTIFICATION ${type.toUpperCase()}]`, message)
}

// Constantes globales
app.config.globalProperties.$API_BASE_URL = window.location.origin
app.config.globalProperties.$DEFAULT_COMPANY_ID = 'benova'

// ============================================================================
// DIRECTIVAS PERSONALIZADAS
// ============================================================================

app.directive('focus', {
  mounted(el) {
    try {
      el.focus()
    } catch (error) {
      console.warn('Focus directive failed:', error)
    }
  }
})

app.directive('click-outside', {
  mounted(el, binding) {
    el.clickOutsideEvent = function(event) {
      if (!(el === event.target || el.contains(event.target))) {
        try {
          binding.value(event)
        } catch (error) {
          console.warn('Click outside handler failed:', error)
        }
      }
    }
    document.addEventListener('click', el.clickOutsideEvent)
  },
  unmounted(el) {
    if (el.clickOutsideEvent) {
      document.removeEventListener('click', el.clickOutsideEvent)
    }
  }
})

app.directive('tooltip', {
  mounted(el, binding) {
    try {
      el.setAttribute('title', binding.value)
      el.style.cursor = 'help'
    } catch (error) {
      console.warn('Tooltip directive failed:', error)
    }
  },
  updated(el, binding) {
    try {
      el.setAttribute('title', binding.value)
    } catch (error) {
      console.warn('Tooltip directive update failed:', error)
    }
  }
})

// ============================================================================
// INICIALIZACIÓN DE COMPATIBILIDAD GLOBAL
// ============================================================================

const initializeGlobalCompatibility = () => {
  if (typeof window !== 'undefined') {
    // Establecer variables globales de manera segura
    try {
      window.API_BASE_URL = window.location.origin
      window.DEFAULT_COMPANY_ID = 'benova'
      window.isVueAppReady = true
      
      // Listener para evento de app montada
      window.addEventListener('vueAppMounted', () => {
        console.log('✅ Vue.js 3 app mounted and ready')
      })
      
      // Función para obtener la instancia de Vue
      window.getVueApp = () => app
      
      console.log('🔗 Global compatibility layer initialized')
    } catch (error) {
      console.error('Failed to initialize global compatibility:', error)
    }
  }
}

// ============================================================================
// MANEJO DE EVENTOS GLOBALES
// ============================================================================

const setupGlobalEventListeners = () => {
  // Error tracking global para JavaScript nativo
  window.addEventListener('error', (event) => {
    const errorInfo = {
      message: event.error?.message || event.message,
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
      timestamp: new Date().toISOString(),
      url: window.location.href
    }
    console.error('🚨 Global JavaScript Error:', errorInfo)
    
    // Log al sistema si está disponible
    if (window.addToLog) {
      try {
        window.addToLog(`JS Error: ${errorInfo.message}`, 'error')
      } catch (logError) {
        console.warn('Failed to log JS error:', logError)
      }
    }
  })
  
  // Error tracking para promises rechazadas
  window.addEventListener('unhandledrejection', (event) => {
    const rejectionInfo = {
      reason: event.reason,
      timestamp: new Date().toISOString(),
      url: window.location.href
    }
    console.error('🚨 Unhandled Promise Rejection:', rejectionInfo)
    
    // Log al sistema si está disponible
    if (window.addToLog) {
      try {
        window.addToLog(`Promise Rejection: ${event.reason}`, 'error')
      } catch (logError) {
        console.warn('Failed to log promise rejection:', logError)
      }
    }
  })
  
  // Listener para cambios de visibilidad
  document.addEventListener('visibilitychange', () => {
    try {
      const event = new CustomEvent('appVisibilityChanged', {
        detail: {
          visible: !document.hidden,
          timestamp: Date.now()
        }
      })
      window.dispatchEvent(event)
    } catch (error) {
      console.warn('Failed to dispatch visibility change:', error)
    }
  })
  
  // Listener para cambios de tamaño de ventana
  window.addEventListener('resize', () => {
    try {
      const event = new CustomEvent('appResized', {
        detail: {
          width: window.innerWidth,
          height: window.innerHeight,
          timestamp: Date.now()
        }
      })
      window.dispatchEvent(event)
    } catch (error) {
      console.warn('Failed to dispatch resize event:', error)
    }
  })
}

// ============================================================================
// INICIALIZACIÓN DE LA APLICACIÓN
// ============================================================================

const initializeApp = async () => {
  try {
    console.log('🚀 Initializing Vue.js 3 MultibackendOpenIA Frontend...')
    
    // Inicializar compatibilidad global
    initializeGlobalCompatibility()
    
    // Configurar event listeners
    setupGlobalEventListeners()
    
    // Montar la aplicación Vue
    app.mount('#app')
    
    // Emitir evento de que la aplicación está lista
    const mountedEvent = new CustomEvent('vueAppMounted', {
      detail: {
        timestamp: Date.now(),
        version: '1.0.0'
      }
    })
    window.dispatchEvent(mountedEvent)
    
    console.log('✅ Vue.js 3 app mounted successfully')
    console.log('🎯 Migration from Vanilla JS to Vue.js 3 completed')
    
  } catch (error) {
    console.error('❌ Error initializing Vue.js 3 app:', error)
    
    // Fallback: mostrar error en el DOM
    const appElement = document.getElementById('app')
    if (appElement) {
      appElement.innerHTML = `
        <div style="padding: 20px; background: #f8d7da; color: #721c24; border-radius: 4px; margin: 20px;">
          <h3>Error Initializing Application</h3>
          <p><strong>Error:</strong> ${error.message}</p>
          <p>Please refresh the page or contact support if the problem persists.</p>
          <button onclick="window.location.reload()" style="padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">
            🔄 Refresh Page
          </button>
        </div>
      `
    }
  }
}

// ============================================================================
// INICIALIZAR APLICACIÓN
// ============================================================================

// Verificar que el DOM esté listo
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeApp)
} else {
  initializeApp()
}
