<script setup lang="ts">
// Static club intro + contact — there's no backend-driven "club info" table
// (out of scope per the issue doc), so this content is edited directly here.
import type { EloTier } from '@/types'
import TierMascot from '@/components/players/TierMascot.vue'

const tiers: { tier: EloTier; label: string; color: string }[] = [
  { tier: 'milk', label: 'Milk', color: 'var(--color-tier-milk)' },
  { tier: 'soju', label: 'Soju', color: 'var(--color-tier-soju)' },
  { tier: 'beer', label: 'Beer', color: 'var(--color-tier-beer)' },
  { tier: 'whisky', label: 'Whisky', color: 'var(--color-tier-whisky)' },
  { tier: 'highball', label: 'Highball', color: 'var(--color-tier-highball)' },
  { tier: 'vodka', label: 'Vodka', color: 'var(--color-tier-vodka)' },
]

const quickLinks = [
  { to: '/members', num: '01', label: 'สมาชิก', desc: 'สถิติทุกคนในก๊วน' },
  { to: '/ranking', num: '02', label: 'อันดับ', desc: 'ใครแน่ที่สุดตอนนี้' },
  { to: '/hall-of-fame', num: '03', label: 'Hall of Fame', desc: 'ตำนานตลอดกาล' },
  { to: '/matches', num: '04', label: 'ผลแมตช์', desc: 'เกมล่าสุดที่จบไป' },
]

// Club vibe strip — hand-drawn line icons (24x24, stroke-based) instead of
// filled/flat glyphs so they sit quietly next to the bolder TierMascot
// illustrations above rather than competing with them.
const vibes = [
  {
    label: 'แอลกอฮอล์',
    path: 'M5 4h14l-7 9z M12 13v7 M8 20h8',
  },
  {
    label: 'เสียงเพลง',
    path: 'M9 18V5l11-2v13 M6 21a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z M17 19a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z',
  },
  {
    label: 'เน้นมือสนุก',
    path: 'M12 2.5l2.9 6.3 6.9.6-5.2 4.6 1.6 6.8L12 16.9l-6.2 3.4 1.6-6.8-5.2-4.6 6.9-.6z',
  },
  {
    label: 'ไม่เครียด',
    path: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z M8 14s1.5 2 4 2 4-2 4-2 M8.5 9.5h.01 M15.5 9.5h.01',
  },
  {
    label: 'มีผลไม้',
    path: 'M12 8.5c-3.3 0-5.5 2.6-5.5 6 0 3.6 2.2 6.5 5.5 6.5s5.5-2.9 5.5-6.5c0-3.4-2.2-6-5.5-6Z M12 8.5V5.5 M12 5.5c1-1.5 3-1.8 3-1.8',
  },
  {
    label: 'มีขนม',
    path: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z',
    dots: [
      [9, 9],
      [15, 10],
      [10.5, 15],
      [15, 15.5],
    ],
  },
  {
    label: 'งดบุหรี่',
    path: 'M4 11h11a2 2 0 0 1 2 2v0a2 2 0 0 1-2 2H4z M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z M5 20 19 4',
  },
]

// -mono.png variants: original logos recolored to a white silhouette
// (RGB -> white, original alpha kept as the mask) so every logo reads
// cleanly straight against the dark background with no card/box needed —
// same treatment bmbad.com uses for its sponsor strip.
const sponsors = [
  { name: 'Wasteland', src: '/sponsors/wasteland-mono.png' },
  { name: 'Match Mellow', src: '/sponsors/match-mellow-mono.png' },
  { name: 'Sawadee Natural Herbal Balm', src: '/sponsors/sawadee-mono.png' },
  { name: 'Umore Made', src: '/sponsors/umore-made-mono.png' },
  { name: 'The Players Club', src: '/sponsors/players-club-mono.png' },
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

    <section class="reveal hud-panel mt-8 border border-brand-pink/20 bg-brand-surface p-6 sm:mt-10">
      <h2 class="text-center text-xs font-semibold tracking-widest text-brand-pink/70 uppercase">บรรยากาศก๊วน</h2>
      <div class="mt-5 flex flex-wrap justify-center gap-x-6 gap-y-5 sm:gap-x-8">
        <div v-for="vibe in vibes" :key="vibe.label" class="flex w-16 flex-col items-center gap-2 text-center">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.75"
            stroke-linecap="round"
            stroke-linejoin="round"
            class="h-7 w-7 text-brand-pink"
          >
            <path :d="vibe.path" />
            <circle v-for="(dot, i) in vibe.dots" :key="i" :cx="dot[0]" :cy="dot[1]" r="1" fill="currentColor" stroke="none" />
          </svg>
          <span class="text-[11px] leading-tight text-white/60">{{ vibe.label }}</span>
        </div>
      </div>
    </section>

    <section class="reveal hud-panel mt-8 border border-brand-pink/20 bg-brand-surface p-6 text-left sm:mt-10">
      <h2 class="font-display text-sm font-bold tracking-wide text-brand-pink uppercase">ติดต่อผู้จัดก๊วน</h2>
      <p class="mt-2 text-sm text-white/60">
        สมัครสมาชิกใหม่ / request คู่ หรือ คู่แข่ง ทักแอดมินได้ทาง LINE OA : @369iojcn ได้เลย
      </p>
    </section>

    <section class="reveal sponsors mt-10 border-t border-b border-brand-pink/15 py-8 text-center sm:mt-12">
      <h2 class="text-xs font-semibold tracking-widest text-brand-pink/70 uppercase">Presented by</h2>
      <div class="mt-6 flex flex-wrap items-center justify-center gap-x-12 gap-y-8">
        <img
          v-for="sponsor in sponsors"
          :key="sponsor.name"
          :src="sponsor.src"
          :alt="sponsor.name"
          class="h-24 w-auto object-contain opacity-80 transition-opacity hover:opacity-100 sm:h-28"
        />
      </div>
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
section.reveal.sponsors {
  animation-delay: 0.3s;
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
