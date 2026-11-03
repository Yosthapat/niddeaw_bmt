<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { getPlayerProfile } from '@/api/public'
import type { PlayerProfile } from '@/types'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'
import ProfileFlipCard from '@/components/players/ProfileFlipCard.vue'
import HudSkeletonBlock from '@/components/common/HudSkeletonBlock.vue'
import PageBanner from '@/components/common/PageBanner.vue'
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

const eyebrow = computed(() => (profile.value ? `Member · ${profile.value.player.member_code}` : 'Member'))
const bannerSub = computed(() => {
  const p = profile.value
  if (!p) return undefined
  const hand = p.player.dominant_hand
  return [
    `${t('profile.eloRank')} #${p.elo_rank} / ${p.total_ranked_players}`,
    hand ? (hand === 'left' ? t('profile.leftHanded') : t('profile.rightHanded')) : null,
  ]
    .filter(Boolean)
    .join(' · ')
})
</script>

<template>
  <main class="pb-12 sm:pb-20">
    <PageBanner :eyebrow="eyebrow" :title="profile?.player.nickname ?? t('nav.members')" :sub="bannerSub" mascot="/hero/cat-color.webp">
      <div class="flex flex-wrap items-center gap-2">
        <RouterLink to="/members" class="glass-pill"><span aria-hidden="true">←</span> {{ t('profile.backToMembers') }}</RouterLink>
        <span v-if="profile?.player.tiktok" class="glass-pill">TikTok {{ profile.player.tiktok }}</span>
        <span v-if="profile?.player.instagram" class="glass-pill">IG {{ profile.player.instagram }}</span>
      </div>
    </PageBanner>

    <div class="home-world">
      <div class="mx-auto max-w-[1100px] px-3 pt-5 sm:px-6 sm:pt-8">
        <div v-if="loading" class="grid gap-6 lg:grid-cols-[360px_minmax(0,1fr)]">
          <HudSkeletonBlock class="mx-auto aspect-[3/4.2] w-full max-w-[340px] rounded-[22px]" />
          <HudSkeletonBlock :delay="90" class="h-40 rounded-[22px]" />
        </div>
        <p v-else-if="error || !profile" class="world-card p-5 text-status-error">{{ error }}</p>

        <div v-else class="grid gap-6 lg:grid-cols-[360px_minmax(0,1fr)] lg:items-start lg:gap-8">
          <!-- the card stays in view on a desktop while the history scrolls -->
          <div v-reveal class="lg:sticky lg:top-[calc(var(--header-h)+16px)]">
            <div class="mx-auto max-w-[340px]">
              <ProfileFlipCard :profile="profile" />
            </div>
            <p v-if="profile.player.quote" class="mx-auto mt-4 max-w-xs text-center text-sm text-white/65 italic">
              "{{ profile.player.quote }}"
            </p>
            <div class="mx-auto mt-4 flex max-w-[340px] gap-2">
              <button type="button" class="glass-pill flex-1 justify-center" @click="toMatches">
                {{ t('card.matchHistory') }}
              </button>
              <button type="button" class="tap flex-1 rounded-full bg-gradient-to-b from-[#ff8fd0] to-[#ea4ca4] px-4 text-sm font-semibold text-[#1a0410] shadow-[0_4px_14px_rgb(234_76_164/0.5)]" @click="share">
                {{ shared ? t('card.copied') : t('card.share') }}
              </button>
            </div>
          </div>

          <div class="min-w-0">
            <dl v-reveal="1" class="grid grid-cols-3 gap-2.5 sm:grid-cols-6">
              <div class="tile world-card">
                <dt>{{ t('common.game') }}</dt>
                <dd><CountUp :value="profile.games" /></dd>
              </div>
              <div class="tile world-card">
                <dt>{{ t('common.win') }}</dt>
                <dd class="text-status-success"><CountUp :value="profile.wins" /></dd>
              </div>
              <div class="tile world-card">
                <dt>{{ t('common.draw') }}</dt>
                <dd class="text-white/75"><CountUp :value="profile.draws" /></dd>
              </div>
              <div class="tile world-card">
                <dt>{{ t('common.loss') }}</dt>
                <dd class="text-status-error"><CountUp :value="profile.losses" /></dd>
              </div>
              <div class="tile world-card !border-brand-pink/45">
                <dt>Pts</dt>
                <dd class="text-brand-pink-light"><CountUp :value="profile.points" /></dd>
              </div>
              <div class="tile world-card">
                <dt>{{ t('common.scorePercent') }}</dt>
                <dd>{{ profile.score_percent.toFixed(1) }}</dd>
              </div>
            </dl>

            <!-- Keyed on the player id: this view swaps profiles by watching the
                 route param without remounting, so without a key these two would
                 keep the previous member's polled state and match pages. -->
            <PlayerLiveStatus :key="`live-${profile.player.id}`" :player-id="profile.player.id" />

            <section v-if="profile.nemesis" v-reveal="2" class="world-card mt-6 p-5">
              <p class="world-eyebrow">NEMESIS</p>
              <h2 class="world-title mt-1 text-lg">{{ t('profile.nemesis') }}</h2>
              <RouterLink :to="`/members/${profile.nemesis.player.id}`" class="mt-3 flex items-center gap-3 rounded-2xl hover:bg-white/5">
                <PlayerAvatar :name="profile.nemesis.player.nickname" :avatar-url="profile.nemesis.player.avatar_url" size="md" round />
                <div class="min-w-0 flex-1">
                  <p class="truncate font-display font-bold text-brand-pink-light">{{ profile.nemesis.player.nickname }}</p>
                  <p class="text-xs text-white/55">
                    {{ t('profile.encountered') }} {{ profile.nemesis.encounters }} {{ t('profile.times') }} · {{ t('common.win') }}
                    {{ profile.nemesis.wins }} · {{ t('common.loss') }} {{ profile.nemesis.losses }} · {{ t('common.draw') }}
                    {{ profile.nemesis.draws }}
                  </p>
                </div>
              </RouterLink>
            </section>
            <p v-else class="world-card mt-6 p-5 text-center text-sm text-white/55">{{ t('profile.noNemesis') }}</p>

            <section v-if="profile.similar_players.length > 0" class="mt-6">
              <p class="world-eyebrow">SAME LEVEL</p>
              <h2 class="world-title mt-1 text-lg">{{ t('profile.similarLevel') }}</h2>
              <ul class="mt-3 flex flex-wrap gap-2">
                <li v-for="p in profile.similar_players" :key="p.id">
                  <RouterLink :to="`/members/${p.id}`" class="glass-pill !pl-1.5">
                    <PlayerAvatar :name="p.nickname" :avatar-url="p.avatar_url" size="sm" round />
                    <span class="font-medium">{{ p.nickname }}</span>
                  </RouterLink>
                </li>
              </ul>
            </section>

            <PlayerShopOrders :player-id="profile.player.id" />

            <div ref="matchesAnchor" class="scroll-mt-24">
              <PlayerSeasonMatches :key="`seasons-${profile.player.id}`" :player-id="profile.player.id" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.tile {
  display: flex;
  flex-direction: column-reverse;
  align-items: center;
  gap: 2px;
  padding: 12px 6px;
  border-radius: 18px;
  text-align: center;
}
.tile dt {
  font-size: 11px;
  letter-spacing: 0.06em;
  color: rgb(255 255 255 / 0.55);
  text-transform: uppercase;
}
.tile dd {
  margin: 0;
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 700;
}
</style>
