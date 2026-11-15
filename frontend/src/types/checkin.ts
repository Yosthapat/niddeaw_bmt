export interface Checkin {
  id: string
  session_id: string
  player_id: string
  checkin_time: string
  checkout_time: string | null
  /** Who checked them in: the admin, or they did, by scanning the QR. */
  via?: 'admin' | 'line' | 'gps'
  /** Set while they rest: still in, left out of pairings. */
  paused_at?: string | null
}
