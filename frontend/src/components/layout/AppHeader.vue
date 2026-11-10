<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ADMIN_PAGES } from './adminPages'
import { setLocale } from '@/i18n'
import LanguageSwitcher from './LanguageSwitcher.vue'
import SlidePill from '@/components/common/SlidePill.vue'
import { shownPath } from '@/composables/usePageSwap'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const { t, locale } = useI18n()

// Inside /admin the club's own nav is dead weight: the admin screens carry
// their own strip of nine destinations directly below this bar, so the
// header was a second row of navigation competing with it — five links to
// pages nobody opens mid-night, above the nine they actually use. What is
// left is the way back out to the site and the language switch.
const isAdmin = computed(() => route.path.startsWith('/admin'))
const isLogin = computed(() => route.path === '/admin/login')
// The night's four, then the office screens that fit beside them on a wide
// screen (members, shop, credit, revenue); everything else under "เพิ่มเติม".
const barPages = ADMIN_PAGES.filter((p) => p.night || ['members', 'shop', 'credit', 'revenue'].includes(p.nav))
const morePages = ADMIN_PAGES.filter((p) => p.listed && !p.night)
const onMore = computed(() => morePages.some((p) => p.to === route.path && !barPages.includes(p)))
const moreOpen = ref(false)
watch(
  () => route.path,
  () => {
    moreOpen.value = false
  },
)
function logout(): void {
  moreOpen.value = false
  auth.logout()
  void router.push('/admin/login')
}
// The menu and search pages are full screens with their own back arrow,
// the way Facebook opens them; the bar would only be a second way out.
// Read off the page on screen, not the route: the route changes as ☰ is
// tapped, while the page it leaves is still fading out underneath.
const ownBar = computed(() => {
  const path = shownPath.value ?? route.path
  return path === '/menu' || path === '/search'
})

// Fetch the pages behind ☰, 🔍 and the tab bar while the phone is idle,
// so the first tap on each has no download to wait for — that wait was a
// blank screen between two pages. They are small, and cached after.
onMounted(() => {
  const warm = (): void => {
    void import('@/views/public/MenuView.vue')
    void import('@/views/public/SearchView.vue')
    void import('@/views/public/MemberListView.vue')
    void import('@/views/public/RankingView.vue')
    void import('@/views/public/LiveView.vue')
    void import('@/views/public/MatchHistoryView.vue')
    void import('@/views/public/ShopView.vue')
  }
  if ('requestIdleCallback' in window) window.requestIdleCallback(warm)
  else setTimeout(warm, 2000)
})

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
  { to: '/shop', label: t('nav.shop') },
])

// A member's profile is still "Members", a match's detail still "Matches".
function isActive(to: string): boolean {
  return to === '/' ? route.path === '/' : route.path === to || route.path.startsWith(`${to}/`)
}
</script>

