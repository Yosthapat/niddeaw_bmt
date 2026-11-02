<script setup lang="ts">
// Static club intro + contact — there's no backend-driven "club info" table
// (out of scope per the issue doc), so this content is edited directly here.
import { computed, onBeforeUnmount, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import type { EloTier } from '@/types'
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
    // LINE's own green, darkened until white text on it is readable.
    cls: 'bg-[#037f36] border-[#06c755]/60 shadow-[0_8px_20px_-8px_rgb(6_199_85/0.6)]',
  },
  {
    label: 'TikTok',
    href: 'https://www.tiktok.com/@nidde4w',
    path: 'M14 4v10.5a3.5 3.5 0 1 1-3.5-3.5 M14 4c.5 2.5 2.5 4 5 4',
    cls: 'bg-white/8 border-white/25',
  },
]
</script>

<template>
  <main class="pb-12 sm:pb-20">
    <HomeHero v-if="wide" @reveal="revealTier = $event" />
    <HomeBanner v-else />

    <!-- Everything under the hero stands in the hero's world: see
         .home-world in tailwind.css. -->
    <div class="home-world">
      <div class="mx-auto flex max-w-4xl flex-col gap-3.5 px-3 pt-3.5 sm:gap-5 sm:px-4 sm:pt-8">
        <HomeCards />
        <LiveNowBox />
      </div>

      <SponsorBand v-if="!wide" class="mt-5" />

      <div class="mx-auto flex max-w-4xl flex-col gap-5 px-3 pt-5 sm:gap-6 sm:px-4 sm:pt-6">
        <!-- the club's people, and how much they've played -->
        <section v-reveal class="world-card p-4 sm:p-5" aria-labelledby="home-members">
          <div class="flex items-end justify-between gap-3">
            <div>
              <p class="world-eyebrow">MEMBERS</p>
              <h2 id="home-members" class="world-title text-xl sm:text-2xl">{{ t('home.memberMarqueeLabel') }}</h2>
            </div>
            <RouterLink to="/members" class="inline-flex min-h-11 items-center gap-1 text-sm text-white/75 hover:text-white">
              {{ t('home.seeAll') }} <span aria-hidden="true">→</span>
            </RouterLink>
          </div>
          <!-- Marquee takes whatever width the counter leaves; min-w-0 lets
               it actually shrink instead of forcing the row wider. -->
          <div class="mt-3 flex items-center gap-3">
            <MemberMarquee class="flex-1" />
            <ClubMatchCounter />
          </div>
        </section>

        <section v-reveal class="world-card p-5 sm:p-6" aria-labelledby="home-vibes">
          <div class="text-center">
            <p class="world-eyebrow">CLUB VIBES</p>
            <h2 id="home-vibes" class="world-title text-xl sm:text-2xl">{{ t('home.vibesTitle') }}</h2>
          </div>
          <!-- wrapped and centred, so a phone's short last row sits in the
               middle instead of hanging off the left -->
          <ul class="mt-5 flex flex-wrap justify-center gap-x-3 gap-y-4 sm:gap-x-6">
            <li v-for="vibe in vibes" :key="vibe.label" class="flex w-[72px] flex-col items-center gap-2 text-center">
              <span class="vibe-chip">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.75"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  class="h-6 w-6"
                  aria-hidden="true"
                >
                  <path :d="vibe.path" />
                  <circle v-for="(dot, i) in vibe.dots" :key="i" :cx="dot[0]" :cy="dot[1]" r="1" fill="currentColor" stroke="none" />
                </svg>
              </span>
              <span class="text-xs leading-tight text-white/75">{{ vibe.label }}</span>
            </li>
          </ul>
        </section>

        <section v-reveal class="world-card overflow-hidden p-5 sm:p-6" aria-labelledby="home-contact">
          <!-- the cat peeking in from the corner, so the last card is still
               the hero's world and not a form -->
          <img src="/hero/cat-color.webp" alt="" width="140" height="140" loading="lazy" class="pointer-events-none absolute -right-6 -bottom-8 h-36 w-36 opacity-25 sm:h-44 sm:w-44" />
          <p class="world-eyebrow">CONTACT</p>
          <h2 id="home-contact" class="world-title text-xl sm:text-2xl">{{ t('home.contactTitle') }}</h2>
          <p class="mt-2 max-w-[36ch] text-sm text-white/75">{{ t('home.contactBody') }}</p>
          <div class="relative mt-4 flex flex-wrap gap-2.5">
            <a
              v-for="social in socialLinks"
              :key="social.label"
              :href="social.href"
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex min-h-12 items-center gap-2 rounded-full border px-5 font-display text-sm font-bold text-white transition-transform hover:-translate-y-0.5"
              :class="social.cls"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5" aria-hidden="true">
                <path :d="social.path" />
              </svg>
              {{ social.label }}
            </a>
          </div>

          <!-- Kept inside the contact card but set apart by the rule: it is
               the same "who runs this" corner of the page, while staying
               visually unlike the LINE/TikTok buttons above so nobody taps
               it expecting to reach a human. -->
          <div class="relative mt-5 border-t border-white/10 pt-3">
            <RouterLink
              :to="authStore.isAuthenticated ? '/admin' : '/admin/login'"
              class="inline-flex min-h-11 items-center gap-2 text-xs font-semibold tracking-wide text-white/55 uppercase transition-colors hover:text-brand-pink-light"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-3.5 w-3.5" aria-hidden="true">
                <rect x="5" y="11" width="14" height="9" rx="1.5" />
                <path d="M8 11V7a4 4 0 0 1 8 0v4" />
              </svg>
              {{ authStore.isAuthenticated ? t('nav.admin') : t('nav.adminLogin') }}
            </RouterLink>
          </div>
        </section>
      </div>
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

<style scoped>
/* Each vibe in a drop of the navigation's glass, lit pink from inside. */
.vibe-chip {
  display: flex;
  width: 56px;
  height: 56px;
  align-items: center;
  justify-content: center;
  border: 1px solid rgb(255 255 255 / 0.2);
  border-radius: 50%;
  background: radial-gradient(120% 140% at 30% 0%, rgb(255 255 255 / 0.22), rgb(255 255 255 / 0.04) 60%);
  box-shadow:
    inset 0 1px 1px rgb(255 255 255 / 0.5),
    inset 0 -3px 8px rgb(234 76 164 / 0.3),
    0 6px 16px rgb(234 76 164 / 0.25);
  color: #ff9fd6;
}
</style>
