<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import * as adminApi from '@/api/admin'
import { ApiError } from '@/api/client'
import type { Admin, AdminActivityLogEntry } from '@/types'
import AdminNav from '@/components/layout/AdminNav.vue'

const { t, locale } = useI18n()

const entries = ref<AdminActivityLogEntry[]>([])
const admins = ref<Admin[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

const selectedAdminId = ref('')
const selectedDate = ref('')

function apiErrorMessage(e: unknown, fallback: string): string {
  if (e instanceof ApiError) return `${fallback} (${e.status}: ${e.message})`
  return fallback
}

function adminName(adminId: string): string {
  return admins.value.find((a) => a.id === adminId)?.username ?? '?'
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(locale.value === 'th' ? 'th-TH' : 'en-US', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function detailSummary(entry: AdminActivityLogEntry): string {
  if (!entry.detail) return ''
  return Object.values(entry.detail).join(', ')
}

async function loadEntries(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    entries.value = await adminApi.getActivityLog({
      adminId: selectedAdminId.value || undefined,
      date: selectedDate.value || undefined,
    })
  } catch (e) {
    error.value = apiErrorMessage(e, t('activityLog.loadFailed'))
  } finally {
    loading.value = false
  }
}

watch([selectedAdminId, selectedDate], loadEntries)

onMounted(async () => {
  admins.value = await adminApi.getActivityLogAdmins()
  await loadEntries()
})
</script>

<template>
  <AdminNav />
  <main class="mx-auto max-w-3xl px-4 py-6">
    <h1 class="text-2xl font-bold text-brand-pink">{{ t('activityLog.title') }}</h1>

    <div class="mt-4 flex flex-wrap gap-2.5">
      <select
        v-model="selectedAdminId"
        class="rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-sm text-white/80"
      >
        <option value="">{{ t('activityLog.allAdmins') }}</option>
        <option v-for="a in admins" :key="a.id" :value="a.id">{{ a.username }}</option>
      </select>
      <input
        v-model="selectedDate"
        type="date"
        class="rounded-lg border border-brand-pink/25 bg-brand-black px-3 py-2 text-sm text-white/80"
      />
      <button
        v-if="selectedAdminId || selectedDate"
        type="button"
        class="rounded-lg border border-white/15 px-3 py-2 text-sm text-white/50 hover:border-white/30 hover:text-white"
        @click="selectedAdminId = ''; selectedDate = ''"
      >
        {{ t('activityLog.clearFilters') }}
      </button>
    </div>

    <p v-if="loading" class="mt-6 text-white/60">{{ t('common.loading') }}</p>
    <p v-else-if="error" class="mt-6 text-status-error">{{ error }}</p>
    <p v-else-if="entries.length === 0" class="mt-6 text-sm text-white/40">{{ t('activityLog.empty') }}</p>

    <ul v-else class="mt-6 space-y-2">
      <li
        v-for="e in entries"
        :key="e.id"
        class="hud-panel border border-brand-pink/15 bg-brand-surface px-4 py-3"
      >
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div>
            <span class="font-medium text-brand-pink">{{ adminName(e.admin_id) }}</span>
            <span class="ml-2 text-white/80">{{ e.action }}</span>
          </div>
          <span class="text-xs text-white/40">{{ formatDateTime(e.created_at) }}</span>
        </div>
        <p v-if="detailSummary(e)" class="mt-0.5 text-xs text-white/40">{{ detailSummary(e) }}</p>
      </li>
    </ul>
  </main>
</template>
