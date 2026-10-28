<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { PlayerProfile } from '@/types'
import { tierMeta } from '@/composables/useEloTier'
import { TIER_CARD } from '@/utils/tierCard'
import MemberCard from '@/components/players/MemberCard.vue'

// The profile's card: the same card as on the roster, which turns over to
// show how this member plays — win rate, the split of their results, rank
// and the opponent they meet most. A tap turns it; so does Enter or Space.
const props = defineProps<{ profile: PlayerProfile }>()

const { t } = useI18n()
const flipped = ref(false)
const style = computed(() => TIER_CARD[props.profile.player.elo_level])
const winRate = computed(() =>
  props.profile.games ? Math.round((props.profile.wins / props.profile.games) * 100) : 0,
)
const bars = computed(() => {
  const g = Math.max(1, props.profile.games)
  return [
    { label: t('common.win'), n: props.profile.wins, pct: (props.profile.wins / g) * 100, color: '#7ff0b4' },
    { label: t('common.draw'), n: props.profile.draws, pct: (props.profile.draws / g) * 100, color: 'rgb(255 255 255 / 0.7)' },
    { label: t('common.loss'), n: props.profile.losses, pct: (props.profile.losses / g) * 100, color: '#ff9db0' },
  ]
})
</script>

<template>
  <div class="flip-wrap">
    <!-- a div acting as the button: a real <button> may not hold the card's
         heading and blocks -->
    <div
      role="button"
      tabindex="0"
      class="flip"
      :class="{ 'is-flipped': flipped }"
      :aria-pressed="flipped"
      :aria-label="flipped ? t('card.showFront') : t('card.showBack')"
      @click="flipped = !flipped"
      @keydown.enter.prevent="flipped = !flipped"
      @keydown.space.prevent="flipped = !flipped"
    >
      <div class="face" :aria-hidden="flipped">
        <MemberCard
          :player="profile.player"
          :games="profile.games"
          :wins="profile.wins"
          :draws="profile.draws"
          :losses="profile.losses"
          :rank="profile.elo_rank"
          large
        />
      </div>

      <div
        class="face face--back"
        :aria-hidden="!flipped"
        :style="{
          background: `linear-gradient(145deg, ${style.light}, ${style.mid} 42%, ${style.dark})`,
        }"
      >
        <div class="back-in">
          <div class="flex items-center justify-between">
            <span class="truncate font-display text-lg font-bold">{{ profile.player.nickname }}</span>
            <img :src="`/tiers/${profile.player.elo_level}.webp`" alt="" width="40" height="40" class="h-10 w-10" />
          </div>
          <div class="flex items-baseline gap-2">
            <span class="font-display text-5xl leading-none font-bold" :style="{ color: style.text }">{{ winRate }}%</span>
            <span class="text-sm text-white/70">{{ t('card.winsOf', { n: profile.games }) }}</span>
          </div>
          <div class="flex flex-col gap-2.5">
            <div v-for="bar in bars" :key="bar.label" class="flex flex-col gap-1">
              <div class="flex justify-between text-[13px]">
                <span class="text-white/75">{{ bar.label }}</span>
                <span class="font-display font-bold">{{ bar.n }}</span>
              </div>
              <div class="h-2 overflow-hidden rounded-full bg-white/10">
                <div class="h-full rounded-full" :style="{ width: `${bar.pct}%`, background: bar.color }" />
              </div>
            </div>
          </div>
          <dl class="grid grid-cols-2 gap-2 text-left">
            <div class="back-cell">
              <dt>ELO</dt>
              <dd>{{ profile.player.elo_score }} · #{{ profile.elo_rank }}</dd>
            </div>
            <div class="back-cell">
              <dt>{{ t('profile.nemesis') }}</dt>
              <dd class="truncate">{{ profile.nemesis ? profile.nemesis.player.nickname : '—' }}</dd>
            </div>
          </dl>
          <p class="mt-auto truncate text-center text-xs text-white/55">
            {{ tierMeta(profile.player.elo_level).label }} · {{ profile.player.member_code }}
          </p>
        </div>
      </div>
    </div>
    <p class="mt-3 text-center text-xs text-white/50" aria-hidden="true">{{ t('card.tapToFlip') }}</p>
  </div>
</template>

<style scoped>
.flip-wrap {
  width: 100%;
  max-width: 20rem;
  margin: 0 auto;
  perspective: 1100px;
}
.flip {
  position: relative;
  cursor: pointer;
  display: grid;
  width: 100%;
  border-radius: 18px;
  text-align: inherit;
  transform-style: preserve-3d;
  transition: transform 0.6s cubic-bezier(0.2, 0.8, 0.2, 1);
}
.flip:focus-visible {
  outline: 2px solid var(--color-brand-pink);
  outline-offset: 4px;
}
.flip.is-flipped {
  transform: rotateY(180deg);
}
/* both faces in the same grid cell, so the card is as tall as the front */
.face {
  grid-area: 1 / 1;
  -webkit-backface-visibility: hidden;
  backface-visibility: hidden;
}
.face--back {
  padding: 3px;
  border-radius: 18px;
  box-shadow: 0 24px 50px rgb(6 0 20 / 0.6);
  transform: rotateY(180deg);
}
.back-in {
  display: flex;
  height: 100%;
  flex-direction: column;
  gap: 14px;
  box-sizing: border-box;
  padding: 16px;
  border-radius: 15px;
  background: radial-gradient(120% 80% at 50% 100%, #2a1450 0%, #120a24 62%);
}
.back-cell {
  min-width: 0;
  padding: 8px 10px;
  border: 1px solid rgb(255 255 255 / 0.1);
  border-radius: 10px;
  background: rgb(255 255 255 / 0.04);
}
.back-cell dt {
  color: rgb(255 255 255 / 0.55);
  font-size: 11px;
}
.back-cell dd {
  margin: 2px 0 0;
  font-family: var(--font-display);
  font-weight: 700;
}
@media (prefers-reduced-motion: reduce) {
  .flip {
    transition: none;
  }
}
</style>
