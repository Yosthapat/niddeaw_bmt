<script setup lang="ts">
// Anything the router doesn't recognise lands here. Before this existed the
// catch-all was nothing at all: a typo'd path, or one of the older links
// people have already shared around, rendered an empty page under the
// header with no way back except editing the URL.
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

// Offered instead of a bare "go home": whoever mistyped was heading
// somewhere, and these are the four places they were most likely going.
const destinations = [
  { to: '/', key: 'home' },
  { to: '/members', key: 'members' },
  { to: '/ranking', key: 'ranking' },
  { to: '/matches', key: 'matches' },
] as const
</script>

<template>
  <main class="mx-auto flex max-w-lg flex-col px-4 py-14 text-center sm:py-20">
    <!-- A shuttlecock that has landed out: the flight arc comes down past
         the end of the sideline, which is this page's whole message in one
         picture. Drawn in the same line-icon language as the shuttlecock
         on the home page rather than borrowed from an icon set. -->
    <svg
      viewBox="0 0 84 52"
      fill="none"
      stroke="currentColor"
      stroke-linecap="round"
      stroke-linejoin="round"
      class="mx-auto h-20 w-32 text-brand-pink"
      aria-hidden="true"
    >
      <!-- the line it sailed past -->
      <path d="M2 43h36" stroke-width="1.5" stroke-dasharray="5 5" stroke="#ffffff33" />
      <!-- and the flight that took it there -->
      <path d="M6 33q16-22 36-6" stroke-width="1.2" stroke-dasharray="3 4" stroke="#ea4ca466" />
      <g stroke-width="1.5" transform="translate(40 22) scale(1.15) rotate(122 12 12)">
        <path d="M5.6 6.2Q12 3.4 18.4 6.2" />
        <path d="M5.6 6.2 8.4 13.2" />
        <path d="M18.4 6.2 15.6 13.2" />
        <path d="M12 4.3V13.2" />
        <path d="M8.4 13.2h7.2" />
        <circle cx="12" cy="17" r="3.4" />
      </g>
    </svg>

    <p class="mt-7 font-display text-5xl font-bold tracking-tight text-brand-pink">404</p>
    <h1 class="mt-3 font-display text-xl font-bold text-white">{{ t('notFound.title') }}</h1>
    <p class="mt-2 text-sm leading-relaxed text-white/55">{{ t('notFound.message') }}</p>

    <nav class="mt-8 flex flex-wrap justify-center gap-2">
      <RouterLink
        v-for="d in destinations"
        :key="d.to"
        :to="d.to"
        class="hud-panel hud-hover border border-brand-pink/25 bg-brand-surface px-4 py-2 text-sm font-semibold text-white/80 transition-colors hover:border-brand-pink hover:text-brand-pink"
      >
        {{ t(`nav.${d.key}`) }}
      </RouterLink>
    </nav>
  </main>
</template>
