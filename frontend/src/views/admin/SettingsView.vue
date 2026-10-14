<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as adminApi from '@/api/admin'
import { ApiError } from '@/api/client'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { compressImage } from '@/utils/imageCompression'
import type { ClubSettings, PaymentMethod, PromptPayType } from '@/types'
import AdminNav from '@/components/layout/AdminNav.vue'

const { t } = useI18n()
const { confirm } = useConfirmDialog()

const settings = ref<ClubSettings | null>(null)
const loading = ref(true)
const loadError = ref<string | null>(null)
const saving = ref(false)
const saved = ref(false)
const saveError = ref<string | null>(null)

const uploadingQr = ref(false)
const qrUploadError = ref<string | null>(null)

// The admin login locks out a caller after five wrong passwords, and who
// counts as "a caller" depends on how many proxies sit in front of the
// app — something only the running deployment can answer. Open this on
// two devices on different networks: different keys mean the lockout is
// per-device as intended, the same key means one wrong-password spree
// locks the whole club out.
const identity = ref<adminApi.ClientIdentity | null>(null)
const identityLoading = ref(false)
const identityError = ref<string | null>(null)

async function loadIdentity(): Promise<void> {
  identityLoading.value = true
  identityError.value = null
  try {
    identity.value = await adminApi.getClientIdentity()
  } catch (e) {
    identityError.value = apiErrorMessage(e, t('settings.identityFailed'))
  } finally {
    identityLoading.value = false
  }
}

// The numbers on a profile are counters kept as results come in, not a
// count of the match rows; the matches are the truth. When the two
// disagree the person who notices is the admin looking at the screen, so
// the check and the repair live here rather than only in a CLI that needs
// a terminal and the service key.
const audit = ref<adminApi.StatsReport | null>(null)
const auditLoading = ref(false)
const auditError = ref<string | null>(null)
const repairing = ref(false)

async function checkStats(): Promise<void> {
  auditLoading.value = true
  auditError.value = null
  try {
    audit.value = await adminApi.checkStats()
  } catch (e) {
    auditError.value = apiErrorMessage(e, t('settings.statsFailed'))
  } finally {
    auditLoading.value = false
  }
}

async function repairStats(): Promise<void> {
  const confirmed = await confirm({
    title: t('settings.statsRepair'),
    message: t('settings.statsRepairConfirm', { n: audit.value?.rows.length ?? 0 }),
    confirmLabel: t('settings.statsRepair'),
  })
  if (!confirmed) return
  repairing.value = true
  auditError.value = null
  try {
    audit.value = await adminApi.repairStats()
  } catch (e) {
    auditError.value = apiErrorMessage(e, t('settings.statsFailed'))
  } finally {
    repairing.value = false
  }
}

// Only the figures that actually differ. A row that printed the game
// count alone read "1 → 1" whenever the disagreement was in the wins, which
// looks like the screen flagging someone for nothing.
function differences(row: adminApi.StatsRow): { label: string; from: number; to: number }[] {
  const fields: [string, number, number][] = [
    [t('common.game'), row.stored_games, row.real_games],
    [t('common.win'), row.stored_wins, row.real_wins],
    [t('common.draw'), row.stored_draws, row.real_draws],
    [t('common.loss'), row.stored_losses, row.real_losses],
  ]
  return fields
    .filter(([, from, to]) => from !== to)
    .map(([label, from, to]) => ({ label, from, to }))
}

async function onQrFileSelected(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file || !settings.value) return
  uploadingQr.value = true
  qrUploadError.value = null
  try {
    settings.value = await adminApi.uploadPaymentQr(await compressImage(file))
  } catch (e) {
    qrUploadError.value = apiErrorMessage(e, t('settings.qrUploadFailed'))
  } finally {
    uploadingQr.value = false
    input.value = ''
  }
}

function apiErrorMessage(e: unknown, fallback: string): string {
  if (e instanceof ApiError) {
    return `${fallback} (${e.status}: ${e.message})`
  }
  return fallback
}

onMounted(async () => {
  try {
    settings.value = await adminApi.getClubSettings()
  } catch (e) {
    loadError.value = apiErrorMessage(e, t('settings.loadFailed'))
  } finally {
    loading.value = false
  }
})

async function save(): Promise<void> {
  if (!settings.value) return
  saving.value = true
  saved.value = false
  saveError.value = null
  try {
    settings.value = await adminApi.updateClubSettings(settings.value)
    saved.value = true
  } catch (e) {
    saveError.value = apiErrorMessage(e, t('settings.saveFailed'))
  } finally {
    saving.value = false
  }
}

const promptPayTypeOptions = computed<{ value: PromptPayType; label: string }[]>(() => [
  { value: 'phone', label: t('settings.phoneNumber') },
  { value: 'national_id', label: t('settings.nationalId') },
  { value: 'ewallet', label: 'e-Wallet ID' },
])

