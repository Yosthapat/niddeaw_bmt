<script setup lang="ts">
// Grouped bar chart: revenue vs. expenses, bucketed by day, month or year.
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
// with the real ones squeezed between them.
//
// Colors are the dataviz skill's validated categorical slots 1 (blue) and
// 2 (orange), dark-mode steps since this app is dark-only — not the brand
// pink, deliberately: pink already means "primary action" everywhere else
// in the UI, so reusing it as a data-series color would blur the two.
// Validated: node scripts/validate_palette.js "#3987e5,#d95926" --mode dark
// -> all checks pass (worst adjacent ΔE 26.8 CVD / 31.8 normal-vision).
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { storeToRefs } from 'pinia'
import { ApiError } from '@/api/client'
import { useFinanceStore } from '@/stores/finance'

const { t } = useI18n()

const REVENUE_COLOR = '#3987e5'
const EXPENSE_COLOR = '#d95926'

type Period = 'day' | 'month' | 'year'

// Day is capped tighter than it could be: 14 play-days is about two months
// of a twice-a-week club, and past that the bars are too narrow to compare.
// Year is effectively "all of them" — a cap only so the axis can't run away
// a decade from now.
const BARS_SHOWN: Record<Period, number> = { day: 14, month: 6, year: 20 }

const period = ref<Period>('month')

const finance = useFinanceStore()
const { dailyRevenue, expenses, loading } = storeToRefs(finance)

const error = computed(() => {
  const e = finance.error
  if (!e) return null
  return e instanceof ApiError
    ? `${t('dashboard.chartLoadFailed')} (${e.status})`
    : t('dashboard.chartLoadFailed')
})

interface Bar {
  key: string
  label: string
  revenue: number
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
    revenueBy.set(key, (revenueBy.get(key) ?? 0) + entry.total_amount)
  }
  const expenseBy = new Map<string, number>()
  for (const expense of expenses.value) {
    const key = bucketKey(expense.expense_date, p)
    expenseBy.set(key, (expenseBy.get(key) ?? 0) + expense.amount)
  }
  return Array.from(new Set([...revenueBy.keys(), ...expenseBy.keys()]))
    .sort()
    .slice(-BARS_SHOWN[p])
    .map((key) => ({
      key,
      label: bucketLabel(key, p),
      revenue: revenueBy.get(key) ?? 0,
      expense: expenseBy.get(key) ?? 0,
    }))
})

function setPeriod(next: Period): void {
  if (period.value === next) return
  period.value = next
  // Switching buckets re-labels every bar, so a pin left on the old one
  // would point at a value that is no longer on screen.
  hovered.value = null
}

onMounted(finance.refresh)

// --- Layout (hand-rolled SVG — no charting lib) ---
const VIEW_W = 600
const VIEW_H = 200
const PAD_LEFT = 44
const PAD_BOTTOM = 24
const PAD_TOP = 12
const innerW = VIEW_W - PAD_LEFT - 8
const innerH = VIEW_H - PAD_TOP - PAD_BOTTOM
const BAR_GAP = 3 // surface gap between the two bars in a group
const GROUP_GAP = 14

const maxValue = computed(() => {
  const values = bars.value.flatMap((b) => [b.revenue, b.expense])
  const max = Math.max(0, ...values)
  return max > 0 ? max : 1
})

const yTicks = computed(() => {
  const steps = 4
  return Array.from({ length: steps + 1 }, (_, i) => (maxValue.value / steps) * i)
})

const groupWidth = computed(() => {
  const n = bars.value.length || 1
  return (innerW - GROUP_GAP * (n - 1)) / n
})
const barWidth = computed(() => Math.max(4, (groupWidth.value - BAR_GAP) / 2))

function barHeight(value: number): number {
  return (value / maxValue.value) * innerH
}
function groupX(index: number): number {
  return PAD_LEFT + index * (groupWidth.value + GROUP_GAP)
}

interface HoveredBar {
  key: string
  series: 'revenue' | 'expense'
}
const hovered = ref<HoveredBar | null>(null)

function toggleHover(key: string, series: 'revenue' | 'expense'): void {
  hovered.value = hovered.value?.key === key && hovered.value?.series === series ? null : { key, series }
}
function hoveredValue(): number | null {
  if (!hovered.value) return null
  const bar = bars.value.find((b) => b.key === hovered.value?.key)
  if (!bar) return null
  return hovered.value.series === 'revenue' ? bar.revenue : bar.expense
}

// Day view packs 14 labels into the same axis six months use. Printing every
// other one keeps them apart; the bars themselves stay one per bucket.
//
// Counted from the newest bar rather than the oldest: the most recent bucket
// is the one being read, so it must never be the one that loses its label.
// (Counting from the oldest drops it whenever the bar count is even.)
function showLabel(index: number): boolean {
  return bars.value.length <= 8 || (bars.value.length - 1 - index) % 2 === 0
}

