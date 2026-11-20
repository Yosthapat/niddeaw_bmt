<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSessionsStore } from '@/stores/sessions'
import { usePlayersStore } from '@/stores/players'
import { useFinanceStore } from '@/stores/finance'
import { moneyShort } from '@/utils/format'
import AdminNav from '@/components/layout/AdminNav.vue'
import SessionPicker from '@/components/layout/SessionPicker.vue'
import RevenueExpenseChart from '@/components/admin/RevenueExpenseChart.vue'
import AccountBalanceChart from '@/components/admin/AccountBalanceChart.vue'
import CountUp from '@/components/common/CountUp.vue'
import { useLineLinksStore } from '@/stores/lineLinks'
import * as adminApi from '@/api/admin'
import type { PassAdmin } from '@/api/admin'

const { t } = useI18n()
const sessionsStore = useSessionsStore()
const playersStore = usePlayersStore()
// The charts below refresh it; the shop card only reads what they fetched.
const finance = useFinanceStore()
const lineLinks = useLineLinksStore()

// Niddeaw Pass: who holds one, this month's, and how many came in since
// this browser last opened the Pass tab.
const passes = ref<PassAdmin | null>(null)
const newPasses = computed(() => (passes.value ? adminApi.unseenPasses(passes.value) : 0))

onMounted(() => {
  sessionsStore.refresh()
  playersStore.ensureLoaded()
  void lineLinks.load()
  adminApi.getPassAdmin().then(
    (p) => (passes.value = p),
    () => (passes.value = null),
  )
})
</script>

<template>
  <AdminNav />
  <main class="mx-auto max-w-4xl px-4 py-6">
    <h1 class="sr-only">{{ t('dashboard.title') }}</h1>

    <div class="mt-4">
      <SessionPicker allow-delete />
    </div>

    <div class="fx-stagger mt-6 grid grid-cols-2 gap-2 sm:grid-cols-4 sm:gap-3">
      <RouterLink to="/admin/members" class="hud-panel hud-hover flex flex-col justify-between border border-brand-pink/20 bg-brand-surface p-3">
        <div class="flex items-center gap-1.5 text-white/50">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" class="h-3.5 w-3.5 shrink-0">
            <path d="M17 21v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2 M10 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z M22 21v-2a4 4 0 0 0-3-3.87 M16 3.13a4 4 0 0 1 0 7.75" />
          </svg>
          <p class="text-xs leading-tight">{{ t('dashboard.totalMembers') }}</p>
        </div>
        <p class="mt-2 font-display text-xl font-bold"><CountUp :value="playersStore.players.length" /></p>
        <p v-if="lineLinks.count > 0 || lineLinks.pending > 0" class="mt-0.5 flex items-center gap-1 text-[11px] leading-tight text-[#7ff0b4]">
          <span class="h-1.5 w-1.5 shrink-0 rounded-full bg-[#06c755]" aria-hidden="true" />
          {{ t('lineSummary.dashboard', { n: lineLinks.count }) }}
          <span v-if="lineLinks.pending > 0" class="text-[#ffd34d]">· {{ t('lineSummary.dashboardPending', { n: lineLinks.pending }) }}</span>
        </p>
      </RouterLink>
      <div class="hud-panel hud-hover flex flex-col justify-between border border-brand-pink/20 bg-brand-surface p-3">
        <div class="flex items-center gap-1.5 text-white/50">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" class="h-3.5 w-3.5 shrink-0">
            <circle cx="12" cy="12" r="9" />
            <path d="M12 7v5l3 3" />
          </svg>
          <p class="text-xs leading-tight">{{ t('dashboard.openSessions') }}</p>
        </div>
        <p class="mt-2 font-display text-xl font-bold text-status-success"><CountUp :value="sessionsStore.openSessions.length" /></p>
      </div>
      <div class="hud-panel hud-hover flex flex-col justify-between border border-brand-pink/20 bg-brand-surface p-3">
        <div class="flex items-center gap-1.5 text-white/50">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" class="h-3.5 w-3.5 shrink-0">
            <rect x="3" y="4" width="18" height="17" rx="2" />
            <path d="M3 9h18 M8 2v4 M16 2v4" />
          </svg>
          <p class="text-xs leading-tight">{{ t('dashboard.totalSessions') }}</p>
        </div>
        <p class="mt-2 font-display text-xl font-bold"><CountUp :value="sessionsStore.sessions.length" /></p>
      </div>
      <RouterLink
        to="/admin/shop"
        class="hud-panel hud-hover flex flex-col justify-between border border-[#199e70]/50 bg-brand-surface p-3"
      >
        <div class="flex items-center gap-1.5 text-white/50">
          <span class="h-2 w-2 shrink-0 rounded-full bg-[#199e70]" aria-hidden="true" />
          <p class="text-xs leading-tight">{{ t('dashboard.shopCard') }}</p>
        </div>
        <p class="mt-2 font-display text-xl font-bold">
          <CountUp :value="Math.round(finance.shop?.total ?? 0)" :format="moneyShort" />
        </p>
        <p class="mt-0.5 text-[11px] leading-tight" :class="finance.shop?.pending_orders ? 'text-[#ffd34d]' : 'text-white/40'">
          {{
            finance.shop?.pending_orders
              ? t('dashboard.shopCardPending', { n: finance.shop.pending_orders, amount: moneyShort(finance.shop.pending_amount) })
              : t('dashboard.shopCardNone')
          }}
        </p>
      </RouterLink>
    </div>

    <RouterLink v-if="passes" to="/admin/credit?tab=passes" class="pass-card mt-2 sm:mt-3">
      <span class="pass-chip">✦ Niddeaw Pass</span>
      <span class="order-last w-full text-sm sm:order-none sm:w-auto sm:min-w-0 sm:flex-1">
        <b>{{ t('dashboard.passHolders', { n: passes.holders }) }}</b>
        <span class="text-white/60"> · {{ t('dashboard.passMonth', { n: passes.month_count, credits: passes.month_credits.toLocaleString('en-US') }) }}</span>
      </span>
      <span class="flex-1 sm:hidden" />
      <span v-if="newPasses" class="pass-new"><span class="dot" aria-hidden="true" />{{ t('dashboard.passNew', { n: newPasses }) }}</span>
      <span v-else class="text-white/40" aria-hidden="true">→</span>
    </RouterLink>

    <div class="mt-6">
      <RevenueExpenseChart />
    </div>

    <div class="mt-6">
      <AccountBalanceChart />
    </div>

  </main>
</template>

<style scoped>
.pass-card {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 10px;
  border: 1px solid rgb(255 211 77 / 0.45);
  border-radius: 14px;
  background: linear-gradient(120deg, rgb(255 211 77 / 0.12), rgb(255 255 255 / 0.02));
  padding: 10px 12px;
}
.pass-chip {
  flex: none;
  border-radius: 999px;
  background: linear-gradient(#ffe58a, #f2c14e);
  padding: 3px 9px;
  color: #3a2600;
  font-family: var(--font-display);
  font-size: 11px;
  font-weight: 700;
}
.pass-new {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: 999px;
  background: #ffd34d;
  padding: 3px 10px;
  color: #000;
  font-size: 12px;
  font-weight: 700;
}
.pass-new .dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: #d61f6b;
  animation: pass-ping 1.4s ease-in-out infinite;
}
@keyframes pass-ping {
  50% {
    opacity: 0.35;
  }
}
@media (prefers-reduced-motion: reduce) {
  .pass-new .dot {
    animation: none;
  }
}
</style>
