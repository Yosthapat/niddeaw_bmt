<script setup lang="ts">
// The club's vibe in seven line icons — the card under the members on a
// phone, and half a row of the desktop grid.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

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
</script>

<template>
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
