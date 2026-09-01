<script setup lang="ts">
import type { EloTier } from '@/types'
import { useTierInfoModal } from '@/composables/useTierInfoModal'

const props = withDefaults(defineProps<{ tier: EloTier; size?: number; interactive?: boolean }>(), {
  size: 64,
  interactive: true,
})

const { open } = useTierInfoModal()

const labels: Record<EloTier, string> = {
  milk: 'Milk tier mascot',
  beer: 'Beer tier mascot',
  highball: 'Highball tier mascot',
  wine: 'Wine tier mascot',
  soju: 'Soju tier mascot',
  whisky: 'Whisky tier mascot',
  vodka: 'Vodka tier mascot',
  absinthe: 'Absinthe tier mascot',
}
</script>

<template>
  <button
    v-if="interactive"
    type="button"
    class="hud-hover inline-block shrink-0 rounded-full transition-transform active:scale-95"
    :aria-label="labels[tier]"
    @click="open(props.tier)"
  >
    <img
      :src="`/tiers/${tier}.webp`"
      :alt="labels[tier]"
      :width="size"
      :height="size"
      class="pointer-events-none block object-contain"
      :style="{ width: `${size}px`, height: `${size}px` }"
    />
  </button>
  <img
    v-else
    :src="`/tiers/${tier}.webp`"
    :alt="labels[tier]"
    :width="size"
    :height="size"
    class="inline-block shrink-0 object-contain"
    :style="{ width: `${size}px`, height: `${size}px` }"
  />
</template>
