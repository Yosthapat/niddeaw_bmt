import type { EloTier } from '@/types'

export interface TierInfo {
  tier: EloTier
  label: string
  colorVar: string
  /** Only set for Absinthe — the rainbow "rarest rank" treatment. */
  gradient?: string
}

// Same thresholds as elo_service.get_tier() on the backend — ordered by
// rising alcohol content (Milk 0% -> Beer ~5% -> Highball ~7-9% -> Wine
// ~12-13% -> Soju ~16-20% -> Whisky ~40% -> Vodka ~40%+ -> Absinthe ~55-74%).
const TIERS: { max: number; tier: EloTier; label: string; colorVar: string; gradient?: string }[] = [
  { max: 900, tier: 'milk', label: 'Milk', colorVar: 'var(--color-tier-milk)' },
  { max: 1100, tier: 'beer', label: 'Beer', colorVar: 'var(--color-tier-beer)' },
  { max: 1300, tier: 'highball', label: 'Highball', colorVar: 'var(--color-tier-highball)' },
  { max: 1500, tier: 'wine', label: 'Wine', colorVar: 'var(--color-tier-wine)' },
  { max: 1700, tier: 'soju', label: 'Soju', colorVar: 'var(--color-tier-soju)' },
  { max: 1900, tier: 'whisky', label: 'Whisky', colorVar: 'var(--color-tier-whisky)' },
  { max: 2100, tier: 'vodka', label: 'Vodka', colorVar: 'var(--color-tier-vodka)' },
  {
    max: Infinity,
    tier: 'absinthe',
    label: 'Absinthe',
    colorVar: 'var(--color-tier-absinthe)',
    gradient: 'var(--gradient-tier-absinthe)',
  },
]

/**
 * Maps an elo_score to its tier metadata. Pure function — no reactivity
 * needed, callers wrap it in a `computed(() => useEloTier(score))` if used
 * against reactive state.
 */
export function useEloTier(eloScore: number): TierInfo {
  const match = TIERS.find(({ max }) => eloScore < max)
  const { tier, label, colorVar, gradient } = match ?? TIERS[TIERS.length - 1]
  return { tier, label, colorVar, gradient }
}

/** Same metadata as useEloTier(), looked up by tier name instead of score
 *  (e.g. for TierInfoModal, which only knows which mascot was clicked). */
export function tierMeta(tier: EloTier): TierInfo {
  const match = TIERS.find((t) => t.tier === tier) ?? TIERS[TIERS.length - 1]
  const { label, colorVar, gradient } = match
  return { tier, label, colorVar, gradient }
}

/** Solid color, unless the tier has a rainbow gradient (Absinthe). */
export function tierTextStyle(
  colorVar: string,
  gradient?: string,
): { color?: string; backgroundImage?: string; WebkitBackgroundClip?: string; backgroundClip?: string } {
  if (gradient) {
    return { backgroundImage: gradient, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent' }
  }
  return { color: colorVar }
}

/** Same idea as tierTextStyle() but for a solid swatch/dot instead of text. */
export function tierSwatchStyle(colorVar: string, gradient?: string): { backgroundColor?: string; backgroundImage?: string } {
  return gradient ? { backgroundImage: gradient } : { backgroundColor: colorVar }
}
