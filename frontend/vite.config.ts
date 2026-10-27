import { execSync } from 'node:child_process'
import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'

/**
 * Which build this is, baked in at build time.
 *
 * The question it answers is the one that cost an evening: a phone with the
 * app on its home screen is served by a service worker, so "the site is
 * updated" and "this phone has the update" are different facts, and from
 * the outside they look the same. The settings screen prints this, and the
 * two can be compared in five seconds instead of guessed at.
 *
 * The host's own commit variable first — Cloudflare's build checkout is
 * shallow and `git` may not even be on the image — then git, then nothing.
 */
function buildSha(): string {
  const fromHost =
    process.env.WORKERS_CI_COMMIT_SHA ??
    process.env.CF_PAGES_COMMIT_SHA ??
    process.env.GITHUB_SHA
  if (fromHost) return fromHost.slice(0, 7)
  try {
    return execSync('git rev-parse --short HEAD', { encoding: 'utf8' }).trim()
  } catch {
    return 'dev'
  }
}

// https://vite.dev/config/
export default defineConfig({
  define: {
    __BUILD_SHA__: JSON.stringify(buildSha()),
    // Seconds are noise at a glance, and the minute is what a deploy log
    // shows beside it.
    __BUILD_TIME__: JSON.stringify(new Date().toISOString().slice(0, 16).replace('T', ' ')),
  },
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
        // The 3D home hero (three.js, ~130 KB gzipped) is only fetched by a
        // phone that will run it. Precaching it would make every installed
        // phone download it, including the ones that keep the CSS hero.
        // Offline, the hero just stays CSS.
        globIgnores: ['**/heroScene-*.js', '**/hero/cat-depth.png'],
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
