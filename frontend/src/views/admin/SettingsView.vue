<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as adminApi from '@/api/admin'
import { ApiError } from '@/api/client'
import type { ClubSettings, PromptPayType } from '@/types'
import AdminNav from '@/components/layout/AdminNav.vue'

const { t } = useI18n()

const settings = ref<ClubSettings | null>(null)
const loading = ref(true)
const loadError = ref<string | null>(null)
const saving = ref(false)
const saved = ref(false)
const saveError = ref<string | null>(null)

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
</script>

<template>
  <AdminNav />
  <main class="mx-auto max-w-md px-4 py-6">
    <h1 class="text-2xl font-bold text-brand-pink">{{ t('settings.title') }}</h1>

    <p v-if="loading" class="mt-6 text-white/60">{{ t('common.loading') }}</p>
    <p v-else-if="loadError" class="mt-6 text-status-error">{{ loadError }}</p>

    <form v-else-if="settings" class="mt-6 flex flex-col gap-4" @submit.prevent="save">
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
  </main>
</template>
