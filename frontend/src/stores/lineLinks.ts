import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import * as adminApi from '@/api/admin'
import { getLineConfig } from '@/api/line'

/**
 * Who has linked their LINE, for the admin screens: a green badge on their
 * face (members, check-in, billing) and the count on the members page and
 * dashboard. A linked member checks in, checks out and pays from LINE, so
 * on a night the admin can see at a glance who will see to themselves and
 * who still needs them.
 *
 * Admin-only and kept apart from the players list: the public players API
 * never says who is linked.
 *
 * Until LINE is switched on (`enabled`) the pages show none of it. A call
 * failing reads as nobody linked and nothing pending, not as an error.
 */
export const useLineLinksStore = defineStore('lineLinks', () => {
  const names = ref<Map<string, string>>(new Map())
  const pending = ref(0)
  const enabled = ref(false)
  const loaded = ref(false)
  let inFlight: Promise<void> | null = null

  async function load(): Promise<void> {
    inFlight ??= (async () => {
      const [config, links, requests] = await Promise.allSettled([getLineConfig(), adminApi.getLineLinks(), adminApi.getLineRequests()])
      enabled.value = config.status === 'fulfilled' && config.value.enabled
      names.value = links.status === 'fulfilled' ? new Map(links.value.map((l) => [l.player_id, l.line_name ?? 'LINE'])) : new Map()
      pending.value = requests.status === 'fulfilled' ? requests.value.length : 0
      loaded.value = true
    })().finally(() => (inFlight = null))
    return inFlight
  }

  function ensureLoaded(): void {
    if (!loaded.value) void load()
  }

  const isLinked = (playerId: string): boolean => names.value.has(playerId)
  const lineName = (playerId: string): string | undefined => names.value.get(playerId)
  const count = computed(() => names.value.size)

  return { names, pending, enabled, loaded, count, load, ensureLoaded, isLinked, lineName }
})
