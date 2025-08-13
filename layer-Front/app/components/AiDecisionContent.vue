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

      <!-- Строка — как есть -->
      <pre v-if="isString" class="dump">{{ String(rawData) }}</pre>
      <!-- Объект/массив — pretty JSON -->
      <pre v-else class="dump">{{ prettyText }}</pre>
    </div>
  </main>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useRuntimeConfig } from '#app'

definePageMeta({
  middleware: ['auth'] // ← запускаем твой middleware на этой странице
})

const route = useRoute()
const config = useRuntimeConfig()
const { $fetch } = useNuxtApp() // ← твой плагин с Authorization

const isLoading = ref(true)
const errorMessage = ref('')
const rawData = ref<unknown>(null)
const copied = ref(false)

const caseId = computed(() => String(route.params.case_id ?? '1'))

onMounted(() => { void load() })
watch(() => caseId.value, () => { void load() })

async function load () {
  isLoading.value = true
  errorMessage.value = ''
  rawData.value = null
  copied.value = false

  try {
    // дождёмся токена (защита от гонки при входе)
    await ensureTokenReady()

    // GET /cases/{case_id}/prompt — токен подставит fetch.client.ts
    const res = await $fetch<any>(`/cases/${caseId.value}/prompt`, {
      baseURL: config.public.apiBase,
      method: 'GET'
    })
    rawData.value = res
  } catch (e: any) {
    console.error('❌ Ошибка загрузки:', e)
    const msg =
      e?.response?._data?.detail ||
      e?.statusText ||
      e?.message ||
      e?.status ||
      'Неизвестная ошибка'
    errorMessage.value = `❌ Ошибка загрузки данных: ${msg}`
    if (e?.response?._data) rawData.value = e.response._data
  } finally {
    isLoading.value = false
  }
}

function reload () {
  void load()
}

const isString = computed(() => typeof rawData.value === 'string')
const prettyText = computed(() => {
  if (isString.value) return String(rawData.value)
  try { return JSON.stringify(rawData.value, null, 2) }
  catch { return String(rawData.value) }
})

const byteSize = computed(() => {
  try {
    const str = isString.value ? String(rawData.value) : JSON.stringify(rawData.value)
    const bytes = new TextEncoder().encode(str).length
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  } catch { return '' }
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

/** Ждём появления токена в localStorage перед запросом */
function getToken(): string | null {
  try { return localStorage.getItem('token') } catch { return null }
}
async function ensureTokenReady() {
  if (getToken()) return
  // короткий, но надёжный цикл ожидания (на случай, если логин только что записал токен)
  let tries = 0
  while (!getToken() && tries < 40) {
    await new Promise(r => setTimeout(r, 25))
    tries++
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
