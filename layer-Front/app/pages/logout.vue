<template>
  <div class="min-h-screen bg-gray-900 flex items-center justify-center">
    <div class="bg-gray-800 p-6 rounded-lg shadow-lg w-full max-w-md">
      <h2 class="text-white text-2xl font-bold mb-4 text-center">
        {{ showRegister ? 'Регистрация' : 'Вход' }}
      </h2>

      <form @submit.prevent="showRegister ? handleRegister() : handleLogin()" class="space-y-4">
        <div>
          <label for="username" class="text-gray-300 block mb-1">Username</label>
          <input
            v-model="username"
            type="text"
            id="username"
            class="w-full p-2 bg-gray-700 text-white rounded"
            required
          />
        </div>
        <div>
          <label for="password" class="text-gray-300 block mb-1">Пароль</label>
          <input
            v-model="password"
            type="password"
            id="password"
            class="w-full p-2 bg-gray-700 text-white rounded"
            required
          />
        </div>

        <div v-if="errorMessage" class="text-red-400 text-sm text-center">
          {{ errorMessage }}
        </div>
        <div v-if="successMessage" class="text-green-400 text-sm text-center">
          {{ successMessage }}
        </div>

        <button
          type="submit"
          class="w-full p-2 rounded text-white font-semibold flex justify-center items-center"
          :class="showRegister ? 'bg-green-600 hover:bg-green-700' : 'bg-blue-600 hover:bg-blue-700'"
          :disabled="isLoading"
        >
          <span v-if="isLoading">⏳</span>
          <span v-else>{{ showRegister ? 'Зарегистрироваться' : 'Войти' }}</span>
        </button>
      </form>

      <p class="text-gray-400 text-center mt-4">
        <a href="#" @click.prevent="toggleMode" class="text-blue-400">
          {{ showRegister ? 'Уже есть аккаунт? Войти' : 'Нет аккаунта? Зарегистрироваться' }}
        </a>
      </p>
    </div>
  </div>
</template>
<script setup>
definePageMeta({ layout: false })

import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const username = ref('')
const password = ref('')
const showRegister = ref(false)

const isLoading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const toggleMode = () => {
  showRegister.value = !showRegister.value
  errorMessage.value = ''
  successMessage.value = ''
}

// 🔐 Вход
const handleLogin = async () => {
  if (!username.value || !password.value) {
    errorMessage.value = 'Введите имя пользователя и пароль'
    return
  }

  isLoading.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const formData = new FormData()
    formData.append('username', username.value)
    formData.append('password', password.value)

    const res = await useFetch('http://localhost:8000/login', {
      method: 'POST',
      body: formData
    })

    const data = res.data.value
    if (data?.access_token) {
      localStorage.setItem('token', data.access_token)
      router.push('/')
    } else {
      errorMessage.value = 'Неверный ответ от сервера'
    }
  } catch (err) {
    console.error('Ошибка входа:', err)
    errorMessage.value = 'Ошибка входа. Проверьте данные.'
  } finally {
    isLoading.value = false
  }
}

// 📝 Регистрация
const handleRegister = async () => {
  if (!username.value || !password.value) {
    errorMessage.value = 'Введите имя пользователя и пароль'
    return
  }

  isLoading.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const formData = new FormData()
    formData.append('username', username.value)
    formData.append('password', password.value)

    const res = await useFetch('http://localhost:8000/register', {
      method: 'POST',
      body: formData
    })

    if (res.error.value) {
      errorMessage.value = res.error.value?.data?.detail || 'Ошибка регистрации. Возможно, имя занято.'
      return
    }

    successMessage.value = 'Регистрация прошла успешно'
    showRegister.value = false
    username.value = ''
    password.value = ''
  } catch (err) {
    console.error('Ошибка регистрации:', err)
    errorMessage.value = 'Ошибка регистрации. Попробуйте позже.'
  } finally {
    isLoading.value = false
  }
}
</script>
