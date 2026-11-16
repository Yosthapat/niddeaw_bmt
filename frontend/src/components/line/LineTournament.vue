<script setup lang="ts">
/**
 * Signing up for the tournament from LINE.
 *
 * The captain picks a partner, a level (their stronger player's, or one
 * above) and a team name, and gives their own name and phone. The partner
 * sees the invite here, accepts with their own details. Then each transfers
 * their half to the tournament's own account — never club credit — and
 * sends the slip; both slips in takes the place, and a tournament admin
 * checks them. Real names and phones are never shown to anyone else here.
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { lineTournament, type Candidate, type Details, type LineTournament, type PublicLevel } from '@/api/tournament'
import type { PaymentInfoResponse } from '@/types'
import { apiErrorMessage } from '@/api/errors'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { compressImage } from '@/utils/imageCompression'
import { formatDateTime, formatDateWithWeekday, money } from '@/utils/format'
import type { Locale } from '@/i18n'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'
import BrandQr from '@/components/common/BrandQr.vue'
import CupMatchCard from '@/components/cup/CupMatchCard.vue'
import CupTeamLine from '@/components/cup/CupTeamLine.vue'
import CupStandings from '@/components/cup/CupStandings.vue'
import CupMatchRow from '@/components/cup/CupMatchRow.vue'
import { rankBands, roundLabel } from '@/utils/cupMatch'
import { usePolling } from '@/composables/usePolling'

const props = defineProps<{ token: string }>()
const emit = defineEmits<{ back: [] }>()
const { t, locale } = useI18n()
const { confirm } = useConfirmDialog()

const INPUT = 'w-full rounded-xl border border-white/15 bg-white/5 px-3 py-2.5 text-[15px] text-white placeholder:text-white/35'

const data = ref<LineTournament | null>(null)
const problem = ref('')
const busy = ref<string | null>(null)

async function run(key: string, job: () => Promise<LineTournament>, fallback: string): Promise<boolean> {
  busy.value = key
  problem.value = ''
  try {
    data.value = await job()
    return true
  } catch (e) {
    problem.value = apiErrorMessage(e, fallback)
    return false
  } finally {
    busy.value = null
  }
}
onMounted(() => run('load', () => lineTournament.get(props.token), t('cup.line.loadFailed')))

const cup = computed(() => data.value?.tournament ?? null)
const me = computed(() => data.value?.me ?? null)
const team = computed(() => data.value?.team ?? null)
const mine = computed(() => team.value?.entrants.find((e) => e.player_id === me.value?.player_id) ?? null)
const other = computed(() => team.value?.entrants.find((e) => e.player_id !== me.value?.player_id) ?? null)
const when = (iso: string): string => formatDateTime(iso, locale.value as Locale)
const day = (iso: string): string => formatDateWithWeekday(iso, locale.value as Locale)
const perPlayer = computed(() => (cup.value ? Math.ceil((cup.value.entry_fee + cup.value.shuttle_fee) / 2) : 0))

// --- the form --------------------------------------------------------------
const details = reactive<Details>({ first_name: '', last_name: '', phone: '' })
watch(
  () => data.value?.last_details,
  (d) => {
    if (d && !details.first_name && !details.last_name && !details.phone) Object.assign(details, d)
  },
  { immediate: true },
)
const phoneOk = computed(() => /^0[0-9]{8,9}$/.test(details.phone.trim()))
const detailsOk = computed(() => !!details.first_name.trim() && !!details.last_name.trim() && phoneOk.value)

const candidates = ref<Candidate[]>([])
const query = ref('')
const partnerId = ref('')
const levelId = ref('')
const teamName = ref('')
async function startSignUp(): Promise<void> {
  if (candidates.value.length) return
  try {
    candidates.value = await lineTournament.candidates(props.token)
  } catch (e) {
    problem.value = apiErrorMessage(e, t('cup.line.loadFailed'))
  }
}
watch(
  () => !!cup.value && !team.value && !!me.value && me.value.games_needed === 0 && cup.value.taking_entries,
  (show) => {
    if (show) void startSignUp()
  },
  { immediate: true },
)
const shownCandidates = computed(() => {
  const q = query.value.trim().toLowerCase()
  return q ? candidates.value.filter((c) => c.nickname.toLowerCase().includes(q)).slice(0, 20) : []
})
const partner = computed(() => candidates.value.find((c) => c.player_id === partnerId.value) ?? null)
const teamElo = computed(() => Math.max(me.value?.elo ?? 0, partner.value?.elo ?? 0))
/** The stronger player's level, or any above — never below. */
const allowed = computed<PublicLevel[]>(() => (cup.value?.levels ?? []).filter((lv) => lv.max_elo === null || teamElo.value < lv.max_elo))
watch(allowed, (list) => {
  if (!list.some((lv) => lv.id === levelId.value)) levelId.value = list[0]?.id ?? ''
})
const chosenLevel = computed(() => cup.value?.levels.find((lv) => lv.id === levelId.value) ?? null)
const full = (lv: PublicLevel): boolean => lv.seats_taken >= lv.max_teams
const canSend = computed(() => !!partner.value && !!levelId.value && teamName.value.trim().length >= 2 && detailsOk.value)

