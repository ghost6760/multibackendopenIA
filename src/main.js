// main.js - Inicialización de la Aplicación Vue.js 3
// Migración de multibackendopenia de Vanilla JS a Vue.js 3 + Composition API

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import './styles/main.css'

// ============================================================================
// CONFIGURACIÓN DE LA APLICACIÓN
// ============================================================================

// Crear instancia de la aplicación Vue
const app = createApp(App)

// Configurar Pinia para gestión de estado global
const pinia = createPinia()
app.use(pinia)

// ============================================================================
// PLUGINS Y CONFIGURACIONES GLOBALES
// ============================================================================

// Configuración global para manejo de errores
app.config.errorHandler = (err, instance, info) => {
  console.error('🚨 Vue Error:', {
    error: err,
    component: instance,
    info: info,
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

// Configuración de warnings en desarrollo
if (import.meta.env.DEV) {
  app.config.warnHandler = (msg, instance, trace) => {
    console.warn('⚠️ Vue Warning:', {
      message: msg,
      component: instance,
      trace: trace,
      timestamp: new Date().toISOString()
    })
  }
}

// ============================================================================
// PROPIEDADES GLOBALES DE LA APLICACIÓN
// ============================================================================

// Configurar propiedades globales que pueden ser útiles en todos los componentes
app.config.globalProperties.$log = (message, level = 'info') => {
  console.log(`[${level.toUpperCase()}]`, message)
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

// Constantes globales de la aplicación (migradas desde script.js)
app.config.globalProperties.$API_BASE_URL = window.location.origin
app.config.globalProperties.$DEFAULT_COMPANY_ID = 'benova'

// ============================================================================
// DIRECTIVAS PERSONALIZADAS
// ============================================================================

// Directiva para auto-focus
app.directive('focus', {
  mounted(el) {
    el.focus()
  }
})

// Directiva para click fuera del elemento (útil para modales y dropdowns)
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

// Directiva para tooltips simples
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

// Función para mantener compatibilidad con el script.js original
const initializeGlobalCompatibility = () => {
  // Configurar variables globales básicas que el sistema original espera
  if (typeof window !== 'undefined') {
    // Asegurar que las constantes estén disponibles globalmente
    window.API_BASE_URL = window.location.origin
    window.DEFAULT_COMPANY_ID = 'benova'
    
    // Función helper para verificar si Vue está cargado
    window.isVueAppReady = true
    
    // Event listener para comunicación entre Vue y código legacy
    window.addEventListener('vueAppMounted', () => {
      console.log('✅ Vue.js 3 app mounted and ready')
    })
    
    // Helper para debugging
    window.getVueApp = () => app
    
    // Log de inicialización
    console.log('🔗 Global compatibility layer initialized')
  }
}

// ============================================================================
// MANEJO DE EVENTOS GLOBALES
// ============================================================================

// Configurar event listeners globales que pueden ser necesarios
const setupGlobalEventListeners = () => {
  // Error tracking global para JavaScript nativo
  window.addEventListener('error', (event) => {
    console.error('🚨 Global JavaScript Error:', {
      message: event.error?.message || event.message,
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
      error: event.error,
      timestamp: new Date().toISOString(),
      url: window.location.href
    })
  })
  
  // Error tracking para promises rechazadas
  window.addEventListener('unhandledrejection', (event) => {
    console.error('🚨 Unhandled Promise Rejection:', {
      reason: event.reason,
      promise: event.promise,
      timestamp: new Date().toISOString(),
      url: window.location.href
    })
  })
  
  // Listener para cambios de visibilidad (útil para pausar/reanudar operaciones)
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

// Función de inicialización completa
const initializeApp = async () => {
  try {
    console.log('🚀 Initializing Vue.js 3 MultibackendOpenIA Frontend...')
    
    // Inicializar compatibilidad global
    initializeGlobalCompatibility()
    
    // Configurar event listeners globales
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
    
    // Fallback: mostrar error en el DOM si la app no se puede montar
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
  // Herramientas de desarrollo disponibles en consola
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

// Inicializar la aplicación cuando el DOM esté listo
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeApp)
} else {
  // El DOM ya está listo
  initializeApp()
}
