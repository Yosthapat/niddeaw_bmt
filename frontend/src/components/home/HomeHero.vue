<script setup lang="ts">
/**
 * The home page's opening screen: the club's crowned cat standing in a
 * hologram on a neon grid floor, a striped sun on the horizon behind it,
 * the club's shout beside it, and the sponsors running past underneath
 * (SponsorBand.vue).
 *
 * Drawn twice, on purpose. The CSS scene below is what everyone sees
 * first, and what stays on a phone that cannot run more, with reduced
 * motion, or on a data saver. On a device that looks able to, the live
 * three.js version (heroScene.ts) loads after the page is up and fades in
 * over it; if it then cannot keep up, it hands back to the CSS scene.
 *
 * Both put the cat in the same place: over `anchor`, a box in the layout
 * (above the words on a phone, beside them from 900px wide). The CSS cat is
 * drawn inside it, and the 3D camera is aimed so its cat fills it too.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import type { EloTier } from '@/types'
import TierMascot from '@/components/players/TierMascot.vue'
import SponsorBand from './SponsorBand.vue'
import type { HeroScene } from './heroScene'

const emit = defineEmits<{ reveal: [tier: EloTier] }>()

const { t } = useI18n()

// Ordered by rising alcohol content — matches elo_service.py's
// _TIER_THRESHOLDS order.
const tiers: { tier: EloTier; label: string }[] = [
  { tier: 'milk', label: 'Milk' },
  { tier: 'beer', label: 'Beer' },
  { tier: 'highball', label: 'Highball' },
  { tier: 'wine', label: 'Wine' },
  { tier: 'soju', label: 'Soju' },
  { tier: 'whisky', label: 'Whisky' },
  { tier: 'vodka', label: 'Vodka' },
  { tier: 'absinthe', label: 'Absinthe' },
]

// ------------------------------------------------------------------ scene
const hero = ref<HTMLElement | null>(null)
const canvas = ref<HTMLCanvasElement | null>(null)
const anchor = ref<HTMLElement | null>(null)

type Mode = 'css' | 'loading' | 'gl'
const mode = ref<Mode>('css')
const reason = ref('')
const wide = ref(false)
const trayMascot = computed(() => (wide.value ? 44 : 30))

// `?hero=stats` shows what this device got and how fast it runs, for
// trying the hero on real phones.
const showStats = new URLSearchParams(window.location.search).get('hero') === 'stats'
const stats = ref('')

let scene: HeroScene | null = null
let gone = false
let onScreen = true
let resizeObserver: ResizeObserver | null = null
let visibilityObserver: IntersectionObserver | null = null

/** Why this device should keep the CSS hero, or null if it can try 3D. */
function unsuitable(): string | null {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return 'reduced motion'
  const nav = navigator as Navigator & { deviceMemory?: number; connection?: { saveData?: boolean } }
  if (nav.connection?.saveData) return 'data saver'
  if ((nav.hardwareConcurrency || 8) < 4) return 'fewer than 4 cores'
  if (nav.deviceMemory !== undefined && nav.deviceMemory < 4) return 'under 4GB memory'
  const probe = document.createElement('canvas').getContext('webgl2')
  if (!probe) return 'no WebGL2'
  probe.getExtension('WEBGL_lose_context')?.loseContext()
  return null
}

/** Measure the anchor and hand its place to both scenes. */
function measure(): void {
  const h = hero.value
  const a = anchor.value
  if (!h || !a) return
  const box = h.getBoundingClientRect()
  const r = a.getBoundingClientRect()
  const rel = new DOMRect(r.left - box.left, r.top - box.top, r.width, r.height)
  wide.value = box.width >= 900
  // The CSS scene's sun, ring and horizon are placed from these.
  h.style.setProperty('--ax', `${rel.x + rel.width / 2}px`)
  h.style.setProperty('--aw', `${rel.width}px`)
  h.style.setProperty('--feet', `${rel.y + rel.height * 0.97}px`)
  h.style.setProperty('--hz', `${rel.y + rel.height * 0.7}px`)
  scene?.layout(box.width, box.height, rel)
}

function run(): void {
  scene?.setRunning(onScreen && !document.hidden)
}

function giveUp(why: string): void {
  reason.value = why
  mode.value = 'css'
  scene?.dispose()
  scene = null
  stats.value = `CSS · ${why}`
}

