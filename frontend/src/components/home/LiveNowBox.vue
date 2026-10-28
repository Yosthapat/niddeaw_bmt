<script setup lang="ts">
// What is on court right now, under the home cards — only while a match
// is actually being played, so it never sits there saying "nothing".
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { getPlayersByIds } from '@/api/public'
import { useLiveNow } from '@/composables/useLiveNow'

const { t } = useI18n()
const { live } = useLiveNow()
const names = ref<Record<string, string>>({})

const match = computed(() => live.value?.in_progress[0] ?? null)
const more = computed(() => Math.max(0, (live.value?.in_progress.length ?? 0) - 1))

// Names for whoever is on court; fetched again only when that changes.
watch(
  match,
  async (m) => {
    if (!m) return
    const ids = [...m.team1_player_ids, ...m.team2_player_ids].filter((id) => !names.value[id])
    if (!ids.length) return
    try {
      const players = await getPlayersByIds(ids)
      names.value = { ...names.value, ...Object.fromEntries(players.map((p) => [p.id, p.nickname])) }
    } catch {
      // the box still says a match is on; names fill in on the next poll
    }
  },
  { immediate: true },
)

const team = (ids: string[]): string => ids.map((id) => names.value[id] ?? '…').join(' & ')
const where = computed(() => {
  const m = match.value
  if (!m) return ''
  return [m.court ? t('home.live.court', { court: m.court }) : null, m.match_no ? `#${m.match_no}` : null]
    .filter(Boolean)
    .join(' · ')
})
</script>

<template>
  <RouterLink
    v-if="match"
    to="/live"
    class="flex flex-col gap-2.5 rounded-[18px] border border-white/12 bg-white/5 p-3 hover:bg-white/8 sm:p-4"
  >
    <div class="flex items-center justify-between gap-2">
      <span class="flex items-center gap-1.5 text-[13px] font-medium">
        <span class="live-blink h-2 w-2 rounded-full bg-[#ff4d6d]" aria-hidden="true" />
        {{ t('home.live.title') }}
      </span>
      <span class="text-xs text-white/60">
        {{ where }}<template v-if="more"> · {{ t('home.live.more', { n: more }) }}</template>
      </span>
    </div>
    <div class="flex items-center justify-between gap-2">
      <span class="min-w-0 flex-1 truncate text-center text-sm">{{ team(match.team1_player_ids) }}</span>
      <span class="rounded-md bg-brand-pink/20 px-2 py-1 font-display text-xs leading-none font-bold text-[#ff9fd6]">VS</span>
      <span class="min-w-0 flex-1 truncate text-center text-sm">{{ team(match.team2_player_ids) }}</span>
    </div>
  </RouterLink>
</template>

<style scoped>
.live-blink {
  animation: live-blink 1.4s ease-in-out infinite;
}
@keyframes live-blink {
  50% {
    opacity: 0.35;
  }
}
@media (prefers-reduced-motion: reduce) {
  .live-blink {
    animation: none;
  }
}
</style>
