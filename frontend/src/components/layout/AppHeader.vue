<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute } from 'vue-router'
import LanguageSwitcher from './LanguageSwitcher.vue'

const route = useRoute()
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
    <!-- Tighter gutters and gaps below sm: even without the admin button,
         the logo + five nav labels + language switcher ran ~31px past a
         400px phone and the whole bar scrolled sideways. Desktop keeps the
         roomier spacing. -->
    <div class="mx-auto flex max-w-5xl items-center gap-2.5 px-3 py-3 sm:gap-4 sm:px-4">
      <RouterLink to="/" class="flex shrink-0 items-center gap-2.5">
        <span class="hud-panel bg-brand-pink p-0.5">
          <img src="/pwa-icons/pwa-64x64.png" alt="นิดเดียว Badminton Club logo" class="hud-panel block h-8 w-8" />
        </span>
        <span class="hidden font-display text-base font-bold tracking-wide text-white sm:inline">
          นิดเดียว<span class="text-brand-pink">BMT</span>
        </span>
      </RouterLink>

      <nav ref="navRef" class="relative flex flex-1 gap-3 text-xs font-semibold tracking-wider uppercase sm:gap-5">
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

      <!-- The admin entry point lives at the bottom of the home page, next
           to the organiser contact block, not up here. Five nav links plus
           the language switcher already overflow a phone's width, and this
           is the one control in the bar that no member ever needs — see
           HomeView.vue. -->
      <LanguageSwitcher class="shrink-0" />
    </div>
  </header>
</template>
