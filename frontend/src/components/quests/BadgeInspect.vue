<script setup lang="ts">
/**
 * One medal, up close. It flies from its slot on the shelf (`source`) to
 * the middle and spins once into place; rays turn behind it and sparks
 * burst if it is earned. Tap it (or drag it sideways) to turn it over: the
 * back is the same medal in dull metal with the quest's name, what to do,
 * the levels and the date engraved on a plate. Closing flies it home.
 *
 * `celebrate`: a medal just won (the LINE page shows each new one once).
 * It drops in from above with a bigger burst and a "new badge" heading.
 *
 * With reduced motion it fades in and out, and turning over is instant.
 */
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { BadgeItem, Metal } from '@/utils/quests'

const props = defineProps<{ item: BadgeItem | null; source?: HTMLElement | null; celebrate?: boolean }>()
const emit = defineEmits<{ close: [] }>()
const { t } = useI18n()

const shown = ref<BadgeItem | null>(null)
const root = ref<HTMLElement | null>(null)
const bg = ref<HTMLElement | null>(null)
const rays = ref<HTMLElement | null>(null)
const stage = ref<HTMLElement | null>(null)
const coin = ref<HTMLElement | null>(null)
const cap = ref<HTMLElement | null>(null)
const actions = ref<HTMLElement | null>(null)
const shine = ref<HTMLElement | null>(null)
const flipBtn = ref<HTMLButtonElement | null>(null)
let angle = 0
let busy = false
let lastFocus: HTMLElement | null = null
const reduce = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

const PAL: Record<Metal, string[]> = {
  b: ['#4a2e1c', '#1a0f08', '#b0744a', '#f0c49a', '0.7'],
  s: ['#3a3f48', '#14171c', '#aab4c2', '#e8eef6', '0.05'],
  g: ['#4a3a1c', '#1c1408', '#c8952e', '#f4d27a', '0.55'],
  p: ['#4a1c38', '#1c0814', '#e05aa6', '#ffd1ea', '0.25'],
}
const backStyle = (m: Metal, src: string): Record<string, string> => {
  const p = PAL[m]
  return { '--m': `url(${src})`, '--b1': p[0]!, '--b2': p[1]!, '--rim': p[2]!, '--ink': p[3]!, '--sep': p[4]! }
}

function setAngle(a: number): void {
  angle = a
  if (coin.value) coin.value.style.transform = `rotateY(${a}deg)`
}

function delta(): { dx: number; dy: number; s: number } | null {
  if (!props.source || !stage.value) return null
  const to = stage.value.getBoundingClientRect()
  const from = props.source.getBoundingClientRect()
  if (!from.width) return null
  return {
    dx: from.left + from.width / 2 - (to.left + to.width / 2),
    dy: from.top + from.height / 2 - (to.top + to.height / 2),
    s: from.width / to.width,
  }
}

function sparks(n: number): void {
  if (reduce || !stage.value || !root.value || shown.value?.locked) return
  const r = stage.value.getBoundingClientRect()
  for (let i = 0; i < n; i++) {
    const s = document.createElement('span')
    s.className = 'badge-spark'
    s.style.left = `${r.left + r.width / 2}px`
    s.style.top = `${r.top + r.height / 2}px`
    root.value.appendChild(s)
    const a = (i / n) * Math.PI * 2 + Math.random() * 0.3
    const d = r.width * (0.55 + Math.random() * 0.4)
    const sc = 0.6 + Math.random() * 1.2
    s.animate(
      [
        { transform: 'translate(-50%,-50%) scale(0) rotate(0deg)', opacity: 1 },
        { transform: `translate(calc(-50% + ${Math.cos(a) * d}px), calc(-50% + ${Math.sin(a) * d}px)) scale(${sc}) rotate(140deg)`, opacity: 0 },
      ],
      { duration: 900 + Math.random() * 400, easing: 'cubic-bezier(.2,.7,.3,1)' },
    ).onfinish = () => s.remove()
  }
}

function sweep(): void {
  if (reduce || !shine.value) return
  shine.value.animate([{ backgroundPosition: '150% 0' }, { backgroundPosition: '-60% 0' }], { duration: 900, easing: 'ease-in-out', delay: 120 })
}

