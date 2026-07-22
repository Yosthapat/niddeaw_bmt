<script setup lang="ts">
import type { EloTier } from '@/types'

withDefaults(defineProps<{ tier: EloTier; size?: number }>(), {
  size: 64,
})

const labels: Record<EloTier, string> = {
  milk: 'Milk tier mascot',
  beer: 'Beer tier mascot',
  highball: 'Highball tier mascot',
  wine: 'Wine tier mascot',
  soju: 'Soju tier mascot',
  whisky: 'Whisky tier mascot',
  vodka: 'Vodka tier mascot',
}
</script>

<template>
  <img
    :src="`/tiers/${tier}.webp`"
    :alt="labels[tier]"
    :width="size"
    :height="size"
    class="inline-block shrink-0 object-contain"
    :style="{ width: `${size}px`, height: `${size}px` }"
  />
</template>
