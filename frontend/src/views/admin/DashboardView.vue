<script setup lang="ts">
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSessionsStore } from '@/stores/sessions'
import { usePlayersStore } from '@/stores/players'
import AdminNav from '@/components/layout/AdminNav.vue'
import SessionPicker from '@/components/layout/SessionPicker.vue'
import RevenueExpenseChart from '@/components/admin/RevenueExpenseChart.vue'
import AccountBalanceChart from '@/components/admin/AccountBalanceChart.vue'
import CountUp from '@/components/common/CountUp.vue'

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
    <h1 class="text-2xl font-bold text-brand-pink">{{ t('dashboard.title') }}</h1>

    <div class="mt-4">
      <SessionPicker allow-delete />
    </div>

    <div class="mt-6 grid grid-cols-3 gap-2 sm:gap-3">
      <div class="hud-panel hud-hover flex flex-col justify-between border border-brand-pink/20 bg-brand-surface p-3">
        <div class="flex items-center gap-1.5 text-white/50">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" class="h-3.5 w-3.5 shrink-0">
            <path d="M17 21v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2 M10 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z M22 21v-2a4 4 0 0 0-3-3.87 M16 3.13a4 4 0 0 1 0 7.75" />
          </svg>
          <p class="text-[11px] leading-tight">{{ t('dashboard.totalMembers') }}</p>
        </div>
        <p class="mt-2 font-display text-xl font-bold"><CountUp :value="playersStore.players.length" /></p>
      </div>
      <div class="hud-panel hud-hover flex flex-col justify-between border border-brand-pink/20 bg-brand-surface p-3">
        <div class="flex items-center gap-1.5 text-white/50">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" class="h-3.5 w-3.5 shrink-0">
            <circle cx="12" cy="12" r="9" />
            <path d="M12 7v5l3 3" />
          </svg>
          <p class="text-[11px] leading-tight">{{ t('dashboard.openSessions') }}</p>
        </div>
        <p class="mt-2 font-display text-xl font-bold text-status-success"><CountUp :value="sessionsStore.openSessions.length" /></p>
      </div>
      <div class="hud-panel hud-hover flex flex-col justify-between border border-brand-pink/20 bg-brand-surface p-3">
        <div class="flex items-center gap-1.5 text-white/50">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" class="h-3.5 w-3.5 shrink-0">
            <rect x="3" y="4" width="18" height="17" rx="2" />
            <path d="M3 9h18 M8 2v4 M16 2v4" />
          </svg>
          <p class="text-[11px] leading-tight">{{ t('dashboard.totalSessions') }}</p>
        </div>
        <p class="mt-2 font-display text-xl font-bold"><CountUp :value="sessionsStore.sessions.length" /></p>
      </div>
    </div>

    <div class="mt-6">
      <RevenueExpenseChart />
    </div>

    <div class="mt-6">
      <AccountBalanceChart />
    </div>

  </main>
</template>
