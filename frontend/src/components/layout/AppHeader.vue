<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import LanguageSwitcher from './LanguageSwitcher.vue'

const route = useRoute()
const authStore = useAuthStore()
const { t } = useI18n()

// Hall of Fame nav link is temporarily hidden (not in use yet) — the
// /hall-of-fame route and view still exist, just unlinked from the header.
const publicLinks = computed(() => [
  { to: '/', label: t('nav.home') },
  { to: '/members', label: t('nav.members') },
  { to: '/ranking', label: t('nav.ranking') },
  { to: '/live', label: t('nav.live') },
  { to: '/matches', label: t('nav.matches') },
])
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

      <nav class="flex flex-1 gap-4 text-xs font-semibold tracking-wider uppercase sm:gap-5">
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

      <LanguageSwitcher class="shrink-0" />

      <RouterLink
        :to="authStore.isAuthenticated ? '/admin' : '/admin/login'"
        class="hud-panel shrink-0 whitespace-nowrap border border-brand-pink/50 p-2 text-xs font-semibold tracking-wide text-brand-pink-light uppercase hover:border-brand-pink hover:bg-brand-pink/10 sm:px-3 sm:py-1.5"
        :aria-label="authStore.isAuthenticated ? t('nav.admin') : t('nav.adminLogin')"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4 sm:hidden">
          <rect x="5" y="11" width="14" height="9" rx="1.5" />
          <path d="M8 11V7a4 4 0 0 1 8 0v4" />
        </svg>
        <span class="hidden sm:inline">{{ authStore.isAuthenticated ? t('nav.admin') : t('nav.adminLogin') }}</span>
      </RouterLink>
    </div>
  </header>
</template>
