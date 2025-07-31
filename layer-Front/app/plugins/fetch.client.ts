export default defineNuxtPlugin((nuxtApp) => {
  nuxtApp.$fetch = $fetch.create({
    onRequest({ options }) {
      const token = localStorage.getItem('token')

      if (token) {
        // 👇 создаём headers корректно
        const headers = new Headers(options.headers)
        headers.set('Authorization', `Bearer ${token}`)
        options.headers = headers
      }
    },

    onResponseError({ response }) {
      if (response.status === 401) {
        console.warn('⛔ 401: автоматический выход')
        localStorage.removeItem('token')
        window.location.href = '/logout'
      }
    },
  })
})
