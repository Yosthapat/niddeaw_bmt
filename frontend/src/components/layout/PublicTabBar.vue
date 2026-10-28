<script setup lang="ts">
/**
 * The public site's six pages, at the bottom of a phone, as icons only —
 * the way Facebook's bar does it. Six labels don't fit a 320px screen;
 * six icons do, and each still has its name for a screen reader and as a
 * tooltip. The shop got the sixth slot; anything else (Hall of Fame, the
 * tiers, the tournament) is one tap away in the ☰ menu (MenuView.vue).
 * From 900px wide AppHeader.vue carries the links instead and this hides
 * itself.
 *
 * Not on admin screens: their buttons that bill people sit at the bottom
 * of the screen, and a bar there would cover them.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute } from 'vue-router'
import { useLiveNow } from '@/composables/useLiveNow'

const route = useRoute()
const { t } = useI18n()
const { playing } = useLiveNow()

// 24x24 stroke icons in the same hand as the rest of the site's line icons.
const tabs = computed(() => [
  { to: '/', label: t('nav.home'), icon: 'M3 11 12 4l9 7M5 10v10h5v-6h4v6h5V10' },
  {
    to: '/members',
    label: t('nav.members'),
    icon: 'M16 19v-1a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v1M9.5 10a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7ZM21 19v-1a4 4 0 0 0-3-3.8M15.5 3.2a3.5 3.5 0 0 1 0 6.6',
  },
  {
    to: '/ranking',
    label: t('nav.ranking'),
    icon: 'M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0zM17 6h3v2a3 3 0 0 1-3 3M7 6H4v2a3 3 0 0 0 3 3',
  },
  {
    to: '/live',
    label: t('nav.live'),
    icon: 'M12 13a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3ZM8.5 15.5a5 5 0 0 1 0-7M15.5 8.5a5 5 0 0 1 0 7M5.6 18.4a9 9 0 0 1 0-12.8M18.4 5.6a9 9 0 0 1 0 12.8',
  },
  { to: '/matches', label: t('nav.matches'), icon: 'M4 5h16v14H4zM12 5v14M7.5 10v4M16.5 10v4' },
  {
    to: '/shop',
    label: t('nav.shop'),
    icon: 'M4 9.5 5.5 4h13L20 9.5M4 9.5h16M4 9.5a2.7 2.7 0 0 0 5.3 0 2.7 2.7 0 0 0 5.4 0 2.7 2.7 0 0 0 5.3 0M5.5 12.5V20h13v-7.5M10 20v-4h4v4',
  },
])

function isActive(to: string): boolean {
  return to === '/' ? route.path === '/' : route.path === to || route.path.startsWith(`${to}/`)
}
</script>

<template>
  <nav
    :aria-label="t('nav.main')"
    class="glass-bar fixed inset-x-3 z-20 grid h-16 grid-cols-6 gap-0.5 rounded-full p-1.5 min-[900px]:hidden"
    style="bottom: calc(14px + env(safe-area-inset-bottom, 0px))"
  >
    <RouterLink v-for="tab in tabs" :key="tab.to" v-slot="{ href, navigate }" :to="tab.to" custom>
      <a
        :href="href"
        :aria-current="isActive(tab.to) ? 'page' : undefined"
        :aria-label="tab.to === '/live' && playing ? t('nav.liveNow') : tab.label"
        :title="tab.label"
        class="relative flex min-w-0 items-center justify-center rounded-full transition-colors"
        :class="isActive(tab.to) ? 'glass-drop text-white' : 'text-white/80 hover:text-white'"
        @click="navigate"
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          :stroke-width="isActive(tab.to) ? 2.2 : 1.9"
          stroke-linecap="round"
          stroke-linejoin="round"
          class="h-[25px] w-[25px]"
          aria-hidden="true"
        >
          <path :d="tab.icon" />
        </svg>
        <span
          v-if="tab.to === '/live' && playing"
          class="live-dot absolute top-2 right-[calc(50%-17px)] h-2 w-2 rounded-full bg-[#ff4d6d] shadow-[0_0_6px_#ff4d6d]"
          aria-hidden="true"
        />
      </a>
    </RouterLink>
  </nav>
</template>

<style scoped>
.live-dot {
  animation: live-blink 1.4s ease-in-out infinite;
}
@keyframes live-blink {
  50% {
    opacity: 0.35;
  }
}
@media (prefers-reduced-motion: reduce) {
  .live-dot {
    animation: none;
  }
}
</style>
