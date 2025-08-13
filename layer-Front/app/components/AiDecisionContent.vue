<template>
  <main class="content">
    <div v-if="isLoading" class="text-center text-gray-500 mt-10">
      ⏳ Загружаем данные...
    </div>

    <div v-else-if="errorMessage" class="text-center text-red-500 mt-10">
      {{ errorMessage }}
    </div>

    <div v-else>
      <div class="toolbar">
        <button class="btn" @click="reload" :disabled="isLoading">🔄 Обновить</button>
        <button class="btn" @click="copyToClipboard" :disabled="!prettyText">📋 Скопировать</button>
        <span class="muted">case_id: {{ caseId }}</span>
        <span class="muted" v-if="byteSize">• {{ byteSize }} </span>
        <span class="muted" v-if="copied">— скопировано!</span>
      </div>

      <!-- Если пришла строка — покажем как есть -->
      <pre v-if="isString" class="dump">{{ String(rawData) }}</pre>

      <!-- Если пришёл JSON (объект/массив) — pretty-print -->
      <pre v-else class="dump">{{ prettyText }}</pre>
    </div>
  </main>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import { useRoute } from 'vue-router'
import { $fetch } from 'ofetch'
import { useRuntimeConfig } from '#app'

const config = useRuntimeConfig()
const route = useRoute()

const isLoading = ref(true)
const errorMessage = ref('')
const rawData = ref<unknown>(null)
const copied = ref(false)

const caseId = computed(() => String(route.params.case_id ?? '1'))

onMounted(load)
watch(() => caseId.value, load)

async function load () {
  isLoading.value = true
  errorMessage.value = ''
  rawData.value = null
  copied.value = false

  try {
    // ✅ Берём из твоего роутера: GET /cases/{case_id}/prompt
    const res = await $fetch<any>(`/cases/${caseId.value}/prompt`, {
      baseURL: config.public.apiBase,
      method: 'GET',
      credentials: 'include', // если auth через cookie
    })
    rawData.value = res
  } catch (e: any) {
    console.error('❌ Ошибка загрузки:', e)
    const msg = e?.response?._data?.detail || e?.message || e?.status || 'Неизвестная ошибка'
    errorMessage.value = `❌ Ошибка загрузки данных: ${msg}`
  } finally {
    isLoading.value = false
  }
}

function reload () {
  load()
}

const isString = computed(() => typeof rawData.value === 'string')
const prettyText = computed(() => {
  if (isString.value) return String(rawData.value)
  try {
    return JSON.stringify(rawData.value, null, 2)
  } catch {
    return String(rawData.value)
  }
})

const byteSize = computed(() => {
  try {
    const str = isString.value ? String(rawData.value) : JSON.stringify(rawData.value)
    const bytes = new TextEncoder().encode(str).length
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  } catch {
    return ''
  }
})

async function copyToClipboard () {
  try {
    await navigator.clipboard.writeText(prettyText.value || '')
    copied.value = true
    setTimeout(() => (copied.value = false), 1500)
  } catch (e) {
    console.warn('Не удалось скопировать', e)
  }
}
</script>

<style scoped>
.content {
  padding: 1.25rem;
  color: #e5e7eb;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: .5rem;
  margin-bottom: .75rem;
  flex-wrap: wrap;
}

.btn {
  background: #111827;
  color: #e5e7eb;
  border: 1px solid #374151;
  padding: .4rem .6rem;
  border-radius: .5rem;
  cursor: pointer;
  transition: .15s ease;
  font-size: .875rem;
}
.btn:disabled {
  opacity: .6;
  cursor: not-allowed;
}
.btn:not(:disabled):hover {
  background: #0b1220;
  border-color: #4b5563;
}

.muted {
  color: #9ca3af;
  font-size: .85rem;
}

.dump {
  background: #0b1220;
  border: 1px solid #1f2a44;
  border-radius: .5rem;
  padding: 1rem;
  white-space: pre-wrap;
  word-break: break-word;
  overflow: auto;
  font-size: .9rem;
  line-height: 1.5;
}
</style>
