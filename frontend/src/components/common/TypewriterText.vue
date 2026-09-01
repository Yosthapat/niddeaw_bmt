<script setup lang="ts">
// Reveals `text` one character at a time instead of popping in all at once.
// Plain JS-driven reveal (not the CSS steps()+width trick) because the text
// wraps across multiple lines — a width animation only works for a single
// line. Restart by changing the component's :key (e.g. to the tier name),
// which remounts it and re-triggers onMounted.
import { onMounted, onUnmounted, ref } from 'vue'

const props = withDefaults(defineProps<{ text: string; charsPerSecond?: number }>(), {
  charsPerSecond: 45,
})

const shown = ref('')
let timer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    shown.value = props.text
    return
  }
  let i = 0
  timer = setInterval(() => {
    i++
    shown.value = props.text.slice(0, i)
    if (i >= props.text.length && timer) {
      clearInterval(timer)
      timer = null
    }
  }, 1000 / props.charsPerSecond)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<template><span>{{ shown }}</span></template>
