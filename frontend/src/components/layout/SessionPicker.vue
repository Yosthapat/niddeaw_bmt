<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useSessionsStore } from '@/stores/sessions'
import { getClubSettings } from '@/api/admin'

const sessionsStore = useSessionsStore()
const creating = ref(false)
const newLocation = ref('')
const newCourtFee = ref(80)
const newShuttlecockPrice = ref(29)

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
  await sessionsStore.createSession({
    date: new Date().toISOString().slice(0, 10),
    location: newLocation.value.trim(),
    court_fee_per_person: newCourtFee.value,
    shuttlecock_price_per_game: newShuttlecockPrice.value,
  })
  creating.value = false
  newLocation.value = ''
}
</script>

<template>
  <div class="flex flex-wrap items-center gap-2 rounded-xl border border-brand-pink-dark/40 bg-white/5 p-3">
    <span class="text-sm text-white/60">Session:</span>
    <select
      v-if="sessionsStore.sessions.length > 0"
      :value="sessionsStore.currentSessionId ?? ''"
      class="rounded-lg border border-brand-pink-dark/40 bg-brand-black px-2 py-1 text-sm"
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
        class="w-32 rounded-lg border border-brand-pink-dark/40 bg-brand-black px-2 py-1 text-sm"
      />
      <input
        v-model.number="newCourtFee"
        type="number"
        min="0"
        placeholder="ค่าสนาม/คน"
        title="ค่าสนามต่อคน (บาท)"
        class="w-24 rounded-lg border border-brand-pink-dark/40 bg-brand-black px-2 py-1 text-sm"
      />
      <input
        v-model.number="newShuttlecockPrice"
        type="number"
        min="0"
        placeholder="ค่าลูก/เกม"
        title="ค่าลูกแบดต่อเกม (บาท)"
        class="w-24 rounded-lg border border-brand-pink-dark/40 bg-brand-black px-2 py-1 text-sm"
      />
      <button class="rounded-full bg-brand-pink px-3 py-1 text-sm font-semibold text-brand-black" @click="createToday">
        บันทึก
      </button>
      <button class="text-sm text-white/50" @click="creating = false">ยกเลิก</button>
    </template>
  </div>
</template>
