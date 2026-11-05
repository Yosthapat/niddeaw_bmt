<script setup lang="ts">
/**
 * The LINE mark on the corner of a member's face when their LINE is
 * linked: they can check in, check out and pay from LINE themselves.
 * Wraps the avatar; with no LINE it is just the avatar.
 */
import LineMark from '@/components/players/LineMark.vue'

withDefaults(defineProps<{ linked: boolean; size?: 'sm' | 'md' }>(), { size: 'sm' })
</script>

<template>
  <span class="relative inline-flex shrink-0">
    <slot />
    <LineMark v-if="linked" :size="size" class="absolute -right-1.5 -bottom-1.5 ring-2 ring-[#1a0d30]" />
  </span>
</template>
