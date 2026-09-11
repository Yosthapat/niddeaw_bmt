<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    images: string[]
    intervalMs?: number
  }>(),
  { intervalMs: 5000 },
)

const activeIndex = ref(0)
let timerId: ReturnType<typeof setInterval> | null = null

function stop(): void {
  if (timerId !== null) {
    clearInterval(timerId)
    timerId = null
  }
}

function start(): void {
  stop()
  if (props.images.length <= 1) return
  timerId = setInterval(() => {
    activeIndex.value = (activeIndex.value + 1) % props.images.length
  }, props.intervalMs)
}

function goTo(i: number): void {
  activeIndex.value = i
  start()
}

watch(
  () => props.images.length,
  () => {
    activeIndex.value = 0
    start()
  },
)

onMounted(start)
onUnmounted(stop)
</script>

<template>
  <!-- The frame is pinned to the current banner's aspect ratio so it sits
       flush with no letterboxing. Other ratios still render fine — the
       images are object-contain, so an odd one gets bars rather than a
       crop — but swapping the banner is a good moment to re-check this. -->
  <div
    v-if="images.length > 0"
    class="hud-panel relative aspect-[1812/750] w-full overflow-hidden border border-brand-pink/20 bg-brand-black"
  >
    <img
      v-for="(src, i) in images"
      :key="src"
      :src="src"
      alt=""
      class="absolute inset-0 h-full w-full object-contain transition-opacity duration-700 ease-out"
      :class="i === activeIndex ? 'opacity-100' : 'opacity-0'"
    />
    <div v-if="images.length > 1" class="absolute bottom-2 left-1/2 flex -translate-x-1/2 gap-1.5">
      <button
        v-for="(src, i) in images"
        :key="`dot-${src}`"
        type="button"
        class="h-1.5 rounded-full transition-all"
        :class="i === activeIndex ? 'w-4 bg-brand-pink' : 'w-1.5 bg-white/40'"
        :aria-label="`Slide ${i + 1}`"
        @click="goTo(i)"
      />
    </div>
  </div>
</template>
