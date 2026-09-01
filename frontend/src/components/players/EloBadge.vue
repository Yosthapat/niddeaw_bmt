<script setup lang="ts">
import { computed } from 'vue'
import { useEloTier, tierTextStyle, tierSwatchStyle } from '@/composables/useEloTier'

const props = defineProps<{ eloScore: number; showScore?: boolean }>()
const tierInfo = computed(() => useEloTier(props.eloScore))
</script>

<template>
  <span class="inline-flex items-center gap-1.5 text-xs font-semibold tracking-wide uppercase">
    <span
      class="h-2 w-2 rotate-45"
      :class="{ 'tier-shimmer': tierInfo.gradient }"
      :style="tierSwatchStyle(tierInfo.colorVar, tierInfo.gradient)"
    />
    <span :class="{ 'tier-shimmer': tierInfo.gradient }" :style="tierTextStyle(tierInfo.colorVar, tierInfo.gradient)">{{
      tierInfo.label
    }}</span>
    <span v-if="showScore" class="font-normal text-white/40 normal-case">{{ eloScore }}</span>
  </span>
</template>
