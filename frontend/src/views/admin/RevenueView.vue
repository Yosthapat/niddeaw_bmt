<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import * as adminApi from '@/api/admin'
import { ApiError } from '@/api/client'
import type { DailyRevenue } from '@/types'
import AdminNav from '@/components/layout/AdminNav.vue'

const daily = ref<DailyRevenue[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

function apiErrorMessage(e: unknown, fallback: string): string {
  if (e instanceof ApiError) {
    return `${fallback} (${e.status}: ${e.message})`
  }
  return fallback
}

function formatDate(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString('th-TH', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

const grandTotal = computed(() => daily.value.reduce((sum, d) => sum + d.total_amount, 0))
const grandPaid = computed(() => daily.value.reduce((sum, d) => sum + d.paid_amount, 0))
const grandUnpaid = computed(() => daily.value.reduce((sum, d) => sum + d.unpaid_amount, 0))

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    daily.value = await adminApi.getRevenue()
  } catch (e) {
    error.value = apiErrorMessage(e, 'โหลดยอดรายรับไม่สำเร็จ')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <AdminNav />
  <main class="mx-auto max-w-3xl px-4 py-6">
    <h1 class="text-2xl font-bold text-brand-pink">ยอดรายรับ</h1>

    <p v-if="loading" class="mt-6 text-white/60">กำลังโหลด...</p>
    <p v-else-if="error" class="mt-6 text-status-error">{{ error }}</p>
    <p v-else-if="daily.length === 0" class="mt-6 text-sm text-white/40">ยังไม่มีข้อมูลรายรับ</p>

    <template v-else>
      <div class="mt-6 grid grid-cols-3 gap-2.5">
        <div class="hud-panel border border-brand-pink/40 bg-brand-surface p-3 text-center">
          <p class="text-xs tracking-wide text-white/40 uppercase">รวมทั้งหมด</p>
          <p class="mt-1 font-display text-xl font-bold text-brand-pink">฿{{ grandTotal.toFixed(2) }}</p>
        </div>
        <div class="hud-panel border border-brand-pink/20 bg-brand-surface p-3 text-center">
          <p class="text-xs tracking-wide text-white/40 uppercase">จ่ายแล้ว</p>
          <p class="mt-1 font-display text-xl font-bold text-status-success">฿{{ grandPaid.toFixed(2) }}</p>
        </div>
        <div class="hud-panel border border-brand-pink/20 bg-brand-surface p-3 text-center">
          <p class="text-xs tracking-wide text-white/40 uppercase">ยังไม่จ่าย</p>
          <p class="mt-1 font-display text-xl font-bold text-status-error">฿{{ grandUnpaid.toFixed(2) }}</p>
        </div>
      </div>

      <ul class="mt-6 space-y-2">
        <li
          v-for="d in daily"
          :key="d.date"
          class="hud-panel border border-brand-pink/20 bg-brand-surface px-4 py-3"
        >
          <div class="flex items-center justify-between gap-3">
            <span class="font-medium">{{ formatDate(d.date) }}</span>
            <span class="font-display text-lg font-bold text-brand-pink">฿{{ d.total_amount.toFixed(2) }}</span>
          </div>
          <div class="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-white/50">
            <span>{{ d.session_count }} session{{ d.session_count > 1 ? 's' : '' }}</span>
            <span>·</span>
            <span>{{ d.billing_count }} บิล</span>
            <span>·</span>
            <span class="text-status-success">จ่ายแล้ว ฿{{ d.paid_amount.toFixed(2) }}</span>
            <span v-if="d.unpaid_amount > 0" class="text-status-error">
              ค้าง ฿{{ d.unpaid_amount.toFixed(2) }}
            </span>
          </div>
        </li>
      </ul>
    </template>
  </main>
</template>
