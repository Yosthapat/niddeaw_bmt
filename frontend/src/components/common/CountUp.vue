<script setup lang="ts">
// Animates a number tweening up (or down) to `value` instead of just
// popping into place — used for the flashier stat columns (Pts, Win) on
// the ranking page. Renders as plain text so callers can style it exactly
// like the static number it replaces.
import { onMounted, ref, watch } from 'vue'

const props = withDefaults(defineProps<{ value: number; duration?: number }>(), { duration: 700 })

const display = ref(0)
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

function animateTo(target: number, from: number): void {
  if (reduceMotion) {
    display.value = target
    return
  }
  const start = performance.now()
  function tick(now: number): void {
    const t = Math.min((now - start) / props.duration, 1)
    const eased = 1 - Math.pow(1 - t, 3)
    display.value = Math.round(from + (target - from) * eased)
    if (t < 1) requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
}

onMounted(() => animateTo(props.value, 0))
watch(
  () => props.value,
  (next, prev) => animateTo(next, prev ?? 0),
)
</script>

<template><span>{{ display }}</span></template>
