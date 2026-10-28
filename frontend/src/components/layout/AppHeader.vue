<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute } from 'vue-router'
import { setLocale } from '@/i18n'
import LanguageSwitcher from './LanguageSwitcher.vue'

const route = useRoute()
const { t, locale } = useI18n()

// Inside /admin the club's own nav is dead weight: the admin screens carry
// their own strip of nine destinations directly below this bar, so the
// header was a second row of navigation competing with it — five links to
// pages nobody opens mid-night, above the nine they actually use. What is
// left is the way back out to the site and the language switch.
const isAdmin = computed(() => route.path.startsWith('/admin'))
// The menu and search pages are full screens with their own back arrow,
// the way Facebook opens them; the bar would only be a second way out.
const ownBar = computed(() => route.path === '/menu' || route.path === '/search')

// One tap flips the language on a phone: with two languages a dropdown is
// a tap more than it needs to be.
function toggleLocale(): void {
  setLocale(locale.value === 'th' ? 'en' : 'th')
}

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
      <RouterLink to="/" class="flex min-h-11 min-w-11 shrink-0 items-center gap-2.5">
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

  <!-- On a phone: a solid bar the way Facebook's is — ☰ and the club on
       the left, search and language on the right. The pages themselves are
       at the bottom of the screen in PublicTabBar.vue, where a thumb
       reaches them; everything else is behind ☰ (MenuView.vue). -->
  <header
    v-else-if="!ownBar"
    class="sticky top-0 z-10 flex h-[var(--header-h)] items-center justify-between border-b border-white/8 bg-[#0b0518] pr-3 pl-1 min-[900px]:hidden"
  >
    <div class="flex min-w-0 items-center">
      <RouterLink to="/menu" class="flex h-11 w-11 shrink-0 items-center justify-center" :aria-label="t('nav.menu')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" class="h-[26px] w-[26px]" aria-hidden="true">
          <path d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </RouterLink>
      <RouterLink to="/" class="flex h-11 min-w-0 items-center gap-2">
        <img
          src="/pwa-icons/pwa-192x192.png"
          alt="นิดเดียว Badminton Club logo"
          width="34"
          height="34"
          class="h-[34px] w-[34px] shrink-0 rounded-full"
        />
        <span class="truncate font-display text-[22px] font-bold tracking-tight text-white">
          นิดเดียว<span class="text-brand-pink">BMT</span>
        </span>
      </RouterLink>
    </div>
    <div class="flex shrink-0 gap-2">
      <RouterLink to="/search" class="fb-round" :aria-label="t('nav.search')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" class="h-[22px] w-[22px]" aria-hidden="true">
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-3.5-3.5" />
        </svg>
      </RouterLink>
      <button type="button" class="fb-round font-display text-[13px] font-bold" :aria-label="t('nav.switchLang')" @click="toggleLocale">
        {{ locale === 'th' ? 'TH' : 'EN' }}
      </button>
    </div>
  </header>

  <!-- From 900px the public site floats its menu on a bar of glass. The
       header row itself is see-through and lets clicks pass, so only the
       bar takes anything from what is behind it. -->
  <header
    v-if="!isAdmin"
    class="pointer-events-none sticky top-0 z-10 hidden h-[var(--header-h)] items-center justify-center px-4 min-[900px]:flex"
  >
    <div class="glass-bar pointer-events-auto flex h-16 items-center gap-1.5 rounded-full pr-2.5 pl-3">
      <RouterLink to="/" class="mr-1 flex min-h-11 shrink-0 items-center gap-2.5 border-r border-white/15 pr-4">
        <img
          src="/pwa-icons/pwa-192x192.png"
          alt="นิดเดียว Badminton Club logo"
          width="40"
          height="40"
          class="h-10 w-10 rounded-full ring-2 ring-white/30"
        />
        <span class="font-display text-lg font-bold text-white">
          นิดเดียว<span class="text-brand-pink">BMT</span>
        </span>
      </RouterLink>

      <nav :aria-label="t('nav.main')" class="flex items-center gap-1">
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
      <LanguageSwitcher glass class="ml-1.5 shrink-0" />
    </div>
  </header>
</template>

<style scoped>
.fb-round {
  display: flex;
  width: 44px;
  height: 44px;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: rgb(255 255 255 / 0.1);
  color: #fff;
}
.fb-round:hover {
  background: rgb(255 255 255 / 0.16);
}
</style>
