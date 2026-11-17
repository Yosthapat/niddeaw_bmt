<script setup lang="ts">
/**
 * A tournament's levels as a row of mascot tiles, pinned under the header
 * while the page scrolls — the tournament admin screens show one level at a
 * time, the way /tournament does for players. Every level fits on one row
 * on a phone (each its mascot, name and count), so there is nothing to
 * swipe sideways. `allLabel` adds a first tile for every level at once
 * (value '').
 */
import { computed } from 'vue'
import TierMascot from '@/components/players/TierMascot.vue'
import { levelTiers } from '@/utils/cupMatch'

const props = defineProps<{
  levels: { id: string; name: string; badge?: string; note?: string; min_elo?: number | null; max_elo?: number | null }[]
  modelValue: string
  allLabel?: string
  label: string
}>()
const emit = defineEmits<{ 'update:modelValue': [id: string] }>()

const tiles = computed(() => props.levels.map((lv) => ({ ...lv, tiers: levelTiers({ name: lv.name, min_elo: lv.min_elo ?? null, max_elo: lv.max_elo ?? null }) })))
/** One row up to five tiles; more levels wrap to a second row. */
const columns = computed(() => Math.min(props.levels.length + (props.allLabel ? 1 : 0), 5))
</script>

<template>
  <div class="sticky top-[calc(var(--header-h)+6px)] z-10 mt-4">
    <div
      class="grid gap-1 rounded-[22px] border border-brand-pink/20 bg-brand-black/90 p-1 backdrop-blur"
      :style="{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }"
      role="tablist"
      :aria-label="label"
    >
      <button
        v-if="allLabel"
        type="button"
        role="tab"
        class="flex min-w-0 flex-col items-center justify-end rounded-[18px] px-1 pt-1.5 pb-1 transition-colors"
        :class="modelValue === '' ? 'bg-brand-pink/20 ring-1 ring-brand-pink' : 'hover:bg-white/6'"
        :aria-selected="modelValue === ''"
        @click="emit('update:modelValue', '')"
      >
        <span class="flex h-10 items-center justify-center" :class="modelValue === '' ? 'text-brand-pink' : 'text-white/50'" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" class="h-7 w-7">
            <path d="M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z" />
          </svg>
        </span>
        <span class="w-full truncate text-center font-display text-[12px] leading-[1.8]" :class="modelValue === '' ? 'font-bold text-white' : 'text-white/75'">{{ allLabel }}</span>
        <span class="text-[10px] leading-tight text-transparent" aria-hidden="true">·</span>
      </button>
      <button
        v-for="lv in tiles"
        :key="lv.id"
        type="button"
        role="tab"
        class="flex min-w-0 flex-col items-center rounded-[18px] px-1 pt-1.5 pb-1 transition-colors"
        :class="modelValue === lv.id ? 'bg-brand-pink/20 ring-1 ring-brand-pink' : 'hover:bg-white/6'"
        :aria-selected="modelValue === lv.id"
        :aria-label="[lv.name, lv.badge, lv.note].filter(Boolean).join(' ')"
        @click="emit('update:modelValue', lv.id)"
      >
        <span class="flex h-10 items-end justify-center" :class="modelValue === lv.id ? '' : 'opacity-60 saturate-50'">
          <TierMascot
            v-for="(tier, i) in lv.tiers"
            :key="tier"
            :tier="tier"
            :size="lv.tiers.length > 1 ? 32 : 40"
            :interactive="false"
            :class="i > 0 ? '-ml-3' : ''"
          />
        </span>
        <span class="w-full truncate text-center font-display text-[12px] leading-[1.8]" :class="modelValue === lv.id ? 'font-bold text-white' : 'text-white/75'">
          {{ lv.name }}
        </span>
        <span v-if="lv.badge" class="font-display text-[10px] leading-tight" :class="modelValue === lv.id ? 'text-brand-pink-light' : 'text-white/45'">{{ lv.badge }}</span>
        <span v-if="lv.note" class="w-full truncate text-center text-[10px] leading-tight text-[#ffd34d]">{{ lv.note }}</span>
      </button>
    </div>
  </div>
</template>
