<script setup lang="ts">
/**
 * One match of the day: its number, estimated time and round, and the two
 * teams with their players' avatars and nicknames (CupTeamLine). Shared by
 * /tournament, the LINE page and the admins' draw screen.
 */
import { useI18n } from 'vue-i18n'
import type { CupMatch } from '@/api/tournament'
import { clock, roundLabel, slotLabel } from '@/utils/cupMatch'
import CupTeamLine from './CupTeamLine.vue'

const props = defineProps<{ match: CupMatch; showLevel?: boolean; mineId?: string | null }>()
const { t } = useI18n()
/** each side's points, set by set: "21 · 18" */
const points = (side: 0 | 1): string => (props.match.sets ?? []).map((s) => s[side]).join(' · ')
const lost = (side: 'a' | 'b'): boolean => props.match.status === 'done' && props.match.winner !== 'draw' && props.match.winner !== side
</script>

<template>
  <article class="rounded-xl bg-white/5 px-3 py-2.5" :class="match.status === 'on_court' ? 'ring-1 ring-[#7ff0b4]/60' : ''">
    <header class="mb-2 flex items-baseline gap-2 text-xs">
      <b class="font-display text-sm text-white">#{{ match.match_no }}</b>
      <span v-if="match.status === 'on_court'" class="rounded-full bg-[#7ff0b4] px-2 py-0.5 font-display text-[11px] font-bold text-[#0a2a1a]">
        {{ t('cup.day.onCourt', { n: match.court }) }}
      </span>
      <span v-else-if="match.status === 'done'" class="font-display text-[11px] font-bold text-white/60">{{ match.walkover ? t('cup.day.walkover') : t('cup.day.final') }}</span>
      <span v-else-if="match.est_start" class="font-display text-white/80">{{ clock(match.est_start) }}</span>
      <span class="ml-auto truncate text-white/50">
        <template v-if="showLevel">{{ match.level_name }} · </template>{{ roundLabel(match, t) }}
      </span>
    </header>
    <div class="flex items-center gap-2" :class="lost('a') ? 'opacity-55' : ''">
      <CupTeamLine class="flex-1" :name="match.a.team_name" :players="match.a.players" :placeholder="slotLabel(match.a.slot, t)" :mine="!!mineId && match.a.team_id === mineId" />
      <b v-if="match.sets" class="shrink-0 font-display text-sm" :class="match.winner === 'a' ? 'text-[#7ff0b4]' : ''">{{ points(0) }}</b>
    </div>
    <div class="my-1 flex items-center gap-2 pl-[62px]" aria-hidden="true">
      <span class="font-display text-[11px] font-bold tracking-widest text-[#ff6cc0]/80">VS</span>
      <span class="h-px flex-1 bg-white/10" />
    </div>
    <div class="flex items-center gap-2" :class="lost('b') ? 'opacity-55' : ''">
      <CupTeamLine class="flex-1" :name="match.b.team_name" :players="match.b.players" :placeholder="slotLabel(match.b.slot, t)" :mine="!!mineId && match.b.team_id === mineId" />
      <b v-if="match.sets" class="shrink-0 font-display text-sm" :class="match.winner === 'b' ? 'text-[#7ff0b4]' : ''">{{ points(1) }}</b>
    </div>
    <slot />
  </article>
</template>
