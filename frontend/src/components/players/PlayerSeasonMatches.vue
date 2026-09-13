<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getPlayerMatches, getPlayersByIds, getSeasons } from '@/api/public'
import type { Match, Player, Season } from '@/types'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'
import HudSkeletonBlock from '@/components/common/HudSkeletonBlock.vue'

// This member's own finished matches, one season (= one calendar year) at a
// time. Rows are written from *their* perspective — a WIN/LOSS badge that
// reads off which side they were on — which is the whole reason this isn't
// reusing the match-log row from MatchHistoryView: that row is neutral
// because it has no player to be relative to.
//
// The parent keys this component on the player id, so switching members
// gets a fresh instance rather than stale state from the previous one.
const props = defineProps<{ playerId: string }>()

const PAGE_SIZE = 10

const { t, locale } = useI18n()

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

function nameOf(playerId: string): string {
  return playersById.value[playerId]?.nickname ?? '?'
}

function avatarOf(playerId: string): string | undefined {
  return playersById.value[playerId]?.avatar_url ?? undefined
}

function sideOf(match: Match, own: boolean): string[] {
  const onTeam1 = match.team1_player_ids.includes(props.playerId)
  return onTeam1 === own ? match.team1_player_ids : match.team2_player_ids
}

function partnersOf(match: Match): string[] {
  return sideOf(match, true).filter((id) => id !== props.playerId)
}

/** Win/loss from this member's side, not team1's. */
function resultOf(match: Match): 'win' | 'loss' | 'draw' | null {
  if (!match.winner) return null
  if (match.winner === 'draw') return 'draw'
  const mySide = match.team1_player_ids.includes(props.playerId) ? 'team1' : 'team2'
  return match.winner === mySide ? 'win' : 'loss'
}

/** WIN/LOSS/DRAW, resolved through an explicit switch rather than a
 * computed `matches.${result}` key so a renamed translation key fails the
 * type-check instead of rendering the raw key at runtime. */
function resultLabel(match: Match): string {
  switch (resultOf(match)) {
    case 'win':
      return t('matches.win')
    case 'loss':
      return t('matches.loss')
    case 'draw':
      return t('matches.draw')
    default:
      return ''
  }
}

function dateLabel(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString(locale.value === 'th' ? 'th-TH' : 'en-US', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

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
    const ids = [
      ...new Set(matchList.flatMap((m) => [...m.team1_player_ids, ...m.team2_player_ids])),
    ].filter((id) => id !== props.playerId)
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

    <div v-if="loading" class="mt-4 space-y-2">
      <HudSkeletonBlock v-for="i in 3" :key="i" :delay="i * 80" class="h-20" />
    </div>
    <p v-else-if="error" class="mt-4 text-sm text-status-error">{{ error }}</p>
    <p v-else-if="seasons.length > 0 && matches.length === 0" class="mt-4 text-sm text-white/40">
      {{ t('profile.noSeasonMatches') }}
    </p>

    <ul v-else-if="matches.length > 0" class="mt-4 space-y-2">
      <li
        v-for="m in matches"
        :key="m.id"
        class="hud-panel glass-panel border border-brand-pink/15 transition-colors hover:border-brand-pink/40"
      >
        <RouterLink :to="`/matches/${m.id}`" class="block px-4 py-3">
          <div class="flex items-center justify-between gap-2 text-xs tracking-wide text-white/40 uppercase">
            <span>{{ m.type === 'double' ? t('matches.doubles') : t('matches.singles') }}</span>
            <span>{{ dateLabel(m.created_at) }}</span>
          </div>

          <div class="mt-2 flex items-center justify-between gap-3">
            <div class="min-w-0 flex-1">
              <p v-if="partnersOf(m).length > 0" class="truncate text-xs text-white/40">
                {{ t('profile.withPartner') }} {{ partnersOf(m).map(nameOf).join(' & ') }}
              </p>
              <p class="mt-0.5 text-xs tracking-wide text-white/40 uppercase">
                {{ t('profile.against') }}
              </p>
              <div class="mt-1 flex flex-wrap items-center gap-2">
                <span
                  v-for="pid in sideOf(m, false)"
                  :key="pid"
                  class="flex items-center gap-1.5 text-sm text-white/80"
                >
                  <PlayerAvatar :name="nameOf(pid)" :avatar-url="avatarOf(pid)" size="sm" />
                  {{ nameOf(pid) }}
                </span>
              </div>
            </div>

            <span
              v-if="resultOf(m)"
              class="hud-panel shrink-0 border bg-brand-black px-2.5 py-1 font-display text-xs font-bold uppercase"
              :class="{
                'border-status-success text-status-success': resultOf(m) === 'win',
                'border-status-error text-status-error': resultOf(m) === 'loss',
                'border-tier-milk text-tier-milk': resultOf(m) === 'draw',
              }"
            >
              {{ resultLabel(m) }}
            </span>
          </div>
        </RouterLink>
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
