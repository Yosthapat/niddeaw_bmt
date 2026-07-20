import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico'],
      // Explicit (not relying on plugin defaults) so a new deploy takes over
      // an already-open tab immediately instead of serving a stale cached
      // build until the user manually clears the service worker.
      workbox: {
        skipWaiting: true,
        clientsClaim: true,
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
