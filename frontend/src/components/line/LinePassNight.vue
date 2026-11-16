<script setup lang="ts">
/**
 * Niddeaw Pass › tonight: their last night as a story-sized picture (1080 ×
 * 1920) to share — rating gained, games and wins, the upset of the night
 * and who they won with (backend pass_perks.night). Drawn on a canvas in
 * the page, so it needs no server; shared through the phone's share sheet
 * where there is one, otherwise saved.
 */
import { computed, nextTick, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as lineApi from '@/api/line'
import type { PassFrame, PassNight } from '@/api/line'
import { apiErrorMessage } from '@/api/errors'
import { formatDate } from '@/utils/format'
import type { Locale } from '@/i18n'

const props = defineProps<{ token: string; avatarUrl?: string | null }>()
const { t, locale } = useI18n()

const night = ref<PassNight | null | undefined>(undefined)
const problem = ref('')
const picture = ref('')
const file = ref<File | null>(null)
const canShare = computed(() => !!file.value && typeof navigator.canShare === 'function' && navigator.canShare({ files: [file.value] }))

const W = 1080
const H = 1920
const RING: Record<PassFrame, string[]> = {
  gold: ['#fff3b0', '#f2c14e', '#9a6a12', '#ffe58a'],
  neon: ['#ff4fa6', '#9b6bff', '#ff4fa6', '#ff8fd0'],
  crown: ['#ff8fd0', '#f2c14e', '#ff8fd0', '#f2c14e'],
  moon: ['#f4f6ff', '#aab3cf', '#6c7391', '#e3e8ff'],
  king: ['#7a2bd6', '#f2c14e', '#ff4fa6', '#f2c14e'],
  legend: ['#8ff7ff', '#b88cff', '#ff8fd0', '#ffe58a'],
}

function cssFont(name: string, fallback: string): string {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}
function load(src: string): Promise<HTMLImageElement | null> {
  return new Promise((done) => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => done(img)
    img.onerror = () => done(null)
    img.src = src
  })
}
function rounded(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number): void {
  ctx.beginPath()
  ctx.roundRect(x, y, w, h, r)
}
function wrap(ctx: CanvasRenderingContext2D, text: string, x: number, y: number, max: number, line: number): number {
  // Thai has no spaces between words: break on characters when a line runs over
  let row = ''
  for (const ch of text) {
    if (ctx.measureText(row + ch).width > max && row) {
      ctx.fillText(row, x, y)
      y += line
      row = ''
    }
    row += ch
  }
  ctx.fillText(row, x, y)
  return y + line
}

