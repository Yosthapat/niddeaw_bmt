import { request } from './client'

/** Quests and badges (backend app/routers/quests.py). */

export interface QuestLevel {
  threshold: number
  earned_at: string | null
}

export interface QuestState {
  key: string
  value: number
  levels: QuestLevel[]
  other_id: string | null
  other_name: string | null
}

export interface MonthState {
  month: string
  target: number
  games: number
  earned_at: string | null
}

export interface PlayerBadges {
  start_date: string
  quests: QuestState[]
  podium: { start_rank: number; rank: number; elo: number; earned: (string | null)[] }
  month: MonthState
  past_months: MonthState[]
  secrets: { key: string; earned_at: string | null }[]
}

export interface BadgeAward {
  badge: string
  level: number
  earned_at: string
}

export interface LineBadges extends PlayerBadges {
  unseen: BadgeAward[]
}

export interface BadgeFeedItem extends BadgeAward {
  player_id: string
  nickname: string
  avatar_url: string | null
}

export interface QuestSettings {
  start_date: string
  monthly_target: number
}

/** null while quests aren't switched on (migration 0038 not run). */
export function getPlayerBadges(playerId: string): Promise<PlayerBadges | null> {
  return request(`/api/quests/players/${playerId}`)
}

export function getTopBadges(): Promise<Record<string, BadgeAward[]>> {
  return request('/api/quests/top')
}

export function getRecentBadges(limit = 8): Promise<BadgeFeedItem[]> {
  return request(`/api/quests/recent?limit=${limit}`)
}

const auth = (token: string): RequestInit => ({ headers: { Authorization: `Bearer ${token}` } })

export function getMyBadges(token: string): Promise<LineBadges | null> {
  return request('/api/line/badges', auth(token))
}

export function markBadgesSeen(token: string, items: BadgeAward[]): Promise<void> {
  return request('/api/line/badges/seen', { ...auth(token), method: 'POST', body: JSON.stringify({ items }) })
}

export function getQuestSettings(): Promise<QuestSettings | null> {
  return request('/api/admin/quests/settings')
}

export function updateQuestSettings(payload: Partial<QuestSettings>): Promise<QuestSettings> {
  return request('/api/admin/quests/settings', { method: 'PUT', body: JSON.stringify(payload) })
}
