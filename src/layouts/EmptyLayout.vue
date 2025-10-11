<!-- src/layouts/EmptyLayout.vue -->
<template>
  <div class="empty-layout">
    <slot />
  </div>
</template>

<script setup>
// Layout sin navegación - para Home con todos los tabs
</script>

<style scoped>
.empty-layout {
  min-height: 100vh;
  background: #f7fafc;
}
</style>
