<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getPlayers } from '@/api/public'
import type { PlayerStats } from '@/types'
import EloBadge from '@/components/players/EloBadge.vue'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'

const stats = ref<PlayerStats[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

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
  <main class="mx-auto max-w-4xl px-4 py-8">
    <h1 class="text-2xl font-bold text-brand-pink">สมาชิก</h1>

    <p v-if="loading" class="mt-6 text-white/60">กำลังโหลด...</p>
    <p v-else-if="error" class="mt-6 text-red-400">{{ error }}</p>
    <p v-else-if="stats.length === 0" class="mt-6 text-white/60">ยังไม่มีสมาชิก</p>

    <div v-else class="mt-6 overflow-x-auto rounded-xl border border-brand-pink-dark/40">
      <table class="w-full min-w-[640px] text-left text-sm">
        <thead class="bg-brand-pink-dark/20 text-white/70">
          <tr>
            <th class="px-3 py-2">ผู้เล่น</th>
            <th class="px-3 py-2">Level</th>
            <th class="px-3 py-2 text-right">Game</th>
            <th class="px-3 py-2 text-right">Win</th>
            <th class="px-3 py-2 text-right">Draw</th>
            <th class="px-3 py-2 text-right">Loss</th>
            <th class="px-3 py-2 text-right">Pts</th>
            <th class="px-3 py-2 text-right">Avg</th>
            <th class="px-3 py-2 text-right">Sc(%)</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-white/10">
          <tr v-for="s in stats" :key="s.player.id">
            <td class="px-3 py-2 font-medium">
              <RouterLink :to="`/members/${s.player.id}`" class="flex items-center gap-2 hover:text-brand-pink">
                <PlayerAvatar :name="s.player.name" :avatar-url="s.player.avatar_url" size="sm" />
                {{ s.player.nickname || s.player.name }}
              </RouterLink>
            </td>
            <td class="px-3 py-2"><EloBadge :elo-score="s.player.elo_score" /></td>
            <td class="px-3 py-2 text-right">{{ s.games }}</td>
            <td class="px-3 py-2 text-right">{{ s.wins }}</td>
            <td class="px-3 py-2 text-right">{{ s.draws }}</td>
            <td class="px-3 py-2 text-right">{{ s.losses }}</td>
            <td class="px-3 py-2 text-right font-semibold text-brand-pink">{{ s.points }}</td>
            <td class="px-3 py-2 text-right">{{ s.avg_points.toFixed(2) }}</td>
            <td class="px-3 py-2 text-right">{{ s.score_percent.toFixed(1) }}%</td>
          </tr>
        </tbody>
      </table>
    </div>
  </main>
</template>
