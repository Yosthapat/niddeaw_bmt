<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getMatches, getPlayers } from '@/api/public'
import type { Match, Player } from '@/types'

const matches = ref<Match[]>([])
const playersById = ref<Record<string, Player>>({})
const loading = ref(true)
const error = ref<string | null>(null)

function nameOf(playerId: string): string {
  const p = playersById.value[playerId]
  return p ? p.nickname || p.name : '?'
}

function teamLabel(ids: string[]): string {
  return ids.map(nameOf).join(' & ')
}

function setsLabel(match: Match): string {
  if (!match.sets) return '-'
  return match.sets.map(([a, b]) => `${a}-${b}`).join(', ')
}

const sortedMatches = computed(() =>
  [...matches.value].sort((a, b) => b.created_at.localeCompare(a.created_at)),
)

onMounted(async () => {
  try {
    const [matchList, stats] = await Promise.all([getMatches(), getPlayers()])
    matches.value = matchList
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
        class="hud-panel border border-brand-pink/15 bg-brand-surface px-4 py-3"
      >
        <div class="flex items-center justify-between text-xs tracking-wide text-white/40 uppercase">
          <span>{{ m.type === 'double' ? 'คู่' : 'เดี่ยว' }}</span>
          <span>{{ new Date(m.created_at).toLocaleString('th-TH') }}</span>
        </div>
        <div class="mt-2 flex items-center justify-between gap-3">
          <span
            class="flex-1 text-right font-medium"
            :class="m.winner === 'team1' ? 'text-brand-pink' : 'text-white/70'"
          >
            {{ teamLabel(m.team1_player_ids) }}
          </span>
          <span class="hud-panel shrink-0 bg-brand-black px-2.5 py-1 font-mono text-sm text-white/80">
            {{ setsLabel(m) }}
          </span>
          <span
            class="flex-1 text-left font-medium"
            :class="m.winner === 'team2' ? 'text-brand-pink' : 'text-white/70'"
          >
            {{ teamLabel(m.team2_player_ids) }}
          </span>
        </div>
        <p v-if="m.winner === 'draw'" class="mt-1 text-center text-xs text-white/40">เสมอ</p>
      </li>
    </ul>
  </main>
</template>
