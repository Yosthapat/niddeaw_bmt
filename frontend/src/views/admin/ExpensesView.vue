<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import * as adminApi from '@/api/admin'
import { ApiError } from '@/api/client'
import { compressImage } from '@/utils/imageCompression'
import type { Admin, Expense, ExpenseCategory, MonthlyExpenseSummary } from '@/types'
import AdminNav from '@/components/layout/AdminNav.vue'

const { t, locale } = useI18n()

const CATEGORIES: ExpenseCategory[] = ['court_fee', 'shuttlecock', 'jersey', 'other']

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}
function currentMonthStr(): string {
  return todayIso().slice(0, 7)
}

const selectedMonth = ref(currentMonthStr())
const expenses = ref<Expense[]>([])
const summary = ref<MonthlyExpenseSummary[]>([])
const payers = ref<Admin[]>([])
const loading = ref(true)
const loadError = ref<string | null>(null)

const selectedMonthSummary = computed(
  () => summary.value.find((s) => s.month === selectedMonth.value) ?? null,
)

function apiErrorMessage(e: unknown, fallback: string): string {
  if (e instanceof ApiError) return `${fallback} (${e.status}: ${e.message})`
  return fallback
}

function categoryLabel(category: ExpenseCategory): string {
  return t(`expenses.categoryLabels.${category}`)
}

function payerName(adminId: string): string {
  return payers.value.find((p) => p.id === adminId)?.username ?? '?'
}

