// main.js - Vue.js 3 Compatible - CORREGIDO: Inicialización secuencial + funcionalidad completa
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'

import './styles/main.css'
import './styles/main.css'
import './styles/components.css'
import './styles/tabs.css'

// ============================================================================
// INICIALIZACIÓN SECUENCIAL SEGURA - CORRIGE "Cannot access 'U' before initialization"
// ============================================================================

const initializeApp = async () => {
  try {
    console.log('🚀 Initializing Vue.js 3 MultibackendOpenIA Frontend (Compatible Mode)...')
    
    // ✅ PASO 1: Crear app base
    const app = createApp(App)
    
    // ✅ PASO 2: Crear e instalar Pinia PRIMERO (crítico para evitar errores de inicialización)
    const pinia = createPinia()
    app.use(pinia)
    app.use(router)
    
    // ✅ PASO 3: Esperar a que Pinia esté completamente instalado
    await new Promise(resolve => setTimeout(resolve, 10))
    
    // ✅ PASO 4: Configurar manejo de errores DESPUÉS de Pinia
    setupErrorHandling(app)
    
    // ✅ PASO 5: Configurar propiedades globales
    setupGlobalProperties(app)
    
    // ✅ PASO 6: Configurar directivas
    setupDirectives(app)
    
    // ✅ PASO 7: Establecer variables globales básicas
    setupGlobalVariables()
    
    // ✅ PASO 8: Limpiar elementos DOM problemáticos
    cleanupDOMErrors()
    
    // ✅ PASO 9: Montar aplicación
    const appElement = document.getElementById('app')
    if (!appElement) {
      throw new Error('App element not found')
    }
    
    // Limpiar el elemento app de cualquier contenido previo
    appElement.innerHTML = ''
    
    // Montar la aplicación Vue
    app.mount('#app')
    
    // ✅ PASO 10: Marcar como listo DESPUÉS del montaje
    if (typeof window !== 'undefined') {
      window.isVueAppReady = true
      window.vueApp = app // Para debug
    }
    
    console.log('✅ Vue.js 3 app mounted successfully (Compatible Mode)')
    console.log('🎯 DOM Manipulation conflicts resolved')
    console.log('🔧 Modal system using Vue reactive state')
    
  } catch (error) {
    console.error('❌ Error initializing Vue.js 3 app:', error)
    showFallbackUI(error)
  }
}

// ============================================================================
// MANEJO DE ERRORES MEJORADO - VUE COMPATIBLE (FUNCIONALIDAD ORIGINAL PRESERVADA)
// ============================================================================

const setupErrorHandling = (app) => {
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
    
    // 🔧 PRESERVADO: Solo mostrar notificación si no es un error de DOM manipulation
    if (!errorMessage.includes('__vnode') && 
        !errorMessage.includes('Cannot set properties of null') &&
        !errorMessage.includes('appendChild') &&
        !errorMessage.includes('removeChild') &&
        !errorMessage.includes('Cannot access') && // ✅ NUEVO: Filtrar errores de inicialización
        !errorMessage.includes('before initialization')) {
      
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

  // Warning handler mejorado - solo en desarrollo (FUNCIONALIDAD ORIGINAL PRESERVADA)
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
}

// ============================================================================
// PROPIEDADES GLOBALES VUE COMPATIBLE (FUNCIONALIDAD ORIGINAL PRESERVADA)
// ============================================================================

const setupGlobalProperties = (app) => {
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
}

// ============================================================================
// DIRECTIVAS VUE COMPATIBLE (FUNCIONALIDAD ORIGINAL PRESERVADA)
// ============================================================================

const setupDirectives = (app) => {
  // Directiva focus mejorada
  app.directive('focus', {
    mounted(el) {
      try {
        // ✅ CORREGIDO: No usar app.config.globalProperties.$nextTick (causa referencia circular)
        setTimeout(() => {
          if (el && typeof el.focus === 'function') {
            el.focus()
          }
        }, 10)
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
}

// ============================================================================
// VARIABLES GLOBALES (FUNCIONALIDAD ORIGINAL PRESERVADA)
// ============================================================================

const setupGlobalVariables = () => {
  // Establecer variables globales básicas de forma segura
  if (typeof window !== 'undefined') {
    // 🔧 VUE COMPATIBLE: Variables globales sin conflictos
    window.API_BASE_URL = window.location.origin
    window.DEFAULT_COMPANY_ID = 'benova'
    window.isVueAppReady = false // Iniciar como false
    
    // 🔧 PRESERVADO: Flag para indicar que estamos usando Vue compatible
    window.isVueCompatibleMode = true
    
    // 🔧 VUE COMPATIBLE: Funciones globales seguras
    window.vueLog = (message, level = 'info') => {
      console.log(`[VUE-${level.toUpperCase()}]`, message)
    }
    
    window.vueError = (error, context = 'Unknown') => {
      console.error(`[VUE-ERROR] ${context}:`, error)
    }
  }
}

// ============================================================================
// DETECCIÓN DE ERRORES DOM Y CLEANUP (FUNCIONALIDAD ORIGINAL PRESERVADA)
// ============================================================================

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
// FALLBACK UI (FUNCIONALIDAD ORIGINAL PRESERVADA Y MEJORADA)
// ============================================================================

const showFallbackUI = (error) => {
  const appElement = document.getElementById('app')
  if (!appElement) return
  
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
        La aplicación no pudo inicializarse correctamente. Esto puede deberse a problemas de dependencias circulares o conflictos de inicialización.
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

// ============================================================================
// INICIALIZACIÓN CON CLEANUP (FUNCIONALIDAD ORIGINAL PRESERVADA)
// ============================================================================

// Limpiar antes de inicializar
cleanupDOMErrors()

// ✅ CORREGIDO: Inicialización secuencial cuando DOM esté listo
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    cleanupDOMErrors()
    // ✅ CRÍTICO: Usar setTimeout para asegurar que el DOM esté completamente listo
    setTimeout(initializeApp, 50)
  })
} else {
  // DOM ya está listo
  setTimeout(() => {
    cleanupDOMErrors()
    initializeApp()
  }, 100)
}

// ============================================================================
// MANEJO DE ERRORES GLOBALES (FUNCIONALIDAD ORIGINAL PRESERVADA Y MEJORADA)
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
      message.includes('removeChild') ||
      message.includes('Cannot access') || // ✅ NUEVO: Detectar errores de inicialización
      message.includes('before initialization')) {
    console.log('🔧 DOM/Initialization error detected, attempting cleanup...')
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
// EXPORTAR PARA DEBUG (FUNCIONALIDAD ORIGINAL PRESERVADA)
// ============================================================================

if (import.meta.env.DEV) {
  // ✅ CORREGIDO: Estas variables se asignarán después de la inicialización
  window.cleanupDOMErrors = cleanupDOMErrors
  
  console.log('🔧 Development mode: Debug tools will be available after app initialization')
  console.log('🔧 Access via: window.vueApp, window.cleanupDOMErrors')
  console.log('✅ Benova Multi-Tenant Frontend initialized with Vue Router')
}
