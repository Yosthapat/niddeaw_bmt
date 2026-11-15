<script setup lang="ts">
/**
 * The tournament's own money in three parts, each with its own total and
 * list: income (entry fees, written from the slips checked; coupon sales),
 * sponsors (kept apart, by name), and expenses (courts, shuttles, trophies,
 * prizes, refunds) — and what is left. Nothing here is the club's: the club's
 * revenue and expense screens never count it.
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import AdminNav from '@/components/layout/AdminNav.vue'
import { tournamentAdmin, type Money, type MoneyCategory, type MoneySummary, type PaidVia } from '@/api/tournament'
import { apiErrorMessage } from '@/api/errors'
import { useTournamentPick } from '@/composables/useTournamentPick'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { formatDate, money } from '@/utils/format'
import type { Locale } from '@/i18n'

const { t, locale } = useI18n()
const { confirm } = useConfirmDialog()
const { all, picked, load, pick } = useTournamentPick()

const INPUT = 'w-full rounded border border-brand-pink-dark/40 bg-brand-black px-2 py-1.5 text-sm text-white'
const INCOME: MoneyCategory[] = ['extra_shuttles', 'other_income']
const EXPENSE: MoneyCategory[] = ['court', 'shuttle', 'trophy', 'prize', 'staff', 'photo', 'coupon_refund', 'other']

const rows = ref<Money[]>([])
const summary = ref<MoneySummary | null>(null)
const admins = ref<{ id: string; username: string }[]>([])
const problem = ref('')
const loading = ref(false)

async function refresh(): Promise<void> {
  if (!picked.value) return
  loading.value = true
  problem.value = ''
  try {
    const id = picked.value.id
    ;[rows.value, summary.value] = await Promise.all([tournamentAdmin.money(id), tournamentAdmin.summary(id)])
  } catch (e) {
    problem.value = apiErrorMessage(e, t('cup.admin.loadFailed'))
  } finally {
    loading.value = false
  }
}
watch(() => picked.value?.id, refresh)
onMounted(async () => {
  if (!all.value.length) await load()
  admins.value = await tournamentAdmin.admins().catch(() => [])
  await refresh()
})

type Tab = 'income' | 'sponsor' | 'expense'
const TABS: Tab[] = ['income', 'sponsor', 'expense']
const tab = ref<Tab>('income')
const tabOf = (m: Money): Tab => (m.category === 'sponsor' ? 'sponsor' : m.direction)
const shown = computed(() => rows.value.filter((m) => tabOf(m) === tab.value))
const sum = (part: Tab): number => rows.value.filter((m) => tabOf(m) === part).reduce((n, m) => n + Number(m.amount), 0)
const totals = computed(() => {
  const income = sum('income')
  const sponsor = sum('sponsor')
  const expense = sum('expense')
  return { income, sponsor, expense, balance: income + sponsor - expense }
})

const today = (): string => new Date().toISOString().slice(0, 10)
const adding = ref(false)
/** The form opens for the part on screen: a sponsor, an income, an expense. */
function openAdd(): void {
  form.direction = tab.value === 'expense' ? 'expense' : 'income'
  form.category = tab.value === 'sponsor' ? 'sponsor' : tab.value === 'income' ? INCOME[0] : EXPENSE[0]
  form.category_other = ''
  adding.value = true
}
const form = reactive({
  direction: 'expense' as 'income' | 'expense',
  category: 'court' as MoneyCategory,
  category_other: '',
  amount: '' as number | '',
  entry_date: today(),
  paid_by: '',
  paid_via: '' as PaidVia | '',
  note: '',
})
const file = ref<File | null>(null)
const categories = computed(() => (form.direction === 'income' ? INCOME : EXPENSE))

