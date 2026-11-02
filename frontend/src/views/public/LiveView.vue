<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getLiveStatus, getPlayers } from '@/api/public'
import type { LiveQueueResponse, Player } from '@/types'
import { usePolling } from '@/composables/usePolling'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'
import HudSkeletonBlock from '@/components/common/HudSkeletonBlock.vue'
import PageBanner from '@/components/common/PageBanner.vue'
import { useGameNight } from '@/composables/useGameNight'
import { formatDayMonth } from '@/utils/format'

const { t, locale } = useI18n()

const live = ref<LiveQueueResponse | null>(null)
const playersById = ref<Record<string, Player>>({})
const loading = ref(true)
const error = ref<string | null>(null)

function nameOf(playerId: string): string {
  return playersById.value[playerId]?.nickname ?? '?'
}

function avatarOf(playerId: string): string | undefined {
  return playersById.value[playerId]?.avatar_url ?? undefined
}

async function refresh(): Promise<void> {
  try {
    live.value = await getLiveStatus()
    error.value = null
  } catch {
    // Only surface the error screen on the initial load. Once we have
    // data on screen, a single failed poll (e.g. a cold-starting free-tier
    // backend) shouldn't wipe out an already-successful view — just keep
    // showing the last-known-good state and let the next poll retry.
    if (!live.value) {
      error.value = t('live.loadError')
    }
  } finally {
    loading.value = false
  }
}

async function loadPlayers(): Promise<void> {
  try {
    const stats = await getPlayers()
    playersById.value = Object.fromEntries(stats.map((s) => [s.player.id, s.player]))
  } catch {
    // Names/avatars just fall back to "?" (see nameOf/avatarOf) — refresh()
    // below still drives the loading/error state for the page as a whole.
  }
}

function formatSessionDate(isoDate: string): string {
  return formatDayMonth(isoDate, locale.value)
}

const { night, countdown, startsAt } = useGameNight()

const teamNames = (ids: string[]): string => ids.map(nameOf).join(' & ')
const eyebrow = computed(() =>
  live.value?.session_date ? `Live · ${formatSessionDate(live.value.session_date)}` : 'Live',
)

onMounted(loadPlayers)
usePolling(refresh, 7000)
</script>

