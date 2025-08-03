<template>
  <div class="container">
    <div v-if="selectedCase">
      <!-- Верхняя панель -->
      <div class="grid-layout">
        <SuspectInfo :caseData="selectedCase" />
        <CaseDetails :caseData="selectedCase" />
      </div>

      <!-- Список документов с фильтрами -->
      <DocumentList :caseId="selectedCase.id" />
    </div>

    <div v-else class="text-center text-red-500 mt-10">
      Дело не выбрано или не найдено.
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import { ref, onMounted } from 'vue'
import SuspectInfo from '~/components/SuspectInfo.vue'
import CaseDetails from '~/components/CaseDetails.vue'
import DocumentList from '~/components/DocumentList/DocumentList.vue'
import { $fetch } from 'ofetch'
import { useRuntimeConfig } from '#app'
import { definePageMeta } from '#imports'

definePageMeta({
  middleware: ['auth'],
})

type CaseOut = {
  id: number
  case_number: string
  surname: string
  name: string
  patronymic: string
  iin: string
  organization: string
  investigator: string
  registration_date: string
  qualification: string
  damage_amount: number
  income_amount: number
  qualification_date: string
  indictment_date: string
  documents: {
    id: number
    title: string
    filetype: string
    content: string
    created_at: string
  }[]
}

const config = useRuntimeConfig()
const route = useRoute()
const selectedCaseId = route.query.id as string

const selectedCase = ref<CaseOut | null>(null)

onMounted(async () => {
  const token = localStorage.getItem('token')

  if (!selectedCaseId) {
    console.warn('ID дела не передан в query')
    return
  }

  try {
    const res = await $fetch<CaseOut>(`/cases/${selectedCaseId}`, {
      baseURL: config.public.apiBase,
      headers: { Authorization: `Bearer ${token}` },
    })

    selectedCase.value = res
  } catch (err) {
    console.error('Ошибка загрузки дела:', err)
  }
})
</script>


<style scoped>
.container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0.5rem;
  box-sizing: border-box;

  background-color: transparent; /* 🌿 теперь он прозрачный */
  color: #111827;
}


.grid-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}
</style>
