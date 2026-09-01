<script setup lang="ts">
import AppHeader from '@/components/layout/AppHeader.vue'
import TierInfoModal from '@/components/players/TierInfoModal.vue'
</script>

<template>
  <div class="min-h-screen bg-brand-black">
    <AppHeader />
    <RouterView />
    <TierInfoModal />
  </div>
</template>
