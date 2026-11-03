<script setup lang="ts">
/**
 * The club's QR card: a pink card, the code drawn as round dots with
 * rounded corner squares, the crowned cat in the middle, and a dark label
 * underneath — the amount and whose account it is, for paying; a caption
 * for check-in.
 *
 * The code itself comes from the server (qr_modules: rows of 0/1, error
 * correction H), so it is exactly the QR the plain image would have been;
 * only its look changes. H is what lets the cat sit on top of the middle:
 * the code still reads with up to ~30% of it hidden, and the cat covers
 * well under a tenth.
 *
 * Drawn on a canvas and shown as an <img>, so a long press saves it (what
 * LINE's browser offers) and "save" downloads or shares the same picture.
 */
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { money } from '@/utils/format'

const props = withDefaults(
  defineProps<{
    modules: string[]
    amount?: number | null
    accountName?: string | null
    caption?: string | null
    alt: string
    saveable?: boolean
    fileName?: string
  }>(),
  { amount: null, accountName: null, caption: null, saveable: false, fileName: 'niddeaw-qr.png' },
)
const { t } = useI18n()

const PINK = '#f4a6c8'
const INK = '#231f26'
const LABEL_TEXT = '#ffb3d9'

const src = ref('')
const saveNote = ref('')

// By hand rather than ctx.roundRect(), which older phones' browsers —
// LINE's in-app one included — don't have.
function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number): void {
  const rr = Math.min(r, w / 2, h / 2)
  ctx.beginPath()
  ctx.moveTo(x + rr, y)
  ctx.arcTo(x + w, y, x + w, y + h, rr)
  ctx.arcTo(x + w, y + h, x, y + h, rr)
  ctx.arcTo(x, y + h, x, y, rr)
  ctx.arcTo(x, y, x + w, y, rr)
  ctx.closePath()
}

function loadImage(url: string): Promise<HTMLImageElement | null> {
  return new Promise((resolve) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = () => resolve(null)
    img.src = url
  })
}

