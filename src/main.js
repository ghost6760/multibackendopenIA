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
// MANEJO DE ERRORES SIMPLIFICADO - SIN LOOPS INFINITOS
// ============================================================================

// Error handler simplificado para evitar loops infinitos
app.config.errorHandler = (err, instance, info) => {
  // Crear objeto de error seguro SIN recursión
  const errorMessage = err?.message || String(err)
  const componentName = instance?.$options?.name || instance?.type?.name || 'Unknown'
  
  // Log simple sin llamadas a funciones que pueden fallar
  console.error('🚨 Vue Error:', {
    message: errorMessage,
    component: componentName,
    info: String(info),
    timestamp: new Date().toISOString()
  })
  
  // NO llamar a funciones que pueden crear loops
  // NO usar window.addToLog
  // NO usar window.showNotification
}

// Warning handler solo en desarrollo - SIMPLIFICADO
if (import.meta.env.DEV) {
  const ignoredWarnings = [
    'failed to resolve component',
    'component is missing template',
    'invalid prop type'
  ]
  
  app.config.warnHandler = (msg, instance, trace) => {
    const safeMessage = String(msg || 'Unknown warning').toLowerCase()
    
    // Filtrar warnings no críticos
    const shouldIgnore = ignoredWarnings.some(warning => 
      safeMessage.includes(warning.toLowerCase())
    )
    
    if (!shouldIgnore) {
      console.warn('⚠️ Vue Warning:', msg)
    }
  }
}

// ============================================================================
// PROPIEDADES GLOBALES SIMPLIFICADAS
// ============================================================================

app.config.globalProperties.$log = (message, level = 'info') => {
  console.log(`[${level.toUpperCase()}]`, message)
}

app.config.globalProperties.$notify = (message, type = 'info') => {
  console.log(`[NOTIFICATION ${type.toUpperCase()}]`, message)
}

// Constantes globales
app.config.globalProperties.$API_BASE_URL = window.location.origin
app.config.globalProperties.$DEFAULT_COMPANY_ID = 'benova'

// ============================================================================
// DIRECTIVAS SIMPLIFICADAS
// ============================================================================

app.directive('focus', {
  mounted(el) {
    el.focus?.()
  }
})

app.directive('click-outside', {
  mounted(el, binding) {
    el.clickOutsideEvent = function(event) {
      if (!(el === event.target || el.contains(event.target))) {
        binding.value?.(event)
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

// ============================================================================
// INICIALIZACIÓN SIMPLIFICADA
// ============================================================================

const initializeApp = async () => {
  try {
    console.log('🚀 Initializing Vue.js 3 MultibackendOpenIA Frontend...')
    
    // Establecer variables globales básicas
    if (typeof window !== 'undefined') {
      window.API_BASE_URL = window.location.origin
      window.DEFAULT_COMPANY_ID = 'benova'
      window.isVueAppReady = true
    }
    
    // Montar la aplicación Vue
    app.mount('#app')
    
    console.log('✅ Vue.js 3 app mounted successfully')
    console.log('🎯 Migration from Vanilla JS to Vue.js 3 completed')
    
  } catch (error) {
    console.error('❌ Error initializing Vue.js 3 app:', error)
    
    // Fallback simple
    const appElement = document.getElementById('app')
    if (appElement) {
      appElement.innerHTML = `
        <div style="padding: 20px; background: #f8d7da; color: #721c24; border-radius: 4px; margin: 20px;">
          <h3>Error Initializing Application</h3>
          <p><strong>Error:</strong> ${error.message}</p>
          <button onclick="window.location.reload()" style="padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">
            🔄 Refresh Page
          </button>
        </div>
      `
    }
  }
}

// Inicializar cuando el DOM esté listo
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeApp)
} else {
  initializeApp()
}
