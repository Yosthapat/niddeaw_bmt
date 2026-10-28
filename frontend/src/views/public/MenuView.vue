<script setup lang="ts">
/**
 * What ☰ opens on a phone, the way Facebook's menu page works: the club
 * where FB puts your profile, then a grid of shortcuts to every corner of
 * the site — the six in the tab bar and the ones that don't fit there
 * (Hall of Fame, the eight tiers, the tournament) — then the club's
 * contacts, the language and, last and quietest, the organisers' login.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { setLocale, type Locale } from '@/i18n'
import { useAuthStore } from '@/stores/auth'
import { useLiveNow } from '@/composables/useLiveNow'
import { useTierInfoModal } from '@/composables/useTierInfoModal'
import { TIER_ORDER } from '@/utils/tierCard'
import TierMascot from '@/components/players/TierMascot.vue'

const { t, locale } = useI18n()
const router = useRouter()
const authStore = useAuthStore()
const { playing } = useLiveNow()
const tierInfo = useTierInfoModal()

// Back to wherever ☰ was pressed; home when the menu was opened directly.
function back(): void {
  if (window.history.state?.back) router.back()
  else router.push('/')
}

const shortcuts = computed(() => [
  {
    to: '/members',
    label: t('nav.members'),
    color: '#7fb6ff',
    icon: 'M16 19v-1a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v1M9.5 10a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7ZM21 19v-1a4 4 0 0 0-3-3.8M15.5 3.2a3.5 3.5 0 0 1 0 6.6',
  },
  {
    to: '/ranking',
    label: t('nav.ranking'),
    color: '#ffcf3f',
    icon: 'M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0zM17 6h3v2a3 3 0 0 1-3 3M7 6H4v2a3 3 0 0 0 3 3',
  },
  {
    to: '/live',
    label: t('nav.live'),
    color: '#ff4d6d',
    icon: 'M12 13a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3ZM8.5 15.5a5 5 0 0 1 0-7M15.5 8.5a5 5 0 0 1 0 7M5.6 18.4a9 9 0 0 1 0-12.8M18.4 5.6a9 9 0 0 1 0 12.8',
    tag: playing.value ? { text: 'LIVE', cls: 'bg-[#ff4d6d] text-white' } : null,
  },
  { to: '/matches', label: t('nav.matches'), color: '#c9b6ff', icon: 'M4 5h16v14H4zM12 5v14M7.5 10v4M16.5 10v4' },
  {
    to: '/hall-of-fame',
    label: t('nav.hallOfFame'),
    color: '#ffe14d',
    icon: 'M12 3l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.4l-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z',
  },
  {
    to: '/shop',
    label: t('nav.shop'),
    color: '#ff6cc0',
    icon: 'M4 9.5 5.5 4h13L20 9.5M4 9.5h16M4 9.5a2.7 2.7 0 0 0 5.3 0 2.7 2.7 0 0 0 5.4 0 2.7 2.7 0 0 0 5.3 0M5.5 12.5V20h13v-7.5M10 20v-4h4v4',
  },
  {
    to: '/tournament',
    label: t('nav.tournament'),
    color: '#7ff0b4',
    icon: 'M4 6h5v4H4zM4 14h5v4H4zM15 10h5v4h-5zM9 8h3v8H9M12 12h3',
    tag: { text: t('menu.soon'), cls: 'bg-[#ffe14d] text-[#2a1a00]' },
  },
])

// Own-drawn line icons, the same pair as the home page's contact block.
const contacts = computed(() => [
  {
    label: t('menu.line'),
    href: 'https://line.me/R/ti/p/@369iojcn',
    bg: 'bg-[#037f36]',
    icon: 'M21 11.5C21 7.4 17 4 12 4S3 7.4 3 11.5c0 3.7 3.2 6.8 7.6 7.4l-.6 2.6 3.9-2.6C18 18.3 21 15.2 21 11.5Z',
  },
  {
    label: t('menu.tiktok'),
    href: 'https://www.tiktok.com/@nidde4w',
    bg: 'bg-white/10',
    icon: 'M14 4v10.5a3.5 3.5 0 1 1-3.5-3.5M14 4c.5 2.5 2.5 4 5 4',
  },
])

const languages: { id: Locale; label: string }[] = [
  { id: 'th', label: 'ไทย' },
  { id: 'en', label: 'EN' },
]
</script>

<template>
  <main class="mx-auto max-w-xl px-3 pb-6">
    <header class="flex h-16 items-center justify-between pr-0 pl-0">
      <div class="flex items-center gap-0.5">
        <button type="button" class="flex h-11 w-11 items-center justify-center" :aria-label="t('menu.close')" @click="back">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" class="h-[22px] w-[22px]" aria-hidden="true">
            <path d="m15 6-6 6 6 6" />
          </svg>
        </button>
        <h1 class="font-display text-[26px] font-bold">{{ t('nav.menu') }}</h1>
      </div>
      <RouterLink to="/search" class="flex h-11 w-11 items-center justify-center rounded-full bg-white/10" :aria-label="t('nav.search')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" class="h-[22px] w-[22px]" aria-hidden="true">
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-3.5-3.5" />
        </svg>
      </RouterLink>
    </header>

    <div class="flex flex-col gap-3.5 pt-1">
      <!-- the club, where FB puts "your profile" -->
      <RouterLink to="/" class="menu-row min-h-[68px]">
        <img src="/pwa-icons/pwa-192x192.png" alt="" width="46" height="46" class="h-[46px] w-[46px] rounded-full ring-2 ring-brand-pink" />
        <span class="flex min-w-0 flex-1 flex-col">
          <span class="text-base font-medium">นิดเดียว Badminton Club</span>
          <span class="text-xs text-white/60">{{ t('home.hero.when') }}</span>
        </span>
      </RouterLink>

      <h2 class="text-sm font-medium text-white/75">{{ t('menu.shortcuts') }}</h2>
      <!-- The last tile takes the whole row when it would be left alone. -->
      <div class="grid grid-cols-2 gap-2">
        <RouterLink
          v-for="(s, i) in shortcuts"
          :key="s.to"
          :to="s.to"
          class="menu-tile"
          :class="{ 'col-span-2': i === shortcuts.length - 1 && shortcuts.length % 2 === 1 }"
        >
          <svg viewBox="0 0 24 24" fill="none" :stroke="s.color" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" class="h-7 w-7" aria-hidden="true">
            <path :d="s.icon" />
          </svg>
          <span class="text-[15px] font-medium">{{ s.label }}</span>
          <span v-if="s.tag" class="absolute top-2.5 right-2.5 rounded-full px-2 py-1 text-[11px] leading-none" :class="s.tag.cls">
            {{ s.tag.text }}
          </span>
        </RouterLink>
      </div>

      <!-- the eight tiers: each mascot opens its own card -->
      <section class="menu-tile h-auto! gap-3!" :aria-labelledby="'menu-tiers'">
        <h2 id="menu-tiers" class="text-[15px] font-medium">{{ t('menu.tiers') }}</h2>
        <div class="grid grid-cols-8 gap-1">
          <button
            v-for="tier in TIER_ORDER"
            :key="tier"
            type="button"
            class="flex min-h-11 items-center justify-center rounded-xl hover:bg-white/8"
            :aria-label="t('menu.tierAbout', { tier: tier.charAt(0).toUpperCase() + tier.slice(1) })"
            @click="tierInfo.open(tier)"
          >
            <TierMascot :tier="tier" :size="34" :interactive="false" />
          </button>
        </div>
      </section>

      <h2 class="text-sm font-medium text-white/75">{{ t('menu.contact') }}</h2>
      <div class="flex flex-col gap-1.5">
        <a v-for="c in contacts" :key="c.href" :href="c.href" target="_blank" rel="noopener noreferrer" class="menu-row">
          <span class="flex h-10 w-10 flex-none items-center justify-center rounded-full" :class="c.bg">
            <svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5" aria-hidden="true">
              <path :d="c.icon" />
            </svg>
          </span>
          <span class="flex-1">{{ c.label }}</span>
        </a>
      </div>

      <div class="flex items-center gap-3">
        <span id="menu-lang" class="flex-1 text-sm text-white/75">{{ t('menu.language') }}</span>
        <div role="radiogroup" aria-labelledby="menu-lang" class="flex w-[150px] rounded-xl bg-white/8 p-1">
          <button
            v-for="l in languages"
            :key="l.id"
            type="button"
            role="radio"
            :aria-checked="locale === l.id"
            class="h-10 flex-1 rounded-[9px] text-sm"
            :class="locale === l.id ? 'bg-white font-medium text-[#1a0d33]' : 'text-white/75'"
            @click="setLocale(l.id)"
          >
            {{ l.label }}
          </button>
        </div>
      </div>

      <RouterLink
        :to="authStore.isAuthenticated ? '/admin' : '/admin/login'"
        class="flex h-12 items-center justify-center rounded-xl bg-white/8 text-sm text-white/75 hover:text-white"
      >
        {{ authStore.isAuthenticated ? t('menu.toAdmin') : t('menu.adminLogin') }}
      </RouterLink>
    </div>
  </main>
</template>

<style scoped>
.menu-row {
  display: flex;
  min-height: 56px;
  align-items: center;
  gap: 12px;
  padding: 0 12px;
  border-radius: 12px;
  background: #1a1226;
  box-shadow: 0 2px 0 rgb(0 0 0 / 0.35);
}
.menu-row:hover,
.menu-tile:hover {
  background: #231833;
}
.menu-tile {
  position: relative;
  display: flex;
  height: 92px;
  flex-direction: column;
  justify-content: space-between;
  gap: 10px;
  padding: 12px;
  border: 1px solid rgb(255 255 255 / 0.08);
  border-radius: 14px;
  background: #1a1226;
  box-shadow: 0 2px 0 rgb(0 0 0 / 0.35);
}
</style>
