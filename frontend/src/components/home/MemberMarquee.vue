<script setup lang="ts">
// A marquee of member photos drifting leftward above the banner, each one a
// link to that member's profile.
//
// Driven by scrollLeft rather than a CSS transform, because the strip is
// also swipeable by hand: both the drift and the finger write the same
// value, so they compose instead of fighting. A transform animation would
// keep sliding the content out from under the reader's thumb.
//
// Built as two identical halves. Once scrollLeft passes the width of the
// first half, subtracting that width lands on the identical pixel of the
// second, so the loop is seamless and the strip never runs out.
//
// Loads once rather than polling like the counter beside it — the roster
// changes when an admin adds a member, not during a session.
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getPlayers } from '@/api/public'
import type { Player } from '@/types'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'
import TierMascot from '@/components/players/TierMascot.vue'

const { t } = useI18n()

// A short roster would leave the track narrower than the strip and open a
// visible gap mid-loop, so the list repeats until there is enough to fill
// one half before the halves are doubled.
const MIN_ITEMS = 10
// In pixels per second, so the strip drifts at one readable pace no matter
// how wide an item turns out with its caption, or how big the roster is.
const PIXELS_PER_SECOND = 28
// How long the drift stays out of the way after the reader last touched it.
const RESUME_AFTER_MS = 1500

const players = ref<Player[]>([])
const strip = ref<HTMLElement | null>(null)
const paused = ref(false)

const half = computed<Player[]>(() => {
  const roster = players.value
  if (roster.length === 0) return []
  const filled: Player[] = []
  while (filled.length < MIN_ITEMS) filled.push(...roster)
  return filled
})
const track = computed(() => [...half.value, ...half.value])

let frame = 0
let lastTime = 0
let interactingUntil = 0
// The drift's own position, kept as a float. Assigning sub-pixel deltas
// straight to scrollLeft loses them to rounding — at this speed that is
// ~0.45px a frame, and the strip creeps by a pixel or two a second instead
// of drifting.
let position = 0
// Whether the last frame was the drift's. When it wasn't, position is
// re-read from the element so the drift carries on from wherever the
// reader left the strip rather than snapping back to its own idea of it.
let driving = false

/** Wraps scrollLeft back by one half whenever it runs past it. Runs for the
 * finger as well as the drift, so swiping never hits the end of the track. */
function wrap(el: HTMLElement): void {
  const halfWidth = el.scrollWidth / 2
  if (halfWidth > 0 && el.scrollLeft >= halfWidth) el.scrollLeft -= halfWidth
}

function step(now: number): void {
  const el = strip.value
  if (!el) return
  const elapsed = lastTime === 0 ? 0 : now - lastTime
  lastTime = now
  // Clamped: a backgrounded tab resumes with a huge delta that would
  // teleport the strip instead of continuing it.
  const dt = Math.min(elapsed, 100) / 1000
  if (!paused.value && now >= interactingUntil) {
    if (!driving) {
      position = el.scrollLeft
      driving = true
    }
    position += PIXELS_PER_SECOND * dt
    const halfWidth = el.scrollWidth / 2
    if (halfWidth > 0 && position >= halfWidth) position -= halfWidth
    el.scrollLeft = position
  } else {
    driving = false
  }
  frame = requestAnimationFrame(step)
}

/** Hand control over for a moment. Called on touch, drag and wheel rather
 * than on scroll, so the drift's own scrolling doesn't read as input. */
function noteInteraction(): void {
  interactingUntil = performance.now() + RESUME_AFTER_MS
}

function onScroll(): void {
  if (strip.value) wrap(strip.value)
}

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
  // Same contract the rest of the site keeps (v-reveal, CountUp, the
  // ambient blobs): no self-starting motion when the reader has asked for
  // less of it. The strip stays swipeable either way.
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  frame = requestAnimationFrame(step)
})

onBeforeUnmount(() => cancelAnimationFrame(frame))
</script>

<template>
  <div
    v-if="track.length > 0"
    ref="strip"
    class="marquee min-w-0"
    @pointerenter="paused = true"
    @pointerleave="paused = false"
    @focusin="paused = true"
    @focusout="paused = false"
    @pointerdown="noteInteraction"
    @touchstart.passive="noteInteraction"
    @wheel.passive="noteInteraction"
    @scroll.passive="onScroll"
  >
    <ul class="flex w-max items-start gap-3">
      <li v-for="(player, i) in track" :key="`${player.id}-${i}`">
        <RouterLink
          :to="`/members/${player.id}`"
          class="flex flex-col items-center gap-1"
          :aria-label="player.nickname"
          :tabindex="i < half.length ? 0 : -1"
        >
          <PlayerAvatar :name="player.nickname" :avatar-url="player.avatar_url" size="md" />
          <span class="flex items-center gap-1 text-[10px] leading-none whitespace-nowrap">
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
