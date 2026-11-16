import { createRouter, createWebHistory } from 'vue-router'
import { nextPage } from '@/composables/usePageSwap'
import { useAuthStore } from '@/stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
  }
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  // Reset scroll to top on every new navigation (App.vue's page transition
  // unmounts the old view, so landing mid-scroll on the new one reads as
  // broken) — except back/forward, which restores where the user was.
  // Between two public pages the scroll waits for the new page to go in:
  // done at once, it moved the old page while it was still fading out (see
  // usePageSwap.ts). Anything without that fade scrolls straight away.
  scrollBehavior(to, from, savedPosition) {
    // Only the query changed (a tab, a filter): stay where the reader is.
    if (!savedPosition && from.matched.length > 0 && to.path === from.path) return false
    const target = savedPosition ?? { top: 0 }
    const fades =
      from.matched.length > 0 &&
      to.path !== from.path &&
      !to.path.startsWith('/admin') &&
      !from.path.startsWith('/admin') &&
      // The LINE page's screens are one page (App.vue's pageKey): no fade.
      !(to.name === 'line' && from.name === 'line')
    return fades ? nextPage().then(() => target) : target
  },
  routes: [
    // Public — read-only, no auth guard.
    {
      path: '/',
      name: 'home',
      component: () => import('../views/public/HomeView.vue'),
    },
    {
      path: '/members',
      name: 'members',
      component: () => import('../views/public/MemberListView.vue'),
    },
    {
      path: '/members/:id',
      name: 'member-profile',
      component: () => import('../views/public/PlayerProfileView.vue'),
    },
    {
      path: '/ranking',
      name: 'ranking',
      component: () => import('../views/public/RankingView.vue'),
    },
    {
      path: '/hall-of-fame',
      name: 'hall-of-fame',
      component: () => import('../views/public/HallOfFameView.vue'),
    },
    {
      path: '/live',
      name: 'live',
      component: () => import('../views/public/LiveView.vue'),
    },
    {
      path: '/matches',
      name: 'matches',
      component: () => import('../views/public/MatchHistoryView.vue'),
    },
    {
      path: '/matches/:id',
      name: 'match-detail',
      component: () => import('../views/public/MatchDetailView.vue'),
    },

    {
      path: '/menu',
      name: 'menu',
      component: () => import('../views/public/MenuView.vue'),
    },
    {
      path: '/search',
      name: 'search',
      component: () => import('../views/public/SearchView.vue'),
    },
    {
      path: '/tournament',
      name: 'tournament',
      component: () => import('../views/public/TournamentView.vue'),
    },
    {
      // The TV in the hall: courts, what's next, the latest results.
      path: '/tournament/board',
      name: 'tournament-board',
      component: () => import('../views/public/TournamentBoardView.vue'),
      meta: { bare: true },
    },
    {
      path: '/tournament/rules',
      name: 'tournament-rules',
      component: () => import('../views/public/TournamentRulesView.vue'),
    },
    {
      // Opened inside LINE (the club OA's LIFF app); no header or tab bar.
      // /line/register: the OA's sign-up button; /line/checkin?c=…: tonight's
      // check-in QR; /line/shop: the OA's shop button, which learns who this
      // is and goes on to /shop (LIFF adds the path to the endpoint URL).
      path: '/line/:section(register|checkin|checkout|bills|credit|badges|shop|profile|pass|tournament)?',
      name: 'line',
      component: () => import('../views/line/LineView.vue'),
      meta: { bare: true },
    },
    {
      path: '/shop',
      name: 'shop',
      component: () => import('../views/public/ShopView.vue'),
    },
    {
      path: '/shop/:id',
      name: 'shop-product',
      component: () => import('../views/public/ShopProductView.vue'),
    },
    {
      path: '/shop/cart',
      name: 'shop-cart',
      component: () => import('../views/public/ShopCartView.vue'),
    },
    {
      path: '/shop/checkout',
      name: 'shop-checkout',
      component: () => import('../views/public/ShopCheckoutView.vue'),
    },
    // Links from before the cart (one product per order) land in the cart.
    { path: '/shop/:id/order', redirect: '/shop/cart' },

    // Admin — guarded except login.
    {
      path: '/admin/login',
      name: 'admin-login',
      component: () => import('../views/admin/LoginView.vue'),
    },
    {
      path: '/admin',
      name: 'admin-dashboard',
      component: () => import('../views/admin/DashboardView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/admin/checkin',
      name: 'admin-checkin',
      component: () => import('../views/admin/CheckinView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/admin/members',
      name: 'admin-members',
      component: () => import('../views/admin/ManageMembersView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/admin/matchmaking',
      name: 'admin-matchmaking',
      component: () => import('../views/admin/MatchmakingView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/admin/matches/record',
      name: 'admin-match-record',
      component: () => import('../views/admin/MatchRecordView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/admin/billing',
      name: 'admin-billing',
      component: () => import('../views/admin/BillingView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/admin/expenses',
      name: 'admin-expenses',
      component: () => import('../views/admin/ExpensesView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/admin/revenue',
      name: 'admin-revenue',
      component: () => import('../views/admin/RevenueView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/admin/shop',
      name: 'admin-shop',
      component: () => import('../views/admin/ShopAdminView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/admin/credit',
      name: 'admin-credit',
      component: () => import('../views/admin/CreditView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/admin/sponsors',
      name: 'admin-sponsors',
      component: () => import('../views/admin/SponsorsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/admin/settings',
      name: 'admin-settings',
      component: () => import('../views/admin/SettingsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/admin/activity-log',
      name: 'admin-activity-log',
      component: () => import('../views/admin/ActivityLogView.vue'),
      meta: { requiresAuth: true },
    },

    // The tournament's own admin screens: only for admins with that right,
    // and none of the club's screens are reached from here.
    {
      path: '/admin/tournament',
      name: 'admin-tournament',
      component: () => import('../views/admin/tournament/TournamentEventView.vue'),
      meta: { requiresAuth: true, area: 'tournament' },
    },
    {
      path: '/admin/tournament/teams',
      name: 'admin-tournament-teams',
      component: () => import('../views/admin/tournament/TournamentTeamsView.vue'),
      meta: { requiresAuth: true, area: 'tournament' },
    },
    {
      path: '/admin/tournament/draw',
      name: 'admin-tournament-draw',
      component: () => import('../views/admin/tournament/TournamentDrawView.vue'),
      meta: { requiresAuth: true, area: 'tournament' },
    },
    {
      path: '/admin/tournament/day',
      name: 'admin-tournament-day',
      component: () => import('../views/admin/tournament/TournamentDayView.vue'),
      meta: { requiresAuth: true, area: 'tournament' },
    },
    {
      // Paper for the day: the match list and a score sheet per match.
      path: '/admin/tournament/print',
      name: 'admin-tournament-print',
      component: () => import('../views/admin/tournament/TournamentPrintView.vue'),
      meta: { requiresAuth: true, area: 'tournament', bare: true },
    },
    {
      path: '/admin/tournament/money',
      name: 'admin-tournament-money',
      component: () => import('../views/admin/tournament/TournamentMoneyView.vue'),
      meta: { requiresAuth: true, area: 'tournament' },
    },
    {
      path: '/admin/tournament/activity',
      name: 'admin-tournament-activity',
      component: () => import('../views/admin/tournament/TournamentActivityView.vue'),
      meta: { requiresAuth: true, area: 'tournament' },
    },

    // Last, so it only catches what nothing above matched. Without it an
    // unknown path matched no route at all and <RouterView> rendered
    // nothing — a blank page under the header, with no way back.
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('../views/public/NotFoundView.vue'),
    },
  ],
})

router.beforeEach((to) => {
  if (!to.meta.requiresAuth) return true

  const authStore = useAuthStore()
  if (!authStore.isAuthenticated) {
    return { name: 'admin-login' }
  }
  // Each side only for those with its right: the other side's screens
  // send them to their own.
  const tournamentArea = to.meta.area === 'tournament'
  if (tournamentArea && !authStore.canTournament) return { path: '/admin' }
  if (!tournamentArea && !authStore.canClub) return { path: '/admin/tournament' }
  return true
})

export default router
