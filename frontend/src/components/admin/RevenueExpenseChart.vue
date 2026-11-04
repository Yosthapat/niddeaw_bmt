<script setup lang="ts">
// Line chart: money in vs. money out, bucketed by day, month or year.
// Money in is session dues plus the shop's sales (confirmed + delivered
// orders, on the Bangkok day they were placed), so one line is everything
// that came in. The gap between the two lines is washed green where more
// came in than went out and red where it didn't, so profit and loss read at
// a glance; the readout under the plot says which, in words and numbers.
// Self-contained (fetches its own data) so DashboardView just drops in
// <RevenueExpenseChart /> — same spirit as SessionPicker.vue.
//
// Both series are fetched once at their finest grain and bucketed here, so
// switching the period is instant and costs no request. That's why expenses
// come from the raw list rather than /expenses/summary: the summary is
// month-only, and a day view can't be derived from it. Bucketing those same
// rows by month gives the identical figures the summary would have.
//
// The fetch itself lives in stores/finance.ts, shared with the balance
// donut below so the dashboard asks for each feed once.
//
// Only buckets that actually have movement are plotted. The club plays once
// or twice a week, so a calendar-strict day view would be mostly empty bars
// with the real ones squeezed between them. (So the x axis is evenly spaced
// buckets, not calendar time.)
//
// Colors are the dataviz skill's validated categorical slots 1 (blue) and
// 2 (orange), dark-mode steps since this app is dark-only — not the brand
// pink, deliberately: pink already means "primary action" everywhere else
// in the UI, so reusing it as a data-series color would blur the two.
// Validated: node scripts/validate_palette.js "#3987e5,#d95926" --mode dark
// -> all checks pass (worst adjacent ΔE 26.8 CVD / 31.8 normal-vision). The
// shop's share is named in the readout (slot 3, aqua, as on the shop page)
// rather than drawn as a third line. The profit / loss wash is a 14% tint of
// the status colors, and always comes with its word in the readout.
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { storeToRefs } from 'pinia'
import { apiErrorMessage } from '@/api/errors'
import { useFinanceStore } from '@/stores/finance'
import { moneyShort } from '@/utils/format'

const { t } = useI18n()

const REVENUE_COLOR = '#3987e5'
const EXPENSE_COLOR = '#d95926'
const SHOP_COLOR = '#199e70'
const PROFIT_COLOR = '#4ade80' // --color-status-success
const LOSS_COLOR = '#f87171' // --color-status-error
const SURFACE = '#180e13' // --color-brand-surface: the ring around markers

type Period = 'day' | 'month' | 'year'

// Day is capped tighter than it could be: 14 play-days is about two months
// of a twice-a-week club, and past that the points crowd the axis labels.
// Year is effectively "all of them" — a cap only so the axis can't run away
// a decade from now.
const BARS_SHOWN: Record<Period, number> = { day: 14, month: 6, year: 20 }

const period = ref<Period>('month')

const finance = useFinanceStore()
const { dailyRevenue, expenses, shop, credit, loading } = storeToRefs(finance)

const error = computed(() => {
  const e = finance.error
  if (!e) return null
  return apiErrorMessage(e, t('dashboard.chartLoadFailed'))
})

interface Bar {
  key: string
  label: string
  revenue: number
  shop: number
  /** baht taken for club credit (less any paid back) */
  credit: number
  expense: number
}

/** "2026-09-11" -> the bucket it belongs to at this period. */
function bucketKey(isoDate: string, p: Period): string {
  if (p === 'day') return isoDate.slice(0, 10)
  return p === 'month' ? isoDate.slice(0, 7) : isoDate.slice(0, 4)
}

function bucketLabel(key: string, p: Period): string {
  const [y, m, d] = key.split('-').map(Number)
  if (p === 'year') {
    return new Date(Date.UTC(y, 0, 1)).toLocaleDateString('th-TH', { year: 'numeric' })
  }
  const date = new Date(Date.UTC(y, (m ?? 1) - 1, d ?? 1))
  return p === 'day'
    ? // Numeric month, not the short name: 14 labels of "11 ก.ย." collide on
      // a phone, and inside a two-week window "11/9" is unambiguous.
      date.toLocaleDateString('th-TH', { day: 'numeric', month: 'numeric' })
    : date.toLocaleDateString('th-TH', { month: 'short', year: '2-digit' })
}

