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

defineProps<{ match: CupMatch; showLevel?: boolean; mineId?: string | null }>()
const { t } = useI18n()
</script>

<template>
  <article class="rounded-xl bg-white/5 px-3 py-2.5">
    <header class="mb-2 flex items-baseline gap-2 text-xs">
      <b class="font-display text-sm text-white">#{{ match.match_no }}</b>
      <span v-if="match.est_start" class="font-display text-white/80">{{ clock(match.est_start) }}</span>
      <span class="ml-auto truncate text-white/50">
        <template v-if="showLevel">{{ match.level_name }} · </template>{{ roundLabel(match, t) }}
      </span>
    </header>
    <CupTeamLine :name="match.a.team_name" :players="match.a.players" :placeholder="slotLabel(match.a.slot, t)" :mine="!!mineId && match.a.team_id === mineId" />
    <div class="my-1 flex items-center gap-2 pl-[62px]" aria-hidden="true">
      <span class="font-display text-[11px] font-bold tracking-widest text-[#ff6cc0]/80">VS</span>
      <span class="h-px flex-1 bg-white/10" />
    </div>
    <CupTeamLine :name="match.b.team_name" :players="match.b.players" :placeholder="slotLabel(match.b.slot, t)" :mine="!!mineId && match.b.team_id === mineId" />
  </article>
</template>
