<script setup lang="ts">
// "How much is actually in the club's account" — a donut of where the money
// taken in has gone, with the balance as the hero number in its middle.
//
//   เงินเข้าทั้งหมด (ค่าก๊วนที่เก็บแล้ว + เงินทุน) = จ่ายไปแล้ว + คงเหลือ
//
// Two slices that sum to the whole, so the ring reads as a meter of "share
// still held" rather than as a comparison of arc angles — the number in the
// centre and the breakdown rows below carry the actual values, since nobody
// reads a quantity off an arc.
//
// Paid-only on both sides on purpose. Session dues not yet collected are
// money owed to the club, and an expense an admin fronted but hasn't been
// reimbursed for is money the club owes — neither has moved through the
// account, so neither belongs in its balance.
//
// Colors are the same two validated slots the monthly chart uses, so the
// dashboard speaks one language: blue = the club's money, orange = money
// paid out. Not the brand pink, which means "primary action" everywhere else.
// Validated: node scripts/validate_palette.js "#3987e5,#d95926" --mode dark
// -> all checks pass (worst adjacent ΔE 26.8 CVD / 31.8 normal-vision).
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as adminApi from '@/api/admin'
import { ApiError } from '@/api/client'
import CountUp from '@/components/common/CountUp.vue'

const { t } = useI18n()

const REMAINING_COLOR = '#3987e5'
const SPENT_COLOR = '#d95926'

const loading = ref(true)
const error = ref<string | null>(null)
const dues = ref(0)
const funding = ref(0)
const spent = ref(0)

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const [daily, expenseSummary, otherIncome] = await Promise.all([
      adminApi.getRevenue(),
      adminApi.getExpenseSummary(),
      adminApi.getOtherIncome(),
    ])
    // All-time, not the last 6 months the bar chart shows: a balance is what
    // has accumulated since the club started, so a window would just be a
    // different number wearing the same label.
    dues.value = daily.reduce((sum, d) => sum + d.paid_amount, 0)
    funding.value = otherIncome.reduce((sum, i) => sum + i.amount, 0)
    spent.value = expenseSummary.reduce((sum, e) => sum + e.paid_amount, 0)
  } catch (e) {
    error.value =
      e instanceof ApiError
        ? `${t('dashboard.chartLoadFailed')} (${e.status})`
        : t('dashboard.chartLoadFailed')
  } finally {
    loading.value = false
  }
}

onMounted(load)

const inflow = computed(() => dues.value + funding.value)
const balance = computed(() => inflow.value - spent.value)
/** Spending has outrun everything ever received — there is no "remaining"
 * slice to draw, so the ring goes solid and the centre carries the deficit. */
const overdrawn = computed(() => balance.value < 0)

function formatBaht(n: number): string {
  // Sign ahead of the symbol ("−฿4,000", not "฿-4,000"), and a real minus
  // sign rather than a hyphen so it lines up with the outflow row.
  const rounded = Math.round(n)
  return `${rounded < 0 ? '−' : ''}฿${Math.abs(rounded).toLocaleString('th-TH')}`
}

// --- Donut geometry ---------------------------------------------------
// pathLength="100" makes every dash length a literal percentage, so none of
// this has to know the real circumference. It must stay camelCase — SVG
// attribute names are case-sensitive, and a kebab-case `path-length` is
// silently ignored, which turns the two arcs into a repeating dash pattern.
const VIEW = 180
const CENTER = VIEW / 2
const RADIUS = 68
const STROKE = 20
// ~2px of surface between the two fills, per the marks spec. Only applied
// when both slices are actually drawn, or a 100% ring would gap against
// itself and read as a hairline crack.
const GAP = 0.9

const spentPct = computed(() => (inflow.value > 0 ? (spent.value / inflow.value) * 100 : 0))
const remainingPct = computed(() => Math.max(0, 100 - spentPct.value))
const twoSlices = computed(() => spentPct.value > 0 && remainingPct.value > 0 && !overdrawn.value)
const gap = computed(() => (twoSlices.value ? GAP : 0))

const remainingDash = computed(() => {
  const len = Math.max(0, remainingPct.value - gap.value)
  return `${len} ${100 - len}`
})
const spentDash = computed(() => {
  const len = Math.max(0, Math.min(spentPct.value, 100) - gap.value)
  return `${len} ${100 - len}`
})
</script>

