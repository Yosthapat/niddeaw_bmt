<script setup lang="ts">
import SlidePill from '@/components/common/SlidePill.vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getPlayDates, getRanking } from '@/api/public'
import type { PlayerStats } from '@/types'
import EloBadge from '@/components/players/EloBadge.vue'
import TierMascot from '@/components/players/TierMascot.vue'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'
import CreditCardMark from '@/components/credit/CreditCardMark.vue'
import HudSkeletonBlock from '@/components/common/HudSkeletonBlock.vue'
import CountUp from '@/components/common/CountUp.vue'
import PageBanner from '@/components/common/PageBanner.vue'
import { onRevisit } from '@/composables/useRevisit'
import Podium from '@/components/ranking/Podium.vue'
import { formatDate } from '@/utils/format'

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
  return formatDate(isoDate, locale.value)
}

/** `quiet`: a refresh behind what is already on screen — no skeleton, and
 *  a failure keeps the figures shown rather than replacing them. */
async function load(quiet = false): Promise<void> {
  if (!quiet) {
    loading.value = true
    error.value = null
  }
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
    if (!quiet) error.value = t('ranking.loadError')
  } finally {
    loading.value = false
  }
}

// The date picker refetches through its own @change rather than a watcher
// on selectedDate: load() assigns the default date itself, and a watcher
// couldn't tell that assignment apart from a real pick without a guard.
watch(period, () => load(), { immediate: true })
onRevisit(() => void load(true))

// The podium takes the top three; the list carries on from fourth.
const podium = computed(() => stats.value.slice(0, 3))
const rest = computed(() => stats.value.slice(3))

const PERIODS = ['all', 'year', 'day'] as const
const periodLabel = { all: 'ranking.allTime', year: 'ranking.thisYear', day: 'ranking.byDay' } as const
</script>

<template>
  <main class="pb-12 sm:pb-20">
    <PageBanner eyebrow="Leaderboard" :title="t('nav.ranking')" :sub="t('ranking.sub')" mascot="/hero/cat-color.webp">
      <div class="flex flex-wrap items-center gap-2">
        <div class="seg" role="group" :aria-label="t('ranking.periodLabel')">
          <SlidePill :watch-key="period" tone="seg" />
          <button
            v-for="p in PERIODS"
            :key="p"
            type="button"
            class="seg-btn"
            :class="{ on: period === p }"
            :data-pill-on="period === p ? '' : undefined"
            :aria-pressed="period === p"
            @click="period = p"
          >
            {{ t(periodLabel[p]) }}
          </button>
        </div>
        <select
          v-if="period === 'day' && playDates.length > 0"
          v-model="selectedDate"
          :aria-label="t('ranking.pickDay')"
          class="min-h-11 rounded-full border border-white/20 bg-white/10 px-4 text-sm text-white backdrop-blur"
          @change="load()"
        >
          <option v-for="d in playDates" :key="d" :value="d" class="bg-brand-black">{{ formatPlayDate(d) }}</option>
        </select>
      </div>
    </PageBanner>

    <div class="home-world">
      <div class="mx-auto max-w-[1200px] px-3 pt-4 sm:px-6 sm:pt-7">
        <div v-if="loading" class="grid gap-4 lg:grid-cols-[400px_minmax(0,1fr)] xl:grid-cols-[440px_minmax(0,1fr)]">
          <HudSkeletonBlock class="h-80 rounded-[22px]" />
          <div class="space-y-2">
            <HudSkeletonBlock v-for="i in 7" :key="i" :delay="i * 70" class="h-16 rounded-[18px]" />
          </div>
        </div>
        <p v-else-if="error" class="world-card p-5 text-status-error">{{ error }}</p>
        <p v-else-if="stats.length === 0" class="world-card p-5 text-white/65">
          {{ period === 'day' && playDates.length === 0 ? t('ranking.noPlayDays') : t('ranking.empty') }}
        </p>

        <div v-else class="grid items-start gap-4 lg:grid-cols-[400px_minmax(0,1fr)] lg:gap-6 xl:grid-cols-[440px_minmax(0,1fr)]">
          <!-- the podium: stays in view beside the list on a desktop -->
          <section v-reveal class="world-card p-5 sm:p-6 lg:!sticky lg:top-[calc(var(--header-h)+12px)]" aria-labelledby="ranking-podium">
            <p class="world-eyebrow">TOP 3</p>
            <h2 id="ranking-podium" class="world-title text-2xl">{{ t('ranking.podium') }}</h2>
            <Podium :top="podium" show-elo class="mt-6" />
          </section>

          <ol v-if="rest.length > 0" class="space-y-2">
            <li v-for="(s, i) in rest" :key="s.player.id" v-reveal="i">
              <RouterLink :to="`/members/${s.player.id}`" class="rank-row world-card">
                <span class="rank-no">{{ i + 4 }}</span>
                <PlayerAvatar :name="s.player.nickname" :avatar-url="s.player.avatar_url" size="md" round />
                <span class="min-w-0">
                  <span class="block truncate font-display text-[15px] font-semibold sm:text-base">{{ s.player.nickname }} <CreditCardMark :player-id="s.player.id" /></span>
                  <span class="block truncate text-[11px] text-white/55 sm:text-xs">
                    {{ s.games }} {{ t('common.game') }} · {{ t('common.win') }} {{ s.wins }} · {{ t('common.draw') }} {{ s.draws }} ·
                    {{ t('common.loss') }} {{ s.losses }}
                  </span>
                  <span class="tier-chip mt-1 sm:!hidden">
                    <TierMascot :tier="s.player.elo_level" :size="22" :interactive="false" />
                    <EloBadge :elo-score="s.player.elo_score" show-score />
                  </span>
                </span>
                <span class="tier-chip !hidden sm:!inline-flex">
                  <TierMascot :tier="s.player.elo_level" :size="24" :interactive="false" />
                  <EloBadge :elo-score="s.player.elo_score" show-score />
                </span>
                <span class="flex w-12 flex-col items-end leading-none">
                  <CountUp :value="s.points" class="pts font-display text-[22px] font-bold sm:text-2xl" />
                  <span class="mt-1 text-[10px] text-white/50">{{ t('common.points') }}</span>
                </span>
              </RouterLink>
            </li>
          </ol>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.rank-row {
  display: grid;
  grid-template-columns: 30px 44px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  min-height: 64px;
  padding: 10px 12px;
  border-radius: 18px;
  transition:
    transform 0.2s,
    border-color 0.2s;
}
.rank-row:hover {
  transform: translateY(-2px);
  border-color: rgb(255 108 192 / 0.5);
}
@media (min-width: 640px) {
  .rank-row {
    grid-template-columns: 38px 44px minmax(0, 1fr) auto auto;
    gap: 14px;
    padding: 10px 16px;
  }
}
.rank-no {
  display: flex;
  width: 30px;
  height: 30px;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: rgb(255 255 255 / 0.08);
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 700;
  color: rgb(255 255 255 / 0.8);
}
@media (min-width: 640px) {
  .rank-no {
    width: 38px;
    height: 38px;
    font-size: 15px;
  }
}
.tier-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 10px 0 4px;
  border: 1px solid rgb(255 255 255 / 0.14);
  border-radius: 999px;
  background: rgb(255 255 255 / 0.07);
}
.pts {
  color: #ff6cc0;
  text-shadow: 0 0 12px rgb(255 108 192 / 0.5);
}
@media (prefers-reduced-motion: reduce) {
  .rank-row {
    transition: none;
  }
}
</style>
