<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSessionsStore } from '@/stores/sessions'
import { getClubSettings } from '@/api/admin'
import { ApiError } from '@/api/client'

const { t } = useI18n()
const sessionsStore = useSessionsStore()
const creating = ref(false)
const newLocation = ref('')
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
  if (!newLocation.value.trim()) return
  createError.value = null
  try {
    await sessionsStore.createSession({
      date: new Date().toISOString().slice(0, 10),
      location: newLocation.value.trim(),
      court_fee_per_person: newCourtFee.value,
      shuttlecock_price_per_game: newShuttlecockPrice.value,
    })
    creating.value = false
    newLocation.value = ''
  } catch (e) {
    createError.value = e instanceof ApiError ? `${t('session.createFailed')} (${e.status}: ${e.message})` : t('session.createFailed')
  }
}

const deleting = ref(false)

async function deleteCurrent(): Promise<void> {
  const session = sessionsStore.currentSession
  if (!session) return
  const confirmed = window.confirm(
    `${t('session.deleteConfirm', { date: session.date, location: session.location })}\n${t('session.deleteWarning')}`,
  )
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
      <option v-for="s in sessionsStore.sessions" :key="s.id" :value="s.id">
        {{ s.date }} · {{ s.location }} ({{ s.status }})
      </option>
    </select>
    <span v-else class="text-sm text-white/40">{{ t('session.none') }}</span>

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
      <input
        v-model="newLocation"
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
