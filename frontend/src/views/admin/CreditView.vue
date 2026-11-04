<script setup lang="ts">
/**
 * Club credit, the admin's side: top-up slips to check, every member's
 * balance with its history and a way to adjust it (cash at the court, a
 * refund, a correction — always with a reason), and the packages on sale.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as adminApi from '@/api/admin'
import type { CreditBalances, CreditTopupAdmin, MemberLedger } from '@/api/admin'
import type { CreditPackage } from '@/api/line'
import { apiErrorMessage } from '@/api/errors'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { usePlayersStore } from '@/stores/players'
import { formatDateTime } from '@/utils/format'
import type { Locale } from '@/i18n'
import AdminNav from '@/components/layout/AdminNav.vue'

const { t, locale } = useI18n()
const { confirm } = useConfirmDialog()
const playersStore = usePlayersStore()

type Tab = 'slips' | 'members' | 'packages'
const tab = ref<Tab>('slips')
const num = (n: number): string => n.toLocaleString('en-US')
const baht = (n: number): string => `฿${n.toLocaleString('en-US', { maximumFractionDigits: 2 })}`
const when = (iso: string | null): string => (iso ? formatDateTime(iso, locale.value as Locale) : '')

const problem = ref('')
const busy = ref<string | null>(null)

// ------------------------------------------------------------------ slips
const waiting = ref<CreditTopupAdmin[]>([])
const done = ref<CreditTopupAdmin[]>([])
const rejecting = ref<string | null>(null)
const reason = ref('')
const bigSlip = ref<string | null>(null)

async function loadSlips(): Promise<void> {
  ;[waiting.value, done.value] = await Promise.all([adminApi.getCreditTopups('waiting'), adminApi.getCreditTopups('done')])
}

async function decide(topup: CreditTopupAdmin, ok: boolean): Promise<void> {
  busy.value = topup.id
  problem.value = ''
  try {
    if (ok) await adminApi.approveCreditTopup(topup.id)
    else await adminApi.rejectCreditTopup(topup.id, reason.value.trim() || null)
    rejecting.value = null
    reason.value = ''
    await Promise.all([loadSlips(), loadBalances()])
  } catch (e) {
    problem.value = apiErrorMessage(e, t('credit.actionFailed'))
    await loadSlips()
  } finally {
    busy.value = null
  }
}

// ---------------------------------------------------------------- members
const balances = ref<CreditBalances | null>(null)
const query = ref('')
const open = ref<MemberLedger | null>(null)
const form = reactive({ add: true, credits: '', cash: '', note: '' })

async function loadBalances(): Promise<void> {
  balances.value = await adminApi.getCreditBalances()
}

// Everyone in the club can be found, not only those who hold credit: the
// first credit a member gets may be cash handed over at the court.
const rows = computed(() => {
  const held = new Map((balances.value?.members ?? []).map((m) => [m.player_id, m.balance]))
  const q = query.value.trim().toLowerCase()
  const everyone = playersStore.players.map((p) => ({
    id: p.id,
    nickname: p.nickname,
    code: p.member_code,
    balance: held.get(p.id) ?? 0,
  }))
  const list = q
    ? everyone.filter((m) => m.nickname.toLowerCase().includes(q) || m.code.toLowerCase().includes(q))
    : everyone.filter((m) => m.balance > 0)
  return list.sort((a, b) => b.balance - a.balance || a.nickname.localeCompare(b.nickname)).slice(0, 80)
})

async function openMember(id: string): Promise<void> {
  problem.value = ''
  try {
    open.value = await adminApi.getMemberLedger(id)
    Object.assign(form, { add: true, credits: '', cash: '', note: '' })
  } catch (e) {
    problem.value = apiErrorMessage(e, t('credit.loadFailed'))
  }
}

const adjustProblem = computed((): string | null => {
  const credits = Number(form.credits)
  if (!form.credits || !Number.isInteger(credits) || credits <= 0) return t('credit.needCredits')
  if (credits > 100000) return t('validation.tooLarge')
  if (form.cash && (!Number.isFinite(Number(form.cash)) || Number(form.cash) < 0)) return t('credit.badCash')
  if (!form.note.trim()) return t('credit.needReason')
  if (!form.add && open.value && credits > open.value.balance) return t('credit.notThatMuch', { n: num(open.value.balance) })
  return null
})

async function saveAdjust(): Promise<void> {
  const member = open.value
  if (!member || adjustProblem.value) return
  const credits = Number(form.credits)
  const ok = await confirm({
    title: form.add ? t('credit.confirmAdd', { n: num(credits), name: member.player.nickname }) : t('credit.confirmSub', { n: num(credits), name: member.player.nickname }),
    message: form.note.trim(),
    confirmLabel: form.add ? t('credit.saveAdd') : t('credit.saveSub'),
  })
  if (!ok) return
  busy.value = member.player.id
  problem.value = ''
  try {
    open.value = await adminApi.adjustCredit(member.player.id, {
      delta: form.add ? credits : -credits,
      cash: form.cash ? Number(form.cash) : null,
      note: form.note.trim(),
    })
    Object.assign(form, { credits: '', cash: '', note: '' })
    await loadBalances()
  } catch (e) {
    problem.value = apiErrorMessage(e, t('credit.actionFailed'))
  } finally {
    busy.value = null
  }
}

// --------------------------------------------------------------- packages
const packages = ref<CreditPackage[]>([])
const newPkg = reactive({ credits: '', price: '' })

async function loadPackages(): Promise<void> {
  packages.value = await adminApi.getCreditPackages()
}

const pkgProblem = computed((): string | null => {
  const c = Number(newPkg.credits)
  const p = Number(newPkg.price)
  if (!Number.isInteger(c) || c <= 0 || !Number.isFinite(p) || p <= 0) return t('credit.pkgNeedBoth')
  if (p > c) return t('credit.pkgPriceTooHigh')
  return null
})

async function addPackage(): Promise<void> {
  if (pkgProblem.value) return
  busy.value = 'pkg'
  problem.value = ''
  try {
    await adminApi.createCreditPackage({
      credits: Number(newPkg.credits),
      price: Number(newPkg.price),
      is_active: true,
      sort_order: packages.value.length,
    })
    Object.assign(newPkg, { credits: '', price: '' })
    await loadPackages()
  } catch (e) {
    problem.value = apiErrorMessage(e, t('credit.actionFailed'))
  } finally {
    busy.value = null
  }
}

async function toggle(p: CreditPackage): Promise<void> {
  busy.value = p.id
  try {
    await adminApi.updateCreditPackage(p.id, { is_active: !p.is_active })
    await loadPackages()
  } catch (e) {
    problem.value = apiErrorMessage(e, t('credit.actionFailed'))
  } finally {
    busy.value = null
  }
}

async function removePackage(p: CreditPackage): Promise<void> {
  if (!(await confirm({ title: t('common.delete'), message: t('credit.pkgDeleteConfirm', { credits: num(p.credits), price: baht(p.price) }), danger: true }))) return
  busy.value = p.id
  try {
    await adminApi.deleteCreditPackage(p.id)
    await loadPackages()
  } catch (e) {
    problem.value = apiErrorMessage(e, t('credit.actionFailed'))
  } finally {
    busy.value = null
  }
}

const loading = ref(true)
onMounted(async () => {
  try {
    await Promise.all([loadSlips(), loadBalances(), loadPackages(), playersStore.ensureLoaded()])
  } catch (e) {
    problem.value = apiErrorMessage(e, t('credit.loadFailed'))
  } finally {
    loading.value = false
  }
})

const KIND_TONE: Record<string, string> = {
  topup: 'text-[#7ff0b4]',
  refund: 'text-[#7ff0b4]',
  adjust: 'text-[#ffe9a8]',
  bill: 'text-[#ffb08a]',
}
</script>

<template>
  <AdminNav />
  <main class="mx-auto max-w-2xl px-4 py-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="font-display text-2xl font-bold">{{ t('credit.title') }}</h1>
      <div role="tablist" class="flex gap-1.5">
        <button
          v-for="x in (['slips', 'members', 'packages'] as const)"
          :key="x"
          type="button"
          role="tab"
          :aria-selected="tab === x"
          class="tap rounded-full px-4 text-sm"
          :class="tab === x ? 'bg-brand-pink font-medium text-brand-black' : 'border border-white/20 text-white/80'"
          @click="tab = x"
        >
          {{ t(`credit.tab.${x}`) }}<template v-if="x === 'slips' && waiting.length"> ({{ waiting.length }})</template>
        </button>
      </div>
    </div>

    <div class="wallet mt-4">
      <p class="text-xs text-[#ffe9a8]/80">{{ t('credit.outstanding') }}</p>
      <p class="mt-0.5 flex items-center gap-2"><span class="coin h-7 w-7 text-sm" aria-hidden="true">฿</span><span class="bal">{{ num(balances?.outstanding ?? 0) }}</span></p>
      <p class="mt-1 text-xs text-white/60">{{ t('credit.outstandingNote') }}</p>
    </div>

    <p v-if="loading" class="mt-6 text-white/60">{{ t('common.loading') }}</p>
    <p v-if="problem" class="mt-4 text-sm text-status-error" role="alert">{{ problem }}</p>

    <!-- ============================================================ slips -->
    <section v-if="!loading && tab === 'slips'" class="mt-5 space-y-3">
      <p v-if="waiting.length === 0" class="hud-panel border border-brand-pink/20 bg-brand-surface p-4 text-sm text-white/55">{{ t('credit.noSlips') }}</p>
      <article v-for="w in waiting" :key="w.id" class="hud-panel border border-[#ffd34d]/35 bg-brand-surface p-4">
        <div class="flex items-start gap-3">
          <button v-if="w.slip_url" type="button" class="shrink-0" :aria-label="t('credit.openSlip')" @click="bigSlip = w.slip_url">
            <img :src="w.slip_url" :alt="t('credit.slipAlt', { name: w.player_nickname })" class="h-28 w-20 rounded-lg border border-white/15 object-cover" />
          </button>
          <div class="min-w-0 flex-1">
            <p class="font-medium">{{ w.player_nickname }} <span class="text-xs text-white/45">{{ w.player_code }}</span></p>
            <p class="mt-0.5 text-sm text-white/75">{{ t('credit.pkgLine', { price: baht(w.price), credits: num(w.credits) }) }}</p>
            <p class="mt-0.5 text-xs text-white/45">{{ when(w.slip_sent_at ?? w.created_at) }}</p>
            <p class="mt-2 text-xs text-[#ffd34d]">{{ t('credit.checkAmount', { price: baht(w.price) }) }}</p>
          </div>
        </div>
        <div v-if="rejecting === w.id" class="mt-3 flex flex-col gap-2">
          <input v-model="reason" type="text" maxlength="300" :placeholder="t('credit.rejectPlaceholder')" class="min-h-11 rounded border border-brand-pink-dark/40 bg-brand-black px-3 text-base text-white" />
          <div class="flex gap-2">
            <button type="button" class="tap flex-1 rounded-lg border border-status-error/50 text-sm text-status-error" :disabled="busy === w.id" @click="decide(w, false)">{{ t('credit.rejectConfirm') }}</button>
            <button type="button" class="tap flex-1 rounded-lg border border-white/20 text-sm" @click="rejecting = null">{{ t('common.cancel') }}</button>
          </div>
        </div>
        <div v-else class="mt-3 flex gap-2">
          <button type="button" class="tap flex-1 rounded-lg bg-status-success/90 text-sm font-semibold text-black" :disabled="busy === w.id" @click="decide(w, true)">
            {{ t('credit.approve', { credits: num(w.credits) }) }}
          </button>
          <button type="button" class="tap flex-1 rounded-lg border border-white/20 text-sm" :disabled="busy === w.id" @click="rejecting = w.id">{{ t('credit.reject') }}</button>
        </div>
      </article>

      <details v-if="done.length" class="hud-panel border border-white/10 bg-brand-surface p-4">
        <summary class="cursor-pointer text-sm text-white/70">{{ t('credit.recent') }}</summary>
        <ul class="mt-2 divide-y divide-white/8 text-sm">
          <li v-for="d in done" :key="d.id" class="flex items-center gap-2 py-2">
            <span class="flex-1">{{ d.player_nickname }} · {{ t('credit.pkgLine', { price: baht(d.price), credits: num(d.credits) }) }}</span>
            <span :class="d.status === 'approved' ? 'text-status-success' : 'text-status-error'">{{ t(`credit.status.${d.status}`) }}</span>
          </li>
        </ul>
      </details>
    </section>

    <!-- ========================================================== members -->
    <section v-if="!loading && tab === 'members'" class="mt-5">
      <input v-model="query" type="search" :placeholder="t('credit.search')" :aria-label="t('credit.search')" class="min-h-11 w-full rounded border border-brand-pink-dark/40 bg-brand-black px-3 text-base text-white" />
      <p v-if="!query && rows.length === 0" class="mt-3 text-sm text-white/55">{{ t('credit.nobodyHolds') }}</p>
      <ul class="mt-3 space-y-2">
        <li v-for="m in rows" :key="m.id">
          <button type="button" class="hud-panel hud-hover flex w-full items-center gap-3 border border-brand-pink/20 bg-brand-surface px-4 py-3 text-left" @click="openMember(m.id)">
            <span class="flex-1">{{ m.nickname }} <span class="text-xs text-white/45">{{ m.code }}</span></span>
            <span class="coin h-5 w-5 text-[10px]" aria-hidden="true">฿</span>
            <b class="font-display text-[#ffe9a8]">{{ num(m.balance) }}</b>
          </button>
        </li>
      </ul>
    </section>

    <!-- ========================================================= packages -->
    <section v-if="!loading && tab === 'packages'" class="mt-5 space-y-3">
      <p class="text-sm text-white/60">{{ t('credit.pkgNote') }}</p>
      <ul class="space-y-2">
        <li v-for="p in packages" :key="p.id" class="hud-panel flex items-center gap-3 border border-brand-pink/20 bg-brand-surface px-4 py-3" :class="{ 'opacity-55': !p.is_active }">
          <span class="flex-1">
            <b class="font-display text-lg text-[#ffe9a8]">{{ num(p.credits) }}</b> {{ t('credit.credits') }}
            <span class="text-white/60"> · {{ t('credit.pay') }} {{ baht(p.price) }}</span>
            <span v-if="p.credits > p.price" class="ml-1 text-xs text-[#ff9fd6]">{{ t('credit.bonus', { pct: Math.round((1 - p.price / p.credits) * 100) }) }}</span>
          </span>
          <button type="button" class="tap rounded-full border border-white/20 px-3 text-xs" :disabled="busy === p.id" @click="toggle(p)">{{ p.is_active ? t('credit.pkgHide') : t('credit.pkgShow') }}</button>
          <button type="button" class="tap rounded-full px-2 text-xs text-status-error" :disabled="busy === p.id" :aria-label="t('common.delete')" @click="removePackage(p)">✕</button>
        </li>
      </ul>
      <form class="hud-panel grid grid-cols-2 items-end gap-2 border sm:grid-cols-[1fr_1fr_auto] border-brand-pink/20 bg-brand-surface p-4" @submit.prevent="addPackage">
        <label class="flex min-w-0 flex-col gap-1 text-xs text-white/50">{{ t('credit.pkgCredits') }}<input v-model="newPkg.credits" type="number" min="1" inputmode="numeric" class="min-h-11 w-full min-w-0 rounded border border-brand-pink-dark/40 bg-brand-black px-2 text-base text-white" /></label>
        <label class="flex min-w-0 flex-col gap-1 text-xs text-white/50">{{ t('credit.pkgPrice') }}<input v-model="newPkg.price" type="number" min="1" step="0.01" inputmode="decimal" class="min-h-11 w-full min-w-0 rounded border border-brand-pink-dark/40 bg-brand-black px-2 text-base text-white" /></label>
        <button type="submit" class="tap col-span-2 min-h-11 rounded-lg bg-brand-pink px-4 text-sm font-semibold text-brand-black disabled:opacity-40 sm:col-span-1" :disabled="!!pkgProblem || busy === 'pkg'">{{ t('credit.pkgAdd') }}</button>
        <p v-if="newPkg.credits && newPkg.price && pkgProblem" class="col-span-2 text-xs sm:col-span-3 text-status-error">{{ pkgProblem }}</p>
      </form>
    </section>

    <!-- a member: history + adjust -->
    <div v-if="open" class="fixed inset-0 z-40 flex items-end justify-center bg-black/60 sm:items-center" @click.self="open = null">
      <div class="max-h-[88dvh] w-full max-w-lg overflow-y-auto rounded-t-2xl border border-white/15 bg-[#160a2a] p-4 sm:rounded-2xl" role="dialog" :aria-label="open.player.nickname">
        <div class="flex items-center gap-2">
          <b class="text-lg">{{ open.player.nickname }}</b><span class="text-xs text-white/45">{{ open.player.member_code }}</span>
          <span class="ml-auto flex items-center gap-1.5"><span class="coin h-6 w-6 text-xs" aria-hidden="true">฿</span><b class="font-display text-xl text-[#ffe9a8]">{{ num(open.balance) }}</b></span>
          <button type="button" class="tap px-2 text-white/60" :aria-label="t('credit.close')" @click="open = null">✕</button>
        </div>
        <form class="mt-3 flex flex-col gap-2" @submit.prevent="saveAdjust">
          <p class="text-xs text-white/55">{{ t('credit.adjustNote') }}</p>
          <div class="flex gap-1 self-start rounded-full border border-white/15 p-1">
            <button type="button" class="tap rounded-full px-4 text-sm" :class="form.add ? 'bg-brand-pink text-brand-black' : 'text-white/70'" @click="form.add = true">{{ t('credit.add') }}</button>
            <button type="button" class="tap rounded-full px-4 text-sm" :class="!form.add ? 'bg-brand-pink text-brand-black' : 'text-white/70'" @click="form.add = false">{{ t('credit.sub') }}</button>
          </div>
          <label class="flex flex-col gap-1 text-xs text-white/50">{{ t('credit.credits') }}<input v-model="form.credits" type="number" min="1" inputmode="numeric" class="min-h-11 rounded border border-brand-pink-dark/40 bg-brand-black px-3 text-base text-white" /></label>
          <label class="flex flex-col gap-1 text-xs text-white/50">{{ form.add ? t('credit.cashIn') : t('credit.cashOut') }}<input v-model="form.cash" type="number" min="0" step="0.01" inputmode="decimal" :placeholder="t('credit.cashPlaceholder')" class="min-h-11 rounded border border-brand-pink-dark/40 bg-brand-black px-3 text-base text-white" /></label>
          <label class="flex flex-col gap-1 text-xs text-white/50">{{ t('credit.reason') }}<input v-model="form.note" type="text" maxlength="300" :placeholder="form.add ? t('credit.reasonAddPlaceholder') : t('credit.reasonSubPlaceholder')" class="min-h-11 rounded border border-brand-pink-dark/40 bg-brand-black px-3 text-base text-white" /></label>
          <p v-if="(form.credits || form.note) && adjustProblem" class="text-xs text-status-error">{{ adjustProblem }}</p>
          <button type="submit" class="tap rounded-lg bg-[#ffc531] font-semibold text-[#2e1a00] disabled:opacity-40" :disabled="!!adjustProblem || busy === open.player.id">
            {{ form.add ? t('credit.saveAdd') : t('credit.saveSub') }}
          </button>
        </form>
        <h3 class="mt-4 text-sm text-white/60">{{ t('credit.history') }}</h3>
        <ul class="mt-1 divide-y divide-white/8 text-sm">
          <li v-for="h in open.history" :key="h.id" class="flex items-start gap-2 py-2">
            <span class="min-w-0 flex-1">
              <span class="block">{{ t(`lineCredit.kind.${h.kind}`) }}<template v-if="h.cash !== null"> · {{ baht(h.cash) }}</template></span>
              <span class="block truncate text-xs text-white/45">{{ when(h.created_at) }}<template v-if="h.note"> · {{ h.note }}</template></span>
            </span>
            <b class="font-display" :class="KIND_TONE[h.kind]">{{ h.delta > 0 ? '+' : '−' }}{{ num(Math.abs(h.delta)) }}</b>
          </li>
          <li v-if="open.history.length === 0" class="py-2 text-white/45">{{ t('lineCredit.noHistory') }}</li>
        </ul>
      </div>
    </div>

    <!-- slip, full size -->
    <div v-if="bigSlip" class="fixed inset-0 z-50 flex items-center justify-center bg-black/85 p-4" @click="bigSlip = null">
      <img :src="bigSlip" alt="" class="max-h-full max-w-full rounded-xl" />
    </div>
  </main>
</template>

<style scoped>
.wallet {
  border-radius: 16px;
  padding: 14px 16px;
  background:
    radial-gradient(260px 160px at 85% 10%, rgb(255 197 49 / 0.3), transparent 70%),
    linear-gradient(135deg, #3a2408, #1c1030 70%);
  border: 1px solid rgb(255 211 77 / 0.45);
}
.bal {
  font: 700 28px 'Chakra Petch', sans-serif;
  color: #ffe9a8;
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
}
</style>