const paymentMethodOptions = computed<{ value: PaymentMethod; label: string }[]>(() => [
  { value: 'promptpay', label: t('settings.paymentMethodPromptpay') },
  { value: 'bank_account', label: t('settings.paymentMethodBankAccount') },
  { value: 'bank_account_qr', label: t('settings.paymentMethodBankAccountQr') },
  { value: 'uploaded_qr', label: t('settings.paymentMethodUploadedQr') },
])
</script>

<template>
  <AdminNav />
  <main class="mx-auto max-w-md px-4 py-6">
    <h1 class="sr-only">{{ t('settings.title') }}</h1>

    <p v-if="loading" class="mt-6 text-white/60">{{ t('common.loading') }}</p>
    <p v-else-if="loadError" class="mt-6 text-status-error">{{ loadError }}</p>

    <form v-else-if="settings" class="mt-6 flex flex-col gap-4" @submit.prevent="save">
      <label class="flex flex-col gap-1 text-sm">
        {{ t('settings.paymentMethod') }}
        <select
          v-model="settings.payment_method"
          class="min-h-11 rounded-lg border border-brand-pink/25 bg-brand-black px-3"
        >
          <option v-for="opt in paymentMethodOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
      </label>

      <template v-if="settings.payment_method === 'promptpay'">
        <label class="flex flex-col gap-1 text-sm">
          PromptPay ID
          <input
            v-model="settings.promptpay_id"
            :placeholder="t('settings.promptpayPlaceholder')"
            class="min-h-11 rounded-lg border border-brand-pink/25 bg-brand-surface px-3 outline-none focus:border-brand-pink"
          />
        </label>

        <label class="flex flex-col gap-1 text-sm">
          {{ t('settings.promptpayType') }}
          <select
            v-model="settings.promptpay_type"
            class="min-h-11 rounded-lg border border-brand-pink/25 bg-brand-black px-3"
          >
            <option v-for="opt in promptPayTypeOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </label>
      </template>

      <template v-else-if="settings.payment_method === 'bank_account' || settings.payment_method === 'bank_account_qr'">
        <label class="flex flex-col gap-1 text-sm">
          {{ t('settings.bankName') }}
          <input
            v-model="settings.bank_name"
            class="min-h-11 rounded-lg border border-brand-pink/25 bg-brand-surface px-3 outline-none focus:border-brand-pink"
          />
        </label>
        <label class="flex flex-col gap-1 text-sm">
          {{ t('settings.bankAccountNumber') }}
          <input
            v-model="settings.bank_account_number"
            class="min-h-11 rounded-lg border border-brand-pink/25 bg-brand-surface px-3 outline-none focus:border-brand-pink"
          />
        </label>
        <label class="flex flex-col gap-1 text-sm">
          {{ t('settings.bankAccountName') }}
          <input
            v-model="settings.bank_account_name"
            class="min-h-11 rounded-lg border border-brand-pink/25 bg-brand-surface px-3 outline-none focus:border-brand-pink"
          />
        </label>
      </template>

      <template v-else-if="settings.payment_method === 'uploaded_qr'">
        <div class="flex flex-col gap-2 text-sm">
          <img
            v-if="settings.uploaded_qr_url"
            :src="settings.uploaded_qr_url"
            :alt="t('settings.currentQr')"
            class="h-40 w-40 self-center rounded-lg bg-white p-2"
          />
          <label class="flex items-center gap-2 rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-sm text-white/60">
            {{ settings.uploaded_qr_url ? t('settings.replaceQr') : t('settings.uploadQr') }}
            <input type="file" accept="image/*" class="flex-1 text-xs" :disabled="uploadingQr" @change="onQrFileSelected" />
          </label>
          <p v-if="qrUploadError" class="text-sm text-status-error">{{ qrUploadError }}</p>
        </div>
      </template>

      <label class="flex flex-col gap-1 text-sm">
        {{ t('settings.defaultCourtFee') }}
        <input
          v-model.number="settings.default_court_fee_per_person"
          type="number"
          min="0"
          class="min-h-11 rounded-lg border border-brand-pink/25 bg-brand-surface px-3 outline-none focus:border-brand-pink"
        />
      </label>

      <label class="flex flex-col gap-1 text-sm">
        {{ t('settings.defaultShuttlecockPrice') }}
        <input
          v-model.number="settings.default_shuttlecock_price_per_game"
          type="number"
          min="0"
          class="min-h-11 rounded-lg border border-brand-pink/25 bg-brand-surface px-3 outline-none focus:border-brand-pink"
        />
      </label>

      <p v-if="saved" class="text-sm text-status-success">{{ t('settings.saved') }}</p>
      <p v-if="saveError" class="text-sm text-status-error">{{ saveError }}</p>

      <button
        type="submit"
        :disabled="saving"
        class="rounded-lg bg-brand-pink px-3 py-2 font-semibold text-brand-black disabled:opacity-50"
      >
        {{ saving ? t('common.saving') : t('settings.saveSettings') }}
      </button>
    </form>

    <section class="mt-10">
      <h2 class="text-sm font-semibold text-white/70">{{ t('settings.statsTitle') }}</h2>
      <p class="mt-1 text-xs text-white/50">{{ t('settings.statsHint') }}</p>

      <button
        type="button"
        :disabled="auditLoading"
        class="tap hud-hover mt-3 w-full rounded-full border border-brand-pink/40 px-4 text-sm font-semibold text-brand-pink disabled:opacity-50"
        @click="checkStats"
      >
        {{ auditLoading ? t('common.loading') : t('settings.statsCheck') }}
      </button>

      <p v-if="auditError" class="mt-3 text-sm text-status-error">{{ auditError }}</p>

      <div v-if="audit" class="hud-panel mt-3 border border-brand-pink/20 bg-brand-surface p-4">
        <p class="text-sm text-white/60">
          {{ t('settings.statsChecked', { players: audit.players_checked, matches: audit.matches_counted }) }}
        </p>

        <!-- After a repair the rows are what was just written, not what is
             still wrong — so they stay on screen, and the button that would
             write them again does not. -->
        <p v-if="audit.applied" class="mt-2 text-sm text-status-success">
          {{ t('settings.statsRepaired', { n: audit.rows.length }) }}
        </p>
        <p v-else-if="audit.rows.length === 0" class="mt-2 text-sm text-status-success">
          {{ t('settings.statsAllGood') }}
        </p>

        <template v-if="audit.rows.length > 0">
          <ul class="mt-3 space-y-1.5">
            <li
              v-for="row in audit.rows"
              :key="row.player_id"
              class="flex items-center justify-between gap-2 text-sm"
            >
              <span class="truncate">
                {{ row.nickname }}
                <span v-if="!row.is_active" class="text-xs text-white/40">
                  ({{ t('members.deletedBadge') }})
                </span>
              </span>
              <span class="flex shrink-0 flex-wrap justify-end gap-x-2 font-mono text-xs">
                <span v-for="d in differences(row)" :key="d.label" class="whitespace-nowrap">
                  <span class="text-white/40">{{ d.label }}</span>
                  <span class="ml-1 text-status-error">{{ d.from }}</span>
                  <span class="text-white/30">→</span>
                  <span class="text-status-success">{{ d.to }}</span>
                </span>
              </span>
            </li>
          </ul>

          <button
            v-if="!audit.applied"
            type="button"
            :disabled="repairing"
            class="tap mt-4 w-full rounded-full bg-brand-pink px-4 text-sm font-semibold text-brand-black disabled:opacity-50"
            @click="repairStats"
          >
            {{ repairing ? t('common.saving') : t('settings.statsRepair') }}
          </button>
          <p class="mt-2 text-xs text-white/40">{{ t('settings.statsEloNote') }}</p>
        </template>

        <p v-if="audit.orphan_player_ids.length > 0" class="mt-3 text-xs text-status-error">
          {{ t('settings.statsOrphans', { n: audit.orphan_player_ids.length }) }}
        </p>
      </div>
    </section>

    <section class="mt-10">
      <h2 class="text-sm font-semibold text-white/70">{{ t('settings.identityTitle') }}</h2>
      <p class="mt-1 text-xs text-white/50">{{ t('settings.identityHint') }}</p>

      <button
        type="button"
        :disabled="identityLoading"
        class="tap hud-hover mt-3 w-full rounded-full border border-brand-pink/40 px-4 text-sm font-semibold text-brand-pink disabled:opacity-50"
        @click="loadIdentity"
      >
        {{ identityLoading ? t('common.loading') : t('settings.identityCheck') }}
      </button>

      <p v-if="identityError" class="mt-3 text-sm text-status-error">{{ identityError }}</p>

      <div
        v-if="identity"
        class="hud-panel mt-3 border border-brand-pink/20 bg-brand-surface p-4 text-sm"
      >
        <p class="text-white/50">{{ t('settings.identityKey') }}</p>
        <p class="mt-1 font-mono text-base break-all text-brand-pink">{{ identity.throttle_key }}</p>

        <p class="mt-3 text-white/50">
          {{ t('settings.identityFailures', { n: identity.recent_failures }) }}
          <span v-if="identity.retry_after_seconds > 0" class="text-status-error">
            — {{ t('settings.identityLocked', { n: Math.ceil(identity.retry_after_seconds / 60) }) }}
          </span>
        </p>

        <p v-if="identity.hops.length > 1" class="mt-3 text-xs text-white/40">
          {{ t('settings.identityHops') }} {{ identity.hops.join(' → ') }}
        </p>
      </div>
    </section>
  </main>
</template>
