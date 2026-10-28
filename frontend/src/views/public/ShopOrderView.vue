<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { getPlayers, getShopPayment, getShopProduct, placeShopOrder } from '@/api/public'
import { apiErrorMessage } from '@/api/errors'
import type { PaymentInfoResponse, PlayerStats, Product, ShopOrder } from '@/types'
import { orderNo } from '@/types'
import { formatDayMonth, money } from '@/utils/format'
import { compressImage } from '@/utils/imageCompression'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'

// Remembered on this phone, so a member's next order starts on their name.
const LAST_BUYER_KEY = 'niddeaw_shop_buyer'

const route = useRoute()
const { t, locale } = useI18n()
const productId = String(route.params.id)
const size = typeof route.query.size === 'string' ? route.query.size : ''
const qty = Math.min(10, Math.max(1, Number(route.query.qty) || 1))

const product = ref<Product | null>(null)
const members = ref<PlayerStats[]>([])
const loadError = ref<string | null>(null)
const step = ref<1 | 2 | 3>(1)
const query = ref('')
const buyerId = ref<string | null>(null)
const pay = ref<PaymentInfoResponse | null>(null)
const payError = ref<string | null>(null)
const slip = ref<File | null>(null)
const slipName = ref('')
const sending = ref(false)
const sendError = ref<string | null>(null)
const tried = ref(false)
const placed = ref<ShopOrder | null>(null)

onMounted(async () => {
  try {
    const [p, m] = await Promise.all([getShopProduct(productId), getPlayers()])
    product.value = p
    members.value = m
    let remembered: string | null = null
    try {
      remembered = localStorage.getItem(LAST_BUYER_KEY)
    } catch {
      // private mode: just start unpicked
    }
    if (remembered && m.some((s) => s.player.id === remembered)) buyerId.value = remembered
  } catch (e) {
    loadError.value = apiErrorMessage(e, t('shop.loadFailed'))
  }
})

const buyer = computed(() => members.value.find((s) => s.player.id === buyerId.value)?.player ?? null)
const found = computed(() => {
  const q = query.value.trim().toLowerCase()
  const list = members.value.filter(
    (s) => !q || s.player.nickname.toLowerCase().includes(q) || s.player.member_code.toLowerCase().includes(q),
  )
  // The remembered buyer first, then by name.
  return [...list]
    .sort((a, b) => Number(b.player.id === buyerId.value) - Number(a.player.id === buyerId.value) || a.player.nickname.localeCompare(b.player.nickname))
    .slice(0, 30)
})
const total = computed(() => (product.value ? product.value.price * qty : 0))
const isPre = computed(() => product.value?.sale_type === 'preorder')
const day = (iso: string | null): string => (iso ? formatDayMonth(iso, locale.value as 'th' | 'en') : '—')

async function toPay(): Promise<void> {
  if (!buyerId.value) return
  try {
    localStorage.setItem(LAST_BUYER_KEY, buyerId.value)
  } catch {
    // not remembering is fine
  }
  step.value = 2
  window.scrollTo({ top: 0 })
  if (pay.value) return
  try {
    pay.value = await getShopPayment(productId, qty)
  } catch (e) {
    payError.value = apiErrorMessage(e, t('shop.payFailed'))
  }
}

async function onSlip(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const picked = input.files?.[0]
  input.value = ''
  if (!picked) return
  slipName.value = picked.name
  slip.value = await compressImage(picked)
}

