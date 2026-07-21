<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { getMatchDetail } from '@/api/public'
import type { MatchDetail } from '@/types'
import EloBadge from '@/components/players/EloBadge.vue'
import TierMascot from '@/components/players/TierMascot.vue'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'

const route = useRoute()
const { t, locale } = useI18n()
const detail = ref<MatchDetail | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

function statusFor(side: 'team1' | 'team2'): 'win' | 'loss' | 'draw' | null {
  const winner = detail.value?.match.winner
  if (!winner) return null
  if (winner === 'draw') return 'draw'
  return winner === side ? 'win' : 'loss'
}

function statusLabel(side: 'team1' | 'team2'): string {
  const status = statusFor(side)
  if (status === 'win') return t('matches.win')
  if (status === 'draw') return t('matches.draw')
  if (status === 'loss') return t('matches.loss')
  return t('matches.inProgress')
}

const setsLabel = computed(() => {
  const sets = detail.value?.match.sets
  if (!sets || sets.length === 0) return '-'
  return sets.map(([a, b]) => `${a}-${b}`).join('  ·  ')
})

const durationLabel = computed(() => {
  const minutes = detail.value?.duration_minutes
  if (minutes == null) return null
  return `${minutes.toFixed(1)} ${t('matches.minutes')}`
})

const dateLabel = computed(() => {
  if (!detail.value) return ''
  return new Date(detail.value.match.created_at).toLocaleString(locale.value === 'th' ? 'th-TH' : 'en-US')
})

