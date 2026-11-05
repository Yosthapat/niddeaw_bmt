<script setup lang="ts">
/**
 * How many members have linked their LINE, on the members page: a bar,
 * the requests still waiting for the admin, the QR that invites the rest,
 * and a filter for the list below (all / linked / not yet).
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

export type LineFilter = 'all' | 'linked' | 'unlinked'

const props = defineProps<{ linked: number; total: number; pending: number }>()
const filter = defineModel<LineFilter>({ required: true })
const emit = defineEmits<{ invite: []; pending: [] }>()
const { t } = useI18n()

const percent = computed(() => (props.total ? Math.round((props.linked / props.total) * 100) : 0))
const options = computed(() => [
  { id: 'all' as LineFilter, label: t('lineSummary.all'), n: props.total },
  { id: 'linked' as LineFilter, label: t('lineSummary.linked'), n: props.linked },
  { id: 'unlinked' as LineFilter, label: t('lineSummary.unlinked'), n: Math.max(0, props.total - props.linked) },
])
</script>

<template>
  <section class="hud-panel mt-4 border border-[#06c755]/30 bg-brand-surface p-4" :aria-label="t('lineSummary.title')">
    <div class="flex items-center justify-between gap-3">
      <div class="min-w-0">
        <p class="flex items-center gap-1.5 text-xs font-semibold whitespace-nowrap text-[#7ff0b4]">
          <span class="h-2 w-2 rounded-full bg-[#06c755]" aria-hidden="true" />
          {{ t('lineSummary.title') }}
        </p>
        <p class="mt-1 font-display text-2xl font-bold whitespace-nowrap">
          {{ linked }}<span class="text-base text-white/50"> / {{ total }} {{ t('lineSummary.people') }}</span>
        </p>
      </div>
      <button type="button" class="tap shrink-0 rounded-full bg-[#06c755] px-4 text-sm font-semibold text-white" @click="emit('invite')">
        {{ t('lineSummary.invite') }}
      </button>
    </div>
    <div
      class="mt-3 h-2 overflow-hidden rounded-full bg-white/10"
      role="progressbar"
      :aria-valuenow="percent"
      aria-valuemin="0"
      aria-valuemax="100"
      :aria-label="t('lineSummary.title')"
    >
      <div class="h-full rounded-full bg-[#06c755]" :style="{ width: percent + '%' }" />
    </div>
    <div class="mt-3 flex flex-wrap gap-2" role="group" :aria-label="t('lineSummary.filter')">
      <button
        v-for="o in options"
        :key="o.id"
        type="button"
        class="tap rounded-full border px-3 text-xs font-semibold"
        :class="filter === o.id ? 'border-[#06c755] bg-[#06c755]/20 text-[#7ff0b4]' : 'border-white/15 text-white/60'"
        :aria-pressed="filter === o.id"
        @click="filter = o.id"
      >
        {{ o.label }} ({{ o.n }})
      </button>
      <button
        v-if="pending > 0"
        type="button"
        class="tap rounded-full bg-[#ffd34d]/15 px-3 text-xs font-semibold text-[#ffd34d]"
        @click="emit('pending')"
      >
        {{ t('lineSummary.pending', { n: pending }) }}
      </button>
    </div>
  </section>
</template>
