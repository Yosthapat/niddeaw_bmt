<script setup lang="ts">
/**
 * The pink or black credit card, full size: what LINE's credit screen shows
 * at the top and what the celebration lifts up. The club's crowned cat
 * leans in from the right, light crosses the face now and then, and an
 * aura of the card's colours travels round its edge (still, with reduced
 * motion).
 */
import { computed } from 'vue'
import type { CardTier } from '@/api/line'

const props = withDefaults(defineProps<{ tier: CardTier; name: string; width?: number }>(), { width: 300 })
const style = computed(() => ({ '--w': `${props.width}px` }))
</script>

<template>
  <div class="cc" :class="tier" :style="style" role="img" :aria-label="tier === 'black' ? 'NIDDEAW BLACK' : 'NIDDEAW CREDIT'">
    <div class="face">
      <img class="cat" src="/credit/cat.webp" alt="" width="384" height="384" />
      <div class="row1">
        <span class="brand">NIDDEAW<small>{{ tier === 'black' ? 'BLACK' : 'CREDIT' }}</small></span>
        <span class="chip" />
      </div>
      <div class="row2">
        <span class="num">•••• {{ tier === 'black' ? '5000' : '1000' }}</span>
        <span class="who">{{ name }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cc {
  position: relative;
  width: var(--w);
  max-width: 100%;
  aspect-ratio: 1.586;
  border-radius: calc(var(--w) * 0.055);
  isolation: isolate;
}
.cc::before,
.cc::after {
  content: '';
  position: absolute;
  inset: calc(var(--w) * -0.04);
  z-index: -1;
  border-radius: calc(var(--w) * 0.09);
  filter: blur(calc(var(--w) * 0.06));
  animation: aura 6s linear infinite;
}
.cc::after {
  inset: calc(var(--w) * -0.01);
  filter: blur(calc(var(--w) * 0.02));
  opacity: 0.7;
  animation: breathe 3.2s ease-in-out infinite;
}
.pink::before {
  background: conic-gradient(from var(--a), #ff5fae, #ffb3d9, #ff2d95, #ff8fd0, #ff5fae);
}
.pink::after {
  background: radial-gradient(closest-side, #ff8fd0, transparent);
}
.black::before {
  background: conic-gradient(from var(--a), #9b6bff, #f2c14e, #ff5fae, #5a2bd6, #9b6bff);
}
.black::after {
  background: radial-gradient(closest-side, #7a4dff, transparent);
}
.face {
  position: absolute;
  inset: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  border-radius: inherit;
  padding: calc(var(--w) * 0.06);
  box-shadow:
    0 calc(var(--w) * 0.04) calc(var(--w) * 0.08) rgb(0 0 0 / 0.55),
    inset 0 0 0 1px rgb(255 255 255 / 0.18);
}
.pink .face {
  background:
    radial-gradient(120% 90% at 0% 0%, #ffd0e8 0%, transparent 45%),
    linear-gradient(135deg, #ff8fd0 0%, #ff4fa6 45%, #b81f74 100%);
  color: #2a0618;
}
.black .face {
  background:
    radial-gradient(90% 70% at 100% 0%, rgb(155 107 255 / 0.35), transparent 60%),
    repeating-linear-gradient(115deg, rgb(255 255 255 / 0.025) 0 2px, transparent 2px 5px),
    linear-gradient(140deg, #26222c 0%, #0b0a0e 55%, #000 100%);
  color: #f4eef8;
}
.face::after {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: linear-gradient(105deg, transparent 38%, rgb(255 255 255 / 0.45) 50%, transparent 62%);
  background-size: 260% 100%;
  background-position: 160% 0;
  mix-blend-mode: soft-light;
  animation: sweep 5s ease-in-out infinite;
}
.black .face::after {
  background: linear-gradient(105deg, transparent 38%, rgb(242 193 78 / 0.5) 50%, transparent 62%);
  background-size: 260% 100%;
  mix-blend-mode: screen;
  opacity: 0.6;
}
.cat {
  position: absolute;
  right: -6%;
  bottom: -14%;
  width: 62%;
  height: auto;
  filter: drop-shadow(0 4px 10px rgb(0 0 0 / 0.35));
}
.black .cat {
  filter: drop-shadow(0 0 calc(var(--w) * 0.04) rgb(155 107 255 / 0.7));
}
.row1 {
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}
.brand {
  font-family: var(--font-display);
  font-size: calc(var(--w) * 0.05);
  font-weight: 700;
  line-height: 1;
  letter-spacing: 0.06em;
}
.brand small {
  display: block;
  margin-top: 4px;
  font-size: calc(var(--w) * 0.032);
  font-weight: 600;
  letter-spacing: 0.24em;
  opacity: 0.75;
}
.black .brand small {
  color: #f2c14e;
  opacity: 1;
}
.chip {
  position: relative;
  width: calc(var(--w) * 0.13);
  aspect-ratio: 1.3;
  border-radius: calc(var(--w) * 0.018);
  background: linear-gradient(135deg, #f7dc8a, #c9952f 55%, #f2d27a);
  box-shadow: inset 0 0 0 1px rgb(0 0 0 / 0.25);
}
.chip::before {
  content: '';
  position: absolute;
  inset: 22% 18%;
  border: 1px solid rgb(90 60 10 / 0.45);
  border-radius: 3px;
}
.row2 {
  position: relative;
  display: flex;
  max-width: 60%;
  flex-direction: column;
  gap: 2px;
}
.num {
  font-family: var(--font-display);
  font-size: calc(var(--w) * 0.052);
  font-weight: 600;
  letter-spacing: 0.14em;
}
.who {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--font-display);
  font-size: calc(var(--w) * 0.036);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  opacity: 0.8;
}
@property --a {
  syntax: '<angle>';
  inherits: false;
  initial-value: 0deg;
}
@keyframes aura {
  to {
    --a: 360deg;
  }
}
@keyframes breathe {
  50% {
    opacity: 0.25;
    transform: scale(1.03);
  }
}
@keyframes sweep {
  0%,
  65% {
    background-position: 160% 0;
  }
  100% {
    background-position: -60% 0;
  }
}
@media (prefers-reduced-motion: reduce) {
  .cc::before,
  .cc::after,
  .face::after {
    animation: none;
  }
}
</style>
