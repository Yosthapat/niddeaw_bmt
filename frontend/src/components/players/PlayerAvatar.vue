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
    class="shrink-0 rounded-full object-cover ring-1 ring-brand-pink-dark/50"
    :class="{ 'h-8 w-8': size === 'sm', 'h-11 w-11': size === 'md', 'h-16 w-16': size === 'lg' }"
  />
  <span
    v-else
    class="flex shrink-0 items-center justify-center rounded-full bg-brand-pink-dark/40 font-semibold text-brand-pink-light ring-1 ring-brand-pink-dark/50"
    :class="{
      'h-8 w-8 text-xs': size === 'sm',
      'h-11 w-11 text-sm': size === 'md',
      'h-16 w-16 text-lg': size === 'lg',
    }"
  >
    {{ initials(name) }}
  </span>
</template>
