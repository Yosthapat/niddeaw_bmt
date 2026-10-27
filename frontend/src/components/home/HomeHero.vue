<script setup lang="ts">
/**
 * The home page's opening screen, laid out the way BreachBunny's is
 * (heroinspo.com/gallery/breachbunny): a two-line shout on the left — white,
 * then neon pink — the club's own character large on the right, a dark grid
 * with crosshair marks behind both, a pink beam sweeping the bottom edge, a
 * "scroll for more" cue, and the partners running past in a band underneath.
 *
 * The layout is borrowed; everything in it is the club's own. The character
 * is the club's cat emblem, the words are the club's tagline split into a
 * shout and a body, the faint shapes in the background are a shuttlecock, a
 * crown and a racket, and the band carries the club's sponsors.
 */
import { useI18n } from 'vue-i18n'
import type { EloTier } from '@/types'
import TierMascot from '@/components/players/TierMascot.vue'
import { tierTextStyle } from '@/composables/useEloTier'

const emit = defineEmits<{ reveal: [tier: EloTier] }>()

const { t } = useI18n()

// Ordered by rising alcohol content — matches elo_service.py's
// _TIER_THRESHOLDS order. Absinthe's `gradient` gives it the rainbow
// "rarest rank" treatment via tierTextStyle() instead of a flat color.
const tiers: {
  tier: EloTier
  label: string
  color: string
  gradient?: string
}[] = [
  { tier: 'milk', label: 'Milk', color: 'var(--color-tier-milk)' },
  { tier: 'beer', label: 'Beer', color: 'var(--color-tier-beer)' },
  { tier: 'highball', label: 'Highball', color: 'var(--color-tier-highball)' },
  { tier: 'wine', label: 'Wine', color: 'var(--color-tier-wine)' },
  { tier: 'soju', label: 'Soju', color: 'var(--color-tier-soju)' },
  { tier: 'whisky', label: 'Whisky', color: 'var(--color-tier-whisky)' },
  { tier: 'vodka', label: 'Vodka', color: 'var(--color-tier-vodka)' },
  {
    tier: 'absinthe',
    label: 'Absinthe',
    color: 'var(--color-tier-absinthe)',
    gradient: 'var(--gradient-tier-absinthe)',
  },
]

// -mono.png variants: original logos recolored to a white silhouette
// (RGB -> white, original alpha kept as the mask) so every logo reads
// cleanly straight against the dark background with no card/box needed.
// Each file is trimmed to the logo itself, and width/height are its real
// intrinsic size so the browser can reserve the right aspect ratio before
// the bytes arrive.
const sponsors = [
  {
    name: 'Wasteland',
    src: '/sponsors/wasteland-mono.png',
    width: 424,
    height: 104,
    href: 'https://www.instagram.com/wastelandbkk',
  },
  {
    name: 'Match Mellow',
    src: '/sponsors/match-mellow-mono.png',
    width: 323,
    height: 205,
    href: 'https://www.instagram.com/match.mellowww',
  },
  {
    name: 'Sawadee Natural Herbal Balm',
    src: '/sponsors/sawadee-mono.png',
    width: 417,
    height: 350,
    href: 'https://www.instagram.com/sawadee_naturalherbalbalm',
  },
  {
    name: 'Umore Made',
    src: '/sponsors/umore-made-mono.png',
    width: 449,
    height: 169,
    href: 'https://www.instagram.com/umore.made',
  },
  {
    name: 'The Players Club',
    src: '/sponsors/players-club-mono.png',
    width: 354,
    height: 388,
    href: 'https://www.instagram.com/theplayersclubthailand',
  },
]

// One height for every logo would make Wasteland's long wordmark a sliver
// and The Players Club's round badge a block. Sizing each to the same area
// instead gives them the same visual weight in the band, the way the
// reference's partner strip reads. In px at phone width; the band scales it.
const LOGO_AREA = 2400
function logoHeight(sponsor: { width: number; height: number }): number {
  const aspect = sponsor.width / sponsor.height
  return Math.round(Math.min(52, Math.max(20, Math.sqrt(LOGO_AREA / aspect))))
}

