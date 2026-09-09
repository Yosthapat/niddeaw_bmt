<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as adminApi from '@/api/admin'
import { ApiError } from '@/api/client'
import type { DailyRevenue, IncomeSource, OtherIncome } from '@/types'
import { compressImage } from '@/utils/imageCompression'
import AdminNav from '@/components/layout/AdminNav.vue'

const { t, locale } = useI18n()

const SOURCES: IncomeSource[] = ['sponsor', 'investment', 'other']

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

const daily = ref<DailyRevenue[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

function apiErrorMessage(e: unknown, fallback: string): string {
  if (e instanceof ApiError) {
    return `${fallback} (${e.status}: ${e.message})`
  }
  return fallback
}

function formatDate(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString(locale.value === 'th' ? 'th-TH' : 'en-US', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

const billingTotal = computed(() => daily.value.reduce((sum, d) => sum + d.total_amount, 0))
const grandPaid = computed(() => daily.value.reduce((sum, d) => sum + d.paid_amount, 0))
const grandUnpaid = computed(() => daily.value.reduce((sum, d) => sum + d.unpaid_amount, 0))

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    daily.value = await adminApi.getRevenue()
  } catch (e) {
    error.value = apiErrorMessage(e, t('revenue.loadFailed'))
  } finally {
    loading.value = false
  }
}

// --- Other income (sponsor payments, investment injections, etc.) ---
const otherIncome = ref<OtherIncome[]>([])
const incomeLoading = ref(true)
const incomeLoadError = ref<string | null>(null)

const otherIncomeTotal = computed(() => otherIncome.value.reduce((sum, i) => sum + i.amount, 0))
const grandTotal = computed(() => billingTotal.value + otherIncomeTotal.value)

function sourceLabel(source: IncomeSource): string {
  return t(`income.sourceLabels.${source}`)
}

async function loadIncome(): Promise<void> {
  incomeLoading.value = true
  incomeLoadError.value = null
  try {
    otherIncome.value = await adminApi.getOtherIncome()
  } catch (e) {
    incomeLoadError.value = apiErrorMessage(e, t('income.loadFailed'))
  } finally {
    incomeLoading.value = false
  }
}

const incomeForm = reactive({
  income_date: todayIso(),
  source: 'sponsor' as IncomeSource,
  source_name: '',
  amount: '',
  note: '',
})
const incomeFormFile = ref<File | null>(null)
const incomeFormFileInput = ref<HTMLInputElement | null>(null)
const savingIncome = ref(false)
const createIncomeError = ref<string | null>(null)

function onIncomeFormFileSelected(event: Event): void {
  const input = event.target as HTMLInputElement
  // Kept raw and compressed at submit time instead: compressing here lands
  // asynchronously (seconds, for a phone photo) and could set the file back
  // *after* resetIncomeForm() cleared it, silently attaching this slip to
  // whichever entry is saved next.
  incomeFormFile.value = input.files?.[0] ?? null
}

function resetIncomeForm(): void {
  incomeForm.income_date = todayIso()
  incomeForm.source = 'sponsor'
  incomeForm.source_name = ''
  incomeForm.amount = ''
  incomeForm.note = ''
  incomeFormFile.value = null
  // Clearing the ref alone doesn't clear the <input>'s own displayed
  // filename — it's not v-model-bound (file inputs can't be), so the DOM
  // element needs its value reset directly or "Choose File" keeps showing
  // the last pick after a successful save.
  if (incomeFormFileInput.value) incomeFormFileInput.value.value = ''
}

async function submitIncome(): Promise<void> {
  createIncomeError.value = null
  incomeRowError.value = null
  const amount = Number(incomeForm.amount)
  if (!amount || amount <= 0) {
    createIncomeError.value = t('income.amountRequired')
    return
  }
  if (!incomeForm.source_name.trim()) {
    createIncomeError.value = t('income.sourceNameRequired')
    return
  }
  savingIncome.value = true
  try {
    let created = await adminApi.createOtherIncome({
      income_date: incomeForm.income_date,
      source: incomeForm.source,
      source_name: incomeForm.source_name.trim(),
      amount,
      note: incomeForm.note.trim() || null,
    })
    if (incomeFormFile.value) {
      try {
        const slip = await compressImage(incomeFormFile.value)
        created = await adminApi.uploadOtherIncomeSlip(created.id, slip)
      } catch {
        incomeRowError.value = t('income.slipUploadFailed')
      }
    }
    otherIncome.value = [created, ...otherIncome.value]
    resetIncomeForm()
  } catch (e) {
    createIncomeError.value = apiErrorMessage(e, t('income.createFailed'))
  } finally {
    savingIncome.value = false
  }
}

const incomeRowError = ref<string | null>(null)
const deletingIncomeId = ref<string | null>(null)
const uploadingSlipId = ref<string | null>(null)
const editingIncomeId = ref<string | null>(null)
const editIncomeForm = reactive({
  income_date: '',
  source: 'sponsor' as IncomeSource,
  source_name: '',
  amount: '',
  note: '',
})
const savingIncomeEdit = ref(false)

function startEditIncome(income: OtherIncome): void {
  editingIncomeId.value = income.id
  editIncomeForm.income_date = income.income_date
  editIncomeForm.source = income.source
  editIncomeForm.source_name = income.source_name
  editIncomeForm.amount = String(income.amount)
  editIncomeForm.note = income.note ?? ''
}

async function saveIncomeEdit(income: OtherIncome): Promise<void> {
  const amount = Number(editIncomeForm.amount)
  if (!amount || amount <= 0) {
    incomeRowError.value = t('income.amountRequired')
    return
  }
  if (!editIncomeForm.source_name.trim()) {
    incomeRowError.value = t('income.sourceNameRequired')
    return
  }
  savingIncomeEdit.value = true
  incomeRowError.value = null
  try {
    const updated = await adminApi.updateOtherIncome(income.id, {
      income_date: editIncomeForm.income_date,
      source: editIncomeForm.source,
      source_name: editIncomeForm.source_name.trim(),
      amount,
      note: editIncomeForm.note.trim() || null,
    })
    otherIncome.value = otherIncome.value.map((i) => (i.id === updated.id ? updated : i))
    editingIncomeId.value = null
  } catch (e) {
    incomeRowError.value = apiErrorMessage(e, t('income.updateFailed'))
  } finally {
    savingIncomeEdit.value = false
  }
}

async function removeIncome(income: OtherIncome): Promise<void> {
  if (!window.confirm(t('income.deleteConfirm'))) return
  deletingIncomeId.value = income.id
  incomeRowError.value = null
  try {
    await adminApi.deleteOtherIncome(income.id)
    otherIncome.value = otherIncome.value.filter((i) => i.id !== income.id)
  } catch (e) {
    incomeRowError.value = apiErrorMessage(e, t('income.deleteFailed'))
  } finally {
    deletingIncomeId.value = null
  }
}

async function onRowSlipSelected(event: Event, income: OtherIncome): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  incomeRowError.value = null
  uploadingSlipId.value = income.id
  try {
    const updated = await adminApi.uploadOtherIncomeSlip(income.id, await compressImage(file))
    otherIncome.value = otherIncome.value.map((i) => (i.id === updated.id ? updated : i))
  } catch (e) {
    incomeRowError.value = apiErrorMessage(e, t('income.slipUploadFailed'))
  } finally {
    uploadingSlipId.value = null
    input.value = ''
  }
}

