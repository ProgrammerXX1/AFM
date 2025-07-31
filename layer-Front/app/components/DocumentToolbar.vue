<template>
  <div class="toolbar">
    <div class="info">
      Показаны {{ pageStart + 1 }}–{{ pageEnd }} из {{ total }} вложений
    </div>

    <div class="actions">
      <!-- 🔼 Кнопка загрузки -->
      <button class="icon-btn" title="Загрузить" @click="triggerUpload">⬆️</button>
      <input
        ref="fileInput"
        type="file"
        accept="application/pdf"
        style="display: none"
        multiple
        @change="handleFileUpload"
      />

      <!-- ✏️ Редактирование и удаление -->
      <button class="icon-btn" title="Редактировать" @click="$emit('edit')" :disabled="!hasSelection">✏️</button>
      <button class="icon-btn" title="Удалить" @click="$emit('delete')" :disabled="!hasSelection">🗑️</button>

      <!-- ◀▶ Пагинация -->
      <div class="pagination">
        <button class="icon-btn" @click="prevPage" :disabled="page === 0">◀</button>
        <button class="icon-btn" @click="nextPage" :disabled="(page + 1) * itemsPerPage >= total">▶</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineOptions({ name: 'DocumentToolbar' })

import { ref, watch, computed } from 'vue'
import { $fetch } from 'ofetch'
import { useRuntimeConfig } from '#app';
const config = useRuntimeConfig()

// ✅ Пропсы
const props = defineProps<{
  total: number
  itemsPerPage: number
  caseId: number
}>()

// ✅ Emit
const emit = defineEmits<{
  (e: 'page-change', page: number): void
  (e: 'edit'): void
  (e: 'delete'): void
  (e: 'refresh-documents'): void
}>()

// 📥 Загрузка файла
const fileInput = ref<HTMLInputElement | null>(null)

const triggerUpload = () => {
  fileInput.value?.click()
}

const handleFileUpload = async (event: Event) => {
  const files = (event.target as HTMLInputElement).files
  if (files && files.length > 0) {
    const formData = new FormData()
    for (const file of Array.from(files)) {
      formData.append("files", file)
    }
    const token = localStorage.getItem('token')
    try {
      const response = await $fetch(`/cases/${props.caseId}/documents`, {
        baseURL: config.public.apiBase,
        method: "POST",
        body: formData,
      headers: {
        Authorization: `Bearer ${token}`
        }
      })

      console.log("✅ Успешная загрузка:", response)

      // 🔄 Обновляем список документов
      emit("refresh-documents")

      // ♻️ Очистка input (если нужно загрузить такой же файл снова)
      fileInput.value!.value = ""

    } catch (err) {
      console.error("❌ Ошибка загрузки файла:", err)
    }
  }
}

// 📄 Страницы
const page = ref(0)
const hasSelection = defineModel<boolean>('hasSelection', { default: true })

const prevPage = () => {
  if (page.value > 0) {
    page.value--
    emit('page-change', page.value)
  }
}

const nextPage = () => {
  if ((page.value + 1) * props.itemsPerPage < props.total) {
    page.value++
    emit('page-change', page.value)
  }
}

watch(() => props.total, () => {
  if (page.value * props.itemsPerPage >= props.total) {
    page.value = 0
    emit('page-change', 0)
  }
})

// 📊 Диапазон
const pageStart = computed(() => page.value * props.itemsPerPage)
const pageEnd = computed(() =>
  Math.min((page.value + 1) * props.itemsPerPage, props.total)
)
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  font-size: 13px;
  color: #ccc;
  border-top: 1px solid #374151;
}

.actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.icon-btn {
  border: 1px solid #6b7280;
  background-color: #2d2d2d;
  border-radius: 6px;
  padding: 4px 6px;
  cursor: pointer;
  font-size: 14px;
  color: #eee;
}

.icon-btn:hover {
  background-color: #3b3b3b;
}

.icon-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.pagination {
  display: flex;
  gap: 2px;
}
</style>
