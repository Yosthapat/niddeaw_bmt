<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSessionsStore } from '@/stores/sessions'
import { getClubSettings } from '@/api/admin'
import { ApiError } from '@/api/client'
import { useConfirmDialog } from '@/composables/useConfirmDialog'

const { t } = useI18n()
const sessionsStore = useSessionsStore()
const { confirm } = useConfirmDialog()
const creating = ref(false)
const closedSessions = computed(() => sessionsStore.sessions.filter((s) => s.status === 'closed'))

const COURT_OPTIONS = ['KB badminton court โยธินพัฒนา', 'Guy badminton court']
const CUSTOM_OPTION = '__custom__'

const locationChoice = ref(COURT_OPTIONS[0])
const customLocation = ref('')
const newCourtFee = ref(80)
const newShuttlecockPrice = ref(29)
const createError = ref<string | null>(null)

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
  const location = locationChoice.value === CUSTOM_OPTION ? customLocation.value.trim() : locationChoice.value
  if (!location) return
  createError.value = null
  try {
    await sessionsStore.createSession({
      date: new Date().toISOString().slice(0, 10),
      location,
      court_fee_per_person: newCourtFee.value,
      shuttlecock_price_per_game: newShuttlecockPrice.value,
    })
    creating.value = false
    locationChoice.value = COURT_OPTIONS[0]
    customLocation.value = ''
  } catch (e) {
    createError.value = e instanceof ApiError ? `${t('session.createFailed')} (${e.status}: ${e.message})` : t('session.createFailed')
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
    createError.value = e instanceof ApiError ? `${t('session.deleteFailed')} (${e.status}: ${e.message})` : t('session.deleteFailed')
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <div class="flex flex-wrap items-center gap-2 hud-panel border border-brand-pink/20 bg-brand-surface p-3">
    <span class="text-sm text-white/60">Session:</span>
    <select
      v-if="sessionsStore.sessions.length > 0"
      :value="sessionsStore.currentSessionId ?? ''"
      class="rounded-lg border border-brand-pink/25 bg-brand-black px-2 py-1 text-sm"
      @change="sessionsStore.setCurrentSession(($event.target as HTMLSelectElement).value || null)"
    >
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
      v-if="sessionsStore.currentSession"
      :disabled="deleting"
      class="rounded-full border border-status-error/50 px-3 py-1 text-xs text-status-error hover:bg-status-error/10 disabled:opacity-50"
      @click="deleteCurrent"
    >
      {{ deleting ? t('session.deleting') : t('session.deleteThis') }}
    </button>

    <button
      v-if="!creating"
      class="rounded-full bg-brand-pink px-3 py-1 text-sm font-semibold text-brand-black"
      @click="creating = true"
    >
      + {{ t('session.createToday') }}
    </button>
    <template v-else>
      <select
        v-model="locationChoice"
        class="rounded-lg border border-brand-pink/25 bg-brand-black px-2 py-1 text-sm"
      >
        <option v-for="loc in COURT_OPTIONS" :key="loc" :value="loc">{{ loc }}</option>
        <option :value="CUSTOM_OPTION">{{ t('session.locationCustom') }}</option>
      </select>
      <input
        v-if="locationChoice === CUSTOM_OPTION"
        v-model="customLocation"
        :placeholder="t('session.location')"
        class="w-32 rounded-lg border border-brand-pink/25 bg-brand-black px-2 py-1 text-sm"
      />
      <input
        v-model.number="newCourtFee"
        type="number"
        min="0"
        :placeholder="t('session.courtFee')"
        :title="t('session.courtFeeTitle')"
        class="w-24 rounded-lg border border-brand-pink/25 bg-brand-black px-2 py-1 text-sm"
      />
      <input
        v-model.number="newShuttlecockPrice"
        type="number"
        min="0"
        :placeholder="t('session.shuttlecockPrice')"
        :title="t('session.shuttlecockPriceTitle')"
        class="w-24 rounded-lg border border-brand-pink/25 bg-brand-black px-2 py-1 text-sm"
      />
      <button class="rounded-full bg-brand-pink px-3 py-1 text-sm font-semibold text-brand-black" @click="createToday">
        {{ t('common.save') }}
      </button>
      <button class="text-sm text-white/50" @click="creating = false">{{ t('common.cancel') }}</button>
    </template>
    <p v-if="createError" class="w-full text-xs text-status-error">{{ createError }}</p>
  </div>
</template>
