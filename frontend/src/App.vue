<script setup lang="ts">
import { useRoute } from 'vue-router'
import AppHeader from '@/components/layout/AppHeader.vue'
import TierInfoModal from '@/components/players/TierInfoModal.vue'
import AmbientBackground from '@/components/common/AmbientBackground.vue'

const route = useRoute()
</script>

<template>
  <div class="min-h-screen">
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
  </div>
</template>
