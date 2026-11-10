<script setup lang="ts">
/**
 * The cart: everything picked, priced by the server as it is right now, one
 * line per product and size. A line that can no longer be had as it is
 * (sold out, fewer left, a pre-order that closed) says so beside itself
 * and offers the fix, and the order can't go in until every line is fine.
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { quoteCart } from '@/api/public'
import { apiErrorMessage } from '@/api/errors'
import type { Quote, QuoteLine } from '@/types'
import { money } from '@/utils/format'
import { useCartStore, MAX_LINE_QTY } from '@/stores/cart'

const { t } = useI18n()
const router = useRouter()
const cart = useCartStore()
const quote = ref<Quote | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
let asked = 0

// Re-priced whenever the cart changes; only the latest answer is drawn.
watch(
  () => JSON.stringify(cart.lines),
  async () => {
    if (cart.lines.length === 0) {
      quote.value = null
      return
    }
    const mine = ++asked
    loading.value = true
    try {
      const q = await quoteCart(cart.lines)
      if (mine === asked) {
        quote.value = q
        error.value = null
      }
    } catch (e) {
      if (mine === asked) error.value = apiErrorMessage(e, t('shop.cartFailed'))
    } finally {
      if (mine === asked) loading.value = false
    }
  },
  { immediate: true },
)

const key = (l: { product_id: string; size: string }): string => `${l.product_id}|${l.size}`
const units = computed(() => cart.count)
const canOrder = computed(() => !!quote.value?.ok && !loading.value)

function step(l: QuoteLine, by: number): void {
  cart.setQty(l.product_id, l.size, l.qty + by)
}
function maxFor(l: QuoteLine): number {
  return Math.min(MAX_LINE_QTY, l.available ?? MAX_LINE_QTY)
}
/** The one-tap fix a problem line offers: fewer, or out of the cart. */
function fix(l: QuoteLine): void {
  if (l.available && l.available > 0 && l.available < l.qty) cart.setQty(l.product_id, l.size, l.available)
  else cart.remove(l.product_id, l.size)
}
function fixLabel(l: QuoteLine): string {
  return l.available && l.available > 0 && l.available < l.qty ? t('shop.fixTo', { n: l.available }) : t('shop.remove')
}
</script>

