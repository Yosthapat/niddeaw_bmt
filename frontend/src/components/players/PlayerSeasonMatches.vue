<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getPlayerMatches, getPlayersByIds, getSeasons } from '@/api/public'
import type { Match, Player, Season } from '@/types'
import MatchRow from '@/components/matches/MatchRow.vue'
import HudSkeletonBlock from '@/components/common/HudSkeletonBlock.vue'

// This member's own finished matches, one season (= one calendar year) at a
// time, drawn with the same MatchRow card as the global match log — same
// stamp, same dimmed loser, same layout. The member finds themselves by
// their own avatar, so the row stays neutral rather than re-centring on
// "you"; a second, profile-only style of match card would just be a second
// thing to keep in sync.
//
// The parent keys this component on the player id, so switching members
// gets a fresh instance rather than stale state from the previous one.
const props = defineProps<{ playerId: string }>()

const PAGE_SIZE = 10

const { t } = useI18n()

const seasons = ref<Season[]>([])
const selectedSeason = ref<number | null>(null)
const matches = ref<Match[]>([])
const playersById = ref<Record<string, Player>>({})
const loading = ref(true)
const error = ref<string | null>(null)
// Page lives in component state, not in the URL like MatchHistoryView's
// ?page= — this is one section of a page whose URL already means "this
// member", and a query param here would also have to coexist with the
// season. Paging is a within-visit action; the linkable state is the member.
const page = ref(1)
const hasNext = ref(false)

const currentSeason = computed(() =>
  seasons.value.find((s) => s.number === selectedSeason.value),
)

async function loadMatches(): Promise<void> {
  if (selectedSeason.value === null) return
  loading.value = true
  error.value = null
  try {
    const matchList = await getPlayerMatches(props.playerId, {
      season: selectedSeason.value,
      limit: PAGE_SIZE,
      offset: (page.value - 1) * PAGE_SIZE,
    })
    matches.value = matchList
    // Same next-page test as the match log: a short page is the last one.
    // No total is fetched because none is shown.
    hasNext.value = matchList.length === PAGE_SIZE
    // Includes this member — the card draws both teams in full, so leaving
    // themselves out would render their own avatar as "?".
    const ids = [
      ...new Set(matchList.flatMap((m) => [...m.team1_player_ids, ...m.team2_player_ids])),
    ]
    playersById.value = Object.fromEntries((await getPlayersByIds(ids)).map((p) => [p.id, p]))
  } catch {
    error.value = t('profile.matchesLoadError')
  } finally {
    loading.value = false
  }
}

function selectSeason(number: number): void {
  if (selectedSeason.value === number) return
  selectedSeason.value = number
  page.value = 1
}

watch([selectedSeason, page], loadMatches)

onMounted(async () => {
  try {
    seasons.value = await getSeasons()
  } catch {
    error.value = t('profile.matchesLoadError')
    loading.value = false
    return
  }
  // Open on the season in progress. Falls back to the newest season when
  // none is flagged current — see build_seasons(): a back-dated session can
  // produce a season list that hasn't reached today yet.
  const initial = seasons.value.find((s) => s.is_current) ?? seasons.value.at(-1)
  if (!initial) {
    loading.value = false
    return
  }
  selectedSeason.value = initial.number
})
</script>

<template>
  <section class="mt-8">
    <h2 class="text-xs font-semibold tracking-widest text-brand-pink/70 uppercase">
      {{ t('profile.myMatches') }}
    </h2>

    <p v-if="seasons.length === 0 && !loading" class="mt-3 text-sm text-white/40">
      {{ t('profile.noSeasons') }}
    </p>

    <div v-if="seasons.length > 0" class="mt-3 flex flex-wrap gap-2">
      <button
        v-for="s in seasons"
        :key="s.number"
        type="button"
        class="hud-hover rounded-full border px-4 py-1.5 text-sm font-semibold transition-colors"
        :class="
          s.number === selectedSeason
            ? 'border-brand-pink bg-brand-pink text-brand-black'
            : 'border-brand-pink/30 text-brand-pink hover:border-brand-pink/60'
        "
        @click="selectSeason(s.number)"
      >
        {{ t('profile.seasonLabel', { n: s.number }) }}
      </button>
    </div>

    <p v-if="currentSeason" class="mt-2 text-xs text-white/40">{{ currentSeason.year }}</p>

    <div v-if="loading" class="mt-4 space-y-3">
      <HudSkeletonBlock v-for="i in 3" :key="i" :delay="i * 80" class="h-28" />
    </div>
    <p v-else-if="error" class="mt-4 text-sm text-status-error">{{ error }}</p>
    <p v-else-if="seasons.length > 0 && matches.length === 0" class="mt-4 text-sm text-white/40">
      {{ t('profile.noSeasonMatches') }}
    </p>

    <ul v-else-if="matches.length > 0" class="mt-4 space-y-3">
      <li
        v-for="(m, i) in matches"
        :key="m.id"
        v-reveal="i"
        class="hud-panel glass-panel hud-hover border border-brand-pink/15 transition-colors hover:border-brand-pink/40"
      >
        <MatchRow :match="m" :players-by-id="playersById" />
      </li>
    </ul>

    <div v-if="!loading && matches.length > 0" class="mt-4 flex items-center justify-center gap-3">
      <button
        type="button"
        :disabled="page <= 1"
        class="hud-hover rounded-full border border-brand-pink/40 px-4 py-2 text-sm font-semibold text-brand-pink hover:bg-brand-pink hover:text-brand-black disabled:pointer-events-none disabled:opacity-30"
        @click="page -= 1"
      >
        {{ t('matches.prevPage') }}
      </button>
      <span class="text-sm text-white/50">{{ t('matches.pageLabel', { n: page }) }}</span>
      <button
        type="button"
        :disabled="!hasNext"
        class="hud-hover rounded-full border border-brand-pink/40 px-4 py-2 text-sm font-semibold text-brand-pink hover:bg-brand-pink hover:text-brand-black disabled:pointer-events-none disabled:opacity-30"
        @click="page += 1"
      >
        {{ t('matches.nextPage') }}
      </button>
    </div>
  </section>
</template>
