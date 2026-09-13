<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getLiveStatus, getPlayersByIds } from '@/api/public'
import type { LiveQueueResponse, Player, QueueEntry } from '@/types'
import { usePolling } from '@/composables/usePolling'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'

// "Where is this member right now" — the same /api/live payload LiveView
// renders for the whole club, narrowed to one player. Sits outside the
// season selector on purpose: it's about this minute, not about a year.
//
// The parent keys this component on the player id, so switching members
// gets a fresh instance rather than stale state from the previous one.
const props = defineProps<{ playerId: string }>()

const { t } = useI18n()

const live = ref<LiveQueueResponse | null>(null)
const playersById = ref<Record<string, Player>>({})
// Ids already asked about, resolved or not. A player who genuinely can't be
// resolved (deactivated, deleted) would otherwise be re-requested on every
// 7s poll for as long as the page is open.
const lookedUp = new Set<string>()

function entryFor(entries: QueueEntry[]): QueueEntry | undefined {
  return entries.find(
    (m) => m.team1_player_ids.includes(props.playerId) || m.team2_player_ids.includes(props.playerId),
  )
}

const playing = computed(() => (live.value ? entryFor(live.value.in_progress) : undefined))
const queued = computed(() => (live.value ? entryFor(live.value.queued) : undefined))
const waiting = computed(() => live.value?.waiting.find((w) => w.player_id === props.playerId))
// The match this member is in, if any — in_progress wins over queued, since
// an admin can queue someone's next pairing while they're still on court.
const entry = computed(() => playing.value ?? queued.value)
// Nothing to show when there's no open session, and also when there is one
// but this member isn't in it — including the gap right after their match
// ends and before they're re-queued. Deliberately silent rather than
// rendering an empty "not playing" panel on every member's profile.
const visible = computed(() => Boolean(entry.value || waiting.value))

function nameOf(playerId: string): string {
  return playersById.value[playerId]?.nickname ?? '?'
}

function avatarOf(playerId: string): string | undefined {
  return playersById.value[playerId]?.avatar_url ?? undefined
}

function sideOf(match: QueueEntry, own: boolean): string[] {
  const onTeam1 = match.team1_player_ids.includes(props.playerId)
  return onTeam1 === own ? match.team1_player_ids : match.team2_player_ids
}

const partners = computed(() =>
  entry.value ? sideOf(entry.value, true).filter((id) => id !== props.playerId) : [],
)
const opponents = computed(() => (entry.value ? sideOf(entry.value, false) : []))

async function resolveNames(): Promise<void> {
  const match = entry.value
  if (!match) return
  const ids = [...match.team1_player_ids, ...match.team2_player_ids].filter((id) => !lookedUp.has(id))
  if (ids.length === 0) return
  ids.forEach((id) => lookedUp.add(id))
  try {
    const players = await getPlayersByIds(ids)
    playersById.value = { ...playersById.value, ...Object.fromEntries(players.map((p) => [p.id, p])) }
  } catch {
    // Transient failure — unmark so the next poll retries. Ids that came
    // back successfully but empty stay marked: that's the unresolvable
    // player case, and retrying it forever would cost a request every 7s.
    ids.forEach((id) => lookedUp.delete(id))
  }
}

async function refresh(): Promise<void> {
  try {
    live.value = await getLiveStatus()
  } catch {
    // Keep the last-known-good state and let the next poll retry. This is a
    // supplementary block on someone's profile — a cold-starting backend
    // must not put an error banner over their stats.
    return
  }
  await resolveNames()
}

usePolling(refresh, 7000)
</script>

<template>
  <section v-if="visible" class="hud-panel glass-panel mt-8 border border-brand-pink/40 p-4">
    <div class="flex items-center gap-2">
      <span class="relative flex h-2 w-2">
        <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-pink opacity-75" />
        <span class="relative inline-flex h-2 w-2 rounded-full bg-brand-pink" />
      </span>
      <h2 class="text-xs font-semibold tracking-widest text-brand-pink/70 uppercase">
        {{ t('profile.rightNow') }}
      </h2>
    </div>

    <template v-if="entry">
      <p class="mt-3 flex flex-wrap items-center gap-2">
        <span
          class="hud-panel border border-brand-pink/30 bg-brand-black px-2.5 py-1 text-xs font-semibold uppercase"
          :class="playing ? 'text-status-success' : 'text-brand-pink'"
        >
          {{ playing ? t('live.inProgress') : t('live.upNext') }}
        </span>
        <span v-if="entry.court" class="text-xs text-white/50">
          {{ t('matchmaking.courtLabel') }} {{ entry.court }}
        </span>
      </p>

      <div v-if="partners.length > 0" class="mt-3">
        <p class="text-xs tracking-wide text-white/40 uppercase">{{ t('profile.withPartner') }}</p>
        <ul class="mt-1.5 flex flex-wrap gap-2">
          <li v-for="pid in partners" :key="pid" class="flex items-center gap-2 text-sm text-white/80">
            <PlayerAvatar :name="nameOf(pid)" :avatar-url="avatarOf(pid)" size="sm" />
            {{ nameOf(pid) }}
          </li>
        </ul>
      </div>

      <div class="mt-3">
        <p class="text-xs tracking-wide text-white/40 uppercase">{{ t('profile.against') }}</p>
        <ul class="mt-1.5 flex flex-wrap gap-2">
          <li v-for="pid in opponents" :key="pid" class="flex items-center gap-2 text-sm text-white/80">
            <PlayerAvatar :name="nameOf(pid)" :avatar-url="avatarOf(pid)" size="sm" />
            {{ nameOf(pid) }}
          </li>
        </ul>
      </div>
    </template>

    <template v-else-if="waiting">
      <p class="mt-3 flex flex-wrap items-center gap-2">
        <span class="hud-panel border border-brand-pink/30 bg-brand-black px-2.5 py-1 text-xs font-semibold text-white/70 uppercase">
          {{ t('live.inQueue') }}
        </span>
        <span class="text-sm text-white/70">
          {{ t('profile.queuePosition', { n: waiting.queue_position }) }}
        </span>
      </p>
      <p class="mt-2 text-xs text-white/40">
        {{ t('profile.estimatedWait') }} ~{{ Math.round(waiting.estimated_wait_minutes) }}
        {{ t('matches.minutes') }}
      </p>
    </template>
  </section>
</template>
