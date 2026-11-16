<script setup lang="ts">
/**
 * Niddeaw Pass › tonight: their last night as a picture to share, with
 * their member card big in the middle — their photo (or tier mascot), the
 * card face they wear (foil or diamond), then the rating the night made,
 * games and wins, the upset of the night and who they won with (backend
 * pass_perks.night).
 *
 * Two sizes: a Story (1080 × 1920) and a square post (1080 × 1080). Drawn
 * on a canvas in the page, so it needs no server. A website can't hand a
 * picture straight to Instagram, Facebook or TikTok; the phone's share
 * sheet can, so each app's button opens it with a note on where that app
 * sits in the sheet. Saving works everywhere.
 */
import { computed, nextTick, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as lineApi from '@/api/line'
import type { PassCard, PassNight } from '@/api/line'
import type { EloTier } from '@/types'
import { apiErrorMessage } from '@/api/errors'
import { formatDate } from '@/utils/format'
import { TIER_CARD } from '@/utils/tierCard'
import { tierMeta } from '@/composables/useEloTier'
import type { Locale } from '@/i18n'

const props = defineProps<{ token: string; avatarUrl?: string | null; tier?: string; code?: string; card?: PassCard | null }>()
const { t, locale } = useI18n()

type Size = 'story' | 'square'
type App = 'instagram' | 'facebook' | 'tiktok'
const night = ref<PassNight | null | undefined>(undefined)
const problem = ref('')
const size = ref<Size>('story')
const pictures = ref<Record<Size, string>>({ story: '', square: '' })
const files = ref<Record<Size, File | null>>({ story: null, square: null })
const hint = ref<App | null>(null)
const file = computed(() => files.value[size.value])
const canShare = computed(
  () => !!file.value && typeof navigator.canShare === 'function' && navigator.canShare({ files: [file.value] }),
)

const W = 1080
const DIMS: Record<Size, number> = { story: 1920, square: 1080 }
const tier = computed<EloTier>(() => (props.tier && props.tier in TIER_CARD ? (props.tier as EloTier) : 'beer'))

function cssFont(name: string, fallback: string): string {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}
function load(src: string): Promise<HTMLImageElement | null> {
  // crossOrigin: a photo from another host only draws if that host allows
  // it, or the canvas could not be saved; when it doesn't, the mascot.
  return new Promise((done) => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => done(img)
    img.onerror = () => done(null)
    img.src = src
  })
}
function round(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number): void {
  ctx.beginPath()
  ctx.roundRect(x, y, w, h, r)
}
function wrap(ctx: CanvasRenderingContext2D, text: string, x: number, y: number, max: number, line: number): number {
  // Thai has no spaces between words: break on characters when a line runs over
  let row = ''
  let lines = 0
  for (const ch of text) {
    if (ctx.measureText(row + ch).width > max && row) {
      ctx.fillText(row, x, y + lines * line)
      lines++
      row = ''
    }
    row += ch
  }
  ctx.fillText(row, x, y + lines * line)
  return lines + 1
}
function linesOf(ctx: CanvasRenderingContext2D, text: string, max: number): number {
  return Math.max(1, Math.ceil(ctx.measureText(text).width / max))
}

interface Art {
  photo: HTMLImageElement | null
  mascot: HTMLImageElement | null
  display: string
  body: string
}

