<!-- src/views/DocumentosView.vue - VERSIÓN CORREGIDA -->
<template>
  <div class="documentos-view">
    <div class="page-container">
      <!-- Header de la vista -->
      <div class="view-header">
        <h2>📄 Documentos</h2>
        <p class="view-subtitle">Gestión de documentos para {{ companyName }}</p>
      </div>

      <!-- Componente DocumentsTab -->
      <DocumentsTab v-if="isLoaded" />
      
      <!-- Loading State -->
      <div v-else class="loading-state">
        <div class="spinner"></div>
        <p>Cargando componente de documentos...</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useAppStore } from '@/stores/app'
import DocumentsTab from '@/components/documents/DocumentsTab.vue'

const appStore = useAppStore()
const isLoaded = ref(false)

const companyName = computed(() => {
  return appStore.currentCompanyId || 'la empresa seleccionada'
})

onMounted(() => {
  console.log('📄 DocumentosView mounted')
  isLoaded.value = true
})
</script>

<style scoped>
.documentos-view {
  min-height: 100vh;
  background: var(--bg-primary, #f7fafc);
  padding: 2rem;
}

.page-container {
  max-width: 1400px;
  margin: 0 auto;
}

.view-header {
  margin-bottom: 2rem;
  padding: 1.5rem;
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.view-header h2 {
  margin: 0 0 0.5rem;
  color: #2d3748;
  font-size: 1.75rem;
}

.view-subtitle {
  margin: 0;
  color: #718096;
  font-size: 1rem;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem;
  text-align: center;
  color: #a0aec0;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #edf2f7;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Responsive */
@media (max-width: 768px) {
  .documentos-view {
    padding: 1rem;
  }
  
  .view-header h2 {
    font-size: 1.5rem;
  }
}
</style>