async function open(): Promise<void> {
  busy = true
  lastFocus = document.activeElement as HTMLElement | null
  setAngle(0)
  await nextTick()
  if (!stage.value || !bg.value || !rays.value || !cap.value || !actions.value) return
  cap.value.style.opacity = '0'
  actions.value.style.opacity = '0'
  rays.value.style.opacity = '0'
  bg.value.animate([{ opacity: 0 }, { opacity: 1 }], { duration: reduce ? 180 : 260, fill: 'forwards' })
  const d = delta()
  if (reduce) {
    await stage.value.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 180 }).finished
  } else if (props.celebrate || !d) {
    await stage.value.animate(
      [
        { transform: 'translateY(-60vh) scale(0.3) rotateY(-720deg)', opacity: 0 },
        { transform: 'translateY(12px) scale(1.12) rotateY(-30deg)', opacity: 1, offset: 0.7 },
        { transform: 'translateY(0) scale(1) rotateY(0deg)' },
      ],
      { duration: 1100, easing: 'cubic-bezier(.2,.8,.3,1)' },
    ).finished
    if (navigator.userActivation?.hasBeenActive) navigator.vibrate?.(30)
    sparks(22)
    sweep()
  } else {
    await stage.value.animate(
      [
        { transform: `translate(${d.dx}px, ${d.dy}px) scale(${d.s}) rotateY(0deg)` },
        { transform: `translate(${d.dx * 0.3}px, ${d.dy * 0.3 - 30}px) scale(${(d.s + 1.1) / 2}) rotateY(200deg)`, offset: 0.55 },
        { transform: 'translate(0,0) scale(1.06) rotateY(350deg)', offset: 0.85 },
        { transform: 'translate(0,0) scale(1) rotateY(360deg)' },
      ],
      { duration: 720, easing: 'cubic-bezier(.25,.8,.3,1)' },
    ).finished
    sparks(14)
    sweep()
  }
  rays.value.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 500, fill: 'forwards' })
  cap.value.animate([{ opacity: 0, transform: 'translateY(10px)' }, { opacity: 1, transform: 'none' }], { duration: 360, easing: 'ease-out', fill: 'forwards' })
  actions.value.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 360, delay: 120, fill: 'forwards' })
  busy = false
  flipBtn.value?.focus({ preventScroll: true })
}

async function close(): Promise<void> {
  if (busy || !shown.value || !stage.value || !bg.value) return
  busy = true
  rays.value?.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 200, fill: 'forwards' })
  cap.value?.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 150, fill: 'forwards' })
  actions.value?.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 150, fill: 'forwards' })
  if (Math.round(angle / 180) % 2 !== 0) setAngle(angle + 180)
  bg.value.animate([{ opacity: 1 }, { opacity: 0 }], { duration: reduce ? 150 : 380, fill: 'forwards' })
  const d = props.celebrate ? null : delta()
  if (reduce || !d) {
    await stage.value.animate([{ opacity: 1, transform: 'none' }, { opacity: 0, transform: reduce ? 'none' : 'scale(0.6)' }], { duration: reduce ? 150 : 300 }).finished
  } else {
    await stage.value.animate([{ transform: 'none' }, { transform: `translate(${d.dx}px, ${d.dy}px) scale(${d.s})` }], { duration: 380, easing: 'cubic-bezier(.5,0,.75,0)' }).finished
  }
  shown.value = null
  busy = false
  emit('close')
  lastFocus?.focus({ preventScroll: true })
}

function flip(): void {
  if (busy) return
  const target = (Math.round(angle / 180) + 1) * 180
  if (!reduce && coin.value) {
    coin.value.animate(
      [{ transform: `rotateY(${angle}deg)` }, { transform: `rotateY(${target + 12}deg)`, offset: 0.78 }, { transform: `rotateY(${target}deg)` }],
      { duration: 650, easing: 'cubic-bezier(.3,.7,.3,1)' },
    )
    setTimeout(sweep, 380)
  }
  setAngle(target)
}

// drag sideways to turn it; a tap turns it over
let drag: { x: number; a: number; moved: boolean } | null = null
function down(e: PointerEvent): void {
  if (busy) return
  drag = { x: e.clientX, a: angle, moved: false }
  stage.value?.setPointerCapture(e.pointerId)
}
function move(e: PointerEvent): void {
  if (!drag) return
  const dx = e.clientX - drag.x
  if (Math.abs(dx) > 6) drag.moved = true
  if (drag.moved) setAngle(drag.a + dx * 0.7)
}
function up(): void {
  if (!drag) return
  const d = drag
  drag = null
  if (!d.moved) return flip()
  const target = Math.round(angle / 180) * 180
  if (!reduce && coin.value) {
    coin.value.animate([{ transform: `rotateY(${angle}deg)` }, { transform: `rotateY(${target}deg)` }], { duration: 380, easing: 'cubic-bezier(.3,1.5,.5,1)' })
  }
  setAngle(target)
}

function onKey(e: KeyboardEvent): void {
  if (!shown.value) return
  if (e.key === 'Escape') void close()
}

