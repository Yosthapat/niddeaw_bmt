<script setup lang="ts">
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSessionsStore } from '@/stores/sessions'
import { usePlayersStore } from '@/stores/players'
import AdminNav from '@/components/layout/AdminNav.vue'
import SessionPicker from '@/components/layout/SessionPicker.vue'

const { t } = useI18n()
const sessionsStore = useSessionsStore()
const playersStore = usePlayersStore()

onMounted(() => {
  sessionsStore.refresh()
  playersStore.ensureLoaded()
})
</script>

<template>
  <AdminNav />
  <main class="mx-auto max-w-4xl px-4 py-6">
    <h1 class="text-2xl font-bold text-brand-pink">Admin Dashboard</h1>

    <div class="mt-4">
      <SessionPicker />
    </div>

    <div class="mt-6 grid gap-3 sm:grid-cols-3">
      <div class="hud-panel border border-brand-pink/20 bg-brand-surface p-4">
        <p class="text-xs text-white/50">{{ t('dashboard.totalMembers') }}</p>
        <p class="mt-1 text-2xl font-bold">{{ playersStore.players.length }}</p>
      </div>
      <div class="hud-panel border border-brand-pink/20 bg-brand-surface p-4">
        <p class="text-xs text-white/50">{{ t('dashboard.openSessions') }}</p>
        <p class="mt-1 text-2xl font-bold">{{ sessionsStore.openSessions.length }}</p>
      </div>
      <div class="hud-panel border border-brand-pink/20 bg-brand-surface p-4">
        <p class="text-xs text-white/50">{{ t('dashboard.totalSessions') }}</p>
        <p class="mt-1 text-2xl font-bold">{{ sessionsStore.sessions.length }}</p>
      </div>
    </div>

    <div class="mt-8 grid gap-3 sm:grid-cols-2">
      <RouterLink
        to="/admin/checkin"
        class="hud-panel border border-brand-pink/20 bg-brand-surface p-4 hover:bg-brand-surface-raised"
      >
        <p class="font-semibold text-brand-pink">{{ t('admin.nav.checkin') }}</p>
        <p class="text-sm text-white/60">{{ t('dashboard.checkinDesc') }}</p>
      </RouterLink>
      <RouterLink
        to="/admin/matchmaking"
        class="hud-panel border border-brand-pink/20 bg-brand-surface p-4 hover:bg-brand-surface-raised"
      >
        <p class="font-semibold text-brand-pink">{{ t('admin.nav.matchmaking') }}</p>
        <p class="text-sm text-white/60">{{ t('dashboard.matchmakingDesc') }}</p>
      </RouterLink>
      <RouterLink
        to="/admin/billing"
        class="hud-panel border border-brand-pink/20 bg-brand-surface p-4 hover:bg-brand-surface-raised"
      >
        <p class="font-semibold text-brand-pink">{{ t('admin.nav.billing') }}</p>
        <p class="text-sm text-white/60">{{ t('dashboard.billingDesc') }}</p>
      </RouterLink>
      <RouterLink
        to="/admin/settings"
        class="hud-panel border border-brand-pink/20 bg-brand-surface p-4 hover:bg-brand-surface-raised"
      >
        <p class="font-semibold text-brand-pink">{{ t('admin.nav.settings') }}</p>
        <p class="text-sm text-white/60">{{ t('dashboard.settingsDesc') }}</p>
      </RouterLink>
    </div>
  </main>
</template>
