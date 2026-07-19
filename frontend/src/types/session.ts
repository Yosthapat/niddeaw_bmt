export type SessionStatus = 'open' | 'closed'

export interface Session {
  id: string
  date: string
  location: string
  court_fee_per_person: number
  shuttlecock_price_per_game: number
  status: SessionStatus
  created_by: string
  created_at: string
}
