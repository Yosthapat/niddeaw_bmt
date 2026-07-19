<script setup lang="ts">
import { ref, watch } from 'vue'
import { getRanking } from '@/api/public'
import type { PlayerStats } from '@/types'
import EloBadge from '@/components/players/EloBadge.vue'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'

const period = ref<'all' | 'year'>('all')
const stats = ref<PlayerStats[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    stats.value = await getRanking(period.value)
  } catch {
    error.value = 'โหลดอันดับไม่สำเร็จ'
  } finally {
    loading.value = false
  }
}

watch(period, load, { immediate: true })

const medalByRank = ['🥇', '🥈', '🥉']
</script>

<template>
  <main class="mx-auto max-w-3xl px-4 py-8">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold text-brand-pink">อันดับ</h1>
      <div class="flex gap-1 rounded-full border border-brand-pink-dark/40 p-1 text-sm">
        <button
          class="rounded-full px-3 py-1"
          :class="period === 'all' ? 'bg-brand-pink text-brand-black font-semibold' : 'text-white/70'"
          @click="period = 'all'"
        >
          All-time
        </button>
        <button
          class="rounded-full px-3 py-1"
          :class="period === 'year' ? 'bg-brand-pink text-brand-black font-semibold' : 'text-white/70'"
          @click="period = 'year'"
        >
          รายปี
        </button>
      </div>
    </div>

    <p v-if="loading" class="mt-6 text-white/60">กำลังโหลด...</p>
    <p v-else-if="error" class="mt-6 text-red-400">{{ error }}</p>
    <p v-else-if="stats.length === 0" class="mt-6 text-white/60">ยังไม่มีข้อมูลอันดับ</p>

    <ol v-else class="mt-6 space-y-2">
      <li
        v-for="(s, i) in stats"
        :key="s.player.id"
        class="flex items-center gap-3 rounded-xl border border-brand-pink-dark/40 bg-white/5 px-4 py-3"
      >
        <span class="w-8 text-center text-lg font-bold text-brand-pink-light">
          {{ medalByRank[i] ?? i + 1 }}
        </span>
        <RouterLink :to="`/members/${s.player.id}`" class="flex flex-1 items-center gap-3 hover:text-brand-pink">
          <PlayerAvatar :name="s.player.name" :avatar-url="s.player.avatar_url" size="sm" />
          <div>
            <p class="font-medium">{{ s.player.nickname || s.player.name }}</p>
            <p class="text-xs text-white/50">{{ s.games }} เกม · ชนะ {{ s.wins }}</p>
          </div>
        </RouterLink>
        <EloBadge :elo-score="s.player.elo_score" show-score />
        <span class="w-12 text-right text-lg font-bold text-brand-pink">{{ s.points }}</span>
      </li>
    </ol>
  </main>
</template>
