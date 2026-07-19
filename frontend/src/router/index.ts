import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
  }
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
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
      path: '/matches',
      name: 'matches',
      component: () => import('../views/public/MatchHistoryView.vue'),
    },

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
      path: '/admin/settings',
      name: 'admin-settings',
      component: () => import('../views/admin/SettingsView.vue'),
      meta: { requiresAuth: true },
    },
  ],
})

router.beforeEach((to) => {
  if (!to.meta.requiresAuth) return true

  const authStore = useAuthStore()
  if (!authStore.isAuthenticated) {
    return { name: 'admin-login' }
  }
  return true
})

export default router
