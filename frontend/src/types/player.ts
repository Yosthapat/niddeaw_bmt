export type EloTier = 'milk' | 'soju' | 'beer' | 'highball' | 'vodka'

export interface Player {
  id: string
  name: string
  nickname: string | null
  avatar_url: string | null
  elo_score: number
  elo_level: EloTier
  phone: string | null
  line_id: string | null
  is_active: boolean
  created_at: string
}

/** Mirrors backend app/models/player.py PlayerStats. */
export interface PlayerStats {
  player: Player
  games: number
  wins: number
  draws: number
  losses: number
  points: number
  avg_points: number
  score_percent: number
}

/** The opponent this player has faced most often ("เทกันจัง"). */
export interface NemesisInfo {
  player: Player
  encounters: number
  wins: number
  losses: number
  draws: number
}

/** Mirrors backend app/models/player.py PlayerProfile. */
export interface PlayerProfile {
  player: Player
  games: number
  wins: number
  draws: number
  losses: number
  points: number
  avg_points: number
  score_percent: number
  nemesis: NemesisInfo | null
  elo_rank: number
  total_ranked_players: number
  similar_players: Player[]
}
