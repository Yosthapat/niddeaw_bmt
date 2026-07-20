<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useSessionsStore } from '@/stores/sessions'
import { usePlayersStore } from '@/stores/players'
import * as adminApi from '@/api/admin'
import { ApiError } from '@/api/client'
import { usePolling } from '@/composables/usePolling'
import type { MatchmakingQueueResponse, PairingSuggestion } from '@/types'
import AdminNav from '@/components/layout/AdminNav.vue'
import SessionPicker from '@/components/layout/SessionPicker.vue'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'

const sessionsStore = useSessionsStore()
const playersStore = usePlayersStore()

const queue = ref<MatchmakingQueueResponse | null>(null)
const confirming = ref<number | null>(null)
const confirmError = ref<string | null>(null)

const editingGroup = ref<number | null>(null)
const draftByGroup = ref<Record<number, { team1: string[]; team2: string[] }>>({})

function apiErrorMessage(e: unknown, fallback: string): string {
  if (e instanceof ApiError) {
    return `${fallback} (${e.status}: ${e.message})`
  }
  return fallback
}

function nameOf(playerId: string): string {
  const p = playersStore.byId(playerId)
  return p ? p.nickname || p.name : '?'
}

async function refreshQueue(): Promise<void> {
  if (!sessionsStore.currentSessionId) {
    queue.value = null
    return
  }
  queue.value = await adminApi.getMatchmakingQueue(sessionsStore.currentSessionId)
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
    confirmError.value = apiErrorMessage(e, 'ยืนยันคู่ไม่สำเร็จ')
  } finally {
    confirming.value = null
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
    <h1 class="text-2xl font-bold text-brand-pink">จับคู่ (Matchmaking)</h1>
    <div class="mt-4">
      <SessionPicker />
    </div>

    <p v-if="confirmError" class="mt-4 text-sm text-status-error">{{ confirmError }}</p>

    <p v-if="!sessionsStore.currentSessionId" class="mt-8 text-white/60">
      เลือกหรือสร้าง session ก่อน
    </p>

    <template v-else-if="queue">
      <section class="mt-6">
        <h2 class="text-sm font-semibold text-white/70">กำลังแข่ง ({{ queue.in_progress.length }})</h2>
        <ul class="mt-2 space-y-2">
          <li
            v-for="m in queue.in_progress"
            :key="m.match_id"
            class="flex items-center justify-between gap-3 hud-panel border border-brand-pink/20 bg-brand-surface px-4 py-3"
          >
            <span class="flex-1 text-right">{{ m.team1_player_ids.map(nameOf).join(' & ') }}</span>
            <span class="text-xs text-white/40">VS</span>
            <span class="flex-1">{{ m.team2_player_ids.map(nameOf).join(' & ') }}</span>
            <RouterLink
              :to="{
                path: '/admin/matches/record',
                query: {
                  match_id: m.match_id,
                  team1: m.team1_player_ids.join(','),
                  team2: m.team2_player_ids.join(','),
                },
              }"
              class="shrink-0 rounded-full bg-brand-pink px-3 py-1 text-xs font-semibold text-brand-black"
            >
              บันทึกผล
            </RouterLink>
          </li>
          <li v-if="queue.in_progress.length === 0" class="text-sm text-white/40">ไม่มีแมตช์ที่กำลังแข่ง</li>
        </ul>
      </section>

      <section class="mt-8">
        <h2 class="text-sm font-semibold text-white/70">แนะนำคู่ถัดไป</h2>
        <ul class="mt-2 space-y-2">
          <li
            v-for="s in queue.suggestions"
            :key="s.group_no"
            class="hud-panel border border-brand-pink/20 bg-brand-surface px-4 py-3"
          >
            <div v-if="editingGroup !== s.group_no" class="flex items-center justify-between gap-3">
              <span class="flex-1 text-right">{{ s.team1_player_ids.map(nameOf).join(' & ') }}</span>
              <span class="text-xs text-white/40">VS</span>
              <span class="flex-1">{{ s.team2_player_ids.map(nameOf).join(' & ') }}</span>
              <div class="flex shrink-0 gap-2">
                <button
                  class="rounded-full border border-white/20 px-3 py-1 text-xs text-white/60 hover:border-brand-pink hover:text-brand-pink"
                  @click="startEdit(s)"
                >
                  แก้คู่
                </button>
                <button
                  :disabled="confirming === s.group_no"
                  class="rounded-full border border-brand-pink px-3 py-1 text-xs text-brand-pink hover:bg-brand-pink hover:text-brand-black disabled:opacity-50"
                  @click="confirmSuggestion(s.group_no)"
                >
                  {{ confirming === s.group_no ? '...' : 'ยืนยัน' }}
                </button>
              </div>
            </div>

            <div v-else class="space-y-3">
              <div class="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <p class="mb-1 text-white/40">ทีม 1</p>
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
                  <p class="mb-1 text-white/40">ทีม 2</p>
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
                เลือกผู้เล่นคนเดียวกันซ้ำ — แก้ก่อนยืนยัน
              </p>
              <div class="flex gap-2">
                <button
                  :disabled="confirming === s.group_no || draftHasDuplicate(s.group_no)"
                  class="rounded-full bg-brand-pink px-3 py-1 text-xs font-semibold text-brand-black disabled:opacity-50"
                  @click="confirmSuggestion(s.group_no)"
                >
                  {{ confirming === s.group_no ? '...' : 'ยืนยันคู่ที่แก้ไข' }}
                </button>
                <button class="text-xs text-white/50" @click="cancelEdit(s.group_no)">ยกเลิก</button>
              </div>
            </div>
          </li>
          <li v-if="queue.suggestions.length === 0" class="text-sm text-white/40">
            รอผู้เล่นเช็คอินให้ครบ 4 คนเพื่อจัดคู่
          </li>
        </ul>
      </section>

      <section class="mt-8">
        <h2 class="text-sm font-semibold text-white/70">รอคิว ({{ queue.waiting.length }})</h2>
        <ul class="mt-2 flex flex-wrap gap-2">
          <li
            v-for="w in queue.waiting"
            :key="w.player_id"
            class="flex items-center gap-2 rounded-full border border-brand-pink/25 bg-brand-surface px-3 py-1.5 text-sm"
          >
            <PlayerAvatar :name="nameOf(w.player_id)" size="sm" />
            {{ nameOf(w.player_id) }}
            <span class="text-xs text-white/40">~{{ Math.round(w.estimated_wait_minutes) }} นาที</span>
          </li>
        </ul>
      </section>
    </template>
  </main>
</template>
