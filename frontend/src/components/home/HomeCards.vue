<script setup lang="ts">
// The two doors under the hero, side by side on every screen: the
// tournament that's coming and the club shop. Cards rather than tabs —
// neither is something a member opens every Friday.
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'

const { t } = useI18n()
</script>

<template>
  <div class="grid grid-cols-2 gap-2.5 sm:gap-4">
    <RouterLink to="/tournament" class="home-card border-[#ffe14d]/50 bg-[linear-gradient(140deg,#3b0f5c,#1a0838_70%)]">
      <span class="card-blink self-start rounded-full border border-[#ffe14d] px-2 py-1 font-display text-[10px] leading-none font-bold tracking-[1.5px] text-[#ffe14d] sm:text-xs">
        COMING SOON
      </span>
      <span class="font-display text-[19px] font-bold sm:text-2xl">{{ t('nav.tournament') }}</span>
      <span class="pr-10 text-[11px] font-light text-white/75 sm:text-sm">{{ t('tournament.card.sub') }}</span>
      <svg viewBox="0 0 24 24" fill="none" stroke="#ffcf3f" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" class="card-art h-10 w-10" aria-hidden="true">
        <path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0zM17 6h3v2a3 3 0 0 1-3 3M7 6H4v2a3 3 0 0 0 3 3" />
      </svg>
    </RouterLink>
    <RouterLink to="/shop" class="home-card border-brand-pink/55 bg-[linear-gradient(140deg,#4a0f3a,#1a0838_70%)]">
      <span class="self-start rounded-full bg-[#ffe14d] px-2 py-1 text-[10px] leading-none font-medium text-[#2a1a00] sm:text-xs">
        {{ t('shop.card.tag') }}
      </span>
      <span class="font-display text-[19px] font-bold sm:text-2xl">{{ t('nav.shop') }}</span>
      <span class="pr-10 text-[11px] font-light text-white/75 sm:text-sm">{{ t('shop.card.sub') }}</span>
      <svg viewBox="0 0 120 110" class="card-art h-[42px] w-[46px] rotate-[8deg]" aria-hidden="true">
        <path
          d="M38 8 18 18 4 40l18 10 6-10v64h64V40l6 10 18-10-14-22-20-10c-4 10-12 14-22 14S42 18 38 8Z"
          fill="#ea4ca4"
          stroke="rgb(255 255 255 / 0.6)"
          stroke-width="3"
        />
      </svg>
    </RouterLink>
  </div>
</template>

<style scoped>
.home-card {
  position: relative;
  display: flex;
  min-height: 118px;
  flex-direction: column;
  gap: 4px;
  overflow: hidden;
  padding: 12px;
  border-width: 1px;
  border-radius: 18px;
  transition: transform 0.15s;
}
.home-card:hover {
  transform: translateY(-2px);
}
.card-art {
  position: absolute;
  right: 8px;
  bottom: 8px;
  opacity: 0.9;
}
@media (min-width: 640px) {
  .home-card {
    min-height: 150px;
    padding: 18px;
    gap: 6px;
  }
  .card-art {
    right: 14px;
    bottom: 14px;
    scale: 1.5;
    transform-origin: 100% 100%;
  }
}
.card-blink {
  animation: card-blink 1.4s ease-in-out infinite;
}
@keyframes card-blink {
  50% {
    opacity: 0.45;
  }
}
@media (prefers-reduced-motion: reduce) {
  .card-blink {
    animation: none;
  }
  .home-card {
    transition: none;
  }
}
</style>
