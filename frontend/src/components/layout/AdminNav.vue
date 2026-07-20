<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const { t } = useI18n()

const links = computed(() => [
  { to: '/admin', label: t('admin.nav.dashboard') },
  { to: '/admin/checkin', label: t('admin.nav.checkin') },
  { to: '/admin/members', label: t('admin.nav.members') },
  { to: '/admin/matchmaking', label: t('admin.nav.matchmaking') },
  { to: '/admin/billing', label: t('admin.nav.billing') },
  { to: '/admin/revenue', label: t('admin.nav.revenue') },
  { to: '/admin/settings', label: t('admin.nav.settings') },
])

function logout(): void {
  authStore.logout()
  router.push('/admin/login')
}
</script>

<template>
  <nav class="mx-auto flex max-w-4xl flex-wrap items-center gap-1.5 px-4 pt-4 text-sm">
    <RouterLink
      v-for="link in links"
      :key="link.to"
      :to="link.to"
      class="hud-panel px-3 py-1.5 font-semibold transition-colors"
      :class="
        route.path === link.to
          ? 'bg-brand-pink text-brand-black'
          : 'bg-brand-surface text-white/60 hover:bg-brand-surface-raised hover:text-white'
      "
    >
      {{ link.label }}
    </RouterLink>
    <button
      class="hud-panel ml-auto border border-white/15 px-3 py-1.5 text-white/50 hover:border-white/30 hover:text-white"
      @click="logout"
    >
      {{ t('admin.nav.logout') }}
    </button>
  </nav>
</template>
