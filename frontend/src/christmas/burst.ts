/**
 * A burst of snow and shuttlecocks from a point on the screen, for the
 * moments worth cheering: a match won, a result saved, a medal earned.
 *
 * Works on any page, LINE and admin ones included: it brings its own
 * canvas, fixed over everything, and takes it away again when the last
 * flake has faded. Does nothing outside the season or with reduced motion.
 */
import { reducedMotion, xmasOn } from './season'
import { crystalSprite, flakeSprite, shuttleSprite, SNOW_PINK, SNOW_WHITE } from './sprites'

interface Bit {
  x: number
  y: number
  vx: number
  vy: number
  size: number
  life: number
  ttl: number
  angle: number
  spin: number
  sprite: HTMLCanvasElement
}

const LIFE = 1.6
let canvas: HTMLCanvasElement | null = null
let g: CanvasRenderingContext2D | null = null
let bits: Bit[] = []
let raf = 0
let last = 0
let sprites: HTMLCanvasElement[] | null = null

function ensureCanvas(): boolean {
  if (canvas && g) return true
  canvas = document.createElement('canvas')
  canvas.setAttribute('aria-hidden', 'true')
  Object.assign(canvas.style, { position: 'fixed', inset: '0', width: '100%', height: '100%', zIndex: '90', pointerEvents: 'none' })
  document.body.appendChild(canvas)
  g = canvas.getContext('2d')
  sizeCanvas()
  window.addEventListener('resize', sizeCanvas)
  return !!g
}

function sizeCanvas(): void {
  if (!canvas) return
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  canvas.width = Math.round(window.innerWidth * dpr)
  canvas.height = Math.round(window.innerHeight * dpr)
  g?.setTransform(dpr, 0, 0, dpr, 0, 0)
}

function teardown(): void {
  window.removeEventListener('resize', sizeCanvas)
  canvas?.remove()
  canvas = null
  g = null
  raf = 0
}

function frame(now: number): void {
  const dt = Math.min((now - (last || now)) / 1000, 0.05)
  last = now
  if (!g || !canvas) return teardown()
  g.clearRect(0, 0, window.innerWidth, window.innerHeight)
  bits = bits.filter((b) => (b.life += dt) < b.ttl)
  for (const b of bits) {
    // thrown out fast, then slowed by the air and drifting down like snow
    b.vx *= 1 - 2.4 * dt
    b.vy = b.vy * (1 - 2.4 * dt) + 60 * dt
    b.x += b.vx * dt
    b.y += b.vy * dt
    b.angle += b.spin * dt
    g.globalAlpha = Math.max(0, 1 - (b.life / b.ttl) ** 2)
    g.save()
    g.translate(b.x, b.y)
    g.rotate(b.angle)
    g.drawImage(b.sprite, -b.size / 2, -b.size / 2, b.size, b.size)
    g.restore()
  }
  g.globalAlpha = 1
  if (bits.length) raf = requestAnimationFrame(frame)
  else teardown()
}

/** Burst at a point in the viewport, in CSS px. */
export function burstAt(x: number, y: number, count = 46): void {
  if (!xmasOn || reducedMotion() || !ensureCanvas()) return
  sprites ??= [flakeSprite(SNOW_WHITE), flakeSprite(SNOW_PINK), flakeSprite(SNOW_WHITE), crystalSprite(SNOW_WHITE), shuttleSprite()]
  for (let i = 0; i < count; i++) {
    const a = Math.random() * Math.PI * 2
    const speed = 160 + Math.random() * 380
    const sprite = sprites[i % 9 === 0 ? 4 : Math.floor(Math.random() * 4)]!
    const shuttle = sprite === sprites[4]
    bits.push({
      x,
      y,
      vx: Math.cos(a) * speed,
      vy: Math.sin(a) * speed - 120,
      size: shuttle ? 30 : 8 + Math.random() * 16,
      life: 0,
      ttl: LIFE * (0.7 + Math.random() * 0.5),
      angle: Math.random() * Math.PI,
      spin: (Math.random() - 0.5) * 8,
      sprite,
    })
  }
  if (!raf) {
    last = 0
    raf = requestAnimationFrame(frame)
  }
}

/** Burst from an element: its centre, or `at` across it (0 left … 1 right). */
export function burstFrom(el: Element | null | undefined, at = 0.5): void {
  if (!el) return burstAt(window.innerWidth / 2, window.innerHeight / 2)
  const r = el.getBoundingClientRect()
  burstAt(r.left + r.width * at, r.top + r.height / 2)
}
