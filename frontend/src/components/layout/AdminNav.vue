<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const links = [
  { to: '/admin', label: 'Dashboard' },
  { to: '/admin/checkin', label: 'Check-in' },
  { to: '/admin/matchmaking', label: 'จับคู่' },
  { to: '/admin/billing', label: 'คิดเงิน' },
  { to: '/admin/settings', label: 'ตั้งค่า' },
]

function logout(): void {
  authStore.logout()
  router.push('/admin/login')
}
</script>

<template>
  <nav class="mx-auto flex max-w-4xl flex-wrap items-center gap-1 px-4 pt-4 text-sm">
    <RouterLink
      v-for="link in links"
      :key="link.to"
      :to="link.to"
      class="rounded-full px-3 py-1.5"
      :class="
        route.path === link.to
          ? 'bg-brand-pink text-brand-black font-semibold'
          : 'text-white/70 hover:text-white'
      "
    >
      {{ link.label }}
    </RouterLink>
    <button class="ml-auto rounded-full border border-white/20 px-3 py-1.5 text-white/60 hover:text-white" @click="logout">
      ออกจากระบบ
    </button>
  </nav>
</template>
