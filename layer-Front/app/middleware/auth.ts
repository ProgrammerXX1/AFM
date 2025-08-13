// middleware/auth.ts
type User = { id: number; username: string }

export default defineNuxtRouteMiddleware(async (to) => {
  const config = useRuntimeConfig()
  const publicPages = ['/', '/logout', '/register', '/login']
  const isPublic = publicPages.includes(to.path)

  if (process.server) return

  const token = localStorage.getItem('token')

  if (!token && !isPublic) {
    return navigateTo('/logout')
  }
  if (!token || isPublic) return

  try {
    // важное: baseURL обязателен, иначе пойдёт на фронтенд-хост
    const me = await $fetch<User>('/me', {
      baseURL: config.public.apiBase,
      // заголовок сейчас поставит наш плагин, но дублировать не вредно:
      headers: { Authorization: `Bearer ${token}` },
      credentials: 'include',
      // небольшой таймаут, чтобы страница не висла
      timeout: 15000,
    })
    if (!me?.username) throw new Error('Invalid user')
  } catch (err) {
    console.warn('❌ Токен истёк/невалиден — уводим на /logout')
    localStorage.removeItem('token')
    return navigateTo('/logout')
  }
})
