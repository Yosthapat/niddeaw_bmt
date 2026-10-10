<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const { t } = useI18n()

const links = computed(() => [
  { to: '/admin', label: t('admin.nav.dashboard') },
  { to: '/admin/checkin', label: t('admin.nav.checkin') },
  { to: '/admin/members', label: t('admin.nav.members') },
  { to: '/admin/matchmaking', label: t('admin.nav.matchmaking') },
  { to: '/admin/billing', label: t('admin.nav.billing') },
  { to: '/admin/expenses', label: t('admin.nav.expenses') },
  { to: '/admin/revenue', label: t('admin.nav.revenue') },
  { to: '/admin/settings', label: t('admin.nav.settings') },
  { to: '/admin/activity-log', label: t('admin.nav.activityLog') },
])

// Nine destinations wrapped onto three rows on a phone, so every admin
// screen opened a third of the way down. One scrolling row costs a strip
// instead — at the price of the off-screen items, which is why the current
// one is scrolled into view rather than left wherever the strip happened
// to be.
const strip = ref<HTMLElement | null>(null)

watch(
  () => route.path,
  async () => {
    await nextTick()
    const active = strip.value?.querySelector<HTMLElement>('[data-active="true"]')
    // inline centres it horizontally; block: 'nearest' keeps the page from
    // scrolling vertically just to satisfy the nav.
    active?.scrollIntoView({ inline: 'center', block: 'nearest' })
  },
  { immediate: true },
)

function logout(): void {
  authStore.logout()
  router.push('/admin/login')
}
</script>

<template>
  <nav class="mx-auto max-w-4xl px-4 pt-4">
    <div ref="strip" class="admin-nav-strip flex items-center gap-1.5 overflow-x-auto text-sm">
      <RouterLink
        v-for="link in links"
        :key="link.to"
        :to="link.to"
        :data-active="route.path === link.to"
        class="hud-panel shrink-0 px-3 py-1.5 font-semibold whitespace-nowrap transition-colors"
        :class="
          route.path === link.to
            ? 'bg-brand-pink text-brand-black'
            : 'bg-brand-surface text-white/60 hover:bg-brand-surface-raised hover:text-white'
        "
      >
        {{ link.label }}
      </RouterLink>
      <span class="mx-1 h-5 w-px shrink-0 bg-white/15" aria-hidden="true" />
      <button
        class="hud-panel shrink-0 border border-white/15 px-3 py-1.5 whitespace-nowrap text-white/50 hover:border-white/30 hover:text-white"
        @click="logout"
      >
        {{ t('admin.nav.logout') }}
      </button>
    </div>
  </nav>
</template>

<style scoped>
/* The strip is swiped, not dragged by its bar — and a visible bar under a
   row of buttons reads as a stray line on a dark panel. The edges fade
   instead, so a half-cut button reads as "there is more that way" rather
   than as a layout bug. */
.admin-nav-strip {
  scrollbar-width: none;
  -ms-overflow-style: none;
  -webkit-mask-image: linear-gradient(
    to right,
    transparent 0,
    #000 1.25rem,
    #000 calc(100% - 1.25rem),
    transparent 100%
  );
  mask-image: linear-gradient(
    to right,
    transparent 0,
    #000 1.25rem,
    #000 calc(100% - 1.25rem),
    transparent 100%
  );
}
.admin-nav-strip::-webkit-scrollbar {
  display: none;
}
</style>
