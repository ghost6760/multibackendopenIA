<!-- src/views/MainAppView.vue - VISTA PRINCIPAL -->
<template>
  <MainLayout>
    <!-- Tab Navigation -->
    <TabNavigation 
      :activeTab="appStore.activeTab"
      @tab-changed="handleTabChange"
    />
    
    <!-- Tab Content -->
    <div class="tab-contents">
      <!-- Dashboard Tab -->
      <DashboardTab 
        v-if="appStore.activeTab === 'dashboard'"
        :isActive="appStore.activeTab === 'dashboard'"
        @content-loaded="onTabContentLoaded"
      />
      
      <!-- Documents Tab -->
      <DocumentsTab 
        v-if="appStore.activeTab === 'documents'"
        :isActive="appStore.activeTab === 'documents'"
        @content-loaded="onTabContentLoaded"
      />
      
      <!-- Conversations Tab -->
      <ConversationsTab 
        v-if="appStore.activeTab === 'conversations'"
        :isActive="appStore.activeTab === 'conversations'"
        @content-loaded="onTabContentLoaded"
      />
      
      <!-- Multimedia Tab -->
      <MultimediaTab 
        v-if="appStore.activeTab === 'multimedia'"
        :isActive="appStore.activeTab === 'multimedia'"
        @content-loaded="onTabContentLoaded"
      />
      
      <!-- Prompts Tab -->
      <PromptsTab 
        v-if="appStore.activeTab === 'prompts'"
        :isActive="appStore.activeTab === 'prompts'"
        @content-loaded="onTabContentLoaded"
      />
      
      <!-- Admin Tab -->
      <AdminTab 
        v-if="appStore.activeTab === 'admin'"
        :isActive="appStore.activeTab === 'admin'"
        @content-loaded="onTabContentLoaded"
      />
      
      <!-- Enterprise Tab -->
      <EnterpriseTab 
        v-if="appStore.activeTab === 'enterprise'"
        :isActive="appStore.activeTab === 'enterprise'"
        @content-loaded="onTabContentLoaded"
      />
      
      <!-- Health Tab -->
      <HealthTab 
        v-if="appStore.activeTab === 'health'"
        :isActive="appStore.activeTab === 'health'"
        @content-loaded="onTabContentLoaded"
      />
    </div>
  </MainLayout>
</template>

<script setup>
import { nextTick } from 'vue'
import { useAppStore } from '@/stores/app'
import MainLayout from '@/layouts/MainLayout.vue'

// Components - Shared
import TabNavigation from '@/components/shared/TabNavigation.vue'

// Components - Tab Content
import DashboardTab from '@/components/dashboard/DashboardTab.vue'
import DocumentsTab from '@/components/documents/DocumentsTab.vue'
import ConversationsTab from '@/components/conversations/ConversationsTab.vue'
import MultimediaTab from '@/components/multimedia/MultimediaTab.vue'
import PromptsTab from '@/components/prompts/PromptsTab.vue'
import AdminTab from '@/components/admin/AdminTab.vue'
import EnterpriseTab from '@/components/enterprise/EnterpriseTab.vue'
import HealthTab from '@/components/health/HealthTab.vue'

const appStore = useAppStore()

// ============================================================================
// FUNCIONES - Delegadas a funciones globales de App.vue
// ============================================================================

const handleTabChange = async (tabName) => {
  // Usar función global expuesta por App.vue
  if (typeof window !== 'undefined' && window.switchTab) {
    window.switchTab(tabName)
  } else {
    // Fallback directo
    const success = appStore.setActiveTab(tabName)
    if (success) {
      appStore.syncToGlobal()
      await nextTick()
      appStore.addToLog(`Tab changed to: ${tabName}`, 'info')
    }
  }
}

const onTabContentLoaded = (tabName) => {
  appStore.setLoadingOverlay(false)
  appStore.addToLog(`Tab content loaded: ${tabName}`, 'info')
}
</script>

<style scoped>
.tab-contents {
  margin-top: 20px;
}
</style>
