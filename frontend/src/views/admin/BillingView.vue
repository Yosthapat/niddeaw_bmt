<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useSessionsStore } from '@/stores/sessions'
import { usePlayersStore } from '@/stores/players'
import * as adminApi from '@/api/admin'
import { effectiveAmount } from '@/types'
import type { Billing } from '@/types'
import AdminNav from '@/components/layout/AdminNav.vue'
import SessionPicker from '@/components/layout/SessionPicker.vue'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'

const sessionsStore = useSessionsStore()
const playersStore = usePlayersStore()

const billings = ref<Billing[]>([])
const closing = ref(false)
const qrByBillingId = ref<Record<string, string>>({})
const editingAdjust = ref<Record<string, string>>({})

function nameOf(playerId: string): string {
  const p = playersStore.byId(playerId)
  return p ? p.nickname || p.name : '?'
}

async function refreshBillings(): Promise<void> {
  if (!sessionsStore.currentSessionId) {
    billings.value = []
    return
  }
  billings.value = await adminApi.getBillings(sessionsStore.currentSessionId)
}

async function closeAndBill(): Promise<void> {
  if (!sessionsStore.currentSessionId) return
  closing.value = true
  try {
    billings.value = await adminApi.closeSessionAndBill(sessionsStore.currentSessionId)
    await sessionsStore.refresh()
  } finally {
    closing.value = false
  }
}

async function saveAdjust(billing: Billing): Promise<void> {
  const raw = editingAdjust.value[billing.id]
  const amount = raw === '' || raw === undefined ? null : Number(raw)
  const updated = await adminApi.adjustBilling(billing.id, amount)
  billings.value = billings.value.map((b) => (b.id === updated.id ? updated : b))
  delete editingAdjust.value[billing.id]
}

async function togglePaid(billing: Billing): Promise<void> {
  const updated = await adminApi.setBillingPaidStatus(
    billing.id,
    billing.paid_status === 'paid' ? 'unpaid' : 'paid',
  )
  billings.value = billings.value.map((b) => (b.id === updated.id ? updated : b))
}

async function showQr(billing: Billing): Promise<void> {
  if (qrByBillingId.value[billing.id]) {
    delete qrByBillingId.value[billing.id]
    return
  }
  const { data_uri } = await adminApi.getBillingQrCode(billing.id)
  qrByBillingId.value[billing.id] = data_uri
}

watch(() => sessionsStore.currentSessionId, refreshBillings)

onMounted(async () => {
  await Promise.all([sessionsStore.refresh(), playersStore.ensureLoaded()])
  await refreshBillings()
})
</script>

<template>
  <AdminNav />
  <main class="mx-auto max-w-3xl px-4 py-6">
    <h1 class="text-2xl font-bold text-brand-pink">คิดเงิน</h1>
    <div class="mt-4">
      <SessionPicker />
    </div>

    <p v-if="!sessionsStore.currentSessionId" class="mt-8 text-white/60">เลือกหรือสร้าง session ก่อน</p>

    <template v-else>
      <div class="mt-6 flex items-center justify-between">
        <p class="text-sm text-white/60">
          Status: <span class="font-semibold text-white">{{ sessionsStore.currentSession?.status }}</span>
        </p>
        <button
          v-if="sessionsStore.currentSession?.status === 'open'"
          :disabled="closing"
          class="rounded-full bg-brand-pink px-4 py-1.5 text-sm font-semibold text-brand-black disabled:opacity-50"
          @click="closeAndBill"
        >
          {{ closing ? 'กำลังปิด...' : 'ปิด Session และคิดเงิน' }}
        </button>
      </div>

      <p v-if="billings.length === 0" class="mt-6 text-sm text-white/40">
        ยังไม่มีบิล — ปิด session เพื่อคำนวณค่าสนาม + ค่าลูกตามจำนวนเกมที่เล่น
      </p>

      <ul v-else class="mt-6 space-y-3">
        <li
          v-for="b in billings"
          :key="b.id"
          class="hud-panel border border-brand-pink/20 bg-brand-surface p-4"
        >
          <div class="flex items-center gap-3">
            <PlayerAvatar :name="nameOf(b.player_id)" size="sm" />
            <span class="flex-1 font-medium">{{ nameOf(b.player_id) }}</span>
            <span class="text-xs text-white/40">{{ b.game_count }} เกม</span>
            <span class="font-bold text-brand-pink">฿{{ effectiveAmount(b).toFixed(2) }}</span>
            <button
              class="rounded-full px-3 py-1 text-xs font-semibold"
              :class="b.paid_status === 'paid' ? 'bg-green-500/20 text-green-400' : 'bg-white/10 text-white/60'"
              @click="togglePaid(b)"
            >
              {{ b.paid_status === 'paid' ? 'จ่ายแล้ว' : 'ยังไม่จ่าย' }}
            </button>
          </div>

          <div class="mt-2 flex flex-wrap items-center gap-2 text-xs">
            <span class="text-white/40">ยอดคำนวณ: ฿{{ b.amount_calc.toFixed(2) }}</span>
            <input
              v-model="editingAdjust[b.id]"
              type="number"
              :placeholder="b.amount_adjusted?.toString() ?? 'ปรับยอด'"
              class="w-24 rounded border border-brand-pink-dark/40 bg-brand-black px-2 py-0.5"
            />
            <button class="text-brand-pink underline" @click="saveAdjust(b)">บันทึกยอดปรับ</button>
            <button class="text-brand-pink underline" @click="showQr(b)">
              {{ qrByBillingId[b.id] ? 'ซ่อน QR' : 'แสดง PromptPay QR' }}
            </button>
          </div>

          <img
            v-if="qrByBillingId[b.id]"
            :src="qrByBillingId[b.id]"
            alt="PromptPay QR"
            class="mx-auto mt-3 h-40 w-40 rounded-lg bg-white p-2"
          />
        </li>
      </ul>
    </template>
  </main>
</template>
