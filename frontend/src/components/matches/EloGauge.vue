<script setup lang="ts">
/**
 * How even a match is, as a tug of war: each team's average ELO at the ends,
 * the bar filled pink from team 1's side and violet from team 2's, meeting
 * at team 1's chance to win (the line in the middle is 50:50).
 *
 * The first time it is seen the fills grow out from the middle and the knob
 * lands on the split. While the match is on (`live`) light runs along both
 * sides and the knob breathes; a finished match lights the winner's side.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { winChance } from '@/utils/eloOdds'

const props = withDefaults(
  defineProps<{
    elo1: number
    elo2: number
    live?: boolean
    winner?: 'team1' | 'team2' | 'draw' | null
    /** "before" for a finished match: the ratings going into it */
    label?: 'avg' | 'before'
    compact?: boolean
  }>(),
  { live: false, winner: null, label: 'avg', compact: false },
)
const { t } = useI18n()

const p1 = computed(() => winChance(props.elo1, props.elo2))
const pct1 = computed(() => Math.round(p1.value * 100))
const pct2 = computed(() => 100 - pct1.value)
// keep the knob off the very ends so it never sits on the round caps
const knob = computed(() => Math.min(96, Math.max(4, p1.value * 100)))
const gap = computed(() => Math.abs(p1.value - 0.5))
const how = computed(() => (gap.value < 0.05 ? t('elo.even') : gap.value < 0.12 ? t('elo.close') : t('elo.apart')))
const fmt = (n: number): string => Math.round(n).toLocaleString('en-US')

const root = ref<HTMLElement | null>(null)
const play = ref(false)
let observer: IntersectionObserver | null = null
onMounted(() => {
  if (!root.value || !('IntersectionObserver' in window)) {
    play.value = true
    return
  }
  observer = new IntersectionObserver(
    ([e]) => {
      if (!e?.isIntersecting) return
      play.value = true
      observer?.disconnect()
      observer = null
    },
    { threshold: 0.4 },
  )
  observer.observe(root.value)
})
onBeforeUnmount(() => observer?.disconnect())
</script>

<template>
  <div
    ref="root"
    class="elo-gauge"
    :class="{ play, live, compact, 'won-1': winner === 'team1', 'won-2': winner === 'team2', done: !!winner }"
    role="img"
    :aria-label="t('elo.aria', { a: fmt(elo1), b: fmt(elo2), p: pct1, q: pct2 })"
  >
    <div class="nums" aria-hidden="true">
      <span class="l">{{ fmt(elo1) }}</span>
      <span class="mid">{{ label === 'before' ? t('elo.before') : t('elo.avg') }}</span>
      <span class="r">{{ fmt(elo2) }}</span>
    </div>
    <div class="bar" :style="{ '--p': `${p1 * 100}%`, '--k': `${knob}%` }" aria-hidden="true">
      <span class="fill fill-l" />
      <span class="fill fill-r" />
      <span class="segs" />
      <span class="center" />
      <span class="knob" />
    </div>
    <div v-if="!compact" class="foot" aria-hidden="true">
      <span><b>{{ pct1 }}%</b> {{ t('elo.chance') }}</span>
      <span>{{ how }}</span>
      <span><b>{{ pct2 }}%</b></span>
    </div>
  </div>
</template>

