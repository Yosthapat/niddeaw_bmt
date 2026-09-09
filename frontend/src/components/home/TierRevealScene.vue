<script setup lang="ts">
// Full-screen "impact" takeover for the home hero's tier row — tapping a
// tier mascot there opens this instead of the small TierInfoModal (which
// every OTHER TierMascot on the site still uses unchanged). Same real
// tier copy/colors/gradient as TierInfoModal, just staged as a cinematic
// moment: a color-wash flash, a screen-wide particle burst, a pulsing
// glow ring around a big mascot, and drifting embers for as long as the
// scene stays open.
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { EloTier } from '@/types'
import { tierMeta, tierTextStyle } from '@/composables/useEloTier'
import TierMascot from '@/components/players/TierMascot.vue'
import TypewriterText from '@/components/common/TypewriterText.vue'

const props = defineProps<{ tier: EloTier | null }>()
const emit = defineEmits<{ close: [] }>()

const { t } = useI18n()

const meta = computed(() => (props.tier ? tierMeta(props.tier) : null))
const blurb = computed(() => (props.tier ? t(`tierInfo.${props.tier}`) : ''))
const accentStyle = computed(() =>
  meta.value ? { '--accent': meta.value.gradient ? '#c96dff' : meta.value.colorVar } : {},
)

const canvasEl = ref<HTMLCanvasElement | null>(null)
const shaking = ref(false)
const flashing = ref(false)

type Particle = { x: number; y: number; vx: number; vy: number; born: number; life: number; size: number; rgb: string }
type Ember = { x: number; y: number; speed: number; drift: number; size: number; phase: number }

let ctx: CanvasRenderingContext2D | null = null
let sparks: Particle[] = []
let embers: Ember[] = []
let emberRgb = '234,76,164'
let rafId: number | null = null
let lastFrame = 0
const reduceMotion =
  typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

function resizeCanvas(): void {
  const el = canvasEl.value
  if (!el) return
  const ratio = Math.min(window.devicePixelRatio || 1, 2)
  el.width = window.innerWidth * ratio
  el.height = window.innerHeight * ratio
  ctx?.setTransform(ratio, 0, 0, ratio, 0, 0)
}

function hexToRgb(hex: string): string {
  const n = parseInt(hex.replace('#', ''), 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255].join(',')
}

function resolveRgb(colorVar: string): string {
  // colorVar is a CSS var() reference (e.g. "var(--color-tier-milk)") —
  // resolve it against the real document so the burst matches the exact
  // token color instead of guessing/duplicating the hex here.
  const probe = document.createElement('span')
  probe.style.color = colorVar
  document.body.appendChild(probe)
  const rgb = getComputedStyle(probe).color
  document.body.removeChild(probe)
  const match = rgb.match(/\d+/g)
  return match ? match.slice(0, 3).join(',') : hexToRgb('#ea4ca4')
}

function burst(rgb: string): void {
  if (reduceMotion) return
  const cx = window.innerWidth / 2
  const cy = window.innerHeight * 0.42
  for (let i = 0; i < 160; i++) {
    const angle = Math.random() * Math.PI * 2
    const speed = 120 + Math.random() * 420
    sparks.push({
      x: cx,
      y: cy,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      born: performance.now(),
      life: 700 + Math.random() * 700,
      size: 2 + Math.random() * 4,
      rgb,
    })
  }
}

function seedEmbers(rgb: string, count: number): void {
  embers = []
  if (reduceMotion) return
  emberRgb = rgb
  for (let i = 0; i < count; i++) {
    embers.push({
      x: Math.random() * window.innerWidth,
      y: window.innerHeight + Math.random() * 200,
      speed: 14 + Math.random() * 26,
      drift: (Math.random() - 0.5) * 14,
      size: 1 + Math.random() * 2.4,
      phase: Math.random() * Math.PI * 2,
    })
  }
}

function loop(now: number): void {
  rafId = requestAnimationFrame(loop)
  const dt = Math.min((now - lastFrame) / 1000, 0.05)
  lastFrame = now
  if (!ctx) return
  ctx.clearRect(0, 0, window.innerWidth, window.innerHeight)
  ctx.globalCompositeOperation = 'lighter'

  for (let i = sparks.length - 1; i >= 0; i--) {
    const sp = sparks[i]
    const age = now - sp.born
    if (age > sp.life) {
      sparks.splice(i, 1)
      continue
    }
    sp.x += sp.vx * dt
    sp.y += sp.vy * dt
    sp.vy += 70 * dt
    sp.vx *= 0.985
    sp.vy *= 0.985
    const alpha = 1 - age / sp.life
    const r = sp.size * (0.5 + 0.5 * alpha) * 3.2
    const g = ctx.createRadialGradient(sp.x, sp.y, 0, sp.x, sp.y, r)
    g.addColorStop(0, `rgba(${sp.rgb},${alpha})`)
    g.addColorStop(1, `rgba(${sp.rgb},0)`)
    ctx.fillStyle = g
    ctx.beginPath()
    ctx.arc(sp.x, sp.y, r, 0, Math.PI * 2)
    ctx.fill()
  }

  for (const em of embers) {
    em.y -= em.speed * dt
    em.x += Math.sin(now / 900 + em.phase) * em.drift * dt
    if (em.y < -20) em.y = window.innerHeight + 20
    const r = em.size * 3
    const g = ctx.createRadialGradient(em.x, em.y, 0, em.x, em.y, r)
    g.addColorStop(0, `rgba(${emberRgb},0.5)`)
    g.addColorStop(1, `rgba(${emberRgb},0)`)
    ctx.fillStyle = g
    ctx.beginPath()
    ctx.arc(em.x, em.y, r, 0, Math.PI * 2)
    ctx.fill()
  }

  ctx.globalCompositeOperation = 'source-over'
}

