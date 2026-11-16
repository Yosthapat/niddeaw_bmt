<script setup lang="ts">
/**
 * The tournament itself: make one, set its prices, its own PromptPay
 * account, when entries open and close, and its levels — how many teams
 * each takes (16 / 24 / 32) and its rules. Opening entries needs the
 * account first; the entry and shuttle prices lock once anyone has paid.
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import AdminNav from '@/components/layout/AdminNav.vue'
import { tournamentAdmin, type Level, type Tournament, type TournamentStatus } from '@/api/tournament'
import { apiErrorMessage } from '@/api/errors'
import { useTournamentPick } from '@/composables/useTournamentPick'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { money } from '@/utils/format'
import DatePick, { type QuickPick } from '@/components/admin/DatePick.vue'

const { t, locale } = useI18n()
const { confirm } = useConfirmDialog()
const { all, picked, loading, problem, load, pick, replace } = useTournamentPick()

const INPUT = 'w-full rounded border border-brand-pink-dark/40 bg-brand-black px-2 py-1.5 text-sm text-white'
const STATUSES: TournamentStatus[] = ['draft', 'open', 'closed', 'running', 'done']

/** datetime-local wants "YYYY-MM-DDTHH:mm" in the device's time. */
function toLocalInput(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n: number): string => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}
const fromLocalInput = (v: string): string | null => (v ? new Date(v).toISOString() : null)

// --- one-tap answers under the date fields --------------------------------------
const pad2 = (n: number): string => String(n).padStart(2, '0')
const ymd = (d: Date): string => `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`
function shortDay(d: Date): string {
  return new Intl.DateTimeFormat(locale.value === 'th' ? 'th-TH' : 'en-GB', { weekday: 'short', day: 'numeric', month: 'short' }).format(d)
}
/** The Saturdays two to five weeks out: time enough to fill the levels. */
const startQuick = computed<QuickPick[]>(() => {
  const d = new Date()
  d.setDate(d.getDate() + ((6 - d.getDay() + 7) % 7) + 14)
  return [0, 1, 2, 3].map((w) => {
    const x = new Date(d)
    x.setDate(d.getDate() + 7 * w)
    return { label: shortDay(x), value: ymd(x) }
  })
})
const opensQuick = computed<QuickPick[]>(() => {
  const tomorrow = new Date()
  tomorrow.setDate(tomorrow.getDate() + 1)
  return [
    { label: t('cup.admin.opensNow'), value: '' },
    { label: t('cup.admin.tomorrowAt', { time: '20:00' }), value: `${ymd(tomorrow)}T20:00` },
  ]
})
/** Midnight-ish a few days before the match day. */
function closeBefore(startsOn: string, days: number): string {
  const [y, m, d] = startsOn.split('-').map(Number)
  return `${ymd(new Date(y, m - 1, d - days))}T23:59`
}
function closesQuick(startsOn: string): QuickPick[] {
  if (!startsOn) return []
  return [3, 7, 14].map((n) => ({ label: t('cup.admin.daysBefore', { n }), value: closeBefore(startsOn, n) }))
}

// --- making one ---------------------------------------------------------------
const creating = ref(false)
const createForm = reactive({ name: '', starts_on: '', venue: '', opens_at: '', closes_at: '' })
const createError = ref('')
watch(
  () => createForm.starts_on,
  (day) => {
    if (day && !createForm.closes_at) createForm.closes_at = closeBefore(day, 7)
  },
)
async function create(): Promise<void> {
  createError.value = ''
  if (!createForm.name.trim() || !createForm.starts_on || !createForm.closes_at) {
    createError.value = t('cup.admin.createMissing')
    return
  }
  try {
    const made = await tournamentAdmin.create({
      name: createForm.name.trim(),
      starts_on: createForm.starts_on,
      venue: createForm.venue.trim(),
      opens_at: fromLocalInput(createForm.opens_at),
      closes_at: fromLocalInput(createForm.closes_at) ?? '',
    })
    replace(made)
    pick(made.id)
    creating.value = false
    Object.assign(createForm, { name: '', starts_on: '', venue: '', opens_at: '', closes_at: '' })
  } catch (e) {
    createError.value = apiErrorMessage(e, t('cup.admin.saveFailed'))
  }
}