/** The member card, as on their profile: frame, header, photo, name. */
function drawCard(ctx: CanvasRenderingContext2D, n: PassNight, art: Art, x: number, y: number, w: number): number {
  const style = TIER_CARD[tier.value]
  const pad = w * 0.04
  const head = w * 0.1
  const photoW = w - pad * 2
  const photoH = photoW * 0.92
  const nameH = w * 0.2
  const h = pad + head + photoH + nameH + pad * 0.6
  const r = w * 0.06

  // the frame: the pass face if worn, else the tier's metal
  ctx.save()
  let edge: CanvasGradient
  if (props.card) {
    edge = ctx.createConicGradient(Math.PI * 1.15, x + w / 2, y + h / 2)
    const stops =
      props.card === 'diamond'
        ? ['#ffffff', '#8ff7ff', '#b88cff', '#e8fbff', '#8fffc1', '#ff8fd0', '#ffffff']
        : ['#fff3b0', '#f2c14e', '#ff8fd0', '#8ff7ff', '#b88cff', '#ffe58a', '#f2c14e', '#fff3b0']
    stops.forEach((c, i) => edge.addColorStop(i / (stops.length - 1), c))
    ctx.shadowColor = props.card === 'diamond' ? 'rgba(143,247,255,0.55)' : 'rgba(242,193,78,0.55)'
  } else {
    edge = ctx.createLinearGradient(x, y, x + w, y + h)
    edge.addColorStop(0, style.light)
    edge.addColorStop(0.42, style.mid)
    edge.addColorStop(1, style.dark)
    ctx.shadowColor = 'rgba(234,76,164,0.45)'
  }
  ctx.shadowBlur = w * 0.08
  ctx.fillStyle = edge
  round(ctx, x, y, w, h, r)
  ctx.fill()
  ctx.restore()

  const b = w * 0.012
  const inner = ctx.createRadialGradient(x + w / 2, y, 0, x + w / 2, y, h)
  inner.addColorStop(0, '#2a1450')
  inner.addColorStop(0.6, '#120a24')
  ctx.fillStyle = inner
  round(ctx, x + b, y + b, w - b * 2, h - b * 2, r - b)
  ctx.fill()

  // header: member code and the rating after the night
  ctx.textBaseline = 'middle'
  ctx.textAlign = 'left'
  ctx.fillStyle = 'rgba(255,255,255,0.65)'
  ctx.font = `600 ${w * 0.04}px ${art.display}`
  ctx.fillText(props.code ?? '', x + pad * 1.2, y + pad + head / 2)
  const elo = `ELO ${n.elo_after.toLocaleString('en-US')}`
  ctx.font = `700 ${w * 0.042}px ${art.display}`
  const ew = ctx.measureText(elo).width + w * 0.06
  round(ctx, x + w - pad - ew, y + pad + head * 0.15, ew, head * 0.7, head * 0.35)
  ctx.fillStyle = 'rgba(0,0,0,0.35)'
  ctx.fill()
  ctx.strokeStyle = 'rgba(255,255,255,0.18)'
  ctx.lineWidth = w * 0.003
  ctx.stroke()
  ctx.fillStyle = '#fff'
  ctx.textAlign = 'center'
  ctx.fillText(elo, x + w - pad - ew / 2, y + pad + head / 2)

  // the photo, or the tier's mascot on the tier's colour
  const px = x + pad
  const py = y + pad + head
  ctx.save()
  round(ctx, px, py, photoW, photoH, w * 0.035)
  ctx.clip()
  const glow = ctx.createRadialGradient(px + photoW / 2, py + photoH * 0.38, 0, px + photoW / 2, py + photoH * 0.38, photoW * 0.75)
  glow.addColorStop(0, style.mid)
  glow.addColorStop(1, '#1a0d33')
  ctx.fillStyle = glow
  ctx.fillRect(px, py, photoW, photoH)
  if (art.photo) {
    // cover: fill the box, crop the overflow, keep the face in the upper half
    const s = Math.max(photoW / art.photo.width, photoH / art.photo.height)
    const dw = art.photo.width * s
    const dh = art.photo.height * s
    ctx.drawImage(art.photo, px + (photoW - dw) / 2, py + (photoH - dh) * 0.35, dw, dh)
  } else if (art.mascot) {
    const m = photoW * 0.64
    ctx.drawImage(art.mascot, px + (photoW - m) / 2, py + (photoH - m) / 2, m, m)
  }
  if (props.card) {
    // the foil's light across the picture
    const sheen = ctx.createLinearGradient(px, py, px + photoW, py + photoH)
    sheen.addColorStop(0.35, 'rgba(255,255,255,0)')
    sheen.addColorStop(0.47, 'rgba(255,255,255,0.22)')
    sheen.addColorStop(0.53, 'rgba(143,247,255,0.16)')
    sheen.addColorStop(0.65, 'rgba(255,255,255,0)')
    ctx.fillStyle = sheen
    ctx.fillRect(px, py, photoW, photoH)
  }
  ctx.restore()

  // tier chip on the photo
  const label = tierMeta(tier.value).label.toUpperCase()
  ctx.font = `700 ${w * 0.034}px ${art.display}`
  const cw = ctx.measureText(label).width + w * 0.05
  round(ctx, px + photoW - cw - w * 0.02, py + w * 0.02, cw, w * 0.055, w * 0.03)
  ctx.fillStyle = 'rgba(0,0,0,0.55)'
  ctx.fill()
  ctx.fillStyle = style.text
  ctx.fillText(label, px + photoW - cw / 2 - w * 0.02, py + w * 0.02 + w * 0.0275)

  // name and tier
  ctx.textAlign = 'left'
  ctx.textBaseline = 'alphabetic'
  ctx.fillStyle = '#fff'
  ctx.font = `800 ${w * 0.085}px ${art.display}`
  ctx.fillText(n.nickname, px + w * 0.005, py + photoH + nameH * 0.52, photoW)
  ctx.fillStyle = 'rgba(255,255,255,0.65)'
  ctx.font = `400 ${w * 0.04}px ${art.body}`
  ctx.fillText(tierMeta(tier.value).label, px + w * 0.005, py + photoH + nameH * 0.85)

  // the pass tag on the frame
  if (props.card) {
    const tag = props.card === 'diamond' ? '◆ LEGEND' : '✦ PASS'
    ctx.font = `800 ${w * 0.034}px ${art.display}`
    const tw = ctx.measureText(tag).width + w * 0.08
    const tx = x + (w - tw) / 2
    const ty = y - w * 0.03
    const g = ctx.createLinearGradient(tx, 0, tx + tw, 0)
    if (props.card === 'diamond') {
      g.addColorStop(0, '#e8fbff')
      g.addColorStop(0.5, '#8ff7ff')
      g.addColorStop(1, '#d6c2ff')
    } else {
      g.addColorStop(0, '#ffe58a')
      g.addColorStop(1, '#f2c14e')
    }
    round(ctx, tx, ty, tw, w * 0.065, w * 0.033)
    ctx.fillStyle = g
    ctx.fill()
    ctx.fillStyle = props.card === 'diamond' ? '#12203a' : '#3a2500'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(tag, tx + tw / 2, ty + w * 0.0325)
  }
  ctx.textBaseline = 'alphabetic'
  return h
}

