<script setup lang="ts">
// A marquee of member photos drifting leftward on the home page, each one a
// link to that member's profile. Swipeable by hand too; the drift and the
// loop live in useDriftStrip.
//
// Loads once rather than polling like the counter beside it — the roster
// changes when an admin adds a member, not during a session.
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getPlayers } from '@/api/public'
import type { Player } from '@/types'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'
import TierMascot from '@/components/players/TierMascot.vue'
import { useDriftStrip } from '@/composables/useDriftStrip'

const { t } = useI18n()

// A short roster would leave the track narrower than the strip and open a
// visible gap mid-loop, so the list repeats until there is enough to fill
// one half before the halves are doubled.
const MIN_ITEMS = 10
// In pixels per second, so the strip drifts at one readable pace no matter
// how wide an item turns out with its caption, or how big the roster is.
const PIXELS_PER_SECOND = 28

const players = ref<Player[]>([])
const strip = ref<HTMLElement | null>(null)
const { handlers } = useDriftStrip(strip, { speed: PIXELS_PER_SECOND })

const half = computed<Player[]>(() => {
  const roster = players.value
  if (roster.length === 0) return []
  const filled: Player[] = []
  while (filled.length < MIN_ITEMS) filled.push(...roster)
  return filled
})
const track = computed(() => [...half.value, ...half.value])

onMounted(async () => {
  try {
    // getPlayers returns each member wrapped in their stats; the strip
    // only needs the member.
    players.value = (await getPlayers()).map((stats) => stats.player)
  } catch {
    // Renders nothing. This sits above the banner as decoration with a
    // useful link in it — it must not put an error across the home page.
    return
  }
})
</script>

<template>
  <div
    v-if="track.length > 0"
    ref="strip"
    class="marquee min-w-0"
    v-on="handlers"
  >
    <ul class="flex w-max items-start gap-3">
      <li v-for="(player, i) in track" :key="`${player.id}-${i}`">
        <RouterLink
          :to="`/members/${player.id}`"
          class="flex flex-col items-center gap-1"
          :aria-label="player.nickname"
          :tabindex="i < half.length ? 0 : -1"
        >
          <PlayerAvatar :name="player.nickname" :avatar-url="player.avatar_url" size="md" round />
          <span class="flex items-center gap-1 text-xs leading-none whitespace-nowrap">
            <!-- Not interactive here: its interactive form is a <button>,
                 which cannot sit inside this link and would swallow the tap
                 that should open the member's profile. -->
            <TierMascot :tier="player.elo_level" :size="13" :interactive="false" />
            <span class="font-medium text-white/75">{{ player.nickname }}</span>
          </span>
        </RouterLink>
      </li>
    </ul>
    <span class="sr-only">{{ t('home.memberMarqueeLabel') }}</span>
  </div>
</template>

<style scoped>
.marquee {
  /* Scrollable by hand, with the bar itself hidden — the drifting content
     already says it moves, and a scrollbar under the photos would read as
     chrome on what is meant to be a quiet strip. */
  overflow-x: auto;
  scrollbar-width: none;
  /* Keeps a swipe that runs off the end of the strip from being handed to
     the page as a back-navigation gesture. */
  overscroll-behavior-x: contain;
  /* The drift writes scrollLeft every frame; smooth scrolling would try to
     animate each of those and fight it. */
  scroll-behavior: auto;
  /* Feathered ends so photos slide out of view instead of being chopped
     against a hard edge. */
  -webkit-mask-image: linear-gradient(to right, transparent, #000 10%, #000 90%, transparent);
  mask-image: linear-gradient(to right, transparent, #000 10%, #000 90%, transparent);
}

.marquee::-webkit-scrollbar {
  display: none;
}
</style>
