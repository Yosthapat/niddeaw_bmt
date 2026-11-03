<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSessionsStore } from '@/stores/sessions'
import { usePlayersStore } from '@/stores/players'
import * as adminApi from '@/api/admin'
import { effectiveAmount, isFree } from '@/types'
import type { Billing, Checkin, PaymentInfoResponse } from '@/types'
import AdminNav from '@/components/layout/AdminNav.vue'
import { money } from '@/utils/format'
import SessionPicker from '@/components/layout/SessionPicker.vue'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'
import { bahtProblem } from '@/utils/limits'
import { apiErrorMessage } from '@/api/errors'
import { usePolling } from '@/composables/usePolling'
import BillSlipReview from '@/components/admin/BillSlipReview.vue'
import BrandQr from '@/components/common/BrandQr.vue'

const { t } = useI18n()
const sessionsStore = useSessionsStore()
const playersStore = usePlayersStore()

const billings = ref<Billing[]>([])
const checkins = ref<Checkin[]>([])
const closing = ref(false)
const billingPlayerId = ref<string | null>(null)
const paymentInfoByBillingId = ref<Record<string, PaymentInfoResponse>>({})
// What the admin has typed per bill. Vue hands a number input's value back
// as a number, so 0 — a member who was hurt and never played — arrives as
// the number 0, which is falsy: "has something been typed" is undefined or
// '' (a cleared box), never a truthiness test.
const editingAdjust = ref<Record<string, string | number>>({})
const hasTyped = (id: string): boolean => editingAdjust.value[id] !== undefined && editingAdjust.value[id] !== ''
// Next to the row it belongs to — the page-level error sits above a list
// that can be twenty bills long, out of sight of the box just typed in.
const adjustError = ref<Record<string, string>>({})
const actionError = ref<string | null>(null)
// A member paid from LINE and attached a slip: waiting for the admin to
// check it against the account (BillSlipReview).
const reviewing = ref<Billing | null>(null)
const waitingSlip = (b: Billing): boolean => b.paid_status !== 'paid' && !!b.slip_url
const slipCount = computed(() => billings.value.filter(waitingSlip).length)
function onReviewed(updated: Billing): void {
  billings.value = billings.value.map((b) => (b.id === updated.id ? updated : b))
}

function nameOf(playerId: string): string {
  const p = playersStore.byId(playerId)
  return p ? p.nickname : '?'
}

function avatarOf(playerId: string): string | undefined {
  return playersStore.byId(playerId)?.avatar_url ?? undefined
}


const unbilledAttendeeIds = computed(() => {
  const billedIds = new Set(billings.value.map((b) => b.player_id))
  const attendeeIds = new Set(checkins.value.map((c) => c.player_id))
  return [...attendeeIds].filter((id) => !billedIds.has(id))
})

// One box filters both lists: on a busy night the person at the table says
// their name, and the admin should not have to know whether they have been
// billed yet to find them. The counts in the headings stay the full ones,
// so a search never looks like people went missing.
const search = ref('')
const matchesSearch = (playerId: string): boolean => {
  const query = search.value.trim().toLowerCase()
  return !query || nameOf(playerId).toLowerCase().includes(query)
}
const visibleUnbilledIds = computed(() => unbilledAttendeeIds.value.filter(matchesSearch))
const visibleBillings = computed(() => billings.value.filter((b) => matchesSearch(b.player_id)))
// The one number the person collecting money wants, on the screen where
// they are collecting it — it lived on the revenue page, a navigation away
// from the table they are standing at.
const totals = computed(() => {
  const paid = billings.value
    .filter((b) => b.paid_status === 'paid')
    .reduce((sum, b) => sum + effectiveAmount(b), 0)
  const due = billings.value
    .filter((b) => b.paid_status !== 'paid')
    .reduce((sum, b) => sum + effectiveAmount(b), 0)
  return { paid, due, total: paid + due }
})

const noSearchResults = computed(
  () =>
    search.value.trim() !== '' &&
    visibleUnbilledIds.value.length === 0 &&
    visibleBillings.value.length === 0,
)

async function refreshBillings(): Promise<void> {
  if (!sessionsStore.currentSessionId) {
    billings.value = []
    checkins.value = []
    return
  }
  ;[billings.value, checkins.value] = await Promise.all([
    adminApi.getBillings(sessionsStore.currentSessionId),
    adminApi.getCheckins(sessionsStore.currentSessionId),
  ])
}

