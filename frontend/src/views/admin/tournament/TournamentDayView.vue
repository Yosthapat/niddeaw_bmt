<script setup lang="ts">
/**
 * The day itself, for the tournament admins at the desk.
 *
 * Courts: every court, free or playing. A free court offers the next match
 * that can go on now (teams known, not on another court, rested); call it,
 * or pick another. A court in play: call again, enter the result from the
 * signed score sheet (and the shuttles it used), give a walkover, or take
 * the match off. Results: each level's matches and group tables, where a
 * result can be corrected until a match it decides is called. Coupons:
 * every team's shuttle coupons, the lowest first; sell a set or buy back
 * what's left. Refreshes itself every 15 seconds.
 */
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import AdminNav from '@/components/layout/AdminNav.vue'
import LevelTabs from '@/components/admin/LevelTabs.vue'
import CupMatchCard from '@/components/cup/CupMatchCard.vue'
import CupTeamLine from '@/components/cup/CupTeamLine.vue'
import { tournamentAdmin, type CupMatch, type GameDay, type PaidVia, type TeamCoupons } from '@/api/tournament'
import { apiErrorMessage } from '@/api/errors'
import { useTournamentPick } from '@/composables/useTournamentPick'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { usePolling } from '@/composables/usePolling'
import { sideLabel } from '@/utils/cupMatch'
import { money } from '@/utils/format'

const { t } = useI18n()
const { confirm } = useConfirmDialog()
const { all, picked, load, pick } = useTournamentPick()

const INPUT = 'w-full rounded border border-brand-pink-dark/40 bg-brand-black px-2 py-1.5 text-sm text-white'
const day = ref<GameDay | null>(null)
const problem = ref('')
const busy = ref<string | null>(null)
type Tab = 'courts' | 'results' | 'coupons'
const tab = ref<Tab>('courts')

async function refresh(): Promise<void> {
  if (!all.value.length) await load()
  if (!picked.value || editing.value || selling.value || walkingOver.value) return // don't move the ground under a form
  try {
    day.value = await tournamentAdmin.day(picked.value.id)
  } catch (e) {
    problem.value = apiErrorMessage(e, t('cup.admin.loadFailed'))
  }
}
usePolling(refresh, 15000)
watch(() => picked.value?.id, () => void refresh())

async function run(key: string, job: () => Promise<GameDay>): Promise<boolean> {
  busy.value = key
  problem.value = ''
  try {
    day.value = await job()
    return true
  } catch (e) {
    problem.value = apiErrorMessage(e, t('cup.admin.saveFailed'))
    return false
  } finally {
    busy.value = null
  }
}

// --- courts -------------------------------------------------------------------
const courts = computed(() => Array.from({ length: day.value?.courts ?? 0 }, (_, i) => i + 1))
const onCourt = (n: number): CupMatch | undefined => day.value?.matches.find((m) => m.status === 'on_court' && m.court === n)
/** what each free court is offered: the ready matches in order, one per court */
const offers = computed(() => {
  const out: Record<number, CupMatch | undefined> = {}
  const queue = (day.value?.ready ?? []).map((id) => day.value?.matches.find((m) => m.id === id)).filter((m): m is CupMatch => !!m)
  const taken = new Set<string>()
  for (const n of courts.value) {
    if (onCourt(n)) continue
    const next = queue.find((m) => !taken.has(m.a.team_id ?? '') && !taken.has(m.b.team_id ?? ''))
    if (next) {
      out[n] = next
      queue.splice(queue.indexOf(next), 1)
      taken.add(next.a.team_id ?? '')
      taken.add(next.b.team_id ?? '')
    }
  }
  return out
})
const callable = computed(() => (day.value?.matches ?? []).filter((m) => m.status === 'scheduled' && m.a.team_id && m.b.team_id))
const choosing = ref<number | null>(null)
const chosen = ref('')
function minutesSince(iso: string | null): number {
  return iso ? Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000)) : 0
}
async function call(m: CupMatch, court: number): Promise<void> {
  if (await run(m.id, () => tournamentAdmin.call(m.id, court))) choosing.value = null
}
// a walkover: pick who turned up, in its own small sheet with a real "cancel"
const walkingOver = ref<CupMatch | null>(null)
function walkover(m: CupMatch): void {
  walkingOver.value = m
}
async function giveWalkover(winner: 'a' | 'b'): Promise<void> {
  const m = walkingOver.value
  if (!m) return
  if (await run(m.id, () => tournamentAdmin.result(m.id, { walkover_winner: winner }))) walkingOver.value = null
}
async function uncall(m: CupMatch): Promise<void> {
  const ok = await confirm({ title: t('cup.day.uncallTitle'), message: t('cup.day.uncallBody', { n: m.match_no }), confirmLabel: t('cup.day.uncall') })
  if (ok) await run(m.id, () => tournamentAdmin.uncall(m.id))
}

