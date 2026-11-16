/**
 * A picture to post: "we're in" for a confirmed team, or a champion's card.
 * Drawn on a canvas in the page — 1080×1350, the size a phone's story or
 * feed takes — in the tournament's own look: the night sky, the sun, the
 * neon floor, the level's mascots, the two players' avatars. Then shared
 * through the phone's own share sheet, or saved where there is none.
 */
import type { EloTier } from '@/types'

export interface CardPlayer {
  nickname: string
  avatar_url: string | null
}

export interface ShareCardInput {
  kind: 'entered' | 'champion'
  eyebrow: string
  title: string
  team: string
  players: CardPlayer[]
  level: string
  tiers: EloTier[]
  footer: string
}

const W = 1080
const H = 1350

function load(src: string): Promise<HTMLImageElement | null> {
  return new Promise((resolve) => {
    const img = new Image()
    // Avatars live on Supabase storage: anonymous CORS keeps the canvas exportable.
    img.crossOrigin = 'anonymous'
    img.onload = () => resolve(img)
    img.onerror = () => resolve(null)
    img.src = src
  })
}

function fit(ctx: CanvasRenderingContext2D, text: string, font: (px: number) => string, start: number, max: number): void {
  let px = start
  ctx.font = font(px)
  while (ctx.measureText(text).width > max && px > 24) {
    px -= 4
    ctx.font = font(px)
  }
}

function background(ctx: CanvasRenderingContext2D, champion: boolean): void {
  const sky = ctx.createRadialGradient(W / 2, H * 0.22, 40, W / 2, H * 0.3, H * 0.9)
  sky.addColorStop(0, champion ? '#7a3a1a' : '#6a1f8f')
  sky.addColorStop(0.45, '#2a0d4e')
  sky.addColorStop(1, '#0a0416')
  ctx.fillStyle = sky
  ctx.fillRect(0, 0, W, H)
  // the sun
  const sun = ctx.createLinearGradient(0, 180, 0, 820)
  sun.addColorStop(0, '#ffe14d')
  sun.addColorStop(0.55, '#ff6cc0')
  sun.addColorStop(1, '#9b2cff')
  ctx.globalAlpha = 0.34
  ctx.fillStyle = sun
  ctx.beginPath()
  ctx.arc(W / 2, 500, 320, 0, Math.PI * 2)
  ctx.fill()
  ctx.globalAlpha = 1
  // the neon floor: lines running to a vanishing point
  ctx.strokeStyle = 'rgba(255,108,192,0.38)'
  ctx.lineWidth = 2
  const horizon = H * 0.86
  for (let i = -12; i <= 12; i++) {
    ctx.beginPath()
    ctx.moveTo(W / 2 + i * 40, horizon)
    ctx.lineTo(W / 2 + i * 220, H)
    ctx.stroke()
  }
  for (let k = 0; k < 9; k++) {
    const y = horizon + (H - horizon) * Math.pow(k / 8, 1.8)
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(W, y)
    ctx.stroke()
  }
  const fade = ctx.createLinearGradient(0, H * 0.88, 0, H)
  fade.addColorStop(0, 'rgba(10,4,22,0)')
  fade.addColorStop(1, 'rgba(10,4,22,0.95)')
  ctx.fillStyle = fade
  ctx.fillRect(0, H * 0.88, W, H * 0.12)
}

function trophy(ctx: CanvasRenderingContext2D, cx: number, top: number, size: number): void {
  const s = size / 200
  ctx.save()
  ctx.translate(cx - 100 * s, top)
  ctx.scale(s, s)
  const gold = ctx.createLinearGradient(0, 0, 200, 200)
  gold.addColorStop(0, '#fff3a8')
  gold.addColorStop(0.45, '#ffcf3f')
  gold.addColorStop(1, '#b8740a')
  ctx.fillStyle = gold
  ctx.beginPath()
  ctx.moveTo(52, 20)
  ctx.lineTo(148, 20)
  ctx.lineTo(148, 58)
  ctx.bezierCurveTo(148, 92, 126, 114, 100, 114)
  ctx.bezierCurveTo(74, 114, 52, 92, 52, 58)
  ctx.closePath()
  ctx.fill()
  ctx.strokeStyle = '#ffcf3f'
  ctx.lineWidth = 9
  ctx.lineCap = 'round'
  ctx.beginPath()
  ctx.moveTo(52, 32)
  ctx.lineTo(28, 32)
  ctx.bezierCurveTo(28, 62, 40, 76, 58, 78)
  ctx.moveTo(148, 32)
  ctx.lineTo(172, 32)
  ctx.bezierCurveTo(172, 62, 160, 76, 142, 78)
  ctx.stroke()
  ctx.fillStyle = '#e0a21c'
  ctx.fillRect(90, 114, 20, 30)
  ctx.fillStyle = '#ffcf3f'
  ctx.fillRect(64, 144, 72, 16)
  ctx.restore()
}

