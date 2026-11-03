<script setup lang="ts">
/**
 * Checking out from LINE, which bills the night there and then: the same
 * sum the admin's "bill this player" works out (services/night_bill.py),
 * shown before they tap. While a match of theirs is still queued or on
 * court they can't — the bill would miss it.
 */
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as lineApi from '@/api/line'
import type { LineBill, LineTonight } from '@/api/line'
import { apiErrorMessage } from '@/api/errors'
import { formatDateWithWeekday, money } from '@/utils/format'
import type { Locale } from '@/i18n'
import LineBillPay from '@/components/line/LineBillPay.vue'

const props = defineProps<{ token: string; initial: LineTonight }>()
const emit = defineEmits<{ bills: [] }>()
const { t, locale } = useI18n()

const now = ref<LineTonight>(props.initial)
const sending = ref(false)
const problem = ref('')

async function refresh(): Promise<void> {
  now.value = await lineApi.getTonight(props.token)
}

async function checkOut(): Promise<void> {
  if (!now.value.night || sending.value) return
  sending.value = true
  problem.value = ''
  try {
    now.value = await lineApi.checkOut(props.token, now.value.night.id)
  } catch (e) {
    problem.value = apiErrorMessage(e, t('lineCheckout.failed'))
    await refresh().catch(() => undefined)
  } finally {
    sending.value = false
  }
}

function onPaid(bill: LineBill): void {
  if (now.value.bill) now.value = { ...now.value, bill }
}
</script>

<template>
  <section class="flex flex-1 flex-col gap-4">
    <!-- not in tonight -->
    <template v-if="now.state === 'none'">
      <div class="mt-6 flex flex-col items-center gap-3 text-center">
        <img src="/tiers/beer.webp" alt="" width="120" height="120" class="h-28 w-28 object-contain" />
        <h1 class="world-title text-2xl">{{ t('lineCheckout.noneTitle') }}</h1>
        <p class="text-white/75">{{ t('lineCheckout.noneBody') }}</p>
      </div>
      <button type="button" class="glass-pill mt-auto w-full justify-center" @click="emit('bills')">{{ t('lineCheckout.myBills') }}</button>
    </template>

    <!-- in: the bill so far, and the button -->
    <template v-else-if="now.state === 'in'">
      <div>
        <p class="world-eyebrow">TONIGHT · {{ now.night ? formatDateWithWeekday(now.night.date, locale as Locale) : '' }}</p>
        <h1 class="world-title mt-1 text-2xl">{{ t('lineCheckout.title', { name: now.player?.nickname }) }}</h1>
      </div>
      <dl class="world-card space-y-2.5 p-4 text-[15px]">
        <div class="flex justify-between"><dt>{{ t('lineCheckout.played') }}</dt><dd class="font-display font-bold">{{ t('lineCheckout.games', { n: now.games }) }}</dd></div>
        <div class="flex justify-between text-white/75"><dt>{{ t('lineCheckout.court') }}</dt><dd>{{ money(now.games > 0 ? now.court_fee : 0) }}</dd></div>
        <div class="flex justify-between text-white/75"><dt>{{ t('lineCheckout.shuttles', { n: now.games, price: money(now.shuttle_price) }) }}</dt><dd>{{ money(now.games * now.shuttle_price) }}</dd></div>
        <div class="border-t border-white/10" />
        <div class="flex items-baseline justify-between"><dt class="font-medium">{{ t('lineCheckout.total') }}</dt><dd class="font-display text-2xl font-bold text-[#ffd34d]">{{ money(now.amount) }}</dd></div>
      </dl>
      <p v-if="now.busy" class="rounded-2xl border border-[#ffd34d]/40 bg-[#ffd34d]/10 p-3 text-sm" role="status">
        <b class="text-[#ffd34d]">{{ t('lineCheckout.busyTitle') }}</b> — {{ t('lineCheckout.busyBody') }}
      </p>
      <p v-else-if="now.games === 0" class="rounded-2xl border border-[#7ff0b4]/40 bg-[#7ff0b4]/10 p-3 text-sm">
        {{ t('lineCheckout.freeBody') }}
      </p>
      <p class="text-xs text-white/55">{{ t('lineCheckout.comeBack') }}</p>
      <p v-if="problem" class="text-sm text-status-error" role="alert">{{ problem }}</p>
      <button type="button" class="cta mt-auto min-h-16 rounded-2xl font-display text-lg font-bold" :disabled="now.busy || sending" @click="checkOut">
        {{ now.busy ? t('lineCheckout.waitMatch') : sending ? t('lineCheckout.sending') : now.amount > 0 ? t('lineCheckout.checkOutPay', { amount: money(now.amount) }) : t('lineCheckout.checkOut') }}
      </button>
    </template>

    <!-- out: the bill, and paying it -->
    <template v-else>
      <p class="flex items-center gap-2 rounded-2xl border border-[#7ff0b4]/35 bg-[#7ff0b4]/10 px-3 py-2.5 text-sm">
        <span class="text-[#7ff0b4]" aria-hidden="true">✓</span> {{ t('lineCheckout.outLine') }}
      </p>
      <div v-if="now.bill && now.bill.amount > 0" class="flex flex-col items-center gap-3">
        <LineBillPay :token="token" :bill="now.bill" @updated="onPaid" />
      </div>
      <div v-else class="world-card flex flex-col items-center gap-1 p-5 text-center">
        <span class="font-display text-lg font-bold text-[#7ff0b4]">{{ t('lineCheckout.freeTitle') }}</span>
        <span class="text-sm text-white/65">{{ t('lineCheckout.thanks') }}</span>
      </div>
      <button type="button" class="glass-pill mt-auto w-full justify-center" @click="emit('bills')">{{ t('lineCheckout.myBills') }}</button>
    </template>
  </section>
</template>

<style scoped>
.cta {
  background: linear-gradient(#ff8fd0, #ea4ca4);
  color: #1a0410;
  box-shadow: 0 8px 22px rgb(234 76 164 / 0.45);
}
.cta:disabled {
  background: #3a1d3a;
  color: rgb(255 255 255 / 0.5);
  box-shadow: none;
}
</style>
