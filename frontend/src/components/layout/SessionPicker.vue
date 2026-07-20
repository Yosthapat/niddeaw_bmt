<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useSessionsStore } from '@/stores/sessions'
import { getClubSettings } from '@/api/admin'
import { ApiError } from '@/api/client'

const sessionsStore = useSessionsStore()
const creating = ref(false)
const newLocation = ref('')
const newCourtFee = ref(80)
const newShuttlecockPrice = ref(29)
const createError = ref<string | null>(null)

onMounted(async () => {
  sessionsStore.refresh()
  try {
    const settings = await getClubSettings()
    newCourtFee.value = settings.default_court_fee_per_person
    newShuttlecockPrice.value = settings.default_shuttlecock_price_per_game
  } catch {
    // Club settings not seeded yet — keep the hardcoded defaults above.
  }
})

async function createToday(): Promise<void> {
  if (!newLocation.value.trim()) return
  createError.value = null
  try {
    await sessionsStore.createSession({
      date: new Date().toISOString().slice(0, 10),
      location: newLocation.value.trim(),
      court_fee_per_person: newCourtFee.value,
      shuttlecock_price_per_game: newShuttlecockPrice.value,
    })
    creating.value = false
    newLocation.value = ''
  } catch (e) {
    createError.value = e instanceof ApiError ? `สร้าง session ไม่สำเร็จ (${e.status}: ${e.message})` : 'สร้าง session ไม่สำเร็จ'
  }
}
</script>

<template>
  <div class="flex flex-wrap items-center gap-2 hud-panel border border-brand-pink/20 bg-brand-surface p-3">
    <span class="text-sm text-white/60">Session:</span>
    <select
      v-if="sessionsStore.sessions.length > 0"
      :value="sessionsStore.currentSessionId ?? ''"
      class="rounded-lg border border-brand-pink/25 bg-brand-black px-2 py-1 text-sm"
      @change="sessionsStore.setCurrentSession(($event.target as HTMLSelectElement).value || null)"
    >
      <option v-for="s in sessionsStore.sessions" :key="s.id" :value="s.id">
        {{ s.date }} · {{ s.location }} ({{ s.status }})
      </option>
    </select>
    <span v-else class="text-sm text-white/40">ยังไม่มี session</span>

    <button
      v-if="!creating"
      class="rounded-full bg-brand-pink px-3 py-1 text-sm font-semibold text-brand-black"
      @click="creating = true"
    >
      + สร้าง session วันนี้
    </button>
    <template v-else>
      <input
        v-model="newLocation"
        placeholder="สถานที่"
        class="w-32 rounded-lg border border-brand-pink/25 bg-brand-black px-2 py-1 text-sm"
      />
      <input
        v-model.number="newCourtFee"
        type="number"
        min="0"
        placeholder="ค่าสนาม/คน"
        title="ค่าสนามต่อคน (บาท)"
        class="w-24 rounded-lg border border-brand-pink/25 bg-brand-black px-2 py-1 text-sm"
      />
      <input
        v-model.number="newShuttlecockPrice"
        type="number"
        min="0"
        placeholder="ค่าลูก/เกม"
        title="ค่าลูกแบดต่อเกม (บาท)"
        class="w-24 rounded-lg border border-brand-pink/25 bg-brand-black px-2 py-1 text-sm"
      />
      <button class="rounded-full bg-brand-pink px-3 py-1 text-sm font-semibold text-brand-black" @click="createToday">
        บันทึก
      </button>
      <button class="text-sm text-white/50" @click="creating = false">ยกเลิก</button>
    </template>
    <p v-if="createError" class="w-full text-xs text-status-error">{{ createError }}</p>
  </div>
</template>
