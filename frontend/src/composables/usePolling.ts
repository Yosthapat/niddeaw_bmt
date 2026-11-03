import { onActivated, onDeactivated, onMounted, onUnmounted } from 'vue'

/**
 * Generic polling composable used by live admin screens (check-in list,
 * matchmaking queue) instead of WebSockets/Supabase Realtime — see plan
 * section on real-time updates.
 *
 * Starts polling on mount and clears the interval on unmount. Also exposes
 * `start`/`stop` for manual control (e.g. pause while a modal is open).
 */
export function usePolling(fetchFn: () => Promise<void>, intervalMs = 7000) {
  let intervalId: ReturnType<typeof setInterval> | null = null

  function start(): void {
    if (intervalId !== null) return
    void fetchFn()
    intervalId = setInterval(() => {
      void fetchFn()
    }, intervalMs)
  }

  function stop(): void {
    if (intervalId === null) return
    clearInterval(intervalId)
    intervalId = null
  }

  onMounted(start)
  onUnmounted(stop)
  // On a page kept alive (App.vue): stop while it is away, and catch up
  // the moment it is back. start() is a no-op while already running, which
  // covers onActivated also firing on the first mount.
  onDeactivated(stop)
  onActivated(start)

  return { start, stop }
}
