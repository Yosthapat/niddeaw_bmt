<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useSessionsStore } from '@/stores/sessions'
import { usePlayersStore } from '@/stores/players'
import * as adminApi from '@/api/admin'
import { usePolling } from '@/composables/usePolling'
import type { Checkin } from '@/types'
import AdminNav from '@/components/layout/AdminNav.vue'
import SessionPicker from '@/components/layout/SessionPicker.vue'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'
import EloBadge from '@/components/players/EloBadge.vue'

const sessionsStore = useSessionsStore()
const playersStore = usePlayersStore()

const checkins = ref<Checkin[]>([])
const newPlayerName = ref('')
const addingPlayer = ref(false)

const activeCheckins = computed(() => checkins.value.filter((c) => c.checkout_time === null))
const activePlayerIds = computed(() => new Set(activeCheckins.value.map((c) => c.player_id)))
const availablePlayers = computed(() =>
  playersStore.players.filter((p) => p.is_active && !activePlayerIds.value.has(p.id)),
)

async function refreshCheckins(): Promise<void> {
  if (!sessionsStore.currentSessionId) {
    checkins.value = []
    return
  }
  checkins.value = await adminApi.getCheckins(sessionsStore.currentSessionId)
}

async function doCheckin(playerId: string): Promise<void> {
  if (!sessionsStore.currentSessionId) return
  await adminApi.checkinPlayer(sessionsStore.currentSessionId, playerId)
  await refreshCheckins()
}

async function doCheckout(checkinId: string): Promise<void> {
  await adminApi.checkoutPlayer(checkinId)
  await refreshCheckins()
}

async function quickAddPlayer(): Promise<void> {
  if (!newPlayerName.value.trim()) return
  await playersStore.createPlayer({ name: newPlayerName.value.trim() })
  newPlayerName.value = ''
  addingPlayer.value = false
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
    <h1 class="text-2xl font-bold text-brand-pink">เช็คอิน</h1>
    <div class="mt-4">
      <SessionPicker />
    </div>

    <section class="mt-6">
      <div class="flex items-center justify-between">
        <h2 class="text-sm font-semibold text-white/70">สมาชิกทั้งหมด</h2>
        <button v-if="!addingPlayer" class="text-xs text-brand-pink underline" @click="addingPlayer = true">
          + เพิ่มสมาชิกใหม่
        </button>
      </div>
      <div v-if="addingPlayer" class="mt-2 flex gap-2">
        <input
          v-model="newPlayerName"
          placeholder="ชื่อสมาชิกใหม่"
          class="flex-1 rounded-lg border border-brand-pink-dark/40 bg-brand-black px-2 py-1 text-sm"
        />
        <button class="rounded-full bg-brand-pink px-3 py-1 text-sm font-semibold text-brand-black" @click="quickAddPlayer">
          บันทึก
        </button>
        <button class="text-sm text-white/50" @click="addingPlayer = false">ยกเลิก</button>
      </div>
    </section>

    <p v-if="!sessionsStore.currentSessionId" class="mt-8 text-white/60">
      เลือกหรือสร้าง session ก่อนเช็คอิน
    </p>

    <template v-else>
      <section class="mt-8">
        <h2 class="text-sm font-semibold text-white/70">
          กำลังเช็คอิน ({{ activeCheckins.length }})
        </h2>
        <ul class="mt-2 space-y-2">
          <li
            v-for="c in activeCheckins"
            :key="c.id"
            class="flex items-center gap-3 rounded-xl border border-brand-pink-dark/40 bg-white/5 px-3 py-2"
          >
            <PlayerAvatar
              :name="playersStore.byId(c.player_id)?.name ?? '?'"
              :avatar-url="playersStore.byId(c.player_id)?.avatar_url"
              size="sm"
            />
            <span class="flex-1 font-medium">
              {{ playersStore.byId(c.player_id)?.nickname || playersStore.byId(c.player_id)?.name }}
            </span>
            <EloBadge v-if="playersStore.byId(c.player_id)" :elo-score="playersStore.byId(c.player_id)!.elo_score" />
            <span class="text-xs text-white/40">
              {{ new Date(c.checkin_time).toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' }) }}
            </span>
            <button
              class="rounded-full border border-brand-pink px-3 py-1 text-xs text-brand-pink hover:bg-brand-pink hover:text-brand-black"
              @click="doCheckout(c.id)"
            >
              เช็คเอาท์
            </button>
          </li>
          <li v-if="activeCheckins.length === 0" class="text-sm text-white/40">ยังไม่มีใครเช็คอิน</li>
        </ul>
      </section>

      <section class="mt-8">
        <h2 class="text-sm font-semibold text-white/70">สมาชิกที่ยังไม่เช็คอิน</h2>
        <ul class="mt-2 grid gap-2 sm:grid-cols-2">
          <li
            v-for="p in availablePlayers"
            :key="p.id"
            class="flex items-center gap-3 rounded-xl border border-brand-pink-dark/40 bg-white/5 px-3 py-2"
          >
            <PlayerAvatar :name="p.name" :avatar-url="p.avatar_url" size="sm" />
            <span class="flex-1">{{ p.nickname || p.name }}</span>
            <button
              class="rounded-full bg-brand-pink px-3 py-1 text-xs font-semibold text-brand-black"
              @click="doCheckin(p.id)"
            >
              เช็คอิน
            </button>
          </li>
        </ul>
      </section>
    </template>
  </main>
</template>
