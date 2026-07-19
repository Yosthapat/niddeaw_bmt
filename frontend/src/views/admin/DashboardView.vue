<script setup lang="ts">
import { onMounted } from 'vue'
import { useSessionsStore } from '@/stores/sessions'
import { usePlayersStore } from '@/stores/players'
import AdminNav from '@/components/layout/AdminNav.vue'
import SessionPicker from '@/components/layout/SessionPicker.vue'

const sessionsStore = useSessionsStore()
const playersStore = usePlayersStore()

onMounted(() => {
  sessionsStore.refresh()
  playersStore.ensureLoaded()
})
</script>

<template>
  <AdminNav />
  <main class="mx-auto max-w-4xl px-4 py-6">
    <h1 class="text-2xl font-bold text-brand-pink">Admin Dashboard</h1>

    <div class="mt-4">
      <SessionPicker />
    </div>

    <div class="mt-6 grid gap-3 sm:grid-cols-3">
      <div class="rounded-xl border border-brand-pink-dark/40 bg-white/5 p-4">
        <p class="text-xs text-white/50">สมาชิกทั้งหมด</p>
        <p class="mt-1 text-2xl font-bold">{{ playersStore.players.length }}</p>
      </div>
      <div class="rounded-xl border border-brand-pink-dark/40 bg-white/5 p-4">
        <p class="text-xs text-white/50">Session ที่เปิดอยู่</p>
        <p class="mt-1 text-2xl font-bold">{{ sessionsStore.openSessions.length }}</p>
      </div>
      <div class="rounded-xl border border-brand-pink-dark/40 bg-white/5 p-4">
        <p class="text-xs text-white/50">Session ทั้งหมด</p>
        <p class="mt-1 text-2xl font-bold">{{ sessionsStore.sessions.length }}</p>
      </div>
    </div>

    <div class="mt-8 grid gap-3 sm:grid-cols-2">
      <RouterLink
        to="/admin/checkin"
        class="rounded-xl border border-brand-pink-dark/40 bg-white/5 p-4 hover:bg-brand-pink-dark/20"
      >
        <p class="font-semibold text-brand-pink">เช็คอิน</p>
        <p class="text-sm text-white/60">จัดการเช็คอิน-เอาท์ผู้เล่นในสนาม</p>
      </RouterLink>
      <RouterLink
        to="/admin/matchmaking"
        class="rounded-xl border border-brand-pink-dark/40 bg-white/5 p-4 hover:bg-brand-pink-dark/20"
      >
        <p class="font-semibold text-brand-pink">จับคู่</p>
        <p class="text-sm text-white/60">จัดคู่ตาม ELO และบันทึกผลแมตช์</p>
      </RouterLink>
      <RouterLink
        to="/admin/billing"
        class="rounded-xl border border-brand-pink-dark/40 bg-white/5 p-4 hover:bg-brand-pink-dark/20"
      >
        <p class="font-semibold text-brand-pink">คิดเงิน</p>
        <p class="text-sm text-white/60">ปิด session, สร้าง PromptPay QR</p>
      </RouterLink>
      <RouterLink
        to="/admin/settings"
        class="rounded-xl border border-brand-pink-dark/40 bg-white/5 p-4 hover:bg-brand-pink-dark/20"
      >
        <p class="font-semibold text-brand-pink">ตั้งค่า</p>
        <p class="text-sm text-white/60">PromptPay ID, อัตราค่าหัวเริ่มต้น</p>
      </RouterLink>
    </div>
  </main>
</template>
