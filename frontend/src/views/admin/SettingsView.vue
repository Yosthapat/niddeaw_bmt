<script setup lang="ts">
import { onMounted, ref } from 'vue'
import * as adminApi from '@/api/admin'
import type { ClubSettings, PromptPayType } from '@/types'
import AdminNav from '@/components/layout/AdminNav.vue'

const settings = ref<ClubSettings | null>(null)
const saving = ref(false)
const saved = ref(false)

onMounted(async () => {
  settings.value = await adminApi.getClubSettings()
})

async function save(): Promise<void> {
  if (!settings.value) return
  saving.value = true
  saved.value = false
  try {
    settings.value = await adminApi.updateClubSettings(settings.value)
    saved.value = true
  } finally {
    saving.value = false
  }
}

const promptPayTypeOptions: { value: PromptPayType; label: string }[] = [
  { value: 'phone', label: 'เบอร์โทรศัพท์' },
  { value: 'national_id', label: 'เลขบัตรประชาชน' },
  { value: 'ewallet', label: 'e-Wallet ID' },
]
</script>

<template>
  <AdminNav />
  <main class="mx-auto max-w-md px-4 py-6">
    <h1 class="text-2xl font-bold text-brand-pink">ตั้งค่าก๊วน</h1>

    <form v-if="settings" class="mt-6 flex flex-col gap-4" @submit.prevent="save">
      <label class="flex flex-col gap-1 text-sm">
        PromptPay ID
        <input
          v-model="settings.promptpay_id"
          placeholder="เบอร์โทร / เลขบัตร / e-Wallet ID"
          class="rounded-lg border border-brand-pink-dark/40 bg-white/5 px-3 py-2 outline-none focus:border-brand-pink"
        />
      </label>

      <label class="flex flex-col gap-1 text-sm">
        ประเภท PromptPay ID
        <select
          v-model="settings.promptpay_type"
          class="rounded-lg border border-brand-pink-dark/40 bg-brand-black px-3 py-2"
        >
          <option v-for="opt in promptPayTypeOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
      </label>

      <label class="flex flex-col gap-1 text-sm">
        อัตราค่าหัวเริ่มต้น (บาท/ชั่วโมง)
        <input
          v-model.number="settings.default_rate_per_hour"
          type="number"
          min="0"
          class="rounded-lg border border-brand-pink-dark/40 bg-white/5 px-3 py-2 outline-none focus:border-brand-pink"
        />
      </label>

      <p v-if="saved" class="text-sm text-green-400">บันทึกแล้ว</p>

      <button
        type="submit"
        :disabled="saving"
        class="rounded-lg bg-brand-pink px-3 py-2 font-semibold text-brand-black disabled:opacity-50"
      >
        {{ saving ? 'กำลังบันทึก...' : 'บันทึกการตั้งค่า' }}
      </button>
    </form>
  </main>
</template>
