<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSessionsStore } from '@/stores/sessions'
import { usePlayersStore } from '@/stores/players'
import * as adminApi from '@/api/admin'
import { ApiError } from '@/api/client'
import { usePolling } from '@/composables/usePolling'
import type { Checkin } from '@/types'
import AdminNav from '@/components/layout/AdminNav.vue'
import SessionPicker from '@/components/layout/SessionPicker.vue'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'
import EloBadge from '@/components/players/EloBadge.vue'
import TierMascot from '@/components/players/TierMascot.vue'

const { t, locale } = useI18n()
const sessionsStore = useSessionsStore()
const playersStore = usePlayersStore()

const checkins = ref<Checkin[]>([])
const newPlayerName = ref('')
const addingPlayer = ref(false)
const actionError = ref<string | null>(null)

const activeCheckins = computed(() => checkins.value.filter((c) => c.checkout_time === null))
const activePlayerIds = computed(() => new Set(activeCheckins.value.map((c) => c.player_id)))
const availablePlayers = computed(() =>
  playersStore.players.filter((p) => p.is_active && !activePlayerIds.value.has(p.id)),
)

function apiErrorMessage(e: unknown, fallback: string): string {
  if (e instanceof ApiError) {
    return `${fallback} (${e.status}: ${e.message})`
  }
  return fallback
}

async function refreshCheckins(): Promise<void> {
  if (!sessionsStore.currentSessionId) {
    checkins.value = []
    return
  }
  checkins.value = await adminApi.getCheckins(sessionsStore.currentSessionId)
}

async function doCheckin(playerId: string): Promise<void> {
  if (!sessionsStore.currentSessionId) return
  actionError.value = null
  try {
    await adminApi.checkinPlayer(sessionsStore.currentSessionId, playerId)
    await refreshCheckins()
  } catch (e) {
    actionError.value = apiErrorMessage(e, t('checkin.checkinFailed'))
  }
}

async function doCheckout(checkinId: string): Promise<void> {
  actionError.value = null
  try {
    await adminApi.checkoutPlayer(checkinId)
    await refreshCheckins()
  } catch (e) {
    actionError.value = apiErrorMessage(e, t('checkin.checkoutFailed'))
  }
}

async function quickAddPlayer(): Promise<void> {
  if (!newPlayerName.value.trim()) return
  actionError.value = null
  try {
    await playersStore.createPlayer({ nickname: newPlayerName.value.trim() })
    newPlayerName.value = ''
    addingPlayer.value = false
  } catch (e) {
    actionError.value = apiErrorMessage(e, t('checkin.addFailed'))
  }
}

watch(() => sessionsStore.currentSessionId, refreshCheckins)

onMounted(async () => {
  await Promise.all([sessionsStore.refresh(), playersStore.ensureLoaded()])
  await refreshCheckins()
})

usePolling(refreshCheckins, 8000)
</script>

<template>
  <AdminNav />
  <main class="mx-auto max-w-4xl px-4 py-6">
    <h1 class="text-2xl font-bold text-brand-pink">{{ t('admin.nav.checkin') }}</h1>
    <div class="mt-4">
      <SessionPicker />
    </div>

    <p v-if="actionError" class="mt-4 text-sm text-status-error">{{ actionError }}</p>

    <section class="mt-6">
      <div class="flex items-center justify-between">
        <h2 class="text-sm font-semibold text-white/70">{{ t('checkin.allMembers') }}</h2>
      </div>
      <div v-if="addingPlayer" class="mt-2 flex gap-2">
        <input
          v-model="newPlayerName"
          :placeholder="t('checkin.newMemberName')"
          class="flex-1 rounded-lg border border-brand-pink/25 bg-brand-black px-2 py-1 text-sm"
        />
        <button class="rounded-full bg-brand-pink px-3 py-1 text-sm font-semibold text-brand-black" @click="quickAddPlayer">
          {{ t('common.save') }}
        </button>
        <button class="text-sm text-white/50" @click="addingPlayer = false">{{ t('common.cancel') }}</button>
      </div>
    </section>

    <p v-if="!sessionsStore.currentSessionId" class="mt-8 text-white/60">
      {{ t('checkin.selectSessionFirst') }}
    </p>

    <template v-else>
      <section class="mt-8">
        <h2 class="text-sm font-semibold text-white/70">
          {{ t('checkin.checkingIn') }} ({{ activeCheckins.length }})
        </h2>
        <ul class="mt-2 space-y-2">
          <li
            v-for="c in activeCheckins"
            :key="c.id"
            class="flex items-center gap-3 hud-panel border border-brand-pink/20 bg-brand-surface px-3 py-2"
          >
            <PlayerAvatar
              :name="playersStore.byId(c.player_id)?.nickname ?? '?'"
              :avatar-url="playersStore.byId(c.player_id)?.avatar_url"
              size="sm"
            />
            <span class="flex-1 font-medium">
              {{ playersStore.byId(c.player_id)?.nickname }}
            </span>
            <TierMascot
              v-if="playersStore.byId(c.player_id)"
              :tier="playersStore.byId(c.player_id)!.elo_level"
              :size="24"
            />
            <EloBadge v-if="playersStore.byId(c.player_id)" :elo-score="playersStore.byId(c.player_id)!.elo_score" />
            <span class="text-xs text-white/40">
              {{ new Date(c.checkin_time).toLocaleTimeString(locale === 'th' ? 'th-TH' : 'en-US', { hour: '2-digit', minute: '2-digit' }) }}
            </span>
            <button
              class="rounded-full border border-brand-pink px-3 py-1 text-xs text-brand-pink hover:bg-brand-pink hover:text-brand-black"
              @click="doCheckout(c.id)"
            >
              {{ t('checkin.checkout') }}
            </button>
          </li>
          <li v-if="activeCheckins.length === 0" class="text-sm text-white/40">{{ t('checkin.noneCheckedIn') }}</li>
        </ul>
      </section>

      <section class="mt-8">
        <h2 class="text-sm font-semibold text-white/70">{{ t('checkin.notCheckedIn') }}</h2>
        <ul class="mt-2 grid gap-2 sm:grid-cols-2">
          <li
            v-for="p in availablePlayers"
            :key="p.id"
            class="flex items-center gap-3 hud-panel border border-brand-pink/20 bg-brand-surface px-3 py-2"
          >
            <PlayerAvatar :name="p.nickname" :avatar-url="p.avatar_url" size="sm" />
            <span class="flex-1">{{ p.nickname }}</span>
            <button
              class="rounded-full bg-brand-pink px-3 py-1 text-xs font-semibold text-brand-black"
              @click="doCheckin(p.id)"
            >
              {{ t('checkin.checkin') }}
            </button>
          </li>
        </ul>
      </section>
    </template>
  </main>
</template>
