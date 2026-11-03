<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { getMatches, getPlayersByIds } from '@/api/public'
import type { Match, Player } from '@/types'
import MatchScoreCard from '@/components/matches/MatchScoreCard.vue'
import HudSkeletonBlock from '@/components/common/HudSkeletonBlock.vue'
import PageBanner from '@/components/common/PageBanner.vue'

const PAGE_SIZE = 20

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const matches = ref<Match[]>([])
const playersById = ref<Record<string, Player>>({})
const loading = ref(true)
const error = ref<string | null>(null)
const hasNext = ref(false)

// Numbered pages (?page=2) instead of an ever-growing "load more" list, so
// the DOM never holds more than one page's worth of match cards no matter
// how far back someone browses, and a page is a real, linkable/bookmarkable
// state (survives refresh, back/forward). Any garbage value (non-numeric,
// fractional, zero, negative, or a repeated ?page= producing an array)
// falls back to page 1 instead of crashing.
const currentPage = computed(() => {
  const raw = Number(route.query.page)
  return Number.isInteger(raw) && raw >= 1 ? raw : 1
})

async function loadPage(page: number): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const matchList = await getMatches({ limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE })
    // A page beyond the last one (a stale bookmark, or a hand-edited URL)
    // comes back empty — bounce back to page 1 instead of stranding the
    // reader on a blank page they can only "Prev" their way out of.
    if (matchList.length === 0 && page > 1) {
      await router.replace({ query: { ...route.query, page: undefined } })
      return
    }
    matches.value = matchList
    hasNext.value = matchList.length === PAGE_SIZE
    // Resolve names/avatars for exactly the players appearing on this page
    // — not the whole roster — so this scales with match volume, not
    // member count. Not filtered by is_active, so a since-deactivated
    // player's name still resolves in old match records instead of "?".
    const ids = [...new Set(matchList.flatMap((m) => [...m.team1_player_ids, ...m.team2_player_ids]))]
    playersById.value = Object.fromEntries((await getPlayersByIds(ids)).map((p) => [p.id, p]))
  } catch {
    error.value = t('matches.loadError')
  } finally {
    loading.value = false
  }
}

function goToPage(page: number): void {
  router.push({ query: { ...route.query, page: page > 1 ? String(page) : undefined } })
}

watch(currentPage, (page) => loadPage(page))
onMounted(() => loadPage(currentPage.value))
</script>

<template>
  <main class="pb-12 sm:pb-20">
    <PageBanner eyebrow="Match Log" :title="t('nav.matches')" :sub="t('matches.sub')" mascot="/tiers/wine.webp" />

    <div class="home-world">
      <div class="mx-auto max-w-[1200px] px-3 pt-4 sm:px-6 sm:pt-7">
        <div v-if="loading" class="grid gap-3 lg:grid-cols-2">
          <HudSkeletonBlock v-for="i in 6" :key="i" :delay="i * 80" class="h-40 rounded-[20px]" />
        </div>
        <p v-else-if="error" class="world-card p-5 text-status-error">{{ error }}</p>
        <p v-else-if="matches.length === 0" class="world-card p-5 text-white/65">{{ t('matches.empty') }}</p>

        <template v-else>
          <!-- One list, newest first: no heading per night, as the club asked. -->
          <ul class="mb-7 grid gap-2.5 sm:gap-4 lg:grid-cols-2">
            <li v-for="(m, i) in matches" :key="m.id" v-reveal="i">
              <MatchScoreCard :match="m" :players-by-id="playersById" />
            </li>
          </ul>

          <div class="flex items-center justify-center gap-3">
            <button
              type="button"
              :disabled="currentPage <= 1"
              class="pager world-card disabled:pointer-events-none disabled:opacity-35"
              @click="goToPage(currentPage - 1)"
            >
              ← {{ t('matches.prevPage') }}
            </button>
            <span class="text-sm text-white/60">{{ t('matches.pageLabel', { n: currentPage }) }}</span>
            <button
              type="button"
              :disabled="!hasNext"
              class="pager world-card text-[#ff9fd6] disabled:pointer-events-none disabled:opacity-35"
              @click="goToPage(currentPage + 1)"
            >
              {{ t('matches.nextPage') }} →
            </button>
          </div>
        </template>
      </div>
    </div>
  </main>
</template>

<style scoped>
.pager {
  min-height: 44px;
  padding: 0 18px;
  border-radius: 999px;
  font-size: 14px;
}
</style>
