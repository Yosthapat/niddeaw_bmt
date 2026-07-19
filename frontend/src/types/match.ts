export type MatchType = 'single' | 'double'
export type MatchWinner = 'team1' | 'team2' | 'draw'
export type MatchStatus = 'in_progress' | 'completed'

/** One game's score as [team1_points, team2_points]. */
export type SetScore = [number, number]

export interface Match {
  id: string
  session_id: string
  type: MatchType
  team1_player_ids: string[]
  team2_player_ids: string[]
  sets: SetScore[] | null
  winner: MatchWinner | null
  status: MatchStatus
  created_at: string
}
