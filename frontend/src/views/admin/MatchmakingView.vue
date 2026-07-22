<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSessionsStore } from '@/stores/sessions'
import { usePlayersStore } from '@/stores/players'
import * as adminApi from '@/api/admin'
import { ApiError } from '@/api/client'
import { usePolling } from '@/composables/usePolling'
import type { MatchmakingQueueResponse, PairingSuggestion } from '@/types'
import AdminNav from '@/components/layout/AdminNav.vue'
import SessionPicker from '@/components/layout/SessionPicker.vue'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'

const { t } = useI18n()
const sessionsStore = useSessionsStore()
const playersStore = usePlayersStore()

const queue = ref<MatchmakingQueueResponse | null>(null)
const confirming = ref<number | null>(null)
const confirmError = ref<string | null>(null)

const cancelling = ref<string | null>(null)
const cancelError = ref<string | null>(null)

const editingGroup = ref<number | null>(null)
const draftByGroup = ref<Record<number, { team1: string[]; team2: string[] }>>({})

const creatingCustom = ref(false)
const customConfirming = ref(false)
const customDraft = ref<{ team1: string[]; team2: string[] }>({ team1: ['', ''], team2: ['', ''] })

function apiErrorMessage(e: unknown, fallback: string): string {
  if (e instanceof ApiError) {
    return `${fallback} (${e.status}: ${e.message})`
  }
  return fallback
}

function nameOf(playerId: string): string {
  const p = playersStore.byId(playerId)
  return p ? p.nickname : '?'
}

function avatarOf(playerId: string): string | undefined {
  return playersStore.byId(playerId)?.avatar_url ?? undefined
}

async function refreshQueue(): Promise<void> {
  if (!sessionsStore.currentSessionId) {
    queue.value = null
    return
  }
  queue.value = await adminApi.getMatchmakingQueue(sessionsStore.currentSessionId)
}

async function cancelMatch(matchId: string, team1: string, team2: string): Promise<void> {
  const confirmed = window.confirm(t('matchmaking.cancelConfirm', { team1, team2 }))
  if (!confirmed) return
  cancelling.value = matchId
  cancelError.value = null
  try {
    await adminApi.cancelMatch(matchId)
    await refreshQueue()
  } catch (e) {
    cancelError.value = apiErrorMessage(e, t('matchmaking.cancelFailed'))
  } finally {
    cancelling.value = null
  }
}

function availablePool(): { id: string; name: string }[] {
  if (!queue.value) return []
  const ids = new Set<string>()
  for (const s of queue.value.suggestions) {
    for (const id of s.team1_player_ids) ids.add(id)
    for (const id of s.team2_player_ids) ids.add(id)
  }
  for (const w of queue.value.waiting) ids.add(w.player_id)
  return Array.from(ids).map((id) => ({ id, name: nameOf(id) }))
}

function draftHasDuplicate(groupNo: number): boolean {
  const d = draftByGroup.value[groupNo]
  if (!d) return false
  const all = [...d.team1, ...d.team2]
  return new Set(all).size !== all.length
}

function startEdit(s: PairingSuggestion): void {
  editingGroup.value = s.group_no
  draftByGroup.value[s.group_no] = {
    team1: [...s.team1_player_ids],
    team2: [...s.team2_player_ids],
  }
  pollControls.stop()
}

function cancelEdit(groupNo: number): void {
  editingGroup.value = null
  delete draftByGroup.value[groupNo]
  pollControls.start()
}

async function confirmSuggestion(groupNo: number): Promise<void> {
  if (!sessionsStore.currentSessionId || !queue.value) return
  const suggestion = queue.value.suggestions.find((s) => s.group_no === groupNo)
  if (!suggestion) return
  const draft = draftByGroup.value[groupNo]
  const team1 = draft ? draft.team1 : suggestion.team1_player_ids
  const team2 = draft ? draft.team2 : suggestion.team2_player_ids
  if (draft && draftHasDuplicate(groupNo)) return
  confirming.value = groupNo
  confirmError.value = null
  try {
    await adminApi.confirmMatch({
      session_id: sessionsStore.currentSessionId,
      type: 'double',
      team1_player_ids: team1,
      team2_player_ids: team2,
    })
    editingGroup.value = null
    delete draftByGroup.value[groupNo]
    pollControls.start()
    await refreshQueue()
  } catch (e) {
    confirmError.value = apiErrorMessage(e, t('matchmaking.confirmFailed'))
  } finally {
    confirming.value = null
  }
}

