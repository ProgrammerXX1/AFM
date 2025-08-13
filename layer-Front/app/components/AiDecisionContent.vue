<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useRuntimeConfig } from '#app'

definePageMeta({ middleware: ['auth'] })

const route = useRoute()
const config = useRuntimeConfig()
const { $fetch } = useNuxtApp()

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

  // собственный AbortController, чтобы прервать долгие вызовы модели
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), 120_000) // 120s

  try {
    const res = await $fetch<any>(`/cases/${caseId.value}/prompt`, {
      baseURL: config.public.apiBase,
      method: 'GET',
      credentials: 'include',
      signal: ctrl.signal,
      // плагин сам подставит Authorization + timeout
    })
    rawData.value = res
  } catch (e: any) {
    console.error('❌ Ошибка загрузки:', e)
    // аккуратная раскрутка сообщения
    const msg =
      e?.response?._data?.detail ||
      e?.response?._data?.message ||
      e?.statusText ||
      e?.message ||
      e?.name || // AbortError
      e?.status ||
      'Неизвестная ошибка'
    errorMessage.value = `❌ Ошибка загрузки данных: ${msg}`

    // полезно увидеть тело ответа, если бэк что-то прислал
    if (e?.response?._data) rawData.value = e.response._data
  } finally {
    clearTimeout(timer)
    isLoading.value = false
  }
}

function reload () { void load() }

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
</script>
