/**
 * Quests as the screens show them: one slot per quest on the shelf, its
 * medal (art in public/badges, see tools/badges/), the tiers on its back
 * and the progress towards the next one. Built from the API's numbers
 * (api/quests.ts); the wording lives in i18n under `quests`.
 */
import type { BadgeAward, PlayerBadges } from '@/api/quests'
import { formatDate, formatMonth } from '@/utils/format'
import type { Locale } from '@/i18n'

export type Metal = 'b' | 's' | 'g' | 'p'
type T = (key: string, values?: Record<string, unknown>) => string

/** Thresholds per level, as in backend quest_service.THRESHOLDS: the art is
 *  named after them (fire_3, fire_5, fire_10). */
export const THRESHOLDS: Record<string, number[]> = {
  fire: [3, 5, 10],
  regular: [5, 20, 50],
  bloodline: [4, 8, 12],
  aged: [10, 50, 100, 300],
  giant: [1, 5, 10],
  unbeaten: [1, 3, 5],
  marathon: [6, 7, 8],
  mixer: [5, 10, 20],
  buddy: [5, 10, 20],
  revenge: [1, 3],
}
const ORDER = ['fire', 'regular', 'bloodline', 'aged', 'giant', 'unbeaten', 'marathon', 'mixer', 'buddy', 'revenge']
const METALS: Record<string, Metal[]> = { aged: ['b', 's', 'g', 'p'], revenge: ['s', 'g'] }
export const PODIUM = [
  { tier: 'milk', art: 800, from: 0 },
  { tier: 'beer', art: 1000, from: 900 },
  { tier: 'highball', art: 1200, from: 1100 },
  { tier: 'wine', art: 1400, from: 1300 },
  { tier: 'soju', art: 1600, from: 1500 },
  { tier: 'whisky', art: 1800, from: 1700 },
  { tier: 'vodka', art: 2000, from: 1900 },
  { tier: 'absinthe', art: 2200, from: 2100 },
]
const PODIUM_METAL: Metal[] = ['b', 'b', 'b', 's', 's', 's', 'g', 'g']
const SECRETS: Record<string, { art: string; metal: Metal }> = {
  secret_opener: { art: 'secret_bronze', metal: 'b' },
  secret_lights: { art: 'secret_silver', metal: 's' },
  secret_history: { art: 'secret_gold', metal: 'g' },
}
export const METAL_RANK: Record<Metal, number> = { b: 1, s: 2, g: 3, p: 4 }

export interface BadgeItem {
  id: string
  img: string
  name: string
  locked: boolean
  secret: boolean
  metal: Metal
  tierLabel: string
  pips: (Metal | null)[]
  earnedAt: string | null
  how: string
  tiers: { label: string; done: boolean }[]
  progress: { value: number; target: number; label: string } | null
  dateLabel: string
}

const img = (name: string): string => `/badges/${name}.webp`
const cap = (s: string): string => s.charAt(0).toUpperCase() + s.slice(1)
const metalsOf = (key: string): Metal[] => METALS[key] ?? ['b', 's', 'g']
const latest = (dates: (string | null)[]): string | null =>
  dates.filter((d): d is string => !!d).sort().at(-1) ?? null

export function metalName(t: T, m: Metal): string {
  return t(`quests.metal.${m}`)
}

/** The medal art for an award (badge + level), e.g. on a member's card. */
export function awardImage(a: BadgeAward): string {
  if (a.badge === 'podium') {
    const p = PODIUM[a.level - 1] ?? PODIUM[0]!
    return img(`podium_${p.tier}_${p.art}`)
  }
  if (a.badge.startsWith('monthly:')) return img('monthly_gold')
  if (SECRETS[a.badge]) return img(SECRETS[a.badge]!.art)
  const th = THRESHOLDS[a.badge]
  return th ? img(`${a.badge}_${th[Math.min(a.level, th.length) - 1]}`) : img('secret_bronze')
}

export function awardMetal(a: BadgeAward): Metal {
  if (a.badge === 'podium') return PODIUM_METAL[a.level - 1] ?? 'b'
  if (a.badge.startsWith('monthly:')) return 'g'
  if (SECRETS[a.badge]) return SECRETS[a.badge]!.metal
  return metalsOf(a.badge)[a.level - 1] ?? 'b'
}

