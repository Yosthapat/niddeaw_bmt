<script setup lang="ts">
// The home page. A phone gets the short banner and one column of cards; from
// 900px wide, the full hero and a bento grid under it — the live card and
// the top three side by side, the shop and tournament doors, the members
// with the club's numbers, then the vibe and how to get in touch.
import { onBeforeUnmount, ref } from 'vue'
import type { EloTier } from '@/types'
import HomeBanner from '@/components/home/HomeBanner.vue'
import HomeCards from '@/components/home/HomeCards.vue'
import HomeContact from '@/components/home/HomeContact.vue'
import HomeHero from '@/components/home/HomeHero.vue'
import HomeLiveBig from '@/components/home/HomeLiveBig.vue'
import HomeMembers from '@/components/home/HomeMembers.vue'
import HomeStats from '@/components/home/HomeStats.vue'
import HomeTopThree from '@/components/home/HomeTopThree.vue'
import HomeVibes from '@/components/home/HomeVibes.vue'
import LiveNowBox from '@/components/home/LiveNowBox.vue'
import SponsorBand from '@/components/home/SponsorBand.vue'
import TierRevealScene from '@/components/home/TierRevealScene.vue'

// The tier row (in the top-three card) opens this full-screen "impact"
// reveal instead of the small shared TierInfoModal that every other
// TierMascot on the site still uses — home is the one place that gets the
// cinematic treatment.
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
</script>

<template>
  <main class="pb-12 sm:pb-20">
    <HomeHero v-if="wide" />
    <HomeBanner v-else />

    <!-- Everything under the hero stands in the hero's world: see
         .home-world in tailwind.css. -->
    <div class="home-world">
      <!-- phone: one column -->
      <template v-if="!wide">
        <div class="mx-auto flex max-w-4xl flex-col gap-3.5 px-3 pt-3.5 sm:gap-5 sm:px-4 sm:pt-8">
          <HomeCards />
          <LiveNowBox />
        </div>

        <SponsorBand class="mt-5" />

        <div class="mx-auto flex max-w-4xl flex-col gap-5 px-3 pt-5 sm:gap-6 sm:px-4 sm:pt-6">
          <HomeMembers counter />
          <HomeVibes />
          <HomeContact />
        </div>
      </template>

      <!-- from 900px: the bento grid. Its places are set in the style
           below, so the order here is the order a screen reader reads. -->
      <div v-else class="bento mx-auto max-w-[1248px] px-6 pt-10">
        <HomeLiveBig class="b-live" />
        <HomeTopThree class="b-top" @reveal="revealTier = $event" />
        <HomeCards class="b-doors" />
        <HomeMembers class="b-members" />
        <HomeStats class="b-stats" />
        <HomeVibes class="b-vibes" />
        <HomeContact class="b-contact" />
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
/* 12 columns. The top three stands two rows tall beside the live card and
   the two doors; the members strip takes most of a row beside the numbers;
   the vibe and the contact card share the last one. */
.bento {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 20px;
}
.b-live,
.b-doors {
  grid-column: span 8;
}
.b-top {
  grid-column: span 4;
  grid-row: span 2;
}
.b-members {
  grid-column: span 9;
}
.b-stats {
  grid-column: span 3;
}
.b-vibes,
.b-contact {
  grid-column: span 6;
}
/* 900–1099px: the podium needs more than a third to stand in. */
@media (max-width: 1099px) {
  .b-live,
  .b-doors {
    grid-column: span 7;
  }
  .b-top {
    grid-column: span 5;
  }
  .b-members {
    grid-column: span 8;
  }
  .b-stats {
    grid-column: span 4;
  }
}
</style>
