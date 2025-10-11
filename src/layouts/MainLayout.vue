<!-- src/layouts/MainLayout.vue - UI COMPARTIDA -->
<template>
  <div class="main-layout">
    <!-- Container -->
    <div class="container">
      <!-- Header -->
      <div class="header">
        <router-link to="/" class="header-link">
          <h1>🏥 Benova Multi-Tenant Backend</h1>
          <p class="subtitle">Panel de Administración - Sistema Multi-Agente</p>
        </router-link>
      </div>
      
      <!-- Company Selector y API Key Status -->
      <div class="company-selector">
        <CompanySelector />
        <ApiKeyStatus />
      </div>
      
      <!-- Slot para contenido específico de cada vista -->
      <slot />
      
      <!-- System Log (si está visible) -->
      <SystemLog v-if="showSystemLog" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useAppStore } from '@/stores/app'
import CompanySelector from '@/components/shared/CompanySelector.vue'
import ApiKeyStatus from '@/components/shared/ApiKeyStatus.vue'
import SystemLog from '@/components/shared/SystemLog.vue'

const appStore = useAppStore()

// Leer del estado global (App.vue lo maneja)
const showSystemLog = computed(() => {
  return typeof window !== 'undefined' && window.showSystemLog === true
})
</script>

<style scoped>
.main-layout {
  min-height: 100vh;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

.header {
  text-align: center;
  margin-bottom: 30px;
  padding: 20px;
  background: var(--bg-secondary);
  border-radius: 12px;
  border: 1px solid var(--border-color);
}

.header-link {
  text-decoration: none;
  color: inherit;
}

.header h1 {
  margin: 0 0 10px 0;
  font-size: 2.5em;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.subtitle {
  margin: 0;
  color: var(--text-secondary);
  font-size: 1.1em;
}

.company-selector {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  padding: 15px;
  background: var(--bg-secondary);
  border-radius: 8px;
  border: 1px solid var(--border-color);
  flex-wrap: wrap;
  gap: 15px;
}

/* Responsive */
@media (max-width: 768px) {
  .container {
    padding: 10px;
  }
  
  .header h1 {
    font-size: 2em;
  }
  
  .company-selector {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
