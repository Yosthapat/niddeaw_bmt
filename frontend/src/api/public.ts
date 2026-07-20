import { request } from './client'
import type { LiveQueueResponse, Match, MatchDetail, Player, PlayerProfile, PlayerStats } from '@/types'

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

export async function getMatches(
  options: { sessionId?: string; limit?: number; offset?: number } = {},
): Promise<Match[]> {
  const params = new URLSearchParams()
  if (options.sessionId) params.set('session_id', options.sessionId)
  if (options.limit !== undefined) params.set('limit', String(options.limit))
  if (options.offset !== undefined) params.set('offset', String(options.offset))
  const query = params.toString()
  return request(`/api/matches${query ? `?${query}` : ''}`)
}

export async function getMatchDetail(matchId: string): Promise<MatchDetail> {
  return request(`/api/matches/${matchId}/detail`)
}

export async function getLiveStatus(): Promise<LiveQueueResponse> {
  return request('/api/live')
}
