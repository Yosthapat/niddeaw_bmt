<script setup lang="ts">
/**
 * The public site's five pages, at the bottom of a phone.
 *
 * Five links did not fit beside the logo and the language switch in a
 * phone-width header; the last one ran off a 320px screen. Down here each
 * page is one thumb-tap away. From 900px wide AppHeader.vue carries them
 * instead and this hides itself.
 *
 * Not on admin screens: their buttons that bill people sit at the bottom
 * of the screen, and a bar there would cover them.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute } from 'vue-router'

const route = useRoute()
const { t } = useI18n()

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
])

function isActive(to: string): boolean {
  return to === '/' ? route.path === '/' : route.path === to || route.path.startsWith(`${to}/`)
}
</script>

<template>
  <nav
    :aria-label="t('nav.main')"
    class="glass-bar fixed inset-x-3 z-20 grid h-[68px] grid-cols-5 gap-0.5 rounded-full p-1.5 min-[900px]:hidden"
    style="bottom: calc(14px + env(safe-area-inset-bottom, 0px))"
  >
    <RouterLink v-for="tab in tabs" :key="tab.to" v-slot="{ href, navigate }" :to="tab.to" custom>
      <a
        :href="href"
        :aria-current="isActive(tab.to) ? 'page' : undefined"
        class="flex min-w-0 flex-col items-center justify-center gap-[3px] rounded-full text-[11px] transition-colors"
        :class="isActive(tab.to) ? 'glass-drop font-medium' : 'text-white/80 hover:text-white'"
        @click="navigate"
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          :stroke-width="isActive(tab.to) ? 2 : 1.8"
          stroke-linecap="round"
          stroke-linejoin="round"
          class="h-[22px] w-[22px]"
          aria-hidden="true"
        >
          <path :d="tab.icon" />
        </svg>
        <span class="max-w-full truncate px-1">{{ tab.label }}</span>
      </a>
    </RouterLink>
  </nav>
</template>
