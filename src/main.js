// main.js - Configuración corregida para eliminar warnings
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

// Configuración global para manejo de errores
app.config.errorHandler = (err, instance, info) => {
  console.error('🚨 Vue Error:', {
    error: err.message || err,
    info: info,
    componentName: instance?.$options?.name || instance?.$?.type?.name || 'Unknown',
    timestamp: new Date().toISOString()
  })
  
  // Enviar error al log del sistema si está disponible
  if (window.addToLog) {
    window.addToLog(`Vue Error: ${err.message} (${info})`, 'error')
  }
  
  // Mostrar notificación al usuario si está disponible
  if (window.showNotification) {
    window.showNotification(`Error de la aplicación: ${err.message}`, 'error')
  }
}

// ⚠️ CONFIGURACIÓN CORREGIDA DEL WARN HANDLER
if (import.meta.env.DEV) {
  app.config.warnHandler = (msg, instance, trace) => {
    // Validar que tenemos valores seguros antes de loggear
    const safeMessage = typeof msg === 'string' ? msg : String(msg)
    const componentName = getComponentName(instance)
    const safeTrace = trace || 'No trace available'
    
    // Usar console.warn nativo en lugar de objeto complejo para evitar referencias circulares
    console.warn(`⚠️ Vue Warning: ${safeMessage}`)
    
    if (componentName !== 'Unknown') {
      console.warn(`📍 Component: ${componentName}`)
    }
    
    if (safeTrace && safeTrace !== 'No trace available') {
      console.warn(`🔍 Trace:`, safeTrace)
    }
    
    // Log simplificado al sistema si está disponible
    if (window.addToLog) {
      window.addToLog(`Vue Warning: ${safeMessage} (${componentName})`, 'warning')
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
  
  if (window.addToLog) {
    window.addToLog(message, level)
  }
}

app.config.globalProperties.$notify = (message, type = 'info', duration = 5000) => {
  if (window.showNotification) {
    return window.showNotification(message, type, duration)
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
    el.focus()
  }
})

app.directive('click-outside', {
  mounted(el, binding) {
    el.clickOutsideEvent = function(event) {
      if (!(el === event.target || el.contains(event.target))) {
        binding.value(event)
      }
    }
    document.addEventListener('click', el.clickOutsideEvent)
  },
  unmounted(el) {
    document.removeEventListener('click', el.clickOutsideEvent)
  }
})

app.directive('tooltip', {
  mounted(el, binding) {
    el.setAttribute('title', binding.value)
    el.style.cursor = 'help'
  },
  updated(el, binding) {
    el.setAttribute('title', binding.value)
  }
})

// ============================================================================
// INICIALIZACIÓN DE COMPATIBILIDAD GLOBAL
// ============================================================================

const initializeGlobalCompatibility = () => {
  if (typeof window !== 'undefined') {
    window.API_BASE_URL = window.location.origin
    window.DEFAULT_COMPANY_ID = 'benova'
    window.isVueAppReady = true
    
    window.addEventListener('vueAppMounted', () => {
      console.log('✅ Vue.js 3 app mounted and ready')
    })
    
    window.getVueApp = () => app
    console.log('🔗 Global compatibility layer initialized')
  }
}

// ============================================================================
// MANEJO DE EVENTOS GLOBALES
// ============================================================================

const setupGlobalEventListeners = () => {
  // Error tracking global para JavaScript nativo
  window.addEventListener('error', (event) => {
    console.error('🚨 Global JavaScript Error:', {
      message: event.error?.message || event.message,
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
      timestamp: new Date().toISOString(),
      url: window.location.href
    })
  })
  
  // Error tracking para promises rechazadas
  window.addEventListener('unhandledrejection', (event) => {
    console.error('🚨 Unhandled Promise Rejection:', {
      reason: event.reason,
      timestamp: new Date().toISOString(),
      url: window.location.href
    })
  })
  
  // Listener para cambios de visibilidad
  document.addEventListener('visibilitychange', () => {
    const event = new CustomEvent('appVisibilityChanged', {
      detail: {
        visible: !document.hidden,
        timestamp: Date.now()
      }
    })
    window.dispatchEvent(event)
  })
  
  // Listener para cambios de tamaño de ventana
  window.addEventListener('resize', () => {
    const event = new CustomEvent('appResized', {
      detail: {
        width: window.innerWidth,
        height: window.innerHeight,
        timestamp: Date.now()
      }
    })
    window.dispatchEvent(event)
  })
}

// ============================================================================
// INICIALIZACIÓN DE LA APLICACIÓN
// ============================================================================

const initializeApp = async () => {
  try {
    console.log('🚀 Initializing Vue.js 3 MultibackendOpenIA Frontend...')
    
    initializeGlobalCompatibility()
    setupGlobalEventListeners()
    
    // Montar la aplicación Vue
    app.mount('#app')
    
    // Emitir evento de que la aplicación está lista
    window.dispatchEvent(new CustomEvent('vueAppMounted', {
      detail: {
        timestamp: Date.now(),
        version: '1.0.0'
      }
    }))
    
    console.log('✅ Vue.js 3 app mounted successfully')
    console.log('🎯 Migration from Vanilla JS to Vue.js 3 completed')
    
  } catch (error) {
    console.error('❌ Error initializing Vue.js 3 app:', error)
    
    // Fallback: mostrar error en el DOM
    const errorElement = document.createElement('div')
    errorElement.innerHTML = `
      <div style="
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: #fee;
        border: 2px solid #f00;
        padding: 20px;
        border-radius: 8px;
        font-family: system-ui;
        text-align: center;
        z-index: 10000;
      ">
        <h3>❌ Error de Inicialización</h3>
        <p>No se pudo cargar la aplicación Vue.js</p>
        <pre style="font-size: 12px; background: #f5f5f5; padding: 10px; border-radius: 4px;">
          ${error.message}
        </pre>
        <button onclick="window.location.reload()" style="
          margin-top: 10px;
          padding: 8px 16px;
          background: #007cba;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
        ">
          Recargar Página
        </button>
      </div>
    `
    document.body.appendChild(errorElement)
  }
}

// ============================================================================
// CONFIGURACIÓN DE DESARROLLO
// ============================================================================

if (import.meta.env.DEV) {
  window.devTools = {
    app,
    pinia,
    version: '1.0.0-dev',
    logLevel: 'debug'
  }
  
  console.log('🔧 Development mode enabled')
  console.log('🛠️ Access dev tools via window.devTools')
}

// ============================================================================
// INICIALIZACIÓN FINAL
// ============================================================================

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeApp)
} else {
  initializeApp()
}
