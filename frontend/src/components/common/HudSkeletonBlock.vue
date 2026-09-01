<script setup lang="ts">
// One shimmering placeholder panel, styled to match .hud-panel cards so
// loading states read as "the UI is about to appear here" instead of a
// plain "กำลังโหลด..." string. Callers stack/grid these with v-for and
// size them via the `class` passthrough (e.g. class="h-12").
withDefaults(defineProps<{ delay?: number }>(), { delay: 0 })
</script>

<template>
  <div
    class="hud-panel skeleton-shimmer border border-brand-pink/10 bg-brand-surface"
    :style="{ animationDelay: `${delay}ms` }"
    aria-hidden="true"
  />
</template>