async function billOnePlayer(playerId: string): Promise<void> {
  if (!sessionsStore.currentSessionId) return
  billingPlayerId.value = playerId
  actionError.value = null
  try {
    const billing = await adminApi.billPlayer(sessionsStore.currentSessionId, playerId)
    billings.value = [...billings.value.filter((b) => b.id !== billing.id), billing]
  } catch (e) {
    actionError.value = apiErrorMessage(e, t('billing.billFailed'))
  } finally {
    billingPlayerId.value = null
  }
}

async function closeAndBill(): Promise<void> {
  if (!sessionsStore.currentSessionId) return
  closing.value = true
  actionError.value = null
  try {
    billings.value = await adminApi.closeSessionAndBill(sessionsStore.currentSessionId)
    await sessionsStore.refresh()
  } catch (e) {
    actionError.value = apiErrorMessage(e, t('billing.closeFailed'))
  } finally {
    closing.value = false
  }
}

/** `clear` goes back to the calculated amount, `waive` makes it nothing (a
 *  member who was hurt and never played); otherwise the typed one. */
async function saveAdjust(billing: Billing, preset?: 'clear' | 'waive'): Promise<void> {
  delete adjustError.value[billing.id]
  let amount: number | null = preset === 'waive' ? 0 : null
  if (!preset) {
    const raw = editingAdjust.value[billing.id]
    const problem = bahtProblem(raw, { allowZero: true })
    if (problem) {
      adjustError.value[billing.id] = t(`validation.${problem}`)
      return
    }
    amount = Number(raw)
  }
  try {
    const updated = await adminApi.adjustBilling(billing.id, amount)
    billings.value = billings.value.map((b) => (b.id === updated.id ? updated : b))
    delete editingAdjust.value[billing.id]
    // An open QR was drawn for the old amount.
    delete paymentInfoByBillingId.value[billing.id]
  } catch (e) {
    adjustError.value[billing.id] = apiErrorMessage(e, t('billing.adjustFailed'))
  }
}

async function togglePaid(billing: Billing): Promise<void> {
  actionError.value = null
  try {
    const updated = await adminApi.setBillingPaidStatus(
      billing.id,
      billing.paid_status === 'paid' ? 'unpaid' : 'paid',
    )
    billings.value = billings.value.map((b) => (b.id === updated.id ? updated : b))
  } catch (e) {
    actionError.value = apiErrorMessage(e, t('billing.paidStatusFailed'))
  }
}

async function showQr(billing: Billing): Promise<void> {
  if (paymentInfoByBillingId.value[billing.id]) {
    delete paymentInfoByBillingId.value[billing.id]
    return
  }
  actionError.value = null
  try {
    paymentInfoByBillingId.value[billing.id] = await adminApi.getBillingPaymentInfo(billing.id)
  } catch (e) {
    actionError.value = apiErrorMessage(e, t('billing.qrFailed'))
  }
}

watch(() => sessionsStore.currentSessionId, refreshBillings)

onMounted(async () => {
  await Promise.all([sessionsStore.refresh(), playersStore.ensureLoaded()])
  await refreshBillings()
})
// Slips arrive from members' phones while the admin is on this screen.
usePolling(refreshBillings, 15000)
</script>