async function avatar(ctx: CanvasRenderingContext2D, p: CardPlayer, cx: number, cy: number, r: number): Promise<void> {
  ctx.save()
  ctx.beginPath()
  ctx.arc(cx, cy, r, 0, Math.PI * 2)
  ctx.closePath()
  ctx.fillStyle = '#2a1450'
  ctx.fill()
  const img = p.avatar_url ? await load(p.avatar_url) : null
  if (img) {
    ctx.clip()
    const side = Math.min(img.width, img.height)
    ctx.drawImage(img, (img.width - side) / 2, (img.height - side) / 2, side, side, cx - r, cy - r, r * 2, r * 2)
  } else {
    ctx.fillStyle = '#ff9fd6'
    ctx.font = `700 ${Math.round(r)}px "Chakra Petch", sans-serif`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText((p.nickname[0] ?? '?').toUpperCase(), cx, cy + 4)
  }
  ctx.restore()
  ctx.lineWidth = 8
  ctx.strokeStyle = '#ff6cc0'
  ctx.beginPath()
  ctx.arc(cx, cy, r, 0, Math.PI * 2)
  ctx.stroke()
}

export async function drawShareCard(input: ShareCardInput): Promise<Blob> {
  await Promise.all([
    document.fonts.load('700 80px "Chakra Petch"'),
    document.fonts.load('500 40px "Mitr"'),
    document.fonts.load('600 40px "Mitr"'),
  ]).catch(() => undefined)
  const canvas = document.createElement('canvas')
  canvas.width = W
  canvas.height = H
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('no canvas')
  const champion = input.kind === 'champion'
  background(ctx, champion)
  ctx.textAlign = 'center'
  ctx.textBaseline = 'alphabetic'

  // the eyebrow pill
  ctx.font = '600 40px "Mitr", sans-serif'
  const pillW = ctx.measureText(input.eyebrow).width + 80
  ctx.strokeStyle = '#ffe14d'
  ctx.lineWidth = 4
  ctx.beginPath()
  ctx.roundRect(W / 2 - pillW / 2, 92, pillW, 76, 38)
  ctx.stroke()
  ctx.fillStyle = '#ffe14d'
  ctx.fillText(input.eyebrow, W / 2, 146)

  // the event
  ctx.shadowColor = 'rgba(255,108,192,0.85)'
  ctx.shadowBlur = 30
  ctx.fillStyle = '#fff'
  fit(ctx, input.title, (px) => `700 ${px}px "Chakra Petch", sans-serif`, 104, W - 120)
  ctx.fillText(input.title, W / 2, 290)
  ctx.shadowBlur = 0

  // a trophy for a champion, the level's mascots for a team that's in
  if (champion) {
    trophy(ctx, W / 2, 350, 300)
  } else {
    const imgs = (await Promise.all(input.tiers.map((t) => load(`/tiers/${t}.webp`)))).filter((x): x is HTMLImageElement => !!x)
    const size = imgs.length > 1 ? 230 : 280
    const gap = -40
    const total = imgs.length * size + (imgs.length - 1) * gap
    imgs.forEach((img, i) => ctx.drawImage(img, W / 2 - total / 2 + i * (size + gap), 340, size, size))
  }

  // the two players
  const r = 92
  const pair = input.players.slice(0, 2)
  const xs = pair.length === 2 ? [W / 2 - 150, W / 2 + 150] : [W / 2]
  for (let i = 0; i < pair.length; i++) {
    await avatar(ctx, pair[i], xs[i], 760, r)
    ctx.fillStyle = '#fff'
    fit(ctx, pair[i].nickname, (px) => `500 ${px}px "Mitr", sans-serif`, 42, 280)
    ctx.fillText(pair[i].nickname, xs[i], 760 + r + 62)
  }

  // the team and its level
  ctx.fillStyle = champion ? '#ffe14d' : '#fff'
  fit(ctx, input.team, (px) => `700 ${px}px "Chakra Petch", sans-serif`, 92, W - 140)
  ctx.fillText(input.team, W / 2, 1060)
  ctx.fillStyle = '#ff9fd6'
  ctx.font = '500 40px "Mitr", sans-serif'
  ctx.fillText(input.level, W / 2, 1120)

  ctx.fillStyle = 'rgba(255,255,255,0.7)'
  fit(ctx, input.footer, (px) => `400 ${px}px "Mitr", sans-serif`, 32, W - 160)
  ctx.fillText(input.footer, W / 2, 1270)

  return new Promise((resolve, reject) => canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('no image'))), 'image/png'))
}

/** The phone's share sheet when it takes files; else save the picture. */
export async function shareImage(blob: Blob, fileName: string, text: string): Promise<'shared' | 'saved'> {
  const file = new File([blob], fileName, { type: 'image/png' })
  if (navigator.canShare?.({ files: [file] })) {
    try {
      await navigator.share({ files: [file], text })
      return 'shared'
    } catch {
      /* cancelled: fall through and save it */
    }
  }
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = fileName
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 10_000)
  return 'saved'
}
