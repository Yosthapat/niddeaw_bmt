import { request } from './client'
import type { Player } from '@/types'

/** Calls made from the /line page, with the member's LINE token rather than
 *  the admin's (api/client.ts keeps an Authorization it is given). */

export interface LineConfig {
  enabled: boolean
  liff_id: string | null
}

export interface LinkRequest {
  id: string
  player: Player
  created_at: string
}

export interface LineStatus {
  line_name: string
  line_picture: string | null
  player: Player | null
  pending: LinkRequest | null
  token?: string | null
}

export interface LinkOption {
  id: string
  nickname: string
  member_code: string
  elo_level: Player['elo_level']
  avatar_url: string | null
  games: number
  taken: boolean
}

const auth = (token: string): RequestInit => ({ headers: { Authorization: `Bearer ${token}` } })

export function getLineConfig(): Promise<LineConfig> {
  return request('/api/line/config')
}

export function startLineSession(idToken: string): Promise<LineStatus> {
  return request('/api/line/session', { method: 'POST', body: JSON.stringify({ id_token: idToken }) })
}

export function getLinkOptions(token: string): Promise<LinkOption[]> {
  return request('/api/line/link/options', auth(token))
}

export function requestLink(token: string, playerId: string): Promise<LineStatus> {
  return request('/api/line/link', { ...auth(token), method: 'POST', body: JSON.stringify({ player_id: playerId }) })
}

export function cancelLink(token: string): Promise<LineStatus> {
  return request('/api/line/link', { ...auth(token), method: 'DELETE' })
}
