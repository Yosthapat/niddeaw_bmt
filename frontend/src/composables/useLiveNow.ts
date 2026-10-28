import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { getLiveStatus } from '@/api/public'
import type { LiveQueueResponse } from '@/types'

// One poll of /api/live for the whole site: the tab bar's red dot, the
// menu's LIVE tag and the home page's "on court now" box all read the same
// answer instead of each asking on their own. It runs only while something
// on screen uses it and the tab is visible — a phone left on the home page
// in a pocket shouldn't keep fetching.
const POLL_MS = 30_000
const live = ref<LiveQueueResponse | null>(null)
let users = 0
let timer: ReturnType<typeof setInterval> | null = null

async function refresh(retry = true): Promise<void> {
  if (document.visibilityState === 'hidden') return
  try {
    live.value = await getLiveStatus()
  } catch {
    // Keep the last answer; a missed poll isn't worth a message. Try once
    // more soon rather than at the next tick, so one dropped request on a
    // phone's flaky signal doesn't hide the live dot for half a minute.
    if (retry && timer) setTimeout(() => void refresh(false), 4000)
  }
}

function onVisible(): void {
  if (document.visibilityState === 'visible') void refresh()
}

export function useLiveNow() {
  onMounted(() => {
    users += 1
    if (users === 1) {
      void refresh()
      timer = setInterval(() => void refresh(), POLL_MS)
      document.addEventListener('visibilitychange', onVisible)
    }
  })
  onBeforeUnmount(() => {
    users -= 1
    if (users === 0 && timer) {
      clearInterval(timer)
      timer = null
      document.removeEventListener('visibilitychange', onVisible)
    }
  })
  return {
    live,
    /** a match is being played right now */
    playing: computed(() => (live.value?.in_progress.length ?? 0) > 0),
  }
}
