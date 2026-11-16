<script setup lang="ts">
/**
 * One knockout bracket drawn as a bracket: a column per round, left to right
 * from the first round to the final, each match a small box, the boxes of a
 * round spread so a match sits level with the two it comes from. On a phone
 * the columns scroll sideways. Before a team is known its box says where it
 * comes from ("A1", "Winner #31"); once the final is played, the champion
 * stands at the end.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { CupMatch } from '@/api/tournament'
import { clock, sideLabel } from '@/utils/cupMatch'

const props = defineProps<{ matches: CupMatch[]; mineId?: string | null }>()
const { t } = useI18n()
const sides = ['a', 'b'] as const

/** Rounds by teams left — 16, 8, 4, 2 — each in match order. */
const rounds = computed(() => {
  const by = new Map<number, CupMatch[]>()
  for (const m of props.matches) by.set(m.round, [...(by.get(m.round) ?? []), m])
  return [...by.entries()]
    .sort((a, b) => b[0] - a[0])
    .map(([n, ms]) => ({ n, matches: ms.sort((a, b) => a.match_no - b.match_no) }))
})
const roundName = (n: number): string =>
  n === 2 ? t('cup.round.final') : n === 4 ? t('cup.round.semi') : n === 8 ? t('cup.view.quarter') : t('cup.round.ko', { n })

const final = computed(() => rounds.value.at(-1)?.matches.at(-1) ?? null)
const champion = computed(() => {
  const f = final.value
  if (!f || f.status !== 'done' || (f.winner !== 'a' && f.winner !== 'b')) return null
  return f[f.winner]
})
const won = (m: CupMatch, side: 'a' | 'b'): boolean => m.winner === side
const lost = (m: CupMatch, side: 'a' | 'b'): boolean => m.status === 'done' && m.winner !== 'draw' && !won(m, side)
const setsWon = (m: CupMatch, side: 'a' | 'b'): number =>
  (m.sets ?? []).filter(([a, b]) => (side === 'a' ? a > b : b > a)).length
</script>

<template>
  <div class="-mx-3 overflow-x-auto px-3 pb-2">
    <div class="flex min-w-max gap-3">
      <section v-for="r in rounds" :key="r.n" class="flex w-[188px] shrink-0 flex-col">
        <h4 class="mb-2 text-center font-display text-xs font-bold tracking-wide" :class="r.n === 2 ? 'text-[#ffe14d]' : 'text-white/60'">
          {{ roundName(r.n) }}
        </h4>
        <!-- Every column is as tall as the first; spreading each round's boxes
             evenly puts a match level with the pair that feeds it. -->
        <div class="flex flex-1 flex-col justify-around gap-2">
          <article
            v-for="m in r.matches"
            :key="m.id"
            class="b-box rounded-xl border bg-[#1d0b3a]/80 p-2"
            :class="[m.status === 'on_court' ? 'border-[#7ff0b4]/70' : r.n === 2 ? 'border-[#ffe14d]/50' : 'border-white/12']"
          >
            <header class="mb-1 flex items-center gap-1.5 text-[10px] text-white/50">
              <b class="font-display text-white/80">#{{ m.match_no }}</b>
              <span v-if="m.status === 'on_court'" class="rounded-full bg-[#7ff0b4] px-1.5 font-bold text-[#0a2a1a]">{{ t('cup.day.onCourt', { n: m.court }) }}</span>
              <span v-else-if="m.status === 'scheduled' && m.est_start" class="font-display">{{ clock(m.est_start) }}</span>
              <span v-else-if="m.walkover" class="ml-auto">{{ t('cup.view.wo') }}</span>
            </header>
            <div
              v-for="side in sides"
              :key="side"
              class="flex items-center gap-1.5 rounded-md px-1 py-0.5"
              :class="[won(m, side) ? 'bg-[#7ff0b4]/12' : '', lost(m, side) ? 'opacity-45' : '']"
            >
              <span class="min-w-0 flex-1 truncate text-[12.5px]" :class="[m[side].team_name ? (won(m, side) ? 'font-bold text-white' : 'text-white/85') : 'text-white/40 italic', mineId && m[side].team_id === mineId ? '!text-[#ff9fd6] font-bold' : '']">
                {{ sideLabel(m[side], t) }}
              </span>
              <b v-if="m.sets" class="w-3 text-right font-display text-xs" :class="won(m, side) ? 'text-[#7ff0b4]' : 'font-normal text-white/60'">{{ setsWon(m, side) }}</b>
            </div>
          </article>
        </div>
      </section>

      <!-- the end of the line -->
      <section class="flex w-[150px] shrink-0 flex-col">
        <h4 class="mb-2 text-center font-display text-xs font-bold tracking-wide text-[#ffe14d]">{{ t('cup.view.champion') }}</h4>
        <div class="flex flex-1 flex-col justify-center">
          <div class="rounded-2xl border p-3 text-center" :class="champion ? 'b-champ border-[#ffe14d]/70' : 'border-dashed border-white/15'">
            <svg viewBox="0 0 24 24" fill="none" stroke="#ffcf3f" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" class="mx-auto h-8 w-8" :class="champion ? '' : 'opacity-40'" aria-hidden="true">
              <path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0zM17 6h3v2a3 3 0 0 1-3 3M7 6H4v2a3 3 0 0 0 3 3" />
            </svg>
            <p v-if="champion" class="mt-1 font-display text-sm leading-tight font-bold text-[#ffe14d]">{{ champion.team_name }}</p>
            <p v-if="champion" class="mt-0.5 truncate text-[11px] text-white/70">{{ champion.players.map((p) => p.nickname).join(' · ') }}</p>
            <p v-else class="mt-1 text-[11px] text-white/45">{{ t('cup.view.championTbd') }}</p>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.b-champ {
  background: radial-gradient(120% 90% at 50% 0%, rgb(255 225 77 / 0.22), rgb(29 11 58 / 0.9) 70%);
  box-shadow: 0 0 24px rgb(255 207 63 / 0.25);
}
</style>
