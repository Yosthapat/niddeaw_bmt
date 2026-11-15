<script setup lang="ts">
/** The tournament side's own log: what its admins changed, and when. The
 *  club's log never shows these, and this one never shows the club's. */
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import AdminNav from '@/components/layout/AdminNav.vue'
import LocalisedDateInput from '@/components/common/LocalisedDateInput.vue'
import { tournamentAdmin, type TournamentActivity } from '@/api/tournament'
import { apiErrorMessage } from '@/api/errors'
import { actionKey } from '@/utils/activityAction'
import { formatDateTime } from '@/utils/format'
import type { Locale } from '@/i18n'

const { t, locale } = useI18n()
const entries = ref<TournamentActivity[]>([])
const day = ref('')
const loading = ref(true)
const problem = ref('')

async function refresh(): Promise<void> {
  loading.value = true
  problem.value = ''
  try {
    entries.value = await tournamentAdmin.activity(day.value || undefined)
  } catch (e) {
    problem.value = apiErrorMessage(e, t('cup.admin.loadFailed'))
  } finally {
    loading.value = false
  }
}
watch(day, refresh)
onMounted(refresh)

function label(e: TournamentActivity): string {
  const key = actionKey(e.method, e.path)
  return key ? t(`activityLog.actions.${key}`) : e.action
}
</script>

<template>
  <AdminNav />
  <main class="mx-auto max-w-3xl px-4 py-6">
    <h1 class="sr-only">{{ t('admin.nav.tActivity') }}</h1>
    <div class="flex gap-2.5">
      <LocalisedDateInput v-model="day" :placeholder="t('activityLog.anyDate')" :aria-label="t('activityLog.anyDate')" />
    </div>
    <p v-if="loading" class="mt-6 text-white/60">{{ t('common.loading') }}</p>
    <p v-else-if="problem" class="mt-6 text-status-error">{{ problem }}</p>
    <p v-else-if="!entries.length" class="mt-6 text-sm text-white/40">{{ t('activityLog.empty') }}</p>
    <ul v-else class="mt-6 space-y-2">
      <li v-for="e in entries" :key="e.id" class="hud-panel border border-brand-pink/15 bg-brand-surface px-4 py-3">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div>
            <span class="font-medium text-brand-pink">{{ e.admin_username }}</span>
            <span class="ml-2 text-white/80">{{ label(e) }}</span>
          </div>
          <span class="text-xs text-white/40">{{ formatDateTime(e.created_at, locale as Locale) }}</span>
        </div>
      </li>
    </ul>
  </main>
</template>