watch(
  () => props.tier,
  (tier) => {
    if (!tier || !meta.value) {
      embers = []
      return
    }
    const rgb = resolveRgb(meta.value.gradient ?? meta.value.colorVar)
    seedEmbers(rgb, meta.value.gradient ? 70 : 40)
    burst(rgb)

    if (!reduceMotion) {
      flashing.value = false
      shaking.value = false
      requestAnimationFrame(() => {
        flashing.value = true
        shaking.value = true
      })
    }
  },
)

function onMountedCanvas(): void {
  const el = canvasEl.value
  if (!el) return
  ctx = el.getContext('2d')
  resizeCanvas()
  window.addEventListener('resize', resizeCanvas)
  lastFrame = performance.now()
  rafId = requestAnimationFrame(loop)
}

watch(canvasEl, (el) => {
  if (el) onMountedCanvas()
})

onBeforeUnmount(() => {
  if (rafId) cancelAnimationFrame(rafId)
  window.removeEventListener('resize', resizeCanvas)
})

function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Escape') emit('close')
}
watch(
  () => props.tier,
  (tier) => {
    if (tier) window.addEventListener('keydown', onKeydown)
    else window.removeEventListener('keydown', onKeydown)
  },
)
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <Teleport to="body">
    <div
      class="reveal-stage"
      :class="{ open: !!tier, shake: shaking }"
      :style="accentStyle"
      @animationend="shaking = false"
    >
      <canvas ref="canvasEl" class="fx-canvas" aria-hidden="true" />
      <div class="flash" :class="{ pop: flashing }" @animationend="flashing = false" />

      <template v-if="meta">
        <div class="wash" />
        <button type="button" class="back-btn" @click="emit('close')">← กลับไปดูทุก tier</button>

        <div class="content">
          <div class="ring">
            <TierMascot :tier="meta.tier" :size="140" :interactive="false" />
          </div>
          <p class="eyebrow">ระดับ ELO</p>
          <h2 class="tier-name" :class="{ 'tier-shimmer': meta.gradient }" :style="tierTextStyle(meta.colorVar, meta.gradient)">
            {{ meta.label }}
          </h2>
          <p class="blurb">
            <TypewriterText :key="meta.tier" :text="blurb" :chars-per-second="55" />
          </p>
        </div>
      </template>
    </div>
  </Teleport>
</template>

<style scoped>
.reveal-stage {
  position: fixed;
  inset: 0;
  z-index: 60;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.2s ease;
  overflow: hidden;
}
.reveal-stage.open {
  opacity: 1;
  pointer-events: auto;
  transition: opacity 0.3s ease;
}
.reveal-stage.shake {
  animation: reveal-shake 0.32s cubic-bezier(0.36, 0.07, 0.19, 0.97);
}
@keyframes reveal-shake {
  10% {
    transform: translate(-3px, 2px);
  }
  25% {
    transform: translate(4px, -2px);
  }
  40% {
    transform: translate(-4px, -1px);
  }
  55% {
    transform: translate(3px, 2px);
  }
  70% {
    transform: translate(-2px, -2px);
  }
  85% {
    transform: translate(2px, 1px);
  }
  100% {
    transform: translate(0, 0);
  }
}

.fx-canvas {
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
}

