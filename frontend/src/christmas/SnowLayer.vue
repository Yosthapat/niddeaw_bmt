<script setup lang="ts">
/**
 * Snow over the public pages: soft white and pink flakes with a neon halo,
 * a few snow crystals, and now and then a shuttlecock drifting down with
 * them. One canvas fixed over the page that lets every tap through.
 *
 * Kept light for a phone at the court: few flakes on a small screen, at
 * most twice the screen's pixels, nothing drawn while the tab is hidden,
 * and none at all with reduced motion or when the member turned it off
 * (prefs.ts, from the music card).
 */
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { snowOn } from './prefs'
import { reducedMotion } from './season'
import { crystalSprite, flakeSprite, shuttleSprite, SNOW_PINK, SNOW_WHITE } from './sprites'

interface Flake {
  x: number
  y: number
  size: number
  fall: number
  sway: number
  phase: number
  spin: number
  angle: number
  alpha: number
  sprite: HTMLCanvasElement
}

const canvas = ref<HTMLCanvasElement | null>(null)
const still = reducedMotion()

let g: CanvasRenderingContext2D | null = null
let flakes: Flake[] = []
let raf = 0
let last = 0
let w = 0
let h = 0
let sprites: { white: HTMLCanvasElement; pink: HTMLCanvasElement; crystal: HTMLCanvasElement; shuttle: HTMLCanvasElement } | null = null

function make(y: number): Flake {
  const s = sprites!
  const roll = Math.random()
  // 1 in 20 is a shuttlecock, 1 in 8 a crystal, the rest soft flakes
  const sprite = roll < 0.05 ? s.shuttle : roll < 0.17 ? s.crystal : Math.random() < 0.3 ? s.pink : s.white
  const big = sprite === s.shuttle ? 26 + Math.random() * 10 : sprite === s.crystal ? 14 + Math.random() * 10 : 6 + Math.random() * 10
  return {
    x: Math.random() * w,
    y,
    size: big,
    // bigger flakes are nearer, so they fall faster
    fall: 18 + big * 2.2 + Math.random() * 14,
    sway: 8 + Math.random() * 22,
    phase: Math.random() * Math.PI * 2,
    spin: sprite === s.white || sprite === s.pink ? 0 : (Math.random() - 0.5) * 1.2,
    angle: Math.random() * Math.PI * 2,
    alpha: 0.55 + Math.random() * 0.45,
    sprite,
  }
}

function resize(): void {
  const c = canvas.value
  if (!c) return
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  w = window.innerWidth
  h = window.innerHeight
  c.width = Math.round(w * dpr)
  c.height = Math.round(h * dpr)
  g = c.getContext('2d')
  g?.setTransform(dpr, 0, 0, dpr, 0, 0)
  // about one flake per 12,000 px²: ~30 on a phone, ~90 on a laptop
  const want = Math.round(Math.min(120, Math.max(28, (w * h) / 12000)))
  while (flakes.length < want) flakes.push(make(Math.random() * h))
  flakes.length = want
}

function frame(now: number): void {
  raf = requestAnimationFrame(frame)
  const dt = Math.min((now - (last || now)) / 1000, 0.05)
  last = now
  if (!g) return
  g.clearRect(0, 0, w, h)
  for (const f of flakes) {
    f.y += f.fall * dt
    f.phase += dt * 0.9
    f.angle += f.spin * dt
    if (f.y - f.size > h) Object.assign(f, make(-f.size))
    const x = f.x + Math.sin(f.phase) * f.sway
    g.globalAlpha = f.alpha
    if (f.spin) {
      g.save()
      g.translate(x, f.y)
      g.rotate(f.angle)
      g.drawImage(f.sprite, -f.size / 2, -f.size / 2, f.size, f.size)
      g.restore()
    } else {
      g.drawImage(f.sprite, x - f.size / 2, f.y - f.size / 2, f.size, f.size)
    }
  }
  g.globalAlpha = 1
}

function run(): void {
  const go = snowOn.value && !document.hidden && !still
  if (go && !raf) {
    last = 0
    raf = requestAnimationFrame(frame)
  } else if (!go && raf) {
    cancelAnimationFrame(raf)
    raf = 0
    g?.clearRect(0, 0, w, h)
  }
}

onMounted(() => {
  if (still) return
  sprites = { white: flakeSprite(SNOW_WHITE), pink: flakeSprite(SNOW_PINK), crystal: crystalSprite(SNOW_WHITE), shuttle: shuttleSprite() }
  resize()
  window.addEventListener('resize', resize)
  document.addEventListener('visibilitychange', run)
  run()
})
watch(snowOn, run)
onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  raf = 0
  window.removeEventListener('resize', resize)
  document.removeEventListener('visibilitychange', run)
})
</script>

<template>
  <canvas v-if="!still" ref="canvas" class="xmas-snow" aria-hidden="true" />
</template>

<style scoped>
.xmas-snow {
  position: fixed;
  inset: 0;
  width: 100%;
  height: 100%;
  /* over the page, under the header (z-20), the tab bar and dialogs */
  z-index: 15;
  pointer-events: none;
}
</style>
