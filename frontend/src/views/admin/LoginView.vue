<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { login } from '@/api/admin'
import { ApiError } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref<string | null>(null)

const authStore = useAuthStore()
const router = useRouter()

async function submit(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const { access_token } = await login({ username: username.value, password: password.value })
    authStore.login(access_token)
    router.push('/admin')
  } catch (e) {
    error.value = e instanceof ApiError && e.status === 401 ? 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง' : 'เข้าสู่ระบบไม่สำเร็จ'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="mx-auto flex max-w-sm flex-col px-4 py-16">
    <h1 class="text-center text-2xl font-bold text-brand-pink">Admin Login</h1>
    <form class="mt-8 flex flex-col gap-4" @submit.prevent="submit">
      <input
        v-model="username"
        type="text"
        placeholder="Username"
        autocomplete="username"
        required
        class="rounded-lg border border-brand-pink/25 bg-brand-surface px-3 py-2 outline-none focus:border-brand-pink"
      />
      <input
        v-model="password"
        type="password"
        placeholder="Password"
        autocomplete="current-password"
        required
        class="rounded-lg border border-brand-pink/25 bg-brand-surface px-3 py-2 outline-none focus:border-brand-pink"
      />
      <p v-if="error" class="text-sm text-status-error">{{ error }}</p>
      <button
        type="submit"
        :disabled="loading"
        class="rounded-lg bg-brand-pink px-3 py-2 font-semibold text-brand-black disabled:opacity-50"
      >
        {{ loading ? 'กำลังเข้าสู่ระบบ...' : 'เข้าสู่ระบบ' }}
      </button>
    </form>
  </main>
</template>
