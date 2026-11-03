<script setup lang="ts">
/**
 * Paying one bill from LINE: the club's QR (PromptPay with the amount in
 * it, or whatever Settings has) and "I've transferred — here's the slip".
 *
 * The slip doesn't make the bill paid; an admin checks it against the
 * account and marks it paid from Billing. Until then it reads "waiting
 * for the admin". If they refuse it, the member is asked for another.
 */
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as lineApi from '@/api/line'
import type { LineBill } from '@/api/line'
import type { PaymentInfoResponse } from '@/types'
import { apiErrorMessage } from '@/api/errors'
import { compressImage } from '@/utils/imageCompression'
import { formatDateWithWeekday, formatTime, money } from '@/utils/format'
import type { Locale } from '@/i18n'

const props = defineProps<{ token: string; bill: LineBill }>()
const emit = defineEmits<{ updated: [bill: LineBill] }>()
const { t, locale } = useI18n()

const info = ref<PaymentInfoResponse | null>(null)
const problem = ref('')
const sending = ref(false)

const waiting = (b: LineBill): boolean => b.paid_status === 'unpaid' && !!b.slip_url

onMounted(async () => {
  if (props.bill.paid_status === 'paid' || props.bill.amount <= 0) return
  try {
    info.value = await lineApi.getPayInfo(props.token, props.bill.id)
  } catch (e) {
    problem.value = apiErrorMessage(e, t('lineBills.payInfoFailed'))
  }
})

async function attach(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const picked = input.files?.[0]
  input.value = ''
  if (!picked || sending.value) return
  sending.value = true
  problem.value = ''
  try {
    emit('updated', await lineApi.sendSlip(props.token, props.bill.id, await compressImage(picked)))
  } catch (e) {
    problem.value = apiErrorMessage(e, t('lineBills.slipFailed'))
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <div class="flex w-full flex-col items-stretch gap-3 text-center">
    <!-- paid -->
    <div v-if="bill.paid_status === 'paid'" class="world-card flex flex-col items-center gap-1 p-5">
      <span class="text-3xl text-[#7ff0b4]" aria-hidden="true">✓</span>
      <span class="font-display text-lg font-bold">{{ t('lineBills.paidTitle') }}</span>
      <span class="text-sm text-white/65">{{ money(bill.amount) }} · {{ formatDateWithWeekday(bill.night.date, locale as Locale) }}</span>
    </div>

    <!-- slip sent, waiting for the admin -->
    <template v-else-if="waiting(bill)">
      <div class="flex flex-col items-center gap-3">
        <img :src="bill.slip_url ?? ''" :alt="t('lineBills.slipAlt')" class="max-h-56 w-auto rounded-xl border border-white/15 object-contain shadow-lg" />
        <h2 class="world-title text-2xl">{{ t('lineBills.sentTitle') }}</h2>
        <p class="text-sm text-white/75">{{ t('lineBills.sentBody') }}</p>
      </div>
      <ul class="world-card space-y-2 p-4 text-left text-sm">
        <li><span class="text-[#ffd34d]">●</span> {{ t('lineBills.statusChecking') }} · {{ money(bill.amount) }}</li>
        <li v-if="bill.slip_sent_at"><span class="text-white/40">●</span> {{ t('lineBills.sentAt', { time: formatTime(bill.slip_sent_at, locale as Locale) }) }}</li>
      </ul>
      <label class="glass-pill cursor-pointer justify-center">
        {{ sending ? t('lineBills.sending') : t('lineBills.resendSlip') }}
        <input type="file" accept="image/*" class="sr-only" :disabled="sending" @change="attach" />
      </label>
    </template>

    <!-- to pay -->
    <template v-else>
      <p v-if="bill.slip_rejected_at" class="rounded-2xl border border-status-error/40 bg-status-error/10 p-3 text-sm text-[#ff9fb2]" role="alert">
        {{ t('lineBills.rejected') }}
      </p>
      <div class="world-card flex flex-col items-center gap-2 p-4">
        <span class="text-xs text-white/60">{{ info?.method === 'promptpay' ? t('lineBills.scanPromptPay') : t('lineBills.transferTo') }}</span>
        <img v-if="info?.data_uri" :src="info.data_uri" :alt="t('lineBills.qrAlt', { amount: money(bill.amount) })" class="h-56 w-56 rounded-xl bg-white p-2" />
        <div v-else-if="!info && !problem" class="flex h-56 w-56 items-center justify-center rounded-xl bg-white/5 text-sm text-white/50">{{ t('common.loading') }}</div>
        <span class="font-display text-3xl font-bold text-[#ffd34d]">{{ money(bill.amount) }}</span>
        <span v-if="info?.bank_account_number" class="text-sm text-white/80">
          {{ info.bank_name }} · <b class="font-display tracking-wide">{{ info.bank_account_number }}</b>
          <template v-if="info.bank_account_name"><br />{{ info.bank_account_name }}</template>
        </span>
        <span v-if="info?.data_uri" class="text-xs text-white/45">{{ t('lineBills.saveHint') }}</span>
      </div>
      <p v-if="problem" class="text-sm text-status-error" role="alert">{{ problem }}</p>
      <label class="cta flex min-h-14 cursor-pointer items-center justify-center rounded-2xl font-display text-base font-bold" :class="{ 'is-busy': sending }">
        {{ sending ? t('lineBills.sending') : t('lineBills.attachSlip') }}
        <input type="file" accept="image/*" class="sr-only" :disabled="sending" @change="attach" />
      </label>
    </template>
  </div>
</template>

<style scoped>
.cta {
  background: linear-gradient(#ff8fd0, #ea4ca4);
  color: #1a0410;
  box-shadow: 0 8px 22px rgb(234 76 164 / 0.45);
}
.cta.is-busy {
  background: #3a1d3a;
  color: rgb(255 255 255 / 0.5);
  box-shadow: none;
}
</style>
