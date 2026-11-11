<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as adminApi from '@/api/admin'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { compressImage } from '@/utils/imageCompression'
import type { ClubSettings, PaymentMethod, PromptPayType } from '@/types'
import AdminNav from '@/components/layout/AdminNav.vue'
import QuestSettingsPanel from '@/components/admin/QuestSettingsPanel.vue'
import { bahtProblem, MAX_HANDLE, promptpayIdProblem } from '@/utils/limits'
import { apiErrorMessage } from '@/api/errors'
import { formatDateTime } from '@/utils/format'
import { forgetSlipChecks } from '@/composables/useSlipChecks'

const { t, locale } = useI18n()
const { confirm } = useConfirmDialog()

// Baked in at build time by vite.config.ts.
const buildSha = __BUILD_SHA__
const buildTime = __BUILD_TIME__

const settings = ref<ClubSettings | null>(null)
const loading = ref(true)
const loadError = ref<string | null>(null)
const saving = ref(false)
const saved = ref(false)
const saveError = ref<string | null>(null)

const uploadingQr = ref(false)
const qrUploadError = ref<string | null>(null)

// Supabase's free plan keeps no backups of its own, so the club keeps its
// own: one ZIP of every table, downloaded by hand. The "last backup" line
// is read from the activity log the download is recorded in, so it is the
// same for every admin on every phone.
const BACKUP_DUE_DAYS = 30
const lastBackup = ref<adminApi.LastBackup | null>(null)
const backingUp = ref(false)
const backupError = ref<string | null>(null)
const backupFile = ref<string | null>(null)

const backupOverdue = computed(() => {
  const at = lastBackup.value?.at
  if (!at) return true
  return Date.now() - new Date(at).getTime() > BACKUP_DUE_DAYS * 24 * 60 * 60 * 1000
})

async function loadLastBackup(): Promise<void> {
  try {
    lastBackup.value = await adminApi.getLastBackup()
  } catch {
    // Only the reminder line is lost; the button still works.
  }
}

/** A file name with the club's date and time, as the backend names it. */
function backupName(now: Date): string {
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat('en-GB', {
      timeZone: 'Asia/Bangkok', year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
    }).formatToParts(now).map((p) => [p.type, p.value]),
  )
  return `niddeaw-backup-${parts.year}-${parts.month}-${parts.day}-${parts.hour}${parts.minute}.zip`
}

async function downloadBackup(): Promise<void> {
  backingUp.value = true
  backupError.value = null
  backupFile.value = null
  try {
    const blob = await adminApi.downloadBackup()
    const name = backupName(new Date())
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = name
    document.body.appendChild(link)
    link.click()
    link.remove()
    // Long enough for the browser (and iOS's download sheet) to take it.
    setTimeout(() => URL.revokeObjectURL(url), 60_000)
    backupFile.value = name
    await loadLastBackup()
  } catch (e) {
    backupError.value = apiErrorMessage(e, t('settings.backupFailed'))
  } finally {
    backingUp.value = false
  }
}

// Slips sent before slip checks existed: read their QR a batch at a time so
// a reused old slip is caught too. Running it again only reads what is new.
const slipRun = ref<{ done: number; left: number; running: boolean; failed: boolean } | null>(null)
async function backfillSlips(): Promise<void> {
  slipRun.value = { done: 0, left: 0, running: true, failed: false }
  try {
    for (let round = 0; round < 500; round++) {
      const r = await adminApi.backfillSlipChecks()
      slipRun.value.done += r.done
      slipRun.value.left = r.remaining
      if (r.remaining <= 0 || r.done === 0) break
    }
    forgetSlipChecks()
  } catch {
    slipRun.value.failed = true
  } finally {
    slipRun.value.running = false
  }
}
const slipPct = computed(() => {
  const r = slipRun.value
  if (!r) return 0
  const all = r.done + r.left
  return all ? Math.round((r.done / all) * 100) : r.running ? 0 : 100
})

// The same data copied into the club's Google Sheet, every Saturday morning
// by a GitHub Action and whenever an admin presses the button. The setup is
// done outside the app (Google Cloud, Render, GitHub); this shows which
// steps are done, whom to share the sheet with, and what went wrong.
const SETUP_GUIDE = 'https://github.com/Yosthapat/niddeaw_bmt/blob/main/docs/google-sheets-setup.md'
const sheets = ref<adminApi.SheetsStatus | null>(null)
const sheetsLoadFailed = ref(false)
const syncing = ref(false)
const syncError = ref<string | null>(null)
const syncDone = ref<adminApi.SheetsSyncDone | null>(null)
const emailCopied = ref(false)

