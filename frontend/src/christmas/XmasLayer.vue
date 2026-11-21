<script setup lang="ts">
/**
 * Everything the season lays over the public pages: the snow, the lights
 * and the Christmas music button. Mounted once in App.vue, and only in the
 * season (season.ts), so outside it none of this is even downloaded. It
 * stays mounted from page to page, so the song keeps playing as a member
 * moves around the site.
 */
import { computed, onBeforeUnmount, ref } from 'vue'
import { useRoute } from 'vue-router'
import SnowLayer from './SnowLayer.vue'
import XmasLights from './XmasLights.vue'
import XmasMusic from './XmasMusic.vue'

const route = useRoute()
// /menu and /search draw their own bar in place of the phone's header.
const ownBar = computed(() => route.path === '/menu' || route.path === '/search')
const wideQuery = window.matchMedia('(min-width: 900px)')
const wide = ref(wideQuery.matches)
const onWide = (e: MediaQueryListEvent): void => {
  wide.value = e.matches
}
wideQuery.addEventListener('change', onWide)
onBeforeUnmount(() => wideQuery.removeEventListener('change', onWide))
</script>

<template>
  <SnowLayer />
  <XmasLights v-if="wide || !ownBar" :below-header="!wide" />
  <XmasMusic />
</template>
