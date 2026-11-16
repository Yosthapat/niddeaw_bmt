<script setup lang="ts">
/**
 * One match on a single tidy row, for lists of many: a group's matches and
 * the results. The number and time (or court, or "final") on the left, the
 * two teams one above the other, and each team's points set by set on the
 * right — the winner bright, the loser dimmed.
 */
import { useI18n } from 'vue-i18n'
import type { CupMatch } from '@/api/tournament'
import { clock, roundLabel, sideLabel } from '@/utils/cupMatch'

const props = defineProps<{ match: CupMatch; showRound?: boolean; showLevel?: boolean }>()
const { t } = useI18n()
const sides = ['a', 'b'] as const
const won = (side: 'a' | 'b'): boolean => props.match.winner === side
const lost = (side: 'a' | 'b'): boolean => props.match.status === 'done' && props.match.winner !== 'draw' && !won(side)
const points = (side: 'a' | 'b'): number[] => (props.match.sets ?? []).map((s) => s[side === 'a' ? 0 : 1])
</script>

<template>
  <div class="flex items-center gap-3 rounded-xl px-3 py-2" :class="match.status === 'on_court' ? 'bg-[#7ff0b4]/10 ring-1 ring-[#7ff0b4]/50' : 'bg-white/5'">
    <div class="w-12 shrink-0 text-center leading-tight">
      <p class="font-display text-[13px] font-bold">#{{ match.match_no }}</p>
      <p v-if="match.status === 'on_court'" class="text-[10px] font-bold text-[#7ff0b4]">{{ t('cup.day.onCourt', { n: match.court }) }}</p>
      <p v-else-if="match.status === 'done'" class="text-[10px] text-white/45">{{ match.walkover ? t('cup.view.wo') : t('cup.day.final') }}</p>
      <p v-else class="font-display text-[11px] text-white/60">{{ clock(match.est_start) }}</p>
    </div>
    <div class="min-w-0 flex-1">
      <p v-if="showRound || showLevel" class="mb-0.5 truncate text-[10px] text-white/45">
        <template v-if="showLevel">{{ match.level_name }} · </template>{{ roundLabel(match, t) }}
      </p>
      <div v-for="side in sides" :key="side" class="flex items-center gap-2" :class="lost(side) ? 'opacity-50' : ''">
        <span class="min-w-0 flex-1 truncate text-[13px]" :class="[won(side) ? 'font-bold text-white' : 'text-white/85', match[side].team_name ? '' : 'text-white/45 italic']">
          {{ sideLabel(match[side], t) }}
        </span>
        <span v-if="match.sets" class="flex shrink-0 gap-1.5 font-display text-[13px] tabular-nums">
          <b v-for="(p, i) in points(side)" :key="i" class="w-5 text-right" :class="won(side) ? 'text-[#7ff0b4]' : 'font-normal text-white/70'">{{ p }}</b>
        </span>
      </div>
    </div>
  </div>
</template>