async function startScene(): Promise<void> {
  const why = unsuitable()
  if (why) {
    reason.value = why
    stats.value = `CSS · ${why}`
    return
  }
  if (!canvas.value) return
  mode.value = 'loading'
  try {
    const { createHeroScene } = await import('./heroScene')
    if (gone || !canvas.value) return
    const created = await createHeroScene({
      canvas: canvas.value,
      followPointer: window.matchMedia('(hover: hover) and (pointer: fine)').matches,
      onFps: (fps, bloom) => {
        stats.value = `3D · ${Math.round(fps)} fps · ${bloom ? 'bloom' : 'no bloom'}`
      },
      onGiveUp: (fps) => giveUp(`too slow (${fps})`),
    })
    if (gone) {
      created.dispose()
      return
    }
    scene = created
    measure()
    run()
    visibilityObserver = new IntersectionObserver(([entry]) => {
      onScreen = entry.isIntersecting
      run()
    })
    if (hero.value) visibilityObserver.observe(hero.value)
    // One frame drawn before the fade starts, so it never fades in black.
    requestAnimationFrame(() => {
      if (scene) mode.value = 'gl'
    })
    stats.value = '3D · measuring…'
  } catch {
    giveUp('3D failed to load')
  }
}

onMounted(() => {
  measure()
  resizeObserver = new ResizeObserver(measure)
  if (hero.value) resizeObserver.observe(hero.value)
  document.addEventListener('visibilitychange', run)
  void startScene()
})

onBeforeUnmount(() => {
  gone = true
  resizeObserver?.disconnect()
  visibilityObserver?.disconnect()
  document.removeEventListener('visibilitychange', run)
  scene?.dispose()
  scene = null
})
</script>

<template>
  <!-- Pulled up by the header's height so the scene runs underneath the
       floating glass bar, then padded back down by the same amount. -->
  <section
    ref="hero"
    class="hero relative isolate overflow-hidden"
    :data-hero-mode="mode"
    :data-hero-reason="reason || undefined"
    aria-labelledby="home-hero-title"
  >
    <!-- The CSS scene: what everyone sees first. -->
    <div class="hero-scene pointer-events-none absolute inset-0 -z-20" aria-hidden="true">
      <div class="hero-sky">
        <div class="hero-stars" />
        <div class="hero-sun" />
      </div>
      <div class="hero-floor" />
      <div class="hero-horizon" />
      <div class="hero-ring" :class="{ 'opacity-0': mode === 'gl' }" />
    </div>

    <!-- The 3D scene, faded in over it once it has drawn. -->
    <canvas
      ref="canvas"
      class="pointer-events-none absolute inset-0 -z-10 h-full w-full transition-opacity duration-700"
      :class="mode === 'gl' ? 'opacity-100' : 'opacity-0'"
      aria-hidden="true"
    />
    <div class="hero-scrim pointer-events-none absolute inset-0 -z-10" aria-hidden="true" />

    <div class="hero-grid mx-auto grid max-w-6xl items-center px-4 sm:px-6">
      <div ref="anchor" class="hero-anchor relative">
        <img
          src="/hero/cat-color.webp"
          :alt="t('home.hero.catAlt')"
          width="1024"
          height="1024"
          fetchpriority="high"
          decoding="async"
          class="hero-cat block h-full w-full transition-opacity duration-700"
          :class="{ 'opacity-0': mode === 'gl' }"
        />
      </div>

      <div class="hero-copy flex flex-col items-center gap-3 text-center min-[900px]:items-start min-[900px]:gap-5 min-[900px]:text-left">
        <p class="glass-bar inline-flex min-h-8 items-center gap-2 rounded-full px-3.5 text-[13px] text-white/90">
          <span class="h-2 w-2 shrink-0 rounded-full bg-brand-pink shadow-[0_0_8px_var(--color-brand-pink)]" aria-hidden="true" />
          {{ t('home.hero.when') }}
        </p>
        <h1
          id="home-hero-title"
          class="m-0 font-display text-[clamp(1.75rem,7.6vw,3.5rem)] leading-[1.16] font-bold text-balance text-white"
        >
          <span class="hero-solid block">{{ t('home.hero.line1') }}</span>
          <span class="hero-neon block text-brand-pink">{{ t('home.hero.line2') }}</span>
        </h1>
        <p class="hero-lede m-0 max-w-[34ch] text-[15px] leading-relaxed font-light text-white/85 min-[900px]:text-lg">
          {{ t('home.hero.body') }}
        </p>
        <div class="flex flex-wrap justify-center gap-2.5 min-[900px]:justify-start min-[900px]:gap-4">
          <RouterLink to="/ranking" class="hero-btn hero-btn-hot">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5" aria-hidden="true">
              <path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0zM17 6h3v2a3 3 0 0 1-3 3M7 6H4v2a3 3 0 0 0 3 3" />
            </svg>
            {{ t('home.hero.ctaRanking') }}
          </RouterLink>
          <RouterLink to="/live" class="hero-btn glass-bar">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5" aria-hidden="true">
              <path d="M12 13a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3ZM8.5 15.5a5 5 0 0 1 0-7M15.5 8.5a5 5 0 0 1 0 7M5.6 18.4a9 9 0 0 1 0-12.8M18.4 5.6a9 9 0 0 1 0 12.8" />
            </svg>
            {{ t('home.hero.ctaLive') }}
          </RouterLink>
        </div>
        <div class="flex flex-col items-center gap-2 min-[900px]:items-start">
          <span class="text-[13px] text-white/65">{{ t('home.hero.tiersLabel') }}</span>
          <div class="glass-bar flex gap-0.5 rounded-[18px] px-2 py-1.5 min-[900px]:gap-1.5 min-[900px]:px-3 min-[900px]:py-2">
            <button
              v-for="tier in tiers"
              :key="tier.tier"
              type="button"
              class="flex min-h-11 items-center justify-center rounded-xl transition-transform hover:-translate-y-0.5"
              :aria-label="`${tier.label} tier — เปิดฉากเต็มจอ`"
              @click="emit('reveal', tier.tier)"
            >
              <TierMascot :tier="tier.tier" :size="trayMascot" :interactive="false" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <p v-if="showStats" class="glass-bar absolute top-[calc(var(--header-h)+8px)] right-3 z-10 rounded-full px-3 py-1.5 text-xs text-white/85" role="status">
      {{ stats }}
    </p>

    <SponsorBand class="mt-8 min-[900px]:mt-12" />
  </section>
