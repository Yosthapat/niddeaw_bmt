export type EloTier = 'milk' | 'beer' | 'highball' | 'wine' | 'soju' | 'whisky' | 'vodka'
export type DominantHand = 'left' | 'right'

export interface Player {
  id: string
  nickname: string
  avatar_url: string | null
  elo_score: number
  elo_level: EloTier
  line_id: string | null
  dominant_hand: DominantHand | null
  tiktok: string | null
  instagram: string | null
  is_active: boolean
  created_at: string
  member_seq: number
  member_code: string
  games: number
  wins: number
  draws: number
  losses: number
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
