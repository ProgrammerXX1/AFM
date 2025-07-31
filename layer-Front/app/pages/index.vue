<template>
  
  <div class="max-w-7xl mx-auto px-2 py-1">
    <LegalAIIcon />
    <SearchBar />

    <!-- 📁 Дела в производстве -->
    <section class="mt-2">
      <div class="section-header">
        <h2 class="section-title">Дела в производстве</h2>
        <div class="nav-buttons">
          <button @click="prevCasePage" :disabled="casePage === 0">⬅️</button>
          <button @click="nextCasePage" :disabled="(casePage + 1) * itemsPerPage >= cases.length">➡️</button>
        </div>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <CaseCard
          v-for="(item, index) in visibleCases"
          :key="index"
          :id="String(item.id)" 
          :number="item.case_number"
          :date="formatDate(item.registration_date)"    
        />
      </div>
    </section>

    <!-- 📄 Недавние документы -->
    <section class="mt-2">
      <div class="section-header">
        <h2 class="section-title">Недавние документы</h2>
        <div class="nav-buttons">
          <button @click="prevDocPage" :disabled="docPage === 0">⬅️</button>
          <button @click="nextDocPage" :disabled="(docPage + 1) * itemsPerPage >= documents.length">➡️</button>
        </div>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <DocumentCard
          v-for="(doc, index) in visibleDocuments"
          :key="index"
          :number="doc.case_number"
          :title="doc.title"
          :date="formatDate(doc.created_at)"
        />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import SearchBar from '~/components/SearchBar.vue'
import CaseCard from '~/components/CaseCard.vue'
import DocumentCard from '~/components/DocumentCard.vue'
import LegalAIIcon from '~/components/animations/LegalALIcon.vue'
import { $fetch } from 'ofetch'
definePageMeta({
  middleware: ['auth'],
})

const itemsPerPage = 3
const cases = ref<{ id: string; case_number: string; registration_date: string }[]>([])
const documents = ref<{ case_number: string; title: string; created_at: string }[]>([])

const casePage = ref(0)
const docPage = ref(0)

const visibleCases = computed(() =>
  cases.value.slice(casePage.value * itemsPerPage, (casePage.value + 1) * itemsPerPage)
)
const visibleDocuments = computed(() =>
  documents.value.slice(docPage.value * itemsPerPage, (docPage.value + 1) * itemsPerPage)
)

const nextCasePage = () => {
  if ((casePage.value + 1) * itemsPerPage < cases.value.length) casePage.value++
}
const prevCasePage = () => {
  if (casePage.value > 0) casePage.value--
}

const nextDocPage = () => {
  if ((docPage.value + 1) * itemsPerPage < documents.value.length) docPage.value++
}
const prevDocPage = () => {
  if (docPage.value > 0) docPage.value--
}

// Форматирование даты
const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('ru-RU', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

// 🔄 Загрузка данных
interface CaseShort {
  id: string
  case_number: string
  registration_date: string
}

interface CaseDocumentPreview {
  case_number: string
  title: string
  created_at: string
}
onMounted(async () => {
  const token = localStorage.getItem('token')
  if (!token) {
    console.warn('Токен не найден. Пользователь не авторизован.')
    return
  }

  const fetchConfig = {
    baseURL: 'http://localhost:8000',
    headers: { Authorization: `Bearer ${token}` },
  }

  try {
    const caseRes = await $fetch('/cases/short', fetchConfig) as CaseShort[]

    if (!Array.isArray(caseRes) || caseRes.length === 0) {
      console.warn('Нет дел у пользователя.')
      return
    }

    cases.value = caseRes

    // ✅ переменную firstCaseId создаём ВНУТРИ блока, после проверки
    const firstCase = caseRes[0]
    if (!firstCase) return  // ещё одна подстраховка
    const firstCaseId = firstCase.id

    const docRes = await $fetch(
      `/cases/${firstCaseId}/documents`,
      fetchConfig
    ) as CaseDocumentPreview[]

    documents.value = docRes

  } catch (err: unknown) {
    console.error('Ошибка при загрузке дел и документов:', err)
  }
})

</script>


<style scoped>
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.section-title {
  font-size: 1.25rem;
  font-weight: 600;
}

.nav-buttons button {
  background-color: #e5e7eb;
  border: none;
  padding: 6px 10px;
  border-radius: 6px;
  margin-left: 6px;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.nav-buttons button:hover {
  background-color: #d1d5db;
}

.nav-buttons button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}


</style>