<style scoped>
.elo-gauge {
  --g-pink: #ff4fae;
  --g-pink-2: #ffb3df;
  --g-violet: #8f6bff;
  --g-violet-2: #c9b8ff;
  --g-gold: #ffcf4d;
}
.nums {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.nums .l {
  color: var(--g-pink-2);
}
.nums .r {
  color: var(--g-violet-2);
}
.nums .mid {
  font-family: var(--font-body, inherit);
  font-size: 11px;
  font-weight: 400;
  color: rgb(255 255 255 / 0.55);
}
.bar {
  position: relative;
  height: 12px;
  margin-top: 6px;
  border-radius: 999px;
  background: rgb(255 255 255 / 0.1);
  box-shadow: inset 0 1px 2px rgb(0 0 0 / 0.5);
}
.compact .bar {
  height: 9px;
  margin-top: 4px;
}
.fill {
  position: absolute;
  top: 0;
  bottom: 0;
  overflow: hidden;
}
.fill-l {
  left: 0;
  width: var(--p);
  border-radius: 999px 0 0 999px;
  background: linear-gradient(90deg, #c22f86, var(--g-pink));
}
.fill-r {
  right: 0;
  width: calc(100% - var(--p));
  border-radius: 0 999px 999px 0;
  background: linear-gradient(90deg, var(--g-violet), #5a3ccc);
}
.segs {
  position: absolute;
  inset: 0;
  border-radius: 999px;
  background: repeating-linear-gradient(90deg, transparent 0 calc(12.5% - 2px), rgb(13 6 25 / 0.85) calc(12.5% - 2px) 12.5%);
  pointer-events: none;
}
.center {
  position: absolute;
  top: -4px;
  bottom: -4px;
  left: 50%;
  width: 2px;
  margin-left: -1px;
  border-radius: 2px;
  background: rgb(255 255 255 / 0.55);
}
.knob {
  position: absolute;
  top: 50%;
  left: var(--k);
  width: 20px;
  height: 20px;
  margin: -10px 0 0 -10px;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 30%, #fff, #ffd9ef 45%, var(--g-pink) 100%);
  box-shadow:
    0 0 0 3px rgb(13 6 25 / 0.9),
    0 0 16px rgb(255 255 255 / 0.6);
}
.compact .knob {
  width: 16px;
  height: 16px;
  margin: -8px 0 0 -8px;
}
.foot {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
  font-size: 12px;
  color: rgb(255 255 255 / 0.6);
  font-variant-numeric: tabular-nums;
}
.foot b {
  font-weight: 600;
  color: #fff;
}
/* finished: the losing side dims, the winner's lights gold */
.done .fill {
  filter: saturate(0.55) brightness(0.75);
}
.won-1 .fill-l,
.won-2 .fill-r {
  filter: none;
  box-shadow: 0 0 14px rgb(255 207 77 / 0.55);
}
.done .knob {
  background: radial-gradient(circle at 35% 30%, #fff, #fff3c4 45%, var(--g-gold) 100%);
}

/* motion, the first time it is seen */
.play .fill-l {
  animation: g-grow-l 0.9s cubic-bezier(0.2, 0.8, 0.2, 1) both;
}
.play .fill-r {
  animation: g-grow-r 0.9s cubic-bezier(0.2, 0.8, 0.2, 1) both;
}
.play .knob {
  animation: g-knob 0.9s cubic-bezier(0.3, 1.4, 0.5, 1) both;
}
.play.live .knob {
  animation:
    g-knob 0.9s cubic-bezier(0.3, 1.4, 0.5, 1) both,
    g-breathe 2.2s ease-in-out 1s infinite;
}
.live .fill::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, rgb(255 255 255 / 0.45), transparent) no-repeat;
  background-size: 40% 100%;
  animation: g-run 2.4s linear infinite;
}
.live .fill-r::after {
  animation-direction: reverse;
}
@keyframes g-grow-l {
  from {
    width: 50%;
  }
}
@keyframes g-grow-r {
  from {
    width: 50%;
  }
}
@keyframes g-knob {
  from {
    left: 50%;
    transform: scale(0.4);
  }
}
@keyframes g-breathe {
  50% {
    box-shadow:
      0 0 0 3px rgb(13 6 25 / 0.9),
      0 0 26px rgb(255 255 255 / 0.95);
  }
}
@keyframes g-run {
  from {
    background-position: -60% 0;
  }
  to {
    background-position: 160% 0;
  }
}
@media (prefers-reduced-motion: reduce) {
  .play .fill-l,
  .play .fill-r,
  .play .knob,
  .play.live .knob,
  .live .fill::after {
    animation: none;
  }
}
</style>
