<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { getPlayerProfile } from '@/api/public'
import type { PlayerProfile } from '@/types'
import EloBadge from '@/components/players/EloBadge.vue'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'
import TierMascot from '@/components/players/TierMascot.vue'

const route = useRoute()
const { t } = useI18n()
const profile = ref<PlayerProfile | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

// Navigating from one profile to another (e.g. clicking a similar-level
// member or the nemesis card) reuses this component instance instead of
// remounting it, since both URLs match the same /members/:id route record
// — onMounted alone would never re-fire, leaving the old profile on screen
// under the new URL. Watching the param (with immediate for the first load)
// re-fetches every time it actually changes.
watch(
  () => route.params.id,
  async (id) => {
    loading.value = true
    error.value = null
    try {
      profile.value = await getPlayerProfile(String(id))
    } catch {
      error.value = t('profile.notFound')
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)
</script>

<template>
  <main class="mx-auto max-w-2xl px-4 py-8 sm:py-12">
    <RouterLink to="/members" class="text-sm font-semibold text-brand-pink/70 hover:text-brand-pink">
      &larr; {{ t('profile.backToMembers') }}
    </RouterLink>

    <p v-if="loading" class="mt-6 text-white/60">{{ t('common.loading') }}</p>
    <p v-else-if="error || !profile" class="mt-6 text-status-error">{{ error }}</p>

    <template v-else>
      <div class="mt-6 flex flex-col items-center gap-6 sm:flex-row sm:items-center sm:justify-center">
        <div class="flex flex-col items-center gap-2 text-center">
          <PlayerAvatar :name="profile.player.nickname" :avatar-url="profile.player.avatar_url" size="xl" />
          <h1 class="mt-1 font-display text-2xl font-bold">{{ profile.player.nickname }}</h1>
        </div>

        <div class="hidden h-56 w-px bg-brand-pink/15 sm:block" />

        <div class="flex flex-col items-center gap-2 text-center">
          <TierMascot :tier="profile.player.elo_level" :size="72" />
          <EloBadge :elo-score="profile.player.elo_score" show-score />
          <p class="text-xs tracking-widest text-white/40 uppercase">
            {{ t('profile.eloRank') }} <span class="font-semibold text-brand-pink">#{{ profile.elo_rank }}</span>
            / {{ profile.total_ranked_players }}
          </p>
          <p v-if="profile.player.dominant_hand" class="text-xs text-white/50">
            {{ profile.player.dominant_hand === 'left' ? t('profile.leftHanded') : t('profile.rightHanded') }}
          </p>
          <div
            v-if="profile.player.tiktok || profile.player.instagram"
            class="mt-1 flex flex-wrap items-center justify-center gap-1.5"
          >
            <span
              v-if="profile.player.tiktok"
              class="hud-panel border border-brand-pink/20 bg-brand-surface px-2.5 py-1 text-xs text-white/70"
            >
              TikTok {{ profile.player.tiktok }}
            </span>
            <span
              v-if="profile.player.instagram"
              class="hud-panel border border-brand-pink/20 bg-brand-surface px-2.5 py-1 text-xs text-white/70"
            >
              IG {{ profile.player.instagram }}
            </span>
          </div>
        </div>
      </div>

      <div class="mt-8 grid grid-cols-3 gap-2.5 sm:grid-cols-6">
        <div class="hud-panel border border-brand-pink/20 bg-brand-surface p-3 text-center">
          <p class="text-xs tracking-wide text-white/40 uppercase">{{ t('common.game') }}</p>
          <p class="mt-1 font-display text-xl font-bold">{{ profile.games }}</p>
        </div>
        <div class="hud-panel border border-brand-pink/20 bg-brand-surface p-3 text-center">
          <p class="text-xs tracking-wide text-white/40 uppercase">{{ t('common.win') }}</p>
          <p class="mt-1 font-display text-xl font-bold text-status-success">{{ profile.wins }}</p>
        </div>
        <div class="hud-panel border border-brand-pink/20 bg-brand-surface p-3 text-center">
          <p class="text-xs tracking-wide text-white/40 uppercase">{{ t('common.draw') }}</p>
          <p class="mt-1 font-display text-xl font-bold text-white/70">{{ profile.draws }}</p>
        </div>
        <div class="hud-panel border border-brand-pink/20 bg-brand-surface p-3 text-center">
          <p class="text-xs tracking-wide text-white/40 uppercase">{{ t('common.loss') }}</p>
          <p class="mt-1 font-display text-xl font-bold text-status-error">{{ profile.losses }}</p>
        </div>
        <div class="hud-panel border border-brand-pink/40 bg-brand-surface p-3 text-center">
          <p class="text-xs tracking-wide text-white/40 uppercase">Pts</p>
          <p class="mt-1 font-display text-xl font-bold text-brand-pink">{{ profile.points }}</p>
        </div>
        <div class="hud-panel border border-brand-pink/20 bg-brand-surface p-3 text-center">
          <p class="text-xs tracking-wide text-white/40 uppercase">{{ t('common.scorePercent') }}</p>
          <p class="mt-1 font-display text-xl font-bold">{{ profile.score_percent.toFixed(1) }}</p>
        </div>
      </div>

      <section v-if="profile.nemesis" class="hud-panel mt-8 border border-brand-pink/20 bg-brand-surface p-4">
        <h2 class="text-xs font-semibold tracking-widest text-brand-pink/70 uppercase">{{ t('profile.nemesis') }}</h2>
        <div class="mt-3 flex items-center gap-3">
          <PlayerAvatar
            :name="profile.nemesis.player.nickname"
            :avatar-url="profile.nemesis.player.avatar_url"
            size="md"
          />
          <div class="flex-1">
            <RouterLink
              :to="`/members/${profile.nemesis.player.id}`"
              class="font-medium text-brand-pink hover:underline"
            >
              {{ profile.nemesis.player.nickname }}
            </RouterLink>
            <p class="text-xs text-white/40">
              {{ t('profile.encountered') }} {{ profile.nemesis.encounters }} {{ t('profile.times') }} · {{ t('common.win') }}
              {{ profile.nemesis.wins }} · {{ t('common.loss') }} {{ profile.nemesis.losses }} · {{ t('common.draw') }}
              {{ profile.nemesis.draws }}
            </p>
          </div>
        </div>
      </section>
      <p v-else class="mt-8 text-center text-sm text-white/40">{{ t('profile.noNemesis') }}</p>

      <section v-if="profile.similar_players.length > 0" class="mt-8">
        <h2 class="text-xs font-semibold tracking-widest text-brand-pink/70 uppercase">
          {{ t('profile.similarLevel') }}
        </h2>
        <ul class="mt-3 flex flex-wrap gap-2">
          <li v-for="p in profile.similar_players" :key="p.id">
            <RouterLink
              :to="`/members/${p.id}`"
              class="hud-panel flex items-center gap-2 border border-brand-pink/20 bg-brand-surface px-3 py-1.5 hover:border-brand-pink/50"
            >
              <PlayerAvatar :name="p.nickname" :avatar-url="p.avatar_url" size="sm" />
              <span class="text-sm font-medium text-white/80">{{ p.nickname }}</span>
            </RouterLink>
          </li>
        </ul>
      </section>
    </template>
  </main>
</template>
