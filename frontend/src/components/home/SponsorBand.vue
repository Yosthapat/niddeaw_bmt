<script setup lang="ts">
// The partners band: every logo a white silhouette trimmed to the mark
// (made by the backend from whatever the sponsor sent), with its real size
// so the browser reserves the right shape before the bytes arrive. Under
// the big hero from 900px wide, under the home cards on a phone.
//
// It drifts on its own and can be swiped or dragged; let go and it drifts
// on from there (useDriftStrip).
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getSponsors } from '@/api/public'
import { useDriftStrip } from '@/composables/useDriftStrip'
import { BUNDLED_SPONSORS, logoHeight, type BandLogo } from '@/utils/sponsorBand'

// About the pace the band had as a CSS animation.
const PIXELS_PER_SECOND = 30

const { t } = useI18n()
const sponsors = ref<BandLogo[]>(BUNDLED_SPONSORS)
const strip = ref<HTMLElement | null>(null)
const { handlers } = useDriftStrip(strip, { speed: PIXELS_PER_SECOND })

// How many times one set of logos repeats in each half of the track. A
// half narrower than the band leaves an empty stretch after the last logo
// on a wide screen — five sponsors are ~800px, a desktop is twice that.
// Three band-widths per half also leaves a full band-width of track on
// each side of the loop's window, so one long swipe either way never runs
// into the end (see useDriftStrip).
const BANDS_PER_HALF = 3
const perHalf = ref(1)

function firstSet(): HTMLElement | null {
  return strip.value?.querySelector<HTMLElement>('[data-copy="1"]') ?? null
}

function measure(): void {
  const el = strip.value
  const set = firstSet()
  if (!el || !set || set.offsetWidth === 0) return
  perHalf.value = Math.max(1, Math.ceil((BANDS_PER_HALF * el.clientWidth) / set.offsetWidth))
}

let observer: ResizeObserver | null = null
function observe(): void {
  observer?.disconnect()
  const el = strip.value
  const set = firstSet()
  if (!el || !set || typeof ResizeObserver === 'undefined') return
  // The band for a rotated phone or a resized window; the set for a logo
  // whose real width only settles once its file arrives.
  observer = new ResizeObserver(measure)
  observer.observe(el)
  observer.observe(set)
}

onMounted(async () => {
  observe()
  try {
    sponsors.value = await getSponsors()
  } catch {
    // keep the bundled five — see BUNDLED_SPONSORS
  }
})
watch(sponsors, async () => {
  await nextTick()
  observe()
  measure()
})
onBeforeUnmount(() => observer?.disconnect())
</script>

<template>
  <!-- The partners band. Two identical halves of perHalf sets each, so
       scrolling past one half lands on the same pixel of the other and the
       loop never shows a seam. Only the first set is announced and
       tabbable: the rest are the same links again. -->
  <div
    v-if="sponsors.length > 0"
    ref="strip"
    class="bb-marquee border-y border-white/10 bg-white/[0.04] py-3 backdrop-blur-md"
    v-on="handlers"
  >
    <div class="bb-track flex w-max items-center">
      <div
        v-for="copy in perHalf * 2"
        :key="copy"
        class="bb-group flex shrink-0 items-center gap-10 pr-10"
        :aria-hidden="copy > 1 ? 'true' : undefined"
        :data-copy="copy"
      >
        <span class="font-display text-[11px] font-semibold tracking-[0.25em] whitespace-nowrap text-white/60 uppercase">
          {{ t('home.sponsorsTitle') }}
        </span>
        <a
          v-for="sponsor in sponsors"
          :key="sponsor.logo_url"
          :href="sponsor.href ?? undefined"
          target="_blank"
          rel="noopener noreferrer"
          :aria-label="sponsor.name"
          :tabindex="copy > 1 ? -1 : undefined"
          class="sponsor-logo shrink-0"
        >
          <img
            :src="sponsor.logo_url"
            :alt="copy > 1 ? '' : sponsor.name"
            :width="sponsor.logo_width"
            :height="sponsor.logo_height"
            loading="lazy"
            decoding="async"
            draggable="false"
            class="bb-logo w-auto object-contain"
            :style="{ '--h': logoHeight(sponsor) }"
          />
        </a>
      </div>
    </div>
  </div>
</template>

<style scoped>
.bb-marquee {
  --band-scale: 1;
  /* Scrollable by hand, with the bar hidden: the drift already says it
     moves. */
  overflow-x: auto;
  scrollbar-width: none;
  /* A swipe off the end must not become the browser's back gesture. */
  overscroll-behavior-x: contain;
  /* The drift writes scrollLeft every frame; smooth scrolling would try to
     animate each write and fight it. */
  scroll-behavior: auto;
  /* A mouse drag pulls the logos, not a text selection across them. */
  user-select: none;
  -webkit-mask-image: linear-gradient(90deg, transparent, #000 8%, #000 92%, transparent);
  mask-image: linear-gradient(90deg, transparent, #000 8%, #000 92%, transparent);
}
.bb-marquee::-webkit-scrollbar {
  display: none;
}
@media (pointer: fine) {
  .bb-marquee {
    cursor: grab;
  }
  .bb-marquee:active {
    cursor: grabbing;
  }
}
.bb-logo {
  height: calc(var(--h) * var(--band-scale) * 1px);
}
@media (min-width: 640px) {
  .bb-marquee {
    --band-scale: 1.25;
  }
}

@media (prefers-reduced-motion: reduce) {
  /* No drift: one set, wrapped and centred, so every sponsor is still on
     screen and none of them has to move to be seen. */
  .bb-marquee {
    overflow-x: visible;
    cursor: auto;
    -webkit-mask-image: none;
    mask-image: none;
  }
  .bb-track {
    width: 100%;
  }
  /* shrink-0 keeps a moving set on one line; here it has to give that up,
     or the row runs off both edges instead of wrapping. */
  .bb-group {
    flex-shrink: 1;
    width: 100%;
    padding-inline: 1rem;
    flex-wrap: wrap;
    justify-content: center;
    row-gap: 1rem;
  }
  .bb-group:not([data-copy='1']) {
    display: none;
  }
}
</style>
