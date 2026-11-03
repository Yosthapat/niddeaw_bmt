import { ref } from 'vue'

/**
 * Which page is on screen, as opposed to which page the URL says.
 *
 * Public pages change with an out-in fade (App.vue): the page being left
 * fades out first, and only then does the new one go in. For those 200ms
 * the route already names the new page while the old one is still showing.
 * Anything that follows the route during that time changes underneath the
 * old page and makes it jump. The phone's top bar vanished the moment ☰
 * was tapped, pulling the home page up by its height before the menu
 * appeared; the scroll went back to the top the same way.
 *
 * App.vue reports each page as it goes in. The header reads `shownPath`,
 * and the router's scrollBehavior waits for `nextPage()`.
 */
export const shownPath = ref<string | null>(null)

let waiting: (() => void)[] = []

/** The new page's element is about to go in: what the header shows changes now. */
export function pageEntering(path: string): void {
  shownPath.value = path
}

/** The new page is in the document: it has a height, so a scroll lands. */
export function pageEntered(): void {
  const ready = waiting
  waiting = []
  for (const resolve of ready) resolve()
}

/** Resolves when the next page has gone in, or after `timeoutMs` at most,
 *  so a navigation that brings no transition never leaves a scroll hanging. */
export function nextPage(timeoutMs = 800): Promise<void> {
  return new Promise((resolve) => {
    const done = (): void => {
      clearTimeout(timer)
      resolve()
    }
    const timer = setTimeout(() => {
      waiting = waiting.filter((w) => w !== done)
      resolve()
    }, timeoutMs)
    waiting.push(done)
  })
}