watch(
  () => props.item,
  (item) => {
    if (item && !shown.value) {
      shown.value = item
      void open()
    }
  },
)
window.addEventListener('keydown', onKey)
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <Teleport to="body">
    <div v-if="shown" ref="root" class="insp" :class="{ locked: shown.locked }" role="dialog" aria-modal="true" :aria-label="shown.name">
      <div ref="bg" class="insp-bg" @click="close" />
      <div ref="rays" class="insp-rays" aria-hidden="true" />
      <button type="button" class="insp-x" :aria-label="t('quests.close')" @click="close">✕</button>
      <p v-if="celebrate" class="insp-new">{{ t('quests.newBadge') }}</p>
      <div
        ref="stage"
        class="insp-stage"
        role="button"
        tabindex="0"
        :aria-label="t('quests.turnOver')"
        @pointerdown="down"
        @pointermove="move"
        @pointerup="up"
        @pointercancel="up"
        @keydown.enter.prevent="flip"
        @keydown.space.prevent="flip"
      >
        <div ref="coin" class="insp-coin">
          <div class="insp-face">
            <img :src="shown.img" alt="" draggable="false" />
            <span ref="shine" class="insp-shine" :style="{ '--m': `url(${shown.img})` }" />
          </div>
          <div class="insp-face insp-back" :style="backStyle(shown.metal, shown.img)">
            <div class="insp-plate-img" />
            <div class="insp-plate">
              <p class="qn engr">{{ shown.name }}</p>
              <p class="qh engr">{{ shown.how }}</p>
              <p v-if="shown.tiers.length" class="qt engr">
                <span v-for="(tier, i) in shown.tiers" :key="i" :class="{ on: tier.done }">{{ tier.done ? '✓ ' : '' }}{{ tier.label }}</span>
              </p>
              <p class="qd engr">{{ shown.dateLabel }}</p>
            </div>
          </div>
        </div>
      </div>
      <div ref="cap" class="insp-cap">
        <p class="tier">{{ shown.tierLabel }}</p>
        <h3 class="font-display text-2xl font-bold">{{ shown.name }}</h3>
        <div v-if="shown.progress" class="prog"><i :style="{ width: `${Math.round((shown.progress.value / shown.progress.target) * 100)}%` }" /></div>
        <p class="hint">{{ shown.progress?.label ?? (shown.locked ? '' : t('quests.tapToTurn')) }}</p>
      </div>
      <div ref="actions" class="insp-actions">
        <button ref="flipBtn" type="button" class="insp-btn" @click="flip">{{ t('quests.turnOver') }}</button>
        <button v-if="celebrate" type="button" class="insp-btn gold" @click="close">{{ t('quests.keep') }}</button>
      </div>
    </div>
  </Teleport>
</template>

<style>
.badge-spark {
  position: fixed;
  z-index: 61;
  width: 10px;
  height: 10px;
  pointer-events: none;
}
.badge-spark::before {
  content: '';
  position: absolute;
  inset: 0;
  background: #fff7d6;
  clip-path: polygon(50% 0, 62% 38%, 100% 50%, 62% 62%, 50% 100%, 38% 62%, 0 50%, 38% 38%);
}
</style>

