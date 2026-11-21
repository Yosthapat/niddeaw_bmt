<script setup lang="ts">
/**
 * Last Christmas, for the season: a small record button in the corner
 * that opens a card with the song's official video playing.
 *
 * Played through YouTube's own player, which keeps it licensed: the club
 * never hosts the song. YouTube's rules want its player seen, not hidden
 * behind a button, so the video shows in the card for as long as it plays,
 * and closing the card stops it. A member signed in to YouTube Premium in
 * the same browser hears it without ads; others may get YouTube's.
 *
 * Nothing loads from YouTube until the button is tapped, and a browser
 * will not start sound without that tap anyway. The card also holds the
 * switch for the snow (prefs.ts).
 */
import { nextTick, onBeforeUnmount, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { snowOn } from './prefs'
import { reducedMotion } from './season'

// Wham! - Last Christmas (Official Video), WhamVEVO
const VIDEO_ID = 'E8gmARGvPlI'
const HIDDEN_KEY = 'niddeaw_xmas_music_hidden'
const WATCH_URL = `https://www.youtube.com/watch?v=${VIDEO_ID}`

interface YTPlayer {
  playVideo(): void
  pauseVideo(): void
  destroy(): void
}
interface YTNamespace {
  Player: new (
    el: HTMLElement,
    opts: {
      videoId: string
      width: string
      height: string
      playerVars: Record<string, string | number>
      events: { onReady: () => void; onStateChange: (e: { data: number }) => void; onError: (e: { data: number }) => void }
    },
  ) => YTPlayer
}
declare global {
  interface Window {
    YT?: YTNamespace
    onYouTubeIframeAPIReady?: () => void
  }
}

const { t } = useI18n()
const open = ref(false)
const playing = ref(false)
const failed = ref(false)
const host = ref<HTMLElement | null>(null)
const showSnowSwitch = !reducedMotion()

function wasHidden(): boolean {
  try {
    return sessionStorage.getItem(HIDDEN_KEY) === '1'
  } catch {
    return false
  }
}
const hidden = ref(wasHidden())

let player: YTPlayer | null = null
let api: Promise<YTNamespace> | null = null

function loadApi(): Promise<YTNamespace> {
  api ??= new Promise<YTNamespace>((resolve, reject) => {
    if (window.YT?.Player) return resolve(window.YT)
    const before = window.onYouTubeIframeAPIReady
    window.onYouTubeIframeAPIReady = () => {
      before?.()
      if (window.YT) resolve(window.YT)
    }
    const s = document.createElement('script')
    s.src = 'https://www.youtube.com/iframe_api'
    s.async = true
    s.onerror = () => {
      api = null
      reject(new Error('YouTube did not load'))
    }
    document.head.appendChild(s)
  })
  return api
}

async function start(): Promise<void> {
  open.value = true
  failed.value = false
  if (player) {
    player.playVideo()
    return
  }
  try {
    const YT = await loadApi()
    await nextTick()
    if (!host.value || !open.value) return
    // YouTube swaps the element it is given for its iframe: hand it one of
    // its own, so the element Vue looks after stays where Vue left it.
    const mount = document.createElement('div')
    host.value.appendChild(mount)
    player = new YT.Player(mount, {
      videoId: VIDEO_ID,
      width: '100%',
      height: '100%',
      playerVars: { autoplay: 1, playsinline: 1, rel: 0, loop: 1, playlist: VIDEO_ID },
      events: {
        onReady: () => player?.playVideo(),
        // 1 playing, 2 paused, 0 ended (loops), 3 buffering
        onStateChange: (e) => {
          playing.value = e.data === 1 || e.data === 3
        },
        // e.g. 150, the video can't be played embedded here: offer YouTube itself
        onError: () => {
          failed.value = true
          playing.value = false
        },
      },
    })
  } catch {
    failed.value = true
  }
}

function toggle(): void {
  if (!player) return void start()
  if (playing.value) player.pauseVideo()
  else player.playVideo()
}

/** Close the card: the video goes, so the music stops with it. */
function close(): void {
  player?.destroy()
  player = null
  playing.value = false
  open.value = false
}

function hide(): void {
  hidden.value = true
  try {
    sessionStorage.setItem(HIDDEN_KEY, '1')
  } catch {
    // storage blocked: hidden until the next page load
  }
}

onBeforeUnmount(() => player?.destroy())
</script>

<template>
  <div v-if="!hidden" class="xmas-music">
    <!-- the card, with the video playing -->
    <section v-if="open" class="card" :aria-label="t('xmas.music.title')">
      <header class="flex items-center gap-3 px-3.5 pt-3 pb-2.5">
        <span class="disc" :class="{ spin: playing }" aria-hidden="true" />
        <span class="min-w-0 flex-1">
          <span class="block truncate font-display text-[15px] font-bold text-white">{{ t('xmas.music.title') }}</span>
          <span class="block truncate text-xs text-white/60">{{ t('xmas.music.artist') }}</span>
        </span>
        <button type="button" class="round" :aria-label="playing ? t('xmas.music.pause') : t('xmas.music.play')" @click="toggle">
          <svg v-if="playing" viewBox="0 0 24 24" fill="currentColor" class="h-5 w-5" aria-hidden="true"><path d="M7 5h3.5v14H7zM13.5 5H17v14h-3.5z" /></svg>
          <svg v-else viewBox="0 0 24 24" fill="currentColor" class="h-5 w-5" aria-hidden="true"><path d="M8 5.5v13l10.5-6.5z" /></svg>
        </button>
        <button type="button" class="round" :aria-label="t('xmas.music.close')" @click="close">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" class="h-5 w-5" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg>
        </button>
      </header>
      <!-- YouTube's player, kept in view while it plays (its rules) -->
      <div class="screen">
        <div ref="host" class="h-full w-full" />
        <div v-if="failed" class="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-black p-4 text-center text-sm text-white/75">
          <p>{{ t('xmas.music.failed') }}</p>
          <a :href="WATCH_URL" target="_blank" rel="noopener" class="rounded-full bg-[#ea4ca4] px-4 py-2.5 font-medium text-white">{{ t('xmas.music.onYoutube') }}</a>
        </div>
      </div>
      <footer v-if="showSnowSwitch" class="flex items-center justify-between gap-3 px-3.5 py-2.5 text-[13px] text-white/75">
        <span>{{ t('xmas.snow.label') }}</span>
        <button type="button" class="switch" role="switch" :aria-checked="snowOn" @click="snowOn = !snowOn">
          <span class="knob" />
          <span class="sr-only">{{ t('xmas.snow.label') }}</span>
        </button>
      </footer>
    </section>

    <!-- the record button -->
    <div v-else class="pill">
      <button type="button" class="pill-main" :aria-label="t('xmas.music.open')" @click="start">
        <span class="disc" aria-hidden="true" />
        <!-- words from 900px; on a phone the record alone, so it covers less -->
        <span class="min-w-0 text-left max-[899px]:hidden">
          <span class="block truncate font-display text-[14px] leading-tight font-bold text-white">{{ t('xmas.music.title') }}</span>
          <span class="block truncate text-[11px] leading-tight text-white/60">{{ t('xmas.music.tap') }}</span>
        </span>
      </button>
      <button type="button" class="pill-x" :aria-label="t('xmas.music.hide')" @click="hide">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" class="h-3.5 w-3.5" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.xmas-music {
  position: fixed;
  z-index: 40;
  right: 12px;
  /* above the phone's tab bar (96px of room is kept for it, App.vue) */
  bottom: calc(96px + env(safe-area-inset-bottom, 0px));
}
@media (min-width: 900px) {
  .xmas-music {
    right: 24px;
    bottom: 24px;
  }
}