// Grid intersections that get a "+" mark, in cells of the 72px grid drawn
// by .bb-hero-bg. Scattered rather than regular, the way the reference
// does it; the ones past a phone's width are simply clipped.
const crosses = [
  [2, 1],
  [8, 1],
  [15, 2],
  [5, 4],
  [12, 5],
  [1, 7],
  [17, 6],
  [7, 8],
  [14, 9],
]

// Same stroke language as the vibe icons further down the page (24x24,
// 1.75 stroke), drawn very faint and very large.
const ghosts = [
  {
    // shuttlecock
    path: 'M9.5 18.5a2.5 2.5 0 0 0 5 0 M9.5 18.5 6 5h12l-3.5 13.5 M10 5l1.2 13.5 M14 5l-1.2 13.5 M6.8 9h10.4',
    class: 'top-[6%] left-[3%] h-28 w-28 -rotate-12 sm:h-36 sm:w-36',
  },
  {
    // crown
    path: 'M3 8.5l4.2 3.8L12 5l4.8 7.3L21 8.5l-2 10H5z M5 21h14',
    class: 'bottom-[24%] left-[30%] hidden h-32 w-32 rotate-6 md:block',
  },
  {
    // racket
    path: 'M15 3a6 6 0 1 1 0 12 6 6 0 0 1 0-12z M10.8 13.2 4 20 M12 6.5l6 6 M15 4.5l3.5 3.5 M11.5 9l4.5 4.5',
    class: 'top-[38%] right-[2%] h-28 w-28 rotate-12 sm:h-36 sm:w-36',
  },
]
</script>

