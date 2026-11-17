<script setup lang="ts">
/**
 * Paper for the day, for when the hall's wifi gives out or a court wants a
 * sheet to sign. Two things to print, on A4:
 *  - the match list: each level's matches in order, with the time, the
 *    teams, and empty boxes for the court and the score;
 *  - a score sheet per match, two to a page: the two teams and their
 *    players (nickname and real name, so the desk can check who is on court),
 *    a box per set, the shuttles used, and lines for the umpire's and both
 *    captains' signatures — the sheet the desk enters results from.
 * Real names come from the admin team list: this page is for admins only.
 * Pick a level, or only the matches not yet played, then print.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { tournamentAdmin, type AdminTeam, type CupMatch, type GameDay } from '@/api/tournament'
import { apiErrorMessage } from '@/api/errors'
import { useTournamentPick } from '@/composables/useTournamentPick'
import { clock, roundLabel, sideLabel } from '@/utils/cupMatch'
import { formatDateWithWeekday } from '@/utils/format'
import type { Locale } from '@/i18n'

const { t, locale } = useI18n()
const { all, picked, load } = useTournamentPick()
const day = ref<GameDay | null>(null)
const teams = ref<AdminTeam[]>([])
const problem = ref('')

async function refresh(): Promise<void> {
  problem.value = ''
  try {
    if (!all.value.length) await load()
    if (picked.value) [day.value, teams.value] = await Promise.all([tournamentAdmin.day(picked.value.id), tournamentAdmin.teams(picked.value.id)])
  } catch (e) {
    problem.value = apiErrorMessage(e, t('cup.admin.loadFailed'))
  }
}
watch(() => picked.value?.id, () => void refresh(), { immediate: true })

const what = ref<'list' | 'sheets'>('list')
const levelId = ref('')
const notPlayed = ref(true)
const levels = computed(() => {
  const seen = new Map<string, string>()
  for (const m of day.value?.matches ?? []) seen.set(m.level_id, m.level_name)
  return [...seen].map(([id, name]) => ({ id, name }))
})
const chosen = computed(() =>
  (day.value?.matches ?? [])
    .filter((m) => (!levelId.value || m.level_id === levelId.value) && (!notPlayed.value || m.status !== 'done'))
    .sort((a, b) => a.match_no - b.match_no),
)
const byLevel = computed(() => levels.value.map((l) => ({ ...l, matches: chosen.value.filter((m) => m.level_id === l.id) })).filter((l) => l.matches.length))
/** Two sheets to an A4 page. */
const pages = computed(() => {
  const out: CupMatch[][] = []
  for (let i = 0; i < chosen.value.length; i += 2) out.push(chosen.value.slice(i, i + 2))
  return out
})
const sets = (m: CupMatch): number => (m.stage === 'group' ? 2 : 3)
/** Each player of a side: nickname and real name, captain first. Before the
 *  team is known ("winner of #37") there is no one to list. */
interface Person {
  nickname: string
  realName: string
}
const people = computed(() => {
  const out = new Map<string, Person[]>()
  for (const tm of teams.value) {
    const order = [...tm.entrants].sort((a, b) => (a.role === b.role ? 0 : a.role === 'captain' ? -1 : 1))
    out.set(tm.id, order.map((e) => ({ nickname: e.nickname, realName: [e.first_name, e.last_name].filter(Boolean).join(' ') })))
  }
  return out
})
function players(m: CupMatch, side: 'a' | 'b'): Person[] {
  const id = m[side].team_id
  if (!id) return []
  return people.value.get(id) ?? m[side].players.map((p) => ({ nickname: p.nickname, realName: '' }))
}
const score = (m: CupMatch): string =>
  m.status !== 'done' ? '' : m.walkover ? t('cup.view.wo') : (m.sets ?? []).map(([a, b]) => `${a}-${b}`).join(' ')