/** The synthwave sky, the sun and the grid, under everything. */
function drawSky(ctx: CanvasRenderingContext2D, H: number, sunX: number, sunY: number, sunR: number, grid: boolean): void {
  const sky = ctx.createLinearGradient(0, 0, 0, H)
  sky.addColorStop(0, '#3b0f5c')
  sky.addColorStop(0.45, '#1a0838')
  sky.addColorStop(1, '#0b0418')
  ctx.fillStyle = sky
  ctx.fillRect(0, 0, W, H)
  const glow = ctx.createRadialGradient(W / 2, 0, 0, W / 2, 0, H * 0.5)
  glow.addColorStop(0, 'rgba(255,79,166,0.8)')
  glow.addColorStop(1, 'rgba(255,79,166,0)')
  ctx.fillStyle = glow
  ctx.fillRect(0, 0, W, H * 0.5)
  ctx.save()
  ctx.beginPath()
  ctx.arc(sunX, sunY, sunR, Math.PI, 0)
  ctx.clip()
  const sun = ctx.createLinearGradient(0, sunY - sunR, 0, sunY)
  sun.addColorStop(0, '#ffd36b')
  sun.addColorStop(1, '#ff4fa6')
  ctx.fillStyle = sun
  for (let y = sunY - sunR; y < sunY; y += sunR / 8) ctx.fillRect(0, y, W, sunR / 11)
  ctx.restore()
  if (!grid) return
  ctx.strokeStyle = 'rgba(255,79,166,0.45)'
  ctx.lineWidth = 3
  for (let i = 0; i < 6; i++) {
    const y = sunY + i * i * 9 + i * 14
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(W, y)
    ctx.stroke()
  }
  for (let i = -8; i <= 8; i++) {
    ctx.beginPath()
    ctx.moveTo(W / 2 + i * 40, sunY)
    ctx.lineTo(W / 2 + i * 220, sunY + 320)
    ctx.stroke()
  }
}

