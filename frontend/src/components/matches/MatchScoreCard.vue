<script setup lang="ts">
// One finished match as a scoreboard: the two teams stacked, the winners
// lit gold with a WIN plate, the losers dimmed, a draw grey on both sides.
// Only the result — the club records who won, not a score. Used by the match log
// (grouped under each night, so it shows the time) and a member's own
// season history (not grouped, so it shows the date as well).
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import type { Match, Player } from '@/types'
import { formatDateTime, formatTime } from '@/utils/format'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'
import TeamNames from '@/components/players/TeamNames.vue'
import EloGauge from '@/components/matches/EloGauge.vue'
import EloDelta from '@/components/matches/EloDelta.vue'
import { isUpset } from '@/utils/eloOdds'

const props = defineProps<{ match: Match; playersById: Record<string, Player>; withDate?: boolean }>()
const { t, locale } = useI18n()

const nameOf = (id: string): string => props.playersById[id]?.nickname ?? '?'
const avatarOf = (id: string): string | null => props.playersById[id]?.avatar_url ?? null

type Result = 'win' | 'draw' | 'lose' | null

function side(ids: string[], me: 'team1' | 'team2') {
  const w = props.match.winner
  const result: Result = !w ? null : w === 'draw' ? 'draw' : w === me ? 'win' : 'lose'
  const delta = me === 'team1' ? props.match.elo_delta_team1 : props.match.elo_delta_team2
  return { ids, result, delta }
}

// each team's average ELO going into it, worked out by the server
const elo = computed(() =>
  typeof props.match.elo_team1 === 'number' && typeof props.match.elo_team2 === 'number'
    ? { a: props.match.elo_team1, b: props.match.elo_team2 }
    : null,
)
const upset = computed(() => isUpset(props.match.elo_team1, props.match.elo_team2, props.match.winner))

const teams = computed(() => [side(props.match.team1_player_ids, 'team1'), side(props.match.team2_player_ids, 'team2')])

const minutes = computed(() => {
  if (props.match.status !== 'completed') return null
  const m = (new Date(props.match.updated_at).getTime() - new Date(props.match.created_at).getTime()) / 60000
  return Number.isFinite(m) && m > 0 ? Math.round(m) : null
})
const when = computed(() =>
  props.withDate ? formatDateTime(props.match.created_at, locale.value) : formatTime(props.match.created_at, locale.value),
)
</script>

<template>
  <RouterLink :to="`/matches/${match.id}`" class="card world-card relative block overflow-hidden" :class="{ decided: match.winner && match.winner !== 'draw' }">
    <span v-if="upset" class="upset-stamp">{{ t('elo.upset') }}</span>
    <div class="head" :style="upset ? { paddingRight: '78px' } : undefined">
      <span class="min-w-0 truncate">
        <span v-if="typeof match.match_no === 'number'" class="no">#{{ match.match_no }}</span>
        <template v-if="match.court"> · {{ t('home.live.court', { court: match.court }) }}</template>
      </span>
      <span class="shrink-0">
        <template v-if="minutes">{{ minutes }} {{ t('matches.minutes') }} · </template>{{ when }}
      </span>
    </div>
    <template v-for="(team, i) in teams" :key="i">
      <div v-if="i === 1" class="mx-4 h-px bg-white/8" aria-hidden="true" />
      <!-- the team's colour on the gauge below: team 1 pink, team 2 violet -->
      <div class="team" :class="[team.result ?? '', elo ? `side-${i + 1}` : '']">
        <div class="flex shrink-0">
          <span v-for="(id, k) in team.ids" :key="id" class="ring" :class="k > 0 ? '-ml-2.5' : ''">
            <PlayerAvatar :name="nameOf(id)" :avatar-url="avatarOf(id)" size="md" round />
          </span>
        </div>
        <span class="min-w-0 truncate pl-1 font-display text-[15px] font-semibold sm:text-base"><TeamNames :ids="team.ids" :name-of="nameOf" /></span>
        <span class="flex shrink-0 items-center gap-2">
          <EloDelta v-if="typeof team.delta === 'number'" :delta="team.delta" />
          <span v-if="team.result" class="plate">{{ t(`matches.${team.result}`) }}</span>
        </span>
      </div>
    </template>
    <div v-if="elo" class="gauge-row">
      <EloGauge :elo1="elo.a" :elo2="elo.b" :winner="match.winner" label="before" />
    </div>
  </RouterLink>
</template>

<style scoped>
.card {
  border-radius: 20px;
  transition:
    transform 0.2s,
    border-color 0.2s;
}
.card.decided {
  border-color: rgb(255 211 77 / 0.3);
}
.card:hover {
  transform: translateY(-2px);
  border-color: rgb(255 108 192 / 0.55);
}
.head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 16px;
  border-bottom: 1px solid rgb(255 255 255 / 0.08);
  font-size: 12px;
  color: rgb(255 255 255 / 0.6);
}
.no {
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 700;
  color: #ff9fd6;
}
.team {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  min-height: 62px;
  padding: 10px 16px;
}
.team.side-1 {
  box-shadow: inset 3px 0 0 rgb(255 79 174 / 0.8);
}
.team.side-2 {
  box-shadow: inset 3px 0 0 rgb(143 107 255 / 0.9);
}
.gauge-row {
  padding: 10px 16px 12px;
  border-top: 1px solid rgb(255 255 255 / 0.08);
}
.ring {
  border-radius: 50%;
  box-shadow: 0 0 0 2px rgb(255 255 255 / 0.22);
}
.team.win {
  background: linear-gradient(90deg, rgb(255 211 77 / 0.16), transparent 70%);
}
.team.win .ring {
  box-shadow:
    0 0 0 2px #ffd34d,
    0 0 14px rgb(255 211 77 / 0.45);
}
.team.lose {
  opacity: 0.62;
}
.plate {
  display: inline-flex;
  min-width: 58px;
  height: 28px;
  align-items: center;
  justify-content: center;
  padding: 0 10px;
  border: 1px solid rgb(255 255 255 / 0.12);
  border-radius: 999px;
  font-family: var(--font-display);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: rgb(255 255 255 / 0.45);
}
.win .plate {
  border: 0;
  background: linear-gradient(#ffe58a, #ffc94d);
  color: #2a1a00;
  box-shadow: 0 0 16px rgb(255 201 77 / 0.6);
}
.draw .plate {
  border-color: rgb(255 255 255 / 0.2);
  background: rgb(255 255 255 / 0.12);
  color: rgb(255 255 255 / 0.85);
}
@media (prefers-reduced-motion: reduce) {
  .card {
    transition: none;
  }
}
</style>