<template>
  <main class="pb-12 sm:pb-20">
    <PageBanner
      :eyebrow="eyebrow"
      :title="t('live.title')"
      :sub="live?.session_id ? [live.location, t('live.autoRefresh')].filter(Boolean).join(' · ') : t('live.sub')"
      mascot="/tiers/soju.webp"
      :live="!!live?.session_id"
    >
      <!-- the night at a glance -->
      <dl v-if="live?.session_id" class="flex gap-2.5">
        <div class="count-chip">
          <dd class="text-brand-pink-light">{{ live.in_progress.length }}</dd>
          <dt>{{ t('live.onCourt') }}</dt>
        </div>
        <div class="count-chip">
          <dd>{{ live.queued.length }}</dd>
          <dt>{{ t('live.upNext') }}</dt>
        </div>
        <div class="count-chip">
          <dd>{{ live.waiting.length }}</dd>
          <dt>{{ t('live.inQueue') }}</dt>
        </div>
      </dl>
    </PageBanner>

    <div class="home-world">
      <div class="mx-auto max-w-[1200px] px-3 pt-4 sm:px-6 sm:pt-7">
        <div v-if="loading" class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <HudSkeletonBlock v-for="i in 3" :key="i" :delay="i * 90" class="h-44 rounded-[22px]" />
        </div>
        <p v-else-if="error" class="world-card p-5 text-status-error">{{ error }}</p>

        <!-- no session: when the next one is -->
        <section v-else-if="!live?.session_id" v-reveal class="world-card p-6 text-center sm:p-9">
          <template v-if="night.on">
            <p class="world-eyebrow">TONIGHT</p>
            <h2 class="world-title mt-1 text-3xl sm:text-4xl">{{ t('home.big.onTonight') }}</h2>
            <p class="mt-2 text-white/70">{{ t('live.waitingForSession') }}</p>
          </template>
          <template v-else>
            <p class="world-eyebrow">NEXT GAME NIGHT</p>
            <h2 class="world-title mt-1 text-3xl sm:text-4xl">{{ startsAt }}</h2>
            <p class="mt-2 text-white/70">{{ t('live.noSessionLong') }}</p>
            <div class="mt-6 flex justify-center gap-2 sm:gap-3.5" role="timer" :aria-label="t('home.big.countdownLabel')">
              <div v-for="part in countdown" :key="part.unit" class="count">
                <span class="font-display text-[30px] leading-none font-bold text-[#ff9fd6] tabular-nums sm:text-[44px]">{{ part.n }}</span>
                <span class="mt-1.5 text-xs text-white/60">{{ part.unit }}</span>
              </div>
            </div>
          </template>
          <p class="mt-6 text-sm text-white/55">{{ t('home.hero.when') }}</p>
        </section>

        <template v-else>
          <!-- on court: each one drawn as a neon court, a team on each half -->
          <ul v-if="live.in_progress.length" class="grid gap-3 sm:grid-cols-2 sm:gap-5 lg:grid-cols-3">
            <li v-for="(m, i) in live.in_progress" :key="m.match_id" v-reveal="i" class="court">
              <div class="mb-3 flex items-center justify-between gap-2">
                <span class="flex items-center gap-2 font-display text-lg font-bold">
                  <span class="live-dot" aria-hidden="true" />
                  {{ m.court ? t('home.live.court', { court: m.court }) : t('live.playing') }}
                </span>
                <span v-if="typeof m.match_no === 'number'" class="text-xs text-white/60">{{ t('home.big.matchNo', { n: m.match_no }) }}</span>
              </div>
              <div class="pitch">
                <div v-for="side in [m.team1_player_ids, m.team2_player_ids]" :key="side.join()" class="side">
                  <div class="flex">
                    <PlayerAvatar
                      v-for="(pid, k) in side"
                      :key="pid"
                      :name="nameOf(pid)"
                      :avatar-url="avatarOf(pid)"
                      size="lg"
                      round
                      :class="k > 0 ? '-ml-3' : ''"
                    />
                  </div>
                  <span class="max-w-full text-center font-display text-sm font-semibold break-words sm:text-[15px]">{{ teamNames(side) }}</span>
                </div>
              </div>
            </li>
          </ul>
          <p v-else class="world-card p-5 text-white/65">{{ t('live.noneInProgress') }}</p>

          <div class="mt-3 grid items-start gap-3 sm:mt-5 sm:gap-5 lg:grid-cols-[1.2fr_1fr]">
            <section v-reveal class="world-card p-4 sm:p-5" aria-labelledby="live-next">
              <h2 id="live-next" class="font-display text-xl font-bold">
                {{ t('live.upNext') }} <span class="text-sm font-normal text-white/55">({{ live.queued.length }})</span>
              </h2>
              <ol v-if="live.queued.length" class="mt-3 space-y-2">
                <li v-for="(m, i) in live.queued" :key="m.match_id" class="queue-row">
                  <span class="num">{{ i + 1 }}</span>
                  <!-- faces then names, mirrored on the right so both teams
                       face the VS; on a phone the names drop under the faces -->
                  <span v-for="(ids, k) in [m.team1_player_ids, m.team2_player_ids]" :key="k" class="q-team" :class="k === 0 ? 'q-left' : 'q-right'">
                    <span class="flex shrink-0">
                      <PlayerAvatar
                        v-for="(pid, j) in ids"
                        :key="pid"
                        :name="nameOf(pid)"
                        :avatar-url="avatarOf(pid)"
                        size="sm"
                        round
                        :class="j > 0 ? '-ml-2' : ''"
                      />
                    </span>
                    <span class="min-w-0 max-w-full truncate text-sm">{{ teamNames(ids) }}</span>
                  </span>
                </li>
              </ol>
              <p v-else class="mt-2 text-sm text-white/55">{{ t('live.noneUpNext') }}</p>
            </section>

            <section v-reveal class="world-card p-4 sm:p-5" aria-labelledby="live-waiting">
              <h2 id="live-waiting" class="font-display text-xl font-bold">
                {{ t('live.inQueue') }} <span class="text-sm font-normal text-white/55">({{ live.waiting.length }})</span>
              </h2>
              <ul v-if="live.waiting.length" class="mt-3 flex flex-wrap gap-2">
                <li v-for="w in live.waiting" :key="w.player_id" class="wait-chip">
                  <PlayerAvatar :name="nameOf(w.player_id)" :avatar-url="avatarOf(w.player_id)" size="sm" round />
                  {{ nameOf(w.player_id) }}
                </li>
              </ul>
              <p v-else class="mt-2 text-sm text-white/55">{{ t('live.noneWaiting') }}</p>
            </section>
          </div>
        </template>
      </div>
    </div>
  </main>