<template>
  <div class="hud-panel border border-brand-pink/20 bg-brand-surface p-4">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h2 class="text-sm font-semibold text-white/70">{{ t('dashboard.balanceChart') }}</h2>
      <!-- Legend — always present for 2+ series, per the dataviz skill. -->
      <div class="flex items-center gap-3 text-xs text-white/60">
        <span class="flex items-center gap-1.5">
          <span class="h-2 w-2 rounded-full" :style="{ backgroundColor: REMAINING_COLOR }" />
          {{ t('dashboard.balanceRemaining') }}
        </span>
        <span class="flex items-center gap-1.5">
          <span class="h-2 w-2 rounded-full" :style="{ backgroundColor: SPENT_COLOR }" />
          {{ t('dashboard.balanceSpent') }}
        </span>
      </div>
    </div>

    <p v-if="loading" class="mt-4 text-sm text-white/50">{{ t('common.loading') }}</p>
    <p v-else-if="error" class="mt-4 text-sm text-status-error">{{ error }}</p>
    <p v-else-if="inflow === 0" class="mt-4 text-sm text-white/40">{{ t('dashboard.balanceEmpty') }}</p>

    <template v-else>
      <div class="mt-4 flex flex-col items-center gap-5 sm:flex-row sm:items-center sm:gap-7">
        <div class="relative shrink-0">
          <svg
            :viewBox="`0 0 ${VIEW} ${VIEW}`"
            class="h-44 w-44 -rotate-90"
            role="img"
            :aria-label="`${t('dashboard.balanceChart')}: ${formatBaht(balance)}`"
          >
            <!-- Track: the whole of what came in. -->
            <circle
              :cx="CENTER"
              :cy="CENTER"
              :r="RADIUS"
              fill="none"
              stroke="rgb(255 255 255 / 0.07)"
              :stroke-width="STROKE"
            />
            <circle
              v-if="!overdrawn"
              :cx="CENTER"
              :cy="CENTER"
              :r="RADIUS"
              fill="none"
              :stroke="REMAINING_COLOR"
              :stroke-width="STROKE"
              pathLength="100"
              :stroke-dasharray="remainingDash"
            />
            <circle
              :cx="CENTER"
              :cy="CENTER"
              :r="RADIUS"
              fill="none"
              :stroke="SPENT_COLOR"
              :stroke-width="STROKE"
              pathLength="100"
              :stroke-dasharray="overdrawn ? '100 0' : spentDash"
              :stroke-dashoffset="overdrawn ? 0 : -(remainingPct + gap / 2)"
            />
          </svg>

          <!-- Hero figure: the answer to "เหลือเท่าไหร่", read as a number
               rather than off the arc. -->
          <div class="absolute inset-0 flex flex-col items-center justify-center text-center">
            <p class="text-[0.65rem] tracking-wide text-white/40 uppercase">
              {{ t('dashboard.balanceRemaining') }}
            </p>
            <p
              class="font-display text-2xl font-bold"
              :class="overdrawn ? 'text-status-error' : 'text-white'"
            >
              <CountUp :value="Math.round(balance)" :format="formatBaht" />
            </p>
            <p v-if="!overdrawn" class="text-[0.65rem] text-white/40">
              {{ Math.round(remainingPct) }}%
            </p>
          </div>
        </div>

        <dl class="w-full space-y-2 text-sm">
          <div class="flex items-baseline justify-between gap-3">
            <dt class="text-white/50">{{ t('dashboard.balanceFromDues') }}</dt>
            <dd class="font-mono text-white/80">{{ formatBaht(dues) }}</dd>
          </div>
          <div class="flex items-baseline justify-between gap-3">
            <dt class="text-white/50">{{ t('dashboard.balanceFromFunding') }}</dt>
            <dd class="font-mono text-white/80">{{ formatBaht(funding) }}</dd>
          </div>
          <div class="flex items-baseline justify-between gap-3 border-t border-white/10 pt-2">
            <dt class="text-white/60">{{ t('dashboard.balanceInflow') }}</dt>
            <dd class="font-mono font-semibold text-white">{{ formatBaht(inflow) }}</dd>
          </div>
          <div class="flex items-baseline justify-between gap-3">
            <dt class="flex items-center gap-1.5 text-white/50">
              <span class="h-2 w-2 shrink-0 rounded-full" :style="{ backgroundColor: SPENT_COLOR }" />
              {{ t('dashboard.balanceOutflow') }}
            </dt>
            <!-- No "−฿0": a club that has reimbursed nothing hasn't paid out. -->
            <dd class="font-mono text-white/80">{{ spent > 0 ? '−' : '' }}{{ formatBaht(spent) }}</dd>
          </div>
          <div class="flex items-baseline justify-between gap-3 border-t border-white/10 pt-2">
            <dt class="flex items-center gap-1.5 text-white/60">
              <span
                v-if="!overdrawn"
                class="h-2 w-2 shrink-0 rounded-full"
                :style="{ backgroundColor: REMAINING_COLOR }"
              />
              {{ t('dashboard.balanceRemaining') }}
            </dt>
            <dd
              class="font-mono text-base font-bold"
              :class="overdrawn ? 'text-status-error' : 'text-status-success'"
            >
              {{ formatBaht(balance) }}
            </dd>
          </div>
        </dl>
      </div>

      <p v-if="overdrawn" class="mt-3 text-xs text-status-error">
        {{ t('dashboard.balanceOverdrawn') }}
      </p>
      <p class="mt-3 text-xs text-white/35">{{ t('dashboard.balanceNote') }}</p>
    </template>
  </div>
</template>