.flash {
  position: absolute;
  inset: 0;
  z-index: 3;
  background: var(--accent, #ea4ca4);
  opacity: 0;
  pointer-events: none;
}
.flash.pop {
  animation: reveal-flash 0.42s ease-out;
}
@keyframes reveal-flash {
  0% {
    opacity: 0.85;
  }
  100% {
    opacity: 0;
  }
}

.wash {
  position: absolute;
  inset: 0;
  z-index: 0;
  background: radial-gradient(
      closest-side,
      color-mix(in srgb, var(--accent, #ea4ca4) 55%, transparent) 0%,
      color-mix(in srgb, var(--accent, #ea4ca4) 16%, transparent) 42%,
      transparent 72%
    ),
    var(--color-brand-black);
  opacity: 0;
  transform: scale(0.85);
  transition: opacity 0.3s ease, transform 0.3s ease;
}
.reveal-stage.open .wash {
  opacity: 1;
  transform: scale(1);
  transition: opacity 0.55s cubic-bezier(0.16, 1, 0.3, 1), transform 0.7s cubic-bezier(0.16, 1, 0.3, 1);
}

.back-btn {
  position: absolute;
  top: 1rem;
  left: 1rem;
  z-index: 4;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  background: rgb(24 14 19 / 0.6);
  border: 1px solid rgb(255 255 255 / 0.14);
  color: rgb(243 233 238 / 0.6);
  padding: 0.5rem 0.9rem;
  font-family: var(--font-display);
  font-size: 0.75rem;
  letter-spacing: 0.03em;
  clip-path: polygon(8px 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%, 0 8px);
  cursor: pointer;
  opacity: 0;
  transform: translateY(-6px);
  transition: opacity 0.2s ease, transform 0.2s ease, color 0.2s ease, border-color 0.2s ease;
}
.reveal-stage.open .back-btn {
  opacity: 1;
  transform: translateY(0);
  transition: opacity 0.35s ease 0.4s, transform 0.35s ease 0.4s, color 0.2s ease, border-color 0.2s ease;
}
.back-btn:hover {
  color: rgb(243 233 238);
  border-color: var(--accent, #ea4ca4);
}

.content {
  position: relative;
  z-index: 1;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 4.5rem 1.5rem 3rem;
}

.ring {
  position: relative;
  width: 11rem;
  height: 11rem;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgb(10 4 6 / 0.35);
  opacity: 0;
  transform: scale(0.3);
  filter: blur(10px);
  transition: opacity 0.2s ease, transform 0.2s ease, filter 0.2s ease;
}
.reveal-stage.open .ring {
  opacity: 1;
  transform: scale(1);
  filter: blur(0);
  transition: opacity 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) 0.08s, transform 0.55s cubic-bezier(0.34, 1.56, 0.64, 1) 0.08s,
    filter 0.4s ease 0.08s;
}
.ring::before {
  content: '';
  position: absolute;
  inset: -14px;
  border-radius: 999px;
  border: 2px solid var(--accent, #ea4ca4);
  box-shadow: 0 0 60px 4px var(--accent, #ea4ca4), inset 0 0 40px -6px var(--accent, #ea4ca4);
  opacity: 0.85;
  animation: reveal-ring-pulse 2.2s ease-in-out infinite;
}
@keyframes reveal-ring-pulse {
  0%,
  100% {
    transform: scale(1);
    opacity: 0.7;
  }
  50% {
    transform: scale(1.06);
    opacity: 1;
  }
}

.eyebrow {
  margin: 1.4rem 0 0;
  font-family: var(--font-display);
  font-size: 0.72rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: rgb(243 233 238 / 0.4);
  opacity: 0;
  transform: translateY(10px);
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.reveal-stage.open .eyebrow {
  opacity: 1;
  transform: translateY(0);
  transition: opacity 0.4s ease 0.32s, transform 0.4s ease 0.32s;
}

.tier-name {
  margin: 0.3rem 0 0;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: clamp(2.4rem, 10vw, 4.2rem);
  line-height: 1;
  letter-spacing: 0.01em;
  text-transform: uppercase;
  opacity: 0;
  transform: translateY(14px) scale(0.94);
  filter: blur(3px);
  transition: opacity 0.2s ease, transform 0.2s ease, filter 0.2s ease;
}
.reveal-stage.open .tier-name {
  opacity: 1;
  transform: translateY(0) scale(1);
  filter: blur(0);
  transition: opacity 0.45s cubic-bezier(0.16, 1, 0.3, 1) 0.4s, transform 0.45s cubic-bezier(0.16, 1, 0.3, 1) 0.4s,
    filter 0.45s ease 0.4s;
}

.blurb {
  margin: 1.2rem 0 0;
  max-width: 32rem;
  min-height: 5.5rem;
  font-size: 0.95rem;
  line-height: 1.75;
  color: rgb(255 255 255 / 0.85);
  white-space: pre-line;
  opacity: 0;
  transform: translateY(10px);
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.reveal-stage.open .blurb {
  opacity: 1;
  transform: translateY(0);
  transition: opacity 0.4s ease 0.62s, transform 0.4s ease 0.62s;
}

@media (max-width: 640px) {
  .ring {
    width: 8.5rem;
    height: 8.5rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .reveal-stage.shake {
    animation: none;
  }
  .flash.pop {
    animation: none;
    opacity: 0 !important;
  }
  .ring::before {
    animation: none;
  }
  .wash,
  .back-btn,
  .ring,
  .eyebrow,
  .tier-name,
  .blurb {
    transition: opacity 0.15s linear !important;
    transform: none !important;
    filter: none !important;
  }
}
</style>
