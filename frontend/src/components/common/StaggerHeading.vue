<script setup lang="ts">
// Splits a heading into words, each fading/blurring up into place with an
// incremental delay, instead of the whole title popping in at once. Used
// on major public-page <h1>s. Renders as plain text under
// prefers-reduced-motion (checked once at setup, matching the pattern
// CountUp.vue and useScrollReveal.ts already use elsewhere).
import { computed } from 'vue'

const props = defineProps<{ text: string }>()

const words = computed(() => props.text.split(' '))
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
</script>

<template>
  <span v-if="reduceMotion">{{ text }}</span>
  <span v-else>
    <span
      v-for="(word, i) in words"
      :key="i"
      class="stagger-word"
      :style="{ '--stagger-delay': `${i * 70}ms` }"
      >{{ word }}<template v-if="i < words.length - 1">&nbsp;</template></span
    >
  </span>
</template>
