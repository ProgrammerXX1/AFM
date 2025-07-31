<template>
  <div class="document-list">
    <!-- 🔍 Фильтрационная панель -->
    <div class="filter-wrapper">
      <DocumentFilterBar 
        @update:search="searchText = $event"
        @update:type="selectedType = $event"
        @update:dateRange="dateRange = $event"
      />
    </div>

    <!-- 🧭 Панель управления -->
    <DocumentToolbar
      :total="filteredDocuments.length"
      :itemsPerPage="itemsPerPage"
      :case-id="caseId"
      :has-selection="!!selectedDoc"
      @page-change="handlePageChange"
      @edit="editSelected"
      @delete="deleteSelected"
      @refresh-documents="fetchDocuments"
    />

    <!-- 🗂 Сетка документов -->
    <div class="document-grid-wrapper">
      <div class="document-grid">
        <DocCard
          v-for="(doc) in paginatedDocuments"
          :key="doc.id"
          :document="doc"
          :selected="selectedDoc?.id === doc.id"
          @click="selectDocument(doc)"
        />
      </div>
    </div>

    <!-- ✏️ Модальное окно редактирования -->
    <div v-if="isEditing" class="modal-backdrop">
      <div class="modal">
        <h3>Редактирование документа</h3>
        <input v-model="editForm.title" placeholder="Заголовок" />
        <input v-model="editForm.filetype" placeholder="Тип" />
        <input v-model="editForm.created_at" placeholder="Дата" />
        <div class="modal-actions">
          <button @click="saveEdit">💾 Сохранить</button>
          <button @click="isEditing = false">❌ Отмена</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { $fetch } from 'ofetch'
import DocCard from '../DocCard.vue'
import DocumentFilterBar from '../DocumentFilterBar.vue'
import DocumentToolbar from '../DocumentToolbar.vue'

const props = defineProps<{ caseId: number }>()

type DocumentType = {
  id: number
  title: string
  filetype: string
  created_at: string
  content?: string // ✅ добавить это
}

const documents = ref<DocumentType[]>([])
const itemsPerPage = 4
const currentPage = ref(0)
const searchText = ref('')
const selectedDoc = ref<DocumentType | null>(null)
const selectedType = ref('')
const dateRange = ref<{ from: Date | null, to: Date | null }>({ from: null, to: null })
const isEditing = ref(false)
const isLoading = ref(false)

const editForm = ref<DocumentType>({
  id: 0,
  title: '',
  filetype: '',
  created_at: '',
  content: '',
})

// ✅ Загрузка документов
const fetchDocuments = async (id?: number) => {
  try {
    isLoading.value = true
    const token = localStorage.getItem('token')
    const caseIdToUse = id ?? props.caseId

    const response = await $fetch(`http://localhost:8000/cases/${caseIdToUse}`, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    })

    documents.value = response.documents || []
    console.log('📄 Загружено документов:', documents.value)

  } catch (error) {
    console.error('❌ Ошибка при загрузке документов:', error)
  } finally {
    isLoading.value = false
  }
}

// ⚡ Авто-загрузка при монтировании
onMounted(() => {
  fetchDocuments()
})

// 🔍 Фильтрация
const filteredDocuments = computed(() => {
  let docs = [...documents.value]

  if (selectedType.value && selectedType.value !== 'Все') {
    docs = docs.filter(doc => doc.filetype?.toLowerCase() === selectedType.value.toLowerCase())
  }

  if (searchText.value.trim() !== '') {
    const q = searchText.value.toLowerCase()
    docs = docs.filter(doc => doc.title?.toLowerCase().includes(q))
  }

  if (dateRange.value.from && dateRange.value.to) {
    const from = new Date(dateRange.value.from)
    const to = new Date(dateRange.value.to)
    to.setHours(23, 59, 59, 999)

    docs = docs.filter(doc => {
      const docDate = new Date(doc.created_at)
      return !isNaN(docDate.getTime()) && docDate >= from && docDate <= to
    })
  }

  return docs
})

// 📄 Пагинация
const paginatedDocuments = computed(() => {
  const start = currentPage.value * itemsPerPage
  return filteredDocuments.value.slice(start, start + itemsPerPage)
})

const handlePageChange = (page: number) => {
  currentPage.value = page
}

// 🔘 Выбор документа
const selectDocument = (doc: DocumentType) => {
  selectedDoc.value = selectedDoc.value?.id === doc.id ? null : doc
}

// ✏️ Редактирование
const editSelected = () => {
  if (!selectedDoc.value) return
  editForm.value = { ...selectedDoc.value }
  isEditing.value = true
}
// 🗑 Удаление
const deleteSelected = async () => {
  const id = selectedDoc.value?.id
  if (!id) return
  const token = localStorage.getItem('token')

  try {
    await $fetch(`http://localhost:8000/documents/${id}`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${token}`, // добавь токен
      },
    })

    documents.value = documents.value.filter(doc => doc.id !== id)
    selectedDoc.value = null
  } catch (e) {
    console.error('Ошибка при удалении документа:', e)
  }
}
const saveEdit = async () => {
  if (!editForm.value || !editForm.value.id) return

  const token = localStorage.getItem('token')

  // 💡 Новый payload с content
  const payload = {
    title: editForm.value.title,
    filetype: editForm.value.filetype,
    content: editForm.value.content || '', // 👈 обязательно строка
  }

  console.log(`📤 [FRONTEND] Отправка запроса PUT /documents/${editForm.value.id}`)
  console.log("📦 [FRONTEND] Тело запроса:", payload)

  try {
    const updated = await $fetch(`http://localhost:8000/documents/${editForm.value.id}`, {
      method: 'PUT',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload), // ⚠️ обязательно строкой
    })

    console.log("✅ [FRONTEND] Ответ от сервера:", updated)

    const index = documents.value.findIndex(d => d.id === editForm.value.id)
    if (index !== -1) {
      documents.value[index] = updated
    }

    isEditing.value = false
    selectedDoc.value = null
  } catch (e: any) {
    console.error(`❌ [FRONTEND] Ошибка при редактировании документа:`, e?.data || e)
  }
}


</script>

<style scoped>
.document-list {
  background: #1e1e1e;
  border-radius: 12px;
  padding: 20px;
  margin-top: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.filter-wrapper {
  width: 100%;
  padding: 1 8px;
  box-sizing: border-box;
}

.document-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.25rem;
}

@media (max-width: 1024px) {
  .document-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .document-grid {
    grid-template-columns: 1fr;
  }
}

/* ====== Modal ====== */
.modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0,0,0,0.5);
  display: flex;
  justify-content: center;
  align-items: center;
}

.modal {
  background: white;
  padding: 20px;
  border-radius: 10px;
  width: 300px;
}

.modal input {
  margin-bottom: 0.5rem;
  width: 100%;
  padding: 6px 10px;
  font-size: 13px;
  border: 1px solid #ccc;
  border-radius: 6px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 1rem;
}
</style>
