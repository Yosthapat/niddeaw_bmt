<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { getMatchDetail } from '@/api/public'
import * as adminApi from '@/api/admin'
import { useAuthStore } from '@/stores/auth'
import type { MatchDetail, MatchWinner } from '@/types'
import { formatDateTime } from '@/utils/format'
import EloBadge from '@/components/players/EloBadge.vue'
import TierMascot from '@/components/players/TierMascot.vue'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'
import CreditCardMark from '@/components/credit/CreditCardMark.vue'
import HudSkeletonBlock from '@/components/common/HudSkeletonBlock.vue'
import PageBanner from '@/components/common/PageBanner.vue'
import EloGauge from '@/components/matches/EloGauge.vue'
import EloDelta from '@/components/matches/EloDelta.vue'
import { isUpset } from '@/utils/eloOdds'
import { apiErrorMessage } from '@/api/errors'

const route = useRoute()
const { t, locale } = useI18n()
const authStore = useAuthStore()
const detail = ref<MatchDetail | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

// The fix-up lives here rather than on the matchmaking screen because by
// the time anyone notices the wrong team was tapped, the match has left
// the queue — this page is where they end up looking at it. Only an
// admin sees it, and the backend refuses once the session is closed.
const editing = ref(false)
const editError = ref<string | null>(null)
const editDone = ref(false)
const editOpen = ref(false)
const canEdit = computed(() => authStore.isAuthenticated && detail.value?.match.status === 'completed')

function teamLabel(side: 'team1' | 'team2'): string {
  const stats = side === 'team1' ? detail.value?.team1 : detail.value?.team2
  return (stats ?? []).map((s) => s.player.nickname).join(' & ')
}

async function fixResult(winner: MatchWinner): Promise<void> {
  const match = detail.value?.match
  if (!match || editing.value) return
  editing.value = true
  editError.value = null
  editDone.value = false
  try {
    await adminApi.editMatchResult(match.id, winner)
    // Re-fetch rather than patch in place: the players' ELO, tiers and
    // win/loss counts on this page all moved too.
    detail.value = await getMatchDetail(match.id)
    editDone.value = true
    editOpen.value = false
  } catch (e) {
    editError.value = apiErrorMessage(e, t('matchRecord.editFailed'))
  } finally {
    editing.value = false
  }
}

function statusFor(side: 'team1' | 'team2'): 'win' | 'loss' | 'draw' | null {
  const winner = detail.value?.match.winner
  if (!winner) return null
  if (winner === 'draw') return 'draw'
  return winner === side ? 'win' : 'loss'
}

// The plate on each team's card, in the same words as the match log.
function plate(side: 'team1' | 'team2'): string {
  const status = statusFor(side)
  if (status === 'win') return t('matches.win')
  if (status === 'draw') return t('matches.draw')
  if (status === 'loss') return t('matches.lose')
  return t('matches.inProgress')
}

// The banner says how it ended, since there is no score to show.
const headline = computed(() => {
  const winner = detail.value?.match.winner
  if (!detail.value) return t('nav.matches')
  if (!winner) return t('matches.inProgress')
  if (winner === 'draw') return t('common.draw')
  return `${teamLabel(winner)} ${t('matchRecord.wins')}`
})
const eyebrow = computed(() => {
  const m = detail.value?.match
  if (!m) return 'Match'
  return [
    typeof m.match_no === 'number' ? `Match #${m.match_no}` : 'Match',
    m.court ? t('home.live.court', { court: m.court }) : null,
  ]
    .filter(Boolean)
    .join(' · ')
})

const durationLabel = computed(() => {
  const minutes = detail.value?.duration_minutes
  if (minutes == null) return null
  return `${minutes.toFixed(1)} ${t('matches.minutes')}`
})

const dateLabel = computed(() => {
  if (!detail.value) return ''
  return formatDateTime(detail.value.match.created_at, locale.value)
})
// each team's average ELO going into it (or now, for a match not played yet)
const gauge = computed(() => {
  const m = detail.value?.match
  return m && typeof m.elo_team1 === 'number' && typeof m.elo_team2 === 'number' ? { a: m.elo_team1, b: m.elo_team2 } : null
})
const upset = computed(() => {
  const m = detail.value?.match
  return !!m && isUpset(m.elo_team1, m.elo_team2, m.winner)
})
const sub = computed(() => [dateLabel.value, durationLabel.value].filter(Boolean).join(' · '))