function formatDate(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString(locale.value === 'th' ? 'th-TH' : 'en-US', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

function shiftMonth(delta: number): void {
  const [y, m] = selectedMonth.value.split('-').map(Number)
  const d = new Date(Date.UTC(y, m - 1 + delta, 1))
  selectedMonth.value = `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}`
}

async function loadExpenses(): Promise<void> {
  loading.value = true
  loadError.value = null
  try {
    expenses.value = await adminApi.getExpenses(selectedMonth.value)
  } catch (e) {
    loadError.value = apiErrorMessage(e, t('expenses.loadFailed'))
  } finally {
    loading.value = false
  }
}

async function loadSummaryAndPayers(): Promise<void> {
  ;[summary.value, payers.value] = await Promise.all([
    adminApi.getExpenseSummary(),
    adminApi.getExpensePayers(),
  ])
}

watch(selectedMonth, loadExpenses)

onMounted(async () => {
  await Promise.all([loadExpenses(), loadSummaryAndPayers()])
})

// --- Add expense form ---
const form = reactive({
  expense_date: todayIso(),
  category: 'court_fee' as ExpenseCategory,
  category_other: '',
  amount: '',
  paid_by: '',
  note: '',
})
const formFile = ref<File | null>(null)
const formFileInput = ref<HTMLInputElement | null>(null)
const saving = ref(false)
const createError = ref<string | null>(null)

async function onFormFileSelected(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  formFile.value = file ? await compressImage(file) : null
}

function resetForm(): void {
  form.expense_date = todayIso()
  form.category = 'court_fee'
  form.category_other = ''
  form.amount = ''
  form.paid_by = ''
  form.note = ''
  formFile.value = null
  // Clearing the ref alone doesn't clear the <input>'s own displayed
  // filename — it's not v-model-bound (file inputs can't be), so the DOM
  // element needs its value reset directly or "Choose File" keeps showing
  // the last pick after a successful save.
  if (formFileInput.value) formFileInput.value.value = ''
}

async function submitExpense(): Promise<void> {
  createError.value = null
  const amount = Number(form.amount)
  if (!amount || amount <= 0) {
    createError.value = t('expenses.amountRequired')
    return
  }
  if (form.category === 'other' && !form.category_other.trim()) {
    createError.value = t('expenses.categoryOtherRequired')
    return
  }
  if (!form.paid_by) return

  saving.value = true
  try {
    let created = await adminApi.createExpense({
      expense_date: form.expense_date,
      category: form.category,
      category_other: form.category === 'other' ? form.category_other.trim() : null,
      amount,
      paid_by: form.paid_by,
      note: form.note.trim() || null,
    })
    if (formFile.value) {
      try {
        created = await adminApi.uploadReceipt(created.id, formFile.value)
      } catch {
        loadError.value = t('expenses.receiptUploadFailed')
      }
    }
    expenses.value =
      created.expense_date.slice(0, 7) === selectedMonth.value
        ? [created, ...expenses.value]
        : expenses.value
    await loadSummaryAndPayers()
    resetForm()
  } catch (e) {
    createError.value = apiErrorMessage(e, t('expenses.createFailed'))
  } finally {
    saving.value = false
  }
}

// --- Row actions: delete, edit, replace receipt, mark paid ---
const rowError = ref<string | null>(null)
const deletingId = ref<string | null>(null)
const markingPaidId = ref<string | null>(null)

async function markPaid(expense: Expense): Promise<void> {
  markingPaidId.value = expense.id
  rowError.value = null
  try {
    const updated = await adminApi.markExpensePaid(expense.id)
    expenses.value = expenses.value.map((e) => (e.id === updated.id ? updated : e))
  } catch (e) {
    rowError.value = apiErrorMessage(e, t('expenses.markPaidFailed'))
  } finally {
    markingPaidId.value = null
  }
}

async function removeExpense(expense: Expense): Promise<void> {
  if (!window.confirm(t('expenses.deleteConfirm'))) return
  deletingId.value = expense.id
  rowError.value = null
  try {
    await adminApi.deleteExpense(expense.id)
    expenses.value = expenses.value.filter((e) => e.id !== expense.id)
    await loadSummaryAndPayers()
  } catch (e) {
    rowError.value = apiErrorMessage(e, t('expenses.deleteFailed'))
  } finally {
    deletingId.value = null
  }
}

async function onRowReceiptSelected(event: Event, expense: Expense): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  rowError.value = null
  try {
    const updated = await adminApi.uploadReceipt(expense.id, await compressImage(file))
    expenses.value = expenses.value.map((e) => (e.id === updated.id ? updated : e))
  } catch (e) {
    rowError.value = apiErrorMessage(e, t('expenses.receiptUploadFailed'))
  } finally {
    input.value = ''
  }
}

const editingId = ref<string | null>(null)
const editForm = reactive({
  expense_date: '',
  category: 'court_fee' as ExpenseCategory,
  category_other: '',
  amount: '',
  paid_by: '',
  note: '',
})
const savingEdit = ref(false)

function startEdit(expense: Expense): void {
  editingId.value = expense.id
  editForm.expense_date = expense.expense_date
  editForm.category = expense.category
  editForm.category_other = expense.category_other ?? ''
  editForm.amount = String(expense.amount)
  editForm.paid_by = expense.paid_by
  editForm.note = expense.note ?? ''
}

async function saveEdit(expense: Expense): Promise<void> {
  const amount = Number(editForm.amount)
  if (!amount || amount <= 0) {
    rowError.value = t('expenses.amountRequired')
    return
  }
  if (editForm.category === 'other' && !editForm.category_other.trim()) {
    rowError.value = t('expenses.categoryOtherRequired')
    return
  }
  savingEdit.value = true
  rowError.value = null
  try {
    const updated = await adminApi.updateExpense(expense.id, {
      expense_date: editForm.expense_date,
      category: editForm.category,
      category_other: editForm.category === 'other' ? editForm.category_other.trim() : null,
      amount,
      paid_by: editForm.paid_by,
      note: editForm.note.trim() || null,
    })
    if (updated.expense_date.slice(0, 7) === selectedMonth.value) {
      expenses.value = expenses.value.map((e) => (e.id === updated.id ? updated : e))
    } else {
      expenses.value = expenses.value.filter((e) => e.id !== updated.id)
    }
    await loadSummaryAndPayers()
    editingId.value = null
  } catch (e) {
    rowError.value = apiErrorMessage(e, t('expenses.updateFailed'))
  } finally {
    savingEdit.value = false
  }
}
</script>

<template>
  <AdminNav />
  <main class="mx-auto max-w-3xl px-4 py-6">
    <h1 class="text-2xl font-bold text-brand-pink">{{ t('admin.nav.expenses') }}</h1>

    <!-- This month summary -->
    <section class="hud-panel mt-4 border border-brand-pink/20 bg-brand-surface p-4">
      <div class="flex items-center justify-between gap-2">
        <button type="button" class="px-2 text-white/50 hover:text-white" @click="shiftMonth(-1)">←</button>
        <input v-model="selectedMonth" type="month" class="rounded border border-brand-pink-dark/40 bg-brand-black px-2 py-1 text-sm" />
        <button type="button" class="px-2 text-white/50 hover:text-white" @click="shiftMonth(1)">→</button>
      </div>

      <div class="mt-3 flex items-center justify-between">
        <span class="text-sm text-white/60">{{ t('expenses.monthTotal') }}</span>
        <span class="text-xl font-bold text-brand-pink">
          ฿{{ (selectedMonthSummary?.total_amount ?? 0).toFixed(2) }}
        </span>
      </div>
      <div v-if="selectedMonthSummary" class="mt-2 flex flex-wrap gap-2 text-xs">
        <span
          v-for="cat in CATEGORIES.filter((c) => selectedMonthSummary?.by_category[c])"
          :key="cat"
          class="rounded-full bg-brand-black px-2.5 py-1 text-white/60"
        >
          {{ categoryLabel(cat) }}: ฿{{ selectedMonthSummary.by_category[cat]?.toFixed(2) }}
        </span>
      </div>
    </section>

    <!-- Add expense -->
    <section class="hud-panel mt-6 border border-brand-pink/20 bg-brand-surface p-4">
      <h2 class="text-sm font-semibold text-white/70">{{ t('expenses.addTitle') }}</h2>
      <p v-if="createError" class="mt-2 text-sm text-status-error">{{ createError }}</p>

      <div class="mt-3 grid grid-cols-2 gap-2.5 sm:grid-cols-3">
        <label class="col-span-1 flex flex-col gap-1 text-xs text-white/50">
          {{ t('expenses.date') }}
          <input v-model="form.expense_date" type="date" class="rounded border border-brand-pink-dark/40 bg-brand-black px-2 py-1.5 text-sm text-white" />
        </label>

        <label class="col-span-1 flex flex-col gap-1 text-xs text-white/50">
          {{ t('expenses.category') }}
          <select v-model="form.category" class="rounded border border-brand-pink-dark/40 bg-brand-black px-2 py-1.5 text-sm text-white">
            <option v-for="cat in CATEGORIES" :key="cat" :value="cat">{{ categoryLabel(cat) }}</option>
          </select>
        </label>

        <label class="col-span-1 flex flex-col gap-1 text-xs text-white/50">
          {{ t('expenses.amount') }}
          <input v-model="form.amount" type="number" min="0" step="0.01" placeholder="0.00" class="rounded border border-brand-pink-dark/40 bg-brand-black px-2 py-1.5 text-sm text-white" />
        </label>

        <label v-if="form.category === 'other'" class="col-span-2 flex flex-col gap-1 text-xs text-white/50 sm:col-span-3">
          {{ t('expenses.category') }} ({{ categoryLabel('other') }})
          <input v-model="form.category_other" type="text" :placeholder="t('expenses.categoryOtherPlaceholder')" class="rounded border border-brand-pink-dark/40 bg-brand-black px-2 py-1.5 text-sm text-white" />
        </label>

        <label class="col-span-1 flex flex-col gap-1 text-xs text-white/50">
          {{ t('expenses.paidBy') }}
          <select v-model="form.paid_by" class="rounded border border-brand-pink-dark/40 bg-brand-black px-2 py-1.5 text-sm text-white">
            <option value="" disabled>—</option>
            <option v-for="p in payers" :key="p.id" :value="p.id">{{ p.username }}</option>
          </select>
        </label>

        <label class="col-span-2 flex flex-col gap-1 text-xs text-white/50 sm:col-span-2">
          {{ t('expenses.note') }}
          <input v-model="form.note" type="text" class="rounded border border-brand-pink-dark/40 bg-brand-black px-2 py-1.5 text-sm text-white" />
        </label>

        <label class="col-span-2 flex flex-col gap-1 text-xs text-white/50 sm:col-span-3">
          {{ t('expenses.receipt') }}
          <input ref="formFileInput" type="file" accept="image/*" class="text-xs" @change="onFormFileSelected" />
        </label>
      </div>

      <button
        type="button"
        :disabled="saving || !form.paid_by"
        class="mt-4 rounded-full bg-brand-pink px-4 py-1.5 text-sm font-semibold text-brand-black disabled:opacity-50"
        @click="submitExpense"
      >
        {{ saving ? t('expenses.saving') : t('expenses.addExpense') }}
      </button>
    </section>

    <!-- List -->
    <p v-if="rowError" class="mt-4 text-sm text-status-error">{{ rowError }}</p>
    <p v-if="loading" class="mt-6 text-white/60">{{ t('common.loading') }}</p>
    <p v-else-if="loadError" class="mt-6 text-status-error">{{ loadError }}</p>
    <p v-else-if="expenses.length === 0" class="mt-6 text-sm text-white/40">{{ t('expenses.noExpensesThisMonth') }}</p>

    <ul v-else class="mt-6 space-y-3">
      <li v-for="e in expenses" :key="e.id" class="hud-panel border border-brand-pink/15 bg-brand-surface p-4">
        <template v-if="editingId === e.id">
          <div class="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
            <input v-model="editForm.expense_date" type="date" class="rounded border border-brand-pink-dark/40 bg-brand-black px-2 py-1.5 text-sm text-white" />
            <select v-model="editForm.category" class="rounded border border-brand-pink-dark/40 bg-brand-black px-2 py-1.5 text-sm text-white">
              <option v-for="cat in CATEGORIES" :key="cat" :value="cat">{{ categoryLabel(cat) }}</option>
            </select>
            <input v-model="editForm.amount" type="number" min="0" step="0.01" class="rounded border border-brand-pink-dark/40 bg-brand-black px-2 py-1.5 text-sm text-white" />
            <input
              v-if="editForm.category === 'other'"
              v-model="editForm.category_other"
              type="text"
              :placeholder="t('expenses.categoryOtherPlaceholder')"
              class="col-span-2 rounded border border-brand-pink-dark/40 bg-brand-black px-2 py-1.5 text-sm text-white sm:col-span-3"
            />
            <select v-model="editForm.paid_by" class="rounded border border-brand-pink-dark/40 bg-brand-black px-2 py-1.5 text-sm text-white">
              <option v-for="p in payers" :key="p.id" :value="p.id">{{ p.username }}</option>
            </select>
            <input v-model="editForm.note" type="text" :placeholder="t('expenses.note')" class="col-span-2 rounded border border-brand-pink-dark/40 bg-brand-black px-2 py-1.5 text-sm text-white" />
          </div>
          <div class="mt-3 flex gap-2">
            <button :disabled="savingEdit" class="rounded-full bg-brand-pink px-3 py-1 text-xs font-semibold text-brand-black disabled:opacity-50" @click="saveEdit(e)">
              {{ t('expenses.save') }}
            </button>
            <button class="rounded-full border border-white/20 px-3 py-1 text-xs text-white/60" @click="editingId = null">
              {{ t('expenses.cancel') }}
            </button>
          </div>
        </template>

        <template v-else>
          <div class="flex items-start gap-3">
            <a v-if="e.receipt_url" :href="e.receipt_url" target="_blank" rel="noopener noreferrer" class="shrink-0">
              <img :src="e.receipt_url" alt="" class="h-14 w-14 rounded border border-brand-pink/20 object-cover" />
            </a>
            <div class="flex-1">
              <div class="flex flex-wrap items-center gap-2">
                <span class="font-medium">{{ e.category === 'other' ? e.category_other : categoryLabel(e.category) }}</span>
                <span class="text-xs text-white/40">{{ formatDate(e.expense_date) }}</span>
              </div>
              <p class="mt-0.5 text-xs text-white/50">{{ t('expenses.paidBy') }}: {{ payerName(e.paid_by) }}</p>
              <p v-if="e.note" class="mt-0.5 text-xs text-white/40">{{ e.note }}</p>
            </div>
            <div class="flex shrink-0 flex-col items-end gap-1.5">
              <span class="font-bold text-brand-pink">฿{{ e.amount.toFixed(2) }}</span>
              <span
                v-if="e.is_paid"
                class="rounded-full border border-status-success/40 px-2 py-0.5 text-[10px] font-semibold text-status-success"
              >
                {{ t('expenses.paidStamp') }}
              </span>
              <button
                v-else
                type="button"
                :disabled="markingPaidId === e.id"
                class="rounded-full border border-brand-pink/40 px-2 py-0.5 text-[10px] font-semibold text-brand-pink disabled:opacity-50"
                @click="markPaid(e)"
              >
                {{ markingPaidId === e.id ? t('expenses.markingPaid') : t('expenses.markPaid') }}
              </button>
            </div>
          </div>

          <div class="mt-3 flex flex-wrap items-center gap-3 text-xs">
            <button class="text-brand-pink underline" @click="startEdit(e)">{{ t('expenses.edit') }}</button>
            <label class="cursor-pointer text-brand-pink underline">
              {{ e.receipt_url ? t('expenses.replaceReceipt') : t('expenses.addReceipt') }}
              <input type="file" accept="image/*" class="hidden" @change="onRowReceiptSelected($event, e)" />
            </label>
            <button
              :disabled="deletingId === e.id"
              class="text-status-error underline disabled:opacity-50"
              @click="removeExpense(e)"
            >
              {{ t('common.delete') }}
            </button>
          </div>
        </template>
      </li>
    </ul>

    <!-- Monthly history -->
    <section v-if="summary.length > 0" class="mt-8">
      <h2 class="text-sm font-semibold text-white/70">{{ t('expenses.history') }}</h2>
      <ul class="mt-2 space-y-1.5">
        <li v-for="s in summary" :key="s.month">
          <button
            type="button"
            class="hud-panel flex w-full items-center justify-between border px-3 py-2 text-sm"
            :class="s.month === selectedMonth ? 'border-brand-pink/60 bg-brand-surface-raised' : 'border-brand-pink/10 bg-brand-surface text-white/60'"
            @click="selectedMonth = s.month"
          >
            <span>{{ s.month }}</span>
            <span class="font-semibold">฿{{ s.total_amount.toFixed(2) }}</span>
          </button>
        </li>
      </ul>
    </section>
  </main>
</template>