function formatBaht(n: number): string {
  return `฿${Math.round(n).toLocaleString('th-TH')}`
}

const totalRevenue = computed(() => bars.value.reduce((sum, b) => sum + b.revenue, 0))
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
          class="px-3 py-1 font-semibold transition-colors"
          :class="period === p ? 'bg-brand-pink text-brand-black' : 'text-white/50 hover:text-white'"
          @click="setPeriod(p)"
        >
          {{ t(`dashboard.period.${p}`) }}
        </button>
      </div>
      <!-- Legend — always present for 2+ series, per the dataviz skill. -->
      <div class="flex items-center gap-3 text-xs text-white/60">
        <span class="flex items-center gap-1.5">
          <span class="h-2 w-2 rounded-full" :style="{ backgroundColor: REVENUE_COLOR }" />
          {{ t('dashboard.revenue') }}
        </span>
        <span class="flex items-center gap-1.5">
          <span class="h-2 w-2 rounded-full" :style="{ backgroundColor: EXPENSE_COLOR }" />
          {{ t('dashboard.expense') }}
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

      <svg :viewBox="`0 0 ${VIEW_W} ${VIEW_H}`" class="mt-2 w-full select-none" role="img" :aria-label="t('dashboard.revenueExpenseChart')">
        <!-- Gridlines + y-axis labels — recessive, muted ink. -->
        <g v-for="(tick, i) in yTicks" :key="i">
          <line
            :x1="PAD_LEFT"
            :x2="VIEW_W - 8"
            :y1="PAD_TOP + innerH - barHeight(tick)"
            :y2="PAD_TOP + innerH - barHeight(tick)"
            stroke="rgb(255 255 255 / 0.08)"
            stroke-width="1"
          />
          <text
            :x="PAD_LEFT - 6"
            :y="PAD_TOP + innerH - barHeight(tick) + 3"
            text-anchor="end"
            font-size="9"
            fill="rgb(255 255 255 / 0.4)"
          >
            {{ tick >= 1000 ? `${(tick / 1000).toFixed(0)}k` : Math.round(tick) }}
          </text>
        </g>

        <!-- Bars -->
        <g v-for="(bar, i) in bars" :key="bar.key">
          <rect
            :x="groupX(i)"
            :y="PAD_TOP + innerH - barHeight(bar.revenue)"
            :width="barWidth"
            :height="Math.max(barHeight(bar.revenue), 0.5)"
            :fill="REVENUE_COLOR"
            :opacity="hovered && !(hovered.key === bar.key && hovered.series === 'revenue') ? 0.55 : 1"
            rx="2"
            class="cursor-pointer"
            @click="toggleHover(bar.key, 'revenue')"
            @mouseenter="hovered = { key: bar.key, series: 'revenue' }"
            @mouseleave="hovered = null"
          />
          <rect
            :x="groupX(i) + barWidth + BAR_GAP"
            :y="PAD_TOP + innerH - barHeight(bar.expense)"
            :width="barWidth"
            :height="Math.max(barHeight(bar.expense), 0.5)"
            :fill="EXPENSE_COLOR"
            :opacity="hovered && !(hovered.key === bar.key && hovered.series === 'expense') ? 0.55 : 1"
            rx="2"
            class="cursor-pointer"
            @click="toggleHover(bar.key, 'expense')"
            @mouseenter="hovered = { key: bar.key, series: 'expense' }"
            @mouseleave="hovered = null"
          />
          <text
            v-if="showLabel(i)"
            :x="groupX(i) + groupWidth / 2"
            :y="VIEW_H - 6"
            text-anchor="middle"
            font-size="10"
            fill="rgb(255 255 255 / 0.5)"
          >
            {{ bar.label }}
          </text>

          <!-- Hover value label, floating above the hovered bar. Carries the
               bucket too, since in the day view not every bar is labelled. -->
          <g v-if="hovered?.key === bar.key">
            <text
              :x="groupX(i) + groupWidth / 2"
              :y="PAD_TOP + innerH - barHeight(hovered.series === 'revenue' ? bar.revenue : bar.expense) - 6"
              text-anchor="middle"
              font-size="11"
              font-weight="700"
              fill="#ffffff"
            >
              {{ formatBaht(hoveredValue() ?? 0) }}
            </text>
            <text
              v-if="!showLabel(i)"
              :x="groupX(i) + groupWidth / 2"
              :y="VIEW_H - 6"
              text-anchor="middle"
              font-size="10"
              fill="rgb(255 255 255 / 0.8)"
            >
              {{ bar.label }}
            </text>
          </g>
        </g>
      </svg>
    </template>
  </div>
</template>
