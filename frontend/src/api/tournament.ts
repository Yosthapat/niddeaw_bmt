import { request, requestBlob } from './client'
import type { PaymentInfoResponse } from '@/types'

/** NIDDEAW CUP — mirrors backend/app/routers/{public/tournament,line_tournament,admin/tournament}.py.
 *  Kept apart from the club's api/admin.ts on purpose: these calls are the
 *  tournament admins' only, and never touch the club's money. */

export type TournamentStatus = 'draft' | 'open' | 'closed' | 'running' | 'done'
export type TeamStatus = 'invited' | 'awaiting_payment' | 'slip_review' | 'confirmed' | 'waitlist' | 'cancelled' | 'withdrawn'
export type PayStatus = 'unpaid' | 'slip_sent' | 'paid' | 'rejected' | 'refunded'
export type PaidVia = 'transfer' | 'cash'
export type PromptPayKind = 'phone' | 'national_id' | 'ewallet'
export type MoneyCategory =
  | 'entry_fee' | 'extra_shuttles' | 'sponsor' | 'other_income'
  | 'court' | 'shuttle' | 'trophy' | 'prize' | 'staff' | 'photo' | 'refund' | 'coupon_refund' | 'other'

export interface Level {
  id: string
  name: string
  min_elo: number | null
  max_elo: number | null
  max_teams: 16 | 24 | 32
  cut_24: boolean
  rules: string
  sort: number
}

export interface Tournament {
  id: string
  name: string
  starts_on: string
  venue: string
  entry_fee: number
  shuttle_fee: number
  coupons_per_set: number
  extra_set_price: number
  coupon_refund_price: number
  promptpay_id: string | null
  promptpay_type: PromptPayKind | null
  account_name: string | null
  opens_at: string | null
  closes_at: string
  min_games: number
  courts: number | null
  status: TournamentStatus
  levels: Level[]
  fees_locked: boolean
  day_start: string
  group_minutes: number
  ko_minutes: number
  rest_minutes: number
  schedule_published_at: string | null
}

export interface PublicPlayer {
  nickname: string
  avatar_url: string | null
  elo_level: string | null
}

export interface PublicTeam {
  id: string | null
  name: string
  players: PublicPlayer[]
}

export interface PublicLevel extends Level {
  seats_taken: number
  waitlist: number
  teams: PublicTeam[]
  /** only once the schedule is published */
  groups: { label: string; teams: PublicTeam[] }[]
}

/** One side of a match: a team once known, else the place it comes from
 *  ("A1" group place, "U3"/"L3" a seed, "W12" the winner of match 12). */
export interface MatchSlot {
  slot: string
  team_id: string | null
  team_name: string | null
  players: PublicPlayer[]
}

export interface CupMatch {
  id: string
  match_no: number
  level_id: string
  level_name: string
  stage: 'group' | 'ko'
  bracket: 'upper' | 'lower' | null
  round: number
  group_label: string | null
  a: MatchSlot
  b: MatchSlot
  est_start: string | null
}

export interface DrawTeam {
  id: string
  name: string
  status: TeamStatus
  group_label: string | null
  group_pos: number | null
  players: PublicPlayer[]
}

export interface DrawLevel {
  level: Level
  confirmed: number
  not_ready: number
  groups: string[]
  teams: DrawTeam[]
}

export interface DrawState {
  tournament_id: string
  levels: DrawLevel[]
  matches: CupMatch[]
  est_end: string | null
  published_at: string | null
}

export interface PublicTournament {
  id: string
  name: string
  starts_on: string
  venue: string
  entry_fee: number
  shuttle_fee: number
  coupons_per_set: number
  opens_at: string | null
  closes_at: string
  min_games: number
  status: TournamentStatus
  taking_entries: boolean
  levels: PublicLevel[]
  schedule_published: boolean
  matches: CupMatch[]
}

export interface Details {
  first_name: string
  last_name: string
  phone: string
}

export interface Entrant {
  id: string
  player_id: string
  role: 'captain' | 'partner'
  nickname: string
  avatar_url: string | null
  elo_level: string | null
  elo: number | null
  share: number
  pay_status: PayStatus
  paid_via: PaidVia | null
  slip_url: string | null
  slip_sent_at: string | null
  paid_at: string | null
  rejected_at: string | null
  refunded_at: string | null
  first_name: string | null
  last_name: string | null
  phone: string | null
}

export interface Team {
  id: string
  tournament_id: string
  level_id: string
  level_name: string
  name: string
  status: TeamStatus
  expires_at: string | null
  invited_at: string | null
  accepted_at: string | null
  seat_held_at: string | null
  waitlist_at: string | null
  confirmed_at: string | null
  ended_at: string | null
  by_admin: boolean
  entrants: Entrant[]
}

