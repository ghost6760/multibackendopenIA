<!-- src/views/WorkflowsView.vue - VERSIÓN FINAL -->
<template>
  <MainLayout>
    <div class="workflows-view">
      <!-- Header de la vista específica -->
      <div class="view-header">
        <div class="view-header-content">
          <h2 class="view-title">⚙️ Gestión de Workflows</h2>
          <p class="view-description">
            Crea y administra workflows automatizados para 
            <strong>{{ companyName }}</strong>
          </p>
        </div>
        
        <!-- Breadcrumb/navegación -->
        <nav class="breadcrumb">
          <router-link to="/" class="breadcrumb-link">🏠 Inicio</router-link>
          <span class="breadcrumb-separator">›</span>
          <span class="breadcrumb-current">Workflows</span>
        </nav>
      </div>

      <!-- Contenido principal - WorkflowsTab -->
      <div class="view-content">
        <WorkflowsTab 
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
import { useRoute } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'
import WorkflowsTab from '@/components/workflows/WorkflowsTab.vue'

const appStore = useAppStore()
const route = useRoute()

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
  appStore.addToLog('[WorkflowsView] Content loaded', 'info')
}

// ============================================================================
// LIFECYCLE
// ============================================================================

onMounted(() => {
  console.log('⚙️ WorkflowsView mounted with MainLayout')
  appStore.addToLog('[WorkflowsView] Mounted', 'info')
  
  // Sincronizar el tab activo en el store (para cuando vuelvan a MainAppView)
  appStore.setActiveTab('workflows')
  
  // Actualizar título de la página
  document.title = 'Workflows - Benova Multi-Tenant Backend'
})

onUnmounted(() => {
  console.log('⚙️ WorkflowsView unmounted')
  appStore.addToLog('[WorkflowsView] Unmounted', 'info')
})
</script>

<style scoped>
.workflows-view {
  /* Padding y espaciado ya viene del MainLayout container */
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

/* ============================================================================
   VIEW HEADER - Información contextual de la vista
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
  
  .breadcrumb-link,
  .breadcrumb-current {
    display: none;
  }
  
  .breadcrumb-separator {
    display: none;
  }
}
</style>
