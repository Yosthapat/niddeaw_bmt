<script setup lang="ts">
/**
 * Checking in by where the phone is: the OA menu's "เช็คอิน" opens
 * /line/checkin, which starts here straight away — find the phone, and if
 * it is inside the circle an admin pinned at the court tonight, the member
 * is checked in, no QR. Who is checked in comes from their LINE token on
 * the server; only where they are comes from this page.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as lineApi from '@/api/line'
import type { LineGpsCheckin } from '@/api/line'
import { apiErrorMessage } from '@/api/errors'
import { formatDateWithWeekday, formatTime } from '@/utils/format'
import { FixError, type FixProblem, locate } from '@/utils/geo'
import type { Locale } from '@/i18n'

const props = defineProps<{ token: string; canScan: boolean }>()
const emit = defineEmits<{ scan: []; done: [] }>()
const { t, locale } = useI18n()

type Phase = 'locating' | 'sending' | 'result' | 'problem'
const phase = ref<Phase>('locating')
const result = ref<LineGpsCheckin | null>(null)
const fixProblem = ref<FixProblem | null>(null)
const problem = ref('')

const night = computed(() =>
  result.value?.night ? formatDateWithWeekday(result.value.night.date, locale.value as Locale) : '',
)
// "about 350 m" reads better than "352 m" for a phone that is ±30 m
const away = computed(() => {
  const d = result.value?.distance_m ?? 0
  return d >= 1000 ? t('checkinGps.km', { n: (d / 1000).toFixed(1) }) : t('checkinGps.m', { n: Math.round(d / 10) * 10 })
})

async function run(): Promise<void> {
  phase.value = 'locating'
  fixProblem.value = null
  problem.value = ''
  try {
    const fix = await locate()
    phase.value = 'sending'
    result.value = await lineApi.checkInNearby(props.token, fix)
    phase.value = 'result'
  } catch (e) {
    if (e instanceof FixError) fixProblem.value = e.problem
    else problem.value = apiErrorMessage(e, t('lineCheckin.failed'))
    phase.value = 'problem'
  }
}

onMounted(run)
</script>

<template>
  <section class="flex flex-1 flex-col items-center gap-4 text-center" aria-live="polite">
    <!-- finding the phone, then asking the server -->
    <template v-if="phase === 'locating' || phase === 'sending'">
      <span class="pin-pulse mt-10 flex h-28 w-28 items-center justify-center rounded-full" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="52" height="52" fill="currentColor"><path d="M12 2a7 7 0 0 0-7 7c0 5.2 7 13 7 13s7-7.8 7-13a7 7 0 0 0-7-7Zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5Z" /></svg>
      </span>
      <h1 class="world-title text-2xl">{{ phase === 'locating' ? t('checkinGps.locating') : t('lineCheckin.sending') }}</h1>
      <p class="text-sm text-white/65">{{ t('checkinGps.locatingHint') }}</p>
    </template>

    <!-- in -->
    <template v-else-if="phase === 'result' && result?.state === 'in'">
      <span class="done-ring mt-8 flex h-28 w-28 items-center justify-center rounded-full text-[#7ff0b4]" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="60" height="60" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>
      </span>
      <h1 class="world-title text-3xl">{{ t('lineCheckin.doneTitle') }}</h1>
      <p class="text-white/80">
        {{ result.player?.nickname }}
        <template v-if="result.checkin_time"> · {{ formatTime(result.checkin_time, locale as Locale) }}</template>
        · {{ t('lineCheckin.doneWait') }}
      </p>
      <p class="text-sm text-white/60">📍 {{ result.night?.location }} · {{ night }}</p>
      <ul class="world-card w-full space-y-2 p-4 text-left text-sm">
        <li><span class="text-[#7ff0b4]">●</span> {{ t('lineCheckin.doneSeen') }}</li>
        <li><span class="text-white/40">●</span> {{ t('lineCheckin.doneLive') }}</li>
      </ul>
      <div class="mt-auto flex w-full flex-col gap-2">
        <RouterLink to="/live" class="glass-pill w-full justify-center">{{ t('lineCheckin.toLive') }}</RouterLink>
        <button type="button" class="min-h-11 text-sm text-white/60" @click="emit('done')">{{ t('line.close') }}</button>
      </div>
    </template>

    <!-- anything else: say why, and what to do instead -->
    <template v-else>
      <img src="/tiers/milk.webp" alt="" width="120" height="120" class="mt-6 h-28 w-28 object-contain opacity-90" />
      <template v-if="fixProblem">
        <h1 class="world-title text-2xl">{{ t(`checkinGps.${fixProblem}Title`) }}</h1>
        <p class="text-white/75">{{ t(`checkinGps.${fixProblem}Body`) }}</p>
      </template>
      <template v-else-if="result?.state === 'far'">
        <h1 class="world-title text-2xl">{{ t('checkinGps.farTitle') }}</h1>
        <p class="text-white/75">{{ t('checkinGps.farBody', { away, place: result.night?.location ?? '' }) }}</p>
      </template>
      <template v-else-if="result?.state === 'weak'">
        <h1 class="world-title text-2xl">{{ t('checkinGps.weakTitle') }}</h1>
        <p class="text-white/75">{{ t('checkinGps.weakBody') }}</p>
      </template>
      <template v-else-if="result?.state === 'none'">
        <h1 class="world-title text-2xl">{{ t('checkinGps.noneTitle') }}</h1>
        <p class="text-white/75">{{ t('checkinGps.noneBody') }}</p>
      </template>
      <template v-else-if="result?.state === 'unlinked'">
        <h1 class="world-title text-2xl">{{ t('lineCheckin.unlinkedTitle') }}</h1>
        <p class="text-white/75">{{ t('lineCheckin.unlinkedBody') }}</p>
      </template>
      <p v-else class="text-status-error" role="alert">{{ problem }}</p>
      <div class="mt-auto flex w-full flex-col gap-2">
        <button
          v-if="fixProblem !== 'unsupported' && result?.state !== 'unlinked'"
          type="button"
          class="cta min-h-14 rounded-2xl font-display text-base font-bold"
          @click="run"
        >
          {{ t('checkinGps.again') }}
        </button>
        <button v-if="canScan" type="button" class="glass-pill w-full justify-center" @click="emit('scan')">{{ t('lineCheckin.scan') }}</button>
        <button type="button" class="min-h-11 text-sm text-white/60" @click="emit('done')">{{ t('line.close') }}</button>
      </div>
    </template>
  </section>
</template>

<style scoped>
.pin-pulse {
  color: #7fd4ff;
  background: rgb(127 212 255 / 0.12);
  box-shadow: 0 0 0 2px rgb(127 212 255 / 0.7);
  animation: pin-pulse 1.4s ease-out infinite;
}
@keyframes pin-pulse {
  0% {
    box-shadow:
      0 0 0 2px rgb(127 212 255 / 0.7),
      0 0 0 0 rgb(127 212 255 / 0.45);
  }
  100% {
    box-shadow:
      0 0 0 2px rgb(127 212 255 / 0.7),
      0 0 0 28px rgb(127 212 255 / 0);
  }
}
@media (prefers-reduced-motion: reduce) {
  .pin-pulse {
    animation: none;
  }
}
.done-ring {
  background: rgb(127 240 180 / 0.14);
  box-shadow:
    0 0 0 2px #7ff0b4,
    0 0 40px rgb(127 240 180 / 0.35);
}
.cta {
  background: linear-gradient(#ff8fd0, #ea4ca4);
  color: #1a0410;
  box-shadow: 0 8px 22px rgb(234 76 164 / 0.45);
}
</style>
