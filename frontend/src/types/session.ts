export type SessionStatus = 'open' | 'closed'

export interface Session {
  id: string
  date: string
  location: string
  rate_per_hour: number
  status: SessionStatus
  created_by: string
  created_at: string
}