const date = computed(() => (picked.value ? formatDateWithWeekday(picked.value.starts_on, locale.value as Locale) : ''))
const print = (): void => window.print()
</script>

<template>
  <div class="print-page min-h-dvh px-4 py-5">
    <!-- the controls: not printed -->
    <div class="no-print mx-auto mb-5 flex max-w-[210mm] flex-col gap-3 text-white">
      <RouterLink :to="{ name: 'admin-tournament-day' }" class="text-sm text-white/70 underline">← {{ t('admin.nav.tDay') }}</RouterLink>
      <h1 class="font-display text-xl font-bold">{{ t('cup.print.title') }}</h1>
      <p v-if="problem" class="text-sm text-status-error" role="alert">{{ problem }}</p>
      <div class="grid grid-cols-2 gap-1 rounded-full border border-white/15 p-1" role="tablist">
        <button
          v-for="x in (['list', 'sheets'] as const)"
          :key="x"
          type="button"
          role="tab"
          :aria-selected="what === x"
          class="min-h-11 rounded-full text-sm font-semibold"
          :class="what === x ? 'bg-brand-pink text-brand-black' : 'text-white/70'"
          @click="what = x"
        >
          {{ t(`cup.print.${x}`) }}
        </button>
      </div>
      <div class="flex flex-wrap items-center gap-3 text-sm">
        <select v-model="levelId" :aria-label="t('cup.level')" class="min-h-11 rounded-lg border border-white/20 bg-brand-black px-3 text-white">
          <option value="">{{ t('cup.print.allLevels') }}</option>
          <option v-for="l in levels" :key="l.id" :value="l.id">{{ l.name }}</option>
        </select>
        <label class="flex min-h-11 items-center gap-2">
          <input v-model="notPlayed" type="checkbox" class="h-5 w-5" />
          {{ t('cup.print.notPlayed') }}
        </label>
        <button type="button" class="tap ml-auto rounded-full bg-brand-pink px-6 font-semibold text-brand-black disabled:opacity-40" :disabled="!chosen.length" @click="print">
          {{ t('cup.print.print', { n: what === 'list' ? chosen.length : pages.length }) }}
        </button>
      </div>
      <p class="text-xs text-white/55">{{ what === 'list' ? t('cup.print.listHint') : t('cup.print.sheetsHint') }}</p>
      <p v-if="day && !chosen.length" class="text-sm text-white/60">{{ t('cup.print.nothing') }}</p>
    </div>

    <!-- the match list -->
    <div v-if="what === 'list' && day && chosen.length" class="paper mx-auto">
      <header class="mb-3 flex items-baseline gap-3 border-b-2 border-black pb-1">
        <b class="text-lg">{{ picked?.name }}</b>
        <span class="text-sm">{{ date }}</span>
        <span class="ml-auto text-xs">{{ t('cup.print.list') }}</span>
      </header>
      <section v-for="l in byLevel" :key="l.id" class="mb-4">
        <h2 class="mb-1 text-base font-bold">{{ l.name }}</h2>
        <table class="w-full border-collapse text-[11px]">
          <thead>
            <tr>
              <th class="w-10">#</th>
              <th class="w-12">{{ t('cup.print.time') }}</th>
              <th class="w-28">{{ t('cup.print.round') }}</th>
              <th>{{ t('cup.print.teamA') }}</th>
              <th>{{ t('cup.print.teamB') }}</th>
              <th class="w-12">{{ t('cup.print.court') }}</th>
              <th class="w-24">{{ t('cup.print.score') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in l.matches" :key="m.id">
              <td class="text-center font-bold">{{ m.match_no }}</td>
              <td class="text-center">{{ clock(m.est_start) }}</td>
              <td>{{ roundLabel(m, t) }}</td>
              <td v-for="side in (['a', 'b'] as const)" :key="side">
                <b class="block">{{ sideLabel(m[side], t) }}</b>
                <span v-for="p in players(m, side)" :key="p.nickname" class="block text-[10px] leading-tight">{{ p.nickname }}<template v-if="p.realName"> ({{ p.realName }})</template></span>
              </td>
              <td class="text-center">{{ m.court ?? '' }}</td>
              <td class="text-center">{{ score(m) }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>

    <!-- the score sheets, two to a page -->
    <div v-if="what === 'sheets' && day">
      <div v-for="(page, i) in pages" :key="i" class="paper sheet-page mx-auto mb-4">
        <article v-for="m in page" :key="m.id" class="sheet">
          <header class="flex items-baseline gap-3 border-b-2 border-black pb-1">
            <b class="text-2xl">#{{ m.match_no }}</b>
            <span class="text-sm font-semibold">{{ m.level_name }} · {{ roundLabel(m, t) }}</span>
            <span class="ml-auto text-xs">{{ picked?.name }}</span>
          </header>
          <p class="mt-1 flex flex-wrap gap-x-6 text-xs">
            <span>{{ t('cup.print.court') }} ______</span>
            <span>{{ t('cup.print.time') }} {{ clock(m.est_start) || '______' }}</span>
            <span>{{ m.stage === 'group' ? t('cup.day.groupRule') : t('cup.day.koRule') }}</span>
          </p>
          <table class="mt-2 w-full border-collapse">
            <thead>
              <tr>
                <th class="text-left">{{ t('cup.print.team') }}</th>
                <th v-for="n in sets(m)" :key="n" class="w-20">{{ t('cup.day.set', { n }) }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="side in (['a', 'b'] as const)" :key="side">
                <td class="h-14">
                  <b class="block text-base">{{ sideLabel(m[side], t) }}</b>
                  <span v-for="p in players(m, side)" :key="p.nickname" class="block text-xs leading-snug">
                    <b>{{ p.nickname }}</b><template v-if="p.realName"> · {{ p.realName }}</template>
                  </span>
                </td>
                <td v-for="n in sets(m)" :key="n" />
              </tr>
            </tbody>
          </table>
          <p class="mt-2 text-xs">{{ t('cup.print.winner') }} ________________________ &nbsp; {{ t('cup.day.shuttles') }} ______</p>
          <div class="mt-6 grid grid-cols-3 gap-4 text-center text-[11px]">
            <p class="border-t border-black pt-1">{{ t('cup.print.umpire') }}</p>
            <p class="border-t border-black pt-1">{{ t('cup.print.captain', { team: sideLabel(m.a, t) }) }}</p>
            <p class="border-t border-black pt-1">{{ t('cup.print.captain', { team: sideLabel(m.b, t) }) }}</p>
          </div>
        </article>
      </div>
    </div>
  </div>
</template>

<style scoped>
.paper {
  width: 100%;
  max-width: 210mm;
  background: #fff;
  color: #000;
  padding: 10mm;
}
table th,
table td {
  border: 1px solid #000;
  padding: 3px 5px;
}
.sheet-page {
  display: flex;
  flex-direction: column;
  gap: 10mm;
}
.sheet + .sheet {
  border-top: 1px dashed #000;
  padding-top: 10mm;
}

@media print {
  @page {
    size: A4;
    margin: 0;
  }
  .no-print {
    display: none !important;
  }
  .print-page {
    padding: 0;
    min-height: 0;
  }
  .paper {
    max-width: none;
    margin: 0;
  }
  .sheet-page {
    height: 296mm;
    break-after: page;
  }
  .sheet-page:last-child {
    break-after: auto;
  }
  .sheet {
    height: calc(50% - 5mm);
  }
}
</style>

<style>
/* On paper, only the sheets: none of the site around them. */
@media print {
  body {
    background: #fff !important;
  }
  .admin-world > :not(.print-page) {
    display: none !important;
  }
  .admin-world::before,
  .admin-world::after {
    display: none !important;
  }
}
</style>