// --- its settings ------------------------------------------------------------
const form = reactive({
  name: '', starts_on: '', venue: '', opens_at: '', closes_at: '',
  entry_fee: 0, shuttle_fee: 0, coupons_per_set: 6, extra_set_price: 0, coupon_refund_price: 0,
  promptpay_type: 'phone' as Tournament['promptpay_type'], promptpay_id: '', account_name: '',
  min_games: 3, courts: '' as number | '',
})
const saving = ref(false)
const saveError = ref('')
const saved = ref(false)

function fill(x: Tournament | null): void {
  if (!x) return
  Object.assign(form, {
    name: x.name, starts_on: x.starts_on, venue: x.venue,
    opens_at: toLocalInput(x.opens_at), closes_at: toLocalInput(x.closes_at),
    entry_fee: x.entry_fee, shuttle_fee: x.shuttle_fee, coupons_per_set: x.coupons_per_set,
    extra_set_price: x.extra_set_price, coupon_refund_price: x.coupon_refund_price,
    promptpay_type: x.promptpay_type ?? 'phone', promptpay_id: x.promptpay_id ?? '', account_name: x.account_name ?? '',
    min_games: x.min_games, courts: x.courts ?? '',
  })
}
watch(picked, fill, { immediate: true })

const perPlayer = computed(() => Math.ceil((Number(form.entry_fee) + Number(form.shuttle_fee)) / 2))

async function save(): Promise<void> {
  if (!picked.value) return
  saving.value = true
  saveError.value = ''
  saved.value = false
  try {
    const body: Parameters<typeof tournamentAdmin.update>[1] = {
      name: form.name.trim(), starts_on: form.starts_on, venue: form.venue.trim(),
      opens_at: fromLocalInput(form.opens_at), closes_at: fromLocalInput(form.closes_at) ?? picked.value.closes_at,
      coupons_per_set: Number(form.coupons_per_set), extra_set_price: Number(form.extra_set_price),
      coupon_refund_price: Number(form.coupon_refund_price), min_games: Number(form.min_games),
      promptpay_type: form.promptpay_id.trim() ? form.promptpay_type : null,
      promptpay_id: form.promptpay_id.trim() || null, account_name: form.account_name.trim() || null,
    }
    if (form.courts !== '') body.courts = Number(form.courts)
    if (!picked.value.fees_locked) {
      body.entry_fee = Number(form.entry_fee)
      body.shuttle_fee = Number(form.shuttle_fee)
    }
    replace(await tournamentAdmin.update(picked.value.id, body))
    saved.value = true
  } catch (e) {
    saveError.value = apiErrorMessage(e, t('cup.admin.saveFailed'))
  } finally {
    saving.value = false
  }
}

async function setStatus(next: TournamentStatus): Promise<void> {
  if (!picked.value || next === picked.value.status) return
  const ok = await confirm({
    title: t('cup.admin.statusTitle'),
    message: t('cup.admin.statusConfirm', { status: t(`cup.status.${next}`) }),
    confirmLabel: t(`cup.status.${next}`),
  })
  if (!ok) return
  saveError.value = ''
  try {
    replace(await tournamentAdmin.update(picked.value.id, { status: next }))
  } catch (e) {
    saveError.value = apiErrorMessage(e, t('cup.admin.saveFailed'))
  }
}

