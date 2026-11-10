<script setup lang="ts">
/**
 * The glass highlight behind the current item of a bar (the admin's bottom
 * bar on a phone, its glass bar at the top on a desktop), sliding to the
 * item that is tapped instead of jumping there.
 *
 * It stretches as it goes: the edge in the direction of travel leaves
 * first and the other one catches up, so the pill reaches toward the new
 * item and then gathers itself in. Put it as the first child of a
 * positioned container, mark the current item with `data-pill-on`, and pass
 * something that changes when the current item does as `watchKey`.
 */
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = withDefaults(defineProps<{ watchKey: unknown; tone?: 'glass' | 'pink' }>(), { tone: 'glass' })

const pill = ref<HTMLElement | null>(null)
const box = ref({ left: 0, right: 0, top: 0, bottom: 0 })
const shown = ref(false)
// no sliding for the first placement, or after the bar was resized
const animate = ref(false)
const lead = ref<'left' | 'right'>('right')
let observer: ResizeObserver | null = null

function place(slide: boolean): void {
  const host = pill.value?.parentElement
  const on = host?.querySelector<HTMLElement>('[data-pill-on]')
  if (!host || !on || on.offsetParent === null) {
    shown.value = false
    return
  }
  // offsets from the host, whatever sits in between
  let left = 0
  let top = 0
  for (let el: HTMLElement | null = on; el && el !== host; el = el.offsetParent as HTMLElement | null) {
    left += el.offsetLeft
    top += el.offsetTop
  }
  const next = {
    left,
    right: host.clientWidth - left - on.offsetWidth,
    top,
    bottom: host.clientHeight - top - on.offsetHeight,
  }
  lead.value = next.left >= box.value.left ? 'right' : 'left'
  animate.value = slide && shown.value
  box.value = next
  shown.value = true
}

watch(
  () => props.watchKey,
  () => void nextTick(() => place(true)),
)

onMounted(() => {
  void nextTick(() => place(false))
  const host = pill.value?.parentElement
  if (host && 'ResizeObserver' in window) {
    observer = new ResizeObserver(() => place(false))
    observer.observe(host)
  }
  // the bar's labels change width once its font has loaded
  void document.fonts?.ready.then(() => place(false))
})
onBeforeUnmount(() => observer?.disconnect())
</script>

<template>
  <span
    ref="pill"
    class="slide-pill"
    :class="[tone === 'pink' ? 'pink' : 'glass-drop', animate ? `lead-${lead}` : 'still', { off: !shown }]"
    :style="{ left: `${box.left}px`, right: `${box.right}px`, top: `${box.top}px`, bottom: `${box.bottom}px` }"
    aria-hidden="true"
  />
</template>

<style scoped>
.slide-pill {
  position: absolute;
  z-index: 0;
  border-radius: 9999px;
  pointer-events: none;
}
.slide-pill.pink {
  border-radius: 12px;
  background: var(--color-brand-pink);
  box-shadow: 0 4px 14px rgb(234 76 164 / 0.45);
}
.slide-pill.off {
  opacity: 0;
}
/* the leading edge goes first, the trailing edge catches up */
.slide-pill.lead-right {
  transition:
    right 0.26s cubic-bezier(0.3, 0.9, 0.3, 1),
    left 0.42s cubic-bezier(0.5, 0, 0.2, 1) 0.05s,
    top 0.3s ease,
    bottom 0.3s ease,
    opacity 0.2s ease;
}
.slide-pill.lead-left {
  transition:
    left 0.26s cubic-bezier(0.3, 0.9, 0.3, 1),
    right 0.42s cubic-bezier(0.5, 0, 0.2, 1) 0.05s,
    top 0.3s ease,
    bottom 0.3s ease,
    opacity 0.2s ease;
}
@media (prefers-reduced-motion: reduce) {
  .slide-pill.lead-left,
  .slide-pill.lead-right {
    transition: none;
  }
}
</style>
