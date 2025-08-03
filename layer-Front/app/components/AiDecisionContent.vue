<template>
  <main class="content">
    <div v-if="isLoading" class="text-center text-gray-500 mt-10">
      ⏳ Генерация постановления...
    </div>

    <div v-else-if="errorMessage" class="text-center text-red-500 mt-10">
      {{ errorMessage }}
    </div>

    <template v-else>
      <template v-for="(section, index) in documentSections" :key="index">
        <!-- Заголовок -->
        <template v-if="section.type === 'title'">
          <h1 class="doc-title" :id="section.id">{{ section.title }}</h1>
          <h2 class="doc-subtitle">{{ section.subtitle }}</h2>
        </template>

        <!-- Параграф -->
        <p v-else-if="section.type === 'paragraph'" class="paragraph">
          {{ section.content }}
        </p>

        <!-- AI блок -->
        <div
          v-else-if="section.type === 'ai'"
          class="ai-block"
          :class="section.variant === 'red' ? 'ai-red' : 'ai-blue'"
          :id="section.id"
        >
          <p>
            <strong>{{ section.article }}</strong> {{ section.content }}<br />
            <span
              :class="section.variant === 'red' ? 'ai-highlight-red' : 'ai-highlight'"
            >
              {{ section.highlight }}
            </span>
          </p>
        </div>
      </template>
    </template>
  </main>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { $fetch } from 'ofetch'
import { useRuntimeConfig } from '#app'
const config = useRuntimeConfig()

const route = useRoute()
const caseId = route.params.case_id?.toString() || '1'

const documentSections = ref<any[]>([])
const isLoading = ref(true)
const errorMessage = ref('')
onMounted(async () => {
  try {
    isLoading.value = true
    const response = await $fetch(`/ask/${caseId}`, {
      baseURL: config.public.apiBase,
      method: 'POST',
      body: {
        question: 'пострадавшие и подозреваемые и их ущерб',
      },
    })

    // ✅ Маппинг полей в ожидаемый формат
    documentSections.value = (response as any[]).map((item, index) => {
      const sectionType = item.ai
        ? 'ai'
        : index === 0
        ? 'title'
        : 'paragraph'

      return {
        type: sectionType,
        id: `section-${index}`,
        title: item.title,
        subtitle: '',
        content: item.paragraph,
        article: item.ai ? '⚖️' : '',
        highlight: item.ai ? item.paragraph.slice(0, 20) + '...' : ''
      }
    })
  } catch (error) {
    console.error('❌ Ошибка при генерации постановления:', error)
    errorMessage.value = '❌ Ошибка генерации. Попробуйте позже.'
  } finally {
    isLoading.value = false
  }
})

</script>

<style scoped>
.content {
  /* background-color: #1e1e1e; */
  padding: 2rem;
  border-radius: 8px;
  color: #f1f1f1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  height: 100%;
  font-family: sans-serif;
  scroll-behavior: smooth;
}

.doc-title {
  font-size: 1.5rem;
  font-weight: bold;
  margin-bottom: 0.5rem;
}

.doc-subtitle {
  font-size: 1rem;
  font-weight: normal;
  margin-bottom: 1.5rem;
  line-height: 1.5;
  color: #ccc;
}

.paragraph {
  font-size: 0.95rem;
  line-height: 1.7;
  margin-bottom: 1rem;
  color: #e5e5e5;
}

.ai-block {
  padding: 1rem;
  border-radius: 8px;
  font-size: 0.95rem;
  margin-bottom: 1.25rem;
  line-height: 1.6;
  border-left: 5px solid;
}

.ai-blue {
  background-color: #0f2d4f;
  border-color: #3b82f6;
}

.ai-red {
  background-color: #3c0d0d;
  border-color: #ef4444;
}

.ai-highlight {
  color: #93c5fd;
  font-weight: 500;
}

.ai-highlight-red {
  color: #f87171;
  font-weight: 500;
}
</style>
