<!-- src/layouts/MainLayout.vue -->
<template>
  <div class="main-layout">
    <!-- Header -->
    <header class="app-header">
      <div class="header-content">
        <div class="header-branding" @click="$router.push('/')">
          <h1 class="app-title">🏢 Benova Multi-Tenant Backend</h1>
          <p class="app-subtitle">Panel de Administración - Sistema Multi-Agente</p>
        </div>
      </div>
      
      <div class="header-actions">
        <!-- Company Selector - Reutilizar tu componente existente -->
        <CompanySelector v-if="CompanySelector" />
        
        <!-- API Key indicator -->
        <div 
          class="api-key-status" 
          :class="{ 'has-key': appStore.hasApiKey }"
          :title="appStore.hasApiKey ? 'API Key configurada' : 'API Key requerida'"
        >
          {{ appStore.hasApiKey ? '✅ API Key' : '⚠️ API Key requerida' }}
        </div>
      </div>
    </header>

    <!-- Navigation Tabs -->
    <nav class="tabs-navigation">
      <!-- Link a Home (todos los tabs) -->
      <router-link to="/" class="tab-link tab-link-home">
        <span class="tab-icon">🏠</span>
        <span class="tab-label">Inicio</span>
      </router-link>
      
      <!-- Links individuales -->
      <router-link 
        v-for="route in navigationRoutes" 
        :key="route.path"
        :to="route.path"
        class="tab-link"
        :class="{ 
          'disabled': route.meta?.requiresCompany && !appStore.currentCompanyId 
        }"
      >
        <span class="tab-icon">{{ route.meta?.icon }}</span>
        <span class="tab-label">{{ route.meta?.label }}</span>
      </router-link>
    </nav>

    <!-- Main Content -->
    <main class="main-content">
      <slot />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { navigationRoutes } from '@/router'

// Importar CompanySelector si existe
let CompanySelector = null
try {
  const module = await import('@/components/shared/CompanySelector.vue')
  CompanySelector = module.default
} catch (e) {
  console.warn('CompanySelector not found, skipping...')
}

const router = useRouter()
const appStore = useAppStore()
</script>

<style scoped>
.main-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f7fafc;
}

.app-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 1.5rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.header-branding {
  cursor: pointer;
}

.app-title {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 700;
}

.app-subtitle {
  margin: 0.25rem 0 0;
  font-size: 0.875rem;
  opacity: 0.9;
}

.header-actions {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.api-key-status {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 0.875rem;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.api-key-status.has-key {
  background: rgba(72, 187, 120, 0.3);
  border-color: rgba(72, 187, 120, 0.5);
}

.tabs-navigation {
  display: flex;
  background: white;
  border-bottom: 2px solid #e2e8f0;
  padding: 0 1rem;
  gap: 0.25rem;
  overflow-x: auto;
}

.tab-link {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem 1.25rem;
  text-decoration: none;
  color: #4a5568;
  border-bottom: 3px solid transparent;
  transition: all 0.2s;
  white-space: nowrap;
}

.tab-link-home {
  background: rgba(102, 126, 234, 0.05);
}

.tab-link:hover:not(.disabled) {
  background: #f7fafc;
  color: #667eea;
}

.tab-link.router-link-active {
  color: #667eea;
  border-bottom-color: #667eea;
  background: #f7fafc;
  font-weight: 600;
}

.tab-link.disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

.tab-icon {
  font-size: 1.25rem;
}

.main-content {
  flex: 1;
  padding: 2rem;
  max-width: 1600px;
  width: 100%;
  margin: 0 auto;
}

@media (max-width: 768px) {
  .app-header {
    flex-direction: column;
    gap: 1rem;
  }
  
  .tabs-navigation {
    overflow-x: scroll;
  }
  
  .tab-label {
    display: none;
  }
  
  .tab-icon {
    font-size: 1.5rem;
  }
}
</style>
