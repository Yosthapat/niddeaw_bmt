<script setup lang="ts">
import AppHeader from '@/components/layout/AppHeader.vue'
import TierInfoModal from '@/components/players/TierInfoModal.vue'
</script>

<template>
  <div class="min-h-screen bg-brand-black">
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
    <TierInfoModal />
  </div>
</template>