export function awardName(t: T, a: BadgeAward, locale: Locale): string {
  if (a.badge === 'podium') return t('quests.name.podiumTier', { tier: cap(PODIUM[a.level - 1]?.tier ?? '') })
  if (a.badge.startsWith('monthly:')) return t('quests.name.monthly', { month: formatMonth(a.badge.slice(8), locale) })
  return t(`quests.name.${a.badge}`)
}

/** One slot per quest, in shelf order. */
export function shelfItems(data: PlayerBadges, t: T, locale: Locale): BadgeItem[] {
  const items: BadgeItem[] = []
  const date = (iso: string | null): string => (iso ? t('quests.earnedOn', { date: formatDate(iso, locale) }) : t('quests.notYet'))

  for (const key of ORDER) {
    const q = data.quests.find((x) => x.key === key)
    if (!q) continue
    const metals = metalsOf(key)
    const got = q.levels.filter((l) => l.earned_at).length
    const shown = Math.max(0, got - 1)
    const next = q.levels[got]
    const who = q.other_name ? t(`quests.with.${key}`, { name: q.other_name }) : ''
    items.push({
      id: key,
      img: img(`${key}_${q.levels[shown]!.threshold}`),
      name: t(`quests.name.${key}`),
      locked: got === 0,
      secret: false,
      metal: metals[shown] ?? 'b',
      tierLabel: got ? metalName(t, metals[got - 1] ?? 'b') : t('quests.notYet'),
      pips: q.levels.map((l, i) => (l.earned_at ? (metals[i] ?? 'b') : null)),
      earnedAt: latest(q.levels.map((l) => l.earned_at)),
      how: t(`quests.how.${key}`),
      tiers: q.levels.map((l, i) => ({ label: t(`quests.tier.${key}`, { n: l.threshold, metal: metalName(t, metals[i] ?? 'b') }), done: !!l.earned_at })),
      progress: next ? { value: Math.min(q.value, next.threshold), target: next.threshold, label: `${t(`quests.unit.${key}`, { n: q.value, target: next.threshold })}${who ? ` · ${who}` : ''}` } : null,
      dateLabel: date(latest(q.levels.map((l) => l.earned_at))),
    })
  }

  // podium: the highest tier reached since counting began, or the next one
  const pod = data.podium
  const reached = pod.earned.map((d, i) => (d ? i : -1)).filter((i) => i >= 0)
  const top = reached.at(-1)
  const nextRank = Math.min(PODIUM.length - 1, Math.max(pod.start_rank, pod.rank) + 1)
  const showRank = top ?? nextRank
  const nextTier = PODIUM[nextRank]!
  items.push({
    id: 'podium',
    img: img(`podium_${PODIUM[showRank]!.tier}_${PODIUM[showRank]!.art}`),
    name: t('quests.name.podium'),
    locked: top === undefined,
    secret: false,
    metal: PODIUM_METAL[showRank] ?? 'b',
    tierLabel: top !== undefined ? cap(PODIUM[top]!.tier) : t('quests.notYet'),
    pips: [],
    earnedAt: latest(pod.earned),
    how: t('quests.how.podium'),
    tiers: PODIUM.slice(pod.start_rank + 1).map((p, i) => ({ label: cap(p.tier), done: !!pod.earned[pod.start_rank + 1 + i] })),
    progress:
      pod.rank < PODIUM.length - 1
        ? { value: Math.max(0, pod.elo - PODIUM[pod.rank]!.from), target: nextTier.from - PODIUM[pod.rank]!.from, label: t('quests.unit.podium', { elo: pod.elo, target: nextTier.from, tier: cap(nextTier.tier) }) }
        : null,
    dateLabel: date(latest(pod.earned)),
  })

  // this month's quest
  const m = data.month
  items.push({
    id: 'monthly',
    img: img('monthly_gold'),
    name: t('quests.name.monthly', { month: formatMonth(m.month, locale) }),
    locked: !m.earned_at,
    secret: false,
    metal: 'g',
    tierLabel: m.earned_at ? t('quests.limited') : t('quests.notYet'),
    pips: [],
    earnedAt: m.earned_at,
    how: t('quests.how.monthly', { n: m.target }),
    tiers: [
      ...data.past_months.slice(0, 5).map((p) => ({ label: formatMonth(p.month, locale), done: true })),
      { label: formatMonth(m.month, locale), done: !!m.earned_at },
    ],
    progress: m.earned_at ? null : { value: Math.min(m.games, m.target), target: m.target, label: t('quests.unit.monthly', { n: m.games, target: m.target }) },
    dateLabel: date(m.earned_at),
  })

  for (const s of data.secrets) {
    const meta = SECRETS[s.key]
    if (!meta) continue
    const got = !!s.earned_at
    items.push({
      id: s.key,
      img: img(meta.art),
      name: got ? t(`quests.name.${s.key}`) : '???',
      locked: !got,
      secret: true,
      metal: meta.metal,
      tierLabel: got ? t('quests.secret') : t('quests.notYet'),
      pips: [],
      earnedAt: s.earned_at,
      how: got ? t(`quests.how.${s.key}`) : t('quests.how.secret'),
      tiers: [],
      progress: null,
      dateLabel: date(s.earned_at),
    })
  }
  return items
}