async function draw(n: PassNight): Promise<void> {
  await document.fonts?.ready
  const display = cssFont('--font-display', 'sans-serif')
  const body = cssFont('--font-body', 'sans-serif')
  const canvas = document.createElement('canvas')
  canvas.width = W
  canvas.height = H
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  // the night sky and the synthwave sun
  const sky = ctx.createLinearGradient(0, 0, 0, H)
  sky.addColorStop(0, '#3b0f5c')
  sky.addColorStop(0.45, '#1a0838')
  sky.addColorStop(1, '#0b0418')
  ctx.fillStyle = sky
  ctx.fillRect(0, 0, W, H)
  const glow = ctx.createRadialGradient(W / 2, 0, 0, W / 2, 0, 900)
  glow.addColorStop(0, 'rgba(255,79,166,0.85)')
  glow.addColorStop(1, 'rgba(255,79,166,0)')
  ctx.fillStyle = glow
  ctx.fillRect(0, 0, W, 900)
  ctx.save()
  ctx.beginPath()
  ctx.arc(W / 2, 640, 340, Math.PI, 0)
  ctx.clip()
  const sun = ctx.createLinearGradient(0, 300, 0, 640)
  sun.addColorStop(0, '#ffd36b')
  sun.addColorStop(1, '#ff4fa6')
  ctx.fillStyle = sun
  for (let y = 300; y < 640; y += 40) ctx.fillRect(0, y, W, 30)
  ctx.restore()
  // the grid running to the horizon
  ctx.strokeStyle = 'rgba(255,79,166,0.55)'
  ctx.lineWidth = 3
  for (let i = 0; i < 6; i++) {
    const y = 640 + i * i * 9 + i * 14
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(W, y)
    ctx.stroke()
  }
  for (let i = -8; i <= 8; i++) {
    ctx.beginPath()
    ctx.moveTo(W / 2 + i * 40, 640)
    ctx.lineTo(W / 2 + i * 220, 960)
    ctx.stroke()
  }
  const cat = await load('/hero/cat-color.webp')
  if (cat) ctx.drawImage(cat, W / 2 - 260, 150, 520, 520)

  ctx.textAlign = 'center'
  ctx.fillStyle = '#ff8fd0'
  ctx.font = `600 34px ${body}`
  ctx.fillText(`NIDDEAW NIGHT · ${formatDate(n.date, locale.value as Locale)}`.toUpperCase(), W / 2, 1030)

  // their picture in their frame, and their name
  const cx = W / 2 - 150
  const cy = 1120
  if (n.frame) {
    const ring = ctx.createConicGradient(0, cx, cy)
    RING[n.frame].forEach((c, i, all) => ring.addColorStop(i / all.length, c))
    ring.addColorStop(1, RING[n.frame][0]!)
    ctx.fillStyle = ring
    ctx.beginPath()
    ctx.arc(cx, cy, 66, 0, Math.PI * 2)
    ctx.fill()
  }
  ctx.save()
  ctx.beginPath()
  ctx.arc(cx, cy, 56, 0, Math.PI * 2)
  ctx.clip()
  const face = props.avatarUrl ? await load(props.avatarUrl) : null
  if (face) {
    ctx.drawImage(face, cx - 56, cy - 56, 112, 112)
  } else {
    ctx.fillStyle = '#3a1230'
    ctx.fillRect(cx - 56, cy - 56, 112, 112)
    ctx.fillStyle = '#ffc6e6'
    ctx.font = `700 52px ${display}`
    ctx.fillText(n.nickname.slice(0, 1).toUpperCase(), cx, cy + 18)
  }
  ctx.restore()
  ctx.textAlign = 'left'
  ctx.fillStyle = '#fff'
  ctx.font = `800 70px ${display}`
  ctx.fillText(n.nickname, cx + 92, cy + 24, 520)

  // the rating the night made
  const gained = n.elo_after - n.elo_before
  ctx.textAlign = 'center'
  ctx.fillStyle = gained >= 0 ? '#7ef0b0' : '#ff8fb0'
  ctx.shadowColor = gained >= 0 ? 'rgba(126,240,176,0.6)' : 'rgba(255,143,176,0.5)'
  ctx.shadowBlur = 40
  ctx.font = `900 170px ${display}`
  ctx.fillText(`${gained >= 0 ? '+' : ''}${gained}`, W / 2, 1360)
  ctx.shadowBlur = 0
  ctx.fillStyle = 'rgba(255,255,255,0.72)'
  ctx.font = `500 36px ${body}`
  ctx.fillText(`ELO ${n.elo_before.toLocaleString('en-US')} → ${n.elo_after.toLocaleString('en-US')}`, W / 2, 1420)

  // games, wins, rate
  const boxes = [
    [String(n.games), t('passPlus.games'), '#fff'],
    [String(n.wins), t('passPlus.wins'), '#7ef0b0'],
    [`${n.games ? Math.round((n.wins / n.games) * 100) : 0}%`, t('passPlus.rate'), '#fff'],
  ]
  boxes.forEach(([big, small, color], i) => {
    const x = 70 + i * 320
    rounded(ctx, x, 1450, 300, 150, 30)
    ctx.fillStyle = 'rgba(255,255,255,0.07)'
    ctx.fill()
    ctx.strokeStyle = 'rgba(255,255,255,0.14)'
    ctx.lineWidth = 2
    ctx.stroke()
    ctx.fillStyle = color!
    ctx.font = `800 64px ${display}`
    ctx.fillText(big!, x + 150, 1536)
    ctx.fillStyle = 'rgba(255,255,255,0.6)'
    ctx.font = `400 28px ${body}`
    ctx.fillText(small!, x + 150, 1580)
  })

  // the upset and the partner
  ctx.textAlign = 'left'
  let y = 1626
  const strip = (text: string, gold: boolean): void => {
    ctx.font = `500 32px ${body}`
    const lines = Math.max(1, Math.ceil(ctx.measureText(text).width / 860))
    const h = 40 + lines * 44
    rounded(ctx, 70, y, W - 140, h, 28)
    ctx.fillStyle = gold ? 'rgba(242,193,78,0.16)' : 'rgba(255,255,255,0.06)'
    ctx.fill()
    ctx.strokeStyle = gold ? 'rgba(242,193,78,0.5)' : 'rgba(255,255,255,0.14)'
    ctx.stroke()
    ctx.fillStyle = gold ? '#ffe8a3' : '#fff'
    wrap(ctx, text, 100, y + 56, 880, 44)
    y += h + 18
  }
  if (n.upset) {
    strip(
      t('passPlus.upsetLine', { names: n.upset.rivals.map((r) => r.nickname).join(' & '), pct: Math.round(n.upset.odds * 100) }),
      true,
    )
  }
  if (n.partner && y < 1760) {
    strip(t('passPlus.partnerLine', { name: n.partner.player.nickname, wins: n.partner.wins, games: n.partner.games }), false)
  }

  // the club
  ctx.fillStyle = '#fff'
  ctx.font = `700 34px ${display}`
  ctx.fillText('นิดเดียว BMT', 70, H - 44)
  ctx.textAlign = 'right'
  ctx.fillStyle = 'rgba(255,255,255,0.6)'
  ctx.font = `400 30px ${body}`
  ctx.fillText('niddeaw.fyi', W - 70, H - 44)

  picture.value = canvas.toDataURL('image/png')
  const blob = await new Promise<Blob | null>((done) => canvas.toBlob(done, 'image/png'))
  if (blob) file.value = new File([blob], `niddeaw-${n.date}.png`, { type: 'image/png' })
}

