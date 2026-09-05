<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import LanguageSwitcher from './LanguageSwitcher.vue'

const route = useRoute()
const authStore = useAuthStore()
const { t, locale } = useI18n()

// Hall of Fame nav link is temporarily hidden (not in use yet) — the
// /hall-of-fame route and view still exist, just unlinked from the header.
const publicLinks = computed(() => [
  { to: '/', label: t('nav.home') },
  { to: '/members', label: t('nav.members') },
  { to: '/ranking', label: t('nav.ranking') },
  { to: '/live', label: t('nav.live') },
  { to: '/matches', label: t('nav.matches') },
])

// Active-link indicator: measured against the real active <a> instead of a
// per-link v-if bar, so it slides to the new position on navigation rather
// than teleporting.
const navRef = ref<HTMLElement | null>(null)
const linkRefs = new Map<string, HTMLElement>()

function setLinkRef(path: string, el: Element | null): void {
  if (el instanceof HTMLElement) linkRefs.set(path, el)
  else linkRefs.delete(path)
}

const underlineStyle = ref({ left: '0px', width: '0px', opacity: '0' })

function updateUnderline(): void {
  const activeLink = publicLinks.value.find((l) => l.to === route.path)
  const linkEl = activeLink ? linkRefs.get(activeLink.to) : undefined
  if (!linkEl || !navRef.value) {
    underlineStyle.value = { left: '0px', width: '0px', opacity: '0' }
    return
  }
  const navRect = navRef.value.getBoundingClientRect()
  const linkRect = linkEl.getBoundingClientRect()
  underlineStyle.value = {
    left: `${linkRect.left - navRect.left}px`,
    width: `${linkRect.width}px`,
    opacity: '1',
  }
}

async function refreshUnderline(): Promise<void> {
  await nextTick()
  updateUnderline()
}

onMounted(() => {
  refreshUnderline()
  window.addEventListener('resize', updateUnderline)
})
onUnmounted(() => window.removeEventListener('resize', updateUnderline))
watch(() => route.path, refreshUnderline)
// Switching language changes label text width, so the bar needs to
// re-measure even though the route didn't change.
watch(locale, refreshUnderline)
</script>

<template>
  <header class="sticky top-0 z-10 border-b border-brand-pink/20 bg-brand-black/95 backdrop-blur">
    <div class="mx-auto flex max-w-5xl items-center gap-4 px-4 py-3">
      <RouterLink to="/" class="flex shrink-0 items-center gap-2.5">
        <span class="hud-panel bg-brand-pink p-0.5">
          <img src="/pwa-icons/pwa-64x64.png" alt="นิดเดียว Badminton Club logo" class="hud-panel block h-8 w-8" />
        </span>
        <span class="hidden font-display text-base font-bold tracking-wide text-white sm:inline">
          นิดเดียว<span class="text-brand-pink">BMT</span>
        </span>
      </RouterLink>

      <nav ref="navRef" class="relative flex flex-1 gap-4 text-xs font-semibold tracking-wider uppercase sm:gap-5">
        <RouterLink
          v-for="link in publicLinks"
          :key="link.to"
          v-slot="{ href, navigate }"
          :to="link.to"
          custom
        >
          <a
            :ref="(el) => setLinkRef(link.to, el as Element | null)"
            :href="href"
            :aria-current="route.path === link.to ? 'page' : undefined"
            class="whitespace-nowrap py-2 transition-colors"
            :class="route.path === link.to ? 'text-brand-pink' : 'text-white/50 hover:text-white'"
            @click="navigate"
          >
            {{ link.label }}
          </a>
        </RouterLink>
        <span class="nav-underline pointer-events-none absolute -bottom-px h-0.5 bg-brand-pink" :style="underlineStyle" />
      </nav>

      <LanguageSwitcher class="shrink-0" />

      <RouterLink
        :to="authStore.isAuthenticated ? '/admin' : '/admin/login'"
        class="hud-panel shrink-0 whitespace-nowrap border border-brand-pink/50 p-2 text-xs font-semibold tracking-wide text-brand-pink-light uppercase hover:border-brand-pink hover:bg-brand-pink/10 sm:px-3 sm:py-1.5"
        :aria-label="authStore.isAuthenticated ? t('nav.admin') : t('nav.adminLogin')"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4 sm:hidden">
          <rect x="5" y="11" width="14" height="9" rx="1.5" />
          <path d="M8 11V7a4 4 0 0 1 8 0v4" />
        </svg>
        <span class="hidden sm:inline">{{ authStore.isAuthenticated ? t('nav.admin') : t('nav.adminLogin') }}</span>
      </RouterLink>
    </div>
  </header>
</template>
