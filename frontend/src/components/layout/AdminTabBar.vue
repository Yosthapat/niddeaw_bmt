<script setup lang="ts">
/**
 * The admin's screens at the bottom of a phone, the way the public site
 * keeps its own (PublicTabBar.vue): a bar of glass a thumb reaches. The four
 * a club night runs on — dashboard, check-in, pairing, billing — and
 * "เพิ่มเติม", which opens the rest as a sheet above the bar. From 900px the
 * glass bar at the top (AppHeader.vue) carries them instead.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ADMIN_PAGES, MORE_ICON } from './adminPages'
import SlidePill from '@/components/common/SlidePill.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const { t } = useI18n()

const night = ADMIN_PAGES.filter((p) => p.night)
const rest = ADMIN_PAGES.filter((p) => p.listed && !p.night)
const open = ref(false)
const onRest = computed(() => rest.some((p) => p.to === route.path))
watch(
  () => route.path,
  () => {
    open.value = false
  },
)

function logout(): void {
  open.value = false
  auth.logout()
  void router.push('/admin/login')
}
</script>

<template>
  <div class="min-[900px]:hidden">
    <Transition name="more-sheet">
      <div v-if="open" class="fixed inset-0 z-30 bg-black/50" aria-hidden="true" @click="open = false" />
    </Transition>
    <Transition name="more-sheet">
      <div
        v-if="open"
        id="admin-more"
        class="glass-bar fixed inset-x-3 z-30 rounded-[28px] p-3"
        style="bottom: calc(90px + env(safe-area-inset-bottom, 0px)); background: rgb(22 10 42 / 0.96)"
        role="dialog"
        :aria-label="t('admin.moreTitle')"
      >
        <p class="px-2 pt-1 pb-2 font-display text-sm font-bold text-white/70">{{ t('admin.moreTitle') }}</p>
        <div class="grid grid-cols-3 gap-1.5">
          <RouterLink
            v-for="p in rest"
            :key="p.to"
            :to="p.to"
            :aria-current="route.path === p.to ? 'page' : undefined"
            class="flex min-h-[74px] flex-col items-center justify-center gap-1.5 rounded-2xl px-1 text-center text-[13px] leading-tight"
            :class="route.path === p.to ? 'glass-drop' : 'bg-white/6 text-white/85'"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" class="h-6 w-6" aria-hidden="true">
              <path :d="p.icon" />
            </svg>
            {{ t(`admin.nav.${p.nav}`) }}
          </RouterLink>
        </div>
        <div class="mt-2 flex gap-1.5">
          <RouterLink to="/" class="flex min-h-11 flex-1 items-center justify-center rounded-full bg-white/6 text-sm text-white/75">{{ t('admin.toSite') }}</RouterLink>
          <button type="button" class="flex min-h-11 flex-1 items-center justify-center rounded-full border border-white/15 text-sm text-white/75" @click="logout">
            {{ t('admin.nav.logout') }}
          </button>
        </div>
      </div>
    </Transition>

    <nav
      :aria-label="t('admin.nav.label')"
      class="glass-bar fixed inset-x-3 z-30 grid h-16 grid-cols-5 gap-0.5 rounded-full p-1.5"
      style="bottom: calc(14px + env(safe-area-inset-bottom, 0px))"
    >
      <SlidePill :watch-key="[route.path, open]" />
      <RouterLink v-for="p in night" :key="p.to" v-slot="{ href, navigate }" :to="p.to" custom>
        <a
          :href="href"
          :aria-current="route.path === p.to ? 'page' : undefined"
          :data-pill-on="route.path === p.to && !open ? '' : undefined"
          class="relative z-[1] flex min-w-0 flex-col items-center justify-center gap-0.5 rounded-full text-[10.5px] leading-none transition-colors"
          :class="route.path === p.to && !open ? 'text-white' : 'text-white/75 hover:text-white'"
          @click="navigate"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" :stroke-width="route.path === p.to ? 2.2 : 1.9" stroke-linecap="round" stroke-linejoin="round" class="h-[22px] w-[22px]" aria-hidden="true">
            <path :d="p.icon" />
          </svg>
          {{ t(`admin.nav.${p.nav}`) }}
        </a>
      </RouterLink>
      <button
        type="button"
        :data-pill-on="open || onRest ? '' : undefined"
        class="relative z-[1] flex min-w-0 flex-col items-center justify-center gap-0.5 rounded-full text-[10.5px] leading-none transition-colors"
        :class="open || onRest ? 'text-white' : 'text-white/75 hover:text-white'"
        :aria-expanded="open"
        aria-controls="admin-more"
        @click="open = !open"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" class="h-[22px] w-[22px]" aria-hidden="true">
          <path :d="MORE_ICON" />
        </svg>
        {{ t('admin.more') }}
      </button>
    </nav>
  </div>
</template>

<style scoped>
.more-sheet-enter-active,
.more-sheet-leave-active {
  transition:
    opacity 0.18s ease,
    transform 0.18s ease;
}
.more-sheet-enter-from,
.more-sheet-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
@media (prefers-reduced-motion: reduce) {
  .more-sheet-enter-active,
  .more-sheet-leave-active {
    transition: none;
  }
}
</style>
