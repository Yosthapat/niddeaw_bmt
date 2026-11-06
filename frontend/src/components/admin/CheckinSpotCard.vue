<script setup lang="ts">
/**
 * Tonight's pin for checking in by location. An admin at the court taps
 * "pin here": their phone's GPS becomes the centre of a circle, and a
 * linked member whose phone is inside it can check in from LINE without
 * the QR. Turning it off (or the night closing) stops that at once.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import * as adminApi from '@/api/admin'
import type { CheckinSpot } from '@/api/admin'
import { apiErrorMessage } from '@/api/errors'
import { formatTime } from '@/utils/format'
import { FixError, locate } from '@/utils/geo'
import type { Checkin } from '@/types'
import type { Locale } from '@/i18n'

const props = defineProps<{ sessionId: string; checkins: Checkin[] }>()
const { t, locale } = useI18n()

const RADII = [50, 100, 200] as const
const spot = ref<CheckinSpot | null>(null)
const loaded = ref(false)
const radius = ref<number>(100)
const busy = ref<'' | 'locating' | 'saving'>('')
const problem = ref('')

const viaGps = computed(() => props.checkins.filter((c) => c.via === 'gps' && c.checkout_time === null).length)
const mapUrl = computed(() => (spot.value ? `https://www.google.com/maps?q=${spot.value.lat},${spot.value.lng}` : ''))

async function load(): Promise<void> {
  loaded.value = false
  problem.value = ''
  try {
    spot.value = await adminApi.getCheckinSpot(props.sessionId)
    if (spot.value) radius.value = spot.value.radius_m
  } catch (e) {
    problem.value = apiErrorMessage(e, t('checkinGps.loadFailed'))
  } finally {
    loaded.value = true
  }
}

async function pinHere(): Promise<void> {
  if (busy.value) return
  problem.value = ''
  busy.value = 'locating'
  try {
    const fix = await locate(10000)
    busy.value = 'saving'
    spot.value = await adminApi.pinCheckinSpot(props.sessionId, { ...fix, radius_m: radius.value })
  } catch (e) {
    problem.value = e instanceof FixError ? t(`checkinGps.${e.problem}Admin`) : apiErrorMessage(e, t('checkinGps.pinFailed'))
  } finally {
    busy.value = ''
  }
}

// A new radius keeps the pin where it is.
async function setRadius(r: number): Promise<void> {
  radius.value = r
  if (!spot.value || busy.value || spot.value.radius_m === r) return
  busy.value = 'saving'
  problem.value = ''
  try {
    const { lat, lng, accuracy_m } = spot.value
    spot.value = await adminApi.pinCheckinSpot(props.sessionId, { lat, lng, accuracy: accuracy_m ?? 0, radius_m: r })
  } catch (e) {
    problem.value = apiErrorMessage(e, t('checkinGps.pinFailed'))
  } finally {
    busy.value = ''
  }
}

async function turnOff(): Promise<void> {
  if (busy.value) return
  busy.value = 'saving'
  problem.value = ''
  try {
    await adminApi.unpinCheckinSpot(props.sessionId)
    spot.value = null
  } catch (e) {
    problem.value = apiErrorMessage(e, t('checkinGps.pinFailed'))
  } finally {
    busy.value = ''
  }
}

watch(() => props.sessionId, load, { immediate: true })
</script>

<template>
  <section class="spot hud-panel mt-3 flex flex-col gap-3 px-4 py-3.5" :class="{ on: !!spot }" :aria-label="t('checkinGps.title')">
    <div class="flex items-start gap-3">
      <span class="pin flex h-10 w-10 flex-none items-center justify-center rounded-full" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor"><path d="M12 2a7 7 0 0 0-7 7c0 5.2 7 13 7 13s7-7.8 7-13a7 7 0 0 0-7-7Zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5Z" /></svg>
      </span>
      <div class="min-w-0 flex-1">
        <p class="flex flex-wrap items-center gap-x-2 text-sm font-semibold">
          {{ t('checkinGps.title') }}
          <span v-if="spot" class="state-on rounded-full px-2 text-[11px]">{{ t('checkinGps.on') }}</span>
          <span v-else-if="loaded" class="rounded-full bg-white/10 px-2 text-[11px] text-white/65">{{ t('checkinGps.off') }}</span>
        </p>
        <p v-if="spot" class="mt-0.5 text-xs text-white/65">
          {{ t('checkinGps.onInfo', { r: spot.radius_m }) }}
          <template v-if="spot.accuracy_m !== null"> · ±{{ spot.accuracy_m }} {{ t('checkinGps.metre') }}</template>
          <template v-if="spot.pinned_at"> · {{ t('checkinGps.pinnedAt', { time: formatTime(spot.pinned_at, locale as Locale) }) }}</template>
          · <a :href="mapUrl" target="_blank" rel="noopener" class="underline">{{ t('checkinGps.map') }}</a>
        </p>
        <p v-else class="mt-0.5 text-xs text-white/65">{{ t('checkinGps.offInfo') }}</p>
        <p v-if="spot && viaGps" class="mt-1 text-xs text-[#7fd4ff]">{{ t('checkinGps.viaCount', { n: viaGps }) }}</p>
      </div>
    </div>

    <div class="flex flex-wrap items-center gap-2">
      <span class="text-xs text-white/60">{{ t('checkinGps.radius') }}</span>
      <div role="radiogroup" :aria-label="t('checkinGps.radius')" class="flex gap-1 rounded-full bg-white/7 p-1">
        <button
          v-for="r in RADII"
          :key="r"
          type="button"
          role="radio"
          :aria-checked="radius === r"
          class="min-h-9 rounded-full px-3 text-xs"
          :class="radius === r ? 'bg-white font-semibold text-brand-black' : 'text-white/75'"
          :disabled="!!busy"
          @click="setRadius(r)"
        >
          {{ r }} {{ t('checkinGps.metre') }}
        </button>
      </div>
    </div>

    <div class="flex gap-2">
      <button type="button" class="pin-btn tap flex-1 rounded-full px-4 text-sm font-semibold" :disabled="!!busy" @click="pinHere">
        {{ busy === 'locating' ? t('checkinGps.locating') : busy === 'saving' ? t('checkinGps.saving') : spot ? t('checkinGps.repin') : t('checkinGps.pin') }}
      </button>
      <button v-if="spot" type="button" class="tap rounded-full border border-white/25 px-4 text-sm text-white/80" :disabled="!!busy" @click="turnOff">
        {{ t('checkinGps.turnOff') }}
      </button>
    </div>
    <p class="text-[11px] leading-snug text-white/50">{{ t('checkinGps.adminHint') }}</p>
    <p v-if="problem" class="text-sm text-status-error" role="alert">{{ problem }}</p>
  </section>
</template>

<style scoped>
.spot {
  border: 1px solid rgb(255 255 255 / 0.12);
}
.spot.on {
  border-color: rgb(127 212 255 / 0.45);
  background: linear-gradient(rgb(63 182 240 / 0.1), rgb(63 182 240 / 0.03));
}
.pin {
  color: #7fd4ff;
  background: rgb(127 212 255 / 0.14);
}
.state-on {
  background: rgb(127 212 255 / 0.2);
  color: #a9e6ff;
}
.pin-btn {
  background: linear-gradient(#a9e6ff, #3fb6f0);
  color: #03202e;
}
.pin-btn:disabled {
  opacity: 0.6;
}
</style>
