<script setup lang="ts">
// The club's top three on a podium — second, first, third, the way a
// podium stands — from the same all-time ranking the ranking page opens
// on. Under it, the eight ELO tiers that used to sit in the hero: they are
// what the ranking is climbing, and here they no longer slide out from
// under the floating header when the page scrolls.
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { getRanking } from '@/api/public'
import type { EloTier, PlayerStats } from '@/types'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'
import TierMascot from '@/components/players/TierMascot.vue'

const emit = defineEmits<{ reveal: [tier: EloTier] }>()
const { t } = useI18n()

// Ordered by rising alcohol content — matches elo_service.py's
// _TIER_THRESHOLDS order.
const TIERS: { tier: EloTier; label: string }[] = [
  { tier: 'milk', label: 'Milk' },
  { tier: 'beer', label: 'Beer' },
  { tier: 'highball', label: 'Highball' },
  { tier: 'wine', label: 'Wine' },
  { tier: 'soju', label: 'Soju' },
  { tier: 'whisky', label: 'Whisky' },
  { tier: 'vodka', label: 'Vodka' },
  { tier: 'absinthe', label: 'Absinthe' },
]

const top = ref<PlayerStats[] | null>(null)
const failed = ref(false)

onMounted(async () => {
  try {
    top.value = (await getRanking('all')).slice(0, 3)
  } catch {
    failed.value = true
  }
})

const STYLE = [
  { ring: '#ffd34d', glow: 'rgb(255 211 77 / 0.55)', base: 'rgb(255 211 77 / 0.45)', step: 'h-[124px]', lift: 'scale-[1.18]' },
  { ring: '#d9dde8', glow: 'rgb(217 221 232 / 0.35)', base: 'rgb(217 221 232 / 0.32)', step: 'h-[88px]', lift: '' },
  { ring: '#e39a6a', glow: 'rgb(227 154 106 / 0.35)', base: 'rgb(227 154 106 / 0.36)', step: 'h-[64px]', lift: '' },
]

// 2 · 1 · 3 across the podium. With fewer than three ranked, the ones
// there are still stand on their own steps.
const podium = computed(() => {
  const list = top.value ?? []
  return [1, 0, 2]
    .filter((place) => list[place])
    .map((place) => ({ place: place + 1, stats: list[place], ...STYLE[place] }))
})
</script>

<template>
  <section class="top3 world-card flex flex-col p-6" aria-labelledby="home-top3">
    <p class="world-eyebrow">RANKING</p>
    <h2 id="home-top3" class="world-title mt-1 text-2xl">{{ t('home.top3.title') }}</h2>

    <div v-if="top === null && !failed" class="mt-6 grid flex-1 grid-cols-3 items-end gap-2.5" aria-hidden="true">
      <span v-for="h in ['h-[150px]', 'h-[190px]', 'h-[120px]']" :key="h" class="skeleton" :class="h" />
    </div>
    <p v-else-if="failed || podium.length === 0" class="mt-6 flex-1 text-sm text-white/60">
      {{ failed ? t('ranking.loadError') : t('ranking.empty') }}
    </p>
    <ol v-else class="mt-6 grid flex-1 grid-cols-3 items-end gap-2.5">
      <li v-for="spot in podium" :key="spot.place" class="flex min-w-0 flex-col items-center">
        <RouterLink :to="`/members/${spot.stats.player.id}`" class="group flex w-full min-w-0 flex-col items-center gap-1.5">
          <TierMascot :tier="spot.stats.player.elo_level" :size="30" :interactive="false" />
          <span
            class="mt-1 rounded-full transition-transform group-hover:-translate-y-1"
            :class="spot.lift"
            :style="{ boxShadow: `0 0 0 3px ${spot.ring}, 0 0 26px ${spot.glow}` }"
          >
            <PlayerAvatar :name="spot.stats.player.nickname" :avatar-url="spot.stats.player.avatar_url" size="lg" round />
          </span>
          <span class="mt-2 w-full truncate text-center font-display text-[15px] font-semibold group-hover:text-brand-pink-light">
            {{ spot.stats.player.nickname }}
          </span>
          <span class="text-xs text-white/55">{{ spot.stats.points }} {{ t('common.points') }}</span>
        </RouterLink>
        <div
          class="mt-2 flex w-full justify-center rounded-t-[14px] rounded-b-md pt-2 font-display text-2xl font-bold text-white/90"
          :class="spot.step"
          :style="{ background: `linear-gradient(180deg, ${spot.base}, rgb(255 255 255 / 0.04))` }"
          :aria-label="t('home.top3.place', { n: spot.place })"
        >
          {{ spot.place }}
        </div>
      </li>
    </ol>

    <div class="mt-5">
      <p class="text-xs text-white/55">{{ t('home.hero.tiersLabel') }}</p>
      <div class="mt-1.5 flex justify-between rounded-2xl border border-white/10 bg-white/5 px-1.5 py-1">
        <button
          v-for="tier in TIERS"
          :key="tier.tier"
          type="button"
          class="flex min-h-11 min-w-9 items-center justify-center rounded-xl transition-transform hover:-translate-y-0.5"
          :aria-label="`${tier.label} tier — เปิดฉากเต็มจอ`"
          @click="emit('reveal', tier.tier)"
        >
          <TierMascot :tier="tier.tier" :size="30" :interactive="false" />
        </button>
      </div>
    </div>
    <RouterLink to="/ranking" class="mt-2 inline-flex min-h-11 items-center gap-1 self-end text-sm text-white/75 hover:text-white">
      {{ t('home.top3.all') }} <span aria-hidden="true">→</span>
    </RouterLink>
  </section>
</template>

<style scoped>
.skeleton {
  border-radius: 14px;
  background: linear-gradient(100deg, rgb(255 255 255 / 0.05) 30%, rgb(255 255 255 / 0.12) 50%, rgb(255 255 255 / 0.05) 70%);
  background-size: 200% 100%;
  animation: shimmer 1.4s linear infinite;
}
@keyframes shimmer {
  to {
    background-position: -200% 0;
  }
}
@media (prefers-reduced-motion: reduce) {
  .skeleton {
    animation: none;
  }
}
</style>
