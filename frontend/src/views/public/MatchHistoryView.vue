<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getMatches, getPlayers } from '@/api/public'
import type { Match, Player } from '@/types'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'

const PAGE_SIZE = 20

const matches = ref<Match[]>([])
const playersById = ref<Record<string, Player>>({})
const loading = ref(true)
const loadingMore = ref(false)
const error = ref<string | null>(null)
const hasMore = ref(true)

function playerOf(playerId: string): Player | undefined {
  return playersById.value[playerId]
}

function nameOf(playerId: string): string {
  const p = playerOf(playerId)
  return p ? p.nickname || p.name : '?'
}

function setsLabel(match: Match): string {
  if (!match.sets) return '-'
  return match.sets.map(([a, b]) => `${a}-${b}`).join(', ')
}

function durationLabel(match: Match): string | null {
  if (match.status !== 'completed') return null
  const minutes = (new Date(match.updated_at).getTime() - new Date(match.created_at).getTime()) / 60000
  if (!Number.isFinite(minutes) || minutes <= 0) return null
  return `${minutes.toFixed(0)} นาที`
}

const sortedMatches = computed(() =>
  [...matches.value].sort((a, b) => b.created_at.localeCompare(a.created_at)),
)

async function loadMore(): Promise<void> {
  loadingMore.value = true
  try {
    const next = await getMatches({ limit: PAGE_SIZE, offset: matches.value.length })
    matches.value = [...matches.value, ...next]
    hasMore.value = next.length === PAGE_SIZE
  } catch {
    error.value = 'โหลดผลแมตช์เพิ่มไม่สำเร็จ'
  } finally {
    loadingMore.value = false
  }
}

onMounted(async () => {
  try {
    const [matchList, stats] = await Promise.all([
      getMatches({ limit: PAGE_SIZE }),
      getPlayers(),
    ])
    matches.value = matchList
    hasMore.value = matchList.length === PAGE_SIZE
    playersById.value = Object.fromEntries(stats.map((s) => [s.player.id, s.player]))
  } catch {
    error.value = 'โหลดผลแมตช์ไม่สำเร็จ'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <main class="mx-auto max-w-3xl px-4 py-8 sm:py-12">
    <p class="text-xs font-semibold tracking-widest text-brand-pink/70 uppercase">Match Log</p>
    <h1 class="font-display text-3xl font-bold text-white">ผลแมตช์</h1>

    <p v-if="loading" class="mt-6 text-white/60">กำลังโหลด...</p>
    <p v-else-if="error" class="mt-6 text-status-error">{{ error }}</p>
    <p v-else-if="sortedMatches.length === 0" class="mt-6 text-white/60">ยังไม่มีผลแมตช์</p>

    <ul v-else class="mt-6 space-y-3">
      <li
        v-for="m in sortedMatches"
        :key="m.id"
        class="hud-panel border border-brand-pink/15 bg-brand-surface transition-colors hover:border-brand-pink/40"
      >
        <RouterLink :to="`/matches/${m.id}`" class="block px-4 py-3">
          <div class="flex items-center justify-between text-xs tracking-wide text-white/40 uppercase">
            <span>{{ m.type === 'double' ? 'คู่' : 'เดี่ยว' }}</span>
            <span class="flex items-center gap-2">
              <span v-if="durationLabel(m)">{{ durationLabel(m) }} ·</span>
              {{ new Date(m.created_at).toLocaleString('th-TH') }}
            </span>
          </div>

          <div class="mt-3 flex items-center justify-between gap-3">
            <div
              class="flex flex-1 flex-col items-end gap-1.5"
              :class="{ 'opacity-50': m.winner === 'team2' }"
            >
              <div class="flex items-center gap-2">
                <span class="text-right font-medium" :class="m.winner === 'team1' ? 'text-brand-pink' : 'text-white/70'">
                  {{ m.team1_player_ids.map(nameOf).join(' & ') }}
                </span>
                <div class="flex -space-x-2">
                  <PlayerAvatar
                    v-for="pid in m.team1_player_ids"
                    :key="pid"
                    :name="nameOf(pid)"
                    :avatar-url="playerOf(pid)?.avatar_url"
                    size="sm"
                  />
                </div>
              </div>
            </div>

            <span class="hud-panel shrink-0 bg-brand-black px-2.5 py-1 font-mono text-sm text-white/80">
              {{ setsLabel(m) }}
            </span>

            <div
              class="flex flex-1 flex-col items-start gap-1.5"
              :class="{ 'opacity-50': m.winner === 'team1' }"
            >
              <div class="flex items-center gap-2">
                <div class="flex -space-x-2">
                  <PlayerAvatar
                    v-for="pid in m.team2_player_ids"
                    :key="pid"
                    :name="nameOf(pid)"
                    :avatar-url="playerOf(pid)?.avatar_url"
                    size="sm"
                  />
                </div>
                <span class="font-medium" :class="m.winner === 'team2' ? 'text-brand-pink' : 'text-white/70'">
                  {{ m.team2_player_ids.map(nameOf).join(' & ') }}
                </span>
              </div>
            </div>
          </div>
          <p v-if="m.winner === 'draw'" class="mt-1 text-center text-xs text-white/40">เสมอ</p>
        </RouterLink>
      </li>
    </ul>

    <div v-if="!loading && hasMore" class="mt-6 text-center">
      <button
        :disabled="loadingMore"
        class="rounded-full border border-brand-pink/40 px-5 py-2 text-sm font-semibold text-brand-pink hover:bg-brand-pink hover:text-brand-black disabled:opacity-50"
        @click="loadMore"
      >
        {{ loadingMore ? 'กำลังโหลด...' : 'โหลดเพิ่ม' }}
      </button>
    </div>
  </main>
</template>
