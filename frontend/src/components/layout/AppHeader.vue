<script setup lang="ts">
import { RouterLink, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const authStore = useAuthStore()

const publicLinks = [
  { to: '/', label: 'หน้าแรก' },
  { to: '/members', label: 'สมาชิก' },
  { to: '/ranking', label: 'อันดับ' },
  { to: '/hall-of-fame', label: 'Hall of Fame' },
  { to: '/matches', label: 'ผลแมตช์' },
]
</script>

<template>
  <header class="sticky top-0 z-10 border-b border-brand-pink-dark/40 bg-brand-black/95 backdrop-blur">
    <div class="mx-auto flex max-w-5xl items-center gap-3 px-4 py-3">
      <RouterLink to="/" class="flex items-center gap-2 shrink-0">
        <img
          src="/pwa-icons/pwa-64x64.png"
          alt="นิดเดียว Badminton Club logo"
          class="h-9 w-9 rounded-full ring-2 ring-brand-pink"
        />
        <span class="hidden text-base font-bold text-brand-pink sm:inline">นิดเดียว BMT</span>
      </RouterLink>

      <nav class="flex flex-1 gap-1 overflow-x-auto text-sm">
        <RouterLink
          v-for="link in publicLinks"
          :key="link.to"
          :to="link.to"
          class="whitespace-nowrap rounded-full px-3 py-1.5 transition-colors"
          :class="
            route.path === link.to
              ? 'bg-brand-pink text-brand-black font-semibold'
              : 'text-white/70 hover:text-white'
          "
        >
          {{ link.label }}
        </RouterLink>
      </nav>

      <RouterLink
        :to="authStore.isAuthenticated ? '/admin' : '/admin/login'"
        class="shrink-0 whitespace-nowrap rounded-full border border-brand-pink-dark px-3 py-1.5 text-sm text-brand-pink-light hover:bg-brand-pink-dark/20"
      >
        {{ authStore.isAuthenticated ? 'Admin' : 'Admin Login' }}
      </RouterLink>
    </div>
  </header>
</template>
