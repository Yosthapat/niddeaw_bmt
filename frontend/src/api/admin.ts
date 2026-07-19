import { request } from './client'
import type {
  Billing,
  Checkin,
  ClubSettings,
  LoginCredentials,
  LoginResponse,
  Match,
  MatchmakingQueueResponse,
  MatchmakingSuggestionResponse,
  Player,
  Session,
  SetScore,
} from '@/types'

// Mirrors backend/app/routers/admin/{auth,sessions,checkins,matchmaking,billing,players_admin,settings}.py.

export async function login(credentials: LoginCredentials): Promise<LoginResponse> {
  return request('/api/admin/auth/login', {
    method: 'POST',
    body: JSON.stringify(credentials),
  })
}

// Sessions
export async function getSessions(): Promise<Session[]> {
  return request('/api/admin/sessions')
}

export async function createSession(session: {
  date: string
  location: string
  court_fee_per_person: number
  shuttlecock_price_per_game: number
}): Promise<Session> {
  return request('/api/admin/sessions', {
    method: 'POST',
    body: JSON.stringify(session),
  })
}

export async function updateSession(
  sessionId: string,
  updates: Partial<
    Pick<Session, 'location' | 'court_fee_per_person' | 'shuttlecock_price_per_game' | 'status'>
  >,
): Promise<Session> {
  return request(`/api/admin/sessions/${sessionId}`, {
    method: 'PATCH',
    body: JSON.stringify(updates),
  })
}

// Check-ins
export async function getCheckins(sessionId: string, activeOnly = false): Promise<Checkin[]> {
  return request(`/api/admin/checkins?session_id=${sessionId}&active_only=${activeOnly}`)
}

export async function checkinPlayer(sessionId: string, playerId: string): Promise<Checkin> {
  return request('/api/admin/checkins', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, player_id: playerId }),
  })
}

export async function checkoutPlayer(checkinId: string): Promise<Checkin> {
  return request(`/api/admin/checkins/${checkinId}/checkout`, { method: 'POST' })
}

// Matchmaking
export async function suggestPairings(sessionId: string): Promise<MatchmakingSuggestionResponse> {
  return request(`/api/admin/matchmaking/suggest?session_id=${sessionId}`)
}

export async function getMatchmakingQueue(sessionId: string): Promise<MatchmakingQueueResponse> {
  return request(`/api/admin/matchmaking/queue?session_id=${sessionId}`)
}

export async function confirmMatch(match: {
  session_id: string
  type: 'single' | 'double'
  team1_player_ids: string[]
  team2_player_ids: string[]
}): Promise<Match> {
  return request('/api/admin/matchmaking/confirm', {
    method: 'POST',
    body: JSON.stringify(match),
  })
}

export async function recordMatchResult(matchId: string, sets: SetScore[]): Promise<Match> {
  return request(`/api/admin/matchmaking/matches/${matchId}/result`, {
    method: 'POST',
    body: JSON.stringify({ sets }),
  })
}

// Billing
export async function getBillings(sessionId: string): Promise<Billing[]> {
  return request(`/api/admin/billing?session_id=${sessionId}`)
}

export async function closeSessionAndBill(sessionId: string): Promise<Billing[]> {
  return request(`/api/admin/billing/close-session/${sessionId}`, { method: 'POST' })
}

export async function adjustBilling(
  billingId: string,
  amountAdjusted: number | null,
): Promise<Billing> {
  return request(`/api/admin/billing/${billingId}/adjust`, {
    method: 'PATCH',
    body: JSON.stringify({ amount_adjusted: amountAdjusted }),
  })
}

export async function setBillingPaidStatus(
  billingId: string,
  paidStatus: 'unpaid' | 'paid',
): Promise<Billing> {
  return request(`/api/admin/billing/${billingId}/paid-status`, {
    method: 'PATCH',
    body: JSON.stringify({ paid_status: paidStatus }),
  })
}

export async function getBillingQrCode(billingId: string): Promise<{ data_uri: string }> {
  return request(`/api/admin/billing/${billingId}/qr`)
}

// Players (admin CRUD)
export async function createPlayer(player: {
  name: string
  nickname?: string | null
  phone?: string | null
  line_id?: string | null
}): Promise<Player> {
  return request('/api/admin/players', {
    method: 'POST',
    body: JSON.stringify(player),
  })
}

export async function updatePlayer(playerId: string, player: Partial<Player>): Promise<Player> {
  return request(`/api/admin/players/${playerId}`, {
    method: 'PATCH',
    body: JSON.stringify(player),
  })
}

export async function uploadAvatar(playerId: string, file: File): Promise<Player> {
  const formData = new FormData()
  formData.append('file', file)
  return request(`/api/admin/players/${playerId}/avatar`, {
    method: 'POST',
    body: formData,
  })
}

// Settings
export async function getClubSettings(): Promise<ClubSettings> {
  return request('/api/admin/settings')
}

export async function updateClubSettings(
  settings: Partial<ClubSettings>,
): Promise<ClubSettings> {
  return request('/api/admin/settings', {
    method: 'PUT',
    body: JSON.stringify(settings),
  })
}
