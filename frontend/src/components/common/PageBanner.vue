<script setup lang="ts">
// The neon banner at the top of the ranking, hall of fame, live and match
// pages: the home hero's world in miniature — a starry violet sky, a
// striped sun, a running grid floor — with the page's name in neon and a
// mascot floating beside it.
//
// On a desktop it runs up under the floating glass header, as the home
// hero does. On a phone it starts under the solid bar, the mascot sits in
// the top corner, and whatever the page puts in the slot (period tabs,
// live counts) takes the full width below the words.
import { useSlots } from 'vue'

defineProps<{
  eyebrow: string
  title: string
  sub?: string
  /** The mascot's image, e.g. /tiers/soju.webp. */
  mascot: string
  /** A pulsing dot before the eyebrow: something is happening now. */
  live?: boolean
  /** Shorter, for the admin's working screens: the same sky, less of it. */
  compact?: boolean
  /** The page already has its own <h1> (the admin screens do, for screen
   * readers), so the banner's title is shown but not announced twice. */
  decorativeTitle?: boolean
}>()
const slots = useSlots()
</script>

<template>
  <section
    class="pb relative isolate overflow-hidden"
    :class="{ 'pb--compact': compact }"
    :aria-labelledby="decorativeTitle ? undefined : 'page-banner-title'"
    :aria-hidden="decorativeTitle ? 'true' : undefined"
  >
    <div class="pointer-events-none absolute inset-0 -z-10" aria-hidden="true">
      <div class="pb-stars absolute inset-0" />
      <div class="pb-sun absolute rounded-full" />
      <div class="pb-horizon absolute right-0 left-0" />
      <div class="pb-floor absolute" />
    </div>
    <img :src="mascot" alt="" width="220" height="220" decoding="async" class="pb-mascot pointer-events-none absolute object-contain" />

    <div class="relative mx-auto max-w-[1200px] px-4 sm:px-6">
      <div class="pb-words">
        <p class="world-eyebrow flex items-center gap-2 uppercase">
          <span v-if="live" class="pb-dot" aria-hidden="true" />
          {{ eyebrow }}
        </p>
        <p v-if="decorativeTitle" class="pb-title mt-1 font-display font-bold">{{ title }}</p>
        <h1 v-else id="page-banner-title" class="pb-title mt-1 font-display font-bold">{{ title }}</h1>
        <p v-if="sub" class="mt-1.5 text-sm text-white/75 sm:text-[15px]">{{ sub }}</p>
      </div>
      <div v-if="slots.default" class="relative mt-4">
        <slot />
      </div>
    </div>
  </section>
</template>

