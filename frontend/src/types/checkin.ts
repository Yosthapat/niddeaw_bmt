export interface Checkin {
  id: string
  session_id: string
  player_id: string
  checkin_time: string
  checkout_time: string | null
}