const sheetsReady = computed(() => !!sheets.value?.has_key && !!sheets.value?.has_sheet && !sheets.value.problem)

async function loadSheets(): Promise<void> {
  try {
    sheets.value = await adminApi.getSheetsStatus()
    sheetsLoadFailed.value = false
  } catch {
    sheetsLoadFailed.value = true
  }
}

async function syncNow(): Promise<void> {
  syncing.value = true
  syncError.value = null
  syncDone.value = null
  try {
    syncDone.value = await adminApi.syncSheets()
    await loadSheets()
  } catch (e) {
    syncError.value = apiErrorMessage(e, t('settings.sheetsSyncFailed'))
  } finally {
    syncing.value = false
  }
}

async function copyEmail(): Promise<void> {
  const email = sheets.value?.account_email
  if (!email) return
  try {
    await navigator.clipboard.writeText(email)
    emailCopied.value = true
    setTimeout(() => (emailCopied.value = false), 2000)
  } catch {
    // No clipboard (an old browser, or no permission): the address is on
    // screen to select by hand.
  }
}

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


onMounted(async () => {
  void loadLastBackup()
  void loadSheets()
  try {
    settings.value = await adminApi.getClubSettings()
  } catch (e) {
    loadError.value = apiErrorMessage(e, t('settings.loadFailed'))
  } finally {
    loading.value = false
  }
})

const promptpayProblem = computed(() => {
  const st = settings.value
  if (!st || st.payment_method !== 'promptpay') return null
  if (!promptpayIdProblem(st.promptpay_id ?? '', st.promptpay_type)) return null
  return t(
    { phone: 'validation.promptpayPhone', national_id: 'validation.promptpayNationalId', ewallet: 'validation.promptpayEwallet' }[
      st.promptpay_type
    ],
  )
})
const courtFeeProblem = computed(() => {
  const p = settings.value && bahtProblem(settings.value.default_court_fee_per_person, { allowZero: true })
  return p ? t(`validation.${p}`) : null
})
const shuttlecockProblem = computed(() => {
  const p = settings.value && bahtProblem(settings.value.default_shuttlecock_price_per_game, { allowZero: true })
  return p ? t(`validation.${p}`) : null
})
// Red only after the first Save, not while the id is half typed.
const tried = ref(false)

