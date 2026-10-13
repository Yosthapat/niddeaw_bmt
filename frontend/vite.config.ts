import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    VitePWA({
      // 'prompt', not 'autoUpdate': the admin uses this standing on a court
      // with a half-filled bill on screen, and a build that swaps itself in
      // underneath them loses what they typed. The new version waits, the
      // screen offers it (UpdateBanner.vue), and the reload happens when
      // they say so.
      //
      // skipWaiting is deliberately absent for the same reason — it is what
      // makes a waiting worker take over on its own. UpdateBanner asks for
      // it by hand, once, on the tap.
      registerType: 'prompt',
      includeAssets: ['favicon.ico'],
      workbox: {
        cleanupOutdatedCaches: true,
      },
      manifest: {
        name: 'นิดเดียว Badminton Club',
        short_name: 'นิดเดียว BMT',
        description: 'นิดเดียว Badminton Club — member ranking, matchmaking, billing and hall of fame.',
        theme_color: '#0a0a0a',
        background_color: '#0a0a0a',
        display: 'standalone',
        start_url: '/',
        icons: [
          {
            src: '/pwa-icons/pwa-64x64.png',
            sizes: '64x64',
            type: 'image/png',
          },
          {
            src: '/pwa-icons/pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: '/pwa-icons/pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
          },
          {
            src: '/pwa-icons/maskable-icon-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
})
