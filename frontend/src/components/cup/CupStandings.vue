<script setup lang="ts">
/**
 * A group's table once any of its matches is played: rank, team, played,
 * won-drawn-lost, point difference, points (spec §3.2's order).
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { PublicTeam, StandingRow } from '@/api/tournament'
import type { Band } from '@/utils/cupMatch'

const props = defineProps<{
  label: string
  teams: PublicTeam[]
  standings: StandingRow[]
  mineId?: string | null
  /** Colour each place by the bracket it leads to, with a key underneath. */
  bands?: Record<number, Band>
}>()
const BAND_STYLE: Record<Band, string> = {
  upper: 'linear-gradient(#ffe14d, #ffe14d)',
  lower: 'linear-gradient(#c9a7ff, #c9a7ff)',
  upperOrLower: 'linear-gradient(#ffe14d 50%, #c9a7ff 50%)',
  lowerOrOut: 'linear-gradient(#c9a7ff 50%, rgb(255 255 255 / 0.25) 50%)',
  out: 'linear-gradient(rgb(255 255 255 / 0.25), rgb(255 255 255 / 0.25))',
}
const bandOf = (rank: number): Band | null => props.bands?.[rank] ?? null
const legend = computed(() => {
  const used = new Set(Object.values(props.bands ?? {}))
  return (['upper', 'upperOrLower', 'lower', 'lowerOrOut', 'out'] as Band[]).filter((b) => used.has(b))
})
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
          <th class="w-6 pl-2 text-left font-normal">#</th>
          <th class="text-left font-normal">{{ t('cup.table.team') }}</th>
          <th class="w-7 font-normal">{{ t('cup.table.played') }}</th>
          <th class="w-12 font-normal">{{ t('cup.table.wdl') }}</th>
          <th class="w-9 font-normal">+/−</th>
          <th class="w-8 font-normal">{{ t('cup.table.points') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in standings" :key="r.team_id" class="border-t border-white/8" :class="mineId === r.team_id ? 'text-[#ff6cc0]' : ''">
          <td class="relative py-1.5 pl-2 font-display">
            <span v-if="bandOf(r.rank)" class="absolute inset-y-1.5 left-0 w-[3px] rounded-full" :style="{ backgroundImage: BAND_STYLE[bandOf(r.rank)!] }" aria-hidden="true" />
            {{ r.rank }}
          </td>
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
    <ul v-if="legend.length" class="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-white/60">
      <li v-for="b in legend" :key="b" class="flex items-center gap-1.5">
        <span class="h-2.5 w-[3px] rounded-full" :style="{ backgroundImage: BAND_STYLE[b] }" aria-hidden="true" />
        {{ t(`cup.band.${b}`) }}
      </li>
    </ul>
  </div>
</template>