<template>
  <section class="bb-hero relative isolate overflow-hidden" aria-labelledby="home-hero-title">
    <!-- Everything decorative sits in one layer behind the content. -->
    <div class="bb-hero-bg pointer-events-none absolute inset-0 -z-10" aria-hidden="true">
      <span
        v-for="([col, row], i) in crosses"
        :key="i"
        class="bb-cross"
        :style="{ left: `${col * 72}px`, top: `${row * 72}px` }"
      />
      <span class="bb-streak top-[-10%] left-[38%]" />
      <span class="bb-streak top-[-20%] left-[44%] opacity-60" />
      <svg
        v-for="(ghost, i) in ghosts"
        :key="`g${i}`"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.75"
        stroke-linecap="round"
        stroke-linejoin="round"
        class="absolute text-white/[0.07]"
        :class="ghost.class"
      >
        <path :d="ghost.path" />
      </svg>
      <span class="bb-beam" />
    </div>

    <div class="mx-auto grid max-w-6xl items-center gap-4 px-4 pt-6 sm:px-6 md:grid-cols-[1.05fr_1fr] md:gap-8 md:pt-14">
      <!-- Character first on a phone, the way a poster reads; to the right
           of the words from tablet width up. -->
      <div class="relative order-first flex justify-center md:order-last">
        <div class="bb-emblem-halo" aria-hidden="true" />
        <img
          src="/hero/emblem.webp"
          :alt="t('home.hero.emblemAlt')"
          width="404"
          height="418"
          fetchpriority="high"
          decoding="async"
          class="bb-emblem w-[min(58vw,14rem)] md:w-[min(100%,24rem)]"
        />
      </div>

      <div class="text-center md:text-left">
        <h1
          id="home-hero-title"
          class="font-display text-[clamp(1.85rem,5.4vw,3.4rem)] leading-[1.08] font-bold tracking-tight text-white uppercase"
        >
          <span class="stagger-word block" style="--stagger-delay: 0ms">{{ t('home.hero.line1') }}</span>
          <span class="bb-neon stagger-word block text-brand-pink" style="--stagger-delay: 140ms">{{
            t('home.hero.line2')
          }}</span>
        </h1>
        <p class="mx-auto mt-4 max-w-md text-[15px] leading-relaxed text-balance text-white/75 md:mx-0">
          {{ t('home.hero.body') }}
        </p>

        <div
          class="mt-6 grid grid-cols-4 justify-items-center gap-x-2 gap-y-4 text-xs font-semibold tracking-widest text-white/40 uppercase sm:flex sm:flex-wrap sm:items-center sm:justify-center sm:gap-3 md:justify-start"
        >
          <button
            v-for="(tier, i) in tiers"
            :key="tier.label"
            type="button"
            v-tilt
            class="float-idle flex flex-col items-center gap-1"
            :style="{ '--float-delay': `${i * 0.25}s` }"
            :aria-label="`${tier.label} tier — เปิดฉากเต็มจอ`"
            @click="emit('reveal', tier.tier)"
          >
            <TierMascot :tier="tier.tier" :size="40" :interactive="false" />
            <span :class="{ 'tier-shimmer': tier.gradient }" :style="tierTextStyle(tier.color, tier.gradient)">{{
              tier.label
            }}</span>
          </button>
        </div>
      </div>
    </div>

    <div
      class="font-display mt-8 flex flex-col items-center gap-1.5 text-[11px] font-semibold tracking-[0.25em] text-white/70 uppercase md:mt-10"
      aria-hidden="true"
    >
      {{ t('home.hero.scrollCue') }}
      <span class="flex gap-1.5">
        <svg v-for="i in 3" :key="i" viewBox="0 0 10 8" class="bb-chevron h-2 w-2.5" :style="{ '--i': i }">
          <path d="M0 0h10L5 8z" fill="currentColor" />
        </svg>
      </span>
    </div>

    <!-- The partners band. Two identical halves on one track that slides
         left by exactly one half, so the loop never shows a seam. The
         second half is hidden from screen readers and the tab order: it is
         the same five links again. -->
    <div class="bb-marquee mt-5 border-y border-white/10 bg-black/25 py-3">
      <div class="bb-track flex w-max items-center">
        <template v-for="copy in 2" :key="copy">
          <div
            class="bb-half flex shrink-0 items-center gap-10 pr-10"
            :aria-hidden="copy === 2 ? 'true' : undefined"
            :data-copy="copy"
          >
            <span class="font-display text-[11px] font-semibold tracking-[0.25em] whitespace-nowrap text-white/60 uppercase">
              {{ t('home.sponsorsTitle') }}
            </span>
            <a
              v-for="sponsor in sponsors"
              :key="sponsor.name"
              :href="sponsor.href"
              target="_blank"
              rel="noopener noreferrer"
              :aria-label="sponsor.name"
              :tabindex="copy === 2 ? -1 : undefined"
              class="sponsor-logo shrink-0"
            >
              <img
                :src="sponsor.src"
                :alt="copy === 2 ? '' : sponsor.name"
                :width="sponsor.width"
                :height="sponsor.height"
                loading="lazy"
                decoding="async"
                class="bb-logo w-auto object-contain"
                :style="{ '--h': logoHeight(sponsor) }"
              />
            </a>
          </div>
        </template>
      </div>
    </div>
  </section>
</template>

<style scoped>
/* Cool navy-violet instead of the site's warm black, so the hero reads as
   its own lit stage; the top layer fades it back into the page colour at
   the bottom edge, so nothing below it has to change. */