// See PlayerProfileView.vue for why this watches the param instead of
// onMounted — navigating between two /matches/:id URLs reuses this
// component instance rather than remounting it.
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
  <main class="mx-auto max-w-3xl px-4 py-8 sm:py-12">
    <RouterLink to="/matches" class="text-sm font-semibold text-brand-pink/70 hover:text-brand-pink">
      &larr; {{ t('matches.backToMatches') }}
    </RouterLink>

    <p v-if="loading" class="mt-6 text-white/60">{{ t('common.loading') }}</p>
    <p v-else-if="error || !detail" class="mt-6 text-status-error">{{ error }}</p>

    <template v-else>
      <div class="mt-6 text-center">
        <p class="text-xs tracking-widest text-white/40 uppercase">
          {{ detail.match.type === 'double' ? t('matches.doubles') : t('matches.singles') }}
          · {{ dateLabel }}
          <span v-if="durationLabel"> · {{ durationLabel }}</span>
        </p>
        <p class="mt-2 font-display text-2xl font-bold text-white">{{ setsLabel }}</p>
        <p v-if="detail.match.winner === 'draw'" class="mt-1 text-sm text-white/40">{{ t('common.draw') }}</p>
      </div>

      <div class="mt-8 grid grid-cols-2 gap-4">
        <div
          class="hud-panel border p-4"
          :class="
            statusFor('team1') === 'win'
              ? 'border-brand-pink bg-brand-surface'
              : 'border-brand-pink/15 bg-brand-surface opacity-70'
          "
        >
          <div class="flex justify-center">
            <span class="stamp-badge" :class="`stamp-badge--${statusFor('team1') ?? 'pending'}`">
              {{ statusLabel('team1') }}
            </span>
          </div>
          <div v-for="stat in detail.team1" :key="stat.player.id" class="mt-4 flex flex-col items-center gap-2">
            <RouterLink :to="`/members/${stat.player.id}`">
              <PlayerAvatar :name="stat.player.nickname" :avatar-url="stat.player.avatar_url" size="lg" />
            </RouterLink>
            <RouterLink
              :to="`/members/${stat.player.id}`"
              class="font-display font-semibold text-white hover:text-brand-pink"
            >
              {{ stat.player.nickname }}
            </RouterLink>
            <TierMascot :tier="stat.player.elo_level" :size="32" />
            <EloBadge :elo-score="stat.player.elo_score" show-score />
            <dl class="mt-1 grid grid-cols-3 gap-x-3 gap-y-1 text-center text-xs text-white/50">
              <div><dt class="uppercase">Rank</dt><dd class="font-semibold text-white/80">#{{ stat.elo_rank }}</dd></div>
              <div><dt class="uppercase">Game</dt><dd class="font-semibold text-white/80">{{ stat.games }}</dd></div>
              <div><dt class="uppercase">Sc%</dt><dd class="font-semibold text-white/80">{{ stat.score_percent.toFixed(0) }}</dd></div>
              <div><dt class="uppercase">W</dt><dd class="font-semibold text-status-success">{{ stat.wins }}</dd></div>
              <div><dt class="uppercase">D</dt><dd class="font-semibold text-white/70">{{ stat.draws }}</dd></div>
              <div><dt class="uppercase">L</dt><dd class="font-semibold text-status-error">{{ stat.losses }}</dd></div>
            </dl>
          </div>
        </div>

        <div
          class="hud-panel border p-4"
          :class="
            statusFor('team2') === 'win'
              ? 'border-brand-pink bg-brand-surface'
              : 'border-brand-pink/15 bg-brand-surface opacity-70'
          "
        >
          <div class="flex justify-center">
            <span class="stamp-badge" :class="`stamp-badge--${statusFor('team2') ?? 'pending'}`">
              {{ statusLabel('team2') }}
            </span>
          </div>
          <div v-for="stat in detail.team2" :key="stat.player.id" class="mt-4 flex flex-col items-center gap-2">
            <RouterLink :to="`/members/${stat.player.id}`">
              <PlayerAvatar :name="stat.player.nickname" :avatar-url="stat.player.avatar_url" size="lg" />
            </RouterLink>
            <RouterLink
              :to="`/members/${stat.player.id}`"
              class="font-display font-semibold text-white hover:text-brand-pink"
            >
              {{ stat.player.nickname }}
            </RouterLink>
            <TierMascot :tier="stat.player.elo_level" :size="32" />
            <EloBadge :elo-score="stat.player.elo_score" show-score />
            <dl class="mt-1 grid grid-cols-3 gap-x-3 gap-y-1 text-center text-xs text-white/50">
              <div><dt class="uppercase">Rank</dt><dd class="font-semibold text-white/80">#{{ stat.elo_rank }}</dd></div>
              <div><dt class="uppercase">Game</dt><dd class="font-semibold text-white/80">{{ stat.games }}</dd></div>
              <div><dt class="uppercase">Sc%</dt><dd class="font-semibold text-white/80">{{ stat.score_percent.toFixed(0) }}</dd></div>
              <div><dt class="uppercase">W</dt><dd class="font-semibold text-status-success">{{ stat.wins }}</dd></div>
              <div><dt class="uppercase">D</dt><dd class="font-semibold text-white/70">{{ stat.draws }}</dd></div>
              <div><dt class="uppercase">L</dt><dd class="font-semibold text-status-error">{{ stat.losses }}</dd></div>
            </dl>
          </div>
        </div>
      </div>
    </template>
  </main>
</template>

<style scoped>
.stamp-badge {
  display: inline-block;
  rotate: -8deg;
  font-family: var(--font-display);
  font-weight: 800;
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 0.15rem 0.75rem;
  border-radius: 0.25rem;
  border-width: 2px;
  border-style: solid;
}
.stamp-badge--win {
  color: var(--color-status-success);
  border-color: var(--color-status-success);
}
.stamp-badge--loss {
  color: rgb(255 255 255 / 0.4);
  border-color: rgb(255 255 255 / 0.2);
  rotate: 8deg;
}
.stamp-badge--draw {
  color: var(--color-tier-milk);
  border-color: var(--color-tier-milk);
}
.stamp-badge--pending {
  color: rgb(255 255 255 / 0.4);
  border-color: rgb(255 255 255 / 0.2);
  border-style: dashed;
}
</style>
