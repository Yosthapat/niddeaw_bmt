import type { EloTier } from '@/types'

// Representative starting score per tier — matches the boundaries in
// backend/app/services/elo_service.py's get_tier() thresholds.
export const STARTING_TIERS: { tier: EloTier; label: string; score: number; color: string; gradient?: string }[] = [
  { tier: 'milk', label: 'Milk', score: 800, color: 'var(--color-tier-milk)' },
  { tier: 'beer', label: 'Beer', score: 1000, color: 'var(--color-tier-beer)' },
  { tier: 'highball', label: 'Highball', score: 1200, color: 'var(--color-tier-highball)' },
  { tier: 'wine', label: 'Wine', score: 1400, color: 'var(--color-tier-wine)' },
  { tier: 'soju', label: 'Soju', score: 1600, color: 'var(--color-tier-soju)' },
  { tier: 'whisky', label: 'Whisky', score: 1800, color: 'var(--color-tier-whisky)' },
  { tier: 'vodka', label: 'Vodka', score: 2000, color: 'var(--color-tier-vodka)' },
  { tier: 'absinthe', label: 'Absinthe', score: 2200, color: 'var(--color-tier-absinthe)', gradient: 'var(--gradient-tier-absinthe)' },
]
