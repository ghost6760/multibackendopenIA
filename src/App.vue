<!-- src/App.vue - VERSIÓN SIMPLE CON ROUTER -->
<template>
  <div id="app">
    <!-- Solo componentes globales -->
    <LoadingOverlay v-if="appStore.isLoadingOverlay" />
    
    <!-- Router View - Delega a las vistas -->
    <router-view />
    
    <!-- Componentes globales -->
    <AppNotifications />
    <div id="modals-container"></div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useAppStore } from '@/stores/app'
import LoadingOverlay from '@/components/shared/LoadingOverlay.vue'
import AppNotifications from '@/components/shared/AppNotifications.vue'

const appStore = useAppStore()

onMounted(() => {
  console.log('✅ App mounted with router')
  
  // Solo funciones globales BÁSICAS
  if (typeof window !== 'undefined') {
    window.addToLog = appStore.addToLog
    window.showNotification = (msg, type) => {
      // Implementar si tienes useNotifications
    }
  }
})
</script>

<style>
/* Solo estilos globales */
:root {
  --bg-primary: #f7fafc;
  --bg-secondary: #ffffff;
  --text-primary: #2d3748;
  --text-secondary: #718096;
  --border-color: #e2e8f0;
}

#app {
  min-height: 100vh;
  background-color: var(--bg-primary);
}
</style>
