<!-- src/views/HomeView.vue -->
<template>
  <div class="home-view">
    <!-- Header principal -->
    <header class="home-header">
      <div class="header-content">
        <h1 class="home-title">🏢 Benova Multi-Tenant Backend</h1>
        <p class="home-subtitle">Panel de Administración - Sistema Multi-Agente</p>
      </div>
      
      <div class="header-actions">
        <!-- Company Selector -->
        <CompanySelector v-if="CompanySelector" />
        
        <div 
          class="api-key-status" 
          :class="{ 'has-key': appStore.hasApiKey }"
        >
          {{ appStore.hasApiKey ? '✅ API Key' : '⚠️ API Key requerida' }}
        </div>
      </div>
    </header>

    <!-- Sistema de tabs original -->
    <div class="tabs-container">
      <!-- Tab Navigation -->
      <nav class="tabs-nav">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="activeTab = tab.id"
          class="tab-button"
          :class="{ active: activeTab === tab.id }"
        >
          <span class="tab-icon">{{ tab.icon }}</span>
          <span class="tab-label">{{ tab.label }}</span>
        </button>
      </nav>

      <!-- Tab Content -->
      <div class="tabs-content">
        <!-- Dashboard Tab -->
        <div v-show="activeTab === 'dashboard'" class="tab-panel">
          <DashboardTab v-if="DashboardTab" />
        </div>

        <!-- Documents Tab -->
        <div v-show="activeTab === 'documentos'" class="tab-panel">
          <DocumentsTab v-if="DocumentsTab" />
        </div>

        <!-- Conversations Tab -->
        <div v-show="activeTab === 'conversaciones'" class="tab-panel">
          <ConversationsTab v-if="ConversationsTab" />
        </div>

        <!-- Multimedia Tab -->
        <div v-show="activeTab === 'multimedia'" class="tab-panel">
          <MultimediaTab v-if="MultimediaTab" />
        </div>

        <!-- Prompts Tab -->
        <div v-show="activeTab === 'prompts'" class="tab-panel">
          <PromptsTab v-if="PromptsTab" />
        </div>

        <!-- Admin Tab -->
        <div v-show="activeTab === 'administracion'" class="tab-panel">
          <AdminTab v-if="AdminTab" />
        </div>

        <!-- Enterprise Tab -->
        <div v-show="activeTab === 'enterprise'" class="tab-panel">
          <EnterpriseTab v-if="EnterpriseTab" />
        </div>

        <!-- Health Tab -->
        <div v-show="activeTab === 'health'" class="tab-panel">
          <HealthTab v-if="HealthTab" />
        </div>
      </div>
    </div>

    <!-- Quick Links a rutas individuales -->
    <div class="quick-links">
      <h3>🔗 Accesos Rápidos</h3>
      <div class="links-grid">
        <router-link 
          v-for="route in quickLinks" 
          :key="route.path"
          :to="route.path"
          class="quick-link-card"
        >
          <span class="link-icon">{{ route.icon }}</span>
          <span class="link-label">{{ route.label }}</span>
          <span class="link-arrow">→</span>
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

// ============================================================================
// IMPORTAR COMPONENTES EXISTENTES DE TABS
// ============================================================================
let CompanySelector, DashboardTab, DocumentsTab, ConversationsTab
let MultimediaTab, PromptsTab, AdminTab, EnterpriseTab, HealthTab

// Importar dinámicamente tus componentes existentes
try {
  CompanySelector = (await import('@/components/shared/CompanySelector.vue')).default
  DashboardTab = (await import('@/components/dashboard/DashboardTab.vue')).default
  DocumentsTab = (await import('@/components/documents/DocumentsTab.vue')).default
  ConversationsTab = (await import('@/components/conversations/ConversationsTab.vue')).default
  MultimediaTab = (await import('@/components/multimedia/MultimediaTab.vue')).default
  PromptsTab = (await import('@/components/prompts/PromptsTab.vue')).default
  AdminTab = (await import('@/components/admin/AdminTab.vue')).default
  EnterpriseTab = (await import('@/components/enterprise/EnterpriseTab.vue')).default
  HealthTab = (await import('@/components/health/HealthTab.vue')).default
} catch (e) {
  console.warn('Some tab components not found:', e)
}

