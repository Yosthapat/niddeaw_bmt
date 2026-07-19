<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getHallOfFame } from '@/api/public'
import type { PlayerStats } from '@/types'
import EloBadge from '@/components/players/EloBadge.vue'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'

const stats = ref<PlayerStats[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    stats.value = await getHallOfFame()
  } catch {
    error.value = 'โหลด Hall of Fame ไม่สำเร็จ'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <main class="mx-auto max-w-3xl px-4 py-8">
    <h1 class="text-2xl font-bold text-brand-pink">🏆 Hall of Fame</h1>
    <p class="mt-1 text-sm text-white/50">อันดับตลอดกาล (ต้องเล่นอย่างน้อย 5 เกม)</p>

    <p v-if="loading" class="mt-6 text-white/60">กำลังโหลด...</p>
    <p v-else-if="error" class="mt-6 text-red-400">{{ error }}</p>
    <p v-else-if="stats.length === 0" class="mt-6 text-white/60">
      ยังไม่มีใครเล่นครบ 5 เกม — เล่นเยอะๆ แล้วมาอยู่ตรงนี้กัน!
    </p>

    <div v-else class="mt-6 grid gap-3 sm:grid-cols-2">
      <div
        v-for="(s, i) in stats"
        :key="s.player.id"
        class="flex items-center gap-3 rounded-xl border p-4"
        :class="
          i === 0
            ? 'border-brand-pink bg-brand-pink/10'
            : 'border-brand-pink-dark/40 bg-white/5'
        "
      >
        <PlayerAvatar :name="s.player.name" :avatar-url="s.player.avatar_url" size="lg" />
        <div class="flex-1">
          <p class="font-bold">
            {{ i === 0 ? '👑 ' : '' }}{{ s.player.nickname || s.player.name }}
          </p>
          <p class="text-xs text-white/50">
            {{ s.games }} เกม · {{ s.points }} pts · Sc {{ s.score_percent.toFixed(0) }}%
          </p>
          <EloBadge :elo-score="s.player.elo_score" show-score class="mt-1" />
        </div>
      </div>
    </div>
  </main>
</template>
