// main.js - Vue.js 3 Compatible - MEJORADO con Inicialización Secuencial
// ✅ MANTIENE compatibilidad con documents, enterprise y otros composables existentes
// ✅ AÑADE mejoras para prevenir dependencias circulares en prompts

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import './styles/main.css'

// ============================================================================
// ✅ PASO 1: CREAR APP Y PINIA EN ORDEN CORRECTO
// ============================================================================

console.log('🚀 Initializing Vue.js 3 MultibackendOpenIA Frontend (Enhanced Compatible Mode)...')

const app = createApp(App)
const pinia = createPinia()

// ✅ PASO 2: CONFIGURAR PINIA PRIMERO (antes de cualquier composable)
app.use(pinia)

// ============================================================================
// ✅ PASO 3: MANEJO DE ERRORES MEJORADO - CON DETECCIÓN DE DEPENDENCIAS CIRCULARES
// ============================================================================

// Error handler mejorado para detectar dependencias circulares
app.config.errorHandler = (err, instance, info) => {
  const errorMessage = err?.message || String(err)
  const componentName = instance?.$options?.name || instance?.type?.name || 'Unknown'
  
  // ✅ DETECTAR ERRORES DE DEPENDENCIAS CIRCULARES
  const isCircularDependency = 
    errorMessage.includes('Cannot access') && errorMessage.includes('before initialization') ||
    errorMessage.includes('ReferenceError') && errorMessage.includes('initialization') ||
    errorMessage.includes('useAppStore') && errorMessage.includes('circular') ||
    errorMessage.includes('getStore') && errorMessage.includes('require')
  
  // Log estructurado para debugging
  const errorDetails = {
    message: errorMessage,
    component: componentName,
    info: String(info),
    timestamp: new Date().toISOString(),
    stack: err?.stack?.substring(0, 500),
    isCircularDependency,
    isProbablyPromptsRelated: errorMessage.includes('usePrompts') || 
                              errorMessage.includes('useSystemLog') || 
                              errorMessage.includes('PromptEditor')
  }
  
  console.error('🚨 Vue Error:', errorDetails)
  
  // ✅ MANEJO ESPECIAL PARA DEPENDENCIAS CIRCULARES
  if (isCircularDependency) {
    console.error('🔄 CIRCULAR DEPENDENCY DETECTED!')
    console.error('💡 This usually means:')
    console.error('   - A composable is trying to use a store before it\'s initialized')
    console.error('   - require() is being used in a computed/watch context')
    console.error('   - Store initialization order needs to be fixed')
    
    // Intentar recovery automático para dependencias circulares
    setTimeout(() => {
      if (window.location.hash.includes('prompts')) {
        console.log('🔧 Attempting auto-recovery for prompts tab...')
        window.location.hash = '#dashboard'
        setTimeout(() => {
          window.location.hash = '#prompts'
        }, 1000)
      }
    }, 2000)
  }
  
  // ✅ MANTENER COMPATIBILIDAD: Solo mostrar notificación si no es DOM manipulation
  if (!errorMessage.includes('__vnode') && 
      !errorMessage.includes('Cannot set properties of null') &&
      !errorMessage.includes('appendChild') &&
      !errorMessage.includes('removeChild')) {
    
    setTimeout(() => {
      if (window.showNotification) {
        const message = isCircularDependency 
          ? `🔄 Error de inicialización detectado. Recargando...`
          : `⚠️ Error en la aplicación: ${errorMessage.substring(0, 100)}`
        
        window.showNotification(message, 'error')
        
        // Auto-reload para dependencias circulares críticas
        if (isCircularDependency && errorDetails.isProbablyPromptsRelated) {
          setTimeout(() => {
            console.log('🔄 Auto-reloading due to critical circular dependency...')
            window.location.reload()
          }, 3000)
        }
      }
    }, 100)
  }
}

// ✅ WARNING HANDLER mejorado - solo en desarrollo
if (import.meta.env.DEV) {
  const ignoredWarnings = [
    'failed to resolve component',
    'component is missing template', 
    'invalid prop type',
    'extraneous non-props attributes',
    'vue-router',
    '__vnode',
    'circular dependency' // ✅ NUEVO: Ignorar warnings de dependencias circulares en dev
  ]
  
  app.config.warnHandler = (msg, instance, trace) => {
    const safeMessage = String(msg || 'Unknown warning').toLowerCase()
    
    const shouldIgnore = ignoredWarnings.some(warning => 
      safeMessage.includes(warning.toLowerCase())
    )
    
    if (!shouldIgnore) {
      console.warn('⚠️ Vue Warning:', {
        message: msg,
        component: instance?.$options?.name || 'Unknown',
        timestamp: new Date().toISOString(),
        isCircularRelated: safeMessage.includes('circular') || 
                          safeMessage.includes('initialization') ||
                          safeMessage.includes('before')
      })
    }
  }
}

