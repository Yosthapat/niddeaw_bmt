<script setup lang="ts">
/**
 * Paying one bill from LINE.
 *
 * With club credit: one tap. Enough credit pays it there and then; not
 * enough puts all of it on the bill and the QR asks for the rest. Without
 * credit (or "pay by QR instead"): the club's QR — PromptPay with the
 * amount in it, or whatever Settings has — and "I've transferred — here's
 * the slip".
 *
 * The slip doesn't make the bill paid; an admin checks it against the
 * account and marks it paid from Billing. Until then it reads "waiting
 * for the admin". If they refuse it, the member is asked for another.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import * as lineApi from '@/api/line'
import type { LineBill } from '@/api/line'
import type { PaymentInfoResponse } from '@/types'
import { apiErrorMessage } from '@/api/errors'
import { compressImage } from '@/utils/imageCompression'
import { formatDateWithWeekday, formatTime, money } from '@/utils/format'
import BrandQr from '@/components/common/BrandQr.vue'
import type { Locale } from '@/i18n'

const props = defineProps<{ token: string; bill: LineBill }>()
const emit = defineEmits<{ updated: [bill: LineBill]; topUp: [] }>()
const { t, locale } = useI18n()

const info = ref<PaymentInfoResponse | null>(null)
const problem = ref('')
const sending = ref(false)
/** Their credit balance; null until known (or not theirs to use). */
const balance = ref<number | null>(null)
const byQr = ref(false)
const paying = ref(false)
const num = (n: number): string => n.toLocaleString('en-US')

const waiting = (b: LineBill): boolean => b.paid_status === 'unpaid' && !!b.slip_url
const toPay = computed(() => props.bill.paid_status !== 'paid' && props.bill.amount > 0 && !waiting(props.bill))
/** Whole credits only: satang are left to transfer. */
const usable = computed(() => Math.min(balance.value ?? 0, Math.floor(props.bill.left + 1e-9)))
const rest = computed(() => Math.max(0, Math.round((props.bill.left - usable.value) * 100) / 100))
/** The credit choice comes first, while they have credit and none is on the bill yet. */
const offerCredit = computed(() => toPay.value && !byQr.value && props.bill.credit_used === 0 && usable.value > 0)
const allCredit = computed(() => props.bill.credit_used > 0 && props.bill.credit_used >= props.bill.amount)

async function loadPayInfo(): Promise<void> {
  info.value = null
  if (!toPay.value || props.bill.left <= 0) return
  try {
    info.value = await lineApi.getPayInfo(props.token, props.bill.id)
  } catch (e) {
    problem.value = apiErrorMessage(e, t('lineBills.payInfoFailed'))
  }
}

onMounted(async () => {
  void loadPayInfo()
  if (!toPay.value) return
  try {
    balance.value = (await lineApi.getCredit(props.token)).balance
  } catch {
    balance.value = null // no credit to offer: the QR as before
  }
})
// Credit put on the bill changes what's left — and so the QR's amount.
watch(
  () => props.bill.left,
  (now, before) => {
    if (now !== before) void loadPayInfo()
  },
)

