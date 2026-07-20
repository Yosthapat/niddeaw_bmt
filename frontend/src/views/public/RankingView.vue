<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getRanking } from '@/api/public'
import type { PlayerStats } from '@/types'
import EloBadge from '@/components/players/EloBadge.vue'
import TierMascot from '@/components/players/TierMascot.vue'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'

const { t } = useI18n()

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
    error.value = t('ranking.loadError')
  } finally {
    loading.value = false
  }
}

watch(period, load, { immediate: true })

const medalByRank = ['🥇', '🥈', '🥉']
</script>

<template>
  <main class="mx-auto max-w-3xl px-4 py-8 sm:py-12">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <p class="text-xs font-semibold tracking-widest text-brand-pink/70 uppercase">Leaderboard</p>
        <h1 class="font-display text-3xl font-bold text-white">{{ t('nav.ranking') }}</h1>
      </div>
      <div class="hud-panel flex border border-brand-pink/25 bg-brand-surface p-1 text-sm">
        <button
          class="px-3 py-1.5 font-semibold transition-colors"
          :class="period === 'all' ? 'bg-brand-pink text-brand-black' : 'text-white/50 hover:text-white'"
          @click="period = 'all'"
        >
          {{ t('ranking.allTime') }}
        </button>
        <button
          class="px-3 py-1.5 font-semibold transition-colors"
          :class="period === 'year' ? 'bg-brand-pink text-brand-black' : 'text-white/50 hover:text-white'"
          @click="period = 'year'"
        >
          {{ t('ranking.thisYear') }}
        </button>
      </div>
    </div>

    <p v-if="loading" class="mt-6 text-white/60">{{ t('common.loading') }}</p>
    <p v-else-if="error" class="mt-6 text-status-error">{{ error }}</p>
    <p v-else-if="stats.length === 0" class="mt-6 text-white/60">{{ t('ranking.empty') }}</p>

    <ol v-else class="mt-6 space-y-2">
      <li
        v-for="(s, i) in stats"
        :key="s.player.id"
        class="hud-panel flex items-center gap-3 border bg-brand-surface px-4 py-3"
        :class="i === 0 ? 'border-brand-pink/70' : 'border-brand-pink/15'"
      >
        <span class="w-9 text-center font-display text-xl font-bold text-white/80">
          {{ medalByRank[i] ?? i + 1 }}
        </span>
        <RouterLink :to="`/members/${s.player.id}`" class="flex flex-1 items-center gap-3 hover:text-brand-pink">
          <PlayerAvatar :name="s.player.nickname" :avatar-url="s.player.avatar_url" size="sm" />
          <div>
            <p class="font-medium">{{ s.player.nickname }}</p>
            <p class="text-xs text-white/40">{{ s.games }} {{ t('common.game') }} · {{ t('common.win') }} {{ s.wins }}</p>
          </div>
        </RouterLink>
        <TierMascot :tier="s.player.elo_level" :size="28" class="hidden sm:block" />
        <EloBadge :elo-score="s.player.elo_score" show-score class="hidden sm:inline-flex" />
        <span class="w-12 text-right font-display text-lg font-bold text-brand-pink">{{ s.points }}</span>
      </li>
    </ol>
  </main>
</template>
