<script setup lang="ts">
// "N matches played" — the club's running tally, sitting right-aligned
// above the home page banner.
//
// Collapses to a small shuttlecock pill on tap, which hands its width back
// to the member marquee beside it (the row is `flex-1` + `shrink-0`, so
// whatever this gives up the strip takes). Collapsed is the default: the
// photos are what people came to look at, and the tally reads fine as an
// icon and a number until someone wants the label.
//
// Polls rather than loading once: on a Friday night the number moves every
// time a result is recorded, and the whole point is that it keeps up
// without a refresh. 15s rather than the 7s LiveView uses — a match takes
// ten minutes at the very least, so a faster poll would only double the
// request rate on the most-visited page of the site to show the same
// number.
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getMatchCount, getPlayerCount } from '@/api/public'
import { usePolling } from '@/composables/usePolling'
import CountUp from '@/components/common/CountUp.vue'

const { t } = useI18n()

const EXPANDED_STORAGE_KEY = 'niddeaw-club-counter'

// null = not known yet. Kept distinct from 0 so a slow first response
// shows nothing rather than briefly claiming the club has played none.
const total = ref<number | null>(null)

// How many people are in the club. Read once rather than polled: a member
// joins every few weeks, where the match tally moves every few minutes on
// a Friday, and this sits on the most-visited page of the site.
const members = ref<number | null>(null)

// Same idiom as the locale preference in i18n/index.ts: anything but the
// stored word reads false, so a first-time reader gets the collapsed
// default and everyone else gets back whatever they last chose.
const expanded = ref(localStorage.getItem(EXPANDED_STORAGE_KEY) === 'expanded')

function toggle(): void {
  expanded.value = !expanded.value
  localStorage.setItem(EXPANDED_STORAGE_KEY, expanded.value ? 'expanded' : 'collapsed')
}

function formatCount(value: number): string {
  return value.toLocaleString('th-TH')
}

async function refresh(): Promise<void> {
  try {
    total.value = (await getMatchCount()).completed
  } catch {
    // Keep the last good number on screen. This is a flourish above the
    // banner — a cold-starting backend must not put an error on the home
    // page over it, and the next poll will pick the count back up.
  }
}

async function loadMembers(): Promise<void> {
  try {
    members.value = (await getPlayerCount()).active
  } catch {
    // Same reasoning as the tally: this is a flourish above the banner,
    // and the match count alone still reads fine without it.
  }
}

usePolling(refresh, 15000)
onMounted(loadMembers)
</script>