<template>
  <template v-if="isAdmin">
    <!-- Admin on a phone: the club and the language, as on the public site;
         the screens themselves are in the bar at the bottom (AdminTabBar). -->
    <header class="sticky top-0 z-20 flex h-[var(--header-h)] items-center justify-between border-b border-white/8 bg-[#0b0518] pr-3 pl-3 min-[900px]:hidden">
      <RouterLink to="/admin" class="flex h-11 min-w-0 items-center gap-2">
        <img src="/pwa-icons/pwa-192x192.png" alt="นิดเดียว Badminton Club logo" width="34" height="34" class="h-[34px] w-[34px] shrink-0 rounded-full" />
        <span class="truncate font-display text-[20px] font-bold tracking-tight text-white">นิดเดียว<span class="text-brand-pink">BMT</span></span>
        <span class="admin-chip">ADMIN</span>
      </RouterLink>
      <button type="button" class="fb-round font-display text-[13px] font-bold" :aria-label="t('nav.switchLang')" @click="toggleLocale">
        {{ locale === 'th' ? 'TH' : 'EN' }}
      </button>
    </header>

    <!-- Admin from 900px: the public site's floating bar of glass, with the
         night's four screens, the office ones, and the rest under "เพิ่มเติม". -->
    <header class="pointer-events-none sticky top-0 z-20 hidden h-[var(--header-h)] items-center justify-center px-4 min-[900px]:flex">
      <div class="glass-bar pointer-events-auto relative flex h-16 items-center gap-1 rounded-full pr-2.5 pl-3">
        <SlidePill v-if="!isLogin" :watch-key="[route.path, moreOpen]" />
        <RouterLink to="/admin" class="mr-1 flex min-h-11 shrink-0 items-center gap-2.5 border-r border-white/15 pr-3">
          <img src="/pwa-icons/pwa-192x192.png" alt="นิดเดียว Badminton Club logo" width="40" height="40" class="h-10 w-10 rounded-full ring-2 ring-white/30" />
          <span class="admin-chip">ADMIN</span>
        </RouterLink>
        <template v-if="!isLogin">
          <nav :aria-label="t('admin.nav.label')" class="flex items-center gap-0.5">
            <RouterLink v-for="p in barPages" :key="p.to" v-slot="{ href, navigate }" :to="p.to" custom>
              <a
                :href="href"
                :aria-current="route.path === p.to ? 'page' : undefined"
                :data-pill-on="route.path === p.to && !moreOpen ? '' : undefined"
                class="relative z-[1] flex h-[46px] items-center rounded-full text-[14px] whitespace-nowrap transition-colors"
                :class="[route.path === p.to && !moreOpen ? 'px-4 font-medium text-white' : 'px-3 text-white/80 hover:text-white', p.night ? '' : 'max-[1279px]:hidden']"
                @click="navigate"
              >
                {{ t(`admin.nav.${p.nav}`) }}
              </a>
            </RouterLink>
          </nav>
          <button
            type="button"
            :data-pill-on="moreOpen || onMore ? '' : undefined"
            class="relative z-[1] flex h-[46px] items-center gap-1 rounded-full px-3 text-[14px] whitespace-nowrap transition-colors"
            :class="moreOpen || onMore ? 'text-white' : 'text-white/80 hover:text-white'"
            :aria-expanded="moreOpen"
            aria-controls="admin-more-desktop"
            @click="moreOpen = !moreOpen"
          >
            {{ t('admin.more') }}
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4" :class="{ 'rotate-180': moreOpen }" aria-hidden="true"><path d="m6 9 6 6 6-6" /></svg>
          </button>
          <div v-if="moreOpen" class="fixed inset-0 z-0" aria-hidden="true" @click="moreOpen = false" />
          <div
            v-if="moreOpen"
            id="admin-more-desktop"
            class="glass-bar more-menu absolute top-[calc(100%+10px)] right-0 z-10 w-64 rounded-3xl p-2"
          >
            <RouterLink
              v-for="p in morePages"
              :key="p.to"
              :to="p.to"
              :aria-current="route.path === p.to ? 'page' : undefined"
              class="flex min-h-11 items-center gap-3 rounded-2xl px-3 text-[14px]"
              :class="[route.path === p.to ? 'glass-drop' : 'text-white/85 hover:bg-white/8', p.listed && barPages.includes(p) ? 'min-[1280px]:hidden' : '']"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5 shrink-0 opacity-80" aria-hidden="true"><path :d="p.icon" /></svg>
              {{ t(`admin.nav.${p.nav}`) }}
            </RouterLink>
            <div class="my-1.5 h-px bg-white/10" />
            <RouterLink to="/" class="flex min-h-11 items-center rounded-2xl px-3 text-[14px] text-white/70 hover:bg-white/8">{{ t('admin.toSite') }}</RouterLink>
            <button type="button" class="flex min-h-11 w-full items-center rounded-2xl px-3 text-left text-[14px] text-white/70 hover:bg-white/8" @click="logout">{{ t('admin.nav.logout') }}</button>
          </div>
        </template>
        <LanguageSwitcher glass class="ml-1.5 shrink-0" />
      </div>
    </header>
  </template>

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
    <div class="glass-bar pointer-events-auto relative flex h-16 items-center gap-1.5 rounded-full pr-2.5 pl-3">
      <SlidePill :watch-key="route.path" />
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
            :data-pill-on="isActive(link.to) ? '' : undefined"
            class="relative z-[1] flex h-[46px] items-center rounded-full text-[15px] whitespace-nowrap transition-colors"
            :class="isActive(link.to) ? 'px-5 font-medium text-white' : 'px-4 text-white/80 hover:text-white'"
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
.more-menu {
  /* solid enough that the page under it doesn't read through */
  background: rgb(22 10 42 / 0.96);
}
.admin-chip {
  border-radius: 999px;
  background: rgb(234 76 164 / 0.18);
  border: 1px solid rgb(255 143 208 / 0.45);
  padding: 2px 8px;
  font: 700 11px 'Chakra Petch', sans-serif;
  letter-spacing: 0.12em;
  color: #ffc2e3;
}
</style>
