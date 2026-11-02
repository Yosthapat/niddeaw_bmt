<script setup lang="ts">
// The top three on a podium — second, first, third, the way a podium
// stands — with gold, silver and bronze rings. Used by the home page's
// top-three card and the ranking page. With fewer than three ranked, the
// ones there are still stand on their own steps.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import type { PlayerStats } from '@/types'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'
import TierMascot from '@/components/players/TierMascot.vue'

const props = defineProps<{ top: PlayerStats[]; showElo?: boolean }>()
const { t } = useI18n()

const LOOK = [
  { ring: '#ffd34d', glow: 'rgb(255 211 77 / 0.55)', base: 'rgb(255 211 77 / 0.45)', step: 'h-[110px] sm:h-[124px]', lift: 'scale-[1.18]' },
  { ring: '#d9dde8', glow: 'rgb(217 221 232 / 0.35)', base: 'rgb(217 221 232 / 0.32)', step: 'h-[78px] sm:h-[88px]', lift: '' },
  { ring: '#e39a6a', glow: 'rgb(227 154 106 / 0.35)', base: 'rgb(227 154 106 / 0.36)', step: 'h-[56px] sm:h-[64px]', lift: '' },
]

const spots = computed(() =>
  [1, 0, 2].filter((i) => props.top[i]).map((i) => ({ place: i + 1, stats: props.top[i], ...LOOK[i] })),
)
</script>

<template>
  <ol class="grid grid-cols-3 items-end gap-2.5">
    <li v-for="spot in spots" :key="spot.stats.player.id" class="flex min-w-0 flex-col items-center">
      <RouterLink :to="`/members/${spot.stats.player.id}`" class="group flex w-full min-w-0 flex-col items-center gap-1">
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
        <span class="font-display text-sm font-bold text-brand-pink-light">{{ spot.stats.points }} {{ t('common.points') }}</span>
        <span v-if="showElo" class="text-[11px] text-white/55">ELO {{ Math.round(spot.stats.player.elo_score).toLocaleString('en-US') }}</span>
      </RouterLink>
      <div
        class="mt-2 flex w-full justify-center rounded-t-[14px] rounded-b-md pt-2 font-display text-2xl font-bold text-white/90 shadow-[inset_0_1px_0_rgb(255_255_255/0.35)]"
        :class="spot.step"
        :style="{ background: `linear-gradient(180deg, ${spot.base}, rgb(255 255 255 / 0.04))` }"
        :aria-label="t('home.top3.place', { n: spot.place })"
      >
        {{ spot.place }}
      </div>
    </li>
  </ol>
</template>
