<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSessionsStore } from '@/stores/sessions'
import { usePlayersStore } from '@/stores/players'
import * as adminApi from '@/api/admin'
import { ApiError } from '@/api/client'
import { effectiveAmount } from '@/types'
import type { Billing, Checkin } from '@/types'
import AdminNav from '@/components/layout/AdminNav.vue'
import SessionPicker from '@/components/layout/SessionPicker.vue'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'

const { t } = useI18n()
const sessionsStore = useSessionsStore()
const playersStore = usePlayersStore()

const billings = ref<Billing[]>([])
const checkins = ref<Checkin[]>([])
const closing = ref(false)
const billingPlayerId = ref<string | null>(null)
const qrByBillingId = ref<Record<string, string>>({})
const editingAdjust = ref<Record<string, string>>({})
const actionError = ref<string | null>(null)

function nameOf(playerId: string): string {
  const p = playersStore.byId(playerId)
  return p ? p.nickname : '?'
}

function avatarOf(playerId: string): string | undefined {
  return playersStore.byId(playerId)?.avatar_url ?? undefined
}

function apiErrorMessage(e: unknown, fallback: string): string {
  if (e instanceof ApiError) {
    return `${fallback} (${e.status}: ${e.message})`
  }
  return fallback
}

const unbilledAttendeeIds = computed(() => {
  const billedIds = new Set(billings.value.map((b) => b.player_id))
  const attendeeIds = new Set(checkins.value.map((c) => c.player_id))
  return [...attendeeIds].filter((id) => !billedIds.has(id))
})

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

async function saveAdjust(billing: Billing): Promise<void> {
  actionError.value = null
  try {
    const raw = editingAdjust.value[billing.id]
    const amount = raw === '' || raw === undefined ? null : Number(raw)
    const updated = await adminApi.adjustBilling(billing.id, amount)
    billings.value = billings.value.map((b) => (b.id === updated.id ? updated : b))
    delete editingAdjust.value[billing.id]
  } catch (e) {
    actionError.value = apiErrorMessage(e, t('billing.adjustFailed'))
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
  if (qrByBillingId.value[billing.id]) {
    delete qrByBillingId.value[billing.id]
    return
  }
  actionError.value = null
  try {
    const { data_uri } = await adminApi.getBillingQrCode(billing.id)
    qrByBillingId.value[billing.id] = data_uri
  } catch (e) {
    actionError.value = apiErrorMessage(e, t('billing.qrFailed'))
  }
}

watch(() => sessionsStore.currentSessionId, refreshBillings)

onMounted(async () => {
  await Promise.all([sessionsStore.refresh(), playersStore.ensureLoaded()])
  await refreshBillings()
})
</script>

<template>
  <AdminNav />
  <main class="mx-auto max-w-3xl px-4 py-6">
    <h1 class="text-2xl font-bold text-brand-pink">{{ t('admin.nav.billing') }}</h1>
    <div class="mt-4">
      <SessionPicker />
    </div>

    <p v-if="actionError" class="mt-4 text-sm text-status-error">{{ actionError }}</p>

    <p v-if="!sessionsStore.currentSessionId" class="mt-8 text-white/60">{{ t('billing.selectSessionFirst') }}</p>

    <template v-else>
      <div class="mt-6 flex items-center justify-between">
        <p class="text-sm text-white/60">
          Status: <span class="font-semibold text-white">{{ sessionsStore.currentSession?.status }}</span>
        </p>
        <button
          v-if="sessionsStore.currentSession?.status === 'open'"
          :disabled="closing"
          class="rounded-full bg-brand-pink px-4 py-1.5 text-sm font-semibold text-brand-black disabled:opacity-50"
          @click="closeAndBill"
        >
          {{ closing ? t('billing.closing') : t('billing.closeAndBill') }}
        </button>
      </div>

      <section v-if="unbilledAttendeeIds.length > 0" class="mt-6">
        <h2 class="text-sm font-semibold text-white/70">{{ t('billing.unbilled') }} ({{ unbilledAttendeeIds.length }})</h2>
        <p class="mt-1 text-xs text-white/40">
          {{ t('billing.unbilledHint') }}
        </p>
        <ul class="mt-2 space-y-2">
          <li
            v-for="pid in unbilledAttendeeIds"
            :key="pid"
            class="flex items-center gap-3 hud-panel border border-brand-pink/15 bg-brand-surface px-3 py-2"
          >
            <PlayerAvatar :name="nameOf(pid)" :avatar-url="avatarOf(pid)" size="sm" />
            <span class="flex-1 font-medium">{{ nameOf(pid) }}</span>
            <button
              :disabled="billingPlayerId === pid"
              class="rounded-full border border-brand-pink px-3 py-1 text-xs text-brand-pink hover:bg-brand-pink hover:text-brand-black disabled:opacity-50"
              @click="billOnePlayer(pid)"
            >
              {{ billingPlayerId === pid ? '...' : t('billing.billThisPlayer') }}
            </button>
          </li>
        </ul>
      </section>

      <p v-if="billings.length === 0" class="mt-6 text-sm text-white/40">
        {{ t('billing.noBills') }}
      </p>

      <ul v-else class="mt-6 space-y-3">
        <li
          v-for="b in billings"
          :key="b.id"
          class="hud-panel border border-brand-pink/20 bg-brand-surface p-4"
        >
          <div class="flex items-center gap-3">
            <PlayerAvatar :name="nameOf(b.player_id)" :avatar-url="avatarOf(b.player_id)" size="sm" />
            <span class="flex-1 font-medium">{{ nameOf(b.player_id) }}</span>
            <span class="text-xs text-white/40">{{ b.game_count }} {{ t('common.game') }}</span>
            <span class="font-bold text-brand-pink">฿{{ effectiveAmount(b).toFixed(2) }}</span>
            <button
              class="rounded-full px-3 py-1 text-xs font-semibold"
              :class="b.paid_status === 'paid' ? 'bg-status-success/20 text-status-success' : 'bg-white/10 text-white/60'"
              @click="togglePaid(b)"
            >
              {{ b.paid_status === 'paid' ? t('billing.paid') : t('billing.unpaid') }}
            </button>
          </div>

          <div class="mt-2 flex flex-wrap items-center gap-2 text-xs">
            <span class="text-white/40">{{ t('billing.calculatedAmount') }}: ฿{{ b.amount_calc.toFixed(2) }}</span>
            <input
              v-model="editingAdjust[b.id]"
              type="number"
              :placeholder="b.amount_adjusted?.toString() ?? t('billing.adjustAmount')"
              class="w-24 rounded border border-brand-pink-dark/40 bg-brand-black px-2 py-0.5"
            />
            <button class="text-brand-pink underline" @click="saveAdjust(b)">{{ t('billing.saveAdjustment') }}</button>
            <button class="text-brand-pink underline" @click="showQr(b)">
              {{ qrByBillingId[b.id] ? t('billing.hideQr') : t('billing.showQr') }}
            </button>
          </div>

          <img
            v-if="qrByBillingId[b.id]"
            :src="qrByBillingId[b.id]"
            alt="PromptPay QR"
            class="mx-auto mt-3 h-40 w-40 rounded-lg bg-white p-2"
          />
        </li>
      </ul>
    </template>
  </main>
</template>
