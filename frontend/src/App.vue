<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import type { RouteLocationNormalizedLoaded } from 'vue-router'
import { pageEntered, pageEntering } from '@/composables/usePageSwap'
import AppHeader from '@/components/layout/AppHeader.vue'
import TierInfoModal from '@/components/players/TierInfoModal.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import AmbientBackground from '@/components/common/AmbientBackground.vue'
import UpdateBanner from '@/components/common/UpdateBanner.vue'
import PublicTabBar from '@/components/layout/PublicTabBar.vue'

const route = useRoute()

// The pages a phone flips between from the tab bar, kept rather than
// rebuilt: coming back to one is instant, with its data and its scroll,
// and each refreshes quietly behind (useRevisit.ts). A member's profile
// or one match is not kept — there are hundreds of those.
// Pages opened inside LINE (meta.bare) stand alone: no site header or tab
// bar around them, since LINE draws its own frame.
const bare = computed(() => route.meta.bare === true)

// A page is rebuilt when its key changes. Normally that is its path, but
// the LINE page's /line/checkout, /line/bills… are screens of one page:
// moving between them must not rebuild it, which would sign in with LINE
// all over again.
function pageKey(r: RouteLocationNormalizedLoaded): string {
  return r.name === 'line' ? 'line' : r.path
}

const KEPT = ['HomeView', 'MemberListView', 'RankingView', 'HallOfFameView', 'MatchHistoryView', 'ShopView']

// See usePageSwap.ts. The admin screens have no transition, nor does the
// first public page after one, so the page on screen is the route at once.
watch(
  () => route.path,
  (to, from) => {
    if (to.startsWith('/admin') || from?.startsWith('/admin')) pageEntering(to)
  },
)
</script>

<template>
  <!-- overflow-x: clip, not hidden: `clip` doesn't create a scroll
       container, so AppHeader's `position: sticky` still sticks to the
       viewport. `hidden` here would silently kill it.

       It exists because decorative glows are positioned to bleed past the
       content box — the home hero's old glow sat at inset:-20% and pushed the
       home page's scrollWidth to 448 in a 400px viewport, letting the whole
       page be dragged sideways on a phone. Only the off-screen part is
       clipped, so nothing that was ever visible changes. Browsers without
       `overflow: clip` just ignore the line and behave as before. -->
  <div class="min-h-dvh overflow-x-clip">
    <AmbientBackground v-if="!route.path.startsWith('/admin')" />
    <AppHeader v-if="!bare" />
    <RouterView v-slot="{ Component, route }">
      <!-- Admin views render <AdminNav /> and <main> as two sibling root
           nodes (no wrapping <div>), which <Transition> can't track — it
           needs a single root to attach enter/leave hooks to, and against
           a multi-root component the transition never resolves, leaving
           the page stuck invisible mid-transition until a manual reload.
           Public views are all single-root, so they keep the transition;
           admin routes render instantly instead. -->
      <!-- The main pages are kept rather than rebuilt when you leave them
           (KEPT): each came back as a blank screen, then skeletons, then
           its cards, every time a tab was tapped. Their loops and polls
           pause while they are away. -->
      <Transition
        v-if="!route.path.startsWith('/admin')"
        name="page"
        mode="out-in"
        @before-enter="pageEntering(route.path)"
        @enter="pageEntered()"
      >
        <KeepAlive :include="KEPT" :max="8">
          <component :is="Component" :key="pageKey(route)" />
        </KeepAlive>
      </Transition>
      <component :is="Component" v-else :key="route.path" />
    </RouterView>
    <div v-if="!bare" class="signature-stripe" aria-hidden="true" />
    <!-- Room at the end of every public page for the tab bar floating
         over it, so the last line can scroll clear of the bar. -->
    <template v-if="!route.path.startsWith('/admin') && !bare">
      <div class="h-[calc(96px+env(safe-area-inset-bottom,0px))] min-[900px]:hidden" aria-hidden="true" />
      <PublicTabBar />
    </template>
    <TierInfoModal />
    <ConfirmDialog />
    <UpdateBanner />
  </div>
</template>
