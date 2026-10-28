<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Player } from '@/types'
import { tierMeta } from '@/composables/useEloTier'
import { TIER_CARD } from '@/utils/tierCard'

// The member as a trading card: photo (or their tier's mascot until they
// have one), tier and ELO on top, record along the bottom. Shared by the
// roster grid and the front of a profile's card, so the two never drift.
const props = withDefaults(
  defineProps<{
    player: Player
    games: number
    wins: number
    draws: number
    losses: number
    /** profile: a bigger card with a larger photo */
    large?: boolean
    /** shown before the ELO, e.g. the member's rank on their profile */
    rank?: number | null
  }>(),
  { large: false, rank: null },
)

const { t } = useI18n()
const style = computed(() => TIER_CARD[props.player.elo_level])
const tierLabel = computed(() => tierMeta(props.player.elo_level).label)
const line = computed(() => props.player.quote || t('roster.tierLine', { tier: tierLabel.value }))
</script>

<template>
  <article
    class="member-card"
    :class="{ 'member-card--large': large }"
    :style="{
      '--c-light': style.light,
      '--c-mid': style.mid,
      '--c-dark': style.dark,
      '--c-text': style.text,
    }"
  >
    <div class="member-card__in">
      <div class="flex items-center justify-between gap-2">
        <span class="font-display text-[11px] font-semibold tracking-[0.12em] text-white/65">{{ player.member_code }}</span>
        <span class="elo-chip font-display"><template v-if="rank">#{{ rank }} · </template>ELO {{ player.elo_score }}</span>
      </div>

      <div class="member-card__photo">
        <img
          v-if="player.avatar_url"
          :src="player.avatar_url"
          :alt="player.nickname"
          loading="lazy"
          decoding="async"
          class="absolute inset-0 h-full w-full object-cover"
        />
        <img
          v-else
          :src="`/tiers/${player.elo_level}.webp`"
          :alt="`${tierLabel} mascot`"
          loading="lazy"
          class="member-card__mascot"
        />
        <span class="tier-chip font-display">{{ tierLabel.toUpperCase() }}</span>
        <div v-if="style.foil" class="member-card__holo" aria-hidden="true" />
        <div class="member-card__sheen" aria-hidden="true" />
      </div>

      <div class="min-w-0">
        <h2 class="truncate font-display text-base leading-tight font-bold sm:text-lg" :class="{ 'sm:text-2xl': large }">
          {{ player.nickname }}
        </h2>
        <p class="truncate text-[11px] text-white/65" :class="{ 'sm:text-sm': large }">{{ line }}</p>
      </div>

      <dl class="member-card__stats font-display">
        <div>
          <dt>{{ t('common.game') }}</dt>
          <dd>{{ games }}</dd>
        </div>
        <div>
          <dt>{{ t('common.win') }}</dt>
          <dd class="text-[#7ff0b4]">{{ wins }}</dd>
        </div>
        <div>
          <dt>{{ t('common.draw') }}</dt>
          <dd class="text-white/80">{{ draws }}</dd>
        </div>
        <div>
          <dt>{{ t('common.loss') }}</dt>
          <dd class="text-[#ff9db0]">{{ losses }}</dd>
        </div>
      </dl>
    </div>
  </article>
</template>

<style scoped>
.member-card {
  position: relative;
  height: 100%;
  border-radius: 18px;
  padding: 3px;
  background: linear-gradient(145deg, var(--c-light), var(--c-mid) 42%, var(--c-dark));
  box-shadow:
    0 14px 32px rgb(6 0 20 / 0.55),
    0 0 22px color-mix(in srgb, var(--c-mid) 33%, transparent);
  transition:
    transform 0.35s cubic-bezier(0.2, 0.8, 0.2, 1),
    box-shadow 0.35s;
}
.member-card__in {
  display: flex;
  height: 100%;
  flex-direction: column;
  gap: 8px;
  box-sizing: border-box;
  padding: 9px;
  border-radius: 15px;
  background: radial-gradient(120% 80% at 50% 0%, #2a1450 0%, #120a24 60%);
}
.member-card__photo {
  position: relative;
  display: flex;
  aspect-ratio: 1 / 0.92;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border: 1px solid rgb(255 255 255 / 0.12);
  border-radius: 12px;
  background: radial-gradient(circle at 50% 38%, color-mix(in srgb, var(--c-mid) 80%, transparent), #1a0d33 74%);
}
.member-card__mascot {
  width: 64%;
  height: 64%;
  object-fit: contain;
  filter: drop-shadow(0 12px 14px rgb(6 0 20 / 0.6));
}
.elo-chip {
  display: inline-flex;
  height: 22px;
  align-items: center;
  padding: 0 8px;
  border: 1px solid rgb(255 255 255 / 0.18);
  border-radius: 999px;
  background: rgb(0 0 0 / 0.35);
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}
.tier-chip {
  position: absolute;
  top: 7px;
  right: 7px;
  height: 20px;
  padding: 0 8px;
  border-radius: 999px;
  background: rgb(0 0 0 / 0.5);
  color: var(--c-text);
  font-size: 10px;
  font-weight: 700;
  line-height: 20px;
  letter-spacing: 0.08em;
}
.member-card__holo {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    115deg,
    transparent 18%,
    rgb(255 110 200 / 0.42) 34%,
    rgb(110 220 255 / 0.42) 46%,
    rgb(255 240 140 / 0.38) 58%,
    transparent 74%
  );
  background-position: 0% 50%;
  background-size: 260% 260%;
  mix-blend-mode: color-dodge;
  opacity: 0.55;
  pointer-events: none;
  animation: member-card-holo 7s ease-in-out infinite;
}
.member-card__sheen {
  position: absolute;
  inset: 0;
  background: linear-gradient(120deg, transparent 35%, rgb(255 255 255 / 0.22) 48%, transparent 60%);
  background-position: 0% 50%;
  background-size: 250% 250%;
  pointer-events: none;
  transition: background-position 0.7s ease;
}
@keyframes member-card-holo {
  50% {
    background-position: 100% 50%;
  }
}
.member-card__stats {
  display: grid;
  margin-top: auto;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 2px;
  padding-top: 7px;
  border-top: 1px solid rgb(255 255 255 / 0.1);
  text-align: center;
}
.member-card__stats > div {
  /* the number on top, though the label comes first in the markup as a
     <dl> requires */
  display: flex;
  flex-direction: column-reverse;
}
.member-card__stats dd {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
}
.member-card__stats dt {
  color: rgb(255 255 255 / 0.6);
  font-size: 10px;
}
.member-card--large .member-card__in {
  gap: 10px;
  padding: 12px;
}
.member-card--large .member-card__stats dd {
  font-size: 20px;
}
.member-card--large .member-card__stats dt {
  font-size: 12px;
}
.member-card--large .elo-chip {
  height: 26px;
  font-size: 14px;
}

/* The lift and tilt only where there is a mouse to hover with — on a phone
   a hover state sticks after the tap and leaves the card crooked. */
@media (hover: hover) and (pointer: fine) {
  .member-card:hover {
    transform: perspective(900px) rotateX(7deg) rotateY(-10deg) translateY(-6px);
  }
  .member-card:hover .member-card__holo {
    opacity: 0.95;
    animation-play-state: paused;
    background-position: 100% 50%;
  }
  .member-card:hover .member-card__sheen {
    background-position: 100% 50%;
  }
}
@media (prefers-reduced-motion: reduce) {
  .member-card,
  .member-card__sheen {
    transition: none;
  }
  .member-card__holo {
    animation: none;
  }
}
</style>
