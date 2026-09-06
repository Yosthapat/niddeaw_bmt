import type { Directive } from 'vue'

const MAX_TILT_DEG = 8
const cleanups = new WeakMap<HTMLElement, () => void>()

function handleMove(el: HTMLElement, e: MouseEvent): void {
  const rect = el.getBoundingClientRect()
  const px = (e.clientX - rect.left) / rect.width - 0.5
  const py = (e.clientY - rect.top) / rect.height - 0.5
  const rotateX = (-py * MAX_TILT_DEG * 2).toFixed(2)
  const rotateY = (px * MAX_TILT_DEG * 2).toFixed(2)
  el.style.transform = `perspective(700px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`
}

function resetTransform(el: HTMLElement): void {
  el.style.transform = ''
}

/**
 * `v-tilt` — subtle 3D pointer-tilt on hover for showcase cards (podium
 * rows, a hero mascot, a profile avatar). Skipped on touch devices (no
 * hover to track), when prefers-reduced-motion is set, and when bound to
 * `false` (e.g. `v-tilt="i === 0"` inside a v-for to enable it on just
 * one item without a v-if wrapper element).
 */
export const vTilt: Directive<HTMLElement, boolean | undefined> = {
  mounted(el, binding) {
    if (binding.value === false) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    if (!window.matchMedia('(hover: hover)').matches) return

    el.style.transition = 'transform 0.15s ease'
    const onMove = (e: MouseEvent): void => handleMove(el, e)
    const onLeave = (): void => resetTransform(el)
    el.addEventListener('mousemove', onMove)
    el.addEventListener('mouseleave', onLeave)
    cleanups.set(el, () => {
      el.removeEventListener('mousemove', onMove)
      el.removeEventListener('mouseleave', onLeave)
    })
  },
  unmounted(el) {
    cleanups.get(el)?.()
    cleanups.delete(el)
  },
}
