import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getPlayers } from '@/api/public'
import { createPlayer as apiCreatePlayer } from '@/api/admin'
import type { Player } from '@/types'

/**
 * Cached player list shared across admin views (check-in, matchmaking,
 * billing all need to resolve player_id -> name/avatar/elo without
 * re-fetching on every view).
 */
export const usePlayersStore = defineStore('players', () => {
  const players = ref<Player[]>([])
  const loaded = ref(false)

  function byId(playerId: string): Player | undefined {
    return players.value.find((p) => p.id === playerId)
  }

  async function ensureLoaded(): Promise<void> {
    if (loaded.value) return
    await refresh()
  }

  async function refresh(): Promise<void> {
    const stats = await getPlayers()
    players.value = stats.map((s) => s.player)
    loaded.value = true
  }

  async function createPlayer(input: {
    nickname: string
    line_id?: string | null
  }): Promise<Player> {
    const player = await apiCreatePlayer(input)
    players.value.push(player)
    return player
  }

  return { players, loaded, byId, ensureLoaded, refresh, createPlayer }
})
