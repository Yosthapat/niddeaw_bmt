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
  <div
    v-if="images.length > 0"
    class="hud-panel relative aspect-[21/5] w-full overflow-hidden border border-brand-pink/20 bg-brand-black sm:aspect-[16/3.2]"
  >
    <img
      v-for="(src, i) in images"
      :key="src"
      :src="src"
      alt=""
      class="absolute inset-0 h-full w-full object-cover transition-opacity duration-700 ease-out"
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
