<script setup lang="ts">
/**
 * Niddeaw Pass in LINE: the gold card while one runs, what it gives, buying
 * it with credit, and tonight's two members not to be partnered with.
 *
 * Only card holders (a 1,000 pack or more bought through LINE) can buy one;
 * the rest are pointed at topping up. The blocks are private: nobody else,
 * admins included, is shown them.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as lineApi from '@/api/line'
import type { LinePass } from '@/api/line'
import { apiErrorMessage } from '@/api/errors'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { formatDate } from '@/utils/format'
import type { Locale } from '@/i18n'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'
import LinePassNight from '@/components/line/LinePassNight.vue'
import LinePassStats from '@/components/line/LinePassStats.vue'
import LinePassStyle from '@/components/line/LinePassStyle.vue'

type Tab = 'perks' | 'style' | 'stats' | 'night'
const props = defineProps<{ token: string; name: string; avatarUrl?: string | null; tier?: string; tab?: Tab }>()
const emit = defineEmits<{ back: []; credit: [] }>()
const { t, locale } = useI18n()
const { confirm } = useConfirmDialog()

const data = ref<LinePass | null>(null)
const problem = ref('')
const busy = ref<string | null>(null)
const picking = ref(false)
const search = ref('')

const num = (n: number): string => n.toLocaleString('en-US', { maximumFractionDigits: 1 })
const active = computed(() => !!data.value?.ends_at)
// The pages beyond the perks: the looks while a pass runs or once one is
// earned; the numbers and tonight's picture only while it runs.
const tab = ref<Tab>(props.tab ?? 'perks')
const tabs = computed<Tab[]>(() => {
  if (!data.value) return []
  if (active.value) return ['perks', 'style', 'stats', 'night']
  return data.value.frames_open.length || data.value.cards_open.length ? ['perks', 'style'] : []
})
const shownTab = computed<Tab>(() => (tabs.value.includes(tab.value) ? tab.value : 'perks'))
const left = computed(() => (data.value ? data.value.max_blocks - data.value.blocks.length : 0))
const shown = computed(() => {
  const q = search.value.trim().toLowerCase()
  return (data.value?.candidates ?? []).filter((c) => !q || c.nickname.toLowerCase().includes(q))
})

async function run(key: string, job: () => Promise<LinePass>, fallback: string): Promise<void> {
  busy.value = key
  problem.value = ''
  try {
    data.value = await job()
  } catch (e) {
    problem.value = apiErrorMessage(e, fallback)
  } finally {
    busy.value = null
  }
}

onMounted(() => run('load', () => lineApi.getPass(props.token), t('pass.loadFailed')))

async function buy(): Promise<void> {
  if (!data.value) return
  const ok = await confirm({
    title: active.value ? t('pass.renewTitle') : t('pass.buyTitle'),
    message: t('pass.buyConfirm', { price: num(data.value.price), days: data.value.days, balance: num(data.value.balance) }),
    confirmLabel: t('pass.buyGo', { price: num(data.value.price) }),
  })
  if (ok) await run('buy', () => lineApi.buyPass(props.token), t('pass.buyFailed'))
}

async function block(playerId: string): Promise<void> {
  await run(playerId, () => lineApi.addPassBlock(props.token, playerId), t('pass.blockFailed'))
  if (left.value <= 0) picking.value = false
}
</script>

<template>
  <section class="flex flex-col gap-3">
    <button type="button" class="-mb-1 flex min-h-11 w-fit items-center gap-1 text-sm text-white/70" @click="emit('back')">
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 6l-6 6 6 6" /></svg>
      {{ t('pass.back') }}
    </button>

    <p v-if="!data && !problem" class="text-sm text-white/60">{{ t('common.loading') }}</p>

    <template v-if="data">
      <!-- the card -->
      <div class="pass-card" :class="{ off: !active }">
        <span v-if="active" class="pass-on">{{ t('pass.on') }}</span>
        <p class="pass-k">NIDDEAW PASS</p>
        <p v-if="active" class="pass-n">{{ name }}</p>
        <p v-else class="pass-price"><b>{{ num(data.price) }}</b> {{ t('pass.perDays', { days: data.days }) }}</p>
        <p class="pass-d">
          {{ active && data.ends_at ? t('pass.until', { when: formatDate(data.ends_at, locale as Locale) }) : t('pass.pitch') }}
        </p>
      </div>

      <div v-if="tabs.length" class="tabs" role="tablist">
        <button
          v-for="k in tabs"
          :key="k"
          type="button"
          role="tab"
          :aria-selected="shownTab === k"
          :class="{ on: shownTab === k }"
          @click="tab = k"
        >
          {{ t(`passPlus.tab${k[0]!.toUpperCase()}${k.slice(1)}`) }}
        </button>
      </div>

      <LinePassStyle
        v-if="shownTab === 'style'"
        :token="token"
        :data="data"
        :name="name"
        :avatar-url="avatarUrl"
        :tier="tier"
        @saved="data = $event"
      />
      <LinePassStats v-else-if="shownTab === 'stats'" :token="token" />
      <LinePassNight v-else-if="shownTab === 'night'" :token="token" :avatar-url="avatarUrl" />

      <template v-else>
      <ul class="grid gap-1.5">
        <li class="perk"><span class="ic" aria-hidden="true">⚖︎</span><span><b>{{ t('pass.perkOdds') }}</b><small>{{ t('pass.perkOddsHint') }}</small></span></li>
        <li class="perk"><span class="ic" aria-hidden="true">⦸</span><span><b>{{ t('pass.perkBlock', { n: data.max_blocks }) }}</b><small>{{ t('pass.perkBlockHint') }}</small></span></li>
      </ul>

      <!-- buying -->
      <template v-if="data.eligible">
        <button type="button" class="buy-btn" :disabled="busy === 'buy'" @click="buy">
          {{ busy === 'buy' ? '…' : active ? t('pass.renew', { price: num(data.price), days: data.days }) : t('pass.buy', { price: num(data.price) }) }}
        </button>
        <p class="text-center text-xs text-white/50">{{ t('pass.balance', { n: num(data.balance) }) }}</p>
      </template>
      <div v-else class="need-card">
        <p>{{ t('pass.needCard') }}</p>
        <button type="button" class="glass-pill mt-2 w-full justify-center" @click="emit('credit')">{{ t('pass.toCredit') }}</button>
      </div>

      <!-- tonight's blocks -->
      <section v-if="active" class="mt-2" aria-labelledby="pass-blocks">
        <h2 id="pass-blocks" class="flex items-center justify-between text-sm font-medium text-white/85">
          {{ t('pass.blocksTitle') }}
          <span class="font-display text-[#ffcf4d]">{{ data.blocks.length }} / {{ data.max_blocks }}</span>
        </h2>
        <p v-if="!data.checked_in" class="mt-1 text-xs text-white/55">{{ t('pass.blocksNotIn') }}</p>
        <template v-else>
          <ul class="mt-2 grid gap-1.5">
            <li v-for="b in data.blocks" :key="b.player_id" class="slot">
              <PlayerAvatar :name="b.nickname" :avatar-url="b.avatar_url ?? undefined" size="sm" round />
              <span class="flex-1 truncate">{{ b.nickname }}</span>
              <button
                type="button"
                class="slot-x"
                :disabled="busy === b.player_id"
                @click="run(b.player_id, () => lineApi.removePassBlock(token, b.player_id), t('pass.blockFailed'))"
              >
                {{ t('pass.unblock') }}
              </button>
            </li>
          </ul>
          <button v-if="left > 0 && !picking" type="button" class="slot slot-add mt-1.5 w-full" @click="picking = true">
            ＋ {{ t('pass.pick', { n: left }) }}
          </button>
          <div v-if="picking" class="picker mt-2">
            <input v-model="search" type="search" class="w-full rounded-xl border border-white/15 bg-black/30 px-3 py-2 text-sm" :placeholder="t('pass.search')" />
            <ul class="mt-2 max-h-72 overflow-y-auto">
              <li v-for="c in shown" :key="c.player_id" class="pick-row">
                <PlayerAvatar :name="c.nickname" :avatar-url="c.avatar_url ?? undefined" size="sm" round />
                <span class="flex-1 truncate">{{ c.nickname }}</span>
                <button type="button" class="pick-btn" :disabled="busy === c.player_id" @click="block(c.player_id)">{{ t('pass.blockOne') }}</button>
              </li>
              <li v-if="shown.length === 0" class="py-2 text-xs text-white/50">{{ t('pass.nobody') }}</li>
            </ul>
            <button type="button" class="mt-2 text-xs text-white/60" @click="picking = false">{{ t('common.cancel') }}</button>
          </div>
          <p class="mt-2 text-xs leading-relaxed text-white/50">🔒 {{ t('pass.private') }}</p>
        </template>
      </section>
      </template>
    </template>

    <p v-if="problem" role="alert" class="text-sm text-status-error">{{ problem }}</p>
  </section>
</template>

<style scoped>
.tabs {
  display: grid;
  grid-auto-columns: 1fr;
  grid-auto-flow: column;
  gap: 4px;
  padding: 4px;
  border: 1px solid rgb(255 255 255 / 0.1);
  border-radius: 999px;
  background: rgb(0 0 0 / 0.3);
}
.tabs button {
  min-height: 36px;
  border-radius: 999px;
  color: rgb(255 255 255 / 0.65);
  font-size: 13px;
  font-weight: 600;
}
.tabs button.on {
  background: linear-gradient(90deg, #ffe58a, #f2c14e);
  color: #2a1a00;
}
.pass-card {
  position: relative;
  overflow: hidden;
  border-radius: 20px;
  padding: 16px;
  background: linear-gradient(135deg, #2a1a05, #5a3a08 45%, #1d1204);
  border: 1px solid rgb(255 207 77 / 0.5);
  box-shadow: 0 0 30px rgb(255 207 77 / 0.18);
}
.pass-card::after {
  content: '';
  position: absolute;
  inset: -40% -60%;
  background: linear-gradient(105deg, transparent 40%, rgb(255 241 184 / 0.25) 50%, transparent 60%);
  transform: rotate(8deg);
  animation: pass-shine 4.5s ease-in-out infinite;
  pointer-events: none;
}
.pass-card.off {
  filter: saturate(0.6);
}
@keyframes pass-shine {
  0%,
  60% {
    translate: -60% 0;
  }
  100% {
    translate: 60% 0;
  }
}
@media (prefers-reduced-motion: reduce) {
  .pass-card::after {
    animation: none;
  }
}
.pass-k {
  font-family: var(--font-display);
  font-weight: 700;
  letter-spacing: 0.18em;
  font-size: 12px;
  color: #ffcf4d;
}
.pass-n {
  font-family: var(--font-display);
  font-size: 26px;
  font-weight: 700;
  color: #fff1b8;
  margin-top: 2px;
}
.pass-price {
  margin-top: 6px;
  color: rgb(255 231 166 / 0.7);
  font-size: 13px;
}
.pass-price b {
  font-family: var(--font-display);
  font-size: 32px;
  color: #fff1b8;
}
.pass-d {
  font-size: 12px;
  color: rgb(255 231 166 / 0.7);
  margin-top: 4px;
}
.pass-on {
  position: absolute;
  right: 14px;
  top: 14px;
  font-size: 11px;
  border-radius: 999px;
  padding: 2px 8px;
  background: rgb(74 222 128 / 0.15);
  color: #4ade80;
  border: 1px solid rgb(74 222 128 / 0.4);
}
.perk {
  display: flex;
  gap: 10px;
  align-items: center;
  border-radius: 14px;
  padding: 9px 11px;
  font-size: 13px;
  background: var(--color-brand-surface);
  border: 1px solid rgb(255 255 255 / 0.07);
}
.perk b {
  font-weight: 500;
}
.perk small {
  display: block;
  font-size: 11px;
  color: rgb(255 255 255 / 0.5);
}
.ic {
  display: grid;
  place-items: center;
  flex: none;
  width: 30px;
  height: 30px;
  border-radius: 10px;
  color: #ffcf4d;
  background: rgb(255 207 77 / 0.12);
}
.buy-btn {
  min-height: 48px;
  border-radius: 999px;
  font-weight: 600;
  color: #2a1a05;
  background: linear-gradient(90deg, #ffcf4d, #ffe58f);
}
.buy-btn:disabled {
  opacity: 0.6;
}
.need-card {
  border-radius: 14px;
  padding: 12px;
  font-size: 13px;
  color: rgb(255 255 255 / 0.75);
  border: 1px dashed rgb(255 207 77 / 0.35);
}
.slot {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 48px;
  border-radius: 14px;
  padding: 6px 10px;
  font-size: 14px;
  border: 1px solid rgb(255 107 107 / 0.35);
  background: linear-gradient(90deg, rgb(255 107 107 / 0.1), transparent);
}
.slot-add {
  justify-content: center;
  border-style: dashed;
  border-color: rgb(255 255 255 / 0.2);
  background: none;
  color: rgb(255 255 255 / 0.7);
}
.slot-x {
  font-size: 12px;
  border-radius: 999px;
  padding: 4px 10px;
  color: rgb(255 255 255 / 0.65);
  border: 1px solid rgb(255 255 255 / 0.18);
}
.picker {
  border-radius: 16px;
  padding: 12px;
  background: var(--color-brand-surface-raised);
}
.pick-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 2px;
  font-size: 14px;
  border-bottom: 1px solid rgb(255 255 255 / 0.05);
}
.pick-btn {
  min-height: 32px;
  font-size: 12px;
  border-radius: 999px;
  padding: 0 12px;
  color: #ffb3b3;
  border: 1px solid rgb(255 107 107 / 0.45);
}
.pick-btn:disabled,
.slot-x:disabled {
  opacity: 0.5;
}
</style>
