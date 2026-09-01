<script setup lang="ts">
import AppHeader from '@/components/layout/AppHeader.vue'
import TierInfoModal from '@/components/players/TierInfoModal.vue'
</script>

<template>
  <div class="min-h-screen bg-brand-black">
    <AppHeader />
    <RouterView v-slot="{ Component, route }">
      <Transition name="page" mode="out-in">
        <component :is="Component" :key="route.path" />
      </Transition>
    </RouterView>
    <TierInfoModal />
  </div>
</template>
