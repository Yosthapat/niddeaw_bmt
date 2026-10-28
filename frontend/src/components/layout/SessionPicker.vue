<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSessionsStore } from '@/stores/sessions'
import { getClubSettings } from '@/api/admin'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { bahtProblem, localToday, MAX_NAME } from '@/utils/limits'
import { apiErrorMessage } from '@/api/errors'

// "ลบ session นี้" wipes a whole night's check-ins, matches and bills, and
// it used to sit a thumb's width from "+ สร้าง session วันนี้" on every
// admin screen. It belongs where someone goes deliberately to manage
// sessions, so only the dashboard asks for it.
withDefaults(defineProps<{ allowDelete?: boolean }>(), { allowDelete: false })

const { t } = useI18n()
const sessionsStore = useSessionsStore()
const { confirm } = useConfirmDialog()
const creating = ref(false)
const closedSessions = computed(() => sessionsStore.sessions.filter((s) => s.status === 'closed'))
// Tonight is already open: a second "create today's session" beside it is
// one tap from splitting the night's check-ins across two sessions.
const todayIsOpen = computed(() => sessionsStore.openSessions.some((s) => s.date === localToday()))

const COURT_OPTIONS = ['KB badminton court โยธินพัฒนา', 'Guy badminton court']
const CUSTOM_OPTION = '__custom__'

const locationChoice = ref(COURT_OPTIONS[0])
const customLocation = ref('')
const newCourtFee = ref(80)
const newShuttlecockPrice = ref(29)
const createError = ref<string | null>(null)
// Shown only after the first Save, so an empty custom-location box isn't
// red before anyone has typed in it.
const tried = ref(false)

const customLocationProblem = computed(() =>
  locationChoice.value === CUSTOM_OPTION && !customLocation.value.trim() ? t('validation.locationRequired') : null,
)
const courtFeeProblem = computed(() => {
  const p = bahtProblem(newCourtFee.value, { allowZero: true })
  return p ? t(`validation.${p}`) : null
})
const shuttlecockProblem = computed(() => {
  const p = bahtProblem(newShuttlecockPrice.value, { allowZero: true })
  return p ? t(`validation.${p}`) : null
})

onMounted(async () => {
  sessionsStore.refresh()
  try {
    const settings = await getClubSettings()
    newCourtFee.value = settings.default_court_fee_per_person
    newShuttlecockPrice.value = settings.default_shuttlecock_price_per_game
  } catch {
    // Club settings not seeded yet — keep the hardcoded defaults above.
  }
})

async function createToday(): Promise<void> {
  tried.value = true
  if (customLocationProblem.value || courtFeeProblem.value || shuttlecockProblem.value) return
  const location = locationChoice.value === CUSTOM_OPTION ? customLocation.value.trim() : locationChoice.value
  createError.value = null
  try {
    await sessionsStore.createSession({
      date: localToday(),
      location,
      court_fee_per_person: newCourtFee.value,
      shuttlecock_price_per_game: newShuttlecockPrice.value,
    })
    creating.value = false
    tried.value = false
    locationChoice.value = COURT_OPTIONS[0]
    customLocation.value = ''
  } catch (e) {
    createError.value = apiErrorMessage(e, t('session.createFailed'))
  }
}

const deleting = ref(false)