// --- entering a result ------------------------------------------------------------
const editing = ref<CupMatch | null>(null)
const form = reactive({ sets: [] as { a: number | ''; b: number | '' }[], shuttles: 2 })
function openResult(m: CupMatch): void {
  editing.value = m
  const n = m.stage === 'group' ? 2 : 3
  form.sets = Array.from({ length: n }, (_, i) => ({ a: m.sets?.[i]?.[0] ?? '', b: m.sets?.[i]?.[1] ?? '' }))
  form.shuttles = m.shuttles ?? 2
}
async function saveResult(): Promise<void> {
  const m = editing.value
  if (!m) return
  const sets = form.sets.filter((s) => s.a !== '' || s.b !== '').map((s) => [Number(s.a), Number(s.b)])
  if (await run(m.id, () => tournamentAdmin.result(m.id, { sets, shuttles: Number(form.shuttles) }))) editing.value = null
}

// --- results by level ---------------------------------------------------------
const levelPick = ref('')
const levels = computed(() => {
  const seen = new Map<string, string>()
  for (const m of day.value?.matches ?? []) seen.set(m.level_id, m.level_name)
  return [...seen].map(([id, name]) => {
    const mine = (day.value?.matches ?? []).filter((m) => m.level_id === id)
    return { id, name, badge: `${mine.filter((m) => m.status === 'done').length}/${mine.length}` }
  })
})
const activeLevel = computed(() => levels.value.find((l) => l.id === levelPick.value)?.id ?? levels.value[0]?.id ?? '')
const levelMatches = computed(() => (day.value?.matches ?? []).filter((m) => m.level_id === activeLevel.value))

// --- coupons -----------------------------------------------------------------
const selling = ref<{ team: TeamCoupons; kind: 'sell' | 'return' } | null>(null)
const sale = reactive({ quantity: 1, via: 'cash' as PaidVia, slip: null as File | null })
function openSale(team: TeamCoupons, kind: 'sell' | 'return'): void {
  selling.value = { team, kind }
  Object.assign(sale, { quantity: kind === 'sell' ? 1 : team.left, via: 'cash', slip: null })
}
const saleAmount = computed(() =>
  selling.value?.kind === 'sell' ? sale.quantity * (day.value?.extra_set_price ?? 0) : sale.quantity * (day.value?.coupon_refund_price ?? 0),
)
async function saveSale(): Promise<void> {
  const s = selling.value
  if (!s) return
  const job =
    s.kind === 'sell'
      ? () => tournamentAdmin.sellCoupons(s.team.team_id, sale.quantity, sale.via, sale.slip)
      : () => tournamentAdmin.returnCoupons(s.team.team_id, sale.quantity, sale.via, sale.slip)
  if (await run(s.team.team_id, job)) selling.value = null
}
</script>

