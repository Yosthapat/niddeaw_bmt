<script setup lang="ts">
/**
 * Paying for the whole cart in one go: who is buying, one transfer and its
 * slip, then the order number. What is being paid for always comes from
 * the server (quoteCart), so the amount in the QR is the products' prices
 * now, not whatever the page last showed. A member who came from the club's
 * LINE page in this tab (api/line.ts rememberLineToken) and is linked there
 * skips "who": the order goes under their LINE-linked name, straight to pay.
 */
import SlidePill from '@/components/common/SlidePill.vue'
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import BrandQr from '@/components/common/BrandQr.vue'
import { useRouter } from 'vue-router'
import { getCartPayment, getPlayers, placeShopOrder, quoteCart, type ShopBuyer } from '@/api/public'
import { apiErrorMessage } from '@/api/errors'
import { getLineConfig, getLineMe, rememberedLineToken } from '@/api/line'
import type { PaymentInfoResponse, PlayerStats, Quote, ShopOrder } from '@/types'
import { formatPhone, orderNo, phoneDigits } from '@/types'
import { money } from '@/utils/format'
import { compressImage } from '@/utils/imageCompression'
import { useCartStore } from '@/stores/cart'
import PlayerAvatar from '@/components/players/PlayerAvatar.vue'

// Remembered on this phone, so the next order starts on the same name: the
// member picked last time, or the name and number a guest typed.
const LAST_BUYER_KEY = 'niddeaw_shop_buyer'
const LAST_GUEST_KEY = 'niddeaw_shop_guest'
const LINE_OA = 'https://line.me/R/ti/p/@369iojcn'

const router = useRouter()
const { t } = useI18n()
const cart = useCartStore()

const quote = ref<Quote | null>(null)
const members = ref<PlayerStats[]>([])
const loadError = ref<string | null>(null)
const step = ref<1 | 2 | 3>(1)
const query = ref('')
const buyerId = ref<string | null>(null)
// A member of the club, or someone from outside it giving a name and phone.
const mode = ref<'member' | 'guest'>('member')
const guestName = ref('')
const guestPhone = ref('')
// The member this tab's LINE account is linked to: the buyer unless they change it.
const linePlayerId = ref<string | null>(null)
// Not linked yet: a note under the picker asks them to link their name in
// LINE once, so the next order skips it. `lineWaiting`: they asked, and an
// admin hasn't confirmed it yet. `lineHref`: where linking starts, the LINE
// page in this tab when it came from LINE, else the club's LIFF link.
const lineWaiting = ref(false)
const lineHref = ref<string | null>(null)
const fromLine = rememberedLineToken() !== null
const pay = ref<PaymentInfoResponse | null>(null)
const payError = ref<string | null>(null)
const slip = ref<File | null>(null)
const slipName = ref('')
const sending = ref(false)
const sendError = ref<string | null>(null)
const tried = ref(false)
const placed = ref<ShopOrder | null>(null)

onMounted(async () => {
  // Nothing to pay for: back to the cart, which says so.
  if (cart.lines.length === 0) {
    router.replace('/shop/cart')
    return
  }
  try {
    const [q, m, line] = await Promise.all([quoteCart(cart.lines), getPlayers(), lineState(), linkStart()])
    // A line that can't be had is fixed on the cart page, not here.
    if (!q.ok) {
      router.replace('/shop/cart')
      return
    }
    quote.value = q
    members.value = m
    let remembered: string | null = null
    try {
      remembered = localStorage.getItem(LAST_BUYER_KEY)
    } catch {
      // private mode: just start unpicked
    }
    if (remembered && m.some((s) => s.player.id === remembered)) buyerId.value = remembered
    try {
      const guest = JSON.parse(localStorage.getItem(LAST_GUEST_KEY) ?? 'null') as { name?: unknown; phone?: unknown } | null
      if (guest && typeof guest.name === 'string' && typeof guest.phone === 'string') {
        guestName.value = guest.name
        guestPhone.value = guest.phone
        // last time it was a guest order and no member is remembered
        if (!buyerId.value) mode.value = 'guest'
      }
    } catch {
      // nothing remembered
    }
    if (line && m.some((s) => s.player.id === line)) {
      linePlayerId.value = line
      buyerId.value = line
      mode.value = 'member'
      void toPay()
    }
  } catch (e) {
    loadError.value = apiErrorMessage(e, t('shop.loadFailed'))
  }
})

