/**
 * Reading a tournament match out loud: which round, and who — a team once
 * known, else where it comes from (backend services/tournament_draw.py).
 */
import type { CupMatch, MatchSlot } from '@/api/tournament'

type T = (key: string, values?: Record<string, unknown>) => string

/** "A1" → A1 · "U3" → upper #3 · "L3" → lower #3 · "W12" → winner of #12 */
export function slotLabel(slot: string, t: T): string {
  if (/^[A-H][1-4]$/.test(slot)) return t('cup.slot.group', { group: slot[0], n: slot.slice(1) })
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
