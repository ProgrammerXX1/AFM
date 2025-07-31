<template>
  
  <div class="analysis-wrapper">
    <div class="container">
      <AIDocumentLayout />
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  middleware: ['auth'],
})

import AIDocumentLayout from '~/components/AIDocumentLayout.vue'
</script>

<style scoped>
.analysis-wrapper {
  min-height: 100vh;
  padding-top: 16px;
}

.container {
  max-width: 1280px; /* аналог max-w-7xl */
  margin: 0 auto;
  padding-left: 1rem;
  padding-right: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
</style>