/** The member this tab's LINE account is linked to, if it came from LINE. */
async function lineState(): Promise<string | null> {
  const token = rememberedLineToken()
  if (!token) return null
  try {
    const me = await getLineMe(token)
    lineWaiting.value = !me.player && !!(me.pending || me.application)
    return me.player?.id ?? null
  } catch {
    // an expired or refused token: pick the name as usual
    return null
  }
}

/** Where linking a name to LINE starts; nothing when LINE isn't switched on. */
async function linkStart(): Promise<void> {
  try {
    const config = await getLineConfig()
    if (config.enabled && config.liff_id) lineHref.value = fromLine ? '/line' : `https://liff.line.me/${config.liff_id}`
  } catch {
    // no note, then
  }
}

const viaLine = computed(() => mode.value === 'member' && !!buyerId.value && buyerId.value === linePlayerId.value)
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
const phone = computed(() => phoneDigits(guestPhone.value))
const guestReady = computed(() => guestName.value.trim().length > 0 && guestName.value.trim().length <= 80 && phone.value !== null)
const phoneHint = computed(() => {
  if (!guestPhone.value.trim()) return { text: t('shop.guestPhoneHint'), cls: 'text-white/55' }
  return phone.value
    ? { text: `✓ ${formatPhone(phone.value)}`, cls: 'text-[#7ff0b4]' }
    : { text: t('shop.guestPhoneBad'), cls: 'text-status-error' }
})
/** The name the order goes under, member or guest. */
const buyerName = computed(() => (mode.value === 'guest' ? guestName.value.trim() : (buyer.value?.nickname ?? '')))
const ready = computed(() => (mode.value === 'guest' ? guestReady.value : !!buyer.value))
const nextLabel = computed(() => {
  if (mode.value === 'member') return buyer.value ? t('shop.whoNext', { name: buyer.value.nickname }) : t('shop.whoFirst')
  if (!guestName.value.trim()) return t('shop.guestNameFirst')
  if (!phone.value) return t('shop.guestPhoneFirst')
  return t('shop.whoNext', { name: guestName.value.trim() })
})
const isGuestOrder = computed(() => mode.value === 'guest')
const units = computed(() => quote.value?.lines.reduce((n, l) => n + l.qty, 0) ?? 0)
const hasPreorder = computed(() => (placed.value?.items ?? quote.value?.lines ?? []).some((l) => l.sale_type === 'preorder'))

