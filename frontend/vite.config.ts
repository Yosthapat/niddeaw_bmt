import { execSync } from 'node:child_process'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'
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

const BUILD_SHA = buildSha()

/**
 * Link previews for the tournament. LINE and Facebook read the page's own
 * HTML and run no script, so the app's one index.html can't show a
 * different card for /tournament. After the build this writes copies of
 * it — dist/tournament.html and dist/tournament/rules.html, which
 * Cloudflare serves at /tournament and /tournament/rules — with the
 * tournament's title, words and picture in their meta tags. The app in
 * them is the same; only the preview differs.
 */
const SITE = 'https://niddeaw.fyi'
const SHARE_PAGES: { file: string; path: string; title: string; description: string }[] = [
  {
    file: 'tournament.html',
    path: '/tournament',
    title: 'NIDDEAW CUP · ทัวร์นาเมนต์แบดมินตันของก๊วนนิดเดียว',
    description: 'แบ่งมือตามระดับ ELO · สมัครเป็นคู่ผ่าน LINE · ดูกลุ่ม สายการแข่ง และผลสดได้จากมือถือ',
  },
  {
    file: 'tournament/rules.html',
    path: '/tournament/rules',
    title: 'กติกาการแข่งขัน · NIDDEAW CUP',
    description: 'การสมัคร · มือ · รอบแบ่งกลุ่ม · น็อคเอาท์ · วันแข่ง · ในสนาม · ลูกและคูปอง',
  },
]
const shareCards = {
  name: 'share-cards',
  apply: 'build' as const,
  enforce: 'post' as const,
  closeBundle() {
    const dist = fileURLToPath(new URL('./dist', import.meta.url))
    const index = readFileSync(`${dist}/index.html`, 'utf8')
    const meta = (prop: string, value: string): [RegExp, string] => [
      new RegExp(`(<meta (?:property|name)="${prop}" content=")[^"]*(")`),
      `$1${value}$2`,
    ]
    for (const page of SHARE_PAGES) {
      let html = index.replace(/<title>[^<]*<\/title>/, `<title>${page.title}</title>`)
      for (const [pattern, value] of [
        meta('description', page.description),
        meta('og:title', page.title),
        meta('og:description', page.description),
        meta('og:image', `${SITE}/og/tournament.jpg`),
        meta('twitter:card', 'summary_large_image'),
      ])
        html = html.replace(pattern, value)
      html = html.replace('<meta property="og:type"', `<meta property="og:url" content="${SITE}${page.path}" />\n    <meta property="og:type"`)
      mkdirSync(dirname(`${dist}/${page.file}`), { recursive: true })
      writeFileSync(`${dist}/${page.file}`, html)
    }
  },
}

/**
 * dist/version.json: which build the server has now. The page compares it
 * with the build it is running (UpdateBanner.vue) — a check that needs no
 * service worker, for the phone whose worker never notices a deploy. JSON
 * is outside the worker's precache (it keeps js, css and html), so the
 * fetch always reaches the network.
 */
const versionFile = {
  name: 'version-file',
  generateBundle(this: { emitFile: (f: { type: 'asset'; fileName: string; source: string }) => void }) {
    this.emitFile({ type: 'asset', fileName: 'version.json', source: JSON.stringify({ sha: BUILD_SHA }) })
  },
}

// https://vite.dev/config/
export default defineConfig({
  define: {
    __BUILD_SHA__: JSON.stringify(BUILD_SHA),
    // Seconds are noise at a glance, and the minute is what a deploy log
    // shows beside it.
    __BUILD_TIME__: JSON.stringify(new Date().toISOString().slice(0, 16).replace('T', ' ')),
  },
  plugins: [
    vue(),
    versionFile,
    shareCards,
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
