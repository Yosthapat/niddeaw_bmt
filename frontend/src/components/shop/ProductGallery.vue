<script setup lang="ts">
/**
 * A product's photos, whole: a shirt photographed front and back with its
 * feature strip underneath is the photo, so nothing is cropped to fit a
 * square — it sits inside the frame instead. Swipe (or the arrows) between
 * them; tap one to open it full screen, where swiping goes on and the
 * print can be read.
 */
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{ images: string[]; name: string }>()
const { t } = useI18n()

const strip = ref<HTMLElement | null>(null)
const viewer = ref<HTMLElement | null>(null)
const closeBtn = ref<HTMLButtonElement | null>(null)
const at = ref(0)
const open = ref(false)
const shownAt = ref(0)
let opener: HTMLElement | null = null

const many = computed(() => props.images.length > 1)

function indexOf(el: HTMLElement | null): number {
  return el ? Math.round(el.scrollLeft / Math.max(1, el.clientWidth)) : 0
}

function go(el: HTMLElement | null, i: number, smooth = true): void {
  if (!el) return
  const n = props.images.length
  const to = (i + n) % n
  el.scrollTo({ left: to * el.clientWidth, behavior: smooth ? 'smooth' : 'auto' })
}

async function show(i: number, event: Event): Promise<void> {
  opener = event.currentTarget as HTMLElement
  shownAt.value = i
  open.value = true
  await nextTick()
  go(viewer.value, i, false)
  closeBtn.value?.focus()
}

function close(): void {
  open.value = false
  // Back on the page at the photo that was being looked at.
  go(strip.value, shownAt.value, false)
  opener?.focus()
}

function onKey(e: KeyboardEvent): void {
  if (!open.value) return
  if (e.key === 'Escape') close()
  else if (e.key === 'ArrowRight') go(viewer.value, shownAt.value + 1)
  else if (e.key === 'ArrowLeft') go(viewer.value, shownAt.value - 1)
}

watch(open, (isOpen) => {
  document.body.style.overflow = isOpen ? 'hidden' : ''
  if (isOpen) window.addEventListener('keydown', onKey)
  else window.removeEventListener('keydown', onKey)
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  document.body.style.overflow = ''
})
</script>

<template>
  <div class="flex flex-col gap-2.5">
    <div class="frame relative overflow-hidden rounded-[20px] border border-white/14">
      <div
        ref="strip"
        class="no-bar flex aspect-square snap-x snap-mandatory overflow-x-auto"
        @scroll="at = indexOf(strip)"
      >
        <template v-if="images.length">
          <button
            v-for="(url, i) in images"
            :key="url"
            type="button"
            class="h-full w-full flex-none cursor-zoom-in snap-center p-2"
            :aria-label="t('shop.photoOpen', { n: i + 1, of: images.length })"
            @click="show(i, $event)"
          >
            <img
              :src="url"
              :alt="`${name} ${i + 1}/${images.length}`"
              :loading="i === 0 ? 'eager' : 'lazy'"
              decoding="async"
              class="h-full w-full object-contain"
            />
          </button>
        </template>
        <div v-else class="flex h-full w-full flex-none items-center justify-center">
          <img src="/pwa-icons/pwa-192x192.png" alt="" class="h-1/3 w-1/3 rounded-full opacity-70" />
        </div>
      </div>
      <slot />
      <template v-if="many">
        <button type="button" class="nav-btn left-2 max-md:hidden" :aria-label="t('shop.photoPrev')" @click="go(strip, at - 1)">‹</button>
        <button type="button" class="nav-btn right-2 max-md:hidden" :aria-label="t('shop.photoNext')" @click="go(strip, at + 1)">›</button>
        <div class="absolute right-0 bottom-2.5 left-0 flex justify-center gap-1.5" aria-hidden="true">
          <span v-for="(_, i) in images" :key="i" class="h-1.5 rounded-full transition-all" :class="i === at ? 'w-5 bg-brand-pink' : 'w-1.5 bg-black/30'" />
        </div>
      </template>
    </div>

    <!-- thumbnails: every photo in reach without swiping through them -->
    <div v-if="many" class="flex gap-2 overflow-x-auto">
      <button
        v-for="(url, i) in images"
        :key="url"
        type="button"
        class="thumb"
        :aria-label="t('shop.photoGoTo', { n: i + 1 })"
        :aria-current="i === at ? 'true' : undefined"
        @click="go(strip, i)"
      >
        <img :src="url" alt="" loading="lazy" class="h-full w-full object-contain" />
      </button>
    </div>

    <Teleport to="body">
      <div
        v-if="open"
        class="fixed inset-0 z-50 flex flex-col bg-black"
        role="dialog"
        aria-modal="true"
        :aria-label="name"
      >
        <div class="flex h-14 shrink-0 items-center justify-between px-3 pt-[env(safe-area-inset-top,0px)]">
          <span class="text-sm text-white/80" aria-live="polite">{{ shownAt + 1 }} / {{ images.length }}</span>
          <button ref="closeBtn" type="button" class="flex h-11 w-11 items-center justify-center rounded-full bg-white/12 text-xl text-white" :aria-label="t('shop.photoClose')" @click="close">✕</button>
        </div>
        <div
          ref="viewer"
          class="no-bar flex min-h-0 flex-1 snap-x snap-mandatory overflow-x-auto"
          @scroll="shownAt = indexOf(viewer)"
          @click.self="close"
        >
          <div v-for="(url, i) in images" :key="url" class="flex h-full w-full flex-none snap-center items-center justify-center p-2" @click.self="close">
            <img :src="url" :alt="`${name} ${i + 1}/${images.length}`" class="max-h-full max-w-full object-contain" />
          </div>
        </div>
        <div v-if="many" class="flex h-16 shrink-0 items-center justify-center gap-3 pb-[env(safe-area-inset-bottom,0px)]">
          <button type="button" class="viewer-btn" :aria-label="t('shop.photoPrev')" @click="go(viewer, shownAt - 1)">‹</button>
          <div class="flex gap-1.5" aria-hidden="true">
            <span v-for="(_, i) in images" :key="i" class="h-1.5 rounded-full transition-all" :class="i === shownAt ? 'w-5 bg-white' : 'w-1.5 bg-white/40'" />
          </div>
          <button type="button" class="viewer-btn" :aria-label="t('shop.photoNext')" @click="go(viewer, shownAt + 1)">›</button>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
/* A light, even backdrop: product shots usually come on white or pastel,
   and whatever the frame doesn't fill should read as margin, not as a
   coloured bar. */
.frame {
  background: radial-gradient(circle at 50% 40%, #fff, #f3eaf1 70%);
}
.no-bar {
  scrollbar-width: none;
}
.no-bar::-webkit-scrollbar {
  display: none;
}
.nav-btn {
  position: absolute;
  top: 50%;
  display: flex;
  width: 44px;
  height: 44px;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: rgb(11 5 24 / 0.6);
  color: #fff;
  font-size: 26px;
  line-height: 1;
  translate: 0 -50%;
}
.thumb {
  height: 64px;
  width: 64px;
  flex: none;
  overflow: hidden;
  border: 2px solid transparent;
  border-radius: 12px;
  background: #f3eaf1;
  padding: 2px;
}
.thumb[aria-current='true'] {
  border-color: var(--color-brand-pink);
}
.viewer-btn {
  display: flex;
  width: 48px;
  height: 48px;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: rgb(255 255 255 / 0.12);
  color: #fff;
  font-size: 28px;
  line-height: 1;
}
</style>