function customHasDuplicate(): boolean {
  const all = [...customDraft.value.team1, ...customDraft.value.team2].filter(Boolean)
  return new Set(all).size !== all.length
}

function customIsComplete(): boolean {
  return [...customDraft.value.team1, ...customDraft.value.team2].every((id) => id !== '')
}

function startCustomMatch(): void {
  customDraft.value = { team1: ['', ''], team2: ['', ''] }
  creatingCustom.value = true
  pollControls.stop()
}

function cancelCustomMatch(): void {
  creatingCustom.value = false
  pollControls.start()
}

async function confirmCustomMatch(): Promise<void> {
  if (!sessionsStore.currentSessionId) return
  if (!customIsComplete() || customHasDuplicate()) return
  customConfirming.value = true
  confirmError.value = null
  try {
    await adminApi.confirmMatch({
      session_id: sessionsStore.currentSessionId,
      type: 'double',
      team1_player_ids: customDraft.value.team1,
      team2_player_ids: customDraft.value.team2,
    })
    creatingCustom.value = false
    pollControls.start()
    await refreshQueue()
  } catch (e) {
    confirmError.value = apiErrorMessage(e, t('matchmaking.confirmFailed'))
  } finally {
    customConfirming.value = false
  }
}

watch(() => sessionsStore.currentSessionId, refreshQueue)

onMounted(async () => {
  await Promise.all([sessionsStore.refresh(), playersStore.ensureLoaded()])
  await refreshQueue()
})

const pollControls = usePolling(refreshQueue, 7000)
</script>