async function send(): Promise<void> {
  tried.value = true
  if (!slip.value || !buyerId.value) return
  sending.value = true
  sendError.value = null
  try {
    placed.value = await placeShopOrder({ productId, playerId: buyerId.value, size, qty, slip: slip.value })
    step.value = 3
    window.scrollTo({ top: 0 })
  } catch (e) {
    sendError.value = apiErrorMessage(e, t('shop.sendFailed'))
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <main class="mx-auto max-w-md px-4 pt-3 pb-8">
    <div class="flex items-center justify-between">
      <RouterLink v-if="step === 1" :to="`/shop/${productId}`" class="inline-flex min-h-11 items-center gap-1 text-sm text-white/70">
        <span aria-hidden="true">←</span> {{ product?.name ?? t('shop.back') }}
      </RouterLink>
      <button v-else-if="step === 2" type="button" class="inline-flex min-h-11 items-center gap-1 text-sm text-white/70" @click="step = 1">
        <span aria-hidden="true">←</span> {{ t('shop.whoTitle') }}
      </button>
      <span v-else />
      <span class="text-sm text-white/65">{{ step === 3 ? t('shop.done') : t('shop.stepOf', { n: step }) }}</span>
    </div>
    <div class="mt-1 grid grid-cols-3 gap-1.5" aria-hidden="true">
      <span v-for="n in 3" :key="n" class="h-1.5 rounded-full" :class="n <= step ? 'bg-gradient-to-r from-[#ff8fd0] to-brand-pink' : 'bg-white/14'" />
    </div>

    <p v-if="loadError" class="mt-6 text-status-error">{{ loadError }}</p>

    <template v-else-if="product">
      <!-- the order, always in view -->
      <div class="mt-4 flex items-center gap-3 rounded-2xl border border-white/12 bg-white/5 p-2.5">
        <img v-if="product.image_urls[0]" :src="product.image_urls[0]" alt="" class="h-13 w-13 shrink-0 rounded-lg object-cover" />
        <div class="min-w-0 flex-1">
          <p class="truncate text-sm font-medium">{{ product.name }}</p>
          <p class="text-xs text-white/65">
            <template v-if="isPre">{{ t('shop.filterPreorder') }} · </template>
            {{ size ? t('shop.summary', { size, qty }) : t('shop.summaryOne', { qty }) }}
          </p>
        </div>
        <span class="font-display font-bold text-brand-pink-light">{{ money(total) }}</span>
      </div>

      <!-- 1 · who -->
      <section v-if="step === 1" class="mt-5 flex flex-col gap-3">
        <h1 class="font-display text-2xl font-bold">{{ t('shop.whoTitle') }}</h1>
        <p class="text-sm text-white/70">{{ t('shop.whoHint') }}</p>
        <input
          v-model="query"
          type="search"
          :placeholder="t('shop.whoSearch')"
          :aria-label="t('shop.whoSearch')"
          class="min-h-12 rounded-full border border-white/20 bg-white/7 px-4 text-base outline-none focus:border-brand-pink"
        />
        <div role="radiogroup" :aria-label="t('nav.members')" class="flex max-h-[46vh] flex-col gap-1.5 overflow-y-auto">
          <button
            v-for="s in found"
            :key="s.player.id"
            type="button"
            role="radio"
            :aria-checked="buyerId === s.player.id"
            class="who-btn"
            @click="buyerId = s.player.id"
          >
            <PlayerAvatar :name="s.player.nickname" :avatar-url="s.player.avatar_url" size="sm" />
            <span class="flex-1 text-left">{{ s.player.nickname }}</span>
            <span class="text-xs text-white/55">{{ s.player.member_code }}</span>
          </button>
        </div>
        <p class="text-xs text-white/55">{{ t('shop.whoMissing') }}</p>
        <button type="button" class="cta mt-2" :disabled="!buyer" @click="toPay">
          {{ buyer ? t('shop.whoNext', { name: buyer.nickname }) : t('shop.whoFirst') }}
        </button>
      </section>

      <!-- 2 · pay -->
      <section v-else-if="step === 2" class="mt-5 flex flex-col items-center gap-3">
        <h1 class="self-start font-display text-2xl font-bold">{{ t('shop.payTitle') }}</h1>
        <p v-if="payError" class="self-start text-sm text-status-error">{{ payError }}</p>
        <template v-else-if="pay">
          <div v-if="pay.data_uri" class="flex flex-col items-center gap-1.5 rounded-2xl bg-white p-3.5">
            <img :src="pay.data_uri" alt="QR PromptPay" class="h-48 w-48" />
            <span v-if="pay.method === 'promptpay'" class="text-[11px] text-[#4a3a5a]">{{ t('shop.payPromptpay') }}</span>
          </div>
          <p v-if="pay.bank_name" class="text-center text-sm text-white/75">
            {{ t('shop.payBank') }} {{ pay.bank_name }} · {{ pay.bank_account_number }}
            <span v-if="pay.bank_account_name"> ({{ pay.bank_account_name }})</span>
          </p>
          <div class="text-center">
            <p class="text-sm text-white/70">{{ t('shop.payAmount') }}</p>
            <p class="font-display text-3xl font-bold text-brand-pink-light">{{ money(pay.amount) }}</p>
          </div>
          <a v-if="pay.data_uri" :href="pay.data_uri" :download="`niddeaw-${product.id.slice(0, 6)}.png`" class="ghost">{{ t('shop.saveQr') }}</a>
        </template>
        <p v-else class="text-sm text-white/60">{{ t('common.loading') }}</p>

        <div class="mt-1 flex w-full flex-col gap-1.5">
          <span class="text-sm font-medium">{{ t('shop.slip') }}</span>
          <label class="slip-pick" :class="{ 'is-set': slip }">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 16V4 M7 9l5-5 5 5 M4 20h16" /></svg>
            {{ slip ? t('shop.slipChange', { name: slipName }) : t('shop.slipPick') }}
            <input type="file" accept="image/*" class="sr-only" @change="onSlip" />
          </label>
          <span v-if="tried && !slip" class="text-xs text-status-error">{{ t('shop.slipRequired') }}</span>
        </div>
        <p v-if="sendError" class="w-full text-sm text-status-error" role="alert">{{ sendError }}</p>
        <button type="button" class="cta mt-2 w-full" :disabled="sending" @click="send">
          {{ sending ? t('shop.sending') : t('shop.send') }}
        </button>
      </section>

      <!-- 3 · done -->
      <section v-else-if="placed" class="mt-6 flex flex-col items-center gap-3 text-center">
        <img src="/pwa-icons/pwa-192x192.png" alt="" class="h-28 w-28 rounded-full shadow-[0_0_30px_rgb(234_76_164/0.5)]" />
        <h1 class="font-display text-2xl font-bold">{{ t('shop.doneTitle') }}</h1>
        <span class="rounded-full border border-white/20 bg-white/8 px-4 py-1.5 font-display font-bold">{{ orderNo(placed.order_no) }}</span>
        <ul class="flex w-full flex-col gap-2 rounded-2xl border border-white/12 bg-white/5 p-4 text-left text-sm">
          <li class="flex gap-2.5"><span class="text-[#ffe14d]">●</span>{{ t('shop.doneCheck') }}</li>
          <li v-if="isPre" class="flex gap-2.5"><span class="text-white/40">●</span>{{ t('shop.donePreorder', { closes: day(product.preorder_closes_on), delivers: day(product.preorder_delivers_on) }) }}</li>
          <li class="flex gap-2.5"><span class="text-white/40">●</span>{{ t('shop.donePickup', { name: buyer?.nickname ?? '' }) }}</li>
        </ul>
        <p class="text-xs text-white/60">{{ t('shop.doneProfile') }}</p>
        <div class="mt-2 flex w-full flex-col gap-2">
          <RouterLink v-if="buyer" :to="`/members/${buyer.id}`" class="cta">{{ t('shop.toProfile') }}</RouterLink>
          <RouterLink to="/shop" class="ghost">{{ t('shop.backToShop') }}</RouterLink>
        </div>
      </section>
    </template>
  </main>
</template>

<style scoped>
.who-btn {
  display: flex;
  min-height: 56px;
  align-items: center;
  gap: 12px;
  padding: 6px 12px;
  border: 1px solid rgb(255 255 255 / 0.14);
  border-radius: 14px;
  background: rgb(255 255 255 / 0.05);
}
.who-btn[aria-checked='true'] {
  border-color: var(--color-brand-pink);
  background: rgb(234 76 164 / 0.16);
  box-shadow: 0 0 0 1px var(--color-brand-pink);
}
.cta {
  display: flex;
  height: 54px;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  background: linear-gradient(#ff8fd0, var(--color-brand-pink) 55%, #c22f86);
  box-shadow:
    0 5px 0 #6d1247,
    0 12px 24px rgb(234 76 164 / 0.4),
    inset 0 1px 0 rgb(255 255 255 / 0.55);
  color: #fff;
  font-family: var(--font-display);
  font-size: 17px;
  font-weight: 700;
}
.cta:disabled {
  background: rgb(255 255 255 / 0.12);
  box-shadow: none;
  color: rgb(255 255 255 / 0.7);
}
.ghost {
  display: flex;
  width: 100%;
  min-height: 48px;
  align-items: center;
  justify-content: center;
  border: 1px solid rgb(255 255 255 / 0.22);
  border-radius: 14px;
  background: rgb(255 255 255 / 0.06);
}
.slip-pick {
  display: flex;
  min-height: 56px;
  cursor: pointer;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 0 12px;
  border: 1px dashed rgb(255 255 255 / 0.35);
  border-radius: 14px;
  background: rgb(255 255 255 / 0.04);
  font-size: 14px;
  text-align: center;
}
.slip-pick.is-set {
  border: 1px solid #7ff0b4;
  background: rgb(127 240 180 / 0.1);
}
</style>
