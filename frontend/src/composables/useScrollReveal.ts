import type { Directive } from 'vue'

/**
 * `v-reveal` — fades an element up into place the first time it scrolls
 * into view, instead of everything firing at once on mount (which is all
 * the old `.reveal` class in HomeView did). Pass a number as the directive
 * value to stagger list/grid items: `v-reveal="i"` delays by `i * 40ms`,
 * capped at 400ms so a long list doesn't take forever to finish revealing.
 *
 * Respects prefers-reduced-motion by skipping straight to the revealed
 * state instead of registering an observer at all.
 */
export const vReveal: Directive<HTMLElement, number | undefined> = {
  mounted(el, binding) {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      el.classList.add('is-revealed')
      return
    }

    const delayMs = Math.min(Math.max(binding.value ?? 0, 0) * 40, 400)
    el.style.setProperty('--reveal-delay', `${delayMs}ms`)
    el.classList.add('reveal-init')

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          el.classList.add('is-revealed')
          observer.disconnect()
        }
      },
      { threshold: 0.1, rootMargin: '0px 0px -10% 0px' },
    )
    observer.observe(el)
  },
}