// See PlayerProfileView.vue for why this watches the param instead of
// onMounted.
watch(
  () => route.params.id,
  async (id) => {
    loading.value = true
    error.value = null
    try {
      detail.value = await getMatchDetail(String(id))
    } catch {
      error.value = t('matches.notFound')
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)
</script>

<template>
  <main class="pb-12 sm:pb-20">
    <PageBanner :eyebrow="eyebrow" :title="headline" :sub="sub" mascot="/tiers/wine.webp">
      <RouterLink to="/matches" class="glass-pill">
        <span aria-hidden="true">←</span> {{ t('matches.backToMatches') }}
      </RouterLink>
    </PageBanner>

    <div class="home-world">
      <div class="mx-auto max-w-[1000px] px-3 pt-5 sm:px-6 sm:pt-8">
        <div v-if="loading" class="grid gap-4 sm:grid-cols-2">
          <HudSkeletonBlock class="h-72 rounded-[22px]" />
          <HudSkeletonBlock :delay="80" class="h-72 rounded-[22px]" />
        </div>
        <p v-else-if="error || !detail" class="world-card p-5 text-status-error">{{ error }}</p>

        <template v-else>
          <section v-if="gauge" v-reveal class="world-card relative mb-4 overflow-hidden p-4 sm:mb-5 sm:p-5" :aria-label="t('elo.avg')">
            <span v-if="upset" class="upset-stamp">{{ t('elo.upset') }}</span>
            <div class="mb-3 flex items-center justify-between gap-3" :style="upset ? { paddingRight: '64px' } : undefined">
              <span class="flex min-w-0 items-center gap-2">
                <span class="h-2.5 w-2.5 shrink-0 rounded-full bg-[#ff4fae]" aria-hidden="true" />
                <span class="truncate font-display text-sm font-semibold">{{ teamLabel('team1') }}</span>
              </span>
              <span class="flex min-w-0 items-center gap-2">
                <span class="truncate font-display text-sm font-semibold">{{ teamLabel('team2') }}</span>
                <span class="h-2.5 w-2.5 shrink-0 rounded-full bg-[#8f6bff]" aria-hidden="true" />
              </span>
            </div>
            <EloGauge
              :elo1="gauge.a"
              :elo2="gauge.b"
              :winner="detail.match.winner"
              :live="detail.match.status === 'in_progress'"
              :label="detail.match.status === 'completed' ? 'before' : 'avg'"
            />
            <div v-if="typeof detail.match.elo_delta_team1 === 'number' && typeof detail.match.elo_delta_team2 === 'number'" class="mt-3 flex justify-between">
              <EloDelta :delta="detail.match.elo_delta_team1" />
              <EloDelta :delta="detail.match.elo_delta_team2" />
            </div>
          </section>
          <div class="grid gap-4 sm:grid-cols-2 sm:gap-5">
            <section
              v-for="(side, i) in (['team1', 'team2'] as const)"
              :key="side"
              v-reveal="i"
              class="world-card team-card p-4 sm:p-5"
              :class="statusFor(side) ?? 'pending'"
              :aria-label="teamLabel(side)"
            >
              <div class="flex items-center justify-between gap-3">
                <p class="world-eyebrow">TEAM {{ i + 1 }}</p>
                <span class="plate">{{ plate(side) }}</span>
              </div>
              <div
                v-for="stat in side === 'team1' ? detail.team1 : detail.team2"
                :key="stat.player.id"
                class="player mt-4"
              >
                <div class="flex items-center gap-3">
                  <RouterLink :to="`/members/${stat.player.id}`" class="ring shrink-0">
                    <PlayerAvatar :name="stat.player.nickname" :avatar-url="stat.player.avatar_url" size="lg" round />
                  </RouterLink>
                  <div class="min-w-0 flex-1">
                    <RouterLink
                      :to="`/members/${stat.player.id}`"
                      class="block truncate font-display text-lg font-bold text-white hover:text-brand-pink-light"
                    >
                      {{ stat.player.nickname }} <CreditCardMark :player-id="stat.player.id" size="md" />
                    </RouterLink>
                    <span class="mt-1 inline-flex items-center gap-1.5">
                      <TierMascot :tier="stat.player.elo_level" :size="24" :interactive="false" />
                      <EloBadge :elo-score="stat.player.elo_score" show-score />
                    </span>
                  </div>
                </div>
                <dl class="stats mt-3">
                  <div><dt>Rank</dt><dd>#{{ stat.elo_rank }}</dd></div>
                  <div><dt>{{ t('common.game') }}</dt><dd>{{ stat.games }}</dd></div>
                  <div><dt>Sc%</dt><dd>{{ stat.score_percent.toFixed(0) }}</dd></div>
                  <div><dt>W</dt><dd class="text-status-success">{{ stat.wins }}</dd></div>
                  <div><dt>D</dt><dd class="text-white/70">{{ stat.draws }}</dd></div>
                  <div><dt>L</dt><dd class="text-status-error">{{ stat.losses }}</dd></div>
                </dl>
              </div>
            </section>
          </div>

          <section v-if="canEdit" class="world-card mt-6 p-5">
            <button
              v-if="!editOpen"
              type="button"
              class="tap rounded-full border border-brand-pink/50 px-4 text-sm font-semibold text-brand-pink-light hover:bg-brand-pink hover:text-brand-black"
              @click="editOpen = true"
            >
              {{ t('matchRecord.editResult') }}
            </button>
            <template v-else>
              <p class="text-sm text-white/65">{{ t('matchRecord.editResultHint') }}</p>
              <div class="mt-3 space-y-2">
                <button
                  v-for="option in [
                    { winner: 'team1' as MatchWinner, label: `${teamLabel('team1')} ${t('matchRecord.wins')}` },
                    { winner: 'draw' as MatchWinner, label: t('common.draw') },
                    { winner: 'team2' as MatchWinner, label: `${teamLabel('team2')} ${t('matchRecord.wins')}` },
                  ]"
                  :key="option.winner"
                  type="button"
                  :disabled="editing"
                  class="min-h-11 w-full rounded-2xl border px-3 text-sm font-semibold disabled:opacity-50"
                  :class="
                    detail.match.winner === option.winner
                      ? 'border-brand-pink bg-brand-pink/15 text-brand-pink-light'
                      : 'border-white/15 bg-white/5 text-white/80 hover:border-brand-pink'
                  "
                  @click="fixResult(option.winner)"
                >
                  {{ option.label }}
                </button>
              </div>
              <button type="button" class="tap mt-2 text-sm text-white/55" @click="editOpen = false">
                {{ t('common.cancel') }}
              </button>
            </template>
            <p v-if="editing" class="mt-3 text-sm text-white/55">{{ t('matchRecord.editing') }}</p>
            <p v-if="editError" class="mt-3 text-sm text-status-error">{{ editError }}</p>
            <p v-if="editDone" class="mt-3 text-sm text-status-success">{{ t('matchRecord.edited') }}</p>
          </section>
        </template>
      </div>
    </div>
  </main>
</template>

<style scoped>
/* The winners lit gold like the match log's WIN row, the losers dimmed. */
.team-card.win {
  border-color: rgb(255 211 77 / 0.5);
  background:
    radial-gradient(90% 60% at 50% 0%, rgb(255 211 77 / 0.16), transparent 70%),
    linear-gradient(135deg, rgb(255 255 255 / 0.12), rgb(255 255 255 / 0.03) 55%, rgb(255 255 255 / 0.07)),
    rgb(24 10 46 / 0.6);
  box-shadow:
    inset 0 1px 1px rgb(255 255 255 / 0.35),
    0 22px 44px -22px rgb(255 211 77 / 0.55),
    0 10px 28px rgb(6 0 20 / 0.45);
}
.team-card.loss {
  opacity: 0.72;
}
.player + .player {
  padding-top: 16px;
  border-top: 1px solid rgb(255 255 255 / 0.08);
}
.ring {
  border-radius: 50%;
  box-shadow: 0 0 0 2px rgb(255 255 255 / 0.22);
}
.win .ring {
  box-shadow:
    0 0 0 2px #ffd34d,
    0 0 14px rgb(255 211 77 / 0.45);
}
.plate {
  display: inline-flex;
  min-width: 64px;
  height: 30px;
  align-items: center;
  justify-content: center;
  padding: 0 12px;
  border: 1px solid rgb(255 255 255 / 0.14);
  border-radius: 999px;
  font-family: var(--font-display);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: rgb(255 255 255 / 0.5);
}
.win .plate {
  border: 0;
  background: linear-gradient(#ffe58a, #ffc94d);
  color: #2a1a00;
  box-shadow: 0 0 16px rgb(255 201 77 / 0.6);
}
.draw .plate {
  border-color: rgb(255 255 255 / 0.22);
  background: rgb(255 255 255 / 0.12);
  color: rgb(255 255 255 / 0.88);
}
.stats {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 4px;
  padding: 8px 6px;
  border: 1px solid rgb(255 255 255 / 0.1);
  border-radius: 14px;
  background: rgb(255 255 255 / 0.05);
  text-align: center;
}
.stats div {
  display: flex;
  flex-direction: column-reverse;
  align-items: center;
}
.stats dt {
  font-size: 10px;
  letter-spacing: 0.06em;
  color: rgb(255 255 255 / 0.5);
  text-transform: uppercase;
}
.stats dd {
  margin: 0;
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 700;
}
</style>