export interface SlipCheckInfo {
  target_id: string
  status: 'ok' | 'duplicate' | 'no_qr' | 'not_slip' | 'unchecked'
  used_before_who: string | null
  used_before_kind: string | null
  used_before_amount: number | null
}

export interface AdminTeam extends Team {
  slip_checks: SlipCheckInfo[]
  refund_owed: number
}

export interface Me {
  player_id: string
  nickname: string
  avatar_url: string | null
  elo: number
  elo_level: string
  games: number
  games_needed: number
  level_id: string | null
}

export interface Candidate {
  player_id: string
  nickname: string
  avatar_url: string | null
  elo: number
  elo_level: string
  games: number
  eligible: boolean
  taken: boolean
}

export interface LineTournament {
  tournament: PublicTournament | null
  me: Me | null
  team: Team | null
  my_role: 'captain' | 'partner' | null
  last_details: Details | null
}

export interface PlayerHit {
  player_id: string
  nickname: string
  avatar_url: string | null
  elo: number
  elo_level: string
  games: number
  line_linked: boolean
  taken: boolean
}

export interface Money {
  id: string
  tournament_id: string
  direction: 'income' | 'expense'
  category: MoneyCategory
  category_other: string | null
  amount: number
  entry_date: string
  paid_by: string | null
  entrant_id: string | null
  team_id: string | null
  quantity: number | null
  unit_price: number | null
  paid_via: PaidVia | null
  receipt_url: string | null
  note: string | null
  created_at: string | null
  automatic: boolean
}

export interface MoneySummary {
  income: number
  expense: number
  balance: number
  by_category: Record<string, number>
  by_level: Record<string, number>
  pending_slips: number
  pending_amount: number
  refunds_owed: number
  refunds_owed_amount: number
}

export interface TournamentActivity {
  id: string
  admin_id: string
  admin_username: string
  action: string
  method: string
  path: string
  detail: Record<string, unknown> | null
  created_at: string
}

const json = (method: string, body: unknown): RequestInit => ({ method, body: JSON.stringify(body) })
const line = (token: string, init: RequestInit = {}): RequestInit => ({
  ...init,
  headers: { ...(init.headers ?? {}), Authorization: `Bearer ${token}` },
})
function file(f: File, init: RequestInit = {}): RequestInit {
  const body = new FormData()
  body.append('file', f)
  return { ...init, method: 'POST', body }
}

// --- public ---------------------------------------------------------------

export function getPublicTournament(): Promise<PublicTournament | null> {
  return request('/api/tournament')
}

// --- LINE -----------------------------------------------------------------

const L = '/api/line/tournament'

export const lineTournament = {
  get: (token: string): Promise<LineTournament> => request(L, line(token)),
  candidates: (token: string): Promise<Candidate[]> => request(`${L}/candidates`, line(token)),
  signUp: (token: string, body: Details & { partner_id: string; level_id: string; team_name: string }): Promise<LineTournament> =>
    request(`${L}/team`, line(token, json('POST', body))),
  accept: (token: string, body: Details): Promise<LineTournament> => request(`${L}/accept`, line(token, json('POST', body))),
  decline: (token: string): Promise<LineTournament> => request(`${L}/decline`, line(token, { method: 'POST' })),
  rename: (token: string, teamName: string): Promise<LineTournament> =>
    request(`${L}/team`, line(token, json('PATCH', { team_name: teamName }))),
  withdraw: (token: string): Promise<LineTournament> => request(`${L}/withdraw`, line(token, { method: 'POST' })),
  payInfo: (token: string): Promise<PaymentInfoResponse> => request(`${L}/pay`, line(token)),
  sendSlip: (token: string, f: File): Promise<LineTournament> => request(`${L}/slip`, line(token, file(f))),
}

// --- tournament admins ----------------------------------------------------

const A = '/api/admin/tournament'