// --- levels ----------------------------------------------------------------
const levelError = ref('')
const levelDrafts = reactive<Record<string, Level>>({})
watch(
  picked,
  (x) => {
    for (const k of Object.keys(levelDrafts)) delete levelDrafts[k]
    for (const lv of x?.levels ?? []) levelDrafts[lv.id] = { ...lv }
  },
  { immediate: true },
)
const groupsOf = (n: number): number => n / 4
const TEAM_SIZES = [16, 24, 32] as const
const RULE_PRESETS = ['cup.admin.noFlick', 'cup.admin.noRules'] as const
/** One colour per level card, so four levels read as four, at a glance. */
const LEVEL_HUES = ['#f2d16b', '#7dd3fc', '#f472b6', '#a78bfa', '#4ade80', '#fb923c']
const totalTeams = computed(() => (picked.value?.levels ?? []).reduce((n, lv) => n + lv.max_teams, 0))
function eloText(lv: Level): string {
  const lo = lv.min_elo === null || String(lv.min_elo) === '' ? null : lv.min_elo
  const hi = lv.max_elo === null || String(lv.max_elo) === '' ? null : lv.max_elo
  if (lo === null && hi === null) return t('cup.admin.eloAny')
  if (hi === null) return t('cup.admin.eloFrom', { lo })
  if (lo === null) return t('cup.admin.eloBelow', { hi })
  return t('cup.admin.eloRange', { lo, hi: Number(hi) - 1 })
}
function levelChanged(lv: Level): boolean {
  const d = levelDrafts[lv.id]
  const num = (v: unknown): number | null => (v === null || v === '' || v === undefined ? null : Number(v))
  return (
    d.name.trim() !== lv.name ||
    num(d.min_elo) !== lv.min_elo ||
    num(d.max_elo) !== lv.max_elo ||
    Number(d.max_teams) !== lv.max_teams ||
    (Number(d.max_teams) === 24 && d.cut_24 !== lv.cut_24) ||
    d.rules.trim() !== lv.rules
  )
}
function bracketsOf(lv: Level): string {
  if (lv.max_teams === 24) return lv.cut_24 ? t('cup.admin.br24cut') : t('cup.admin.br24')
  return t('cup.admin.brEven', { n: lv.max_teams / 2 })
}
function matchesOf(lv: Level): number {
  const group = groupsOf(lv.max_teams) * 6
  if (lv.max_teams === 24) return group + (lv.cut_24 ? 7 + 7 : 15 + 7)
  return group + 2 * (lv.max_teams / 2 - 1)
}

async function saveLevel(id: string): Promise<void> {
  if (!picked.value) return
  const d = levelDrafts[id]
  levelError.value = ''
  try {
    replace(
      await tournamentAdmin.updateLevel(picked.value.id, id, {
        name: d.name.trim(),
        min_elo: d.min_elo === null || String(d.min_elo) === '' ? null : Number(d.min_elo),
        max_elo: d.max_elo === null || String(d.max_elo) === '' ? null : Number(d.max_elo),
        max_teams: Number(d.max_teams) as Level['max_teams'],
        cut_24: Number(d.max_teams) === 24 ? d.cut_24 : false,
        rules: d.rules.trim(),
      }),
    )
  } catch (e) {
    levelError.value = apiErrorMessage(e, t('cup.admin.saveFailed'))
  }
}

/** Fewer levels: one with nobody in it goes. Its players can still enter a
 *  level above — unless it was the top one, which leaves the strongest out. */
async function removeLevel(lv: Level): Promise<void> {
  if (!picked.value) return
  const ok = await confirm({
    title: t('cup.admin.removeLevelTitle', { name: lv.name }),
    message: lv.max_elo === null ? t('cup.admin.removeTopWarn', { elo: lv.min_elo ?? 0 }) : t('cup.admin.removeWarn'),
    confirmLabel: t('cup.admin.removeLevel'),
    danger: true,
  })
  if (!ok) return
  levelError.value = ''
  try {
    replace(await tournamentAdmin.deleteLevel(picked.value.id, lv.id))
  } catch (e) {
    levelError.value = apiErrorMessage(e, t('cup.admin.saveFailed'))
  }
}

