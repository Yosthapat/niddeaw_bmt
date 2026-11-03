<script setup lang="ts">
/**
 * "My bills" in LINE: every night they were billed for, newest first, and
 * what they still owe. A night they forgot to check out of shows up here
 * once the admin closes it, and can be paid from here like any other.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as lineApi from '@/api/line'
import type { LineBill, LineBills } from '@/api/line'
import { apiErrorMessage } from '@/api/errors'
import { formatDateWithWeekday, money } from '@/utils/format'
import type { Locale } from '@/i18n'
import LineBillPay from '@/components/line/LineBillPay.vue'

const props = defineProps<{ token: string }>()
const emit = defineEmits<{ back: [] }>()
const { t, locale } = useI18n()

const data = ref<LineBills | null>(null)
const problem = ref('')
const openId = ref<string | null>(null)

async function load(): Promise<void> {
  try {
    data.value = await lineApi.getBills(props.token)
  } catch (e) {
    problem.value = apiErrorMessage(e, t('lineBills.loadFailed'))
  }
}
onMounted(load)

type Badge = 'due' | 'checking' | 'rejected' | 'free' | 'paid'
function badge(b: LineBill): Badge {
  if (b.paid_status === 'paid') return 'paid'
  if (b.amount <= 0) return 'free'
  if (b.slip_url) return 'checking'
  return b.slip_rejected_at ? 'rejected' : 'due'
}
const open = computed(() => data.value?.bills.find((b) => b.id === openId.value) ?? null)

function onUpdated(bill: LineBill): void {
  if (!data.value) return
  data.value = { ...data.value, bills: data.value.bills.map((b) => (b.id === bill.id ? bill : b)) }
  void load()
}
</script>

<template>
  <section class="flex flex-1 flex-col gap-4">
    <!-- one bill, open to pay -->
    <template v-if="open">
      <div>
        <p class="world-eyebrow">BILL · {{ formatDateWithWeekday(open.night.date, locale as Locale) }}</p>
        <h1 class="world-title mt-1 text-2xl">{{ t('lineBills.payTitle', { amount: money(open.amount) }) }}</h1>
        <p class="mt-1 text-sm text-white/65">{{ t('lineCheckout.games', { n: open.game_count }) }} · {{ open.night.location }}</p>
      </div>
      <LineBillPay :token="token" :bill="open" @updated="onUpdated" />
      <button type="button" class="glass-pill mt-auto w-full justify-center" @click="openId = null">{{ t('lineBills.backToList') }}</button>
    </template>

    <template v-else>
      <div>
        <p class="world-eyebrow">MY BILLS</p>
        <h1 class="world-title mt-1 text-2xl">{{ t('lineBills.title', { name: data?.player.nickname ?? '' }) }}</h1>
      </div>
      <div class="world-card flex items-center justify-between p-4">
        <span>{{ t('lineBills.due') }}</span>
        <span class="font-display text-2xl font-bold" :class="(data?.due ?? 0) > 0 ? 'text-[#ffd34d]' : 'text-[#7ff0b4]'">{{ money(data?.due ?? 0) }}</span>
      </div>
      <p v-if="problem" class="text-sm text-status-error" role="alert">{{ problem }}</p>
      <p v-else-if="!data" class="text-sm text-white/60" role="status">{{ t('common.loading') }}</p>
      <ul v-else class="flex flex-col gap-2">
        <li v-for="b in data.bills" :key="b.id">
          <button
            type="button"
            class="row flex min-h-16 w-full items-center gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-2.5 text-left"
            :disabled="badge(b) === 'free'"
            @click="openId = b.id"
          >
            <span class="min-w-0 flex-1">
              <span class="block font-medium">{{ formatDateWithWeekday(b.night.date, locale as Locale) }}</span>
              <span class="block text-xs text-white/60">{{ t('lineCheckout.games', { n: b.game_count }) }} · {{ money(b.amount) }}</span>
            </span>
            <span class="badge shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold" :class="badge(b)">{{ t(`lineBills.badge.${badge(b)}`) }}</span>
            <span v-if="badge(b) === 'due' || badge(b) === 'rejected'" class="pay shrink-0 rounded-full px-3 py-1.5 text-sm font-bold">{{ t('lineBills.pay') }}</span>
          </button>
        </li>
        <li v-if="data.bills.length === 0" class="world-card p-4 text-center text-sm text-white/60">{{ t('lineBills.none') }}</li>
      </ul>
      <p class="text-xs text-white/55">{{ t('lineBills.forgotNote') }}</p>
      <button type="button" class="glass-pill mt-auto w-full justify-center" @click="emit('back')">{{ t('lineBills.back') }}</button>
    </template>
  </section>
</template>

<style scoped>
.badge.due {
  background: rgb(255 211 77 / 0.15);
  color: #ffd34d;
}
.badge.checking {
  background: rgb(169 155 255 / 0.18);
  color: #cbbfff;
}
.badge.rejected {
  background: rgb(255 107 138 / 0.16);
  color: #ff9fb2;
}
.badge.free {
  background: rgb(255 255 255 / 0.08);
  color: rgb(255 255 255 / 0.6);
}
.badge.paid {
  background: rgb(127 240 180 / 0.14);
  color: #7ff0b4;
}
.pay {
  background: linear-gradient(#ff8fd0, #ea4ca4);
  color: #1a0410;
}
</style>