<template>
  <!-- Hidden until there is something to report: a club with no recorded
       matches yet shouldn't lead its home page with a zero. -->
  <!-- No margin or alignment of its own: HomeView places this in a row
       beside the member marquee, and owning the spacing here would fight
       that layout. -->
  <button
    v-if="total !== null && total > 0"
    type="button"
    class="hud-panel glass-panel hud-hover counter flex shrink-0 cursor-pointer items-center border border-brand-pink/25 hover:border-brand-pink/50"
    :class="expanded ? 'gap-3 px-3.5 py-2' : 'gap-2 px-2.5 py-1.5'"
    :aria-expanded="expanded"
    :aria-label="
      members === null
        ? `${formatCount(total)} ${t('home.clubMatchesLabel')}`
        : `${formatCount(total)} ${t('home.clubMatchesLabel')}, ${formatCount(members)} ${t('home.clubMembersLabel')}`
    "
    @click="toggle"
  >
    <!-- Own-drawn shuttlecock glyph, same line-icon language as the
         contact and vibe rows further down the page. Stays put through the
         toggle — collapsed, it is the whole control. -->
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.6"
      stroke-linecap="round"
      stroke-linejoin="round"
      class="shrink-0 text-brand-pink/60"
      :class="expanded ? 'h-5 w-5' : 'h-4 w-4'"
      aria-hidden="true"
    >
      <path d="M5.6 6.2Q12 3.4 18.4 6.2" />
      <path d="M5.6 6.2 8.4 13.2" />
      <path d="M18.4 6.2 15.6 13.2" />
      <path d="M12 4.3V13.2" />
      <path d="M8.4 13.2h7.2" />
      <circle cx="12" cy="17" r="3.4" />
    </svg>

    <div class="flex flex-col items-end leading-none">
      <!-- One CountUp for both states, never behind a v-if: remounting it
           on each tap would replay the count from zero. tabular-nums so the
           width doesn't jitter as the count ticks. -->
      <p
        class="font-display font-bold tabular-nums text-brand-pink"
        :class="expanded ? 'text-lg' : 'text-sm'"
      >
        <CountUp :value="total" :format="formatCount" />
      </p>
      <!-- Collapsed to nothing on both axes rather than hidden, so the
           width it frees goes to the marquee as the panel shrinks.
           aria-hidden as well: clipping it to 0fr leaves it in the
           accessibility tree, and the button's own label already says
           what the number is. -->
      <!-- Each figure's label sits directly under that figure, in its own
           collapsible: one shared collapsible would stack both labels
           after both numbers, which reads as the wrong label under the
           wrong figure the moment the panel opens. -->
      <div class="collapsible" :class="{ 'is-open': expanded }" :aria-hidden="!expanded">
        <div>
          <span
            class="mt-1.5 flex items-center justify-end gap-1.5 text-xs tracking-wide whitespace-nowrap text-white/45 uppercase"
          >
            <!-- Same pulse LiveView uses, at half the size: it says the number
                 is live rather than a figure baked in at page load. -->
            <span class="relative flex h-1.5 w-1.5">
              <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-pink opacity-75" />
              <span class="relative inline-flex h-1.5 w-1.5 rounded-full bg-brand-pink" />
            </span>
            {{ t('home.clubMatchesLabel') }}
          </span>
        </div>
      </div>

      <!-- The member tally, under the match one. Collapsed it is a bare
           number beside a small figure glyph, so the pill stays a pill;
           expanded it gets its own label like the tally above it. Hidden
           until it is known rather than shown as a zero, the same rule the
           match count follows. -->
      <p
        v-if="members !== null"
        class="mt-1 flex items-center gap-1 font-display font-bold tabular-nums text-white/55"
        :class="expanded ? 'text-sm' : 'text-xs'"
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
          stroke-linejoin="round"
          class="shrink-0"
          :class="expanded ? 'h-3.5 w-3.5' : 'h-3 w-3'"
          aria-hidden="true"
        >
          <path d="M16 20v-1.6a3.4 3.4 0 0 0-3.4-3.4H7.4A3.4 3.4 0 0 0 4 18.4V20" />
          <circle cx="10" cy="7.6" r="3.4" />
          <path d="M20 20v-1.6a3.4 3.4 0 0 0-2.6-3.3M15.2 4.3a3.4 3.4 0 0 1 0 6.6" />
        </svg>
        <CountUp :value="members" :format="formatCount" />
      </p>

      <div
        v-if="members !== null"
        class="collapsible"
        :class="{ 'is-open': expanded }"
        :aria-hidden="!expanded"
      >
        <div>
          <span
            class="mt-1 flex items-center justify-end gap-1.5 text-xs tracking-wide whitespace-nowrap text-white/35 uppercase"
          >
            {{ t('home.clubMembersLabel') }}
          </span>
        </div>
      </div>
    </div>
  </button>
</template>

<style scoped>
/* .hud-hover already transitions transform/box-shadow/border-color; this
   adds the size change the toggle drives. */
.counter {
  transition: padding 0.26s ease;
}

/* The glyph and the figure change size with the panel; without these they
   would jump to their new size while the panel eased to its. */
.counter svg {
  transition:
    width 0.26s ease,
    height 0.26s ease;
}

.counter p {
  transition: font-size 0.26s ease;
}

.counter p svg {
  transition:
    width 0.26s ease,
    height 0.26s ease;
}

/* Both axes: the label is what makes the panel wide *and* tall, so
   collapsing only its height would leave the pill as wide as the words it
   is no longer showing. `fr` tracks animate, so the marquee gains the
   freed width over the same 0.26s rather than snapping. */
.collapsible {
  display: grid;
  grid-template-columns: 0fr;
  grid-template-rows: 0fr;
  opacity: 0;
  transition:
    grid-template-columns 0.26s ease,
    grid-template-rows 0.26s ease,
    opacity 0.18s ease;
}

.collapsible.is-open {
  grid-template-columns: 1fr;
  grid-template-rows: 1fr;
  opacity: 1;
}

/* The grid item does the clipping — min-* defaults would otherwise hold it
   open at its content size and the 0fr track would never take effect. */
.collapsible > * {
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

/* Same contract the rest of the site keeps: the panel still resizes, it
   just arrives there at once. */
@media (prefers-reduced-motion: reduce) {
  .counter,
  .counter svg,
  .counter p,
  .collapsible {
    transition: none;
  }
}
</style>