const bars = computed<Bar[]>(() => {
  const p = period.value
  const revenueBy = new Map<string, number>()
  for (const entry of dailyRevenue.value) {
    const key = bucketKey(entry.date, p)
    // Less what credit paid: that baht is counted on the day it was topped up.
    revenueBy.set(key, (revenueBy.get(key) ?? 0) + entry.total_amount - (entry.credit_amount ?? 0))
  }
  const shopBy = new Map<string, number>()
  for (const day of shop.value?.daily ?? []) {
    const key = bucketKey(day.date, p)
    shopBy.set(key, (shopBy.get(key) ?? 0) + day.amount)
  }
  const creditBy = new Map<string, number>()
  for (const day of credit.value?.daily ?? []) {
    const key = bucketKey(day.date, p)
    creditBy.set(key, (creditBy.get(key) ?? 0) + day.cash)
  }
  const expenseBy = new Map<string, number>()
  for (const expense of expenses.value) {
    const key = bucketKey(expense.expense_date, p)
    expenseBy.set(key, (expenseBy.get(key) ?? 0) + expense.amount)
  }
  return Array.from(new Set([...revenueBy.keys(), ...shopBy.keys(), ...creditBy.keys(), ...expenseBy.keys()]))
    .sort()
    .slice(-BARS_SHOWN[p])
    .map((key) => ({
      key,
      label: bucketLabel(key, p),
      revenue: revenueBy.get(key) ?? 0,
      shop: shopBy.get(key) ?? 0,
      credit: creditBy.get(key) ?? 0,
      expense: expenseBy.get(key) ?? 0,
    }))
})

function setPeriod(next: Period): void {
  if (period.value === next) return
  period.value = next
  // Switching buckets re-labels every point, so a pick left on the old one
  // would point at a value that is no longer on screen.
  picked.value = null
}

onMounted(finance.refresh)

// --- Layout (hand-rolled SVG — no charting lib) ---
// The viewBox is the plot's real width in CSS pixels, kept in step by a
// ResizeObserver, so text and markers are the size written here on every
// screen. A fixed 600-wide viewBox scaled down to a phone shrank the axis
// labels to about 5px.
const viewW = ref(600)
const VIEW_H = 220
const PAD_LEFT = 44
const PAD_RIGHT = 14
const PAD_BOTTOM = 26
const PAD_TOP = 14
const innerW = computed(() => viewW.value - PAD_LEFT - PAD_RIGHT)
const innerH = VIEW_H - PAD_TOP - PAD_BOTTOM
const INSET = 12 // first and last points sit this far in from the plot's edges

/** Money in for a bucket: dues, the shop, and cash taken for credit. */
const income = (b: Bar): number => b.revenue + b.shop + b.credit

/** A round top for the y axis — 1, 2, 2.5 or 5 × 10^k per step — so the
 * gridlines land on numbers a person would say out loud. */
const niceTop = computed(() => {
  const max = Math.max(0, ...bars.value.flatMap((b) => [income(b), b.expense]))
  if (max <= 0) return 4
  const raw = max / 4
  const mag = 10 ** Math.floor(Math.log10(raw))
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((v) => v >= raw) ?? 10 * mag
  return step * 4
})
const yTicks = computed(() => Array.from({ length: 5 }, (_, i) => (niceTop.value / 4) * i))

function y(value: number): number {
  return PAD_TOP + innerH - (value / niceTop.value) * innerH
}
function x(index: number): number {
  const n = bars.value.length
  if (n <= 1) return PAD_LEFT + innerW.value / 2
  return PAD_LEFT + INSET + (index * (innerW.value - INSET * 2)) / (n - 1)
}

function linePath(values: number[]): string {
  return values.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')
}
const incomePath = computed(() => linePath(bars.value.map(income)))
const expensePath = computed(() => linePath(bars.value.map((b) => b.expense)))

/** The wash between the two lines, one polygon per run, split where they
 * cross so each piece is wholly profit or wholly loss. */
