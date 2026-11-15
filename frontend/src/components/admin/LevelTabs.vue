<script setup lang="ts">
/**
 * A tournament's levels as a row of tabs, pinned under the header while the
 * page scrolls — the tournament admin screens show one level at a time, the
 * way /tournament does for players. `allLabel` adds a first tab for every
 * level at once (value '').
 */
import { nextTick, ref, watch } from 'vue'

const props = defineProps<{
  levels: { id: string; name: string; badge?: string }[]
  modelValue: string
  allLabel?: string
  label: string
}>()
const emit = defineEmits<{ 'update:modelValue': [id: string] }>()

const row = ref<HTMLElement | null>(null)
// keep the chosen tab in view when the row is wider than the phone
watch(
  () => props.modelValue,
  async () => {
    await nextTick()
    row.value?.querySelector<HTMLElement>('[aria-selected="true"]')?.scrollIntoView({ block: 'nearest', inline: 'nearest' })
  },
)
</script>

<template>
  <div class="sticky top-[calc(var(--header-h)+6px)] z-10 -mx-4 mt-4 overflow-x-auto px-4 pb-1">
    <div ref="row" class="flex w-max gap-1.5 rounded-full border border-brand-pink/20 bg-brand-black/90 p-1 backdrop-blur" role="tablist" :aria-label="label">
      <button
        v-if="allLabel"
        type="button"
        role="tab"
        class="flex min-h-11 items-center rounded-full px-4 text-sm whitespace-nowrap"
        :class="modelValue === '' ? 'bg-brand-pink font-bold text-brand-black' : 'text-white/75'"
        :aria-selected="modelValue === ''"
        @click="emit('update:modelValue', '')"
      >
        {{ allLabel }}
      </button>
      <button
        v-for="lv in levels"
        :key="lv.id"
        type="button"
        role="tab"
        class="flex min-h-11 items-center gap-1.5 rounded-full px-4 text-sm whitespace-nowrap"
        :class="modelValue === lv.id ? 'bg-brand-pink font-bold text-brand-black' : 'text-white/75'"
        :aria-selected="modelValue === lv.id"
        @click="emit('update:modelValue', lv.id)"
      >
        {{ lv.name }}
        <span v-if="lv.badge" class="text-xs" :class="modelValue === lv.id ? 'text-brand-black/70' : 'text-white/45'">{{ lv.badge }}</span>
      </button>
    </div>
  </div>
</template>
