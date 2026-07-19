import type { EloTier } from '@/types'

export interface TierInfo {
  tier: EloTier
  label: string
  colorVar: string
}

// Same thresholds as elo_service.get_tier() on the backend (plan section 3).
const TIERS: { max: number; tier: EloTier; label: string; colorVar: string }[] = [
  { max: 900, tier: 'milk', label: 'Milk', colorVar: 'var(--color-tier-milk)' },
  { max: 1100, tier: 'soju', label: 'Soju', colorVar: 'var(--color-tier-soju)' },
  { max: 1300, tier: 'beer', label: 'Beer', colorVar: 'var(--color-tier-beer)' },
  { max: 1500, tier: 'highball', label: 'Highball', colorVar: 'var(--color-tier-highball)' },
  { max: Infinity, tier: 'vodka', label: 'Vodka', colorVar: 'var(--color-tier-vodka)' },
]

/**
 * Maps an elo_score to its tier metadata. Pure function — no reactivity
 * needed, callers wrap it in a `computed(() => useEloTier(score))` if used
 * against reactive state.
 */
export function useEloTier(eloScore: number): TierInfo {
  const match = TIERS.find(({ max }) => eloScore < max)
  const { tier, label, colorVar } = match ?? TIERS[TIERS.length - 1]
  return { tier, label, colorVar }
}