</template>

<style scoped>
.hero {
  margin-top: calc(-1 * var(--header-h));
  /* where the cat stands; measure() replaces these once it has looked */
  --ax: 50%;
  --aw: 340px;
  --hz: 55%;
  --feet: 70%;
  background: #0a0416;
}

/* ---------- layout ---------- */
.hero-grid {
  padding-top: calc(var(--header-h) + 8px);
  grid-template-columns: minmax(0, 1fr);
  row-gap: 18px;
}
.hero-anchor {
  justify-self: center;
  width: min(78vw, 360px);
  aspect-ratio: 1;
}
@media (min-width: 900px) {
  .hero-grid {
    padding-top: calc(var(--header-h) + 24px);
    grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.9fr);
    column-gap: 32px;
  }
  .hero-anchor {
    order: 2;
    width: min(100%, 560px);
    justify-self: end;
  }
  .hero-copy {
    order: 1;
  }
}

/* ---------- the CSS scene ---------- */
.hero-sky {
  position: absolute;
  inset: 0 0 auto 0;
  height: var(--hz);
  overflow: hidden;
  background:
    radial-gradient(ellipse 60% 70% at var(--ax) 100%, #5b1f7d 0%, #2c1352 42%, rgb(20 10 41 / 0) 76%),
    linear-gradient(#07030f 0%, #140a2b 55%, #2a1250 100%);
}
.hero-stars {
  position: absolute;
  inset: 0;
  opacity: 0.9;
  background-image:
    radial-gradient(1.5px 1.5px at 8% 18%, #fff, transparent), radial-gradient(1.2px 1.2px at 21% 40%, #fff, transparent),
    radial-gradient(1.7px 1.7px at 33% 10%, #ffd0ea, transparent), radial-gradient(1.2px 1.2px at 47% 30%, #fff, transparent),
    radial-gradient(1.5px 1.5px at 61% 8%, #fff, transparent), radial-gradient(1.2px 1.2px at 74% 36%, #d9c7ff, transparent),
    radial-gradient(1.4px 1.4px at 88% 16%, #fff, transparent), radial-gradient(1.2px 1.2px at 95% 44%, #ffd0ea, transparent);
}
.hero-sun {
  position: absolute;
  left: var(--ax);
  bottom: calc(var(--aw) * -0.5);
  width: calc(var(--aw) * 1.15);
  aspect-ratio: 1;
  translate: -50% 0;
  border-radius: 50%;
  background: linear-gradient(#ffe0f1, #ff8fd0 30%, #ea4ca4 58%, #8e4cf0);
  -webkit-mask-image: linear-gradient(#000 0 50%, transparent 50% 54%, #000 54% 60%, transparent 60% 65%, #000 65% 70%, transparent 70%);
  mask-image: linear-gradient(#000 0 50%, transparent 50% 54%, #000 54% 60%, transparent 60% 65%, #000 65% 70%, transparent 70%);
  filter: drop-shadow(0 0 40px rgb(234 76 164 / 0.6));
}
.hero-horizon {
  position: absolute;
  left: 0;
  right: 0;
  top: calc(var(--hz) - 1px);
  height: 3px;
  background: linear-gradient(90deg, transparent, #ff8fd0 30%, #ffe0f1 60%, transparent);
  box-shadow: 0 0 22px 6px rgb(234 76 164 / 0.6);
}
.hero-floor {
  position: absolute;
  left: 0;
  right: 0;
  top: var(--hz);
  bottom: 0;
  overflow: hidden;
  perspective: 420px;
  perspective-origin: var(--ax) 0;
  background: linear-gradient(#2a0f45, #0a0416 60%);
}
.hero-floor::before {
  content: '';
  position: absolute;
  left: -80%;
  width: 260%;
  top: 0;
  height: 240%;
  transform-origin: 50% 0;
  transform: rotateX(70deg);
  background-image: linear-gradient(rgb(255 110 190 / 0.7) 2px, transparent 2px), linear-gradient(90deg, rgb(255 110 190 / 0.55) 2px, transparent 2px);
  background-size: 56px 56px;
  -webkit-mask-image: linear-gradient(transparent, #000 22%);
  mask-image: linear-gradient(transparent, #000 22%);
  animation: hero-floor 2.2s linear infinite;
}
@keyframes hero-floor {
  to {
    background-position:
      0 56px,
      0 0;
  }
}
.hero-ring {
  position: absolute;
  left: var(--ax);
  top: var(--feet);
  width: calc(var(--aw) * 1.05);
  aspect-ratio: 5 / 1;
  translate: -50% -50%;
  border-radius: 50%;
  border: 2px solid #ff9ad5;
  background: radial-gradient(closest-side, rgb(255 124 198 / 0.5), rgb(157 91 244 / 0.15) 70%, transparent);
  box-shadow:
    0 0 26px rgb(234 76 164 / 0.9),
    inset 0 0 22px rgb(234 76 164 / 0.7);
  transition: opacity 0.7s;
}
.hero-cat {
  filter: drop-shadow(14px 20px 18px rgb(6 0 20 / 0.6)) drop-shadow(0 0 28px rgb(234 76 164 / 0.45));
  animation: hero-hover 6s ease-in-out infinite;
}
@keyframes hero-hover {
  50% {
    transform: translateY(-12px);
  }
}

/* keeps the words readable whatever the scene does behind them */
.hero-scrim {
  background: linear-gradient(
    to bottom,
    rgb(10 4 22 / 0) calc(var(--feet) - 20px),
    rgb(10 4 22 / 0.72) calc(var(--feet) + 110px),
    rgb(10 4 22 / 0.88)
  );
}
@media (min-width: 900px) {
  .hero-scrim {
    background: linear-gradient(90deg, rgb(10 4 22 / 0.8) 0%, rgb(10 4 22 / 0.55) 34%, rgb(10 4 22 / 0) 56%);
  }
}

/* ---------- words ---------- */
.hero-solid {
  text-shadow:
    0 1px 0 #f6d3e8,
    0 2px 0 #e293c5,
    0 3px 0 #c766aa,
    0 4px 0 #a34a8c,
    0 5px 0 #7a2f6b,
    0 6px 0 #4e1b47,
    0 12px 20px rgb(8 0 24 / 0.75);
}
.hero-neon {
  color: #ff6cc0;
  text-shadow:
    0 0 14px rgb(255 92 184 / 0.9),
    0 0 38px rgb(234 76 164 / 0.55),
    0 3px 0 #7a1650;
}
.hero-lede {
  text-shadow: 0 2px 12px rgb(6 0 20 / 0.8);
}
.hero-btn {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  min-height: 48px;
  padding: 0 20px;
  border-radius: 14px;
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 700;
  color: #fff;
}
.hero-btn-hot {
  background: linear-gradient(#ff8fd0, #ea4ca4 55%, #c22f86);
  box-shadow:
    0 5px 0 #6d1247,
    0 12px 24px rgb(234 76 164 / 0.45),
    inset 0 1px 0 rgb(255 255 255 / 0.55);
}
.hero-btn-hot:active {
  translate: 0 3px;
  box-shadow:
    0 2px 0 #6d1247,
    0 8px 18px rgb(234 76 164 / 0.45),
    inset 0 1px 0 rgb(255 255 255 / 0.55);
}
@media (min-width: 900px) {
  .hero-btn {
    min-height: 56px;
    padding: 0 28px;
    font-size: 18px;
    border-radius: 16px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .hero-floor::before,
  .hero-cat {
    animation: none;
  }
}
</style>
