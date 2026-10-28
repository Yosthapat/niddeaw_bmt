<script setup lang="ts">
// Static club intro + contact — there's no backend-driven "club info" table
// (out of scope per the issue doc), so this content is edited directly here.
import { computed, onBeforeUnmount, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import type { EloTier } from '@/types'
import AdCarousel from '@/components/home/AdCarousel.vue'
import ClubMatchCounter from '@/components/home/ClubMatchCounter.vue'
import HomeBanner from '@/components/home/HomeBanner.vue'
import HomeCards from '@/components/home/HomeCards.vue'
import HomeHero from '@/components/home/HomeHero.vue'
import LiveNowBox from '@/components/home/LiveNowBox.vue'
import MemberMarquee from '@/components/home/MemberMarquee.vue'
import SponsorBand from '@/components/home/SponsorBand.vue'
import TierRevealScene from '@/components/home/TierRevealScene.vue'

const { t } = useI18n()
// Moved off the header: see the comment in AppHeader.vue.
const authStore = useAuthStore()

// The hero tier row opens this full-screen "impact" reveal instead of the
// small shared TierInfoModal that every other TierMascot on the site still
// uses — home is the one place that gets the cinematic treatment.
const revealTier = ref<EloTier | null>(null)

// A phone gets the short banner, so the cards and the live box show
// without scrolling; from 900px the full hero. Chosen in script rather than
// with CSS so a phone never mounts the hero and downloads its 3D scene
// only to hide it.
const wideQuery = window.matchMedia('(min-width: 900px)')
const wide = ref(wideQuery.matches)
const onWide = (e: MediaQueryListEvent): void => {
  wide.value = e.matches
}
wideQuery.addEventListener('change', onWide)
onBeforeUnmount(() => wideQuery.removeEventListener('change', onWide))

// Auto-rotating promo banner slot, up to 4 images — drop files into
// frontend/public/ads/ and list them here.
const ads = ['/ads/friday-night.webp']

// Club vibe strip — hand-drawn line icons (24x24, stroke-based) instead of
// filled/flat glyphs so they sit quietly next to the bolder TierMascot
// illustrations above rather than competing with them.
const vibes = computed(() => [
  { label: t('home.vibes.alcohol'), path: 'M5 4h14l-7 9z M12 13v7 M8 20h8' },
  {
    label: t('home.vibes.music'),
    path: 'M9 18V5l11-2v13 M6 21a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z M17 19a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z',
  },
  {
    label: t('home.vibes.fun'),
    path: 'M12 2.5l2.9 6.3 6.9.6-5.2 4.6 1.6 6.8L12 16.9l-6.2 3.4 1.6-6.8-5.2-4.6 6.9-.6z',
  },
  {
    label: t('home.vibes.relax'),
    path: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z M8 14s1.5 2 4 2 4-2 4-2 M8.5 9.5h.01 M15.5 9.5h.01',
  },
  {
    label: t('home.vibes.fruit'),
    path: 'M12 8.5c-3.3 0-5.5 2.6-5.5 6 0 3.6 2.2 6.5 5.5 6.5s5.5-2.9 5.5-6.5c0-3.4-2.2-6-5.5-6Z M12 8.5V5.5 M12 5.5c1-1.5 3-1.8 3-1.8',
  },
  {
    label: t('home.vibes.snacks'),
    path: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z',
    dots: [
      [9, 9],
      [15, 10],
      [10.5, 15],
      [15, 15.5],
    ],
  },
  {
    label: t('home.vibes.noSmoking'),
    path: 'M4 11h11a2 2 0 0 1 2 2v0a2 2 0 0 1-2 2H4z M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z M5 20 19 4',
  },
])

// Own-drawn line-icon glyphs (not the real brand marks) so the contact
// badges match the site's hand-drawn icon language instead of pasting in
// LINE's green speech-bubble or TikTok's note logo.
const socialLinks = [
  {
    label: 'LINE OA',
    href: 'https://line.me/R/ti/p/@369iojcn',
    path: 'M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H9l-4 4v-4H6a2 2 0 0 1-2-2Z',
  },
  {
    label: 'TikTok',
    href: 'https://www.tiktok.com/@nidde4w',
    path: 'M6 20V10 M12 20V4 M18 20V13',
  },
]
</script>

<template>
  <main class="pb-12 sm:pb-20">
    <HomeHero v-if="wide" @reveal="revealTier = $event" />
    <HomeBanner v-else />

    <div class="mx-auto flex max-w-4xl flex-col gap-3.5 px-3 pt-3.5 sm:gap-4 sm:px-4 sm:pt-8">
      <HomeCards />
      <LiveNowBox />
    </div>

    <SponsorBand v-if="!wide" class="mt-5" />

    <div class="mx-auto max-w-4xl px-4 pt-6 sm:pt-8">
      <!-- Marquee takes whatever width the counter leaves; min-w-0 lets it
           actually shrink instead of forcing the row wider than the page. -->
      <div class="mb-4 flex items-center gap-3 sm:mb-5">
        <MemberMarquee class="flex-1" />
        <ClubMatchCounter />
      </div>

      <div v-reveal>
        <AdCarousel :images="ads" />
      </div>

      <section v-reveal class="hud-panel glass-panel mt-8 border border-brand-pink/20 p-6 sm:mt-10">
        <h2 class="text-center text-xs font-semibold tracking-widest text-brand-pink/70 uppercase">{{ t('home.vibesTitle') }}</h2>
        <div class="mt-5 flex flex-wrap justify-center gap-x-6 gap-y-5 sm:gap-x-8">
          <div v-for="vibe in vibes" :key="vibe.label" class="flex w-16 flex-col items-center gap-2 text-center">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.75"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="h-7 w-7 text-brand-pink"
            >
              <path :d="vibe.path" />
              <circle v-for="(dot, i) in vibe.dots" :key="i" :cx="dot[0]" :cy="dot[1]" r="1" fill="currentColor" stroke="none" />
            </svg>
            <span class="text-xs leading-tight text-white/60">{{ vibe.label }}</span>
          </div>
        </div>
      </section>

      <section v-reveal class="hud-panel glass-panel mt-8 border border-brand-pink/20 p-6 text-left sm:mt-10">
        <h2 class="font-display text-sm font-bold tracking-wide text-brand-pink uppercase">{{ t('home.contactTitle') }}</h2>
        <p class="mt-2 text-sm text-white/60">
          {{ t('home.contactBody') }}
        </p>
        <div class="mt-4 flex flex-wrap gap-2">
          <a
            v-for="social in socialLinks"
            :key="social.label"
            :href="social.href"
            target="_blank"
            rel="noopener noreferrer"
            class="hud-panel hud-hover inline-flex min-h-11 items-center gap-1.5 border border-brand-pink/25 bg-brand-black px-3 text-xs font-semibold text-white/80 transition-colors hover:border-brand-pink hover:text-brand-pink"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.75"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="h-4 w-4"
            >
              <path :d="social.path" />
            </svg>
            {{ social.label }}
          </a>
        </div>

        <!-- Kept inside the contact panel but set apart by the rule: it is
             the same "who runs this" corner of the page, while staying
             visually unlike the LINE/TikTok buttons above so nobody taps it
             expecting to reach a human. -->
        <div class="mt-5 border-t border-brand-pink/15 pt-4">
          <RouterLink
            :to="authStore.isAuthenticated ? '/admin' : '/admin/login'"
            class="hud-hover inline-flex min-h-11 items-center gap-2 text-xs font-semibold tracking-wide text-white/40 uppercase transition-colors hover:text-brand-pink"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-3.5 w-3.5">
              <rect x="5" y="11" width="14" height="9" rx="1.5" />
              <path d="M8 11V7a4 4 0 0 1 8 0v4" />
            </svg>
            {{ authStore.isAuthenticated ? t('nav.admin') : t('nav.adminLogin') }}
          </RouterLink>
        </div>
      </section>

    </div>

    <!-- Teleports its actual content to <body> on its own, but must stay a
         child here (not a sibling of <main>) — App.vue's page <Transition>
         needs this view to render as a single root node to track enter/leave
         hooks; a second sibling root here makes it multi-root the same way
         admin views are (see App.vue's comment), which leaves the page stuck
         invisible mid-transition until a manual reload. -->
    <TierRevealScene :tier="revealTier" @close="revealTier = null" />
  </main>
</template>
