import type { Product } from '@/types'

export type BadgeTone = 'preorder' | 'left' | 'in' | 'out'

/** The one-line status every product card and page shows, and its tone:
 *  a pre-order and when it closes, how many are left, or sold out. The
 *  caller turns `key` into words. */
export function productBadge(p: Product): { key: string; params: Record<string, string | number>; tone: BadgeTone } {
  if (p.sale_type === 'preorder') {
    return p.open
      ? { key: 'shop.badgePreorder', params: { date: p.preorder_closes_on ?? '' }, tone: 'preorder' }
      : { key: 'shop.badgePreorderClosed', params: {}, tone: 'out' }
  }
  const left = Object.values(p.stock).reduce((sum, n) => sum + n, 0)
  if (left === 0) return { key: 'shop.badgeSoldOut', params: {}, tone: 'out' }
  if (left <= 10) return { key: 'shop.badgeLeft', params: { n: left }, tone: 'left' }
  return { key: 'shop.badgeInStock', params: {}, tone: 'in' }
}

export const BADGE_CLASS: Record<BadgeTone, string> = {
  preorder: 'bg-[#ffe14d] text-[#2a1a00]',
  left: 'bg-black/55 text-white',
  in: 'bg-[#7ff0b4]/20 text-[#7ff0b4]',
  out: 'bg-black/60 text-white/75',
}