const washes = computed(() => {
  const out: { d: string; profit: boolean }[] = []
  const pts = bars.value.map((b, i) => ({ x: x(i), a: income(b), e: b.expense }))
  for (let i = 0; i + 1 < pts.length; i++) {
    const p = pts[i]
    const q = pts[i + 1]
    const d0 = p.a - p.e
    const d1 = q.a - q.e
    const quad = (x0: number, a0: number, e0: number, x1: number, a1: number, e1: number): string =>
      `M${x0},${y(a0)} L${x1},${y(a1)} L${x1},${y(e1)} L${x0},${y(e0)} Z`
    if (d0 * d1 >= 0) {
      if (d0 !== 0 || d1 !== 0) out.push({ d: quad(p.x, p.a, p.e, q.x, q.a, q.e), profit: d0 + d1 > 0 })
      continue
    }
    // they cross: split at the crossing
    const t = d0 / (d0 - d1)
    const cx = p.x + (q.x - p.x) * t
    const cv = p.a + (q.a - p.a) * t
    out.push({ d: quad(p.x, p.a, p.e, cx, cv, cv), profit: d0 > 0 })
    out.push({ d: quad(cx, cv, cv, q.x, q.a, q.e), profit: d1 > 0 })
  }
  return out
})

// --- Picking a bucket: the crosshair snaps to the nearest one ---
const picked = ref<number | null>(null)
const svgEl = ref<SVGSVGElement | null>(null)