onMounted(async () => {
  await Promise.all([load(), loadIncome()])
})
</script>

<template>
  <AdminNav />
  <main class="mx-auto max-w-3xl px-4 py-6">
    <h1 class="text-2xl font-bold text-brand-pink">{{ t('admin.nav.revenue') }}</h1>

    <p v-if="loading" class="mt-6 text-white/60">{{ t('common.loading') }}</p>
    <p v-else-if="error" class="mt-6 text-status-error">{{ error }}</p>

    <template v-else>
      <div v-if="daily.length > 0 || otherIncome.length > 0" class="mt-6 grid grid-cols-3 gap-2.5">
        <div class="hud-panel border border-brand-pink/40 bg-brand-surface p-3 text-center">
          <p class="text-xs tracking-wide text-white/40 uppercase">{{ t('revenue.grandTotal') }}</p>
          <p class="mt-1 font-display text-xl font-bold text-brand-pink">฿{{ grandTotal.toFixed(2) }}</p>
        </div>
        <div class="hud-panel border border-brand-pink/20 bg-brand-surface p-3 text-center">
          <p class="text-xs tracking-wide text-white/40 uppercase">{{ t('revenue.fromBilling') }}</p>
          <p class="mt-1 font-display text-xl font-bold">฿{{ billingTotal.toFixed(2) }}</p>
        </div>
        <div class="hud-panel border border-brand-pink/20 bg-brand-surface p-3 text-center">
          <p class="text-xs tracking-wide text-white/40 uppercase">{{ t('revenue.fromOtherIncome') }}</p>
          <p class="mt-1 font-display text-xl font-bold">฿{{ otherIncomeTotal.toFixed(2) }}</p>
        </div>
      </div>

      <div v-if="daily.length > 0" class="mt-2.5 grid grid-cols-2 gap-2.5">
        <div class="hud-panel border border-brand-pink/20 bg-brand-surface p-3 text-center">
          <p class="text-xs tracking-wide text-white/40 uppercase">{{ t('billing.paid') }}</p>
          <p class="mt-1 font-display text-xl font-bold text-status-success">฿{{ grandPaid.toFixed(2) }}</p>
        </div>
        <div class="hud-panel border border-brand-pink/20 bg-brand-surface p-3 text-center">
          <p class="text-xs tracking-wide text-white/40 uppercase">{{ t('billing.unpaid') }}</p>
          <p class="mt-1 font-display text-xl font-bold text-status-error">฿{{ grandUnpaid.toFixed(2) }}</p>
        </div>
      </div>

      <p v-if="daily.length === 0" class="mt-6 text-sm text-white/40">{{ t('revenue.empty') }}</p>
      <ul v-else class="mt-6 space-y-2">
        <li
          v-for="d in daily"
          :key="d.date"
          class="hud-panel border border-brand-pink/20 bg-brand-surface px-4 py-3"
        >
          <div class="flex items-center justify-between gap-3">
            <span class="font-medium">{{ formatDate(d.date) }}</span>
            <span class="font-display text-lg font-bold text-brand-pink">฿{{ d.total_amount.toFixed(2) }}</span>
          </div>
          <div class="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-white/50">
            <span>{{ d.session_count }} session{{ d.session_count > 1 ? 's' : '' }}</span>
            <span>·</span>
            <span>{{ d.billing_count }} {{ t('revenue.bills') }}</span>
            <span>·</span>
            <span class="text-status-success">{{ t('billing.paid') }} ฿{{ d.paid_amount.toFixed(2) }}</span>
            <span v-if="d.unpaid_amount > 0" class="text-status-error">
              {{ t('revenue.outstanding') }} ฿{{ d.unpaid_amount.toFixed(2) }}
            </span>
          </div>
        </li>
      </ul>
    </template>

    <!-- Other income (sponsor payments, investment injections, etc.) -->
    <section class="mt-10">
      <h2 class="text-sm font-semibold text-white/70">{{ t('revenue.otherIncomeTitle') }}</h2>

      <div class="hud-panel mt-3 border border-brand-pink/20 bg-brand-surface p-4">
        <h3 class="text-sm font-semibold text-white/70">{{ t('income.addTitle') }}</h3>
        <p v-if="createIncomeError" class="mt-2 text-sm text-status-error">{{ createIncomeError }}</p>

        <div class="mt-3 grid grid-cols-2 gap-2.5 sm:grid-cols-3">
          <label class="flex flex-col gap-1 text-xs text-white/50">
            {{ t('income.date') }}
            <input v-model="incomeForm.income_date" type="date" class="rounded border border-brand-pink-dark/40 bg-brand-black px-2 py-1.5 text-sm text-white" />
          </label>
          <label class="flex flex-col gap-1 text-xs text-white/50">
            {{ t('income.source') }}
            <select v-model="incomeForm.source" class="rounded border border-brand-pink-dark/40 bg-brand-black px-2 py-1.5 text-sm text-white">
              <option v-for="src in SOURCES" :key="src" :value="src">{{ sourceLabel(src) }}</option>
            </select>
          </label>
          <label class="flex flex-col gap-1 text-xs text-white/50">
            {{ t('income.amount') }}
            <input v-model="incomeForm.amount" type="number" min="0" step="0.01" placeholder="0.00" class="rounded border border-brand-pink-dark/40 bg-brand-black px-2 py-1.5 text-sm text-white" />
          </label>
          <label class="col-span-2 flex flex-col gap-1 text-xs text-white/50 sm:col-span-2">
            {{ t('income.sourceName') }}
            <input v-model="incomeForm.source_name" type="text" class="rounded border border-brand-pink-dark/40 bg-brand-black px-2 py-1.5 text-sm text-white" />
          </label>
          <label class="col-span-2 flex flex-col gap-1 text-xs text-white/50 sm:col-span-3">
            {{ t('income.note') }}
            <input v-model="incomeForm.note" type="text" class="rounded border border-brand-pink-dark/40 bg-brand-black px-2 py-1.5 text-sm text-white" />
          </label>
          <label class="col-span-2 flex flex-col gap-1 text-xs text-white/50 sm:col-span-3">
            {{ t('income.slip') }}
            <input ref="incomeFormFileInput" type="file" accept="image/*" class="text-xs" @change="onIncomeFormFileSelected" />
          </label>
        </div>

        <button
          type="button"
          :disabled="savingIncome"
          class="mt-4 rounded-full bg-brand-pink px-4 py-1.5 text-sm font-semibold text-brand-black disabled:opacity-50"
          @click="submitIncome"
        >
          {{ savingIncome ? t('income.saving') : t('income.addIncome') }}
        </button>
      </div>

      <p v-if="incomeRowError" class="mt-4 text-sm text-status-error">{{ incomeRowError }}</p>
      <p v-if="incomeLoading" class="mt-6 text-white/60">{{ t('common.loading') }}</p>
      <p v-else-if="incomeLoadError" class="mt-6 text-status-error">{{ incomeLoadError }}</p>
      <p v-else-if="otherIncome.length === 0" class="mt-6 text-sm text-white/40">{{ t('income.empty') }}</p>

      <ul v-else class="mt-6 space-y-3">
        <li v-for="i in otherIncome" :key="i.id" class="hud-hover hud-panel border border-brand-pink/15 bg-brand-surface p-4">
          <template v-if="editingIncomeId === i.id">
            <div class="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
              <input v-model="editIncomeForm.income_date" type="date" class="rounded border border-brand-pink-dark/40 bg-brand-black px-2 py-1.5 text-sm text-white" />
              <select v-model="editIncomeForm.source" class="rounded border border-brand-pink-dark/40 bg-brand-black px-2 py-1.5 text-sm text-white">
                <option v-for="src in SOURCES" :key="src" :value="src">{{ sourceLabel(src) }}</option>
              </select>
              <input v-model="editIncomeForm.amount" type="number" min="0" step="0.01" class="rounded border border-brand-pink-dark/40 bg-brand-black px-2 py-1.5 text-sm text-white" />
              <input v-model="editIncomeForm.source_name" type="text" class="col-span-2 rounded border border-brand-pink-dark/40 bg-brand-black px-2 py-1.5 text-sm text-white sm:col-span-3" />
              <input v-model="editIncomeForm.note" type="text" :placeholder="t('income.note')" class="col-span-2 rounded border border-brand-pink-dark/40 bg-brand-black px-2 py-1.5 text-sm text-white sm:col-span-3" />
            </div>
            <div class="mt-3 flex gap-2">
              <button :disabled="savingIncomeEdit" class="rounded-full bg-brand-pink px-3 py-1 text-xs font-semibold text-brand-black disabled:opacity-50" @click="saveIncomeEdit(i)">
                {{ t('income.save') }}
              </button>
              <button class="rounded-full border border-white/20 px-3 py-1 text-xs text-white/60" @click="editingIncomeId = null">
                {{ t('income.cancel') }}
              </button>
            </div>
          </template>

          <template v-else>
            <div class="flex items-start gap-3">
              <a v-if="i.slip_url" :href="i.slip_url" target="_blank" rel="noopener noreferrer" class="shrink-0">
                <img :src="i.slip_url" alt="" class="h-14 w-14 rounded border border-brand-pink/20 object-cover" />
              </a>
              <div class="flex-1">
                <div class="flex flex-wrap items-center gap-2">
                  <span class="rounded-full bg-brand-black px-2 py-0.5 text-[10px] font-semibold tracking-wide text-brand-pink/80 uppercase">
                    {{ sourceLabel(i.source) }}
                  </span>
                  <span class="font-medium">{{ i.source_name }}</span>
                </div>
                <p class="mt-0.5 text-xs text-white/40">{{ formatDate(i.income_date) }}</p>
                <p v-if="i.note" class="mt-0.5 text-xs text-white/40">{{ i.note }}</p>
              </div>
              <span class="shrink-0 font-bold text-brand-pink">฿{{ i.amount.toFixed(2) }}</span>
            </div>
            <div class="mt-3 flex flex-wrap items-center gap-3 text-xs">
              <button class="text-brand-pink underline" @click="startEditIncome(i)">{{ t('income.edit') }}</button>
              <label
                class="cursor-pointer text-brand-pink underline"
                :class="{ 'pointer-events-none opacity-50': uploadingSlipId === i.id }"
              >
                <template v-if="uploadingSlipId === i.id">{{ t('income.uploadingSlip') }}</template>
                <template v-else>{{ i.slip_url ? t('income.replaceSlip') : t('income.addSlip') }}</template>
                <input
                  type="file"
                  accept="image/*"
                  class="hidden"
                  :disabled="uploadingSlipId === i.id"
                  @change="onRowSlipSelected($event, i)"
                />
              </label>
              <button
                :disabled="deletingIncomeId === i.id"
                class="text-status-error underline disabled:opacity-50"
                @click="removeIncome(i)"
              >
                {{ t('common.delete') }}
              </button>
            </div>
          </template>
        </li>
      </ul>
    </section>
  </main>
</template>
