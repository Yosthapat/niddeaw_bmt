<script setup lang="ts">
// `round`: a circle instead of the HUD notch, for the home page, which
// takes the hero's rounded glass rather than the scoreboard look.
withDefaults(defineProps<{ name: string; avatarUrl?: string | null; size?: 'sm' | 'md' | 'lg' | 'xl'; round?: boolean }>(), {
  size: 'md',
  round: false,
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
  <!-- lg steps down a size on phones: two doubles teams of 64px faces plus
       the score between them were 30px wider than a 375px screen. -->
  <img
    v-if="avatarUrl"
    :src="avatarUrl"
    :alt="name"
    loading="lazy"
    decoding="async"
    class="shrink-0 border border-brand-pink/40 object-cover"
    :class="{
      'hud-panel': !round,
      'rounded-full ring-2 ring-white/25': round,
      'h-8 w-8': size === 'sm',
      'h-11 w-11': size === 'md',
      'h-12 w-12 sm:h-16 sm:w-16': size === 'lg',
      'h-44 w-44 sm:h-60 sm:w-60': size === 'xl',
    }"
  />
  <span
    v-else
    class="flex shrink-0 items-center justify-center border border-brand-pink/40 bg-brand-surface-raised font-display font-semibold text-brand-pink-light"
    :class="{
      'hud-panel': !round,
      'rounded-full ring-2 ring-white/25': round,
      'h-8 w-8 text-xs': size === 'sm',
      'h-11 w-11 text-sm': size === 'md',
      'h-12 w-12 text-base sm:h-16 sm:w-16 sm:text-lg': size === 'lg',
      'h-44 w-44 text-6xl sm:h-60 sm:w-60': size === 'xl',
    }"
  >
    {{ initials(name) }}
  </span>
</template>
