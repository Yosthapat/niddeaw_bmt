<script setup lang="ts">
import { computed } from 'vue'
import { useEloTier } from '@/composables/useEloTier'

const props = defineProps<{ eloScore: number; showScore?: boolean }>()
const tierInfo = computed(() => useEloTier(props.eloScore))
</script>

<template>
  <span
    class="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-semibold"
    :style="{ color: tierInfo.colorVar, borderColor: tierInfo.colorVar }"
  >
    {{ tierInfo.label }}
    <span v-if="showScore" class="opacity-70">({{ eloScore }})</span>
  </span>
</template>
