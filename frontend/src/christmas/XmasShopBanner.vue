<script setup lang="ts">
/**
 * The shop's Christmas strip: gifts for your partner, picked up at the
 * court on Friday. Shown above the products in the season (ShopView.vue).
 */
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
</script>

<template>
  <section class="xmas-shop world-card relative mb-4 flex items-center gap-4 overflow-hidden p-4 sm:mb-5 sm:gap-6 sm:p-5">
    <!-- a gift tied with the club's pink ribbon, a shuttlecock on top -->
    <svg class="h-[74px] w-[74px] shrink-0 sm:h-[92px] sm:w-[92px]" viewBox="0 0 96 96" aria-hidden="true">
      <defs>
        <linearGradient id="xs-box" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#2d1a55" />
          <stop offset="1" stop-color="#170b30" />
        </linearGradient>
      </defs>
      <rect x="14" y="44" width="68" height="44" rx="6" fill="url(#xs-box)" stroke="#ff7cc6" stroke-width="2.5" />
      <rect x="10" y="32" width="76" height="16" rx="5" fill="#3a2270" stroke="#ff7cc6" stroke-width="2.5" />
      <rect x="42" y="32" width="12" height="56" fill="#ea4ca4" />
      <path d="M48 32c-10-12-24-14-26-6s14 8 26 6zm0 0c10-12 24-14 26-6s-14 8-26 6z" fill="#ff7cc6" stroke="#ffd0ea" stroke-width="2" stroke-linejoin="round" />
      <!-- the shuttlecock, cork down on the bow -->
      <g transform="translate(62 2) rotate(24)">
        <path d="M-9 0h18l-5 18h-8z" fill="#fff" />
        <path d="M-4 0l1 18M4 0l-1 18M0 0v18" stroke="#c9bde0" stroke-width="1" />
        <rect x="-5" y="17" width="10" height="3" fill="#ea4ca4" />
        <path d="M-5 20a5 5 0 0 0 10 0z" fill="#fff1f8" />
      </g>
      <circle cx="20" cy="18" r="2.2" fill="#fff" /><circle cx="86" cy="26" r="1.8" fill="#ffb3dc" /><circle cx="8" cy="62" r="1.6" fill="#fff" />
    </svg>
    <div class="min-w-0">
      <p class="world-eyebrow">{{ t('xmas.shop.eyebrow') }}</p>
      <h2 class="world-title mt-0.5 text-xl sm:text-2xl">{{ t('xmas.shop.title') }}</h2>
      <p class="mt-1 text-sm text-white/70">{{ t('xmas.shop.body') }}</p>
    </div>
  </section>
</template>

<style scoped>
.xmas-shop {
  border-color: rgb(255 124 198 / 0.45);
  background:
    radial-gradient(70% 140% at 100% 0%, rgb(234 76 164 / 0.22), transparent 60%),
    radial-gradient(60% 120% at 0% 100%, rgb(92 232 138 / 0.1), transparent 60%),
    linear-gradient(135deg, rgb(255 255 255 / 0.12), rgb(255 255 255 / 0.03) 55%, rgb(255 255 255 / 0.07)),
    rgb(24 10 46 / 0.6);
}
</style>
