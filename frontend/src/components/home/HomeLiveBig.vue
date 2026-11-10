<script setup lang="ts">
// The big card at the top of the desktop home page. It is never empty:
//
// - a match on court: who is playing whom, with faces and ELO;
// - Friday night, nobody on court yet (or between games): the night is on,
//   how many games are waiting;
// - any other time: a countdown to the next Friday at 20:00.
//
// The phone keeps its slim LiveNowBox, which only appears while a match is
// on; a phone screen has no room to spare for a countdown.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { getPlayersByIds } from '@/api/public'
import { useLiveNow } from '@/composables/useLiveNow'
import type { Player } from '@/types'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'
import EloGauge from '@/components/matches/EloGauge.vue'
import { teamElo } from '@/utils/eloOdds'
import { useGameNight } from '@/composables/useGameNight'

const { t } = useI18n()
const { live } = useLiveNow()
const players = ref<Record<string, Player>>({})

const match = computed(() => live.value?.in_progress[0] ?? null)
const otherCourts = computed(() => Math.max(0, (live.value?.in_progress.length ?? 0) - 1))
const waiting = computed(() => live.value?.queued.length ?? 0)

watch(
  match,
  async (m) => {
    if (!m) return
    const ids = [...m.team1_player_ids, ...m.team2_player_ids].filter((id) => !players.value[id])
    if (!ids.length) return
    try {
      const found = await getPlayersByIds(ids)
      players.value = { ...players.value, ...Object.fromEntries(found.map((p) => [p.id, p])) }
    } catch {
      // names fill in on the next poll; the card already says a match is on
    }
  },
  { immediate: true },
)

const team = (ids: string[]): Player[] =>
  ids.map((id) => players.value[id] ?? ({ id, nickname: '…', avatar_url: null, elo_score: 0 } as Player))
const names = (ids: string[]): string => team(ids).map((p) => p.nickname).join(' & ')
// the match on court, rated on the players' ELO now
const gauge = computed(() => {
  const m = match.value
  if (!m) return null
  const eloOf = (id: string): number | undefined => players.value[id]?.elo_score || undefined
  const a = teamElo(m.team1_player_ids, eloOf)
  const b = teamElo(m.team2_player_ids, eloOf)
  return a === null || b === null ? null : { a, b }
})
const elos = (ids: string[]): string =>
  team(ids)
    .map((p) => (p.elo_score ? Math.round(p.elo_score).toLocaleString('en-US') : '—'))
    .join(' · ')

const where = computed(() => {
  const m = match.value
  if (!m) return ''
  return [m.court ? t('home.live.court', { court: m.court }) : null, m.match_no ? t('home.big.matchNo', { n: m.match_no }) : null]
    .filter(Boolean)
    .join(' · ')
})

const { night, countdown, startsAt } = useGameNight()
</script>

