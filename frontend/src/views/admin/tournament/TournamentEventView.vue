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

onMounted(load)
</script>

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
        <h2 class="text-sm font-semibold text-white/70">{{ t('cup.admin.levels') }}</h2>
        <p class="mt-1 text-xs text-white/50">{{ t('cup.admin.levelsHint') }}</p>
        <p v-if="levelError" class="mt-2 text-sm text-status-error" role="alert">{{ levelError }}</p>
        <ul class="mt-3 space-y-3">
          <li v-for="lv in picked.levels" :key="lv.id" class="rounded-xl border border-white/10 bg-brand-black/40 p-3">
            <template v-if="levelDrafts[lv.id]">
              <div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
                <label class="col-span-2 flex flex-col gap-1 text-xs text-white/50">{{ t('cup.admin.levelName') }}<input v-model="levelDrafts[lv.id].name" :class="INPUT" /></label>
                <label class="flex flex-col gap-1 text-xs text-white/50">{{ t('cup.admin.minElo') }}<input v-model.number="levelDrafts[lv.id].min_elo" type="number" :placeholder="t('cup.admin.noFloor')" :class="INPUT" /></label>
                <label class="flex flex-col gap-1 text-xs text-white/50">{{ t('cup.admin.maxElo') }}<input v-model.number="levelDrafts[lv.id].max_elo" type="number" :placeholder="t('cup.admin.noCeiling')" :class="INPUT" /></label>
                <label class="flex flex-col gap-1 text-xs text-white/50">
                  {{ t('cup.admin.maxTeams') }}
                  <select v-model.number="levelDrafts[lv.id].max_teams" :class="INPUT">
                    <option :value="16">16</option>
                    <option :value="24">24</option>
                    <option :value="32">32</option>
                  </select>
                </label>
                <label v-if="levelDrafts[lv.id].max_teams === 24" class="col-span-1 flex flex-col gap-1 text-xs text-white/50 sm:col-span-3">
                  {{ t('cup.admin.format24') }}
                  <select v-model="levelDrafts[lv.id].cut_24" :class="INPUT">
                    <option :value="false">{{ t('cup.admin.br24') }}</option>
                    <option :value="true">{{ t('cup.admin.br24cut') }}</option>
                  </select>
                </label>
                <label class="col-span-2 flex flex-col gap-1 text-xs text-white/50 sm:col-span-4">{{ t('cup.admin.rules') }}<input v-model="levelDrafts[lv.id].rules" :class="INPUT" /></label>
              </div>
              <p class="mt-2 text-xs text-white/55">
                {{ t('cup.admin.shape', { groups: groupsOf(levelDrafts[lv.id].max_teams), matches: matchesOf(levelDrafts[lv.id]) }) }} · {{ bracketsOf(levelDrafts[lv.id]) }}
              </p>
              <button type="button" class="tap mt-2 rounded-full border border-brand-pink/40 px-4 text-xs font-semibold text-brand-pink" @click="saveLevel(lv.id)">
                {{ t('cup.admin.saveLevel') }}
              </button>
            </template>
          </li>
        </ul>
      </section>
    </template>
  </main>
</template>
