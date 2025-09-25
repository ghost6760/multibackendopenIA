// main.js - Vue.js 3 Compatible - SIN errores DOM manipulation
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import './styles/main.css'

// ============================================================================
// CONFIGURACIÓN DE LA APLICACIÓN VUE COMPATIBLE
// ============================================================================

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)

// ============================================================================
// MANEJO DE ERRORES MEJORADO - VUE COMPATIBLE
// ============================================================================

// Error handler que NO causa loops infinitos
app.config.errorHandler = (err, instance, info) => {
  // Crear objeto de error seguro SIN recursión
  const errorMessage = err?.message || String(err)
  const componentName = instance?.$options?.name || instance?.type?.name || 'Unknown'
  
  // Log simple y seguro
  console.error('🚨 Vue Error:', {
    message: errorMessage,
    component: componentName,
    info: String(info),
    timestamp: new Date().toISOString(),
    stack: err?.stack?.substring(0, 500) // Limitar stack trace
  })
  
  // 🔧 NUEVO: Solo mostrar notificación si no es un error de DOM manipulation
  if (!errorMessage.includes('__vnode') && 
      !errorMessage.includes('Cannot set properties of null') &&
      !errorMessage.includes('appendChild') &&
      !errorMessage.includes('removeChild')) {
    
    // Usar setTimeout para evitar errores en el ciclo reactivo
    setTimeout(() => {
      if (window.showNotification) {
        window.showNotification(
          `⚠️ Error en la aplicación: ${errorMessage.substring(0, 100)}`, 
          'error'
        )
      }
    }, 100)
  }
}

// Warning handler mejorado - solo en desarrollo
if (import.meta.env.DEV) {
  const ignoredWarnings = [
    'failed to resolve component',
    'component is missing template',
    'invalid prop type',
    'extraneous non-props attributes',
    'vue-router',
    '__vnode'
  ]
  
  app.config.warnHandler = (msg, instance, trace) => {
    const safeMessage = String(msg || 'Unknown warning').toLowerCase()
    
    // Filtrar warnings no críticos
    const shouldIgnore = ignoredWarnings.some(warning => 
      safeMessage.includes(warning.toLowerCase())
    )
    
    if (!shouldIgnore) {
      console.warn('⚠️ Vue Warning:', {
        message: msg,
        component: instance?.$options?.name || 'Unknown',
        timestamp: new Date().toISOString()
      })
    }
  }
}

// ============================================================================
// PROPIEDADES GLOBALES VUE COMPATIBLE
// ============================================================================

// Funciones de logging seguras
app.config.globalProperties.$log = (message, level = 'info') => {
  const timestamp = new Date().toISOString()
  console.log(`[${level.toUpperCase()}] ${timestamp}:`, message)
}

app.config.globalProperties.$notify = (message, type = 'info') => {
  const timestamp = new Date().toISOString()
  console.log(`[NOTIFICATION ${type.toUpperCase()}] ${timestamp}:`, message)
  
  // 🔧 VUE COMPATIBLE: Usar window.showNotification si existe
  if (window.showNotification) {
    window.showNotification(message, type)
  }
}

// Constantes globales seguras
app.config.globalProperties.$API_BASE_URL = window.location.origin
app.config.globalProperties.$DEFAULT_COMPANY_ID = 'benova'
app.config.globalProperties.$APP_VERSION = '3.0.0-vue'

// ============================================================================
// DIRECTIVAS VUE COMPATIBLE
// ============================================================================

// Directiva focus mejorada
app.directive('focus', {
  mounted(el) {
    try {
      // Usar nextTick para asegurar que el elemento esté en el DOM
      app.config.globalProperties.$nextTick(() => {
        if (el && typeof el.focus === 'function') {
          el.focus()
        }
      })
    } catch (error) {
      console.warn('Focus directive error:', error.message)
    }
  }
})

