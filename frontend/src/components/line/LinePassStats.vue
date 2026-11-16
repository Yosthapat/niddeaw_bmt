<script setup lang="ts">
/**
 * Niddeaw Pass › my numbers, for the holder alone: their ELO over time, the
 * partner they win most with, the opponent they beat least, how they do
 * through the night, and their last ten games (backend pass_perks.stats).
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as lineApi from '@/api/line'
import type { PassStats } from '@/api/line'
import { apiErrorMessage } from '@/api/errors'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'

const props = defineProps<{ token: string }>()
const { t } = useI18n()

type Range = 'week' | 'month' | 'season' | 'all'
const RANGES: Range[] = ['week', 'month', 'season', 'all']
const data = ref<PassStats | null>(null)
const problem = ref('')
const range = ref<Range>('month')

onMounted(async () => {
  try {
    data.value = await lineApi.getPassStats(props.token)
  } catch (e) {
    problem.value = apiErrorMessage(e, t('passPlus.statsFailed'))
  }
})

const W = 330
const H = 120
const points = computed(() => {
  const all = data.value?.series ?? []
  const now = Date.now()
  const since =
    range.value === 'week'
      ? now - 7 * 86_400_000
      : range.value === 'month'
        ? now - 30 * 86_400_000
        : range.value === 'season'
          ? new Date(new Date().getFullYear(), 0, 1).getTime()
          : 0
  return all.filter((p) => new Date(p.at).getTime() >= since)
})
// The line starts at their rating going into the range's first game, so
// even one game draws a line and the change across the range adds up.
const line = computed(() => {
  const p = points.value
  if (!p.length) return []
  return [{ at: p[0]!.at, elo: p[0]!.elo - p[0]!.delta, delta: 0, upset: false }, ...p]
})
const move = computed(() => (line.value.length && data.value ? data.value.elo - line.value[0]!.elo : 0))
const chart = computed(() => {
  const p = line.value
  if (p.length < 2) return null
  const elos = p.map((x) => x.elo)
  const lo = Math.min(...elos) - 8
  const hi = Math.max(...elos) + 8
  const x = (i: number): number => (i / (p.length - 1)) * W
  const y = (e: number): number => H - 12 - ((e - lo) / (hi - lo)) * (H - 24)
  const path = p.map((pt, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)} ${y(pt.elo).toFixed(1)}`).join(' ')
  return {
    line: path,
    area: `${path} L${W} ${H} L0 ${H}Z`,
    end: { x: x(p.length - 1), y: y(p[p.length - 1]!.elo) },
    upsets: p.flatMap((pt, i) => (pt.upset ? [{ x: x(i), y: y(pt.elo) }] : [])),
  }
})
const pct = (w: number, g: number): number => (g ? Math.round((w / g) * 100) : 0)
const form = computed(() =>
  (data.value?.form ?? []).map((b) => ({
    ...b,
    label: t(`passPlus.form${b.bucket[0]!.toUpperCase()}${b.bucket.slice(1)}`),
    rate: pct(b.wins, b.games),
  })),
)
const fades = computed(() => {
  const [early, , late] = form.value
  return !!early && !!late && late.games >= 5 && early.games >= 5 && early.rate - late.rate >= 15
})
const COLORS = ['linear-gradient(90deg,#7ef0b0,#3cc98a)', 'linear-gradient(90deg,#ffe58a,#f2c14e)', 'linear-gradient(90deg,#ff8fb0,#ea4ca4)']
</script>

<template>
  <section class="flex flex-col gap-3">
    <p v-if="!data && !problem" class="text-sm text-white/60">{{ t('common.loading') }}</p>
    <p v-if="problem" role="alert" class="text-sm text-status-error">{{ problem }}</p>
    <p v-if="data && data.games === 0" class="glass p-4 text-sm text-white/65">{{ t('passPlus.noGames') }}</p>

    <template v-if="data && data.games > 0">
      <div class="glass p-4 pb-3">
        <div class="flex items-baseline justify-between">
          <div>
            <p class="text-xs text-white/55">{{ t('passPlus.eloNow') }}</p>
            <p class="font-display text-3xl font-bold">{{ data.elo.toLocaleString('en-US') }}</p>
          </div>
          <span class="text-sm font-bold" :class="move >= 0 ? 'text-[#7ef0b0]' : 'text-[#ff8fb0]'">
            {{ move >= 0 ? '▲' : '▼' }} {{ Math.abs(move) }} {{ t('passPlus.eloMove', { range: t(`passPlus.rangeIn.${range}`) }) }}
          </span>
        </div>
        <svg v-if="chart" :viewBox="`0 0 ${W} ${H}`" class="mt-2 w-full" role="img" :aria-label="t('passPlus.statsTitle')">
          <defs>
            <linearGradient id="elo-fill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0" stop-color="#ff4fa6" stop-opacity=".45" />
              <stop offset="1" stop-color="#ff4fa6" stop-opacity="0" />
            </linearGradient>
          </defs>
          <g stroke="rgb(255 255 255 / .08)">
            <line x1="0" :x2="W" y1="30" y2="30" />
            <line x1="0" :x2="W" y1="65" y2="65" />
            <line x1="0" :x2="W" y1="100" y2="100" />
          </g>
          <path :d="chart.area" fill="url(#elo-fill)" />
          <path :d="chart.line" fill="none" stroke="#ff8fd0" stroke-width="3" stroke-linejoin="round" stroke-linecap="round" />
          <circle v-for="(u, i) in chart.upsets" :key="i" :cx="u.x" :cy="u.y" r="4" fill="#ffe58a"><title>{{ t('passPlus.upset') }}</title></circle>
          <circle :cx="chart.end.x" :cy="chart.end.y" r="5" fill="#fff" stroke="#ff4fa6" stroke-width="3" />
        </svg>
        <p v-else class="py-6 text-center text-xs text-white/45">—</p>
        <div class="mt-2 flex flex-wrap items-center gap-1.5" role="tablist">
          <button
            v-for="r in RANGES"
            :key="r"
            type="button"
            role="tab"
            class="chip"
            :class="{ on: range === r }"
            :aria-selected="range === r"
            @click="range = r"
          >
            {{ t(`passPlus.range.${r}`) }}
          </button>
          <span v-if="chart?.upsets.length" class="ml-auto text-[11px] text-[#ffe8a3]">● {{ t('passPlus.upset') }}</span>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-2.5">
        <div class="glass flex flex-col gap-1.5 p-3.5">
          <span class="text-[11px] text-white/55">{{ t('passPlus.partner') }}</span>
          <template v-if="data.partner">
            <span class="flex items-center gap-2 font-bold">
              <PlayerAvatar :name="data.partner.player.nickname" :avatar-url="data.partner.player.avatar_url" size="sm" round />
              <span class="truncate">{{ data.partner.player.nickname }}</span>
            </span>
            <span class="font-display text-2xl font-bold text-[#7ef0b0]">{{ pct(data.partner.wins, data.partner.games) }}%</span>
            <span class="text-[11px] text-white/60">{{ t('passPlus.partnerNote', data.partner) }}</span>
          </template>
          <span v-else class="text-xs text-white/45">{{ t('passPlus.notEnough') }}</span>
        </div>
        <div class="glass flex flex-col gap-1.5 p-3.5">
          <span class="text-[11px] text-white/55">{{ t('passPlus.rival') }}</span>
          <template v-if="data.rival">
            <span class="flex items-center gap-2 font-bold">
              <PlayerAvatar :name="data.rival.player.nickname" :avatar-url="data.rival.player.avatar_url" size="sm" round />
              <span class="truncate">{{ data.rival.player.nickname }}</span>
            </span>
            <span class="font-display text-2xl font-bold text-[#ff8fb0]">{{ pct(data.rival.wins, data.rival.games) }}%</span>
            <span class="text-[11px] text-white/60">{{ t('passPlus.rivalNote', data.rival) }}</span>
          </template>
          <span v-else class="text-xs text-white/45">{{ t('passPlus.notEnough') }}</span>
        </div>
      </div>

      <div class="glass p-4">
        <p class="text-sm font-bold">{{ t('passPlus.form') }}</p>
        <div v-for="(b, i) in form" :key="b.bucket" class="mt-2.5 flex items-center gap-2.5 text-xs">
          <span class="w-[86px] shrink-0 text-white/70">{{ b.label }}</span>
          <span class="h-2.5 flex-1 overflow-hidden rounded-full bg-white/8">
            <i class="block h-full rounded-full" :style="{ width: `${b.rate}%`, background: COLORS[i] }" />
          </span>
          <b class="w-16 shrink-0 text-right">{{ b.games ? `${b.rate}%` : '—' }} <small class="font-normal text-white/45">({{ b.games }})</small></b>
        </div>
        <p v-if="fades" class="mt-2.5 text-[11px] text-white/60">{{ t('passPlus.formTip') }}</p>
      </div>

      <div class="glass p-4">
        <div class="flex items-baseline justify-between">
          <p class="text-sm font-bold">{{ t('passPlus.last10') }}</p>
          <span class="text-xs text-white/60">{{ t('passPlus.bestStreak') }} <b class="text-[#ffe58a]">{{ data.best_streak }}</b></span>
        </div>
        <div class="mt-2.5 flex flex-wrap gap-1.5">
          <i v-for="(r, i) in data.last" :key="i" class="res" :class="r">{{ r }}</i>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.glass {
  border: 1px solid rgb(255 255 255 / 0.12);
  border-radius: 20px;
  background: linear-gradient(160deg, rgb(255 255 255 / 0.07), rgb(255 255 255 / 0.02));
}
.chip {
  min-height: 28px;
  padding: 0 11px;
  border-radius: 999px;
  background: rgb(255 255 255 / 0.06);
  color: rgb(255 255 255 / 0.6);
  font-size: 11.5px;
}
.chip.on {
  background: #ea4ca4;
  color: #fff;
}
.res {
  display: grid;
  width: 24px;
  height: 24px;
  place-items: center;
  border-radius: 7px;
  font-size: 11px;
  font-style: normal;
  font-weight: 800;
}
.res.W {
  background: rgb(126 240 176 / 0.2);
  color: #7ef0b0;
}
.res.L {
  background: rgb(255 107 154 / 0.18);
  color: #ff8fb0;
}
.res.D {
  background: rgb(255 255 255 / 0.1);
  color: rgb(255 255 255 / 0.75);
}
</style>
