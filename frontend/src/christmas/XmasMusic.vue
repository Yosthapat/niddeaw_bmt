<script setup lang="ts">
/**
 * Christmas music for the season: a small record button in the corner that
 * opens a card with a Christmas classics DJ mix playing in Mixcloud's own
 * small player (nearly two hours). Mixcloud licenses the songs in its
 * mixes, which is what lets a site embed one; the club never hosts a song.
 *
 * The card folds down to the record button with the music still playing
 * (the player stays loaded, just out of sight); tap the record to bring it
 * back. Only the card's ✕ stops the music.
 *
 * Nothing loads from Mixcloud until the button is tapped (a browser will
 * not start sound without a tap anyway), and closing the card stops the
 * music. Once Mixcloud's player is up it is asked to play; where the
 * browser still wants a tap inside the player itself (iPhones, and some
 * desktops), a line in the card says to press its play button. The card also holds the switch for the snow (prefs.ts).
 */
import { onBeforeUnmount, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { snowOn } from './prefs'
import { reducedMotion } from './season'

// Christmas Classics - Back 2 Back, Joe Vinyl (1 h 48 min)
const MIX_URL = 'https://www.mixcloud.com/joevinyl/christmas-classics-back-2-back-favorites/'
const MIX_SRC = `https://www.mixcloud.com/widget/iframe/?feed=${encodeURIComponent(MIX_URL)}&hide_cover=1&mini=1&autoplay=1`
const HIDDEN_KEY = 'niddeaw_xmas_music_hidden'
const WIDGET_API = 'https://widget.mixcloud.com/media/js/widgetApi.js'

interface MixWidget {
  ready: Promise<void>
  play(): void
  togglePlay(): void
  events: { play: { on(fn: () => void): void }; pause: { on(fn: () => void): void }; ended: { on(fn: () => void): void } }
}
declare global {
  interface Window {
    Mixcloud?: { PlayerWidget(frame: HTMLIFrameElement): MixWidget }
  }
}

const { t } = useI18n()
/** The player is loaded (music may be playing). */
const open = ref(false)
/** Folded down to the record button, the player still running out of sight. */
const mini = ref(false)
const playing = ref(false)
const mixReady = ref(false)
/** The player is up but silent: the browser wants a tap on its own button. */
const needsTap = ref(false)
const TAP_HINT_MS = 2500
let hintTimer: ReturnType<typeof setTimeout> | null = null
const mixFrame = ref<HTMLIFrameElement | null>(null)
const showSnowSwitch = !reducedMotion()

function wasHidden(): boolean {
  try {
    return sessionStorage.getItem(HIDDEN_KEY) === '1'
  } catch {
    return false
  }
}
const hidden = ref(wasHidden())

let mix: MixWidget | null = null
let api: Promise<void> | null = null

function loadApi(): Promise<void> {
  api ??= new Promise<void>((resolve, reject) => {
    const s = document.createElement('script')
    s.src = WIDGET_API
    s.async = true
    s.onload = () => resolve()
    s.onerror = () => {
      api = null
      reject(new Error('Mixcloud did not load'))
    }
    document.head.appendChild(s)
  })
  return api
}

/** Mixcloud's player is up: follow its play and pause for the spinning record. */
async function onMixLoad(): Promise<void> {
  const frame = mixFrame.value
  if (!frame) return
  // whatever happens below, if no sound has started by then, say how
  if (hintTimer) clearTimeout(hintTimer)
  hintTimer = setTimeout(() => {
    if (!playing.value && mixFrame.value === frame) needsTap.value = true
  }, TAP_HINT_MS)
  try {
    await loadApi()
    if (!window.Mixcloud || mixFrame.value !== frame) return
    const w = window.Mixcloud.PlayerWidget(frame)
    await w.ready
    if (mixFrame.value !== frame) return
    mix = w
    mixReady.value = true
    w.events.play.on(() => {
      playing.value = true
      needsTap.value = false
    })
    w.events.pause.on(() => (playing.value = false))
    w.events.ended.on(() => (playing.value = false))
    // autoplay=1 in its address is not always honoured: ask outright
    w.play()
  } catch {
    // its own play button still works; only ours stays hidden
  }
}

function toggle(): void {
  mix?.togglePlay()
}

/** Close the card: the player goes, so the music stops with it. */
function close(): void {
  if (hintTimer) clearTimeout(hintTimer)
  hintTimer = null
  needsTap.value = false
  mix = null
  mixReady.value = false
  playing.value = false
  open.value = false
  mini.value = false
}

/** The record button: open the player, or unfold it if it is running folded. */
function openCard(): void {
  open.value = true
  mini.value = false
}

/** The record button's ✕: stop music that is playing folded, else hide the button. */
function pillX(): void {
  if (open.value) close()
  else hide()
}

function hide(): void {
  hidden.value = true
  try {
    sessionStorage.setItem(HIDDEN_KEY, '1')
  } catch {
    // storage blocked: hidden until the next page load
  }
}

onBeforeUnmount(close)
</script>

<template>
  <div v-if="!hidden" class="xmas-music">
    <!-- the card, with Mixcloud's player in it -->
    <!-- Folded, it is moved out of sight rather than removed, so the music
         carries on (visibility, not display: none, keeps the player running). -->
    <section v-if="open" class="card" :class="{ 'card-mini': mini }" :aria-label="t('xmas.music.label')" :aria-hidden="mini || undefined" :inert="mini || undefined">
      <header class="flex items-center gap-3 px-3.5 pt-3 pb-2.5">
        <span class="disc" :class="{ spin: playing }" aria-hidden="true" />
        <span class="min-w-0 flex-1">
          <span class="block truncate font-display text-[15px] font-bold text-white">{{ t('xmas.music.mixTitle') }}</span>
          <span class="block truncate text-xs text-white/60">{{ t('xmas.music.mixBy') }}</span>
        </span>
        <button v-if="mixReady" type="button" class="round" :aria-label="playing ? t('xmas.music.pause') : t('xmas.music.play')" @click="toggle">
          <svg v-if="playing" viewBox="0 0 24 24" fill="currentColor" class="h-5 w-5" aria-hidden="true"><path d="M7 5h3.5v14H7zM13.5 5H17v14h-3.5z" /></svg>
          <svg v-else viewBox="0 0 24 24" fill="currentColor" class="h-5 w-5" aria-hidden="true"><path d="M8 5.5v13l10.5-6.5z" /></svg>
        </button>
        <button type="button" class="round" :aria-label="t('xmas.music.fold')" @click="mini = true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5" aria-hidden="true"><path d="m6 9 6 6 6-6" /></svg>
        </button>
        <button type="button" class="round" :aria-label="t('xmas.music.close')" @click="close">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" class="h-5 w-5" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg>
        </button>
      </header>

      <p v-if="needsTap" class="tap-hint mx-3.5 mb-2 flex items-center gap-2 text-[13px] text-white/90" role="status">
        <svg viewBox="0 0 24 24" fill="currentColor" class="h-4 w-4 shrink-0 text-[#ff7cc6]" aria-hidden="true"><path d="M12 4v12m0 0-5-5m5 5 5-5" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" fill="none" /></svg>
        {{ t('xmas.music.tapPlayer') }}
      </p>
      <div class="mix" :class="{ 'mix-nudge': needsTap }">
        <iframe
          ref="mixFrame"
          :src="MIX_SRC"
          :title="t('xmas.music.mixTitle')"
          width="100%"
          height="60"
          frameborder="0"
          allow="encrypted-media; fullscreen; autoplay; idle-detection; speaker-selection; web-share"
          @load="onMixLoad"
        />
        <a :href="MIX_URL" target="_blank" rel="noopener" class="mt-1.5 block px-3.5 text-right text-[11px] text-white/50 hover:text-white/80">{{ t('xmas.music.onMixcloud') }} ↗</a>
      </div>

      <footer v-if="showSnowSwitch" class="flex items-center justify-between gap-3 px-3.5 py-2.5 text-[13px] text-white/75">
        <span>{{ t('xmas.snow.label') }}</span>
        <button type="button" class="switch" role="switch" :aria-checked="snowOn" @click="snowOn = !snowOn">
          <span class="knob" />
          <span class="sr-only">{{ t('xmas.snow.label') }}</span>
        </button>
      </footer>
    </section>

    <!-- the record button (also what the card folds down to) -->
    <div v-if="!open || mini" class="pill">
      <button type="button" class="pill-main" :aria-label="open ? t('xmas.music.unfold') : t('xmas.music.open')" @click="openCard">
        <span class="disc" :class="{ spin: playing }" aria-hidden="true" />
        <!-- words from 900px; on a phone the record alone, so it covers less -->
        <span class="min-w-0 text-left max-[899px]:hidden">
          <span class="block truncate font-display text-[14px] leading-tight font-bold text-white">{{ t('xmas.music.label') }}</span>
          <span class="block truncate text-[11px] leading-tight text-white/60">{{ playing ? t('xmas.music.playing') : t('xmas.music.tap') }}</span>
        </span>
      </button>
      <button type="button" class="pill-x" :aria-label="open ? t('xmas.music.close') : t('xmas.music.hide')" @click="pillX">
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

.card-mini {
  position: absolute;
  right: 0;
  bottom: 0;
  visibility: hidden;
  pointer-events: none;
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
.mix {
  padding-bottom: 2px;
  border-radius: 10px;
  transition: box-shadow 0.3s;
}
/* pointing at Mixcloud's own play button when the browser wants a tap there */
.mix-nudge {
  box-shadow: 0 0 0 2px #ea4ca4, 0 0 18px rgb(234 76 164 / 0.55);
  animation: mix-nudge 1.6s ease-in-out infinite;
}
@keyframes mix-nudge {
  50% {
    box-shadow: 0 0 0 2px rgb(234 76 164 / 0.4), 0 0 6px rgb(234 76 164 / 0.2);
  }
}
.mix iframe {
  display: block;
  border: 0;
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
  .spin,
  .mix-nudge {
    animation: none;
  }
}
</style>
