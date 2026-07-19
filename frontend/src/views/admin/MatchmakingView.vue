<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useSessionsStore } from '@/stores/sessions'
import { usePlayersStore } from '@/stores/players'
import * as adminApi from '@/api/admin'
import { usePolling } from '@/composables/usePolling'
import type { MatchmakingQueueResponse } from '@/types'
import AdminNav from '@/components/layout/AdminNav.vue'
import SessionPicker from '@/components/layout/SessionPicker.vue'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'

const sessionsStore = useSessionsStore()
const playersStore = usePlayersStore()

const queue = ref<MatchmakingQueueResponse | null>(null)
const confirming = ref<number | null>(null)

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

async function confirmSuggestion(groupNo: number): Promise<void> {
  if (!sessionsStore.currentSessionId || !queue.value) return
  const suggestion = queue.value.suggestions.find((s) => s.group_no === groupNo)
  if (!suggestion) return
  confirming.value = groupNo
  try {
    await adminApi.confirmMatch({
      session_id: sessionsStore.currentSessionId,
      type: 'double',
      team1_player_ids: suggestion.team1_player_ids,
      team2_player_ids: suggestion.team2_player_ids,
    })
    await refreshQueue()
  } finally {
    confirming.value = null
  }
}

watch(() => sessionsStore.currentSessionId, refreshQueue)

onMounted(async () => {
  await Promise.all([sessionsStore.refresh(), playersStore.ensureLoaded()])
  await refreshQueue()
})

usePolling(refreshQueue, 7000)
</script>

<template>
  <AdminNav />
  <main class="mx-auto max-w-4xl px-4 py-6">
    <h1 class="text-2xl font-bold text-brand-pink">จับคู่ (Matchmaking)</h1>
    <div class="mt-4">
      <SessionPicker />
    </div>

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
            class="flex items-center justify-between gap-3 rounded-xl border border-brand-pink-dark/40 bg-white/5 px-4 py-3"
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
            class="flex items-center justify-between gap-3 rounded-xl border border-brand-pink-dark/40 bg-white/5 px-4 py-3"
          >
            <span class="flex-1 text-right">{{ s.team1_player_ids.map(nameOf).join(' & ') }}</span>
            <span class="text-xs text-white/40">VS</span>
            <span class="flex-1">{{ s.team2_player_ids.map(nameOf).join(' & ') }}</span>
            <button
              :disabled="confirming === s.group_no"
              class="shrink-0 rounded-full border border-brand-pink px-3 py-1 text-xs text-brand-pink hover:bg-brand-pink hover:text-brand-black disabled:opacity-50"
              @click="confirmSuggestion(s.group_no)"
            >
              {{ confirming === s.group_no ? '...' : 'ยืนยัน' }}
            </button>
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
            class="flex items-center gap-2 rounded-full border border-brand-pink-dark/40 bg-white/5 px-3 py-1.5 text-sm"
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
