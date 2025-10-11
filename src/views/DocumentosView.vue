<!-- src/views/DocumentosView.vue - VERSIÓN CORRECTA CON LAYOUT -->
<template>
  <MainLayout>
    <div class="documents-page">
      <!-- DocumentsTab con todo su contenido -->
      <DocumentsTab />
    </div>
  </MainLayout>
</template>

<script setup>
import { onMounted } from 'vue'
import MainLayout from '@/layouts/MainLayout.vue'
import DocumentsTab from '@/components/documents/DocumentsTab.vue'

onMounted(() => {
  console.log('📄 DocumentosView mounted with MainLayout')
})
</script>

<style scoped>
.documents-page {
  /* Estilos adicionales si los necesitas */
}
</style>
