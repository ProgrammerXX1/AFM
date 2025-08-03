<template>
  <router-link
  :to="`/cases?id=${id}`"
  class="block transition hover:shadow-lg no-underline text-inherit"
>

     <div class="p-6 rounded-lg shadow text-center">
      <div class="text-5xl mb-3">📄</div>
      <p class="font-semibold text-base">{{ number }}</p>
      <p class="text-sm text-gray-700">Дата регистрации: {{ date }}</p>
    </div>
  </router-link>
</template>

<script setup lang="ts">
defineProps<{
  id: string
  number: string
  date: string
}>()
</script>