async function draw(): Promise<void> {
  const n = props.modules.length
  if (!n) return
  try {
    await Promise.all([document.fonts.load('700 56px "Chakra Petch"'), document.fonts.load('500 30px Mitr')])
  } catch {
    // fonts not reachable: the browser's fallback still renders Thai
  }
  const cat = await loadImage('/hero/cat-color.webp')

  const W = 720
  const pad = 52
  const qrSize = W - pad * 2
  const cell = qrSize / n
  const label = props.amount !== null || props.accountName || props.caption
  const labelH = props.amount !== null && props.accountName ? 150 : 104
  const H = pad + qrSize + (label ? 40 + labelH + 40 : pad)

  const canvas = document.createElement('canvas')
  canvas.width = W
  canvas.height = H
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  // card
  ctx.fillStyle = PINK
  roundRect(ctx, 0, 0, W, H, 56)
  ctx.fill()

  // Where the corner squares and the cat go: no dots there.
  const inFinder = (r: number, c: number): boolean =>
    (r < 7 && c < 7) || (r < 7 && c >= n - 7) || (r >= n - 7 && c < 7)
  const logoCells = Math.round(n * 0.22) | 1 // odd, so it centres on a module
  const logoStart = (n - logoCells) / 2
  const inLogo = (r: number, c: number): boolean =>
    r >= logoStart && r < logoStart + logoCells && c >= logoStart && c < logoStart + logoCells

  ctx.fillStyle = INK
  for (let r = 0; r < n; r++) {
    const row = props.modules[r]
    for (let c = 0; c < n; c++) {
      if (row[c] !== '1' || inFinder(r, c) || inLogo(r, c)) continue
      ctx.beginPath()
      ctx.arc(pad + (c + 0.5) * cell, pad + (r + 0.5) * cell, cell * 0.43, 0, Math.PI * 2)
      ctx.fill()
    }
  }

  // corner squares: a rounded ring and a rounded centre
  for (const [r0, c0] of [
    [0, 0],
    [0, n - 7],
    [n - 7, 0],
  ]) {
    const x = pad + c0 * cell
    const y = pad + r0 * cell
    ctx.fillStyle = INK
    roundRect(ctx, x, y, cell * 7, cell * 7, cell * 2.2)
    ctx.fill()
    ctx.fillStyle = PINK
    roundRect(ctx, x + cell, y + cell, cell * 5, cell * 5, cell * 1.5)
    ctx.fill()
    ctx.fillStyle = INK
    roundRect(ctx, x + cell * 2, y + cell * 2, cell * 3, cell * 3, cell * 1)
    ctx.fill()
  }

  // the cat
  if (cat) {
    const box = logoCells * cell
    const bx = pad + logoStart * cell
    const by = pad + logoStart * cell
    ctx.fillStyle = PINK
    roundRect(ctx, bx, by, box, box, box * 0.22)
    ctx.fill()
    const inset = box * 0.08
    ctx.drawImage(cat, bx + inset, by + inset, box - inset * 2, box - inset * 2)
  }

  // the label
  if (label) {
    const ly = pad + qrSize + 40
    ctx.fillStyle = INK
    roundRect(ctx, pad, ly, qrSize, labelH, labelH / 2 > 60 ? 48 : labelH / 2)
    ctx.fill()
    ctx.fillStyle = LABEL_TEXT
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    const cx = W / 2
    if (props.amount !== null) {
      const big = money(props.amount)
      ctx.font = '700 56px "Chakra Petch", Mitr, sans-serif'
      ctx.fillText(big, cx, props.accountName ? ly + 52 : ly + labelH / 2 + 2, qrSize - 60)
      if (props.accountName) {
        ctx.fillStyle = '#ffffff'
        ctx.font = '500 30px Mitr, sans-serif'
        ctx.fillText(props.accountName, cx, ly + 108, qrSize - 60)
      }
    } else {
      ctx.font = '600 44px Mitr, sans-serif'
      ctx.fillText(props.caption ?? props.accountName ?? '', cx, ly + labelH / 2 + 2, qrSize - 60)
    }
  }

  src.value = canvas.toDataURL('image/png')
}

async function save(): Promise<void> {
  saveNote.value = ''
  try {
    const blob = await (await fetch(src.value)).blob()
    const file = new File([blob], props.fileName, { type: 'image/png' })
    // Phones: the share sheet has "save image"; LINE's browser often
    // ignores downloads, so this is tried first.
    if (navigator.canShare?.({ files: [file] })) {
      await navigator.share({ files: [file] })
      return
    }
    const a = document.createElement('a')
    a.href = src.value
    a.download = props.fileName
    a.click()
  } catch (e) {
    if ((e as Error)?.name === 'AbortError') return // closed the share sheet
    saveNote.value = t('brandQr.saveHint')
  }
}

onMounted(draw)
watch(() => [props.modules, props.amount, props.accountName, props.caption], draw)
</script>

<template>
  <div class="flex flex-col items-center gap-2">
    <img v-if="src" :src="src" :alt="alt" class="brand-qr block h-auto w-full max-w-[300px] select-none" />
    <div v-else class="aspect-[720/900] w-full max-w-[300px] animate-pulse rounded-[24px] bg-[#f4a6c8]/40" aria-hidden="true" />
    <button v-if="saveable && src" type="button" class="glass-pill" @click="save">
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 4v11M7 10l5 5 5-5M5 20h14" /></svg>
      {{ t('brandQr.save') }}
    </button>
    <p v-if="saveNote" class="text-xs text-white/60">{{ saveNote }}</p>
  </div>
</template>

<style scoped>
.brand-qr {
  -webkit-touch-callout: default;
  filter: drop-shadow(0 10px 24px rgb(234 76 164 / 0.35));
}
</style>
