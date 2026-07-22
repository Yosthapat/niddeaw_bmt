<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getPlayers } from '@/api/public'
import type { PlayerStats } from '@/types'
import EloBadge from '@/components/players/EloBadge.vue'
import TierMascot from '@/components/players/TierMascot.vue'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'

const PAGE_SIZE = 20

const { t } = useI18n()

const stats = ref<PlayerStats[]>([])
const loading = ref(true)
const loadingMore = ref(false)
const error = ref<string | null>(null)
const hasMore = ref(true)
const search = ref('')
const loadedAll = ref(false)

// Sorted by points server-side now (cheap — denormalized stats, no
// match-history scan), so the roster arrives in ranked order already.
const filteredStats = computed(() => {
  const query = search.value.trim().toLowerCase()
  if (!query) return stats.value
  return stats.value.filter((s) => s.player.nickname.toLowerCase().includes(query))
})

async function loadMore(): Promise<void> {
  loadingMore.value = true
  try {
    const next = await getPlayers({ limit: PAGE_SIZE, offset: stats.value.length })
    stats.value = [...stats.value, ...next]
    hasMore.value = next.length === PAGE_SIZE
  } catch {
    error.value = t('members.loadMoreError')
  } finally {
    loadingMore.value = false
  }
}

// Search has to look across the whole roster, not just what's paged in
// so far — fetch everyone once, the first time the box is actually used.
watch(search, async (value) => {
  if (!value.trim() || loadedAll.value) return
  loadedAll.value = true
  try {
    stats.value = await getPlayers()
    hasMore.value = false
  } catch {
    error.value = t('members.loadError')
  }
})

onMounted(async () => {
  try {
    const first = await getPlayers({ limit: PAGE_SIZE })
    stats.value = first
    hasMore.value = first.length === PAGE_SIZE
  } catch {
    error.value = t('members.loadError')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <main class="mx-auto max-w-4xl px-4 py-8 sm:py-12">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <p class="text-xs font-semibold tracking-widest text-brand-pink/70 uppercase">Roster</p>
        <h1 class="font-display text-3xl font-bold text-white">{{ t('nav.members') }}</h1>
      </div>
      <input
        v-model="search"
        type="search"
        :placeholder="t('members.searchPlaceholder')"
        class="hud-panel w-full max-w-xs border border-brand-pink/25 bg-brand-surface px-4 py-2 text-sm outline-none focus:border-brand-pink"
      />
    </div>

    <p v-if="loading" class="mt-6 text-white/60">{{ t('common.loading') }}</p>
    <p v-else-if="error" class="mt-6 text-status-error">{{ error }}</p>
    <p v-else-if="stats.length === 0" class="mt-6 text-white/60">{{ t('members.empty') }}</p>
    <p v-else-if="filteredStats.length === 0" class="mt-6 text-white/60">{{ t('members.noSearchResults') }}</p>

    <div v-else class="hud-panel mt-6 overflow-x-auto border border-brand-pink/20 bg-brand-surface">
      <table class="w-full min-w-[680px] text-left text-sm">
        <thead class="border-b border-brand-pink/20 text-xs font-semibold tracking-wider text-white/40 uppercase">
          <tr>
            <th class="px-4 py-3">{{ t('common.player') }}</th>
            <th class="px-4 py-3">Level</th>
            <th class="px-4 py-3 text-right">{{ t('common.game') }}</th>
            <th class="px-4 py-3 text-right">{{ t('common.win') }}</th>
            <th class="px-4 py-3 text-right">{{ t('common.draw') }}</th>
            <th class="px-4 py-3 text-right">{{ t('common.loss') }}</th>
            <th class="px-4 py-3 text-right">Pts</th>
            <th class="px-4 py-3 text-right">{{ t('common.avg') }}</th>
            <th class="px-4 py-3 text-right">{{ t('common.scorePercent') }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-white/5">
          <tr v-for="s in filteredStats" :key="s.player.id" class="transition-colors hover:bg-brand-surface-raised">
            <td class="px-4 py-3 font-medium">
              <RouterLink :to="`/members/${s.player.id}`" class="flex items-center gap-2.5 hover:text-brand-pink">
                <PlayerAvatar :name="s.player.nickname" :avatar-url="s.player.avatar_url" size="sm" />
                {{ s.player.nickname }}
              </RouterLink>
            </td>
            <td class="px-4 py-3">
              <div class="flex items-center gap-1.5">
                <TierMascot :tier="s.player.elo_level" :size="22" />
                <EloBadge :elo-score="s.player.elo_score" />
              </div>
            </td>
            <td class="px-4 py-3 text-right text-white/70">{{ s.games }}</td>
            <td class="px-4 py-3 text-right text-white/70">{{ s.wins }}</td>
            <td class="px-4 py-3 text-right text-white/70">{{ s.draws }}</td>
            <td class="px-4 py-3 text-right text-white/70">{{ s.losses }}</td>
            <td class="px-4 py-3 text-right font-display font-semibold text-brand-pink">{{ s.points }}</td>
            <td class="px-4 py-3 text-right text-white/70">{{ s.avg_points.toFixed(2) }}</td>
            <td class="px-4 py-3 text-right text-white/70">{{ s.score_percent.toFixed(1) }}%</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="!loading && hasMore && !search.trim()" class="mt-6 text-center">
      <button
        :disabled="loadingMore"
        class="rounded-full border border-brand-pink/40 px-5 py-2 text-sm font-semibold text-brand-pink hover:bg-brand-pink hover:text-brand-black disabled:opacity-50"
        @click="loadMore"
      >
        {{ loadingMore ? t('common.loading') : t('matches.loadMore') }}
      </button>
    </div>
  </main>
</template>
