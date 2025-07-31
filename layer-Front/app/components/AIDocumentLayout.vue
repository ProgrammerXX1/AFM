<template>
  <div class="layout-wrapper">
    <div class="layout-grid">
      <DocumentSidebar />
      <AiDecisionContent />
    </div>
  </div>
</template>

<script setup lang="ts">
import DocumentSidebar from '~/components/DocumentSidebar.vue'
import AiDecisionContent from '~/components/AiDecisionContent.vue'
</script>

<style scoped>
.layout-wrapper {
  height: calc(100vh - 140px);
  padding: 0rem;
  margin-top: -0.3rem;
  box-sizing: border-box;
  display: flex;
  justify-content: center;
  align-items: flex-start;
}

.layout-grid {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 1rem;
  width: 100%;
  max-width: 1400px;
  height: 100%;
}
</style>