.bb-hero-bg {
  background:
    linear-gradient(to bottom, transparent 62%, var(--color-brand-black) 100%),
    linear-gradient(rgb(255 255 255 / 0.05) 1px, transparent 1px) 0 0 / 72px 72px,
    linear-gradient(90deg, rgb(255 255 255 / 0.05) 1px, transparent 1px) 0 0 / 72px 72px,
    radial-gradient(70% 55% at 72% 38%, #2c1755 0%, transparent 70%),
    #140b29;
}

/* A "+" centred on a grid intersection. */
.bb-cross {
  position: absolute;
  width: 13px;
  height: 13px;
  translate: -50% -50%;
  background:
    linear-gradient(rgb(255 255 255 / 0.4), rgb(255 255 255 / 0.4)) center / 1px 100% no-repeat,
    linear-gradient(rgb(255 255 255 / 0.4), rgb(255 255 255 / 0.4)) center / 100% 1px no-repeat;
}

/* Thin pink rain streaks across the top. */
.bb-streak {
  position: absolute;
  width: 1px;
  height: 46%;
  rotate: 28deg;
  background: linear-gradient(to bottom, transparent, rgb(234 76 164 / 0.7), transparent);
}

/* The beam of light sweeping across the bottom edge. */
.bb-beam {
  position: absolute;
  left: -15%;
  right: -10%;
  bottom: 9%;
  height: 8rem;
  rotate: -5deg;
  border-radius: 9999px;
  background: linear-gradient(
    90deg,
    rgb(234 76 164 / 0.95) 0%,
    rgb(192 38 211 / 0.8) 38%,
    rgb(157 91 244 / 0.35) 70%,
    transparent 92%
  );
  filter: blur(34px);
  opacity: 0.75;
}

/* Light the cat throws on the stage behind it. */
.bb-emblem-halo {
  position: absolute;
  inset: 8% 6%;
  border-radius: 9999px;
  background: radial-gradient(closest-side, rgb(234 76 164 / 0.45), rgb(157 91 244 / 0.2) 60%, transparent);
  filter: blur(30px);
}

/* The emblem is the logo with its black ground turned into transparency,
   so the glow follows the drawing rather than a square. */
.bb-emblem {
  position: relative;
  height: auto;
  filter: drop-shadow(0 0 14px rgb(234 76 164 / 0.55)) drop-shadow(0 0 40px rgb(157 91 244 / 0.35));
  animation: bb-hover 6s ease-in-out infinite;
}
@keyframes bb-hover {
  0%,
  100% {
    transform: translateY(0) rotate(-2deg);
  }
  50% {
    transform: translateY(-10px) rotate(1.5deg);
  }
}

.bb-neon {
  text-shadow:
    0 0 12px rgb(234 76 164 / 0.65),
    0 0 32px rgb(234 76 164 / 0.35);
}

.bb-chevron {
  animation: bb-chevron 1.6s ease-in-out infinite;
  animation-delay: calc(var(--i) * 0.18s);
}
@keyframes bb-chevron {
  0%,
  100% {
    opacity: 0.35;
    transform: translateY(0);
  }
  50% {
    opacity: 1;
    transform: translateY(2px);
  }
}

.bb-marquee {
  --band-scale: 1;
  overflow: hidden;
  mask-image: linear-gradient(90deg, transparent, #000 8%, #000 92%, transparent);
}
.bb-track {
  animation: bb-marquee 32s linear infinite;
}
.bb-logo {
  height: calc(var(--h) * var(--band-scale) * 1px);
}
@media (min-width: 640px) {
  .bb-marquee {
    --band-scale: 1.25;
  }
}
/* Holds still while someone is aiming at a logo, by mouse or keyboard. */
.bb-marquee:hover .bb-track,
.bb-marquee:focus-within .bb-track {
  animation-play-state: paused;
}
@keyframes bb-marquee {
  to {
    transform: translateX(-50%);
  }
}

@media (prefers-reduced-motion: reduce) {
  .bb-emblem,
  .bb-chevron {
    animation: none;
  }
  /* No drift: one copy, wrapped and centred, so every sponsor is still on
     screen and none of them has to move to be seen. */
  .bb-track {
    animation: none;
    width: 100%;
  }
  /* shrink-0 keeps the moving copy on one line; here it has to give that
     up, or the row runs off both edges instead of wrapping. */
  .bb-half {
    flex-shrink: 1;
    width: 100%;
    padding-inline: 1rem;
    flex-wrap: wrap;
    justify-content: center;
    row-gap: 1rem;
  }
  .bb-half[data-copy='2'] {
    display: none;
  }
  .bb-marquee {
    mask-image: none;
  }
}
</style>
