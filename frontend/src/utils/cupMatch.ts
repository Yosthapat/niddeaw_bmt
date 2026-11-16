/**
 * Reading a tournament match out loud: which round, and who — a team once
 * known, else where it comes from (backend services/tournament_draw.py).
 */
import type { CupMatch, MatchSlot, PublicLevel } from '@/api/tournament'

type T = (key: string, values?: Record<string, unknown>) => string

/** "A1" → A1 · "U3" → upper #3 · "L3" → lower #3 · "W12" → winner of #12 ·
 *  "P2"/"Q2" → an opponent drawn by lot once the groups are done */
export function slotLabel(slot: string, t: T): string {
  if (/^[A-H][1-4]$/.test(slot)) return t('cup.slot.group', { group: slot[0], n: slot.slice(1) })
  if (slot.startsWith('P')) return t('cup.slot.drawUpper')
  if (slot.startsWith('Q')) return t('cup.slot.drawLower')
  if (slot.startsWith('U')) return t('cup.slot.upper', { n: slot.slice(1) })
  if (slot.startsWith('L')) return t('cup.slot.lower', { n: slot.slice(1) })
  if (slot.startsWith('W')) return t('cup.slot.winner', { n: slot.slice(1) })
  return slot
}

export function sideLabel(side: MatchSlot, t: T): string {
  return side.team_name ?? slotLabel(side.slot, t)
}

export function roundLabel(m: CupMatch, t: T): string {
  if (m.stage === 'group') return t('cup.round.group', { group: m.group_label ?? '', n: m.round })
  const name = m.round === 2 ? t('cup.round.final') : m.round === 4 ? t('cup.round.semi') : t('cup.round.ko', { n: m.round })
  return `${m.bracket === 'lower' ? t('cup.bracket.lower') : t('cup.bracket.upper')} · ${name}`
}

/** "09:40" in the club's time, or "" without an estimate. */
export function clock(iso: string | null): string {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Bangkok' })
}

/** Where a group place goes once the groups are done (backend
 *  tournament_play.seeds): straight to a bracket, or — when only the best
 *  of that place go up — one of two. */
export type Band = 'upper' | 'lower' | 'upperOrLower' | 'lowerOrOut' | 'out'

export function rankBands(level: Pick<PublicLevel, 'max_teams' | 'cut_24' | 'groups'>): Record<number, Band> {
  const sizes = level.groups.map((g) => g.teams.length)
  const n = sizes.reduce((a, b) => a + b, 0)
  const full = n === level.max_teams && sizes.every((s) => s === 4)
  if (full && n === 24 && !level.cut_24) return { 1: 'upper', 2: 'upper', 3: 'upperOrLower', 4: 'lower' }
  if (full && n === 24) return { 1: 'upper', 2: 'upperOrLower', 3: 'lowerOrOut', 4: 'out' }
  return { 1: 'upper', 2: 'upper', 3: 'lower', 4: 'lower' }
}
