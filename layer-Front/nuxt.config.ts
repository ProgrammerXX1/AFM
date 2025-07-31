// nuxt.config.ts
export default defineNuxtConfig({
  css: ['~/assets/css/tailwind.css'],
  modules: ['@nuxtjs/tailwindcss'],
  ssr: true, // можно оставить true, если защищаешь доступ к FormData через `process.client`
  runtimeConfig: {
    public: {
      apiBase: process.env.API_BASE || 'http://localhost:8000'
    }
  },
  vite: {
    ssr: {
      noExternal: ['axios']
    }
  },
  
})
