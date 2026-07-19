import { request } from './client'
import type { Match, Player, PlayerProfile, PlayerStats } from '@/types'

// Mirrors backend/app/routers/public/{players,ranking,hall_of_fame,matches}.py.

export async function getPlayers(): Promise<PlayerStats[]> {
  return request('/api/players')
}

export async function getPlayer(playerId: string): Promise<Player> {
  return request(`/api/players/${playerId}`)
}

export async function getPlayerProfile(playerId: string): Promise<PlayerProfile> {
  return request(`/api/players/${playerId}/profile`)
}

export async function getRanking(period: 'year' | 'all' = 'all'): Promise<PlayerStats[]> {
  return request(`/api/ranking?period=${period}`)
}

export async function getHallOfFame(limit = 10): Promise<PlayerStats[]> {
  return request(`/api/hall-of-fame?limit=${limit}`)
}

export async function getMatches(sessionId?: string): Promise<Match[]> {
  const query = sessionId ? `?session_id=${sessionId}` : ''
  return request(`/api/matches${query}`)
}
