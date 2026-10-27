<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute } from 'vue-router'
import LanguageSwitcher from './LanguageSwitcher.vue'

const route = useRoute()
const { t } = useI18n()

// Inside /admin the club's own nav is dead weight: the admin screens carry
// their own strip of nine destinations directly below this bar, so the
// header was a second row of navigation competing with it — five links to
// pages nobody opens mid-night, above the nine they actually use. What is
// left is the way back out to the site and the language switch.
const isAdmin = computed(() => route.path.startsWith('/admin'))

// Hall of Fame nav link is temporarily hidden (not in use yet) — the
// /hall-of-fame route and view still exist, just unlinked from the header.
const publicLinks = computed(() => [
  { to: '/', label: t('nav.home') },
  { to: '/members', label: t('nav.members') },
  { to: '/ranking', label: t('nav.ranking') },
  { to: '/live', label: t('nav.live') },
  { to: '/matches', label: t('nav.matches') },
])

// A member's profile is still "Members", a match's detail still "Matches".
function isActive(to: string): boolean {
  return to === '/' ? route.path === '/' : route.path === to || route.path.startsWith(`${to}/`)
}
</script>

<template>
  <header v-if="isAdmin" class="sticky top-0 z-10 border-b border-brand-pink/20 bg-brand-black/95 backdrop-blur">
    <div class="mx-auto flex max-w-5xl items-center gap-2.5 px-3 py-3 sm:gap-4 sm:px-4">
      <RouterLink to="/" class="flex min-h-11 shrink-0 items-center gap-2.5">
        <span class="hud-panel bg-brand-pink p-0.5">
          <img
            src="/pwa-icons/pwa-192x192.png"
            alt="นิดเดียว Badminton Club logo"
            width="32"
            height="32"
            class="hud-panel block h-8 w-8"
          />
        </span>
        <span class="hidden font-display text-base font-bold tracking-wide text-white sm:inline">
          นิดเดียว<span class="text-brand-pink">BMT</span>
        </span>
      </RouterLink>
      <LanguageSwitcher class="ml-auto shrink-0" />
    </div>
  </header>

  <!-- The public site floats its menu on a bar of glass. The header row
       itself is see-through and lets clicks pass, so only the bar takes
       anything from what is behind it.

       On a phone the bar holds the club and the language only: the five
       pages sit at the bottom of the screen in PublicTabBar.vue, where a
       thumb reaches them, instead of overflowing a 320px bar the way the
       old header's "ผลแมตช์" did. From 900px they all fit up here. -->
  <header
    v-else
    class="pointer-events-none sticky top-0 z-10 flex h-[var(--header-h)] items-center justify-center px-3 min-[900px]:px-4"
  >
    <div
      class="glass-bar pointer-events-auto flex h-14 w-full items-center justify-between gap-1.5 rounded-full pr-1.5 pl-2 min-[900px]:h-16 min-[900px]:w-auto min-[900px]:justify-start min-[900px]:pr-2.5 min-[900px]:pl-3"
    >
      <RouterLink
        to="/"
        class="flex min-h-11 shrink-0 items-center gap-2.5 min-[900px]:mr-1 min-[900px]:border-r min-[900px]:border-white/15 min-[900px]:pr-4"
      >
        <img
          src="/pwa-icons/pwa-192x192.png"
          alt="นิดเดียว Badminton Club logo"
          width="40"
          height="40"
          class="h-9 w-9 rounded-full ring-2 ring-white/30 min-[900px]:h-10 min-[900px]:w-10"
        />
        <span class="font-display text-[17px] font-bold text-white min-[900px]:text-lg">
          นิดเดียว<span class="text-brand-pink">BMT</span>
        </span>
      </RouterLink>

      <nav :aria-label="t('nav.main')" class="hidden items-center gap-1 min-[900px]:flex">
        <RouterLink v-for="link in publicLinks" :key="link.to" v-slot="{ href, navigate }" :to="link.to" custom>
          <a
            :href="href"
            :aria-current="isActive(link.to) ? 'page' : undefined"
            class="flex h-[46px] items-center rounded-full text-[15px] whitespace-nowrap transition-colors"
            :class="isActive(link.to) ? 'glass-drop px-5 font-medium' : 'px-4 text-white/80 hover:text-white'"
            @click="navigate"
          >
            {{ link.label }}
          </a>
        </RouterLink>
      </nav>

      <!-- The admin entry point lives at the bottom of the home page, next
           to the organiser contact block, not up here: it is the one
           control no member ever needs — see HomeView.vue. -->
      <LanguageSwitcher glass class="shrink-0 min-[900px]:ml-1.5" />
    </div>
  </header>
</template>
