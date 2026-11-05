<script setup lang="ts">
/**
 * "My credit" in LINE: the balance and every change to it, and topping up
 * — pick a package, pay its price with the club's QR, send the slip. The
 * credit arrives when an admin has checked the slip (CreditView), never
 * from the slip alone.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import * as lineApi from '@/api/line'
import type { LedgerEntry, LineCredit } from '@/api/line'
import type { PaymentInfoResponse } from '@/types'
import { apiErrorMessage } from '@/api/errors'
import { compressImage } from '@/utils/imageCompression'
import { formatDayMonth, formatTime } from '@/utils/format'
import type { Locale } from '@/i18n'
import BrandQr from '@/components/common/BrandQr.vue'
import CreditCardFace from '@/components/credit/CreditCardFace.vue'
import CreditCardMark from '@/components/credit/CreditCardMark.vue'

const props = defineProps<{ token: string }>()
const emit = defineEmits<{ back: [] }>()
const { t, locale } = useI18n()

const data = ref<LineCredit | null>(null)
const problem = ref('')
const busy = ref(false)
const pick = ref<string | null>(null)
const info = ref<PaymentInfoResponse | null>(null)
const tab = ref<'all' | 'in' | 'out'>('all')

const num = (n: number): string => n.toLocaleString('en-US')
// what a package earns: 1,000 credit or more a pink card, 5,000 a black one
const packTier = (credits: number): 'pink' | 'black' | null => (credits >= 5000 ? 'black' : credits >= 1000 ? 'pink' : null)
const baht = (n: number): string => `฿${n.toLocaleString('en-US', { maximumFractionDigits: 2 })}`

async function load(): Promise<void> {
  try {
    data.value = await lineApi.getCredit(props.token)
    problem.value = ''
  } catch (e) {
    problem.value = apiErrorMessage(e, t('lineCredit.loadFailed'))
  }
}
onMounted(load)

const pending = computed(() => data.value?.pending ?? null)
const waiting = computed(() => !!pending.value?.slip_url)
const chosen = computed(() => data.value?.packages.find((p) => p.id === pick.value) ?? data.value?.packages[0] ?? null)

// The QR for the package being paid, fetched when one is picked.
watch(
  () => (pending.value && !pending.value.slip_url ? pending.value.id : null),
  async (id) => {
    info.value = null
    if (!id) return
    try {
      info.value = await lineApi.getTopupPayInfo(props.token, id)
    } catch (e) {
      problem.value = apiErrorMessage(e, t('lineCredit.payInfoFailed'))
    }
  },
)

async function run(job: () => Promise<LineCredit>, failed: string): Promise<void> {
  if (busy.value) return
  busy.value = true
  problem.value = ''
  try {
    data.value = await job()
  } catch (e) {
    problem.value = apiErrorMessage(e, t(failed))
    await load()
  } finally {
    busy.value = false
  }
}

function start(): void {
  const p = chosen.value
  if (p) void run(() => lineApi.startTopup(props.token, p.id), 'lineCredit.startFailed')
}

async function attach(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  const id = pending.value?.id
  if (!file || !id) return
  await run(async () => lineApi.sendTopupSlip(props.token, id, await compressImage(file)), 'lineCredit.slipFailed')
}

function cancel(): void {
  const id = pending.value?.id
  if (id) void run(() => lineApi.cancelTopup(props.token, id), 'lineCredit.cancelFailed')
}

const shown = computed<LedgerEntry[]>(() =>
  (data.value?.history ?? []).filter((h) => tab.value === 'all' || (tab.value === 'in' ? h.delta > 0 : h.delta < 0)),
)
const ICON: Record<LedgerEntry['kind'], string> = { topup: '🪙', bill: '🏸', refund: '↩️', adjust: '🛠' }
</script>

<template>
  <section class="flex flex-1 flex-col gap-4">
    <div>
      <p class="world-eyebrow">MY CREDIT</p>
      <h1 class="world-title mt-1 text-2xl">{{ t('lineCredit.title', { name: data?.player.nickname ?? '' }) }}</h1>
    </div>

    <div v-if="data?.card" class="flex flex-col items-center gap-2 py-3">
      <CreditCardFace :tier="data.card.tier" :name="data.player.nickname" :width="280" />
      <p class="mt-2 text-xs text-white/65">{{ t('creditCard.lasts') }}</p>
    </div>

    <div class="wallet">
      <span class="text-xs text-[#ffe9a8]/80">{{ t('lineCredit.balance') }}</span>
      <div class="mt-0.5 flex items-center gap-2.5">
        <span class="coin h-8 w-8 text-base" aria-hidden="true">฿</span>
        <span class="bal">{{ data ? num(data.balance) : '–' }}</span>
      </div>
      <p class="mt-1 text-xs text-white/65">{{ t('lineCredit.what') }}</p>
      <p v-if="data && !data.card" class="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-white/70">
        <CreditCardMark tier="pink" />{{ t('creditCard.howPink') }}
        <CreditCardMark tier="black" />{{ t('creditCard.howBlack') }}
      </p>
    </div>

    <p v-if="problem" class="text-sm text-status-error" role="alert">{{ problem }}</p>
    <p v-else-if="!data" class="text-sm text-white/60" role="status">{{ t('common.loading') }}</p>

    <template v-if="data">
      <!-- slip sent: waiting for the admin -->
      <div v-if="pending && waiting" class="world-card flex flex-col items-center gap-3 p-4 text-center">
        <img :src="pending.slip_url ?? ''" :alt="t('lineCredit.slipAlt')" class="max-h-48 w-auto rounded-xl border border-white/15 object-contain" />
        <h2 class="world-title text-xl">{{ t('lineCredit.sentTitle') }}</h2>
        <p class="text-sm text-white/75">{{ t('lineCredit.sentBody', { credits: num(pending.credits), price: baht(pending.price) }) }}</p>
        <span v-if="pending.slip_sent_at" class="text-xs text-white/50">{{ t('lineCredit.sentAt', { time: formatTime(pending.slip_sent_at, locale as Locale) }) }}</span>
        <div class="flex w-full gap-2">
          <label class="glass-pill flex-1 cursor-pointer justify-center">
            {{ busy ? t('lineCredit.sending') : t('lineCredit.resend') }}
            <input type="file" accept="image/*" class="sr-only" :disabled="busy" @change="attach" />
          </label>
          <button type="button" class="glass-pill flex-1 justify-center" :disabled="busy" @click="cancel">{{ t('lineCredit.cancel') }}</button>
        </div>
      </div>

      <!-- a package picked: pay it -->
      <div v-else-if="pending" class="flex flex-col gap-3">
        <div class="world-card flex flex-col items-center gap-2 p-4 text-center">
          <span class="text-sm text-white/75">{{ t('lineCredit.payFor', { credits: num(pending.credits) }) }}</span>
          <BrandQr
            v-if="info?.qr_modules"
            :modules="info.qr_modules"
            :amount="pending.price"
            :account-name="info.bank_account_name"
            :alt="t('lineCredit.qrAlt', { price: baht(pending.price) })"
            saveable
            file-name="niddeaw-credit.png"
            class="w-full"
          />
          <img v-else-if="info?.data_uri" :src="info.data_uri" :alt="t('lineCredit.qrAlt', { price: baht(pending.price) })" class="h-56 w-56 rounded-xl bg-white p-2" />
          <div v-else class="flex h-56 w-56 items-center justify-center rounded-xl bg-white/5 text-sm text-white/50">{{ t('common.loading') }}</div>
          <span v-if="!info?.qr_modules" class="font-display text-3xl font-bold text-[#ffd34d]">{{ baht(pending.price) }}</span>
          <span v-if="info?.bank_account_number" class="text-sm text-white/80">
            {{ info.bank_name }} · <b class="font-display tracking-wide">{{ info.bank_account_number }}</b>
            <template v-if="info.bank_account_name"><br />{{ info.bank_account_name }}</template>
          </span>
        </div>
        <p class="text-xs text-white/55">{{ t('lineCredit.payNote') }}</p>
        <label class="gold-cta cursor-pointer" :class="{ 'is-busy': busy }">
          {{ busy ? t('lineCredit.sending') : t('lineCredit.attach') }}
          <input type="file" accept="image/*" class="sr-only" :disabled="busy" @change="attach" />
        </label>
        <button type="button" class="glass-pill justify-center" :disabled="busy" @click="cancel">{{ t('lineCredit.changePackage') }}</button>
      </div>

      <!-- nothing waiting: pick a package -->
      <div v-else class="flex flex-col gap-3">
        <p v-if="data.rejected" class="rounded-2xl border border-status-error/40 bg-status-error/10 p-3 text-sm text-[#ff9fb2]" role="alert">
          {{ t('lineCredit.rejected', { note: data.rejected.note ?? '' }) }}
        </p>
        <h2 class="world-title text-lg">{{ t('lineCredit.pickTitle') }}</h2>
        <p v-if="data.packages.length === 0" class="text-sm text-white/60">{{ t('lineCredit.noPackages') }}</p>
        <div role="radiogroup" :aria-label="t('lineCredit.pickTitle')" class="flex flex-col gap-3">
          <button
            v-for="p in data.packages"
            :key="p.id"
            type="button"
            role="radio"
            :aria-checked="chosen?.id === p.id"
            class="pkg"
            :class="{ on: chosen?.id === p.id }"
            @click="pick = p.id"
          >
            <span v-if="p.credits > p.price" class="tag">{{ t('lineCredit.bonus', { pct: Math.round((1 - p.price / p.credits) * 100) }) }}</span>
            <span class="coin h-7 w-7 text-sm" aria-hidden="true">฿</span>
            <span class="flex flex-col text-left">
              <span class="font-display text-[22px] font-bold text-[#ffe9a8]">{{ num(p.credits) }}</span>
              <span class="flex items-center gap-1.5 text-xs text-white/60">{{ t('lineCredit.credits') }}<template v-if="packTier(p.credits)"> · <CreditCardMark :tier="packTier(p.credits)" />{{ t(`creditCard.${packTier(p.credits)}`) }}</template></span>
            </span>
            <span class="ml-auto text-right">
              <span class="block text-xs text-white/60">{{ t('lineCredit.pay') }}</span>
              <b class="font-display text-lg">{{ baht(p.price) }}</b>
            </span>
          </button>
        </div>
        <button v-if="chosen" type="button" class="gold-cta" :class="{ 'is-busy': busy }" :disabled="busy" @click="start">
          {{ t('lineCredit.buy', { price: baht(chosen.price), credits: num(chosen.credits) }) }}
        </button>
      </div>

      <!-- history -->
      <div class="flex flex-col gap-2">
        <div class="flex gap-1.5" role="tablist">
          <button
            v-for="x in (['all', 'in', 'out'] as const)"
            :key="x"
            type="button"
            role="tab"
            :aria-selected="tab === x"
            class="tap rounded-full px-3.5 text-sm"
            :class="tab === x ? 'bg-white/20 font-medium text-white' : 'border border-white/15 text-white/70'"
            @click="tab = x"
          >
            {{ t(`lineCredit.tab.${x}`) }}
          </button>
        </div>
        <ul v-if="shown.length" class="world-card divide-y divide-white/8 px-4">
          <li v-for="h in shown" :key="h.id" class="flex items-center gap-3 py-2.5">
            <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-white/8 text-base" aria-hidden="true">{{ ICON[h.kind] }}</span>
            <span class="min-w-0 flex-1">
              <span class="block text-sm">{{ t(`lineCredit.kind.${h.kind}`) }}</span>
              <span class="block truncate text-xs text-white/55">{{ formatDayMonth(h.created_at, locale as Locale) }}<template v-if="h.note"> · {{ h.note }}</template></span>
            </span>
            <span class="shrink-0 text-right">
              <b class="block font-display" :class="h.delta > 0 ? 'text-[#7ff0b4]' : 'text-[#ffb08a]'">{{ h.delta > 0 ? '+' : '−' }}{{ num(Math.abs(h.delta)) }}</b>
              <span class="block text-[11px] text-white/45">{{ t('lineCredit.after', { n: num(h.balance_after) }) }}</span>
            </span>
          </li>
        </ul>
        <p v-else class="world-card p-4 text-center text-sm text-white/55">{{ t('lineCredit.noHistory') }}</p>
      </div>
    </template>

    <button type="button" class="glass-pill mt-auto w-full justify-center" @click="emit('back')">{{ t('lineCredit.back') }}</button>
  </section>
</template>

<style scoped>
.wallet {
  position: relative;
  overflow: hidden;
  border-radius: 20px;
  padding: 16px;
  background:
    radial-gradient(260px 160px at 85% 10%, rgb(255 197 49 / 0.35), transparent 70%),
    linear-gradient(135deg, #3a2408, #1c1030 70%);
  border: 1px solid rgb(255 211 77 / 0.45);
  box-shadow: 0 14px 30px -14px rgb(255 197 49 / 0.6);
}
.bal {
  font: 700 34px 'Chakra Petch', sans-serif;
  color: #ffe9a8;
  text-shadow: 0 0 16px rgb(255 197 49 / 0.5);
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
  box-shadow: inset 0 -2px 0 rgb(0 0 0 / 0.2), 0 0 12px rgb(255 197 49 / 0.5);
}
.pkg {
  position: relative;
  display: flex;
  min-height: 72px;
  width: 100%;
  align-items: center;
  gap: 12px;
  border-radius: 16px;
  border: 1.5px solid rgb(255 255 255 / 0.14);
  background: rgb(255 255 255 / 0.05);
  padding: 14px;
  color: #fff;
}
.pkg.on {
  border-color: #ffd34d;
  background: rgb(255 211 77 / 0.12);
  box-shadow: 0 0 0 1px rgb(255 211 77 / 0.4);
}
.tag {
  position: absolute;
  right: 12px;
  top: -10px;
  display: flex;
  height: 20px;
  align-items: center;
  border-radius: 999px;
  background: #ff5078;
  padding: 0 8px;
  font: 700 11px 'Chakra Petch', sans-serif;
}
.gold-cta {
  display: flex;
  min-height: 56px;
  width: 100%;
  align-items: center;
  justify-content: center;
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
