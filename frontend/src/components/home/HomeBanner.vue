<script setup lang="ts">
/**
 * The home hero cut down to a banner for a phone: the same world (the
 * striped sun, the neon floor, the crowned cat) in a quarter of the screen,
 * so the tournament and shop cards and what's on court now are visible
 * without scrolling — the way Facebook puts the feed right under its bar.
 * From 900px wide the full HomeHero.vue, with its 3D scene, is used instead.
 */
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'

const { t } = useI18n()
</script>

<template>
  <section class="banner relative isolate h-[212px] overflow-hidden" aria-labelledby="home-banner-title">
    <div class="pointer-events-none absolute inset-0 -z-10" aria-hidden="true">
      <div class="absolute inset-0 bg-[radial-gradient(90%_90%_at_75%_20%,#5a1a7a_0%,#1a0838_55%,#0b0518_90%)]" />
      <div class="banner-sun absolute top-[18px] right-[30px] h-[150px] w-[150px] rounded-full" />
      <div class="banner-floor absolute right-[-30%] bottom-0 left-[-30%] h-[120px]" />
    </div>
    <img
      src="/hero/cat-color.webp"
      :alt="t('home.hero.catAlt')"
      width="168"
      height="168"
      fetchpriority="high"
      decoding="async"
      class="banner-cat absolute right-[18px] bottom-1.5 h-[168px] w-[168px] object-contain max-[389px]:right-[-8px] max-[389px]:h-[150px] max-[389px]:w-[150px] max-[359px]:h-[140px] max-[359px]:w-[140px]"
    />
    <div class="absolute top-4 left-4 flex w-[200px] flex-col gap-2 max-[359px]:w-[180px]">
      <p class="flex h-6 items-center gap-1.5 self-start rounded-full border border-white/20 bg-black/45 px-2.5 text-[11px]">
        <span class="banner-blink h-1.5 w-1.5 rounded-full bg-brand-pink" aria-hidden="true" />
        {{ t('home.banner.when') }}
      </p>
      <!-- Two lines, each kept whole: Thai has no spaces to break at, so
           left alone the browser split "หนีสถิติไป|ได้" into a third line
           that ran under the cat. -->
      <h1 id="home-banner-title" class="banner-title font-display text-[20px] leading-[1.2] font-bold max-[359px]:text-[17px]">
        <span class="block whitespace-nowrap">{{ t('home.banner.line1') }}</span>
        <span class="block whitespace-nowrap text-brand-pink-light">{{ t('home.banner.line2') }}</span>
      </h1>
      <div class="mt-0.5 flex gap-1.5">
        <RouterLink to="/ranking" class="banner-hot flex h-10 items-center rounded-full px-3.5 text-[13px] font-medium">
          {{ t('home.hero.ctaRanking') }}
        </RouterLink>
        <RouterLink to="/live" class="flex h-10 items-center rounded-full border border-white/25 bg-white/10 px-3.5 text-[13px]">
          {{ t('home.hero.ctaLive') }}
        </RouterLink>
      </div>
    </div>
  </section>
</template>

<style scoped>
.banner-sun {
  background:
    repeating-linear-gradient(transparent 0 9px, rgb(11 5 24 / 0.85) 9px 12px),
    linear-gradient(#ffe14d, #ff6cc0 55%, #9b2cff);
  opacity: 0.75;
}
.banner-floor {
  background-image:
    linear-gradient(rgb(255 108 192 / 0.6) 2px, transparent 2px),
    linear-gradient(90deg, rgb(255 108 192 / 0.6) 2px, transparent 2px);
  background-size: 30px 30px;
  transform: perspective(220px) rotateX(58deg);
  transform-origin: 50% 100%;
  animation: banner-floor 2.2s linear infinite;
}
@keyframes banner-floor {
  to {
    background-position: 0 30px, 0 0;
  }
}
.banner-cat {
  filter: drop-shadow(0 12px 14px rgb(6 0 20 / 0.6));
  animation: banner-float 6s ease-in-out infinite;
}
@keyframes banner-float {
  50% {
    transform: translateY(-6px);
  }
}
.banner-blink {
  animation: banner-blink 1.4s ease-in-out infinite;
}
@keyframes banner-blink {
  50% {
    opacity: 0.35;
  }
}
.banner-title {
  text-shadow:
    0 0 14px rgb(255 108 192 / 0.7),
    0 1px 2px rgb(0 0 0 / 0.6);
}
.banner-hot {
  background: linear-gradient(#f06bb6, #c22f86);
  box-shadow: 0 3px 0 #6d1247;
  color: #fff;
}
@media (prefers-reduced-motion: reduce) {
  .banner-floor,
  .banner-cat,
  .banner-blink {
    animation: none;
  }
}
</style>
