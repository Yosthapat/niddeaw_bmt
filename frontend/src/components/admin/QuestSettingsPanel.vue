<script setup lang="ts">
/** The two quest settings: the day counting began, and the monthly target. */
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getQuestSettings, updateQuestSettings } from '@/api/quests'
import { apiErrorMessage } from '@/api/errors'

const { t } = useI18n()
const start = ref('')
const target = ref(20)
const ready = ref(false)
const off = ref(false)
const saving = ref(false)
const note = ref('')
const problem = ref('')
// counting can't start in the future (the API refuses it too)
const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Bangkok' }).format(new Date())

onMounted(async () => {
  try {
    const s = await getQuestSettings()
    if (!s) {
      off.value = true
      return
    }
    start.value = s.start_date
    target.value = s.monthly_target
    ready.value = true
  } catch {
    off.value = true
  }
})

async function save(): Promise<void> {
  saving.value = true
  note.value = ''
  problem.value = ''
  try {
    const s = await updateQuestSettings({ start_date: start.value, monthly_target: target.value })
    start.value = s.start_date
    target.value = s.monthly_target
    note.value = t('quests.settings.saved')
  } catch (e) {
    problem.value = apiErrorMessage(e, t('quests.settings.failed'))
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <section class="mt-10" aria-labelledby="quest-title">
    <h2 id="quest-title" class="text-sm font-semibold text-white/70">{{ t('quests.settings.title') }}</h2>
    <p class="mt-1 text-xs text-white/50">{{ off ? t('quests.settings.off') : t('quests.settings.hint') }}</p>
    <form v-if="ready" class="mt-3 grid gap-3 sm:grid-cols-2" @submit.prevent="save">
      <label class="flex flex-col gap-1 text-sm">
        <span class="text-white/60">{{ t('quests.settings.start') }}</span>
        <input id="quest-start" v-model="start" type="date" :max="today" required class="min-h-11 rounded-lg border border-brand-pink/25 bg-brand-black px-3 text-base sm:text-sm" />
      </label>
      <label class="flex flex-col gap-1 text-sm">
        <span class="text-white/60">{{ t('quests.settings.target') }}</span>
        <input id="quest-target" v-model.number="target" type="number" inputmode="numeric" min="1" max="200" required class="min-h-11 rounded-lg border border-brand-pink/25 bg-brand-black px-3 text-base sm:text-sm" />
      </label>
      <button type="submit" :disabled="saving" class="tap rounded-full bg-brand-pink px-5 text-sm font-semibold text-brand-black disabled:opacity-50 sm:col-span-2">
        {{ saving ? t('common.saving') : t('quests.settings.save') }}
      </button>
      <p v-if="note" role="status" class="text-sm text-status-success sm:col-span-2">✓ {{ note }}</p>
      <p v-if="problem" role="alert" class="text-sm text-status-error sm:col-span-2">{{ problem }}</p>
    </form>
  </section>
</template>