async function add(): Promise<void> {
  if (!picked.value) return
  problem.value = ''
  if (form.category === 'sponsor' && !form.category_other.trim()) {
    problem.value = t('cup.money.sponsorNameMissing')
    return
  }
  try {
    const made = await tournamentAdmin.addMoney(picked.value.id, {
      direction: form.direction,
      category: form.category,
      // a sponsor's name, or what an "other" was for
      category_other: form.category === 'other' || form.category === 'sponsor' ? form.category_other.trim() || null : null,
      amount: Number(form.amount),
      entry_date: form.entry_date,
      paid_by: form.direction === 'expense' && form.paid_by ? form.paid_by : null,
      paid_via: form.paid_via || null,
      note: form.note.trim() || null,
    })
    if (file.value) await tournamentAdmin.receipt(made.id, file.value)
    adding.value = false
    Object.assign(form, { amount: '', category_other: '', note: '', entry_date: today() })
    file.value = null
    await refresh()
  } catch (e) {
    problem.value = apiErrorMessage(e, t('cup.admin.saveFailed'))
  }
}

async function remove(m: Money): Promise<void> {
  const ok = await confirm({ title: t('cup.money.deleteTitle'), message: t('cup.money.deleteBody', { amount: money(m.amount) }), confirmLabel: t('cup.money.delete') })
  if (!ok) return
  try {
    await tournamentAdmin.deleteMoney(m.id)
    await refresh()
  } catch (e) {
    problem.value = apiErrorMessage(e, t('cup.admin.saveFailed'))
  }
}

const label = (m: Money): string =>
  (m.category === 'other' || m.category === 'sponsor') && m.category_other ? m.category_other : t(`cup.money.cat.${m.category}`)
const payer = (id: string | null): string => admins.value.find((a) => a.id === id)?.username ?? ''
</script>

