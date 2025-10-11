<!-- src/views/DocumentosView.vue -->
<template>
  <div class="documentos-view">
    <!-- Reutilizar tu componente existente de DocumentsTab -->
    <DocumentsTab v-if="DocumentsTab" />
    
    <div v-else class="loading">
      Cargando componente de documentos...
    </div>
  </div>
</template>

<script setup>
// Importar tu componente existente
let DocumentsTab = null

try {
  const module = await import('@/components/documents/DocumentsTab.vue')
  DocumentsTab = module.default
} catch (e) {
  console.error('Error loading DocumentsTab:', e)
}
</script>

<style scoped>
.documentos-view {
  /* El componente DocumentsTab ya tiene sus estilos */
}

.loading {
  text-align: center;
  padding: 3rem;
  color: #a0aec0;
}
</style>
