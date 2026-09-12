import { request } from './client'
import type { LiveQueueResponse, Match, MatchDetail, Player, PlayerProfile, PlayerStats } from '@/types'

// Mirrors backend/app/routers/public/{players,ranking,hall_of_fame,matches}.py.

export async function getPlayers(
  options: { limit?: number; offset?: number } = {},
): Promise<PlayerStats[]> {
  const params = new URLSearchParams()
  if (options.limit !== undefined) params.set('limit', String(options.limit))
  if (options.offset !== undefined) params.set('offset', String(options.offset))
  const query = params.toString()
  return request(`/api/players${query ? `?${query}` : ''}`)
}

export async function getPlayersByIds(ids: string[]): Promise<Player[]> {
  if (ids.length === 0) return []
  const params = new URLSearchParams()
  for (const id of ids) params.append('ids', id)
  const stats = await request<PlayerStats[]>(`/api/players?${params.toString()}`)
  return stats.map((s) => s.player)
}

export async function getPlayer(playerId: string): Promise<Player> {
  return request(`/api/players/${playerId}`)
}

export async function getPlayerProfile(playerId: string): Promise<PlayerProfile> {
  return request(`/api/players/${playerId}/profile`)
}

export async function getRanking(
  period: 'day' | 'year' | 'all' = 'all',
  date?: string,
): Promise<PlayerStats[]> {
  // `date` applies to period="day" only; omitting it there lets the backend
  // resolve the most recent day that has matches.
  const query = date ? `?period=${period}&date=${date}` : `?period=${period}`
  return request(`/api/ranking${query}`)
}

/** Session dates that have at least one completed match, newest first —
 * every one is guaranteed to produce a non-empty daily ranking. */
export async function getPlayDates(): Promise<string[]> {
  return request('/api/ranking/days')
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
