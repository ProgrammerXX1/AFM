<template>
  <router-link
    to="/cases"
    class="block hover:shadow-lg transition rounded-lg no-underline text-inherit"
  >
    <div class="bg-white p-6 rounded-lg shadow text-center">
      <div class="text-5xl mb-3">📄</div>
      <p class="font-semibold text-base">Содержимое {{ number }}</p>
      <p class="text-sm text-gray-700">{{ title }}</p>
      <p class="text-xs text-gray-500">Дата добавления: {{ date }}</p>
    </div>
  </router-link>
</template>

<script setup>
defineProps({
  number: String,
  title: String,
  date: String
})
</script>