async function payCredit(): Promise<void> {
  if (paying.value) return
  paying.value = true
  problem.value = ''
  try {
    const done = await lineApi.payWithCredit(props.token, props.bill.id)
    balance.value = done.balance
    emit('updated', done.bill)
  } catch (e) {
    problem.value = apiErrorMessage(e, t('lineBills.creditFailed'))
  } finally {
    paying.value = false
  }
}

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
      <span class="font-display text-lg font-bold">{{ allCredit ? t('lineBills.paidCreditTitle') : t('lineBills.paidTitle') }}</span>
      <span class="text-sm text-white/65">{{ money(bill.amount) }} · {{ formatDateWithWeekday(bill.night.date, locale as Locale) }}</span>
      <span v-if="allCredit" class="text-sm text-white/75">{{ t('lineBills.paidCreditBody') }}</span>
      <span v-if="bill.credit_used > 0" class="credit-chip mt-1">
        <span class="coin h-4 w-4 text-[9px]" aria-hidden="true">฿</span>
        {{ allCredit ? t('lineBills.creditChip', { n: num(bill.credit_used) }) : t('lineBills.creditPlusTransfer', { n: num(bill.credit_used), rest: money(bill.amount - bill.credit_used) }) }}
      </span>
      <span v-if="balance !== null && bill.credit_used > 0" class="text-xs text-white/55">{{ t('lineBills.creditLeft', { n: num(balance) }) }}</span>
    </div>

    <!-- slip sent, waiting for the admin -->
    <template v-else-if="waiting(bill)">
      <div class="flex flex-col items-center gap-3">
        <img :src="bill.slip_url ?? ''" :alt="t('lineBills.slipAlt')" class="max-h-56 w-auto rounded-xl border border-white/15 object-contain shadow-lg" />
        <h2 class="world-title text-2xl">{{ t('lineBills.sentTitle') }}</h2>
        <p class="text-sm text-white/75">{{ t('lineBills.sentBody') }}</p>
      </div>
      <ul class="world-card space-y-2 p-4 text-left text-sm">
        <li><span class="text-[#ffd34d]">●</span> {{ t('lineBills.statusChecking') }} · {{ money(bill.left) }}</li>
        <li v-if="bill.credit_used > 0"><span class="text-[#ffc531]">●</span> {{ t('lineBills.creditOnBill', { n: num(bill.credit_used) }) }}</li>
        <li v-if="bill.slip_sent_at"><span class="text-white/40">●</span> {{ t('lineBills.sentAt', { time: formatTime(bill.slip_sent_at, locale as Locale) }) }}</li>
      </ul>
      <label class="glass-pill cursor-pointer justify-center">
        {{ sending ? t('lineBills.sending') : t('lineBills.resendSlip') }}
        <input type="file" accept="image/*" class="sr-only" :disabled="sending" @change="attach" />
      </label>
    </template>

    <!-- to pay with credit: one tap -->
    <template v-else-if="offerCredit">
      <div class="wallet flex items-center gap-2.5 text-left">
        <span class="coin h-8 w-8 text-base" aria-hidden="true">฿</span>
        <span class="flex flex-col">
          <span class="text-xs text-[#ffe9a8]/80">{{ t('lineBills.creditHave') }}</span>
          <b class="bal">{{ num(balance ?? 0) }}</b>
        </span>
        <span v-if="rest > 0" class="short ml-auto">{{ t('lineBills.creditShort', { gap: money(rest) }) }}</span>
      </div>
      <div v-if="rest > 0" class="world-card flex flex-col gap-1.5 p-4 text-left text-sm">
        <div class="flex justify-between text-white/70"><span>{{ t('lineBills.useAllCredit') }}</span><span class="text-[#ffd34d]">−{{ money(usable) }}</span></div>
        <div class="flex justify-between"><span>{{ t('lineBills.transferRest') }}</span><b class="font-display">{{ money(rest) }}</b></div>
      </div>
      <p v-if="problem" class="text-sm text-status-error" role="alert">{{ problem }}</p>
      <button type="button" class="gold-cta" :class="{ 'is-busy': paying }" :disabled="paying" @click="payCredit">
        <span class="coin h-5 w-5 text-[11px]" aria-hidden="true">฿</span>
        {{ paying ? t('lineBills.creditPaying') : rest > 0 ? t('lineBills.creditSplitCta', { n: num(usable), rest: money(rest) }) : t('lineBills.creditPayCta', { n: num(usable) }) }}
      </button>
      <button v-if="rest > 0" type="button" class="glass-pill justify-center" @click="emit('topUp')">{{ t('lineBills.topUpFirst') }}</button>
      <button type="button" class="glass-pill justify-center" @click="byQr = true">{{ t('lineBills.payByQr', { amount: money(bill.left) }) }}</button>
    </template>

    <!-- to pay by transfer (all of it, or what credit didn't cover) -->
    <template v-else>
      <p v-if="bill.slip_rejected_at" class="rounded-2xl border border-status-error/40 bg-status-error/10 p-3 text-sm text-[#ff9fb2]" role="alert">
        {{ t('lineBills.rejected') }}
      </p>
      <p v-if="bill.credit_used > 0" class="credit-chip self-center">
        <span class="coin h-4 w-4 text-[9px]" aria-hidden="true">฿</span>
        {{ t('lineBills.creditTaken', { n: num(bill.credit_used) }) }}
      </p>
      <div class="world-card flex flex-col items-center gap-2 p-4">
        <span class="text-xs text-white/60">{{ bill.credit_used > 0 ? t('lineBills.scanRest') : info?.method === 'promptpay' ? t('lineBills.scanPromptPay') : t('lineBills.transferTo') }}</span>
        <BrandQr
          v-if="info?.qr_modules"
          :modules="info.qr_modules"
          :amount="bill.left"
          :account-name="info.bank_account_name"
          :alt="t('lineBills.qrAlt', { amount: money(bill.left) })"
          saveable
          :file-name="`niddeaw-bill-${bill.night.date}.png`"
          class="w-full"
        />
        <img v-else-if="info?.data_uri" :src="info.data_uri" :alt="t('lineBills.qrAlt', { amount: money(bill.left) })" class="h-56 w-56 rounded-xl bg-white p-2" />
        <div v-else-if="!info && !problem" class="flex h-56 w-56 items-center justify-center rounded-xl bg-white/5 text-sm text-white/50">{{ t('common.loading') }}</div>
        <span v-if="!info?.qr_modules" class="font-display text-3xl font-bold text-[#ffd34d]">{{ money(bill.left) }}</span>
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
      <button v-if="byQr && bill.credit_used === 0" type="button" class="glass-pill justify-center" @click="byQr = false">{{ t('lineBills.backToCredit') }}</button>
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
.wallet {
  border-radius: 18px;
  padding: 12px 14px;
  background:
    radial-gradient(220px 120px at 85% 10%, rgb(255 197 49 / 0.32), transparent 70%),
    linear-gradient(135deg, #3a2408, #1c1030 70%);
  border: 1px solid rgb(255 211 77 / 0.45);
}
.bal {
  font: 700 22px 'Chakra Petch', sans-serif;
  color: #ffe9a8;
}
.short {
  border-radius: 999px;
  background: rgb(255 211 77 / 0.15);
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 600;
  color: #ffd34d;
}
.coin {
  display: inline-flex;
  flex: none;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 30%, #fff2b3, #ffc531 45%, #c98500);
  color: #4a2d00;
  font-family: 'Chakra Petch', sans-serif;
  font-weight: 700;
}
.credit-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: 999px;
  border: 1px solid rgb(255 211 77 / 0.4);
  background: rgb(255 211 77 / 0.1);
  padding: 5px 12px;
  font-size: 13px;
  color: #ffe9a8;
}
.gold-cta {
  display: flex;
  min-height: 56px;
  width: 100%;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-radius: 16px;
  background: linear-gradient(#ffe58a, #ffad1f);
  color: #2e1a00;
  font: 700 16px 'Chakra Petch', sans-serif;
  box-shadow: 0 8px 22px rgb(255 173 31 / 0.45);
}
.gold-cta.is-busy,
.gold-cta:disabled {
  background: #3a2a10;
  color: rgb(255 255 255 / 0.5);
  box-shadow: none;
}
</style>
