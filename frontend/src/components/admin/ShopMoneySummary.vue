<script setup lang="ts">
/**
 * The top of the admin's shop page: what the shop has sold, this month,
 * what it made after its costs, what is waiting to be checked or shipped,
 * and what sells.
 *
 * Sold is confirmed + delivered orders — the same figure the dashboard adds
 * to the account's balance (services/shop_revenue.py). Costs are the
 * expenses filed as shop cost or shirts. `version` is bumped by the page
 * after anything that moves an order, so the figures follow.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import * as adminApi from '@/api/admin'
import { apiErrorMessage } from '@/api/errors'
import type { ShopRevenue } from '@/types'
import { moneyShort } from '@/utils/format'
import { localToday } from '@/utils/limits'

const props = defineProps<{ version: number }>()
const { t } = useI18n()

const SHOP_COLOR = '#199e70' // dataviz slot 3, as on the dashboard

const data = ref<ShopRevenue | null>(null)
const problem = ref('')

async function load(): Promise<void> {
  try {
    data.value = await adminApi.getShopRevenue()
    problem.value = ''
  } catch (e) {
    problem.value = apiErrorMessage(e, t('shopAdmin.money.loadFailed'))
  }
}
onMounted(load)
watch(() => props.version, load)

const thisMonth = computed(() => {
  const month = localToday().slice(0, 7)
  return (data.value?.daily ?? []).filter((d) => d.date.startsWith(month)).reduce((sum, d) => sum + d.amount, 0)
})
const topMax = computed(() => Math.max(1, ...(data.value?.top ?? []).map((x) => x.amount)))
</script>

<template>
  <p v-if="problem" class="mt-4 text-sm text-status-error" role="alert">{{ problem }}</p>
  <section v-else-if="data" class="mt-4 space-y-2.5" :aria-label="t('shopAdmin.money.title')">
    <div class="hud-panel border border-[#199e70]/50 bg-brand-surface p-4">
      <div class="flex items-end justify-between gap-3">
        <div>
          <p class="text-xs text-white/50">{{ t('shopAdmin.money.sold') }}</p>
          <p class="font-display text-3xl font-bold text-[#7fe0bd]">{{ moneyShort(data.total) }}</p>
        </div>
        <div class="text-right">
          <p class="text-xs text-white/50">{{ t('shopAdmin.money.thisMonth') }}</p>
          <p class="font-display text-xl font-bold">{{ moneyShort(thisMonth) }}</p>
        </div>
      </div>
      <dl class="mt-3 space-y-1.5 border-t border-white/10 pt-3 text-sm">
        <div class="flex items-baseline justify-between gap-3">
          <dt class="text-white/60">{{ t('shopAdmin.money.soldLine') }}</dt>
          <dd class="font-mono text-white/80">{{ moneyShort(data.total) }}</dd>
        </div>
        <div class="flex items-baseline justify-between gap-3">
          <dt class="text-white/60">
            {{ t('shopAdmin.money.cost') }}
            <RouterLink to="/admin/expenses" class="text-xs text-white/40 underline-offset-2 hover:underline">{{ t('shopAdmin.money.costFrom') }}</RouterLink>
          </dt>
          <dd class="font-mono text-[#ffb08a]">{{ data.cost > 0 ? '−' : '' }}{{ moneyShort(data.cost) }}</dd>
        </div>
        <div class="flex items-baseline justify-between gap-3">
          <dt class="font-medium">{{ t('shopAdmin.money.profit') }}</dt>
          <dd class="font-mono text-base font-bold" :class="data.profit >= 0 ? 'text-status-success' : 'text-status-error'">
            {{ moneyShort(data.profit) }}
          </dd>
        </div>
      </dl>
    </div>

    <div class="grid grid-cols-2 gap-2.5">
      <div class="hud-panel border border-brand-pink/20 bg-brand-surface p-3">
        <p class="text-xs text-white/50">{{ t('shopAdmin.money.pending', { n: data.pending_orders }) }}</p>
        <p class="font-display text-lg font-bold" :class="data.pending_orders ? 'text-[#ffd34d]' : 'text-white/60'">
          {{ moneyShort(data.pending_amount) }}
        </p>
        <p class="text-[11px] text-white/40">{{ t('shopAdmin.money.pendingNote') }}</p>
      </div>
      <div class="hud-panel border border-brand-pink/20 bg-brand-surface p-3">
        <p class="text-xs text-white/50">{{ t('shopAdmin.money.toShip') }}</p>
        <p class="font-display text-lg font-bold">{{ t('shopAdmin.money.orders', { n: data.to_ship }) }}</p>
        <p class="text-[11px] text-white/40">{{ t('shopAdmin.money.toShipNote') }}</p>
      </div>
    </div>

    <div v-if="data.top.length" class="hud-panel border border-brand-pink/20 bg-brand-surface p-3">
      <p class="text-xs text-white/50">{{ t('shopAdmin.money.top') }}</p>
      <ul class="mt-2 space-y-2">
        <li v-for="item in data.top" :key="item.name">
          <div class="flex items-baseline gap-2 text-sm">
            <span class="min-w-0 truncate">{{ item.name }}</span>
            <span class="shrink-0 text-xs text-white/50">{{ t('shopAdmin.money.qty', { n: item.qty }) }}</span>
            <span class="ml-auto shrink-0 font-mono text-white/80">{{ moneyShort(item.amount) }}</span>
          </div>
          <div class="mt-1 h-1.5 overflow-hidden rounded-full bg-white/8">
            <div class="h-full rounded-full" :style="{ width: `${(item.amount / topMax) * 100}%`, backgroundColor: SHOP_COLOR }" />
          </div>
        </li>
      </ul>
    </div>
  </section>
</template>
