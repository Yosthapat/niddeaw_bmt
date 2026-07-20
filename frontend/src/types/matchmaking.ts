import type { MatchStatus } from './match'

/** Mirrors backend app/models/matchmaking.py. */
export interface PairingSuggestion {
  group_no: number
  team1_player_ids: string[]
  team2_player_ids: string[]
  elo_balance_score: number
  fairness_penalty: number
}

export interface MatchmakingSuggestionResponse {
  suggestions: PairingSuggestion[]
  waiting_player_ids: string[]
}

export interface QueueEntry {
  match_id: string
  team1_player_ids: string[]
  team2_player_ids: string[]
  status: MatchStatus
}

export interface WaitingEntry {
  player_id: string
  queue_position: number
  estimated_wait_minutes: number
}

export interface MatchmakingQueueResponse {
  in_progress: QueueEntry[]
  suggestions: PairingSuggestion[]
  waiting: WaitingEntry[]
  avg_match_duration_minutes: number
}

export interface LiveQueueResponse {
  session_id: string | null
  session_date: string | null
  location: string | null
  in_progress: QueueEntry[]
  suggestions: PairingSuggestion[]
  waiting: WaitingEntry[]
  avg_match_duration_minutes: number
}
