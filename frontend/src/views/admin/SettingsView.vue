<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as adminApi from '@/api/admin'
import { ApiError } from '@/api/client'
import { compressImage } from '@/utils/imageCompression'
import type { ClubSettings, PaymentMethod, PromptPayType } from '@/types'
import AdminNav from '@/components/layout/AdminNav.vue'

const { t } = useI18n()

const settings = ref<ClubSettings | null>(null)
const loading = ref(true)
const loadError = ref<string | null>(null)
const saving = ref(false)
const saved = ref(false)
const saveError = ref<string | null>(null)

const uploadingQr = ref(false)
const qrUploadError = ref<string | null>(null)

// Photos uploaded before the API started resizing them are still stored at
// up to 1600px, where 480 is the biggest the site ever draws. This is the
// one-off that fixes them, from a phone, without anyone handling a key.
const shrinkReport = ref<adminApi.AvatarShrinkReport | null>(null)
const shrinking = ref(false)
const shrinkError = ref<string | null>(null)

async function runShrink(apply: boolean): Promise<void> {
  shrinking.value = true
  shrinkError.value = null
  try {
    shrinkReport.value = await adminApi.shrinkAvatars(apply)
  } catch (e) {
    shrinkError.value = apiErrorMessage(e, t('settings.shrinkFailed'))
  } finally {
    shrinking.value = false
  }
}

function kb(bytes: number): string {
  return bytes < 1024 * 1024
    ? `${Math.round(bytes / 1024)} KB`
    : `${(bytes / 1048576).toFixed(1)} MB`
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
    <h1 class="text-2xl font-bold text-brand-pink">{{ t('settings.title') }}</h1>

    <p v-if="loading" class="mt-6 text-white/60">{{ t('common.loading') }}</p>
    <p v-else-if="loadError" class="mt-6 text-status-error">{{ loadError }}</p>

    <form v-else-if="settings" class="mt-6 flex flex-col gap-4" @submit.prevent="save">
      <label class="flex flex-col gap-1 text-sm">
        {{ t('settings.paymentMethod') }}
        <select
          v-model="settings.payment_method"
          class="rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2"
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
            class="rounded-lg border border-brand-pink/25 bg-brand-surface px-3 py-2 outline-none focus:border-brand-pink"
          />
        </label>

        <label class="flex flex-col gap-1 text-sm">
          {{ t('settings.promptpayType') }}
          <select
            v-model="settings.promptpay_type"
            class="rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2"
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
            class="rounded-lg border border-brand-pink/25 bg-brand-surface px-3 py-2 outline-none focus:border-brand-pink"
          />
        </label>
        <label class="flex flex-col gap-1 text-sm">
          {{ t('settings.bankAccountNumber') }}
          <input
            v-model="settings.bank_account_number"
            class="rounded-lg border border-brand-pink/25 bg-brand-surface px-3 py-2 outline-none focus:border-brand-pink"
          />
        </label>
        <label class="flex flex-col gap-1 text-sm">
          {{ t('settings.bankAccountName') }}
          <input
            v-model="settings.bank_account_name"
            class="rounded-lg border border-brand-pink/25 bg-brand-surface px-3 py-2 outline-none focus:border-brand-pink"
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
          class="rounded-lg border border-brand-pink/25 bg-brand-surface px-3 py-2 outline-none focus:border-brand-pink"
        />
      </label>

      <label class="flex flex-col gap-1 text-sm">
        {{ t('settings.defaultShuttlecockPrice') }}
        <input
          v-model.number="settings.default_shuttlecock_price_per_game"
          type="number"
          min="0"
          class="rounded-lg border border-brand-pink/25 bg-brand-surface px-3 py-2 outline-none focus:border-brand-pink"
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

    <section v-if="!loading && !loadError" class="mt-10">
      <h2 class="text-sm font-semibold text-white/70">{{ t('settings.shrinkTitle') }}</h2>
      <p class="mt-1 text-xs text-white/50">{{ t('settings.shrinkHint') }}</p>

      <button
        type="button"
        :disabled="shrinking"
        class="tap hud-hover mt-3 w-full rounded-full border border-brand-pink/40 px-4 text-sm font-semibold text-brand-pink disabled:opacity-50"
        @click="runShrink(false)"
      >
        {{ shrinking ? t('common.loading') : t('settings.shrinkCheck') }}
      </button>

      <p v-if="shrinkError" class="mt-3 text-sm text-status-error">{{ shrinkError }}</p>

      <div v-if="shrinkReport" class="hud-panel mt-3 border border-brand-pink/20 bg-brand-surface p-4">
        <p v-if="shrinkReport.rows.length === 0" class="text-sm text-white/50">
          {{ t('settings.shrinkNoPhotos') }}
        </p>
        <template v-else>
          <ul class="space-y-1.5 text-sm">
            <li
              v-for="row in shrinkReport.rows"
              :key="row.player_id"
              class="flex items-center gap-2"
            >
              <span class="min-w-0 flex-1 truncate">{{ row.nickname }}</span>
              <span v-if="row.status === 'failed'" class="shrink-0 text-xs text-status-error">
                {{ row.detail }}
              </span>
              <span v-else-if="row.status === 'already'" class="shrink-0 text-xs text-white/40">
                {{ t('settings.shrinkAlready') }}
              </span>
              <span v-else class="shrink-0 font-mono text-xs">
                <span class="text-white/40">{{ kb(row.before_bytes) }}</span>
                <span class="text-white/30"> → </span>
                <span class="text-status-success">{{ kb(row.after_bytes) }}</span>
              </span>
            </li>
          </ul>

          <p class="mt-3 border-t border-white/10 pt-3 text-sm">
            {{ t('settings.shrinkTotal') }}
            <span class="font-mono text-white/50">{{ kb(shrinkReport.before_total) }}</span>
            <span class="text-white/30"> → </span>
            <span class="font-mono font-semibold text-status-success">
              {{ kb(shrinkReport.after_total) }}
            </span>
          </p>

          <p v-if="shrinkReport.applied" class="mt-3 text-sm text-status-success">
            {{ t('settings.shrinkDone', { n: shrinkReport.shrunk }) }}
          </p>
          <button
            v-else-if="shrinkReport.shrunk > 0"
            type="button"
            :disabled="shrinking"
            class="tap mt-3 w-full rounded-full bg-brand-pink px-4 text-sm font-semibold text-brand-black disabled:opacity-50"
            @click="runShrink(true)"
          >
            {{ shrinking ? t('common.saving') : t('settings.shrinkApply', { n: shrinkReport.shrunk }) }}
          </button>
          <p v-else class="mt-3 text-sm text-white/50">{{ t('settings.shrinkNothingToDo') }}</p>
        </template>
      </div>
    </section>
  </main>
</template>
