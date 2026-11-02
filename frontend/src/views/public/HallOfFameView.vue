<script setup lang="ts">
// The club's legends: everyone with at least five games, best first. The
// first stands alone in a big gold card with a crown; the rest hang on a
// wall of trading cards — a big photo, the tier, three numbers — that tilt
// under the pointer like the members page's cards.
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { getHallOfFame } from '@/api/public'
import type { PlayerStats } from '@/types'
import EloBadge from '@/components/players/EloBadge.vue'
import TierMascot from '@/components/players/TierMascot.vue'
import HudSkeletonBlock from '@/components/common/HudSkeletonBlock.vue'
import CountUp from '@/components/common/CountUp.vue'
import PageBanner from '@/components/common/PageBanner.vue'

const { t } = useI18n()

const stats = ref<PlayerStats[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    stats.value = await getHallOfFame()
  } catch {
    error.value = t('hallOfFame.loadError')
  } finally {
    loading.value = false
  }
})

const champ = computed(() => stats.value[0] ?? null)
const wall = computed(() => stats.value.slice(1))

// Second and third keep their medal colour on the wall.
const MEDAL: Record<number, string> = { 2: '#d9dde8', 3: '#e39a6a' }
const pct = (s: PlayerStats): number => Math.round(s.score_percent)
</script>

<template>
  <main class="pb-12 sm:pb-20">
    <PageBanner eyebrow="Legends" title="Hall of Fame" :sub="t('hallOfFame.subtitle')" mascot="/tiers/absinthe.webp" />

    <div class="home-world">
      <div class="mx-auto max-w-[1200px] px-3 pt-6 sm:px-6 sm:pt-10">
        <div v-if="loading" class="space-y-4">
          <HudSkeletonBlock class="h-56 rounded-[22px]" />
          <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            <HudSkeletonBlock v-for="i in 4" :key="i" :delay="i * 80" class="h-72 rounded-[22px]" />
          </div>
        </div>
        <p v-else-if="error" class="world-card p-5 text-status-error">{{ error }}</p>
        <p v-else-if="!champ" class="world-card p-5 text-white/65">{{ t('hallOfFame.empty') }}</p>

        <template v-else>
          <!-- #1 -->
          <RouterLink
            v-reveal
            :to="`/members/${champ.player.id}`"
            class="legend champ grid grid-cols-[112px_minmax(0,1fr)] items-center gap-4 p-4 sm:grid-cols-[220px_minmax(0,1fr)] sm:gap-8 sm:p-6"
          >
            <div class="relative mt-4 sm:mt-6">
              <div class="photo champ-photo">
                <img v-if="champ.player.avatar_url" :src="champ.player.avatar_url" :alt="champ.player.nickname" class="h-full w-full object-cover" />
                <span v-else>{{ champ.player.nickname.slice(0, 1) }}</span>
              </div>
              <span class="crown" aria-hidden="true">👑</span>
            </div>
            <div class="min-w-0">
              <p class="world-eyebrow !text-[#ffd34d]">{{ t('hallOfFame.champion') }}</p>
              <h2 class="champ-name mt-1 truncate font-display font-bold">{{ champ.player.nickname }}</h2>
              <span class="tier-chip mt-2.5">
                <TierMascot :tier="champ.player.elo_level" :size="24" :interactive="false" />
                <EloBadge :elo-score="champ.player.elo_score" show-score />
              </span>
              <dl class="stats mt-3 sm:mt-5">
                <div><dt>{{ t('common.game') }}</dt><dd><CountUp :value="champ.games" /></dd></div>
                <div><dt>{{ t('common.points') }}</dt><dd class="text-brand-pink-light"><CountUp :value="champ.points" /></dd></div>
                <div><dt>{{ t('common.win') }}</dt><dd><CountUp :value="champ.wins" /></dd></div>
                <div><dt>Score</dt><dd><CountUp :value="pct(champ)" />%</dd></div>
              </dl>
            </div>
          </RouterLink>

          <!-- everyone else -->
          <ol v-if="wall.length" class="mt-4 grid grid-cols-2 gap-3 sm:mt-6 sm:grid-cols-3 sm:gap-5 lg:grid-cols-4">
            <li v-for="(s, i) in wall" :key="s.player.id" v-reveal="i">
              <RouterLink
                v-tilt
                :to="`/members/${s.player.id}`"
                class="legend flex h-full flex-col p-3 sm:p-3.5"
                :style="MEDAL[i + 2] ? { borderColor: `${MEDAL[i + 2]}99`, '--glow': `${MEDAL[i + 2]}88` } : undefined"
              >
                <div class="relative">
                  <div class="photo">
                    <img v-if="s.player.avatar_url" :src="s.player.avatar_url" :alt="s.player.nickname" loading="lazy" class="h-full w-full object-cover" />
                    <span v-else>{{ s.player.nickname.slice(0, 1) }}</span>
                  </div>
                  <span class="badge" :style="MEDAL[i + 2] ? { color: MEDAL[i + 2] } : undefined">#{{ i + 2 }}</span>
                  <span class="absolute right-1.5 bottom-1.5 drop-shadow-[0_6px_10px_rgb(6_0_20/0.6)]">
                    <TierMascot :tier="s.player.elo_level" :size="40" :interactive="false" />
                  </span>
                </div>
                <h3 class="mt-2.5 truncate font-display text-base font-bold sm:text-lg">{{ s.player.nickname }}</h3>
                <EloBadge :elo-score="s.player.elo_score" show-score class="mt-0.5" />
                <dl class="mini mt-auto pt-2.5">
                  <div><dt>{{ t('common.game') }}</dt><dd>{{ s.games }}</dd></div>
                  <div><dt>{{ t('common.points') }}</dt><dd class="text-brand-pink-light">{{ s.points }}</dd></div>
                  <div><dt>Score</dt><dd>{{ pct(s) }}%</dd></div>
                </dl>
              </RouterLink>
            </li>
          </ol>
        </template>
      </div>
    </div>
  </main>