function nearest(event: PointerEvent): number | null {
  const el = svgEl.value
  if (!el || bars.value.length === 0) return null
  const box = el.getBoundingClientRect()
  const vx = ((event.clientX - box.left) / box.width) * viewW.value
  let best = 0
  for (let i = 1; i < bars.value.length; i++) if (Math.abs(x(i) - vx) < Math.abs(x(best) - vx)) best = i
  return best
}
// A mouse picks as it moves and lets go when it leaves; a finger picks
// where it lands and the pick stays, since there is no hover on a phone.
function onMove(event: PointerEvent): void {
  if (event.pointerType === 'mouse') picked.value = nearest(event)
}
function onDown(event: PointerEvent): void {
  picked.value = nearest(event)
}
function onLeave(event: PointerEvent): void {
  if (event.pointerType === 'mouse') picked.value = null
}
function onKey(event: KeyboardEvent): void {
  const n = bars.value.length
  if (!n || (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight')) return
  event.preventDefault()
  const at = picked.value ?? n - 1
  picked.value = Math.min(n - 1, Math.max(0, at + (event.key === 'ArrowRight' ? 1 : -1)))
}

const plotBox = ref<HTMLElement | null>(null)
const resize = new ResizeObserver(([entry]) => {
  const w = Math.round(entry.contentRect.width)
  if (w > 0) viewW.value = Math.max(260, w)
})
// The plot only exists once the data has loaded (and again after a period
// switch from an empty one), so follow the element rather than observing
// once on mount.
watch(plotBox, (el, old) => {
  if (old) resize.unobserve(old)
  if (el) resize.observe(el)
})
onBeforeUnmount(() => resize.disconnect())

/** The readout under the plot: the picked bucket, else the newest. */
const shownIndex = computed(() => picked.value ?? bars.value.length - 1)
const shownBar = computed(() => bars.value[shownIndex.value] ?? null)
/** Any shop sales on screen: without them the readout's shop line is noise. */
const anyShop = computed(() => bars.value.some((b) => b.shop > 0 || b.credit !== 0))

// Day view packs 14 labels into the same axis six months use. Printing every
// other one keeps them apart; the points themselves stay one per bucket.
//
// Counted from the newest point rather than the oldest: the most recent
// bucket is the one being read, so it must never be the one that loses its
// label. (Counting from the oldest drops it whenever the count is even.)
function showLabel(index: number): boolean {
  return bars.value.length <= 8 || (bars.value.length - 1 - index) % 2 === 0
}

function formatBaht(n: number): string {
  return moneyShort(n)
}
function tickLabel(v: number): string {
  if (v >= 1000) return `${Number((v / 1000).toFixed(1))}k`
  return String(Math.round(v))
}

const totalRevenue = computed(() => bars.value.reduce((sum, b) => sum + income(b), 0))
const totalExpense = computed(() => bars.value.reduce((sum, b) => sum + b.expense, 0))
const net = computed(() => totalRevenue.value - totalExpense.value)
</script>

<template>
  <div class="hud-panel border border-brand-pink/20 bg-brand-surface p-4">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h2 class="text-sm font-semibold text-white/70">{{ t('dashboard.revenueExpenseChart') }}</h2>
      <!-- Filters sit in one row above the plot, per the dataviz skill. -->
      <div class="hud-panel flex border border-brand-pink/25 bg-brand-surface p-1 text-xs">
        <button
          v-for="p in (['day', 'month', 'year'] as const)"
          :key="p"
          type="button"
          class="tap px-3 font-semibold transition-colors"
          :class="period === p ? 'bg-brand-pink text-brand-black' : 'text-white/50 hover:text-white'"
          @click="setPeriod(p)"
        >
          {{ t(`dashboard.period.${p}`) }}
        </button>
      </div>
      <!-- Legend — always present for 2+ series, per the dataviz skill. -->
      <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-white/60">
        <span class="flex items-center gap-1.5">
          <span class="h-0.5 w-4 rounded-full" :style="{ backgroundColor: REVENUE_COLOR }" />
          {{ t('dashboard.revenueTotal') }}
        </span>
        <span class="flex items-center gap-1.5">
          <span class="h-0.5 w-4 rounded-full" :style="{ backgroundColor: EXPENSE_COLOR }" />
          {{ t('dashboard.expense') }}
        </span>
        <span class="flex items-center gap-1.5">
          <span class="h-2.5 w-3 rounded-sm" :style="{ backgroundColor: PROFIT_COLOR, opacity: 0.35 }" />
          {{ t('dashboard.profit') }}
        </span>
        <span class="flex items-center gap-1.5">
          <span class="h-2.5 w-3 rounded-sm" :style="{ backgroundColor: LOSS_COLOR, opacity: 0.35 }" />
          {{ t('dashboard.loss') }}
        </span>
      </div>
    </div>

    <p v-if="loading" class="mt-4 text-sm text-white/50">{{ t('common.loading') }}</p>
    <p v-else-if="error" class="mt-4 text-sm text-status-error">{{ error }}</p>
    <p v-else-if="bars.length === 0" class="mt-4 text-sm text-white/40">{{ t('dashboard.chartEmpty') }}</p>

    <template v-else>
      <div class="mt-2 flex flex-wrap items-baseline gap-2 text-xs text-white/50">
        {{ t('dashboard.net') }} ({{ t('dashboard.netScope', { n: bars.length }) }})
        <span class="text-base font-bold" :class="net >= 0 ? 'text-status-success' : 'text-status-error'">
          {{ net >= 0 ? '+' : '' }}{{ formatBaht(net) }}
        </span>
      </div>

      <div ref="plotBox" class="mt-2 w-full">
      <svg
        ref="svgEl"
        :viewBox="`0 0 ${viewW} ${VIEW_H}`"
        :height="VIEW_H"
        class="block w-full touch-pan-y select-none outline-none focus-visible:ring-2 focus-visible:ring-brand-pink/60"
        role="img"
        tabindex="0"
        :aria-label="t('dashboard.revenueExpenseChart')"
        @pointermove="onMove"
        @pointerdown="onDown"
        @pointerleave="onLeave"
        @keydown="onKey"
      >
        <!-- Gridlines + y-axis labels — hairline, solid, recessive. -->
        <g v-for="(tick, i) in yTicks" :key="i">
          <line :x1="PAD_LEFT" :x2="viewW - PAD_RIGHT" :y1="y(tick)" :y2="y(tick)" stroke="rgb(255 255 255 / 0.08)" stroke-width="1" />
          <text :x="PAD_LEFT - 8" :y="y(tick) + 3" text-anchor="end" font-size="10" fill="rgb(255 255 255 / 0.4)">{{ tickLabel(tick) }}</text>
        </g>

        <!-- Profit / loss wash between the lines -->
        <path
          v-for="(w, i) in washes"
          :key="`w${i}`"
          :d="w.d"
          :fill="w.profit ? PROFIT_COLOR : LOSS_COLOR"
          fill-opacity="0.14"
          stroke="none"
        />

        <!-- Crosshair: a hairline on the picked bucket -->
        <line
          v-if="picked !== null"
          :x1="x(picked)"
          :x2="x(picked)"
          :y1="PAD_TOP"
          :y2="PAD_TOP + innerH"
          stroke="rgb(255 255 255 / 0.35)"
          stroke-width="1"
        />

        <path v-if="bars.length > 1" :d="expensePath" fill="none" :stroke="EXPENSE_COLOR" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
        <path v-if="bars.length > 1" :d="incomePath" fill="none" :stroke="REVENUE_COLOR" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />

        <!-- Markers: filled, with a ring in the surface color so they stay
             legible where the lines cross. The picked bucket's grow. -->
        <g v-for="(bar, i) in bars" :key="bar.key">
          <circle :cx="x(i)" :cy="y(bar.expense)" :r="i === shownIndex ? 5.5 : 4" :fill="EXPENSE_COLOR" :stroke="SURFACE" stroke-width="2" />
          <circle :cx="x(i)" :cy="y(income(bar))" :r="i === shownIndex ? 5.5 : 4" :fill="REVENUE_COLOR" :stroke="SURFACE" stroke-width="2" />
          <!-- One bucket has no line to read: say its two values beside the
               dots, money in above, money out below. -->
          <template v-if="bars.length === 1">
            <text :x="x(i) + 12" :y="Math.min(y(income(bar)), y(bar.expense)) - 4" font-size="11" fill="rgb(255 255 255 / 0.85)">
              {{ formatBaht(income(bar) >= bar.expense ? income(bar) : bar.expense) }}
            </text>
            <text :x="x(i) + 12" :y="Math.max(y(income(bar)), y(bar.expense)) + 14" font-size="11" fill="rgb(255 255 255 / 0.6)">
              {{ formatBaht(income(bar) >= bar.expense ? bar.expense : income(bar)) }}
            </text>
          </template>
          <text
            v-if="showLabel(i) || i === picked"
            :x="x(i)"
            :y="VIEW_H - 8"
            text-anchor="middle"
            font-size="11"
            :fill="i === shownIndex ? 'rgb(255 255 255 / 0.85)' : 'rgb(255 255 255 / 0.5)'"
          >
            {{ bar.label }}
          </text>
        </g>
      </svg>
      </div>

      <!-- The readout: every series at the picked bucket (else the newest),
           in words, so nothing rests on reading a line's height or a color. -->
      <div v-if="shownBar" class="mt-2 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2.5 text-xs" role="status">
        <div class="flex items-baseline justify-between gap-3">
          <span class="font-semibold text-white/85">{{ shownBar.label }}</span>
          <span class="text-white/40">{{ picked === null ? t('dashboard.chartLatest') : '' }}</span>
        </div>
        <dl class="mt-1.5 grid grid-cols-[1fr_auto] gap-x-4 gap-y-1">
          <dt class="flex items-center gap-1.5 text-white/60">
            <span class="h-2 w-2 rounded-full" :style="{ backgroundColor: REVENUE_COLOR }" />{{ t('dashboard.revenueTotal') }}
          </dt>
          <dd class="text-right font-mono text-white/90">{{ formatBaht(income(shownBar)) }}</dd>
          <template v-if="anyShop">
            <dt class="pl-3.5 text-white/45">{{ t('dashboard.revenueDues') }}</dt>
            <dd class="text-right font-mono text-white/60">{{ formatBaht(shownBar.revenue) }}</dd>
            <dt class="flex items-center gap-1.5 pl-3.5 text-white/45">
              <span class="h-1.5 w-1.5 rounded-full" :style="{ backgroundColor: SHOP_COLOR }" />{{ t('dashboard.revenueShop') }}
            </dt>
            <dd class="text-right font-mono text-white/60">{{ formatBaht(shownBar.shop) }}</dd>
            <template v-if="shownBar.credit !== 0">
              <dt class="flex items-center gap-1.5 pl-3.5 text-white/45">
                <span class="h-1.5 w-1.5 rounded-full bg-[#ffc531]" />{{ t('dashboard.revenueCredit') }}
              </dt>
              <dd class="text-right font-mono text-white/60">{{ formatBaht(shownBar.credit) }}</dd>
            </template>
          </template>
          <dt class="flex items-center gap-1.5 text-white/60">
            <span class="h-2 w-2 rounded-full" :style="{ backgroundColor: EXPENSE_COLOR }" />{{ t('dashboard.expense') }}
          </dt>
          <dd class="text-right font-mono text-white/90">{{ formatBaht(shownBar.expense) }}</dd>
        </dl>
        <div class="mt-1.5 flex items-baseline justify-between gap-4 border-t border-white/10 pt-1.5">
          <span class="font-medium text-white/75">
            {{ income(shownBar) >= shownBar.expense ? t('dashboard.profit') : t('dashboard.loss') }}
          </span>
          <span class="font-mono font-bold" :class="income(shownBar) >= shownBar.expense ? 'text-status-success' : 'text-status-error'">
            {{ income(shownBar) >= shownBar.expense ? '+' : '' }}{{ formatBaht(income(shownBar) - shownBar.expense) }}
          </span>
        </div>
      </div>
      <p v-if="finance.creditError" class="mt-2 text-xs text-[#ffb08a]" role="status">{{ t('dashboard.creditMissing') }}</p>
      <p class="mt-1.5 text-[11px] text-white/35">{{ t('dashboard.chartPickHint') }}</p>
    </template>
  </div>
</template>
