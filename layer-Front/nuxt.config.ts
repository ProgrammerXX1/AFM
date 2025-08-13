// nuxt.config.ts
export default defineNuxtConfig({
  css: ['~/assets/css/tailwind.css'],
  modules: ['@nuxtjs/tailwindcss'],
  ssr: true, // можно оставить true, если защищаешь доступ к FormData через `process.client`
  runtimeConfig: {
    public: {
      apiBase: process.env.API_BASE
    }
  },
  vite: {
    ssr: {
      noExternal: ['axios']
    }
  },
  devServer: {
    host: '0.0.0.0',
    port: 3000, // не обязательно, если и так 3000
  }
})