<template>
  <AdminNav />
  <main class="mx-auto max-w-3xl px-4 py-6">
    <h1 class="sr-only">{{ t('admin.nav.billing') }}</h1>
    <div class="mt-4">
      <SessionPicker />
    </div>

    <p v-if="actionError" class="mt-4 text-sm text-status-error">{{ actionError }}</p>

    <p v-if="!sessionsStore.currentSessionId" class="mt-8 text-white/60">{{ t('billing.selectSessionFirst') }}</p>

    <template v-else>
      <input
        v-model="search"
        type="search"
        :placeholder="t('billing.searchPlaceholder')"
        :aria-label="t('billing.searchPlaceholder')"
        class="hud-panel mt-4 min-h-11 w-full border border-brand-pink/25 bg-brand-surface px-3 text-sm outline-none focus:border-brand-pink"
      />
      <div v-if="sessionsStore.currentSession?.status === 'open'" class="mt-6">
        <button
          :disabled="closing"
          class="tap w-full rounded-full bg-brand-pink px-4 text-sm font-semibold text-brand-black disabled:opacity-50"
          @click="closeAndBill"
        >
          {{ closing ? t('billing.closing') : t('billing.closeAndBill') }}
        </button>
      </div>

      <section v-if="visibleUnbilledIds.length > 0" class="mt-6">
        <h2 class="text-sm font-semibold text-white/70">{{ t('billing.unbilled') }} ({{ unbilledAttendeeIds.length }})</h2>
        <p class="mt-1 text-xs text-white/40">
          {{ t('billing.unbilledHint') }}
        </p>
        <ul class="mt-2 space-y-2">
          <li
            v-for="pid in visibleUnbilledIds"
            :key="pid"
            class="hud-hover flex items-center gap-3 hud-panel border border-brand-pink/15 bg-brand-surface px-3 py-2"
          >
            <PlayerAvatar :name="nameOf(pid)" :avatar-url="avatarOf(pid)" size="sm" />
            <span class="flex-1 font-medium">{{ nameOf(pid) }}</span>
            <button
              :disabled="billingPlayerId === pid"
              class="tap rounded-full border border-brand-pink px-3 text-xs text-brand-pink hover:bg-brand-pink hover:text-brand-black disabled:opacity-50"
              @click="billOnePlayer(pid)"
            >
              {{ billingPlayerId === pid ? '...' : t('billing.billThisPlayer') }}
            </button>
          </li>
        </ul>
      </section>

      <section v-if="billings.length > 0" class="mt-8">
        <div class="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
          <h2 class="text-sm font-semibold text-white/70">
            {{ t('billing.billed') }} ({{ billings.length }})
          </h2>
          <p class="text-sm">
            <span class="text-white/40">{{ t('billing.collected') }}</span>
            <span class="ml-1 font-semibold text-status-success">{{ money(totals.paid) }}</span>
            <span class="mx-1.5 text-white/20">·</span>
            <span class="text-white/40">{{ t('billing.outstanding') }}</span>
            <span class="ml-1 font-semibold text-brand-pink">{{ money(totals.due) }}</span>
            <template v-if="slipCount > 0">
              <span class="mx-1.5 text-white/20">·</span>
              <span class="text-white/40">{{ t('billSlip.waiting') }}</span>
              <span class="ml-1 font-semibold text-[#cbbfff]">{{ slipCount }}</span>
            </template>
          </p>
        </div>
      </section>

      <p v-if="noSearchResults" class="mt-6 text-sm text-white/40">
        {{ t('billing.noSearchResults') }}
      </p>
      <p v-else-if="billings.length === 0" class="mt-6 text-sm text-white/40">
        {{ t('billing.noBills') }}
      </p>

      <ul v-else-if="visibleBillings.length > 0" class="mt-3 space-y-3">
        <li
          v-for="b in visibleBillings"
          :key="b.id"
          class="hud-hover hud-panel border border-brand-pink/20 bg-brand-surface p-4"
        >
          <div class="flex items-center gap-3">
            <PlayerAvatar :name="nameOf(b.player_id)" :avatar-url="avatarOf(b.player_id)" size="sm" />
            <span class="flex-1 font-medium">{{ nameOf(b.player_id) }}</span>
            <span class="text-xs text-white/40">{{ b.game_count }} {{ t('common.game') }}</span>
            <span class="font-bold text-brand-pink">{{ money(effectiveAmount(b)) }}</span>
            <!-- Nothing owed is settled as it stands: no paid/unpaid to flip. -->
            <span
              v-if="isFree(b)"
              class="inline-flex min-h-11 items-center rounded-full border border-white/15 px-3 text-xs font-semibold text-white/55"
            >
              {{ t('billing.free') }}
            </span>
            <button
              v-else-if="waitingSlip(b)"
              class="tap rounded-full bg-[#7b5cff]/25 px-3 text-xs font-semibold text-[#cbbfff]"
              @click="reviewing = b"
            >
              {{ t('billSlip.check') }}
            </button>
            <button
              v-else
              class="tap rounded-full px-3 text-xs font-semibold"
              :class="b.paid_status === 'paid' ? 'bg-status-success/20 text-status-success' : 'bg-white/10 text-white/60'"
              @click="togglePaid(b)"
            >
              {{ b.paid_status === 'paid' ? t('billing.paid') : t('billing.unpaid') }}
            </button>
          </div>

          <div class="mt-2 flex flex-wrap items-center gap-2 text-xs">
            <span class="text-white/40">{{ t('billing.calculatedAmount') }}: {{ money(b.amount_calc) }}</span>
            <input
              v-model="editingAdjust[b.id]"
              type="number"
              inputmode="decimal"
              min="0"
              :aria-label="`${t('billing.adjustAmount')} — ${nameOf(b.player_id)}`"
              :aria-invalid="!!adjustError[b.id]"
              :placeholder="b.amount_adjusted?.toString() ?? t('billing.adjustAmount')"
              class="min-h-11 w-28 rounded border border-brand-pink-dark/40 bg-brand-black px-2"
              @keydown.enter="saveAdjust(b)"
            />
            <button
              class="tap px-1 text-brand-pink underline disabled:no-underline disabled:opacity-40"
              :disabled="!hasTyped(b.id)"
              @click="saveAdjust(b)"
            >
              {{ t('billing.saveAdjustment') }}
            </button>
            <button
              v-if="b.amount_adjusted !== null && b.amount_adjusted !== undefined"
              class="tap px-1 text-white/50 underline"
              @click="saveAdjust(b, 'clear')"
            >
              {{ t('billing.useCalculated') }}
            </button>
            <button
              v-if="!isFree(b)"
              class="tap px-1 text-white/60 underline"
              :aria-label="`${t('billing.waiveLabel')} — ${nameOf(b.player_id)}`"
              @click="saveAdjust(b, 'waive')"
            >
              {{ t('billing.waive') }}
            </button>
            <button v-if="b.slip_url && !waitingSlip(b)" class="tap px-1 text-[#cbbfff] underline" @click="reviewing = b">
              {{ t('billSlip.view') }}
            </button>
            <!-- nothing to pay, nothing to scan -->
            <button v-if="effectiveAmount(b) > 0" class="tap px-1 text-brand-pink underline" @click="showQr(b)">
              {{ paymentInfoByBillingId[b.id] ? t('billing.hideQr') : t('billing.showQr') }}
            </button>
          </div>

          <p v-if="adjustError[b.id]" class="mt-1 text-xs text-status-error" role="alert">{{ adjustError[b.id] }}</p>

          <div v-if="paymentInfoByBillingId[b.id] && effectiveAmount(b) > 0" class="mt-3 flex flex-col items-center gap-2 text-center">
            <BrandQr
              v-if="paymentInfoByBillingId[b.id].qr_modules"
              :modules="paymentInfoByBillingId[b.id].qr_modules!"
              :amount="paymentInfoByBillingId[b.id].amount"
              :account-name="paymentInfoByBillingId[b.id].bank_account_name"
              :alt="`QR ${money(paymentInfoByBillingId[b.id].amount)} — ${nameOf(b.player_id)}`"
              saveable
              :file-name="`niddeaw-bill-${nameOf(b.player_id)}.png`"
              class="w-full max-w-[260px]"
            />
            <img
              v-else-if="paymentInfoByBillingId[b.id].data_uri"
              :src="paymentInfoByBillingId[b.id].data_uri!"
              alt="QR"
              class="h-40 w-40 rounded-lg bg-white p-2"
            />
            <p v-if="paymentInfoByBillingId[b.id].bank_name" class="text-sm text-white/70">
              {{ paymentInfoByBillingId[b.id].bank_name }} · {{ paymentInfoByBillingId[b.id].bank_account_number }}
              <span v-if="paymentInfoByBillingId[b.id].bank_account_name">
                ({{ paymentInfoByBillingId[b.id].bank_account_name }})
              </span>
            </p>
            <p v-if="paymentInfoByBillingId[b.id].method !== 'promptpay'" class="text-sm">
              <span class="text-white/40">{{ t('billing.amountToTransfer') }}:</span>
              <span class="ml-1 font-bold text-brand-pink">{{ money(paymentInfoByBillingId[b.id].amount) }}</span>
            </p>
          </div>
        </li>
      </ul>
    </template>
    <BillSlipReview v-if="reviewing" :bill="reviewing" :name="nameOf(reviewing.player_id)" @close="reviewing = null" @updated="onReviewed" />
  </main>
</template>