async function addLevel(): Promise<void> {
  if (!picked.value) return
  levelError.value = ''
  try {
    replace(
      await tournamentAdmin.addLevel(picked.value.id, {
        name: t('cup.admin.newLevelName'),
        min_elo: null,
        max_elo: null,
        max_teams: 16,
        cut_24: false,
        rules: '',
      }),
    )
  } catch (e) {
    levelError.value = apiErrorMessage(e, t('cup.admin.saveFailed'))
  }
}

// --- trying it out ------------------------------------------------------------
const deleting = ref(false)
const deleteName = ref('')
const deleteError = ref('')
async function removeTournament(): Promise<void> {
  if (!picked.value || deleteName.value.trim() !== picked.value.name) return
  deleteError.value = ''
  try {
    await tournamentAdmin.remove(picked.value.id)
    deleting.value = false
    deleteName.value = ''
    await load()
  } catch (e) {
    deleteError.value = apiErrorMessage(e, t('cup.admin.saveFailed'))
  }
}

onMounted(load)
</script>

<style scoped>
.level-card {
  background: linear-gradient(160deg, color-mix(in srgb, var(--hue) 9%, transparent), rgb(0 0 0 / 0.25) 55%);
  border-top: 2px solid color-mix(in srgb, var(--hue) 55%, transparent);
}
</style>

