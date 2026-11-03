<script setup lang="ts">
// The way to the cart from anywhere in the shop, with how much is in it.
import { useI18n } from 'vue-i18n'
import { useCartStore } from '@/stores/cart'

/** On a phone, the icon and count only — beside the filter there is no
 *  room for the word as well. */
defineProps<{ compact?: boolean }>()
const { t } = useI18n()
const cart = useCartStore()
</script>

<template>
  <RouterLink
    to="/shop/cart"
    class="relative inline-flex min-h-11 items-center gap-2 rounded-full border border-white/18 bg-white/7 px-4 text-sm hover:bg-white/12"
    :aria-label="t('shop.cartWith', { n: cart.count })"
  >
    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M3 4h2l2.4 11.2a2 2 0 0 0 2 1.6h7.7a2 2 0 0 0 2-1.5L21 8H6.2" />
      <circle cx="10" cy="20" r="1.2" />
      <circle cx="17" cy="20" r="1.2" />
    </svg>
    <span :class="compact ? 'max-sm:sr-only' : ''">{{ t('shop.cart') }}</span>
    <span v-if="cart.count" class="min-w-6 rounded-full bg-brand-pink px-1.5 py-0.5 text-center font-display text-xs leading-none font-bold text-white">
      {{ cart.count }}
    </span>
  </RouterLink>
</template>