/** +ELO, then games / wins / rate boxes; returns the y under them. */
function drawNumbers(ctx: CanvasRenderingContext2D, n: PassNight, art: Art, cx: number, y: number, width: number, big: number): number {
  const gained = n.elo_after - n.elo_before
  ctx.textAlign = 'center'
  ctx.fillStyle = gained >= 0 ? '#7ef0b0' : '#ff8fb0'
  ctx.shadowColor = gained >= 0 ? 'rgba(126,240,176,0.6)' : 'rgba(255,143,176,0.5)'
  ctx.shadowBlur = 40
  ctx.font = `900 ${big}px ${art.display}`
  ctx.fillText(`${gained >= 0 ? '+' : ''}${gained}`, cx, y + big * 0.85)
  ctx.shadowBlur = 0
  ctx.fillStyle = 'rgba(255,255,255,0.72)'
  ctx.font = `500 ${big * 0.22}px ${art.body}`
  ctx.fillText(`ELO ${n.elo_before.toLocaleString('en-US')} → ${n.elo_after.toLocaleString('en-US')}`, cx, y + big * 1.2)

  const top = y + big * 1.42
  const gap = 18
  const bw = (width - gap * 2) / 3
  const bh = big * 0.85
  const boxes: [string, string, string][] = [
    [String(n.games), t('passPlus.games'), '#fff'],
    [String(n.wins), t('passPlus.wins'), '#7ef0b0'],
    [`${n.games ? Math.round((n.wins / n.games) * 100) : 0}%`, t('passPlus.rate'), '#fff'],
  ]
  boxes.forEach(([value, label, color], i) => {
    const bx = cx - width / 2 + i * (bw + gap)
    round(ctx, bx, top, bw, bh, 26)
    ctx.fillStyle = 'rgba(255,255,255,0.07)'
    ctx.fill()
    ctx.strokeStyle = 'rgba(255,255,255,0.14)'
    ctx.lineWidth = 2
    ctx.stroke()
    ctx.fillStyle = color
    ctx.font = `800 ${bh * 0.42}px ${art.display}`
    ctx.fillText(value, bx + bw / 2, top + bh * 0.55)
    ctx.fillStyle = 'rgba(255,255,255,0.6)'
    ctx.font = `400 ${bh * 0.19}px ${art.body}`
    ctx.fillText(label, bx + bw / 2, top + bh * 0.84)
  })
  return top + bh
}

/** The upset and the partner, as strips; returns the y under them. */
function drawStrips(ctx: CanvasRenderingContext2D, n: PassNight, art: Art, x: number, y: number, width: number, font: number, bottom: number): number {
  const strip = (text: string, gold: boolean): void => {
    ctx.font = `500 ${font}px ${art.body}`
    const lines = linesOf(ctx, text, width - 60)
    const h = font * 1.25 + lines * font * 1.38
    if (y + h > bottom) return
    round(ctx, x, y, width, h, 24)
    ctx.fillStyle = gold ? 'rgba(242,193,78,0.16)' : 'rgba(255,255,255,0.06)'
    ctx.fill()
    ctx.strokeStyle = gold ? 'rgba(242,193,78,0.5)' : 'rgba(255,255,255,0.14)'
    ctx.lineWidth = 2
    ctx.stroke()
    ctx.fillStyle = gold ? '#ffe8a3' : '#fff'
    ctx.textAlign = 'left'
    wrap(ctx, text, x + 30, y + font * 1.55, width - 60, font * 1.38)
    y += h + 16
  }
  if (n.upset) {
    strip(t('passPlus.upsetLine', { names: n.upset.rivals.map((r) => r.nickname).join(' & '), pct: Math.round(n.upset.odds * 100) }), true)
  }
  if (n.partner) strip(t('passPlus.partnerLine', { name: n.partner.player.nickname, wins: n.partner.wins, games: n.partner.games }), false)
  return y
}

