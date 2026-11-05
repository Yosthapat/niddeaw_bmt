import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getCreditCards, type CardTier } from '@/api/line'

/**
 * Who holds a pink or black credit card right now, for the small card by
 * their name on every page that lists members. One call for the whole
 * club, read again at most every STALE_MS while pages change. A failed
 * call reads as nobody holding one, not as an error.
 */
const STALE_MS = 60_000

export const useCreditCardsStore = defineStore('creditCards', () => {
  const tiers = ref<Record<string, CardTier>>({})
  let loadedAt = 0
  let inFlight: Promise<void> | null = null

  function load(force = false): Promise<void> {
    if (!force && Date.now() - loadedAt < STALE_MS) return Promise.resolve()
    inFlight ??= getCreditCards()
      .then((m) => {
        tiers.value = m
        loadedAt = Date.now()
      })
      .catch(() => {
        loadedAt = Date.now()
      })
      .finally(() => (inFlight = null))
    return inFlight
  }

  const tierOf = (playerId: string | null | undefined): CardTier | null => (playerId ? (tiers.value[playerId] ?? null) : null)

  return { tiers, load, tierOf }
})
