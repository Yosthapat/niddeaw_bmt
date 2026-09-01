<script setup lang="ts">
// Grouped bar chart: monthly revenue vs. expenses, last 6 months.
// Self-contained (fetches its own data) so DashboardView just drops in
// <RevenueExpenseChart /> — same spirit as SessionPicker.vue.
//
// Colors are the dataviz skill's validated categorical slots 1 (blue) and
// 2 (orange), dark-mode steps since this app is dark-only — not the brand
// pink, deliberately: pink already means "primary action" everywhere else
// in the UI, so reusing it as a data-series color would blur the two.
// Validated: node scripts/validate_palette.js "#3987e5,#d95926" --mode dark
// -> all checks pass (worst adjacent ΔE 26.8 CVD / 31.8 normal-vision).
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as adminApi from '@/api/admin'
import { ApiError } from '@/api/client'

const { t } = useI18n()

const REVENUE_COLOR = '#3987e5'
const EXPENSE_COLOR = '#d95926'
const MONTHS_SHOWN = 6

const loading = ref(true)
const error = ref<string | null>(null)

interface MonthBar {
  month: string
  label: string
  revenue: number
  expense: number
}

const bars = ref<MonthBar[]>([])

function monthLabel(month: string): string {
  const [y, m] = month.split('-').map(Number)
  return new Date(Date.UTC(y, m - 1, 1)).toLocaleDateString('th-TH', { month: 'short', year: '2-digit' })
}

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const [daily, expenseSummary] = await Promise.all([
      adminApi.getRevenue(),
      adminApi.getExpenseSummary(),
    ])

    const revenueByMonth = new Map<string, number>()
    for (const d of daily) {
      const month = d.date.slice(0, 7)
      revenueByMonth.set(month, (revenueByMonth.get(month) ?? 0) + d.total_amount)
    }
    const expenseByMonth = new Map(expenseSummary.map((s) => [s.month, s.total_amount]))

    const months = Array.from(new Set([...revenueByMonth.keys(), ...expenseByMonth.keys()]))
      .sort()
      .slice(-MONTHS_SHOWN)

    bars.value = months.map((month) => ({
      month,
      label: monthLabel(month),
      revenue: revenueByMonth.get(month) ?? 0,
      expense: expenseByMonth.get(month) ?? 0,
    }))
  } catch (e) {
    error.value = e instanceof ApiError ? `${t('dashboard.chartLoadFailed')} (${e.status})` : t('dashboard.chartLoadFailed')
  } finally {
    loading.value = false
  }
}

onMounted(load)

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
  month: string
  series: 'revenue' | 'expense'
}
const hovered = ref<HoveredBar | null>(null)

function toggleHover(month: string, series: 'revenue' | 'expense'): void {
  hovered.value = hovered.value?.month === month && hovered.value?.series === series ? null : { month, series }
}
function hoveredValue(): number | null {
  if (!hovered.value) return null
  const bar = bars.value.find((b) => b.month === hovered.value?.month)
  if (!bar) return null
  return hovered.value.series === 'revenue' ? bar.revenue : bar.expense
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
      <div class="mt-2 flex items-baseline gap-2 text-xs text-white/50">
        {{ t('dashboard.net') }}
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
        <g v-for="(bar, i) in bars" :key="bar.month">
          <rect
            :x="groupX(i)"
            :y="PAD_TOP + innerH - barHeight(bar.revenue)"
            :width="barWidth"
            :height="Math.max(barHeight(bar.revenue), 0.5)"
            :fill="REVENUE_COLOR"
            :opacity="hovered && !(hovered.month === bar.month && hovered.series === 'revenue') ? 0.55 : 1"
            rx="2"
            class="cursor-pointer"
            @click="toggleHover(bar.month, 'revenue')"
            @mouseenter="hovered = { month: bar.month, series: 'revenue' }"
            @mouseleave="hovered = null"
          />
          <rect
            :x="groupX(i) + barWidth + BAR_GAP"
            :y="PAD_TOP + innerH - barHeight(bar.expense)"
            :width="barWidth"
            :height="Math.max(barHeight(bar.expense), 0.5)"
            :fill="EXPENSE_COLOR"
            :opacity="hovered && !(hovered.month === bar.month && hovered.series === 'expense') ? 0.55 : 1"
            rx="2"
            class="cursor-pointer"
            @click="toggleHover(bar.month, 'expense')"
            @mouseenter="hovered = { month: bar.month, series: 'expense' }"
            @mouseleave="hovered = null"
          />
          <text
            :x="groupX(i) + groupWidth / 2"
            :y="VIEW_H - 6"
            text-anchor="middle"
            font-size="10"
            fill="rgb(255 255 255 / 0.5)"
          >
            {{ bar.label }}
          </text>

          <!-- Hover value label, floating above the hovered bar. -->
          <g v-if="hovered?.month === bar.month">
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
          </g>
        </g>
      </svg>
    </template>
  </div>
</template>