export const tournamentAdmin = {
  list: (): Promise<Tournament[]> => request(`${A}/tournaments`),
  create: (body: { name: string; starts_on: string; venue: string; closes_at: string; opens_at: string | null }): Promise<Tournament> =>
    request(`${A}/tournaments`, json('POST', body)),
  get: (id: string): Promise<Tournament> => request(`${A}/tournaments/${id}`),
  update: (id: string, body: Partial<Omit<Tournament, 'id' | 'levels' | 'fees_locked'>>): Promise<Tournament> =>
    request(`${A}/tournaments/${id}`, json('PATCH', body)),
  addLevel: (id: string, body: Omit<Level, 'id' | 'sort'>): Promise<Tournament> => request(`${A}/tournaments/${id}/levels`, json('POST', body)),
  updateLevel: (id: string, levelId: string, body: Partial<Omit<Level, 'id' | 'sort'>>): Promise<Tournament> =>
    request(`${A}/tournaments/${id}/levels/${levelId}`, json('PATCH', body)),
  deleteLevel: (id: string, levelId: string): Promise<Tournament> =>
    request(`${A}/tournaments/${id}/levels/${levelId}`, { method: 'DELETE' }),

  teams: (id: string): Promise<AdminTeam[]> => request(`${A}/tournaments/${id}/teams`),
  exportCsv: (id: string): Promise<Blob> => requestBlob(`${A}/tournaments/${id}/teams.csv`),
  players: (id: string): Promise<PlayerHit[]> => request(`${A}/tournaments/${id}/players`),
  signUp: (
    id: string,
    body: {
      level_id: string
      team_name: string
      captain: Details & { player_id: string }
      partner: Details & { player_id: string }
      paid_via: PaidVia | 'unpaid'
    },
  ): Promise<AdminTeam[]> => request(`${A}/tournaments/${id}/teams`, json('POST', body)),
  updateTeam: (teamId: string, body: { name?: string; level_id?: string }): Promise<AdminTeam[]> =>
    request(`${A}/teams/${teamId}`, json('PATCH', body)),
  withdraw: (teamId: string, noRefund: boolean): Promise<AdminTeam[]> =>
    request(`${A}/teams/${teamId}/withdraw`, json('POST', { no_refund: noRefund })),
  updateEntrant: (entrantId: string, body: Partial<Details>): Promise<AdminTeam[]> =>
    request(`${A}/entrants/${entrantId}`, json('PATCH', body)),
  approve: (entrantId: string): Promise<AdminTeam[]> => request(`${A}/entrants/${entrantId}/approve`, { method: 'POST' }),
  reject: (entrantId: string): Promise<AdminTeam[]> => request(`${A}/entrants/${entrantId}/reject`, { method: 'POST' }),
  cash: (entrantId: string): Promise<AdminTeam[]> => request(`${A}/entrants/${entrantId}/cash`, { method: 'POST' }),
  refund: (entrantId: string, slip: File | null): Promise<AdminTeam[]> =>
    request(`${A}/entrants/${entrantId}/refund`, slip ? file(slip) : { method: 'POST' }),

  money: (id: string): Promise<Money[]> => request(`${A}/tournaments/${id}/money`),
  summary: (id: string): Promise<MoneySummary> => request(`${A}/tournaments/${id}/summary`),
  addMoney: (
    id: string,
    body: {
      direction: 'income' | 'expense'
      category: MoneyCategory
      category_other: string | null
      amount: number
      entry_date: string
      paid_by: string | null
      paid_via: PaidVia | null
      note: string | null
    },
  ): Promise<Money> => request(`${A}/tournaments/${id}/money`, json('POST', body)),
  deleteMoney: (moneyId: string): Promise<void> => request(`${A}/money/${moneyId}`, { method: 'DELETE' }),
  receipt: (moneyId: string, f: File): Promise<Money> => request(`${A}/money/${moneyId}/receipt`, file(f)),

  draw: (id: string): Promise<DrawState> => request(`${A}/tournaments/${id}/draw`),
  drawLevel: (id: string, levelId: string): Promise<DrawState> =>
    request(`${A}/tournaments/${id}/levels/${levelId}/draw`, { method: 'POST' }),
  clearLevel: (id: string, levelId: string): Promise<DrawState> =>
    request(`${A}/tournaments/${id}/levels/${levelId}/draw`, { method: 'DELETE' }),
  place: (teamId: string, groupLabel: string, groupPos: number): Promise<DrawState> =>
    request(`${A}/teams/${teamId}/group`, json('PUT', { group_label: groupLabel, group_pos: groupPos })),
  makeSchedule: (id: string): Promise<DrawState> => request(`${A}/tournaments/${id}/schedule`, { method: 'POST' }),
  clearSchedule: (id: string): Promise<DrawState> => request(`${A}/tournaments/${id}/schedule`, { method: 'DELETE' }),
  publish: (id: string, on: boolean): Promise<DrawState> => request(`${A}/tournaments/${id}/publish`, json('POST', { on })),

  admins: (): Promise<{ id: string; username: string }[]> => request(`${A}/admins`),
  activity: (day?: string): Promise<TournamentActivity[]> => request(`${A}/activity${day ? `?day=${day}` : ''}`),
}

export interface AdminMe {
  id: string
  username: string
  club_access: boolean
  tournament_access: boolean
}

export function getAdminMe(): Promise<AdminMe> {
  return request('/api/admin/auth/me')
}
