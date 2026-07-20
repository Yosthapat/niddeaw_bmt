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
  <header class="sticky top-0 z-10 border-b border-brand-pink/20 bg-brand-black/95 backdrop-blur">
    <div class="mx-auto flex max-w-5xl items-center gap-4 px-4 py-3">
      <RouterLink to="/" class="flex shrink-0 items-center gap-2.5">
        <span class="hud-panel bg-brand-pink p-0.5">
          <img src="/pwa-icons/pwa-64x64.png" alt="นิดเดียว Badminton Club logo" class="hud-panel block h-8 w-8" />
        </span>
        <span class="hidden font-display text-base font-bold tracking-wide text-white sm:inline">
          นิดเดียว<span class="text-brand-pink">BMT</span>
        </span>
      </RouterLink>

      <nav class="flex flex-1 gap-4 overflow-x-auto text-xs font-semibold tracking-wider uppercase sm:gap-5">
        <RouterLink
          v-for="link in publicLinks"
          :key="link.to"
          :to="link.to"
          class="relative whitespace-nowrap py-2 transition-colors"
          :class="route.path === link.to ? 'text-brand-pink' : 'text-white/50 hover:text-white'"
        >
          {{ link.label }}
          <span
            v-if="route.path === link.to"
            class="absolute -bottom-px left-0 h-0.5 w-full bg-brand-pink"
          />
        </RouterLink>
      </nav>

      <RouterLink
        :to="authStore.isAuthenticated ? '/admin' : '/admin/login'"
        class="hud-panel shrink-0 whitespace-nowrap border border-brand-pink/50 px-3 py-1.5 text-xs font-semibold tracking-wide text-brand-pink-light uppercase hover:border-brand-pink hover:bg-brand-pink/10"
      >
        {{ authStore.isAuthenticated ? 'Admin' : 'Admin Login' }}
      </RouterLink>
    </div>
  </header>
</template>
