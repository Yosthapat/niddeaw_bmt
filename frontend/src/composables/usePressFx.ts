/**
 * A ring that spreads from where a button was pressed, on the admin's
 * screens: a tap answers at once, before whatever it does has loaded.
 *
 * The ring is drawn on the page, at the pointer, rather than inside the
 * button: putting an element into a button would change its layout (flex
 * gaps, the last child, :empty), and a ring on top of the page never does.
 * The press itself (the slight squeeze) is CSS, in tailwind.css.
 */
import { onBeforeUnmount, onMounted } from 'vue'

const TARGETS = 'button, a[href], [role="button"], [role="tab"], [role="radio"], summary, label:has(input)'

export function usePressFx(enabled: () => boolean): void {
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)')

  function onDown(e: PointerEvent): void {
    if (!enabled() || reduce.matches || e.button !== 0) return
    const hit = (e.target as Element | null)?.closest(TARGETS)
    if (!hit || (hit as HTMLButtonElement).disabled || hit.getAttribute('aria-disabled') === 'true') return
    const ring = document.createElement('span')
    ring.className = 'press-ring'
    ring.style.left = `${e.clientX}px`
    ring.style.top = `${e.clientY}px`
    document.body.appendChild(ring)
    ring.addEventListener('animationend', () => ring.remove(), { once: true })
    // in case the animation never runs (a hidden tab)
    setTimeout(() => ring.remove(), 1000)
  }

  onMounted(() => document.addEventListener('pointerdown', onDown, { passive: true }))
  onBeforeUnmount(() => document.removeEventListener('pointerdown', onDown))
}
