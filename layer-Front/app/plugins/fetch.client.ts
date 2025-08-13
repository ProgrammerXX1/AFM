// plugins/fetch.client.ts
export default defineNuxtPlugin((nuxtApp) => {
  async function waitTokenReady() {
    // ждём до ~1s если токен только что писался
    let tries = 0
    while (!localStorage.getItem('token') && tries < 40) {
      await new Promise(r => setTimeout(r, 25))
      tries++
    }
  }

  nuxtApp.$fetch = $fetch.create({
    async onRequest({ options }) {
      // 1) дождаться токена, чтобы не было гонки
      await waitTokenReady()

      // 2) приклеить токен корректно (без new Headers)
      const token = localStorage.getItem('token')
      options.headers = {
        ...(options.headers as Record<string, string> | undefined),
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      }

      // 3) передаём куки (если бэк их тоже принимает/проксирует)
      // безопасно: браузер сам отправит только к своему домену
      options.credentials = 'include'

      // 4) общий таймаут, чтобы не зависать навечно
      if (options.timeout == null) options.timeout = 60000 // 60s
    },

    onResponseError({ response }) {
      // аккуратнее ведём себя на 401
      if (response.status === 401) {
        console.warn('⛔ 401: токен протух, чистим и уводим на /logout')
        try { localStorage.removeItem('token') } catch {}
        window.location.href = '/logout'
      }
    },
  })
})
