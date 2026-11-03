import { onActivated } from 'vue'

/**
 * Runs `fn` each time a page kept alive (App.vue's KeepAlive) comes back
 * into view, but not on its first showing, when it has just loaded anyway.
 *
 * A kept page comes back instantly with what it showed before; this is
 * where it quietly asks again, so a ranking that moved during the night
 * catches up without a skeleton flashing over figures that were fine.
 */
export function onRevisit(fn: () => void): void {
  let first = true
  onActivated(() => {
    if (first) {
      first = false
      return
    }
    fn()
  })
}
