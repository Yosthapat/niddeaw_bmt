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
  <main class="mx-auto max-w-3xl px-4 py-8 sm:py-12">
    <p class="text-xs font-semibold tracking-widest text-brand-pink/70 uppercase">Legends</p>
    <h1 class="font-display text-3xl font-bold text-white">Hall of Fame</h1>
    <p class="mt-1 text-sm text-white/40">อันดับตลอดกาล (ต้องเล่นอย่างน้อย 5 เกม)</p>

    <p v-if="loading" class="mt-6 text-white/60">กำลังโหลด...</p>
    <p v-else-if="error" class="mt-6 text-red-400">{{ error }}</p>
    <p v-else-if="stats.length === 0" class="mt-6 text-white/60">
      ยังไม่มีใครเล่นครบ 5 เกม — เล่นเยอะๆ แล้วมาอยู่ตรงนี้กัน!
    </p>

    <div v-else class="mt-6 grid gap-3 sm:grid-cols-2">
      <div
        v-for="(s, i) in stats"
        :key="s.player.id"
        class="hud-panel flex items-center gap-3 border bg-brand-surface p-4"
        :class="i === 0 ? 'border-brand-pink/70 bg-brand-pink/5' : 'border-brand-pink/15'"
      >
        <RouterLink :to="`/members/${s.player.id}`" class="flex flex-1 items-center gap-3 hover:opacity-80">
          <PlayerAvatar :name="s.player.name" :avatar-url="s.player.avatar_url" size="lg" />
          <div class="flex-1">
            <p class="font-display font-bold">
              {{ i === 0 ? '👑 ' : '' }}{{ s.player.nickname || s.player.name }}
            </p>
            <p class="text-xs text-white/40">
              {{ s.games }} เกม · {{ s.points }} pts · Sc {{ s.score_percent.toFixed(0) }}%
            </p>
            <EloBadge :elo-score="s.player.elo_score" show-score class="mt-1" />
          </div>
        </RouterLink>
      </div>
    </div>
  </main>
</template>