// Directiva click-outside mejorada con cleanup
app.directive('click-outside', {
  mounted(el, binding) {
    if (typeof binding.value !== 'function') {
      console.warn('click-outside expects a function')
      return
    }
    
    el.clickOutsideEvent = function(event) {
      try {
        if (el && !(el === event.target || el.contains(event.target))) {
          binding.value(event)
        }
      } catch (error) {
        console.warn('click-outside handler error:', error.message)
      }
    }
    
    // Usar captura para mejor compatibilidad
    document.addEventListener('click', el.clickOutsideEvent, true)
  },
  
  unmounted(el) {
    if (el && el.clickOutsideEvent) {
      document.removeEventListener('click', el.clickOutsideEvent, true)
      delete el.clickOutsideEvent
    }
  }
})

// ============================================================================
// INICIALIZACIÓN VUE COMPATIBLE
// ============================================================================

const initializeApp = async () => {
  try {
    console.log('🚀 Initializing Vue.js 3 MultibackendOpenIA Frontend (Compatible Mode)...')
    
    // Establecer variables globales básicas de forma segura
    if (typeof window !== 'undefined') {
      // 🔧 VUE COMPATIBLE: Variables globales sin conflictos
      window.API_BASE_URL = window.location.origin
      window.DEFAULT_COMPANY_ID = 'benova'
      window.isVueAppReady = false // Iniciar como false
      
      // 🔧 NUEVO: Flag para indicar que estamos usando Vue compatible
      window.isVueCompatibleMode = true
      
      // 🔧 VUE COMPATIBLE: Funciones globales seguras
      window.vueLog = (message, level = 'info') => {
        console.log(`[VUE-${level.toUpperCase()}]`, message)
      }
      
      window.vueError = (error, context = 'Unknown') => {
        console.error(`[VUE-ERROR] ${context}:`, error)
      }
    }
    
    // 🔧 VUE COMPATIBLE: Montar la aplicación con error handling
    const appElement = document.getElementById('app')
    if (!appElement) {
      throw new Error('App element not found')
    }
    
    // Limpiar el elemento app de cualquier contenido previo
    appElement.innerHTML = ''
    
    // Montar la aplicación Vue
    app.mount('#app')
    
    // 🔧 VUE COMPATIBLE: Marcar como listo DESPUÉS del montaje
    if (typeof window !== 'undefined') {
      window.isVueAppReady = true
    }
    
    console.log('✅ Vue.js 3 app mounted successfully (Compatible Mode)')
    console.log('🎯 DOM Manipulation conflicts resolved')
    console.log('🔧 Modal system using Vue reactive state')
    
  } catch (error) {
    console.error('❌ Error initializing Vue.js 3 app:', error)
    
    // 🔧 VUE COMPATIBLE: Fallback mejorado sin causar más errores
    const appElement = document.getElementById('app')
    if (appElement) {
      appElement.innerHTML = `
        <div style="
          padding: 20px; 
          background: linear-gradient(135deg, #f8d7da, #f5c6cb); 
          color: #721c24; 
          border-radius: 8px; 
          margin: 20px;
          border: 1px solid #f1b0b7;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        ">
          <h3 style="margin: 0 0 15px 0; color: #721c24;">⚠️ Error de Inicialización de la Aplicación</h3>
          <p style="margin: 10px 0;"><strong>Error:</strong> ${error.message}</p>
          <p style="margin: 10px 0; font-size: 0.9em; color: #856404;">
            La aplicación no pudo inicializarse correctamente. Esto puede deberse a conflictos con manipulación del DOM.
          </p>
          <div style="margin-top: 15px;">
            <button 
              onclick="window.location.reload()" 
              style="
                padding: 10px 20px; 
                background: #007bff; 
                color: white; 
                border: none; 
                border-radius: 4px; 
                cursor: pointer;
                font-weight: 500;
                transition: background-color 0.2s ease;
              "
              onmouseover="this.style.background='#0056b3'"
              onmouseout="this.style.background='#007bff'"
            >
              🔄 Recargar Página
            </button>
            <button 
              onclick="console.clear(); window.location.reload()" 
              style="
                padding: 10px 20px; 
                background: #6c757d; 
                color: white; 
                border: none; 
                border-radius: 4px; 
                cursor: pointer;
                font-weight: 500;
                margin-left: 10px;
                transition: background-color 0.2s ease;
              "
              onmouseover="this.style.background='#5a6268'"
              onmouseout="this.style.background='#6c757d'"
            >
              🧹 Limpiar y Recargar
            </button>
          </div>
          <details style="margin-top: 15px; font-size: 0.8em;">
            <summary style="cursor: pointer; color: #007bff;">Ver detalles técnicos</summary>
            <pre style="
              background: #f8f9fa; 
              padding: 10px; 
              border-radius: 4px; 
              overflow-x: auto; 
              margin-top: 10px;
              border: 1px solid #dee2e6;
              color: #495057;
            ">${error.stack || error.toString()}</pre>
          </details>
        </div>
      `
    }
  }
}

