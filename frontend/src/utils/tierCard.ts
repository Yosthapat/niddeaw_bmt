import type { EloTier } from '@/types'

/** How a member card is dressed for each tier: a metal frame in the tier's
 *  own colour (light -> mid -> dark, from the --color-tier-* tokens), and
 *  from Soju up a moving holographic foil — the rarer the tier, the shinier
 *  the card, which is the point of a trading card. */
export interface TierCardStyle {
  light: string
  mid: string
  dark: string
  /** tier name on the card; lighter than `mid` so it reads on dark glass */
  text: string
  foil: boolean
}

export const TIER_CARD: Record<EloTier, TierCardStyle> = {
  milk: { light: '#ffffff', mid: '#e8e4da', dark: '#8d8778', text: '#f4f1ea', foil: false },
  beer: { light: '#ffe28a', mid: '#dfa11a', dark: '#6e4a05', text: '#ffd36a', foil: false },
  highball: { light: '#ffc8a3', mid: '#ea6f2f', dark: '#7a2c0c', text: '#ffb07f', foil: false },
  wine: { light: '#f0a9bd', mid: '#9b3552', dark: '#3d1220', text: '#ff9fbb', foil: false },
  soju: { light: '#e2fbe6', mid: '#8ec899', dark: '#2f6b3c', text: '#a8f0b6', foil: true },
  whisky: { light: '#f3b3a6', mid: '#a8503f', dark: '#4d1d14', text: '#ffb19f', foil: true },
  vodka: { light: '#e2ccff', mid: '#9d5bf4', dark: '#3d1680', text: '#d2b2ff', foil: true },
  absinthe: { light: '#ffe14d', mid: '#6d7dff', dark: '#4b3f9e', text: '#ffe14d', foil: true },
}

export const TIER_ORDER: EloTier[] = ['milk', 'beer', 'highball', 'wine', 'soju', 'whisky', 'vodka', 'absinthe']
