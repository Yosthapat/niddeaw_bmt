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
  <main class="mx-auto max-w-3xl px-4 py-8">
    <h1 class="text-2xl font-bold text-brand-pink">ผลแมตช์</h1>

    <p v-if="loading" class="mt-6 text-white/60">กำลังโหลด...</p>
    <p v-else-if="error" class="mt-6 text-red-400">{{ error }}</p>
    <p v-else-if="sortedMatches.length === 0" class="mt-6 text-white/60">ยังไม่มีผลแมตช์</p>

    <ul v-else class="mt-6 space-y-3">
      <li
        v-for="m in sortedMatches"
        :key="m.id"
        class="rounded-xl border border-brand-pink-dark/40 bg-white/5 px-4 py-3"
      >
        <div class="flex items-center justify-between text-sm text-white/50">
          <span>{{ m.type === 'double' ? 'คู่' : 'เดี่ยว' }}</span>
          <span>{{ new Date(m.created_at).toLocaleString('th-TH') }}</span>
        </div>
        <div class="mt-2 flex items-center justify-between gap-3">
          <span
            class="flex-1 text-right font-medium"
            :class="m.winner === 'team1' ? 'text-brand-pink' : 'text-white/80'"
          >
            {{ teamLabel(m.team1_player_ids) }}
          </span>
          <span class="shrink-0 rounded bg-black/40 px-2 py-1 text-sm font-mono">
            {{ setsLabel(m) }}
          </span>
          <span
            class="flex-1 text-left font-medium"
            :class="m.winner === 'team2' ? 'text-brand-pink' : 'text-white/80'"
          >
            {{ teamLabel(m.team2_player_ids) }}
          </span>
        </div>
        <p v-if="m.winner === 'draw'" class="mt-1 text-center text-xs text-white/40">เสมอ</p>
      </li>
    </ul>
  </main>
</template>