async function save(): Promise<void> {
  if (!settings.value) return
  tried.value = true
  saved.value = false
  if (promptpayProblem.value || courtFeeProblem.value || shuttlecockProblem.value) return
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
            inputmode="numeric"
            autocomplete="off"
            :maxlength="MAX_HANDLE"
            :aria-invalid="tried && !!promptpayProblem"
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
        <p v-if="tried && promptpayProblem" class="-mt-2 text-xs text-status-error" role="alert">{{ promptpayProblem }}</p>
        <!-- Printed under the QR card, so the payer can see whose account
             it is before they transfer. -->
        <label class="flex flex-col gap-1 text-sm">
          {{ t('settings.qrAccountName') }}
          <input
            v-model="settings.bank_account_name"
            :maxlength="MAX_HANDLE"
            :placeholder="t('settings.qrAccountNamePlaceholder')"
            class="min-h-11 rounded-lg border border-brand-pink/25 bg-brand-surface px-3 outline-none focus:border-brand-pink"
          />
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
          inputmode="decimal"
          min="0"
          :aria-invalid="tried && !!courtFeeProblem"
          class="min-h-11 rounded-lg border border-brand-pink/25 bg-brand-surface px-3 outline-none focus:border-brand-pink"
        />
        <span v-if="tried && courtFeeProblem" class="text-xs text-status-error">{{ courtFeeProblem }}</span>
      </label>

      <label class="flex flex-col gap-1 text-sm">
        {{ t('settings.defaultShuttlecockPrice') }}
        <input
          v-model.number="settings.default_shuttlecock_price_per_game"
          type="number"
          inputmode="decimal"
          min="0"
          :aria-invalid="tried && !!shuttlecockProblem"
          class="min-h-11 rounded-lg border border-brand-pink/25 bg-brand-surface px-3 outline-none focus:border-brand-pink"
        />
        <span v-if="tried && shuttlecockProblem" class="text-xs text-status-error">{{ shuttlecockProblem }}</span>
      </label>

      <p v-if="saved" class="text-sm text-status-success">{{ t('settings.saved') }}</p>
      <p v-if="saveError" class="text-sm text-status-error">{{ saveError }}</p>

      <button
        type="submit"
        :disabled="saving"
        class="tap rounded-lg bg-brand-pink px-3 font-semibold text-brand-black disabled:opacity-50"
      >
        {{ saving ? t('common.saving') : t('settings.saveSettings') }}
      </button>
    </form>

    <QuestSettingsPanel />

    <section class="mt-10" aria-labelledby="backup-title">
      <h2 id="backup-title" class="text-sm font-semibold text-white/70">{{ t('settings.backupTitle') }}</h2>
      <p class="mt-1 text-xs text-white/50">{{ t('settings.backupHint') }}</p>

      <p class="mt-3 text-sm" :class="backupOverdue ? 'text-[#ffe14d]' : 'text-white/70'">
        <template v-if="lastBackup?.at">
          {{ t('settings.backupLast', { when: formatDateTime(lastBackup.at, locale), who: lastBackup.by ?? '?' }) }}
          <span v-if="lastBackup.rows !== null" class="text-white/40">
            · {{ t('settings.backupLastRows', { n: lastBackup.rows.toLocaleString() }) }}
          </span>
          <span v-if="backupOverdue" class="block text-xs">{{ t('settings.backupOverdue') }}</span>
        </template>
        <template v-else-if="lastBackup">{{ t('settings.backupNever') }}</template>
      </p>

      <button
        type="button"
        :disabled="backingUp"
        class="tap mt-3 inline-flex w-full items-center justify-center gap-2 rounded-full bg-brand-pink px-4 text-sm font-semibold text-brand-black disabled:opacity-50"
        @click="downloadBackup"
      >
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 4v11M7 10l5 5 5-5M5 20h14" /></svg>
        {{ backingUp ? t('settings.backupWorking') : t('settings.backupDownload') }}
      </button>

      <p v-if="backupFile" role="status" class="mt-3 text-sm text-status-success">
        ✓ {{ t('settings.backupDone') }}
        <span class="block font-mono text-xs break-all text-white/60">{{ backupFile }}</span>
        <span class="block text-xs text-white/45">{{ t('settings.backupWhere') }}</span>
      </p>
      <p v-if="backupError" role="alert" class="mt-3 text-sm text-status-error">{{ backupError }}</p>

      <p class="mt-3 text-xs text-white/45">{{ t('settings.backupInside') }}</p>
      <p class="mt-1 text-xs text-white/45">{{ t('settings.backupPrivate') }}</p>
    </section>

    <section class="mt-10" aria-labelledby="slips-title">
      <h2 id="slips-title" class="text-sm font-semibold text-white/70">{{ t('slipCheck.backfillTitle') }}</h2>
      <p class="mt-1 text-xs text-white/50">{{ t('slipCheck.backfillBody') }}</p>
      <button
        type="button"
        :disabled="slipRun?.running"
        class="tap mt-3 inline-flex w-full items-center justify-center gap-2 rounded-full border border-white/20 px-4 text-sm font-semibold text-white disabled:opacity-50"
        @click="backfillSlips"
      >
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 7V4h3M20 7V4h-3M4 17v3h3M20 17v3h-3M7 12h10" /></svg>
        {{ t('slipCheck.backfillGo') }}
      </button>
      <div v-if="slipRun" class="mt-3" role="status">
        <div class="h-2 overflow-hidden rounded-full bg-white/10">
          <div class="h-full rounded-full bg-brand-pink transition-[width] duration-500" :style="{ width: `${slipPct}%` }" />
        </div>
        <p class="mt-2 text-sm" :class="slipRun.failed ? 'text-status-error' : slipRun.running ? 'text-white/70' : 'text-status-success'">
          <template v-if="slipRun.failed">{{ t('slipCheck.backfillFailed') }}</template>
          <template v-else-if="slipRun.running">{{ t('slipCheck.backfillRunning', { done: slipRun.done, left: slipRun.left || '…' }) }}</template>
          <template v-else-if="slipRun.done">✓ {{ t('slipCheck.backfillDone', { done: slipRun.done }) }}</template>
          <template v-else>✓ {{ t('slipCheck.backfillNothing') }}</template>
        </p>
      </div>
    </section>

    <section class="mt-10" aria-labelledby="sheets-title">
      <h2 id="sheets-title" class="text-sm font-semibold text-white/70">{{ t('settings.sheetsTitle') }}</h2>
      <p class="mt-1 text-xs text-white/50">{{ t('settings.sheetsHint') }}</p>

      <p v-if="sheetsLoadFailed" class="mt-3 text-sm text-status-error">{{ t('settings.sheetsLoadFailed') }}</p>

      <template v-if="sheets">
        <!-- What is set up so far. Each step is done outside the app, so
             the list is how an admin knows which one is left. -->
        <ul class="mt-3 space-y-2 text-sm">
          <li class="flex items-start gap-2">
            <span aria-hidden="true" :class="sheets.has_key ? 'text-status-success' : 'text-white/35'">{{ sheets.has_key ? '✓' : '○' }}</span>
            <span :class="sheets.has_key ? 'text-white/80' : 'text-white/55'">{{ t('settings.sheetsStepKey') }}</span>
          </li>
          <li class="flex items-start gap-2">
            <span aria-hidden="true" :class="sheets.has_sheet ? 'text-status-success' : 'text-white/35'">{{ sheets.has_sheet ? '✓' : '○' }}</span>
            <span :class="sheets.has_sheet ? 'text-white/80' : 'text-white/55'">{{ t('settings.sheetsStepSheet') }}</span>
          </li>
          <li class="flex items-start gap-2">
            <span aria-hidden="true" :class="sheets.last ? 'text-status-success' : 'text-white/35'">{{ sheets.last ? '✓' : '○' }}</span>
            <span class="min-w-0" :class="sheets.last ? 'text-white/80' : 'text-white/55'">
              {{ t('settings.sheetsStepShare') }}
              <span v-if="sheets.account_email" class="mt-1 flex flex-wrap items-center gap-2">
                <code class="rounded bg-white/8 px-2 py-1 font-mono text-xs break-all text-brand-pink">{{ sheets.account_email }}</code>
                <button type="button" class="tap rounded-full border border-white/20 px-3 text-xs text-white/70" @click="copyEmail">
                  {{ emailCopied ? t('settings.sheetsCopied') : t('settings.sheetsCopy') }}
                </button>
              </span>
            </span>
          </li>
          <li class="flex items-start gap-2">
            <span aria-hidden="true" :class="sheets.weekly ? 'text-status-success' : 'text-white/35'">{{ sheets.weekly ? '✓' : '○' }}</span>
            <span :class="sheets.weekly ? 'text-white/80' : 'text-white/55'">{{ t('settings.sheetsStepWeekly') }}</span>
          </li>
        </ul>

        <p v-if="sheets.problem" role="alert" class="mt-3 text-sm text-status-error">{{ sheets.problem }}</p>

        <a
          v-if="!sheetsReady || !sheets.last"
          :href="SETUP_GUIDE"
          target="_blank"
          rel="noopener noreferrer"
          class="mt-3 inline-flex min-h-11 items-center text-sm text-brand-pink underline underline-offset-4"
        >{{ t('settings.sheetsGuide') }} ↗</a>

        <template v-if="sheetsReady">
          <p v-if="sheets.last" class="mt-3 text-sm text-white/70">
            {{ t('settings.sheetsLast', { when: sheets.last.at, who: sheets.last.by }) }}
            <span v-if="sheets.last.rows !== null" class="text-white/40">· {{ t('settings.backupLastRows', { n: sheets.last.rows.toLocaleString() }) }}</span>
          </p>
          <div class="mt-3 flex flex-col gap-2 min-[420px]:flex-row">
            <button
              type="button"
              :disabled="syncing"
              class="tap flex-1 rounded-full border border-brand-pink/40 px-4 text-sm font-semibold text-brand-pink disabled:opacity-50"
              @click="syncNow"
            >
              {{ syncing ? t('settings.sheetsSyncing') : t('settings.sheetsSync') }}
            </button>
            <a
              v-if="sheets.sheet_url"
              :href="sheets.sheet_url"
              target="_blank"
              rel="noopener noreferrer"
              class="tap inline-flex flex-1 items-center justify-center rounded-full border border-white/20 px-4 text-sm text-white/80"
            >{{ t('settings.sheetsOpen') }} ↗</a>
          </div>
          <p v-if="syncDone" role="status" class="mt-3 text-sm text-status-success">
            ✓ {{ t('settings.sheetsSynced', { n: syncDone.rows.toLocaleString(), tab: syncDone.snapshot }) }}
          </p>
          <p v-if="syncError" role="alert" class="mt-3 text-sm text-status-error">{{ syncError }}</p>
        </template>
      </template>
    </section>

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

    <!-- Which build this phone is actually running. A home-screen app is
         served by a service worker, so "the site is updated" and "this
         phone has the update" are different facts that look identical from
         the outside; this is how they get compared. -->
    <p class="mt-10 text-center text-xs text-white/30">
      {{ t('settings.buildStamp', { time: buildTime, sha: buildSha }) }}
    </p>
  </main>
</template>
