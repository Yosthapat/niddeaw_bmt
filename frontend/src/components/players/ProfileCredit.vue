<script setup lang="ts">
/**
 * A member's credit on their own profile — only for them. The page knows
 * it's them when they came from the club's LINE page in this tab (it keeps
 * their LINE token for the tab: api/line.ts rememberLineToken) and that
 * token's member is the one on this profile. The server checks the token;
 * anyone else, or the same person in an ordinary browser, sees nothing.
 */
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import * as lineApi from '@/api/line'
import type { LedgerEntry, LineCredit } from '@/api/line'
import { formatDayMonth } from '@/utils/format'
import type { Locale } from '@/i18n'

const props = defineProps<{ playerId: string }>()
const { t, locale } = useI18n()
const mine = ref<LineCredit | null>(null)
const showHistory = ref(false)
const num = (n: number): string => n.toLocaleString('en-US')

watch(
  () => props.playerId,
  async (id) => {
    mine.value = null
    const token = lineApi.rememberedLineToken()
    if (!token) return
    try {
      const credit = await lineApi.getCredit(token)
      if (credit.player.id === id) mine.value = credit
    } catch {
      // an expired or refused token: quietly not theirs to see here
    }
  },
  { immediate: true },
)

const ICON: Record<LedgerEntry['kind'], string> = { topup: '🪙', bill: '🏸', refund: '↩️', adjust: '🛠' }
</script>

<template>
  <section v-if="mine" class="mt-6">
    <div class="wallet">
      <div class="flex items-center justify-between">
        <span class="text-xs text-[#ffe9a8]/85">{{ t('lineCredit.mine') }}</span>
        <span class="text-xs text-white/60">🔒 {{ t('lineCredit.onlyYou') }}</span>
      </div>
      <div class="mt-0.5 flex items-center gap-2.5">
        <span class="coin h-8 w-8 text-base" aria-hidden="true">฿</span>
        <span class="bal">{{ num(mine.balance) }}</span>
      </div>
      <p class="text-xs text-white/60">{{ t('lineCredit.what') }}</p>
      <div class="mt-3 flex gap-2">
        <RouterLink to="/line/credit" class="gold flex-1">{{ t('lineCredit.topUp') }}</RouterLink>
        <button type="button" class="glass-pill flex-1 justify-center" :aria-expanded="showHistory" @click="showHistory = !showHistory">
          {{ showHistory ? t('lineCredit.hideHistory') : t('lineCredit.showHistory') }}
        </button>
      </div>
    </div>
    <ul v-if="showHistory" class="world-card mt-2 divide-y divide-white/8 px-4">
      <li v-for="h in mine.history.slice(0, 10)" :key="h.id" class="flex items-center gap-3 py-2.5">
        <span aria-hidden="true">{{ ICON[h.kind] }}</span>
        <span class="min-w-0 flex-1">
          <span class="block text-sm">{{ t(`lineCredit.kind.${h.kind}`) }}</span>
          <span class="block truncate text-xs text-white/55">{{ formatDayMonth(h.created_at, locale as Locale) }}<template v-if="h.note"> · {{ h.note }}</template></span>
        </span>
        <b class="font-display" :class="h.delta > 0 ? 'text-[#7ff0b4]' : 'text-[#ffb08a]'">{{ h.delta > 0 ? '+' : '−' }}{{ num(Math.abs(h.delta)) }}</b>
      </li>
      <li v-if="mine.history.length === 0" class="py-3 text-center text-sm text-white/55">{{ t('lineCredit.noHistory') }}</li>
    </ul>
  </section>
</template>

<style scoped>
.wallet {
  border-radius: 20px;
  padding: 16px;
  background:
    radial-gradient(260px 160px at 85% 10%, rgb(255 197 49 / 0.35), transparent 70%),
    linear-gradient(135deg, #3a2408, #1c1030 70%);
  border: 1px solid rgb(255 211 77 / 0.45);
  box-shadow: 0 14px 30px -14px rgb(255 197 49 / 0.6);
}
.bal {
  font: 700 32px 'Chakra Petch', sans-serif;
  color: #ffe9a8;
  text-shadow: 0 0 16px rgb(255 197 49 / 0.5);
}
.coin {
  display: inline-flex;
  flex: none;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 30%, #fff2b3, #ffc531 45%, #c98500);
  color: #4a2d00;
  font-family: 'Chakra Petch', sans-serif;
  font-weight: 700;
}
.gold {
  display: flex;
  min-height: 44px;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: linear-gradient(#ffe58a, #ffad1f);
  color: #2e1a00;
  font: 700 14px 'Chakra Petch', sans-serif;
}
</style>