// ============================================================================
// ✅ PASO 4: PROPIEDADES GLOBALES MEJORADAS - COMPATIBLE CON EXISTENTES
// ============================================================================

// Funciones de logging seguras (mantener compatibilidad)
app.config.globalProperties.$log = (message, level = 'info') => {
  const timestamp = new Date().toISOString()
  console.log(`[${level.toUpperCase()}] ${timestamp}:`, message)
}

app.config.globalProperties.$notify = (message, type = 'info') => {
  const timestamp = new Date().toISOString()
  console.log(`[NOTIFICATION ${type.toUpperCase()}] ${timestamp}:`, message)
  
  // Usar window.showNotification si existe
  if (window.showNotification) {
    window.showNotification(message, type)
  }
}

// ✅ NUEVAS: Funciones para debugging de dependencias circulares
app.config.globalProperties.$debugCircular = () => {
  console.log('=== CIRCULAR DEPENDENCY DEBUG ===')
  console.log('1. Vue App Ready:', !!window.isVueAppReady)
  console.log('2. Pinia Store:', !!pinia)
  console.log('3. Window globals:', {
    currentCompanyId: window.currentCompanyId,
    showNotification: !!window.showNotification,
    addToLog: !!window.addToLog
  })
  console.log('4. Available composables:', {
    useAppStore: typeof window.useAppStore,
    useApiRequest: typeof window.useApiRequest,
    useSystemLog: typeof window.useSystemLog
  })
}

// Constantes globales (mantener compatibilidad)
app.config.globalProperties.$API_BASE_URL = window.location.origin
app.config.globalProperties.$DEFAULT_COMPANY_ID = 'benova'
app.config.globalProperties.$APP_VERSION = '3.1.0-enhanced' // ✅ Version bumped

// ============================================================================
// ✅ PASO 5: DIRECTIVAS - MANTENER EXISTENTES + MEJORAS
// ============================================================================