<template>
  <AdminNav />
  <main class="mx-auto max-w-3xl px-4 py-6">
    <h1 class="sr-only">{{ t('admin.nav.tDay') }}</h1>

    <select
      v-if="all.length > 1"
      :value="picked?.id"
      :aria-label="t('cup.admin.pick')"
      class="mb-3 min-h-11 w-full rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-sm text-white"
      @change="pick(($event.target as HTMLSelectElement).value)"
    >
      <option v-for="x in all" :key="x.id" :value="x.id">{{ x.name }} · {{ x.starts_on }}</option>
    </select>

    <p v-if="day && !day.published" class="hud-panel border border-[#ffd34d]/40 bg-brand-surface p-4 text-sm text-[#ffd34d]">{{ t('cup.day.notPublished') }}</p>
    <p v-if="problem" class="mb-3 text-sm text-status-error" role="alert">{{ problem }}</p>

    <template v-if="day && day.published">
      <div class="grid grid-cols-3 gap-1 rounded-full border border-white/10 p-1" role="tablist">
        <button
          v-for="x in (['courts', 'results', 'coupons'] as Tab[])"
          :key="x"
          type="button"
          role="tab"
          class="min-h-11 rounded-full text-sm font-semibold"
          :class="tab === x ? 'bg-brand-pink text-brand-black' : 'text-white/70'"
          :aria-selected="tab === x"
          @click="tab = x"
        >
          {{ t(`cup.day.tab.${x}`) }}
        </button>
      </div>

      <!-- courts -->
      <section v-if="tab === 'courts'" class="mt-4 grid gap-3 sm:grid-cols-2">
        <div v-for="n in courts" :key="n" class="hud-panel border bg-brand-surface p-3" :class="onCourt(n) ? 'border-[#7ff0b4]/40' : 'border-brand-pink/15'">
          <p class="mb-2 flex items-baseline gap-2">
            <b class="font-display text-lg">{{ t('cup.day.court', { n }) }}</b>
            <span v-if="onCourt(n)" class="text-xs text-white/55">
              {{ t('cup.day.calledAgo', { m: minutesSince(onCourt(n)!.called_at), k: onCourt(n)!.call_count }) }}
            </span>
            <span v-else class="text-xs text-status-success">{{ t('cup.day.free') }}</span>
          </p>

          <template v-if="onCourt(n)">
            <CupMatchCard :match="onCourt(n)!" show-level />
            <div class="mt-2 flex flex-wrap gap-1.5">
              <button type="button" class="tap rounded-full bg-brand-pink px-4 text-xs font-semibold text-brand-black" @click="openResult(onCourt(n)!)">{{ t('cup.day.enterResult') }}</button>
              <button type="button" :disabled="busy === onCourt(n)!.id" class="tap rounded-full border border-white/25 px-3 text-xs text-white/75" @click="run(onCourt(n)!.id, () => tournamentAdmin.callAgain(onCourt(n)!.id))">
                {{ t('cup.day.callAgain') }}
              </button>
              <button type="button" class="tap rounded-full border border-status-error/40 px-3 text-xs text-status-error" @click="walkover(onCourt(n)!)">{{ t('cup.day.walkover') }}</button>
              <button type="button" class="tap rounded-full border border-white/15 px-3 text-xs text-white/50" @click="uncall(onCourt(n)!)">{{ t('cup.day.uncall') }}</button>
            </div>
          </template>

          <template v-else>
            <template v-if="offers[n] && choosing !== n">
              <p class="mb-1 text-xs text-white/55">{{ t('cup.day.next') }}</p>
              <CupMatchCard :match="offers[n]!" show-level />
              <div class="mt-2 flex flex-wrap gap-1.5">
                <button type="button" :disabled="busy === offers[n]!.id" class="tap rounded-full bg-status-success px-4 text-xs font-semibold text-brand-black" @click="call(offers[n]!, n)">
                  {{ t('cup.day.callTo', { no: offers[n]!.match_no, n }) }}
                </button>
                <button type="button" class="tap rounded-full border border-white/20 px-3 text-xs text-white/65" @click="choosing = n; chosen = ''">{{ t('cup.day.pickOther') }}</button>
              </div>
            </template>
            <template v-else>
              <p v-if="!offers[n]" class="text-xs text-white/50">{{ t('cup.day.nothingReady') }}</p>
              <div class="mt-2 flex gap-1.5">
                <select v-model="chosen" :class="INPUT" :aria-label="t('cup.day.pickOther')">
                  <option value="">{{ t('cup.day.pickOther') }}</option>
                  <option v-for="m in callable" :key="m.id" :value="m.id">#{{ m.match_no }} · {{ sideLabel(m.a, t) }} vs {{ sideLabel(m.b, t) }}</option>
                </select>
                <button type="button" :disabled="!chosen" class="tap shrink-0 rounded-full bg-status-success px-4 text-xs font-semibold text-brand-black disabled:opacity-40" @click="call(callable.find((m) => m.id === chosen)!, n)">
                  {{ t('cup.day.call') }}
                </button>
              </div>
              <button v-if="choosing === n" type="button" class="mt-1 text-xs text-white/50 underline" @click="choosing = null">{{ t('common.cancel') }}</button>
            </template>
          </template>
        </div>
      </section>

      <!-- results by level -->
      <template v-if="tab === 'results'">
        <LevelTabs :levels="levels" :model-value="activeLevel" :label="t('cup.level')" @update:model-value="levelPick = $event" />
        <p class="mt-2 text-xs text-white/50">{{ t('cup.day.fixHint') }}</p>
        <div class="mt-2 flex flex-col gap-1.5">
          <CupMatchCard v-for="m in levelMatches" :key="m.id" :match="m">
            <button
              v-if="m.status !== 'scheduled' || (m.a.team_id && m.b.team_id)"
              type="button"
              class="mt-2 text-xs text-brand-pink underline"
              @click="m.status === 'scheduled' ? walkover(m) : openResult(m)"
            >
              {{ m.status === 'done' ? t('cup.day.fix') : m.status === 'on_court' ? t('cup.day.enterResult') : t('cup.day.walkover') }}
            </button>
          </CupMatchCard>
        </div>
      </template>

      <!-- coupons -->
      <template v-if="tab === 'coupons'">
        <p class="mt-4 text-xs text-white/55">
          {{ t('cup.day.couponRule', { n: day.coupons_per_set, price: money(day.extra_set_price), back: money(day.coupon_refund_price) }) }}
        </p>
        <ul class="mt-3 space-y-2">
          <li v-for="c in day.coupons" :key="c.team_id" class="hud-panel border bg-brand-surface p-3" :class="c.left < 2 && c.next_match_no ? 'border-[#ffd34d]/50' : 'border-brand-pink/15'">
            <div class="flex items-center gap-2">
              <CupTeamLine class="min-w-0 flex-1" :name="c.team_name" :players="c.players" />
              <span class="shrink-0 text-right">
                <b class="block font-display text-lg" :class="c.left < 2 ? 'text-[#ffd34d]' : ''">{{ c.left }}</b>
                <span class="text-[11px] text-white/50">{{ t('cup.day.left') }}</span>
              </span>
            </div>
            <p class="mt-1 text-xs text-white/55">
              {{ c.level_name }} · {{ t('cup.day.couponLine', { sets: c.sets, given: c.given, used: c.used, returned: c.returned }) }}
              <template v-if="c.next_match_no"> · {{ t('cup.day.nextMatch', { n: c.next_match_no }) }}</template>
            </p>
            <p v-if="c.left < 2 && c.next_match_no" class="mt-1 text-xs text-[#ffd34d]">{{ t('cup.day.low') }}</p>
            <div class="mt-2 flex gap-1.5">
              <button type="button" class="tap rounded-full border border-brand-pink/40 px-3 text-xs font-semibold text-brand-pink" :disabled="c.returned > 0" @click="openSale(c, 'sell')">{{ t('cup.day.sell') }}</button>
              <button type="button" class="tap rounded-full border border-white/20 px-3 text-xs text-white/70" :disabled="c.left < 1" @click="openSale(c, 'return')">{{ t('cup.day.buyBack') }}</button>
            </div>
            <div v-if="selling?.team.team_id === c.team_id" class="mt-3 rounded-xl border border-white/10 p-3">
              <p class="text-xs font-semibold text-white/70">{{ selling.kind === 'sell' ? t('cup.day.sellTitle') : t('cup.day.buyBackTitle') }}</p>
              <div class="mt-2 grid grid-cols-2 gap-2">
                <label class="flex flex-col gap-1 text-xs text-white/50">
                  {{ selling.kind === 'sell' ? t('cup.day.sets') : t('cup.day.coupons') }}
                  <input v-model.number="sale.quantity" type="number" min="1" :max="selling.kind === 'return' ? c.left : 20" :class="INPUT" />
                </label>
                <label class="flex flex-col gap-1 text-xs text-white/50">
                  {{ t('cup.money.via') }}
                  <select v-model="sale.via" :class="INPUT">
                    <option value="cash">{{ t('cup.admin.paidCash') }}</option>
                    <option value="transfer">{{ t('cup.admin.paidTransfer') }}</option>
                  </select>
                </label>
                <label v-if="sale.via === 'transfer'" class="col-span-2 flex flex-col gap-1 text-xs text-white/50">
                  {{ t('cup.money.receipt') }}
                  <input type="file" accept="image/*" class="text-xs" @change="sale.slip = ($event.target as HTMLInputElement).files?.[0] ?? null" />
                </label>
              </div>
              <p class="mt-2 text-sm">{{ selling.kind === 'sell' ? t('cup.day.toTake', { amount: money(saleAmount) }) : t('cup.day.toGive', { amount: money(saleAmount) }) }}</p>
              <div class="mt-2 flex gap-2">
                <button type="button" :disabled="busy === c.team_id" class="tap rounded-full bg-brand-pink px-4 text-xs font-semibold text-brand-black" @click="saveSale">{{ t('cup.admin.save') }}</button>
                <button type="button" class="tap rounded-full border border-white/20 px-3 text-xs text-white/60" @click="selling = null">{{ t('common.cancel') }}</button>
              </div>
            </div>
          </li>
        </ul>
      </template>
    </template>

    <!-- a walkover -->
    <div v-if="walkingOver" class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-3" role="dialog" aria-modal="true" :aria-label="t('cup.day.walkoverTitle')">
      <div class="w-full max-w-md rounded-2xl border border-status-error/40 bg-[#1c0f33] p-4 shadow-2xl">
        <p class="font-display text-base font-bold">#{{ walkingOver.match_no }} · {{ t('cup.day.walkoverTitle') }}</p>
        <p class="mt-1 text-xs text-white/60">{{ t('cup.day.walkoverHint') }}</p>
        <div class="mt-3 flex flex-col gap-2">
          <button
            v-for="side in (['a', 'b'] as const)"
            :key="side"
            type="button"
            :disabled="busy === walkingOver.id"
            class="tap rounded-full border border-white/25 px-4 text-sm"
            @click="giveWalkover(side)"
          >
            {{ t('cup.day.wins', { team: sideLabel(walkingOver[side], t) }) }}
          </button>
        </div>
        <p v-if="problem" class="mt-2 text-sm text-status-error" role="alert">{{ problem }}</p>
        <button type="button" class="tap mt-3 rounded-full border border-white/20 px-4 text-sm text-white/60" @click="walkingOver = null; problem = ''">{{ t('common.cancel') }}</button>
      </div>
    </div>

    <!-- the result form -->
    <div v-if="editing" class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-3" role="dialog" aria-modal="true" :aria-label="t('cup.day.enterResult')">
      <div class="w-full max-w-md rounded-2xl border border-brand-pink/30 bg-[#1c0f33] p-4 shadow-2xl">
        <p class="font-display text-base font-bold">#{{ editing.match_no }} · {{ t('cup.day.enterResult') }}</p>
        <p class="text-xs text-white/55">{{ editing.stage === 'group' ? t('cup.day.groupRule') : t('cup.day.koRule') }}</p>
        <div class="mt-3 grid items-center gap-1.5 text-sm" :style="{ gridTemplateColumns: `minmax(0,1fr) repeat(${form.sets.length}, 3.5rem)` }">
          <span />
          <span v-for="(_, i) in form.sets" :key="`h${i}`" class="text-center text-xs text-white/50">{{ t('cup.day.set', { n: i + 1 }) }}</span>
          <span class="truncate">{{ sideLabel(editing.a, t) }}</span>
          <input v-for="(s, i) in form.sets" :key="`a${i}`" v-model.number="s.a" type="number" inputmode="numeric" min="0" max="30" :class="[INPUT, 'text-center']" :aria-label="`${sideLabel(editing.a, t)} ${t('cup.day.set', { n: i + 1 })}`" />
          <span class="truncate">{{ sideLabel(editing.b, t) }}</span>
          <input v-for="(s, i) in form.sets" :key="`b${i}`" v-model.number="s.b" type="number" inputmode="numeric" min="0" max="30" :class="[INPUT, 'text-center']" :aria-label="`${sideLabel(editing.b, t)} ${t('cup.day.set', { n: i + 1 })}`" />
        </div>
        <label class="mt-3 flex items-center gap-2 text-sm whitespace-nowrap">
          {{ t('cup.day.shuttles') }}
          <input v-model.number="form.shuttles" type="number" min="0" max="20" class="w-20 rounded border border-brand-pink-dark/40 bg-brand-black px-2 py-1.5 text-center text-sm text-white" />
        </label>
        <p class="mt-1 text-xs text-white/50">{{ t('cup.day.shuttlesHint') }}</p>
        <p v-if="problem" class="mt-2 text-sm text-status-error" role="alert">{{ problem }}</p>
        <div class="mt-3 flex gap-2">
          <button type="button" :disabled="busy === editing.id" class="tap rounded-full bg-brand-pink px-5 text-sm font-semibold text-brand-black" @click="saveResult">{{ t('cup.admin.save') }}</button>
          <button type="button" class="tap rounded-full border border-white/20 px-4 text-sm text-white/60" @click="editing = null; problem = ''">{{ t('common.cancel') }}</button>
        </div>
      </div>
    </div>
  </main>
</template>