<template>
  <AdminNav />
  <main class="mx-auto max-w-3xl px-4 py-6">
    <h1 class="sr-only">{{ t('admin.nav.tEvent') }}</h1>

    <p v-if="loading && !all.length" class="text-white/60">{{ t('common.loading') }}</p>
    <p v-if="problem" class="text-status-error">{{ problem }}</p>

    <!-- which tournament -->
    <div class="flex flex-wrap items-center gap-2">
      <select
        v-if="all.length"
        :value="picked?.id"
        :aria-label="t('cup.admin.pick')"
        class="min-h-11 flex-1 rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-sm text-white"
        @change="pick(($event.target as HTMLSelectElement).value)"
      >
        <option v-for="x in all" :key="x.id" :value="x.id">{{ x.name }} · {{ x.starts_on }} · {{ t(`cup.status.${x.status}`) }}</option>
      </select>
      <button type="button" class="tap rounded-full border border-brand-pink/40 px-4 text-sm font-semibold text-brand-pink" @click="creating = !creating">
        + {{ t('cup.admin.new') }}
      </button>
    </div>

    <section v-if="creating || (!loading && !all.length)" class="hud-panel mt-4 border border-brand-pink/20 bg-brand-surface p-4">
      <h2 class="text-sm font-semibold text-white/70">{{ t('cup.admin.new') }}</h2>
      <div class="mt-3 grid grid-cols-2 gap-2.5">
        <label class="col-span-2 flex flex-col gap-1 text-xs text-white/50">{{ t('cup.admin.name') }}<input v-model="createForm.name" :class="INPUT" placeholder="NIDDEAW CUP 2026" /></label>
        <div class="col-span-2 flex flex-col gap-1 text-xs text-white/50">{{ t('cup.admin.startsOn') }}<DatePick v-model="createForm.starts_on" :placeholder="t('cup.admin.pickDay')" :quick="startQuick" :aria-label="t('cup.admin.startsOn')" /></div>
        <label class="col-span-2 flex flex-col gap-1 text-xs text-white/50">{{ t('cup.admin.venue') }}<input v-model="createForm.venue" :class="INPUT" class="min-h-11" /></label>
        <div class="col-span-2 flex flex-col gap-1 text-xs text-white/50">{{ t('cup.admin.opensAt') }}<DatePick v-model="createForm.opens_at" with-time :placeholder="t('cup.admin.opensNowLong')" :quick="opensQuick" :aria-label="t('cup.admin.opensAt')" /></div>
        <div class="col-span-2 flex flex-col gap-1 text-xs text-white/50">{{ t('cup.admin.closesAt') }}<DatePick v-model="createForm.closes_at" with-time default-time="23:59" :placeholder="t('cup.admin.pickDay')" :quick="closesQuick(createForm.starts_on)" :aria-label="t('cup.admin.closesAt')" /></div>
      </div>
      <p class="mt-2 text-xs text-white/50">{{ t('cup.admin.newHint') }}</p>
      <p v-if="createError" class="mt-2 text-sm text-status-error" role="alert">{{ createError }}</p>
      <button type="button" class="tap mt-3 rounded-full bg-brand-pink px-5 text-sm font-semibold text-brand-black" @click="create">{{ t('cup.admin.create') }}</button>
    </section>

    <template v-if="picked">
      <!-- where it stands -->
      <section class="hud-panel mt-4 border border-brand-pink/15 bg-brand-surface p-4">
        <h2 class="text-sm font-semibold text-white/70">{{ t('cup.admin.status') }}</h2>
        <div class="mt-2 flex flex-wrap gap-1.5">
          <button
            v-for="s in STATUSES"
            :key="s"
            type="button"
            class="tap rounded-full px-3 text-xs font-semibold"
            :class="picked.status === s ? 'bg-brand-pink text-brand-black' : 'border border-white/20 text-white/70'"
            :aria-pressed="picked.status === s"
            @click="setStatus(s)"
          >
            {{ t(`cup.status.${s}`) }}
          </button>
        </div>
        <p class="mt-2 text-xs text-white/50">{{ t(`cup.admin.statusHint.${picked.status}`) }}</p>
        <p v-if="!picked.promptpay_id" class="mt-2 text-xs text-[#ffd34d]">{{ t('cup.admin.needAccount') }}</p>
      </section>

      <!-- the event -->
      <section class="hud-panel mt-4 border border-brand-pink/15 bg-brand-surface p-4">
        <h2 class="text-sm font-semibold text-white/70">{{ t('cup.admin.event') }}</h2>
        <div class="mt-3 grid grid-cols-2 gap-2.5">
          <label class="col-span-2 flex flex-col gap-1 text-xs text-white/50">{{ t('cup.admin.name') }}<input v-model="form.name" :class="INPUT" /></label>
          <div class="col-span-2 flex flex-col gap-1 text-xs text-white/50">{{ t('cup.admin.startsOn') }}<DatePick v-model="form.starts_on" :placeholder="t('cup.admin.pickDay')" :quick="startQuick" :aria-label="t('cup.admin.startsOn')" /></div>
          <label class="col-span-2 flex flex-col gap-1 text-xs text-white/50">{{ t('cup.admin.venue') }}<input v-model="form.venue" :class="INPUT" class="min-h-11" /></label>
          <div class="col-span-2 flex flex-col gap-1 text-xs text-white/50">{{ t('cup.admin.opensAt') }}<DatePick v-model="form.opens_at" with-time :placeholder="t('cup.admin.opensNowLong')" :quick="opensQuick" :aria-label="t('cup.admin.opensAt')" /></div>
          <div class="col-span-2 flex flex-col gap-1 text-xs text-white/50">{{ t('cup.admin.closesAt') }}<DatePick v-model="form.closes_at" with-time default-time="23:59" :placeholder="t('cup.admin.pickDay')" :quick="closesQuick(form.starts_on)" :aria-label="t('cup.admin.closesAt')" /></div>
          <label class="flex flex-col gap-1 text-xs text-white/50">{{ t('cup.admin.minGames') }}<input v-model.number="form.min_games" type="number" min="0" max="100" :class="INPUT" /></label>
          <label class="flex flex-col gap-1 text-xs text-white/50">{{ t('cup.admin.courts') }}<input v-model.number="form.courts" type="number" min="1" max="60" :class="INPUT" /></label>
        </div>

        <h3 class="mt-5 text-xs font-semibold tracking-wide text-white/60">{{ t('cup.admin.prices') }}</h3>
        <div class="mt-2 grid grid-cols-2 gap-2.5">
          <label class="flex flex-col gap-1 text-xs text-white/50">{{ t('cup.admin.entryFee') }}<input v-model.number="form.entry_fee" type="number" min="0" :disabled="picked.fees_locked" :class="INPUT" /></label>
          <label class="flex flex-col gap-1 text-xs text-white/50">{{ t('cup.admin.shuttleFee') }}<input v-model.number="form.shuttle_fee" type="number" min="0" :disabled="picked.fees_locked" :class="INPUT" /></label>
          <p class="col-span-2 text-xs text-white/60">
            {{ t('cup.admin.perPlayer', { amount: money(perPlayer) }) }}
            <span v-if="picked.fees_locked" class="text-[#ffd34d]"> · {{ t('cup.admin.feesLocked') }}</span>
          </p>
          <label class="flex flex-col gap-1 text-xs text-white/50">{{ t('cup.admin.couponsPerSet') }}<input v-model.number="form.coupons_per_set" type="number" min="1" max="50" :class="INPUT" /></label>
          <label class="flex flex-col gap-1 text-xs text-white/50">{{ t('cup.admin.extraSetPrice') }}<input v-model.number="form.extra_set_price" type="number" min="0" :class="INPUT" /></label>
          <label class="flex flex-col gap-1 text-xs text-white/50">{{ t('cup.admin.couponRefund') }}<input v-model.number="form.coupon_refund_price" type="number" min="0" :class="INPUT" /></label>
        </div>

        <h3 class="mt-5 text-xs font-semibold tracking-wide text-white/60">{{ t('cup.admin.account') }}</h3>
        <p class="mt-1 text-xs text-white/50">{{ t('cup.admin.accountHint') }}</p>
        <div class="mt-2 grid grid-cols-2 gap-2.5">
          <label class="flex flex-col gap-1 text-xs text-white/50">
            {{ t('cup.admin.promptpayType') }}
            <select v-model="form.promptpay_type" :class="INPUT">
              <option value="phone">{{ t('cup.admin.ppPhone') }}</option>
              <option value="national_id">{{ t('cup.admin.ppId') }}</option>
              <option value="ewallet">e-Wallet</option>
            </select>
          </label>
          <label class="flex flex-col gap-1 text-xs text-white/50">PromptPay<input v-model="form.promptpay_id" inputmode="numeric" :class="INPUT" /></label>
          <label class="col-span-2 flex flex-col gap-1 text-xs text-white/50">{{ t('cup.admin.accountName') }}<input v-model="form.account_name" :class="INPUT" /></label>
        </div>

        <p v-if="saveError" class="mt-3 text-sm text-status-error" role="alert">{{ saveError }}</p>
        <p v-if="saved" class="mt-3 text-sm text-status-success" role="status">{{ t('cup.admin.saved') }}</p>
        <button type="button" :disabled="saving" class="tap mt-3 rounded-full bg-brand-pink px-5 text-sm font-semibold text-brand-black disabled:opacity-50" @click="save">
          {{ saving ? t('cup.admin.saving') : t('cup.admin.save') }}
        </button>
      </section>

      <!-- levels -->
      <section class="hud-panel mt-4 border border-brand-pink/15 bg-brand-surface p-4">
        <div class="flex flex-wrap items-baseline justify-between gap-2">
          <h2 class="text-sm font-semibold text-white/70">{{ t('cup.admin.levels') }}</h2>
          <span class="text-xs text-white/50">{{ t('cup.admin.levelsSummary', { n: picked.levels.length, teams: totalTeams }) }}</span>
        </div>
        <p class="mt-1 text-xs text-white/45">{{ t('cup.admin.levelsHint') }}</p>
        <p v-if="levelError" class="mt-2 text-sm text-status-error" role="alert">{{ levelError }}</p>
        <ul class="mt-3 grid gap-3 lg:grid-cols-2">
          <li v-for="(lv, i) in picked.levels" :key="lv.id" class="level-card rounded-2xl border border-white/10 p-3.5" :style="{ '--hue': LEVEL_HUES[i % LEVEL_HUES.length] }">
            <template v-if="levelDrafts[lv.id]">
              <div class="flex items-start gap-2">
                <span class="mt-1.5 h-3 w-3 shrink-0 rounded-full" :style="{ background: 'var(--hue)' }" aria-hidden="true" />
                <div class="min-w-0 flex-1">
                  <input
                    v-model="levelDrafts[lv.id].name"
                    :aria-label="t('cup.admin.levelName')"
                    class="w-full rounded-md border border-transparent bg-transparent px-1 py-0.5 font-display text-lg font-bold text-white hover:border-white/15 focus:border-brand-pink/50 focus:outline-none"
                  />
                  <p class="px-1 text-xs text-white/55">{{ eloText(levelDrafts[lv.id]) }} · {{ t('cup.admin.teamsUnit', { n: levelDrafts[lv.id].max_teams }) }}</p>
                </div>
                <button
                  v-if="picked.levels.length > 1"
                  type="button"
                  class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-white/45 hover:bg-status-error/15 hover:text-status-error"
                  :aria-label="t('cup.admin.removeLevelTitle', { name: lv.name })"
                  @click="removeLevel(lv)"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" class="h-[18px] w-[18px]" aria-hidden="true"><path d="M4 7h16M10 11v6M14 11v6M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2l1-12M9 7V4h6v3" /></svg>
                </button>
              </div>

              <div class="mt-3 grid grid-cols-2 gap-2">
                <label class="flex flex-col gap-1 text-xs text-white/50">{{ t('cup.admin.minElo') }}<input v-model.number="levelDrafts[lv.id].min_elo" type="number" inputmode="numeric" :placeholder="t('cup.admin.noFloor')" :class="INPUT" class="min-h-10" /></label>
                <label class="flex flex-col gap-1 text-xs text-white/50">{{ t('cup.admin.maxElo') }}<input v-model.number="levelDrafts[lv.id].max_elo" type="number" inputmode="numeric" :placeholder="t('cup.admin.noCeiling')" :class="INPUT" class="min-h-10" /></label>
              </div>

              <p class="mt-3 text-xs text-white/50">{{ t('cup.admin.maxTeams') }}</p>
              <div class="mt-1 grid grid-cols-3 gap-1 rounded-full bg-black/30 p-1" role="radiogroup" :aria-label="t('cup.admin.maxTeams')">
                <button
                  v-for="n in TEAM_SIZES"
                  :key="n"
                  type="button"
                  role="radio"
                  :aria-checked="levelDrafts[lv.id].max_teams === n"
                  class="min-h-9 rounded-full text-sm font-semibold transition-colors"
                  :class="levelDrafts[lv.id].max_teams === n ? 'bg-brand-pink text-brand-black' : 'text-white/65 hover:text-white'"
                  @click="levelDrafts[lv.id].max_teams = n"
                >
                  {{ n }}
                </button>
              </div>
              <div v-if="levelDrafts[lv.id].max_teams === 24" class="mt-2 flex flex-wrap gap-1.5">
                <button
                  v-for="cut in [false, true]"
                  :key="String(cut)"
                  type="button"
                  class="min-h-9 rounded-full border px-3 text-xs"
                  :class="levelDrafts[lv.id].cut_24 === cut ? 'border-brand-pink bg-brand-pink/20 font-semibold text-white' : 'border-white/15 text-white/65'"
                  :aria-pressed="levelDrafts[lv.id].cut_24 === cut"
                  @click="levelDrafts[lv.id].cut_24 = cut"
                >
                  {{ cut ? t('cup.admin.br24cut') : t('cup.admin.br24') }}
                </button>
              </div>

              <p class="mt-3 text-xs text-white/50">{{ t('cup.admin.rules') }}</p>
              <div class="mt-1 flex flex-wrap items-center gap-1.5">
                <button
                  v-for="r in RULE_PRESETS"
                  :key="r"
                  type="button"
                  class="min-h-9 rounded-full border px-3 text-xs"
                  :class="levelDrafts[lv.id].rules === t(r) || (r === 'cup.admin.noRules' && !levelDrafts[lv.id].rules) ? 'border-brand-pink bg-brand-pink/20 font-semibold text-white' : 'border-white/15 text-white/65'"
                  @click="levelDrafts[lv.id].rules = r === 'cup.admin.noRules' ? '' : t(r)"
                >
                  {{ t(r) }}
                </button>
              </div>
              <input v-model="levelDrafts[lv.id].rules" :aria-label="t('cup.admin.rules')" :class="INPUT" class="mt-1.5 min-h-10" />

              <div class="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-white/8 pt-3">
                <p class="text-xs text-white/55">
                  {{ t('cup.admin.shape', { groups: groupsOf(levelDrafts[lv.id].max_teams), matches: matchesOf(levelDrafts[lv.id]) }) }}<br />{{ bracketsOf(levelDrafts[lv.id]) }}
                </p>
                <button
                  v-if="levelChanged(lv)"
                  type="button"
                  class="tap rounded-full bg-brand-pink px-4 text-xs font-semibold text-brand-black"
                  @click="saveLevel(lv.id)"
                >
                  {{ t('cup.admin.saveLevel') }}
                </button>
                <span v-else class="text-xs text-white/40">✓ {{ t('cup.admin.saved') }}</span>
              </div>
            </template>
          </li>
          <li>
            <button
              type="button"
              class="flex h-full min-h-24 w-full flex-col items-center justify-center gap-1 rounded-2xl border border-dashed border-white/20 text-sm text-white/60 hover:border-brand-pink/50 hover:text-white"
              @click="addLevel"
            >
              <span class="text-2xl leading-none">+</span>
              {{ t('cup.admin.addLevel') }}
            </button>
          </li>
        </ul>
      </section>

      <!-- trying it out: the whole tournament can go, before it is played -->
      <section v-if="picked.status !== 'running' && picked.status !== 'done'" class="hud-panel mt-4 border border-status-error/25 bg-brand-surface p-4">
        <h2 class="text-sm font-semibold text-white/70">{{ t('cup.admin.deleteTitle') }}</h2>
        <p class="mt-1 text-xs text-white/50">{{ t('cup.admin.deleteHint') }}</p>
        <button v-if="!deleting" type="button" class="tap mt-3 rounded-full border border-status-error/50 px-4 text-xs font-semibold text-status-error" @click="deleting = true">
          {{ t('cup.admin.deleteStart') }}
        </button>
        <div v-else class="mt-3 flex flex-col gap-2">
          <label class="flex flex-col gap-1 text-xs text-white/60">
            {{ t('cup.admin.deleteType', { name: picked.name }) }}
            <input v-model="deleteName" :class="INPUT" class="min-h-10" :placeholder="picked.name" autocomplete="off" />
          </label>
          <p v-if="deleteError" class="text-sm text-status-error" role="alert">{{ deleteError }}</p>
          <div class="flex gap-2">
            <button
              type="button"
              class="tap rounded-full bg-status-error px-4 text-xs font-semibold text-white disabled:opacity-40"
              :disabled="deleteName.trim() !== picked.name"
              @click="removeTournament"
            >
              {{ t('cup.admin.deleteConfirm') }}
            </button>
            <button type="button" class="tap rounded-full border border-white/15 px-4 text-xs text-white/70" @click="deleting = false; deleteName = ''">
              {{ t('common.cancel') }}
            </button>
          </div>
        </div>
      </section>
    </template>
  </main>
</template>