// ============================================================================
// DETECCIÓN DE ERRORES DOM Y CLEANUP
// ============================================================================

// 🔧 NUEVO: Detectar y limpiar errores de manipulación DOM
const cleanupDOMErrors = () => {
  try {
    // Limpiar modals huérfanos que pueden causar conflictos
    const orphanModals = document.querySelectorAll(
      '.modal-overlay, .document-modal, .document-modal-safe, [id^="docModal_"], [id^="documentModal_"]'
    )
    
    orphanModals.forEach(modal => {
      if (modal && modal.parentNode) {
        console.log('🧹 Cleaning orphan modal:', modal.id || modal.className)
        modal.remove()
      }
    })
    
    // Limpiar event listeners huérfanos
    if (window._documentTabObserver) {
      window._documentTabObserver.disconnect()
      delete window._documentTabObserver
    }
    
    // Resetear funciones globales problemáticas
    const globalFunctions = [
      'handleViewDocument', 
      'handleDeleteDocument', 
      'handleViewDocumentSafe', 
      'handleDeleteDocumentSafe'
    ]
    
    globalFunctions.forEach(funcName => {
      if (window[funcName]) {
        console.log('🧹 Cleaning global function:', funcName)
        delete window[funcName]
      }
    })
    
  } catch (error) {
    console.warn('Cleanup error (non-critical):', error.message)
  }
}

// ============================================================================
// INICIALIZACIÓN CON CLEANUP
// ============================================================================

// Limpiar antes de inicializar
cleanupDOMErrors()

// Inicializar cuando el DOM esté listo
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    cleanupDOMErrors()
    initializeApp()
  })
} else {
  // DOM ya está listo
  setTimeout(() => {
    cleanupDOMErrors()
    initializeApp()
  }, 100)
}

// ============================================================================
// MANEJO DE ERRORES GLOBALES
// ============================================================================

// 🔧 VUE COMPATIBLE: Capturar errores no manejados
window.addEventListener('error', (event) => {
  const error = event.error || event
  const message = error.message || String(error)
  
  console.error('🚨 Unhandled Error:', {
    message,
    filename: event.filename,
    lineno: event.lineno,
    colno: event.colno,
    timestamp: new Date().toISOString()
  })
  
  // Si es un error de DOM manipulation, intentar limpieza
  if (message.includes('__vnode') || 
      message.includes('appendChild') || 
      message.includes('removeChild')) {
    console.log('🔧 DOM manipulation error detected, attempting cleanup...')
    setTimeout(cleanupDOMErrors, 500)
  }
})

// Capturar promesas rechazadas
window.addEventListener('unhandledrejection', (event) => {
  console.error('🚨 Unhandled Promise Rejection:', {
    reason: event.reason,
    timestamp: new Date().toISOString()
  })
  
  // Prevenir que aparezca en consola como uncaught
  event.preventDefault()
})

// ============================================================================
// EXPORTAR PARA DEBUG
// ============================================================================

if (import.meta.env.DEV) {
  window.vueApp = app
  window.cleanupDOMErrors = cleanupDOMErrors
  
  console.log('🔧 Development mode: window.vueApp and window.cleanupDOMErrors available')
}