// ============================================================================
// ESTADO
// ============================================================================
const activeTab = ref('dashboard')

const tabs = [
  { id: 'dashboard', label: 'Dashboard', icon: '📊' },
  { id: 'documentos', label: 'Documentos', icon: '📄' },
  { id: 'conversaciones', label: 'Conversaciones', icon: '💬' },
  { id: 'multimedia', label: 'Multimedia', icon: '🎥' },
  { id: 'prompts', label: 'Prompts', icon: '🎭' },
  { id: 'administracion', label: 'Administración', icon: '🔧' },
  { id: 'enterprise', label: 'Enterprise', icon: '🏢' },
  { id: 'health', label: 'Health Check', icon: '💚' }
]

const quickLinks = computed(() => [
  { path: '/dashboard', label: 'Dashboard', icon: '📊' },
  { path: '/documentos', label: 'Documentos', icon: '📄' },
  { path: '/conversaciones', label: 'Conversaciones', icon: '💬' },
  { path: '/multimedia', label: 'Multimedia', icon: '🎥' },
  { path: '/prompts', label: 'Prompts', icon: '🎭' },
  { path: '/administracion', label: 'Administración', icon: '🔧' },
  { path: '/enterprise', label: 'Enterprise', icon: '🏢' },
  { path: '/health-check', label: 'Health Check', icon: '💚' }
])
</script>

<style scoped>
.home-view {
  min-height: 100vh;
  background: #f7fafc;
}

.home-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.home-title {
  margin: 0;
  font-size: 2rem;
  font-weight: 700;
}

.home-subtitle {
  margin: 0.5rem 0 0;
  opacity: 0.9;
}

.header-actions {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.api-key-status {
  background: rgba(255, 255, 255, 0.2);
  padding: 0.5rem 1rem;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.api-key-status.has-key {
  background: rgba(72, 187, 120, 0.3);
  border-color: rgba(72, 187, 120, 0.5);
}

.tabs-container {
  background: white;
  margin: 2rem;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.tabs-nav {
  display: flex;
  background: #f7fafc;
  border-bottom: 2px solid #e2e8f0;
  padding: 0.5rem;
  gap: 0.25rem;
  overflow-x: auto;
}

.tab-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  background: transparent;
  border: none;
  border-bottom: 3px solid transparent;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
  color: #4a5568;
}

.tab-button:hover {
  background: white;
  color: #667eea;
}

.tab-button.active {
  background: white;
  color: #667eea;
  border-bottom-color: #667eea;
  font-weight: 600;
}

.tab-icon {
  font-size: 1.25rem;
}

.tabs-content {
  padding: 2rem;
}

.tab-panel {
  animation: fadeIn 0.2s;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.quick-links {
  margin: 2rem;
  padding: 2rem;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.quick-links h3 {
  margin: 0 0 1.5rem;
  color: #2d3748;
}

.links-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
}

.quick-link-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.5rem;
  background: #f7fafc;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  text-decoration: none;
  color: #4a5568;
  transition: all 0.2s;
}

.quick-link-card:hover {
  border-color: #667eea;
  background: white;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.1);
}

.link-icon {
  font-size: 1.5rem;
}

.link-label {
  flex: 1;
  font-weight: 500;
}

.link-arrow {
  opacity: 0;
  transition: opacity 0.2s;
}

.quick-link-card:hover .link-arrow {
  opacity: 1;
}

@media (max-width: 768px) {
  .home-header {
    flex-direction: column;
    gap: 1rem;
  }
  
  .tabs-nav {
    overflow-x: scroll;
  }
  
  .tab-label {
    display: none;
  }
  
  .links-grid {
    grid-template-columns: 1fr;
  }
}
</style>
