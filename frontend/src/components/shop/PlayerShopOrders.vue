<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getMemberOrders } from '@/api/public'
import { orderNo, type OrderStatus, type ShopOrder } from '@/types'
import { formatDayMonth, money } from '@/utils/format'

const props = defineProps<{ playerId: string }>()
const { t, locale } = useI18n()
const orders = ref<ShopOrder[]>([])

// Quiet when it fails or there's nothing: most members never buy anything,
// and a profile isn't the place to say the shop is down.
watch(
  () => props.playerId,
  async (id) => {
    try {
      orders.value = await getMemberOrders(id)
    } catch {
      orders.value = []
    }
  },
  { immediate: true },
)

const TONE: Record<OrderStatus, string> = {
  pending: 'bg-[#ffe14d]/15 text-[#ffe14d]',
  confirmed: 'bg-brand-pink/20 text-brand-pink-light',
  delivered: 'bg-status-success/15 text-status-success',
  rejected: 'bg-status-error/15 text-status-error',
}
</script>

<template>
  <section v-if="orders.length" class="mt-6">
    <p class="world-eyebrow">ORDERS</p>
    <h2 class="world-title mt-1 text-lg">{{ t('shop.myOrders') }}</h2>
    <ul class="mt-3 flex flex-col gap-2">
      <li
        v-for="o in orders"
        :key="o.id"
        class="world-card flex flex-col gap-1 !rounded-[18px] px-4 py-3"
      >
        <div class="flex items-start justify-between gap-3">
          <p class="text-xs text-white/60">{{ orderNo(o.order_no) }} · {{ formatDayMonth(o.created_at, locale as 'th' | 'en') }}</p>
          <span class="shrink-0 font-display font-bold">{{ money(o.total) }}</span>
        </div>
        <ul class="flex flex-col gap-0.5 text-sm">
          <li v-for="(item, i) in o.items" :key="i" class="flex justify-between gap-3">
            <span class="min-w-0 truncate">{{ item.product_name }}<span v-if="item.size" class="text-white/60"> · {{ item.size }}</span></span>
            <span class="shrink-0 text-white/70">× {{ item.qty }}</span>
          </li>
        </ul>
        <span class="self-start rounded-full px-2.5 py-1 text-xs leading-none font-medium" :class="TONE[o.status]">
          {{ t(`shop.status.${o.status}`) }}
        </span>
        <p v-if="o.status === 'rejected' && o.note" class="text-xs text-white/70">{{ t('shop.rejectedWhy', { note: o.note }) }}</p>
      </li>
    </ul>
  </section>
</template>
