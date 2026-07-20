<script setup lang="ts">
// Static club intro + contact — there's no backend-driven "club info" table
// (out of scope per the issue doc), so this content is edited directly here.
import type { EloTier } from '@/types'
import TierMascot from '@/components/players/TierMascot.vue'

const tiers: { tier: EloTier; label: string; color: string }[] = [
  { tier: 'milk', label: 'Milk', color: 'var(--color-tier-milk)' },
  { tier: 'soju', label: 'Soju', color: 'var(--color-tier-soju)' },
  { tier: 'beer', label: 'Beer', color: 'var(--color-tier-beer)' },
  { tier: 'highball', label: 'Highball', color: 'var(--color-tier-highball)' },
  { tier: 'vodka', label: 'Vodka', color: 'var(--color-tier-vodka)' },
]

const quickLinks = [
  { to: '/members', num: '01', label: 'สมาชิก', desc: 'สถิติทุกคนในก๊วน' },
  { to: '/ranking', num: '02', label: 'อันดับ', desc: 'ใครแน่ที่สุดตอนนี้' },
  { to: '/hall-of-fame', num: '03', label: 'Hall of Fame', desc: 'ตำนานตลอดกาล' },
  { to: '/matches', num: '04', label: 'ผลแมตช์', desc: 'เกมล่าสุดที่จบไป' },
]
</script>

<template>
  <main class="mx-auto max-w-4xl px-4 py-12 sm:py-20">
    <div class="reveal flex flex-col items-center text-center">
      <span class="hud-panel border border-brand-pink/40 bg-brand-surface p-1">
        <img src="/pwa-icons/pwa-512x512.png" alt="นิดเดียว Badminton Club logo" class="hud-panel h-24 w-24 sm:h-32 sm:w-32" />
      </span>

      <h1 class="mt-8 font-display text-[clamp(2rem,7vw,3.75rem)] leading-none font-bold text-white">
        นิดเดียว<span class="text-brand-pink">BADMINTON</span>
      </h1>
      <p class="mt-4 max-w-md text-balance text-white/60">
        ก๊วนแบดสายมันส์ — เช็คอิน จัดคู่ตาม ELO คิดเงินอัตโนมัติ
        ไม่มีใครหนีสถิติไปได้
      </p>

      <div class="mt-6 flex flex-wrap items-center justify-center gap-3 text-xs font-semibold tracking-widest text-white/40 uppercase">
        <span v-for="tier in tiers" :key="tier.label" class="flex flex-col items-center gap-1">
          <TierMascot :tier="tier.tier" :size="40" />
          <span :style="{ color: tier.color }">{{ tier.label }}</span>
        </span>
      </div>
    </div>

    <nav class="reveal mt-12 grid grid-cols-2 gap-3 sm:mt-16 sm:grid-cols-4">
      <RouterLink
        v-for="link in quickLinks"
        :key="link.to"
        :to="link.to"
        class="hud-panel group border border-brand-pink/20 bg-brand-surface p-4 transition-colors hover:border-brand-pink/60 hover:bg-brand-surface-raised"
      >
        <span class="font-display text-xs text-brand-pink/60 group-hover:text-brand-pink">{{ link.num }}</span>
        <p class="mt-2 font-display font-semibold text-white">{{ link.label }}</p>
        <p class="mt-1 text-xs text-white/40">{{ link.desc }}</p>
      </RouterLink>
    </nav>

    <section class="reveal hud-panel mt-8 border border-brand-pink/20 bg-brand-surface p-6 text-left sm:mt-10">
      <h2 class="font-display text-sm font-bold tracking-wide text-brand-pink uppercase">ติดต่อผู้จัดก๊วน</h2>
      <p class="mt-2 text-sm text-white/60">
        สมัครสมาชิกใหม่ / request คู่ หรือ คู่แข่ง ทักแอดมินได้ทาง LINE OA : @369iojcn ได้เลย
      </p>
    </section>
  </main>
</template>

<style scoped>
.reveal {
  animation: reveal-up 0.6s cubic-bezier(0.16, 1, 0.3, 1) both;
}
nav.reveal > * {
  animation: reveal-up 0.5s cubic-bezier(0.16, 1, 0.3, 1) both;
}
nav.reveal > *:nth-child(1) {
  animation-delay: 0.05s;
}
nav.reveal > *:nth-child(2) {
  animation-delay: 0.1s;
}
nav.reveal > *:nth-child(3) {
  animation-delay: 0.15s;
}
nav.reveal > *:nth-child(4) {
  animation-delay: 0.2s;
}
section.reveal {
  animation-delay: 0.25s;
}

@keyframes reveal-up {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .reveal,
  nav.reveal > * {
    animation: none;
  }
}
</style>