function drawFooter(ctx: CanvasRenderingContext2D, art: Art, H: number): void {
  ctx.textAlign = 'left'
  ctx.fillStyle = '#fff'
  ctx.font = `700 32px ${art.display}`
  ctx.fillText('นิดเดียว BMT', 64, H - 40)
  ctx.textAlign = 'right'
  ctx.fillStyle = 'rgba(255,255,255,0.6)'
  ctx.font = `400 28px ${art.body}`
  ctx.fillText('niddeaw.fyi', W - 64, H - 40)
}

function drawTitle(ctx: CanvasRenderingContext2D, n: PassNight, art: Art, x: number, y: number, align: CanvasTextAlign): void {
  ctx.textAlign = align
  ctx.fillStyle = '#ff8fd0'
  ctx.font = `700 32px ${art.body}`
  ctx.fillText(`NIDDEAW NIGHT · ${formatDate(n.date, locale.value as Locale)}`.toUpperCase(), x, y)
}

async function render(n: PassNight, which: Size, art: Art): Promise<void> {
  const H = DIMS[which]
  const canvas = document.createElement('canvas')
  canvas.width = W
  canvas.height = H
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  if (which === 'story') {
    drawSky(ctx, H, W / 2, 640, 360, true)
    drawTitle(ctx, n, art, W / 2, 140, 'center')
    const ch = drawCard(ctx, n, art, 170, 230, 740)
    const under = drawNumbers(ctx, n, art, W / 2, 230 + ch + 50, 940, 130)
    drawStrips(ctx, n, art, 70, under + 36, 940, 30, H - 100)
  } else {
    drawSky(ctx, H, 284, 560, 330, false)
    drawTitle(ctx, n, art, 64, 92, 'left')
    const ch = drawCard(ctx, n, art, 64, 150, 440)
    drawNumbers(ctx, n, art, 790, 190, 450, 120)
    drawStrips(ctx, n, art, 64, 150 + ch + 40, W - 128, 27, H - 90)
  }
  drawFooter(ctx, art, H)
  pictures.value[which] = canvas.toDataURL('image/png')
  const blob = await new Promise<Blob | null>((done) => canvas.toBlob(done, 'image/png'))
  if (blob) files.value[which] = new File([blob], `niddeaw-${n.date}-${which}.png`, { type: 'image/png' })
}

onMounted(async () => {
  try {
    night.value = await lineApi.getPassNight(props.token)
    if (!night.value) return
    await nextTick()
    await document.fonts?.ready
    const art: Art = {
      photo: props.avatarUrl ? await load(props.avatarUrl) : null,
      mascot: await load(`/tiers/${tier.value}.webp`),
      display: cssFont('--font-display', 'sans-serif'),
      body: cssFont('--font-body', 'sans-serif'),
    }
    await render(night.value, 'story', art)
    await render(night.value, 'square', art)
  } catch (e) {
    problem.value = apiErrorMessage(e, t('passPlus.nightFailed'))
  }
})

async function share(app: App): Promise<void> {
  if (!file.value) return
  hint.value = app
  try {
    await navigator.share({ files: [file.value] })
  } catch {
    // closed the sheet: nothing to do
  }
}
</script>

