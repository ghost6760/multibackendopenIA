<!-- src/views/PromptsView.vue -->
<template>
  <MainLayout>
    <div class="prompts-view">
      <!-- Header de la vista -->
      <div class="view-header">
        <div class="view-header-content">
          <h2 class="view-title">🎭 Gestión de Prompts</h2>
          <p class="view-description">
            Administra y optimiza prompts del sistema para 
            <strong>{{ companyName }}</strong>
          </p>
        </div>
        
        <!-- Breadcrumb -->
        <nav class="breadcrumb">
          <router-link to="/" class="breadcrumb-link">🏠 Inicio</router-link>
          <span class="breadcrumb-separator">›</span>
          <span class="breadcrumb-current">Prompts</span>
        </nav>
      </div>

      <!-- Contenido principal -->
      <div class="view-content">
        <PromptsTab 
          :isActive="true"
          @content-loaded="handleContentLoaded"
        />
      </div>
    </div>
  </MainLayout>
</template>

<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'
import MainLayout from '@/layouts/MainLayout.vue'
import PromptsTab from '@/components/prompts/PromptsTab.vue'

const appStore = useAppStore()

// ============================================================================
// COMPUTED
// ============================================================================

const companyName = computed(() => {
  return appStore.currentCompanyId 
    ? appStore.currentCompanyId.charAt(0).toUpperCase() + appStore.currentCompanyId.slice(1)
    : 'la empresa seleccionada'
})

// ============================================================================
// FUNCIONES
// ============================================================================

const handleContentLoaded = () => {
  appStore.setLoadingOverlay(false)
  appStore.addToLog('[PromptsView] Content loaded', 'info')
}

// ============================================================================
// LIFECYCLE
// ============================================================================

onMounted(() => {
  console.log('🎭 PromptsView mounted with MainLayout')
  appStore.addToLog('[PromptsView] Mounted', 'info')
  
  // Sincronizar tab activo
  appStore.setActiveTab('prompts')
  
  // Actualizar título
  document.title = 'Prompts - Benova Multi-Tenant Backend'
})

onUnmounted(() => {
  console.log('🎭 PromptsView unmounted')
  appStore.addToLog('[PromptsView] Unmounted', 'info')
})
</script>

<style scoped>
.prompts-view {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

/* ============================================================================
   VIEW HEADER
   ============================================================================ */

.view-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 2rem;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
  color: white;
}

.view-header-content {
  margin-bottom: 1rem;
}

.view-title {
  margin: 0 0 0.5rem;
  font-size: 1.75rem;
  font-weight: 700;
}

.view-description {
  margin: 0;
  font-size: 1rem;
  opacity: 0.95;
}

.view-description strong {
  font-weight: 600;
  text-decoration: underline;
  text-decoration-color: rgba(255, 255, 255, 0.4);
  text-underline-offset: 3px;
}

/* ============================================================================
   BREADCRUMB
   ============================================================================ */

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  opacity: 0.9;
}

.breadcrumb-link {
  color: white;
  text-decoration: none;
  transition: opacity 0.2s;
}

.breadcrumb-link:hover {
  opacity: 0.8;
  text-decoration: underline;
}

.breadcrumb-separator {
  opacity: 0.6;
}

.breadcrumb-current {
  font-weight: 600;
}

/* ============================================================================
   VIEW CONTENT
   ============================================================================ */

.view-content {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  min-height: 400px;
}

/* ============================================================================
   RESPONSIVE
   ============================================================================ */

@media (max-width: 768px) {
  .view-header {
    padding: 1.5rem;
  }
  
  .view-title {
    font-size: 1.5rem;
  }
  
  .view-content {
    padding: 1rem;
  }
  
  .breadcrumb {
    font-size: 0.75rem;
  }
}

@media (max-width: 480px) {
  .view-header {
    padding: 1rem;
  }
  
  .view-title {
    font-size: 1.25rem;
  }
}
</style>
