<script setup lang="ts">
/**
 * What the 🔍 in the phone bar opens: one box that finds a member by
 * nickname or member number, the way Facebook's search page works. Before
 * anything is typed it offers what was searched last on this phone and who
 * is on top right now, so the page is never blank.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { getPlayers } from '@/api/public'
import type { PlayerStats } from '@/types'
import { tierMeta } from '@/composables/useEloTier'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'
import TierMascot from '@/components/players/TierMascot.vue'

const { t } = useI18n()
const router = useRouter()
const q = ref('')
const stats = ref<PlayerStats[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

const RECENT_KEY = 'niddeaw_recent_search'
const MAX_RECENT = 6
function readRecent(): string[] {
  try {
    const raw = JSON.parse(localStorage.getItem(RECENT_KEY) ?? '[]') as unknown
    return Array.isArray(raw) ? raw.filter((x): x is string => typeof x === 'string').slice(0, MAX_RECENT) : []
  } catch {
    return []
  }
}
const recent = ref<string[]>(readRecent())
function remember(term: string): void {
  const next = [term, ...recent.value.filter((r) => r.toLowerCase() !== term.toLowerCase())].slice(0, MAX_RECENT)
  recent.value = next
  try {
    localStorage.setItem(RECENT_KEY, JSON.stringify(next))
  } catch {
    // private mode: it just won't be remembered
  }
}

onMounted(async () => {
  try {
    stats.value = await getPlayers()
  } catch {
    error.value = t('members.loadError')
  } finally {
    loading.value = false
  }
})

function back(): void {
  if (window.history.state?.back) router.back()
  else router.push('/')
}

const query = computed(() => q.value.trim().toLowerCase())
const results = computed(() => {
  if (!query.value) {
    return [...stats.value].sort((a, b) => b.player.elo_score - a.player.elo_score).slice(0, 6)
  }
  // Names that start with what was typed first, then the rest.
  const hits = stats.value.filter(
    (s) => s.player.nickname.toLowerCase().includes(query.value) || s.player.member_code.toLowerCase().includes(query.value),
  )
  const starts = (s: PlayerStats): number => Number(s.player.nickname.toLowerCase().startsWith(query.value))
  return hits.sort((a, b) => starts(b) - starts(a) || b.player.elo_score - a.player.elo_score)
})

function open(s: PlayerStats): void {
  remember(q.value.trim() || s.player.nickname)
  router.push(`/members/${s.player.id}`)
}
</script>

<template>
  <main class="mx-auto max-w-xl pb-6">
    <header class="flex h-16 items-center gap-1.5 border-b border-white/8 pr-3 pl-1.5">
      <button type="button" class="flex h-11 w-11 flex-none items-center justify-center" :aria-label="t('search.back')" @click="back">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" class="h-[22px] w-[22px]" aria-hidden="true">
          <path d="m15 6-6 6 6 6" />
        </svg>
      </button>
      <label for="member-search" class="sr-only">{{ t('nav.search') }}</label>
      <input
        id="member-search"
        v-model="q"
        type="search"
        enterkeyhint="search"
        autocomplete="off"
        autofocus
        :placeholder="t('search.placeholder')"
        class="h-11 min-w-0 flex-1 rounded-full border-0 bg-white/10 px-4 text-base text-white placeholder:text-white/50"
      />
    </header>

    <div class="flex flex-col gap-3.5 px-4 py-3.5">
      <template v-if="!query">
        <div v-if="recent.length" class="flex flex-col gap-2.5">
          <h2 class="text-[15px] font-medium">{{ t('search.recent') }}</h2>
          <div class="flex flex-wrap gap-2">
            <button v-for="r in recent" :key="r" type="button" class="search-chip" @click="q = r">{{ r }}</button>
          </div>
        </div>
        <h2 class="text-[15px] font-medium">{{ t('search.top') }}</h2>
      </template>
      <p v-else-if="!loading && results.length" class="text-[13px] text-white/65" aria-live="polite">{{ t('search.count', { n: results.length }) }}</p>

      <p v-if="loading" class="text-sm text-white/60">{{ t('search.loading') }}</p>
      <p v-else-if="error" class="text-status-error">{{ error }}</p>
      <ul v-else-if="results.length" class="flex flex-col gap-0.5">
        <li v-for="s in results" :key="s.player.id">
          <a
            :href="`/members/${s.player.id}`"
            class="flex min-h-16 items-center gap-3 rounded-xl px-2 hover:bg-white/6"
            @click.prevent="open(s)"
          >
            <PlayerAvatar :name="s.player.nickname" :avatar-url="s.player.avatar_url" size="md" />
            <span class="flex min-w-0 flex-1 flex-col">
              <span class="truncate text-base font-medium">{{ s.player.nickname }}</span>
              <span class="text-xs text-white/60">
                {{ s.player.member_code }} · {{ tierMeta(s.player.elo_level).label }} · ELO {{ Math.round(s.player.elo_score) }}
              </span>
            </span>
            <TierMascot :tier="s.player.elo_level" :size="34" :interactive="false" />
          </a>
        </li>
      </ul>
      <div v-else-if="query" class="flex flex-col items-center gap-2 pt-8 text-center text-white/70">
        <TierMascot tier="milk" :size="80" :interactive="false" class="opacity-80" />
        <p>{{ t('search.none', { q: q.trim() }) }}</p>
      </div>
    </div>
  </main>
</template>

<style scoped>
.search-chip {
  display: inline-flex;
  min-height: 40px;
  align-items: center;
  padding: 0 14px;
  border: 1px solid rgb(255 255 255 / 0.16);
  border-radius: 999px;
  background: rgb(255 255 255 / 0.06);
  font-size: 14px;
}
</style>