export interface AlmostItem {
  id: string
  /** the medal they are working towards, shown greyed */
  img: string
  title: string
  label: string
  /** 0..1, how far along */
  ratio: number
}

/**
 * "Almost there": the quests a member is furthest along towards their next
 * medal, for the top of their badges in LINE. Only quests already started
 * (some progress) and not finished; secrets never, since they say nothing
 * about themselves until won. This month's quest adds the days left.
 */
export function almostThere(data: PlayerBadges, t: T, locale: Locale, today: Date = new Date(), n = 3): AlmostItem[] {
  const out: AlmostItem[] = []
  for (const key of ORDER) {
    const q = data.quests.find((x) => x.key === key)
    if (!q) continue
    const got = q.levels.filter((l) => l.earned_at).length
    const next = q.levels[got]
    if (!next || q.value <= 0) continue
    const who = q.other_name ? t(`quests.with.${key}`, { name: q.other_name }) : ''
    out.push({
      id: key,
      img: img(`${key}_${next.threshold}`),
      title: `${t(`quests.name.${key}`)} · ${metalName(t, metalsOf(key)[got] ?? 'b')}`,
      label: `${t(`quests.unit.${key}`, { n: q.value, target: next.threshold })}${who ? ` · ${who}` : ''}`,
      ratio: Math.min(q.value, next.threshold) / next.threshold,
    })
  }

  const pod = data.podium
  const nextTier = PODIUM[pod.rank + 1]
  const here = PODIUM[pod.rank]
  if (nextTier && here) {
    const value = Math.max(0, pod.elo - here.from)
    const target = nextTier.from - here.from
    if (value > 0)
      out.push({
        id: 'podium',
        img: img(`podium_${nextTier.tier}_${nextTier.art}`),
        title: `${t('quests.name.podium')} · ${cap(nextTier.tier)}`,
        label: t('quests.unit.podium', { elo: pod.elo, target: nextTier.from, tier: cap(nextTier.tier) }),
        ratio: Math.min(1, value / target),
      })
  }

  const m = data.month
  if (!m.earned_at && m.games > 0) {
    const [y, mo] = m.month.split('-').map(Number)
    const thisMonth = y === today.getFullYear() && mo === today.getMonth() + 1
    const left = thisMonth ? new Date(y!, mo!, 0).getDate() - today.getDate() : 0
    out.push({
      id: 'monthly',
      img: img('monthly_gold'),
      title: t('quests.name.monthly', { month: formatMonth(m.month, locale) }),
      label: `${t('quests.unit.monthly', { n: m.games, target: m.target })}${thisMonth ? ` · ${t('quests.daysLeft', { n: left })}` : ''}`,
      ratio: Math.min(m.games, m.target) / m.target,
    })
  }
  return out.sort((a, b) => b.ratio - a.ratio).slice(0, n)
}

/** A member's grandest three, for their card: gold before silver before bronze, newest first. */
export function topThree(items: BadgeItem[]): BadgeItem[] {
  return items
    .filter((i) => !i.locked)
    .sort((a, b) => METAL_RANK[b.metal] - METAL_RANK[a.metal] || (b.earnedAt ?? '').localeCompare(a.earnedAt ?? ''))
    .slice(0, 3)
}