<template>
  <AdminNav />
  <main class="mx-auto max-w-4xl px-4 py-6">
    <h1 class="text-2xl font-bold text-brand-pink">{{ t('admin.nav.matchmaking') }} (Matchmaking)</h1>
    <div class="mt-4">
      <SessionPicker />
    </div>

    <p v-if="confirmError" class="mt-4 text-sm text-status-error">{{ confirmError }}</p>
    <p v-if="cancelError" class="mt-4 text-sm text-status-error">{{ cancelError }}</p>

    <p v-if="!sessionsStore.currentSessionId" class="mt-8 text-white/60">
      {{ t('matchmaking.selectSessionFirst') }}
    </p>

    <template v-else-if="queue">
      <section class="mt-6">
        <h2 class="text-sm font-semibold text-white/70">{{ t('matchmaking.inProgress') }} ({{ queue.in_progress.length }})</h2>
        <ul class="mt-2 space-y-2">
          <li
            v-for="m in queue.in_progress"
            :key="m.match_id"
            class="hud-panel border border-brand-pink/20 bg-brand-surface px-4 py-3"
          >
            <div class="flex items-center justify-between gap-3">
              <div class="flex flex-1 flex-col items-end gap-1.5">
                <div class="flex items-center gap-2">
                  <span class="text-right font-medium text-white/80">{{ m.team1_player_ids.map(nameOf).join(' & ') }}</span>
                  <div class="flex -space-x-2">
                    <PlayerAvatar
                      v-for="pid in m.team1_player_ids"
                      :key="pid"
                      :name="nameOf(pid)"
                      :avatar-url="avatarOf(pid)"
                      size="md"
                    />
                  </div>
                </div>
              </div>

              <span class="hud-panel shrink-0 border border-brand-pink/20 bg-brand-black px-2.5 py-1 text-xs font-semibold text-white/50 uppercase">
                {{ t('matches.inProgress') }}
              </span>

              <div class="flex flex-1 flex-col items-start gap-1.5">
                <div class="flex items-center gap-2">
                  <div class="flex -space-x-2">
                    <PlayerAvatar
                      v-for="pid in m.team2_player_ids"
                      :key="pid"
                      :name="nameOf(pid)"
                      :avatar-url="avatarOf(pid)"
                      size="md"
                    />
                  </div>
                  <span class="font-medium text-white/80">{{ m.team2_player_ids.map(nameOf).join(' & ') }}</span>
                </div>
              </div>
            </div>
            <div class="mt-2 flex items-center justify-center gap-2">
              <RouterLink
                :to="{
                  path: '/admin/matches/record',
                  query: {
                    match_id: m.match_id,
                    team1: m.team1_player_ids.join(','),
                    team2: m.team2_player_ids.join(','),
                  },
                }"
                class="rounded-full bg-brand-pink px-3 py-1 text-xs font-semibold text-brand-black"
              >
                {{ t('matchmaking.recordResult') }}
              </RouterLink>
              <button
                :disabled="cancelling === m.match_id"
                class="rounded-full border border-white/20 px-3 py-1 text-xs text-white/60 hover:border-status-error hover:text-status-error disabled:opacity-50"
                @click="
                  cancelMatch(m.match_id, m.team1_player_ids.map(nameOf).join(' & '), m.team2_player_ids.map(nameOf).join(' & '))
                "
              >
                {{ cancelling === m.match_id ? t('matchmaking.cancelling') : t('matchmaking.cancelMatch') }}
              </button>
            </div>
          </li>
          <li v-if="queue.in_progress.length === 0" class="text-sm text-white/40">{{ t('matchmaking.noneInProgress') }}</li>
        </ul>
      </section>

      <section class="mt-8">
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-semibold text-white/70">{{ t('matchmaking.nextSuggestion') }}</h2>
          <button
            v-if="!creatingCustom"
            class="rounded-full border border-brand-pink/40 px-3 py-1 text-xs text-brand-pink hover:bg-brand-pink hover:text-brand-black"
            @click="startCustomMatch"
          >
            {{ t('matchmaking.createCustom') }}
          </button>
        </div>

        <div v-if="creatingCustom" class="hud-panel mt-2 border border-brand-pink/20 bg-brand-surface px-4 py-3">
          <div class="grid grid-cols-2 gap-3 text-xs">
            <div>
              <p class="mb-1 text-white/40">{{ t('matchmaking.team') }} 1</p>
              <select
                v-for="(_, i) in customDraft.team1"
                :key="'c1-' + i"
                v-model="customDraft.team1[i]"
                class="mb-1 w-full rounded border border-brand-pink/25 bg-brand-black px-2 py-1"
              >
                <option value="" disabled>{{ t('matchmaking.pickPlayer') }}</option>
                <option v-for="p in availablePool()" :key="p.id" :value="p.id">{{ p.name }}</option>
              </select>
            </div>
            <div>
              <p class="mb-1 text-white/40">{{ t('matchmaking.team') }} 2</p>
              <select
                v-for="(_, i) in customDraft.team2"
                :key="'c2-' + i"
                v-model="customDraft.team2[i]"
                class="mb-1 w-full rounded border border-brand-pink/25 bg-brand-black px-2 py-1"
              >
                <option value="" disabled>{{ t('matchmaking.pickPlayer') }}</option>
                <option v-for="p in availablePool()" :key="p.id" :value="p.id">{{ p.name }}</option>
              </select>
            </div>
          </div>
          <p v-if="customHasDuplicate()" class="mt-2 text-xs text-status-error">
            {{ t('matchmaking.duplicatePlayer') }}
          </p>
          <div class="mt-3 flex gap-2">
            <button
              :disabled="customConfirming || !customIsComplete() || customHasDuplicate()"
              class="rounded-full bg-brand-pink px-3 py-1 text-xs font-semibold text-brand-black disabled:opacity-50"
              @click="confirmCustomMatch"
            >
              {{ customConfirming ? '...' : t('matchmaking.confirm') }}
            </button>
            <button class="text-xs text-white/50" @click="cancelCustomMatch">{{ t('common.cancel') }}</button>
          </div>
        </div>

        <ul class="mt-2 space-y-2">
          <li
            v-for="s in queue.suggestions"
            :key="s.group_no"
            class="hud-panel border border-brand-pink/20 bg-brand-surface px-4 py-3"
          >
            <div v-if="editingGroup !== s.group_no" class="flex items-center justify-between gap-3">
              <div class="flex flex-1 items-center justify-end gap-2">
                <span class="text-right">{{ s.team1_player_ids.map(nameOf).join(' & ') }}</span>
                <div class="flex -space-x-2">
                  <PlayerAvatar
                    v-for="pid in s.team1_player_ids"
                    :key="pid"
                    :name="nameOf(pid)"
                    :avatar-url="avatarOf(pid)"
                    size="sm"
                  />
                </div>
              </div>
              <span class="text-xs text-white/40">VS</span>
              <div class="flex flex-1 items-center gap-2">
                <div class="flex -space-x-2">
                  <PlayerAvatar
                    v-for="pid in s.team2_player_ids"
                    :key="pid"
                    :name="nameOf(pid)"
                    :avatar-url="avatarOf(pid)"
                    size="sm"
                  />
                </div>
                <span>{{ s.team2_player_ids.map(nameOf).join(' & ') }}</span>
              </div>
              <div class="flex shrink-0 gap-2">
                <button
                  class="rounded-full border border-white/20 px-3 py-1 text-xs text-white/60 hover:border-brand-pink hover:text-brand-pink"
                  @click="startEdit(s)"
                >
                  {{ t('matchmaking.editPair') }}
                </button>
                <button
                  :disabled="confirming === s.group_no"
                  class="rounded-full border border-brand-pink px-3 py-1 text-xs text-brand-pink hover:bg-brand-pink hover:text-brand-black disabled:opacity-50"
                  @click="confirmSuggestion(s.group_no)"
                >
                  {{ confirming === s.group_no ? '...' : t('matchmaking.confirm') }}
                </button>
              </div>
            </div>

            <div v-else class="space-y-3">
              <div class="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <p class="mb-1 text-white/40">{{ t('matchmaking.team') }} 1</p>
                  <select
                    v-for="(_, i) in draftByGroup[s.group_no]?.team1 ?? []"
                    :key="'t1-' + i"
                    v-model="draftByGroup[s.group_no].team1[i]"
                    class="mb-1 w-full rounded border border-brand-pink/25 bg-brand-black px-2 py-1"
                  >
                    <option v-for="p in availablePool()" :key="p.id" :value="p.id">{{ p.name }}</option>
                  </select>
                </div>
                <div>
                  <p class="mb-1 text-white/40">{{ t('matchmaking.team') }} 2</p>
                  <select
                    v-for="(_, i) in draftByGroup[s.group_no]?.team2 ?? []"
                    :key="'t2-' + i"
                    v-model="draftByGroup[s.group_no].team2[i]"
                    class="mb-1 w-full rounded border border-brand-pink/25 bg-brand-black px-2 py-1"
                  >
                    <option v-for="p in availablePool()" :key="p.id" :value="p.id">{{ p.name }}</option>
                  </select>
                </div>
              </div>
              <p v-if="draftHasDuplicate(s.group_no)" class="text-xs text-status-error">
                {{ t('matchmaking.duplicatePlayer') }}
              </p>
              <div class="flex gap-2">
                <button
                  :disabled="confirming === s.group_no || draftHasDuplicate(s.group_no)"
                  class="rounded-full bg-brand-pink px-3 py-1 text-xs font-semibold text-brand-black disabled:opacity-50"
                  @click="confirmSuggestion(s.group_no)"
                >
                  {{ confirming === s.group_no ? '...' : t('matchmaking.confirmEdited') }}
                </button>
                <button class="text-xs text-white/50" @click="cancelEdit(s.group_no)">{{ t('common.cancel') }}</button>
              </div>
            </div>
          </li>
          <li v-if="queue.suggestions.length === 0" class="text-sm text-white/40">
            {{ t('matchmaking.waitingForPlayers') }}
          </li>
        </ul>
      </section>

      <section class="mt-8">
        <h2 class="text-sm font-semibold text-white/70">{{ t('matchmaking.inQueue') }} ({{ queue.waiting.length }})</h2>
        <ul class="mt-2 flex flex-wrap gap-2">
          <li
            v-for="w in queue.waiting"
            :key="w.player_id"
            class="flex items-center gap-2 rounded-full border border-brand-pink/25 bg-brand-surface px-3 py-1.5 text-sm"
          >
            <PlayerAvatar :name="nameOf(w.player_id)" :avatar-url="avatarOf(w.player_id)" size="sm" />
            {{ nameOf(w.player_id) }}
            <span class="text-xs text-white/40">~{{ Math.round(w.estimated_wait_minutes) }} {{ t('matches.minutes') }}</span>
          </li>
        </ul>
      </section>
    </template>
  </main>
</template>
