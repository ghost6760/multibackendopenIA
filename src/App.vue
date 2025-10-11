<!-- src/App.vue -->
<template>
  <div id="app">
    <!-- Loading Overlay Global - Debe estar aquí para todas las vistas -->
    <LoadingOverlay v-if="appStore.isLoadingOverlay" />
    
    <!-- Router View - Renderiza la vista según la ruta -->
    <router-view />
    
    <!-- Notification Container Global - Debe estar aquí para todas las vistas -->
    <AppNotifications />
    
    <!-- Modals Container Global - Debe estar aquí para todas las vistas -->
    <div id="modals-container"></div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { useNotifications } from '@/composables/useNotifications'

// Componentes Globales - Deben estar en App.vue
import LoadingOverlay from '@/components/shared/LoadingOverlay.vue'
import AppNotifications from '@/components/shared/AppNotifications.vue'

// Stores y Composables
const appStore = useAppStore()
const { showNotification } = useNotifications()

// ============================================================================
// INICIALIZACIÓN GLOBAL - Solo lo que TODAS las vistas necesitan
// ============================================================================

/**
 * Configuración global de drag and drop para archivos
 * Esto debe estar en App.vue porque afecta a toda la aplicación
 */
const setupGlobalFileUploadHandlers = () => {
  const preventDefaults = (e) => {
    e.preventDefault()
    e.stopPropagation()
  }
  
  const events = ['dragenter', 'dragover', 'dragleave', 'drop']
  events.forEach(eventName => {
    document.addEventListener(eventName, preventDefaults, false)
  })
  
  appStore.addToLog('Global file upload handlers configured', 'info')
}

// ============================================================================
// LIFECYCLE HOOKS
// ============================================================================

onMounted(async () => {
  console.log('✅ App.vue mounted with router')
  appStore.addToLog('Application root mounted', 'info')
  
  try {
    // Configurar handlers globales
    setupGlobalFileUploadHandlers()
    
    // Sincronizar estado global inicial
    appStore.syncToGlobal()
    
    appStore.addToLog('Global app initialization completed', 'info')
    
  } catch (error) {
    console.error('Error during global app initialization:', error)
    showNotification(`Error en inicialización global: ${error.message}`, 'error')
    appStore.addToLog(`Global app initialization error: ${error.message}`, 'error')
  }
})

onUnmounted(() => {
  appStore.addToLog('Application root unmounting', 'info')
  // Limpiar recursos globales si es necesario
})

// ============================================================================
// EXPONER FUNCIONES GLOBALES - Solo las que TODAS las vistas necesitan
// ============================================================================

onMounted(() => {
  if (typeof window !== 'undefined') {
    // Funciones de utilidad global que todas las vistas pueden necesitar
    window.addToLog = appStore.addToLog
    window.showNotification = showNotification
    
    appStore.addToLog('Global utility functions exposed', 'info')
  }
})

onUnmounted(() => {
  // Limpiar funciones globales al desmontar
  if (typeof window !== 'undefined') {
    const functionsToClean = ['addToLog', 'showNotification']
    functionsToClean.forEach(func => {
      if (window[func]) {
        delete window[func]
      }
    })
  }
})
</script>

<style>
/* ============================================================================
   ESTILOS GLOBALES - Aplicables a toda la aplicación
   ============================================================================ */

/* Variables CSS globales - Si aún no están en main.css */
:root {
  --bg-primary: #f7fafc;
  --bg-secondary: #ffffff;
  --text-primary: #2d3748;
  --text-secondary: #718096;
  --border-color: #e2e8f0;
  --accent-color: #667eea;
  --accent-hover: #5568d3;
  --success-color: #48bb78;
  --error-color: #f56565;
  --warning-color: #ed8936;
}

/* Reset básico */
* {
  box-sizing: border-box;
}

#app {
  min-height: 100vh;
  background-color: var(--bg-primary);
  color: var(--text-primary);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

/* Scrollbar personalizado */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: var(--bg-primary);
}

::-webkit-scrollbar-thumb {
  background: #cbd5e0;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #a0aec0;
}

/* Transiciones globales */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Container de modales - posicionamiento global */
#modals-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 9999;
}

#modals-container > * {
  pointer-events: auto;
}
</style>