<style scoped>
.insp {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: max(16px, env(safe-area-inset-top)) max(16px, env(safe-area-inset-right)) max(16px, env(safe-area-inset-bottom)) max(16px, env(safe-area-inset-left));
  color: #f1e9f4;
}
.insp-bg {
  position: absolute;
  inset: 0;
  background: rgb(8 3 16 / 0.86);
  backdrop-filter: blur(8px);
  opacity: 0;
}
.insp-rays {
  position: absolute;
  left: 50%;
  top: 42%;
  width: min(760px, 160vw);
  aspect-ratio: 1;
  translate: -50% -50%;
  border-radius: 50%;
  pointer-events: none;
  background: repeating-conic-gradient(from 0deg, rgb(255 214 120 / 0.13) 0 7deg, transparent 7deg 18deg);
  -webkit-mask: radial-gradient(closest-side, #000 30%, transparent 100%);
  mask: radial-gradient(closest-side, #000 30%, transparent 100%);
  animation: insp-turn 24s linear infinite;
}
.insp.locked .insp-rays {
  background: repeating-conic-gradient(from 0deg, rgb(180 170 200 / 0.07) 0 7deg, transparent 7deg 18deg);
}
@keyframes insp-turn {
  to { rotate: 360deg; }
}
.insp-x {
  position: absolute;
  top: max(14px, env(safe-area-inset-top));
  right: max(14px, env(safe-area-inset-right));
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 1px solid rgb(255 255 255 / 0.2);
  background: rgb(255 255 255 / 0.06);
  font-size: 20px;
}
.insp-new {
  position: relative;
  font-family: var(--font-display, inherit);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #f2c14e;
}
.insp-stage {
  position: relative;
  width: min(300px, 74vw);
  aspect-ratio: 1;
  perspective: 1100px;
  touch-action: pan-y;
  cursor: grab;
}
.insp-stage:focus-visible,
.insp-btn:focus-visible,
.insp-x:focus-visible {
  outline: 2px solid #f2c14e;
  outline-offset: 2px;
}
.insp-coin {
  position: absolute;
  inset: 0;
  transform-style: preserve-3d;
}
.insp-face {
  position: absolute;
  inset: 0;
  backface-visibility: hidden;
  -webkit-backface-visibility: hidden;
}
.insp-face img {
  display: block;
  width: 100%;
  height: 100%;
  filter: drop-shadow(0 18px 24px rgb(0 0 0 / 0.6));
  user-select: none;
  pointer-events: none;
}
.insp.locked .insp-face img {
  filter: grayscale(1) brightness(0.5) drop-shadow(0 18px 24px rgb(0 0 0 / 0.6));
}
.insp-shine {
  position: absolute;
  inset: 0;
  pointer-events: none;
  -webkit-mask: var(--m) center / contain no-repeat;
  mask: var(--m) center / contain no-repeat;
  background: linear-gradient(105deg, transparent 40%, rgb(255 255 255 / 0.55) 50%, transparent 60%);
  background-size: 260% 100%;
  background-position: 150% 0;
}
.insp-back {
  transform: rotateY(180deg);
}
.insp-plate-img {
  position: absolute;
  inset: 0;
  background: var(--m) center / contain no-repeat;
  transform: scaleX(-1);
  filter: grayscale(1) sepia(var(--sep, 0.55)) brightness(0.36) contrast(1.15) drop-shadow(0 18px 24px rgb(0 0 0 / 0.6));
}
.insp-plate {
  position: absolute;
  left: 50%;
  top: 47%;
  display: flex;
  width: 64%;
  aspect-ratio: 1;
  translate: -50% -50%;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4%;
  border-radius: 50%;
  padding: 10% 9%;
  text-align: center;
  background: radial-gradient(circle at 35% 30%, var(--b1), var(--b2) 70%);
  box-shadow: inset 0 3px 6px rgb(0 0 0 / 0.7), inset 0 -2px 3px rgb(255 255 255 / 0.12), 0 0 0 2px rgb(0 0 0 / 0.4), 0 0 0 4px var(--rim);
}
.engr {
  color: var(--ink);
  text-shadow: 0 -1px 0 rgb(0 0 0 / 0.75), 0 1px 0 rgb(255 255 255 / 0.22);
}
.qn { font-family: var(--font-display, inherit); font-size: clamp(16px, 5.2vw, 22px); font-weight: 700; line-height: 1.1; }
.qh { font-size: clamp(10px, 3vw, 12.5px); line-height: 1.35; opacity: 0.9; }
.qt { display: flex; flex-wrap: wrap; justify-content: center; gap: 4px 6px; font-size: clamp(9.5px, 2.8vw, 11px); font-weight: 600; }
.qt span { opacity: 0.45; }
.qt span.on { opacity: 1; }
.qd { font-size: clamp(9px, 2.6vw, 10.5px); letter-spacing: 0.06em; opacity: 0.7; }
.insp-cap {
  position: relative;
  display: flex;
  min-height: 88px;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  text-align: center;
}
.tier { font-size: 12px; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: #f2c14e; }
.insp.locked .tier { color: rgb(255 255 255 / 0.55); }
.hint { font-size: 12.5px; color: rgb(255 255 255 / 0.6); }
.prog { width: 200px; height: 6px; margin-top: 4px; overflow: hidden; border-radius: 99px; background: rgb(255 255 255 / 0.12); }
.prog i { display: block; height: 100%; border-radius: 99px; background: linear-gradient(90deg, #f2c14e, #ea4ca4); }
.insp-actions { position: relative; display: flex; gap: 8px; }
.insp-btn {
  min-height: 44px;
  border-radius: 999px;
  border: 1px solid rgb(255 255 255 / 0.2);
  background: rgb(255 255 255 / 0.06);
  padding: 0 18px;
  font-size: 14px;
}
.insp-btn.gold { border: 0; background: #f2c14e; color: #2a1a02; font-weight: 600; }
@media (prefers-reduced-motion: reduce) {
  .insp-rays { animation: none; }
}
</style>