async function signUp(): Promise<void> {
  if (!canSend.value) return
  await run(
    'signup',
    () =>
      lineTournament.signUp(props.token, {
        ...details,
        phone: details.phone.trim(),
        partner_id: partnerId.value,
        level_id: levelId.value,
        team_name: teamName.value.trim(),
      }),
    t('cup.line.signUpFailed'),
  )
}

async function accept(): Promise<void> {
  if (!detailsOk.value) return
  await run('accept', () => lineTournament.accept(props.token, { ...details, phone: details.phone.trim() }), t('cup.line.acceptFailed'))
}
async function decline(): Promise<void> {
  const captainSide = data.value?.my_role === 'captain'
  const ok = await confirm({
    title: captainSide ? t('cup.line.cancelInviteTitle') : t('cup.line.declineTitle'),
    message: captainSide ? t('cup.line.cancelInviteBody') : t('cup.line.declineBody', { team: team.value?.name ?? '' }),
    confirmLabel: captainSide ? t('cup.line.cancelInvite') : t('cup.line.decline'),
  })
  if (ok) await run('decline', () => lineTournament.decline(props.token), t('cup.line.actionFailed'))
}
const renaming = ref(false)
const newName = ref('')
async function rename(): Promise<void> {
  if (newName.value.trim().length < 2) return
  if (await run('rename', () => lineTournament.rename(props.token, newName.value.trim()), t('cup.line.actionFailed'))) renaming.value = false
}

const myGroup = computed(() => {
  const lv = cup.value?.levels.find((x) => x.id === team.value?.level_id)
  return lv?.groups.find((g) => g.teams.some((x) => x.id === team.value?.id)) ?? null
})
const myMatches = computed(() => (cup.value?.matches ?? []).filter((m) => m.a.team_id === team.value?.id || m.b.team_id === team.value?.id))

const calledNow = computed(() => myMatches.value.find((m) => m.status === 'on_court') ?? null)
const myLevel = computed(() => cup.value?.levels.find((x) => x.id === team.value?.level_id) ?? null)
const pending = computed(() => myMatches.value.filter((m) => m.status !== 'done').sort((a, b) => a.match_no - b.match_no))
const nextMatch = computed(() => calledNow.value ?? pending.value[0] ?? null)
const laterMatches = computed(() => pending.value.filter((m) => m.id !== nextMatch.value?.id))
const playedMatches = computed(() =>
  myMatches.value.filter((m) => m.status === 'done').sort((a, b) => (b.finished_at ?? '').localeCompare(a.finished_at ?? '') || b.match_no - a.match_no),
)
const koMine = computed(() => myMatches.value.filter((m) => m.stage === 'ko').sort((a, b) => b.match_no - a.match_no))
/** Where my team stands, in a word: still in its group, in a bracket, out, or champions. */
const STANDING_CLASS = {
  group: 'bg-[#ff6cc0]/20 text-[#ff9fd6]',
  ko: 'bg-[#7ff0b4]/20 text-[#7ff0b4]',
  out: 'bg-white/10 text-white/60',
  champion: 'bg-[#ffe14d] text-[#2a1a00]',
} as const
const standing = computed<{ kind: keyof typeof STANDING_CLASS; text: string } | null>(() => {
  const me = team.value?.id
  const last = koMine.value[0]
  if (last && me) {
    const side = last.a.team_id === me ? 'a' : 'b'
    const bracket = t(`cup.bracket.${last.bracket ?? 'upper'}`)
    if (last.status === 'done' && last.winner && last.winner !== side) return { kind: 'out', text: t('cup.line.out') }
    if (last.status === 'done' && last.winner === side && last.round === 2) return { kind: 'champion', text: t('cup.line.champion', { bracket }) }
    return { kind: 'ko', text: `${bracket} · ${roundLabel(last, t).split(' · ').pop()}` }
  }
  const row = myGroup.value?.standings.find((r) => r.team_id === me)
  if (myGroup.value) return { kind: 'group', text: row?.played ? t('cup.line.groupPlace', { g: myGroup.value.label, n: row.rank }) : t('cup.draw.group', { g: myGroup.value.label }) }
  return null
})
// On the day: hear about a call without reopening the page.
usePolling(async () => {
  if (data.value?.tournament?.schedule_published && !busy.value) {
    try {
      data.value = await lineTournament.get(props.token)
    } catch {
      /* the next tick tries again */
    }
  }
}, 20000)

