<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Product } from '@/types'
import { formatDayMonth, money } from '@/utils/format'
import { BADGE_CLASS, productBadge } from './productBadge'

const props = defineProps<{ product: Product }>()
const { t, locale } = useI18n()

const badge = computed(() => {
  const b = productBadge(props.product)
  const params = { ...b.params }
  if (typeof params.date === 'string' && params.date) params.date = formatDayMonth(params.date, locale.value as 'th' | 'en')
  return { text: t(b.key, params), cls: BADGE_CLASS[b.tone], out: b.tone === 'out' }
})
const sizesLine = computed(() => {
  const s = props.product.sizes
  if (s.length === 0) return t('shop.oneSize')
  return s.length === 1 ? s[0] : t('shop.sizesRange', { from: s[0], to: s[s.length - 1] })
})
</script>

<template>
  <RouterLink
    :to="`/shop/${product.id}`"
    class="product-card flex h-full flex-col gap-2 rounded-[18px] border border-white/14 p-2 pb-3 transition-colors hover:border-brand-pink/60"
    :class="{ 'opacity-55': badge.out }"
  >
    <div class="relative flex aspect-[1/0.95] items-center justify-center overflow-hidden rounded-xl bg-[radial-gradient(circle_at_50%_40%,rgb(234_76_164/0.45),#1a0d33_75%)]">
      <img
        v-if="product.image_urls[0]"
        :src="product.image_urls[0]"
        :alt="product.name"
        loading="lazy"
        decoding="async"
        class="absolute inset-0 h-full w-full object-cover"
        :class="{ grayscale: badge.out }"
      />
      <img v-else src="/pwa-icons/pwa-192x192.png" alt="" class="h-1/2 w-1/2 rounded-full object-contain opacity-70" />
      <span class="absolute top-2 left-2 rounded-full px-2.5 py-1 text-[11px] leading-none font-medium" :class="badge.cls">
        {{ badge.text }}
      </span>
    </div>
    <div class="flex flex-col gap-0.5 px-1">
      <span class="text-sm leading-snug font-medium">{{ product.name }}</span>
      <span class="text-xs text-white/65">{{ sizesLine }}</span>
      <span class="mt-1 font-display text-lg font-bold" :class="badge.out ? 'text-white/50' : 'text-brand-pink-light'">
        {{ money(product.price) }}
      </span>
    </div>
  </RouterLink>
</template>

<style scoped>
.product-card {
  background: linear-gradient(160deg, rgb(255 255 255 / 0.1), rgb(255 255 255 / 0.03));
}
</style>