<style scoped>
.pb {
  min-height: 210px;
  padding: 22px 0 26px;
  background:
    radial-gradient(60% 120% at 82% 100%, #5b1f7d 0%, #2c1352 45%, rgb(20 10 41 / 0) 80%),
    linear-gradient(#07030f, #140a2b 60%, #2a1250);
}
.pb-words {
  /* clear of the mascot in the top corner on a phone */
  max-width: calc(100% - 118px);
}
.pb-title {
  font-size: 34px;
  line-height: 1.1;
  color: #fff;
  text-shadow:
    0 0 18px rgb(255 108 192 / 0.7),
    0 0 2px rgb(255 255 255 / 0.7);
}
.pb-stars {
  opacity: 0.85;
  background-image:
    radial-gradient(1.5px 1.5px at 8% 18%, #fff, transparent), radial-gradient(1.2px 1.2px at 21% 40%, #fff, transparent),
    radial-gradient(1.7px 1.7px at 33% 12%, #ffd0ea, transparent), radial-gradient(1.2px 1.2px at 47% 30%, #fff, transparent),
    radial-gradient(1.5px 1.5px at 61% 8%, #fff, transparent), radial-gradient(1.2px 1.2px at 88% 16%, #fff, transparent);
}
.pb-sun {
  top: 6px;
  right: -28px;
  width: 140px;
  height: 140px;
  background: linear-gradient(#ffe0f1, #ff8fd0 30%, #ea4ca4 58%, #8e4cf0);
  -webkit-mask-image: linear-gradient(#000 0 50%, transparent 50% 55%, #000 55% 62%, transparent 62% 68%, #000 68% 74%, transparent 74%);
  mask-image: linear-gradient(#000 0 50%, transparent 50% 55%, #000 55% 62%, transparent 62% 68%, #000 68% 74%, transparent 74%);
  filter: drop-shadow(0 0 30px rgb(234 76 164 / 0.6));
  opacity: 0.85;
}
.pb-horizon {
  bottom: 30%;
  height: 2px;
  background: linear-gradient(90deg, transparent, #ff8fd0 30%, #ffe0f1 60%, transparent);
  box-shadow: 0 0 18px 5px rgb(234 76 164 / 0.55);
}
.pb-floor {
  left: -30%;
  right: -30%;
  bottom: -2px;
  height: 30%;
  background-image:
    linear-gradient(rgb(255 110 190 / 0.65) 2px, transparent 2px),
    linear-gradient(90deg, rgb(255 110 190 / 0.5) 2px, transparent 2px);
  background-size: 56px 34px;
  transform: perspective(300px) rotateX(58deg);
  transform-origin: bottom;
  -webkit-mask-image: linear-gradient(transparent, #000 45%);
  mask-image: linear-gradient(transparent, #000 45%);
  animation: pb-floor 2.2s linear infinite;
}
@keyframes pb-floor {
  to {
    background-position:
      0 34px,
      0 0;
  }
}
.pb-mascot {
  top: 18px;
  right: 10px;
  width: 104px;
  height: 104px;
  filter: drop-shadow(0 10px 14px rgb(6 0 20 / 0.6));
  animation: pb-bob 4.5s ease-in-out infinite;
}
@keyframes pb-bob {
  50% {
    transform: translateY(-8px);
  }
}
.pb-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #ff5078;
  animation: pb-pulse 1.6s infinite;
}
@keyframes pb-pulse {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgb(255 80 120 / 0.7);
  }
  50% {
    box-shadow: 0 0 0 7px rgb(255 80 120 / 0);
  }
}

/* Desktop: up under the floating header, the words on the left and the
   mascot standing on the floor to the right. */
@media (min-width: 900px) {
  .pb {
    min-height: 330px;
    margin-top: calc(-1 * var(--header-h));
    padding: calc(var(--header-h) + 22px) 0 34px;
  }
  .pb-words {
    max-width: 620px;
  }
  .pb-title {
    font-size: 48px;
  }
  .pb-horizon {
    bottom: 26%;
  }
  .pb-floor {
    height: 26%;
  }
  .pb-sun {
    top: auto;
    right: max(24px, calc(50% - 600px + 20px));
    bottom: 26%;
    width: 240px;
    height: 240px;
  }
  .pb-mascot {
    top: auto;
    right: max(40px, calc(50% - 600px + 40px));
    bottom: 28px;
    width: 210px;
    height: 210px;
  }
}

/* The admin's working screens: the same world, a shorter strip of it,
   so the work starts high on the screen. */
.pb--compact {
  min-height: 150px;
  padding: 18px 0 20px;
}
.pb--compact .pb-title {
  font-size: 28px;
}
.pb--compact .pb-mascot {
  top: 12px;
  width: 88px;
  height: 88px;
}
.pb--compact .pb-sun {
  width: 120px;
  height: 120px;
}
@media (min-width: 900px) {
  .pb--compact {
    min-height: 264px;
    padding: calc(var(--header-h) + 22px) 0 28px;
  }
  .pb--compact .pb-title {
    font-size: 40px;
  }
  .pb--compact .pb-sun {
    width: 200px;
    height: 200px;
  }
  .pb--compact .pb-mascot {
    width: 140px;
    height: 140px;
    bottom: 18px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .pb-floor,
  .pb-mascot,
  .pb-dot {
    animation: none;
  }
}
</style>
