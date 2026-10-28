import type { Sponsor } from '@/types'

/** What the band needs to draw one logo. */
export type BandLogo = Pick<Sponsor, 'name' | 'href' | 'logo_url' | 'logo_width' | 'logo_height'>

// The five that were on the band before sponsors moved into the database
// (db/migrations/0026_sponsors.sql seeds the same five). Shown until the
// list arrives, and kept if it can't be fetched — a backend deployed
// before the migration ran, or a cold start — so the band is never empty
// because of the network.
export const BUNDLED_SPONSORS: BandLogo[] = [
  { name: 'Wasteland', logo_url: '/sponsors/wasteland-mono.png', logo_width: 424, logo_height: 104, href: 'https://www.instagram.com/wastelandbkk' },
  { name: 'Match Mellow', logo_url: '/sponsors/match-mellow-mono.png', logo_width: 323, logo_height: 205, href: 'https://www.instagram.com/match.mellowww' },
  { name: 'Sawadee Natural Herbal Balm', logo_url: '/sponsors/sawadee-mono.png', logo_width: 417, logo_height: 350, href: 'https://www.instagram.com/sawadee_naturalherbalbalm' },
  { name: 'Umore Made', logo_url: '/sponsors/umore-made-mono.png', logo_width: 449, logo_height: 169, href: 'https://www.instagram.com/umore.made' },
  { name: 'The Players Club', logo_url: '/sponsors/players-club-mono.png', logo_width: 354, logo_height: 388, href: 'https://www.instagram.com/theplayersclubthailand' },
]

// One height for every logo would make a long wordmark a sliver and a
// round badge a block. Sizing each to the same area instead gives them the
// same visual weight in the band. In px at phone width; the band scales it.
const LOGO_AREA = 2400
export function logoHeight(logo: { logo_width: number; logo_height: number }): number {
  const aspect = logo.logo_width / logo.logo_height
  return Math.round(Math.min(52, Math.max(20, Math.sqrt(LOGO_AREA / aspect))))
}
