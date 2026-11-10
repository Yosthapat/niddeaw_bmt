<script setup lang="ts">
/** What a result did to a team's ELO: ▲ up, ▼ down, ± nothing. */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{ delta: number }>()
const { t } = useI18n()
const kind = computed(() => (props.delta > 0 ? 'up' : props.delta < 0 ? 'down' : 'flat'))
const label = computed(() => (props.delta < 0 ? t('elo.lost', { n: -props.delta }) : t('elo.gained', { n: props.delta })))
</script>

<template>
  <span class="elo-delta" :class="kind" :title="label" :aria-label="label">
    <span aria-hidden="true">{{ kind === 'up' ? '▲' : kind === 'down' ? '▼' : '±' }}</span>{{ Math.abs(delta) }}
  </span>
</template>
