<script setup lang="ts">
// A marquee of member photos drifting leftward above the banner, each one a
// link to that member's profile.
//
// Built as two identical halves translated by -50%: when the first half has
// slid exactly its own width off to the left, the second is sitting where
// the first started, so the loop restarts on an indistinguishable frame and
// reads as endless.
//
// Loads once rather than polling like the counter beside it — the roster
// changes when an admin adds a member, not during a session.
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getPlayers } from '@/api/public'
import type { Player } from '@/types'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'

const { t } = useI18n()

// A short roster would leave the track narrower than the strip and open a
// visible gap mid-loop, so the list repeats until there is enough to fill
// one half before the halves are doubled.
const MIN_ITEMS = 10
// Per item rather than for the whole track, so the photos drift at the same
// speed whether the club has twelve members or ninety.
const SECONDS_PER_ITEM = 2.4

const players = ref<Player[]>([])

const half = computed<Player[]>(() => {
  const roster = players.value
  if (roster.length === 0) return []
  const filled: Player[] = []
  while (filled.length < MIN_ITEMS) filled.push(...roster)
  return filled
})
const track = computed(() => [...half.value, ...half.value])
const duration = computed(() => `${(half.value.length * SECONDS_PER_ITEM).toFixed(1)}s`)

onMounted(async () => {
  try {
    // getPlayers returns each member wrapped in their stats; the strip
    // only needs the member.
    players.value = (await getPlayers()).map((stats) => stats.player)
  } catch {
    // Renders nothing. This sits above the banner as decoration with a
    // useful link in it — it must not put an error across the home page.
  }
})
</script>

<template>
  <div v-if="track.length > 0" class="marquee min-w-0">
    <ul class="marquee-track flex w-max items-center gap-2" :style="{ '--marquee-duration': duration }">
      <li v-for="(player, i) in track" :key="`${player.id}-${i}`">
        <RouterLink
          :to="`/members/${player.id}`"
          class="block transition-opacity hover:opacity-100 focus-visible:opacity-100"
          :aria-label="player.nickname"
          :tabindex="i < half.length ? 0 : -1"
        >
          <PlayerAvatar :name="player.nickname" :avatar-url="player.avatar_url" size="md" />
        </RouterLink>
      </li>
    </ul>
    <span class="sr-only">{{ t('home.memberMarqueeLabel') }}</span>
  </div>
</template>

<style scoped>
.marquee {
  overflow: hidden;
  /* Feathered ends so photos slide out of view instead of being chopped
     against a hard edge. */
  -webkit-mask-image: linear-gradient(to right, transparent, #000 10%, #000 90%, transparent);
  mask-image: linear-gradient(to right, transparent, #000 10%, #000 90%, transparent);
}

.marquee-track {
  animation: marquee-drift var(--marquee-duration, 40s) linear infinite;
}

/* Hovering holds it still so a photo can actually be aimed at and clicked. */
.marquee:hover .marquee-track,
.marquee:focus-within .marquee-track {
  animation-play-state: paused;
}

@keyframes marquee-drift {
  from {
    transform: translateX(0);
  }
  to {
    transform: translateX(-50%);
  }
}

/* Same contract the rest of the site keeps (v-reveal, CountUp, the ambient
   blobs): no drifting motion when the reader has asked for less of it. The
   strip becomes an ordinary scrollable row instead of freezing on whichever
   faces happened to be visible. */
@media (prefers-reduced-motion: reduce) {
  .marquee {
    overflow-x: auto;
  }
  .marquee-track {
    animation: none;
  }
}
</style>
