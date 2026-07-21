<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getLiveStatus, getPlayers } from '@/api/public'
import type { LiveQueueResponse, Player } from '@/types'
import { usePolling } from '@/composables/usePolling'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'

const { t, locale } = useI18n()

const live = ref<LiveQueueResponse | null>(null)
const playersById = ref<Record<string, Player>>({})
const loading = ref(true)
const error = ref<string | null>(null)

function nameOf(playerId: string): string {
  return playersById.value[playerId]?.nickname ?? '?'
}

function avatarOf(playerId: string): string | undefined {
  return playersById.value[playerId]?.avatar_url ?? undefined
}

async function refresh(): Promise<void> {
  try {
    live.value = await getLiveStatus()
    error.value = null
  } catch {
    error.value = t('live.loadError')
  } finally {
    loading.value = false
  }
}

async function loadPlayers(): Promise<void> {
  const stats = await getPlayers()
  playersById.value = Object.fromEntries(stats.map((s) => [s.player.id, s.player]))
}

function formatSessionDate(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString(locale.value === 'th' ? 'th-TH' : 'en-US', {
    day: 'numeric',
    month: 'long',
  })
}

onMounted(loadPlayers)
usePolling(refresh, 7000)
</script>

<template>
  <main class="mx-auto max-w-3xl px-4 py-8 sm:py-12">
    <p class="text-xs font-semibold tracking-widest text-brand-pink/70 uppercase">Live</p>
    <h1 class="font-display text-3xl font-bold text-white">{{ t('live.title') }}</h1>

    <p v-if="loading" class="mt-6 text-white/60">{{ t('common.loading') }}</p>
    <p v-else-if="error" class="mt-6 text-status-error">{{ error }}</p>

    <template v-else-if="!live?.session_id">
      <p class="mt-6 text-white/60">{{ t('live.noSession') }}</p>
    </template>

    <template v-else>
      <p v-if="live.session_date" class="mt-1 text-sm text-white/50">
        {{ live.location }} · {{ formatSessionDate(live.session_date) }}
      </p>

      <section class="mt-6">
        <h2 class="text-sm font-semibold text-white/70">
          {{ t('live.inProgress') }} ({{ live.in_progress.length }})
        </h2>
        <ul class="mt-2 space-y-2">
          <li
            v-for="m in live.in_progress"
            :key="m.match_id"
            class="hud-panel border border-brand-pink/20 bg-brand-surface px-4 py-3"
          >
            <div class="flex items-center justify-between gap-3">
              <div class="flex flex-1 flex-col items-center gap-1.5">
                <div class="flex -space-x-3">
                  <PlayerAvatar
                    v-for="pid in m.team1_player_ids"
                    :key="pid"
                    :name="nameOf(pid)"
                    :avatar-url="avatarOf(pid)"
                    size="lg"
                  />
                </div>
                <span class="text-center font-medium text-white/80">
                  {{ m.team1_player_ids.map(nameOf).join(' & ') }}
                </span>
              </div>

              <span class="hud-panel shrink-0 border border-brand-pink/20 bg-brand-black px-2.5 py-1 text-xs font-semibold text-white/50 uppercase">
                {{ t('live.playing') }}
              </span>

              <div class="flex flex-1 flex-col items-center gap-1.5">
                <div class="flex -space-x-3">
                  <PlayerAvatar
                    v-for="pid in m.team2_player_ids"
                    :key="pid"
                    :name="nameOf(pid)"
                    :avatar-url="avatarOf(pid)"
                    size="lg"
                  />
                </div>
                <span class="text-center font-medium text-white/80">
                  {{ m.team2_player_ids.map(nameOf).join(' & ') }}
                </span>
              </div>
            </div>
          </li>
          <li v-if="live.in_progress.length === 0" class="text-sm text-white/40">
            {{ t('live.noneInProgress') }}
          </li>
        </ul>
      </section>

      <section class="mt-8">
        <h2 class="text-sm font-semibold text-white/70">{{ t('live.upNext') }}</h2>
        <ul class="mt-2 space-y-2">
          <li
            v-for="s in live.suggestions"
            :key="s.group_no"
            class="hud-panel border border-brand-pink/20 bg-brand-surface px-4 py-3"
          >
            <div class="flex items-center justify-between gap-3">
              <div class="flex flex-1 flex-col items-center gap-1.5">
                <div class="flex -space-x-3">
                  <PlayerAvatar
                    v-for="pid in s.team1_player_ids"
                    :key="pid"
                    :name="nameOf(pid)"
                    :avatar-url="avatarOf(pid)"
                    size="lg"
                  />
                </div>
                <span class="text-center text-sm text-white/80">
                  {{ s.team1_player_ids.map(nameOf).join(' & ') }}
                </span>
              </div>

              <span class="hud-panel shrink-0 border border-brand-pink/20 bg-brand-black px-2 py-0.5 text-xs font-semibold text-brand-pink/70 uppercase">
                VS
              </span>

              <div class="flex flex-1 flex-col items-center gap-1.5">
                <div class="flex -space-x-3">
                  <PlayerAvatar
                    v-for="pid in s.team2_player_ids"
                    :key="pid"
                    :name="nameOf(pid)"
                    :avatar-url="avatarOf(pid)"
                    size="lg"
                  />
                </div>
                <span class="text-center text-sm text-white/80">
                  {{ s.team2_player_ids.map(nameOf).join(' & ') }}
                </span>
              </div>
            </div>
          </li>
          <li v-if="live.suggestions.length === 0" class="text-sm text-white/40">
            {{ t('live.noneUpNext') }}
          </li>
        </ul>
      </section>

      <section class="mt-8">
        <h2 class="text-sm font-semibold text-white/70">{{ t('live.inQueue') }} ({{ live.waiting.length }})</h2>
        <ul class="mt-2 flex flex-wrap gap-2">
          <li
            v-for="w in live.waiting"
            :key="w.player_id"
            class="flex items-center gap-2 rounded-full border border-brand-pink/25 bg-brand-surface px-3 py-1.5 text-sm"
          >
            <PlayerAvatar :name="nameOf(w.player_id)" :avatar-url="avatarOf(w.player_id)" size="sm" />
            {{ nameOf(w.player_id) }}
            <span class="text-xs text-white/40">~{{ Math.round(w.estimated_wait_minutes) }} {{ t('matches.minutes') }}</span>
          </li>
          <li v-if="live.waiting.length === 0" class="text-sm text-white/40">{{ t('live.noneWaiting') }}</li>
        </ul>
      </section>
    </template>
  </main>
</template>
