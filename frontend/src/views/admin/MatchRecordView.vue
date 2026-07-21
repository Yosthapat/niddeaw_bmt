<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { usePlayersStore } from '@/stores/players'
import * as adminApi from '@/api/admin'
import { ApiError } from '@/api/client'
import type { MatchWinner } from '@/types'
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

const submitting = ref(false)
const error = ref<string | null>(null)

async function submit(winner: MatchWinner): Promise<void> {
  if (!matchId.value) return
  submitting.value = true
  error.value = null
  try {
    await adminApi.recordMatchResult(matchId.value, winner)
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

      <p v-if="error" class="mt-4 text-center text-sm text-status-error">{{ error }}</p>

      <div class="mt-6 space-y-3">
        <button
          :disabled="submitting"
          class="w-full rounded-lg bg-status-success/90 px-3 py-3 text-center font-semibold text-brand-black hover:bg-status-success disabled:opacity-50"
          @click="submit('team1')"
        >
          {{ team1Ids.map(nameOf).join(' & ') }} {{ t('matchRecord.wins') }}
        </button>
        <button
          :disabled="submitting"
          class="w-full rounded-lg border border-brand-pink/25 bg-brand-surface px-3 py-3 text-center font-semibold text-white/80 hover:border-brand-pink disabled:opacity-50"
          @click="submit('draw')"
        >
          {{ t('common.draw') }}
        </button>
        <button
          :disabled="submitting"
          class="w-full rounded-lg bg-status-success/90 px-3 py-3 text-center font-semibold text-brand-black hover:bg-status-success disabled:opacity-50"
          @click="submit('team2')"
        >
          {{ team2Ids.map(nameOf).join(' & ') }} {{ t('matchRecord.wins') }}
        </button>
      </div>

      <p v-if="submitting" class="mt-4 text-center text-sm text-white/50">{{ t('common.saving') }}</p>
    </template>
  </main>
</template>