<template>
  <AdminNav />
  <main class="mx-auto max-w-3xl px-4 py-6">
    <h1 class="sr-only">{{ t('admin.nav.tMoney') }}</h1>

    <select
      v-if="all.length"
      :value="picked?.id"
      :aria-label="t('cup.admin.pick')"
      class="min-h-11 w-full rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-sm text-white"
      @change="pick(($event.target as HTMLSelectElement).value)"
    >
      <option v-for="x in all" :key="x.id" :value="x.id">{{ x.name }} · {{ x.starts_on }}</option>
    </select>
    <p v-else class="text-sm text-white/50">{{ t('cup.admin.noneYet') }}</p>

    <template v-if="picked">
      <p class="mt-3 text-xs text-white/50">{{ t('cup.money.apart') }}</p>

      <!-- the totals: income, sponsors, expenses, what is left -->
      <section class="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
        <button
          v-for="part in TABS"
          :key="part"
          type="button"
          class="hud-panel border bg-brand-surface p-3 text-left"
          :class="tab === part ? 'border-brand-pink' : 'border-brand-pink/15'"
          :aria-pressed="tab === part"
          @click="tab = part; adding = false"
        >
          <span class="block text-xs text-white/55">{{ t(`cup.money.part.${part}`) }}</span>
          <b class="font-display text-lg" :class="part === 'expense' ? 'text-[#ff9fb2]' : part === 'sponsor' ? 'text-[#ffd34d]' : 'text-status-success'">
            {{ money(totals[part]) }}
          </b>
        </button>
        <div class="hud-panel border border-brand-pink/15 bg-brand-surface p-3">
          <span class="block text-xs text-white/55">{{ totals.balance >= 0 ? t('cup.money.left') : t('cup.money.loss') }}</span>
          <b class="font-display text-lg" :class="totals.balance >= 0 ? 'text-white' : 'text-status-error'">{{ money(Math.abs(totals.balance)) }}</b>
        </div>
      </section>
      <p class="mt-1.5 text-xs text-white/45">{{ t('cup.money.balanceHow') }}</p>
      <div v-if="summary" class="mt-2 flex flex-wrap gap-2 text-xs">
        <RouterLink v-if="summary.pending_slips" to="/admin/tournament/teams" class="rounded-full border border-[#7fd0ff]/40 px-2.5 py-1 text-[#7fd0ff]">
          {{ t('cup.money.pending', { n: summary.pending_slips, amount: money(summary.pending_amount) }) }}
        </RouterLink>
        <RouterLink v-if="summary.refunds_owed" to="/admin/tournament/teams" class="rounded-full border border-[#ffd34d]/40 px-2.5 py-1 text-[#ffd34d]">
          {{ t('cup.money.owed', { n: summary.refunds_owed, amount: money(summary.refunds_owed_amount) }) }}
        </RouterLink>
      </div>

      <!-- one part at a time -->
      <div class="mt-5 grid grid-cols-3 gap-1 rounded-full border border-white/10 p-1" role="tablist" :aria-label="t('cup.money.parts')">
        <button
          v-for="part in TABS"
          :key="part"
          type="button"
          role="tab"
          class="min-h-11 rounded-full text-sm font-semibold"
          :class="tab === part ? 'bg-brand-pink text-brand-black' : 'text-white/70'"
          :aria-selected="tab === part"
          @click="tab = part; adding = false"
        >
          {{ t(`cup.money.part.${part}`) }}
        </button>
      </div>

      <div v-if="tab === 'income' && summary && Object.keys(summary.by_level).length" class="mt-3 flex flex-wrap gap-2 text-xs">
        <span class="text-white/50">{{ t('cup.money.feesByLevel') }}</span>
        <span v-for="(amount, name) in summary.by_level" :key="name" class="rounded-full bg-brand-black px-2.5 py-1 text-white/65">{{ name }}: {{ money(amount) }}</span>
      </div>
      <p v-if="tab === 'income'" class="mt-2 text-xs text-white/45">{{ t('cup.money.incomeHint') }}</p>

      <!-- add, for the part on screen -->
      <button v-if="!adding" type="button" class="tap hud-hover mt-4 w-full rounded-full border border-brand-pink/40 px-4 text-sm font-semibold text-brand-pink" @click="openAdd">
        + {{ t(`cup.money.add.${tab}`) }}
      </button>
      <section v-else class="hud-panel mt-4 border border-brand-pink/20 bg-brand-surface p-4">
        <h2 class="text-sm font-semibold text-white/70">{{ t(`cup.money.add.${tab}`) }}</h2>
        <div class="mt-3 grid grid-cols-2 gap-2.5 sm:grid-cols-3">
          <label v-if="tab === 'sponsor'" class="col-span-2 flex flex-col gap-1 text-xs text-white/50 sm:col-span-3">
            {{ t('cup.money.sponsorName') }}<input v-model="form.category_other" maxlength="60" :class="INPUT" />
          </label>
          <label v-else class="flex flex-col gap-1 text-xs text-white/50">
            {{ t('cup.money.category') }}
            <select v-model="form.category" :class="INPUT">
              <option v-for="c in categories" :key="c" :value="c">{{ t(`cup.money.cat.${c}`) }}</option>
            </select>
          </label>
          <label class="flex flex-col gap-1 text-xs text-white/50">{{ t('cup.money.amount') }}<input v-model.number="form.amount" type="number" min="0" step="0.01" :class="INPUT" /></label>
          <label class="flex flex-col gap-1 text-xs text-white/50">{{ t('cup.money.date') }}<input v-model="form.entry_date" type="date" :class="INPUT" /></label>
          <label v-if="form.category === 'other'" class="col-span-2 flex flex-col gap-1 text-xs text-white/50 sm:col-span-3">{{ t('cup.money.what') }}<input v-model="form.category_other" maxlength="60" :class="INPUT" /></label>
          <label v-if="form.direction === 'expense'" class="flex flex-col gap-1 text-xs text-white/50">
            {{ t('cup.money.paidBy') }}
            <select v-model="form.paid_by" :class="INPUT">
              <option value="">{{ t('cup.money.me') }}</option>
              <option v-for="a in admins" :key="a.id" :value="a.id">{{ a.username }}</option>
            </select>
          </label>
          <label class="flex flex-col gap-1 text-xs text-white/50">
            {{ t('cup.money.via') }}
            <select v-model="form.paid_via" :class="INPUT">
              <option value="">—</option>
              <option value="transfer">{{ t('cup.admin.paidTransfer') }}</option>
              <option value="cash">{{ t('cup.admin.paidCash') }}</option>
            </select>
          </label>
          <label class="col-span-2 flex flex-col gap-1 text-xs text-white/50 sm:col-span-3">{{ t('cup.money.note') }}<input v-model="form.note" maxlength="300" :class="INPUT" /></label>
          <label class="col-span-2 flex flex-col gap-1 text-xs text-white/50 sm:col-span-3">
            {{ t('cup.money.receipt') }}
            <span class="hud-panel cursor-pointer border border-brand-pink/30 bg-brand-black px-3 py-2 text-sm text-brand-pink">
              {{ file ? file.name : t('common.chooseFile') }}
              <input type="file" accept="image/*" class="hidden" @change="file = ($event.target as HTMLInputElement).files?.[0] ?? null" />
            </span>
          </label>
        </div>
        <div class="mt-3 flex gap-2">
          <button type="button" class="tap rounded-full bg-brand-pink px-5 text-sm font-semibold text-brand-black" @click="add">{{ t('cup.money.save') }}</button>
          <button type="button" class="tap rounded-full border border-white/20 px-4 text-sm text-white/60" @click="adding = false">{{ t('common.cancel') }}</button>
        </div>
      </section>

      <p v-if="problem" class="mt-4 text-sm text-status-error" role="alert">{{ problem }}</p>
      <p v-if="loading && !rows.length" class="mt-6 text-white/60">{{ t('common.loading') }}</p>
      <p v-else-if="!shown.length" class="mt-6 text-sm text-white/40">{{ t(`cup.money.empty.${tab}`) }}</p>

      <ul class="mt-4 space-y-2">
        <li v-for="m in shown" :key="m.id" class="hud-panel flex items-start gap-3 border border-brand-pink/15 bg-brand-surface p-3">
          <a v-if="m.receipt_url" :href="m.receipt_url" target="_blank" rel="noopener" class="shrink-0">
            <img :src="m.receipt_url" :alt="t('cup.money.receipt')" class="h-12 w-12 rounded border border-white/15 object-cover" />
          </a>
          <div class="min-w-0 flex-1">
            <p class="text-sm font-medium">{{ label(m) }}</p>
            <p class="text-xs text-white/50">
              {{ formatDate(m.entry_date, locale as Locale) }}
              <template v-if="m.paid_by && payer(m.paid_by)"> · {{ t('cup.money.paidBy') }} {{ payer(m.paid_by) }}</template>
              <template v-if="m.paid_via"> · {{ m.paid_via === 'cash' ? t('cup.admin.paidCash') : t('cup.admin.paidTransfer') }}</template>
              <template v-if="m.automatic"> · {{ t('cup.money.auto') }}</template>
            </p>
            <p v-if="m.note" class="text-xs text-white/45">{{ m.note }}</p>
          </div>
          <div class="flex shrink-0 flex-col items-end gap-1">
            <b :class="m.direction === 'income' ? (m.category === 'sponsor' ? 'text-[#ffd34d]' : 'text-status-success') : 'text-[#ff9fb2]'">
              {{ m.direction === 'income' ? '+' : '−' }}{{ money(m.amount) }}
            </b>
            <button v-if="!m.automatic" type="button" class="text-xs text-white/40 underline" @click="remove(m)">{{ t('cup.money.delete') }}</button>
          </div>
        </li>
      </ul>
    </template>
  </main>
</template>