<template>
  <!-- the world the rest of the site stands in, behind this page too -->
  <div class="no-enter-fx home-world">
    <main class="mx-auto max-w-2xl px-4 pt-4 pb-48 md:pb-12">
      <RouterLink to="/shop" class="inline-flex min-h-11 items-center gap-1 text-sm text-white/70 hover:text-white">
        <span aria-hidden="true">←</span> {{ t('shop.keepShopping') }}
      </RouterLink>
      <h1 class="mt-1 font-display text-3xl font-bold">{{ t('shop.cart') }}</h1>

      <div v-if="cart.lines.length === 0" class="mt-10 flex flex-col items-center gap-3 text-center text-white/70">
        <svg viewBox="0 0 24 24" width="56" height="56" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="text-brand-pink" aria-hidden="true">
          <path d="M3 4h2l2.4 11.2a2 2 0 0 0 2 1.6h7.7a2 2 0 0 0 2-1.5L21 8H6.2" />
          <circle cx="10" cy="20" r="1.2" />
          <circle cx="17" cy="20" r="1.2" />
        </svg>
        <p>{{ t('shop.cartEmpty') }}</p>
        <RouterLink to="/shop" class="cta mt-2 w-full max-w-xs">{{ t('shop.toShop') }}</RouterLink>
      </div>

      <template v-else>
        <p v-if="error" class="mt-4 text-sm text-status-error" role="alert">{{ error }}</p>
        <ul class="mt-4 flex flex-col gap-2.5" :aria-busy="loading">
          <li
            v-for="l in quote?.lines ?? []"
            :key="key(l)"
            class="flex gap-3 rounded-2xl border p-2.5"
            :class="l.problem ? 'border-status-error/50 bg-status-error/8' : 'border-white/12 bg-white/5'"
          >
            <RouterLink :to="`/shop/${l.product_id}`" class="h-20 w-20 shrink-0 overflow-hidden rounded-xl bg-[#f3eaf1]">
              <img v-if="l.image_url" :src="l.image_url" :alt="l.product_name" class="h-full w-full object-contain" />
            </RouterLink>
            <div class="flex min-w-0 flex-1 flex-col gap-1">
              <div class="flex items-start justify-between gap-2">
                <p class="min-w-0 text-sm leading-snug font-medium">
                  {{ l.product_name }}
                  <span v-if="l.size" class="ml-1 rounded-md bg-white/12 px-1.5 py-0.5 font-display text-xs">{{ l.size }}</span>
                </p>
                <button type="button" class="-mt-1 -mr-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-white/60 hover:bg-white/10" :aria-label="t('shop.removeLine', { name: l.product_name, size: l.size })" @click="cart.remove(l.product_id, l.size)">✕</button>
              </div>
              <p class="text-xs text-white/60">
                {{ l.sale_type === 'preorder' ? t('shop.filterPreorder') + ' · ' : '' }}{{ money(l.unit_price) }} / {{ t('shop.unit') }}
              </p>
              <p v-if="l.problem" class="flex flex-wrap items-center gap-2 text-xs text-status-error">
                {{ l.problem }}
                <button type="button" class="rounded-full border border-status-error/60 px-2.5 py-1 font-medium" @click="fix(l)">{{ fixLabel(l) }}</button>
              </p>
              <div class="mt-auto flex items-center justify-between">
                <div class="flex items-center gap-1.5">
                  <button type="button" class="qty-btn" :aria-label="t('shop.less')" :disabled="l.qty <= 1" @click="step(l, -1)">−</button>
                  <span class="min-w-6 text-center font-display font-bold" aria-live="polite">{{ l.qty }}</span>
                  <button type="button" class="qty-btn" :aria-label="t('shop.more')" :disabled="l.qty >= maxFor(l)" @click="step(l, 1)">+</button>
                </div>
                <span class="font-display font-bold">{{ money(l.line_total) }}</span>
              </div>
            </div>
          </li>
        </ul>

        <!-- desktop: the total under the lines -->
        <div class="mt-5 hidden items-center justify-between gap-4 md:flex">
          <div>
            <p class="text-sm text-white/65">{{ t('shop.totalUnits', { n: units }) }}</p>
            <p class="font-display text-3xl font-bold text-brand-pink-light">{{ money(quote?.total ?? 0) }}</p>
          </div>
          <button type="button" class="cta min-w-64" :disabled="!canOrder" @click="router.push('/shop/checkout')">
            {{ quote && !quote.ok ? t('shop.fixFirst') : t('shop.checkout') }}
          </button>
        </div>

        <!-- phone: the total and the button above the tab bar -->
        <div class="fixed inset-x-0 bottom-[calc(96px+env(safe-area-inset-bottom,0px))] z-20 flex items-center gap-3 border-t border-white/8 bg-[#0b0518]/95 px-4 py-3 backdrop-blur md:hidden">
          <div class="flex flex-col">
            <span class="text-xs text-white/65">{{ t('shop.totalUnits', { n: units }) }}</span>
            <span class="font-display text-lg font-bold whitespace-nowrap">{{ money(quote?.total ?? 0) }}</span>
          </div>
          <button type="button" class="cta flex-1" :disabled="!canOrder" @click="router.push('/shop/checkout')">
            {{ quote && !quote.ok ? t('shop.fixFirst') : t('shop.checkout') }}
          </button>
        </div>
      </template>
    </main>
  </div>
</template>

<style scoped>
.qty-btn {
  width: 36px;
  height: 36px;
  border: 1px solid rgb(255 255 255 / 0.2);
  border-radius: 10px;
  background: rgb(255 255 255 / 0.06);
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 700;
}
.qty-btn:disabled {
  opacity: 0.35;
}
.cta {
  display: flex;
  height: 54px;
  align-items: center;
  justify-content: center;
  padding: 0 16px;
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
</style>
