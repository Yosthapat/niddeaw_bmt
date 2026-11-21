<script setup lang="ts">
/**
 * A string of neon Christmas lights: hung from the foot of the phone's
 * header bar, and across the top of the screen above the floating glass
 * bar from 900px wide. The bulbs twinkle slowly, out of step; with reduced
 * motion they just stay lit.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps<{ belowHeader: boolean }>()

const GAP = 30
const COLORS = ['#ff4d8d', '#ffe14d', '#5ce88a', '#4dd2ff', '#c96dff']
const width = ref(window.innerWidth)
const onResize = (): void => {
  width.value = window.innerWidth
}
onMounted(() => window.addEventListener('resize', onResize))
onBeforeUnmount(() => window.removeEventListener('resize', onResize))

const bulbs = computed(() =>
  Array.from({ length: Math.ceil(width.value / GAP) }, (_, i) => ({
    color: COLORS[i % COLORS.length]!,
    // a scattered, repeatable rhythm rather than a wave running along
    delay: `${((i * 7) % 11) * -0.37}s`,
  })),
)
</script>

<template>
  <div class="xmas-lights" :class="{ 'below-header': props.belowHeader }" aria-hidden="true">
    <span v-for="(b, i) in bulbs" :key="i" class="bulb" :style="{ '--c': b.color, '--d': b.delay }" />
  </div>
</template>

<style scoped>
.xmas-lights {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 21;
  height: 26px;
  display: flex;
  overflow: hidden;
  pointer-events: none;
  /* the wire: one dip between every two bulbs */
  background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='30' height='26'%3E%3Cpath d='M0 3Q15 15 30 3' fill='none' stroke='%23463146' stroke-width='1.6'/%3E%3C/svg%3E") repeat-x 0 0;
}
.below-header {
  top: calc(var(--header-h) - 4px);
}
.bulb {
  flex: 0 0 30px;
  position: relative;
}
.bulb::before {
  /* the cap */
  content: '';
  position: absolute;
  left: 12px;
  top: 7px;
  width: 6px;
  height: 4px;
  border-radius: 1px;
  background: #5b4a5b;
}
.bulb::after {
  content: '';
  position: absolute;
  left: 10.5px;
  top: 10px;
  width: 9px;
  height: 12px;
  border-radius: 50% 50% 50% 50% / 42% 42% 58% 58%;
  background: radial-gradient(circle at 40% 35%, #fff 0 18%, var(--c) 45%);
  box-shadow:
    0 0 8px var(--c),
    0 0 18px var(--c);
  animation: bulb-twinkle 3.2s ease-in-out var(--d) infinite;
}
@keyframes bulb-twinkle {
  0%,
  100% {
    opacity: 1;
  }
  45% {
    opacity: 0.35;
  }
  55% {
    opacity: 0.35;
  }
}
@media (prefers-reduced-motion: reduce) {
  .bulb::after {
    animation: none;
  }
}
</style>
