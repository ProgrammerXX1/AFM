<template>
  <div
    class="card"
    :class="{ selected }"
    @click="$emit('click')"
  >
    <div class="preview">
      <img src="../assets/css/docs.png" alt="document preview" />
    </div>
    <div class="info">
      <h4 class="title">{{ document.title }}</h4>
      <p class="type">Тип файла: {{ document.filetype?.toUpperCase() || 'неизвестно' }}</p>
      <p class="date">Создан: {{ formattedDate }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type CaseDocument = {
  id: number
  title: string
  filetype: string
  created_at: string
}

const props = defineProps<{
  document: CaseDocument
  selected?: boolean
}>()

defineEmits(['click'])

const formattedDate = computed(() => {
  const date = new Date(props.document.created_at)
  return isNaN(date.getTime()) ? 'неизвестно' : date.toLocaleDateString('ru-RU')
})
</script>
<style scoped>
.card {
  /* background-color: var(--card-bg, #f9fafb); */
  border-radius: 10px;
  overflow: hidden;
  font-family: 'Segoe UI', sans-serif;
  height: 230px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  transition: background 0.3s, border 0.2s;
  border: 2px solid transparent;
  cursor: pointer;
}

.card:hover {
  background-color: var(--card-hover-bg, #363636);
  box-shadow: 0 4px 10px rgba(94, 87, 87, 0.05);
}

/* ✅ Когда выбрана */
.card.selected {
  border-color: #3b82f6; /* синий */
  background-color: #e0f2fe; /* светло-синий фон */
}

.preview {
  /* background-color: #f0f0f0; */
  height: 110px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.info {
  padding: 10px;
  font-size: 13px;
  color: #222;
}

.title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 4px;
  line-height: 1.2;
}

.type {
  font-size: 12px;
  font-weight: 500;
  color: #444;
  margin-bottom: 2px;
}

.date {
  color: #777;
  font-size: 12px;
}
</style>
