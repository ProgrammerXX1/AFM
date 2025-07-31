<template>
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
</template>

<style lang="postcss">
html, body {
  @apply bg-gray-100 text-black font-sans;
}
html, body {
  overflow: hidden;
  height: 100%;
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
@media (max-width: 1024px) {
  html, body {
    overflow: auto;
  }
}
</style>
