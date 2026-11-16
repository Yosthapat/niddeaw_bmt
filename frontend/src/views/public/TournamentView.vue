<script setup lang="ts">
/**
 * The tournament. Before any is announced: a page that says it's coming
 * and where to hear first. Once one is open: the event, its levels and how
 * full each is, the teams that hold a place (nicknames only — never a real
 * name or phone), and the way in through LINE.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import TierMascot from '@/components/players/TierMascot.vue'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'
import { getPublicTournament, type PublicTournament } from '@/api/tournament'
import { getLineConfig } from '@/api/line'
import { formatDateTime, formatDateWithWeekday, money } from '@/utils/format'
import type { Locale } from '@/i18n'
import CupTeamLine from '@/components/cup/CupTeamLine.vue'
import CupStandings from '@/components/cup/CupStandings.vue'
import CupMatchRow from '@/components/cup/CupMatchRow.vue'
import CupBracket from '@/components/cup/CupBracket.vue'
import { rankBands } from '@/utils/cupMatch'
import { usePolling } from '@/composables/usePolling'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const cup = ref<PublicTournament | null>(null)
const loaded = ref(false)
const lineHref = ref('https://line.me/R/ti/p/@369iojcn')

async function reload(): Promise<void> {
  try {
    cup.value = await getPublicTournament()
  } catch {
    if (!loaded.value) cup.value = null // the "coming soon" page, as before
  } finally {
    loaded.value = true
  }
}
// On the day, the board and results follow the desk without a refresh.
usePolling(async () => {
  if (cup.value?.schedule_published) await reload()
}, 20000)
const live = computed(() => (cup.value?.matches ?? []).filter((m) => m.status === 'on_court').sort((a, b) => (a.court ?? 0) - (b.court ?? 0)))

onMounted(async () => {
  await reload()
  try {
    const config = await getLineConfig()
    // LIFF adds the path to the endpoint: this opens /line/tournament in LINE
    if (config.enabled && config.liff_id) lineHref.value = `https://liff.line.me/${config.liff_id}/tournament`
  } catch {
    /* the OA link stays */
  }
})

// The level on screen: ?level=… (so a level's page can be shared in a
// group chat), else the first level anyone has signed up for.
const shown = computed(() => {
  const levels = cup.value?.levels ?? []
  const asked = typeof route.query.level === 'string' ? route.query.level : ''
  return levels.find((lv) => lv.id === asked) ?? levels.find((lv) => lv.seats_taken > 0) ?? levels[0] ?? null
})
function choose(id: string): void {
  void router.replace({ query: { ...route.query, level: id } })
}
// --- one level, three stages ---------------------------------------------------
type Stage = 'group' | 'ko' | 'results'
const STAGES: Stage[] = ['group', 'ko', 'results']
const mine = computed(() => (cup.value?.matches ?? []).filter((m) => m.level_id === shown.value?.id))
const groupMatches = computed(() => mine.value.filter((m) => m.stage === 'group'))
const koMatches = computed(() => mine.value.filter((m) => m.stage === 'ko'))
const doneMatches = computed(() =>
  mine.value
    .filter((m) => m.status === 'done')
    .sort((a, b) => (b.finished_at ?? '').localeCompare(a.finished_at ?? '') || b.match_no - a.match_no),
)
/** The knockout is where the day is once its first teams are known. */
const koUnderway = computed(() => koMatches.value.some((m) => m.status !== 'scheduled' || (m.a.team_id && m.b.team_id)))
const stage = computed<Stage>(() => {
  const asked = route.query.stage
  if (typeof asked === 'string' && (STAGES as string[]).includes(asked)) return asked as Stage
  return koUnderway.value ? 'ko' : 'group'
})
function pickStage(s: Stage): void {
  void router.replace({ query: { ...route.query, stage: s } })
}
const stageCount = (s: Stage): string => {
  if (!cup.value?.schedule_published) return ''
  if (s === 'group') return `${groupMatches.value.filter((m) => m.status === 'done').length}/${groupMatches.value.length}`
  if (s === 'ko') return koMatches.value.length ? `${koMatches.value.filter((m) => m.status === 'done').length}/${koMatches.value.length}` : ''
  return doneMatches.value.length ? String(doneMatches.value.length) : ''
}

