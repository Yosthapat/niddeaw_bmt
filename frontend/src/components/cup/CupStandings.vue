<script setup lang="ts">
/**
 * A group's table once any of its matches is played: rank, team, played,
 * won-drawn-lost, point difference, points (spec §3.2's order).
 */
import { useI18n } from 'vue-i18n'
import type { PublicTeam, StandingRow } from '@/api/tournament'

const props = defineProps<{ label: string; teams: PublicTeam[]; standings: StandingRow[]; mineId?: string | null }>()
const { t } = useI18n()
const name = (id: string): string => props.teams.find((x) => x.id === id)?.name ?? '?'
const nicks = (id: string): string => (props.teams.find((x) => x.id === id)?.players ?? []).map((p) => p.nickname).join(' · ')
</script>

<template>
  <div class="rounded-xl bg-white/5 p-2.5">
    <p class="mb-1 font-display text-sm font-bold text-[#ff6cc0]">{{ t('cup.draw.group', { g: label }) }}</p>
    <table class="w-full text-xs">
      <thead class="text-white/45">
        <tr>
          <th class="w-5 text-left font-normal">#</th>
          <th class="text-left font-normal">{{ t('cup.table.team') }}</th>
          <th class="w-7 font-normal">{{ t('cup.table.played') }}</th>
          <th class="w-12 font-normal">{{ t('cup.table.wdl') }}</th>
          <th class="w-9 font-normal">+/−</th>
          <th class="w-8 font-normal">{{ t('cup.table.points') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in standings" :key="r.team_id" class="border-t border-white/8" :class="mineId === r.team_id ? 'text-[#ff6cc0]' : ''">
          <td class="py-1.5 font-display">{{ r.rank }}</td>
          <td class="max-w-0 py-1.5">
            <span class="block truncate font-semibold">{{ name(r.team_id) }}</span>
            <span class="block truncate text-[11px] text-white/50">{{ nicks(r.team_id) }}</span>
          </td>
          <td class="text-center">{{ r.played }}</td>
          <td class="text-center">{{ r.won }}-{{ r.drawn }}-{{ r.lost }}</td>
          <td class="text-center">{{ r.diff > 0 ? '+' : '' }}{{ r.diff }}</td>
          <td class="text-center font-display font-bold">{{ r.points }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
