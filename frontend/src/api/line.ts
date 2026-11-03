import { request } from './client'
import type { PaymentInfoResponse, Player } from '@/types'

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

export interface JoinApplication {
  id: string
  nickname: string
  dominant_hand: 'left' | 'right' | null
  instagram: string | null
  tiktok: string | null
  quote: string | null
  photo_url: string | null
  created_at: string
}

export interface JoinForm {
  nickname: string
  dominant_hand: 'left' | 'right' | null
  instagram: string | null
  tiktok: string | null
  quote: string | null
  use_line_photo: boolean
}

export interface LineStatus {
  line_name: string
  line_picture: string | null
  player: Player | null
  pending: LinkRequest | null
  application: JoinApplication | null
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

export function sendJoin(token: string, form: JoinForm): Promise<LineStatus> {
  return request('/api/line/join', { ...auth(token), method: 'POST', body: JSON.stringify(form) })
}

export function uploadJoinPhoto(token: string, file: File): Promise<LineStatus> {
  const body = new FormData()
  body.append('file', file)
  return request('/api/line/join/photo', { ...auth(token), method: 'POST', body })
}

export function cancelJoin(token: string): Promise<LineStatus> {
  return request('/api/line/join', { ...auth(token), method: 'DELETE' })
}

export interface LineCheckinState {
  state: 'ready' | 'in' | 'expired' | 'unlinked'
  night: { id: string; date: string; location: string } | null
  player: Player | null
  checkin_time: string | null
}

export function getCheckin(token: string, code: string): Promise<LineCheckinState> {
  return request(`/api/line/checkin?c=${encodeURIComponent(code)}`, auth(token))
}

export function checkInTonight(token: string, code: string): Promise<LineCheckinState> {
  return request('/api/line/checkin', { ...auth(token), method: 'POST', body: JSON.stringify({ code }) })
}

export interface LineNight {
  id: string
  date: string
  location: string
}

export interface LineBill {
  id: string
  night: LineNight
  game_count: number
  amount: number
  paid_status: 'unpaid' | 'paid'
  slip_url: string | null
  slip_sent_at: string | null
  slip_rejected_at: string | null
}

export interface LineTonight {
  state: 'none' | 'in' | 'out'
  night: LineNight | null
  player: Player | null
  games: number
  court_fee: number
  shuttle_price: number
  amount: number
  busy: boolean
  bill: LineBill | null
}

export interface LineBills {
  player: Player
  due: number
  bills: LineBill[]
}

export function getTonight(token: string): Promise<LineTonight> {
  return request('/api/line/tonight', auth(token))
}

export function checkOut(token: string, sessionId: string): Promise<LineTonight> {
  return request('/api/line/checkout', { ...auth(token), method: 'POST', body: JSON.stringify({ session_id: sessionId }) })
}

export function getBills(token: string): Promise<LineBills> {
  return request('/api/line/bills', auth(token))
}

export function getPayInfo(token: string, billId: string): Promise<PaymentInfoResponse> {
  return request(`/api/line/bills/${billId}/pay`, auth(token))
}

export function sendSlip(token: string, billId: string, file: File): Promise<LineBill> {
  const body = new FormData()
  body.append('file', file)
  return request(`/api/line/bills/${billId}/slip`, { ...auth(token), method: 'POST', body })
}