<template>
  <section class="flex flex-col gap-3">
    <p class="text-xs text-white/55">{{ t('passPlus.nightSub') }}</p>
    <p v-if="night === undefined && !problem" class="text-sm text-white/60">{{ t('common.loading') }}</p>
    <p v-if="problem" role="alert" class="text-sm text-status-error">{{ problem }}</p>
    <p v-if="night === null" class="rounded-2xl border border-white/12 bg-white/5 p-4 text-sm text-white/65">{{ t('passPlus.nightNone') }}</p>
    <template v-if="night && pictures[size]">
      <div class="sizes" role="tablist">
        <button
          v-for="s in (['story', 'square'] as const)"
          :key="s"
          type="button"
          role="tab"
          :aria-selected="size === s"
          :class="{ on: size === s }"
          @click="size = s"
        >
          {{ t(`passPlus.size.${s}`) }}
        </button>
      </div>
      <img :src="pictures[size]" :alt="t('passPlus.nightTitle')" class="pic mx-auto w-full" :class="size" />
      <template v-if="canShare">
        <p class="text-center text-xs text-white/60">{{ t('passPlus.shareTo') }}</p>
        <div class="grid grid-cols-3 gap-2">
          <button type="button" class="app ig" @click="share('instagram')">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <rect x="3" y="3" width="18" height="18" rx="5" />
              <circle cx="12" cy="12" r="4.2" />
              <circle cx="17.3" cy="6.7" r="1.1" fill="currentColor" stroke="none" />
            </svg>
            Instagram
          </button>
          <button type="button" class="app fb" @click="share('facebook')">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden="true">
              <path d="M13.5 21v-7.5h2.6l.4-3h-3V8.6c0-.9.3-1.5 1.5-1.5h1.6V4.4c-.3 0-1.2-.1-2.3-.1-2.3 0-3.9 1.4-3.9 4v2.2H7.8v3h2.6V21h3.1Z" />
            </svg>
            Facebook
          </button>
          <button type="button" class="app tt" @click="share('tiktok')">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden="true">
              <path d="M16.6 3h-3.1v12.2a2.7 2.7 0 1 1-2.7-2.7c.3 0 .6 0 .8.1V9.4a5.9 5.9 0 1 0 5 5.8V9.1a7.6 7.6 0 0 0 4.4 1.4V7.4c-2.4 0-4.4-2-4.4-4.4Z" />
            </svg>
            TikTok
          </button>
        </div>
        <p v-if="hint" class="rounded-xl border border-white/12 bg-white/5 p-2.5 text-center text-[11.5px] leading-relaxed text-white/75" role="status">
          {{ t('passPlus.shareHint', { app: t(`passPlus.app.${hint}`) }) }}
        </p>
      </template>
      <a :href="pictures[size]" :download="file?.name ?? 'niddeaw.png'" class="rounded-full border border-white/20 bg-white/10 py-3 text-center font-bold">
        {{ t('passPlus.save') }}
      </a>
      <p class="text-center text-[11px] text-white/45">{{ t('passPlus.saveHint') }}</p>
    </template>
  </section>
</template>

<style scoped>
.sizes {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
  padding: 4px;
  border: 1px solid rgb(255 255 255 / 0.1);
  border-radius: 999px;
  background: rgb(0 0 0 / 0.3);
}
.sizes button {
  min-height: 34px;
  border-radius: 999px;
  color: rgb(255 255 255 / 0.65);
  font-size: 12.5px;
  font-weight: 600;
}
.sizes button.on {
  background: #ea4ca4;
  color: #fff;
}
.pic {
  border-radius: 22px;
  box-shadow: 0 30px 60px -20px rgb(0 0 0 / 0.9);
}
.pic.story {
  max-width: 320px;
  aspect-ratio: 9 / 16;
}
.pic.square {
  max-width: 360px;
  aspect-ratio: 1;
}
.app {
  display: flex;
  min-height: 48px;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border-radius: 14px;
  color: #fff;
  font-size: 12.5px;
  font-weight: 700;
}
.app.ig {
  background: linear-gradient(45deg, #f9ce34, #ee2a7b 45%, #6228d7);
}
.app.fb {
  background: #1877f2;
}
.app.tt {
  border: 1px solid rgb(255 255 255 / 0.2);
  background: #000;
  box-shadow:
    -2px 0 0 #25f4ee inset,
    2px 0 0 #fe2c55 inset;
}
</style>
