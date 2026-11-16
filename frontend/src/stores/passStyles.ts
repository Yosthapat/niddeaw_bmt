import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getPassStyles, type PassCard, type PassFrame, type PassLook } from '@/api/line'

/**
 * Who wears a Niddeaw Pass look right now — the frame round their picture
 * and their profile card's face — for every page that shows members. One
 * call for the whole club, read again at most every STALE_MS while pages
 * change, as the credit cards are (creditCards.ts). A failed call reads as
 * nobody wearing one.
 */
const STALE_MS = 60_000

export const usePassStylesStore = defineStore('passStyles', () => {
  const looks = ref<Record<string, PassLook>>({})
  let loadedAt = 0
  let inFlight: Promise<void> | null = null

  function load(force = false): Promise<void> {
    if (!force && Date.now() - loadedAt < STALE_MS) return Promise.resolve()
    inFlight ??= getPassStyles()
      .then((m) => {
        looks.value = m
        loadedAt = Date.now()
      })
      .catch(() => {
        loadedAt = Date.now()
      })
      .finally(() => (inFlight = null))
    return inFlight
  }

  const frameOf = (playerId: string | null | undefined): PassFrame | null =>
    playerId ? (looks.value[playerId]?.frame ?? null) : null
  const cardOf = (playerId: string | null | undefined): PassCard | null =>
    playerId ? (looks.value[playerId]?.card ?? null) : null

  return { looks, load, frameOf, cardOf }
})
