<script setup lang="ts">
/**
 * The tournament, not built yet: a page that says it's coming, what it
 * will be, and where to hear first when sign-ups open. The three lines
 * are plans, not promises — no dates until the organisers set them.
 */
import { useI18n } from 'vue-i18n'
import TierMascot from '@/components/players/TierMascot.vue'

const { t } = useI18n()
</script>

<template>
  <main class="relative isolate overflow-hidden">
    <!-- same world as the home hero: a sky, a sun, a neon floor -->
    <div class="pointer-events-none absolute inset-0 -z-10" aria-hidden="true">
      <div class="absolute inset-0 bg-[radial-gradient(80%_50%_at_50%_30%,#5a1a7a_0%,#1a0838_55%,#0a0416_80%)]" />
      <div class="absolute top-[110px] left-1/2 h-[260px] w-[260px] -translate-x-1/2 rounded-full bg-[linear-gradient(#ffe14d,#ff6cc0_55%,#9b2cff)] opacity-35 blur-[2px]" />
      <div class="t-floor absolute right-[-40%] bottom-0 left-[-40%] h-[330px]" />
      <div class="absolute inset-x-0 bottom-0 h-[420px] bg-[linear-gradient(rgb(10_4_22/0),#0a0416_85%)]" />
    </div>

    <div class="mx-auto flex max-w-md flex-col items-center gap-3.5 px-4 pt-4 pb-10 text-center">
      <RouterLink to="/" class="inline-flex min-h-11 items-center gap-1 self-start text-sm text-white/75 hover:text-white">
        <span aria-hidden="true">←</span> {{ t('shop.backHome') }}
      </RouterLink>

      <span class="t-blink rounded-full border border-[#ffe14d] px-3.5 py-1.5 font-display text-[13px] leading-none font-bold tracking-[3px] text-[#ffe14d]">
        COMING SOON
      </span>

      <!-- the cup, with the club's cat sitting on it -->
      <div class="t-float relative mt-10 h-[230px] w-[220px]">
        <svg viewBox="0 0 200 210" width="220" height="230" role="img" :aria-label="t('tournament.trophy')">
          <defs>
            <linearGradient id="t-cup" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stop-color="#fff3a8" />
              <stop offset=".45" stop-color="#ffcf3f" />
              <stop offset="1" stop-color="#b8740a" />
            </linearGradient>
          </defs>
          <path d="M52 40H148V78C148 112 126 134 100 134 74 134 52 112 52 78Z" fill="url(#t-cup)" stroke="#fff6c8" stroke-width="2" />
          <path d="M52 52H28C28 82 40 96 58 98M148 52h24c0 30-12 44-30 46" fill="none" stroke="#ffcf3f" stroke-width="8" stroke-linecap="round" />
          <rect x="90" y="134" width="20" height="30" fill="#e0a21c" />
          <rect x="64" y="164" width="72" height="16" rx="4" fill="#ffcf3f" />
          <rect x="54" y="180" width="92" height="22" rx="6" fill="#2a1450" stroke="#ff6cc0" stroke-width="2" />
          <text x="100" y="196" text-anchor="middle" font-family="Chakra Petch, sans-serif" font-weight="700" font-size="12" fill="#ff6cc0">NIDDEAW CUP</text>
          <path d="m84 70 16-14 16 14" fill="none" stroke="#fff6c8" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <img
          src="/hero/cat-color.webp"
          alt=""
          width="92"
          height="92"
          class="absolute top-[-48px] left-16 h-[92px] w-[92px] object-contain drop-shadow-[0_8px_10px_rgb(6_0_20/0.6)]"
        />
      </div>

      <h1 class="t-glow font-display text-[40px] leading-none font-bold">{{ t('nav.tournament') }}</h1>
      <p class="text-[15px] font-light text-white/85">{{ t('tournament.lead') }}</p>

      <ul class="mt-1.5 flex w-full flex-col gap-2 text-left">
        <li class="t-plan">
          <TierMascot tier="milk" :size="36" :interactive="false" />
          <span>{{ t('tournament.plan1') }}</span>
        </li>
        <li class="t-plan">
          <svg viewBox="0 0 24 24" fill="none" stroke="#ff6cc0" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" class="h-9 w-9 flex-none" aria-hidden="true">
            <path d="M4 6h5v4H4zM4 14h5v4H4zM15 10h5v4h-5zM9 8h3v8H9M12 12h3" />
          </svg>
          <span>{{ t('tournament.plan2') }}</span>
        </li>
        <li class="t-plan">
          <svg viewBox="0 0 24 24" fill="none" stroke="#ffe14d" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" class="h-9 w-9 flex-none" aria-hidden="true">
            <path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0zM17 6h3v2a3 3 0 0 1-3 3M7 6H4v2a3 3 0 0 0 3 3" />
          </svg>
          <span>{{ t('tournament.plan3') }}</span>
        </li>
      </ul>

      <a
        href="https://line.me/R/ti/p/@369iojcn"
        target="_blank"
        rel="noopener noreferrer"
        class="t-line mt-4 flex h-[54px] w-full items-center justify-center gap-2 rounded-[14px] font-display text-base font-bold"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5" aria-hidden="true">
          <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0" />
        </svg>
        {{ t('tournament.notify') }}
      </a>
      <p class="text-xs text-white/60">{{ t('tournament.notifyHint') }}</p>
    </div>
  </main>
</template>

<style scoped>
.t-floor {
  background-image:
    linear-gradient(rgb(255 108 192 / 0.55) 2px, transparent 2px),
    linear-gradient(90deg, rgb(255 108 192 / 0.55) 2px, transparent 2px);
  background-size: 40px 40px;
  transform: perspective(300px) rotateX(58deg);
  transform-origin: 50% 100%;
  animation: t-floor 2.2s linear infinite;
}
@keyframes t-floor {
  to {
    background-position: 0 40px, 0 0;
  }
}
.t-float {
  animation: t-float 6s ease-in-out infinite;
}
@keyframes t-float {
  50% {
    transform: translateY(-6px);
  }
}
.t-blink {
  animation: t-blink 1.4s ease-in-out infinite;
}
@keyframes t-blink {
  50% {
    opacity: 0.45;
  }
}
.t-glow {
  text-shadow:
    0 0 18px rgb(255 108 192 / 0.8),
    0 0 2px #fff;
}
.t-plan {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid rgb(255 255 255 / 0.14);
  border-radius: 14px;
  background: rgb(255 255 255 / 0.06);
  font-size: 14px;
  backdrop-filter: blur(10px);
}
.t-line {
  background: #037f36;
  box-shadow:
    0 5px 0 #014a1f,
    0 12px 24px rgb(6 199 85 / 0.35);
  color: #fff;
}
.t-line:active {
  transform: translateY(3px);
  box-shadow: 0 2px 0 #014a1f;
}
@media (prefers-reduced-motion: reduce) {
  .t-floor,
  .t-float,
  .t-blink {
    animation: none;
  }
}
</style>
