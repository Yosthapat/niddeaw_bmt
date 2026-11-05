/**
 * The admin screens, once: their names, icons, the mascot on each one's
 * banner and the line under its title. The glass bar (AppHeader.vue), the
 * phone's bottom bar (AdminTabBar.vue) and the banners (AdminNav.vue) all
 * read from here, so a new screen is one entry.
 *
 * `night` are the four a club night runs on, in the order it runs them —
 * they get the phone's bottom bar; the rest sit behind "เพิ่มเติม".
 */
export interface AdminPage {
  to: string
  /** i18n key of its name under admin.nav */
  nav: string
  /** i18n key of the line under its banner title, under admin.banner */
  banner: string
  /** English eyebrow over the banner title, in the public pages' voice */
  eyebrow: string
  mascot: string
  /** 24×24 line icon path */
  icon: string
  night?: boolean
  /** in the menus (match record is reached from the matchmaking screen) */
  listed?: boolean
}

export const ADMIN_PAGES: AdminPage[] = [
  { to: '/admin', nav: 'dashboard', banner: 'dashboard', eyebrow: 'Admin · Dashboard', mascot: '/hero/cat-color.webp', night: true, listed: true,
    icon: 'M3 11 12 4l9 7M5 10v10h5v-6h4v6h5V10' },
  { to: '/admin/checkin', nav: 'checkin', banner: 'checkin', eyebrow: 'Admin · Check-in', mascot: '/tiers/beer.webp', night: true, listed: true,
    icon: 'M9 11l3 3 8-8M20 12v7a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h9' },
  { to: '/admin/matchmaking', nav: 'matchmaking', banner: 'matchmaking', eyebrow: 'Admin · Matchmaking', mascot: '/tiers/soju.webp', night: true, listed: true,
    icon: 'M16 19v-1a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v1M9.5 10a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7ZM21 19v-1a4 4 0 0 0-3-3.8M15.5 3.2a3.5 3.5 0 0 1 0 6.6' },
  { to: '/admin/billing', nav: 'billing', banner: 'billing', eyebrow: 'Admin · Billing', mascot: '/tiers/highball.webp', night: true, listed: true,
    icon: 'M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1ZM16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8M12 17.5v-11' },
  { to: '/admin/members', nav: 'members', banner: 'members', eyebrow: 'Admin · Members', mascot: '/tiers/milk.webp', listed: true,
    icon: 'M19 8v6M22 11h-6M15 19v-1a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v1M8.5 10a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z' },
  { to: '/admin/shop', nav: 'shop', banner: 'shop', eyebrow: 'Admin · Shop', mascot: '/tiers/highball.webp', listed: true,
    icon: 'M4 9.5 5.5 4h13L20 9.5M4 9.5h16M4 9.5a2.7 2.7 0 0 0 5.3 0 2.7 2.7 0 0 0 5.4 0 2.7 2.7 0 0 0 5.3 0M5.5 12.5V20h13v-7.5M10 20v-4h4v4' },
  { to: '/admin/credit', nav: 'credit', banner: 'credit', eyebrow: 'Admin · Credit', mascot: '/tiers/whisky.webp', listed: true,
    icon: 'M8 14A6 6 0 1 0 8 2a6 6 0 0 0 0 12ZM18.09 10.37A6 6 0 1 1 10.34 18M7 6h1v4M16.71 13.88l.7.71-2.82 2.82' },
  { to: '/admin/revenue', nav: 'revenue', banner: 'revenue', eyebrow: 'Admin · Revenue', mascot: '/tiers/wine.webp', listed: true,
    icon: 'M3 3v18h18M7 15l4-4 3 3 6-7' },
  { to: '/admin/expenses', nav: 'expenses', banner: 'expenses', eyebrow: 'Admin · Expenses', mascot: '/tiers/whisky.webp', listed: true,
    icon: 'M2 7h20v12H2zM2 11h20M6 15h4' },
  { to: '/admin/sponsors', nav: 'sponsors', banner: 'sponsors', eyebrow: 'Admin · Sponsors', mascot: '/tiers/absinthe.webp', listed: true,
    icon: 'M12 2 15 8.5l7 .9-5.1 4.8 1.3 7L12 17.8 5.8 21.2l1.3-7L2 9.4l7-.9z' },
  { to: '/admin/settings', nav: 'settings', banner: 'settings', eyebrow: 'Admin · Settings', mascot: '/tiers/vodka.webp', listed: true,
    icon: 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z' },
  { to: '/admin/activity-log', nav: 'activityLog', banner: 'activityLog', eyebrow: 'Admin · Activity', mascot: '/tiers/wine.webp', listed: true,
    icon: 'M12 8v4l3 2M3.05 11a9 9 0 1 1 .5 4M3 4v5h5' },
  { to: '/admin/matches/record', nav: 'matchRecord', banner: 'matchRecord', eyebrow: 'Admin · Match result', mascot: '/tiers/soju.webp',
    icon: '' },
]

export const MORE_ICON = 'M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z'

export function adminPage(path: string): AdminPage | undefined {
  return ADMIN_PAGES.find((p) => p.to === path)
}