</template>

<style scoped>
.count-chip {
  display: flex;
  min-width: 76px;
  flex-direction: column-reverse;
  align-items: center;
  padding: 8px 14px;
  border: 1px solid rgb(255 255 255 / 0.16);
  border-radius: 16px;
  background: rgb(255 255 255 / 0.08);
  -webkit-backdrop-filter: blur(12px);
  backdrop-filter: blur(12px);
}
.count-chip dd {
  margin: 0;
  font-family: var(--font-display);
  font-size: 24px;
  font-weight: 700;
  line-height: 1;
}
.count-chip dt {
  margin-top: 4px;
  font-size: 12px;
  color: rgb(255 255 255 / 0.65);
}
.count {
  display: flex;
  width: 74px;
  flex-direction: column;
  align-items: center;
  padding: 14px 0;
  border: 1px solid rgb(255 255 255 / 0.14);
  border-radius: 18px;
  background: rgb(255 255 255 / 0.07);
}
@media (min-width: 640px) {
  .count {
    width: 110px;
  }
}
.court {
  padding: 16px;
  border: 1px solid rgb(255 108 192 / 0.35);
  border-radius: 22px;
  background:
    linear-gradient(160deg, rgb(255 255 255 / 0.1), rgb(255 255 255 / 0.02)),
    rgb(30 12 56 / 0.8);
  box-shadow:
    inset 0 1px 1px rgb(255 255 255 / 0.25),
    0 22px 44px -20px rgb(234 76 164 / 0.6);
}
/* a badminton court seen from above: the net down the middle, a team on
   each side of it */
.pitch {
  position: relative;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  padding: 16px 10px;
  border: 2px solid rgb(255 160 220 / 0.55);
  border-radius: 12px;
  background: linear-gradient(90deg, rgb(234 76 164 / 0.12), rgb(142 76 240 / 0.12));
  box-shadow: inset 0 0 30px rgb(234 76 164 / 0.25);
}
.pitch::before {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: 50%;
  border-left: 3px dashed rgb(255 255 255 / 0.7);
  filter: drop-shadow(0 0 6px rgb(255 255 255 / 0.6));
}
.pitch::after {
  content: '';
  position: absolute;
  inset: 18% 10%;
  border: 1.5px solid rgb(255 160 220 / 0.3);
  border-radius: 4px;
  pointer-events: none;
}
.side {
  position: relative;
  z-index: 1;
  display: flex;
  min-width: 0;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.live-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #ff5078;
  animation: live-pulse 1.6s infinite;
}
@keyframes live-pulse {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgb(255 80 120 / 0.7);
  }
  50% {
    box-shadow: 0 0 0 7px rgb(255 80 120 / 0);
  }
}
.queue-row {
  position: relative;
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr) 26px minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  min-height: 56px;
  padding: 8px 12px;
  border: 1px solid rgb(255 255 255 / 0.1);
  border-radius: 14px;
  background: rgb(255 255 255 / 0.05);
}
.queue-row::after {
  content: 'VS';
  grid-row: 1;
  grid-column: 3;
  text-align: center;
  font-family: var(--font-display);
  font-size: 11px;
  font-weight: 700;
  color: #ff9fd6;
}
.q-team {
  display: flex;
  min-width: 0;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  grid-row: 1;
}
.q-left {
  grid-column: 2;
}
.q-right {
  grid-column: 4;
}
@media (min-width: 640px) {
  .q-team {
    flex-direction: row;
    gap: 8px;
  }
  .q-left {
    flex-direction: row-reverse;
    justify-content: flex-start;
  }
}
.num {
  display: flex;
  width: 30px;
  height: 30px;
  align-items: center;
  justify-content: center;
  border: 1px solid rgb(255 108 192 / 0.4);
  border-radius: 10px;
  background: rgb(234 76 164 / 0.2);
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 700;
  color: #ff9fd6;
}
.wait-chip {
  display: inline-flex;
  min-height: 40px;
  align-items: center;
  gap: 8px;
  padding: 4px 12px 4px 4px;
  border: 1px solid rgb(255 255 255 / 0.14);
  border-radius: 999px;
  background: rgb(255 255 255 / 0.07);
  font-size: 13px;
}
@media (prefers-reduced-motion: reduce) {
  .live-dot {
    animation: none;
  }
}
</style>
