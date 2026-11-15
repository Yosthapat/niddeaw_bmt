<script setup lang="ts">
/**
 * One team on a tournament page: the two players' avatars, the team's name
 * and their nicknames. Before a knockout match's team is known, an empty
 * circle and where it comes from ("Upper #1", "Winner #23") instead.
 */
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'
import type { PublicPlayer } from '@/api/tournament'

defineProps<{
  name: string | null
  players?: PublicPlayer[]
  /** shown when there is no team yet */
  placeholder?: string
  prefix?: string
  mine?: boolean
}>()
</script>

<template>
  <div class="flex min-w-0 items-center gap-2.5">
    <span v-if="prefix" class="w-6 shrink-0 font-display text-xs text-white/45">{{ prefix }}</span>
    <div v-if="name && players?.length" class="flex shrink-0 -space-x-2.5">
      <PlayerAvatar v-for="p in players" :key="p.nickname" :name="p.nickname" :avatar-url="p.avatar_url" size="sm" round class="ring-2 ring-[#1a0838]" />
    </div>
    <span v-else class="flex h-8 w-[52px] shrink-0 items-center justify-center rounded-full border border-dashed border-white/25 text-xs text-white/40" aria-hidden="true">?</span>
    <span class="min-w-0">
      <span class="block truncate text-sm font-semibold" :class="[name ? '' : 'font-normal text-white/55', mine ? 'text-[#ff6cc0]' : '']">{{ name ?? placeholder }}</span>
      <span v-if="name && players?.length" class="block truncate text-xs text-white/60">{{ players.map((p) => p.nickname).join(' · ') }}</span>
    </span>
  </div>
</template>