async function toPay(): Promise<void> {
  if (!ready.value) return
  try {
    if (mode.value === 'member' && buyerId.value) {
      localStorage.setItem(LAST_BUYER_KEY, buyerId.value)
    } else {
      localStorage.setItem(LAST_GUEST_KEY, JSON.stringify({ name: guestName.value.trim(), phone: phone.value }))
    }
  } catch {
    // not remembering is fine
  }
  step.value = 2
  window.scrollTo({ top: 0 })
  if (pay.value) return
  try {
    pay.value = await getCartPayment(cart.lines)
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
  if (!slip.value || !ready.value) return
  sending.value = true
  sendError.value = null
  const who: ShopBuyer =
    mode.value === 'guest'
      ? { guestName: guestName.value.trim(), guestPhone: phone.value ?? '' }
      : { playerId: buyerId.value ?? '' }
  try {
    placed.value = await placeShopOrder({ buyer: who, items: cart.lines, slip: slip.value })
    cart.clear()
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
  <!-- the world the rest of the site stands in, behind this page too -->
  <div class="home-world">
    <main class="mx-auto max-w-md px-4 pt-3 pb-8">
      <div class="flex items-center justify-between">
        <RouterLink v-if="step === 1" to="/shop/cart" class="inline-flex min-h-11 items-center gap-1 text-sm text-white/70">
          <span aria-hidden="true">←</span> {{ t('shop.cart') }}
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

      <template v-else-if="quote">
        <!-- what is being paid for, always in view -->
        <details v-if="step !== 3" class="mt-4 rounded-2xl border border-white/12 bg-white/5">
          <summary class="flex min-h-14 cursor-pointer list-none items-center gap-3 px-3">
            <span class="flex-1 text-sm">{{ t('shop.cartSummary', { lines: quote.lines.length, n: units }) }}</span>
            <span class="font-display text-lg font-bold text-brand-pink-light">{{ money(quote.total) }}</span>
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" class="chev text-white/60" aria-hidden="true"><path d="m6 9 6 6 6-6" /></svg>
          </summary>
          <ul class="flex flex-col gap-1.5 border-t border-white/10 px-3 py-2.5 text-sm">
            <li v-for="l in quote.lines" :key="`${l.product_id}-${l.size}`" class="flex justify-between gap-3">
              <span class="min-w-0 truncate">{{ l.product_name }}<span v-if="l.size" class="text-white/60"> · {{ l.size }}</span> × {{ l.qty }}</span>
              <span class="shrink-0">{{ money(l.line_total) }}</span>
            </li>
          </ul>
        </details>

        <!-- 1 · who -->
        <section v-if="step === 1" class="mt-5 flex flex-col gap-3">
          <h1 class="font-display text-2xl font-bold">{{ t('shop.whoTitle') }}</h1>
          <!-- a club member, or someone from outside -->
          <div role="radiogroup" :aria-label="t('shop.whoTitle')" class="relative flex gap-1 rounded-2xl bg-white/7 p-1">
            <SlidePill :watch-key="mode" tone="white" />
            <button
              v-for="m in (['member', 'guest'] as const)"
              :key="m"
              type="button"
              role="radio"
              :aria-checked="mode === m"
              :data-pill-on="mode === m ? '' : undefined"
              class="relative z-[1] min-h-11 flex-1 rounded-xl text-sm transition-colors"
              :class="mode === m ? 'font-medium text-brand-black' : 'text-white/75'"
              @click="mode = m"
            >
              {{ m === 'member' ? t('shop.whoMember') : t('shop.whoGuest') }}
            </button>
          </div>
        </section>
        <section v-if="step === 1 && mode === 'guest'" class="mt-3 flex flex-col gap-3">
          <p class="text-sm text-white/70">{{ t('shop.guestHint') }}</p>
          <label class="flex flex-col gap-1.5 text-sm">
            {{ t('shop.guestName') }}
            <input v-model="guestName" type="text" autocomplete="name" maxlength="80" :placeholder="t('shop.guestNamePlaceholder')" class="min-h-12 rounded-2xl border border-white/22 bg-white/7 px-4 text-base outline-none focus:border-brand-pink" />
          </label>
          <label class="flex flex-col gap-1.5 text-sm">
            {{ t('shop.guestPhone') }}
            <input
              v-model="guestPhone"
              type="tel"
              inputmode="numeric"
              autocomplete="tel"
              maxlength="20"
              placeholder="08x-xxx-xxxx"
              :aria-invalid="!!guestPhone.trim() && !phone"
              class="min-h-12 rounded-2xl border bg-white/7 px-4 text-base outline-none focus:border-brand-pink"
              :class="guestPhone.trim() && !phone ? 'border-status-error' : 'border-white/22'"
            />
            <span class="text-xs" :class="phoneHint.cls" aria-live="polite">{{ phoneHint.text }}</span>
          </label>
          <ul class="flex flex-col gap-2 rounded-2xl border border-white/12 bg-white/5 p-3.5 text-[13px] text-white/80">
            <li class="flex gap-2"><span class="text-brand-pink">●</span>{{ t('shop.guestPickup') }}</li>
            <li class="flex gap-2"><span class="text-brand-pink">●</span>{{ t('shop.guestPrivacy') }}</li>
          </ul>
          <!-- floats over the list, so it never has to be scrolled to -->
          <div class="float-go">
            <button type="button" class="cta w-full" :disabled="!ready" @click="toPay">{{ nextLabel }}</button>
          </div>
        </section>
        <section v-if="step === 1 && mode === 'member'" class="mt-3 flex flex-col gap-3">
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
          <div v-if="lineHref && !linePlayerId" class="line-nudge">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden="true" class="mt-0.5 flex-none text-[#06c755]"><path d="M12 3C6.5 3 2 6.6 2 11c0 3.9 3.5 7.2 8.3 7.9.3.1.8.2.9.5.1.3.1.7 0 1l-.1.9c0 .3-.2 1 .9.5 1.1-.5 5.9-3.5 8-5.9C21.4 14.3 22 12.7 22 11c0-4.4-4.5-8-10-8Z" /></svg>
            <div class="min-w-0 flex-1">
              <template v-if="lineWaiting">
                <p class="font-semibold text-white/90">{{ t('shop.lineWaitTitle') }}</p>
                <p class="mt-0.5 text-white/65">{{ t('shop.lineWaitText') }}</p>
              </template>
              <template v-else>
                <p class="font-semibold text-white/90">{{ t('shop.lineNudgeTitle') }}</p>
                <p class="mt-0.5 text-white/65">{{ t('shop.lineNudgeText') }}</p>
                <RouterLink v-if="fromLine" :to="lineHref" class="line-link">{{ t('shop.lineNudgeGo') }}</RouterLink>
                <a v-else :href="lineHref" class="line-link">{{ t('shop.lineNudgeGo') }}</a>
              </template>
            </div>
          </div>
          <!-- floats over the list, so it never has to be scrolled to -->
          <div class="float-go">
            <button type="button" class="cta w-full" :disabled="!ready" @click="toPay">{{ nextLabel }}</button>
          </div>
        </section>

        <!-- 2 · pay -->
        <section v-if="step === 2" class="mt-5 flex flex-col items-center gap-3">
          <h1 class="self-start font-display text-2xl font-bold">{{ t('shop.payTitle') }}</h1>
          <div v-if="buyerName" class="buyer-chip">
            <PlayerAvatar v-if="mode === 'member' && buyer" :name="buyer.nickname" :avatar-url="buyer.avatar_url" size="sm" />
            <span class="min-w-0 flex-1 truncate">{{ t('shop.orderingAs', { name: buyerName }) }}</span>
            <span v-if="viaLine" class="line-tag">{{ t('shop.viaLine') }}</span>
            <button type="button" class="change" @click="step = 1">{{ t('shop.changeBuyer') }}</button>
          </div>
          <p v-if="payError" class="self-start text-sm text-status-error">{{ payError }}</p>
          <template v-else-if="pay">
            <BrandQr
              v-if="pay.qr_modules"
              :modules="pay.qr_modules"
              :amount="pay.amount"
              :account-name="pay.bank_account_name"
              :alt="`QR ${money(pay.amount)}`"
              saveable
              file-name="niddeaw-shop-qr.png"
              class="w-full"
            />
            <div v-else-if="pay.data_uri" class="flex flex-col items-center gap-1.5 rounded-2xl bg-white p-3.5">
              <img :src="pay.data_uri" alt="QR PromptPay" class="h-48 w-48" />
              <span v-if="pay.method === 'promptpay'" class="text-[11px] text-[#4a3a5a]">{{ t('shop.payPromptpay') }}</span>
            </div>
            <span v-if="pay.qr_modules && pay.method === 'promptpay'" class="text-xs text-white/60">{{ t('shop.payPromptpay') }}</span>
            <p v-if="pay.bank_name" class="text-center text-sm text-white/75">
              {{ t('shop.payBank') }} {{ pay.bank_name }} · {{ pay.bank_account_number }}
              <span v-if="pay.bank_account_name"> ({{ pay.bank_account_name }})</span>
            </p>
            <div class="text-center">
              <p class="text-sm text-white/70">{{ t('shop.payAmount') }}</p>
              <p class="font-display text-3xl font-bold text-brand-pink-light">{{ money(pay.amount) }}</p>
            </div>
            <a v-if="pay.data_uri && !pay.qr_modules" :href="pay.data_uri" download="niddeaw-shop-qr.png" class="ghost">{{ t('shop.saveQr') }}</a>
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
          <p v-if="sendError" class="w-full text-sm text-status-error" role="alert">
            {{ sendError }}
            <RouterLink to="/shop/cart" class="underline">{{ t('shop.backToCart') }}</RouterLink>
          </p>
          <button type="button" class="cta mt-2 w-full" :disabled="sending" @click="send">
            {{ sending ? t('shop.sending') : t('shop.send') }}
          </button>
        </section>

        <!-- 3 · done -->
        <section v-else-if="placed" class="mt-6 flex flex-col items-center gap-3 text-center">
          <img src="/pwa-icons/pwa-192x192.png" alt="" class="h-28 w-28 rounded-full shadow-[0_0_30px_rgb(234_76_164/0.5)]" />
          <h1 class="font-display text-2xl font-bold">{{ t('shop.doneTitle') }}</h1>
          <!-- with no profile, the number is a guest's only handle on the order -->
          <div v-if="isGuestOrder" class="flex w-full flex-col items-center gap-1 rounded-2xl border border-[#ffe14d]/50 bg-white/7 p-4">
            <span class="text-xs text-white/70">{{ t('shop.guestOrderNo') }}</span>
            <span class="font-display text-4xl font-bold tracking-wide text-[#ffe14d] [text-shadow:0_0_16px_rgb(255_225_77/0.45)]">{{ orderNo(placed.order_no) }}</span>
            <span class="text-sm">{{ buyerName }} · {{ phone ? formatPhone(phone) : '' }}</span>
            <span class="mt-1 rounded-full bg-[#ffe14d]/14 px-3 py-1 text-xs text-[#ffe14d]">{{ t('shop.guestScreenshot') }}</span>
          </div>
          <span v-else class="rounded-full border border-white/20 bg-white/8 px-4 py-1.5 font-display font-bold">{{ orderNo(placed.order_no) }}</span>
          <ul class="flex w-full flex-col gap-1 text-left text-sm text-white/80">
            <li v-for="(l, i) in placed.items" :key="i" class="flex justify-between gap-3">
              <span class="min-w-0 truncate">{{ l.product_name }}<span v-if="l.size" class="text-white/60"> · {{ l.size }}</span> × {{ l.qty }}</span>
              <span class="shrink-0">{{ money(l.line_total) }}</span>
            </li>
            <li class="flex justify-between gap-3 border-t border-white/12 pt-1 font-medium">
              <span>{{ t('shop.total') }}</span><span>{{ money(placed.total) }}</span>
            </li>
          </ul>
          <ul class="flex w-full flex-col gap-2 rounded-2xl border border-white/12 bg-white/5 p-4 text-left text-sm">
            <li class="flex gap-2.5"><span class="text-[#ffe14d]">●</span>{{ t('shop.doneCheck') }}</li>
            <li v-if="hasPreorder" class="flex gap-2.5"><span class="text-white/40">●</span>{{ t('shop.donePreorderCart') }}</li>
            <li v-if="isGuestOrder" class="flex gap-2.5"><span class="text-white/40">●</span>{{ t('shop.guestDonePickup', { no: orderNo(placed.order_no), name: buyerName }) }}</li>
            <li v-else class="flex gap-2.5"><span class="text-white/40">●</span>{{ t('shop.donePickup', { name: buyerName }) }}</li>
            <li v-if="isGuestOrder" class="flex gap-2.5"><span class="text-white/40">●</span>{{ t('shop.guestDoneAsk') }}</li>
          </ul>
          <p v-if="!isGuestOrder" class="text-xs text-white/60">{{ t('shop.doneProfile') }}</p>
          <div class="mt-2 flex w-full flex-col gap-2">
            <a v-if="isGuestOrder" :href="LINE_OA" target="_blank" rel="noopener noreferrer" class="cta line-cta">{{ t('shop.guestLine') }}</a>
            <RouterLink v-else-if="buyer" :to="`/members/${buyer.id}`" class="cta">{{ t('shop.toProfile') }}</RouterLink>
            <RouterLink to="/shop" class="ghost">{{ t('shop.backToShop') }}</RouterLink>
          </div>
        </section>
      </template>
    </main>
  </div>
</template>

<style scoped>
.line-cta {
  background: #037f36;
  box-shadow: 0 5px 0 #014a1f;
}
details[open] .chev {
  rotate: 180deg;
}
.line-nudge {
  display: flex;
  gap: 10px;
  border-radius: 16px;
  border: 1px solid rgb(6 199 85 / 0.35);
  background: rgb(6 199 85 / 0.08);
  padding: 12px 14px;
  font-size: 13px;
  line-height: 1.45;
}
.line-link {
  display: inline-flex;
  min-height: 40px;
  align-items: center;
  margin-top: 8px;
  border-radius: 999px;
  background: #06c755;
  padding: 0 16px;
  font-size: 14px;
  font-weight: 700;
  color: #fff;
}
.line-link:focus-visible {
  outline: 2px solid #fff;
  outline-offset: 2px;
}
.buyer-chip {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 10px;
  border-radius: 16px;
  border: 1px solid rgb(255 255 255 / 0.12);
  background: rgb(255 255 255 / 0.05);
  padding: 8px 8px 8px 12px;
  font-size: 14px;
}
.line-tag {
  flex: none;
  border-radius: 999px;
  background: rgb(6 199 85 / 0.16);
  padding: 3px 9px;
  font-size: 12px;
  font-weight: 600;
  color: #7dffb0;
}
.buyer-chip .change {
  flex: none;
  min-height: 36px;
  border-radius: 999px;
  padding: 0 12px;
  font-size: 13px;
  color: rgb(255 255 255 / 0.75);
  text-decoration: underline;
  text-underline-offset: 3px;
}
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
/* the backdrop runs down to the screen edge behind the tab bar, so the
   list never peeks out between the button and the bar */
.float-go {
  position: sticky;
  z-index: 10;
  bottom: 0;
  margin: 4px -16px calc(-90px - env(safe-area-inset-bottom, 0px));
  padding: 18px 16px calc(102px + env(safe-area-inset-bottom, 0px));
  background: linear-gradient(to top, #0b0518 82%, rgb(11 5 24 / 0));
}
@media (min-width: 900px) {
  .float-go {
    margin-bottom: 0;
    padding-bottom: 16px;
  }
}
.float-go .cta:disabled {
  background: #2a2238;
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
