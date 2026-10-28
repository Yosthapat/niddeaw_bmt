<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { getPlayerProfile } from '@/api/public'
import type { PlayerProfile } from '@/types'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'
import ProfileFlipCard from '@/components/players/ProfileFlipCard.vue'
import HudSkeletonBlock from '@/components/common/HudSkeletonBlock.vue'
import CountUp from '@/components/common/CountUp.vue'
import PlayerLiveStatus from '@/components/players/PlayerLiveStatus.vue'
import PlayerSeasonMatches from '@/components/players/PlayerSeasonMatches.vue'
import PlayerShopOrders from '@/components/shop/PlayerShopOrders.vue'

const route = useRoute()
const { t } = useI18n()
const profile = ref<PlayerProfile | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const matchesAnchor = ref<HTMLElement | null>(null)
const shared = ref(false)

function toMatches(): void {
  matchesAnchor.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

// The phone's own share sheet where there is one (LINE, Messenger...);
// otherwise the link goes on the clipboard and the button says so.
async function share(): Promise<void> {
  const url = window.location.href
  const title = profile.value?.player.nickname ?? document.title
  try {
    if (navigator.share) {
      await navigator.share({ title, url })
      return
    }
    await navigator.clipboard.writeText(url)
    shared.value = true
    setTimeout(() => (shared.value = false), 2000)
  } catch {
    // the share sheet was dismissed, or the clipboard refused — nothing to say
  }
}

// Watches the param instead of onMounted so this also works if Vue ever
// reuses the component instance across two /members/:id URLs (both match
// the same route record, so onMounted alone wouldn't re-fire). App.vue's
// route-transition currently keys on the full path, which happens to force
// a remount on every navigation too — but don't rely on that holding.
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

    <div v-if="loading" class="mt-6 space-y-3">
      <HudSkeletonBlock class="mx-auto h-44 w-44 sm:h-60 sm:w-60" />
      <HudSkeletonBlock :delay="90" class="h-24" />
    </div>
    <p v-else-if="error || !profile" class="mt-6 text-status-error">{{ error }}</p>

    <template v-else>
      <div v-reveal class="mt-6">
        <ProfileFlipCard :profile="profile" />
        <p v-if="profile.player.quote" class="mx-auto mt-4 max-w-xs text-center text-sm text-white/55 italic">
          "{{ profile.player.quote }}"
        </p>
        <div class="mt-3 flex flex-wrap items-center justify-center gap-1.5 text-xs text-white/60">
          <span>{{ t('profile.eloRank') }} <span class="font-semibold text-brand-pink">#{{ profile.elo_rank }}</span> / {{ profile.total_ranked_players }}</span>
          <template v-if="profile.player.dominant_hand">
            <span aria-hidden="true">·</span>
            <span>{{ profile.player.dominant_hand === 'left' ? t('profile.leftHanded') : t('profile.rightHanded') }}</span>
          </template>
          <span v-if="profile.player.tiktok" class="hud-panel glass-panel border border-brand-pink/20 px-2.5 py-1">TikTok {{ profile.player.tiktok }}</span>
          <span v-if="profile.player.instagram" class="hud-panel glass-panel border border-brand-pink/20 px-2.5 py-1">IG {{ profile.player.instagram }}</span>
        </div>
        <div class="mx-auto mt-4 flex max-w-xs gap-2">
          <button type="button" class="tap flex-1 rounded-full border border-white/20 px-4 text-sm text-white/80" @click="toMatches">
            {{ t('card.matchHistory') }}
          </button>
          <button type="button" class="tap flex-1 rounded-full bg-brand-pink px-4 text-sm font-semibold text-brand-black" @click="share">
            {{ shared ? t('card.copied') : t('card.share') }}
          </button>
        </div>
      </div>

      <!-- Keyed on the player id: this view swaps profiles by watching the
           route param without remounting, so without a key these two would
           keep the previous member's polled state and match pages. -->
      <PlayerLiveStatus :key="`live-${profile.player.id}`" :player-id="profile.player.id" />

      <div v-reveal="1" class="mt-8 grid grid-cols-3 gap-2.5 sm:grid-cols-6">
        <div class="hud-panel glass-panel border border-brand-pink/20 p-3 text-center">
          <p class="text-xs tracking-wide text-white/40 uppercase">{{ t('common.game') }}</p>
          <p class="mt-1 font-display text-xl font-bold"><CountUp :value="profile.games" /></p>
        </div>
        <div class="hud-panel glass-panel border border-brand-pink/20 p-3 text-center">
          <p class="text-xs tracking-wide text-white/40 uppercase">{{ t('common.win') }}</p>
          <p class="mt-1 font-display text-xl font-bold text-status-success"><CountUp :value="profile.wins" /></p>
        </div>
        <div class="hud-panel glass-panel border border-brand-pink/20 p-3 text-center">
          <p class="text-xs tracking-wide text-white/40 uppercase">{{ t('common.draw') }}</p>
          <p class="mt-1 font-display text-xl font-bold text-white/70"><CountUp :value="profile.draws" /></p>
        </div>
        <div class="hud-panel glass-panel border border-brand-pink/20 p-3 text-center">
          <p class="text-xs tracking-wide text-white/40 uppercase">{{ t('common.loss') }}</p>
          <p class="mt-1 font-display text-xl font-bold text-status-error"><CountUp :value="profile.losses" /></p>
        </div>
        <div class="hud-panel glass-panel border border-brand-pink/40 p-3 text-center">
          <p class="text-xs tracking-wide text-white/40 uppercase">Pts</p>
          <p class="mt-1 font-display text-xl font-bold text-brand-pink"><CountUp :value="profile.points" /></p>
        </div>
        <div class="hud-panel glass-panel border border-brand-pink/20 p-3 text-center">
          <p class="text-xs tracking-wide text-white/40 uppercase">{{ t('common.scorePercent') }}</p>
          <p class="mt-1 font-display text-xl font-bold">{{ profile.score_percent.toFixed(1) }}</p>
        </div>
      </div>

      <section v-if="profile.nemesis" v-reveal="2" class="hud-panel glass-panel mt-8 border border-brand-pink/20 p-4">
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
              class="hud-panel glass-panel hud-hover flex items-center gap-2 border border-brand-pink/20 px-3 py-1.5 hover:border-brand-pink/50"
            >
              <PlayerAvatar :name="p.nickname" :avatar-url="p.avatar_url" size="sm" />
              <span class="text-sm font-medium text-white/80">{{ p.nickname }}</span>
            </RouterLink>
          </li>
        </ul>
      </section>

      <PlayerShopOrders :player-id="profile.player.id" />

      <div ref="matchesAnchor" class="scroll-mt-24">
        <PlayerSeasonMatches :key="`seasons-${profile.player.id}`" :player-id="profile.player.id" />
      </div>
    </template>
  </main>
</template>