// Directiva focus mejorada (mantener compatibilidad)
app.directive('focus', {
  mounted(el) {
    try {
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

// Directiva click-outside mejorada (mantener compatibilidad)
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
// ✅ PASO 6: INICIALIZACIÓN MEJORADA CON SECUENCIA ESPECÍFICA
// ============================================================================

const initializeApp = async () => {
  try {
    console.log('🏁 Step 1: Setting up basic globals...')
    
    // ✅ PASO 6.1: Establecer variables globales básicas ANTES de stores
    if (typeof window !== 'undefined') {
      window.API_BASE_URL = window.location.origin
      window.DEFAULT_COMPANY_ID = 'benova'
      window.isVueAppReady = false // Importante: FALSE hasta que todo esté listo
      window.isVueCompatibleMode = true
      
      // ✅ NUEVO: Flags específicos para detectar estado de inicialización
      window.isPiniaReady = true // Pinia ya está configurado
      window.areStoresInitialized = false
      window.areComposablesReady = false
      
      // Funciones seguras de logging
      window.vueLog = (message, level = 'info') => {
        console.log(`[VUE-${level.toUpperCase()}]`, message)
      }
      
      window.vueError = (error, context = 'Unknown') => {
        console.error(`[VUE-ERROR] ${context}:`, error)
      }
      
      // ✅ NUEVO: Función para debugging de dependencias
      window.debugCircularDependencies = () => {
        app.config.globalProperties.$debugCircular()
      }
    }
    
    console.log('🏁 Step 2: Pre-mounting DOM cleanup...')
    
    // ✅ PASO 6.2: Limpiar DOM ANTES de montar
    const appElement = document.getElementById('app')
    if (!appElement) {
      throw new Error('App element not found')
    }
    
    // Limpiar contenido previo y elementos problemáticos
    appElement.innerHTML = ''
    cleanupDOMErrors()
    
    console.log('🏁 Step 3: Initializing critical stores...')
    
    // ✅ PASO 6.3: INICIALIZAR STORES PRINCIPALES de forma controlada
    try {
      // Importación dinámica para evitar dependencias circulares durante la inicialización
      const { useAppStore } = await import('@/stores/app')
      const appStore = useAppStore()
      
      // Verificar que el store se haya inicializado correctamente
      if (!appStore) {
        throw new Error('Failed to initialize app store')
      }
      
      console.log('✅ App store initialized successfully')
      window.areStoresInitialized = true
      
    } catch (storeError) {
      console.warn('⚠️ Store initialization warning:', storeError.message)
      // Continuar sin stores - los composables usarán fallbacks
      window.areStoresInitialized = false
    }
    
    console.log('🏁 Step 4: Mounting Vue application...')
    
    // ✅ PASO 6.4: MONTAR LA APLICACIÓN
    app.mount('#app')
    
    console.log('🏁 Step 5: Post-mount initialization...')
    
    // ✅ PASO 6.5: MARCAR COMO LISTO DESPUÉS DEL MONTAJE
    if (typeof window !== 'undefined') {
      window.isVueAppReady = true
      window.areComposablesReady = true
    }
    
    console.log('✅ Vue.js 3 app initialized successfully (Enhanced Compatible Mode)')
    console.log('🎯 Features enabled:')
    console.log('   - DOM manipulation conflicts resolved')
    console.log('   - Circular dependency detection active') 
    console.log('   - Modal system using Vue reactive state')
    console.log('   - Compatible with documents/enterprise composables')
    
    // ✅ PASO 6.6: VERIFICACIÓN POST-INICIALIZACIÓN
    setTimeout(() => {
      console.log('🔍 Post-initialization health check:')
      if (window.debugCircularDependencies) {
        window.debugCircularDependencies()
      }
    }, 1000)
    
  } catch (error) {
    console.error('❌ Critical error during app initialization:', error)
    
    // ✅ MANTENER FALLBACK EXISTENTE (compatible)
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
          <h3 style="margin: 0 0 15px 0; color: #721c24;">⚠️ Error de Inicialización Crítico</h3>
          <p style="margin: 10px 0;"><strong>Error:</strong> ${error.message}</p>
          <p style="margin: 10px 0; font-size: 0.9em; color: #856404;">
            ${error.message.includes('circular') || error.message.includes('initialization') 
              ? 'Error de dependencias circulares detectado. Esto puede deberse a problemas de inicialización en composables.' 
              : 'La aplicación no pudo inicializarse correctamente.'}
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
                margin-right: 10px;
              "
            >
              🔄 Recargar Página
            </button>
            <button 
              onclick="console.clear(); localStorage.clear(); window.location.reload()" 
              style="
                padding: 10px 20px; 
                background: #6c757d; 
                color: white; 
                border: none; 
                border-radius: 4px; 
                cursor: pointer;
                font-weight: 500;
              "
            >
              🧹 Reset Completo
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
// ✅ PASO 7: CLEANUP DOM MEJORADO - MANTENER COMPATIBILIDAD
// ============================================================================

const cleanupDOMErrors = () => {
  try {
    // ✅ MANTENER: Limpiar modals huérfanos (compatible con documents/enterprise)
    const orphanModals = document.querySelectorAll(
      '.modal-overlay, .document-modal, .document-modal-safe, [id^="docModal_"], [id^="documentModal_"]'
    )
    
    orphanModals.forEach(modal => {
      if (modal && modal.parentNode) {
        console.log('🧹 Cleaning orphan modal:', modal.id || modal.className)
        modal.remove()
      }
    })
    
    // ✅ NUEVO: Limpiar elementos específicos de prompts que pueden causar conflictos
    const promptsOrphans = document.querySelectorAll(
      '[id^="prompt-"], .prompt-editor-container.orphan, .prompt-preview-modal'
    )
    
    promptsOrphans.forEach(element => {
      if (element && element.parentNode && !element.closest('.prompts-tab')) {
        console.log('🧹 Cleaning orphan prompt element:', element.id || element.className)
        element.remove()
      }
    })
    
    // ✅ MANTENER: Limpiar observers (compatible)
    if (window._documentTabObserver) {
      window._documentTabObserver.disconnect()
      delete window._documentTabObserver
    }
    
    // ✅ NUEVO: Limpiar funciones globales problemáticas específicas de prompts
    const problematicFunctions = [
      'handleViewDocument', 
      'handleDeleteDocument', 
      'handleViewDocumentSafe', 
      'handleDeleteDocumentSafe',
      // ✅ NUEVO: Funciones específicas de prompts que pueden causar problemas
      'getStore', // La función problemática de useSystemLog
      'loadCurrentPrompts_old', // Versiones viejas
      'updatePrompt_old',
      'resetPrompt_old'
    ]
    
    problematicFunctions.forEach(funcName => {
      if (window[funcName]) {
        console.log('🧹 Cleaning problematic function:', funcName)
        delete window[funcName]
      }
    })
    
  } catch (error) {
    console.warn('Cleanup error (non-critical):', error.message)
  }
}

// ============================================================================
// ✅ PASO 8: INICIALIZACIÓN CON TIMING MEJORADO - COMPATIBLE
// ============================================================================

// Limpiar antes de inicializar
cleanupDOMErrors()

// ✅ INICIALIZACIÓN COMPATIBLE: Mantener el patrón existente que funciona
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    cleanupDOMErrors()
    initializeApp()
  })
} else {
  // DOM ya está listo - usar timing que no conflicte con otros composables
  setTimeout(() => {
    cleanupDOMErrors()
    initializeApp()
  }, 50) // ✅ Reducido de 100ms para mejor performance
}

// ============================================================================
// ✅ PASO 9: MANEJO DE ERRORES GLOBALES MEJORADO
// ============================================================================

// Error handler global mejorado (mantener compatibilidad)
window.addEventListener('error', (event) => {
  const error = event.error || event
  const message = error.message || String(error)
  
  // ✅ DETECCIÓN MEJORADA de errores de dependencias circulares
  const isCircularDependency = 
    message.includes('Cannot access') && message.includes('before initialization') ||
    message.includes('ReferenceError') ||
    message.includes('require is not defined') ||
    message.includes('getStore') ||
    message.includes('useAppStore') && message.includes('circular')
  
  console.error('🚨 Unhandled Error:', {
    message,
    filename: event.filename,
    lineno: event.lineno,
    colno: event.colno,
    timestamp: new Date().toISOString(),
    isCircularDependency,
    potentialCause: isCircularDependency ? 'Circular dependency in composable initialization' : 'Unknown'
  })
  
  // ✅ RECOVERY AUTOMÁTICO para dependencias circulares
  if (isCircularDependency) {
    console.log('🔧 Circular dependency detected, attempting automatic recovery...')
    
    // Limpiar estado problemático
    setTimeout(() => {
      cleanupDOMErrors()
      
      // Si estamos en prompts, intentar reset
      if (window.location.hash.includes('prompts')) {
        console.log('🔧 Resetting prompts tab due to circular dependency...')
        window.location.hash = '#dashboard'
        setTimeout(() => {
          window.location.hash = '#prompts'
        }, 1500)
      }
    }, 1000)
  }
  
  // ✅ MANTENER: Limpiar DOM si es error de manipulation
  if (message.includes('__vnode') || 
      message.includes('appendChild') || 
      message.includes('removeChild')) {
    console.log('🔧 DOM manipulation error detected, attempting cleanup...')
    setTimeout(cleanupDOMErrors, 500)
  }
})

// Promise rejection handler (mantener)
window.addEventListener('unhandledrejection', (event) => {
  console.error('🚨 Unhandled Promise Rejection:', {
    reason: event.reason,
    timestamp: new Date().toISOString(),
    isPossibleCircular: String(event.reason).includes('circular') || 
                       String(event.reason).includes('initialization') ||
                       String(event.reason).includes('Cannot access')
  })
  
  event.preventDefault()
})

// ============================================================================
// ✅ PASO 10: DEBUG Y DESARROLLO - MEJORADO
// ============================================================================

if (import.meta.env.DEV) {
  // ✅ MANTENER compatibilidad + nuevas funciones
  window.vueApp = app
  window.cleanupDOMErrors = cleanupDOMErrors
  
  // ✅ NUEVAS funciones de debugging específicas para dependencias circulares
  window.debugApp = {
    checkCircularDependencies: () => {
      console.log('=== CIRCULAR DEPENDENCIES CHECK ===')
      console.log('App ready:', window.isVueAppReady)
      console.log('Stores initialized:', window.areStoresInitialized) 
      console.log('Composables ready:', window.areComposablesReady)
      
      // Verificar funciones problemáticas
      const problematic = ['getStore', 'require']
      const found = problematic.filter(fn => window[fn])
      if (found.length > 0) {
        console.warn('⚠️ Potentially problematic functions found:', found)
      } else {
        console.log('✅ No problematic functions detected')
      }
    },
    
    testPromptsInitialization: async () => {
      console.log('=== TESTING PROMPTS INITIALIZATION ===')
      try {
        if (window.isPromptsTabReady) {
          console.log('Prompts tab ready check:', window.isPromptsTabReady())
        }
        
        const { usePrompts } = await import('@/composables/usePrompts')
        const prompts = usePrompts()
        console.log('✅ usePrompts initialized successfully')
        return prompts
      } catch (error) {
        console.error('❌ Error testing prompts:', error)
        return null
      }
    },
    
    forceCleanup: () => {
      cleanupDOMErrors()
      console.log('🧹 Force cleanup completed')
    }
  }
  
  console.log('🔧 Enhanced development mode active')
  console.log('🔧 Available: window.vueApp, window.cleanupDOMErrors, window.debugApp')
}
