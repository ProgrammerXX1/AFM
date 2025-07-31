type User = {
  id: number
  username: string
}

export default defineNuxtRouteMiddleware(async (to) => {
  const publicPages = ['/', '/logout', '/register']
  const isPublic = publicPages.includes(to.path)

  if (process.server) return

  const token = localStorage.getItem('token')

  if (!token && !isPublic) {
    return navigateTo('/logout')
  }

  // Не запрашиваем /me на публичных страницах
  if (!token || isPublic) return

  try {
    const res = await $fetch<User>('/me', {
      baseURL: 'http://localhost:8000',
      headers: { Authorization: `Bearer ${token}` },
    })

    if (!res?.username) throw new Error('Invalid user')
  } catch (err) {
    console.warn('❌ Токен истёк, редиректим...')
    localStorage.removeItem('token')
    return navigateTo('/logout')
  }
})