</template>

<style scoped>
.legend {
  --glow: rgb(234 76 164 / 0.5);
  position: relative;
  overflow: hidden;
  border: 1px solid rgb(255 255 255 / 0.16);
  border-radius: 22px;
  background:
    linear-gradient(160deg, rgb(255 255 255 / 0.14), rgb(255 255 255 / 0.03) 55%),
    rgb(30 12 56 / 0.75);
  box-shadow:
    inset 0 1px 1px rgb(255 255 255 / 0.3),
    0 18px 36px -18px var(--glow),
    0 10px 24px rgb(6 0 20 / 0.5);
}
/* a sheen that sweeps across the card on hover, like foil */
.legend::before {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 1;
  background: linear-gradient(115deg, transparent 35%, rgb(255 255 255 / 0.16) 48%, transparent 60%);
  transform: translateX(-70%);
  transition: transform 0.7s;
  pointer-events: none;
}
.legend:hover::before {
  transform: translateX(70%);
}
.champ {
  --glow: rgb(255 211 77 / 0.6);
  overflow: visible;
  border-color: rgb(255 211 77 / 0.55);
  transition: transform 0.25s;
}
/* The crown pokes out above the card, so the card can't clip — and an
   unclipped sheen would sweep across the page instead of the card. */
.champ::before {
  display: none;
}
.champ:hover {
  transform: translateY(-3px);
}
.photo {
  display: flex;
  aspect-ratio: 4 / 5;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 14px;
  background:
    radial-gradient(80% 60% at 50% 30%, rgb(255 255 255 / 0.16), transparent),
    linear-gradient(160deg, #4a2470, #1c0e33);
  font-family: var(--font-display);
  font-size: 44px;
  font-weight: 700;
  color: #ffb3dd;
}
.champ-photo {
  font-size: 56px;
  box-shadow:
    0 0 0 3px #ffd34d,
    0 0 40px rgb(255 211 77 / 0.45);
}
.crown {
  position: absolute;
  top: -26px;
  left: 50%;
  font-size: 36px;
  transform: translateX(-50%) rotate(-8deg);
  filter: drop-shadow(0 6px 10px rgb(255 211 77 / 0.5));
}
.champ-name {
  font-size: 30px;
  line-height: 1.05;
  text-shadow: 0 0 20px rgb(255 211 77 / 0.45);
}
.badge {
  position: absolute;
  top: 8px;
  left: 8px;
  display: flex;
  min-width: 34px;
  height: 34px;
  align-items: center;
  justify-content: center;
  padding: 0 9px;
  border: 1px solid rgb(255 255 255 / 0.25);
  border-radius: 999px;
  background: rgb(10 4 22 / 0.75);
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 700;
}
.tier-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 30px;
  padding: 0 10px 0 4px;
  border: 1px solid rgb(255 255 255 / 0.14);
  border-radius: 999px;
  background: rgb(255 255 255 / 0.07);
}
.stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px;
  padding: 10px;
  border: 1px solid rgb(255 255 255 / 0.12);
  border-radius: 16px;
  background: rgb(255 255 255 / 0.06);
  text-align: center;
}
.stats dd,
.mini dd {
  margin: 0;
  font-family: var(--font-display);
  font-weight: 700;
}
.stats dd {
  font-size: 18px;
}
.stats dt,
.mini dt {
  font-size: 11px;
  color: rgb(255 255 255 / 0.55);
}
.stats div,
.mini div {
  display: flex;
  flex-direction: column-reverse;
  align-items: center;
}
.mini {
  display: flex;
  justify-content: space-between;
  border-top: 1px solid rgb(255 255 255 / 0.1);
}
.mini dd {
  font-size: 15px;
}
@media (min-width: 640px) {
  .champ-photo {
    font-size: 80px;
  }
  .crown {
    top: -36px;
    font-size: 52px;
  }
  .champ-name {
    font-size: 48px;
  }
  .stats dd {
    font-size: 22px;
  }
  .mini dd {
    font-size: 17px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .legend::before {
    display: none;
  }
  .champ {
    transition: none;
  }
}
</style>