async function deleteCurrent(): Promise<void> {
  const session = sessionsStore.currentSession
  if (!session) return
  const confirmed = await confirm({
    title: t('session.deleteConfirmTitle'),
    message: `${t('session.deleteConfirm', { date: session.date, location: session.location })}\n${t('session.deleteWarning')}`,
    danger: true,
  })
  if (!confirmed) return
  deleting.value = true
  createError.value = null
  try {
    await sessionsStore.deleteSession(session.id)
  } catch (e) {
    createError.value = apiErrorMessage(e, t('session.deleteFailed'))
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <div class="flex flex-wrap items-center gap-2 hud-panel border border-brand-pink/20 bg-brand-surface p-3">
    <label for="session-picker" class="text-sm text-white/60">{{ t('session.label') }}</label>
    <select
      v-if="sessionsStore.sessions.length > 0"
      id="session-picker"
      :value="sessionsStore.currentSessionId ?? ''"
      class="min-h-11 max-w-full min-w-0 flex-1 basis-full truncate rounded-lg border border-brand-pink/25 bg-brand-black px-2 text-sm sm:basis-auto"
      @change="sessionsStore.setCurrentSession(($event.target as HTMLSelectElement).value || null)"
    >
      <!-- With no night open (the morning after one is closed) nothing is
           chosen, and a select with nothing chosen draws as an empty box. -->
      <option v-if="!sessionsStore.currentSessionId" value="" disabled>{{ t('session.pickNight') }}</option>
      <optgroup v-if="sessionsStore.openSessions.length > 0" :label="t('session.openGroup')">
        <option v-for="s in sessionsStore.openSessions" :key="s.id" :value="s.id">{{ s.date }} · {{ s.location }}</option>
      </optgroup>
      <optgroup v-if="closedSessions.length > 0" :label="t('session.closedGroup')">
        <option v-for="s in closedSessions" :key="s.id" :value="s.id">{{ s.date }} · {{ s.location }}</option>
      </optgroup>
    </select>
    <span v-else class="text-sm text-white/40">{{ t('session.none') }}</span>

    <span
      v-if="sessionsStore.currentSession"
      class="rounded-full px-2.5 py-1 text-xs font-semibold whitespace-nowrap"
      :class="
        sessionsStore.currentSession.status === 'open'
          ? 'bg-status-success/20 text-status-success'
          : 'bg-white/10 text-white/50'
      "
    >
      ● {{ sessionsStore.currentSession.status === 'open' ? t('session.statusOpen') : t('session.statusClosed') }}
    </span>

    <button
      v-if="allowDelete && sessionsStore.currentSession"
      :disabled="deleting"
      class="tap rounded-full border border-status-error/50 px-3 text-xs text-status-error hover:bg-status-error/10 disabled:opacity-50"
      @click="deleteCurrent"
    >
      {{ deleting ? t('session.deleting') : t('session.deleteThis') }}
    </button>

    <button
      v-if="!creating && !todayIsOpen"
      class="tap rounded-full bg-brand-pink px-3 text-sm font-semibold text-brand-black"
      @click="creating = true"
    >
      + {{ t('session.createToday') }}
    </button>
    <form v-if="creating" class="grid w-full gap-3 border-t border-brand-pink/15 pt-3 sm:grid-cols-2" novalidate @submit.prevent="createToday">
      <label class="flex flex-col gap-1 text-xs text-white/60 sm:col-span-2">
        {{ t('session.location') }}
        <select v-model="locationChoice" class="min-h-11 rounded-lg border border-brand-pink/25 bg-brand-black px-2 text-sm text-white">
          <option v-for="loc in COURT_OPTIONS" :key="loc" :value="loc">{{ loc }}</option>
          <option :value="CUSTOM_OPTION">{{ t('session.locationCustom') }}</option>
        </select>
      </label>
      <label v-if="locationChoice === CUSTOM_OPTION" class="flex flex-col gap-1 text-xs text-white/60 sm:col-span-2">
        {{ t('session.locationCustom') }}
        <input
          v-model="customLocation"
          :maxlength="MAX_NAME"
          :aria-invalid="tried && !!customLocationProblem"
          class="min-h-11 rounded-lg border border-brand-pink/25 bg-brand-black px-3 text-sm text-white"
        />
        <span v-if="tried && customLocationProblem" class="text-status-error">{{ customLocationProblem }}</span>
      </label>
      <label class="flex flex-col gap-1 text-xs text-white/60">
        {{ t('session.courtFeeTitle') }}
        <input
          v-model.number="newCourtFee"
          type="number"
          inputmode="decimal"
          min="0"
          :aria-invalid="tried && !!courtFeeProblem"
          class="min-h-11 rounded-lg border border-brand-pink/25 bg-brand-black px-3 text-sm text-white"
        />
        <span v-if="tried && courtFeeProblem" class="text-status-error">{{ courtFeeProblem }}</span>
      </label>
      <label class="flex flex-col gap-1 text-xs text-white/60">
        {{ t('session.shuttlecockPriceTitle') }}
        <input
          v-model.number="newShuttlecockPrice"
          type="number"
          inputmode="decimal"
          min="0"
          :aria-invalid="tried && !!shuttlecockProblem"
          class="min-h-11 rounded-lg border border-brand-pink/25 bg-brand-black px-3 text-sm text-white"
        />
        <span v-if="tried && shuttlecockProblem" class="text-status-error">{{ shuttlecockProblem }}</span>
      </label>
      <div class="flex gap-2 sm:col-span-2">
        <button type="submit" class="tap flex-1 rounded-full bg-brand-pink px-4 text-sm font-semibold text-brand-black">
          {{ t('session.createToday') }}
        </button>
        <button type="button" class="tap rounded-full border border-white/20 px-4 text-sm text-white/60" @click="creating = false; tried = false">
          {{ t('common.cancel') }}
        </button>
      </div>
    </form>
    <p v-if="createError" class="w-full text-xs text-status-error">{{ createError }}</p>
  </div>
</template>
