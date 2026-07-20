<script setup lang="ts">
withDefaults(defineProps<{ name: string; avatarUrl?: string | null; size?: 'sm' | 'md' | 'lg' }>(), {
  size: 'md',
})

function initials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
}
</script>

<template>
  <img
    v-if="avatarUrl"
    :src="avatarUrl"
    :alt="name"
    class="hud-panel shrink-0 border border-brand-pink/40 object-cover"
    :class="{ 'h-8 w-8': size === 'sm', 'h-11 w-11': size === 'md', 'h-16 w-16': size === 'lg' }"
  />
  <span
    v-else
    class="hud-panel flex shrink-0 items-center justify-center border border-brand-pink/40 bg-brand-surface-raised font-display font-semibold text-brand-pink-light"
    :class="{
      'h-8 w-8 text-xs': size === 'sm',
      'h-11 w-11 text-sm': size === 'md',
      'h-16 w-16 text-lg': size === 'lg',
    }"
  >
    {{ initials(name) }}
  </span>
</template>
