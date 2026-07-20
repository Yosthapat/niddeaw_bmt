<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getPlayers } from '@/api/public'
import type { PlayerStats } from '@/types'
import EloBadge from '@/components/players/EloBadge.vue'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'

const stats = ref<PlayerStats[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const search = ref('')

const filteredStats = computed(() => {
  const query = search.value.trim().toLowerCase()
  if (!query) return stats.value
  return stats.value.filter((s) =>
    [s.player.name, s.player.nickname ?? ''].some((field) => field.toLowerCase().includes(query)),
  )
})

onMounted(async () => {
  try {
    stats.value = (await getPlayers()).sort((a, b) => b.points - a.points)
  } catch {
    error.value = 'โหลดข้อมูลสมาชิกไม่สำเร็จ'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <main class="mx-auto max-w-4xl px-4 py-8 sm:py-12">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <p class="text-xs font-semibold tracking-widest text-brand-pink/70 uppercase">Roster</p>
        <h1 class="font-display text-3xl font-bold text-white">สมาชิก</h1>
      </div>
      <input
        v-model="search"
        type="search"
        placeholder="ค้นหาสมาชิก..."
        class="hud-panel w-full max-w-xs border border-brand-pink/25 bg-brand-surface px-4 py-2 text-sm outline-none focus:border-brand-pink"
      />
    </div>

    <p v-if="loading" class="mt-6 text-white/60">กำลังโหลด...</p>
    <p v-else-if="error" class="mt-6 text-status-error">{{ error }}</p>
    <p v-else-if="stats.length === 0" class="mt-6 text-white/60">ยังไม่มีสมาชิก</p>
    <p v-else-if="filteredStats.length === 0" class="mt-6 text-white/60">ไม่พบสมาชิกที่ค้นหา</p>

    <div v-else class="hud-panel mt-6 overflow-x-auto border border-brand-pink/20 bg-brand-surface">
      <table class="w-full min-w-[680px] text-left text-sm">
        <thead class="border-b border-brand-pink/20 text-xs font-semibold tracking-wider text-white/40 uppercase">
          <tr>
            <th class="px-4 py-3">ผู้เล่น</th>
            <th class="px-4 py-3">Level</th>
            <th class="px-4 py-3 text-right">Game</th>
            <th class="px-4 py-3 text-right">Win</th>
            <th class="px-4 py-3 text-right">Draw</th>
            <th class="px-4 py-3 text-right">Loss</th>
            <th class="px-4 py-3 text-right">Pts</th>
            <th class="px-4 py-3 text-right">Avg</th>
            <th class="px-4 py-3 text-right">Sc(%)</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-white/5">
          <tr v-for="s in filteredStats" :key="s.player.id" class="transition-colors hover:bg-brand-surface-raised">
            <td class="px-4 py-3 font-medium">
              <RouterLink :to="`/members/${s.player.id}`" class="flex items-center gap-2.5 hover:text-brand-pink">
                <PlayerAvatar :name="s.player.name" :avatar-url="s.player.avatar_url" size="sm" />
                {{ s.player.nickname || s.player.name }}
              </RouterLink>
            </td>
            <td class="px-4 py-3"><EloBadge :elo-score="s.player.elo_score" /></td>
            <td class="px-4 py-3 text-right text-white/70">{{ s.games }}</td>
            <td class="px-4 py-3 text-right text-white/70">{{ s.wins }}</td>
            <td class="px-4 py-3 text-right text-white/70">{{ s.draws }}</td>
            <td class="px-4 py-3 text-right text-white/70">{{ s.losses }}</td>
            <td class="px-4 py-3 text-right font-display font-semibold text-brand-pink">{{ s.points }}</td>
            <td class="px-4 py-3 text-right text-white/70">{{ s.avg_points.toFixed(2) }}</td>
            <td class="px-4 py-3 text-right text-white/70">{{ s.score_percent.toFixed(1) }}%</td>
          </tr>
        </tbody>
      </table>
    </div>
  </main>
</template>