onMounted(async () => {
  try {
    night.value = await lineApi.getPassNight(props.token)
    if (night.value) {
      await nextTick()
      await draw(night.value)
    }
  } catch (e) {
    problem.value = apiErrorMessage(e, t('passPlus.nightFailed'))
  }
})

async function share(): Promise<void> {
  if (!file.value) return
  try {
    await navigator.share({ files: [file.value], text: 'นิดเดียว BMT · niddeaw.fyi' })
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
    <template v-if="night && picture">
      <img :src="picture" :alt="t('passPlus.nightTitle')" class="story mx-auto w-full max-w-[320px]" />
      <div class="flex gap-2.5">
        <button v-if="canShare" type="button" class="flex-1 rounded-full bg-[#06c755] py-3 font-bold" @click="share">{{ t('passPlus.share') }}</button>
        <a :href="picture" :download="file?.name ?? 'niddeaw.png'" class="flex-1 rounded-full border border-white/20 bg-white/10 py-3 text-center font-bold">
          {{ t('passPlus.save') }}
        </a>
      </div>
      <p class="text-center text-[11px] text-white/45">{{ t('passPlus.saveHint') }}</p>
    </template>
  </section>
</template>

<style scoped>
.story {
  aspect-ratio: 9 / 16;
  border-radius: 22px;
  box-shadow: 0 30px 60px -20px rgb(0 0 0 / 0.9);
}
</style>
