<script setup lang="ts">
/**
 * Tonight's check-in QR, full screen, for a phone or tablet left at the
 * door. Members scan it with their camera (it opens LINE) or from the
 * club's LINE menu, and check themselves in; their names come up here as
 * they do, from the check-in list the page already refreshes.
 *
 * z-40, under the confirm dialog (z-50) that "new QR" opens.
 *
 * The QR is a link with a code only tonight's session accepts. If someone
 * sends a photo of it to the group, "new QR" replaces the code and the
 * photo stops working.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as adminApi from '@/api/admin'
import type { CheckinQr } from '@/api/admin'
import { apiErrorMessage } from '@/api/errors'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { usePlayersStore } from '@/stores/players'
import { formatDateWithWeekday, formatTime } from '@/utils/format'
import type { Locale } from '@/i18n'
import type { Checkin } from '@/types'
import BrandQr from '@/components/common/BrandQr.vue'

const props = defineProps<{ sessionId: string; checkins: Checkin[] }>()
const emit = defineEmits<{ close: [] }>()
const { t, locale } = useI18n()
const { confirm } = useConfirmDialog()
const playersStore = usePlayersStore()

const qr = ref<CheckinQr | null>(null)
const problem = ref('')
const rotating = ref(false)

async function load(): Promise<void> {
  try {
    qr.value = await adminApi.getCheckinQr(props.sessionId)
  } catch (e) {
    problem.value = apiErrorMessage(e, t('checkinQr.loadFailed'))
  }
}

async function rotate(): Promise<void> {
  const ok = await confirm({ title: t('checkinQr.rotate'), message: t('checkinQr.rotateConfirm'), confirmLabel: t('checkinQr.rotateYes') })
  if (!ok) return
  rotating.value = true
  try {
    qr.value = await adminApi.rotateCheckinQr(props.sessionId)
  } catch (e) {
    problem.value = apiErrorMessage(e, t('checkinQr.loadFailed'))
  } finally {
    rotating.value = false
  }
}

const viaLine = computed(() =>
  props.checkins
    .filter((c) => c.via === 'line' && c.checkout_time === null)
    .sort((a, b) => b.checkin_time.localeCompare(a.checkin_time)),
)

// A phone left showing the QR shouldn't dim and lock after a minute.
let wake: { release(): Promise<void> } | null = null
function onKey(e: KeyboardEvent): void {
  if (e.key === 'Escape') emit('close')
}
onMounted(async () => {
  window.addEventListener('keydown', onKey)
  void load()
  try {
    const nav = navigator as Navigator & { wakeLock?: { request(type: 'screen'): Promise<{ release(): Promise<void> }> } }
    wake = (await nav.wakeLock?.request('screen')) ?? null
  } catch {
    wake = null // not allowed here; the screen just dims as usual
  }
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  void wake?.release().catch(() => undefined)
})
</script>

<template>
  <Teleport to="body">
    <div class="qr-screen fixed inset-0 z-40 flex flex-col items-center overflow-y-auto px-5 pt-4 pb-[calc(20px+env(safe-area-inset-bottom,0px))] text-center" role="dialog" aria-modal="true" :aria-label="t('checkinQr.title')">
      <div class="flex w-full max-w-md justify-end">
        <button type="button" class="flex h-11 w-11 items-center justify-center rounded-full bg-white/10 text-white" :aria-label="t('line.close')" @click="emit('close')">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" /></svg>
        </button>
      </div>
      <div class="flex w-full max-w-md flex-1 flex-col items-center gap-3">
        <p v-if="qr" class="font-display text-xs font-bold tracking-[0.3em] text-brand-pink">
          CHECK-IN · {{ formatDateWithWeekday(qr.night.date, locale as Locale) }}
        </p>
        <h2 class="font-display text-2xl font-bold">{{ t('checkinQr.title') }}</h2>
        <p class="text-sm text-white/65">{{ t('checkinQr.how') }}</p>

        <BrandQr v-if="qr" :modules="qr.qr_modules" :caption="t('checkinQr.caption')" :alt="t('checkinQr.title')" class="mt-1 w-[min(300px,74vw)]" />
        <div v-else class="flex h-[min(300px,72vw)] w-[min(300px,72vw)] items-center justify-center rounded-3xl bg-[#f4a6c8]/30 text-sm text-white/70">
          {{ problem || t('common.loading') }}
        </div>
        <p v-if="qr" class="text-xs text-white/50">{{ t('checkinQr.validTonight', { place: qr.night.location }) }}</p>
        <p v-if="problem && qr" class="text-sm text-status-error" role="alert">{{ problem }}</p>

        <span class="inline-flex min-h-9 items-center gap-2 rounded-full bg-[#06c755]/15 px-4 text-sm font-medium text-[#7ff0b4]">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>
          {{ t('checkinQr.viaLine', { n: viaLine.length }) }}
        </span>
        <ul v-if="viaLine.length" class="flex w-full flex-col gap-1.5" aria-live="polite">
          <li v-for="c in viaLine.slice(0, 4)" :key="c.id" class="flex items-center justify-between rounded-xl bg-white/5 px-3 py-2 text-sm">
            <span class="font-medium">{{ playersStore.byId(c.player_id)?.nickname ?? '?' }}</span>
            <span class="text-xs text-white/45">{{ formatTime(c.checkin_time, locale as Locale) }}</span>
          </li>
        </ul>

        <button type="button" class="mt-auto min-h-11 w-full rounded-full border border-white/20 px-4 text-sm text-white/70 disabled:opacity-50" :disabled="rotating || !qr" @click="rotate">
          {{ t('checkinQr.rotate') }}
        </button>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.qr-screen {
  background:
    radial-gradient(600px 400px at 50% 0%, rgb(234 76 164 / 0.25), transparent 70%),
    #080312;
}
</style>
