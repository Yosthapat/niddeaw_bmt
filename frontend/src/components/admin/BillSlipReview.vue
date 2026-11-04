<script setup lang="ts">
/**
 * A slip a member sent from LINE for one bill: the admin checks it against
 * the club's account, then says it's paid — or that it isn't, which
 * removes the slip and asks the member for another.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as adminApi from '@/api/admin'
import { apiErrorMessage } from '@/api/errors'
import { effectiveAmount, leftToPay } from '@/types'
import type { Billing } from '@/types'
import { formatDateTime, money } from '@/utils/format'
import type { Locale } from '@/i18n'

const props = defineProps<{ bill: Billing; name: string }>()
const emit = defineEmits<{ close: []; updated: [bill: Billing] }>()
const { t, locale } = useI18n()

const busy = ref(false)
const problem = ref('')

async function decide(ok: boolean): Promise<void> {
  busy.value = true
  problem.value = ''
  try {
    const updated = ok ? await adminApi.setBillingPaidStatus(props.bill.id, 'paid') : await adminApi.rejectBillSlip(props.bill.id)
    emit('updated', updated)
    emit('close')
  } catch (e) {
    problem.value = apiErrorMessage(e, t('billing.paidStatusFailed'))
  } finally {
    busy.value = false
  }
}

function onKey(e: KeyboardEvent): void {
  if (e.key === 'Escape') emit('close')
}
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-40 flex items-end justify-center bg-black/75 p-3 backdrop-blur-sm sm:items-center" role="dialog" aria-modal="true" :aria-label="t('billSlip.title', { name })" @click.self="emit('close')">
      <div class="hud-panel flex max-h-[92dvh] w-full max-w-sm flex-col gap-3 overflow-y-auto border border-brand-pink/30 bg-brand-surface p-4 text-center">
        <p class="font-display text-xs font-bold tracking-[0.25em] text-brand-pink">SLIP · {{ name }}</p>
        <h2 class="font-display text-2xl font-bold">{{ t('billSlip.amount', { amount: money(leftToPay(bill)) }) }}</h2>
        <p v-if="(bill.credit_used ?? 0) > 0" class="text-xs text-[#ffe9a8]">{{ t('billSlip.creditPart', { total: money(effectiveAmount(bill)), n: (bill.credit_used ?? 0).toLocaleString('en-US') }) }}</p>
        <a v-if="bill.slip_url" :href="bill.slip_url" target="_blank" rel="noopener" class="block">
          <img :src="bill.slip_url" :alt="t('billSlip.title', { name })" class="mx-auto max-h-[52dvh] w-auto rounded-xl bg-white object-contain" />
        </a>
        <p v-if="bill.slip_sent_at" class="text-xs text-white/50">{{ t('billSlip.sentAt', { time: formatDateTime(bill.slip_sent_at, locale as Locale) }) }}</p>
        <p v-if="problem" class="text-sm text-status-error" role="alert">{{ problem }}</p>
        <template v-if="bill.paid_status !== 'paid'">
          <button type="button" class="tap rounded-full bg-status-success px-4 text-sm font-semibold text-brand-black disabled:opacity-50" :disabled="busy" @click="decide(true)">
            {{ t('billSlip.approve') }}
          </button>
          <button type="button" class="tap rounded-full border border-status-error/50 px-4 text-sm font-semibold text-status-error disabled:opacity-50" :disabled="busy" @click="decide(false)">
            {{ t('billSlip.reject') }}
          </button>
        </template>
        <button type="button" class="tap rounded-full border border-white/20 px-4 text-sm text-white/70" @click="emit('close')">{{ t('line.close') }}</button>
      </div>
    </div>
  </Teleport>
</template>
