<script setup lang="ts">
/**
 * Finding a team on /tournament, and keeping one as "my team".
 *
 * One search box finds any team that holds a place by its name or a
 * player's nickname; a result jumps to its level, or is starred as mine.
 * The starred team (kept on this phone) gets a card at the top — where it
 * stands and its next match — and is highlighted everywhere on the page.
 * No sign-in: it's only a bookmark.
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { CupMatch, PublicTeam, PublicTournament } from '@/api/tournament'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'
import CupMatchRow from './CupMatchRow.vue'
import { roundLabel } from '@/utils/cupMatch'

const props = defineProps<{ cup: PublicTournament }>()
const mine = defineModel<string | null>('mine', { required: true })
const emit = defineEmits<{ show: [levelId: string, stage: 'group' | 'ko' | 'results'] }>()
const { t } = useI18n()

interface Found {
  team: PublicTeam & { id: string }
  levelId: string
  levelName: string
  group: string | null
}
const all = computed<Found[]>(() =>
  props.cup.levels.flatMap((lv) =>
    lv.teams
      .filter((tm): tm is PublicTeam & { id: string } => !!tm.id)
      .map((tm) => ({
        team: tm,
        levelId: lv.id,
        levelName: lv.name,
        group: lv.groups.find((g) => g.teams.some((x) => x.id === tm.id))?.label ?? null,
      })),
  ),
)

const query = ref('')
const results = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return []
  return all.value
    .filter((f) => f.team.name.toLowerCase().includes(q) || f.team.players.some((p) => p.nickname.toLowerCase().includes(q)))
    .slice(0, 8)
})

const myTeam = computed(() => all.value.find((f) => f.team.id === mine.value) ?? null)
const myMatches = computed(() =>
  props.cup.matches.filter((m) => m.a.team_id === mine.value || m.b.team_id === mine.value).sort((a, b) => a.match_no - b.match_no),
)
const nextMatch = computed<CupMatch | null>(() => myMatches.value.find((m) => m.status === 'on_court') ?? myMatches.value.find((m) => m.status === 'scheduled') ?? null)
const lastKo = computed(() => [...myMatches.value].reverse().find((m) => m.stage === 'ko') ?? null)
/** Where my team stands, in a few words. */
const standing = computed(() => {
  const f = myTeam.value
  if (!f) return ''
  const ko = lastKo.value
  if (ko) {
    const side = ko.a.team_id === mine.value ? 'a' : 'b'
    if (ko.status === 'done' && ko.winner && ko.winner !== side) return t('cup.line.out')
    if (ko.status === 'done' && ko.winner === side && ko.round === 2) return t('cup.line.champion', { bracket: t(`cup.bracket.${ko.bracket ?? 'upper'}`) })
    return roundLabel(ko, t)
  }
  const row = props.cup.levels.find((lv) => lv.id === f.levelId)?.groups.find((g) => g.label === f.group)?.standings.find((r) => r.team_id === mine.value)
  if (f.group && row?.played) return t('cup.line.groupPlace', { g: f.group, n: row.rank })
  if (f.group) return t('cup.draw.group', { g: f.group })
  return t('cup.my.waitingDraw')
})

function star(f: Found): void {
  mine.value = mine.value === f.team.id ? null : f.team.id
  query.value = ''
}
function go(f: Found): void {
  emit('show', f.levelId, lastKo.value && f.team.id === mine.value ? 'ko' : 'group')
  query.value = ''
}
</script>

<template>
  <section class="flex flex-col gap-2">
    <!-- my team, once starred -->
    <div v-if="myTeam" class="my-card rounded-2xl border border-[#ff6cc0]/50 p-3">
      <div class="flex items-center gap-2.5">
        <div class="flex shrink-0 -space-x-2">
          <PlayerAvatar v-for="p in myTeam.team.players" :key="p.nickname" :name="p.nickname" :avatar-url="p.avatar_url" size="sm" round class="ring-2 ring-[#ff6cc0]/60" />
        </div>
        <div class="min-w-0 flex-1">
          <p class="text-[11px] font-semibold tracking-wide text-[#ff9fd6]">{{ t('cup.my.title') }}</p>
          <p class="truncate font-display text-base leading-tight font-bold">{{ myTeam.team.name }}</p>
          <p class="truncate text-xs text-white/65">{{ myTeam.levelName }} · {{ standing }}</p>
        </div>
        <button type="button" class="min-h-10 shrink-0 rounded-full border border-white/20 px-3 text-xs text-white/80" @click="go(myTeam)">{{ t('cup.my.see') }}</button>
      </div>
      <div v-if="nextMatch" class="mt-2.5">
        <p class="mb-1 text-[11px] font-semibold text-[#7ff0b4]">{{ nextMatch.status === 'on_court' ? t('cup.day.liveTitle') : t('cup.my.next') }}</p>
        <CupMatchRow :match="nextMatch" show-round :mine-id="mine" />
      </div>
      <button type="button" class="mt-1.5 min-h-9 text-[11px] text-white/45 underline" @click="mine = null">{{ t('cup.my.forget') }}</button>
    </div>

    <!-- find any team -->
    <div class="relative">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" class="pointer-events-none absolute top-1/2 left-3.5 h-4 w-4 -translate-y-1/2 text-white/45" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
      <input
        v-model="query"
        type="search"
        :placeholder="myTeam ? t('cup.my.search') : t('cup.my.searchFirst')"
        :aria-label="t('cup.my.search')"
        class="min-h-12 w-full rounded-2xl border border-white/15 bg-white/6 pr-3 pl-10 text-[15px] text-white placeholder:text-white/45"
      />
    </div>
    <ul v-if="query.trim()" class="flex flex-col gap-1 rounded-2xl border border-white/10 bg-[#1a0838]/95 p-1.5">
      <li v-for="f in results" :key="f.team.id" class="flex items-center gap-2 rounded-xl px-2 py-1.5 hover:bg-white/6">
        <button type="button" class="flex min-h-11 min-w-0 flex-1 items-center gap-2 text-left" @click="go(f)">
          <div class="flex shrink-0 -space-x-2">
            <PlayerAvatar v-for="p in f.team.players" :key="p.nickname" :name="p.nickname" :avatar-url="p.avatar_url" size="sm" round />
          </div>
          <span class="min-w-0">
            <span class="block truncate text-sm font-semibold">{{ f.team.name }}</span>
            <span class="block truncate text-xs text-white/55">{{ f.team.players.map((p) => p.nickname).join(' · ') }} · {{ f.levelName }}<template v-if="f.group"> · {{ t('cup.draw.group', { g: f.group }) }}</template></span>
          </span>
        </button>
        <button
          type="button"
          class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full"
          :class="mine === f.team.id ? 'text-[#ffe14d]' : 'text-white/40 hover:text-white/80'"
          :aria-label="t('cup.my.star', { team: f.team.name })"
          :aria-pressed="mine === f.team.id"
          @click="star(f)"
        >
          <svg viewBox="0 0 24 24" class="h-5 w-5" :fill="mine === f.team.id ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" aria-hidden="true">
            <path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z" />
          </svg>
        </button>
      </li>
      <li v-if="!results.length" class="px-2 py-3 text-center text-sm text-white/55">{{ t('cup.my.none') }}</li>
    </ul>
  </section>
</template>

<style scoped>
.my-card {
  background: linear-gradient(140deg, rgb(255 108 192 / 0.16), rgb(255 255 255 / 0.04) 60%);
}
</style>
