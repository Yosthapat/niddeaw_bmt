import type { Player } from './player'

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
  updated_at: string
}

/** A player's overall record, shown side-by-side with their match opponents. */
export interface PlayerMatchStat {
  player: Player
  games: number
  wins: number
  draws: number
  losses: number
  score_percent: number
  elo_rank: number
}

/** Mirrors backend app/models/match.py MatchDetail. */
export interface MatchDetail {
  match: Match
  team1: PlayerMatchStat[]
  team2: PlayerMatchStat[]
  duration_minutes: number | null
}
