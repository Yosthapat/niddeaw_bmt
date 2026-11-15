<script setup lang="ts">
/**
 * The teams of the tournament: who signed up in which level, where each
 * stands, the slips to check, and what is owed back. Real names and phones
 * are shown here — to tournament admins only — and in the CSV export.
 * A pair without LINE is signed up from here (cash or transfer at the desk).
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import AdminNav from '@/components/layout/AdminNav.vue'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'
import {
  tournamentAdmin,
  type AdminTeam,
  type Details,
  type Entrant,
  type PaidVia,
  type PlayerHit,
  type TeamStatus,
} from '@/api/tournament'
import { apiErrorMessage } from '@/api/errors'
import { useTournamentPick } from '@/composables/useTournamentPick'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { formatDateTime, money } from '@/utils/format'
import type { Locale } from '@/i18n'

const { t, locale } = useI18n()
const { confirm } = useConfirmDialog()
const { all, picked, load, pick } = useTournamentPick()

const INPUT = 'w-full rounded border border-brand-pink-dark/40 bg-brand-black px-2 py-1.5 text-sm text-white'
const LIVE: TeamStatus[] = ['invited', 'awaiting_payment', 'slip_review', 'confirmed', 'waitlist']

const teams = ref<AdminTeam[]>([])
const loading = ref(false)
const problem = ref('')
const busy = ref<string | null>(null)
const levelFilter = ref('')
type Show = 'live' | 'slips' | 'refunds' | 'ended' | 'all'
const show = ref<Show>('live')

async function refresh(): Promise<void> {
  if (!picked.value) return
  loading.value = true
  problem.value = ''
  try {
    teams.value = await tournamentAdmin.teams(picked.value.id)
  } catch (e) {
    problem.value = apiErrorMessage(e, t('cup.admin.loadFailed'))
  } finally {
    loading.value = false
  }
}
watch(() => picked.value?.id, refresh)
onMounted(async () => {
  if (!all.value.length) await load()
  await refresh()
})

const toCheck = (x: AdminTeam): boolean => x.entrants.some((e) => e.pay_status === 'slip_sent')
const shown = computed(() =>
  teams.value.filter((x) => {
    if (levelFilter.value && x.level_id !== levelFilter.value) return false
    if (show.value === 'live') return LIVE.includes(x.status)
    if (show.value === 'slips') return toCheck(x)
    if (show.value === 'refunds') return x.refund_owed > 0
    if (show.value === 'ended') return !LIVE.includes(x.status)
    return true
  }),
)
const counts = computed(() => ({
  slips: teams.value.filter(toCheck).length,
  refunds: teams.value.filter((x) => x.refund_owed > 0).length,
}))
function seats(levelId: string): { taken: number; wait: number } {
  const mine = teams.value.filter((x) => x.level_id === levelId)
  return {
    taken: mine.filter((x) => x.status === 'slip_review' || x.status === 'confirmed').length,
    wait: mine.filter((x) => x.status === 'waitlist').length,
  }
}

async function run(key: string, job: () => Promise<AdminTeam[]>): Promise<void> {
  busy.value = key
  problem.value = ''
  try {
    teams.value = await job()
  } catch (e) {
    problem.value = apiErrorMessage(e, t('cup.admin.saveFailed'))
  } finally {
    busy.value = null
  }
}

const checkOf = (x: AdminTeam, e: Entrant) => x.slip_checks.find((c) => c.target_id === e.id)
const canCash = (x: AdminTeam, e: Entrant): boolean =>
  LIVE.includes(x.status) && x.status !== 'invited' && (e.pay_status === 'unpaid' || e.pay_status === 'rejected')
const owes = (x: AdminTeam, e: Entrant): boolean =>
  (x.status === 'cancelled' || x.status === 'withdrawn') && x.refund_owed > 0 && e.pay_status === 'paid'

async function approve(e: Entrant): Promise<void> {
  await run(e.id, () => tournamentAdmin.approve(e.id))
}
async function reject(e: Entrant): Promise<void> {
  const ok = await confirm({ title: t('cup.admin.rejectTitle'), message: t('cup.admin.rejectBody', { name: e.nickname }), confirmLabel: t('cup.admin.reject') })
  if (ok) await run(e.id, () => tournamentAdmin.reject(e.id))
}
async function cash(e: Entrant): Promise<void> {
  const ok = await confirm({ title: t('cup.admin.cashTitle'), message: t('cup.admin.cashBody', { name: e.nickname, amount: money(e.share) }), confirmLabel: t('cup.admin.cash') })
  if (ok) await run(e.id, () => tournamentAdmin.cash(e.id))
}

// refund, with the transfer's slip if there is one
const refunding = ref<string | null>(null)
const refundFile = ref<File | null>(null)
async function refund(e: Entrant): Promise<void> {
  await run(e.id, () => tournamentAdmin.refund(e.id, refundFile.value))
  refunding.value = null
  refundFile.value = null
}

// withdraw: refund or keep the fees
const withdrawing = ref<string | null>(null)
async function withdraw(x: AdminTeam, noRefund: boolean): Promise<void> {
  await run(x.id, () => tournamentAdmin.withdraw(x.id, noRefund))
  withdrawing.value = null
}

// rename / move level
const editing = ref<string | null>(null)
const teamDraft = reactive({ name: '', level_id: '' })
function startEdit(x: AdminTeam): void {
  editing.value = x.id
  teamDraft.name = x.name
  teamDraft.level_id = x.level_id
}
async function saveTeam(x: AdminTeam): Promise<void> {
  const body: { name?: string; level_id?: string } = {}
  if (teamDraft.name.trim() !== x.name) body.name = teamDraft.name.trim()
  if (teamDraft.level_id !== x.level_id) body.level_id = teamDraft.level_id
  if (Object.keys(body).length) await run(x.id, () => tournamentAdmin.updateTeam(x.id, body))
  if (!problem.value) editing.value = null
}

// a player's own details
const editingPerson = ref<string | null>(null)
const personDraft = reactive<Details>({ first_name: '', last_name: '', phone: '' })
function startPerson(e: Entrant): void {
  editingPerson.value = e.id
  Object.assign(personDraft, { first_name: e.first_name ?? '', last_name: e.last_name ?? '', phone: e.phone ?? '' })
}
async function savePerson(e: Entrant): Promise<void> {
  await run(e.id, () => tournamentAdmin.updateEntrant(e.id, { ...personDraft }))
  if (!problem.value) editingPerson.value = null
}

async function exportCsv(): Promise<void> {
  if (!picked.value) return
  const blob = await tournamentAdmin.exportCsv(picked.value.id)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `tournament-${picked.value.starts_on}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

// --- signing a pair up at the desk -------------------------------------------
const adding = ref(false)
const people = ref<PlayerHit[]>([])
const addForm = reactive({
  level_id: '',
  team_name: '',
  paid_via: 'cash' as PaidVia | 'unpaid',
  captain: { player_id: '', first_name: '', last_name: '', phone: '' },
  partner: { player_id: '', first_name: '', last_name: '', phone: '' },
})
const queries = reactive({ captain: '', partner: '' })
async function openAdd(): Promise<void> {
  adding.value = !adding.value
  if (adding.value && picked.value) {
    people.value = await tournamentAdmin.players(picked.value.id)
    addForm.level_id ||= picked.value.levels[0]?.id ?? ''
  }
}
function matches(q: string): PlayerHit[] {
  const s = q.trim().toLowerCase()
  return s ? people.value.filter((p) => p.nickname.toLowerCase().includes(s)).slice(0, 8) : []
}
const chosen = (id: string): PlayerHit | undefined => people.value.find((p) => p.player_id === id)
const minGames = computed(() => picked.value?.min_games ?? 3)
async function submitAdd(): Promise<void> {
  if (!picked.value) return
  await run('add', () => tournamentAdmin.signUp(picked.value!.id, { ...addForm, team_name: addForm.team_name.trim() }))
  if (!problem.value) {
    adding.value = false
    Object.assign(addForm.captain, { player_id: '', first_name: '', last_name: '', phone: '' })
    Object.assign(addForm.partner, { player_id: '', first_name: '', last_name: '', phone: '' })
    addForm.team_name = ''
    queries.captain = queries.partner = ''
  }
}

const statusTone: Record<TeamStatus, string> = {
  invited: 'border-white/25 text-white/70',
  awaiting_payment: 'border-[#ffd34d]/50 text-[#ffd34d]',
  slip_review: 'border-[#7fd0ff]/50 text-[#7fd0ff]',
  confirmed: 'border-status-success/50 text-status-success',
  waitlist: 'border-[#c9a7ff]/50 text-[#c9a7ff]',
  cancelled: 'border-white/15 text-white/40',
  withdrawn: 'border-white/15 text-white/40',
}
const when = (iso: string | null): string => (iso ? formatDateTime(iso, locale.value as Locale) : '')
</script>

<template>
  <AdminNav />
  <main class="mx-auto max-w-3xl px-4 py-6">
    <h1 class="sr-only">{{ t('admin.nav.tTeams') }}</h1>

    <div v-if="all.length" class="flex flex-wrap items-center gap-2">
      <select
        :value="picked?.id"
        :aria-label="t('cup.admin.pick')"
        class="min-h-11 flex-1 rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-sm text-white"
        @change="pick(($event.target as HTMLSelectElement).value)"
      >
        <option v-for="x in all" :key="x.id" :value="x.id">{{ x.name }} · {{ x.starts_on }}</option>
      </select>
      <button type="button" class="tap rounded-full border border-white/20 px-4 text-sm text-white/75" @click="exportCsv">{{ t('cup.admin.csv') }}</button>
    </div>
    <p v-else class="text-sm text-white/50">{{ t('cup.admin.noneYet') }}</p>

    <template v-if="picked">
      <!-- seats per level -->
      <div class="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
        <button
          v-for="lv in picked.levels"
          :key="lv.id"
          type="button"
          class="hud-panel border bg-brand-surface p-3 text-left"
          :class="levelFilter === lv.id ? 'border-brand-pink' : 'border-brand-pink/15'"
          :aria-pressed="levelFilter === lv.id"
          @click="levelFilter = levelFilter === lv.id ? '' : lv.id"
        >
          <span class="block text-xs text-white/60">{{ lv.name }}</span>
          <span class="font-display text-lg font-bold">{{ seats(lv.id).taken }}<span class="text-sm text-white/45">/{{ lv.max_teams }}</span></span>
          <span v-if="seats(lv.id).wait" class="block text-xs text-[#c9a7ff]">{{ t('cup.admin.waiting', { n: seats(lv.id).wait }) }}</span>
        </button>
      </div>

      <div class="mt-4 flex flex-wrap gap-1.5" role="group" :aria-label="t('cup.admin.filter')">
        <button
          v-for="s in (['live', 'slips', 'refunds', 'ended', 'all'] as Show[])"
          :key="s"
          type="button"
          class="tap rounded-full px-3 text-xs font-semibold"
          :class="show === s ? 'bg-brand-pink text-brand-black' : 'border border-white/20 text-white/70'"
          :aria-pressed="show === s"
          @click="show = s"
        >
          {{ t(`cup.admin.show.${s}`) }}
          <span v-if="s === 'slips' && counts.slips"> · {{ counts.slips }}</span>
          <span v-if="s === 'refunds' && counts.refunds"> · {{ counts.refunds }}</span>
        </button>
        <button type="button" class="tap ml-auto rounded-full border border-brand-pink/40 px-4 text-xs font-semibold text-brand-pink" @click="openAdd">
          + {{ t('cup.admin.signUpPair') }}
        </button>
      </div>

      <!-- sign a pair up -->
      <section v-if="adding" class="hud-panel mt-4 border border-brand-pink/20 bg-brand-surface p-4">
        <h2 class="text-sm font-semibold text-white/70">{{ t('cup.admin.signUpPair') }}</h2>
        <p class="mt-1 text-xs text-white/50">{{ t('cup.admin.signUpHint', { n: minGames }) }}</p>
        <div class="mt-3 grid grid-cols-2 gap-2.5">
          <label class="flex flex-col gap-1 text-xs text-white/50">
            {{ t('cup.level') }}
            <select v-model="addForm.level_id" :class="INPUT">
              <option v-for="lv in picked.levels" :key="lv.id" :value="lv.id">{{ lv.name }}</option>
            </select>
          </label>
          <label class="flex flex-col gap-1 text-xs text-white/50">{{ t('cup.teamName') }}<input v-model="addForm.team_name" maxlength="40" :class="INPUT" /></label>
        </div>
        <div v-for="role in (['captain', 'partner'] as const)" :key="role" class="mt-4 rounded-xl border border-white/10 p-3">
          <p class="text-xs font-semibold text-white/70">{{ t(`cup.role.${role}`) }}</p>
          <template v-if="chosen(addForm[role].player_id)">
            <p class="mt-1 flex items-center gap-2 text-sm">
              <b>{{ chosen(addForm[role].player_id)?.nickname }}</b>
              <span class="text-xs text-white/50">ELO {{ chosen(addForm[role].player_id)?.elo }} · {{ t('cup.admin.games', { n: chosen(addForm[role].player_id)?.games }) }}</span>
              <button type="button" class="ml-auto text-xs text-white/60 underline" @click="addForm[role].player_id = ''">{{ t('cup.admin.change') }}</button>
            </p>
          </template>
          <template v-else>
            <input v-model="queries[role]" :placeholder="t('cup.admin.searchPlayer')" :class="[INPUT, 'mt-1']" />
            <ul class="mt-1 space-y-1">
              <li v-for="p in matches(queries[role])" :key="p.player_id">
                <button
                  type="button"
                  class="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm hover:bg-white/5 disabled:opacity-40"
                  :disabled="p.taken || p.games < minGames"
                  @click="addForm[role].player_id = p.player_id"
                >
                  {{ p.nickname }}
                  <span class="text-xs text-white/45">ELO {{ p.elo }} · {{ t('cup.admin.games', { n: p.games }) }}</span>
                  <span v-if="p.taken" class="ml-auto text-xs text-white/45">{{ t('cup.admin.taken') }}</span>
                  <span v-else-if="p.games < minGames" class="ml-auto text-xs text-white/45">{{ t('cup.admin.tooFew') }}</span>
                </button>
              </li>
            </ul>
          </template>
          <div class="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3">
            <input v-model="addForm[role].first_name" :placeholder="t('cup.firstName')" :class="INPUT" />
            <input v-model="addForm[role].last_name" :placeholder="t('cup.lastName')" :class="INPUT" />
            <input v-model="addForm[role].phone" inputmode="tel" :placeholder="t('cup.phone')" :class="INPUT" />
          </div>
        </div>
        <label class="mt-3 flex flex-col gap-1 text-xs text-white/50">
          {{ t('cup.admin.paidHow') }}
          <select v-model="addForm.paid_via" :class="INPUT">
            <option value="cash">{{ t('cup.admin.paidCash') }}</option>
            <option value="transfer">{{ t('cup.admin.paidTransfer') }}</option>
            <option value="unpaid">{{ t('cup.admin.paidLater') }}</option>
          </select>
        </label>
        <button type="button" :disabled="busy === 'add'" class="tap mt-3 rounded-full bg-brand-pink px-5 text-sm font-semibold text-brand-black disabled:opacity-50" @click="submitAdd">
          {{ t('cup.admin.signUpGo') }}
        </button>
      </section>

      <p v-if="problem" class="mt-4 text-sm text-status-error" role="alert">{{ problem }}</p>
      <p v-if="loading && !teams.length" class="mt-6 text-white/60">{{ t('common.loading') }}</p>
      <p v-else-if="!shown.length" class="mt-6 text-sm text-white/40">{{ t('cup.admin.noTeams') }}</p>

      <ul class="mt-4 space-y-3">
        <li v-for="x in shown" :key="x.id" class="hud-panel border border-brand-pink/15 bg-brand-surface p-4">
          <!-- the team -->
          <div v-if="editing === x.id" class="grid grid-cols-2 gap-2">
            <input v-model="teamDraft.name" maxlength="40" :class="INPUT" :aria-label="t('cup.teamName')" />
            <select v-model="teamDraft.level_id" :class="INPUT" :aria-label="t('cup.level')">
              <option v-for="lv in picked.levels" :key="lv.id" :value="lv.id">{{ lv.name }}</option>
            </select>
            <div class="col-span-2 flex gap-2">
              <button type="button" class="tap rounded-full bg-brand-pink px-4 text-xs font-semibold text-brand-black" @click="saveTeam(x)">{{ t('cup.admin.save') }}</button>
              <button type="button" class="tap rounded-full border border-white/20 px-4 text-xs text-white/60" @click="editing = null">{{ t('common.cancel') }}</button>
            </div>
          </div>
          <div v-else class="flex flex-wrap items-center gap-2">
            <b class="font-display text-base">{{ x.name }}</b>
            <span class="text-xs text-white/55">{{ x.level_name }}</span>
            <span class="rounded-full border px-2 py-0.5 text-xs font-semibold" :class="statusTone[x.status]">{{ t(`cup.teamStatus.${x.status}`) }}</span>
            <span v-if="x.by_admin" class="text-xs text-white/45">{{ t('cup.admin.byAdmin') }}</span>
            <span v-if="x.expires_at" class="text-xs text-[#ffd34d]">{{ t('cup.admin.expires', { at: when(x.expires_at) }) }}</span>
            <button v-if="LIVE.includes(x.status)" type="button" class="ml-auto text-xs text-white/60 underline" @click="startEdit(x)">{{ t('cup.admin.editTeam') }}</button>
          </div>

          <!-- its two players -->
          <ul class="mt-3 space-y-2">
            <li v-for="e in x.entrants" :key="e.id" class="rounded-xl border border-white/10 bg-brand-black/40 p-3">
              <div class="flex items-start gap-3">
                <PlayerAvatar :name="e.nickname" :avatar-url="e.avatar_url" size="sm" round />
                <div class="min-w-0 flex-1">
                  <p class="text-sm">
                    <b>{{ e.nickname }}</b>
                    <span class="text-xs text-white/50"> · {{ t(`cup.role.${e.role}`) }} · ELO {{ e.elo ?? '—' }}</span>
                  </p>
                  <template v-if="editingPerson === e.id">
                    <div class="mt-1 grid grid-cols-2 gap-1.5 sm:grid-cols-3">
                      <input v-model="personDraft.first_name" :placeholder="t('cup.firstName')" :class="INPUT" />
                      <input v-model="personDraft.last_name" :placeholder="t('cup.lastName')" :class="INPUT" />
                      <input v-model="personDraft.phone" inputmode="tel" :placeholder="t('cup.phone')" :class="INPUT" />
                    </div>
                    <div class="mt-1.5 flex gap-2">
                      <button type="button" class="tap rounded-full bg-brand-pink px-3 text-xs font-semibold text-brand-black" @click="savePerson(e)">{{ t('cup.admin.save') }}</button>
                      <button type="button" class="tap rounded-full border border-white/20 px-3 text-xs text-white/60" @click="editingPerson = null">{{ t('common.cancel') }}</button>
                    </div>
                  </template>
                  <p v-else class="text-xs text-white/70">
                    <template v-if="e.first_name">{{ e.first_name }} {{ e.last_name }} · <a :href="`tel:${e.phone}`" class="text-brand-pink underline">{{ e.phone }}</a></template>
                    <span v-else class="text-white/40">{{ t('cup.admin.noDetails') }}</span>
                    <button type="button" class="ml-2 text-white/45 underline" @click="startPerson(e)">{{ t('cup.admin.edit') }}</button>
                  </p>
                  <p class="mt-1 text-xs">
                    <span :class="e.pay_status === 'paid' ? 'text-status-success' : e.pay_status === 'rejected' ? 'text-status-error' : 'text-white/60'">
                      {{ t(`cup.payStatus.${e.pay_status}`) }}<template v-if="e.paid_via === 'cash' && e.pay_status === 'paid'"> · {{ t('cup.admin.paidCash') }}</template>
                    </span>
                    · {{ money(e.share) }}
                    <template v-if="checkOf(x, e)">
                      ·
                      <span :class="checkOf(x, e)?.status === 'duplicate' ? 'font-semibold text-status-error' : checkOf(x, e)?.status === 'ok' ? 'text-status-success' : 'text-[#ffd34d]'">
                        {{ t(`cup.slipCheck.${checkOf(x, e)?.status}`) }}
                        <template v-if="checkOf(x, e)?.used_before_who"> ({{ checkOf(x, e)?.used_before_who }})</template>
                      </span>
                    </template>
                  </p>
                </div>
                <a v-if="e.slip_url" :href="e.slip_url" target="_blank" rel="noopener" class="shrink-0">
                  <img :src="e.slip_url" :alt="t('cup.admin.slipOf', { name: e.nickname })" class="h-16 w-12 rounded border border-white/15 object-cover" />
                </a>
              </div>

              <div class="mt-2 flex flex-wrap gap-1.5">
                <template v-if="e.pay_status === 'slip_sent'">
                  <button type="button" :disabled="busy === e.id" class="tap rounded-full bg-status-success px-3 text-xs font-semibold text-brand-black disabled:opacity-50" @click="approve(e)">{{ t('cup.admin.approve') }}</button>
                  <button type="button" :disabled="busy === e.id" class="tap rounded-full border border-status-error/50 px-3 text-xs text-status-error" @click="reject(e)">{{ t('cup.admin.reject') }}</button>
                </template>
                <button v-if="canCash(x, e)" type="button" :disabled="busy === e.id" class="tap rounded-full border border-white/25 px-3 text-xs text-white/75" @click="cash(e)">{{ t('cup.admin.cash') }}</button>
                <template v-if="owes(x, e)">
                  <template v-if="refunding === e.id">
                    <label class="tap cursor-pointer rounded-full border border-white/25 px-3 text-xs text-white/75">
                      {{ refundFile ? refundFile.name : t('cup.admin.refundSlip') }}
                      <input type="file" accept="image/*" class="sr-only" @change="refundFile = ($event.target as HTMLInputElement).files?.[0] ?? null" />
                    </label>
                    <button type="button" :disabled="busy === e.id" class="tap rounded-full bg-[#ffd34d] px-3 text-xs font-semibold text-brand-black" @click="refund(e)">{{ t('cup.admin.refundDone', { amount: money(e.share) }) }}</button>
                    <button type="button" class="tap rounded-full border border-white/20 px-3 text-xs text-white/60" @click="refunding = null">{{ t('common.cancel') }}</button>
                  </template>
                  <button v-else type="button" class="tap rounded-full border border-[#ffd34d]/50 px-3 text-xs text-[#ffd34d]" @click="refunding = e.id; refundFile = null">
                    {{ t('cup.admin.refund', { amount: money(e.share) }) }}
                  </button>
                </template>
              </div>
            </li>
          </ul>

          <!-- withdraw -->
          <div v-if="LIVE.includes(x.status)" class="mt-3">
            <div v-if="withdrawing === x.id" class="flex flex-wrap items-center gap-1.5">
              <span class="text-xs text-white/70">{{ t('cup.admin.withdrawAsk') }}</span>
              <button type="button" :disabled="busy === x.id" class="tap rounded-full border border-status-error/50 px-3 text-xs text-status-error" @click="withdraw(x, false)">{{ t('cup.admin.withdrawRefund') }}</button>
              <button type="button" :disabled="busy === x.id" class="tap rounded-full border border-status-error/50 px-3 text-xs text-status-error" @click="withdraw(x, true)">{{ t('cup.admin.withdrawKeep') }}</button>
              <button type="button" class="tap rounded-full border border-white/20 px-3 text-xs text-white/60" @click="withdrawing = null">{{ t('common.cancel') }}</button>
            </div>
            <button v-else type="button" class="text-xs text-white/45 underline" @click="withdrawing = x.id">{{ t('cup.admin.withdraw') }}</button>
          </div>
        </li>
      </ul>
    </template>
  </main>
</template>