const rulesOf = (id: string): string => cup.value?.levels.find((lv) => lv.id === id)?.rules ?? ''

// --- paying ----------------------------------------------------------------
const pay = ref<PaymentInfoResponse | null>(null)
const toPay = computed(
  () => !!team.value && ['awaiting_payment', 'slip_review', 'waitlist'].includes(team.value.status) && (mine.value?.pay_status === 'unpaid' || mine.value?.pay_status === 'rejected'),
)
watch(
  toPay,
  async (need) => {
    pay.value = null
    if (!need) return
    try {
      pay.value = await lineTournament.payInfo(props.token)
    } catch (e) {
      problem.value = apiErrorMessage(e, t('cup.line.payInfoFailed'))
    }
  },
  { immediate: true },
)
async function attach(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const picked = input.files?.[0]
  input.value = ''
  if (!picked) return
  const slip = await compressImage(picked)
  await run('slip', () => lineTournament.sendSlip(props.token, slip), t('cup.line.slipFailed'))
}
</script>

<template>
  <section class="flex flex-col gap-3">
    <button type="button" class="-mb-1 flex min-h-11 w-fit items-center gap-1 text-sm text-white/70" @click="emit('back')">
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 6l-6 6 6 6" /></svg>
      {{ t('cup.line.back') }}
    </button>

    <p v-if="!data && !problem" class="text-sm text-white/60">{{ t('common.loading') }}</p>
    <p v-if="!data && problem" class="text-sm text-status-error" role="alert">{{ problem }}</p>

    <div v-if="data && !cup" class="world-card flex flex-col items-center gap-2 p-6 text-center">
      <p class="world-eyebrow">NIDDEAW CUP</p>
      <h2 class="world-title text-xl">{{ t('cup.line.noneTitle') }}</h2>
      <p class="text-sm text-white/70">{{ t('cup.line.noneBody') }}</p>
    </div>

    <template v-if="cup && me">
      <!-- the event -->
      <div class="world-card flex flex-col gap-1 p-4">
        <p class="world-eyebrow">NIDDEAW CUP</p>
        <h2 class="world-title text-xl">{{ cup.name }}</h2>
        <p class="text-sm text-white/75">{{ day(cup.starts_on) }}<template v-if="cup.venue"> · {{ cup.venue }}</template></p>
        <p class="text-sm text-white/75">{{ t('cup.feeLine', { amount: money(perPlayer) }) }}</p>
        <p class="text-xs text-white/55">{{ t('cup.couponLine', { n: cup.coupons_per_set }) }}</p>
        <p class="text-xs text-white/55">{{ cup.taking_entries ? t('cup.closesAt', { at: when(cup.closes_at) }) : t('cup.closed') }}</p>
      </div>

      <!-- not signed up -->
      <template v-if="!team">
        <div v-if="me.games_needed > 0" class="world-card flex flex-col items-center gap-2 p-5 text-center">
          <span class="text-3xl" aria-hidden="true">🏸</span>
          <h3 class="font-display text-lg font-bold">{{ t('cup.line.needGamesTitle', { n: me.games_needed }) }}</h3>
          <p class="text-sm text-white/70">{{ t('cup.line.needGamesBody', { min: cup.min_games, have: me.games }) }}</p>
        </div>
        <div v-else-if="!cup.taking_entries" class="world-card p-5 text-center text-sm text-white/70">{{ t('cup.line.notOpen') }}</div>

        <template v-else>
          <div class="world-card flex flex-col gap-3 p-4">
            <h3 class="font-display text-lg font-bold">{{ t('cup.line.signUpTitle') }}</h3>

            <!-- partner -->
            <div>
              <p class="mb-1 text-xs text-white/60">{{ t('cup.line.partner') }}</p>
              <div v-if="partner" class="flex items-center gap-2 rounded-xl bg-white/6 p-2">
                <PlayerAvatar :name="partner.nickname" :avatar-url="partner.avatar_url" size="sm" round />
                <b>{{ partner.nickname }}</b>
                <span class="text-xs text-white/50">ELO {{ partner.elo }}</span>
                <button type="button" class="ml-auto min-h-11 px-2 text-xs text-white/60 underline" @click="partnerId = ''">{{ t('cup.line.change') }}</button>
              </div>
              <template v-else>
                <input v-model="query" :class="INPUT" :placeholder="t('cup.line.searchPartner')" :aria-label="t('cup.line.searchPartner')" />
                <ul class="mt-1 flex flex-col gap-1">
                  <li v-for="c in shownCandidates" :key="c.player_id">
                    <button
                      type="button"
                      class="flex min-h-12 w-full items-center gap-2 rounded-xl px-2 text-left disabled:opacity-45"
                      :disabled="c.taken || !c.eligible"
                      @click="partnerId = c.player_id"
                    >
                      <PlayerAvatar :name="c.nickname" :avatar-url="c.avatar_url" size="sm" round />
                      <span>{{ c.nickname }}</span>
                      <span class="ml-auto text-xs text-white/55">
                        {{ c.taken ? t('cup.line.taken') : !c.eligible ? t('cup.line.notEnoughGames', { n: cup.min_games - c.games }) : `ELO ${c.elo}` }}
                      </span>
                    </button>
                  </li>
                </ul>
                <p class="mt-1 text-xs text-white/45">{{ t('cup.line.partnerHint') }}</p>
              </template>
            </div>

            <!-- level -->
            <div v-if="partner">
              <p class="mb-1 text-xs text-white/60">{{ t('cup.level') }}</p>
              <div class="flex flex-wrap gap-1.5">
                <button
                  v-for="lv in allowed"
                  :key="lv.id"
                  type="button"
                  class="min-h-11 rounded-full px-4 text-sm"
                  :class="levelId === lv.id ? 'bg-[#ff6cc0] font-bold text-[#1a0838]' : 'border border-white/20 text-white/80'"
                  :aria-pressed="levelId === lv.id"
                  @click="levelId = lv.id"
                >
                  {{ lv.name }} · {{ lv.seats_taken }}/{{ lv.max_teams }}
                </button>
              </div>
              <p class="mt-1 text-xs text-white/55">{{ t('cup.line.levelRule') }}</p>
              <p v-if="chosenLevel?.rules" class="mt-1 text-xs text-[#ffd34d]">{{ t('cup.rulesLine', { rules: chosenLevel.rules }) }}</p>
              <p v-if="chosenLevel && full(chosenLevel)" class="mt-1 text-xs text-[#c9a7ff]">{{ t('cup.line.levelFull') }}</p>
              <p v-if="chosenLevel?.max_teams === 24 && chosenLevel.cut_24" class="mt-1 text-xs text-white/55">{{ t('cup.line.cut24') }}</p>
            </div>

            <label class="flex flex-col gap-1 text-xs text-white/60">
              {{ t('cup.teamName') }}
              <input v-model="teamName" maxlength="40" :class="INPUT" :placeholder="t('cup.line.teamNameHint')" />
            </label>

            <fieldset class="flex flex-col gap-2">
              <legend class="mb-1 text-xs text-white/60">{{ t('cup.line.yourDetails') }}</legend>
              <div class="grid grid-cols-2 gap-2">
                <input v-model="details.first_name" maxlength="60" autocomplete="given-name" :class="INPUT" :placeholder="t('cup.firstName')" :aria-label="t('cup.firstName')" />
                <input v-model="details.last_name" maxlength="60" autocomplete="family-name" :class="INPUT" :placeholder="t('cup.lastName')" :aria-label="t('cup.lastName')" />
              </div>
              <input v-model="details.phone" inputmode="tel" autocomplete="tel" maxlength="10" :class="INPUT" :placeholder="t('cup.phone')" :aria-label="t('cup.phone')" />
              <p v-if="details.phone && !phoneOk" class="text-xs text-status-error">{{ t('cup.line.phoneBad') }}</p>
              <p class="text-xs text-white/45">{{ t('cup.line.privacy') }}</p>
            </fieldset>

            <p v-if="problem" class="text-sm text-status-error" role="alert">{{ problem }}</p>
            <button type="button" class="cta flex min-h-14 items-center justify-center rounded-2xl font-display text-base font-bold disabled:opacity-50" :disabled="!canSend || busy === 'signup'" @click="signUp">
              {{ busy === 'signup' ? t('cup.line.sending') : t('cup.line.sendInvite') }}
            </button>
            <p class="text-center text-xs text-white/50">{{ t('cup.line.inviteHint') }}</p>
          </div>
        </template>
      </template>

      <!-- in a team -->
      <template v-else>
        <div class="world-card flex flex-col gap-3 p-4">
          <div class="flex items-center gap-2">
            <h3 class="font-display text-lg font-bold">{{ team.name }}</h3>
            <span class="text-xs text-white/55">{{ team.level_name }}</span>
          </div>
          <ul class="flex flex-col gap-1.5">
            <li v-for="e in team.entrants" :key="e.id" class="flex items-center gap-2">
              <PlayerAvatar :name="e.nickname" :avatar-url="e.avatar_url" size="sm" round />
              <span>{{ e.nickname }}<span class="text-xs text-white/50"> · {{ t(`cup.role.${e.role}`) }}</span></span>
              <span class="ml-auto text-xs" :class="e.pay_status === 'paid' ? 'text-[#7ff0b4]' : 'text-white/60'">
                {{ team.status === 'invited' && e.role === 'partner' ? t('cup.line.notAnswered') : t(`cup.payStatus.${e.pay_status}`) }}
              </span>
            </li>
          </ul>

          <!-- where it stands -->
          <div class="rounded-2xl border border-white/12 bg-white/5 p-3 text-sm">
            <b class="block">{{ t(`cup.teamStatus.${team.status}`) }}</b>
            <span class="text-white/70">
              <template v-if="team.status === 'invited'">
                {{ data?.my_role === 'captain' ? t('cup.line.waitPartner', { name: other?.nickname ?? '' }) : t('cup.line.invitedBy', { name: other?.nickname ?? '' }) }}
              </template>
              <template v-else-if="team.status === 'awaiting_payment'">{{ t('cup.line.payBoth') }}</template>
              <template v-else-if="team.status === 'slip_review'">{{ t('cup.line.seatHeld') }}</template>
              <template v-else-if="team.status === 'confirmed'">{{ t('cup.line.confirmed', { day: day(cup.starts_on) }) }}</template>
              <template v-else-if="team.status === 'waitlist'">{{ t('cup.line.waitlist') }}</template>
            </span>
            <span v-if="team.expires_at" class="mt-1 block text-xs text-[#ffd34d]">{{ t('cup.line.expires', { at: when(team.expires_at) }) }}</span>
          </div>

          <!-- the invited partner answers -->
          <template v-if="team.status === 'invited' && data?.my_role === 'partner'">
            <fieldset class="flex flex-col gap-2">
              <legend class="mb-1 text-xs text-white/60">{{ t('cup.line.yourDetails') }}</legend>
              <div class="grid grid-cols-2 gap-2">
                <input v-model="details.first_name" maxlength="60" autocomplete="given-name" :class="INPUT" :placeholder="t('cup.firstName')" :aria-label="t('cup.firstName')" />
                <input v-model="details.last_name" maxlength="60" autocomplete="family-name" :class="INPUT" :placeholder="t('cup.lastName')" :aria-label="t('cup.lastName')" />
              </div>
              <input v-model="details.phone" inputmode="tel" autocomplete="tel" maxlength="10" :class="INPUT" :placeholder="t('cup.phone')" :aria-label="t('cup.phone')" />
              <p v-if="details.phone && !phoneOk" class="text-xs text-status-error">{{ t('cup.line.phoneBad') }}</p>
              <p class="text-xs text-white/45">{{ t('cup.line.privacy') }}</p>
            </fieldset>
            <button type="button" class="cta flex min-h-14 items-center justify-center rounded-2xl font-display text-base font-bold disabled:opacity-50" :disabled="!detailsOk || busy === 'accept'" @click="accept">
              {{ t('cup.line.accept') }}
            </button>
            <button type="button" class="glass-pill justify-center" :disabled="busy === 'decline'" @click="decline">{{ t('cup.line.decline') }}</button>
          </template>
          <button v-else-if="team.status === 'invited'" type="button" class="glass-pill justify-center" :disabled="busy === 'decline'" @click="decline">{{ t('cup.line.cancelInvite') }}</button>

          <!-- pay my half -->
          <template v-if="toPay && mine">
            <p v-if="mine.pay_status === 'rejected'" class="rounded-2xl border border-status-error/40 bg-status-error/10 p-3 text-sm text-[#ff9fb2]" role="alert">
              {{ t('cup.line.slipRejected') }}
            </p>
            <div class="flex flex-col items-center gap-2 rounded-2xl bg-white/5 p-3">
              <span class="text-xs text-white/60">{{ t('cup.line.scanToPay', { amount: money(mine.share) }) }}</span>
              <BrandQr
                v-if="pay?.qr_modules"
                :modules="pay.qr_modules"
                :amount="mine.share"
                :account-name="pay.bank_account_name"
                :alt="t('cup.line.qrAlt', { amount: money(mine.share) })"
                saveable
                file-name="niddeaw-cup.png"
                class="w-full"
              />
              <div v-else class="flex h-56 w-56 items-center justify-center rounded-xl bg-white/5 text-sm text-white/50">{{ t('common.loading') }}</div>
              <span class="text-xs text-white/50">{{ t('cup.line.ownAccount') }}</span>
            </div>
            <label class="cta flex min-h-14 cursor-pointer items-center justify-center rounded-2xl font-display text-base font-bold" :class="{ 'is-busy': busy === 'slip' }">
              {{ busy === 'slip' ? t('cup.line.sending') : t('cup.line.attachSlip') }}
              <input type="file" accept="image/*" class="sr-only" :disabled="busy === 'slip'" @change="attach" />
            </label>
          </template>
          <div v-else-if="mine?.pay_status === 'slip_sent'" class="flex items-center gap-3 rounded-2xl bg-white/5 p-3 text-sm">
            <img v-if="mine.slip_url" :src="mine.slip_url" :alt="t('cup.line.yourSlip')" class="h-16 w-12 rounded border border-white/15 object-cover" />
            <span class="text-white/75">{{ t('cup.line.slipWaiting') }}</span>
            <label class="ml-auto min-h-11 cursor-pointer px-2 py-3 text-xs text-white/60 underline">
              {{ t('cup.line.resend') }}
              <input type="file" accept="image/*" class="sr-only" @change="attach" />
            </label>
          </div>

          <p v-if="problem" class="text-sm text-status-error" role="alert">{{ problem }}</p>

          <!-- rename while entries are open; pulling out goes through the organisers -->
          <template v-if="cup.taking_entries && team.status !== 'invited'">
            <div v-if="renaming" class="flex gap-2">
              <input v-model="newName" maxlength="40" :class="INPUT" :aria-label="t('cup.teamName')" />
              <button type="button" class="glass-pill shrink-0" :disabled="busy === 'rename'" @click="rename">{{ t('cup.line.save') }}</button>
            </div>
            <div class="flex flex-wrap justify-center gap-x-4 text-xs text-white/55">
              <button v-if="!renaming" type="button" class="min-h-11 underline" @click="renaming = true; newName = team.name">{{ t('cup.line.rename') }}</button>
            </div>
            <p class="text-center text-xs text-white/45">{{ t('cup.line.withdrawByAdmin') }}</p>
          </template>
        </div>

        <!-- called to a court: the one thing that matters right now -->
        <div v-if="calledNow" class="called flex flex-col items-center gap-1 rounded-3xl p-5 text-center" role="alert">
          <span class="font-display text-sm font-bold tracking-[3px]">{{ t('cup.day.calledYou') }}</span>
          <span class="font-display text-4xl font-bold">{{ t('cup.day.court', { n: calledNow.court }) }}</span>
          <span class="text-sm">#{{ calledNow.match_no }} · {{ t('cup.day.calledHint') }}</span>
        </div>

        <!-- my team's day: where it stands, the next match, its group and its results -->
        <div v-if="team.status === 'confirmed'" class="world-card flex flex-col gap-3 p-4">
          <div class="flex flex-wrap items-center gap-2">
            <h3 class="font-display text-base font-bold">{{ t('cup.schedule.mine') }}</h3>
            <span v-if="cup.schedule_published && standing" class="ml-auto rounded-full px-2.5 py-1 font-display text-[11px] font-bold" :class="STANDING_CLASS[standing.kind]">
              {{ standing.text }}
            </span>
          </div>
          <p v-if="!cup.schedule_published" class="text-sm text-white/70">
            <span class="mr-1 rounded-full border border-[#ffe14d] px-2 py-0.5 font-display text-[11px] font-bold tracking-[2px] text-[#ffe14d]">COMING SOON</span>
            {{ t('cup.schedule.soon') }}
          </p>
          <template v-else>
            <div v-if="nextMatch && !calledNow">
              <p class="mb-1.5 text-xs font-semibold text-[#7ff0b4]">{{ t('cup.line.nextMatch') }}</p>
              <CupMatchCard :match="nextMatch" :mine-id="team.id" />
            </div>
            <p v-else-if="!nextMatch && standing?.kind !== 'out' && standing?.kind !== 'champion'" class="rounded-xl bg-white/5 p-3 text-sm text-white/70">
              {{ t('cup.line.waitingDraw') }}
            </p>

            <CupStandings v-if="myGroup?.standings.length" :label="myGroup.label" :teams="myGroup.teams" :standings="myGroup.standings" :mine-id="team.id" :bands="myLevel ? rankBands(myLevel) : undefined" />
            <div v-else-if="myGroup" class="rounded-xl bg-white/5 p-2.5">
              <p class="mb-1.5 font-display text-sm font-bold text-[#ff6cc0]">{{ t('cup.draw.group', { g: myGroup.label }) }}</p>
              <div class="flex flex-col gap-2">
                <CupTeamLine v-for="(x, i) in myGroup.teams" :key="x.id ?? x.name" :name="x.name" :players="x.players" :prefix="`${myGroup.label}${i + 1}`" :mine="x.id === team.id" />
              </div>
            </div>

            <div v-if="laterMatches.length">
              <p class="mb-1.5 text-xs font-semibold text-white/70">{{ t('cup.line.laterMatches') }}</p>
              <div class="flex flex-col gap-1.5">
                <CupMatchRow v-for="m in laterMatches" :key="m.id" :match="m" show-round />
              </div>
            </div>
            <div v-if="playedMatches.length">
              <p class="mb-1.5 text-xs font-semibold text-white/70">{{ t('cup.line.played') }}</p>
              <div class="flex flex-col gap-1.5">
                <CupMatchRow v-for="m in playedMatches" :key="m.id" :match="m" show-round />
              </div>
            </div>
            <p class="text-xs text-white/50">{{ t('cup.schedule.mineHint') }}</p>
            <RouterLink
              :to="{ path: '/tournament', query: { level: team.level_id, stage: koMine ? 'ko' : 'group' } }"
              class="flex min-h-11 items-center justify-center rounded-full border border-white/15 text-sm text-white/80"
            >
              {{ t('cup.line.seeAll') }} →
            </RouterLink>
          </template>
        </div>

        <p v-if="rulesOf(team.level_id)" class="text-center text-xs text-[#ffd34d]">{{ t('cup.rulesLine', { rules: rulesOf(team.level_id) }) }}</p>
      </template>
    </template>
  </section>
</template>


<style scoped>
.called {
  background: linear-gradient(#7ff0b4, #2fbf7f);
  color: #06281a;
  box-shadow: 0 10px 28px rgb(47 191 127 / 0.45);
}
/* the screen's one next step, as on the bill screen (LineBillPay.vue) */
.cta {
  background: linear-gradient(#ff8fd0, #ea4ca4);
  color: #1a0410;
  box-shadow: 0 8px 22px rgb(234 76 164 / 0.45);
}
.cta.is-busy,
.cta:disabled {
  background: #3a1d3a;
  color: rgb(255 255 255 / 0.5);
  box-shadow: none;
}
</style>