.pill {
  position: relative;
  display: flex;
  align-items: center;
  border-radius: 999px;
  background: rgb(10 4 6 / 0.82);
  border: 1px solid rgb(234 76 164 / 0.55);
  box-shadow:
    0 0 18px rgb(234 76 164 / 0.4),
    0 10px 24px rgb(0 0 0 / 0.45);
  -webkit-backdrop-filter: blur(10px);
  backdrop-filter: blur(10px);
}
.pill-main {
  display: flex;
  min-height: 52px;
  max-width: 220px;
  align-items: center;
  gap: 10px;
  padding: 6px 14px 6px 7px;
  border-radius: 999px;
}
@media (max-width: 899px) {
  .pill-main {
    padding: 6px;
  }
}
.pill-x {
  position: absolute;
  top: -8px;
  right: -6px;
  display: grid;
  width: 24px;
  height: 24px;
  place-items: center;
  border-radius: 999px;
  background: #26181f;
  border: 1px solid rgb(255 255 255 / 0.2);
  color: rgb(255 255 255 / 0.75);
}
/* a 24px tap target is small; the pseudo-element widens it to 40px */
.pill-x::after {
  content: '';
  position: absolute;
  inset: -8px;
}

/* the record: a pink label on black vinyl */
.disc {
  position: relative;
  flex-shrink: 0;
  width: 38px;
  height: 38px;
  border-radius: 999px;
  background:
    radial-gradient(circle, #0a0406 0 7%, #ea4ca4 8% 30%, transparent 31%),
    repeating-radial-gradient(circle, #1b1b1f 0 2px, #0c0c0f 2px 4px);
  box-shadow:
    inset 0 0 0 2px #2b2b33,
    0 0 12px rgb(234 76 164 / 0.45);
}
.disc::after {
  /* the shine that shows it turning */
  content: '';
  position: absolute;
  inset: 3px;
  border-radius: 999px;
  background: conic-gradient(from 30deg, transparent 0 20%, rgb(255 255 255 / 0.18) 25%, transparent 32% 70%, rgb(255 255 255 / 0.12) 75%, transparent 80%);
}
.spin {
  animation: disc-spin 2.2s linear infinite;
}
@keyframes disc-spin {
  to {
    rotate: 360deg;
  }
}

.card {
  width: min(340px, calc(100vw - 24px));
  overflow: hidden;
  border-radius: 22px;
  background: rgb(14 6 22 / 0.94);
  border: 1px solid rgb(234 76 164 / 0.5);
  box-shadow:
    0 0 26px rgb(234 76 164 / 0.35),
    0 18px 40px rgb(0 0 0 / 0.55);
  -webkit-backdrop-filter: blur(12px);
  backdrop-filter: blur(12px);
}
.screen {
  position: relative;
  /* YouTube asks for a player of at least 200 × 200 */
  height: 200px;
  background: #000;
}
.round {
  display: grid;
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  place-items: center;
  border-radius: 999px;
  background: rgb(255 255 255 / 0.1);
  color: #fff;
}
.round:hover {
  background: rgb(255 255 255 / 0.18);
}
.switch {
  position: relative;
  width: 46px;
  height: 28px;
  flex-shrink: 0;
  border-radius: 999px;
  background: rgb(255 255 255 / 0.18);
  transition: background 0.2s;
}
.switch[aria-checked='true'] {
  background: #ea4ca4;
}
.knob {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 22px;
  height: 22px;
  border-radius: 999px;
  background: #fff;
  transition: translate 0.2s;
}
.switch[aria-checked='true'] .knob {
  translate: 18px 0;
}
@media (prefers-reduced-motion: reduce) {
  .spin {
    animation: none;
  }
}
</style>
