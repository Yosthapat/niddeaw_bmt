<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getPlayers } from '@/api/public'
import type { EloTier, PlayerStats } from '@/types'
import { tierMeta } from '@/composables/useEloTier'
import { TIER_ORDER } from '@/utils/tierCard'
import MemberCard from '@/components/players/MemberCard.vue'
import HudSkeletonBlock from '@/components/common/HudSkeletonBlock.vue'
import StaggerHeading from '@/components/common/StaggerHeading.vue'

type Sort = 'elo' | 'name' | 'games'

const { t } = useI18n()

const stats = ref<PlayerStats[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const search = ref('')
const tier = ref<EloTier | 'all'>('all')
const sort = ref<Sort>('elo')

// The whole roster at once: a tier filter or a sort over the first page
// only would be quietly wrong, and it is about a hundred small rows.
onMounted(async () => {
  try {
    stats.value = await getPlayers()
  } catch {
    error.value = t('members.loadError')
  } finally {
    loading.value = false
  }
})

const counts = computed(() => {
  const by: Partial<Record<EloTier, number>> = {}
  for (const s of stats.value) by[s.player.elo_level] = (by[s.player.elo_level] ?? 0) + 1
  return by
})

const shown = computed(() => {
  const query = search.value.trim().toLowerCase()
  const list = stats.value.filter(
    (s) =>
      (tier.value === 'all' || s.player.elo_level === tier.value) &&
      (!query ||
        s.player.nickname.toLowerCase().includes(query) ||
        s.player.member_code.toLowerCase().includes(query)),
  )
  const by: Record<Sort, (a: PlayerStats, b: PlayerStats) => number> = {
    elo: (a, b) => b.player.elo_score - a.player.elo_score,
    name: (a, b) => a.player.nickname.localeCompare(b.player.nickname),
    games: (a, b) => b.games - a.games || b.player.elo_score - a.player.elo_score,
  }
  return [...list].sort(by[sort.value])
})

const emptyMascot = computed(() => (tier.value === 'all' ? 'milk' : tier.value))
</script>

<template>
  <main class="mx-auto max-w-6xl px-4 py-8 sm:py-12">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <p class="text-xs font-semibold tracking-widest text-brand-pink/70 uppercase">
          Roster<template v-if="!loading && !error"> · {{ t('roster.count', { n: stats.length }) }}</template>
        </p>
        <h1 class="font-display text-3xl font-bold text-white sm:text-5xl"><StaggerHeading :text="t('nav.members')" /></h1>
      </div>
      <div class="flex w-full gap-2 sm:w-auto">
        <input
          v-model="search"
          type="search"
          :placeholder="t('roster.searchPlaceholder')"
          :aria-label="t('roster.searchPlaceholder')"
          class="min-h-11 min-w-0 flex-1 rounded-full border border-white/20 bg-white/[0.07] px-4 text-sm outline-none focus:border-brand-pink sm:w-72"
        />
        <select
          v-model="sort"
          :aria-label="t('roster.sortLabel')"
          class="min-h-11 shrink-0 rounded-full border border-white/20 bg-[#140a2b] px-3 text-sm text-white"
        >
          <option value="elo">{{ t('roster.sortElo') }}</option>
          <option value="games">{{ t('roster.sortGames') }}</option>
          <option value="name">{{ t('roster.sortName') }}</option>
        </select>
      </div>
    </div>

    <!-- tier filter: scrolls sideways on a phone rather than wrapping into
         three rows above the cards -->
    <div
      role="group"
      :aria-label="t('roster.filterLabel')"
      class="tier-chips mt-5 -mx-4 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:flex-wrap sm:px-0"
    >
      <button type="button" class="tier-chip" :aria-pressed="tier === 'all'" @click="tier = 'all'">
        {{ t('roster.all') }}
      </button>
      <button
        v-for="id in TIER_ORDER"
        :key="id"
        type="button"
        class="tier-chip"
        :aria-pressed="tier === id"
        @click="tier = id"
      >
        <img :src="`/tiers/${id}.webp`" alt="" width="24" height="24" class="h-6 w-6" />
        {{ tierMeta(id).label }}
        <span class="text-xs text-white/45">{{ counts[id] ?? 0 }}</span>
      </button>
    </div>

    <div v-if="loading" class="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 lg:gap-6">
      <HudSkeletonBlock v-for="i in 10" :key="i" :delay="i * 60" class="aspect-[3/4.4]" />
    </div>
    <p v-else-if="error" class="mt-6 text-status-error">{{ error }}</p>
    <p v-else-if="stats.length === 0" class="mt-6 text-white/60">{{ t('members.empty') }}</p>

    <div v-else-if="shown.length === 0" class="mt-12 flex flex-col items-center gap-3 text-center text-white/70">
      <img :src="`/tiers/${emptyMascot}.webp`" alt="" width="96" height="96" class="h-24 w-24 opacity-80" />
      <p>{{ search.trim() ? t('members.noSearchResults') : t('roster.emptyTier') }}</p>
    </div>

    <ul v-else class="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 lg:gap-6">
      <li v-for="s in shown" :key="s.player.id">
        <RouterLink
          :to="`/members/${s.player.id}`"
          class="block h-full rounded-[18px] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-pink"
        >
          <MemberCard :player="s.player" :games="s.games" :wins="s.wins" :draws="s.draws" :losses="s.losses" />
        </RouterLink>
      </li>
    </ul>
  </main>
</template>

<style scoped>
.tier-chips {
  scrollbar-width: none;
}
.tier-chips::-webkit-scrollbar {
  display: none;
}
.tier-chip {
  display: inline-flex;
  min-height: 44px;
  flex: none;
  align-items: center;
  gap: 6px;
  padding: 0 14px;
  border: 1px solid rgb(255 255 255 / 0.18);
  border-radius: 999px;
  background: rgb(255 255 255 / 0.06);
  color: rgb(255 255 255 / 0.82);
  font-size: 14px;
  white-space: nowrap;
}
.tier-chip[aria-pressed='true'] {
  border-color: rgb(255 255 255 / 0.4);
  background: radial-gradient(120% 140% at 30% 0%, rgb(255 255 255 / 0.4), rgb(255 255 255 / 0.1) 60%);
  box-shadow:
    inset 0 1px 1px rgb(255 255 255 / 0.7),
    inset 0 -3px 8px rgb(234 76 164 / 0.38),
    0 6px 14px rgb(234 76 164 / 0.35);
  color: #fff;
}
</style>
