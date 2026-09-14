<script setup lang="ts">
import { useRoute } from 'vue-router'
import AppHeader from '@/components/layout/AppHeader.vue'
import TierInfoModal from '@/components/players/TierInfoModal.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import AmbientBackground from '@/components/common/AmbientBackground.vue'

const route = useRoute()
</script>

<template>
  <!-- overflow-x: clip, not hidden: `clip` doesn't create a scroll
       container, so AppHeader's `position: sticky` still sticks to the
       viewport. `hidden` here would silently kill it.

       It exists because decorative glows are positioned to bleed past the
       content box — HomeView's .hero-aura sits at inset:-20% and pushed the
       home page's scrollWidth to 448 in a 400px viewport, letting the whole
       page be dragged sideways on a phone. Only the off-screen part is
       clipped, so nothing that was ever visible changes. Browsers without
       `overflow: clip` just ignore the line and behave as before. -->
  <div class="min-h-screen overflow-x-clip">
    <AmbientBackground v-if="!route.path.startsWith('/admin')" />
    <AppHeader />
    <RouterView v-slot="{ Component, route }">
      <!-- Admin views render <AdminNav /> and <main> as two sibling root
           nodes (no wrapping <div>), which <Transition> can't track — it
           needs a single root to attach enter/leave hooks to, and against
           a multi-root component the transition never resolves, leaving
           the page stuck invisible mid-transition until a manual reload.
           Public views are all single-root, so they keep the transition;
           admin routes render instantly instead. -->
      <Transition v-if="!route.path.startsWith('/admin')" name="page" mode="out-in">
        <component :is="Component" :key="route.path" />
      </Transition>
      <component :is="Component" v-else :key="route.path" />
    </RouterView>
    <div class="signature-stripe" aria-hidden="true" />
    <TierInfoModal />
    <ConfirmDialog />
  </div>
</template>
