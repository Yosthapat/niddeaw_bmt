<script setup lang="ts">
// "N matches played" — the club's running tally, sitting right-aligned
// above the home page banner.
//
// Polls rather than loading once: on a Friday night the number moves every
// time a result is recorded, and the whole point is that it keeps up
// without a refresh. 15s rather than the 7s LiveView uses — a match takes
// ten minutes at the very least, so a faster poll would only double the
// request rate on the most-visited page of the site to show the same
// number.
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getMatchCount } from '@/api/public'
import { usePolling } from '@/composables/usePolling'
import CountUp from '@/components/common/CountUp.vue'

const { t } = useI18n()

// null = not known yet. Kept distinct from 0 so a slow first response
// shows nothing rather than briefly claiming the club has played none.
const total = ref<number | null>(null)

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

usePolling(refresh, 15000)
</script>

<template>
  <!-- Hidden until there is something to report: a club with no recorded
       matches yet shouldn't lead its home page with a zero. -->
  <!-- No margin or alignment of its own: HomeView places this in a row
       beside the member marquee, and owning the spacing here would fight
       that layout. -->
  <div
    v-if="total !== null && total > 0"
    class="hud-panel glass-panel hud-hover flex shrink-0 items-center gap-3 border border-brand-pink/25 px-3.5 py-2 transition-colors hover:border-brand-pink/50"
  >
      <!-- Own-drawn shuttlecock glyph, same line-icon language as the
           contact and vibe rows further down the page. -->
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.6"
        stroke-linecap="round"
        stroke-linejoin="round"
        class="h-5 w-5 shrink-0 text-brand-pink/60"
        aria-hidden="true"
      >
        <path d="M5.6 6.2Q12 3.4 18.4 6.2" />
        <path d="M5.6 6.2 8.4 13.2" />
        <path d="M18.4 6.2 15.6 13.2" />
        <path d="M12 4.3V13.2" />
        <path d="M8.4 13.2h7.2" />
        <circle cx="12" cy="17" r="3.4" />
      </svg>

      <div class="text-right leading-none">
        <!-- tabular-nums so the width doesn't jitter as the count ticks. -->
        <p class="font-display text-lg font-bold tabular-nums text-brand-pink">
          <CountUp :value="total" :format="formatCount" />
        </p>
        <p
          class="mt-1.5 flex items-center justify-end gap-1.5 text-[10px] tracking-wide text-white/45 uppercase"
        >
          <!-- Same pulse LiveView uses, at half the size: it says the number
               is live rather than a figure baked in at page load. -->
          <span class="relative flex h-1.5 w-1.5">
            <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-pink opacity-75" />
            <span class="relative inline-flex h-1.5 w-1.5 rounded-full bg-brand-pink" />
          </span>
          {{ t('home.clubMatchesLabel') }}
        </p>
    </div>
  </div>
</template>