// group stage: each group with its own matches
const groupsWithMatches = computed(() =>
  (shown.value?.groups ?? []).map((g) => {
    const ms = groupMatches.value.filter((m) => m.group_label === g.label).sort((a, b) => a.match_no - b.match_no)
    return { ...g, matches: ms, done: ms.filter((m) => m.status === 'done').length }
  }),
)
function jumpTo(label: string): void {
  document.getElementById(`cup-group-${label}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

// knockout: upper or lower bracket
const bracketPick = ref<'upper' | 'lower'>('upper')
const brackets = computed(() => (['upper', 'lower'] as const).filter((b) => koMatches.value.some((m) => m.bracket === b)))
const bracketShown = computed(() => (brackets.value.includes(bracketPick.value) ? bracketPick.value : (brackets.value[0] ?? 'upper')))
const bracketMatches = computed(() => koMatches.value.filter((m) => m.bracket === bracketShown.value))
function formatOf(maxTeams: number, cut: boolean): string {
  if (maxTeams === 24) return cut ? t('cup.admin.br24cut') : t('cup.admin.br24')
  return t('cup.admin.brEven', { n: maxTeams / 2 })
}

// results: the champions, then every result, latest first
const resultFilter = ref<'all' | 'group' | 'ko'>('all')
const results = computed(() => doneMatches.value.filter((m) => resultFilter.value === 'all' || m.stage === resultFilter.value))
const podiums = computed(() =>
  (['upper', 'lower'] as const).flatMap((b) => {
    const ko = koMatches.value.filter((m) => m.bracket === b)
    if (!ko.length) return []
    const final = ko.reduce((x, y) => (y.round < x.round || (y.round === x.round && y.match_no > x.match_no) ? y : x))
    if (final.status !== 'done' || (final.winner !== 'a' && final.winner !== 'b')) return []
    const loser = final.winner === 'a' ? 'b' : 'a'
    return [{ bracket: b, champion: final[final.winner], runnerUp: final[loser] }]
  }),
)

const perPlayer = computed(() => (cup.value ? Math.ceil((cup.value.entry_fee + cup.value.shuttle_fee) / 2) : 0))
const day = (iso: string): string => formatDateWithWeekday(iso, locale.value as Locale)
const when = (iso: string): string => formatDateTime(iso, locale.value as Locale)
function range(min: number | null, max: number | null): string {
  if (min === null && max !== null) return t('cup.eloBelow', { n: max })
  if (min !== null && max === null) return t('cup.eloFrom', { n: min })
  if (min !== null && max !== null) return `ELO ${min}–${max - 1}`
  return ''
}
</script>

<template>
  <main v-if="cup" class="relative isolate overflow-x-clip">
    <div class="pointer-events-none absolute inset-0 -z-10" aria-hidden="true">
      <div class="absolute inset-0 bg-[radial-gradient(80%_50%_at_50%_20%,#5a1a7a_0%,#1a0838_55%,#0a0416_80%)]" />
    </div>
    <div class="mx-auto flex max-w-2xl flex-col gap-4 px-4 pt-4 pb-12">
      <RouterLink to="/" class="inline-flex min-h-11 items-center gap-1 self-start text-sm text-white/75 hover:text-white">
        <span aria-hidden="true">←</span> {{ t('shop.backHome') }}
      </RouterLink>

      <header class="text-center">
        <p class="font-display text-[13px] font-bold tracking-[3px] text-[#ffe14d]">NIDDEAW CUP</p>
        <h1 class="t-glow mt-1 font-display text-[34px] leading-tight font-bold">{{ cup.name }}</h1>
        <p class="mt-1 text-[15px] text-white/85">{{ day(cup.starts_on) }}<template v-if="cup.venue"> · {{ cup.venue }}</template></p>
      </header>

      <section class="t-plan flex-col !items-stretch gap-1.5 text-sm">
        <p>{{ t('cup.feeLine', { amount: money(perPlayer) }) }}</p>
        <p class="text-white/70">{{ t('cup.couponLine', { n: cup.coupons_per_set }) }}</p>
        <p class="text-white/70">{{ t('cup.whoCan', { n: cup.min_games }) }}</p>
        <p class="text-white/70">{{ t('cup.levelRule') }}</p>
        <p class="font-semibold" :class="cup.taking_entries ? 'text-[#7ff0b4]' : 'text-white/60'">
          {{ cup.taking_entries ? t('cup.closesAt', { at: when(cup.closes_at) }) : t('cup.closed') }}
        </p>
      </section>

      <a
        v-if="cup.taking_entries"
        :href="lineHref"
        target="_blank"
        rel="noopener noreferrer"
        class="t-line flex h-[54px] w-full items-center justify-center gap-2 rounded-[14px] font-display text-base font-bold"
      >
        {{ t('cup.signUpInLine') }}
      </a>

      <!-- on court now, across every level -->
      <section v-if="live.length" class="t-plan flex-col !items-stretch gap-2 !border-[#7ff0b4]/40">
        <h2 class="flex items-center gap-2 font-display text-lg font-bold">
          <span class="inline-block h-2.5 w-2.5 animate-pulse rounded-full bg-[#7ff0b4]" aria-hidden="true" />
          {{ t('cup.day.liveTitle') }}
        </h2>
        <!-- one tidy row each, so a full hall of courts doesn't push the levels off the screen -->
        <div class="grid gap-1.5 sm:grid-cols-2">
          <CupMatchRow v-for="m in live" :key="m.id" :match="m" show-level />
        </div>
      </section>

      <!-- one level at a time -->
      <div class="sticky top-[calc(var(--header-h)+6px)] z-10 -mx-4 overflow-x-auto px-4 pb-1" role="tablist" :aria-label="t('cup.level')">
        <div class="flex w-max gap-1.5 rounded-full border border-white/12 bg-[#1a0838]/90 p-1 backdrop-blur">
          <button
            v-for="lv in cup.levels"
            :key="lv.id"
            type="button"
            role="tab"
            class="flex min-h-11 items-center gap-1.5 rounded-full px-4 text-sm whitespace-nowrap"
            :class="shown?.id === lv.id ? 'bg-[#ff6cc0] font-bold text-[#1a0838]' : 'text-white/80'"
            :aria-selected="shown?.id === lv.id"
            @click="choose(lv.id)"
          >
            {{ lv.name }}
            <span class="text-xs" :class="shown?.id === lv.id ? 'text-[#1a0838]/70' : 'text-white/50'">{{ lv.seats_taken }}/{{ lv.max_teams }}</span>
          </button>
        </div>
      </div>

      <template v-if="shown">
        <!-- the level -->
        <section class="t-plan flex-col !items-stretch gap-2">
          <div class="flex flex-wrap items-baseline gap-2">
            <h2 class="font-display text-xl font-bold">{{ shown.name }}</h2>
            <span class="text-xs text-white/60">{{ range(shown.min_elo, shown.max_elo) }}</span>
            <span class="ml-auto font-display text-sm font-bold">{{ t('cup.seats', { n: shown.seats_taken, max: shown.max_teams }) }}</span>
          </div>
          <div class="h-1.5 overflow-hidden rounded-full bg-white/10" aria-hidden="true">
            <div class="h-full rounded-full bg-[#ff6cc0]" :style="{ width: `${Math.min(100, (shown.seats_taken / shown.max_teams) * 100)}%` }" />
          </div>
          <p v-if="shown.rules" class="text-xs text-[#ffd34d]">{{ t('cup.rulesLine', { rules: shown.rules }) }}</p>
          <p v-if="shown.waitlist" class="text-xs text-[#c9a7ff]">{{ t('cup.waitlistCount', { n: shown.waitlist }) }}</p>
        </section>

        <!-- the level's three stages -->
        <div class="grid grid-cols-3 gap-1 rounded-2xl border border-white/12 bg-[#1a0838]/80 p-1" role="tablist" :aria-label="t('cup.view.stages')">
          <button
            v-for="s in STAGES"
            :key="s"
            type="button"
            role="tab"
            class="flex min-h-12 flex-col items-center justify-center rounded-xl px-1 leading-tight transition-colors"
            :class="stage === s ? 'bg-[linear-gradient(135deg,#ff6cc0,#c13cff)] text-white shadow-[0_6px_18px_-6px_rgb(255_108_192/0.7)]' : 'text-white/70 hover:text-white'"
            :aria-selected="stage === s"
            @click="pickStage(s)"
          >
            <span class="font-display text-[13px] font-bold">{{ t(`cup.view.stage.${s}`) }}</span>
            <span v-if="stageCount(s)" class="font-display text-[10px]" :class="stage === s ? 'text-white/85' : 'text-white/45'">{{ stageCount(s) }}</span>
          </button>
        </div>

        <!-- 1 · the group stage -->
        <template v-if="stage === 'group'">
          <template v-if="!cup.schedule_published">
            <section class="t-plan flex-col !items-center gap-1 py-4 text-center">
              <span class="t-blink rounded-full border border-[#ffe14d] px-3 py-1 font-display text-[12px] font-bold tracking-[3px] text-[#ffe14d]">COMING SOON</span>
              <h2 class="mt-1.5 font-display text-base font-bold">{{ t('cup.schedule.title') }}</h2>
              <p class="text-sm text-white/70">{{ t('cup.schedule.soon') }}</p>
            </section>
            <section class="t-plan flex-col !items-stretch gap-2">
              <h3 class="font-display text-base font-bold">{{ t('cup.teamsIn', { level: shown.name }) }}</h3>
              <ul v-if="shown.teams.length" class="grid gap-1.5 sm:grid-cols-2">
                <li v-for="team in shown.teams" :key="team.id ?? team.name" class="flex items-center gap-2 rounded-xl bg-white/5 px-2.5 py-2">
                  <div class="flex -space-x-2">
                    <PlayerAvatar v-for="p in team.players" :key="p.nickname" :name="p.nickname" :avatar-url="p.avatar_url" size="sm" round />
                  </div>
                  <div class="min-w-0">
                    <p class="truncate text-sm font-semibold">{{ team.name }}</p>
                    <p class="truncate text-xs text-white/60">{{ team.players.map((p) => p.nickname).join(' / ') }}</p>
                  </div>
                </li>
              </ul>
              <p v-else class="text-xs text-white/50">{{ t('cup.noTeamsYet') }}</p>
            </section>
          </template>
          <template v-else>
            <div v-if="groupsWithMatches.length > 2" class="-mx-4 overflow-x-auto px-4">
              <div class="flex w-max gap-1.5">
                <button
                  v-for="g in groupsWithMatches"
                  :key="g.label"
                  type="button"
                  class="min-h-9 rounded-full border border-white/15 px-3.5 font-display text-sm font-bold text-white/80 hover:border-[#ff6cc0]/60"
                  @click="jumpTo(g.label)"
                >
                  {{ t('cup.draw.group', { g: g.label }) }}
                </button>
              </div>
            </div>
            <section
              v-for="g in groupsWithMatches"
              :id="`cup-group-${g.label}`"
              :key="g.label"
              class="t-plan scroll-mt-40 flex-col !items-stretch gap-2.5"
            >
              <div class="flex items-center gap-2">
                <span class="flex h-9 w-9 items-center justify-center rounded-xl bg-[#ff6cc0]/20 font-display text-lg font-bold text-[#ff6cc0]">{{ g.label }}</span>
                <h3 class="font-display text-base font-bold">{{ t('cup.draw.group', { g: g.label }) }}</h3>
                <span class="ml-auto text-xs text-white/55">{{ t('cup.view.played', { n: g.done, of: g.matches.length }) }}</span>
              </div>
              <CupStandings v-if="g.standings.length" :label="g.label" :teams="g.teams" :standings="g.standings" :bands="rankBands(shown)" class="!bg-transparent !p-0 [&>p:first-child]:hidden" />
              <div v-else class="flex flex-col gap-2">
                <CupTeamLine v-for="(team, i) in g.teams" :key="team.id ?? team.name" :name="team.name" :players="team.players" :prefix="`${g.label}${i + 1}`" />
              </div>
              <details v-if="g.matches.length" class="group/m" :open="groupsWithMatches.length <= 2 || undefined">
                <summary class="flex min-h-10 cursor-pointer list-none items-center gap-1.5 rounded-lg px-1 text-xs font-semibold text-white/70 hover:text-white">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4 transition-transform group-open/m:rotate-90" aria-hidden="true"><path d="m9 6 6 6-6 6" /></svg>
                  {{ t('cup.view.groupMatches', { n: g.matches.length }) }}
                </summary>
                <div class="mt-1 flex flex-col gap-1.5">
                  <CupMatchRow v-for="m in g.matches" :key="m.id" :match="m" />
                </div>
              </details>
            </section>
            <p class="text-center text-xs text-white/50">{{ t('cup.schedule.estimate') }}</p>
          </template>
        </template>

        <!-- 2 · the knockout -->
        <template v-else-if="stage === 'ko'">
          <section v-if="!cup.schedule_published || !koMatches.length" class="t-plan flex-col !items-center gap-2 py-5 text-center">
            <svg viewBox="0 0 24 24" fill="none" stroke="#ff6cc0" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" class="h-10 w-10" aria-hidden="true">
              <path d="M4 6h5v4H4zM4 14h5v4H4zM15 10h5v4h-5zM9 8h3v8H9M12 12h3" />
            </svg>
            <h2 class="font-display text-base font-bold">{{ t('cup.view.koSoonTitle') }}</h2>
            <p class="text-sm text-white/70">{{ t('cup.view.koSoon') }}</p>
            <p class="rounded-full bg-white/8 px-3 py-1 text-xs text-white/80">{{ formatOf(shown.max_teams, shown.cut_24) }}</p>
          </section>
          <template v-else>
            <div v-if="brackets.length > 1" class="grid grid-cols-2 gap-1 rounded-full bg-black/30 p-1">
              <button
                v-for="b in brackets"
                :key="b"
                type="button"
                class="min-h-10 rounded-full font-display text-sm font-bold"
                :class="bracketShown === b ? (b === 'upper' ? 'bg-[#ffe14d] text-[#2a1a00]' : 'bg-[#c9a7ff] text-[#1a0838]') : 'text-white/65'"
                :aria-pressed="bracketShown === b"
                @click="bracketPick = b"
              >
                {{ t(`cup.bracket.${b}`) }}
              </button>
            </div>
            <section class="t-plan flex-col !items-stretch gap-2 !px-3">
              <p class="text-xs text-white/55">{{ koUnderway ? t('cup.view.koHint') : t('cup.view.koDrawHint') }}</p>
              <CupBracket :matches="bracketMatches" />
            </section>
          </template>
        </template>

        <!-- 3 · results -->
        <template v-else>
          <div v-if="podiums.length" class="grid gap-2 sm:grid-cols-2">
            <section v-for="p in podiums" :key="p.bracket" class="r-podium flex flex-col items-center gap-1 rounded-2xl border border-[#ffe14d]/45 p-4 text-center">
              <span class="font-display text-[11px] font-bold tracking-[2px] text-[#ffe14d]">{{ t('cup.view.championOf', { bracket: t(`cup.bracket.${p.bracket}`) }) }}</span>
              <svg viewBox="0 0 24 24" fill="none" stroke="#ffcf3f" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" class="h-9 w-9" aria-hidden="true">
                <path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0zM17 6h3v2a3 3 0 0 1-3 3M7 6H4v2a3 3 0 0 0 3 3" />
              </svg>
              <div class="flex -space-x-2">
                <PlayerAvatar v-for="pl in p.champion.players" :key="pl.nickname" :name="pl.nickname" :avatar-url="pl.avatar_url" size="md" round class="ring-2 ring-[#ffe14d]/70" />
              </div>
              <p class="font-display text-lg leading-tight font-bold">{{ p.champion.team_name }}</p>
              <p class="text-xs text-white/70">{{ p.champion.players.map((x) => x.nickname).join(' · ') }}</p>
              <p class="mt-1 text-xs text-white/55">{{ t('cup.view.runnerUp', { team: p.runnerUp.team_name ?? '—' }) }}</p>
            </section>
          </div>
          <section class="t-plan flex-col !items-stretch gap-2">
            <div class="flex flex-wrap items-center gap-2">
              <h3 class="font-display text-base font-bold">{{ t('cup.view.latest') }}</h3>
              <div class="ml-auto flex gap-1">
                <button
                  v-for="f in ['all', 'group', 'ko'] as const"
                  :key="f"
                  type="button"
                  class="min-h-8 rounded-full border px-3 text-xs"
                  :class="resultFilter === f ? 'border-[#ff6cc0] bg-[#ff6cc0]/20 font-semibold text-white' : 'border-white/15 text-white/65'"
                  :aria-pressed="resultFilter === f"
                  @click="resultFilter = f"
                >
                  {{ t(`cup.view.filter.${f}`) }}
                </button>
              </div>
            </div>
            <div v-if="results.length" class="flex flex-col gap-1.5">
              <CupMatchRow v-for="m in results" :key="m.id" :match="m" show-round />
            </div>
            <p v-else class="py-4 text-center text-sm text-white/55">{{ t('cup.view.noResults') }}</p>
          </section>
        </template>
      </template>
    </div>
  </main>

  <main v-else-if="loaded" class="relative isolate overflow-hidden">
    <!-- same world as the home hero: a sky, a sun, a neon floor -->
    <div class="pointer-events-none absolute inset-0 -z-10" aria-hidden="true">
      <div class="absolute inset-0 bg-[radial-gradient(80%_50%_at_50%_30%,#5a1a7a_0%,#1a0838_55%,#0a0416_80%)]" />
      <div class="absolute top-[110px] left-1/2 h-[260px] w-[260px] -translate-x-1/2 rounded-full bg-[linear-gradient(#ffe14d,#ff6cc0_55%,#9b2cff)] opacity-35 blur-[2px]" />
      <div class="t-floor absolute right-[-40%] bottom-0 left-[-40%] h-[330px]" />
      <div class="absolute inset-x-0 bottom-0 h-[420px] bg-[linear-gradient(rgb(10_4_22/0),#0a0416_85%)]" />
    </div>

    <div class="mx-auto flex max-w-md flex-col items-center gap-3.5 px-4 pt-4 pb-10 text-center">
      <RouterLink to="/" class="inline-flex min-h-11 items-center gap-1 self-start text-sm text-white/75 hover:text-white">
        <span aria-hidden="true">←</span> {{ t('shop.backHome') }}
      </RouterLink>

      <span class="t-blink rounded-full border border-[#ffe14d] px-3.5 py-1.5 font-display text-[13px] leading-none font-bold tracking-[3px] text-[#ffe14d]">
        COMING SOON
      </span>

      <!-- the cup, with the club's cat sitting on it -->
      <div class="t-float relative mt-10 h-[230px] w-[220px]">
        <svg viewBox="0 0 200 210" width="220" height="230" role="img" :aria-label="t('tournament.trophy')">
          <defs>
            <linearGradient id="t-cup" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stop-color="#fff3a8" />
              <stop offset=".45" stop-color="#ffcf3f" />
              <stop offset="1" stop-color="#b8740a" />
            </linearGradient>
          </defs>
          <path d="M52 40H148V78C148 112 126 134 100 134 74 134 52 112 52 78Z" fill="url(#t-cup)" stroke="#fff6c8" stroke-width="2" />
          <path d="M52 52H28C28 82 40 96 58 98M148 52h24c0 30-12 44-30 46" fill="none" stroke="#ffcf3f" stroke-width="8" stroke-linecap="round" />
          <rect x="90" y="134" width="20" height="30" fill="#e0a21c" />
          <rect x="64" y="164" width="72" height="16" rx="4" fill="#ffcf3f" />
          <rect x="54" y="180" width="92" height="22" rx="6" fill="#2a1450" stroke="#ff6cc0" stroke-width="2" />
          <text x="100" y="196" text-anchor="middle" font-family="Chakra Petch, sans-serif" font-weight="700" font-size="12" fill="#ff6cc0">NIDDEAW CUP</text>
          <path d="m84 70 16-14 16 14" fill="none" stroke="#fff6c8" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <img
          src="/hero/cat-color.webp"
          alt=""
          width="92"
          height="92"
          class="absolute top-[-48px] left-16 h-[92px] w-[92px] object-contain drop-shadow-[0_8px_10px_rgb(6_0_20/0.6)]"
        />
      </div>

      <h1 class="t-glow font-display text-[40px] leading-none font-bold">{{ t('nav.tournament') }}</h1>
      <p class="text-[15px] font-light text-white/85">{{ t('tournament.lead') }}</p>

      <ul class="mt-1.5 flex w-full flex-col gap-2 text-left">
        <li class="t-plan">
          <TierMascot tier="milk" :size="36" :interactive="false" />
          <span>{{ t('tournament.plan1') }}</span>
        </li>
        <li class="t-plan">
          <svg viewBox="0 0 24 24" fill="none" stroke="#ff6cc0" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" class="h-9 w-9 flex-none" aria-hidden="true">
            <path d="M4 6h5v4H4zM4 14h5v4H4zM15 10h5v4h-5zM9 8h3v8H9M12 12h3" />
          </svg>
          <span>{{ t('tournament.plan2') }}</span>
        </li>
        <li class="t-plan">
          <svg viewBox="0 0 24 24" fill="none" stroke="#ffe14d" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" class="h-9 w-9 flex-none" aria-hidden="true">
            <path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0zM17 6h3v2a3 3 0 0 1-3 3M7 6H4v2a3 3 0 0 0 3 3" />
          </svg>
          <span>{{ t('tournament.plan3') }}</span>
        </li>
      </ul>

      <a
        href="https://line.me/R/ti/p/@369iojcn"
        target="_blank"
        rel="noopener noreferrer"
        class="t-line mt-4 flex h-[54px] w-full items-center justify-center gap-2 rounded-[14px] font-display text-base font-bold"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5" aria-hidden="true">
          <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0" />
        </svg>
        {{ t('tournament.notify') }}
      </a>
      <p class="text-xs text-white/60">{{ t('tournament.notifyHint') }}</p>
    </div>
  </main>
</template>

<style scoped>
.t-floor {
  background-image:
    linear-gradient(rgb(255 108 192 / 0.55) 2px, transparent 2px),
    linear-gradient(90deg, rgb(255 108 192 / 0.55) 2px, transparent 2px);
  background-size: 40px 40px;
  transform: perspective(300px) rotateX(58deg);
  transform-origin: 50% 100%;
  animation: t-floor 2.2s linear infinite;
}
@keyframes t-floor {
  to {
    background-position: 0 40px, 0 0;
  }
}
.t-float {
  animation: t-float 6s ease-in-out infinite;
}
@keyframes t-float {
  50% {
    transform: translateY(-6px);
  }
}
.t-blink {
  animation: t-blink 1.4s ease-in-out infinite;
}
@keyframes t-blink {
  50% {
    opacity: 0.45;
  }
}
.t-glow {
  text-shadow:
    0 0 18px rgb(255 108 192 / 0.8),
    0 0 2px #fff;
}
.t-plan {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid rgb(255 255 255 / 0.14);
  border-radius: 14px;
  background: rgb(255 255 255 / 0.06);
  font-size: 14px;
  backdrop-filter: blur(10px);
}
/* a champion's card: gold light from above */
.r-podium {
  background: radial-gradient(120% 80% at 50% 0%, rgb(255 225 77 / 0.2), rgb(255 255 255 / 0.04) 70%);
  box-shadow: 0 0 30px -6px rgb(255 207 63 / 0.35);
}
.t-line {
  background: #037f36;
  box-shadow:
    0 5px 0 #014a1f,
    0 12px 24px rgb(6 199 85 / 0.35);
  color: #fff;
}
.t-line:active {
  transform: translateY(3px);
  box-shadow: 0 2px 0 #014a1f;
}
@media (prefers-reduced-motion: reduce) {
  .t-floor,
  .t-float,
  .t-blink {
    animation: none;
  }
}
</style>
