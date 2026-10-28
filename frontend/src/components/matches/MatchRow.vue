<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { Match, Player } from '@/types'
import { formatDateTime } from '@/utils/format'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'

// The match-log card: both teams face to face, the winner stamped and the
// loser dimmed. Shared by the global match log and a member's own season
// history so the two can't drift apart visually.
//
// Deliberately neutral — it has no "viewing player", so it reads the same
// wherever it appears. On a profile the member finds themselves by their own
// avatar; the stamp sitting over their side is what says they won.
//
// Rendered inside a <li> owned by the caller, which keeps the list's keying
// and its v-reveal stagger where the v-for is.
const props = defineProps<{ match: Match; playersById: Record<string, Player> }>()

const { t, locale } = useI18n()

function playerOf(playerId: string): Player | undefined {
  return props.playersById[playerId]
}

function nameOf(playerId: string): string {
  return playerOf(playerId)?.nickname ?? '?'
}

function setsLabel(match: Match): string {
  // Results are recorded as a winner only, so most matches have no sets;
  // a lone "-" between the teams read as a missing score.
  if (!match.sets || match.sets.length === 0) return 'VS'
  return match.sets.map(([a, b]) => `${a}-${b}`).join(', ')
}

function durationLabel(match: Match): string | null {
  if (match.status !== 'completed') return null
  const minutes = (new Date(match.updated_at).getTime() - new Date(match.created_at).getTime()) / 60000
  if (!Number.isFinite(minutes) || minutes <= 0) return null
  return `${minutes.toFixed(0)} ${t('matches.minutes')}`
}

function dateLabel(isoDate: string): string {
  return formatDateTime(isoDate, locale.value)
}
</script>

<template>
  <RouterLink :to="`/matches/${match.id}`" class="block px-4 py-3">
    <div class="flex items-center justify-between text-xs tracking-wide text-white/40 uppercase">
      <span class="flex items-center gap-2">
        <!-- Leads the row: the number is how people refer to a match out
             loud, so it should be the first thing read, not a detail
             hidden among the metadata.
             typeof, not !== null: a backend older than the numbered view
             leaves the key out entirely, and `undefined !== null` would
             render "#undefined" through a deploy where the frontend lands
             first. -->
        <span
          v-if="typeof match.match_no === 'number'"
          class="hud-panel shrink-0 border border-brand-pink/30 bg-brand-black px-1.5 py-0.5 font-mono text-xs font-semibold text-brand-pink/80"
          :title="t('matches.matchNo', { n: match.match_no })"
        >#{{ match.match_no }}</span>
        <!-- No doubles/singles split any more: the club only plays
             doubles, and the admin UI can only create type="double".
             A legacy singles row, if the database still holds one,
             reads "แมตช์" like everything else. -->
        {{ t('matches.typeLabel') }}
      </span>
      <span class="flex items-center gap-2">
        <span v-if="durationLabel(match)">{{ durationLabel(match) }} ·</span>
        {{ dateLabel(match.created_at) }}
      </span>
    </div>

    <div class="mt-3 flex items-center justify-between gap-3">
      <div
        class="flex min-w-0 flex-1 flex-col items-center gap-1.5"
        :class="{ 'opacity-45 grayscale': match.winner === 'team2' }"
      >
        <div class="stamp-wrap relative flex gap-2">
          <PlayerAvatar
            v-for="pid in match.team1_player_ids"
            :key="pid"
            :name="nameOf(pid)"
            :avatar-url="playerOf(pid)?.avatar_url"
            size="lg"
          />
          <span v-if="match.winner === 'team1'" class="stamp stamp--win">{{ t('matches.win') }}</span>
          <span v-else-if="match.winner === 'draw'" class="stamp stamp--draw">{{ t('matches.draw') }}</span>
        </div>
        <span
          class="max-w-full text-center text-sm font-medium break-words"
          :class="match.winner === 'team1' ? 'text-brand-pink' : 'text-white/70'"
        >
          {{ match.team1_player_ids.map(nameOf).join(' & ') }}
        </span>
      </div>

      <span class="hud-panel shrink-0 bg-brand-black px-2.5 py-1 font-mono text-sm text-white/80">
        {{ setsLabel(match) }}
      </span>

      <div
        class="flex min-w-0 flex-1 flex-col items-center gap-1.5"
        :class="{ 'opacity-45 grayscale': match.winner === 'team1' }"
      >
        <div class="stamp-wrap relative flex gap-2">
          <PlayerAvatar
            v-for="pid in match.team2_player_ids"
            :key="pid"
            :name="nameOf(pid)"
            :avatar-url="playerOf(pid)?.avatar_url"
            size="lg"
          />
          <span v-if="match.winner === 'team2'" class="stamp stamp--win">{{ t('matches.win') }}</span>
          <span v-else-if="match.winner === 'draw'" class="stamp stamp--draw">{{ t('matches.draw') }}</span>
        </div>
        <span
          class="max-w-full text-center text-sm font-medium break-words"
          :class="match.winner === 'team2' ? 'text-brand-pink' : 'text-white/70'"
        >
          {{ match.team2_player_ids.map(nameOf).join(' & ') }}
        </span>
      </div>
    </div>
  </RouterLink>
</template>

<style scoped>
.stamp-wrap {
  overflow: visible;
}
.stamp {
  position: absolute;
  top: -0.6rem;
  left: 50%;
  translate: -50% 0;
  rotate: -10deg;
  font-family: var(--font-display);
  font-weight: 800;
  /* 12px floor, same as every other label on the page: this stamp was
     9.6px, the smallest text in the app. */
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 0.05rem 0.4rem;
  border-radius: 0.25rem;
  border-width: 2px;
  border-style: solid;
  background-color: var(--color-brand-black);
  pointer-events: none;
  white-space: nowrap;
}
.stamp--win {
  color: var(--color-status-success);
  border-color: var(--color-status-success);
}
.stamp--draw {
  color: var(--color-tier-milk);
  border-color: var(--color-tier-milk);
}
</style>
