<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { usePlayersStore } from '@/stores/players'
import * as adminApi from '@/api/admin'
import { ApiError } from '@/api/client'
import type { SetScore } from '@/types'
import AdminNav from '@/components/layout/AdminNav.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const playersStore = usePlayersStore()

const matchId = computed(() => String(route.query.match_id ?? ''))
const team1Ids = computed(() => String(route.query.team1 ?? '').split(',').filter(Boolean))
const team2Ids = computed(() => String(route.query.team2 ?? '').split(',').filter(Boolean))

function nameOf(playerId: string): string {
  const p = playersStore.byId(playerId)
  return p ? p.nickname : '?'
}

const sets = ref<SetScore[]>([
  [0, 0],
  [0, 0],
  [0, 0],
])
const submitting = ref(false)
const error = ref<string | null>(null)

const validSets = computed(() => sets.value.filter(([a, b]) => a !== 0 || b !== 0))

async function submit(): Promise<void> {
  if (!matchId.value || validSets.value.length === 0) return
  submitting.value = true
  error.value = null
  try {
    await adminApi.recordMatchResult(matchId.value, validSets.value)
    router.push('/admin/matchmaking')
  } catch (e) {
    error.value = e instanceof ApiError ? `${t('matchRecord.failed')} (${e.status}: ${e.message})` : t('matchRecord.failed')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  playersStore.ensureLoaded()
})
</script>

<template>
  <AdminNav />
  <main class="mx-auto max-w-lg px-4 py-6">
    <h1 class="text-2xl font-bold text-brand-pink">{{ t('matchRecord.title') }}</h1>

    <p v-if="!matchId" class="mt-8 text-white/60">
      {{ t('matchRecord.notFound') }}
      <RouterLink to="/admin/matchmaking" class="text-brand-pink underline">{{ t('admin.nav.matchmaking') }}</RouterLink>
    </p>

    <template v-else>
      <div class="mt-4 flex items-center justify-between text-sm">
        <span class="flex-1 text-right font-medium">{{ team1Ids.map(nameOf).join(' & ') }}</span>
        <span class="mx-3 text-white/40">VS</span>
        <span class="flex-1 font-medium">{{ team2Ids.map(nameOf).join(' & ') }}</span>
      </div>

      <div class="mt-6 space-y-3">
        <div v-for="(setScore, i) in sets" :key="i" class="flex items-center justify-center gap-3">
          <span class="w-16 text-right text-xs text-white/40">{{ t('matchRecord.set') }} {{ i + 1 }}</span>
          <input
            v-model.number="setScore[0]"
            type="number"
            min="0"
            class="w-16 rounded-lg border border-brand-pink/25 bg-brand-surface px-2 py-1 text-center"
          />
          <span class="text-white/40">-</span>
          <input
            v-model.number="setScore[1]"
            type="number"
            min="0"
            class="w-16 rounded-lg border border-brand-pink/25 bg-brand-surface px-2 py-1 text-center"
          />
        </div>
      </div>

      <p v-if="error" class="mt-4 text-center text-sm text-status-error">{{ error }}</p>

      <button
        :disabled="submitting || validSets.length === 0"
        class="mt-6 w-full rounded-lg bg-brand-pink px-3 py-2 font-semibold text-brand-black disabled:opacity-50"
        @click="submit"
      >
        {{ submitting ? t('common.saving') : t('matchRecord.submit') }}
      </button>
    </template>
  </main>
</template>
