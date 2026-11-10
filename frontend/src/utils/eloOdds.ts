/**
 * The odds two teams had, from their average ELO, the way the backend's
 * elo_service.expected_score works them out: 1 / (1 + 10^((b − a) / 400)).
 */

export function winChance(team1: number, team2: number): number {
  return 1 / (1 + 10 ** ((team2 - team1) / 400))
}

/** Below this chance a team was the underdog; winning from there is an upset. */
export const UPSET_BELOW = 0.4

export function isUpset(team1: number | null | undefined, team2: number | null | undefined, winner: string | null | undefined): boolean {
  if (team1 == null || team2 == null || (winner !== 'team1' && winner !== 'team2')) return false
  const p1 = winChance(team1, team2)
  return winner === 'team1' ? p1 < UPSET_BELOW : 1 - p1 < UPSET_BELOW
}

/** A team's average ELO from the players' ratings now; null if any is unknown. */
export function teamElo(ids: string[], eloOf: (id: string) => number | undefined): number | null {
  if (!ids.length) return null
  let sum = 0
  for (const id of ids) {
    const e = eloOf(id)
    if (typeof e !== 'number') return null
    sum += e
  }
  return sum / ids.length
}