<template>
  <!-- A container: under ~700px of its own width (the grid's 900–1100px
       range) each team stands as faces over a name, rather than a name
       squeezed down to "Ball …" beside its faces. -->
  <RouterLink to="/live" class="big world-card @container flex flex-col p-6 xl:p-7" :class="match ? 'big-live' : ''">
    <!-- on court now -->
    <template v-if="match">
      <div class="flex items-center justify-between gap-3">
        <span class="flex items-center gap-2.5 font-display text-base font-bold">
          <span class="live-dot" aria-hidden="true" />
          {{ t('home.live.title') }}
        </span>
        <span class="text-sm text-white/60">
          <template v-if="otherCourts">{{ t('home.big.otherCourts', { n: otherCourts }) }} · </template>
          {{ t('home.big.waiting', { n: waiting }) }}
        </span>
      </div>
      <div class="my-auto grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-5 py-6">
        <div class="flex min-w-0 flex-col-reverse items-center gap-2.5 @2xl:flex-row @2xl:justify-end @2xl:gap-3.5">
          <div class="min-w-0 max-w-full text-center @2xl:text-right">
            <p class="truncate font-display text-2xl font-bold xl:text-[26px]">{{ names(match.team1_player_ids) }}</p>
            <p class="text-xs text-white/55">ELO {{ elos(match.team1_player_ids) }}</p>
          </div>
          <div class="flex shrink-0">
            <PlayerAvatar
              v-for="(p, i) in team(match.team1_player_ids)"
              :key="p.id"
              :name="p.nickname"
              :avatar-url="p.avatar_url"
              size="lg"
              round
              :class="i > 0 ? '-ml-3.5' : ''"
            />
          </div>
        </div>
        <span class="vs">VS</span>
        <div class="flex min-w-0 flex-col items-center gap-2.5 @2xl:flex-row @2xl:gap-3.5">
          <div class="flex shrink-0">
            <PlayerAvatar
              v-for="(p, i) in team(match.team2_player_ids)"
              :key="p.id"
              :name="p.nickname"
              :avatar-url="p.avatar_url"
              size="lg"
              round
              :class="i > 0 ? '-ml-3.5' : ''"
            />
          </div>
          <div class="min-w-0 max-w-full text-center @2xl:text-left">
            <p class="truncate font-display text-2xl font-bold xl:text-[26px]">{{ names(match.team2_player_ids) }}</p>
            <p class="text-xs text-white/55">ELO {{ elos(match.team2_player_ids) }}</p>
          </div>
        </div>
      </div>
      <EloGauge v-if="gauge" class="mb-5" :elo1="gauge.a" :elo2="gauge.b" live />
      <div class="flex items-center justify-between gap-3 text-sm">
        <span class="text-white/60">{{ where }}</span>
        <span class="text-white/80">{{ t('home.big.allCourts') }} <span aria-hidden="true">→</span></span>
      </div>
    </template>

    <!-- Friday night, between games -->
    <template v-else-if="night.on">
      <p class="world-eyebrow">TONIGHT</p>
      <h2 class="world-title mt-1 text-3xl">{{ t('home.big.onTonight') }}</h2>
      <p class="mt-3 max-w-[44ch] text-white/75">
        {{ waiting ? t('home.big.waitingTonight', { n: waiting }) : t('home.big.quietTonight') }}
      </p>
      <span class="mt-auto pt-6 text-sm text-white/80">{{ t('home.big.seeQueue') }} <span aria-hidden="true">→</span></span>
    </template>

    <!-- the rest of the week -->
    <template v-else>
      <p class="world-eyebrow">NEXT GAME NIGHT</p>
      <h2 class="world-title mt-1 text-3xl">{{ startsAt }}</h2>
      <div class="mt-5 flex gap-3" role="timer" :aria-label="t('home.big.countdownLabel')">
        <div v-for="part in countdown" :key="part.unit" class="count">
          <span class="font-display text-4xl leading-none font-bold text-[#ff9fd6] tabular-nums">{{ part.n }}</span>
          <span class="mt-1.5 text-xs text-white/60">{{ part.unit }}</span>
        </div>
      </div>
      <p class="mt-auto pt-5 text-sm text-white/60">{{ t('home.hero.when') }}</p>
    </template>
  </RouterLink>
</template>

<style scoped>
.big {
  min-height: 260px;
  transition:
    transform 0.25s ease,
    border-color 0.25s ease;
}
.big:hover {
  transform: translateY(-3px);
  border-color: rgb(255 108 192 / 0.55);
}
.big-live {
  background:
    radial-gradient(80% 120% at 100% 0%, rgb(255 80 120 / 0.22), transparent 60%),
    linear-gradient(135deg, rgb(255 255 255 / 0.12), rgb(255 255 255 / 0.03) 55%, rgb(255 255 255 / 0.07)),
    rgb(24 10 46 / 0.6);
}
.live-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #ff5078;
  animation: live-pulse 1.6s infinite;
}
@keyframes live-pulse {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgb(255 80 120 / 0.7);
  }
  50% {
    box-shadow: 0 0 0 8px rgb(255 80 120 / 0);
  }
}
.vs {
  display: flex;
  width: 60px;
  height: 60px;
  align-items: center;
  justify-content: center;
  border: 1px solid rgb(255 108 192 / 0.5);
  border-radius: 18px;
  background: rgb(234 76 164 / 0.2);
  color: #ff9fd6;
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 700;
}
.count {
  display: flex;
  width: 96px;
  flex-direction: column;
  align-items: center;
  padding: 14px 0;
  border: 1px solid rgb(255 255 255 / 0.14);
  border-radius: 18px;
  background: rgb(255 255 255 / 0.07);
}
@media (prefers-reduced-motion: reduce) {
  .live-dot {
    animation: none;
  }
  .big {
    transition: none;
  }
}
</style>
