<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getPlayDates, getRanking } from '@/api/public'
import type { PlayerStats } from '@/types'
import EloBadge from '@/components/players/EloBadge.vue'
import TierMascot from '@/components/players/TierMascot.vue'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'
import HudSkeletonBlock from '@/components/common/HudSkeletonBlock.vue'
import CountUp from '@/components/common/CountUp.vue'
import StaggerHeading from '@/components/common/StaggerHeading.vue'

const { t, locale } = useI18n()

const period = ref<'all' | 'year' | 'day'>('all')
const stats = ref<PlayerStats[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

// Days that actually have matches, newest first — the backend only lists
// dates whose leaderboard is non-empty, so the picker can't land on a blank
// day. Fetched once, the first time the daily tab is opened.
const playDates = ref<string[]>([])
const selectedDate = ref<string>('')

function formatPlayDate(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString(locale.value === 'th' ? 'th-TH' : 'en-US', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    if (period.value === 'day') {
      if (playDates.value.length === 0) {
        playDates.value = await getPlayDates()
      }
      // Default to the latest play day. A date picked earlier is kept when
      // it's still in the list, so switching tabs away and back doesn't
      // silently jump the user back to today's session.
      if (!playDates.value.includes(selectedDate.value)) {
        selectedDate.value = playDates.value[0] ?? ''
      }
      stats.value = selectedDate.value ? await getRanking('day', selectedDate.value) : []
    } else {
      stats.value = await getRanking(period.value)
    }
  } catch {
    error.value = t('ranking.loadError')
  } finally {
    loading.value = false
  }
}

// The date picker refetches through its own @change rather than a watcher
// on selectedDate: load() assigns the default date itself, and a watcher
// couldn't tell that assignment apart from a real pick without a guard.
watch(period, load, { immediate: true })

const medalByRank = ['🥇', '🥈', '🥉']
const rankBadgeClass = ['rank-badge-gold', 'rank-badge-silver', 'rank-badge-bronze']
</script>

<template>
  <main class="mx-auto max-w-3xl px-4 py-8 sm:py-12">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <p class="text-xs font-semibold tracking-widest text-brand-pink/70 uppercase">Leaderboard</p>
        <h1 class="font-display text-3xl font-bold text-white"><StaggerHeading :text="t('nav.ranking')" /></h1>
      </div>
      <div class="flex flex-wrap items-center gap-2">
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
          <button
            class="px-3 py-1.5 font-semibold transition-colors"
            :class="period === 'day' ? 'bg-brand-pink text-brand-black' : 'text-white/50 hover:text-white'"
            @click="period = 'day'"
          >
            {{ t('ranking.byDay') }}
          </button>
        </div>
        <select
          v-if="period === 'day' && playDates.length > 0"
          v-model="selectedDate"
          :aria-label="t('ranking.pickDay')"
          class="hud-panel border border-brand-pink/25 bg-brand-surface px-3 py-2 text-sm text-white"
          @change="load"
        >
          <option v-for="d in playDates" :key="d" :value="d">{{ formatPlayDate(d) }}</option>
        </select>
      </div>
    </div>

    <div v-if="loading" class="mt-6 space-y-2">
      <HudSkeletonBlock v-for="i in 8" :key="i" :delay="i * 70" class="h-16" />
    </div>
    <p v-else-if="error" class="mt-6 text-status-error">{{ error }}</p>
    <p v-else-if="stats.length === 0" class="mt-6 text-white/60">
      {{ period === 'day' && playDates.length === 0 ? t('ranking.noPlayDays') : t('ranking.empty') }}
    </p>

    <ol v-else class="mt-6 space-y-2">
      <li
        v-for="(s, i) in stats"
        :key="s.player.id"
        v-reveal="i"
        v-tilt="i < 3"
        class="hud-panel glass-panel hud-hover flex items-center gap-3 border px-4 py-3"
        :class="[i < 3 ? 'float-idle' : '', i === 0 ? 'border-brand-pink/70 bg-gradient-to-r from-brand-pink/10 to-transparent' : 'border-brand-pink/15']"
        :style="i < 3 ? { '--float-delay': `${i * 0.3}s` } : undefined"
      >
        <span
          class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full font-display text-sm font-bold"
          :class="rankBadgeClass[i] ?? 'bg-brand-black text-white/70'"
        >
          {{ medalByRank[i] ?? i + 1 }}
        </span>
        <RouterLink :to="`/members/${s.player.id}`" class="flex flex-1 items-center gap-3 hover:text-brand-pink">
          <PlayerAvatar :name="s.player.nickname" :avatar-url="s.player.avatar_url" size="sm" />
          <div>
            <p class="font-medium">{{ s.player.nickname }}</p>
            <p class="text-xs text-white/40">
              {{ s.games }} {{ t('common.game') }} · {{ t('common.win') }} <CountUp :value="s.wins" />
            </p>
          </div>
        </RouterLink>
        <TierMascot :tier="s.player.elo_level" :size="28" class="hidden sm:block" />
        <EloBadge :elo-score="s.player.elo_score" show-score class="hidden sm:inline-flex" />
        <CountUp :value="s.points" class="w-12 text-right font-display text-lg font-bold text-brand-pink" />
      </li>
    </ol>
  </main>
</template>
